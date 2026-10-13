# sha256 批量修复与迁移（raw 提取物哈希元数据）— 多模态扩展

> **来源**：multimodal-wiki v1.0.0（kigner/multimodal-wiki）`references/sha256-bulk-fix.md`，2026-08 融合；2026-10 按统一哈希口径重写。
> 口径规范见 `legal-research-wiki` 的 `references/multimodal-pdf-extraction.md` 第 0 节；与 `scripts/batch_extract_papers.py --verify` 完全一致。

## 边界（先读）

- 原件（`raw/` 下的 PDF/DOCX/图片/音频二进制）**永不写入**；本流程只更新提取物（.md）的**哈希元数据字段**。
- 写入前必须有：明确授权、`BACKUP_DIR`、系统性归因结论；默认预览（DRY_RUN）。
- **真实漂移不自动重算覆盖**：`text_sha256` 已存在且与当前正文不符 → 只报告，先行归因（人工润色？清洗脚本？编码/换行变更？）；确需重建基线时保留旧值、旧口径与理由，记入台账。
- 本流程只做三类写入：① 缺 `text_sha256` → 按统一口径补齐；② 占位值（`<placeholder>`/`PLACEHOLDER`）→ 替换；③ 旧字段 `sha256` → 追加 `text_sha256`（**旧值保留为历史，不删**）。

## Script（预览为首选；写入需 `BACKUP_DIR` 且 `DRY_RUN=0`）

```python
import os, re, hashlib, shutil

WIKI = os.path.abspath(os.environ["WIKI_PATH"])
raw_dir = os.path.join(WIKI, 'raw')
DRY_RUN = os.environ.get("DRY_RUN", "1") != "0"
BACKUP_DIR = os.environ.get("BACKUP_DIR")

if not os.path.isdir(raw_dir):
    raise SystemExit(f"raw directory not found: {raw_dir}")
if not DRY_RUN and not BACKUP_DIR:
    raise SystemExit("BACKUP_DIR is required when DRY_RUN=0")
if BACKUP_DIR:
    BACKUP_DIR = os.path.abspath(BACKUP_DIR)


def canonical_body(text):
    return text.replace('\r\n', '\n').replace('\r', '\n').lstrip('\n')


def sha256_text(text):
    return hashlib.sha256(canonical_body(text).encode('utf-8')).hexdigest()


def rebuild(fm_text, body):
    if not fm_text.endswith('\n'):
        fm_text += '\n'
    return '---' + fm_text + '---' + body


def write_with_backup(path, new_content):
    if DRY_RUN:
        return
    relative = os.path.relpath(path, raw_dir)
    backup_path = os.path.join(BACKUP_DIR, relative)
    if os.path.exists(backup_path):
        raise FileExistsError(f"backup already exists: {backup_path}")
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(path, backup_path)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(new_content)


stats = {'added': 0, 'migrated': 0, 'placeholder_fixed': 0,
         'ok': 0, 'drift_report': 0, 'skipped': 0}

for root, dirs, files in os.walk(raw_dir):
    for f in sorted(files):
        if not f.endswith('.md'):
            continue
        path = os.path.join(root, f)
        with open(path, 'r', encoding='utf-8') as fh:
            original = fh.read()
        if not original.startswith('---'):
            stats['skipped'] += 1
            continue
        end = original.find('---', 3)
        if end == -1:
            stats['skipped'] += 1
            continue
        fm = original[3:end]
        body = original[end + 3:]
        current = sha256_text(body)

        m_text = re.search(r'^text_sha256:\s*(\S+)\s*$', fm, re.M)
        m_legacy = re.search(r'^sha256:\s*(\S+)\s*$', fm, re.M)
        m_placeholder = re.search(r'^text_sha256:\s*(<placeholder>|PLACEHOLDER)\s*$', fm, re.M)

        if m_text and not m_placeholder:
            if m_text.group(1) == current:
                stats['ok'] += 1
                continue
            # 真实漂移：只报告，不覆盖
            stats['drift_report'] += 1
            print(f"[DRIFT] {os.path.relpath(path, raw_dir)} — 正文与 text_sha256 不符，先归因（不自动重算）")
            continue

        if m_placeholder:
            new_fm = fm[:m_placeholder.start()] + f'text_sha256: {current}' + fm[m_placeholder.end():]
            stats['placeholder_fixed'] += 1
        elif m_legacy:
            new_fm = fm.rstrip() + '\n' + f'text_sha256: {current}\n'
            stats['migrated'] += 1
            legacy_now_raw = hashlib.sha256(body.encode('utf-8')).hexdigest()
            if m_legacy.group(1) not in (current, legacy_now_raw):
                print(f"[NOTE] {os.path.relpath(path, raw_dir)} — 旧 sha256 与当前正文也不符，请人工核对后再依此迁移")
        else:
            ingested = re.search(r'^ingested:.*$', fm, re.M)
            insert_at = ingested.end() if ingested else len(fm.rstrip())
            new_fm = fm[:insert_at] + '\n' + f'text_sha256: {current}' + fm[insert_at:]
            stats['added'] += 1

        write_with_backup(path, rebuild(new_fm, body))

mode = "DRY-RUN" if DRY_RUN else "WRITE"
print(f"{mode}: {stats}")
```

先只设置 `WIKI_PATH` 运行预览，确认计数与抽样文件；确认后设置一个新的 `BACKUP_DIR` 并显式 `DRY_RUN=0`。备份目标已有同名文件时脚本停止，不会覆盖旧备份。

## Verification

一键复核（推荐；只读，drift 时退出码 1）：

```bash
python3 scripts/batch_extract_papers.py raw/papers --verify   # 在 legal-research-wiki 技能目录下运行
```

输出每条 .md 的 `ok / legacy_ok / missing_hash / drift / source_drift`。批量修复完成后应无 `drift`/`source_drift`；`legacy_ok` 表示旧口径哈希仍然相符，可在下一轮迁移为 `text_sha256`。

## When to Use

- 初始建库时用了占位哈希 → 批量替换（第 ② 类写入）；
- 旧文件缺 `text_sha256` 或仍是旧字段 `sha256` → 批量补齐/迁移（第 ①③ 类写入）；
- 检修发现大量漂移（10 个以上）先归因（占位哈希、行尾符、编码、批量清洗脚本），确认系统性原因后才修；
- 单个漂移先核对是否真实变更，确认后更新并记入台账；**不得**静默重算覆盖。
