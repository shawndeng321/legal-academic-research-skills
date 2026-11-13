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


SCHEMA_VERSION = 2


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
        # Configurations may reinclude default backup/maintenance directories.
        # Bind all files except Git internals, not just the default audit scope.
        dirs[:] = sorted(d for d in dirs if d != '.git')
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
        if state['schema_version'] != SCHEMA_VERSION or state['complete'] is not True:
            raise ValueError('unsupported or incomplete receipt')
        result = state['result']
        if (result['tool'] != 'multimodal_audit' or result['summary']['exit_code'] not in (0, 1)
                or [c['check'] for c in result['checks']] != list(range(1, 8))
                or result['unreadable_pages'] or result['unreadable_raw']
                or not isinstance(state['snapshot'], dict)):
            raise ValueError('invalid audit result')
        if not date.fromisoformat(state['full_day']) <= date.fromisoformat(state['day']) <= date.today():
            raise ValueError('invalid receipt dates')
        if (result['schema_version'] != 1 or result['wiki'] != state['wiki']
                or result['strict'] != state['engine']['strict']
                or not isinstance(result['notes'], dict)
                or not isinstance(result['duplicate_keys'], list)
                or not all(type(result['counts'][k]) is int and result['counts'][k] >= 0
                           for k in ('pages', 'raw_files'))
                or not sum(result['counts'].values())):
            raise ValueError('invalid result metadata')
        for row in result['checks']:
            if row['status'] not in ('pass', 'warn', 'fail', 'not_checked'):
                raise ValueError('invalid check status')
        for row in result['findings']:
            if (not all(isinstance(row[k], str) for k in
                        ('rule', 'severity', 'scope', 'path', 'location', 'message'))
                    or row['severity'] not in ('broken', 'warning', 'observation')
                    or not deep._rule_check(row['rule'])
                    or ('paths' in row and (not isinstance(row['paths'], list)
                        or row['path_count'] != len(row['paths'])))):
                raise ValueError('invalid finding')
        for severity in ('broken', 'warning', 'observation'):
            if result['summary'][severity] != sum(r['severity'] == severity for r in result['findings']):
                raise ValueError('finding count mismatch')
        expected = int(bool(result['summary']['broken'] or
                            (result['strict'] and result['summary']['warning'])))
        if result['summary']['exit_code'] != expected:
            raise ValueError('exit code mismatch')
        for rel, value in state['snapshot'].items():
            if not isinstance(rel, str) or not isinstance(value, str) or not (
                    value == 'directory' or (len(value) == 64 and all(c in '0123456789abcdef' for c in value))):
                raise ValueError('invalid snapshot')
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


def full_audit(wiki, strict, privacy, selected=None, previous=None):
    config = deep.load_config(wiki)
    if privacy:
        config['privacy']['enabled'] = True
    audit = deep.Audit(wiki, config)
    if selected is None:
        audit.run()
    else:
        # Cross-page checks always cover the whole current graph. Reuse only
        # entire unaffected checks; never splice a local link-count result.
        audit.collect()
        audit.findings = [f for f in audit.findings if deep._rule_check(f.rule) in selected]
        for row in previous['checks']:
            if row['check'] not in selected:
                audit.check_stats[row['check']] = {k: v for k, v in row.items()
                                                 if k not in ('check', 'title', 'note')}
                if row.get('note') is not None:
                    audit.check_notes[row['check']] = row['note']
        for row in previous['findings']:
            if deep._rule_check(row['rule']) not in selected:
                audit.findings.append(deep.Finding(**{k: v for k, v in row.items() if k != 'path_count'}))
        methods = (audit.check_index, audit.check_raw, audit.check_frontmatter,
                   audit.check_links, audit.check_hygiene, audit.check_log, audit.check_special)
        for number in selected:
            methods[number - 1]()
    empty = not audit.pages and not audit.raw_files
    broken = any(f.severity == 'broken' for f in audit.findings)
    warning = any(f.severity == 'warning' for f in audit.findings)
    code = 2 if empty else (1 if broken or (strict and warning) else 0)
    result = deep.build_result(audit, strict, code)
    complete = not (empty or audit.unreadable or audit.raw_unreadable)
    return result, complete


