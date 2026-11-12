"""Daily summary must expose coverage gaps and subprocess failures."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'legal-wiki-audit-repair/scripts/daily_check.py'
RESEARCH = ROOT / 'legal-research-wiki'


class DailyCoverageTests(unittest.TestCase):
    def run_daily(self, wiki, *flags):
        p = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), str(wiki), '--json', *flags],
                           capture_output=True, text=True, encoding='utf-8')
        self.assertTrue(p.stdout.strip(), p.stderr)
        return p.returncode, json.loads(p.stdout)

    def test_repeated_unknown_tag_and_wrong_hash_never_claim_complete(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            (wiki / 'entities').mkdir()
            (wiki / 'raw/papers').mkdir(parents=True)
            for name in ('a', 'b'):
                (wiki / f'entities/{name}.md').write_text(
                    f'---\ntitle: {name}\ncreated: 2026-01-01\nupdated: 2026-01-01\ntype: concept\ntags: [unknown]\nsources: []\n---\n[[a]] [[b]]\n', encoding='utf-8')
            (wiki / 'SCHEMA.md').write_text('### A. 标签\n- known\n', encoding='utf-8')
            (wiki / 'index.md').write_text('总页数：2\n[[a]] [[b]]\n', encoding='utf-8')
            (wiki / 'log.md').write_text('raw/papers/a.md\n', encoding='utf-8')
            (wiki / 'raw/papers/a.pdf').write_bytes(b'original')
            body = 'body\n'
            (wiki / 'raw/papers/a.md').write_text(
                '---\nsource_path: raw/papers/a.pdf\nsource_sha256: ' + '0' * 64 +
                '\ntext_sha256: ' + hashlib.sha256(body.encode()).hexdigest() + '\n---\n\n' + body, encoding='utf-8')
            before = {p.relative_to(wiki).as_posix(): p.read_bytes() for p in wiki.rglob('*') if p.is_file()}
            code, result = self.run_daily(wiki, '--research-skill', str(RESEARCH))
            self.assertEqual(code, 1)
            checks = {row['id']: row for row in result['coverage']}
            self.assertEqual(checks['tags']['status'], 'partial')
            self.assertIn('重复', checks['tags']['note'])
            self.assertEqual(checks['hashes']['status'], 'issues')
            self.assertFalse(result['complete'])
            self.assertTrue(any(r.get('source_status') == 'drift' for r in result['tools']['hashes']['result']))
            self.assertEqual(before, {p.relative_to(wiki).as_posix(): p.read_bytes() for p in wiki.rglob('*') if p.is_file()})

    def test_absent_optional_skill_and_empty_scope_are_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, result = self.run_daily(Path(tmp))
            self.assertEqual(code, 2)
            checks = {row['id']: row for row in result['coverage']}
            self.assertEqual(checks['hashes']['status'], 'not_checked')
            self.assertFalse(result['complete'])

    def test_legal_subchecks_cannot_pass_from_privacy_or_one_type_only(self):
        for kinds, expected in [(('concept',), 'not_checked'), (('norm',), 'partial'), (('case',), 'partial'), (('norm', 'case'), 'passed')]:
            with self.subTest(kinds=kinds), tempfile.TemporaryDirectory() as tmp:
                wiki = Path(tmp)
                (wiki / 'entities').mkdir()
                (wiki / 'wiki-audit.config.json').write_text(json.dumps({'privacy': {'enabled': True}}), encoding='utf-8')
                for kind in kinds:
                    (wiki / f'entities/{kind}.md').write_text(
                        f'---\ntitle: {kind}\ntype: {kind}\ntags: [known]\ncreated: 2026-01-01\nupdated: 2026-01-01\n'
                        '效力状态: 现行有效\n核验日期: 2099-01-01\ndocket: 合成案号001\n---\n正文\n', encoding='utf-8')
                before = {str(p): p.read_bytes() for p in wiki.rglob('*') if p.is_file()}
                code, result = self.run_daily(wiki)
                row = next(r for r in result['coverage'] if r['id'] == 'legal')
                self.assertEqual(row['status'], expected, row)
                if expected != 'passed':
                    self.assertIn('legal', result['summary']['outstanding'])
                    self.assertIn('未检查', row['note'])
                self.assertEqual(before, {str(p): p.read_bytes() for p in wiki.rglob('*') if p.is_file()})

    def test_tool_failure_and_missing_dependency_are_retained(self):
        self.assertTrue(SCRIPT.is_file())
        spec = importlib.util.spec_from_file_location('daily_summary', SCRIPT)
        daily = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(daily)
        for message in ('ImportError: No module named yaml', 'unexpected execution failure'):
            with self.subTest(message=message):
                with mock.patch.object(daily.subprocess, 'run', return_value=subprocess.CompletedProcess([], 2, '', message)):
                    result = daily.run_tool([sys.executable, 'tool.py'])
                self.assertEqual(result['status'], 'not_checked')
                self.assertIn(message, result['error'])

    def test_invalid_json_and_timeout_are_incomplete(self):
        self.assertTrue(SCRIPT.is_file())
        spec = importlib.util.spec_from_file_location('daily_summary_errors', SCRIPT)
        daily = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(daily)
        with mock.patch.object(daily.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'invalid', '')):
            self.assertEqual(daily.run_tool(['tool'])['status'], 'not_checked')
        with mock.patch.object(daily.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['tool'], 30)):
            self.assertEqual(daily.run_tool(['tool'])['status'], 'not_checked')


if __name__ == '__main__':
    unittest.main()
