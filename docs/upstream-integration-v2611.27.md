# 写作技能同步上游 v1.6（v2611.27）

## 固定来源与范围

- 上游：[VictorTran1023/law-paper-writing-skill v1.6](https://github.com/VictorTran1023/law-paper-writing-skill/tree/9e6507aed1f55946e3186a172346f9bf45860fa6)，提交 `9e6507aed1f55946e3186a172346f9bf45860fa6`。
- 上游差异基线：`v1.5` 标签，提交 `0454eea1d6ee8955199d9c4c2af7e4c3e9d10c73`。
- 本包基线：`e5fcf83`（v2611.13）。本次日期版本为 `v2611.27`，机器字段 `2611.27.0`，与上游版本分别编号。
- 本次仅对 `law-paper-writing/` 增量同步上游 v1.6 的引注实质核验、法律与案例边界、改稿压缩防失真规则及 C1—C12 合成评估材料；`legal-research-wiki` 与 `legal-wiki-audit-repair` 不修改任何业务规则、模板或脚本，仅随包同步版本号与文件锁。保留 MIT 许可证与原作者署名。

## 文件处置

以下路径除特别注明外均相对 `law-paper-writing/`。

| 上游变化 | 本包落点与适配处理 |
|---|---|
| `SKILL.md` | 同步 `AUDIT` 原文实质核验、检索摘要归入 `LEAD_ONLY`、引注完整性忠实原文要求及缺文推定/压缩失真易错点；保留 `law-paper-writing` 名称、双语 `Use when` 简介契约、宿主预检，并将总体积保持在 12,000 字节上限以内 |
| `references/evidence-and-legal-validity.md` | 同步检索摘要实页核验与纸媒优先、法条与条约实质四查（方向与编章、分款与但书前提、禁常识外延与缺文推定、域外法与译本防草案偏移）、典型案例“裁判结果”与“典型意义”区分、会晤报道禁拔高为“达成共识”、转引多组样本隔离；第50条与第84条链接分别适配指向本包分册 `citation-format-chinese.md` 与 `citation-format-legal.md` |
| `references/citation-integrity.md` | 新增“实质忠实度逆向核查”（脱离对话记忆回翻原件、长文大改建议独立只读复核、局部任务只查受影响引注），补“禁一注兜底无据推演”与事实通报/学理观点分注；完整保留本包“程序研究与改判机制例外” |
| `references/legal-prose.md` | 同步三类结构性 AI 套话识别（连字符/加号自造公式词、跨界公文黑话、同构段落模具，保留有正式出处的专有提法）及改稿压缩四条边界（合句不并款、缩句不混样本、对仗不添事实、拆句重对注位）；保留 `citation-format-legal.md` 第70条链接 |
| `references/workflow.md` | 同步整理材料关键限定词短摘录提示、全文修改第4轮“引注回原核验轮”及对外修改说明条号数据同步与脱敏要求 |
| `references/argumentation-diagnostics.md` | 同步随稿对外修改说明与正文条号数据一致及清除内部工具话术要求；保留方法或结果章节保护规则 |
| 上游 `references/obsidian-hermes-workflow.md` | 对应落入本包 `references/obsidian-knowledge-base.md`（不恢复旧文件名）：补多课题同库异题隔离及库内既有文件仍须核验是否为生效正式本 |
| 本包专属 `references/empirical-case-research.md`、`references/docx-production.md` | 轻量呼应上游 v1.6：实证细则补转引他人多组样本分母隔离；DOCX 交付前检查补旧样稿页眉残留核对及对外修改说明 DOCX 清空模板孤立脚注与脱敏核对（`scripts/md2docx_footnotes.py` 代码不变） |
| `assets/templates/citation-audit.md`、`claim-evidence-matrix.md`、`submission-checklist.md` | 引注审核拆为“形式与链路核查 + 正文—原文实质忠实度核查”（保留本包“适用引注体例”“再次引用”表述）；论点表提示附关键限定短摘录；投稿检查清单补对外修改说明脱敏与多文档一致 |
| `evals/citation-fidelity-cases.md`、`evals/pressure-tests.md` | 新增 C1—C12 共12个合成场景（9个失真识别 + 3个合理写法防误判），更新压力测试路由；写作评估场景总数由71项增至83项 |
| 上游 `README.md`、`CHANGELOG.md`、`docs/releases/1.6.md` | 不整体覆盖；按本包日期版本融入根 `README.md`、`README.en.md`、`docs/README.md`、`docs/release-v2611.27.md` 及写作 `README.md` / `CHANGELOG.md` |

## 协调后的执行口径

1. 全文定稿前须脱离当前对话记忆，逐条打开原件核对带注正文句与原文语义、限定前提和注位；局部润色或单节改稿仅核查受影响引注，不强制重审全文。
2. 援引程序法、涉外法或国际条约时核对请求方向与编章、分款主体与“但书/除外”前提；明示原适用方向、仅将国内规定作为立法或条约谈判参照的，属合理规范论证，不判为方向误用。
3. 未取得条约或法律全文前不凭常识推定常见条款；使用资料库既有外文法典或译本时排查 `Draft`/非官方本与跨源条号偏移；无中译本但已据官方正式本或双语公报核准条号的，按 `citation-format-legal.md` 第84条标注即可，不强造中文译者信息。
4. 典型案例严格区分法院实际裁判结果与发布机关“典型意义/裁判要点”评述；会晤或会议报道如实复述表态，不自行拔高为“达成共识”；联网检索摘要与合成链接按 `LEAD_ONLY` 对待，同内容有权威纸媒版面时优先引纸媒。
5. 改稿压缩守住合句不并款、缩句不混样本、对仗不添事实、拆句重对注位；有正式文件或文献出处的带符号专有提法按原貌保留；随稿对外提交的修改说明与正文同步条号、数据与总注数，不留内部知识库或写作工具过程词。
6. 保留本包的 DOCX 真实脚注脚本、实证与群案细则、知识库 note-level 溯源、共享自动更新器、多宿主适配与引注 7 分册结构。另两技能业务规则与脚本零改动。

## 验证边界

- `law-paper-writing/SKILL.md` 字节数保持在 `test_wiki12c_skill_slimming.py` 规定的 9,000～12,000 字节区间内，双语简介与触发词契约保持不变。
- 引注格式 7 分册文件未改动，手册第1—150条标题覆盖与分册体积上限保持不变；新增跨文件链接均指向本包实际分册并逐一解析通过。
- 修改文件统一归一为 LF 换行后运行 `tools/bump_version.py` 与 `tools/prepare_bundle_release.py --write`，并通过 `prepare_bundle_release.py --check` 指纹一致性校验。
- 新增公开内容经敏感词与私人路径扫描零命中；`tests/test_writing_upstream_integration.py` 增补 v1.6 整合回归断言并通过。独立只读子会话对 C1—C12（隐藏观察标准）完成盲测核验，12/12 符合预期行为边界；既有其余 71 项历史场景未在本轮重跑模型行为测试，不记为本轮重跑成绩。
