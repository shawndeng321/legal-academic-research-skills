"""WIKI-12：两技能职责归位——审计细则归属审计技能、引用同步更新、参考文档全中文。"""

import re
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


CHINESE_DOCS = (
    "legal-research-wiki/references/multimodal-audio-ingest.md",
    "legal-research-wiki/references/multimodal-image-ingest.md",
    "legal-research-wiki/references/multimodal-pdf-extraction.md",
    "legal-research-wiki/references/multimodal-bulk-refs.md",
    "law-paper-writing/references/multimodal-citation-format.md",
    "legal-wiki-audit-repair/references/multimodal-reingest-stubs.md",
    "legal-wiki-audit-repair/references/staged-deep-repair.md",
    "legal-wiki-audit-repair/references/systematic-vault-audit-and-optimization-ledger.md",
    "legal-research-wiki/references/multimodal-obsidian-headless.md",
)


class LanguageTests(unittest.TestCase):
    def test_reference_docs_have_no_english_h1(self):
        for rel in CHINESE_DOCS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(doc=rel):
                self.assertNotRegex(text, r"^# [A-Za-z].*$", re.M)

    def test_former_engineering_examples_replaced(self):
        for rel in ("legal-research-wiki/references/multimodal-bulk-refs.md",
                    "legal-wiki-audit-repair/references/multimodal-reingest-stubs.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            for term in ("CVPR", "ICCV", "SIGGRAPH", "Stable Diffusion", "CVF"):
                with self.subTest(doc=rel, term=term):
                    self.assertNotIn(term, text)

    def test_key_rules_survive_translation(self):
        bulk = (ROOT / "legal-research-wiki/references/multimodal-bulk-refs.md").read_text(encoding="utf-8")
        self.assertIn("arXiv", bulk)
        self.assertIn("stub", bulk.lower())
        reingest = (ROOT / "legal-wiki-audit-repair/references/multimodal-reingest-stubs.md").read_text(encoding="utf-8")
        self.assertIn("只算正文", reingest)
        self.assertIn("查询阶段不得补全", reingest)
        staged = (ROOT / "legal-wiki-audit-repair/references/staged-deep-repair.md").read_text(encoding="utf-8")
        self.assertIn("子批次", staged)
        self.assertIn("页码", staged)
        ledger = (ROOT / "legal-wiki-audit-repair/references/" / "systematic-vault-audit-and-optimization-ledger.md").read_text(encoding="utf-8")
        self.assertIn("OPT-001", ledger)
        self.assertIn("RULE-CANDIDATE-XXX", ledger)
        self.assertIn("P0", ledger)


if __name__ == "__main__":
    unittest.main()
