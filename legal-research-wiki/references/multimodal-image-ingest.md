# 图片素材摄入（截图/图表/扫描件）— 多模态扩展

> **来源**：multimodal-wiki v1.0.0（kigner/multimodal-wiki）`references/image-ingest.md`，2026-08 融合。
> 法学库用法：裁判文书扫描件、证据图表、网页截图等图片素材按此流程摄入。
> 与法学摄入纪律一致：raw/ 不可变、sha256 漂移检测、note-level 溯源。

单张图片——粘贴进对话的截图、存到 `raw/screenshots/` 的图表、文章里的插图——是**一等来源**，不是被动的 `raw/assets/` 附件；与 PDF 同等对待：原件不可变地存档，文本提取物存在旁边。

## 目录分工（必须分开）

```
raw/screenshots/
    <主题>.png   # 原件图片——不可变的 Layer-1 来源/证据。不直接嵌入、不编辑。
    <主题>.md    # 文本提取物——存在原件旁边（对应 raw/papers/ 的 .pdf + .md）
raw/assets/
    <主题>.png   # 展示副本——仅当 Layer-2 页面用 ![[...]] 嵌入图片时才创建
```

- `raw/screenshots/` 是**来源归档**：原件 PNG + 它的文本提取物，不可变。
- `raw/assets/` 只放确实在页面里**展示**的图片；只有 Layer-2 页面需要展示时才把原件复制过来。
- **不要把来源截图直接丢进 `assets/`**——那会把证据与展示混在一起；原件始终在 `raw/screenshots/`。

## 流程

### 1. 归档原件

把源图片存为 `raw/screenshots/<主题>.png`（描述性、小写连字符）。若图片是粘贴进对话的，先向宿主解析真实本地/导出路径，再以真实文件名复制到 `raw/screenshots/`；之后永不修改。

### 2. 读图

用模型直接打开保存的 PNG（当前模型原生读图）并详尽描述，例如：

> “请极其详尽地描述这张图片：所有文字、标签、数字、模块/方框、箭头及方向、颜色与整体布局。结构化图表按结构转述（逐块列出，并说明各块之间的连接）。”

把返回的完整描述**逐字**保留——这段文字就是提取物。

### 3. 文本提取物存在原件旁边

写 `raw/screenshots/<主题>.md`：

```yaml
---
source: raw/screenshots/<主题>.png          # 提取自哪张原图
source_url: ''                               # 若图片来自网页则填写
ingested: YYYY-MM-DD
text_sha256: <描述正文的十六进制摘要——口径见 multimodal-pdf-extraction.md 第 0 节>
extracted_by: <模型 id>                      # 由哪个模型读取——溯源
confidence: medium                           # 视觉会误读图表，见下
---

![[<主题>.png]]

<完整描述，逐字>
```

- 即使模型之后还能再看图，也要保留提取物：它是图片在 Wiki 中可搜索、可引用、可链接的依据，并记录摄入当时实际读到的内容。
- **`text_sha256` 必须真实**——按第 0 节口径对描述正文计算（CRLF/CR 归一为 LF、去前导换行；旧字段 `sha256:` 仍接受并标 legacy_ok）。不得写占位符（曾见：伪造的 `a1b2c3…` 会让漂移检测静默失效）。
- `.md` 是后续编织的**工作副本**；`.png` 是证据。

### 4. 编织进 Layer 2（常规摄入步骤 ③④⑤⑥）

按标准流程：检查已有页面，新建/更新实体页与概念页，交叉链接（≥2 个 `[[wikilinks]]`），更新 `index.md` + `log.md`。

- 页面 frontmatter 引用：`sources: [raw/screenshots/<主题>.md]`。
- 综合论断加溯源标记 `^[raw/screenshots/<主题>.md]`（见 `law-paper-writing` 技能的 `references/multimodal-citation-format.md`）。
- 要在 Layer-2 页面**展示**图：把 PNG 复制到 `raw/assets/<主题>.png` 并嵌 `![[<主题>.png]]`；`raw/screenshots/` 的原件保持不动。

## 发现未摄入图片（文件夹投递情形）

摄入的发现环节依赖缺失 frontmatter——但 `.png` 是二进制，带不了 frontmatter。图片的未摄入信号是：

> **`raw/screenshots/` 下有 `.png` 但没有同名基名的 `.md`。**

列出 `raw/screenshots/*.png` 逐个核对；没有同名 `.md` 的就是投递了但未摄入 → 补跑第 2—4 步。

## 准确性注意

视觉模型会自信地编造图表细节（层数、具体数字、标签文字）。单一图片建的页面标 `confidence: medium`，**精确数字须标记待人工核验**，不直接当事实断言；诚实的“约”好过编造的具体值。

## 文章中的内嵌图片

`web_extract` 返回的文章带图片链接（`![说明](https://…png)`）时，这些图默认未被读取。**关键**图表值得保留的：下载到 `raw/screenshots/`，跑第 2—3 步，把描述并入该文章的 Wiki 页面。不要留下会腐烂的远程热链。

## Windows 路径

在当前宿主的文件与图像分析工具里使用原生路径（`<WIKI_PATH>\raw\screenshots\…`），不要用 bash 风格的 `/d/…`。
