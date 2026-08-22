"""Rebuild the audio of TEDxJP-5K-V / TEDxJP-5K-N from the source videos.

The clips cannot be redistributed (TEDx talks are CC BY-NC-ND 4.0), so this
repository ships only the segmentation plan and the reference text.  Run this
script once and it fetches the source material and reproduces ``clips/``.

    pip install numpy soundfile "yt-dlp[default]"
    python rebuild.py

Requires ffmpeg on PATH, plus a JavaScript runtime such as Node.js for the
YouTube extractor.  Keep yt-dlp current: YouTube-side changes break older
versions, and a nightly build is occasionally needed before the fix lands in a
release.  If a talk has been made private or removed since the plan was
written, its segments are skipped and listed at the end; everything else still
builds.

``plan.json``      one entry per segment: source video, cut range, reference
``augment.jsonl``  TEDxJP-5K-N only -- the corruption applied to each segment,
                   including the id of the music track mixed into it
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

try:
    import soundfile
except ImportError:  # pragma: no cover
    soundfile = None

SAMPLE_RATE = 16000
_MIN_RMS = 1e-8
CODECS = {
    "libmp3lame": ("mp3", "mp3"),
    "aac": ("adts", "aac"),
    "libopus": ("ogg", "ogg"),
}


# --------------------------------------------------------------------------
# download
# --------------------------------------------------------------------------


def ytdlp_extra_args(ytdlp: str) -> list[str]:
    """Options this yt-dlp understands.

    ``--js-runtimes`` is recent; passing it to an older build aborts with
    "no such option" before anything downloads.
    """
    try:
        help_text = subprocess.run([ytdlp, "--help"], capture_output=True,
                                   text=True, errors="replace").stdout
    except OSError:
        return []
    return ["--js-runtimes", "node"] if "--js-runtimes" in help_text else []


def fetch(video_id: str, out_dir: Path, extension: str, ytdlp: str,
          extra: list[str]) -> bool:
    """Download one YouTube item's audio, or report that it is unavailable."""
    destination = out_dir / f"{video_id}.{extension}"
    if destination.exists() and destination.stat().st_size > 0:
        return True
    command = [
        ytdlp, f"https://www.youtube.com/watch?v={video_id}",
        *extra, "--no-playlist", "--extract-audio",
        "--audio-format", extension,
        "--postprocessor-args", f"ffmpeg:-ac 1 -ar {SAMPLE_RATE}",
        "--output", str(out_dir / f"{video_id}.%(ext)s"),
        "--no-progress", "--quiet", "--no-warnings",
    ]
    subprocess.run(command, capture_output=True)
    return destination.exists() and destination.stat().st_size > 0


def download_all(ids: list[str], out_dir: Path, extension: str,
                 args: argparse.Namespace, label: str) -> set[str]:
    """Fetch every id, returning the ones that could not be retrieved."""
    out_dir.mkdir(parents=True, exist_ok=True)
    extra = ytdlp_extra_args(args.ytdlp)
    missing: set[str] = set()
    for done, video_id in enumerate(ids, 1):
        if not fetch(video_id, out_dir, extension, args.ytdlp, extra):
            missing.add(video_id)
        if done % 25 == 0 or done == len(ids):
            print(f"  {label}: {done}/{len(ids)}"
                  + (f" ({len(missing)} unavailable)" if missing else ""),
                  flush=True)
    return missing


# --------------------------------------------------------------------------
# audio helpers
# --------------------------------------------------------------------------


def rms(signal: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(signal)))) if signal.size else 0.0


def run_ffmpeg(payload: bytes, in_args: list[str], out_args: list[str]) -> bytes:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         *in_args, "-i", "pipe:0", *out_args, "pipe:1"],
        input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors="replace")[:400])
    return proc.stdout


def to_pcm(signal: np.ndarray) -> bytes:
    return np.clip(signal * 32767.0, -32768, 32767).astype("<i2").tobytes()


def from_pcm(payload: bytes) -> np.ndarray:
    return np.frombuffer(payload, dtype="<i2").astype(np.float32) / 32768.0


