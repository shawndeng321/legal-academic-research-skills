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

## WIKI-02 链接解析与两技能检查口径统一

- 状态：已完成
- 实施提交：`f6b860e`
- 修改文件：
  - `legal-research-wiki/scripts/check_wikilinks.py`（改用共享模块；新增类别；`--strict` 扩展）
  - `legal-research-wiki/scripts/wiki_links.py`（新增：与 `legal-wiki-audit-repair` 同款副本，字节一致）
  - `tests/test_script_safety.py`（新增：空目标／嵌套／路径／锚点检出回归；两检查器一致性回归）
  - `tests/test_wiki_links.py`（新增：双副本字节一致性测试）
  - `legal-research-wiki/SKILL.md`、`legal-research-wiki/references/linking-and-cross-references.md`、`legal-wiki-audit-repair/SKILL.md`（口径同步）
- 原问题与复现样例：0 字节目标、嵌套方括号、错误目录前缀、不存在的标题锚点同时出现时，`--strict` 仍输出 Dead=0、Malformed=0 并返回 0（违反技能自身验收要求）。
- 实际改动：
  - 解析规则统一到 `wiki_links.py`（两技能各持一份、字节一致；深度扫描同用一套规则）；
  - 新类别：EMPTY（0 字节目标）、ATTACH（缺失附件，按全库文件名核对、不混入笔记死链）、PATH（显式路径前缀不符）、ANCHOR（标题／块锚点不存在，块锚点待核）、AMBIGUOUS／DUP（同名不静默合并）；
  - `--strict`：上述任一类存在即返回非零；默认仍为只读报告；drafts/ 与维护文档（SCHEMA／log／台账）容忍规则保持不变；
  - 解析回归补齐：别名（`|`、`\|`）、`.md` 后缀、路径语义、附件嵌入、空目标。
- 验收命令或评估场景：
  - RED：对旧 `check_wikilinks.py` 运行新增回归 → 恰好 2 项失败（`FAILED (failures=2)`）；
  - GREEN：恢复新脚本后 `test_script_safety.py` 14/14 `OK`；`test_wiki_links.py` 15/15 `OK`；
  - 一致性：同一合成 vault 上，`check_wikilinks.py --strict` 与 `multimodal_audit.py --json` 的死链／附件／畸形／空目标／路径／锚点／同名歧义计数逐项相等（回归断言）；
  - 全套：依赖齐全 `Ran 176 tests … OK`；无依赖 `Ran 176 tests … OK (skipped=62)`。
- 实际结果：通过（RED→GREEN 与一致性断言如上）。
- 兼容性与恢复验证：旧调用方式（`<vault> [target_page] [--strict]`）与默认退出码不变（仅 `--strict` 扩展）；容忍类不变；旧库无需迁移。
- 剩余问题：块锚点按文本近似核对（待核）；check_wikilinks 输出语言保持英文（任务书仅要求深检报告中文；如需统一中文另行确认）。

## WIKI-04 原件、提取物与哈希口径统一

- 状态：已完成
- 实施提交：`60b8ddb`
- 修改文件：
  - `legal-research-wiki/scripts/batch_extract_papers.py`（`--format md`／`--out-dir`／`--verify` 与统一哈希）
  - `legal-research-wiki/references/multimodal-pdf-extraction.md`（哈希口径规范第 0 节；重写）
  - `legal-research-wiki/references/multimodal-audio-ingest.md`、`multimodal-image-ingest.md`（字段与口径对齐）
  - `legal-wiki-audit-repair/references/multimodal-sha256-bulk-fix.md`（按新口径重写：边界／三类写入／漂移只报告）
  - `legal-wiki-audit-repair/SKILL.md`（raw 只读的修复例外边界；SHA256-DRIFT 巡检项）、`legal-research-wiki/SKILL.md`（按材料类型表）
  - `tests/test_extract_papers_md.py`（新增 8 项）
