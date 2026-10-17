# 更新记录

自 v2610.9 起，三个技能同步按日期发布：公开标签 `vYYMM.D`，机器字段 `YYMM.D.N`；同日追加版递增 N，历史编号保留。变更同时更新 SKILL、锁、清单与当前 README。此规则不改变论文稿件版本。

## v2610.17（2026-10-17；机器字段 2610.17.0）

- 适配 Devin（CLI / Desktop）：新增 Devin 原生能力映射（`ask_user_question`、`read`、`subagent_explore`、`todo_write`），说明 Devin 全局与项目技能路径及其自动读取 `~/.claude/skills` 带来的重复安装风险。
- 预检与脚本在 Devin 下按技能 `Base directory` 拼绝对路径运行，同一会话只预检一次。
- `model-orchestrated-legal-research-workflow.md` 宿主对照表增加 Devin 列。
- SKILL.md 精简（写作 −36%／建库 −16%／审计 −20%），宿主专属说明移入 references/host-adapters.md。
- 预检对所有宿主改为同一会话只运行一次；check --json 不再输出完整清单与历史（约 28 KB → 不足 1 KB）。
- 新增 tools/bump_version.py，版本号以 bundle-release.json 为单一来源，测试不再硬编码版本。
- 锁与发布清单随技能包统一升级至 2610.17.0。

## v2610.16（2026-10-16；机器字段 2610.16.0）

- 适配 Google Antigravity 原生环境：原生支持 `view_file`、`ask_question`、`invoke_subagent` 工具映射；识别 Antigravity 全局与工作区技能路径。
- 修复更新预检在沙盒无写入/外网权限时抛出 `PermissionError` 的问题，优雅降级为离线安全检查。
- 锁与发布清单随技能包统一升级至 2610.16.0。

## v2610.14（2026-10-14；机器字段 2610.14.0）

- 任务入口与路由：五种入口（新建／增量摄入／查询／加深／审计）先判定进路再执行；首批材料顺序按研究类型推荐（论文导向可先论文、群案实证可先案例）；设计书与建库访谈去重，避免重复提问与顺带建页。
- 口径统一：两技能共享同一链接检查实现（`wiki_links.py` 双副本），`check_wikilinks` 扩展类别与 `--strict`；原件与提取物哈希统一为 `source_sha256`／`text_sha256`，`batch_extract_papers.py` 增 `--format md`／`--out-dir`／`--verify`。
- 内容完整性改为证据驱动：移除诱导补写的硬指标；SCHEMA 更新策略与规范时序对齐。
- 证据最小记录与行为回归：SCHEMA 新增“证据最小记录”（定位＝页码／章节段／时间戳、摘录与核验状态）；新增边界夹具、模板端到端与行为评估记录测试。
- 文档整理：参考文档全中文化；`SKILL.md` 瘦身约 23.7%，规则原样迁入 8 份新参考（双轨隔离、目录与页面类型、材料路由、技术健康清单、学术可用性清单、每日维护与周期检查、Obsidian 解析细节、模板化与假图谱检测）。
- 三份审计参考文档迁出至审计技能（引用同步更新）。

## v2610.9（2026-10-09；机器字段 2610.9.0）

- 与写作技能同步日期版；写作技能活动名称改为 `law-paper-writing`，跨技能引用及安装入口同步。
- 保留本技能的建库/审计范围、闭世界来源纪律与原有全部业务能力。
- 更新器新增历史版本排序、旧名原位迁移、独立确认、备份和失败回滚测试；旧更新器不能透明识别新名称清单，迁移说明见技能包 README。
- 从本版开始公开标签采用 `vYYMM.D`，三技能统一机器版本 `YYMM.D.N`；历史版本记录不改写。

## 5.0.1（2026-09-28）

- 仓库更名为 `shawndeng321/legal-academic-research-skills`：更新器的清单地址与 README 中的安装命令随之更新。旧地址由 GitHub 自动跳转，已安装的用户不受影响。

## 5.0.0（2026-09-25）

从单一研究项目中积累的经验，改写为适用于任何法学领域的通用建库技能。

