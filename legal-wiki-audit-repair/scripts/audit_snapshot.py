#!/usr/bin/env python3
"""Read-only deep audit with explicit, snapshot-bound result reuse.

No files are written unless --save-state names a NEW JSON file outside the wiki
and the skill. A receipt records machine checks only, never manual acceptance.
Use --baseline to request reuse; any mismatch falls back to a fresh full audit.
"""
import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sys

import multimodal_audit as deep
from wiki_links import DEFAULT_SKIP_DIR_NAMES

SCHEMA_VERSION = 1


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def snapshot(wiki):
    """Hash content plus namespace; never infer unchanged content from timestamps."""
    result = {}
    def failed(exc):
        raise exc
    for directory, dirs, files in os.walk(wiki, followlinks=False, onerror=failed):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in DEFAULT_SKIP_DIR_NAMES)
        for name in dirs + sorted(files):
            path = Path(directory) / name
            if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                raise OSError('snapshot does not support linked paths: ' + str(path))
            rel = path.relative_to(wiki).as_posix()
            result[rel] = 'directory' if path.is_dir() else file_digest(path)
    return result


def engine_identity(strict, privacy):
    scripts = Path(__file__).resolve().parent
    return {'scripts': {p.name: file_digest(p) for p in sorted(scripts.glob('*.py'))},
            'python': sys.version, 'pyyaml': getattr(deep.yaml, '__version__', None),
            'strict': strict, 'privacy': privacy}


def load_state(path):
    if path is None:
        return None, 'no_baseline'
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
        state = document['state']
        if not isinstance(state, dict) or document['sha256'] != digest(state):
            raise ValueError('receipt checksum mismatch')
        if state['schema_version'] != SCHEMA_VERSION or not state['complete']:
            raise ValueError('unsupported or incomplete receipt')
        result = state['result']
        if (result['tool'] != 'multimodal_audit' or result['summary']['exit_code'] not in (0, 1)
                or [c['check'] for c in result['checks']] != list(range(1, 8))
                or result['unreadable_pages'] or result['unreadable_raw']
                or not isinstance(state['snapshot'], dict)):
            raise ValueError('invalid audit result')
        date.fromisoformat(state['day'])
        date.fromisoformat(state['full_day'])
        return state, 'available'
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None, 'invalid_baseline'


def validate_destination(path, wiki):
    if path is None:
        return
    target = path.resolve()
    for root in (wiki, Path(__file__).resolve().parents[1]):
        if target == root or root in target.parents:
            raise ValueError('state output must be outside wiki and skill')
    if path.exists() or path.is_symlink():
        raise ValueError('state output already exists; choose a new JSON file')
    if path.suffix.lower() != '.json' or not path.parent.is_dir():
        raise ValueError('state output needs an existing parent and .json suffix')


def full_audit(wiki, strict, privacy):
    config = deep.load_config(wiki)
    if privacy:
        config['privacy']['enabled'] = True
    audit = deep.Audit(wiki, config)
    audit.run()
    empty = not audit.pages and not audit.raw_files
    broken = any(f.severity == 'broken' for f in audit.findings)
    warning = any(f.severity == 'warning' for f in audit.findings)
    code = 2 if empty else (1 if broken or (strict and warning) else 0)
    result = deep.build_result(audit, strict, code)
    complete = not (empty or audit.unreadable or audit.raw_unreadable)
    return result, complete


def run(wiki, strict=False, privacy=False, baseline=None, save_state=None, force_full=False):
    wiki = wiki.expanduser().resolve()
    validate_destination(save_state, wiki)
    if not wiki.is_dir() or deep.yaml is None:
        raise ValueError('existing wiki directory and PyYAML required')
    before = snapshot(wiki)
    engine = engine_identity(strict, privacy)
    day = date.today().isoformat()
    old, reason = load_state(baseline)
    reuse = False
    if old:
        if old.get('wiki') != str(wiki) or old.get('engine') != engine:
            reason = 'checker_options_or_wiki_changed'
        elif old['day'] != day:
            reason = 'date_changed'
        elif old['snapshot'] != before:
            reason = 'files_changed'
        else:
            reuse, reason = True, 'identical_final_snapshot'
    if force_full:
        reuse, reason = False, 'forced_full'
    changed = sorted(p for p in set(before) | set(old['snapshot'] if old else {})
                     if before.get(p) != (old['snapshot'].get(p) if old else None))
    if reuse:
        result, complete = old['result'], True
    else:
        result, complete = full_audit(wiki, strict, privacy)
    after = snapshot(wiki)
    stable = before == after and engine == engine_identity(strict, privacy) and day == date.today().isoformat()
    complete = complete and stable
    if not complete and result['summary']['exit_code'] == 0:
        result['summary']['exit_code'] = 2
    state = {'schema_version': SCHEMA_VERSION, 'wiki': str(wiki), 'engine': engine,
             'snapshot': before, 'day': day, 'full_day': old['full_day'] if reuse else day,
             'complete': complete, 'result': result}
    saved = False
    if save_state is not None and complete:
        with save_state.open('x', encoding='utf-8', newline='\n') as f:
            json.dump({'state': state, 'sha256': digest(state)}, f, ensure_ascii=False, indent=2)
            f.write('\n')
        saved = True
    result = dict(result)
    result['execution'] = {'mode': 'reused' if reuse else 'full', 'reason': reason,
                           'changed_files': changed, 'snapshot_stable': stable,
                           'machine_scan_complete': complete,
                           'checks_executed': [] if reuse else list(range(1, 8)),
                           'checks_reused': list(range(1, 8)) if reuse else [],
                           'saved_state': str(save_state) if saved else None,
                           'manual_acceptance': 'not_checked'}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wiki', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--save-state', type=Path)
    parser.add_argument('--force-full', action='store_true')
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--privacy', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = run(args.wiki, args.strict, args.privacy, args.baseline, args.save_state, args.force_full)
    except (OSError, ValueError, RuntimeError) as exc:
        result = {'schema_version': 1, 'tool': 'multimodal_audit', 'wiki': str(args.wiki),
                  'checks': [], 'findings': [], 'summary': {'broken': 0, 'warning': 0, 'exit_code': 2},
                  'execution': {'mode': 'incomplete', 'reason': str(exc), 'machine_scan_complete': False,
                                'manual_acceptance': 'not_checked', 'saved_state': None}}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        execution = result['execution']
        print('只读深检：{}（{}）'.format(execution['mode'], execution['reason']))
        for finding in result['findings']:
            print('[{}] {} {}：{}'.format(finding['severity'], finding['rule'], finding['path'], finding['message']))
        print('检查范围与完整计数见 --json；人工验收未自动完成。退出码：{}'.format(result['summary']['exit_code']))
    return result['summary']['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
