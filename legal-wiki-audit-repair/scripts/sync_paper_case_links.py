#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CASE-PAPER-SYNC：案例页“## 与论文的关联” → 论文页“## 与案例的关联”批量同步。

用法：
    python3 sync_paper_case_links.py <wiki> --plan <plan.json> --dry-run   # 预演（输出具体 diff）
    python3 sync_paper_case_links.py <wiki> --plan <plan.json>             # 正式执行
    （wiki 也可用环境变量 WIKI_PATH；DRY_RUN=1 等价于 --dry-run）

plan.json（TARGETS 已移出源码，运行任务不再需要修改技能文件）：
    {
      "papers": [
        {"key": "作者-论文题名", "file": "作者-论文题名.md",
         "expect_sha256": "（可选）上一次预演输出的论文页哈希"}
      ]
    }
    也接受简写：{"papers": {"作者-论文题名": "作者-论文题名.md"}}。

批次纪律（备份 → 修改 → updated → 日志 → 复核 一次完成）：
- 预演输出每个论文页的具体 diff、将追加条目（含关系类型与理由字数）与文件哈希；
- 正式执行前核对 expect_sha256（若提供），冲突时停止并重新预演；
- 备份到 <wiki>/.maintenance/paper-case-link/before_batchN/（不覆盖旧备份）；
- 只追加不修改既有条目；编号接续写入时章节内最大编号；
  空章节、文末章节、`[[ ]]` 与无链接两种写法、别名链接（含 `\\|`）均可用；
- 修改页更新 updated；向 log.md 追加一条简记；写后逐页复核（链接目标、理由字数）；
  部分失败时报告已改与未改范围（备份可恢复）；
- 关系类型（支持／反驳／边界例／引用）自“——”前的连接语分类并分开统计；
- 理由取“——”之后，60-150 字（CJK 口径，与 verify_case_link_sections.py 共用同一函数）；
- 同一作者多篇论文必须整名匹配；去重按论文页章节内全部链接 stem。
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import case_link_utils as u  # noqa: E402

WIKI = CASE_DIR = PAPER_DIR = TASK_DIR = BACKUP_DIR = None
SECTION = "与案例的关联"


def configure_paths(wiki, backup_dir=None):
    """Configure all paths from the caller's vault; never use a host path."""
    global WIKI, CASE_DIR, PAPER_DIR, TASK_DIR, BACKUP_DIR
    WIKI = os.path.abspath(os.path.expanduser(wiki))
    CASE_DIR = os.path.join(WIKI, "entities", "案例")
    PAPER_DIR = os.path.join(WIKI, "entities", "引用文献")
    if not os.path.isdir(CASE_DIR) or not os.path.isdir(PAPER_DIR):
        raise ValueError("wiki must contain entities/案例 and entities/引用文献")
    TASK_DIR = os.path.join(WIKI, ".maintenance", "paper-case-link")
    BACKUP_DIR = os.path.abspath(os.path.expanduser(backup_dir)) if backup_dir else os.path.join(TASK_DIR, "before_batchN")
    if os.path.commonpath([BACKUP_DIR, PAPER_DIR]) == PAPER_DIR:
        raise ValueError("backup directory must not be inside entities/引用文献")


def safe_paper_path(filename):
    path = os.path.abspath(os.path.join(PAPER_DIR, filename))
    if os.path.commonpath([path, PAPER_DIR]) != PAPER_DIR:
        raise ValueError(f"target paper escapes entities/引用文献: {filename}")
    return path


def env_truthy(name):
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_plan(path):
    """解析 plan.json；返回 [{'key','file','expect'}]。格式见文件头。"""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not (isinstance(raw, dict) and "papers" in raw):
        raise ValueError('plan 需含 "papers" 键（列表或映射）')
    entries = raw["papers"]
    papers = []
    if isinstance(entries, dict):
        for key, fn in entries.items():
            papers.append({"key": str(key), "file": str(fn), "expect": None})
    elif isinstance(entries, list):
        for item in entries:
            if not isinstance(item, dict) or "key" not in item or "file" not in item:
                raise ValueError("papers 列表项必须含 key 与 file")
            papers.append({"key": str(item["key"]), "file": str(item["file"]),
                           "expect": item.get("expect_sha256")})
    else:
        raise ValueError("papers 必须是列表或映射")
    if not papers:
        raise ValueError("plan 未列出任何论文")
    for paper in papers:
        if paper["expect"] is not None and not re.fullmatch(r"[0-9a-f]{64}", str(paper["expect"])):
            raise ValueError(f"expect_sha256 不是 sha256：{paper['key']}")
    return papers


