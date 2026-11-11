#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NORM-REFERENCE 模式：批量给概念/比较页插入 '## 规范依据' 小节。

用法：
    python3 insert_norm_sections.py <wiki> --plan <plan.json> --dry-run   # 试跑（只校验与预演）
    python3 insert_norm_sections.py <wiki> --plan <plan.json>             # 正式执行
    （wiki 也可用环境变量 WIKI_PATH；DRY_RUN=1 等价于 --dry-run）

plan.json（PLAN 已移出源码，运行任务不再需要修改技能文件）：
    {
      "pages": {
        "concepts/某概念.md": [
          ["某法（2017修正）", "第十四条确立本概念的构成要件，是判断该问题的规范起点"],
          ["司法解释-某某规定", "第六条列举本概念的四种典型情形，为解释提供权威基准"]
        ]
      }
    }
    也接受列表形式：{"pages": [{"file": "concepts/某概念.md", "items": [[链接, 说明], …]}]}；
    条目也可写作 {"link": …, "desc": …}。每页 2-4 条。

批次纪律（备份 → 修改 → updated → 日志 → 复核 一次完成）：
- 插在 '## 与比较页的关联' 之前；该 anchor 不存在时回退 '## 相关概念'；
- 格式：## 规范依据\\n\\n- [[法规范页完整文件名]]——说明（30-80 字）\\n；
- 说明 30-80 字（CJK 口径，与论文—案例脚本共用同一函数）；链接必须真实存在于
  entities/法规范/ 下（递归）；页面已有 '## 规范依据' 则跳过（幂等）；
- 预演输出具体 diff；修改页更新 updated 并向 log.md 追加简记；
- 写入前备份到 <wiki>/.maintenance/norm-reference/before/，不覆盖旧备份；
  部分失败时报告已改与未改范围（备份可恢复）。
