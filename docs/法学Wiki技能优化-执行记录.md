# 法学 Wiki 技能优化执行记录

- 任务书：《法学Wiki技能优化任务书_合并版_v2610.9》（档案位于仓库之外，由作者保存）
- 审阅基线：`84dab856e2560fae3ae36e8ec60e0854c2fc90d7`（release/v2610.9，2026-10-09；工作开始前已核对无漂移）
- 工作分支：`work/wiki-audit-v2610.9`（本地开发；按任务书铁律，不执行 `git push`）
- 记录纪律：只含相对路径与合成样例；不含本机绝对路径、密钥或用户研究数据；每项任务随做随记，每批收尾附批次小结。

## WIKI-09 测试环境可复现

- 状态：已完成
- 实施提交：`aa98c37`
- 修改文件：
  - `requirements-dev.txt`（新增；PyYAML、python-docx、lxml；pymupdf 标注可选）
  - `tests/test_writing_upstream_integration.py`、`tests/test_docx_footnotes.py`、`tests/test_skill_compatibility.py`（缺依赖改为显式跳过并附原因，不再模块导入失败）
  - `README.md`（开发验证：安装步骤、跳过说明、目录结构）
- 原问题与复现样例：macOS 自带 Python 3.9.6、未装依赖时 `Ran 111 … FAILED (errors=3, skipped=1)`，三个模块共 36 项未运行。
- 实际改动：见上；跳过项单列、不计为通过；发布校验仍要求在依赖齐全环境运行。
- 验收命令或评估场景：仓库根目录 `python3 -X utf8 -m unittest discover -s tests`（无依赖）；同一命令在装有 `requirements-dev.txt` 的 venv（Python 3.9.6 + PyYAML 6.0.3 + python-docx 1.2.0）。
- 实际结果：通过。无依赖 `Ran 147 tests … OK (skipped=48)`（0 导入错误）；依赖齐全 `Ran 147 tests … OK`。
- 兼容性与恢复验证：不涉及写入路径与数据迁移。
- 剩余问题：可选的 GitHub Actions（Python 3.9 与最新版双跑）未实施，须所有者另行同意。

## WIKI-01 深检脚本重构

- 状态：已完成
- 实施提交：`83d4720`
- 修改文件：
  - `legal-wiki-audit-repair/scripts/multimodal_audit.py`（整体重构）
  - `legal-wiki-audit-repair/scripts/wiki_links.py`（新增：共享链接解析与解析规则）
  - `tests/test_multimodal_audit_scan.py`（新增 12 项回归）
  - `tests/test_wiki_links.py`（新增 14 项）
  - `tests/test_script_safety.py`（深检测试加 PyYAML 跳过护栏；断言随中文报告更新）
  - `legal-wiki-audit-repair/SKILL.md`、`README.md`（脚本说明与运行前提同步）
- 原问题与复现样例（对照任务书；均已由新回归测试覆盖）：
  - 缺右括号的 YAML 被报“valid frontmatter”；
  - 两个子目录的同名页只计 1 页；
  - `raw/cases/`、`raw/法规范/` 不计入原始文件数（旧为硬编码目录白名单）；
  - 零出站页面被“All pages ≥2 outbound links”掩盖；
  - 存在阻断发现时退出码仍为 0；
  - 多行缩进 YAML 标签列表被解析为空字符串、误报缺标签。
- 实际改动：
  - 真实 YAML 解析（检查字段类型、空值与重复键；解析失败单列并注明该页其余检查未执行）；
  - 页面身份 = vault 相对路径；stem 为多值索引，同名冲突单独报告（LINK-03）；
  - 约定配置：`wiki-audit.config.json` 可覆盖页面目录／原始目录／排除目录／必填字段；默认扫描整个 `raw/`，输出保留完整相对路径；
  - 状态模型：未检查／通过／有提示／有阻断；未扫描到对象时不输出“通过”；
  - `--json`（字段名英文、内容中文）与 `--strict`；退出码 0／1／2；
  - 报告全中文；每条发现含规则编号（IDX/RAW/FM/LINK/HYG/LOG）、路径、定位、严重程度与检查范围；
  - 链接解析迁移到共享模块：别名（`|` 与 `\|`）、`.md` 后缀、显式路径语义、附件按全库文件名核对、空目标（0 字节页）、标题／块锚点近似核对、同名不静默合并；
  - 结构与来源检查、学术可用性抽查分开声明（报告尾注）。
- 验收命令或评估场景：
  - RED 证据：对基线旧脚本运行新回归 `python3 -X utf8 -m unittest discover -s tests -p "test_multimodal_audit_scan.py"` → `Ran 12 tests … FAILED (failures=12)`；
  - GREEN：同命令对新脚本 → `OK`；`-p "test_wiki_links.py"` → 14/14 `OK`；
  - 全套：依赖齐全环境 `Ran 173 tests … OK`；无依赖环境 `Ran 173 tests … OK (skipped=61)`。
- 实际结果：通过（RED→GREEN 证据如上；跳过项均为缺依赖显式跳过）。
- 兼容性与恢复验证：脚本只读；旧库无需迁移；排除目录与文件名清单与原行为兼容，配置缺省即原默认。真实 vault 只读回归：未执行（未取得授权；合成夹具已覆盖验收点）。
- 剩余问题：
  - 标题／块锚点按文本近似核对；“待核”项未在真实 Obsidian 全版本实测；
  - WIKI-02 将把 `wiki_links.py` 复制到 `legal-research-wiki`（同字节），并统一 `check_wikilinks.py` 口径。
