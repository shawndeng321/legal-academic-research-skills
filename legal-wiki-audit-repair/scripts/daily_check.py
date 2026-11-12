#!/usr/bin/env python3
"""Read-only daily coverage summary; never equates tool success with full acceptance.

Use: daily_check.py WIKI --research-skill /actual/legal-research-wiki [--json]
The research skill is explicit and need not be installed beside this skill.
Exit: 1 known issues; otherwise 2 incomplete coverage; 0 only full coverage.
Manual checks remain outstanding and are never automatically marked passed.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def run_tool(command):
    try:
        proc = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=60)
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        return {'status': 'not_checked', 'error': str(exc), 'result': None}
    try:
        result = json.loads(proc.stdout)
    except (ValueError, TypeError):
        return {'status': 'not_checked', 'exit_code': proc.returncode,
                'error': proc.stderr or '工具未输出有效 JSON', 'result': None}
    return {'status': 'returned', 'exit_code': proc.returncode,
            'error': proc.stderr, 'result': result}


def summarize(wiki, research_skill=None, strict=False):
    command = [sys.executable, '-X', 'utf8', str(Path(__file__).with_name('multimodal_audit.py')),
               str(wiki), '--json']
    if strict:
        command.append('--strict')
    structure = run_tool(command)
    payload = structure['result']
    structure_valid = (isinstance(payload, dict) and isinstance(payload.get('checks'), list)
                       and isinstance(payload.get('findings'), list)
                       and structure.get('exit_code') in (0, 1, 2))
    if not structure_valid:
        structure['status'] = 'not_checked'
    hashes = {'status': 'not_checked', 'result': None, 'error': '未提供建库技能位置；原件与正文指纹未检查'}
    if research_skill:
        script = research_skill / 'scripts/batch_extract_papers.py'
        if script.is_file():
            hashes = run_tool([sys.executable, '-X', 'utf8', str(script), str(wiki / 'raw'), '--verify'])
        else:
            hashes['error'] = '指定位置没有 batch_extract_papers.py；不猜测相邻技能位置'
    hash_rows = hashes['result']
    hashes_valid = (isinstance(hash_rows, list) and bool(hash_rows)
                    and all(isinstance(row, dict) and row.get('verification_status') in
                            ('passed', 'issues', 'incomplete') for row in hash_rows)
                    and hashes.get('exit_code') in (0, 1, 2))
    if not hashes_valid:
        hashes['status'] = 'not_checked'
    coverage = []

    def add(key, status, note):
        coverage.append({'id': key, 'status': status, 'note': note})

    def structural(key, numbers, note, required_counts=()):
        if not structure_valid:
            add(key, 'not_checked', note + '；深检未成功返回，见 tools.structure.error')
            return
        checks = {row.get('check'): row for row in payload['checks']}
        statuses = [checks.get(n, {}).get('status', 'not_checked') for n in numbers]
        status = 'not_checked' if 'not_checked' in statuses else ('issues' if any(s in ('warn', 'fail') for s in statuses) else 'passed')
        missing = [label for field, label in required_counts
                   if not any(checks.get(n, {}).get(field, 0) > 0 for n in numbers)]
        if missing:
            note += '；未检查：' + '、'.join(missing)
            if status == 'passed':
                status = 'not_checked' if len(missing) == len(required_counts) else 'partial'
        if payload.get('unreadable_pages') or payload.get('unreadable_raw'):
            status = 'partial'
        add(key, status, note)

    add('orientation', 'manual', '读取 log 最近30—80行及台账最近三条执行记录，人工确认本批范围')
    structural('structure', [1, 3, 4], '索引、通用 frontmatter/YAML、正式页链接由七项深检检查；完整发现见 tools.structure.result')
    add('baseline', 'manual', '磁盘/索引计数不等于台账基线比较，须人工对照台账及统计口径')
    add('tags', 'partial' if structure_valid else 'not_checked', '现有 FM-04 仅提示词表外且只用一次的标签；重复出现的词表外标签可能漏掉，须对全部标签与 SCHEMA 词表逐项核对')
    add('type_fields', 'partial' if structure_valid else 'not_checked', '通用必填字段和规范/案例专项已有检查；全部类型专属字段覆盖率须按 SCHEMA 人工补查')
    add('symmetry', 'manual', '论文↔案例双向对称须补查；可先运行 scan_missing_paper_case_links.py 与 verify_case_link_sections.py，再回读两侧来源和章节')
    structural('legal', [7], '法规范时效和案号去重按机器字段检查；法律效力与案号归属仍需回到原件核验',
               (('norms', '法规范时效（无可检查 norm 页）'), ('cases', '案号去重（无可检查 case 页）')))
    hash_status = 'not_checked'
    if hashes_valid:
        hash_status = 'issues' if any(r['verification_status'] == 'issues' for r in hash_rows) else ('passed' if all(r['verification_status'] == 'passed' for r in hash_rows) else 'partial')
    add('hashes', hash_status, '仅复核 raw 下 Markdown 的正文哈希及其 source_path/source_sha256；无字段或 MANIFEST 独立指纹、无提取物的二进制原件须补查，不因无字段判材料损坏')
    add('manifest', 'manual', 'raw/MANIFEST.md 的机器核验指纹需按台账逐件重算；本入口不解析该表，也不代替来源真实性核验')
    add('opt', 'manual', '对照最近 OPT 的验收缺口及未闭环事项，发现 P1 以上问题列修复方案')
    add('contested', 'manual', '逐页核对 contested/contradictions，保留分歧双方立场、日期与来源')
    add('log', 'manual', '日志默认只读；拟追加记录附报告末尾，既定写日志授权、三日迭代与每周深检要求仍适用')
    known_issues = ((structure_valid and structure.get('exit_code') == 1)
                    or (hashes_valid and any(r['verification_status'] == 'issues' for r in hash_rows)))
    complete = all(row['status'] == 'passed' for row in coverage)
    code = 1 if known_issues else (0 if complete else 2)
    return {'schema_version': 1, 'tool': 'daily_check', 'wiki': str(wiki), 'complete': complete,
            'coverage': coverage, 'tools': {'structure': structure, 'hashes': hashes},
            'summary': {'exit_code': code, 'known_issues': bool(known_issues),
                        'outstanding': [r['id'] for r in coverage if r['status'] != 'passed']}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wiki', type=Path)
    parser.add_argument('--research-skill', type=Path)
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    wiki = args.wiki.expanduser().resolve()
    if not wiki.is_dir():
        parser.error('Wiki 根目录不存在或不是目录')
    research = args.research_skill.expanduser().resolve() if args.research_skill else None
    result = summarize(wiki, research, args.strict)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print('每日检修覆盖汇总（只读）')
        for row in result['coverage']:
            print('[{}] {}：{}'.format(row['status'], row['id'], row['note']))
        for name, tool in result['tools'].items():
            if tool.get('error'):
                print('{}：{}'.format(name, tool['error']))
        print('完整发现与路径：用 --json 查看 tools 中的原始结果。')
        print('退出码：{}；人工和未覆盖项尚须完成。'.format(result['summary']['exit_code']))
    return result['summary']['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
