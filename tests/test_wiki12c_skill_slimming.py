"""WIKI-12c：SKILL.md 瘦身与迁移对照回归。"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SlimmingTests(unittest.TestCase):
    def test_skill_sizes_reduced(self):
        research = len((ROOT / "legal-research-wiki" / "SKILL.md").read_bytes())
        audit = len((ROOT / "legal-wiki-audit-repair" / "SKILL.md").read_bytes())
        self.assertLessEqual(research, 18_200, f"research SKILL 仍偏大：{research}")
        self.assertGreaterEqual(research, 13_000, f"research SKILL 疑似被截断：{research}")
        self.assertLessEqual(audit, 22_600, f"audit SKILL 仍偏大：{audit}")
        self.assertGreaterEqual(audit, 16_000, f"audit SKILL 疑似被截断：{audit}")

    def test_moved_rules_are_linked(self):
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
        for kw in ("LOG-ROTATE", "SHA256-DRIFT", "CONTESTED", "CLOSED-WORLD", "检修满 3 天", "自测"):
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
