---
name: law-paper-writing
description: "Use when writing or reviewing Chinese legal papers. 法学期刊/CSSCI论文：选题、五问需求拆解、提纲、起草、改稿、审稿意见落实、引注与法律时效核查、期刊适配、投稿DOCX脚注; planning, drafting, revising, auditing, journal adaptation. Not for theses, books, contracts, pleadings or client advice."
license: MIT
metadata:
  version: "2610.14.0"
---

# Law Paper Writing（法学论文写作）

## 技能包更新预检

每次加载本技能时，先运行 `python3 -X utf8 scripts/legal_skills_update.py check --json`（Windows 用 `py -X utf8 …` 或 `python -X utf8 …`）。脚本按 **6 小时**缓存自动检查结果；只有返回 `update_available` 时才向用户展示 `[立即更新] [查看更新说明] [稍后提醒] [忽略此版本]`，其他状态（含离线、沙箱拒绝联网或状态目录不可写）不打断当前任务并继续执行。没有用户的明确确认，绝不运行 `apply`；“查看更新说明”只读取版本、变更与本地差异，不执行写入。

**Claude Code 插件安装时跳过预检**：宿主给出的本技能基础目录路径含 `/plugins/cache/`（或位于 `.claude/plugins/` 下）时，本技能由 Claude Code 插件安装，更新由 Claude Code 负责，不运行上面的预检命令，直接执行当前任务。用户问起更新时，请其运行 `claude plugin marketplace update legal-academic-research` 与 `claude plugin update legal-academic-research@legal-academic-research`，再在会话中运行 `/reload-plugins`。若已运行预检且结果的 `update_channel` 为 `claude-plugin`，同样不运行 `apply`，只按上述方式提示。

## 运行环境（Hermes / Claude Code / Codex 通用）

- 本技能是标准 `SKILL.md` 技能目录。正文中的 `references/`、`assets/`、`scripts/` 等相对路径一律以本技能目录为基准解析；宿主加载技能时给出的基础目录就是本目录。
- 读写文件、运行命令、委派子任务均使用当前宿主自带的工具；本文不绑定任何宿主的工具名。宿主不支持子代理时，按小批次串行执行同样的步骤。
- Python 命令按系统选择：macOS/Linux 用 `python3`（macOS 默认没有 `python` 命令）；Windows 用 `py`，没有时用 `python`。本文及参考文件中写作 `python3` 的命令，在 Windows 上照此替换。所需版本为 Python 3.9 及以上。临时文件放在系统临时目录（Python `tempfile`、`$TMPDIR` 或 `%TEMP%`），不要写死 `/tmp`。
- 宿主沙箱拒绝联网或写入时，先向用户说明需要的权限；更新预检失败直接跳过。

## 适用范围

用于任何法学领域的中文期刊论文：选题、研究、提纲、起草、修改、审核和目标期刊适配，包括 CSSCI 投稿论文。不用于专著、学位论文、合同、法律意见书、诉讼文书或当事人咨询。需要先建立或整理研究资料库时配合 `legal-research-wiki`，需要体检已有资料库时配合 `legal-wiki-audit-repair`。

## 配套技能

本技能与 `legal-research-wiki`、`legal-wiki-audit-repair` 同属一个技能包，可以单独安装使用。三个技能不一定在同一目录（例如 Hermes 可能把它们分放在不同分类子目录下），引用其他技能的文件时按**技能名**找到该技能再读取，不要假设相对路径。配套技能没有安装时，按下表“未安装时”一列处理，不要假装读取了不存在的文件；需要完整能力时，提示用户安装整个技能包。

| 用到的内容 | 所在技能 | 未安装时 |
|---|---|---|
| 把资料整理成研究库、从库中取证据 | `legal-research-wiki` | 直接按本技能的材料边界与来源登记处理用户提供的资料 |
| 草稿出新版本时的库内同步流程（`references/draft-version-sync.md`） | `legal-research-wiki` | 只按本技能“稿件版本”一节管理版本与旧稿 |
| 本技能 `multimodal-citation-format.md` 提到的原始文件路径记录方式 | `legal-research-wiki` | 使用用户提供的原始文件路径，不自行推断 |

