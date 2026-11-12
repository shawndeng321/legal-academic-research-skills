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
退出码：正常提取/预览为 0；``--verify`` 全部核完且相符为 0；发现漂移为 1；
无漂移但核验未完成为 2。漂移与未完成可并存，须同时读取子状态与 checks_complete。

Existing companions are preserved; verified complete Markdown may be reused,
otherwise it is reported as pending (exit 2) or changed (exit 1). Empty PDF pages
are conservatively marked needs_ocr. ``--force`` is an explicit
opt-in to overwrite it (原提取物先自行备份，或改用 ``--out-dir`` 写入派生
目录)；``--dry-run`` never opens or writes a PDF. Originals are never
modified.
"""
import argparse
import hashlib
import json
import os
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
    complete = bool(text.strip()) and all(part.strip() for part in text_parts)
    extraction_status = "complete" if complete else "needs_ocr"
    if fmt == "md":
        frontmatter = (
            "---\n"
            f"source_path: {source_path}\n"
            f"ingested: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"source_sha256: {source_sha}\n"
            f"text_sha256: {sha256_text(text)}\n"
            f"extractor: pymupdf {_pymupdf_version(pymupdf)}\n"
            f"extraction_status: {extraction_status}\n"
            f"pages: {len(text_parts)}\n"
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
        "status": "extracted" if complete else "needs_ocr",
    }


def verify_file(md_path, root, source_root=None):
    """Read one companion, retaining separate text/source verification results."""
    entry = {"file": md_path.relative_to(root).as_posix(),
             "text_status": "unreadable", "source_status": "not_checked",
             "verification_status": "incomplete", "checks_complete": False}
    try:
        content = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        entry.update(status="unreadable", error=str(exc))
        return entry
    fm_text, body = split_frontmatter(content)
    if fm_text is None:
        entry.update(status="skipped_no_frontmatter", text_status="skipped_no_frontmatter")
        return entry
    text_sha = read_field(fm_text, "text_sha256")
    legacy_sha = read_field(fm_text, "sha256")
    now = sha256_text(body)
    if text_sha:
        entry["text_sha256_stored"] = text_sha
        entry["text_status"] = "ok" if text_sha == now else "drift"
    elif legacy_sha:
        raw = hashlib.sha256(body.encode("utf-8")).hexdigest()
        entry["text_status"] = "legacy_ok" if legacy_sha in (now, raw) else "drift"
        if entry["text_status"] == "legacy_ok":
            entry["note"] = "旧口径 sha256 命中；建议迁移为 text_sha256（见 multimodal-sha256-bulk-fix.md）"
    else:
        entry["text_status"] = "missing_hash"
    if entry["text_status"] == "drift":
        entry["text_sha256_now"] = now
    source_sha = read_field(fm_text, "source_sha256")
    source_path = read_field(fm_text, "source_path")
    entry["source_status"] = "missing_metadata"
    if source_sha and source_path:
        try:
            # Preserve the recorded path. Never fall back to an unrelated basename.
            source_root = source_root if source_root is not None else root
            candidates = {base / source_path for base in (source_root, *list(source_root.parents)[:3])}
            found = sorted({p.resolve() for p in candidates if p.is_file()})
            if not found:
                entry["source_status"] = "missing"
            elif len(found) > 1:
                entry["source_status"] = "ambiguous"
                entry["source_candidates"] = [str(p) for p in found]
            else:
                entry["source_file"] = str(found[0])
                actual = sha256_bytes(found[0].read_bytes())
                entry["source_status"] = "ok" if actual == source_sha else "drift"
                if actual != source_sha:
                    entry["source_sha256_now"] = actual
        except OSError as exc:
            entry["source_status"] = "unreadable"
            entry["source_error"] = str(exc)
    entry["checks_complete"] = (entry["text_status"] in ("ok", "legacy_ok", "drift")
                                 and entry["source_status"] in ("ok", "drift"))
    if entry["text_status"] == "drift" or entry["source_status"] == "drift":
        entry["verification_status"] = "issues"
        entry["status"] = "drift" if entry["text_status"] == "drift" else "source_drift"
    elif entry["checks_complete"]:
        entry["verification_status"] = "passed"
        entry["status"] = entry["text_status"]
    elif entry["text_status"] == "missing_hash":
        entry["status"] = "missing_hash"
    else:
        entry["status"] = "source_" + entry["source_status"]
    return entry


def verify_md(root):
    """Read-only scan; unreadable directories and empty scopes remain incomplete."""
    results = []

    def scan_error(exc):
        results.append({"file": str(exc.filename), "status": "scan_error",
                        "text_status": "not_checked", "source_status": "not_checked",
                        "verification_status": "incomplete", "checks_complete": False,
                        "error": str(exc)})

    for directory, dirs, files in os.walk(root, onerror=scan_error):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            if Path(name).suffix.lower() == ".md":
                results.append(verify_file(Path(directory) / name, root))
    if not results:
        results.append({"file": None, "status": "no_files", "text_status": "not_checked",
                        "source_status": "not_checked", "verification_status": "incomplete",
                        "checks_complete": False})
    return results


def assess_reuse(pdf_path, out_path, fmt, source_root):
    """Existing files are preserved; only complete, matching extraction is reusable."""
    result = {"status": "unverified_existing", "reuse_status": "incomplete"}
    if fmt != "md":
        result["reason"] = "旧 txt 无原件指纹和提取状态，无法确认复用"
        return result
    check = verify_file(out_path, out_path.parent, source_root=source_root)
    result["verification"] = check
    if check["verification_status"] == "issues":
        result.update(status="needs_reextract", reuse_status="issues",
                      reason="原件或正文变化；先归因，不自动覆盖")
        return result
    if check["verification_status"] != "passed":
        result["reason"] = "原件或正文核验未完成"
        return result
    try:
        fm, body = split_frontmatter(out_path.read_text(encoding="utf-8"))
        if Path(check["source_file"]).resolve() != pdf_path.resolve():
            result["reason"] = "已存提取物对应其他原件"
        elif not body.strip() or read_field(fm, "extraction_status") != "complete":
            result["reason"] = "提取物为空或缺少完整提取状态，须人工确认/OCR"
        else:
            result.update(status="reused", reuse_status="verified",
                          reason="指纹及提取状态一致；不代表内容准确性已人工核验")
    except (OSError, UnicodeError) as exc:
        result["reason"] = str(exc)
    return result


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
        if any(r["verification_status"] == "issues" for r in results):
            return 1
        return 2 if any(r["verification_status"] == "incomplete" for r in results) else 0

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
            if args.dry_run:
                entry.update(status="skipped_existing", reuse_status="not_checked",
                             note="预演未读原件，不能据此确认可复用")
            else:
                entry.update(assess_reuse(pdf_path, out_path, args.format, root))
            results.append(entry)
            continue
        if args.dry_run:
            entry["status"] = "planned"
            results.append(entry)
            continue
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = extract_pdf(pdf_path, out_path, args.format,
                                 f"{source_prefix}/{rel_pdf.as_posix()}")
        except (OSError, RuntimeError, ValueError, ImportError) as exc:
            result = {"status": "extraction_failed", "error": str(exc)}
        entry.update(result)
        results.append(entry)

    print(json.dumps(results, ensure_ascii=False))
    if any(r["status"] == "needs_reextract" for r in results):
        return 1
    if not results or any(r["status"] in ("unverified_existing", "needs_ocr", "extraction_failed") for r in results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
