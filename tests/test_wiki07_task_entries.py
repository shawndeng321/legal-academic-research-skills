"""WIKI-07：五种任务入口与模板边界回归。"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "legal-research-wiki" / "SKILL.md"
BRIEF = ROOT / "legal-research-wiki" / "assets" / "templates" / "wiki-design-brief.md"
DESIGN = ROOT / "legal-research-wiki" / "assets" / "templates" / "research-design.md"
INTERVIEW = ROOT / "legal-research-wiki" / "references" / "wiki-design-interview.md"


class TaskEntriesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.brief = BRIEF.read_text(encoding="utf-8")
        cls.design = DESIGN.read_text(encoding="utf-8")
        cls.interview = INTERVIEW.read_text(encoding="utf-8")

    def test_five_entries_present_in_skill(self):
        for entry in ("1 新建", "2 增量摄入", "3 查询", "4 加深", "5 审计"):
            self.assertIn(entry, self.skill)
        self.assertIn("不重复提问", self.skill)
        self.assertIn("不重启整套访谈", self.skill)
        self.assertIn("不顺带建页", self.skill)

    def test_first_material_order_is_recommendation(self):
        self.assertIn("推荐先论文", self.skill)
        self.assertIn("按研究类型", self.skill)
        self.assertNotIn("用户问\u201c先摄入论文还是案例\u201d时，建议**先论文**", self.skill)

    def test_design_brief_does_not_duplicate_progress_table(self):
        self.assertIn("只写建库架构决定", self.brief)
        self.assertIn("五问研究设计页为准", self.brief)
        self.assertIn("只写结论", self.brief)
        self.assertNotIn("| 材料类型 | 数量 | 格式与位置 | 权威层级或来源 | 状态 |", self.brief)

    def test_research_design_owns_progress_table(self):
        self.assertIn("设计书只写结论", self.design)
        self.assertIn("材料进度表与五问细节以本页为准", self.design)

    def test_interview_covers_incremental(self):
        self.assertIn("增量摄入", self.interview)
        self.assertIn("追加材料", self.interview)


if __name__ == "__main__":
    unittest.main()
