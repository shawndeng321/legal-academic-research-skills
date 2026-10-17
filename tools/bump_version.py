from __future__ import annotations

"""Single-source version bump: rewrite the pinned version strings across the repo.

bundle-release.json is produced by prepare_bundle_release.py and stays the
machine source of truth; this script only syncs the human-facing copies:
SKILL.md frontmatter, the Claude plugin manifest, and the README version
lines/badges. CHANGELOG entries and "本版" notes are content and stay manual.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "law-paper-writing",
    "legal-research-wiki",
    "legal-wiki-audit-repair",
)
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def public_tag(version: str) -> str:
    # 公开日期标签的首版省略当天序号 0（与 tests 中的口径一致）。
    if version.endswith(".0"):
        return "v" + version.rsplit(".", 1)[0]
    return "v" + version


def _sub(pattern: str, repl: str, text: str, *, expect: int, label: str) -> str:
    matches = list(re.finditer(pattern, text, re.MULTILINE))
    if len(matches) != expect:
        raise ValueError(
            f"{label}: expected {expect} match(es), found {len(matches)}"
        )
    return re.sub(pattern, repl, text, flags=re.MULTILINE)


def rewrite(root: Path, version: str, release_date: str) -> dict[Path, str]:
    tag = public_tag(version)
    results: dict[Path, str] = {}

    for skill_name in SKILLS:
        path = root / skill_name / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        results[path] = _sub(
            r'^  version: "\d+\.\d+\.\d+"$',
            f'  version: "{version}"',
            text,
            expect=1,
            label=f"{skill_name}/SKILL.md metadata.version",
        )

    plugin = root / ".claude-plugin" / "plugin.json"
    results[plugin] = _sub(
        r'"version": "\d+\.\d+\.\d+"',
        f'"version": "{version}"',
        plugin.read_text(encoding="utf-8"),
        expect=1,
        label=".claude-plugin/plugin.json version",
    )

    readme = root / "README.md"
    results[readme] = _sub(
        r"\| \*\*v\d+\.\d+(?:\.\d+)?\*\* \|",
        f"| **{tag}** |",
        readme.read_text(encoding="utf-8"),
        expect=3,
        label="README.md skill table tags",
    )

    paper = root / "law-paper-writing" / "README.md"
    text = paper.read_text(encoding="utf-8")
    badge = re.search(
        r"!\[Version: v\d+\.\d+(?:\.\d+)?\]"
        r"\(https://img\.shields\.io/badge/Version-v\d+\.\d+(?:\.\d+)?-[^)]*\)",
        text,
    )
    if badge is None:
        raise ValueError("law-paper-writing/README.md: version badge not found")
    new_badge = re.sub(r"v\d+\.\d+(?:\.\d+)?", tag, badge.group(0), count=2)
    text = text.replace(badge.group(0), new_badge, 1)
    results[paper] = _sub(
        r"\*\*当前版本：v\d+\.\d+(?:\.\d+)?（机器字段 \d+\.\d+\.\d+；\d{4}-\d{2}-\d{2}）\*\*",
        f"**当前版本：{tag}（机器字段 {version}；{release_date}）**",
        text,
        expect=1,
        label="law-paper-writing/README.md 当前版本",
    )

    for skill_name in ("legal-research-wiki", "legal-wiki-audit-repair"):
        path = root / skill_name / "README.md"
        results[path] = _sub(
            r"\*\*当前版本：v\d+\.\d+(?:\.\d+)?（\d{4}-\d{2}-\d{2}；机器字段 \d+\.\d+\.\d+）\*\*",
            f"**当前版本：{tag}（{release_date}；机器字段 {version}）**",
            path.read_text(encoding="utf-8"),
            expect=1,
            label=f"{skill_name}/README.md 当前版本",
        )

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bump the pinned skill-bundle version across repo files."
    )
    parser.add_argument("version")
    parser.add_argument("--date", dest="release_date", default=None)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    if not SEMVER_RE.fullmatch(args.version):
        print(f"invalid version: {args.version!r} (expect N.N.N)", file=sys.stderr)
        return 2
    release_date = args.release_date or date.today().isoformat()
    if not DATE_RE.fullmatch(release_date):
        print(f"invalid date: {release_date!r} (expect YYYY-MM-DD)", file=sys.stderr)
        return 2

    root = args.root.resolve()
    try:
        results = rewrite(root, args.version, release_date)
    except (ValueError, OSError) as exc:
        print(f"bump failed, nothing written: {exc}", file=sys.stderr)
        return 1

    for path, content in results.items():
        old = path.read_text(encoding="utf-8")
        if content != old:
            path.write_text(content, encoding="utf-8")
            print(f"updated {path.relative_to(root)}")
        else:
            print(f"unchanged {path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
