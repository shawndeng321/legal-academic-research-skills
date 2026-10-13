---
name: legal-research-wiki
description: "Use when building or querying a Chinese legal wiki. 法学研究Wiki建库（Obsidian/Markdown）：摄入论文PDF/案例汇编/法律法规与司法解释/初稿/图片音频、研究设计、论文—案例—法规范关联、知识库查询. For auditing an existing wiki use legal-wiki-audit-repair."
license: MIT
metadata:
  version: "2610.9.0"
---

# 法学研究 Wiki 建库

## 技能包更新预检

每次加载本技能时，先运行 `python3 -X utf8 scripts/legal_skills_update.py check --json`（Windows 用 `py -X utf8 …` 或 `python -X utf8 …`）。脚本按 **6 小时**缓存自动检查结果；只有返回 `update_available` 时才向用户展示 `[立即更新] [查看更新说明] [稍后提醒] [忽略此版本]`，其他状态（含离线、沙箱拒绝联网或状态目录不可写）不打断当前任务并继续执行。没有用户的明确确认，绝不运行 `apply`；“查看更新说明”只读取版本、变更与本地差异，不执行写入。

**Claude Code 插件安装时跳过预检**：宿主给出的本技能基础目录路径含 `/plugins/cache/`（或位于 `.claude/plugins/` 下）时，本技能由 Claude Code 插件安装，更新由 Claude Code 负责，不运行上面的预检命令，直接执行当前任务。用户问起更新时，请其运行 `claude plugin marketplace update legal-academic-research` 与 `claude plugin update legal-academic-research@legal-academic-research`，再在会话中运行 `/reload-plugins`。若已运行预检且结果的 `update_channel` 为 `claude-plugin`，同样不运行 `apply`，只按上述方式提示。

## 运行环境（Hermes / Claude Code / Codex 通用）

- 本技能是标准 `SKILL.md` 技能目录。正文中的 `references/`、`assets/`、`scripts/` 等相对路径一律以本技能目录为基准解析；宿主加载技能时给出的基础目录就是本目录。
- 读写文件、运行命令、委派子任务均使用当前宿主自带的工具；本文不绑定任何宿主的工具名。宿主不支持子代理时，按小批次串行执行同样的步骤。
- Python 命令按系统选择：macOS/Linux 用 `python3`（macOS 默认没有 `python` 命令）；Windows 用 `py`，没有时用 `python`。本文及参考文件中写作 `python3` 的命令，在 Windows 上照此替换。所需版本为 Python 3.9 及以上。临时文件放在系统临时目录（Python `tempfile`、`$TMPDIR` 或 `%TEMP%`），不要写死 `/tmp`。
- 宿主沙箱拒绝联网或写入时，先向用户说明需要的权限；更新预检失败直接跳过。

## 适用范围

为任何法学领域的学术研究建立和维护来源可追溯的 Markdown/Obsidian 研究库（LLM Wiki）：学术论文、裁判文书与案例汇编、法律法规与司法文件、用户自己的初稿，以及图片、扫描件、音频等多模态材料。尤其适合群案研究、类型化研究和期刊论文写作前的资料准备。

- 写论文、改稿、期刊适配 → `law-paper-writing`；
- 体检、审计、批量修复已有研究库 → `legal-wiki-audit-repair`；
- 只问一个法律问题、不涉及建库时，不使用本技能。

## 配套技能

本技能与 `law-paper-writing`、`legal-research-wiki`、`legal-wiki-audit-repair` 同属一个技能包，可以单独安装使用。三个技能不一定在同一目录（例如 Hermes 可能把它们分放在不同分类子目录下），引用其他技能的文件时按**技能名**找到该技能再读取，不要假设相对路径。配套技能没有安装时，按下表“未安装时”一列处理，不要假装读取了不存在的文件；需要完整能力时，提示用户安装整个技能包。

