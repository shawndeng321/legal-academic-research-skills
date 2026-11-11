---
name: law-paper-writing
description: "Use when writing or reviewing Chinese legal papers. 中文法学期刊/CSSCI论文：选题、五问需求拆解、提纲、正文、摘要、改稿、审稿意见落实、论证诊断、引注体例与法律时效核查、期刊适配、知识库溯源、实证材料、投稿DOCX真实脚注及稿件版本管理；不用于专著、学位论文、合同、法律意见书、诉讼文书或个案咨询。 Not for books, theses, contracts, pleadings or client advice."
license: MIT
metadata:
  version: "2611.11.0"
---

# Law Paper Writing（法学论文写作）

## 预检与运行环境

- **更新预检**：同一会话里本技能包任一技能已预检过就不再重复；否则运行 `python3 -X utf8 scripts/legal_skills_update.py check --json`（Windows 用 `py`；不在技能目录执行时拼成绝对路径）。结果按 6 小时缓存。只有 `update_available` 才向用户展示 `[立即更新] [查看更新说明] [稍后提醒] [忽略此版本]`；其他状态（含离线、沙箱拒绝）静默继续，不为预检申请权限。没有用户的明确确认，绝不运行 `apply`。
- **Claude Code 插件安装时跳过预检**：基础目录含 `/plugins/cache/` 或位于 `.claude/plugins/` 下，或 `update_channel` 为 `claude-plugin`／`antigravity-plugin` 时，更新由宿主插件管理器负责，不运行 `apply`；更新命令见 [host-adapters.md](references/host-adapters.md)。
- `references/`、`assets/`、`scripts/` 均相对本技能目录；需要 Python 3.9+。宿主专属路径与工具名见 [host-adapters.md](references/host-adapters.md)，只读当前宿主那一节。

## 适用范围

任何法学领域的中文期刊论文（含 CSSCI 投稿）：选题、研究、提纲、起草、修改、审核与目标期刊适配。不用于专著、学位论文、合同、法律意见书、诉讼文书或当事人咨询。

## 配套技能

同包技能可单独安装；引用其他技能的文件时按**技能名**找到该技能再读取，不假设相对路径。未安装时：

| 用到的内容 | 所在技能 | 未安装时 |
|---|---|---|
| 建研究库、从库中取证据 | `legal-research-wiki` | 按本技能的材料边界与来源登记处理用户资料 |
| 稿件新版本的库内同步（`references/draft-version-sync.md`） | `legal-research-wiki` | 只按本文“稿件版本”管理 |
| `multimodal-citation-format.md` 提到的原始文件路径记录 | `legal-research-wiki` | 用用户提供的原始路径，不自行推断 |
| 体检已有资料库 | `legal-wiki-audit-repair` | 提示用户安装 |

## 核心原则

围绕一个可论证的主问题组织论文；每项来源性主张可追溯，每项法律判断标明依据、版本与核验状态。宁可保留待核项，也不补造文献、页码、案号、法条、数据或期刊要求。模型记忆不是来源。

## 任务入口：交付物、必读与完成条件

按当前任务选一行，遇相应内容再加读；已读且未变的规则不重读。链接是按需索引；模式可交叉或回退，局部任务不强迫用户重走完整流程。

