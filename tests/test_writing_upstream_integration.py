from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - 缺依赖时跳过相关测试，而不是模块导入失败
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
_REQUIRE_YAML = "需要 PyYAML：python3 -m pip install -r requirements-dev.txt"


class WritingUpstreamIntegrationTests(unittest.TestCase):
    @unittest.skipIf(yaml is None, _REQUIRE_YAML)
    def test_writing_skill_has_one_canonical_name(self) -> None:
        skill = ROOT / "law-paper-writing" / "SKILL.md"
        self.assertTrue(skill.is_file(), "renamed writing skill is not present")
        self.assertFalse((ROOT / "chinese-law-paper-writing").exists())
        metadata = yaml.safe_load(skill.read_text(encoding="utf-8").split("---", 2)[1])
        self.assertEqual(metadata["name"], "law-paper-writing")

    @unittest.skipIf(yaml is None, _REQUIRE_YAML)
    def test_three_skill_metadata_versions_share_date_release(self) -> None:
        bundle_version = json.loads(
            (ROOT / "bundle-release.json").read_text(encoding="utf-8")
        )["bundle_version"]
        for name in ("law-paper-writing", "legal-research-wiki", "legal-wiki-audit-repair"):
            with self.subTest(skill=name):
                text = (ROOT / name / "SKILL.md").read_text(encoding="utf-8")
                metadata = yaml.safe_load(text.split("---", 2)[1])
                self.assertEqual(metadata["metadata"]["version"], bundle_version)

    def test_new_citation_formats_are_routed_and_audited(self) -> None:
        writing = ROOT / "law-paper-writing"
        entry = (writing / "SKILL.md").read_text(encoding="utf-8")
        audit = (writing / "assets/templates/citation-audit.md").read_text(encoding="utf-8")
        for name in ("citation-format.md", "citation-format-foreign.md"):
            with self.subTest(file=name):
                self.assertTrue((writing / "references" / name).is_file())
                self.assertIn("references/" + name, entry)
        self.assertIn("适用引注体例", audit)
        self.assertIn("再次引用", audit)

    def test_review_and_abstract_rules_preserve_research_boundaries(self) -> None:
        writing = ROOT / "law-paper-writing"
        diagnostics = (writing / "references/argumentation-diagnostics.md").read_text(encoding="utf-8")
        citation = (writing / "references/citation-integrity.md").read_text(encoding="utf-8")
        journal = (writing / "references/journal-adaptation.md").read_text(encoding="utf-8")
        for section in ("研究现状与文献综述", "一致意见单列", "脚注内的批语", "方法或结果章节"):
            self.assertIn(section, diagnostics)
        self.assertIn("逐观点", citation)
        self.assertIn("程序研究", citation)
        self.assertIn("改判机制", citation)
        self.assertIn("四个功能位", journal)
        self.assertIn("期刊风格观察卡", journal)
        self.assertIn("用户已确认", journal)
        self.assertTrue((writing / "assets/examples/abstract-examples.md").is_file())
        for name in ("citation-format-cases.md", "review-feedback-cases.md"):
            self.assertTrue((writing / "evals" / name).is_file())
        pressure = (writing / "evals/pressure-tests.md").read_text(encoding="utf-8")
        self.assertIn("citation-format-cases.md", pressure)
        self.assertIn("review-feedback-cases.md", pressure)
        # 用户扩展能力不是上游精简版的删除候选。
        for relative in ("references/docx-production.md", "references/empirical-case-research.md",
                         "references/multimodal-citation-format.md", "references/obsidian-knowledge-base.md"):
            self.assertTrue((writing / relative).is_file())
        requirement = (writing / "references/requirement-decomposition.md").read_text(encoding="utf-8")
        self.assertIn("期刊论文项目的展开提示", requirement)
        self.assertFalse((writing / "references/obsidian-hermes-workflow.md").exists())

    def test_citation_format_split_is_indexed(self) -> None:
        refs = ROOT / "law-paper-writing" / "references"
        volumes = [
            "citation-format.md",
            "citation-format-paper-items.md",
            "citation-format-chinese.md",
            "citation-format-legal.md",
            "citation-format-examples.md",
            "citation-format-foreign.md",
            "citation-format-foreign-other.md",
        ]
        for name in volumes:
            with self.subTest(file=name):
                self.assertTrue((refs / name).is_file(), name)
        index = (refs / "citation-format.md").read_text(encoding="utf-8")
        for name in volumes[1:]:
            self.assertIn(f"]({name})", index)
        self.assertLessEqual(len((refs / "citation-format.md").read_bytes()), 13_000)
        self.assertLessEqual(
            len((refs / "citation-format-foreign.md").read_bytes()), 11_000
        )
        # 手册第1—150条须在各分册 ##/### 标题中完整覆盖，无缺号。
        covered = set()
        for name in volumes:
            text = (refs / name).read_text(encoding="utf-8")
            for heading in re.findall(r"^#{2,3} .*$", text, re.M):
                for match in re.finditer(r"第(\d+)(?:—(\d+))?条", heading):
                    start = int(match.group(1))
                    end = int(match.group(2) or start)
                    covered.update(range(start, end + 1))
        self.assertEqual(covered, set(range(1, 151)))


if __name__ == "__main__":
    unittest.main()
