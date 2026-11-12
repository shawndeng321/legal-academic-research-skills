# 法学研究 Wiki 建库 Skill

把论文、案例、法条和研究方法整理成可追溯、可审计、可继续维护的法学研究 Wiki。适用于任何法学领域的学术研究，适合在研究项目开始时建立底层资料结构，也适合已有 Wiki 的分批扩充。

> 运行时入口是 [`SKILL.md`](SKILL.md)。本页解决“什么时候用、怎么开始、如何验收”；详细规则按需阅读 `references/`。
>
> **当前版本：v2611.11（2026-11-11；机器字段 2611.11.0）**。本版：随技能包同步写作技能的上游 v1.5；本技能运行规则与脚本不变，继续保留既有建库/审计和多宿主能力。变更见 [CHANGELOG.md](CHANGELOG.md)。
>
> **未发布改动**：建库与摄入默认“当前多模态主模型＋按需工具＋必要子代理”，不再要求按角色选型号或维护注册表。旧文档中的写作路由、交接与必要复核原样保留。
>
> 核验完成状态：PDF 只读复核分别报告正文、原件与扫描完整性；缺失、读取失败、旧格式和空扫描明确列为未完成，退出码不再误报通过。
>
> 命令目录定位：PDF 示例分别定位技能脚本和知识库；从知识库根调用，保留 source_path 的库内相对写法，兼容中文和空格路径。

