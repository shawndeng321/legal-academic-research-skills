"""Quantity is an observation; malformed and unsupported relations still fail."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import json
from tests.test_audit_snapshot import make_wiki, contents, ROOT

AUDIT = ROOT / 'legal-wiki-audit-repair/scripts/multimodal_audit.py'
INSERT = ROOT / 'legal-wiki-audit-repair/scripts/insert_norm_sections.py'


class LinkQuantityTests(unittest.TestCase):
    def test_one_real_outgoing_relation_is_nonblocking_in_strict_json_and_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_wiki(root)
            (root/'entities/c.md').unlink()
            for name in ('a', 'b'):
                p = root/'entities'/f'{name}.md'
                p.write_text(p.read_text(encoding='utf-8').replace('[[entities/c]]', ''), encoding='utf-8')
            (root/'index.md').write_text('总页数：2\n[[entities/a]] [[entities/b]]\n', encoding='utf-8')
            before = contents(root)
            for output in ('--json', '--verbose'):
                proc = subprocess.run([sys.executable, str(AUDIT), str(root), '--strict', output],
                                      capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(proc.returncode, 0, proc.stdout+proc.stderr)
                if output == '--json':
                    payload = json.loads(proc.stdout)
                    observations = [f for f in payload['findings'] if f['rule'] == 'LINK-08']
                    self.assertEqual(len(observations), 2)
                    self.assertTrue(all(f['severity'] == 'observation' for f in observations))
                    self.assertEqual(payload['summary']['observation'], 2)
                else:
                    self.assertIn('观察', proc.stdout)
            self.assertEqual(contents(root), before)

    def test_single_norm_with_evidence_can_be_previewed_and_inserted(self):
        self.check_norm_count(1)

    def test_more_than_four_supported_norms_are_allowed(self):
        self.check_norm_count(5)

    def test_empty_plan_and_missing_or_unexplained_norms_do_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'wiki'
            (root/'entities/法规范').mkdir(parents=True)
            (root/'concepts').mkdir()
            (root/'concepts/概念.md').write_text('# 概念\n\n## 相关概念\n\n正文。\n', encoding='utf-8')
            (root/'entities/法规范/有效.md').write_text('# 规范\n具体条文。\n', encoding='utf-8')
            plan = Path(tmp)/'plan.json'
            desc = '该条文规定了构成要件与例外情形并且有明确的适用前提，为本概念提供直接的规范依据'
            for items in ([], [['不存在',desc]], [['有效','']]):
                with self.subTest(items=items):
                    plan.write_text(json.dumps({'pages':{'concepts/概念.md':items}}, ensure_ascii=False), encoding='utf-8')
                    before = contents(root)
                    proc = subprocess.run([sys.executable, str(INSERT), str(root), '--plan', str(plan)], capture_output=True)
                    self.assertEqual(proc.returncode, 1)
                    self.assertEqual(contents(root), before)

    def check_norm_count(self, count):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent/'wiki'
            norms = root/'entities/法规范'
            norms.mkdir(parents=True)
            (root/'concepts').mkdir()
            page = root/'concepts/概念.md'
            page.write_text('---\ntitle: 概念\nupdated: 2026-01-01\n---\n# 概念\n\n## 相关概念\n\n原有内容。\n', encoding='utf-8')
            (root/'log.md').write_text('# 日志\n', encoding='utf-8')
            for n in range(count):
                (norms/f'规范{n}.md').write_text('# 合成规范\n用于核对构成要件的实际条文内容。\n', encoding='utf-8')
            desc = '本条明确相关构成要件和适用前提，为概念中的责任范围提供具体规范依据，条文已经回读核验'
            plan = parent/'plan.json'
            plan.write_text(json.dumps({'pages': {'concepts/概念.md': [[f'规范{n}',desc] for n in range(count)]}}, ensure_ascii=False), encoding='utf-8')
            command = [sys.executable, str(INSERT), str(root), '--plan', str(plan)]
            before = contents(root)
            preview = subprocess.run(command+['--dry-run'], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(preview.returncode, 0, preview.stdout+preview.stderr)
            self.assertEqual(contents(root), before)
            actual = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(actual.returncode, 0, actual.stdout+actual.stderr)
            changed = page.read_text(encoding='utf-8')
            self.assertIn('## 规范依据', changed)
            self.assertEqual(changed.count('——'+desc), count)
            self.assertIn('原有内容。', changed)
            self.assertEqual((root/'.maintenance/norm-reference/before/concepts/概念.md').read_bytes(), before['concepts/概念.md'])
            inserted = contents(root)
            again = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(again.returncode, 0, again.stdout+again.stderr)
            self.assertEqual(contents(root), inserted)


if __name__ == '__main__':
    unittest.main()
