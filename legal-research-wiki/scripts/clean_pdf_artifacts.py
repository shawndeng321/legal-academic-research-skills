#!/usr/bin/env python3
"""
Clean PDF extraction artifacts from paper (literature) wiki pages.

Usage:
    python3 clean_pdf_artifacts.py /path/to/wiki/entities/引用文献 --dry-run
    python3 clean_pdf_artifacts.py /path/to/wiki/entities/引用文献 --backup-dir /path/to/backup
    python3 clean_pdf_artifacts.py /path/to/wiki/entities --backup-dir /path/to/backup file1.md file2.md ...

Only four paper-page sections are touched: ## 摘要, ## 关键词, ## 核心论点, ## 主要结论.
Frontmatter and every other section (for example case pages' 【裁判要旨】 labels)
are left exactly as they are. Dry-run is read-only. A backup directory is
required before any in-place write.
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

PAPER_SECTIONS = ("摘要", "关键词", "核心论点", "主要结论")
SECTION_RE = re.compile(
    r"^## (" + "|".join(PAPER_SECTIONS) + r")[ \t]*\n(.*?)(?=^## |\Z)",
    re.M | re.S,
)
# PDF layout labels such as 【摘要】/［关键词］ that leak into extracted text.
LABEL_RE = re.compile(r"[【［]\s*(?:摘\s*要|内容提要|提\s*要|关\s*键\s*词|Abstract|Key\s*words?)\s*[】］][:：]?", re.I)
# Footnote markers rendered as ［1］, ［12］ inside running text.
FOOTNOTE_MARK_RE = re.compile(r"［\s*\d{1,3}\s*］")


STRUCTURAL_LINE = re.compile(
    r"^\s*(?:#{1,6}\s|[-+*•]\s|\d+[.)、]\s*|[（(]\d+[）)]|"
    r"[（(]?[一二三四五六七八九十]+[）)、.]|[>|]|`{3}|~{3})"
)


def _join_broken_lines(text):
    """Join clear prose wraps; retain structure and uncertain word splitting."""
    result = []
    for line in text.split("\n"):
        if not result or not result[-1].strip() or not line.strip():
            result.append(line)
            continue
        previous = result[-1]
        left, right = previous.rstrip(), line.lstrip()
        if (STRUCTURAL_LINE.match(line) or previous.lstrip().startswith(("#", "|", ">", "```", "~~~"))
                or left.endswith(("-", "。", "！", "？", ".", "!", "?", ":", "："))
                or line.startswith(("    ", "\t"))):
            result.append(line)
            continue
        if re.search(r"[A-Za-z0-9]$", left) and re.match(r"[A-Za-z0-9]", right):
            result[-1] = left + " " + right
        elif re.search(r"[\u3400-\u9fff，、；]$", left) and re.match(r"[\u3400-\u9fff]", right):
            result[-1] = left + right
        else:
            result.append(line)
    return "\n".join(result)


def _clean_section(name, body):
    trailing = body[len(body.rstrip("\n")):]
    content = body.rstrip("\n")
    content = LABEL_RE.sub("", content)
    content = FOOTNOTE_MARK_RE.sub("", content)
    content = content.replace("］", "").replace("［", "")
    if name == "关键词":
        content = content.replace("【", "").replace("】", "")
        lead = content[: len(content) - len(content.lstrip("\n"))]
        content = lead + _join_broken_lines(content.strip()).strip(";；")
    elif name in ("摘要", "主要结论"):
        content = _join_broken_lines(content)
    else:  # 核心论点
        content = "\n\n".join(_join_broken_lines(p) for p in content.split("\n\n"))
    return content + trailing


def clean_pdf_artifacts(text):
    """Remove PDF extraction artifacts from the four paper-page sections only."""

    def replace(match):
        header_end = match.start(2) - match.start(0)
        return match.group(0)[:header_end] + _clean_section(match.group(1), match.group(2))

    return SECTION_RE.sub(replace, text)


def scan_for_issues(filepath):
    """Check the four paper-page sections of a single file for PDF artifacts."""
    content = Path(filepath).read_text(encoding="utf-8")
    issues = []
    for match in SECTION_RE.finditer(content):
        name, body = match.group(1), match.group(2).strip("\n")
        if LABEL_RE.search(body) or FOOTNOTE_MARK_RE.search(body) or "］" in body or "［" in body:
            issues.append(f"{name}PDF方括号残留")
        if name == "关键词" and ("\n" in body or "【" in body or "】" in body):
            issues.append("关键词格式异常")
        if name in ("摘要", "主要结论") and re.search(r"[，；。、]\n[^\n]", body):
            issues.append(f"{name}PDF换行残留")
    if "Vo1." in content:
        issues.append("OCR错误(Vo1.)（需人工核对，脚本不自动改）")
    return issues


def collect_files(entities_dir, specific_files=None):
    """Resolve inputs and reject explicit files outside the requested scope."""
    root = Path(entities_dir).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"entities directory does not exist: {root}")
    if not specific_files:
        return root, sorted(root.rglob("*.md"))

    files = []
    for raw in specific_files:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"file is outside entities directory: {raw}") from exc
        if candidate.suffix.lower() != ".md":
            raise ValueError(f"file is not a Markdown page: {raw}")
        files.append(candidate)
    return root, files


def validate_backup_dir(root, backup_dir):
    if not backup_dir:
        raise ValueError("in-place writes require --backup-dir")
    backup_root = Path(backup_dir).expanduser().resolve()
    if backup_root == root or root in backup_root.parents:
        raise ValueError("backup directory must not be inside entities directory")
    return backup_root


def write_atomic(path, text):
    """Replace one page atomically after its backup has been created."""
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entities_dir", help="directory containing wiki entity pages")
    parser.add_argument("files", nargs="*", help="optional Markdown files relative to entities_dir")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    parser.add_argument("--backup-dir", help="backup destination required for writes")
    args = parser.parse_args(argv)

    try:
        root, files = collect_files(args.entities_dir, args.files)
    except ValueError as exc:
        parser.error(str(exc))

    changes = []
    for path in files:
        if not path.exists():
            print(f"  ⏭️ {path.relative_to(root)} (not found)")
            continue
        issues = scan_for_issues(path)
        if not issues:
            continue
        original = path.read_text(encoding="utf-8")
        cleaned = clean_pdf_artifacts(original)
        if cleaned == original:
            print(f"⚠️ {path.relative_to(root)}: issues detected but no changes made: {issues}")
            continue
        changes.append((path, issues, original, cleaned))

    if args.dry_run:
        for path, issues, _, _ in changes:
            print(f"[DRY-RUN] {path.relative_to(root)}: would fix {', '.join(issues)}")
        print(f"\nFixed: 0 files | Planned changes: {len(changes)} files | Remaining issues: not rewritten")
        return 0

    backup_root = validate_backup_dir(root, args.backup_dir) if changes else None
    # Preflight every backup path before changing any page, preventing partial batches.
    if backup_root is None:
        print("\nFixed: 0 files | Remaining issues: 0")
        return 0
    backup_root.mkdir(parents=True, exist_ok=True)
    destinations = []
    for path, _, _, _ in changes:
        destination = backup_root / path.relative_to(root)
        if destination.exists():
            raise RuntimeError(f"backup already exists; refusing to clobber it: {destination}")
        destinations.append((path, destination))
    for path, destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    fixed_count = 0
    for path, issues, _, cleaned in changes:
        write_atomic(path, cleaned)
        print(f"✅ {path.relative_to(root)}: fixed {', '.join(issues)}")
        fixed_count += 1

    remaining = sum(bool(scan_for_issues(path)) for path in files if path.exists())
    print(f"\nFixed: {fixed_count} files | Remaining issues: {remaining}")
    return 0


if __name__ == '__main__':
    main()
