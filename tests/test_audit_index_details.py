"""Structured findings retain every missing and ghost index path."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from tests.test_audit_relations import audit_module


class IndexDetailTests(unittest.TestCase):
    def test_index_path_counts_at_display_boundary(self):
        for count in (0, 3, 8, 11):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'entities').mkdir()
                missing = [f'entities/page-{i:02}.md' for i in range(count)]
                ghosts = [f'entities/ghost-{i:02}' for i in range(count)]
                for rel in missing:
                    (root / rel).write_text('# page\n', encoding='utf-8')
                (root / 'index.md').write_text('\n'.join('[[' + p + ']]' for p in ghosts), encoding='utf-8')
                obj = audit_module.Audit(root, audit_module.load_config(root))
                obj.collect()
                obj.check_index()
                result = audit_module.build_result(obj, False, 1 if count else 0)
                by_rule = {f['rule']: f for f in result['findings']}
                if not count:
                    self.assertNotIn('IDX-02', by_rule)
                    self.assertNotIn('IDX-03', by_rule)
                    continue
                for rule, expected in [('IDX-02', missing), ('IDX-03', ghosts)]:
                    self.assertEqual(by_rule[rule]['paths'], expected)
                    self.assertEqual(by_rule[rule]['path_count'], count)
                    for path in expected:
                        self.assertIn(path, by_rule[rule]['message'])
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    audit_module.print_report(obj)
                if count > 8:
                    self.assertIn('另有 3 项', out.getvalue())
                    self.assertIn('--json', out.getvalue())


if __name__ == '__main__':
    unittest.main()