def atomic_write(path, text):
    fd, tmp_name = tempfile.mkstemp(prefix=".paper-case-sync.", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def build_diff(old_text, new_text, label):
    diff = difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=label, tofile=label + "（预演后）", n=2,
    )
    return "".join(diff)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wiki", nargs="?", default=os.environ.get("WIKI_PATH"),
                        help="wiki root (or set WIKI_PATH)")
    parser.add_argument("--plan", help="本批同步计划 JSON（见文件头；TARGETS 已移出源码）")
    parser.add_argument("--dry-run", action="store_true", help="只预演（输出具体 diff），不写任何文件")
    parser.add_argument("--backup-dir", help="备份目录；默认 <wiki>/.maintenance/paper-case-link/before_batchN")
    args = parser.parse_args(argv)
    if not args.wiki:
        parser.error("wiki root is required (pass it as an argument or set WIKI_PATH)")
    if not args.plan:
        parser.error("--plan is required：把本批论文清单写进 plan JSON（见文件头说明），不要改脚本源码")
    try:
        configure_paths(args.wiki, args.backup_dir)
    except ValueError as exc:
        parser.error(str(exc))
    dry_run = args.dry_run or env_truthy("DRY_RUN")
    try:
        plan = load_plan(args.plan)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"错误：plan 读取失败：{exc}", file=sys.stderr)
        return 2

    keys = [p["key"] for p in plan]
    by_paper = {k: [] for k in keys}
    for case_path in u.iter_case_files(CASE_DIR):
        text = case_path.read_text(encoding="utf-8")
        for parsed in u.extract_case_entries(text, keys):
            by_paper[parsed["key"]].append((case_path.stem, parsed))

    today = date.today().isoformat()
    items = []
    problems = []
    for paper in plan:
        ppath = safe_paper_path(paper["file"])
        if not os.path.isfile(ppath):
            problems.append(f"目标论文不存在：{paper['file']}")
            continue
        text = Path(ppath).read_text(encoding="utf-8")
        existing, max_num = u.load_paper_state(text)
        if existing is None:
            problems.append(f"缺少 '## {SECTION}' 章节：{paper['file']}")
            continue
        if paper["expect"]:
            actual = sha256_text(text)
            if actual != paper["expect"]:
                problems.append(
                    f"哈希冲突：{paper['file']} 自预演后已变化；停止并重新预演"
                    f"（现 {actual[:12]}… ≠ 计划 {str(paper['expect'])[:12]}…）")
                continue
        missing = []
        seen = set()
        for stem, parsed in by_paper[paper["key"]]:
            if stem in existing:
                continue
            dedup = (stem, parsed["line"])
            if dedup in seen:
                continue
            seen.add(dedup)
            missing.append((stem, parsed))
        entries = []
        number = max_num
        for stem, parsed in missing:
            number += 1
            entries.append((number, stem, parsed))
        items.append({"paper": paper, "path": ppath, "text": text,
                      "max_num": max_num, "missing": missing, "entries": entries,
                      "hash": sha256_text(text)})

    if problems:
        for msg in problems:
            print(f"[停止] {msg}")
        print("未写入任何文件；修正后重新预演。")
        return 1

    print(f"论文 {len(plan)} 篇；案例页目录：{CASE_DIR}")
    for item in items:
        paper = item["paper"]
        rel_counts = {}
        for _stem, parsed in item["missing"]:
            key = parsed["relation"] or "未标注"
            rel_counts[key] = rel_counts.get(key, 0) + 1
        rel_note = f"；关系分布 {rel_counts}" if item["missing"] else ""
        print(f"\n=== {paper['key']}（{paper['file']}）：现有编号至 {item['max_num']}，"
              f"缺漏 {len(item['missing'])} 条{rel_note}")
        if not item["missing"]:
            continue
        for number, stem, parsed in item["entries"]:
            print(f"    + {stem} | {parsed['view']} | {parsed['relation'] or '未标注'} "
                  f"| {u.cjk_len(parsed['reason'])}字")
        if dry_run:
            new_lines = [f"{number}. **{parsed['view']}** ↔ [[{stem}]]——{parsed['reason']}"
                         for number, stem, parsed in item["entries"]]
            new_text = u.append_entries_to_section(item["text"], SECTION, new_lines)
            new_text, updated_changed = u.touch_updated(new_text, today)
            print("  [预演 diff]")
            diff = build_diff(item["text"], new_text, paper["file"])
            for line in diff.splitlines():
                print("    " + line)
            print(f"  将追加 {len(item['entries'])} 条（编号 {item['max_num'] + 1}-"
                  f"{item['entries'][-1][0]}）；updated：{'将更新为 ' + today if updated_changed else '无需更新'}；"
                  f"文件 sha256: {item['hash']}")

    if dry_run:
        total = sum(len(item["missing"]) for item in items)
        print(f"\n[预演结束] 将追加 {total} 条，未写入任何文件。"
              f"正式执行：去掉 --dry-run；如需锁定文件版本，可把上面的 sha256 填入 plan 的 expect_sha256。")
        return 0

    writable = [item for item in items if item["missing"]]
    if not writable:
        print("\n总计追加: 0 条")
        return 0

    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_pairs = []
    for item in writable:
        destination = os.path.join(BACKUP_DIR, item["paper"]["file"])
        if os.path.exists(destination):
            print(f"[停止] 备份已存在，拒绝覆盖：{destination}")
            return 1
        backup_pairs.append((item["path"], destination))
    for source, destination in backup_pairs:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(source, destination)

    changed, summaries, failed = [], [], []
    total = 0
    for item in writable:
        fn = item["paper"]["file"]
        try:
            current = Path(item["path"]).read_text(encoding="utf-8")
            new_lines = [f"{number}. **{parsed['view']}** ↔ [[{stem}]]——{parsed['reason']}"
                         for number, stem, parsed in item["entries"]]
            new_text = u.append_entries_to_section(current, SECTION, new_lines)
            new_text, updated_changed = u.touch_updated(new_text, today)
            before_hash = sha256_text(current)
            atomic_write(item["path"], new_text)
            after_hash = sha256_text(new_text)
            changed.append(fn)
            total += len(new_lines)
            low, high = item["max_num"] + 1, item["entries"][-1][0]
            summaries.append(f"{fn} +{len(new_lines)} 条（编号 {low}-{high}）")
            print(f"[已追加] {fn}：+{len(new_lines)} 条（编号 {low}-{high}）；"
                  f"updated：{'已更新' if updated_changed else '未变'}；"
                  f"sha256 {before_hash[:12]}… → {after_hash[:12]}…")
        except Exception as exc:  # 单页失败不阻塞其余，最后统一报告
            failed.append((fn, str(exc)))

    log_path = Path(WIKI) / "log.md"
    if changed and log_path.is_file():
        block = (f"## [{today}] 关联｜论文—案例同步（{len(changed)} 篇）\n\n"
                 f"- 做了什么：{'；'.join(summaries)}\n"
                 f"- 验收：写后复核（链接目标存在、理由 60-150 字口径）\n"
                 f"- 备份：{os.path.relpath(BACKUP_DIR, WIKI)}\n")
        content = log_path.read_text(encoding="utf-8")
        log_path.write_text(content.rstrip("\n") + "\n\n" + block + "\n", encoding="utf-8")
        print("[日志] 已追加到 log.md")
    elif changed:
        print("[日志] 未找到 log.md，跳过日志")

    case_stems = {p.stem for p in u.iter_case_files(CASE_DIR)}
    for fn in changed:
        text = Path(safe_paper_path(fn)).read_text(encoding="utf-8")
        body = u.section_body(text, SECTION) or ""
        links = [u.normalize_link_target(m) for m in re.findall(r"\[\[([^\]]+)\]\]", body)]
        dead = [l for l in links if l.startswith("案例") and l not in case_stems]
        bad = []
        for line in body.split("\n"):
            if re.match(r"^\d+\. ", line):
                reason = line.split("——", 1)[1] if "——" in line else line
                n = u.cjk_len(reason)
                if not (60 <= n <= 150):
                    bad.append((line[:18], n))
        status = "OK" if not dead and not bad else "需处理"
        print(f"[复核] {fn}: 死链 {dead or 0}；理由字数超标 {bad or '无'} → {status}")

    if failed:
        print(f"[部分失败] 已修改：{changed or '无'}；未修改：{[f for f, _ in failed]}；备份可恢复：{BACKUP_DIR}")
        for fn, err in failed:
            print(f"  - {fn}: {err}")
        return 1
    print(f"\n总计追加: {total} 条（{len(changed)} 篇）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