- 原问题与复现样例：PDF 示例对纯提取文本算哈希、复核示例对分隔符后全部正文（含前导换行）算哈希 → 未改动文件被判漂移；raw 只读规则与批量修复脚本改写 raw 冲突；批量提取只有 `.txt`，无带 frontmatter 与哈希的 `.md` 能力。
- 实际改动：
  - 统一口径：`source_sha256`（原件字节）＋`text_sha256`（正文：CRLF/CR→LF、去全部前导换行、UTF-8）；配套 `source_path`／`ingested`／`extractor`；旧 `sha256` 字段双容差（`legacy_ok`，建议迁移）；
  - `batch_extract_papers.py`：`--format {txt,md}`（默认仍为 txt）、`--dry-run`、`--out-dir`（派生目录）、`--verify`（只读复核；drift／source_drift → 退出码 1）；默认不覆盖、`--force` 显式、原件永不写；
  - 边界统一：摄入时写 raw；摄入完成后 raw 只读，哈希元数据字段更新属修复动作（授权＋备份＋归因）；真实漂移不得静默重算覆盖；
  - 批量修复重写为三类写入（补齐／占位替换／旧字段迁移），drift 只报告。
- 验收命令或评估场景：
  - `--format md --dry-run` 输出 `planned` 且路径为 `.md`；默认格式仍为 `.txt`；
  - `--verify`：统一口径文件 `ok`（无虚假漂移）；两种旧口径写法 `legacy_ok`；真实改动 `drift`（rc 1）；原件不符 `source_drift`（rc 1）；无哈希字段 `missing_hash`（信息性，rc 0）；
  - 既有保护用例（txt dry-run 不覆盖）不变；原件字节全程不变。
- 实际结果：通过。8/8（对旧脚本 RED：6 失败＋1 错误）；全套 `Ran 184 tests … OK`（依赖齐全）与 `OK (skipped=62)`（无依赖）。
- 兼容性与恢复验证：旧 `.txt`／旧 `.md` 布局兼容；默认不覆盖；备份与环境变量纪律保留。全部在合成夹具上执行，未触碰真实库。
- 剩余问题：`extract_pdf` 的真实提取路径未在依赖齐全环境实跑（pymupdf 为可选依赖，未安装；dry-run／verify／合成覆盖已通过）；WIKI-13 将刷新锁与清单。

## WIKI-05 内容完整性改为证据驱动

- 状态：已完成
- 实施提交：`cd52b15`
- 修改文件：
  - `legal-research-wiki/references/content-completeness.md`（重写：移除硬指标，新增合法状态词）
  - `legal-research-wiki/SKILL.md`（概念页／比较页标准、每批验收条目）
  - `legal-research-wiki/references/pdf-paper-ingestion.md`（质量表改筛查信号；引号经验规则改真实解析核验）
  - `legal-research-wiki/references/pitfalls-and-lessons.md`、`assets/templates/SCHEMA.md`、`assets/templates/concept.md`、`assets/templates/comparison.md`
  - `legal-wiki-audit-repair/SKILL.md`、`references/comparison-page-format.md`（口径同步）
- 原问题与规则冲突：完整性文档要求“至少 500 字符、至少两个概念链接”、概念页“正例／反例／边界例各至少一个”、比较页反例“必须有”，与“证据不足时不形成结论”的核心纪律冲突，诱导补写；SCHEMA 模板“较新的来源通常取代较旧的”与规范时序“新版不覆盖旧版”冲突；“摘要纯中文”“弯引号致 YAML 失败”会误删外文术语、误判合法标点。
- 实际改动：
  - 合格依据＝原文覆盖与具体证据；字数／链接数／反例数降为**复核信号**；
  - 新增合法状态词（已核验／原文未载明／未发现材料／待核验／不适用）；缺口记录与空壳分开；“先穷尽来源，再如实标注”；
  - 原文有要旨则摘录，没有时只写标明身份的研究者归纳，不补造法院要旨；
  - 更新策略按四类区分（规范新版本不覆盖旧版及适用时段／同一文书更正记录依据／学术观点分歧并列／资料错误纠正并记日志）；
  - 引号规则改为按真实解析结果核验（防嵌套／未闭合，不误伤合法标点与术语）。
