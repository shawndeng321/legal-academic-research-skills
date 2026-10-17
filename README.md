# 法学学术研究技能包（Legal Academic Research Skills）

面向中国法学学术研究的三项 AI Skill：把论文、案例和法条整理成来源可追溯的研究 Wiki，对研究库做审计与安全修复，再把研究证据转化为可核验的期刊论文工作稿。适用于任何部门法与研究主题，不绑定特定项目。

> 本技能包 Hermes、Claude Code 与 Codex 通用，也可用于其他支持标准 `SKILL.md` 的代理宿主（如 DeepSeek Harness）。技能正文只保留一份：运行时元数据分别放在 `SKILL.md`（通用 frontmatter）、`agents/openai.yaml`（Codex）与 `.claude-plugin/`（Claude Code 插件）中。

[快速选择](#先从这里开始) · [更新内容](#2026-10-更新内容) · [安装](#安装) · [自动更新](#自动更新) · [验证](#验证与排错)

<p align="center">
  <img src="law-paper-writing/assets/readme/paper-banner.jpg" alt="法学学术研究、知识库审计与论文写作技能包" width="100%">
</p>

## 先从这里开始

| 你的目标 | 先使用 | 你会得到 |
|---|---|---|
| 建立或扩充法学研究 Wiki | [`legal-research-wiki`](legal-research-wiki/) | 有范围、有来源、有质量门禁的论文/案例/法条知识库 |
| 检查并修复已有 Wiki | [`legal-wiki-audit-repair`](legal-wiki-audit-repair/) | 只读审计、P0—P3 台账、小批修复与全量复核 |
| 从选题写到投稿工作稿 | [`law-paper-writing`](law-paper-writing/) | 研究问题—论证—证据—引注链、期刊适配与 DOCX 工作稿 |

常见顺序：`law-paper-writing` 先用五问收窄研究问题 → `legal-research-wiki` 组织材料 → `legal-wiki-audit-repair` 定期体检与修复 → 回到写作技能起草和终检。只做其中一项时，可以直接进入对应技能。

## 技能一览

| 技能 | 版本 | 适合什么时候用 | 核心能力 |
|---|---:|---|---|
| [`law-paper-writing`](law-paper-writing/) | **v2610.17** | 选题、研究、起草、修订、审核或期刊适配 | 七种任务模式、五项硬门禁、按命题类型检查论证、正文表达与作者声音、材料边界、实证材料细则、期刊适配、DOCX 真实脚注 |
| [`legal-research-wiki`](legal-research-wiki/) | **v2610.17** | 新建、扩充或重新整理研究库 | 研究思路先行、范围优先摄入、PDF/DOCX/图片/音频摄入、法规范分层、论文—案例双轨关联、研究设计层、六维质量门禁、闭世界查询 |
| [`legal-wiki-audit-repair`](legal-wiki-audit-repair/) | **v2610.17** | 已有 Wiki 出现死链、字段缺失、批量操作或技能包更新需求 | AUDIT_ONLY、P0—P3 分级、备份/DRY_RUN、小批修复、模板化检测、每日检修与迭代、七项深检脚本（含法学专项） |

## 2026-10 更新内容

> **v2610.17（2026-10-17；机器字段 2610.17.0）**：适配 Devin（CLI / Desktop）：三技能新增 Devin 原生能力映射（`ask_user_question`、`read`、`subagent_explore`、`todo_write`）；预检与脚本按技能 `Base directory` 拼绝对路径、同一会话只预检一次；说明 Devin 技能路径及其自动读取 `~/.claude/skills` 带来的重复安装风险；三技能 SKILL.md 精简（宿主说明外移、预检同会话去重、check 输出瘦身），写作技能移除旧版上游并入说明。
>
> **v2610.16（2026-10-16；机器字段 2610.16.0）**：全套适配 Google Antigravity 原生环境（`view_file`、`ask_question`、`invoke_subagent`、`schedule` 原生工具映射；Antigravity 全局与工作区技能路径识别；修复沙盒限制下更新预检锁权限报错并优雅降级为离线安全检查；清理旧版命名冲突）。
>
> **v2610.14（2026-10-14；机器字段 2610.14.0）**：三技能批量优化——深检扩展为七项（法规范时效 NORM、案号去重 DUP、可选隐私检查 PRIV）；新增论文—案例链接同步／扫描／验收工具组；任务入口五种路由、首批材料按研究类型；新增“证据最小记录”；参考文档全中文化与 SKILL 精简（建库 −23.7%、审计 −32.1%）；发布面清理（项目专属词表移入本机文件、`raw/MANIFEST.md` 豁免）。本版承接 v2610.9 的更名与上游并入（迁移见下文“一次性升级”）。

详细变更见各技能 `CHANGELOG.md`；本批逐项记录见 [`docs/法学Wiki技能优化-执行记录.md`](docs/法学Wiki技能优化-执行记录.md)。

## 2026-09 更新内容

> 2026-09-28：仓库由 `hermes-obsidian-legal-cssci-wiki-writing-skills` 更名为 `legal-academic-research-skills`。旧地址会自动跳转，已安装的用户无需操作；新安装请使用新地址。

本次发布把技能包从“为一个研究项目迭代出来的工具”改成**通用的法学学术研究技能包**，并同步了 [VictorTran1023/law-paper-writing-skill](https://github.com/VictorTran1023/law-paper-writing-skill) 的最新写作方法。

### 通用化

- **去除项目专属内容**：删除特定研究项目的案例编号、样本数量、分类方案、分析框架、标签词表、期刊格式实测值、作者名单、本机路径与个人信息；可复用的做法改写为“先问用途，再按项目设计”的通用流程，示例一律使用合成材料。
- **结构精简**：`legal-research-wiki` 的 `SKILL.md` 由约 107 KB 精简为约 16 KB；20 份会话记录合并为 5 份按主题组织的参考文件；审计技能中两份单一项目数据清单删除，方法并入批量操作手册。
- **规则更正**：表格内别名链接统一为 `[[目标\|别名]]`（旧批量操作手册一处仍推荐 `&#124;`，与已验证规则矛盾）；司法解释与规章关系改为审慎表述。

### 写作技能同步 Victor 1.2.0-rc.1

- 按命题类型检查理由（案例归纳、现行法解释、制度评价、制度建议、概念分析、统计表述），允许先提出判断再证明；
- 正文表达与作者声音（`legal-prose.md`）及合成改写示例；需求拆解（五问）；论证诊断与审稿反馈落实表；
- 保留本技能包原有的 DOCX 真实脚注与修改标注版、note-level 溯源、技能包自动更新；五问展开提示、实证与群案材料细则、期刊风格观察卡由原规则通用化而来。

### 三宿主通用

- **Claude Code 插件**：仓库根目录提供 `.claude-plugin/plugin.json` 与 `marketplace.json`，一条命令安装三个技能（已用 `claude plugin validate` 校验并实测安装）。
- **宿主中立的运行说明**：每个 `SKILL.md` 增加“运行环境”一节，相对路径以技能目录为基准解析、不绑定宿主工具名、不写死 `/tmp`；多模态和多模型编排参考文件给出 Hermes / Claude Code / Codex 的能力对照。原 `dsh/dsh-compatibility` 分支的适配思路由此并入主线。
- **更新器识别插件安装**：`check` 输出 `update_channel`；Claude Code 插件安装走 `claude plugin update`，更新器不会写入插件目录。
- **自动选用更可靠**：三个技能的描述改为中英双语并含中文触发词（如“改稿”“建库”“摄入”“每日检修”），用中文提出任务时 Claude Code 与 Codex 更容易自动调用对应技能；插件安装时跳过更新预检，避免每次加载弹出命令权限确认。
- **建库模板**：`legal-research-wiki/assets/templates/` 提供 20 个页面模板（SCHEMA、案例、论文、概念、比较、法规范及时序版本、研究设计、交接页等），以实际运行的法学研究库为蓝本通用化。
- **建库访谈**：建库或加深已有研究库前，代理按十组问题（目的、研究问题、将来怎么用、材料、深度、组织、关联、时间维度、质量与边界、维护与协作）分批提问，整理成《Wiki 设计书》，确认后再建库。
- **评估场景**：三个技能都有行为评估场景（`evals/pressure-tests.md`），修改核心规则后逐条检查。
- **单独安装也能用**：每个技能写明用到了其他技能的哪些内容、未安装时如何处理；跨技能引用按技能名查找，不依赖三个技能在同一目录。
- **按原生多模态模型精简**：模型直接读图片和扫描件，不再保留“模型不支持看图”时的检查与分工；音频仍通过转录处理。
- **找回本地改进**：知识库与论文写作双轨隔离、论文草稿新版本同步、法规范时序版本与历史案件两层评价，此前只存在于作者本机，现已通用化并入。
- **Python 3.9+ 即可**：macOS 自带的 `python3` 就能运行全部脚本与测试；技能中的命令统一写作 `python3`（Windows 用 `py`）。

详细变更见各技能的 `CHANGELOG.md`；历史设计与实施记录见 [`docs/superpowers/`](docs/superpowers/)。

## 安装

三个技能一起使用效果最好，也可以只装其中一个。无论哪种方式，都要安装**完整技能目录**（`references/`、`scripts/`、`assets/`、`agents/` 一并保留），不要只复制单个 `SKILL.md`。

### Claude Code

在终端运行（或在 Claude Code 会话中把 `claude plugin` 换成 `/plugin`）：

```bash
claude plugin marketplace add shawndeng321/legal-academic-research-skills
claude plugin install legal-academic-research@legal-academic-research
```

安装后新建会话，或在当前会话运行 `/reload-plugins`。更新：

```bash
claude plugin marketplace update legal-academic-research
claude plugin update legal-academic-research@legal-academic-research
```

也可以不用插件，按下文“源码安装”把三个目录复制到 `~/.claude/skills/`（个人）或项目内的 `.claude/skills/`（仅该项目）。

### Hermes Skills Hub

三个技能需要分别安装：

```bash
hermes skills install shawndeng321/legal-academic-research-skills/law-paper-writing
hermes skills install shawndeng321/legal-academic-research-skills/legal-research-wiki
hermes skills install shawndeng321/legal-academic-research-skills/legal-wiki-audit-repair
```

脚本或 CI 环境加 `--yes`：

```bash
hermes skills install shawndeng321/legal-academic-research-skills/law-paper-writing --yes
hermes skills install shawndeng321/legal-academic-research-skills/legal-research-wiki --yes
hermes skills install shawndeng321/legal-academic-research-skills/legal-wiki-audit-repair --yes
```

安装后运行 `hermes skills list`，确认三个技能均为 `enabled`。不要把仓库根 URL 或单个 `SKILL.md` 当成完整安装入口。

### 源码安装（Codex / Hermes / Claude Code / 其他宿主）

需要本地审查、离线安装或固定版本时，从 `main` 克隆仓库，再复制完整技能目录到目标宿主的技能目录。

macOS / Linux：

```bash
checkout="$(mktemp -d)/legal-skills"
git clone --branch main https://github.com/shawndeng321/legal-academic-research-skills.git "$checkout"

# 选择目标目录（任选其一）：
target="$HOME/.gemini/config/skills"  # Google Antigravity 全局技能（或 <workspace>/.agents/skills）
# target="$HOME/.config/devin/skills"  # Devin（或 ~/.agents/skills；Devin 也读 ~/.claude/skills，只装一处）
# target="$HOME/.codex/skills"        # Codex
# target="$HOME/.claude/skills"       # Claude Code（个人）
# target="${HERMES_HOME:-$HOME/.hermes}/skills"   # Hermes
# target="$HOME/.agents/skills"       # 其他扫描 ~/.agents/skills 的宿主（如 DeepSeek Harness）

mkdir -p "$target"
for s in law-paper-writing legal-research-wiki legal-wiki-audit-repair; do
  cp -R "$checkout/$s" "$target/$s"
done
```

Windows（PowerShell），使用一个空的临时目录：

```powershell
$checkout = Join-Path $env:TEMP 'legal-academic-research-skills'
git clone --branch main https://github.com/shawndeng321/legal-academic-research-skills.git $checkout
```

Codex：

```powershell
$codexSkills = Join-Path $HOME '.codex\skills'
New-Item -ItemType Directory -Force $codexSkills | Out-Null
Copy-Item -Recurse -Force "$checkout\law-paper-writing" (Join-Path $codexSkills 'law-paper-writing')
Copy-Item -Recurse -Force "$checkout\legal-research-wiki" (Join-Path $codexSkills 'legal-research-wiki')
Copy-Item -Recurse -Force "$checkout\legal-wiki-audit-repair" (Join-Path $codexSkills 'legal-wiki-audit-repair')
```

Hermes：

```powershell
$hermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA 'hermes' }
$hermesSkills = Join-Path $hermesHome 'skills'
New-Item -ItemType Directory -Force $hermesSkills | Out-Null
Copy-Item -Recurse -Force "$checkout\law-paper-writing" (Join-Path $hermesSkills 'law-paper-writing')
Copy-Item -Recurse -Force "$checkout\legal-research-wiki" (Join-Path $hermesSkills 'legal-research-wiki')
Copy-Item -Recurse -Force "$checkout\legal-wiki-audit-repair" (Join-Path $hermesSkills 'legal-wiki-audit-repair')
hermes skills list --source local --enabled-only
```

Claude Code 或其他宿主：把上面的目标目录换成 `Join-Path $HOME '.claude\skills'` 或 `Join-Path $HOME '.agents\skills'`。

复制安装不要放在 Git 工作树里（自动更新器会拒绝 Git 工作树安装，此时请用 `git pull` 更新源码）。

### 使用方式

安装后在新会话中直接说明要用哪个技能和做什么，例如：

```text
使用 legal-research-wiki。只读取 ~/research/某某研究项目 目录，先检查 SCHEMA.md、index.md 和 log.md，
提出本批 5—8 页的摄入计划。不要扫描其他目录，不要写回任何文件。
```

Claude Code 中也可以用 `/law-paper-writing` 等斜杠命令直接调用；Codex 中可用 `$law-paper-writing`。

## 自动更新

Bundle `1.0.0` 起，三个法学 Skill 作为一个整体检查和更新（Claude Code 插件安装除外，见下）。Agent 每次首次使用其中任一 Skill 时都会调用更新检查，但网络请求最多 **每 6 小时**一次；其余加载直接使用缓存。它不是开机自启程序，也没有后台守护进程。需要立即重新检查时，对 Agent 说“**检查法学技能更新**”，它会绕过缓存执行强制检查。

只有检测到更高 Bundle 版本时，Agent 才展示以下四个选择：

```text
[立即更新] [查看更新说明] [稍后提醒] [忽略此版本]
```

- **立即更新**：仍需用户明确确认；不会静默运行 `apply`。
- **查看更新说明**：只显示累计变更、本地差异和版本，不写入文件。
- **稍后提醒**：暂停提示 4 小时，期间不重复联网。
- **忽略此版本**：只忽略当前 Bundle；出现更高版本时会重新提示。

更新范围固定为 `law-paper-writing`、`legal-research-wiki`、`legal-wiki-audit-repair`，不会顺带更新其他 Skill。自动更新器只读取这三个 Skill 目录、自己的状态目录和 GitHub 官方仓库的 HTTPS 发布清单/源码包；它不读取或修改论文、研究 Wiki、Obsidian Vault 等用户研究文件。下载包在写入前必须通过路径、清单、版本和 SHA256 校验。

### 三种安装方式

- **Claude Code 插件**：`check` 返回 `update_channel: claude-plugin`。Agent 只提示有新版本，并请你运行 `claude plugin marketplace update legal-academic-research` 与 `claude plugin update legal-academic-research@legal-academic-research`；更新器不会写入插件目录。

- **Hermes Skills Hub**：Agent 校验 Hub lock 中三个目标 Skill 的共同 GitHub 来源，完整备份三个目录和 lock，再逐个调用 `hermes skills update <skill-name>`。不会调用裸的全量更新命令，也不会覆盖无关 Skill 的 lock 条目。
- **Codex / Claude Code 技能目录 / 源码复制**：三个技能可以在同一目录，也可以分放在一层分类子目录中（如 Hermes 的 `research/`），更新器按技能名定位并原地更新；Agent 先把三个新版目录放到与安装目录相同的文件系统，完整备份旧目录，再作为一个事务替换。Git 工作树或符号链接安装会被拒绝，需改用 Git 更新源码。

发现本地修改、新增、删除、缺失 Skill 或无法验证的文件时，更新器只返回差异报告；覆盖本地修改和安装缺失项是两个独立确认。备份默认位于 Windows 的 `%LOCALAPPDATA%\hermes-legal-research-skills\backups\`，其他系统位于 `$XDG_STATE_HOME/hermes-legal-research-skills/backups/`（未设置时使用 `~/.local/state/...`）。任一步失败都会自动回滚三个 Skill；若 Hermes 的无关 lock 条目在事务中同时变化，则保留前后两份 lock 并要求人工恢复。

更新成功后，请**新建一个 Agent 任务**，让运行时重新加载新版 `SKILL.md`。

### 一次性升级

在 Bundle `1.0.0` 之前安装的旧版本没有清单和包锁，需要先做一次性升级：

- Hermes Hub 用户分别运行以下三个官方更新命令：

```bash
hermes skills update law-paper-writing
hermes skills update legal-research-wiki
hermes skills update legal-wiki-audit-repair
```

- Codex 或源码复制用户重新克隆 `main`，再按安装章节复制三个完整目录。

完成后确认三个目录都包含 `bundle-lock.json` 和 `scripts/legal_skills_update.py`，后续即可使用统一更新。

**分目录安装的用户（Bundle 1.0.0 → 2026.0925.0 这一次需手动升级）**：有些宿主会把技能分放在分类子目录中，例如 Hermes 本地安装时写作技能在 `~/.hermes/skills/`，另两个在 `~/.hermes/skills/research/`。1.0.0 的更新器只认“三个技能在同一目录”，处理不了这种布局。这一次请先备份旧目录，再把新版三个目录分别复制到原来的位置（不要在根目录另装一份，否则会出现同名重复技能）。2026.0925.0 起更新器会按技能名定位各自的安装目录（根目录或一层分类子目录），原地更新；发现同一技能装了两份时会停止并报告。

**写作技能更名（v2610.9；已安装用户这一次需要一次性引导）**：写作技能正式名称由 `chinese-law-paper-writing` 改为 `law-paper-writing`，三个技能一起改为日期版本。旧版更新器无法识别新名称的发布清单（会直接拒绝），所以这次更新不能全自动完成；请对号入座引导一次，完成后恢复正常的自动检查与更新：

- **源码复制安装**：让 Agent 从本仓库取新版 `scripts/legal_skills_update.py`，把新版三个技能目录暂存到与安装位置同一磁盘、且不含符号链接的目录，用**新版**脚本对新版暂存包运行 `apply`（用户确认后加 `--allow-local-changes`）。旧名目录会在原位置就地改名并更新，迁移前完整备份、失败自动回滚。
- **Hermes Skills Hub 里登记的还是旧名**：更新器会拒绝写入并返回 `migration_required`；请先按 Hermes 支持的方式卸载旧名、重新安装 `law-paper-writing`（或按提示先显式转为非托管源码安装），然后再执行更新。不要删除 Hub 记录，也不要用旧名的 `hermes skills update` 当作已完成改名。
- **Claude Code 插件安装**：运行 `claude plugin marketplace update legal-academic-research` 和 `claude plugin update legal-academic-research@legal-academic-research` 即可；插件方式不涉及目录改名迁移。

### 检查与开发命令

先解析实际安装根目录，不依赖当前工作目录。下面优先使用 Codex 安装；如果不存在，再使用 Hermes 本地目录：

```powershell
$codexSkills = Join-Path $HOME '.codex\skills'
$hermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA 'hermes' }
$hermesSkills = Join-Path $hermesHome 'skills'
$skillsRoot = if (Test-Path (Join-Path $codexSkills 'law-paper-writing')) { $codexSkills } else { $hermesSkills }
$updater = Join-Path $skillsRoot 'law-paper-writing\scripts\legal_skills_update.py'
```

```powershell
# 自动检查 / 手动强制检查
python -X utf8 $updater check --json
python -X utf8 $updater check --force --json

# 更新说明、稍后提醒、忽略指定 Bundle 版本
python -X utf8 $updater details --json
python -X utf8 $updater snooze --hours 4 --json
python -X utf8 $updater ignore 1.1.0 --json
```

`diff` 和源码复制模式的 `apply` 只应由 Agent 在下载、解压和校验暂存 Bundle 后调用；不要把未经验证的目录传给它们。以下命令展示接口形状，其中路径必须是绝对路径且不含符号链接——macOS 的 `$TMPDIR`（`/var/folders/...`）和 `/tmp` 都是系统符号链接，先解析为真实路径再使用（如 `cd "$TMPDIR" && pwd -P`），否则更新器会以 `contains a symlink` 拒绝：

```powershell
python -X utf8 $updater diff --skills-root $skillsRoot --staged-root $stagedRoot --manifest $manifestPath --state-root $stateRoot --json

# 用户明确确认覆盖本地修改后；缺失 Skill 还需单独增加 --install-missing
python -X utf8 $updater apply --skills-root $skillsRoot --staged-root $stagedRoot --manifest $manifestPath --state-root $stateRoot --allow-local-changes --json
```

## 三分钟工作流

```text
1. PLAN       用 law-paper-writing 的五问收窄主问题、范围和交付物
2. RESEARCH   用 legal-research-wiki 建研究设计、来源登记和 Wiki 结构
3. AUDIT      用 legal-wiki-audit-repair 只读体检，建立 P0—P3 台账
4. REPAIR     用户确认范围后按 5—8 页小批修复，先备份再写入
5. DRAFT      回到写作技能起草，同步设置脚注标识
6. AUDIT      终检引注、法律版本、匿名信息和目标期刊正式要求
```

## 验证与排错

### 安装验证

- Claude Code：`claude plugin details legal-academic-research@legal-academic-research` 应列出 3 个技能；会话中可用 `/law-paper-writing` 等命令调用。
- Hermes：`hermes skills list --source local --enabled-only` 或 `hermes skills list`。
- Codex：新建任务后直接要求使用对应技能；技能目录必须包含 `SKILL.md` 和 `agents/openai.yaml`。
- 远程 Hub 因网络探测超时时，改用“源码安装”，不要重复下载单个 `SKILL.md`。

### 开发验证

先安装开发依赖（Python 3.9+）：

```bash
python3 -m pip install -r requirements-dev.txt
```

每次发布都要求兼容性、脚本安全与 Bundle 更新器测试全部通过：

```bash
python3 -X utf8 -m unittest discover -s tests -v
```

未安装开发依赖时，依赖相关测试会以“跳过”（`skipped`，附原因）列出，不计入通过；发布校验必须在依赖齐全的环境中运行。

Claude Code 插件清单校验：

```bash
claude plugin validate .
claude plugin validate .claude-plugin/plugin.json
```

Codex 技能校验：

```powershell
$validator = "$HOME\.codex\skills\.system\skill-creator\scripts\quick_validate.py"
python -X utf8 $validator law-paper-writing
python -X utf8 $validator legal-research-wiki
python -X utf8 $validator legal-wiki-audit-repair
```

修改任何技能文件后，用 `python3 tools/prepare_bundle_release.py --write --bundle-version X.Y.Z --published-at <ISO时间> --update-level <级别> --summary "<摘要>" --change "<变更>"` 重新生成 `bundle-release.json` 与各技能的 `bundle-lock.json`，再运行 `python3 tools/prepare_bundle_release.py --check` 确认指纹一致；同时更新 `.claude-plugin/plugin.json` 的 `version`。

## 目录结构

```text
README.md                    # 总入口、安装、更新内容和验证
requirements-dev.txt         # 开发、测试与发布校验依赖
.claude-plugin/              # Claude Code 插件与 marketplace 清单
law-paper-writing/           # 论文写作与投稿工作稿
legal-research-wiki/         # 研究 Wiki 建库与摄入
legal-wiki-audit-repair/     # Wiki 审计、批量修复与复核
bundle-release.json          # 技能包发布清单（自动更新读取）
tools/                        # 发布清单生成与校验
docs/superpowers/             # 设计与实施记录
tests/                        # 兼容性、脚本安全、深检/链接解析与更新器回归测试
```

## 运行前提与边界

- Hermes Agent、Claude Code、OpenAI Codex 或其他支持标准 `SKILL.md` 的宿主。
- Python 3.9+（macOS 自带的 `python3` 即可；技能包更新器、各脚本、发布工具与测试均兼容 3.9）；DOCX 脚注脚本需要 `python-docx` 与 `lxml`；PDF 文字提取按需安装 `pymupdf`；七项深检脚本（multimodal_audit）需要 `PyYAML`（见 `requirements-dev.txt`）；扫描件与图片由模型直接读取。
- 默认不扫描整个 Obsidian Vault，也不写回用户资料；只有用户明确授权并指定目标文件后才允许修改。
- 不编造法条、案号、页码、期刊规则或统计数字；资料不完整时必须保留待核状态。
- 不适用于合同、诉状、法律意见书、客户法律建议、学位论文或声称保证录用的内容。

## 致谢与来源

- 写作技能的 6.x 版本线合并了 [VictorTran1023/law-paper-writing-skill](https://github.com/VictorTran1023/law-paper-writing-skill)（MIT）的写作方法，初始方法源于《关于中国法学类CSSCI期刊发表论文的写作过程与方法》；
- 多模态摄入与 note-level 溯源来自 [kigner/multimodal-wiki](https://github.com/kigner/multimodal-wiki) v1.0.0；深检脚本源自其六项结构检查，本包扩展为七项（增法学专项）并按法学研究适配。

## 版本与许可证

三个技能与技能包统一按发布日期编号，不再使用 v6、v7 等能力代际编号。公开标签格式为 `vYYMM.D`，例如 **v2610.9** 表示 2026 年 10 月 9 日；同日追加发布用 `v2610.9.1`、`v2610.9.2`。为了保留宿主和更新器的三段数字契约，`metadata.version`、插件版本与 `bundle_version` 统一使用 `YYMM.D.当天序号`，首版为 `2610.9.0`。这里的三段是日期与当天序号，不是主、次、修订版本。历史发布记录中的旧版本号原样保留；论文稿件的版本由作者决定，不跟随技能包日期版。

MIT。`law-paper-writing` © VictorTran1023 与 Shawn Deng；其余 © 2026 Shawn Deng。本项目不是 Hermes、Anthropic、OpenAI、Obsidian、CSSCI 期刊或其他机构的官方指南、认证或录用承诺。
