"""Existing extraction files are reusable only with matching evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
try:
    import pymupdf
except ImportError:
    pymupdf = None

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'legal-research-wiki/scripts/batch_extract_papers.py'


@unittest.skipIf(pymupdf is None, "需要 PyMuPDF 执行真实合成PDF回归")
class ReuseTests(unittest.TestCase):
    def make_pdf(self, root, text='Synthetic source text.'):
        pdf = root / 'a.pdf'
        doc = pymupdf.open()
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
        doc.save(pdf)
        doc.close()
        return pdf

    def run_extract(self, root, *flags):
        p = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), str(root), *flags],
                           capture_output=True, text=True, encoding='utf-8')
        return p.returncode, json.loads(p.stdout)

    def test_unchanged_extraction_reuses_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_pdf(root)
            self.assertEqual(self.run_extract(root, '--format', 'md')[0], 0)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            code, rows = self.run_extract(root, '--format', 'md')
            self.assertEqual(code, 0)
            self.assertEqual(rows[0]['status'], 'reused')
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_nested_relative_source_reuses_in_separate_output_tree(self):
        for derived in (False, True):
            with self.subTest(derived=derived), tempfile.TemporaryDirectory() as tmp:
                wiki = Path(tmp) / '知识库 空格'
                folder = wiki / 'raw/papers/topic/year'
                folder.mkdir(parents=True)
                self.make_pdf(folder)
                flags = ['--format', 'md']
                output = Path(tmp) / '另一处 派生/very/deep/output'
                if derived:
                    flags += ['--out-dir', str(output)]
                command = [sys.executable, '-X', 'utf8', str(SCRIPT), 'raw/papers', *flags]
                def run():
                    proc = subprocess.run(command, cwd=wiki, capture_output=True, text=True, encoding='utf-8')
                    return proc.returncode, json.loads(proc.stdout)
                self.assertEqual(run()[0], 0)
                before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                          for p in Path(tmp).rglob('*') if p.is_file()}
                code, rows = run()
                self.assertEqual(code, 0, rows)
                self.assertEqual(rows[0]['status'], 'reused')
                self.assertEqual(before, {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                                         for p in Path(tmp).rglob('*') if p.is_file()})

    def test_changed_original_needs_reextraction_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = self.make_pdf(root)
            self.run_extract(root, '--format', 'md')
            original_md = (root / 'a.md').read_bytes()
            pdf.write_bytes(pdf.read_bytes() + b'\n% changed')
            code, rows = self.run_extract(root, '--format', 'md')
            self.assertEqual(code, 1)
            self.assertEqual(rows[0]['status'], 'needs_reextract')
            self.assertEqual((root / 'a.md').read_bytes(), original_md)

    def test_empty_or_legacy_companion_not_reused(self):
        for content, suffix in [('', 'md'), ('old extraction', 'txt'), ('---\ntitle: old\n---\nold', 'md')]:
            with self.subTest(suffix=suffix, content=content), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.make_pdf(root)
                path = root / ('a.' + suffix)
                path.write_text(content, encoding='utf-8')
                before = path.read_bytes()
                code, rows = self.run_extract(root, '--format', suffix)
                self.assertEqual(code, 2)
                self.assertEqual(rows[0]['status'], 'unverified_existing')
                self.assertEqual(path.read_bytes(), before)

    def test_missing_source_location_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_pdf(root)
            self.run_extract(root, '--format', 'md')
            path = root / 'a.md'
            text = path.read_text(encoding='utf-8')
            source_line = next(line for line in text.splitlines() if line.startswith('source_path:'))
            path.write_text(text.replace(source_line, 'source_path: missing/a.pdf'), encoding='utf-8')
            code, rows = self.run_extract(root, '--format', 'md')
            self.assertEqual(code, 2)
            self.assertEqual(rows[0]['status'], 'unverified_existing')

    def test_empty_pdf_is_pending_and_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_pdf(root, '')
            code, rows = self.run_extract(root, '--format', 'md')
            self.assertEqual(code, 2)
            self.assertEqual(rows[0]['status'], 'needs_ocr')
            code, rows = self.run_extract(root, '--format', 'md')
            self.assertEqual(code, 2)
            self.assertEqual(rows[0]['status'], 'unverified_existing')

    def test_changed_text_is_not_silently_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_pdf(root)
            self.run_extract(root, '--format', 'md')
            path = root / 'a.md'
            path.write_bytes(path.read_bytes() + b'changed')
            code, rows = self.run_extract(root, '--format', 'md')
            self.assertEqual(code, 1)
            self.assertEqual(rows[0]['status'], 'needs_reextract')


if __name__ == '__main__':
    unittest.main()