| 用到的内容 | 所在技能 | 未安装时 |
|---|---|---|
| 写论文的五问（`references/requirement-decomposition.md`） | `law-paper-writing` | 建库访谈的 A、B 两组已覆盖研究问题所需内容，直接按访谈提问 |
| 逐条溯源的回答格式（`references/multimodal-citation-format.md`） | `law-paper-writing` | 每项事实主张后注明库内页面与原始文件路径，不写无出处的断言 |
| 实证与群案材料在论文中的表述限制（`references/empirical-case-research.md`） | `law-paper-writing` | 比例一律限定为“样本内”，不把样本分布写成趋势 |
| 批量同步、缺漏扫描、规范依据插入等脚本；幽灵文件清理；每日检修 | `legal-wiki-audit-repair` | 按本技能 `references/linking-and-cross-references.md` 的手工流程小批执行，先备份 |

## 核心纪律

### 1. 范围先于速度

用户给出一个装满材料的目录时：先盘点（列目录、计数、识别分组与重复文件）→ 展示一两份代表性材料的要点 → 问清范围 → 分主题分批处理。即使用户说“全部摄入”，也分批进行、每批汇报。不要在用户不知情时处理几十份文件。

### 2. 材料边界（闭世界查询）

- 查询知识库、为写作调取证据时，**只用库内页面及其 `raw/` 原始材料回答**；模型记忆不是来源；
- 库内没有的，如实说“库内无此内容”，标 `[来源不明]`，并给出摄入方案（先摄入再回答）；
- **空壳或占位页面不算覆盖**：只有 frontmatter 或占位文字的页面视为未摄入；未摄入的样本不能支撑统计结论；
- 联网检索属于**摄入环节**（经用户授权、为补充材料），不属于查询环节；新获取的材料先入 `raw/` 并登记，再进入页面；
- 来源性主张（法条、案号、文献页码、数据）必须能回溯到库内页面和原始材料；回答时标出处（`[[页面名]]`，需要逐条溯源时用 `law-paper-writing` 的 note-level 溯源格式）。

### 3. 一个项目一个 vault

不同研究项目使用独立 vault；不混扫、不混改，不因为发现旧路径就恢复或迁移旧库。跨项目复用的方法论放在 `methodology/` 或技能中，不共享实体页面。

### 4. 先问清楚要建什么样的库，由用户主导

新建研究库，或把已有研究库做得更深之前，先做**建库访谈**（[wiki-design-interview.md](references/wiki-design-interview.md)）：分组提问，一次 1—3 个问题并附选项；必问目的、研究问题与分析框架、“将来会怎么用这个库”三组，其余按需深入；整理成《Wiki 设计书》（模板 `assets/templates/wiki-design-brief.md`），用户确认后再定 SCHEMA、目录与模板。已有研究库走访谈的“加深模式”：先只读了解现状，再问痛点、新维度与试点范围。

访谈中关于论文本身的问题（交付物、读者、问题意识、材料、验收标准）与写论文的五问一致，见 `law-paper-writing` 的 `references/requirement-decomposition.md`；答案写入 `research-design/` 后再开始摄入。用户已有自己的框架时以用户框架为准；用户暂时没有思路时，允许先建库，并在每个模块完成时根据已摄入材料主动归纳可行方向、提出建议。**不要把其他项目的分析框架、案例分类或标签体系套到新项目上。**

### 5. 来源与分析分开，宁缺毋滥

页面中的事实、日期、案号、条文、裁判理由只能来自原始材料；研究分析另写并可追溯。证据不足时写“暂不形成结论”或标待核，不用模板或推测填满。

## 新建研究库的顺序

1. **确认 vault 路径与项目边界**；
2. **建库访谈与研究设计**：按 [wiki-design-interview.md](references/wiki-design-interview.md) 提问 → 写《Wiki 设计书》并请用户确认 → 写 `research-design/` 研究设计页（见 [research-design-pages.md](references/research-design-pages.md)）；
3. **SCHEMA、index、log**：从 [assets/templates/](assets/templates/README.md) 复制 `SCHEMA.md`、`index.md`、`log.md`，与用户确定目录、页面类型、标签词表（中文标签）和必填字段；
4. （可选）**期刊风格观察**：用户有目标期刊时，请其提供 2—3 篇该刊近期范文，摄入为 `entities/范文/`，在 `methodology/` 写风格观察卡（只作写作参考，不作期刊正式要求）；
5. **论文**：先摄入论文，建立概念骨架；
6. **案例**：再摄入案例，挂到已有概念上；
7. **法规范**：按效力层级摄入相关条文；
8. **比较层与网络**：`comparisons/` 跨案比较、论文—案例—法规范互联；
9. 之后才进入论文写作（交给 `law-paper-writing`）。

