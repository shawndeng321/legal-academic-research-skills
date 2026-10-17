# 上游整合来源与处置

## 来源固定

- 上游：https://github.com/VictorTran1023/law-paper-writing-skill ，tag `v1.4.0`，提交 `7a9ad004b120773add271f2d1277d09588adcd90`。
- 用户基线：https://github.com/shawndeng321/legal-academic-research-skills ，提交 `042b998`，三技能上一 Bundle `2026.0928.0`。
- 候选公开日期标签 `v2610.9`，三技能/Bundle/插件机器字段 `2610.9.0`。正式写作名 `law-paper-writing`，另外两个名称不变。
- 全量文本审查覆盖上游与用户双方；本文是处置映射，不是独立法律来源核验报告。沿用 MIT 许可证及原著作权信息，不将上游内容归作用户原创。

## 框架对接

| 上游新增能力 | 本地阶段 / 用户能力 | 落点 |
|---|---|---|
| 中文、英德法俄日意引注体例及再次引用 | DRAFT / AUDIT / ADAPT 的来源与体例门禁 | citation-format.md、citation-format-foreign.md、citation-audit 模板 |
| 逐观点引注、综述组织、概念/常识处理 | RESEARCH / OUTLINE / DRAFT 的主张—证据—引注链 | argumentation-diagnostics.md、citation-integrity.md、legal-prose.md |
| 标题/脚注批语、多轮多方反馈 | REVISE 及不覆盖旧稿的版本管理 | argumentation-diagnostics.md、revision-response 模板 |
| 摘要问题—进路—观点—结论功能位 | ADAPT 与期刊风格观察卡 | journal-adaptation.md、abstract-examples.md |
| 引注与反馈行为场景 | 既有 A/G/压力、写作评测 | F1—F8、H1—H18 场景与本轮单独执行记录 |
| 外文显式斜体、标准 Markdown 注号 | 本地真实 Word 脚注、红色修订与样稿 | md2docx_footnotes.py、docx-production.md |

## 冲突协调与优先级

1. **研究例外**：普通例证引注从简，但程序研究、改判机制、群案和审级比较允许必要的多文书分析；说明各阶段、生效状态、来源与用途，保留统计单位和分母。
2. **不强塞理论**：主要论证章按问题必要性处理学说；方法/结果章交代方法、样本或检验目标即可。找不到原文只列补检，不编造来源；作者自己的推论不强求权威背书。
3. **期刊/用户/样稿优先**：正式期刊规则、用户已确认要求及获准样稿优先。200—300 字、3—5 关键词、临时页面只是不带期刊时可逆的本稿参数，不是统一 CSSCI 标准。
4. **格式例不等于证据**：书目样例来自上游，未在本轮独立核验；只能示范格式，不能凭样例补真实稿件的引注。
5. **闭世界仍独立生效**：查询与写作以用户限定材料为边界；无材料明确待核；联网须授权并先登记，模型记忆不是来源。
6. **旧成果保留**：DOCX、实证/统计、note-level 源路径、宿主中立接口、更新器、五问展开、期刊风格卡、稿件管理及历史评测全部保留；论文稿件版本不改成日期编号。

## 全部文件处置表

基线并集各路径只出现一次；新加的整合说明与本轮执行记录不计入基线并集。开发计划不作为技能安装内容。

