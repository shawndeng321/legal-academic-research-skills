# 音频素材摄入（语音备忘录/录音）— 多模态扩展

> **来源**：multimodal-wiki v1.0.0（kigner/multimodal-wiki）`references/audio-ingest.md`，2026-08 融合。
> 法学库用法：庭审录音、访谈录音、语音备忘等音频素材按此流程摄入。
> 关键约束：转录必须逐字（verbatim），不做摘要；raw/ 不可变。

# Audio Source Ingestion (voice memos, recordings)

An audio file — a voice memo, an interview, a recorded thought — is a **first-class
source**. It gets the same treatment as a PDF or screenshot: the original is archived
immutably in `raw/transcripts/` and a text transcript is saved beside it. This doc
defines that flow.

## 宿主能力检查

不同宿主（Hermes、Claude Code、Codex 等）的转录工具、Python 环境和模型配置并不相同，不能假定 `transcribe_audio` 或 `faster-whisper` 已安装。摄入前先确认当前宿主实际暴露的音频转录能力：

- 某些 Hermes 部署可能提供 `tools.transcription_tools.transcribe_audio`；只有导入检查成功后才能使用。
- Claude Code、Codex 或其他宿主可使用当前已提供的转录工具，或在用户授权安装依赖后运行 `faster-whisper`。
- 如果没有可用转录能力，保留原始音频并标记“待转录”，不要伪造逐字稿或声称摄入完成。

## Engine options
- 选择 `faster-whisper` 时，需要实际安装 `faster-whisper` 与 `ctranslate2`。
- Model + language come from config `stt.local` (e.g. `model: large-v3`, `language: zh`).
  `base` is fast but weak — for Chinese use `large-v3` (best) or `medium`.
- Decoding uses PyAV, so `mp3`/`m4a`/`wav`/`ogg`/`flac` work with **no separate ffmpeg**.
- First run downloads the model from HuggingFace to `~/.cache/huggingface/hub` (one-time,
  ~3 GB for large-v3). Expect a stall on the first transcription.

## Steps

### 1. Archive the original
Save the source audio to `raw/transcripts/<topic>.<ext>` (descriptive, lowercase-hyphen).
**Rename a generic source name (e.g. `audio.wav`, `recording.m4a`) to the descriptive
`<topic>` you'll use for the transcript, so the audio and its `.md` transcript share the
SAME basename** — e.g. `id2reflectance-voice-memo.wav` + `id2reflectance-voice-memo.md`.
This keeps the "no sibling `.md` = uningested" discovery (Check 2 of `scripts/multimodal_audit.py`)
reliable: a generic `audio.wav` sitting next to a differently-named transcript false-flags
as untranscribed.
Once archived under its final name, this is the immutable Layer-1 source — never modify its
**content** (renaming at archive time is fine; editing the audio is not).

### 2. Transcribe with an available host capability

If the host is a Hermes deployment that exposes `transcribe_audio()`, it can honor the configured provider/model/language:

```python
import os
from tools.transcription_tools import transcribe_audio
# WIKI_PATH = your wiki root (environment variable), e.g. D:\wiki on Windows or ~/wiki on macOS/Linux
audio = os.path.join(os.environ["WIKI_PATH"], "raw", "transcripts", "<topic>.m4a")
r = transcribe_audio(audio)
assert r["success"], r.get("error")
text = r["transcript"]
```

If that function is unavailable, or the configured gateway rejects a long file, use an explicitly installed `faster-whisper` runtime:

```python
from faster_whisper import WhisperModel
m = WhisperModel("large-v3", device="auto", compute_type="auto")  # auto→CPU int8 if VRAM is full
segments, info = m.transcribe(audio, language="zh", beam_size=5)  # `audio` from the snippet above
text = " ".join(s.text.strip() for s in segments)
# info.language, info.duration are available for the frontmatter
```

If VRAM is tight (e.g. an 8 GB card already loaded), `device="auto"` falls back to CPU
(slower but works). For very long audio, transcribe in chunks and concatenate.

### 3. Save the transcript beside the original
Write `raw/transcripts/<topic>.md`:

```yaml
---
source: raw/transcripts/<topic>.m4a           # the audio this was transcribed from
source_url: ''                                # if it came from somewhere online
ingested: YYYY-MM-DD
text_sha256: <hex digest of the transcript body — 口径见 multimodal-pdf-extraction.md 第 0 节>
transcribed_by: whisper (<model>, faster-whisper, local)   # provenance
language: zh                                  # info.language
duration_sec: <info.duration>
confidence: medium                            # ASR misreads names/terms — see caveat
---

<raw ASR output, word-for-word — no summary, no headings, no added metadata>
```

- **Verbatim ONLY.** The body is the raw ASR output word-for-word — exactly what the
  model heard. Do NOT summarize, restructure, add headings/sections, fix terms, or append
  metadata (arXiv URLs, paper titles, author lists, section numbers) the speaker didn't
  say. Summary / polish / structuring / enrichment belongs in **Layer-2 pages, NEVER in
  this raw note** — keep the raw layer a faithful, diffable record so ASR misreads can be
  caught later. (`source_url`/`title` may go in frontmatter; the body stays verbatim.)
- **`text_sha256` must be REAL** — computed over the transcript body（口径与 `multimodal-pdf-extraction.md` 第 0 节一致：CRLF/CR→LF、去掉全部前导换行；旧布局 `sha256:` 字段仍被复核接受，标记 legacy_ok）. Never fabricate.
- The `.md` is the working copy for weaving; the audio file is the evidence.
- `raw/assets/` is NOT involved — audio is not embedded for display.

### 4. Weave into Layer 2 (normal Ingest steps ③④⑤⑥)
Check existing pages, create/update entity & concept pages, cross-link (≥2 `[[wikilinks]]`),
update `index.md` + `log.md`.
- Cite the source in page frontmatter: `sources: [raw/transcripts/<topic>.md]`.
- Provenance markers on synthesized claims: `^[raw/transcripts/<topic>.md]` (per
  `law-paper-writing` 技能的 `references/multimodal-citation-format.md` — the raw-note path is the traceable anchor).

## Discovery (folder-drop path)
An audio file is binary and can't carry frontmatter. The uningested signal is:

> **an audio file in `raw/transcripts/` with no sibling `.md` of the same basename.**

List `raw/transcripts/*.{mp3,m4a,wav,ogg,flac}`, check each for a matching `.md`; any
audio file without one was dropped but never ingested → run steps 2–4 on it.

## Accuracy caveat
ASR (especially the `base` model, and on Chinese) misreads names, technical terms,
numbers, and acronyms. Set `confidence: medium` on pages built from a single transcript,
**flag uncertain terms** rather than asserting them, and prefer `large-v3`/`medium` over
`base`. A raw memo is the user's own words — when a claim is critical, keep the verbatim
quote in the transcript so the user can spot a misheard term.

## Windows paths
Use native paths (`<WIKI_PATH>\raw\transcripts\…`, where `<WIKI_PATH>` is your wiki root) in the current host's file and code-execution tools—not bash `/d/…` paths on Windows.
