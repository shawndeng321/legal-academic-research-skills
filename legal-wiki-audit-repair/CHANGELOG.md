# 更新记录

自 v2610.9 起，三个技能同步按日期发布：公开标签 `vYYMM.D`，机器字段 `YYMM.D.N`；同日追加版递增 N，历史编号保留。变更同时更新 SKILL、锁、清单与当前 README。此规则不改变论文稿件版本。

## v2610.17（2026-10-17；机器字段 2610.17.0）

- 适配 Devin（CLI / Desktop）：新增 Devin 原生能力映射（`ask_user_question`、`read`、`subagent_explore`、`todo_write`），说明 Devin 全局与项目技能路径及其自动读取 `~/.claude/skills` 带来的重复安装风险。
- 预检与脚本在 Devin 下按技能 `Base directory` 拼绝对路径运行，同一会话只预检一次。
- SKILL.md 精简（写作 −36%／建库 −16%／审计 −20%），宿主专属说明移入 references/host-adapters.md。
- 预检对所有宿主改为同一会话只运行一次；check --json 不再输出完整清单与历史（约 28 KB → 不足 1 KB）。
- 深检脚本细则迁入 technical-health-checklist.md；合并重复验收清单；删除开发者自测节（见 daily-maintenance-and-periodic-checks.md 第四节）。
- 锁与发布清单随技能包统一升级至 2610.17.0。

## v2610.16（2026-10-16；机器字段 2610.16.0）

- 适配 Google Antigravity 原生环境：原生支持 `ask_question`、`schedule` 工具映射；识别 Antigravity 全局与工作区技能路径。
- 修复更新预检在沙盒无写入/外网权限时抛出 `PermissionError` 的问题，优雅降级为离线安全检查。
- 锁与发布清单随技能包统一升级至 2610.16.0。

## v2610.14（2026-10-14；机器字段 2610.14.0）

- 深检重构与扩展（`multimodal_audit.py`）：真实 YAML 解析、全路径身份、全 raw 扫描、中文报告、退出码与 `--json`／`--strict` 契约；检查扩展为七项，新增法学专项——NORM-01～03（法规范效力状态与核验日期、失效引用）、DUP-01（案号规范化去重）、PRIV-01（可选隐私格式检查，默认关闭、命中打码）。
- 论文—案例链接工具组：`sync_paper_case_links.py`（`--plan`、`--dry-run` 预演 diff、哈希核对、备份、只追加）、`scan_missing_paper_case_links.py`、`verify_case_link_sections.py`（验收）；共享 `case_link_utils.py` 统一章节／字数／关系口径；`insert_norm_sections.py` 规范依据增补（幂等、备份）。
- 规则与保护：统一只读／日志／持续授权口径（模式表、每日检修日志门控、REPAIR 小批推进）；`raw/MANIFEST.md` 豁免提取物 frontmatter 检查。
- 文档：三份审计细则参考迁入本技能；全部参考文档中文化；`SKILL.md` 瘦身约 32.1%（规则原样迁入新参考）。
- 评估：新增行为评估记录规范（输入／产物差异／判定／证据）与运行记录。

## v2610.9（2026-10-09；机器字段 2610.9.0）

- 与写作技能同步日期版；写作技能活动名称改为 `law-paper-writing`，跨技能引用及安装入口同步。
- 保留本技能的建库/审计范围、闭世界来源纪律与原有全部业务能力。
- 更新器新增历史版本排序、旧名原位迁移、独立确认、备份和失败回滚测试；旧更新器不能透明识别新名称清单，迁移说明见技能包 README。
- 从本版开始公开标签采用 `vYYMM.D`，三技能统一机器版本 `YYMM.D.N`；历史版本记录不改写。

## 5.0.1（2026-09-28）

- 仓库更名为 `shawndeng321/legal-academic-research-skills`：更新器的清单地址与 README 中的安装命令随之更新。旧地址由 GitHub 自动跳转，已安装的用户不受影响。

## 5.0.0（2026-09-25）

- `SKILL.md` 通用化：移除特定项目的基线计数（页数、标签数、样本数、哈希文件数）和案例编号；每日检修改为对照台账中记录的本项目基线；检修脚本不再依赖某一宿主的固定路径，可用系统定时任务运行。
- 不再要求宿主提供 `llm-wiki`、`obsidian` 等外部技能；本技能自足。
- `references/batch-operations.md` 重写为通用流程；**更正**表格内别名链接写法为 `[[目标\|别名]]`（旧版该文件一处仍推荐 `&#124;`，与已验证规则矛盾）。
- 删除 `paper-case-theme-mapping.md` 与 `pure-link-verification.md`（均为单一项目的数据清单），其通用方法并入 `batch-operations.md` 第六节。
- `group-case-stats-extraction.md`、`comparison-page-format.md` 通用化。
- 脚本：移除示例中的真实作者与论文名；默认备份目录去掉日期后缀；`verify_case_link_sections.py` 的说明行检查改为宽松匹配。
- 技能包更新器识别 Claude Code 插件安装：`check` 输出 `update_channel`，并拒绝对插件目录执行 `apply`。
- 预检与示例命令改为 `python3`（Windows 用 `py`）；macOS 默认没有 `python` 命令。
- 兼容性：`description` 改为“英文开头句 + 中文触发词”（约 200—240 字符，Codex 与 Hermes 上限均为 1024）。开头一句不超过 57 字符，因为 Hermes 在系统提示的技能目录中只显示前 57 个字符；后半部分的中文触发词供 Claude Code、Codex 自动选用；Claude Code 插件安装时跳过更新预检，不再每次加载都弹出命令权限确认。
- 死链验收口径写明：`drafts/` 链接为容忍类，正式内容页死链为零即通过。
- 新增 `evals/pressure-tests.md`：15 个行为评估场景（工作模式与写入权限、证据判断、批量操作、检修与更新、报告）。
- 新增“配套技能”一节：写明用到其他两个技能的哪些内容，以及未安装时如何处理；跨技能引用改为按技能名查找，不再使用 `../../其他技能/` 相对链接（Hermes 等宿主可能把技能分放在不同子目录，相对链接会失效）。
- 技能包更新器支持分目录安装：按技能名在技能根目录或一层分类子目录（如 Hermes 的 `research/`）中定位各技能，原地备份、更新与回滚；同一技能装了两份时停止并报告。

## 4.3.0（2026-08）

技能包按需更新路由；multimodal-wiki 六项深检；每日检修与三日迭代。