- `SKILL.md` 重写（约 107 KB → 约 16 KB）：保留范围优先、材料边界（闭世界查询）、研究思路先行、来源与分析分开、模块化验收等纪律；细节移入按主题组织的参考文件。
- 20 份会话记录（`session-*.md`）合并为 5 份主题参考文件：`pdf-paper-ingestion.md`、`case-ingestion.md`、`linking-and-cross-references.md`、`research-design-pages.md`、`literature-audit-and-repair.md`；删除其中的具体作者、案例编号、样本数量、本机路径和个人信息。
- 移除项目专属规则：固定的三层案例分类、三维分析框架、特定标签词表与论文主题分类、特定期刊的格式实测值；改为“先问用途，再按项目设计”，并给出可选的常见方案。
- `legal-norm-hierarchy-and-reply-ingestion.md` 重写为通用的法源、规范层级与法规范摄入流程；对司法解释与规章的关系改用审慎表述。
- `pitfalls-and-lessons.md`、`statistics-landing-and-case-matching.md`、`docx-case-parsing-lessons.md` 通用化；多模态与模型编排参考文件改为宿主中立，增加 Hermes / Claude Code / Codex 的能力对照。
- 新增“技能包更新预检”中的 Claude Code 插件通道与“运行环境”说明：相对路径以技能目录为基准，不绑定宿主工具名，不写死 `/tmp`。
- 修复（发布前审查）：`clean_pdf_artifacts.py` 原先删除全页的 `【】`，会损坏案例页的 `【裁判要旨】` 等标签，并把 `［1］` 注码变成紧贴正文的数字；现只处理论文页的摘要、关键词、核心论点、主要结论四个章节，注码整体删除。
- 修复（发布前审查）：`check_wikilinks.py` 在 Python 3.9 上无法运行，且把 `[[目标\|别名]]`、`[[目标.md]]` 误报为死链；现按 Obsidian 规则解析别名、锚点、`.md` 后缀与附件嵌入，跳过隐藏目录和备份，单列畸形链接，新增 `--strict`。
- 预检与示例命令改为 `python3`（Windows 用 `py`）；macOS 默认没有 `python` 命令。
- 兼容性：`description` 改为“英文开头句 + 中文触发词”（约 200—240 字符，Codex 与 Hermes 上限均为 1024）。开头一句不超过 57 字符，因为 Hermes 在系统提示的技能目录中只显示前 57 个字符；后半部分的中文触发词供 Claude Code、Codex 自动选用；Claude Code 插件安装时跳过更新预检，不再每次加载都弹出命令权限确认。
- 新增 `assets/templates/`：20 个页面模板（SCHEMA、index、log，以及案例、论文、概念、比较、法规范、规范实体/版本/条款版本、研究设计、论点证据引注矩阵、期刊风格观察卡、范文、底稿、争点导航、会话交接、行文思路页），以一个实际运行的法学研究库为蓝本通用化，不含原库内容。
- 找回并通用化本机旧版中从未上传的内容：“知识库与论文写作双轨隔离”（写入 SKILL.md）、`references/draft-version-sync.md`（论文草稿新版本同步）、`references/norm-versioning.md`（规范时序版本、七类研究对象、历史案件两层评价、试点方法）、`docx-footnote-extraction.md` 中引用位自带方括号时的 `[[脚注N]]` 形态。
- `check_wikilinks.py` 把 `drafts/` 中的链接列为容忍类（`[[脚注N]]` 汇总报告），把根目录台账与轮转日志 `log-YYYY.md` 视为维护文档。
- 新增建库访谈：`references/wiki-design-interview.md`（十组问题：目的、研究问题、将来怎么用、材料、深度、组织、关联、时间维度、质量与边界、维护与协作；新建与加深两种模式；提问规则）与 `assets/templates/wiki-design-brief.md`（Wiki 设计书），接入建库流程第 2 步。
- 新增 `evals/pressure-tests.md`：15 个行为评估场景。
- 新增“配套技能”一节：写明用到其他两个技能的哪些内容，以及未安装时如何处理；跨技能引用改为按技能名查找，不再使用 `../../其他技能/` 相对链接（Hermes 等宿主可能把技能分放在不同子目录，相对链接会失效）。
- 技能包更新器支持分目录安装：按技能名在技能根目录或一层分类子目录（如 Hermes 的 `research/`）中定位各技能，原地备份、更新与回滚；同一技能装了两份时停止并报告。
- 按“模型原生支持多模态”调整：删除图片摄入的“宿主能力检查”与视觉工具路由（模型直接读图，文字存档保留以便检索与溯源）；扫描版 PDF 改为模型直接读页面并逐页转写，专门 OCR 工具仅作数百页以上大批量的省钱选项；模型编排删除“多模态角色先整理、再交给写作模型”的分工，保留“先登记来源、后写作”。音频转录保留（Claude、Codex 等模型不能直接读音频）。

## 4.2.0（2026-08）

技能包按需更新预检；多模态摄入（图片、音频、本地 PDF、批量参考文献、Obsidian headless 同步）。
