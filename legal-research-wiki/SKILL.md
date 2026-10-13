---
name: legal-research-wiki
description: "Use when building or querying a Chinese legal wiki. 法学研究Wiki建库（Obsidian/Markdown）：摄入论文PDF/案例汇编/法律法规与司法解释/初稿/图片音频、研究设计、论文—案例—法规范关联、知识库查询. For auditing an existing wiki use legal-wiki-audit-repair."
license: MIT
metadata:
  version: "2610.9.0"
---

# 法学研究 Wiki 建库

## 技能包更新预检

每次加载本技能时，先运行 `python3 -X utf8 scripts/legal_skills_update.py check --json`（Windows 用 `py -X utf8 …` 或 `python -X utf8 …`）。脚本按 **6 小时**缓存；只有返回 `update_available` 时才向用户展示 `[立即更新] [查看更新说明] [稍后提醒] [忽略此版本]`，其他状态（离线、沙箱拒绝联网或状态目录不可写）不打断当前任务。没有用户的明确确认，绝不运行 `apply`；“查看更新说明”只读版本、变更与本地差异，不执行写入。

**Claude Code 插件安装时跳过预检**：宿主给出的基础目录路径含 `/plugins/cache/`（或位于 `.claude/plugins/` 下）时，更新由 Claude Code 负责，不运行预检命令；用户问起更新时，请其运行 `claude plugin marketplace update legal-academic-research` 与 `claude plugin update legal-academic-research@legal-academic-research`，再在会话中运行 `/reload-plugins`。若预检结果的 `update_channel` 为 `claude-plugin`，同样不运行 `apply`，只按上述方式提示。

## 运行环境（Hermes / Claude Code / Codex 通用）

- 本技能是标准 `SKILL.md` 技能目录；正文中的 `references/`、`assets/`、`scripts/` 相对路径以本技能目录为基准；宿主给出的基础目录就是本目录。
- 读写文件、运行命令、委派子任务均用当前宿主自带工具，不绑定宿主工具名；宿主没有子代理时按小批次串行。
- Python 3.9+：macOS/Linux 用 `python3`（macOS 默认没有 `python` 命令）；Windows 用 `py`，没有时用 `python`。临时文件放系统临时目录（`tempfile`／`$TMPDIR`／`%TEMP%`），不写死 `/tmp`。
- 宿主沙箱拒绝联网或写入时先向用户说明所需权限；更新预检失败直接跳过。

## 适用范围

为任何法学领域的学术研究建立和维护来源可追溯的 Markdown/Obsidian 研究库（LLM Wiki）：学术论文、裁判文书与案例汇编、法律法规与司法文件、用户初稿，以及图片、扫描件、音频等多模态材料；适合群案研究、类型化研究与期刊论文写作前的资料准备。

- 写论文、改稿、期刊适配 → `law-paper-writing`；
- 已有库体检、审计、批量修复 → `legal-wiki-audit-repair`；
- 只问单个法律问题、不涉及建库时，不使用本技能。

## 配套技能

本技能与 `law-paper-writing`、`legal-wiki-audit-repair` 同属一个技能包，可以单独安装使用。三个技能不一定在同一目录（例如 Hermes 可能把它们分放在不同分类子目录下），引用其他技能的文件时按**技能名**找到该技能再读取，不要假设相对路径。配套技能没有安装时，按下表“未安装时”一列处理，不要假装读取了不存在的文件；需要完整能力时，提示用户安装整个技能包。

| 用到的内容 | 所在技能 | 未安装时 |
|---|---|---|
| 写论文的五问（`references/requirement-decomposition.md`） | `law-paper-writing` | 建库访谈的 A、B 两组已覆盖研究问题所需内容，直接按访谈提问 |
| 逐条溯源的回答格式（`references/multimodal-citation-format.md`） | `law-paper-writing` | 每项事实主张后注明库内页面与原始文件路径，不写无出处的断言 |
| 实证与群案材料在论文中的表述限制（`references/empirical-case-research.md`） | `law-paper-writing` | 比例一律限定为“样本内”，不把样本分布写成趋势 |
| 批量同步、缺漏扫描、规范依据插入等脚本；幽灵文件清理；每日检修 | `legal-wiki-audit-repair` | 按本技能 `references/linking-and-cross-references.md` 的手工流程小批执行，先备份 |

## 任务入口（先判定入口，再按需加载参考文档）