## 本次整合

日期版 v2610.9 增量并入上游 v1.4.0：引注体例、逐观点引注、综述与概念处理、多方反馈、摘要规则；保留 DOCX、实证统计、note-level 溯源及稿件管理。处置与保留映射见 [upstream-integration.md](references/upstream-integration.md)，不另装第二个同义写作技能。

## 核心原则

围绕一个可论证的主问题组织论文；让每项来源性主张可追溯，让每项法律判断标明依据、版本与核验状态。宁可保留待核项，也不得补造文献、页码、案号、法条、数据或期刊要求。

## 先确定任务模式

识别用户需要的模式，只执行必要阶段：

| 模式 | 主要输出 |
|---|---|
| `PLAN` | 选题诊断、研究问题、范围与项目卡 |
| `RESEARCH` | 材料分类、来源核验、研究现状与证据缺口 |
| `OUTLINE` | 主张链、章节功能、论点—证据—引注表 |
| `DRAFT` | 带引注标识的分节或全文工作稿 |
| `REVISE` | 逻辑、论证、表达、术语和结构修改 |
| `AUDIT` | 引注、来源、法律时效、匿名与投稿检查 |
| `ADAPT` | 按目标期刊正式要求调整稿件 |

上述模式可以反复调用、交叉执行或按材料状态返回前序模式。完整论文通常经历 `PLAN、RESEARCH、OUTLINE、DRAFT、REVISE、AUDIT`，但不强制线性顺序；`ADAPT` 仅在已指定目标期刊且相关要求已经核验时执行。局部任务不得强迫用户重走完整流程。

## 按需读取参考文件

- 执行完整流程、选题、提纲、起草或修改时，读取 [workflow.md](references/workflow.md)。
- 需求模糊、开始新项目或用户未说明研究思路时，读取 [requirement-decomposition.md](references/requirement-decomposition.md)。
- 提纲、起草或实质改稿时，读取 [argumentation-diagnostics.md](references/argumentation-diagnostics.md) 的“按命题检查理由”部分；检查增量、框架、章节或审稿意见时，再读取对应部分。
- 起草正文、修改表达或处理“AI味”反馈时，读取 [legal-prose.md](references/legal-prose.md)；局部任务只处理指定范围，不扩展成全文审核。
- 使用法律规范、案例、政策、数据或学术文献时，读取 [evidence-and-legal-validity.md](references/evidence-and-legal-validity.md)。
- 起草正文、补引注、生成全文或执行引用审核时，必须读取 [citation-integrity.md](references/citation-integrity.md)。
- 决定或核对引注格式时，读取 [citation-format.md](references/citation-format.md)；涉及外文文献，另读 [citation-format-foreign.md](references/citation-format-foreign.md)。未指定期刊时按手册整理的工作体例，期刊正式要求及用户已确认的稿件体例优先；格式正确不等于来源已核验。
- 适配期刊、摘要、关键词、匿名或投稿要求时，读取 [journal-adaptation.md](references/journal-adaptation.md)。
- 以案例群、裁判文书样本、调研数据或统计结果支撑论证时，读取 [empirical-case-research.md](references/empirical-case-research.md)。
- 使用 Obsidian、Markdown 笔记或知识库时，读取 [obsidian-knowledge-base.md](references/obsidian-knowledge-base.md)；回答知识库查询或写作支撑需要把每项主张追溯到具体源文件时，再读取 [multimodal-citation-format.md](references/multimodal-citation-format.md)。
- 把工作稿转成投稿 DOCX（真实 Word 脚注、样稿格式复刻、修改标注版）时，读取 [docx-production.md](references/docx-production.md)，配套脚本为 [md2docx_footnotes.py](scripts/md2docx_footnotes.py)。

## 建立任务边界

开始前尽量确认：