| 任务／模式 | 主要交付物 | 必读 | 完成检查 |
|---|---|---|---|
| 选题 `PLAN` | 主问题、范围与项目卡 | [工作流](references/workflow.md) | 问题与材料能对应；方向不明再用五问 |
| 研究 `RESEARCH` | 来源登记与证据缺口 | [证据核验](references/evidence-and-legal-validity.md) | 原文定位、法律版本与来源状态明确 |
| 提纲 `OUTLINE` | 主张链与章节功能 | [工作流](references/workflow.md)、[日常论证](references/argumentation-core.md) | 各节理由、证据与结论边界明确 |
| 正文起草 `DRAFT` | 带引注标识的工作稿 | `OUTLINE` 必读，加[正文表达](references/legal-prose.md)、[引注完整性](references/citation-integrity.md) | 主张有理由；来源性主张就近加注，缺口保留待核 |
| 实质改稿 `REVISE` | 修改稿与变化说明 | 同 `DRAFT`；实质反馈再读下列专题 | 回读受影响论证与引注，未解决项明确 |
| 只改摘要、关键词 | 指定范围的摘要或关键词 | [abstract-writing.md](references/abstract-writing.md) | 对照正文，无新增未证观点；满足本稿已核要求 |
| 局部表达修改 | 指定句段的修改 | [正文表达](references/legal-prose.md) | 原意、立场强弱和术语不变；改到主张或引语再加相应核验 |
| 引用核对／全文审核 `AUDIT` | 核验结果与待核清单 | [引注完整性](references/citation-integrity.md) | 单项只声明该项结果；最终稿检查全部适用门禁 |
| 期刊适配 `ADAPT` | 适配稿与未决项 | [期刊适配](references/journal-adaptation.md) | 目标期刊已指定、要求已核验 |

**遇到相应内容再加读**：

- 需求模糊或研究思路缺失：[五问](references/requirement-decomposition.md)。
- 增量、综述、框架、章节或反馈专题：[专题诊断](references/argumentation-diagnostics.md)；专项按内容触发，不强塞比较法、实证或证明责任。
- 使用、改变或审核法律规范、案例、政策、数据或文献主张：[证据核验](references/evidence-and-legal-validity.md)；补引注沿用 `AUDIT` 的必读规则。
- 核对引注格式：先读 [citation-format.md](references/citation-format.md) 的总则和索引，再读所需分册；英文见 [citation-format-foreign.md](references/citation-format-foreign.md)，其他语种沿其索引。期刊正式要求与用户已确认的稿件体例优先。
- 涉及案例群或统计材料：[实证材料](references/empirical-case-research.md)；使用知识库：[知识库](references/obsidian-knowledge-base.md)，逐项追溯源文件时再读 [原件溯源](references/multimodal-citation-format.md)。
- 转投稿 DOCX、真实脚注或样稿复刻：[DOCX制作](references/docx-production.md) 和 [md2docx_footnotes.py](scripts/md2docx_footnotes.py)。

## 任务边界

开始前确认：模式与交付物；主问题、领域与范围；可用材料、Obsidian 读取范围与写回授权；目标期刊及其正式要求；法律与事实截止日期；引注格式、篇幅与文件格式。缺项不影响方向时用标明的暂定方案继续；会改变结论、期刊适配或来源真实性时先问。需求模糊时先做五问，不猜方向动笔。项目卡用 [paper-project-brief.md](assets/templates/paper-project-brief.md)。

未指定目标期刊时只出“通用工作稿”，不声称存在统一的 CSSCI 字数、摘要、关键词、节数、引注或审稿期限。用户要求立即排版时，可给逐项标注为暂定的“本稿临时参数”，不替期刊设定一稿多投、撤稿、独家等待、匿名或附件规则。

## 材料边界

写作用料只有两类：用户提供的材料；用户授权范围内、已核验并登记的正式来源。

- 材料未覆盖的问题：说明“现有材料中没有”，标 `[待核]` 或 `[来源不明]`，并给出去哪查、补什么。
- 只有条目或摘要线索、没有原文定位的材料按 `LEAD_ONLY` 对待，取得原文前不写具体表述。
- 联网检索属于取材与核验：新材料先登记（来源、定位、核验日期、状态）再进入写作。
- 引注格式样例只示范格式，不能据以补真实稿件的引注；格式正确不等于来源已核验。

## 五项硬门禁

| 门禁 | 通过条件 | 未通过时 |
|---|---|---|
| 来源真实性 | 书目信息、原文位置、案号、数据来源可核验 | 标记待核、降级表述或删除 |
| 法律有效性 | 明确规范类型、版本、效力状态与核验日期 | 不作确定性现行法判断 |
| 引注完整性 | 来源性主张后有标识，正文、脚注与来源一一对应 | 不得交付最终稿 |
| 论证充分性 | 核心主张有理由、证据并处理重要反方观点 | 降为假说或补充论证 |
| 期刊适配 | 要求来自目标期刊正式来源并记录核验日期 | 保持通用工作稿状态 |