先判定本次任务属于哪一类；参考文档按入口与材料类型路由读取（下表与“按材料类型摄入”表），不必每次加载全部经验规则：

| 入口 | 触发 | 做法 | 先读 |
|---|---|---|---|
| 1 新建 | 要建新研究库 | 复用用户已提供的信息，只追问影响库设计的缺项；少量试点后将设计书交用户确认 | [wiki-design-interview.md](references/wiki-design-interview.md)、模板 `assets/templates/wiki-design-brief.md` |
| 2 增量摄入 | 已有库追加材料 | 读已有 SCHEMA 与设计书，盘点差量，按材料类型摄入；**不重启整套访谈、不重新设计** | “按材料类型摄入”表的对应参考文件 |
| 3 查询 | 提问题、要出处 | 检索库内页面与原始材料，给出处和缺口；**不顺带建页、改库或写日志** | [linking-and-cross-references.md](references/linking-and-cross-references.md) |
| 4 加深 | 围绕一个争点补材料与关联 | 先只读了解现状，再问痛点、新维度与试点范围（访谈“加深模式”）；明确试点范围，验收后扩展 | [content-completeness.md](references/content-completeness.md)、[linking-and-cross-references.md](references/linking-and-cross-references.md) |
| 5 审计/修复 | 已有库体检、批量修复 | 转交 `legal-wiki-audit-repair` 技能，并传递范围、基线与写入授权；默认只读，修复先备份、小批推进 | 审计技能的 `SKILL.md` |

用户已经说明目的、材料和范围时，直接进入执行，不重复提问；只在范围有缺口时补问对应的问题。

## 核心纪律

1. **范围先于速度**：拿到装满材料的目录，先盘点（列目录、计数、分组、识别重复）→ 展示一两份代表材料的要点 → 问清范围 → 分主题分批处理；用户说“全部摄入”也分批进行、每批汇报。
2. **材料边界（闭世界查询）**：查询与写作调证据**只用库内页面及其 `raw/` 原始材料**回答，模型记忆不是来源；库内没有的如实说明并标 `[来源不明]`，给出摄入方案；**空壳或占位页面不算覆盖**，未摄入样本不能支撑统计结论；联网检索属**摄入环节**（经授权），新获取材料先入 `raw/` 并登记再进入页面；来源性主张（法条、案号、文献页码、数据）必须能回溯到库内页面和原始材料，回答时标出处（逐条溯源用 `law-paper-writing` 的 note-level 格式）。
3. **一个项目一个 vault**：不同项目独立 vault，不混扫不混改；不因发现旧路径就恢复或迁移旧库；跨项目方法论放 `methodology/` 或技能中，不共享实体页。
4. **先问清楚要建什么样的库，由用户主导**：新建或加深前做**建库访谈**（[wiki-design-interview.md](references/wiki-design-interview.md)）：一次 1—3 个问题并附选项；必问目的、研究问题与分析框架、“将来会怎么用这个库”三组；整理成《Wiki 设计书》（`assets/templates/wiki-design-brief.md`），确认后再定 SCHEMA、目录与模板。已有库走“加深模式”：先只读了解现状，再问痛点、新维度与试点范围。论文五问见 `law-paper-writing` 的 `references/requirement-decomposition.md`，答案写入 `research-design/` 后再摄入；用户已有框架以其为准；暂无思路时允许先建库、模块完成时归纳建议。**不把其他项目的框架、分类、标签套到新项目上。**
5. **来源与分析分开，宁缺毋滥**：事实、日期、案号、条文、裁判理由只能来自原始材料；研究分析另写并可追溯；证据不足写“暂不形成结论”或待核，不用模板或推测填满。
## 新建研究库的推荐顺序（入口 1 详细流程）

1. **确认 vault 路径与项目边界**；
2. **建库访谈与研究设计**：按 [wiki-design-interview.md](references/wiki-design-interview.md) 提问 → 写《Wiki 设计书》并确认 → 写 `research-design/` 研究设计页（见 [research-design-pages.md](references/research-design-pages.md)）；
3. **SCHEMA、index、log**：从 [assets/templates/](assets/templates/README.md) 复制，与用户确定目录、页面类型、标签词表（中文标签）与必填字段；
4. （可选）**期刊风格观察**：用户有目标期刊时，摄入 2—3 篇该刊范文到 `entities/范文/`，在 `methodology/` 写风格观察卡（只作写作参考）；
5. **首批材料（按研究类型定顺序）**：论文导向与群案研究一般先摄入论文（建立概念骨架），再案例、再法规范；纯案例实证型可从案例先行，概念页由案例归纳；规范解释型从法规范先行；文献争议型从论文与争议文献先行；
6. **案例**：挂到已有概念上；**7. 法规范**：按效力层级摄入相关条文；**8. 比较层与网络**：`comparisons/`、论文—案例—法规范互联；**9. 之后进入写作**（交给 `law-paper-writing`）。

