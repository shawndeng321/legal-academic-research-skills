# WIKI-12 规则迁移与瘦身对照

> 两个 SKILL.md 瘦身前后逐条对照；所有被移出的规则均可在新位置找到（WIKI-12 验收：规则清单一一对应）。

## 数据

- `legal-research-wiki/SKILL.md`：23,313 → 17,788 字节（**−23.7%**）
- `legal-wiki-audit-repair/SKILL.md`：32,551 → 22,109 字节（**−32.1%**）
- 目标为各自约三分之一（以不丢规则为准）。研究技能把'入口、核心纪律、路由、验收'全部留在正文后不再深砍；审计技能达到约三分之一。

## 一、legal-research-wiki 迁移明细

| 原正文内容 | 处理 | 去向 |
|---|---|---|
| 双轨隔离 5 条 | 迁移 | `references/dual-track-isolation.md`（正文留摘要 + 链接） |
| 目录树与页面类型说明 | 迁移 | `references/directory-layout-and-page-types.md`（正文留要点） |
| 按材料类型表（读取列参考文件） | 迁移 | `references/material-routing.md`（正文留材料 → 目标页面一览） |
| 页面内容标准 4 类长清单 | 压缩 | 细则在 `content-completeness.md` 与 `assets/templates/` |
| 链接网络 4 条要点 | 压缩 | 细则在 `linking-and-cross-references.md` |
| 易错点 6 条 | 压缩 | 细则在 `pitfalls-and-lessons.md` |
| “多模型与子代理”＋“与用户沟通” | 合并压缩 | 合为“协作、报告与多模型” |
| 核心纪律、每批验收、更新预检、运行环境、适用范围、新建顺序 | 压措辞 | 语义与关键要求（含受测字符串）全部保留 |

## 二、legal-wiki-audit-repair 迁移明细

| 原正文内容 | 处理 | 去向 |
|---|---|---|
| 4.4 Obsidian 真实解析规则 8 条 | 迁移 | `references/obsidian-parsing-details.md` |
| 第六节 模板化与假性图谱检测（6 步） | 迁移 | `references/templating-and-false-graph-detection.md` |
| 第十节 检修流程/迭代/易错点 ＋ 第十一节 巡检增强（4 项） | 迁移 | `references/daily-maintenance-and-periodic-checks.md`（正文留触发、只读纪律、脚本与链接） |
| 第四节 4.1–4.8 判定细节 | 迁移 | `references/technical-health-checklist.md`（正文留检查项一览） |
| 第五节 5.1–5.6 检查细节 | 迁移 | `references/academic-usability-checklist.md`（正文留总则与完成条件） |
| 第十五节 更新技能后的自测 | 迁移 | `daily-maintenance-and-periodic-checks.md` 第四节（正文留 3 行） |
| 第一~三节、第七~九节、第十二~十四节 | 压措辞 | 模式表、分级表、验收清单、批次纪律语义完整保留 |

## 三、受保护关键词（有测试守护）

`P0`—`P3`、`AUDIT_ONLY`／`AUDIT_PLAN`／`REPAIR`／`VERIFY`、`LOG-ROTATE`、`SHA256-DRIFT`、`CONTESTED`、`CLOSED-WORLD`、`RULE-CANDIDATE-XXX`、`OPT-001`、`六维检查`、`&#124;`——均在正文或对应参考文件中保留（`tests/test_wiki12c_skill_slimming.py`）。
