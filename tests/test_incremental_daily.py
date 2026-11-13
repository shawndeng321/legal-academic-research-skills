"""Incremental machine checks must agree with fresh full checks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import hashlib
import importlib.util
from unittest import mock
from datetime import date, timedelta

from tests.test_audit_snapshot import ROOT, make_wiki, contents

SNAPSHOT = ROOT / 'legal-wiki-audit-repair/scripts/audit_snapshot.py'
DAILY = ROOT / 'legal-wiki-audit-repair/scripts/daily_check.py'


def comparable(result):
    result = {k: v for k, v in result.items() if k != 'execution'}
    result['findings'] = sorted(result['findings'], key=lambda row: json.dumps(row, sort_keys=True))
    return result


class IncrementalTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.parent = Path(tmp.name)
        self.wiki = self.parent / 'wiki'
        make_wiki(self.wiki)
        self.receipt = self.parent / 'baseline.json'

    def run_check(self, *flags, script=SNAPSHOT):
        proc = subprocess.run([sys.executable, '-X', 'utf8', str(script), str(self.wiki),
                               '--json', *map(str, flags)], capture_output=True, text=True, encoding='utf-8')
        self.assertTrue(proc.stdout.strip(), proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, result['summary']['exit_code'])
        return result

    def test_changed_page_rechecks_global_relationships_and_matches_full(self):
        self.run_check('--save-state', self.receipt)
        path = self.wiki / 'entities/a.md'
        stamp = path.stat()
        path.write_text(path.read_text(encoding='utf-8').replace('# a', '# changed') + '\n[[missing]]\n', encoding='utf-8')
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        before = contents(self.wiki)
        incremental = self.run_check('--incremental', '--baseline', self.receipt)
        self.assertEqual(incremental['execution']['mode'], 'incremental')
        self.assertEqual(incremental['execution']['checks_executed'], [3, 4, 5, 7])
        self.assertEqual(incremental['execution']['checks_reused'], [1, 2, 6])
        self.assertEqual(comparable(incremental), comparable(self.run_check('--force-full')))
        self.assertEqual(incremental['summary']['exit_code'], 1)
        self.assertEqual(contents(self.wiki), before)

    def test_daily_entry_preserves_manual_gaps_and_only_saves_explicitly(self):
        before = contents(self.wiki)
        first = self.run_check('--save-state', self.receipt, script=DAILY)
        self.assertTrue(self.receipt.is_file())
        self.assertEqual(first['summary']['exit_code'], 2)
        self.assertFalse(first['complete'])
        second = self.run_check('--incremental', '--baseline', self.receipt, script=DAILY)
        self.assertEqual(second['tools']['structure']['result']['execution']['mode'], 'reused')
        self.assertEqual(first['coverage'], second['coverage'])
        self.assertEqual(contents(self.wiki), before)

    def rewrite_receipt(self, mutate):
        document = json.loads(self.receipt.read_text(encoding='utf-8'))
        mutate(document['state'])
        data = json.dumps(document['state'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
        document['sha256'] = hashlib.sha256(data).hexdigest()
        self.receipt.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')

    def test_periodic_full_check_cannot_be_postponed_by_reuse(self):
        self.run_check('--save-state', self.receipt)
        self.rewrite_receipt(lambda s: s.update(full_day=(date.today()-timedelta(days=7)).isoformat()))
        result = self.run_check('--incremental', '--baseline', self.receipt)
        self.assertEqual(result['execution']['mode'], 'full')
        self.assertEqual(result['execution']['reason'], 'periodic_full_due')

    def test_invalid_receipt_structure_falls_back_to_full(self):
        self.run_check('--save-state', self.receipt)
        original = self.receipt.read_bytes()
        for mutate in (lambda s: s['result'].pop('findings'),
                       lambda s: s['result']['summary'].update(broken=99),
                       lambda s: s['result']['checks'][0].pop('status'),
                       lambda s: s.update(day='2099-01-01', full_day='2099-01-01')):
            with self.subTest(mutate=mutate):
                self.receipt.write_bytes(original)
                self.rewrite_receipt(mutate)
                result = self.run_check('--incremental', '--baseline', self.receipt)
                self.assertEqual(result['execution']['mode'], 'full')
                self.assertEqual(result['execution']['reason'], 'invalid_baseline')

    def test_raw_page_overlap_never_reuses_raw_findings(self):
        (self.wiki/'wiki-audit.config.json').write_text(json.dumps({'page_dirs': ['entities', 'raw']}), encoding='utf-8')
        self.run_check('--save-state', self.receipt)
        path = self.wiki/'raw/evidence.md'
        path.write_text(path.read_text(encoding='utf-8')+'\nContent extracted\n', encoding='utf-8')
        result = self.run_check('--incremental', '--baseline', self.receipt)
        self.assertEqual(comparable(result), comparable(self.run_check('--force-full')))
        self.assertEqual(result['execution']['mode'], 'full')

    def test_configuration_can_reinclude_default_skipped_directories(self):
        (self.wiki/'wiki-audit.config.json').write_text(json.dumps({'exclude_dirs': []}), encoding='utf-8')
        backup = self.wiki/'entities/backup'
        backup.mkdir()
        page = backup/'sample.md'
        page.write_bytes((self.wiki/'entities/a.md').read_bytes())
        self.run_check('--save-state', self.receipt)
        page.write_text(page.read_text(encoding='utf-8')+'\n[[missing]]\n', encoding='utf-8')
        result = self.run_check('--incremental', '--baseline', self.receipt)
        self.assertNotEqual(result['execution']['mode'], 'reused')
        self.assertEqual(comparable(result), comparable(self.run_check('--force-full')))

    def test_all_global_changes_fall_back_and_match_full(self):
        for change in ('delete', 'rename', 'move', 'new', 'schema', 'config', 'index', 'log', 'raw', 'empty'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                self.wiki = Path(tmp)/'wiki'
                self.receipt = Path(tmp)/'baseline.json'
                make_wiki(self.wiki)
                self.run_check('--save-state', self.receipt)
                page = self.wiki/'entities/a.md'
                if change == 'delete':
                    page.unlink()
                elif change in ('rename', 'move'):
                    target = self.wiki/('entities/new.md' if change == 'rename' else 'concepts/a.md')
                    target.parent.mkdir(exist_ok=True)
                    page.rename(target)
                elif change == 'new':
                    (self.wiki/'entities/new.md').write_bytes(page.read_bytes())
                elif change == 'config':
                    (self.wiki/'wiki-audit.config.json').write_text('{"privacy":{"enabled":true}}', encoding='utf-8')
                elif change == 'empty':
                    page.write_bytes(b'')
                else:
                    rel = {'schema':'SCHEMA.md', 'index':'index.md', 'log':'log.md', 'raw':'raw/evidence.md'}[change]
                    target = self.wiki/rel
                    target.write_text(target.read_text(encoding='utf-8')+'\nchanged\n', encoding='utf-8')
                before = contents(self.wiki)
                result = self.run_check('--incremental', '--baseline', self.receipt)
                if change != 'empty':
                    self.assertEqual(result['execution']['mode'], 'full')
                self.assertEqual(comparable(result), comparable(self.run_check('--force-full')))
                self.assertEqual(contents(self.wiki), before)

    def load_engine(self):
        with mock.patch.object(sys, 'path', [str(SNAPSHOT.parent), *sys.path]):
            spec = importlib.util.spec_from_file_location('incremental_test_engine', SNAPSHOT)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return module

    def test_next_day_rechecks_norm_expiry_and_missing_dependency_stops(self):
        engine = self.load_engine()
        verified = date.today()-timedelta(days=365)
        page = self.wiki/'entities/c.md'
        # Quote the date so patching datetime.date does not change PyYAML's
        # native-date isinstance behavior in the audit's _as_date helper.
        page.write_text(page.read_text(encoding='utf-8').replace(
            '核验日期: '+date.today().isoformat(), "核验日期: '"+verified.isoformat()+"'"), encoding='utf-8')
        first = engine.run(self.wiki, save_state=self.receipt)
        self.assertFalse(any(f['rule']=='NORM-02' for f in first['findings']))
        today = date.today()
        class Tomorrow(date):
            @classmethod
            def today(cls):
                return today+timedelta(days=1)
        with mock.patch.object(engine, 'date', Tomorrow), mock.patch.object(engine.deep, 'date', Tomorrow):
            result = engine.run(self.wiki, baseline=self.receipt, incremental=True)
            self.assertEqual(result['execution']['reason'], 'date_changed')
            self.assertEqual(result['execution']['mode'], 'full')
            self.assertTrue(any(f['rule']=='NORM-02' for f in result['findings']))
            self.assertEqual(comparable(result), comparable(engine.run(self.wiki, force_full=True)))
        with mock.patch.object(engine.deep, 'yaml', None):
            with self.assertRaises(ValueError):
                engine.run(self.wiki, baseline=self.receipt, incremental=True)

    def test_read_or_mid_scan_failure_never_saves_a_receipt(self):
        engine = self.load_engine()
        with mock.patch.object(engine, 'snapshot', side_effect=PermissionError('synthetic unreadable input')):
            with self.assertRaises(PermissionError):
                engine.run(self.wiki, save_state=self.receipt)
        self.assertFalse(self.receipt.exists())
        original = engine.full_audit
        def changed_during_scan(*args, **kwargs):
            result = original(*args, **kwargs)
            (self.wiki/'log.md').write_text('changed during scan', encoding='utf-8')
            return result
        with mock.patch.object(engine, 'full_audit', side_effect=changed_during_scan):
            result = engine.run(self.wiki, save_state=self.receipt)
        self.assertFalse(result['execution']['snapshot_stable'])
        self.assertFalse(result['execution']['machine_scan_complete'])
        self.assertEqual(result['summary']['exit_code'], 2)
        self.assertFalse(self.receipt.exists())

    def test_checker_or_options_changes_invalidate_receipt(self):
        self.run_check('--save-state', self.receipt)
        self.rewrite_receipt(lambda s: s['engine'].update(pyyaml='different'))
        result = self.run_check('--incremental', '--baseline', self.receipt)
        self.assertEqual(result['execution']['reason'], 'checker_options_or_wiki_changed')
        self.assertEqual(result['execution']['mode'], 'full')
        for flags in (('--strict',), ('--privacy',), ('--force-full',)):
            result = self.run_check('--incremental', '--baseline', self.receipt, *flags)
            self.assertEqual(result['execution']['mode'], 'full')

    def test_configured_external_scope_is_incomplete_and_never_cached(self):
        (self.wiki/'wiki-audit.config.json').write_text(json.dumps({'page_dirs':['entities','../outside']}), encoding='utf-8')
        result = self.run_check('--save-state', self.receipt)
        self.assertEqual(result['summary']['exit_code'], 2)
        self.assertFalse(result['execution']['machine_scan_complete'])
        self.assertFalse(self.receipt.exists())

    def test_changed_target_rechecks_inbound_anchors_and_legal_dependencies(self):
        a = self.wiki/'entities/a.md'
        a.write_text(a.read_text(encoding='utf-8')+'\n[[entities/c#c]]\n', encoding='utf-8')
        self.run_check('--save-state', self.receipt)
        norm = self.wiki/'entities/c.md'
        norm.write_text(norm.read_text(encoding='utf-8').replace('# c', '# changed').replace('效力状态: 有效', '效力状态: 已废止'), encoding='utf-8')
        result = self.run_check('--incremental', '--baseline', self.receipt)
        self.assertEqual(result['execution']['mode'], 'incremental')
        rules = {r['rule'] for r in result['findings']}
        self.assertTrue({'LINK-06','NORM-03'} <= rules)
        self.assertEqual(comparable(result), comparable(self.run_check('--force-full')))


if __name__ == '__main__':
    unittest.main()
