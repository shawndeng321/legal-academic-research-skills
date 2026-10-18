# 音频素材摄入（语音备忘录/录音）— 多模态扩展

> **来源**：multimodal-wiki v1.0.0（kigner/multimodal-wiki）`references/audio-ingest.md`，2026-08 融合。
> 法学库用法：庭审录音、访谈录音、语音备忘等音频素材按此流程摄入。
> 关键约束：转录必须逐字（verbatim），不做摘要；raw/ 不可变。

音频文件——语音备忘录、访谈、录音——是**一等来源**，与 PDF、截图同等对待：原件不可变地存档在 `raw/transcripts/`，逐字稿文本存在它旁边。

## 宿主能力检查

不同宿主（Hermes、Claude Code、Codex、DeepSeek Harness 等）的转录工具、Python 环境和模型配置并不相同，不能假定 `transcribe_audio` 或 `faster-whisper` 已安装。摄入前先确认当前宿主实际暴露的音频转录能力：

- 某些 Hermes 部署可能提供 `tools.transcription_tools.transcribe_audio`；只有导入检查成功后才能使用。
- Claude Code、Codex 或其他宿主可使用当前已提供的转录工具，或在用户授权安装依赖后运行 `faster-whisper`。
- DeepSeek Harness 没有内置转录工具；需要转录时经用户授权在工作区 venv 安装 `faster-whisper`／`ctranslate2`，或由用户提供现成逐字稿；沙盒默认只能写会话工作区，模型缓存与输出目录要放在可写位置。
- 如果没有可用转录能力，保留原始音频并标记“待转录”，不要伪造逐字稿或声称摄入完成。

## 引擎与配置

- 选择 `faster-whisper` 时，需要实际安装 `faster-whisper` 与 `ctranslate2`。
- 模型与语言来自配置 `stt.local`（如 `model: large-v3`、`language: zh`）。`base` 快但弱——中文用 `large-v3`（最佳）或 `medium`。
- 解码用 PyAV，`mp3`/`m4a`/`wav`/`ogg`/`flac` 均可，**不需要单独安装 ffmpeg**。
- 首次运行会从 HuggingFace 下载模型到 `~/.cache/huggingface/hub`（一次性；large-v3 约 3 GB），第一次转录可能长时间无输出，属正常。

## 流程

### 1. 归档原件

把源音频存为 `raw/transcripts/<主题>.<扩展名>`（描述性命名，小写连字符）。**把 `audio.wav`、`recording.m4a` 这类泛名改成与逐字稿相同的描述性 `<主题>`，让音频与 `.md` 逐字稿共享同一基名**——如 `某案访谈-voice-memo.wav` 配 `某案访谈-voice-memo.md`。这样“没有同名 `.md` = 未摄入”的发现机制（深检脚本检查 2）才可靠：泛名音频配另起名的逐字稿会被误报为未转录。归档后即不可变的 Layer-1 来源——**内容**永不修改（归档时改名可以，编辑音频不行）。

### 2. 用宿主可用的能力转录

Hermes 部署暴露 `transcribe_audio()` 时（按已配置的 provider/model/language）：

```python
import os
from tools.transcription_tools import transcribe_audio
# WIKI_PATH = 你的 wiki 根目录（环境变量），如 Windows 的 D:\wiki 或 macOS/Linux 的 ~/wiki
audio = os.path.join(os.environ["WIKI_PATH"], "raw", "transcripts", "<主题>.m4a")
r = transcribe_audio(audio)
assert r["success"], r.get("error")
text = r["transcript"]
```

该函数不可用、或网关拒绝长文件时，使用显式安装的 `faster-whisper` 运行环境：

```python
from faster_whisper import WhisperModel
m = WhisperModel("large-v3", device="auto", compute_type="auto")  # 显存不足时 auto 会回退 CPU int8
segments, info = m.transcribe(audio, language="zh", beam_size=5)  # audio 同上
text = " ".join(s.text.strip() for s in segments)
# info.language、info.duration 可供 frontmatter 使用
```

显存紧张（如 8 GB 卡已占用）时 `device="auto"` 会回退 CPU（慢但可用）。超长音频分段转录后拼接。

### 3. 逐字稿存在原件旁边

写 `raw/transcripts/<主题>.md`：

```yaml
---
source: raw/transcripts/<主题>.m4a           # 转录自哪个音频
source_url: ''                                # 若来自网络则填写
ingested: YYYY-MM-DD
text_sha256: <逐字稿正文的十六进制摘要——口径见 multimodal-pdf-extraction.md 第 0 节>
transcribed_by: whisper (<模型>, faster-whisper, local)   # 溯源
language: zh                                  # info.language
duration_sec: <info.duration>
confidence: medium                            # ASR 会误读人名与术语，见下
---

<原始 ASR 输出，逐字——不加摘要、不加标题、不加额外元数据>
```

- **只放逐字内容。** 正文是原始 ASR 输出逐字照录——模型听到什么就是什么。**不要**概括、重排、加标题/章节、修术语，或追加说话人没说过的元数据（URL、论文题名、作者列表、章节号）。摘要／润色／结构化／补充属于 **Layer-2 页面，绝不放这份 raw 笔记**——raw 层保持忠实、可 diff 的记录，之后才能发现 ASR 误读。
- **`text_sha256` 必须真实**——按正文计算（口径与 `multimodal-pdf-extraction.md` 第 0 节一致：CRLF/CR 归一为 LF、去掉全部前导换行；旧字段 `sha256:` 仍被复核接受，标记 legacy_ok）。绝不编造。
- `.md` 是后续编织的工作副本；音频文件是证据。
- 不涉及 `raw/assets/`——音频不从页面嵌入展示。

### 4. 编织进 Layer 2（常规摄入步骤 ③④⑤⑥）

检查已有页面，新建/更新实体页与概念页，交叉链接（≥2 个 `[[wikilinks]]`），更新 `index.md` + `log.md`。

- 页面 frontmatter 引用来源：`sources: [raw/transcripts/<主题>.md]`。
- 综合论断加溯源标记：`^[raw/transcripts/<主题>.md]`（格式见 `law-paper-writing` 技能的 `references/multimodal-citation-format.md`——raw 笔记路径是可追溯锚点）。

## 发现未摄入音频（文件夹投递情形）

音频是二进制，带不了 frontmatter。未摄入的信号是：

> **`raw/transcripts/` 下有音频文件但没有同名基名的 `.md`。**

列出 `raw/transcripts/*.{mp3,m4a,wav,ogg,flac}`，逐个核对同名 `.md`；没有的就是投递了但尚未摄入 → 对它补跑第 2—4 步。

## 准确性注意

ASR（尤其 `base` 模型、中文语料）会误读人名、专业术语、数字与缩写。单一逐字稿建的页面标 `confidence: medium`，**可疑术语先标记**、不直接下断言，优先 `large-v3`／`medium`。原始备忘是用户自己的话——关键主张保留逐字引用，便于用户识别误听。

## Windows 路径

在当前宿主的文件与代码执行工具里使用原生路径（`<WIKI_PATH>\raw\transcripts\…`），不要用 bash 风格的 `/d/…`。
