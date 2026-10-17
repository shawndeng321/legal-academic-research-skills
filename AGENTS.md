# 技能仓库协作规则（所有 agent 必读）

本仓库：legal-academic-research-skills（GitHub：https://github.com/shawndeng321/legal-academic-research-skills），三个技能 `law-paper-writing`、`legal-research-wiki`、`legal-wiki-audit-repair`，2026-10-17 时版本为 v2610.14（2610.14.0）。

本机位置：`~/Desktop/legal academic skills/skills/`。旧路径 `~/Desktop/法学Wiki/skill` 现在是指向这里的符号链接，仅为兼容；新的命令和配置请用真实路径（技能更新器会拒绝祖先目录含符号链接的路径）。

适用于 Hermes、Codex、Claude、DeepSeek 等所有在本机修改法学技能的 agent。

## 1. 只在这里改
- 技能只在本仓库里修改。不得另存私有副本，不得在自己的 workspace 里改完再拷回来。
- 已安装到各宿主（如 `~/.hermes/skills`）的副本只是安装产物，不在那里改。

## 2. 改之前
- 先运行 `git status` 和 `git pull`，确认工作区干净、是最新版本。
- 工作区有别人未提交的改动时，不要覆盖、reset 或丢弃，先停下来告诉用户。

## 3. 每次修改一次提交
- 一项改动一次提交，提交信息写明「agent 名称：改了什么」，例如：`Claude：law-paper-writing 摘要规则补充自查清单`。
- 改动技能内容后，按仓库现有流程同步版本号、CHANGELOG 和 `bundle-release.json`，并运行测试。
- 不改写历史：禁止 `git push --force`、`git reset --hard`、`rebase` 已推送的提交。

## 4. 不并行改同一个技能
- 同一时间只有一个 agent 改同一个技能。
- 需要并行时，各开分支：`agent/<名称>-<主题>`，例如 `agent/codex-citation-fix`，完成后由用户决定合并。

## 5. 目录分工（仓库外，同在 `legal academic skills/` 下）
- `../materials/`：论文原稿、老师反馈、引注手册、任务书，**只读**，不得修改或移动。
- `../outputs/<agent>/`：各 agent 的产出（报告、草稿、测试记录）放到自己的文件夹，如 `../outputs/claude/`，不要放进本仓库。
- `../_archive/`：旧副本和移交包，只留存，不再修改。

## 6. 推送
- 未经用户明确同意，不得 `git push`，不得打 tag 或发布 Release。
