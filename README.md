# TEDxJP-5K-V

A Japanese ASR evaluation set. 5,000 segments, uniformly distributed from 2 to 30 seconds.

[日本語はこちら](#日本語)

## Overview

Built from Japanese TEDx talks on YouTube. The audio is the talk itself; the reference text is the human-written Japanese caption track published with it.

Changes from the sources:

- Adjacent caption cues are merged so that segment lengths spread uniformly over 2 to 30 seconds.
- Cuts are placed only where the captions leave a pause, with a random margin of 0 to 200 ms at each end to imitate a different voice-activity detector.
- Caption text is normalised: full-width digits and Latin letters to half-width, non-speech markers such as laughter and applause removed, whitespace stripped.

Each segment is a single continuous cut of the original audio, with no splicing or synthesised silence.

A companion set with heavy noise, using the same segmentation and the same references, is at [TEDxJP-5K-N](https://github.com/Columba1198/TEDxJP-5K-N). The difference between scores on the two sets is a measure of robustness. This set is [TEDxJP-5K-V](https://github.com/Columba1198/TEDxJP-5K-V).

## Why this exists

Japanese ASR benchmarks that can be obtained without an application process are scarce, and the ones that exist cover a narrow range.

- Common Voice ja is read speech averaging around four seconds. Long-form behaviour is invisible, and some references do not match their audio.
- TEDxJP-10K has reliable references, but one utterance is one caption cue, so nothing runs longer than about 11 seconds. Its references are close to verbatim: fillers were added by hand and Arabic numerals rewritten as kanji.

## Variety

| Property | Setting |
|---|---|
| Segment length | Uniform over 2 to 30 seconds, in 1-second bins |
| Merging | Adjacent caption cues joined; cuts only at pauses of 0.5 s or longer |
| Edge margin | 0 to 200 ms at each end, drawn independently |
| Speakers | Tuned so that a wide range of talks is represented |

## Statistics

| | |
|---|---|
| Segments | 5,000 |
| Total audio | 22.2 hours |
| Length | 2.0 to 30.0 s, mean 16.0 s |
| Talks | 257 |
| Reference characters | 409,033 |
| Format | FLAC, 16 kHz, mono |

## Notes

- The captions favour readability over verbatim accuracy, so fillers are not transcribed. A system that writes out every hesitation is charged for insertions.
- Numbers are written with half-width Arabic digits.
- Punctuation and symbols are kept in the references. Strip them, along with whitespace, from both reference and hypothesis before computing CER.
- Audio is not distributed. TEDx talks are licensed CC BY-NC-ND 4.0, so this repository ships the segmentation and the references. You can rebuild the dataset by running `rebuild.py`.
- If a talk becomes private or is removed, its segments cannot be rebuilt. `rebuild.py` skips them and lists which ones.
- The source talks are the ones TEDxJP-10K uses, but the segmentation differs, so no clip matches a TEDxJP-10K utterance.

## Layout

```
plan.json             segmentation: source talk, cut range, reference text
manifest.jsonl        NeMo-style manifest, one line per segment
manifest_offset.jsonl same, referencing source/ with an offset
text                  utterance id and reference, Kaldi style
segments utt2spk spk2utt   Kaldi-style metadata
rebuild.py            downloads the talks and regenerates clips/
clips/ source/        produced by rebuild.py, not tracked
```

## Rebuilding

```sh
pip install numpy soundfile "yt-dlp[default]"
python rebuild.py
```

ffmpeg must be on PATH, along with a JavaScript runtime such as Node.js for the YouTube extractor. Keep yt-dlp current: YouTube-side changes break older versions, and a nightly build is occasionally needed before the fix reaches a release.

## Licence

This repository is licensed under Apache-2.0, covering the segmentation, the metadata and the scripts.

The audio produced by `rebuild.py` is not covered. The source talks remain under CC BY-NC-ND 4.0 and belong to their speakers and TEDx organisers.

---

<a name="日本語"></a>

# TEDxJP-5K-V

音声長が2〜30秒に均一分布する、5,000セグメントの日本語ASR評価セット。

## 概要

YouTubeで公開されている、日本語のTEDxトークから作成しました。音声はトーク本体、字幕は各トークに付随する手入力の日本語字幕です。

元データからの変更点:

- 隣接する字幕を連結し、セグメント長を2〜30秒に均一分布させています。
- 切れ目は字幕の間が空いている箇所にのみ置き、VADの違いを模して前後に0〜200msのランダムなマージンを付けています。
- 字幕を正規化しています。全角の数字と英字は半角にし、笑いや拍手などの非発話注記と空白は除去しています。

各セグメントは元音声を1回切り出したもので、継ぎ接ぎや無音の合成はありません。

同じ分割と字幕のまま強いノイズを加えたセットが [TEDxJP-5K-N](https://github.com/Columba1198/TEDxJP-5K-N) にあります。両者のスコア差がロバスト性の指標になります。本セットは [TEDxJP-5K-V](https://github.com/Columba1198/TEDxJP-5K-V) です。

## 作成理由

申請なしで入手できる日本語ASRベンチマークは少なく、既存のものは測れる範囲が限られています。

- Common Voice ja は読み上げ音声で平均4秒程度です。長尺での精度を計測できないうえ、音声と一致しない字幕も含まれます。
- TEDxJP-10K は字幕の質が高い一方、1発話が字幕1キューなので最長でも約11秒です。字幕は逐語寄りで、フィラーが手作業で追加され、アラビア数字が漢数字に書き換えられています。

## 考慮した多様性

| 項目 | 内容 |
|---|---|
| セグメント長 | 2〜30秒を1秒刻みのビンで均一分布 |
| 連結 | 隣接する字幕を連結。切れ目は0.5秒以上の間がある箇所のみ |
| 端のマージン | 前後に0〜200msを独立に付与 |
| 話者 | 多様なトークを含むよう、1トークあたりの本数を調整 |

## 統計

| | |
|---|---|
| セグメント数 | 5,000 |
| 合計 | 22.2 時間 |
| 音声長 | 2.0〜30.0 秒、平均 16.0 秒 |
| トーク数 | 257 |
| 字幕文字数 | 409,033 |
| 形式 | FLAC、16 kHz、モノラル |

## 注意事項

- 字幕は逐語記録ではなく読みやすさを優先しており、フィラーは書かれていません。言い淀みまで書き起こすシステムは挿入誤りとして減点されます。
- 数字は半角アラビア数字です。
- 字幕には句読点と記号が残っています。CERの計算前に、空白とあわせて字幕とモデル出力の両方から除去してください。
- 音声は同梱していません。TEDxトークは CC BY-NC-ND 4.0 ライセンスのため、本リポジトリには分割情報と字幕のみを収録しています。`rebuild.py` を実行することで、データセットを再構築できます。
- 動画が非公開化または削除されると、そのセグメントは再構築できません。`rebuild.py` は該当分をスキップして一覧を表示します。
- 元動画は TEDxJP-10K と共通ですが、分割点が異なるため、クリップが一致することはありません。

## ディレクトリ構成

```
plan.json             分割情報（元トーク・切り出し範囲・字幕）
manifest.jsonl        NeMo形式マニフェスト。1行1セグメント
manifest_offset.jsonl 同上。source/ をオフセット字幕する版
text                  発話IDと字幕（Kaldi形式）
segments utt2spk spk2utt   Kaldi形式メタデータ
rebuild.py            元トークを取得し clips/ を生成
clips/ source/        rebuild.py が生成（追跡対象外）
```

## 再構築

```sh
pip install numpy soundfile "yt-dlp[default]"
python rebuild.py
```

ffmpegがPATH上に必要です。YouTubeからのダウンロードには、Node.jsなどのJavaScriptランタイムも要ります。yt-dlpは最新版を使ってください。YouTube側の変更で古いバージョンはダウンロードに失敗することがあり、修正が正式リリースに入るまではnightlyビルドが必要な場合もあります。

## ライセンス

本リポジトリは Apache-2.0 です。分割情報・メタデータ・スクリプトが対象になります。

`rebuild.py` が生成する音声は対象外です。元トークは CC BY-NC-ND 4.0 のままで、権利は各講演者およびTEDx主催者に帰属します。
