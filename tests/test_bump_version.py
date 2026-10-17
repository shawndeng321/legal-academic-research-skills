from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUMP = ROOT / "tools" / "bump_version.py"
SKILLS = (
    "law-paper-writing",
    "legal-research-wiki",
    "legal-wiki-audit-repair",
)
SYNCED_FILES = [
    ".claude-plugin/plugin.json",
    "README.md",
    "law-paper-writing/README.md",
    "legal-research-wiki/README.md",
    "legal-wiki-audit-repair/README.md",
    *[f"{name}/SKILL.md" for name in SKILLS],
]


def copy_synced_files(root: Path) -> None:
    for relative in SYNCED_FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


def run_bump(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(BUMP),
            *extra,
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


class BumpVersionTests(unittest.TestCase):
    def test_bump_rewrites_every_pinned_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_synced_files(root)
            result = run_bump(root, "2610.18.1", "--date", "2026-10-18")
            self.assertEqual(result.returncode, 0, result.stderr)

            for name in SKILLS:
                with self.subTest(skill=name):
                    skill = (root / name / "SKILL.md").read_text(encoding="utf-8")
                    self.assertIn('  version: "2610.18.1"', skill)
            plugin = (root / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
            self.assertIn('"version": "2610.18.1"', plugin)
            readme = (root / "README.md").read_text(encoding="utf-8")
            self.assertEqual(readme.count("| **v2610.18.1** |"), 3)
            paper = (root / "law-paper-writing/README.md").read_text(encoding="utf-8")
            self.assertEqual(paper.count("v2610.18.1"), 3)
            self.assertIn(
                "**当前版本：v2610.18.1（机器字段 2610.18.1；2026-10-18）**",
                paper,
            )
            for name in ("legal-research-wiki", "legal-wiki-audit-repair"):
                with self.subTest(skill=name):
                    text = (root / name / "README.md").read_text(encoding="utf-8")
                    self.assertIn(
                        "**当前版本：v2610.18.1（2026-10-18；机器字段 2610.18.1）**",
                        text,
                    )

    def test_bump_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_synced_files(root)
            first = run_bump(root, "2610.18.1", "--date", "2026-10-18")
            self.assertEqual(first.returncode, 0, first.stderr)
            snapshot = {
                relative: (root / relative).read_bytes()
                for relative in SYNCED_FILES
            }
            second = run_bump(root, "2610.18.1", "--date", "2026-10-18")
            self.assertEqual(second.returncode, 0, second.stderr)
            for relative, content in snapshot.items():
                with self.subTest(file=relative):
                    self.assertEqual((root / relative).read_bytes(), content)

    def test_bump_writes_nothing_when_any_target_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            copy_synced_files(root)
            wiki_readme = root / "legal-research-wiki" / "README.md"
            text = wiki_readme.read_text(encoding="utf-8")
            lines = [
                line for line in text.split("\n") if "当前版本" not in line
            ]
            wiki_readme.write_text("\n".join(lines), encoding="utf-8")
            snapshot = {
                relative: (root / relative).read_bytes()
                for relative in SYNCED_FILES
            }
            result = run_bump(root, "2610.18.1", "--date", "2026-10-18")
            self.assertNotEqual(result.returncode, 0)
            for relative, content in snapshot.items():
                with self.subTest(file=relative):
                    self.assertEqual((root / relative).read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