- 验收命令或评估场景：全文检索硬指标残留（“50 字以上”“200 字”“各至少一个”“必须有”）为零；模板仍通过解析与完整性测试；全套测试双环境通过；短篇批复、单一可靠关联、暂未找到反例、无独立结语、历史法版本五类场景按状态词如实表达（合成审查）。
- 实际结果：通过。`Ran 184 tests … OK`（依赖齐全）与 `OK (skipped=62)`（无依赖）。
- 兼容性与恢复验证：模板结构未破坏（类型选择器与必需字段不变，模板解析测试通过）；旧库文案层面的口径变化不要求数据迁移。
- 剩余问题：代理行为层面的场景评估待 WIKI-08 具体化。

## WIKI-06 只读、日志与持续授权规则统一

- 状态：已完成
- 实施提交：`2ab26ff`
- 修改文件：`legal-wiki-audit-repair/SKILL.md`（模式表、每日检修、分批修复、台账协议句）、`legal-wiki-audit-repair/evals/pressure-tests.md`（场景 12 改写＋新增场景 15）
- 原问题与规则冲突：`AUDIT_ONLY` 不允许写日志，但“今天检修”流程第 4 步要求在 `log.md` 追加记录，且该流程自称“默认只读”；压力测试把这一冲突固化。
- 实际改动：
  - 模式表写入规则：`AUDIT_ONLY`／`VERIFY` 零写入、报告直接输出在会话中；`AUDIT_PLAN` 只写明确指定的报告或台账；`REPAIR` 授权范围内连续推进（默认 5—8 页），新增范围／改口径／删资料再决策；
  - 每日检修：默认只读（含日志）；仅**既定授权**时写 `log.md`，否则拟追加条目附报告末尾待确认；
  - 跨会话延续：已确认范围、允许写入路径与未决项写入交接页，后续会话据此继续（“继续上一批”）；
  - 压力测试：场景 12 按新规改写；新增场景 15“继续上一批”（原 15 顺延为 16）。
- 验收命令或评估场景：旧冲突表述全文检索残留为零；四场景（只排查／今天检修／排查并修复／继续上一批）与模式表逐条对齐；全套测试双环境通过。
- 实际结果：通过（“只读运行前后全库哈希一致”为行为级验证，随 WIKI-08 的代理行为评估执行；本轮为规则文本统一＋场景固化）。
- 兼容性与恢复验证：仅规则与文档变更，无脚本与数据迁移。
- 剩余问题：行为级四场景实测待 WIKI-08；README 的措辞随 WIKI-12／13 复核。

## WIKI-13（第一批收尾）元数据与措辞一致性

- 状态：已完成（本批收尾）
- 实施提交：`f95f877`
- 修改文件：三个 `SKILL.md`（「配套技能」引言去除自指）、三个 `bundle-lock.json` 与 `bundle-release.json`（刷新）
- 原问题与复现样例：三个技能的「配套技能」引言均把本技能自身列入三技能枚举（“本技能与 A、B、C 同属……”）；批量修改后 `prepare_bundle_release.py --check` 报 `legal-research-wiki/bundle-lock.json differs from expected content`。
- 实际改动：修正措辞（只列其他两个技能）；以现行版本 `2610.9.0` 刷新锁与清单（纳入 `scripts/wiki_links.py` 双副本等本批新增文件）；未变更版本号与发布记录（发布决定留待所有者；后续批次还会再次刷新）。
- 验收命令或评估场景：`python3 tools/prepare_bundle_release.py --check` → `Bundle 2610.9.0 is consistent`；全套测试双环境通过。
- 实际结果：通过。`Ran 184 tests … OK`（依赖齐全）与 `OK (skipped=62)`（无依赖）。
- 兼容性与恢复验证：同版本刷新由工具设计支持（历史条目同版本替换）；更新器与锁相关测试全绿。
- 剩余问题：CHANGELOG 条目与发布版本号留待发布决定。

## 第一批小结（WIKI-09、01、02、04、05、06、13-1）