1. 任务模式与交付物；
2. 主问题、法学领域与研究范围；
3. 用户允许使用的材料范围、Obsidian 读取范围、允许写回的具体文件及写回授权；
4. 目标期刊及其正式投稿要求；
5. 法律与事实资料截止日期；
6. 引注格式、篇幅和文件格式。

缺失信息不影响方向时，使用明确标注的暂定方案继续；缺失信息会改变结论、期刊适配或来源真实性时，先询问。不得将模型记忆当作已核验来源。需求模糊或用户未说明研究思路时，先用五问拆解（见 [requirement-decomposition.md](references/requirement-decomposition.md)），不猜测方向。

使用 [paper-project-brief.md](assets/templates/paper-project-brief.md) 建立项目卡。未指定目标期刊时，只能生成“通用工作稿”，不得声称存在统一的 CSSCI 字数、摘要、关键词、节数、引注或审稿期限。

用户要求立即排版时，可以给出明确但可逆的“本稿临时参数”；必须逐项标注为暂定，不得替目标期刊设定一稿多投、撤稿、独家等待、匿名或附件规则。

## 遵守材料边界与查询纪律

写作用料只允许两类：用户提供的材料，以及用户授权范围内、经核验并登记过的正式来源。模型记忆永远不是来源。

- 材料未覆盖的问题：如实说明“现有材料中没有”，保留 `[待核]` 或标 `[来源不明]`，并给出补充方案（去哪里查、补什么）；不得用模型记忆补全或凭印象脑补。
- 占位材料不算掌握：只有条目、摘要线索而无原文、页码、条文或案号的材料，按 `LEAD_ONLY` 对待；取得原文之前不得据此写具体表述。
- 联网检索属于材料获取与核验环节：新获取的材料先完成来源登记（来源、定位、核验日期、状态）再进入写作；写作与查询环节不引入来源登记以外的外部事实。

## 执行五项硬门禁

| 门禁 | 通过条件 | 未通过时 |
|---|---|---|
| 来源真实性 | 书目信息、原文位置、案号、数据来源可核验 | 标记待核、降级表述或删除 |
| 法律有效性 | 明确规范类型、版本、效力状态与核验日期 | 不作确定性现行法判断 |
| 引注完整性 | 来源性主张后有标识，正文、脚注与来源一一对应 | 不得交付最终稿 |
| 论证充分性 | 核心主张有理由、证据并处理重要反方观点 | 降为假说或补充论证 |
| 期刊适配 | 要求来自目标期刊正式来源并记录核验日期 | 保持通用工作稿状态 |

以下行为一律禁止：

- 编造作者、题名、期刊、出版社、年份、卷期、页码、DOI 或网址；
- 编造法律条文、效力状态、案号、法院、裁判日期、裁判观点、数据或调研结果；
- 把会议纪要、政策文件、案例、学术观点错误描述为法律或司法解释；
- 为满足字数或脚注数量而添加未阅读、未定位或不存在的材料；
- 删除待核标记并把未经核验的工作稿称为最终稿。

## 组织研究问题与论证

- 用一句话表述主问题，但允许设置有限子问题。
- 说明现有研究尚未充分解决的争议、缺口或解释困难；不强制同时存在理论与实务“双重空白”。
- 确认法律相关性，但允许法学与经济学、社会学、政治学、技术研究等交叉。
- 将研究范围压缩到可由现有材料和篇幅支持的程度。
- 区分作者主张、他人观点、法律文本、裁判观点、经验事实与推测。
- 对核心主张检查实质相关的竞争解释与反例；回应可以是反驳、吸收、区分或缩窄主张，不凑反方数量。

不要用“已有三篇相似论文”“必须三至四节”“必须固定字数”等机械阈值代替学术判断。

核心结论须有可复核的前提、理由和适用边界；说明材料为什么支持该判断。按命题类型选用 [论证检查](references/argumentation-diagnostics.md)，不把实证归纳作为统一方法。证明依赖关系不等于段落排列顺序：可以先提出判断再证明，也可以由疑难情形或解释分歧展开；说明性例子不能代替证明。

