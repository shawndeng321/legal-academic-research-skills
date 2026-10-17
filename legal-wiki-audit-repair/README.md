# 法学 Wiki 审计与修复 Skill

对法学研究 Obsidian/LLM Wiki 做全库体检、问题分级、分批整改和复核。它把“发现问题”和“修改页面”分成不同阶段，适合需要保留证据、备份和回滚边界的研究库。

> 运行时入口是 [`SKILL.md`](SKILL.md)。本页提供模式选择、安装和安全使用方式；批量操作细则见 `references/`。
>
> **当前版本：v2610.17（2026-10-17；机器字段 2610.17.0）**。本版：适配 Devin（CLI / Desktop）原生工具映射与按 `Base directory` 绝对路径预检，并精简 SKILL.md；上一版适配 Google Antigravity。前版优化承接：深检扩展为七项（法规范时效 NORM-01～03、案号去重 DUP-01、可选隐私检查 PRIV-01）；新增论文—案例链接同步／扫描／验收与规范依据插入工具组；审计细则迁入本技能；`raw/MANIFEST.md` 豁免 frontmatter 检查。变更见 [CHANGELOG.md](CHANGELOG.md)。

自动检查、四种提示选择、本地修改保护与回滚说明见[根 README 的自动更新章节](../README.md#自动更新)。

## 什么时候使用

- Wiki 出现死链、YAML 错误、字段缺失、标签漂移或图谱断裂。
- 需要批量重命名、编号、链接迁移、反向链接补齐或论文—案例链接同步。
- 需要定期检查页面总数、字段覆盖率和统计口径，但不希望审计过程直接改库。
- 需要对模型提出的修复规则保留 OPT 编号、证据和用户确认记录。

## 四种工作模式

| 模式 | 默认行为 | 适合场景 |
|---|---|---|
| `AUDIT_ONLY` | 只读扫描，不修改页面 | 第一次体检、风险盘点、每日检修 |
| `AUDIT_PLAN` | 输出问题、范围、顺序和验收条件 | 需要先给出整改方案 |
| `REPAIR` | 用户确认后按小批执行修改 | 处理已冻结范围的问题 |
| `VERIFY` | 对修复结果做全量复核 | 关闭 OPT、确认没有新增回归 |

## 核心纪律

- **双轨审计**：技术健康（YAML/来源/死链/图谱/标签）与学术可用性（模板化、假说/事实、论证充分性）分开报告。
- **P0—P3 分级**：P0 代表可能造成原始材料丢失、全库损坏或正式内容大规模错误的问题。
- **小批修复**：默认每批 5—8 页，超过 10 页先征得用户确认；每批完成后再全量验收。
- **备份优先**：批量脚本先 `--dry-run`，写入前由调用方指定备份目录；禁止把旧备份静默覆盖。
- **统计复核**：机器重算与人工口径清单交叉核对，差异逐项归因，不直接改定稿数字。
- **三日迭代**：连续三天执行每日检修后，根据 `log.md` 的重复错误更新检修方法。

## 推荐工作流

```text
AUDIT_ONLY → AUDIT_PLAN → 用户确认范围 → 备份 + DRY_RUN → REPAIR → VERIFY → 追加台账与 log
```

任务提示应明确 Wiki 根目录、只读/写入权限、备份目录和本批页数。例如：

```text
使用 legal-wiki-audit-repair 的 AUDIT_ONLY 模式。只检查指定 Wiki 根目录，输出 YAML、死链、字段覆盖率、
链接对称和统计口径问题；不要修改文件。将问题按 P0—P3 编号，给出证据、范围和验收条件。
```

## 快速安装

本技能属于[法学学术研究技能包](../README.md)，Claude Code、Codex、Hermes、Devin、Google Antigravity 等支持 `SKILL.md` 的宿主通用；完整说明见[根 README 的安装说明](../README.md#安装)。

### Claude Code（插件，一次安装三个技能）

```bash
claude plugin marketplace add shawndeng321/legal-academic-research-skills
claude plugin install legal-academic-research@legal-academic-research
```

### Hermes Skills Hub

```bash
hermes skills install shawndeng321/legal-academic-research-skills/legal-wiki-audit-repair
```

无交互终端加 `--yes`：

```bash
hermes skills install shawndeng321/legal-academic-research-skills/legal-wiki-audit-repair --yes
```

### 其他宿主（源码复制）

复制完整的 `legal-wiki-audit-repair` 目录（连同 `references/`、`scripts/` 和 `agents/`）到宿主的技能目录，例如 `~/.codex/skills/`、`~/.claude/skills/`、`~/.config/devin/skills/`、`~/.gemini/config/skills/`、`~/.hermes/skills/` 或 `~/.agents/skills/`。

## 配套脚本

- `scripts/sync_paper_case_links.py`：把案例页“与论文的关联”同步到论文页（先 `--dry-run`）。
- `scripts/scan_missing_paper_case_links.py`、`scripts/verify_case_link_sections.py`：论文—案例关联的缺漏扫描与章节验收。
- `scripts/insert_norm_sections.py`：按确认范围给概念页插入“规范依据”小节。
- `scripts/multimodal_audit.py`：对指定 Wiki 执行索引、raw 摄入、frontmatter、wikilink、文件卫生、log 与法学专项（法规范时效／案件去重／隐私格式，`--privacy` 可选）七项只读深检。
- `references/batch-operations.md`：批量重命名、编号、链接迁移、反链补齐、论文—案例同步与纯链接核验的安全流程。
- `references/comparison-page-format.md`：跨案比较页格式与链接纪律。
- `references/group-case-stats-extraction.md`：群案统计提取流水线。
- `references/literature-audit-and-repair.md`：文献库语料的四遍审计、引用规范／引用案例精度与分批修复。
- `references/staged-deep-repair.md`：深度修复的子批次划分、书目证据层级与安全修补模式。
- `references/systematic-vault-audit-and-optimization-ledger.md`：全库审计方法论与整改台账协议模板。
- `evals/pressure-tests.md`：15 个评估场景（工作模式与写入权限、证据判断、批量操作、检修与更新、报告），修改核心规则后逐条检查。
- `references/multimodal-reingest-stubs.md`：空壳来源补全边界。
- `references/multimodal-sha256-bulk-fix.md`：raw 提取文本的 SHA256 批量修复方法。
- 每日检修、三日迭代和通用巡检增强纪律直接维护在 `SKILL.md`。

所有会写入 Wiki 的脚本都应先用 `--dry-run` 查看计划；不要直接把整个 Vault 作为目标，也不要使用未经确认的备份路径。

## 与其他技能配合

- 建库与摄入：[legal-research-wiki](../legal-research-wiki/)
- 论文写作：[law-paper-writing](../law-paper-writing/)

## 适用范围与边界

适用于任何法学领域研究 Wiki 的审计、维护和批量修复。不替代法律意见或客户法律服务；对于原始材料、正式稿件和跨库批量修改，始终保留人工确认和可回滚备份。

## 许可证

MIT © 2026 Shawn Deng