- 已解决任务：WIKI-09、WIKI-01、WIKI-02、WIKI-04、WIKI-05、WIKI-06、WIKI-13（第一批收尾）。
- 变更文件清单（基线 `84dab85`..`f95f877`，36 个文件）：
  - 仓库级：`README.md`、`requirements-dev.txt`（新增）、`bundle-release.json`、三个 `bundle-lock.json`、`docs/法学Wiki技能优化-执行记录.md`（新增）；
  - `legal-research-wiki`：`SKILL.md`；`scripts/check_wikilinks.py`、`scripts/batch_extract_papers.py`、`scripts/wiki_links.py`（新增）；`references/`：content-completeness、linking-and-cross-references、multimodal-pdf-extraction、multimodal-audio-ingest、multimodal-image-ingest、pdf-paper-ingestion、pitfalls-and-lessons；`assets/templates/`：SCHEMA、concept、comparison；
  - `legal-wiki-audit-repair`：`SKILL.md`；`scripts/multimodal_audit.py`、`scripts/wiki_links.py`（新增）；`references/comparison-page-format.md`、`references/multimodal-sha256-bulk-fix.md`；`evals/pressure-tests.md`；
  - `law-paper-writing`：`SKILL.md`（仅配套技能引言措辞）；
  - 测试：`tests/test_multimodal_audit_scan.py`（新增 12）、`tests/test_wiki_links.py`（新增 15）、`tests/test_extract_papers_md.py`（新增 8）、`tests/test_script_safety.py`、`tests/test_skill_compatibility.py`、`tests/test_docx_footnotes.py`、`tests/test_writing_upstream_integration.py`。
- 测试命令及结果：`python3 -X utf8 -m unittest discover -s tests` → 依赖齐全 `Ran 184 tests … OK`；无依赖 `Ran 184 tests … OK (skipped=62)`；`python3 tools/prepare_bundle_release.py --check` → `Bundle 2610.9.0 is consistent`。
- 已知限制：块锚点“待核”（未在真实 Obsidian 全版本实测）；`extract_pdf` 真实提取路径未在依赖齐全环境实跑（pymupdf 可选依赖）；行为级场景（只读哈希一致、四场景压力测试）待 WIKI-08 抽测执行；真实 vault 只读回归未执行（未获授权）。
- 未实施（后续批次）：WIKI-03、WIKI-07、WIKI-08、WIKI-10、WIKI-11、WIKI-12。
- 铁律核对：全程未执行 `git push`（分支 `work/wiki-audit-v2610.9` 仅本地）。


## WIKI-03 官方模板与论文—案例同步闭环

- 状态：已完成
- 实施提交：`c87bc17`
- 修改文件：`legal-wiki-audit-repair/scripts/`（`case_link_utils.py` 新增；`sync_paper_case_links.py`、`scan_missing_paper_case_links.py`、`verify_case_link_sections.py`、`insert_norm_sections.py` 重写）；`legal-wiki-audit-repair/references/batch-operations.md`；`legal-research-wiki/assets/templates/case.md`；`tests/test_paper_case_sync.py`（新增 5）。
- 原问题与复现样例：同步脚本只认旧的无链接写法、单层目录，官方模板 `[[ ]]` 写法扫不到；`TARGETS` 写在源码里；缺漏扫描只扫一层；预演没有具体 diff；验收用 `len()`、同步用 CJK 口径（同步通过而验收误报）；空章节追加崩溃。
- 实际改动：共享模块统一章节提取（文末/空章节）、条目解析（`[[ ]]`/无链接/别名/中英文冒号）、唯一 `cjk_len` 与关系分类；同步改 `--plan JSON` 输入、预演输出具体 diff 与文件哈希、`expect_sha256` 冲突即停、批次含备份→修改→updated→日志→写后复核、部分失败报告已改/未改；扫描递归化并支持 `--plan`；验收与同步同口径并统计关系分布；规范依据插入同样 `--plan` 化。
- 验收命令或评估场景：`tests/test_paper_case_sync.py` 官方模板全流程（扫描→预演→同步→二次同步 0 条→验收）。
- 实际结果：通过。RED 5/5（对 HEAD 旧脚本全失败）→ GREEN；全套 189/189 双环境。
- 兼容性与恢复验证：哈希冲突不写入；备份拒绝覆盖；二次执行幂等；旧写法继续可用。
- 剩余问题：无。

## WIKI-10 法规范效力与案件去重的审计检查