一律禁止：编造任何书目信息、法条、效力状态、案号、裁判内容、数据或调研结果；把会议纪要、政策、案例或学术观点说成法律或司法解释；为凑字数或脚注加入未读、未定位或不存在的材料；删除待核标记并把工作稿称为最终稿。

## 论证与论点—证据—引注链

- 一句话主问题，可设有限子问题；说明现有研究未解决的争议、缺口或解释困难，不强求理论与实务“双重空白”；范围压缩到材料与篇幅能支持的程度；允许法学与其他学科交叉。
- 区分作者主张、他人观点、法律文本、裁判观点、经验事实与推测；对核心主张处理实质相关的竞争解释与反例（反驳、吸收、区分或缩窄），不凑反方数量。
- 不用“已有三篇相似论文”“必须三至四节”“必须固定字数”等机械阈值代替学术判断。按命题类型选用论证检查，不把实证归纳当统一方法；说明性例子不能代替证明。
- 整理材料时用 [source-register.md](assets/templates/source-register.md) 登记来源，起草前用 [claim-evidence-matrix.md](assets/templates/claim-evidence-matrix.md) 记录每个核心主张的功能、证据与定位、推论理由与局限、反方材料和核验状态。只有 `VERIFIED` 来源能支持最终稿的来源性主张；证据不足的主张降为假说、缩窄或删除，不用修辞掩盖缺口。

## 正文与引注

他人观点、原文、数据、案例、法律规范及非一般常识的外部事实，按观点在对应句就近加注，不堆在段末，不只在文末罗列参考文献；同一主张的多个来源可合为一注。直接引语须有页码、条文号、段落号等可复核定位；转述同样需要来源。未指定格式时，Markdown 工作稿用脚注，资料不全时用待核注：

```markdown
相关研究提出……。[^S001]

[^S001]: 作者：《题名》，载《期刊》年份第X期，第X页。

另有观点认为……。[^待核引注-01]

[^待核引注-01]: [待核：缺少原文页码，不得进入最终稿]
```

DOCX 投稿稿转为真实脚注或目标期刊指定格式。

## 工作稿与最终稿

工作稿可含 `[待确认：目标期刊]`、`[待核引注-01：缺页码]`、`[待核案例-02：缺正式案号]`、`[待核法条-03：需确认效力状态]`、`[来源不明：现有材料未覆盖]` 及标明的暂定结构或篇幅预算。

最终稿须五项门禁全部通过、不含任何待核或待确认标记；题目、摘要、引言、正文与结论围绕同一主问题，结论不超出正文已证明的范围。最终检查用 [citation-audit.md](assets/templates/citation-audit.md) 与 [submission-checklist.md](assets/templates/submission-checklist.md)。

## 稿件版本

交付新版本必须升版本号并写明相对上一版的变化；旧版保留，不静默覆盖。版本号格式：X.Y.Z 为建议格式：结构、主线或研究方向变化升主版本号，增量修改升次版本号，低风险纠错升修订号。文件名带版本号，被取代的旧版可加“废弃-”前缀保留。保留几版由用户决定；超出窗口的旧稿先归档到备份目录（如 `.maintenance/`）再移除。稿件在研究库中时，同步流程见 `legal-research-wiki` 的 `references/draft-version-sync.md`。

## 易错点

- 把背景介绍当作问题提出；综述按作者罗列而不评价分歧，或用文献起止页码代替观点定位；
- 多方反馈冲突时自行取舍，漏掉脚注批语、标题括注、高亮范围或附录；
- 摘要用研究动作代替具体判断，或加入正文未证明的创新或数据；
- 只有材料和案例，没有可反驳的作者主张；法条、案例与结论各说各话；
- 把 Obsidian 内部链接当作正式引注；结语重复正文而不给出答案。
