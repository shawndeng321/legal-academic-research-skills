"""WIKI-12c：SKILL.md 瘦身与迁移对照回归。"""

import unittest
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# Presence is checked by obligation, not by padding to a byte minimum.
ENTRY_REQUIREMENTS = {
    "research": {
        "任务路由": (r"新建", r"增量摄入", r"查询", r"加深", r"审计/修复"),
        "范围与来源": (r"范围先于速度", r"原始材料", r"来源不明"),
        "质量与写入": (r"YAML", r"死链", r"备份", r"试运行", r"逐页复核"),
    },
    "audit": {
        "权限模式": (r"AUDIT_ONLY", r"AUDIT_PLAN", r"REPAIR", r"VERIFY", r"零写入"),
        "定向与边界": (r"SCHEMA\.md", r"index\.md", r"log\.md", r"raw/.*只读"),
        "验收": (r"P0", r"P1", r"P2", r"P3", r"试运行", r"备份", r"逐页"),
    },
}


def entry_contract_errors(text, skill):
    return [name for name, patterns in ENTRY_REQUIREMENTS[skill].items()
            if not all(re.search(pattern, text) for pattern in patterns)]


def route_errors(root, skill, names):
    directory = root / skill
    text = (directory / "SKILL.md").read_text(encoding="utf-8")
    errors = []
    for name in names:
        target = directory / "references" / name
        if f"](references/{name})" not in text or not target.is_file():
            errors.append(name)
        elif not target.read_text(encoding="utf-8").strip():
            errors.append(name)
    return errors


class SlimmingTests(unittest.TestCase):
    def test_skill_sizes_reduced(self):
        writing = len((ROOT / "law-paper-writing" / "SKILL.md").read_bytes())
        research = len((ROOT / "legal-research-wiki" / "SKILL.md").read_bytes())
        audit = len((ROOT / "legal-wiki-audit-repair" / "SKILL.md").read_bytes())
        self.assertLessEqual(writing, 12_000, f"writing SKILL 仍偏大：{writing}")
        self.assertGreaterEqual(writing, 9_000, f"writing SKILL 疑似被截断：{writing}")
        self.assertLessEqual(research, 16_500, f"research SKILL 仍偏大：{research}")
        self.assertEqual(entry_contract_errors((ROOT / "legal-research-wiki" / "SKILL.md").read_text(encoding="utf-8"), "research"), [])
        self.assertLessEqual(audit, 19_000, f"audit SKILL 仍偏大：{audit}")
        self.assertEqual(entry_contract_errors((ROOT / "legal-wiki-audit-repair" / "SKILL.md").read_text(encoding="utf-8"), "audit"), [])

    def test_moved_rules_are_linked(self):
        research = (ROOT / "legal-research-wiki" / "SKILL.md").read_text(encoding="utf-8")
        for name in ("dual-track-isolation.md", "directory-layout-and-page-types.md",
                     "material-routing.md"):
            self.assertIn(f"](references/{name})", research)
            self.assertEqual(route_errors(ROOT, "legal-research-wiki", [name]), [])
        audit = (ROOT / "legal-wiki-audit-repair" / "SKILL.md").read_text(encoding="utf-8")
        for name in ("daily-maintenance-and-periodic-checks.md", "obsidian-parsing-details.md",
                     "templating-and-false-graph-detection.md", "technical-health-checklist.md",
                     "academic-usability-checklist.md"):
            self.assertIn(f"](references/{name})", audit)
            self.assertEqual(route_errors(ROOT, "legal-wiki-audit-repair", [name]), [])

    def test_moved_references_keep_keywords(self):
        base = ROOT / "legal-wiki-audit-repair" / "references"
        daily = (base / "daily-maintenance-and-periodic-checks.md").read_text(encoding="utf-8")
        for kw in ("LOG-ROTATE", "SHA256-DRIFT", "CONTESTED", "CLOSED-WORLD"):
            self.assertIn(kw, daily)
        self.assertRegex(daily, r"连续检修满\s*(?:3|三)\s*天")
        self.assertIn("python3 -m unittest discover -s tests", daily)
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


    def test_contract_allows_short_entries_with_obligations(self):
        examples = {
            "research": "新建、增量摄入、查询、加深、审计/修复。范围先于速度；只认原始材料，缺口标来源不明。检查YAML和死链；先备份、试运行，写后逐页复核。",
            "audit": "AUDIT_ONLY/AUDIT_PLAN/REPAIR/VERIFY 分别按授权执行，默认零写入。读SCHEMA.md、index.md、log.md；raw/只读。按P0/P1/P2/P3分级，先备份、试运行，写后逐页回读。",
        }
        for skill, text in examples.items():
            self.assertEqual(entry_contract_errors(text, skill), [])
            self.assertLess(len(text.encode("utf-8")), 1000)

    def test_contract_detects_removed_safety_obligation(self):
        for skill, path in (("research", "legal-research-wiki"), ("audit", "legal-wiki-audit-repair")):
            text = (ROOT / path / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(entry_contract_errors(text.replace("备份", ""), skill))

    def test_route_detects_missing_and_empty_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "example"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text("[入口](references/rule.md)", encoding="utf-8")
            self.assertEqual(route_errors(root, "example", ["rule.md"]), ["rule.md"])
            target = skill / "references/rule.md"
            target.write_text(" ", encoding="utf-8")
            self.assertEqual(route_errors(root, "example", ["rule.md"]), ["rule.md"])
            target.write_text("来源与权限规则", encoding="utf-8")
            self.assertEqual(route_errors(root, "example", ["rule.md"]), [])


if __name__ == "__main__":
    unittest.main()