用户问“先摄入论文还是案例”时，按研究类型给建议：论文导向与群案研究**推荐先论文**（论文搭概念骨架，案例才有可挂接的概念页，也揭示标签维度、避免返工）；其余按上条第 5 步。这是推荐顺序，不是固定规则。

## 目录与页面类型

完整目录骨架（`SCHEMA.md`／`index.md`／`log.md`、`raw/`、`entities/`、`concepts/`、`comparisons/`、`queries/`、`research-design/`、`methodology/`、`drafts/`、`.maintenance/`）与页面类型说明见 [directory-layout-and-page-types.md](references/directory-layout-and-page-types.md)。要点：实体目录超过约 30 个文件时按类型分子目录；调整结构后全库死链为零，并同步 `index.md` 与 SCHEMA；`legal-wiki-audit-repair` 的脚本默认使用 `entities/引用文献`、`entities/案例`、`entities/法规范` 三个目录名；标签使用中文并在 SCHEMA 中维护词表（主题、要件、程序、来源、结果、研究用途）。

## 按材料类型摄入

| 材料 | 目标页面 | 参考 |
|---|---|---|
| 学术论文 PDF | `entities/引用文献/` ＋ 概念页更新 | pdf-paper-ingestion；`batch_extract_papers.py`／`clean_pdf_artifacts.py` |
| 案例、裁判文书、案例汇编 | `entities/案例/` | case-ingestion、docx-* 系列 |
| 法律法规、司法解释、批复答复、会议纪要、审判答疑 | `entities/法规范/` | legal-norm-hierarchy-and-reply-ingestion；norm-versioning |
| 用户初稿与思路文件 | `drafts/` | case-ingestion 第八节；docx-footnote-extraction；draft-version-sync |
| 图片、截图、扫描件 | `raw/screenshots/` ＋ 提取文件 | multimodal-image-ingest |
| 音频、访谈、录音 | `raw/transcripts/` ＋ 逐字稿 | multimodal-audio-ingest |
| 批量下载参考文献 | stub → 补全 | multimodal-bulk-refs |
| 云端同步 vault | — | multimodal-obsidian-headless |

以上文件的完整路径（含 `references/` 前缀）与选择理由见 [material-routing.md](references/material-routing.md)。通用要求：**汇编中每一项单独建页**（`index.md` 列出每一个页面，只有分组标题不够）；**重复文件**用哈希比对后报告给用户，不静默过滤；**旧版 `.doc`** 先转换为文本（macOS `textutil`，其他系统 LibreOffice），原件入 `raw/`；**DOCX 的脚注**不在 `paragraphs` 里，需读取 `word/footnotes.xml`，转换论文或初稿后确认脚注已提取。

## 页面内容标准

每个页面都要有实质内容，不允许空壳或占位文字（判定见 [content-completeness.md](references/content-completeness.md)）；模板结构见 [assets/templates/](assets/templates/README.md)，复制后按项目调整并同步 SCHEMA。四类页面的必备结构：

- **论文页**：书目信息、摘要、关键词、核心论点、方法、结论、引用规范／引用案例、与底稿及其他论文的关联；
- **案例页**：基本信息、案情、程序与结果、争点、裁判理由与要旨、裁判依据、研究定位、关联页；事实与分析分开；
- **概念页**：定义、当前认识、代表文献与代表案例（正例必列；反例与边界例逐一检查，暂未找到时写明检索范围与结论限制，不硬凑）、争议与反方、规范依据、相关页；
- **比较页**（群案研究价值最集中一层）：纳入标准 → 案例表 → 相同点 → 差异点 → **反例与边界**（必须检查）→ **可支持的论文主张**（用户最先看）→ 关联比较页；正文用 `[[案例文件名|简称]]`、表格用 `[[案例文件名\|简称]]`。

## 链接网络