用户问“先摄入论文还是案例”时，建议**先论文**：论文搭建概念骨架，案例才有可挂接的概念页；论文也揭示哪些维度值得打标签，避免返工。

## 目录与页面类型

```
<vault>/
├── SCHEMA.md            # 页面类型、字段、标签词表、链接约定
├── index.md             # 列出每一个正式页面
├── log.md               # 一行一事的时间线（只追加）
├── raw/                 # 原始材料，只读、不可修改
│   ├── papers/  cases/  法规范/  screenshots/  transcripts/  assets/
├── entities/
│   ├── 引用文献/        # 学术论文
│   ├── 案例/            # 案例（可按用途再分子目录）
│   ├── 法规范/          # 按效力层级分子目录
│   ├── 范文/            # 目标期刊范文（只作风格参考，不是引用文献）
│   └── 底稿/            # 用户自己的已完成作品（锚点）
├── concepts/            # 概念页、争议地图
├── comparisons/         # 跨案比较
├── queries/             # 查询结果、对照表
├── research-design/     # 研究设计、论点—证据—引注矩阵（随项目演进）
├── methodology/         # 跨项目方法论、期刊风格观察卡（稳定层）
├── drafts/              # 用户初稿与思路文件（非正式页面，不计入页数）
└── .maintenance/        # 备份、映射、证据（不计入页数）
```

- 实体目录超过约 30 个文件时按类型分子目录；Obsidian 按文件名解析链接，子目录不需要路径前缀；调整结构后全库死链为零，并同步 `index.md` 与 SCHEMA；
- `legal-wiki-audit-repair` 的脚本默认使用 `entities/引用文献`、`entities/案例`、`entities/法规范` 这三个目录名；采用其他名称时在 SCHEMA 中写明，并相应调整脚本参数或配置；
- 标签使用中文（Graph View 中拼音难读）；在 SCHEMA 中维护标签词表，区分主题、要件、程序、来源、结果和研究用途，不随意新增自由标签。

## 按材料类型摄入

| 材料 | 目标页面 | 读取 |
|---|---|---|
| 学术论文 PDF | `entities/引用文献/` + 概念页更新 | [pdf-paper-ingestion.md](references/pdf-paper-ingestion.md)；脚本 [batch_extract_papers.py](scripts/batch_extract_papers.py)、[clean_pdf_artifacts.py](scripts/clean_pdf_artifacts.py) |
| 本地 PDF 的哈希、双文件保存与复核 | `raw/papers/`（新提取物也可放派生目录） | [multimodal-pdf-extraction.md](references/multimodal-pdf-extraction.md)（统一哈希口径；批量提取 `--format md`、只读复核 `--verify`） |
| 案例、裁判文书、案例汇编 | `entities/案例/` | [case-ingestion.md](references/case-ingestion.md)、[docx-case-parsing-lessons.md](references/docx-case-parsing-lessons.md)、[docx-scope-and-mapping.md](references/docx-scope-and-mapping.md)、[docx-case-compilation-revalidation.md](references/docx-case-compilation-revalidation.md) |
| 法律法规、司法解释、批复答复、会议纪要、审判答疑 | `entities/法规范/` | [legal-norm-hierarchy-and-reply-ingestion.md](references/legal-norm-hierarchy-and-reply-ingestion.md)；需要研究规范在不同时期的版本与历史案件适用时，见 [norm-versioning.md](references/norm-versioning.md) |
| 用户初稿与思路文件 | `drafts/` | [case-ingestion.md](references/case-ingestion.md) 第八节；脚注提取 [docx-footnote-extraction.md](references/docx-footnote-extraction.md)；稿件出新版本时的同步流程 [draft-version-sync.md](references/draft-version-sync.md) |
| 图片、截图、扫描件 | `raw/screenshots/` + 提取文件 | [multimodal-image-ingest.md](references/multimodal-image-ingest.md) |
| 音频、访谈、录音 | `raw/transcripts/` + 逐字稿 | [multimodal-audio-ingest.md](references/multimodal-audio-ingest.md) |
| 批量下载参考文献 | stub → 补全 | [multimodal-bulk-refs.md](references/multimodal-bulk-refs.md) |
| 云端同步 vault | — | [multimodal-obsidian-headless.md](references/multimodal-obsidian-headless.md) |

