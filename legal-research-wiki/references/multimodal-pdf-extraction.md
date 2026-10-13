# 本地 PDF 提取（pymupdf 流程）与哈希口径

> **来源**：multimodal-wiki v1.0.0（kigner/multimodal-wiki）`references/pdf-extraction.md`，2026-08 融合；2026-10 统一哈希口径。
> 法学库用法：与既有 PDF 提取纪律互补——法学库要求提取后做格式清洗（去方括号、合并断行）。
> 本文件同时是**哈希口径的规范出处**：提取（`scripts/batch_extract_papers.py`）、复核（`--verify`）、批量修复（审计技能 `references/multimodal-sha256-bulk-fix.md`）都按本文件执行。

## 0. 哈希口径（规范）

- **原件（PDF/DOCX/图片/音频）**：`source_sha256` = 原件**文件字节**的 sha256。原件永不改动。
- **提取物（.md 正文）**：`text_sha256` = 正文的 sha256。正文定义：
  1. 取 frontmatter 结束分隔符（第二个 `---` 行）之后的内容；
  2. 换行归一化：`\r\n`、`\r` → `\n`；
  3. 去掉**全部前导换行**；保留其余字符（含结尾换行）；
  4. 按 UTF-8 编码后计算 sha256。
- frontmatter 另记 `source_path`（按调用时给出的目录写法拼接；从 wiki 根调用即为 vault 相对路径）、`ingested`（日期）、`extractor`（提取器与版本，如 `pymupdf 1.24`）。
- 旧字段 `sha256:` 属历史口径（对“分隔符后全部内容”或“纯提取文本”两种写法），复核时**两种容差都接受**并标记 `legacy_ok`；**新文件一律写 `text_sha256`**，迁移建议见审计技能 `references/multimodal-sha256-bulk-fix.md`。
- 写入规范：UTF-8；本仓库脚本与示例统一 LF；哈希只算正文，不算 frontmatter。

> 复现过的坑：旧 PDF 示例对“纯提取文本”算哈希，旧复核流程对“分隔符之后的全部内容（含前导换行）”算哈希，两者差一个前导换行，未改动的文件也被判成漂移。第 0 节口径在复核端先做归一化，新文件不再产生该误差。

## Step 1: Copy PDFs to raw/papers/

```powershell
$wikiPath = 'D:\wiki'
Copy-Item -Path 'C:\source-dir\*.pdf' -Destination (Join-Path $wikiPath 'raw\papers')
```

## Step 2: Install pymupdf (if needed)

```bash
uv pip install pymupdf
# or: pip install pymupdf
```

## Step 3: Extract text — 首选脚本（默认不覆盖）

从 wiki 根目录运行：

```bash
python3 scripts/batch_extract_papers.py raw/papers --format md --dry-run    # 先预览计划生成的 .md
python3 scripts/batch_extract_papers.py raw/papers --format md              # 写入提取物（已存在则跳过）
python3 scripts/batch_extract_papers.py raw/papers --format md --out-dir raw/derived/papers   # 新提取物写入派生目录（推荐）
python3 scripts/batch_extract_papers.py raw/papers --verify                 # 只读复核（重算正文哈希 + 核对原件字节）
```

- 默认**不覆盖**：目标已存在时跳过；重新提取请显式 `--force`（先自行备份原提取物）或写入派生目录。
- 复核输出 `ok / legacy_ok / missing_hash / drift / source_drift`；`drift`/`source_drift` 使退出码为 1，先归因（真实变更？清洗？编码？），**不以“重算并覆盖”作为常规修复**。
- 旧库兼容：既有 `.txt` 布局、既有 `.md`（含旧字段 `sha256`）原样保留。

手动提取（等价参考实现，供没有脚本的宿主使用；同样按第 0 节口径）：

```python
import fitz  # pymupdf
import hashlib, os, re
from datetime import datetime

papers_dir = os.path.join(os.environ["WIKI_PATH"], "raw", "papers")  # your wiki root

for fname in sorted(os.listdir(papers_dir)):
    if not fname.endswith('.pdf'):
        continue
    pdf_path = os.path.join(papers_dir, fname)
    out_path = pdf_path[:-4] + '.md'
    if os.path.exists(out_path):
        print(f"[SKIP] {fname} — 已存在提取物（不覆盖；重提取请另行处理）")
        continue

    doc = fitz.open(pdf_path)
    text_parts = [page.get_text() for page in doc]
    doc.close()
    text = '\n'.join(text_parts)

    source_sha = hashlib.sha256(open(pdf_path, 'rb').read()).hexdigest()
    canonical = text.replace('\r\n', '\n').replace('\r', '\n').lstrip('\n')
    text_sha = hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    frontmatter = (
        '---\n'
        f'source_path: raw/papers/{fname}\n'
        f'ingested: {datetime.now().strftime("%Y-%m-%d")}\n'
        f'source_sha256: {source_sha}\n'
        f'text_sha256: {text_sha}\n'
        f'extractor: pymupdf\n'
        '---\n\n'
    )
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(frontmatter + text)

    title = re.sub(r'\s*\[[a-f0-9]+\]\s*', '', fname[:-4])
    print(f"[OK] {title[:80]} ({len(text)} chars)")
```

## Step 4: Categorize papers (for bulk ingest)

Use another code-execution pass to classify by keyword matching on titles, then
group into categories to plan which entity/concept pages to create.

## Key points

- **Always save both** the original `.pdf` AND the extracted `.md`；提取物也可放派生目录（`--out-dir`），旧库保留 `raw/papers/` 同目录布局。
- **The `.md` is the working copy** — 读取用；正文不在修复流程中改写（补全属摄入动作，见 `multimodal-bulk-refs.md` 与审计技能 `multimodal-reingest-stubs.md`）。
- **默认不覆盖**：重新提取生成新版本并记录对应原件（`source_path`/`source_sha256`）。
- **哈希只算正文，不算 frontmatter**；`source_sha256` 只算原件字节；复核随时用 `--verify`。
- **raw 生命周期**：摄入时写入原件与提取物；摄入完成后 raw 进入只读状态——正文不再改，哈希元数据字段的更新属修复动作（授权、备份、归因后执行）。
- **Use native Windows paths**（`<WIKI_PATH>\...`，your wiki root）in the current host's file tools, not bash paths。