规则、死链预防、底稿锚点、论文—案例双轨与法规范三角互联见 [linking-and-cross-references.md](references/linking-and-cross-references.md)。要点：只给已有页面或重要概念加链接，每批死链为零；每条关系说得出理由（呼应、补充、分歧、规范依据、证明结构、程序阶段、时间演变），不机械加链接；论文—案例按“引用轨 + 主旨轨”，无实质对应不硬加，镜像带印证说明；表格别名用 `\|`，维护文档示例写纯文本。

## 知识库与论文写作双轨隔离

知识库管知识库的更新，论文管论文的写作，两条轨道隔离，防止互相污染：论文写作期间知识库只做纯素材补充、不做批量结构调整（页面迁移、重新分类、字段变更冻结）；定稿后把写作期间记下的缺口一次性回填；不按论点重新分类（在论点—证据—引注矩阵里填对应，不动目录）；交接页是主存档。完整规则（写入方向单向、三阶段、反馈收集、交接页）见 [dual-track-isolation.md](references/dual-track-isolation.md)。

## 研究设计层

`research-design/` 随项目演进：设计页、论点—证据—引注矩阵、样本与口径清单、门禁状态表；`concepts/` 可建学术史争议地图。统计“可执行”≠“已计算”：数据落地前假说待验证、写作中不出现数字。见 [research-design-pages.md](references/research-design-pages.md)、[statistics-landing-and-case-matching.md](references/statistics-landing-and-case-matching.md)。

## 每批摄入后的一次性验收

摄入、清洗、链接全部完成后，一次运行全部检查并提交一份报告；不要修完一个维度就宣布完成：

1. **内容**：无空壳、无占位文字；缺口（待核验／未发现材料）与空壳分开记录；
2. **论文质量**：摘要与结论对照原文核验真实完整（长度与链接数只作筛查信号）；无 PDF 残留、关键词干净；YAML 以真实解析结果核验（见 [pdf-paper-ingestion.md](references/pdf-paper-ingestion.md)）；
3. **死链**：全库递归扫描为零（`python3 scripts/check_wikilinks.py <vault> --strict`）；畸形链接、空目标、缺失附件、路径前缀不符、锚点缺失与同名歧义同为零，示例和历史引用单列；
4. **交叉引用**：实体页之间有带理由的链接，锚点页连到相关页面；
5. **YAML 与 index**：全库可解析，每个正式页面都在 `index.md` 中；
6. **研究设计同步**：材料状态、门禁、口径与现状一致。

以模块为单位推进（一个文件夹通常是一个模块）：摄入 → 关联 → MODULE-END CHECK → 下一模块。检查项见 [case-ingestion.md](references/case-ingestion.md) 第七节。子代理报告的“完成”不是证据，按文件核验内容。
## 审计与修复

已有的研究库要体检、审计或批量修复时，转交 `legal-wiki-audit-repair` 技能：文献库逐篇审计与分批修复、深度修复的分批推进、全库结构与学术可用性审计、模板化检测、图谱形态、整改台账、P0—P3 分级、批量重命名与链接迁移、每日检修，细则随该技能安装（其 `references/` 下同名参考文件）。传递时带上范围、基线与写入授权；按**技能名**找到该技能再读取，不假设相对路径。

审计默认只读；用户授权修复后，默认每批 5—8 页，超过 10 页先列清单确认；先备份、先试运行，再写入。

## 协作、报告与多模型

**多模型与子代理**：批量提取、格式修复、死链检查等明确任务用单一模型；研究规划、疑难章节、实质审计、期刊适配等关口才需多方意见。每个产物只有一个主写者；子代理不共享上下文，交接依靠落盘文件（见 [model-orchestrated-legal-research-workflow.md](references/model-orchestrated-legal-research-workflow.md)）。

**向用户报告**：行动优先、简短——本批规模、具体页面、每页一项改动、关键验收数字、下一批（尚未开始）。用户批准前问“要不要改、有什么好处、怎么做”时，用几句平实的话加至多一张小表回答。规则层面的改进（如新的检查项）先登记为候选，经用户确认后再写入 SCHEMA 或方法论。

## 易错点

批量摄入、审计或修复前，先读 [pitfalls-and-lessons.md](references/pitfalls-and-lessons.md)。最常踩的：递归扫描到 vault 根目录；改 frontmatter 后重新解析 YAML 并看 diff；批量改动先备份、先试运行、写后逐页复核；文件名以磁盘为准（含中文全角标点）；汇编解析时区分分隔线与副标题破折号；追加日志前读真实末尾，子代理不各自写日志。
