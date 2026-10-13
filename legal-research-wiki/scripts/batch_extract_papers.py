#!/usr/bin/env python3
"""Extract text from PDFs without silently clobbering companion files.

Usage:
    python3 batch_extract_papers.py /path/to/papers --dry-run
    python3 batch_extract_papers.py /path/to/papers                      # .txt companions (legacy layout)
    python3 batch_extract_papers.py /path/to/papers --format md [--out-dir DIR]
    python3 batch_extract_papers.py /path/to/papers --verify             # 只读复核既有 .md 提取物

Formats:
    txt (default)  plain-text companion beside the PDF (legacy layout);
    md             companion with frontmatter: ``source_path``, ``ingested``,
                   ``source_sha256``, ``text_sha256``, ``extractor``。

哈希口径（与 ``legal-research-wiki/references/multimodal-pdf-extraction.md``
及审计技能的「sha256 批量修复」一致）：
    - ``source_sha256``：原件文件**字节**的 sha256（原件永不改动）；
    - ``text_sha256``：提取**正文**的 sha256。正文 = frontmatter 结束分隔符
      之后的内容，先做换行归一化（CRLF/CR → LF），再去掉全部前导换行；
      保留其余字符（含结尾换行）；编码 UTF-8。

``--verify`` 复核既有 .md 提取物（只读）：按上述口径重算正文哈希；旧字段
``sha256`` 按旧口径的两种容差（含前导换行／不含）各试一次，命中标记
``legacy_ok``（建议迁移为 ``text_sha256``）；``source_path`` 可解析时同时
核对 ``source_sha256`` 与原件字节。drift 只报告归因，不自动重算覆盖。
退出码：正常提取/预览为 0；``--verify`` 发现 drift 或 source_drift 为 1。

By default, an existing companion is skipped. ``--force`` is an explicit
opt-in to overwrite it (原提取物先自行备份，或改用 ``--out-dir`` 写入派生
目录)；``--dry-run`` never opens or writes a PDF. Originals are never
modified.
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


def canonical_body(text):
    """正文规范化（统一口径）：CRLF/CR → LF，去掉全部前导换行。"""
    return text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\n")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_text(text):
    return hashlib.sha256(canonical_body(text).encode("utf-8")).hexdigest()


def split_frontmatter(content):
    """返回 (fm_text, body)；无 frontmatter 时 fm_text 为 None。"""
    if not content.startswith("---"):
        return None, content
    end = content.find("---", 3)
    if end == -1:
        return None, content
    return content[3:end], content[end + 3:]


def read_field(fm_text, name):
    for line in fm_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(name + ":"):
            return stripped.split(":", 1)[1].strip()
    return None


def _pymupdf_version(pymupdf):
    version = getattr(pymupdf, "__version__", None)
    if version:
        return str(version)
    try:
        return ".".join(str(part) for part in pymupdf.version[:3])
    except Exception:
        return "unknown"


def extract_pdf(pdf_path, out_path, fmt, source_path):
    """Extract one PDF and return result fields; originals are never touched."""
    import pymupdf

    source_sha = sha256_bytes(pdf_path.read_bytes())
    doc = pymupdf.open(str(pdf_path))
    try:
        text_parts = [page.get_text() for page in doc]
    finally:
        doc.close()
    text = "\n".join(text_parts)
    if fmt == "md":
        frontmatter = (
            "---\n"
            f"source_path: {source_path}\n"
            f"ingested: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"source_sha256: {source_sha}\n"
            f"text_sha256: {sha256_text(text)}\n"
            f"extractor: pymupdf {_pymupdf_version(pymupdf)}\n"
            "---\n\n"
        )
        out_path.write_text(frontmatter + text, encoding="utf-8")
    else:
        out_path.write_text(text, encoding="utf-8")
    return {
        "source_sha256": source_sha,
        "text_sha256": sha256_text(text),
        "pages": len(text_parts),
        "chars": len(text),
        "status": "extracted",
    }


def verify_md(root):
    """只读复核 root 下的 .md 提取物；返回结果列表。"""
    results = []
    for md_path in sorted(root.rglob("*.md")):
        rel_parts = md_path.relative_to(root).parts
        if any(part.startswith(".") for part in rel_parts[:-1]):
            continue
        rel = "/".join(rel_parts)
        entry = {"file": rel, "status": "ok"}
        try:
            content = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            entry["status"] = "unreadable"
            entry["error"] = str(exc)
            results.append(entry)
            continue
        fm_text, body = split_frontmatter(content)
        if fm_text is None:
            entry["status"] = "skipped_no_frontmatter"
            results.append(entry)
            continue
        text_sha = read_field(fm_text, "text_sha256")
        legacy_sha = read_field(fm_text, "sha256")
        if text_sha:
            entry["text_sha256_stored"] = text_sha
            if text_sha == sha256_text(body):
                entry["status"] = "ok"
            else:
                entry["status"] = "drift"
                entry["text_sha256_now"] = sha256_text(body)
        elif legacy_sha:
            now_canonical = sha256_text(body)
            now_raw = hashlib.sha256(body.encode("utf-8")).hexdigest()
            if legacy_sha in (now_canonical, now_raw):
                entry["status"] = "legacy_ok"
                entry["note"] = ("旧口径 sha256 命中；建议迁移为 text_sha256"
                                 "（见 multimodal-sha256-bulk-fix.md）")
            else:
                entry["status"] = "drift"
                entry["text_sha256_now"] = now_canonical
        else:
            entry["status"] = "missing_hash"
        source_sha = read_field(fm_text, "source_sha256")
        source_path = read_field(fm_text, "source_path")
        source_status = None
        if source_sha and source_path:
            candidates = [root / source_path]
            for parent in list(root.parents)[:3]:
                candidates.append(parent / source_path)
            candidates.append(root / Path(source_path).name)
            source_file = next((c for c in candidates if c.is_file()), None)
            if source_file is None:
                source_status = "missing"
            else:
                actual = sha256_bytes(source_file.read_bytes())
                source_status = "ok" if actual == source_sha else "drift"
            if source_status == "drift" and entry["status"] == "ok":
                entry["status"] = "source_drift"
        if source_status:
            entry["source_status"] = source_status
        results.append(entry)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("papers_dir", nargs="?", default=".", help="directory containing PDF files")
    parser.add_argument("--dry-run", action="store_true", help="list planned work without reading or writing PDFs")
    parser.add_argument("--force", action="store_true", help="overwrite existing companions (explicit opt-in)")
    parser.add_argument("--format", choices=("txt", "md"), default="txt",
                        help="companion format: txt (default) or md（带 frontmatter 与哈希，默认不覆盖）")
    parser.add_argument("--out-dir", default=None,
                        help="companion output directory (default: beside each PDF)；可指向派生目录")
    parser.add_argument("--verify", action="store_true",
                        help="只读复核既有 .md 提取物（重算正文哈希并核对原件字节）")
    args = parser.parse_args(argv)

    root = Path(args.papers_dir).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"papers directory does not exist: {root}")

    if args.verify:
        results = verify_md(root)
        print(json.dumps(results, ensure_ascii=False))
        return 1 if any(r.get("status") in ("drift", "source_drift") for r in results) else 0

    suffix = ".md" if args.format == "md" else ".txt"
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else None
    source_prefix = str(args.papers_dir).rstrip("/\\")

    results = []
    for pdf_path in sorted(root.rglob("*.pdf")):
        rel_pdf = pdf_path.relative_to(root)
        out_path = ((out_dir / rel_pdf) if out_dir else pdf_path).with_suffix(suffix)
        try:
            display_out = str(out_path.relative_to(root))
        except ValueError:
            display_out = str(out_path)
        entry = {"file": str(rel_pdf), "output": display_out}
        if out_path.exists() and not args.force:
            entry["status"] = "skipped_existing"
            results.append(entry)
            continue
        if args.dry_run:
            entry["status"] = "planned"
            results.append(entry)
            continue
        out_path.parent.mkdir(parents=True, exist_ok=True)
        result = extract_pdf(pdf_path, out_path, args.format,
                             f"{source_prefix}/{rel_pdf.as_posix()}")
        entry.update(result)
        results.append(entry)

    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