自动检查、四种提示选择、本地修改保护与回滚说明见[根 README 的自动更新章节](../README.md#自动更新)。

## 适合解决什么问题

- 研究材料散落在 PDF、DOCX、网页和 Obsidian 笔记中，缺少统一来源登记。
- 论文、底稿、案例和法条之间没有稳定的双向链接。
- 批量摄入后出现 PDF 残留、空壳页面、YAML 错误或标题格式问题。
- 需要在写作前确认材料范围、证据状态和 Wiki 质量，而不是直接让模型“补全”。

## 核心能力

| 能力 | 结果 |
|---|---|
| 研究思路先行 | 先用五问确认问题意识与分析框架，由用户主导；不套用其他项目的分类与框架 |
| 范围优先摄入 | 先勘察目录和授权范围，再确认批次，避免无边界扫描整个 Vault |
| 材料边界 | 查询与写作支撑只用库内页面及原始材料；库内没有的如实说明，先摄入再回答 |
| 多格式提取 | 支持 PDF/DOCX/图片/音频进入可复核的 Markdown 工作层；扫描件与图片由模型直接读取并存档文字，音频按宿主提供的转录能力处理 |
| 关系网络 | 建立论文↔底稿↔案例↔法条的可追溯链接（引用轨 + 主旨轨），每条关系写明理由 |
| 法规范分层 | 按效力层级组织法律、行政法规、司法解释、规章与司法文件，标注性质与现行版本 |
| 研究设计层 | 研究设计页、论点—证据—引注矩阵、统计口径清单、学术史争议地图 |
| 六维质量门禁 | 检查摘要、结论、PDF 残留、关键词、YAML 和标题空行 |
| 学术可用性 | 区分假说与事实、来源线索与已核验材料，保留证据缺口 |

## 典型工作流

```text
勘察范围 → 确认批次 → 读 SCHEMA/index/log → 摄入 → 六维检查 → 链接复核 → 记录台账
```

建议每批只处理有限页数，并在进入下一批前完成：死链检查、YAML 检查、六维质量检查和交叉引用检查。

## 快速安装

本技能属于[法学学术研究技能包](../README.md)，Claude Code、Codex、Hermes、Devin、Google Antigravity、DeepSeek Harness 等支持 `SKILL.md` 的宿主通用；完整说明见[根 README 的安装说明](../README.md#安装)。

### Claude Code（插件，一次安装三个技能）

```bash
claude plugin marketplace add shawndeng321/legal-academic-research-skills
claude plugin install legal-academic-research@legal-academic-research
```

### Hermes Skills Hub

```bash
hermes skills install shawndeng321/legal-academic-research-skills/legal-research-wiki
```

无交互终端加 `--yes`：

```bash
hermes skills install shawndeng321/legal-academic-research-skills/legal-research-wiki --yes
```

### 其他宿主（源码复制）

复制完整的 `legal-research-wiki` 目录（连同 `references/`、`scripts/` 和 `agents/`）到宿主的技能目录，例如 `~/.codex/skills/`、`~/.claude/skills/`、`~/.config/devin/skills/`、`~/.gemini/config/skills/`、`~/.hermes/skills/`、`~/.dsh/skills/` 或 `~/.agents/skills/`。

## 第一次使用

给任一宿主的任务都应明确范围、资料入口和写回权限，例如：

```text
使用 legal-research-wiki。只读取指定的 research/2026 行政法项目目录，先检查 SCHEMA.md、index.md 和 log.md，
提出本批 5—8 页的摄入计划。不要扫描其他目录，不要写回任何文件，先列出待确认的范围和质量门禁。
```

摄入前先固定：

1. 允许读取的目录和原始文件范围；
2. 本批处理的页数、类型和命名规则；
3. 来源登记、版本日期和精确定位要求；
4. 允许写回的具体文件，以及备份位置。

## 配套技能与脚本

- 维护与修复：[legal-wiki-audit-repair](../legal-wiki-audit-repair/)
- 论文写作：[law-paper-writing](../law-paper-writing/)
- 批量 PDF 提取：`scripts/batch_extract_papers.py`；论文摄入与质量修复：`references/pdf-paper-ingestion.md`
- 案例摄入与汇编解析：`references/case-ingestion.md`、`references/docx-case-parsing-lessons.md`
- 法规范层级与摄入：`references/legal-norm-hierarchy-and-reply-ingestion.md`
- 链接网络：`references/linking-and-cross-references.md`；全库死链检查：`scripts/check_wikilinks.py`
- 研究设计与统计：`references/research-design-pages.md`、`references/statistics-landing-and-case-matching.md`
- 文献库审计与修复：转交 `legal-wiki-audit-repair` 技能（细则在其 `references/`：literature-audit-and-repair、staged-deep-repair、systematic-vault-audit-and-optimization-ledger）
- 建库多模态执行：[当前模型、按需工具与必要子代理](references/multimodal-task-execution.md)
- 写作路由、质量职责与交接：[既有说明](references/model-orchestrated-legal-research-workflow.md)（正式写作约束保留；型号与注册表不作为建库前提）
- 易错点清单：`references/pitfalls-and-lessons.md`
- 页面模板：`assets/templates/`（SCHEMA、index、log，以及案例、论文、概念、比较、法规范含时序版本、研究设计、矩阵、范文、底稿、导航、交接、行文思路页）
- 规范时序版本与历史案件评价：`references/norm-versioning.md`
- 论文草稿新版本同步：`references/draft-version-sync.md`
- 建库访谈与 Wiki 设计书：`references/wiki-design-interview.md`、`assets/templates/wiki-design-brief.md`
- 评估场景：`evals/pressure-tests.md`（15 个场景：建库访谈、摄入、材料边界、链接与批量操作、报告），修改核心规则后逐条检查
- 多模态摄入：`references/multimodal-image-ingest.md`、`references/multimodal-audio-ingest.md`、`references/multimodal-pdf-extraction.md`
- 批量参考文献：`references/multimodal-bulk-refs.md`
- PDF 文本残留清洗：`scripts/clean_pdf_artifacts.py`（只处理论文页的摘要、关键词、核心论点、主要结论四个章节，其他页面与章节不动）

脚本默认偏保守：先 `--dry-run`，写入时提供调用方指定的备份目录；不要把作者本机路径、整库路径或未经确认的批量范围写进命令。

## 适用范围与边界

适用于任何法学领域的论文、案例研究、法条和研究方法材料的知识库整理。不替代法律意见、诉状、合同审查或客户法律建议；不把来源线索自动升级为已核验事实。

## 许可证

MIT © 2026 Shawn Deng
