"""共享链接解析模块（wiki_links.py）的单元测试。

覆盖 WIKI-02 的解析口径：别名（| 与 \\|）、.md 后缀、路径语义、锚点、
附件、空目标、同名歧义、畸形写法。纯标准库，无需额外依赖。
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "legal-wiki-audit-repair" / "scripts"))

import wiki_links  # noqa: E402


class MalformedTests(unittest.TestCase):
    def test_clean_line_has_no_problems(self):
        line = "[[目标|别名]] [[目标\\|表格别名]] [[#本页标题]] ![[图.png]] [[子目录/目标#锚点]]"
        self.assertEqual(wiki_links.malformed_problems(line), [])

    def test_nested_brackets_flagged(self):
        problems = wiki_links.malformed_problems("[[甲页 [[乙页]]]]")
        self.assertTrue(any("嵌套方括号" in p for p in problems))

    def test_missing_close_flagged(self):
        problems = wiki_links.malformed_problems("截断 [[目标## 标题\n")
        self.assertTrue(any("缺少 `]]`" in p for p in problems))

    def test_empty_target_flagged(self):
        problems = wiki_links.malformed_problems("[[]] 与 [[|别名]]")
        self.assertTrue(any("空链接目标" in p for p in problems))

    def test_escaped_entity_pipe_flagged(self):
        problems = wiki_links.malformed_problems("[[目标&#124;别名]]")
        self.assertTrue(any("&#124;" in p for p in problems))


class ParseTests(unittest.TestCase):
    def test_alias_md_suffix_and_anchor_stripped(self):
        links = wiki_links.parse_links_in_line("[[a/b.md#裁判要旨|别名]]")
        self.assertEqual(len(links), 1)
        link = links[0]
        self.assertEqual(link.file_part, "a/b.md")
        self.assertEqual(link.anchor, "裁判要旨")
        self.assertTrue(link.has_alias)
        self.assertFalse(link.embed)

    def test_escaped_pipe_is_alias_separator(self):
        links = wiki_links.parse_links_in_line("[[目标\\|别名]]")
        self.assertEqual(links[0].file_part, "目标")
        self.assertTrue(links[0].has_alias)

    def test_embed_flag(self):
        links = wiki_links.parse_links_in_line("![[图1.png]]")
        self.assertTrue(links[0].embed)
        self.assertEqual(links[0].file_part, "图1.png")


class VaultIndexTests(unittest.TestCase):
    def build(self, tmp):
        return wiki_links.VaultIndex.build(Path(tmp))

    def test_duplicate_stems_not_merged_and_ambiguous(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            (wiki / "a").mkdir()
            (wiki / "b").mkdir()
            (wiki / "a" / "同名.md").write_text("# 1\n", encoding="utf-8")
            (wiki / "b" / "同名.md").write_text("# 2\n", encoding="utf-8")

            index = self.build(tmp)
            self.assertEqual(len(index.duplicate_stems()["同名"]), 2)
            resolution = index.resolve("同名")
            self.assertEqual(resolution.status, "ambiguous")
            self.assertIn(resolution.target, ("a/同名.md", "b/同名.md"))

    def test_path_link_keeps_path_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            (wiki / "entities" / "案例").mkdir(parents=True)
            (wiki / "entities" / "案例" / "甲.md").write_text("# 甲\n", encoding="utf-8")

            index = self.build(tmp)
            self.assertEqual(index.resolve("entities/案例/甲").status, "ok")
            self.assertEqual(index.resolve("entities/案例/甲.md").status, "ok")
            wrong = index.resolve("错误目录/甲")
            self.assertEqual(wrong.status, "path_mismatch")

    def test_empty_target_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            (wiki / "空页.md").write_text("", encoding="utf-8")

            index = self.build(tmp)
            self.assertEqual(index.resolve("空页").status, "empty_target")

    def test_attachment_resolved_by_full_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            (wiki / "raw" / "assets").mkdir(parents=True)
            (wiki / "raw" / "assets" / "图1.png").write_bytes(b"png")

            index = self.build(tmp)
            self.assertEqual(index.resolve("图1.png").status, "ok")
            self.assertEqual(index.resolve("无图.png").status, "missing")

    def test_heading_and_block_anchors(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            (wiki / "页.md").write_text(
                "# 页\n\n## 裁判要旨\n\n内容 ^blk\n", encoding="utf-8"
            )

            index = self.build(tmp)
            self.assertEqual(index.resolve("页#裁判要旨").status, "ok")
            self.assertEqual(index.resolve("页#不存在").status, "anchor_missing")
            self.assertEqual(index.resolve("页#^blk").status, "ok")
            self.assertEqual(index.resolve("页#^无").status, "anchor_missing")

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = self.build(tmp)
            self.assertEqual(index.resolve("不存在").status, "missing")


class CopyIdentityTests(unittest.TestCase):
    def test_shared_module_copies_are_byte_identical(self):
        research = (ROOT / "legal-research-wiki" / "scripts" / "wiki_links.py").read_bytes()
        audit = (ROOT / "legal-wiki-audit-repair" / "scripts" / "wiki_links.py").read_bytes()
        self.assertEqual(
            research, audit,
            "wiki_links.py 的两份副本必须字节相同（改一份后必须同步复制）",
        )


if __name__ == "__main__":
    unittest.main()
