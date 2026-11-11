"""WIKI-12c：SKILL.md 瘦身与迁移对照回归。"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SlimmingTests(unittest.TestCase):
    def test_skill_size_ceilings(self):
        writing = len((ROOT / "law-paper-writing" / "SKILL.md").read_bytes())
        research = len((ROOT / "legal-research-wiki" / "SKILL.md").read_bytes())
        audit = len((ROOT / "legal-wiki-audit-repair" / "SKILL.md").read_bytes())
        self.assertLessEqual(writing, 12_000, f"writing SKILL 仍偏大：{writing}")
        self.assertLessEqual(research, 16_500, f"research SKILL 仍偏大：{research}")
        self.assertLessEqual(audit, 19_000, f"audit SKILL 仍偏大：{audit}")

    def test_small_task_routes_and_safety_boundaries(self):
        writing = (ROOT / "law-paper-writing/SKILL.md").read_text(encoding="utf-8")
        rows = [row for row in writing.splitlines() if row.startswith("|")]
        abstract = next(row for row in rows if "只改摘要" in row)
        self.assertIn("references/abstract-writing.md", abstract)
        self.assertNotIn("journal-adaptation.md", abstract)
        self.assertNotIn("workflow.md", abstract)
        local = next(row for row in rows if "局部表达修改" in row)
        self.assertIn("references/legal-prose.md", local)
        self.assertNotIn("argumentation-diagnostics.md", local)
        # Rule contracts, not proof of model behavior or a prose-length minimum.
        for skill in ("legal-research-wiki", "legal-wiki-audit-repair"):
            text = (ROOT / skill / "SKILL.md").read_text(encoding="utf-8")
            for contract in ("最终快照", "规则版本", "失效", "影响范围不明"):
                self.assertIn(contract, text, (skill, contract))
        audit = (ROOT / "legal-wiki-audit-repair/SKILL.md").read_text(encoding="utf-8")
        for mode in ("AUDIT_ONLY", "AUDIT_PLAN", "REPAIR", "VERIFY"):
            self.assertIn(f"`{mode}`", audit)
        self.assertIn("零写入", audit)
        self.assertIn("试运行", audit)
        self.assertIn("备份", audit)

    def test_moved_rules_are_linked(self):
        writing = (ROOT / "law-paper-writing/SKILL.md").read_text(encoding="utf-8")
        for name in ("abstract-writing.md", "argumentation-core.md"):
            self.assertIn(f"](references/{name})", writing)
            self.assertTrue((ROOT / "law-paper-writing/references" / name).is_file())
        research = (ROOT / "legal-research-wiki" / "SKILL.md").read_text(encoding="utf-8")
        for name in ("dual-track-isolation.md", "directory-layout-and-page-types.md",
                     "material-routing.md"):
            self.assertIn(f"](references/{name})", research)
        audit = (ROOT / "legal-wiki-audit-repair" / "SKILL.md").read_text(encoding="utf-8")
        for name in ("daily-maintenance-and-periodic-checks.md", "obsidian-parsing-details.md",
                     "templating-and-false-graph-detection.md", "technical-health-checklist.md",
                     "academic-usability-checklist.md"):
            self.assertIn(f"](references/{name})", audit)

    def test_moved_references_keep_keywords(self):
        base = ROOT / "legal-wiki-audit-repair" / "references"
        daily = (base / "daily-maintenance-and-periodic-checks.md").read_text(encoding="utf-8")
        for kw in ("LOG-ROTATE", "SHA256-DRIFT", "CONTESTED", "CLOSED-WORLD", "自测"):
            self.assertIn(kw, daily)
        obsidian = (base / "obsidian-parsing-details.md").read_text(encoding="utf-8")
        for kw in ("&#124;", "workspace.json", "app.json", "幽灵"):
            self.assertIn(kw, obsidian)
        templ = (base / "templating-and-false-graph-detection.md").read_text(encoding="utf-8")
        self.assertIn("指纹", templ)
        tech = (base / "technical-health-checklist.md").read_text(encoding="utf-8")
        self.assertIn("六维检查", tech)
        acad = (base / "academic-usability-checklist.md").read_text(encoding="utf-8")
        self.assertIn("双向对称", acad)
        dual = (ROOT / "legal-research-wiki" / "references" / "dual-track-isolation.md").read_text(encoding="utf-8")
        self.assertIn("写入方向单向", dual)
        routing = (ROOT / "legal-research-wiki" / "references" / "material-routing.md").read_text(encoding="utf-8")
        self.assertIn("pdf-paper-ingestion.md", routing)

    def test_comparison_doc_exists(self):
        doc = (ROOT / "docs" / "WIKI-12-规则迁移对照.md").read_text(encoding="utf-8")
        for marker in ("规则迁移", "dual-track-isolation.md",
                       "daily-maintenance-and-periodic-checks.md",
                       "technical-health-checklist.md", "academic-usability-checklist.md"):
            self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