- 状态：已完成
- 实施提交：`2adafc5`
- 修改文件：`legal-wiki-audit-repair/scripts/multimodal_audit.py`（新增第 7 项检查）、`legal-wiki-audit-repair/SKILL.md`、`legal-wiki-audit-repair/README.md`、根 `README.md`、`legal-research-wiki/references/case-ingestion.md`、`legal-research-wiki/assets/templates/SCHEMA.md`、`legal-research-wiki/assets/templates/case.md`；`tests/test_audit_special_checks.py`（新增 8）。
- 原问题与复现样例：深检与每日检修检不出——法规范页缺 `效力状态/核验日期`、核验日期超期、失效规范被概念/比较页当现行依据引用、同一案号（全半角括号不同）重复页面。
- 实际改动：新增第 7 项「法学专项」——NORM-01/02/03 与 DUP-01（案号全半角与空格规范化为主键，辅以法院/裁判日期展示；只报告不合并）；`norm_verify_max_age_days`（默认 365）可配置；「七项深检」文档与每日检修回归项同步；案例摄入补“按案号查重”纪律；案例模板与 SCHEMA 增可选 `authority`（权威层级）。
- 验收命令或评估场景：合成样例（缺字段/过期/被引用失效规范/全半角同案号两页）；`multimodal_audit.py <fixture> --json`。
- 实际结果：通过。四类问题全部按预期报告；运行零写入（前后目录树哈希一致）；RED 8/8 → GREEN。
- 兼容性与恢复验证：纯只读检查；新配置键缺省兼容。
- 剩余问题：无。

## WIKI-11 个人信息与脱敏检查

- 状态：已完成
- 实施提交：`2adafc5`（与 WIKI-10 同一检查项落地）
- 修改文件：同上（`PRIV-01` 部分）。
- 原问题与复现样例：没有任何个人信息格式检查；设计书脱敏规则没有落点。
- 实际改动：可选检查（`--privacy` 或配置 `privacy.enabled`）：身份证号/手机号/银行卡号 + `privacy.extra_patterns`（设计书规则；非法正则拒绝）；命中值一律打码（前 3 后 2）；raw 提取物只报告不修改；默认关闭时在报告中说明。
- 验收命令或评估场景：`--privacy` 合成样例（页面手机号 ×1；raw 内身份证/手机/银行卡各 ×1）；配置启用与非法正则两个边界。
- 实际结果：通过。4/4 命中打码输出，全文号码不出现在任何输出；默认关闭不误报。
- 兼容性与恢复验证：只读；默认关闭不影响既有库。
- 剩余问题：无。

## WIKI-13（第二批收尾）发布元数据与措辞一致性

- 状态：已完成
- 实施提交：`64792d5`
- 修改文件：三个 `bundle-lock.json` 与 `bundle-release.json`（刷新）。
- 验收命令或评估场景：`python3 tools/prepare_bundle_release.py --check`。
- 实际结果：通过（`Bundle 2610.9.0 is consistent`）；全套 197/197 双环境（无依赖显式跳过 70）。
- 兼容性与恢复验证：同版本刷新由工具设计支持。
- 剩余问题：版本号与 CHANGELOG 条目留待发布决定。

## 第二批小结（WIKI-03、10、11、13-2）

- 已解决任务：WIKI-03、WIKI-10、WIKI-11、WIKI-13（第二批收尾）。
- 变更文件：`legal-wiki-audit-repair/`（scripts：新增 `case_link_utils.py`，重写 sync/scan/verify/insert_norm 与 multimodal_audit；SKILL.md、README.md、references/batch-operations.md）；`legal-research-wiki/`（assets/templates：case.md、SCHEMA.md；references：case-ingestion.md）；根 `README.md`；tests：`test_paper_case_sync.py`、`test_audit_special_checks.py`（新增共 13）；bundle 三锁与清单。
- 测试命令及结果：`python3 -X utf8 -m unittest discover -s tests` → 197/197（依赖齐全）；无依赖显式跳过 70；`--check` 一致。
- 已知限制：块锚点“待核”（沿旧）；真实 vault 只读回归未执行（未获授权）。
- 未实施（当时）：WIKI-07、WIKI-08、WIKI-12。
- 铁律核对：仍未执行 `git push`。

## WIKI-07 五种任务入口与模板边界

