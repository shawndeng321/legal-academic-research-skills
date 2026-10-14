import hashlib
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLEAN_SCRIPT = ROOT / "legal-research-wiki" / "scripts" / "clean_pdf_artifacts.py"
EXTRACT_SCRIPT = ROOT / "legal-research-wiki" / "scripts" / "batch_extract_papers.py"
CHECK_LINKS_SCRIPT = ROOT / "legal-research-wiki" / "scripts" / "check_wikilinks.py"
SYNC_SCRIPT = ROOT / "legal-wiki-audit-repair" / "scripts" / "sync_paper_case_links.py"
INSERT_NORM_SCRIPT = ROOT / "legal-wiki-audit-repair" / "scripts" / "insert_norm_sections.py"
DOCX_SCRIPT = ROOT / "law-paper-writing" / "scripts" / "md2docx_footnotes.py"
MULTIMODAL_AUDIT_SCRIPT = (
    ROOT / "legal-wiki-audit-repair" / "scripts" / "multimodal_audit.py"
)

try:
    import yaml as _yaml  # noqa: F401  （缺依赖时，深检相关测试显式跳过）
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

requires_yaml = unittest.skipUnless(HAVE_YAML, "需要 PyYAML（见 requirements-dev.txt）")


class ScriptSafetyTests(unittest.TestCase):
    def run_script(self, script, *args):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(script), *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_clean_pdf_dry_run_is_recursive_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "entities"
            page = root / "nested" / "paper.md"
            page.parent.mkdir(parents=True)
            page.write_text(
                "# Paper\n\n## 关键词\n\n甲\n乙\n\n## 摘要\n\n摘要］\n\n## 结论\n",
                encoding="utf-8",
            )
            before = hashlib.sha256(page.read_bytes()).digest()

            result = self.run_script(CLEAN_SCRIPT, root, "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("paper.md", result.stdout)
            self.assertIn("DRY-RUN", result.stdout)
            self.assertEqual(before, hashlib.sha256(page.read_bytes()).digest())

    def test_clean_pdf_requires_backup_and_rejects_files_outside_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "entities"
            page = root / "paper.md"
            outside = Path(tmp) / "outside.md"
            root.mkdir()
            content = "# Paper\n\n## 摘要\n\n［摘要］正文。\n"
            page.write_text(content, encoding="utf-8")
            outside.write_text(content, encoding="utf-8")

            missing_backup = self.run_script(CLEAN_SCRIPT, root)
            self.assertNotEqual(missing_backup.returncode, 0)
            self.assertEqual(page.read_text(encoding="utf-8"), content)

            outside_result = self.run_script(CLEAN_SCRIPT, root, str(outside), "--dry-run")
            self.assertNotEqual(outside_result.returncode, 0)
            self.assertEqual(outside.read_text(encoding="utf-8"), content)

    def test_clean_pdf_creates_backup_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "entities"
            page = root / "paper.md"
            backup = Path(tmp) / "backup"
            root.mkdir()
            page.write_text("# Paper\n\n## 摘要\n\n［摘要］正文［1］。\n", encoding="utf-8")

            result = self.run_script(CLEAN_SCRIPT, root, "--backup-dir", backup)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((backup / "paper.md").exists())
            self.assertIn("［摘要］", (backup / "paper.md").read_text(encoding="utf-8"))
            self.assertEqual(
                page.read_text(encoding="utf-8"), "# Paper\n\n## 摘要\n\n正文。\n"
            )

    def test_clean_pdf_only_touches_paper_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "entities"
            case = root / "案例" / "案例1-2016-示例案.md"
            paper = root / "引用文献" / "论文.md"
            case.parent.mkdir(parents=True)
            paper.parent.mkdir(parents=True)
            case_text = (
                "---\ntitle: 示例案\n---\n# 示例案\n\n## 基本案情\n\n【基本案情】某甲受伤。\n\n"
                "## 裁判要旨\n\n【裁判要旨】援引《某法》第十条［1］。\n"
            )
            case.write_text(case_text, encoding="utf-8")
            paper.write_text(
                "# 论文\n\n## 摘要\n\n［摘要］本文讨论，\n认为如此［3］。\n\n"
                "## 关键词\n\n］行政确认；\n程序；［\n\n## 核心论点\n\n1. 第一点，\n继续。\n\n"
                "## 主要结论\n\n结论一，\n结论二。\n\n## 相关概念\n\n- 【注】保留\n",
                encoding="utf-8",
            )

            result = self.run_script(CLEAN_SCRIPT, root, "--backup-dir", Path(tmp) / "bak")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(case.read_text(encoding="utf-8"), case_text)
            self.assertEqual(
                paper.read_text(encoding="utf-8"),
                "# 论文\n\n## 摘要\n\n本文讨论，认为如此。\n\n## 关键词\n\n行政确认；程序\n\n"
                "## 核心论点\n\n1. 第一点，继续。\n\n## 主要结论\n\n结论一，结论二。\n\n"
                "## 相关概念\n\n- 【注】保留\n",
            )

    def test_check_wikilinks_follows_obsidian_resolution_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            (wiki / "entities" / "案例").mkdir(parents=True)
            (wiki / ".maintenance" / "before").mkdir(parents=True)
            (wiki / "raw" / "assets").mkdir(parents=True)
            (wiki / "raw" / "assets" / "图1.png").write_bytes(b"png")
            (wiki / "entities" / "案例" / "案例1-2016-示例案.md").write_text("# 甲\n", encoding="utf-8")
            (wiki / ".maintenance" / "before" / "已删除页.md").write_text("# 备份\n", encoding="utf-8")
            (wiki / "SCHEMA.md").write_text("示例 [[wikilinks]]\n", encoding="utf-8")
            (wiki / "entities" / "测试页.md").write_text(
                "| 案例 | 说明 |\n|---|---|\n| [[案例1-2016-示例案\\|示例案]] | 表格别名 |\n"
                "| [[案例1-2016-示例案&#124;示例案]] | 错误写法 |\n\n"
                "[[案例1-2016-示例案|示例案]] [[案例1-2016-示例案.md]] [[案例1-2016-示例案#裁判要旨]] "
                "[[entities/案例/案例1-2016-示例案]] ![[图1.png]] [[#本页标题]]\n"
                "[[不存在的页]] [[已删除页]]\n截断 [[案例1-2016-示例案## 相关概念\n",
                encoding="utf-8",
            )

            result = self.run_script(CHECK_LINKS_SCRIPT, wiki, "--strict")

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("Dead links: 2", result.stdout)
            self.assertIn("Malformed: 3", result.stdout)
            self.assertIn("-> [[不存在的页]]", result.stdout)
            self.assertIn("-> [[已删除页]]", result.stdout)
            self.assertNotIn("DEAD       entities/测试页.md:3", result.stdout)
            self.assertIn("FALSE      SCHEMA.md:1", result.stdout)

            (wiki / "entities" / "测试页.md").write_text(
                "[[案例1-2016-示例案\\|示例案]]\n", encoding="utf-8"
            )
            clean = self.run_script(CHECK_LINKS_SCRIPT, wiki, "--strict")
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)

    def test_check_wikilinks_tolerates_drafts_and_maintenance_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            (wiki / "entities").mkdir()
            (wiki / "drafts").mkdir()
            (wiki / "entities" / "甲.md").write_text("# 甲\n", encoding="utf-8")
            (wiki / "drafts" / "4.3初稿.md").write_text(
                "正文[[脚注1]]、[[脚注2]]；旧链接 [[旧页面]]\n", encoding="utf-8"
            )
            (wiki / "知识库排查修复流程与整改台账.md").write_text(
                "示例 [[目标&#124;别名]] [[不存在]]\n", encoding="utf-8"
            )
            (wiki / "log-2025.md").write_text("[[旧]]\n", encoding="utf-8")
            (wiki / "entities" / "乙.md").write_text("[[甲]]\n", encoding="utf-8")

            result = self.run_script(CHECK_LINKS_SCRIPT, wiki, "--strict")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Dead links: 0", result.stdout)
            self.assertIn("Malformed: 0", result.stdout)
            self.assertIn("Tolerated (drafts/): 3", result.stdout)
            self.assertIn("2 footnote markers", result.stdout)
            self.assertIn("False positives (SCHEMA/log/台账): 2", result.stdout)

    def test_batch_extract_dry_run_does_not_clobber_existing_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "article.pdf"
            txt = root / "article.txt"
            pdf.write_bytes(b"not a real pdf")
            txt.write_text("keep me", encoding="utf-8")

            result = self.run_script(EXTRACT_SCRIPT, root, "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("article.txt", result.stdout)
            self.assertIn("keep me", txt.read_text(encoding="utf-8"))

    def test_mutating_wiki_scripts_require_a_caller_supplied_vault(self):
        for script in (SYNC_SCRIPT, INSERT_NORM_SCRIPT):
            result = self.run_script(script)
            self.assertNotEqual(result.returncode, 0, script.name)
            self.assertIn("WIKI_PATH", result.stderr)
            self.assertNotIn("/Users/shawndeng/Desktop/", script.read_text(encoding="utf-8"))

    def test_sync_and_norm_scripts_expose_read_only_preview(self):
        for script in (SYNC_SCRIPT, INSERT_NORM_SCRIPT):
            result = self.run_script(script, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--dry-run", result.stdout)

    def test_docx_script_generates_real_footnotes_from_cli_inputs(self):
        try:
            from docx import Document
            from docx.enum.style import WD_STYLE_TYPE
        except ImportError as exc:  # pragma: no cover - environment-specific
            self.skipTest(f"python-docx unavailable: {exc}")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template.docx"
            draft = root / "draft.md"
            output = root / "output.docx"
            doc = Document()
            for name in ("一级标题", "二级标题", "三级标题", "正文1", "FootnoteText", "FootnoteReference"):
                if name not in [style.name for style in doc.styles]:
                    doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            doc.save(template)
            draft.write_text(
                "题目\n作者姓名\n摘要：摘要内容\n关键词：示例；样例\n一、正文\n正文含脚注[1]。\n\n## 脚注\n[1] 判决书，第1页。\n",
                encoding="utf-8",
            )

            result = self.run_script(DOCX_SCRIPT, "--src", template, "--md", draft, "--dst", output)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            Document(output)
            with zipfile.ZipFile(output) as archive:
                document_xml = archive.read("word/document.xml")
                footnotes_xml = archive.read("word/footnotes.xml")
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            document_root = ET.fromstring(document_xml)
            footnotes_root = ET.fromstring(footnotes_xml)
            refs = document_root.findall(".//w:footnoteReference", ns)
            ids = [node.attrib["{%s}id" % ns["w"]] for node in footnotes_root.findall("w:footnote", ns)]
            self.assertEqual(len(refs), 1)
            self.assertIn("1", ids)
            self.assertIn("判决书，第1页。", footnotes_xml.decode("utf-8"))

    @requires_yaml
    def test_multimodal_audit_normalizes_windows_raw_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            entities = wiki / "entities"
            screenshots = wiki / "raw" / "screenshots"
            entities.mkdir(parents=True)
            screenshots.mkdir(parents=True)

            (wiki / "index.md").write_text(
                "当前纳入导航的页面：1\n\n- [[Topic]]\n",
                encoding="utf-8",
            )
            (wiki / "SCHEMA.md").write_text(
                "### A. 概念类\n- topic\n",
                encoding="utf-8",
            )
            (wiki / "log.md").write_text(
                "## [2026-08-07] ingest\n\n- raw/screenshots/sample.md\n",
                encoding="utf-8",
            )
            (entities / "Topic.md").write_text(
                "---\n"
                "title: Topic\n"
                "created: 2026-08-07\n"
                "updated: 2026-08-07\n"
                "type: concept\n"
                "tags: [topic]\n"
                "sources: [raw/screenshots/sample.md]\n"
                "---\n\n"
                "# Topic\n\n[[Topic]]\n",
                encoding="utf-8",
            )
            (screenshots / "sample.png").write_bytes(b"test-image")
            (screenshots / "sample.md").write_text(
                "---\n"
                "title: Sample\n"
                "sha256: abc123\n"
                "---\n\n"
                "line one\nline two\nline three\n",
                encoding="utf-8",
            )

            result = self.run_script(MULTIMODAL_AUDIT_SCRIPT, wiki)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("raw 的 .md 均已登记到 log.md", result.stdout)
            self.assertIn("提取正文 3 行", result.stdout)

    def test_multimodal_audit_requires_an_explicit_wiki_path(self):
        env = os.environ.copy()
        env.pop("WIKI_PATH", None)

        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(MULTIMODAL_AUDIT_SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("WIKI_PATH", result.stderr)

    def test_check_wikilinks_flags_empty_nested_path_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            (wiki / "entities").mkdir()
            (wiki / "entities" / "空页.md").write_text("", encoding="utf-8")
            (wiki / "entities" / "甲页.md").write_text("# 甲页\n\n## 标题\n", encoding="utf-8")
            (wiki / "entities" / "乙页.md").write_text(
                "[[空页]]\n"
                "[[甲页#不存在的标题]]\n"
                "[[错误目录/甲页]]\n"
                "[[甲页 [[乙页]]]]\n",
                encoding="utf-8",
            )

            result = self.run_script(CHECK_LINKS_SCRIPT, wiki, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("Dead links: 0", result.stdout)
            self.assertIn("Empty: 1", result.stdout)
            self.assertIn("Anchor: 1", result.stdout)
            self.assertIn("Path prefix: 1", result.stdout)
            self.assertIn("Malformed: 1", result.stdout)
            self.assertIn("EMPTY      entities/乙页.md:1", result.stdout)
            self.assertIn("ANCHOR     entities/乙页.md:2", result.stdout)
            self.assertIn("PATH       entities/乙页.md:3", result.stdout)
            self.assertIn("MALFORMED  entities/乙页.md:4", result.stdout)

    @requires_yaml
    def test_link_checkers_agree_on_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            entities = wiki / "entities"
            entities.mkdir()
            (entities / "甲页.md").write_text(
                "# 甲页\n\n## 标题\n\n[[乙页]] [[不存在页]]\n", encoding="utf-8"
            )
            (entities / "乙页.md").write_text("# 乙页\n\n[[空页]]\n", encoding="utf-8")
            (entities / "空页.md").write_text("", encoding="utf-8")
            (entities / "丙页.md").write_text(
                "# 丙页\n\n[[甲页#不存在的标题]]\n", encoding="utf-8"
            )
            (entities / "子目录A").mkdir()
            (entities / "子目录B").mkdir()
            (entities / "子目录A" / "同名.md").write_text("# 1\n", encoding="utf-8")
            (entities / "子目录B" / "同名.md").write_text("# 2\n", encoding="utf-8")
            (entities / "丁页.md").write_text("# 丁页\n\n[[同名]]\n", encoding="utf-8")

            links = self.run_script(CHECK_LINKS_SCRIPT, wiki, "--strict")
            audit = self.run_script(MULTIMODAL_AUDIT_SCRIPT, wiki, "--json")

            self.assertEqual(links.returncode, 1, links.stdout)
            self.assertEqual(audit.returncode, 1, audit.stdout[:800])
            match = re.search(
                r"Dead links: (\d+) \| Attachments: (\d+) \| Malformed: (\d+) \| "
                r"Empty: (\d+) \| Path prefix: (\d+) \| Anchor: (\d+) \| Ambiguous: (\d+)",
                links.stdout,
            )
            self.assertIsNotNone(match, links.stdout)
            wdead, wattach, wmalformed, wempty, wpath, wanchor, wambiguous = map(int, match.groups())

            data = json.loads(audit.stdout)
            findings = data["findings"]

            def count(rule, pred=lambda f: True):
                return len([f for f in findings if f["rule"] == rule and pred(f)])

            self.assertEqual(wdead, count("LINK-01", lambda f: "附件" not in f["message"]))
            self.assertEqual(wattach, count("LINK-01", lambda f: "附件" in f["message"]))
            self.assertEqual(wmalformed, count("LINK-04"))
            self.assertEqual(wempty, count("LINK-02"))
            self.assertEqual(wpath, count("LINK-05"))
            self.assertEqual(wanchor, count("LINK-06"))
            self.assertEqual(
                wambiguous,
                count("LINK-03", lambda f: str(f["location"]).startswith("L")),
            )
            self.assertTrue(
                any(str(f["location"]).startswith("同名")
                    for f in findings if f["rule"] == "LINK-03")
            )


if __name__ == "__main__":
    unittest.main()
