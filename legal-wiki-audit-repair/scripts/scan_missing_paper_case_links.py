#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""论文页“与案例的关联”缺漏扫描器（案例页 → 论文页镜像同步用）。

用法：
    python3 scan_missing_paper_case_links.py <wiki根目录> <论文stem1> [论文stem2 …] [--plan plan.json]
    参数不足时打印用法并以退出码 2 结束；wiki 也可用环境变量 WIKI_PATH。

递归扫描 entities/案例 下**任意层级**的案例页“与论文的关联”章节，提取指向目标论文
的条目（`- **[[论文名]]**：本文观点X（…）以本案[要旨]为支持/反驳/边界例/引用——理由`，
兼容无链接写法、别名、中英文冒号），与论文页“与案例的关联”章节已有链接比对，
报告缺漏；关系类型（支持／反驳／边界例／引用／未标注）分开统计。

本脚本只读，不写任何文件；参数不足打印用法并以退出码 2 结束。
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import case_link_utils as u  # noqa: E402

USAGE = ("用法：python3 scan_missing_paper_case_links.py <wiki根目录> <论文stem1> [论文stem2 …] "
         "[--plan plan.json]；wiki 也可用环境变量 WIKI_PATH")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wiki", nargs="?", default=os.environ.get("WIKI_PATH"),
                        help="wiki root (or set WIKI_PATH)")
    parser.add_argument("papers", nargs="*", help="论文 stem（entities/引用文献 下文件名去 .md）")
    parser.add_argument("--plan", help="可选：与同步脚本共用同一份 plan.json")
    args = parser.parse_args(argv)
    if not args.wiki:
        print(USAGE, file=sys.stderr)
        return 2

    papers = list(args.papers)
    if args.plan:
        try:
            raw = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            entries = raw.get("papers") if isinstance(raw, dict) else None
            if isinstance(entries, dict):
                papers = list(entries.keys())
            elif isinstance(entries, list):
                papers = [str(item["key"]) for item in entries]
            else:
                raise ValueError('plan 需含 "papers"（列表或映射）')
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            print(f"错误：plan 读取失败：{exc}", file=sys.stderr)
            return 2
    if not papers:
        print(USAGE, file=sys.stderr)
        return 2

    base = Path(os.path.abspath(os.path.expanduser(args.wiki)))
    case_dir = base / "entities" / "案例"
    paper_dir = base / "entities" / "引用文献"
    if not case_dir.is_dir():
        print(f"错误：未找到 {case_dir}", file=sys.stderr)
        return 2

    entries = {p: [] for p in papers}
    for case_path in u.iter_case_files(case_dir):
        text = case_path.read_text(encoding="utf-8")
        for parsed in u.extract_case_entries(text, papers):
            entries[parsed["key"]].append((case_path.stem, parsed))

    for paper in papers:
        print("=" * 20, paper, f"{len(entries[paper])} 条案例页条目")
        paper_path = paper_dir / (paper + ".md")
        if not paper_path.is_file():
            print("  论文页不存在！")
            continue
        stems, max_num = u.load_paper_state(paper_path.read_text(encoding="utf-8"))
        if stems is None:
            print("  论文页无'## 与案例的关联'章节，全部待建")
            continue
        print(f"  论文页已有 {len(stems)} 个链接，最大编号 {max_num}")
        missing = [(stem, parsed) for stem, parsed in entries[paper] if stem not in stems]
        rel = Counter(parsed["relation"] or "未标注" for _stem, parsed in missing)
        print(f"  缺漏 {len(missing)} 条（关系分布 {dict(rel)}）：")
        for stem, parsed in missing:
            print(f"    - {stem} | {parsed['view']} | {parsed['relation'] or '未标注'} "
                  f"| {u.cjk_len(parsed['reason'])}字")
            print(f"      条目: {parsed['line']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
