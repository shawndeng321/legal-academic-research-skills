#!/usr/bin/env python3
"""Vault-wide wikilink checker for Obsidian legal wikis.

Usage:
    python3 check_wikilinks.py /path/to/wiki [target_page] [--strict]

Parsing and resolution rules come from the shared module `wiki_links.py`
(identical copy in this skill and in `legal-wiki-audit-repair`; the deep-scan
script there uses the same rules, so both checkers reach the same
conclusions on the same scope):
- links resolve by explicit path first (vault-relative), then by file name
  anywhere in the vault; `[[target]]`, `[[target|alias]]`, `[[target\\|alias]]`
  (tables), `[[target#heading]]`, `[[target#^block]]`, `[[target.md]]` and
  embeds `![[image.png]]` are all handled;
- duplicate file names are never silently merged — they are reported
  (AMBIGUOUS / DUP) and a link resolves to the shortest path;
- headings/block anchors are matched textually (block anchors are “待核”,
  not verified against every Obsidian version).

Reported separately:
- DEAD       missing targets linked from content pages;
- ATTACH     missing attachment embeds (checked against all file names);
- MALFORMED  `&#124;` aliases, links that swallow a heading (`[[x## ...`),
             nested brackets, empty targets, unmatched `[[`;
- EMPTY      links whose target is a 0-byte page (Obsidian opens it, but the
             link is not healthy);
- PATH       explicit path links whose prefix does not exist (resolvable by
             file name; fix the prefix);
- ANCHOR     missing heading/block in an otherwise valid target;
- AMBIGUOUS  links matching several same-named files;
- TOLERATED  links inside drafts/ (footnote markers like [[脚注12]] expected);
- FALSE      links inside maintenance documents: SCHEMA.md, log.md, rotated
             log-YYYY.md and root-level ledgers whose name contains 台账
             (rule examples and history — never "fix" these).

Hidden directories (`.maintenance/`, `.obsidian/`, `.trash/` ...) and backup
folders (ghosts, backup(s), _scripts, node_modules, _archive) are skipped:
backups must not make a deleted page look alive.

With target_page (page stem, no [[]] or .md), counts inbound backlinks from
every content page. Exit codes: 0 normally; with --strict, 1 when any of
DEAD/ATTACH/MALFORMED/EMPTY/PATH/ANCHOR/AMBIGUOUS (or duplicate page names)
is present.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wiki_links  # noqa: E402
from wiki_links import (  # noqa: E402
    DEFAULT_SKIP_DIR_NAMES,
    VaultIndex,
    malformed_problems,
    parse_links_in_line,
    strip_md_suffix,
)

KNOWN_FALSE_POSITIVE_FILES = {"SCHEMA.md", "log.md"}
ROTATED_LOG_RE = re.compile(r"^log-\d{4}.*\.md$")
DRAFT_DIR_NAMES = {"drafts"}


def is_maintenance_doc(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    if name in KNOWN_FALSE_POSITIVE_FILES or ROTATED_LOG_RE.match(name):
        return True
    return "/" not in rel and "台账" in name


def is_draft(rel: str) -> bool:
    return rel.split("/", 1)[0] in DRAFT_DIR_NAMES


def check(wiki: Path, target: str | None = None) -> int:
    """Run the scan; returns the number of hard findings (strict-mode basis)."""
    index = VaultIndex.build(wiki, exclude_dir_names=set(DEFAULT_SKIP_DIR_NAMES))
    page_rels = sorted(
        rel for rel, path in index.files.items() if path.suffix.lower() == ".md"
    )
    dead, attach, empty, path_mm, anchor, ambiguous = [], [], [], [], [], []
    malformed, tolerated, false_pos = [], [], []
    backlink_sources = []

    for rel in page_rels:
        text = index.read_text(rel)
        if text is None:
            continue
        is_doc = is_maintenance_doc(rel)
        in_drafts = is_draft(rel)
        is_content = not is_doc and not in_drafts
        linked = set()
        for number, line in enumerate(text.splitlines(), 1):
            if is_content:
                for problem in malformed_problems(line):
                    malformed.append((rel, number, problem, line.strip()[:80]))
            for link in parse_links_in_line(line):
                if "://" in link.file_part:
                    continue
                if link.file_part == "":
                    if is_content and link.anchor \
                            and index.check_heading_anchor(rel, link.anchor) == "missing":
                        anchor.append((rel, number, "#" + link.anchor, rel))
                    continue
                display = strip_md_suffix(link.file_part.rsplit("/", 1)[-1])
                linked.add(display)
                resolution = index.resolve(link.file_part, link.anchor)
                if resolution.status == "ok":
                    continue
                if not is_content:
                    # drafts/docs: unresolvable links go to their tolerant buckets
                    (false_pos if is_doc else tolerated).append((rel, number, display))
                    continue
                if resolution.status == "missing":
                    (attach if link.embed else dead).append((rel, number, link.file_part))
                elif resolution.status == "empty_target":
                    empty.append((rel, number, link.file_part, resolution.target))
                elif resolution.status == "path_mismatch":
                    path_mm.append((rel, number, link.file_part, resolution.target))
                elif resolution.status == "anchor_missing":
                    label = link.file_part + ("#" + link.anchor if link.anchor else "")
                    anchor.append((rel, number, label, resolution.target or ""))
                elif resolution.status == "ambiguous":
                    ambiguous.append((rel, number, link.file_part, resolution.candidates))
        if target and target in linked and is_content:
            backlink_sources.append(rel)

    dup_stems = index.duplicate_stems()

    print(f"Vault: {wiki}")
    print(
        f"Pages: {len(page_rels)} | Dead links: {len(dead)} | Attachments: {len(attach)} | "
        f"Malformed: {len(malformed)} | Empty: {len(empty)} | Path prefix: {len(path_mm)} | "
        f"Anchor: {len(anchor)} | Ambiguous: {len(ambiguous)} | "
        f"Tolerated (drafts/): {len(tolerated)} | "
        f"False positives (SCHEMA/log/台账): {len(false_pos)}"
    )
    for rel, number, name in dead:
        print(f"  DEAD       {rel}:{number} -> [[{name}]]")
    for rel, number, name in attach:
        print(f"  ATTACH     {rel}:{number} -> ![[{name}]] (attachment not found)")
    for rel, number, problem, snippet in malformed:
        print(f"  MALFORMED  {rel}:{number} {problem} | {snippet}")
    for rel, number, name, resolved in empty:
        print(f"  EMPTY      {rel}:{number} -> [[{name}]] (0-byte target: {resolved})")
    for rel, number, name, resolved in path_mm:
        print(f"  PATH       {rel}:{number} -> [[{name}]] "
              f"(path prefix not found; resolves by name to {resolved})")
    for rel, number, name, resolved in anchor:
        print(f"  ANCHOR     {rel}:{number} -> [[{name}]] "
              f"(no matching heading/block in {resolved})")
    for rel, number, name, candidates in ambiguous:
        print(f"  AMBIGUOUS  {rel}:{number} -> [[{name}]] "
              f"({len(candidates)} files: {', '.join(candidates)})")
    if dup_stems:
        print("  Duplicate page names (links resolve to the shortest path; disambiguate):")
        for stem, paths in dup_stems.items():
            print(f"  DUP        {stem}: {', '.join(paths)}")
    footnote_markers = sum(1 for _, _, name in tolerated if re.fullmatch(r"脚注\d+", name))
    if footnote_markers:
        print(f"  TOLERATED  drafts/: {footnote_markers} footnote markers like [[脚注N]] (expected)")
    for rel, number, name in tolerated:
        if not re.fullmatch(r"脚注\d+", name):
            print(f"  TOLERATED  {rel}:{number} -> [[{name}]] (draft — not a live page)")
    for rel, number, name in false_pos:
        print(f"  FALSE      {rel}:{number} -> [[{name}]] (doc example / history — ignore)")
    if target:
        print(f"Backlinks to [[{target}]]: {len(backlink_sources)}")
        for source in backlink_sources:
            print(f"  <- {source}")
    return (
        len(dead) + len(attach) + len(malformed) + len(empty)
        + len(path_mm) + len(anchor) + len(ambiguous) + len(dup_stems)
    )


def main(argv: list[str]) -> int:
    args = [arg for arg in argv if arg != "--strict"]
    strict = len(args) != len(argv)
    if not args:
        print(__doc__)
        return 1
    wiki = Path(args[0]).expanduser()
    if not wiki.is_dir():
        print(f"Wiki root is not a directory: {wiki}", file=sys.stderr)
        return 1
    failures = check(wiki, args[1] if len(args) > 1 else None)
    return 1 if strict and failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