- 状态：已完成
- 实施提交：`2ee8eaa`
- 修改文件：`legal-research-wiki/SKILL.md`、`assets/templates/wiki-design-brief.md`、`assets/templates/research-design.md`、`references/wiki-design-interview.md`；`tests/test_wiki07_task_entries.py`（新增 5）。
- 原问题与复现样例：正文偏重“新建”；“先论文后案例”被写成固定规则；《设计书》与《研究设计页》两份模板各维护一张材料表（重复大表）。
- 实际改动：新增“任务入口”五类（新建/增量摄入/查询/加深/审计修复）及路由与边界（增量不重启访谈、查询不建页不改库、已说明目的材料范围时不重复提问）；首批材料顺序改为按研究类型（论文导向推荐先论文）；设计书只写建库架构决定、D 节去大表并链接研究设计页；访谈参考补增量说明与常见错误。
- 验收命令或评估场景：`tests/test_wiki07_task_entries.py`（五入口、边界语句、推荐顺序、模板去重）。
- 实际结果：通过。RED 5/5 → GREEN；全套 202/202 双环境。
- 兼容性与恢复验证：纯文档变更；既有引用路径不变。
- 剩余问题：无。

## WIKI-12 两技能职责归位与 SKILL.md 瘦身

- 状态：已完成
- 实施提交：`791d85b`（归位）、`2fd8645`（语言统一）、`58f0872`（瘦身）
- 修改文件：`legal-wiki-audit-repair/references/`（迁入 literature-audit-and-repair、staged-deep-repair、systematic-vault-audit-and-optimization-ledger；新增 daily-maintenance-and-periodic-checks、obsidian-parsing-details、templating-and-false-graph-detection、technical-health-checklist、academic-usability-checklist）；`legal-research-wiki/references/`（新增 dual-track-isolation、directory-layout-and-page-types、material-routing；迁出三件）；两个 `SKILL.md` 与 `README.md`；`legal-research-wiki/references/pdf-paper-ingestion.md`；多份 `multimodal-*.md` 中文化与示例替换；`docs/WIKI-12-规则迁移对照.md`（新增）；`tests/test_wiki12_doc_ownership.py`、`tests/test_wiki12c_skill_slimming.py`（新增 8）。
- 原问题与复现样例：审计细则存于建库技能（单装审计技能拿不到）；`staged-deep-repair.md` 与台账参考整篇英文；多份 multimodal 文档残留重复英文一级标题与理工示例；两个 SKILL 常驻篇幅过大。
- 实际改动：三件审计参考迁入审计技能并更新全部引用（先改测试与引用、不删断言）；`staged-deep-repair`、`systematic-ledger` 全文中译（保留 `OPT-001`、`RULE-CANDIDATE-XXX`、`P0`—`P3` 等术语）；CVPR/ICCV/SIGGRAPH/Stable Diffusion/CVF 等示例替换为法学示例（保留 arXiv 预印本示例）；瘦身 research −23.7%（23,313→17,788 字节）、audit −32.1%（32,551→22,109 字节），迁移明细见对照文档。
- 验收命令或评估场景：归属回归（4）、语言回归（6）、瘦身回归（4）；`--check` 与全套。
- 实际结果：通过。RED 4/4、6/6 → GREEN；全套 213/213 双环境。
- 兼容性与恢复验证：`git mv` 保留历史；跨技能引用按技能名解析；受保护关键词有测试守护。
- 剩余问题：无。

## WIKI-08 精确证据定位与行为回归体系

