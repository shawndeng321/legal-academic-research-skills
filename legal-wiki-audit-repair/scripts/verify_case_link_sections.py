#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收论文页 '## 与案例的关联' 章节（PAPER-CASE-LINK 模式）。

用法:
    python3 verify_case_link_sections.py <wiki根目录> <论文文件1.md> [论文文件2.md ...]
    参数不足时打印本用法并以退出码 2 结束。

检查项:
  1. 章节 '## 与案例的关联' 位于 '## 与其他论文的关联' 之前（该锚点缺失时按文末章节处理）；
  2. 章节内所有 [[案例…]] 链接（含别名与 `\\|` 写法）命中 entities/案例（递归）真实文件
     stem（死链 0）；非案例链接不属于本脚本范围；
  3. 每条条目理由（'——'之后）60-150 字——与同步脚本**共用同一** cjk_len 口径
     （只计中文字符与全角标点，不再用 len() 误伤英文与标点）；
  4. 章节开头有 '> …主旨…' 说明行；
  5. 关系分布统计（支持／反驳／边界例／引用／未标注，信息性）。

退出码: 0 = 全部通过, 1 = 有失败, 2 = 用法错误。
只检查'与案例的关联'章节本身；其他章节的既有死链不在本脚本范围。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_link_utils as u  # noqa: E402

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(2)

base = Path(sys.argv[1])
ref_dir = base / "entities/引用文献"
case_dir = base / "entities/案例"
case_stems = {p.stem for p in u.iter_case_files(case_dir)}
NOTE_RE = re.compile(r"^> .*主旨", re.M)
SECTION = "与案例的关联"
ANCHOR = "## 与其他论文的关联"

ok = True
for fn in sys.argv[2:]:
    path = ref_dir / fn
    text = path.read_text(encoding="utf-8")
    sec = u.section_body(text, SECTION)
    if sec is None:
        print(fn, "| FAIL: 缺少 ## 与案例的关联 章节")
        ok = False
        continue
    if text.count(ANCHOR) > 1:
        print(fn, '| FAIL: "## 与其他论文的关联" anchor 数量 >1')
        ok = False
        continue
    if text.count(ANCHOR) == 1:
        pos_ok = text.index("## " + SECTION) < text.index(ANCHOR)
    else:
        pos_ok = True  # 文末章节：其后没有锚点，按顺序通过
    links = re.findall(r"\[\[([^\]]+)\]\]", sec)
    case_links = [u.normalize_link_target(l) for l in links]
    dead = [l for l in case_links if l.startswith("案例") and l not in case_stems]
    bad_len = []
    relations = {}
    for line in sec.split("\n"):
        if re.match(r"^\d+\. ", line):
            reason = line.split("——", 1)[1] if "——" in line else line
            n = u.cjk_len(reason)
            if n < 60 or n > 150:
                bad_len.append((line[:20], n))
            rel = u.classify_relation(line) or "未标注"
            relations[rel] = relations.get(rel, 0) + 1
    note_ok = bool(NOTE_RE.search(sec))
    print(fn, "| 顺序OK:", pos_ok, "| 章节链接数:", len(links),
          "| 死链:", dead if dead else 0, "| 理由字数超标:", bad_len if bad_len else "无",
          "| 说明行:", note_ok, "| 关系分布:", relations)
    ok = ok and pos_ok and not dead and not bad_len and note_ok

sys.exit(0 if ok else 1)
