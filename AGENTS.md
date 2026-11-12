# 技能仓库协作规则（所有 agent 必读）

本仓库：legal-academic-research-skills（GitHub：https://github.com/shawndeng321/legal-academic-research-skills），三个技能 `law-paper-writing`、`legal-research-wiki`、`legal-wiki-audit-repair`，当前版本以 `bundle-release.json` 的 `bundle_version` 为准。

仓库位置以当前检出的实际路径为准，可用 `git rev-parse --show-toplevel` 确认；本文件中的仓库内相对路径均以该根目录为基准。命令与配置使用实际路径，不假定桌面目录或旧路径别名（技能更新器会拒绝祖先目录含符号链接的路径）。

适用于 Hermes、Codex、Claude、Devin、Antigravity、DeepSeek 等所有在本机修改法学技能的 agent。

若宿主规则要求读取的上层或本地附加规则实际存在，按宿主的适用范围与优先级一并遵守；不存在 `../AGENTS.md` 不代表仓库缺失，也不据此创建或修改上层规则。

## 1. 只在这里改
- 技能只在本仓库里修改。不得另存私有副本，不得在自己的 workspace 里改完再拷回来。
- 已安装到各宿主（如 `~/.hermes/skills`）的副本只是安装产物，不在那里改。

## 2. 改之前
- 先运行 `git status` 和 `git pull`，确认工作区干净、是最新版本。
- 工作区有别人未提交的改动时，不要覆盖、reset 或丢弃，先停下来告诉用户。

## 3. 每次修改一次提交
- 一项改动一次提交，提交信息写明「agent 名称：改了什么」，例如：`Claude：law-paper-writing 摘要规则补充自查清单`。
- 改动技能内容后：写 CHANGELOG 与 README“本版”说明 → `python3 tools/bump_version.py <版本>` → `python3 tools/prepare_bundle_release.py --write …`（见根 README“开发验证”）→ `--check` → 跑测试。
- 不改写历史：禁止 `git push --force`、`git reset --hard`、`rebase` 已推送的提交。

## 4. 不并行改同一个技能
- 同一时间只有一个 agent 改同一个技能。
- 需要并行时，各开分支：`agent/<名称>-<主题>`，例如 `agent/codex-citation-fix`，完成后由用户决定合并。

## 5. 目录分工（仓库外，按用户实际布局定位）
- 材料目录：论文原稿、老师反馈、引注手册、任务书，**只读**，不得修改或移动。
- 产出目录：报告、草稿、测试记录放入用户指定的仓库外产出位置；按 agent 区分文件，不要放进本仓库。
- 归档目录：旧副本和移交包，只留存，不再修改。
- 上述目录按用户提供的位置或适用的工作区规则定位，不要求与仓库相邻。`materials/`、`outputs/<agent>/`、`_archive/` 只是布局示例；不自动创建、搬迁或删除这些目录，位置不明确时先确认再使用。

## 6. 推送
- 未经用户明确同意，不得 `git push`，不得打 tag 或发布 Release。