- 状态：已完成
- 实施提交：`34d3996`
- 修改文件：`legal-research-wiki/assets/templates/SCHEMA.md`（新增“证据最小记录”）、`paper.md`、`case.md`（注入提示）；`legal-wiki-audit-repair/references/academic-usability-checklist.md`（证据定位抽查）；`legal-wiki-audit-repair/evals/behavior-runs.md`（新增）；两份 `evals/pressure-tests.md`（运行记录规范）；`tests/test_fixture_edge_cases.py`、`tests/test_template_end_to_end.py`、`tests/test_behavior_records.py`（新增 6）。
- 原问题与复现样例：精确定位只写在方法论、未落到摄入结果与审计输入；行为评估只有场景描述、没有记录格式与实例；模板端到端与边界夹具没有成套回归。
- 实际改动：证据最小记录（原件与稳定来源标识；定位＝PDF 页码/DOCX 章节段/音频时间戳；摘录标注原文或归纳；核验状态与时间、规范版本；受影响页面），优先用于条文、数字、裁判结果与论文核心主张；行为评估记录规范（输入/产物差异/判定/证据），Hermes 机器回归 4 项 + 五项核心行为抽测清单；三组测试（边界夹具、模板端到端、行为记录）。
- 验收命令或评估场景：`tests/test_template_end_to_end.py`（摄入→检查→同步→幂等→恢复）；`tests/test_fixture_edge_cases.py`；`tests/test_behavior_records.py`。
- 实际结果：通过。模板端到端全链路与备份原样回滚实测通过；全套 219/219 双环境（无依赖显式跳过 73）。
- 兼容性与恢复验证：备份可原样回滚；行为“真实会话抽测”未执行，已在 `behavior-runs.md` 列为待执行（未写成已通过）。
- 剩余问题：真实会话与其他宿主的抽测按行为清单执行；块锚点“待核”沿用。

## WIKI-13（第三批收尾）发布元数据与措辞一致性

- 状态：已完成
- 实施提交：`36f3fbc`、`0713085`（补刷 `law-paper-writing/bundle-lock.json`）
- 修改文件：三个 `bundle-lock.json` 与 `bundle-release.json`（刷新，含 WIKI-12b 的 citation-format 变更）。
- 验收命令或评估场景：`python3 tools/prepare_bundle_release.py --check`。
- 实际结果：通过（`Bundle 2610.9.0 is consistent`）。
- 兼容性与恢复验证：同版本刷新由工具设计支持。
- 剩余问题：版本号与 CHANGELOG 条目留待发布决定。

## 第三批小结（WIKI-07、12、08、13-3）

- 已解决任务：WIKI-07、WIKI-12、WIKI-08、WIKI-13（第三批收尾）。
- 变更文件：见上方各任务条目与 `docs/WIKI-12-规则迁移对照.md`（瘦身逐条对照）。
- 测试命令及结果：`python3 -X utf8 -m unittest discover -s tests` → 219/219（依赖齐全）；`/usr/bin/python3` 同命令 → `OK (skipped=73)`（显式跳过、无导入错误）；`prepare_bundle_release.py --check` 一致。
- 已知限制：块锚点“待核”；真实 vault 只读回归未执行（未获授权）；宿主加载实测未执行；行为评估真实会话抽测待执行（清单与格式已备）。
- 未实施：无。13 项任务与三批收尾全部完成。
- 总体核对：基线 `84dab85` 起共 19 个本地提交（至 `0713085`）；全程未执行 `git push`（分支 `work/wiki-audit-v2610.9` 仅本地）。

## 发布 v2610.14（第四批：发布准备与发布） | 状态：完成

- 发布面清理：项目专属词表移入本机文件 `tests/.project_terms.local.json`（由 `.gitignore` 排除，不入库；守护测试改为读取本机词表，未配置时显式跳过）；两处测试夹具与 `law-paper-writing/CHANGELOG.md` 沿革表述中性化；CHANGELOG 纳入词表扫描范围（解除原豁免）。
- 深检豁免：`raw/MANIFEST.md` 不再要求提取物 frontmatter（检查 2 RAW-05），新增回归测试；修复后真实研究库复检阻断清零。
- 版本刷新：三技能 `metadata.version`、`.claude-plugin/plugin.json`、根 README（版本表、“2026-10 更新内容”节）、三技能 README“当前版本”、三份 CHANGELOG 新增 `v2610.14` 节；`tools/prepare_bundle_release.py --write` 重建锁与发布清单（`2610.14.0`，历史链保留），`--check` 一致。
- 测试：依赖齐全环境 221/221 通过；无依赖环境（/usr/bin/python3）OK (skipped=74)，无导入错误。
  说明：无依赖基线须在剥离 `PYTHONPATH` 的干净环境取值——Hermes execute_code 内核会把自带环境的 PYTHONPATH 泄漏给子进程，使跳过数假降至 22；已按干净环境复核为 74。
- 发布件：`bundle-release.json`（2610.14.0）、三份 `bundle-lock.json`、`PR说明.md` 更新；“推送与宿主回执”见下一条记录。