def mix_at_snr(speech: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    speech_rms, noise_rms = rms(speech), rms(noise)
    if speech_rms <= _MIN_RMS or noise_rms <= _MIN_RMS:
        return speech
    return speech + (speech_rms / noise_rms) * 10.0 ** (-snr_db / 20.0) \
        * noise[: len(speech)]


def apply_corruption(audio: np.ndarray, recipe: dict, bgm_dir: Path,
                     max_duration: float) -> np.ndarray:
    """Replay one ``augment.jsonl`` entry onto a freshly cut clip."""
    raw = ["-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", "1"]

    if "stretch" in recipe:
        audio = from_pcm(run_ffmpeg(
            to_pcm(audio), raw,
            ["-filter:a", f"atempo={recipe['stretch']:.6f}", *raw]))

    if "bgm" in recipe:
        entry = recipe["bgm"]
        track = bgm_dir / f"{entry['track']}.flac"
        if track.exists():
            with soundfile.SoundFile(str(track)) as handle:
                start = min(int(entry["offset_frames"]),
                            max(0, handle.frames - len(audio)))
                handle.seek(start)
                music = handle.read(len(audio), dtype="float32")
            if music.ndim > 1:
                music = music.mean(axis=1)
            if len(music) < len(audio):
                music = np.pad(music, (0, len(audio) - len(music)))
            audio = mix_at_snr(audio, music, entry["snr_db"])

    if "white_snr_db" in recipe:
        generator = np.random.default_rng(recipe["white_seed"])
        audio = mix_at_snr(
            audio, generator.standard_normal(len(audio)).astype(np.float32),
            recipe["white_snr_db"])

    if "bgm" in recipe or "white_snr_db" in recipe:
        peak = float(np.abs(audio).max()) if audio.size else 0.0
        if peak > 0.99:
            audio = audio * (0.99 / peak)

    if "codec" in recipe:
        muxer, demuxer = CODECS[recipe["codec"]["format"]]
        encoded = run_ffmpeg(to_pcm(audio), raw,
                             ["-c:a", recipe["codec"]["format"], "-b:a",
                              f"{recipe['codec']['bitrate_kbps']}k",
                              "-f", muxer])
        audio = from_pcm(run_ffmpeg(encoded, ["-f", demuxer], raw))

    limit = int(max_duration * SAMPLE_RATE)
    return audio[:limit] if len(audio) > limit else audio


# --------------------------------------------------------------------------


def build_clip(block: dict, recipe: dict | None, root: Path,
               bgm_dir: Path, max_duration: float) -> str | None:
    source = root / "source" / f"{block['video_id']}.wav"
    if not source.exists():
        return None
    with soundfile.SoundFile(str(source)) as handle:
        start = max(0, int(round(block["start"] * handle.samplerate)))
        stop = min(handle.frames, int(round(block["end"] * handle.samplerate)))
        handle.seek(start)
        audio = handle.read(stop - start, dtype="float32")
    if recipe:
        audio = apply_corruption(audio, recipe, bgm_dir, max_duration)
    soundfile.write(str(root / "clips" / f"{block['utt_id']}.flac"),
                    audio, SAMPLE_RATE, format="FLAC", subtype="PCM_16")
    return block["utt_id"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).parent,
                        help="dataset directory (default: alongside this script)")
    parser.add_argument("--ytdlp", default="yt-dlp",
                        help="yt-dlp executable")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-duration", type=float, default=30.0)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if soundfile is None:
        print("pip install numpy soundfile", file=sys.stderr)
        return 1

    root: Path = args.root
    blocks = json.loads((root / "plan.json").read_text(encoding="utf-8"))["blocks"]
    recipes: dict[str, dict] = {}
    augment_path = root / "augment.jsonl"
    if augment_path.exists():
        for line in augment_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                recipes[entry.pop("utt_id")] = entry

    bgm_dir = root / "bgm"
    if not args.skip_download:
        talks = sorted({block["video_id"] for block in blocks})
        print(f"downloading {len(talks)} talks -> source/")
        download_all(talks, root / "source", "wav", args, "talks")
        # The track ids in augment.jsonl are YouTube video ids, so the music
        # to fetch is exactly what the log names -- there is no separate URL
        # list that can drift out of sync with it.
        wanted = sorted({entry["bgm"]["track"] for entry in recipes.values()
                         if "bgm" in entry})
        if wanted:
            print(f"downloading {len(wanted)} music tracks -> bgm/")
            download_all(wanted, bgm_dir, "flac", args, "music")

    (root / "clips").mkdir(exist_ok=True)
    print(f"cutting {len(blocks)} segments -> clips/")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(
            lambda block: build_clip(block, recipes.get(block["utt_id"]), root,
                                     bgm_dir, args.max_duration),
            blocks))

    missing = [block for block, made in zip(blocks, results) if made is None]
    print(f"built {len(blocks) - len(missing)}/{len(blocks)} segments")
    if missing:
        lost = sorted({block["video_id"] for block in missing})
        print(f"{len(missing)} segments from {len(lost)} unavailable talks "
              f"were skipped:")
        print("  " + " ".join(lost))
        print("Filter manifest.jsonl to the segments that exist before scoring, "
              "and say so when reporting numbers -- the set is no longer the "
              "published one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
