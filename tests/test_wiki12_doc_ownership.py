"""WIKI-12：两技能职责归位——审计细则归属审计技能、引用同步更新。"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOVED = (
    "literature-audit-and-repair.md",
    "staged-deep-repair.md",
    "systematic-vault-audit-and-optimization-ledger.md",
)


class DocOwnershipTests(unittest.TestCase):
    def test_moved_files_live_in_audit_skill(self):
        for name in MOVED:
            self.assertTrue(
                (ROOT / "legal-wiki-audit-repair" / "references" / name).is_file(), name)
            self.assertFalse(
                (ROOT / "legal-research-wiki" / "references" / name).exists(), name)

    def test_research_skill_points_to_audit_skill(self):
        skill = (ROOT / "legal-research-wiki" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## 审计与修复", skill)
        self.assertIn("转交 `legal-wiki-audit-repair`", skill)
        for name in MOVED:
            self.assertNotIn(f"](references/{name})", skill)
        readme = (ROOT / "legal-research-wiki" / "README.md").read_text(encoding="utf-8")
        for name in MOVED:
            self.assertNotIn(f"`references/{name}`", readme)

    def test_audit_skill_links_its_own_details(self):
        skill = (ROOT / "legal-wiki-audit-repair" / "SKILL.md").read_text(encoding="utf-8")
        for name in MOVED:
            self.assertIn(f"](references/{name})", skill)

    def test_pdf_reference_updated(self):
        text = (ROOT / "legal-research-wiki" / "references" / "pdf-paper-ingestion.md").read_text(
            encoding="utf-8")
        self.assertNotIn("](literature-audit-and-repair.md)", text)
        self.assertIn("legal-wiki-audit-repair", text)


if __name__ == "__main__":
    unittest.main()
