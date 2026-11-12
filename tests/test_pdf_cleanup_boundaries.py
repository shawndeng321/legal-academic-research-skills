"""Conservative PDF cleanup preserves words, lists and unrelated sections."""
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'legal-research-wiki/scripts/clean_pdf_artifacts.py'
spec = importlib.util.spec_from_file_location('pdf_cleanup', SCRIPT)
cleaner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleaner)


class CleanupTests(unittest.TestCase):
    def test_word_boundaries_and_continuous_chinese_lines(self):
        for section in ('摘要', '主要结论', '关键词'):
            with self.subTest(section=section):
                source = f'## {section}\n\nburden of\nproof\n\n中文自然\n断行继续\n合并。\n'
                self.assertEqual(cleaner.clean_pdf_artifacts(source),
                                 f'## {section}\n\nburden of proof\n\n中文自然断行继续合并。\n')

    def test_lists_headings_tables_and_uncertain_hyphens_stay_separate(self):
        bodies = ['1. 第一项\n2. 第二项\n3. 第三项',
                  '- 第一项\n- 第二项', '（一）第一项\n（二）第二项',
                  '正文。\n### 小标题\n新段落', '| 甲 |\n|---|\n| 乙 |',
                  'co-\noperate', '第一段。\n第二段。']
        for body in bodies:
            with self.subTest(body=body):
                source = '## 核心论点\n\n' + body + '\n'
                self.assertEqual(cleaner.clean_pdf_artifacts(source), source)

    def test_numbered_heading_followed_by_prose_keeps_boundary(self):
        for title in ('（一）适用条件', '(一)适用条件', '1. Applicable conditions', '- Applicable conditions'):
            with self.subTest(title=title):
                text = '## 核心论点\n\n' + title + '\n应当审查相关材料。\n'
                self.assertEqual(cleaner.clean_pdf_artifacts(text), text)

    def test_mixed_words_keep_separation(self):
        text = '## 摘要\n\n适用 burden of\nproof，结合中文\n论证。\n'
        self.assertEqual(cleaner.clean_pdf_artifacts(text), '## 摘要\n\n适用 burden of proof，结合中文论证。\n')

    def test_cli_preview_backup_and_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = root / 'pages'
            pages.mkdir()
            page = pages / '合成.md'
            before = ('---\ntitle: unchanged\n---\n## 摘要\n\n【摘要】burden of\nproof\n\n'
                      '## 核心论点\n\n1. 第一项\n2. 第二项\n（一）适用条件\n应当审查相关材料。\n\n## 其他\n\n【原文】保留\n断行\n')
            page.write_text(before, encoding='utf-8')
            original = page.read_bytes()
            pdf = pages / '原件.pdf'
            pdf.write_bytes(b'original-pdf')
            def run(*flags):
                return subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), str(pages), *flags],
                                      capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run('--dry-run').returncode, 0)
            self.assertEqual(page.read_bytes(), original)
            self.assertEqual(run('--backup-dir', str(root / 'backup')).returncode, 0)
            self.assertEqual((root / 'backup/合成.md').read_bytes(), original)
            after = page.read_text(encoding='utf-8')
            self.assertIn('burden of proof', after)
            self.assertIn('1. 第一项\n2. 第二项', after)
            self.assertIn('（一）适用条件\n应当审查相关材料。', after)
            self.assertEqual(after.split('## 其他')[1], before.split('## 其他')[1])
            self.assertEqual(after.split('## 摘要')[0], before.split('## 摘要')[0])
            self.assertEqual(pdf.read_bytes(), b'original-pdf')


if __name__ == '__main__':
    unittest.main()
