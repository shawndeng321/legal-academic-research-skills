"""Count usable knowledge-page relations without weakening link checks."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('relation_audit', ROOT / 'legal-wiki-audit-repair/scripts/multimodal_audit.py')
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class RelationTests(unittest.TestCase):
    def check(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, body in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding='utf-8')
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            obj = audit_module.Audit(root, audit_module.load_config(root))
            obj.collect()
            obj.check_links()
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            return obj

    def test_self_attachment_and_navigation_do_not_supply_relations(self):
        obj = self.check({'entities/a.md': '# a\n[[a]] ![[raw/assets/x.png]] [[index]] [[entities/nav]]\n',
                          'entities/nav.md': '---\ntype: moc\n---\n[[a]]\n',
                          'raw/assets/x.png': 'image', 'index.md': '[[a]]\n'})
        rules = {(f.rule, f.path): f.message for f in obj.findings}
        self.assertIn(('LINK-07', 'entities/a.md'), rules)
        self.assertIn('0 < 2', rules[('LINK-08', 'entities/a.md')])
        self.assertEqual(obj.check_stats[4]['knowledge_edges'], 0)

    def test_other_page_counts_once_and_resolves_orphan(self):
        obj = self.check({'entities/a.md': '# a\n[[b]] [[b]]\n', 'entities/b.md': '# b\n[[a]]\n'})
        self.assertFalse(any(f.rule == 'LINK-07' for f in obj.findings))
        self.assertEqual(obj.check_stats[4]['knowledge_edges'], 2)
        self.assertTrue(all('1 < 2' in f.message for f in obj.findings if f.rule == 'LINK-08'))

    def test_invalid_links_still_reported_and_do_not_count(self):
        obj = self.check({'entities/a.md': '# a\n[[missing]] [[empty]] [[wrong/b]] [[b#absent]] [[dup]]\n',
                          'entities/b.md': '# b\n', 'entities/empty.md': '',
                          'entities/one/dup.md': '# dup\n', 'entities/two/dup.md': '# dup\n'})
        self.assertTrue({'LINK-01', 'LINK-02', 'LINK-03', 'LINK-05', 'LINK-06'} <= {f.rule for f in obj.findings})
        self.assertEqual(obj.check_stats[4]['knowledge_edges'], 0)
        self.assertTrue(any(f.rule == 'LINK-07' and f.path == 'entities/b.md' for f in obj.findings))


if __name__ == '__main__':
    unittest.main()
