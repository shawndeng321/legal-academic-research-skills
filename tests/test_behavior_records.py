"""WIKI-08 行为评估记录回归：pressure-tests 运行记录规范、behavior-runs 记录可复核。"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BehaviorRecordTests(unittest.TestCase):
    def test_behavior_runs_document(self):
        doc = (ROOT / "legal-wiki-audit-repair" / "evals" / "behavior-runs.md").read_text(
            encoding="utf-8")
        for behavior in ("只读不写日志", "稀疏证据不编造", "无反例如实说明",
                         "学术分歧不按日期覆盖", "增量摄入不重复访谈"):
            self.assertIn(behavior, doc)
        for kw in ("Hermes", "输入", "产物差异", "判定", "证据"):
            self.assertIn(kw, doc)
        self.assertIn("tests/test_template_end_to_end.py", doc)

    def test_pressure_tests_have_record_schema(self):
        for skill in ("legal-research-wiki", "legal-wiki-audit-repair"):
            text = (ROOT / skill / "evals" / "pressure-tests.md").read_text(encoding="utf-8")
            with self.subTest(skill=skill):
                self.assertIn("运行记录规范", text)
                for kw in ("输入", "产物差异", "判定"):
                    self.assertIn(kw, text)

    def test_cited_tests_exist(self):
        doc = (ROOT / "legal-wiki-audit-repair" / "evals" / "behavior-runs.md").read_text(
            encoding="utf-8")
        cited = set(re.findall(r"tests/(test_[a-z0-9_]+)\.py", doc))
        self.assertTrue(cited)
        for name in cited:
            self.assertTrue((ROOT / "tests" / (name + ".py")).is_file(), name)


if __name__ == "__main__":
    unittest.main()