## 建立论点—证据—引注链

整理材料时先使用 [source-register.md](assets/templates/source-register.md) 建立平台无关的来源登记；起草前再使用 [claim-evidence-matrix.md](assets/templates/claim-evidence-matrix.md)。每个核心主张记录：

- 主张及其在全文中的功能；
- 证据类型和来源编号；
- 原文页码、条文、段落或案例定位；
- 从证据到判断的推论理由、必要前提及支持范围与局限；
- 反方材料；
- 核验状态；只有 `VERIFIED` 来源可以支持最终稿中的来源性主张。

没有足够证据的主张只能标为待证假说、缩窄表述或删除，不能通过修辞把证据缺口藏起来。

## 生成正文与引注

生成完整文章、章节或投稿稿件时，凡使用他人观点、原文、数据、案例、法律规范或其他非一般常识的外部事实，必须按观点在对应句就近设置引注标识，不把多项观点的来源堆在段末；同一主张的多个来源可合为一注。不得只在文末罗列参考文献。

未指定期刊和输出格式时，Markdown 工作稿使用脚注标识：

```markdown
相关研究提出……。[^S001]

[^S001]: 作者：《题名》，载《期刊》年份第X期，第X页。
```

资料不完整时使用：

```markdown
相关研究提出……。[^待核引注-01]

[^待核引注-01]: [待核：缺少原文页码，不得进入最终稿]
```

直接引语必须有准确页码、条文号、段落号或其他可复核定位；转述同样需要来源。DOCX 投稿稿应转换为真实脚注或目标期刊指定格式。

## 区分工作稿与最终稿

### 工作稿可以包含

- `[待确认：目标期刊]`
- `[待核引注-01：缺页码]`
- `[待核案例-02：缺正式案号]`
- `[待核法条-03：需确认效力状态]`
- `[来源不明：现有材料未覆盖]`
- 明确标注的暂定结构或篇幅预算

### 最终稿必须满足

- 不含任何待核、待确认或虚构补全内容；
- 每项来源性主张均能反向追溯；
- 法律规范与案例身份经过核验；
- 直接引语定位完整；
- 目标期刊要求有正式来源；
- 题目、摘要、引言、正文与结论围绕同一主问题；
- 结论不超出正文已经证明的范围。

使用 [citation-audit.md](assets/templates/citation-audit.md) 和 [submission-checklist.md](assets/templates/submission-checklist.md) 完成最终检查。

## 稿件版本

交付新版本必须升版本号，并在交付说明中写明相对上一版的变化；旧版本保留，不静默覆盖。版本号格式：X.Y.Z 为建议格式：结构、主线或研究方向变化升主版本号，增量修改升次版本号，低风险纠错升修订号。文件名带版本号，被取代的旧版可加“废弃-”等前缀保留。旧稿保留多少版由用户决定（例如只保留当前版与上一版）；超出保留窗口的旧稿先归档到备份目录（如 `.maintenance/`）再移除，不直接删除。稿件存放在研究库中时，新版本的同步流程见 `legal-research-wiki` 的 `references/draft-version-sync.md`。

## 常见错误

- 把背景介绍当作问题提出；
- 按作者逐一罗列而不评价研究分歧；
- 综述把多项观点的来源堆在段末，或用文献起止页码替代观点定位；
- 多方反馈冲突时自行取舍，漏掉脚注批语、标题括注、高亮范围或附录；
- 摘要用研究动作代替具体判断，加入正文未证明的创新或数据；
- 只有材料和案例，没有可反驳的作者主张；
- 法条、案例与规范结论各说各话；
- 把资料的存在误当作资料已被核验；
- 把 Obsidian 内部链接直接当作正式引注；
- 把一般经验值写成所有 CSSCI 法学期刊的统一标准；
- 为迎合用户要求而补造引用信息；
- 结语重复正文而不给出答案；
- 需求模糊时自行猜测方向动笔。