| 基线相对路径 | 处置 | 理由 / 承接 |
|---|---|---|
| `.gitignore` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `CHANGELOG.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `LICENSE` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `README.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `SKILL.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `agents/openai.yaml` | 保留用户独有 | 保留现有 DOCX、实证、溯源、宿主配置和更新器，按本版需求增补而非替换。 |
| `assets/examples/abstract-examples.md` | 新增并路由 | 增加至同相对路径；格式例和合成素材不自动视为 VERIFIED 来源，场景文件不等于执行成绩。 |
| `assets/examples/legal-prose-examples.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `assets/readme/paper-banner.jpg` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `assets/readme/paper-evidence-chain.jpg` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `assets/templates/citation-audit.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `assets/templates/claim-evidence-matrix.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `assets/templates/journal-profile.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `assets/templates/paper-project-brief.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `assets/templates/revision-response.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `assets/templates/source-register.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `assets/templates/submission-checklist.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `bundle-lock.json` | 保留用户独有 | 保留现有 DOCX、实证、溯源、宿主配置和更新器，按本版需求增补而非替换。 |
| `docs/superpowers/plans/2026-07-30-readme-redesign.md` | 不装入运行技能 | 上游开发计划/规格已审查；改进已进入运行参考及评测，计划不作为执行指令，避免携带机器路径。 |
| `docs/superpowers/plans/2026-09-14-generic-rules-fusion.md` | 不装入运行技能 | 上游开发计划/规格已审查；改进已进入运行参考及评测，计划不作为执行指令，避免携带机器路径。 |
| `docs/superpowers/plans/2026-10-07-citation-format-fusion.md` | 不装入运行技能 | 上游开发计划/规格已审查；改进已进入运行参考及评测，计划不作为执行指令，避免携带机器路径。 |
| `docs/superpowers/plans/2026-10-07-review-feedback-fusion.md` | 不装入运行技能 | 上游开发计划/规格已审查；改进已进入运行参考及评测，计划不作为执行指令，避免携带机器路径。 |
| `docs/superpowers/plans/2026-10-08-review-feedback-gap-fix.md` | 不装入运行技能 | 上游开发计划/规格已审查；改进已进入运行参考及评测，计划不作为执行指令，避免携带机器路径。 |
| `docs/superpowers/specs/2026-07-30-readme-redesign.md` | 不装入运行技能 | 上游开发计划/规格已审查；改进已进入运行参考及评测，计划不作为执行指令，避免携带机器路径。 |
| `evals/2026-09-09-review.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `evals/2026-09-18-writing-review.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `evals/argumentation-cases.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `evals/citation-format-cases.md` | 新增并路由 | 增加至同相对路径；格式例和合成素材不自动视为 VERIFIED 来源，场景文件不等于执行成绩。 |
| `evals/generic-fusion-cases.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `evals/pressure-tests.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `evals/review-feedback-cases.md` | 新增并路由 | 增加至同相对路径；格式例和合成素材不自动视为 VERIFIED 来源，场景文件不等于执行成绩。 |
| `evals/runs/2026-09-18-writing-smoke.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `evals/writing-evaluation.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `evals/writing-inputs.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `references/argumentation-diagnostics.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `references/citation-format-foreign.md` | 新增并路由 | 增加至同相对路径；格式例和合成素材不自动视为 VERIFIED 来源，场景文件不等于执行成绩。 |
| `references/citation-format.md` | 新增并路由 | 增加至同相对路径；格式例和合成素材不自动视为 VERIFIED 来源，场景文件不等于执行成绩。 |
| `references/citation-integrity.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `references/docx-production.md` | 保留用户独有 | 保留现有 DOCX、实证、溯源、宿主配置和更新器，按本版需求增补而非替换。 |
| `references/empirical-case-research.md` | 保留用户独有 | 保留现有 DOCX、实证、溯源、宿主配置和更新器，按本版需求增补而非替换。 |
| `references/evidence-and-legal-validity.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `references/journal-adaptation.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `references/legal-prose.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `references/multimodal-citation-format.md` | 保留用户独有 | 保留现有 DOCX、实证、溯源、宿主配置和更新器，按本版需求增补而非替换。 |
| `references/obsidian-hermes-workflow.md` | 由本地已有能力承接 | 本地 obsidian-knowledge-base.md 与 multimodal-citation-format.md 具有更完整的边界、note-level 原始来源链；不另加重复工作流。 |
| `references/obsidian-knowledge-base.md` | 保留用户独有 | 保留现有 DOCX、实证、溯源、宿主配置和更新器，按本版需求增补而非替换。 |
| `references/requirement-decomposition.md` | 章节级协调 | 以用户结构为骨架吸收上游新增，保留本地独有层；身份、宿主、版本和研究边界按本版适配。 |
| `references/workflow.md` | 保留共同基线 | 两端相同，保留；历史评测不充当本轮成绩。 |
| `scripts/legal_skills_update.py` | 保留用户独有 | 保留现有 DOCX、实证、溯源、宿主配置和更新器，按本版需求增补而非替换。 |
| `scripts/md2docx_footnotes.py` | 保留用户独有 | 保留现有 DOCX、实证、溯源、宿主配置和更新器，按本版需求增补而非替换。 |

## 验收边界

静态路由与关键词测试只证明文件/规则存在；脚本单元测试证明所覆盖场景的代码行为。模型走查需保留合成输入、实际输出和观察；同模型维护者走查不能声称独立盲测或多模型效果。DOCX ZIP/XML 验收不等于 Word/WPS 视觉排版验收。正式候选以发布清单、锁和本轮执行记录为准，不能把历史评测当作本轮结果。