"""
import argparse
import difflib
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

WIKI = NORM_ROOT = BACKUP_DIR = None

ANCHOR_1 = "## 与比较页的关联"
ANCHOR_2 = "## 相关概念"
NEW_SECTION = "## 规范依据"


def link_exists(link):
    for dirpath, dirnames, filenames in os.walk(NORM_ROOT):
        if link + ".md" in filenames:
            return True
    return False


def configure_paths(wiki, backup_dir=None):
    global WIKI, NORM_ROOT, BACKUP_DIR
    WIKI = os.path.abspath(os.path.expanduser(wiki))
    NORM_ROOT = os.path.join(WIKI, "entities", "法规范")
    if not os.path.isdir(WIKI) or not os.path.isdir(NORM_ROOT):
        raise ValueError("wiki must contain entities/法规范")
    BACKUP_DIR = os.path.abspath(os.path.expanduser(backup_dir)) if backup_dir else os.path.join(
        WIKI, ".maintenance", "norm-reference", "before"
    )
    if os.path.commonpath([BACKUP_DIR, NORM_ROOT]) == NORM_ROOT:
        raise ValueError("backup directory must not be inside entities/法规范")


def safe_page_path(filename):
    path = os.path.abspath(os.path.join(WIKI, filename))
    if os.path.commonpath([path, WIKI]) != WIKI:
        raise ValueError(f"planned page escapes wiki root: {filename}")
    return path


def atomic_write(path, text):
    fd, tmp_name = tempfile.mkstemp(prefix=".norm-reference.", suffix=".tmp", dir=os.path.dirname(path))
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


def env_truthy(name):
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


def _norm_item(item):
    if isinstance(item, (list, tuple)) and len(item) == 2:
        return (str(item[0]), str(item[1]))
    if isinstance(item, dict) and "link" in item and "desc" in item:
        return (str(item["link"]), str(item["desc"]))
    raise ValueError(f"条目必须是 [链接, 说明] 或 {{link, desc}}：{item!r}")


def load_plan(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not (isinstance(raw, dict) and "pages" in raw):
        raise ValueError('plan 需含 "pages" 键（映射或列表）')
    pages = raw["pages"]
    plan = []
    if isinstance(pages, dict):
        for fn, items in pages.items():
            plan.append({"file": str(fn), "items": [_norm_item(i) for i in items]})
    elif isinstance(pages, list):
        for entry in pages:
            if not isinstance(entry, dict) or "file" not in entry or "items" not in entry:
                raise ValueError("pages 列表项必须含 file 与 items")
            plan.append({"file": str(entry["file"]),
                         "items": [_norm_item(i) for i in entry["items"]]})
    else:
        raise ValueError("pages 必须是映射或列表")
    if not plan:
        raise ValueError("plan 未列出任何页面")
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wiki", nargs="?", default=os.environ.get("WIKI_PATH"),
                        help="wiki root (or set WIKI_PATH)")
    parser.add_argument("--plan", help="本批插入计划 JSON（见文件头；PLAN 已移出源码）")
    parser.add_argument("--dry-run", action="store_true", help="只校验与预演（输出具体 diff），不写文件")
    parser.add_argument("--backup-dir", help="备份目录；默认 <wiki>/.maintenance/norm-reference/before")
    args = parser.parse_args(argv)
    if not args.wiki:
        parser.error("wiki root is required (pass it as an argument or set WIKI_PATH)")
    if not args.plan:
        parser.error("--plan is required：把'页面 → 法规范链接清单'写进 plan JSON（见文件头），不要改脚本源码")
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

    today = date.today().isoformat()

    ok = True
    for entry in plan:
        items = entry["items"]
        if not (2 <= len(items) <= 4):
            print(f"[条数超限] {entry['file']}: {len(items)}条（需2-4条）")
            ok = False
        for link, desc in items:
            n = u.cjk_len(desc)
            if not (30 <= n <= 80):
                print(f"[字数超限] {entry['file']} / {link}: {n}字（需30-80）")
                ok = False
            if not link_exists(link):
                print(f"[链接缺失] {entry['file']} -> {link} 在 {NORM_ROOT} 下未找到（核对实际文件名）")
                ok = False
    if not ok:
        return 1

    changes = []
    for entry in plan:
        fn = entry["file"]
        items = entry["items"]
        path = safe_page_path(fn)
        text = Path(path).read_text(encoding="utf-8")
        if NEW_SECTION in text:
            print(f"[跳过-已存在] {fn}")
            continue
        anchor = ANCHOR_1 if ANCHOR_1 in text else ANCHOR_2
        count = text.count(anchor)
        if count != 1:
            print(f"[错误] {fn} 中 '{anchor}' 出现 {count} 次")
            return 1
        block = NEW_SECTION + "\n\n" + "".join(f"- [[{link}]]——{desc}\n" for link, desc in items) + "\n"
        new_text = text.replace(anchor, block + anchor, 1)
        new_text, updated_changed = u.touch_updated(new_text, today)
        if dry_run:
            print(f"[预演] {fn}: 在 '{anchor}' 前插入 {len(items)} 条；"
                  f"updated：{'将更新为 ' + today if updated_changed else '无需更新'}；未写入任何文件。")
            diff = difflib.unified_diff(
                text.splitlines(keepends=True), new_text.splitlines(keepends=True),
                fromfile=fn, tofile=fn + "（预演后）", n=2,
            )
            for line in "".join(diff).splitlines():
                print("    " + line)
            continue
        changes.append({"file": fn, "path": path, "new_text": new_text,
                        "n": len(items), "updated_changed": updated_changed})

    if dry_run:
        print("DONE（预演）")
        return 0
    if not changes:
        print("DONE（无需修改）")
        return 0

    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_pairs = []
    for change in changes:
        destination = os.path.join(BACKUP_DIR, change["file"])
        if os.path.exists(destination):
            raise RuntimeError(f"backup already exists; refusing to clobber it: {destination}")
        backup_pairs.append((change["path"], destination))
    for source, destination in backup_pairs:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(source, destination)

    changed, failed = [], []
    for change in changes:
        try:
            atomic_write(change["path"], change["new_text"])
            changed.append(change)
            print(f"[已插入] {change['file']}: {change['n']}条"
                  f"（updated {'已更新' if change['updated_changed'] else '未变'}）")
        except Exception as exc:
            failed.append((change["file"], str(exc)))

    log_path = Path(WIKI) / "log.md"
    if changed and log_path.is_file():
        done_desc = "；".join("{} +{} 条".format(c["file"], c["n"]) for c in changed)
        block = (f"## [{today}] 关联｜规范依据小节插入（{len(changed)} 页）\n\n"
                 f"- 做了什么：{done_desc}\n"
                 f"- 备份：{os.path.relpath(BACKUP_DIR, WIKI)}\n")
        content = log_path.read_text(encoding="utf-8")
        log_path.write_text(content.rstrip("\n") + "\n\n" + block + "\n", encoding="utf-8")
        print("[日志] 已追加到 log.md")
    elif changed:
        print("[日志] 未找到 log.md，跳过日志")

    for change in changed:
        text = Path(change["path"]).read_text(encoding="utf-8")
        body = u.section_body(text, "规范依据") or ""
        links = re.findall(r"\[\[([^\]]+)\]\]", body)
        missing = [link for link in links if not link_exists(link)]
        print(f"[复核] {change['file']}: 规范依据 {len(links)} 条；链接缺失 {missing or '无'} → "
              f"{'OK' if not missing else '需处理'}")

    if failed:
        print(f"[部分失败] 已修改：{[c['file'] for c in changed] or '无'}；"
              f"未修改：{[f for f, _ in failed]}；备份可恢复：{BACKUP_DIR}")
        for fn, err in failed:
            print(f"  - {fn}: {err}")
        return 1
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
