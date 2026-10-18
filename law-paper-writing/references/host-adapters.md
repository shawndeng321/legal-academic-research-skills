# 宿主适配

只读当前宿主那一节。通用规则以各技能 `SKILL.md` 为准，本文件只补路径、工具名与更新渠道。三个技能各带一份，内容一致。

## Claude Code

- 插件安装（基础目录含 `/plugins/cache/`，或位于 `.claude/plugins/` 下；预检结果 `update_channel` 为 `claude-plugin`）：不运行预检，更新由 Claude Code 负责。用户问起更新时，请其运行 `claude plugin marketplace update legal-academic-research` 与 `claude plugin update legal-academic-research@legal-academic-research`，再在会话中运行 `/reload-plugins`。
- 个人技能目录 `~/.claude/skills/` 按普通源码安装处理。

## Google Antigravity

- 路径：全局 `~/.gemini/config/skills/`，工作区 `<workspace>/.agents/skills/`。
- 工具：结构化提问与确认用 `ask_question`；PDF、图片、扫描件用 `view_file` 直接读取；跨多篇文献或法源的只读检索可用 `invoke_subagent` 委派 `research` 子代理，写入由主会话完成；审计技能的周期巡检可配合 `schedule`（`/schedule`）。
- 默认沙盒下预检返回 `offline` 属正常，静默继续；仅当用户明确要求更新技能时才申请网络权限。插件目录安装（`update_channel` 为 `antigravity-plugin`）由插件管理器更新。

## Devin（CLI / Desktop）

- 路径：全局 `~/.config/devin/skills/` 或 `~/.agents/skills/`，项目级 `<workspace>/.devin/skills/` 或 `<workspace>/.agents/skills/`。Devin 也读 `~/.claude/skills/`，同一技能只保留一处安装。
- 命令在工作区目录执行：预检与技能脚本都用加载技能时给出的 `Base directory` 拼绝对路径，如 `python3 -X utf8 "<Base directory>/scripts/legal_skills_update.py" check --json`。
- 工具：提问用 `ask_user_question`（每次至多 4 题、每题 2—4 个选项，五问分两轮）；图片、截图、扫描页用 `read`，PDF、DOCX 用技能脚本抽取文本；只读检索可委派 `subagent_explore`，写入与核验结论由主会话完成；多阶段任务用 `todo_write` 跟踪；`web_search`／`webfetch` 取得的材料先登记来源再使用。

## DeepSeek Harness（DSH）

- 路径：用户级 `~/.dsh/skills/`（DSH 原生用户根，优先），也扫描 `~/.agents/skills/`；项目级 `<workspace>/.dsh/skills/`、`<workspace>/.agents/skills/`。同名技能按扫描根 rank 裁决，`~/.dsh/skills/` 优先于 `~/.agents/skills/`，同一技能只保留一处安装。
- 调用：会话输入 `/law-paper-writing`、`/legal-research-wiki`、`/legal-wiki-audit-repair` 即注入正文；模型侧用 `skill` 工具按名称加载。加载结果会给出技能目录即 `Base directory`，`references/`、`scripts/`、`assets/` 相对路径以它为准。
- 工具：结构化提问用 `ask_user_question`；图片、截图、扫描页用 `read_image` 直接读取；PDF、DOCX 用技能脚本抽取文本；只读检索与并行可委派 `subagent`（需要独立上下文时用 `subagent_fork`），多阶段任务用 `todo_write` 跟踪，批量编排可用 `workflow`；`web_search`／`web_fetch` 取得的材料先登记来源再使用。
- 沙盒：默认 `workspace-write`，只能写会话工作区；写研究库、论文目录或 `~/.dsh/skills/` 前先确认路径并取得授权，必要时请用户在更宽权限下执行。预检在沙盒拒绝写入时静默降级为离线/缓存检查，不打断任务。
- 更新：源码复制安装的 `update_channel` 为 `bundle`。在终端 `git pull` 后重新复制三个完整目录（含 `references/`、`scripts/`、`assets/`、`agents/`）；经用户明确同意并放宽权限时也可运行 `apply`。不要只替换 `SKILL.md`；更新后新建会话重载。

## Hermes、Codex 与其他宿主

- 用宿主自带的读写、命令与子任务工具；不支持子代理时按小批次串行。
- Hermes 可能把技能分放在不同分类子目录下，跨技能引用按技能名查找。