通用要求：

- **汇编中的每一项单独建页**：一份 DOCX 里有几十个案例、批复或问答时，逐项建页；汇总页只是补充。`index.md` 列出每一个页面，只有分组标题不够；
- **重复文件**用哈希比对后报告给用户，不静默过滤；
- **旧版 `.doc`** 先转换为文本（macOS `textutil`，其他系统 LibreOffice），原件入 `raw/`；
- **DOCX 的脚注**不在 `python-docx` 的 `paragraphs` 里，需要读取 `word/footnotes.xml`；转换任何论文或初稿 DOCX 后都要确认脚注已提取。

## 页面内容标准

每个页面都要有实质内容，不允许只有元数据的空壳、“详见原文”“待补充”等占位文字，见 [content-completeness.md](references/content-completeness.md)。各类页面的模板（YAML 字段与章节结构）见 [assets/templates/](assets/templates/README.md)，新建页面时复制对应模板，按项目需要调整后同步修改 SCHEMA。

- **论文页**：作者与单位、书目信息、摘要、关键词、核心论点（3—5 条完整判断）、研究方法、主要结论、引用规范、引用案例、与底稿和其他论文的关联、相关概念；
- **案例页**：基本信息、基本案情、程序历程与裁判结果、争议焦点、裁判理由与要旨、裁判依据、研究定位、与底稿/论文/其他案例的关联；来源事实与分析分开；
- **概念页**：定义、当前认识、代表文献、代表案例（正例必列并附裁判要点；反例与边界例逐一检查——暂未找到时写明检索范围与结论限制，如实标注“未发现材料／待核验”，不硬凑）、争议与反方、规范依据、与比较页和其他概念的关联；方法论和写作指南类页面不需要案例层；
- **比较页**（`comparisons/`，群案研究价值最集中的一层）：样本纳入标准 → 案例表（案例链接 / 案情 / 争点 / 裁判结果）→ 相同点 → 差异点 → **反例与边界**（必须检查：写明边界在哪里；暂未找到时写“未发现材料＋检索范围＋结论限制”，不硬凑否定样本）→ **可支持的论文主张**（直接通往论文，用户最先看这一节）→ 与其他比较页的关联。正文中提到案例一律用带显示名的链接 `[[案例文件名|简称]]`，表格中用 `[[案例文件名\|简称]]`。

## 链接网络

链接规则、死链预防、以底稿为锚点的交叉引用、论文—案例双轨关联、法规范三角互联和批量替换陷阱，见 [linking-and-cross-references.md](references/linking-and-cross-references.md)。要点：

- 只给已有页面或足够重要的概念加链接，每批结束死链为零；
- 每条关系说得出理由（呼应、补充、分歧、规范依据、证明结构、程序阶段、时间演变），不为降低孤岛数而机械加链接；
- 论文—案例按“引用轨 + 主旨轨”建立，无实质对应不硬加；镜像到另一侧时带印证说明，不留裸链接；
- 表格中别名用 `\|`；维护文档里的示例链接写成纯文本。

## 知识库与论文写作双轨隔离

知识库管知识库的更新，论文管论文的写作，两条轨道隔离，防止互相污染：

1. **写入方向单向**：论文写作不改知识库（唯一例外是论文定稿后的版本同步，见 [draft-version-sync.md](references/draft-version-sync.md)）；论文写作期间，知识库不做批量结构调整（页面迁移、重新分类、字段变更冻结），只做纯素材补充。
2. **三个阶段**：写作期，知识库照常扩展但不碰 `drafts/` 与论文层内容；写作定稿后，写作只从定格的知识库状态取证据；定稿后，把写作期间记下的缺口一次性回填。
3. **写作反馈不丢**：写作中发现的证据缺口（论点缺案例、比较页缺反例）记入交接页的待补清单，定稿后统一回填。隔离的是写入动作，不是需求收集。
4. **不按论点重新分类**：论点定稿后，在论点—证据—引注矩阵中填写“论点 → 案例”对应，不移动目录；按时间演变的需求用筛选（文件名年份、案例页时序一节）满足，不重新分类。
5. **交接页是主存档**：重要决定与用户反馈写进交接页（模板 `assets/templates/handoff.md`），新会话先读；不要只放在代理的记忆里。

