"""Verification must distinguish complete results from missing evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'legal-research-wiki/scripts/batch_extract_papers.py'
spec = importlib.util.spec_from_file_location('extraction_verification', SCRIPT)
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def companion(root, *, source='raw/papers/a.pdf', source_hash=None, body='body\n', legacy=False):
    path = root / 'a.md'
    field = 'sha256' if legacy else 'text_sha256'
    fields = [f'{field}: {digest(body.encode())}']
    if source is not None:
        fields.append(f'source_path: {source}')
    if source_hash is not None:
        fields.append(f'source_sha256: {source_hash}')
    path.write_text('---\n' + '\n'.join(fields) + '\n---\n\n' + body, encoding='utf-8')
    return path


def run_verify(root):
    proc = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), str(root), '--verify'],
                          capture_output=True, text=True, encoding='utf-8')
    return proc.returncode, json.loads(proc.stdout)


class VerificationTests(unittest.TestCase):
    def test_missing_original_is_incomplete_and_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = companion(root, source_hash=digest(b'original'))
            before = path.read_bytes()
            code, rows = run_verify(root)
            self.assertEqual(code, 2)
            self.assertEqual(rows[0]['verification_status'], 'incomplete')
            self.assertEqual(rows[0]['text_status'], 'ok')
            self.assertEqual(rows[0]['source_status'], 'missing')
            self.assertEqual(path.read_bytes(), before)

    def test_complete_source_and_text_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'raw/papers'
            root.mkdir(parents=True)
            (root / 'a.pdf').write_bytes(b'original')
            companion(root, source_hash=digest(b'original'))
            code, rows = run_verify(root)
            self.assertEqual(code, 0)
            self.assertEqual(rows[0]['verification_status'], 'passed')
            self.assertEqual(rows[0]['source_status'], 'ok')

    def test_legacy_text_does_not_hide_source_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'a.pdf').write_bytes(b'changed')
            companion(root, source='a.pdf', source_hash=digest(b'original'), legacy=True)
            code, rows = run_verify(root)
            self.assertEqual(code, 1)
            self.assertEqual(rows[0]['text_status'], 'legacy_ok')
            self.assertEqual(rows[0]['source_status'], 'drift')
            self.assertEqual(rows[0]['verification_status'], 'issues')

    def test_old_formats_and_missing_hash_are_incomplete_not_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'no-frontmatter.md').write_text('body', encoding='utf-8')
            (root / 'no-hash.md').write_text('---\ntitle: old\n---\nbody', encoding='utf-8')
            companion(root, source=None, legacy=True)
            code, rows = run_verify(root)
            self.assertEqual(code, 2)
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(row['verification_status'] == 'incomplete' for row in rows))
            self.assertEqual({row['text_status'] for row in rows}, {'legacy_ok', 'missing_hash', 'skipped_no_frontmatter'})

    def test_empty_scan_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, rows = run_verify(Path(tmp))
            self.assertEqual(code, 2)
            self.assertEqual(rows[0]['status'], 'no_files')
            self.assertEqual(rows[0]['verification_status'], 'incomplete')

    def test_unreadable_text_does_not_stop_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'bad.md').write_bytes(b'\xff\xfe')
            companion(root, source=None)
            code, rows = run_verify(root)
            self.assertEqual(code, 2)
            self.assertEqual(len(rows), 2)
            bad = next(row for row in rows if row['file'] == 'bad.md')
            self.assertEqual(bad['text_status'], 'unreadable')
            self.assertEqual(bad['verification_status'], 'incomplete')

    def test_wrong_path_cannot_match_same_basename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'a.pdf').write_bytes(b'original')
            companion(root, source='missing/a.pdf', source_hash=digest(b'original'))
            code, rows = run_verify(root)
            self.assertEqual(code, 2)
            self.assertEqual(rows[0]['source_status'], 'missing')

    def test_ambiguous_source_location_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp)
            root = outer / 'papers'
            root.mkdir()
            for base in (root, outer):
                (base / 'a.pdf').write_bytes(b'original')
            companion(root, source='a.pdf', source_hash=digest(b'original'))
            code, rows = run_verify(root)
            self.assertEqual(code, 2)
            self.assertEqual(rows[0]['source_status'], 'ambiguous')

    def test_source_read_error_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'a.pdf').write_bytes(b'original')
            companion(root, source='a.pdf', source_hash=digest(b'original'))
            with mock.patch.object(Path, 'read_bytes', side_effect=PermissionError('denied')):
                rows = extractor.verify_md(root)
            self.assertEqual(rows[0]['source_status'], 'unreadable')
            self.assertEqual(rows[0]['verification_status'], 'incomplete')

    def test_scan_error_is_not_an_empty_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def failed_walk(*args, **kwargs):
                kwargs['onerror'](PermissionError(13, 'denied', str(root / 'blocked')))
                return iter(())
            with mock.patch('os.walk', side_effect=failed_walk):
                rows = extractor.verify_md(root)
            self.assertTrue(any(row['status'] == 'scan_error' for row in rows))
            self.assertTrue(all(row['verification_status'] == 'incomplete' for row in rows))


if __name__ == '__main__':
    unittest.main()
