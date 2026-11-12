"""Compact/verbose reports preserve the same findings and JSON totals."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from tests.test_audit_relations import audit_module


class ReportTests(unittest.TestCase):
    def test_compact_hides_passes_but_preserves_all_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = audit_module.Audit(Path(tmp), audit_module.load_config(Path(tmp)))
            obj.add('LINK-9', 'pass', '链接', 'all', 'all', 'PASS-MESSAGE')
            obj.add('LINK-01', 'broken', '链接', 'entities/a.md', 'L1', 'MISSING')
            paths = [f'entities/item-{n:02}.md' for n in range(11)]
            obj.add('IDX-02', 'broken', '结构', 'index.md', 'items', '未索引：' + '、'.join(paths), paths=paths)
            obj.check_stats = {1: {'status': 'fail'}, 4: {'status': 'fail'}}
            before = audit_module.build_result(obj, False, 1)
            compact = io.StringIO()
            with contextlib.redirect_stdout(compact):
                audit_module.print_report(obj)
            self.assertNotIn('PASS-MESSAGE', compact.getvalue())
            full = io.StringIO()
            with contextlib.redirect_stdout(full):
                audit_module.print_report(obj, verbose=True)
            self.assertIn('PASS-MESSAGE', full.getvalue())
            for path in paths:
                self.assertIn(path, full.getvalue())
            for out in (compact.getvalue(), full.getvalue()):
                self.assertIn('[IDX-02]', out)
                self.assertIn('[LINK-01]', out)
                self.assertIn('阻断项：2', out)
                self.assertIn('未检查', out)
            self.assertIn('另有 3 项', compact.getvalue())
            self.assertIn('--json', compact.getvalue())
            self.assertEqual(before, audit_module.build_result(obj, False, 1))


if __name__ == '__main__':
    unittest.main()