## 研究设计层

`research-design/` 随项目同步演进：研究设计页、论点—证据—引注矩阵、样本选取标准、统计口径清单、门禁状态表；`concepts/` 中可建学术史争议地图。统计“可执行”不等于“已计算”，数据落地前假说保持待验证，写作中不出现数字。见 [research-design-pages.md](references/research-design-pages.md) 与 [statistics-landing-and-case-matching.md](references/statistics-landing-and-case-matching.md)。

## 每批摄入后的一次性验收

摄入、清洗、链接全部完成后，一次运行全部检查并提交一份报告；不要修完一个维度就宣布完成：

1. **内容**：无空壳、无占位文字；缺口（待核验／未发现材料）与空壳分开记录；
2. **论文质量**：对照原文核验摘要与结论的真实完整（长度与链接数只作筛查信号）；无 PDF 残留、关键词干净；YAML 以真实解析结果核验（见 [pdf-paper-ingestion.md](references/pdf-paper-ingestion.md)）；
3. **死链**：全库递归扫描为零（`python3 scripts/check_wikilinks.py <vault> --strict`，见 [check_wikilinks.py](scripts/check_wikilinks.py)）；`--strict` 口径下畸形链接、空目标、缺失附件、路径前缀不符、锚点缺失与同名歧义同为零，示例和历史引用单列；
4. **交叉引用**：实体页之间有带理由的链接，锚点页连到相关页面；
5. **YAML 与 index**：全库可解析，每个正式页面都在 `index.md` 中；
6. **研究设计同步**：材料状态、门禁、口径与现状一致。

以模块为单位推进（一个文件夹通常是一个模块）：摄入 → 关联 → MODULE-END CHECK → 下一模块。检查项见 [case-ingestion.md](references/case-ingestion.md) 第七节。子代理报告的“完成”不是证据，按文件核验内容。

## 审计与修复

- 对已有语料的只读诊断和小批修复：[literature-audit-and-repair.md](references/literature-audit-and-repair.md)、[staged-deep-repair.md](references/staged-deep-repair.md)；
- 全库结构与学术可用性审计、模板化检测、图谱形态、整改台账：[systematic-vault-audit-and-optimization-ledger.md](references/systematic-vault-audit-and-optimization-ledger.md)；
- 系统性的全库体检、P0—P3 分级、批量重命名与链接迁移、每日检修，交给 `legal-wiki-audit-repair`。

审计默认只读；用户授权修复后，默认每批 5—8 页，超过 10 页先列清单确认；先备份、先试运行，再写入。

## 多模型与子代理

批量提取、格式修复、死链检查等明确任务用单一模型；研究规划、疑难章节、实质审计、期刊适配等关口才需要多方意见。每个产物只有一个主写者；子代理之间不共享上下文，交接依靠落盘文件。各宿主的落地方式与交接物契约见 [model-orchestrated-legal-research-workflow.md](references/model-orchestrated-legal-research-workflow.md)。

## 与用户沟通

- 报告行动优先、简短：本批规模、具体页面、每页一项改动、关键验收数字、下一批（尚未开始）；
- 用户在批准前问“要不要改、有什么好处、怎么做”时，用几句平实的话加至多一张小表回答；
- 规则层面的改进（例如新的检查项）先登记为候选，经用户确认后再写入 SCHEMA 或方法论。

## 易错点

批量摄入、审计或修复前，先读 `references/pitfalls-and-lessons.md`（[易错点清单](references/pitfalls-and-lessons.md)）。最常见的几条：

- 递归扫描嵌套目录，包括 vault 根目录；
- 每次修改 frontmatter 后重新解析 YAML 并查看 diff；
- 批量改动前备份，先试运行，写后逐页复核；
- 文件名以磁盘为准（中文全角标点）；
- 汇编解析时区分分隔线与副标题破折号，生成文件名时处理重名；
- 追加日志前读真实末尾，并行子代理不各自写日志。
