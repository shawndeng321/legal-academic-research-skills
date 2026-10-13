"""batch_extract_papers.py 的 md 模式与复核（--verify）回归测试。

对应任务书 WIKI-04 验收点：`--format md --dry-run` 列出计划生成的 .md；
默认不覆盖；原件字节不变；新提取文件立即复核无虚假漂移（含旧口径容差）；
真实改动可被定位为 drift。不需要 pymupdf（跳过/复核路径不打开 PDF）。
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "legal-research-wiki" / "scripts" / "batch_extract_papers.py"


def sha_text(text):
    """与统一口径一致的正文哈希（测试端独立实现）。"""
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha_raw(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(root, *args):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), str(root), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def parse(result):
    return json.loads(result.stdout)


class ExtractMdTests(unittest.TestCase):
    def test_dry_run_md_lists_planned_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "papers"
            root.mkdir()
            (root / "article.pdf").write_bytes(b"%PDF-fake")
            result = run(root, "--format", "md", "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            entries = parse(result)
            self.assertEqual(entries[0]["status"], "planned")
            self.assertTrue(entries[0]["output"].endswith(".md"), entries)

    def test_default_format_still_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "papers"
            root.mkdir()
            (root / "article.pdf").write_bytes(b"%PDF-fake")
            result = run(root, "--dry-run")
            entries = parse(result)
            self.assertTrue(entries[0]["output"].endswith(".txt"), entries)

    def test_existing_md_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "papers"
            root.mkdir()
            pdf = root / "article.pdf"
            md = root / "article.md"
            pdf.write_bytes(b"%PDF-fake")
            md.write_text("---\ntitle: keep\n---\n\nkeep me\n", encoding="utf-8")
            pdf_before = pdf.read_bytes()
            md_before = md.read_bytes()

            dry = run(root, "--format", "md", "--dry-run")
            self.assertEqual(parse(dry)[0]["status"], "skipped_existing", dry.stdout)
            actual = run(root, "--format", "md")
            self.assertEqual(parse(actual)[0]["status"], "skipped_existing", actual.stdout)
            self.assertEqual(md.read_bytes(), md_before)
            self.assertEqual(pdf.read_bytes(), pdf_before)

    def test_verify_ok_without_false_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "papers"
            root.mkdir()
            (root / "a.pdf").write_bytes(b"PDF-BYTES-A")
            text = "first line\nsecond line\n"
            (root / "a.md").write_text(
                "---\n"
                "source_path: raw/papers/a.pdf\n"
                "ingested: 2026-10-14\n"
                f"source_sha256: {hashlib.sha256(b'PDF-BYTES-A').hexdigest()}\n"
                f"text_sha256: {sha_text(text)}\n"
                "extractor: pymupdf test\n"
                "---\n\n" + text,
                encoding="utf-8",
            )
            before = (root / "a.md").read_bytes()
            result = run(root, "--verify")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            entry = parse(result)[0]
            self.assertEqual(entry["status"], "ok", entry)
            self.assertEqual(entry["source_status"], "ok", entry)
            self.assertEqual((root / "a.md").read_bytes(), before)

    def test_verify_tolerates_legacy_sha256_variants(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "papers"
            root.mkdir()
            text = "alpha\nbeta\n"
            body = "\n\n" + text  # 旧提取示例的正文写法（分隔符后带前导换行）
            # ① 旧批量修复口径：对“含前导换行”的正文算哈希
            (root / "b.md").write_text(
                "---\n"
                f"sha256: {sha_raw(body)}\n"
                "---" + body,
                encoding="utf-8",
            )
            # ② 旧 PDF 示例口径：对纯提取文本（无前导换行）算哈希
            (root / "c.md").write_text(
                "---\n"
                f"sha256: {sha_text(text)}\n"
                "---" + body,
                encoding="utf-8",
            )
            result = run(root, "--verify")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            entries = {e["file"]: e for e in parse(result)}
            self.assertEqual(entries["b.md"]["status"], "legacy_ok", entries["b.md"])
            self.assertEqual(entries["c.md"]["status"], "legacy_ok", entries["c.md"])
            self.assertIn("迁移为 text_sha256", entries["b.md"].get("note", ""))

    def test_verify_detects_real_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "papers"
            root.mkdir()
            body_text = "edited text\n"
            (root / "d.md").write_text(
                "---\n"
                f"text_sha256: {sha_text('original text')}\n"
                "---\n\n"
                + body_text,
                encoding="utf-8",
            )
            result = run(root, "--verify")
            self.assertEqual(result.returncode, 1, result.stdout)
            entry = parse(result)[0]
            self.assertEqual(entry["status"], "drift", entry)
            self.assertEqual(entry["text_sha256_now"], sha_text(body_text))

    def test_verify_detects_source_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "papers"
            root.mkdir()
            (root / "e.pdf").write_bytes(b"REAL-BYTES")
            text = "body\n"
            (root / "e.md").write_text(
                "---\n"
                "source_path: raw/papers/e.pdf\n"
                f"source_sha256: {hashlib.sha256(b'OTHER-BYTES').hexdigest()}\n"
                f"text_sha256: {sha_text(text)}\n"
                "---\n\n" + text,
                encoding="utf-8",
            )
            result = run(root, "--verify")
            self.assertEqual(result.returncode, 1, result.stdout)
            entry = parse(result)[0]
            self.assertEqual(entry["status"], "source_drift", entry)
            self.assertEqual(entry["source_status"], "drift", entry)

    def test_verify_missing_hash_is_informational(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "papers"
            root.mkdir()
            (root / "f.md").write_text(
                "---\ntitle: 无哈希旧文件\n---\n\n正文\n", encoding="utf-8"
            )
            result = run(root, "--verify")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(parse(result)[0]["status"], "missing_hash")


if __name__ == "__main__":
    unittest.main()
