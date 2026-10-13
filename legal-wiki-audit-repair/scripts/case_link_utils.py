#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""论文—案例关联脚本的共享工具（sync / scan / verify / insert-norm 共用）。

单一事实来源，避免“同步通过、验收却报错”一类口径分叉：

- ``cjk_len()``：理由与说明的字数口径（只计中文字符与全角标点）。四个脚本共用
  同一函数；理由 60-150 字、说明 30-80 字均以它为准。
- ``find_section()`` / ``section_body()``：章节提取，支持**文末章节**（其后没有
  下一个 ``## `` 标题）与**空章节**。
- ``parse_case_entry_line()`` / ``extract_case_entries()``：案例页条目解析，支持
  ``- **[[论文名]]**：``、``- **[[论文名|别名]]**：``、``- **[[论文名\\|别名]]**：``、
  ``- **论文名**：``（无链接写法）、中英文冒号、全/半角“本文观点”括号；
  整名匹配（禁止作者名前缀匹配），同一条目重复出现按（目标, 原文）去重。
- ``classify_relation()``：关系类型分类——**支持／反驳／边界例／引用**，取自
  “——”之前的连接语（“以本案……为 X”“引用本案”）；未识别返回空串。
- ``normalize_link_target()``：链接目标规范化（去 ``[[ ]]``、去别名、去 ``.md``、
  去空白）。
- ``load_paper_state()``：论文页“与案例的关联”的既有链接 stem 集合与最大编号；
  章节缺失返回 ``(None, 0)`` 以区分“空章节”。
- ``append_entries_to_section()``：在章节最后一个非空行之后追加条目（空章节
  与文末章节安全）。
- ``touch_updated()``：更新 frontmatter 的 ``updated`` 字段（缺失时补写）。
- ``iter_case_files()``：递归列出案例页（跳过隐藏目录）。
"""
from __future__ import annotations

import re
from pathlib import Path

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
ALIAS_SPLIT_RE = re.compile(r"\\\||(?<!\\)\|")
ENTRY_RE = re.compile(r"^-\s*\*\*(?P<target>.+?)\*\*\s*[:：]\s*(?P<rest>.*)$")
VIEW_RE_STRICT = re.compile(r"本文观点\s*(\d+)?\s*（(.*?)）(?=以本案)")
VIEW_RE_LOOSE = re.compile(r"本文观点\s*(\d+)?\s*（([^（）]*?)）")


def cjk_len(text: str) -> int:
    """唯一字数口径：只计中文字符与全角标点。"""
    return len(CJK_RE.findall(text))


def find_section(text: str, header: str):
    """返回 (body_start, body_end)；章节不存在返回 None。支持文末章节。"""
    m = re.search(r"^## " + re.escape(header) + r"[ \t]*(?:\n|$)", text, re.M)
    if not m:
        return None
    body_start = m.end()
    nxt = re.search(r"^## ", text[body_start:], re.M)
    body_end = body_start + nxt.start() if nxt else len(text)
    return (body_start, body_end)


def section_body(text: str, header: str):
    span = find_section(text, header)
    return None if span is None else text[span[0]:span[1]]


def normalize_link_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("[[") and target.endswith("]]"):
        target = target[2:-2]
    target = ALIAS_SPLIT_RE.split(target, 1)[0].strip()
    if target.lower().endswith(".md"):
        target = target[:-3]
    return re.sub(r"\s+", "", target)


def classify_relation(entry_text: str) -> str:
    """从“——”之前的连接语分类关系类型；未识别返回空串。"""
    idx = entry_text.find("——")
    head = entry_text[:idx] if idx != -1 else entry_text
    if "边界" in head:
        return "边界例"
    if re.search(r"反衬|反驳|反例", head):
        return "反驳"
    if "引用" in head:
        return "引用"
    if re.search(r"支撑|印证", head):
        return "支持"
    return ""


def parse_case_entry_line(line: str):
    """解析一条案例页条目；不是条目返回 None。"""
    m = ENTRY_RE.match(line.strip())
    if not m:
        return None
    target = normalize_link_target(m.group("target"))
    rest = m.group("rest").strip()
    vm = VIEW_RE_STRICT.search(rest) or VIEW_RE_LOOSE.search(rest)
    if vm:
        num, brief = vm.group(1), vm.group(2)
        view = f"观点{num}（{brief}）" if num else "本文观点"
    else:
        view = "本文观点"
    rm = re.search(r"以本案[^\n]{0,40}?——(.*)$", rest, re.S)
    if rm:
        reason = rm.group(1).strip()
    else:
        idx = rest.find("——")
        reason = rest[idx + 2:].strip() if idx != -1 else ""
    return {
        "target": target,
        "view": view,
        "reason": reason,
        "relation": classify_relation(rest),
        "line": line.strip(),
    }


def extract_case_entries(text: str, keys) -> list:
    """从案例页正文提取指向 keys（论文完整名）的条目；整名匹配、逐条去重。"""
    span = find_section(text, "与论文的关联")
    if span is None:
        return []
    key_set = set(keys)
    results = []
    seen = set()
    for line in text[span[0]:span[1]].splitlines():
        parsed = parse_case_entry_line(line)
        if not parsed:
            continue
        if parsed["target"] not in key_set:
            continue
        dedup_key = (parsed["target"], parsed["line"])
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        parsed["key"] = parsed["target"]
        results.append(parsed)
    return results


def load_paper_state(text: str):
    """论文页“与案例的关联”：返回 (既有链接 stem 集合, 最大编号)。

    章节缺失时返回 ``(None, 0)``（调用方应报错）；章节存在但为空返回 ``(set(), 0)``。
    """
    body = section_body(text, "与案例的关联")
    if body is None:
        return None, 0
    stems = {normalize_link_target(m) for m in re.findall(r"\[\[([^\]]+)\]\]", body)}
    nums = [int(n) for n in re.findall(r"^(\d+)\.\s", body, re.M)]
    return stems, (max(nums) if nums else 0)


def append_entries_to_section(text: str, header: str, entries) -> str:
    """在章节最后一个非空行之后追加条目；空章节与文末章节安全。"""
    span = find_section(text, header)
    if span is None:
        raise KeyError(f"section not found: {header}")
    body = text[span[0]:span[1]]
    lines = body.split("\n")
    insert_at = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            insert_at = i + 1
            break
    if insert_at is None:
        insert_at = 0
    new_body = "\n".join(lines[:insert_at] + list(entries) + lines[insert_at:])
    return text[:span[0]] + new_body + text[span[1]:]


def touch_updated(text: str, today: str):
    """更新 frontmatter 的 updated；字段缺失时补写。返回 (新文本, 是否修改)。"""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return text, False
    fm = m.group(1)
    if re.search(r"^updated:", fm, re.M):
        if re.search(rf"^updated:\s*{re.escape(today)}\s*$", fm, re.M):
            return text, False
        new_fm = re.sub(r"^updated:.*$", f"updated: {today}", fm, count=1, flags=re.M)
    else:
        new_fm = fm + f"\nupdated: {today}"
    return text[:m.start(1)] + new_fm + text[m.end(1):], True


def iter_case_files(case_dir) -> list:
    """递归列出案例页（跳过隐藏目录），按路径排序。"""
    root = Path(case_dir)
    if not root.is_dir():
        return []
    files = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        if any(part.startswith(".") for part in rel.parts[:-1]):
            continue
        files.append(path)
    return files