def affected_checks(wiki, old, current, changed):
    if old.keys() != current.keys():
        return None, 'namespace_changed'
    config = deep.load_config(wiki)
    # A deliberately small supported envelope. Unknown paths, raw material,
    # schema and configuration changes get a full audit.
    if config['page_dirs'] != list(deep.DEFAULT_PAGE_DIRS) or config['raw_dir'] != deep.DEFAULT_RAW_DIR:
        return None, 'custom_scope_requires_full'
    selected = set()
    for rel in changed:
        is_page = rel.endswith('.md') and any(rel.startswith(p.rstrip('/') + '/')
                                             for p in config['page_dirs'])
        if not is_page:
            return None, 'global_or_unknown_input_changed'
        selected.update((3, 4, 5, 7))
        empty_hash = hashlib.sha256(b'').hexdigest()
        if old[rel] == empty_hash or current[rel] == empty_hash:
            selected.add(1)
    return sorted(selected), 'changed_pages_global_dependencies'


def run(wiki, strict=False, privacy=False, baseline=None, save_state=None, force_full=False,
        incremental=False):
    wiki = wiki.expanduser().resolve()
    validate_destination(save_state, wiki)
    if not wiki.is_dir() or deep.yaml is None:
        raise ValueError('existing wiki directory and PyYAML required')
    config = deep.load_config(wiki)
    for rel in [*config['page_dirs'], config['raw_dir']]:
        root = (wiki / rel).resolve()
        if root != wiki and wiki not in root.parents:
            raise ValueError('snapshot cannot cover configured paths outside wiki')
    before = snapshot(wiki)
    engine = engine_identity(strict, privacy)
    day = date.today().isoformat()
    old, reason = load_state(baseline)
    reuse = False
    selected = None
    changed = sorted(p for p in set(before) | set(old['snapshot'] if old else {})
                     if before.get(p) != (old['snapshot'].get(p) if old else None))
    if old:
        if old.get('wiki') != str(wiki) or old.get('engine') != engine:
            reason = 'checker_options_or_wiki_changed'
        elif (date.today() - date.fromisoformat(old['full_day'])).days >= 7:
            reason = 'periodic_full_due'
        elif old['day'] != day:
            reason = 'date_changed'
        elif old['snapshot'] != before:
            reason = 'files_changed'
            if incremental:
                selected, reason = affected_checks(wiki, old['snapshot'], before, changed)
        else:
            reuse, reason = True, 'identical_final_snapshot'
    if force_full:
        reuse, reason = False, 'forced_full'
        selected = None
    if reuse:
        result, complete = old['result'], True
    else:
        result, complete = full_audit(wiki, strict, privacy, selected, old['result'] if old else None)
    after = snapshot(wiki)
    stable = before == after and engine == engine_identity(strict, privacy) and day == date.today().isoformat()
    complete = complete and stable
    if not complete and result['summary']['exit_code'] == 0:
        result['summary']['exit_code'] = 2
    state = {'schema_version': SCHEMA_VERSION, 'wiki': str(wiki), 'engine': engine,
             'snapshot': before, 'day': day, 'full_day': old['full_day'] if reuse or selected is not None else day,
             'complete': complete, 'result': result}
    saved = False
    if save_state is not None and complete:
        with save_state.open('x', encoding='utf-8', newline='\n') as f:
            json.dump({'state': state, 'sha256': digest(state)}, f, ensure_ascii=False, indent=2)
            f.write('\n')
        saved = True
    result = dict(result)
    executed = [] if reuse else (selected if selected is not None else list(range(1, 8)))
    result['execution'] = {'mode': 'reused' if reuse else ('incremental' if selected is not None else 'full'), 'reason': reason,
                           'changed_files': changed, 'snapshot_stable': stable,
                           'machine_scan_complete': complete,
                           'checks_executed': executed,
                           'checks_reused': [n for n in range(1, 8) if n not in executed],
                           'affected_scope': 'whole_check_across_vault',
                           'saved_state': str(save_state) if saved else None,
                           'manual_acceptance': 'not_checked'}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wiki', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--save-state', type=Path)
    parser.add_argument('--force-full', action='store_true')
    parser.add_argument('--incremental', action='store_true')
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--privacy', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = run(args.wiki, args.strict, args.privacy, args.baseline, args.save_state,
                     args.force_full, args.incremental)
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
