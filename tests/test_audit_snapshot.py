"""Snapshot reuse must be tied to actual inputs, not mtime or a past 'passed'."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'legal-wiki-audit-repair/scripts/audit_snapshot.py'


def make_wiki(root):
    files = {'SCHEMA.md': '## Tag Taxonomy\n共同\n',
             'index.md': '总页数：3\n[[entities/a]] [[entities/b]] [[entities/c]]\n',
             'log.md': '# 操作日志\n\n## [2026-01-01] 摄入\nraw/evidence.md\n',
             'raw/evidence.md': '---\ntitle: 合成来源\n---\n用于程序校验的合成原材料。\n',
             'raw/assets/sample.png': 'synthetic fixture, not an image'}
    for key, kind in [('a', 'concept'), ('b', 'case'), ('c', 'norm')]:
        extra = ('效力状态: 有效\n核验日期: '+date.today().isoformat()+'\n') if kind == 'norm' else ''
        files['entities/'+key+'.md'] = ('---\ntitle: '+key+'\ncreated: 2026-01-01\nupdated: 2026-01-01\n'
            'type: '+kind+'\ntags: [共同]\nsources: [raw/evidence.md]\n'+extra+'---\n# '+key+'\n'
            + ' '.join('[[entities/'+other+']]' for other in 'abc' if other != key)
            + '\n![[raw/assets/sample.png]]\n有依据的合成说明。\n')
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')


def contents(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name)
        self.wiki = self.parent / 'wiki'
        make_wiki(self.wiki)
        self.receipt = self.parent / 'full.json'

    def run_check(self, *args):
        self.assertTrue(SCRIPT.is_file(), 'snapshot-bound audit entry is not implemented')
        proc = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), str(self.wiki), '--json', *map(str,args)],
                              capture_output=True, text=True, encoding='utf-8')
        self.assertIn(proc.returncode, (0, 1, 2), proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result['summary']['exit_code'], proc.returncode)
        return result

    def test_identical_final_state_reuses_and_leaves_vault_untouched(self):
        before = contents(self.wiki)
        first = self.run_check('--save-state', self.receipt)
        self.assertEqual(first['summary']['exit_code'], 0)
        self.assertEqual(first['execution']['mode'], 'full')
        second = self.run_check('--baseline', self.receipt)
        self.assertEqual(second['execution']['mode'], 'reused')
        self.assertEqual(second['execution']['checks_executed'], [])
        self.assertEqual(second['execution']['checks_reused'], list(range(1, 8)))
        self.assertEqual({k:v for k,v in first.items() if k != 'execution'},
                         {k:v for k,v in second.items() if k != 'execution'})
        self.assertEqual(before, contents(self.wiki))

    def test_changed_content_even_with_same_mtime_invalidates(self):
        self.run_check('--save-state', self.receipt)
        path = self.wiki / 'entities/a.md'
        stamp = path.stat()
        path.write_text(path.read_text(encoding='utf-8') + '\n[[missing]]\n', encoding='utf-8')
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        before = contents(self.wiki)
        result = self.run_check('--baseline', self.receipt)
        self.assertEqual(result['execution']['mode'], 'full')
        self.assertEqual(result['summary']['exit_code'], 1)
        self.assertTrue(any(f['rule'] == 'LINK-01' for f in result['findings']))
        self.assertEqual(before, contents(self.wiki))

    def test_index_log_schema_and_namespace_change_invalidate(self):
        self.run_check('--save-state', self.receipt)
        original = contents(self.wiki)
        for rel in ['index.md', 'log.md', 'SCHEMA.md', 'entities/a.md']:
            with self.subTest(rel=rel):
                path = self.wiki / rel
                path.write_bytes(original[rel] + b'\nchanged\n')
                result = self.run_check('--baseline', self.receipt)
                self.assertEqual(result['execution']['mode'], 'full')
                self.assertIn(rel, result['execution']['changed_files'])
                path.write_bytes(original[rel])
        (self.wiki / 'entities/a.md').rename(self.wiki / 'entities/renamed.md')
        result = self.run_check('--baseline', self.receipt)
        self.assertEqual(result['execution']['mode'], 'full')
        self.assertTrue({'entities/a.md','entities/renamed.md'} <= set(result['execution']['changed_files']))

    def test_corrupt_or_other_options_fall_back_without_overwriting_receipt(self):
        self.run_check('--save-state', self.receipt)
        previous = self.receipt.read_bytes()
        result = self.run_check('--baseline', self.receipt, '--strict')
        self.assertEqual(result['execution']['mode'], 'full')
        self.assertEqual(self.receipt.read_bytes(), previous)
        self.receipt.write_text('{bad json', encoding='utf-8')
        result = self.run_check('--baseline', self.receipt)
        self.assertEqual(result['execution']['reason'], 'invalid_baseline')
        self.assertEqual(result['execution']['mode'], 'full')

    def test_saving_requires_new_file_outside_wiki_and_never_changes_existing_files(self):
        before = contents(self.wiki)
        result = self.run_check('--save-state', self.wiki/'state.json')
        self.assertEqual(result['summary']['exit_code'], 2)
        self.assertEqual(before, contents(self.wiki))
        self.receipt.write_text('keep this', encoding='utf-8')
        result = self.run_check('--save-state', self.receipt)
        self.assertEqual(result['summary']['exit_code'], 2)
        self.assertEqual(self.receipt.read_text(encoding='utf-8'), 'keep this')

    def test_parse_failure_is_not_cached_or_reported_complete(self):
        (self.wiki/'entities/a.md').write_text('---\ntitle: [broken\n---\n', encoding='utf-8')
        result = self.run_check('--save-state', self.receipt)
        self.assertFalse(result['execution']['machine_scan_complete'])
        self.assertFalse(self.receipt.exists())
        self.assertNotEqual(result['summary']['exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
