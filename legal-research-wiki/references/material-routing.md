# 按材料类型摄入：参考文件与脚本（路由细则）

> 由建库技能 SKILL.md 迁出（WIKI-12 瘦身）；SKILL.md 保留材料→目标页面一览，本文载每类材料的参考文件与脚本。

| 材料 | 目标页面 | 读取 |
|---|---|---|
| 学术论文 PDF | `entities/引用文献/` + 概念页更新 | [pdf-paper-ingestion.md](pdf-paper-ingestion.md)；脚本 [batch_extract_papers.py](../scripts/batch_extract_papers.py)、[clean_pdf_artifacts.py](../scripts/clean_pdf_artifacts.py) |
| 本地 PDF 的哈希、双文件保存与复核 | `raw/papers/`（新提取物也可放派生目录） | [multimodal-pdf-extraction.md](multimodal-pdf-extraction.md)（统一哈希口径；批量提取 `--format md`、只读复核 `--verify`） |
| 案例、裁判文书、案例汇编 | `entities/案例/` | [case-ingestion.md](case-ingestion.md)、[docx-case-parsing-lessons.md](docx-case-parsing-lessons.md)、[docx-scope-and-mapping.md](docx-scope-and-mapping.md)、[docx-case-compilation-revalidation.md](docx-case-compilation-revalidation.md) |
| 法律法规、司法解释、批复答复、会议纪要、审判答疑 | `entities/法规范/` | [legal-norm-hierarchy-and-reply-ingestion.md](legal-norm-hierarchy-and-reply-ingestion.md)；需要研究规范在不同时期的版本与历史案件适用时，见 [norm-versioning.md](norm-versioning.md) |
| 用户初稿与思路文件 | `drafts/` | [case-ingestion.md](case-ingestion.md) 第八节；脚注提取 [docx-footnote-extraction.md](docx-footnote-extraction.md)；稿件出新版本时的同步流程 [draft-version-sync.md](draft-version-sync.md) |
| 图片、截图、扫描件 | `raw/screenshots/` + 提取文件 | [multimodal-image-ingest.md](multimodal-image-ingest.md) |
| 音频、访谈、录音 | `raw/transcripts/` + 逐字稿 | [multimodal-audio-ingest.md](multimodal-audio-ingest.md) |
| 批量下载参考文献 | stub → 补全 | [multimodal-bulk-refs.md](multimodal-bulk-refs.md) |
| 云端同步 vault | — | [multimodal-obsidian-headless.md](multimodal-obsidian-headless.md) |

通用要求：**汇编中每一项单独建页**（`index.md` 列出每一个页面，只有分组标题不够）；**重复文件**用哈希比对后报告给用户，不静默过滤；**旧版 `.doc`** 先转换为文本（macOS `textutil`，其他系统 LibreOffice），原件入 `raw/`；**DOCX 的脚注**不在 `paragraphs` 里，需读取 `word/footnotes.xml`，转换论文或初稿后确认脚注已提取。
