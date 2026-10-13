"""论文—案例同步闭环（WIKI-03）回归测试。

覆盖验收链路：官方模板生成页面 → 扫描缺漏（递归）→ 预演（具体 diff）→ 同步
（空章节/文末章节/别名链接）→ 二次同步无变化 → 验收（统一字数口径）。
另覆盖：参数校验退出码 2、expect_sha256 哈希冲突停止、insert_norm 的 --plan。

四个脚本均为标准库实现，无额外依赖，可在两个测试环境中运行。
"""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "legal-wiki-audit-repair" / "scripts"
SYNC = SCRIPTS / "sync_paper_case_links.py"
SCAN = SCRIPTS / "scan_missing_paper_case_links.py"
VERIFY = SCRIPTS / "verify_case_link_sections.py"
INSERT = SCRIPTS / "insert_norm_sections.py"

REASON = "理由说明" * 25  # 100 个 CJK 字符（在 60-150 区间内）


def run(script, *args):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(script), *map(str, args)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )


def make_vault(tmp):
    wiki = Path(tmp) / "wiki"
    cases = wiki / "entities" / "案例"
    papers = wiki / "entities" / "引用文献"
    (cases / "子目录").mkdir(parents=True)
    (cases / "深层" / "更深").mkdir(parents=True)
    papers.mkdir(parents=True)
    (wiki / "log.md").write_text(
        "# 操作日志\n\n## [2026-10-01] 摄入｜初始化\n\n- 做了什么：初始化\n",
        encoding="utf-8",
    )

    def write_case(rel, body):
        text = (
            f"---\ntitle: {Path(rel).stem}\ncreated: 2026-10-01\nupdated: 2026-10-01\n"
            f"type: case\nsources: [raw/cases/x.docx]\n---\n\n# 案\n\n"
            f"## 与论文的关联\n\n{body}\n\n## 相关概念\n\n- [[某概念]]\n"
        )
        (cases / rel).write_text(text, encoding="utf-8")

    # 官方模板写法（[[链接]] + 全角冒号 + 支撑）
    write_case("案例1-2016-甲案.md",
               f"- **[[作者甲-论文一]]**：本文观点1（简述一）以本案要旨为支撑——{REASON}")
    # 别名链接写法（案例页也在库根层）
    write_case("案例2-2017-乙案.md",
               f"- **[[作者甲-论文一|论文一]]**：本文观点2（简述二）以本案要旨为反衬——{REASON}")
    # 旧的无链接写法 + 半角冒号（子目录）
    write_case("子目录/案例3-2018-丙案.md",
               f"- **作者甲-论文一**: 本文观点3（简述三）以本案为印证——{REASON}")
    # 文末章节（深层目录）
    (cases / "深层" / "更深" / "案例4-2019-丁案.md").write_text(
        "---\ntitle: 案例4-2019-丁案\ncreated: 2026-10-01\nupdated: 2026-10-01\n"
        "type: case\n---\n\n# 丁案\n\n"
        f"## 与论文的关联\n\n- **[[作者甲-论文一]]**：本文观点1（简述一）以本案要旨为支撑——{REASON}\n",
        encoding="utf-8",
    )
    # 另一篇论文（反例关系）
    write_case("案例5-2020-戊案.md",
               f"- **[[作者乙-论文二]]**：本文观点2（简述二）以本案为反例——{REASON}")

    # 论文一：空章节（其后还有下一节）
    (papers / "作者甲-论文一.md").write_text(
        "---\ntitle: 论文一\ncreated: 2026-01-01\nupdated: 2026-01-01\ntype: paper\n"
        "tags: [标签一]\nsources: []\n---\n\n# 论文一\n\n"
        "## 与案例的关联\n\n> 按“观点 ↔ 案例主旨”对应建立：论文核心论点与库内案例裁判要旨的印证关系。\n\n"
        "## 与其他论文的关联\n\n- 与 [[作者乙-论文二]]：相关性。\n",
        encoding="utf-8",
    )
    # 论文二：文末章节（后方没有锚点）
    (papers / "作者乙-论文二.md").write_text(
        "---\ntitle: 论文二\ncreated: 2026-01-01\nupdated: 2026-01-01\ntype: paper\n"
        "tags: [标签一]\nsources: []\n---\n\n# 论文二\n\n"
        "## 与案例的关联\n\n> 按“观点 ↔ 案例主旨”对应建立：本论文案例要旨的印证关系。\n",
        encoding="utf-8",
    )
    return wiki


def write_plan(tmp, papers):
    path = Path(tmp) / "plan.json"
    path.write_text(json.dumps({"papers": papers}, ensure_ascii=False), encoding="utf-8")
    return path


class PaperCaseSyncTests(unittest.TestCase):
    def test_scripts_argument_contracts(self):
        sync_bare = run(SYNC)
        self.assertNotEqual(sync_bare.returncode, 0)
        self.assertIn("WIKI_PATH", sync_bare.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            sync_no_plan = run(SYNC, wiki)
            self.assertEqual(sync_no_plan.returncode, 2)
            self.assertIn("--plan", sync_no_plan.stderr)

            insert_no_plan = run(INSERT, wiki)
            self.assertEqual(insert_no_plan.returncode, 2)
            self.assertIn("--plan", insert_no_plan.stderr)

        scan_bare = run(SCAN)
        self.assertEqual(scan_bare.returncode, 2)
        self.assertIn("用法", scan_bare.stderr)

        verify_bare = run(VERIFY)
        self.assertEqual(verify_bare.returncode, 2)
        self.assertIn("用法", verify_bare.stdout)

        insert_bare = run(INSERT)
        self.assertNotEqual(insert_bare.returncode, 0)
        self.assertIn("WIKI_PATH", insert_bare.stderr)

    def test_full_flow_scan_preview_sync_resync_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            plan = write_plan(tmp, [
                {"key": "作者甲-论文一", "file": "作者甲-论文一.md"},
                {"key": "作者乙-论文二", "file": "作者乙-论文二.md"},
            ])

            scan = run(SCAN, wiki, "作者甲-论文一", "作者乙-论文二")
            self.assertEqual(scan.returncode, 0, scan.stderr)
            for stem in ("案例1-2016-甲案", "案例2-2017-乙案",
                         "案例3-2018-丙案", "案例4-2019-丁案"):
                self.assertIn(stem, scan.stdout)  # 根层、子目录、深层均可找到
            self.assertIn("缺漏 4 条", scan.stdout)
            self.assertIn("支持", scan.stdout)
            self.assertIn("反驳", scan.stdout)

            scan_plan = run(SCAN, wiki, "--plan", plan)
            self.assertEqual(scan_plan.returncode, 0, scan_plan.stderr)

            paper1 = wiki / "entities" / "引用文献" / "作者甲-论文一.md"
            before = paper1.read_bytes()

            prev = run(SYNC, wiki, "--plan", plan, "--dry-run")
            self.assertEqual(prev.returncode, 0, prev.stderr)
            self.assertIn("[预演 diff]", prev.stdout)
            self.assertIn("+ 案例1-2016-甲案", prev.stdout)
            self.assertIn("将追加 5 条，未写入任何文件", prev.stdout)
            self.assertIn("文件 sha256:", prev.stdout)
            self.assertEqual(paper1.read_bytes(), before)  # 预演不写

            sync = run(SYNC, wiki, "--plan", plan)
            self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)
            text1 = paper1.read_text(encoding="utf-8")
            # 模板写法、别名写法、无链接写法全部同步；空章节追加未抛错
            self.assertRegex(text1, r"\d+\. \*\*观点1（简述一）\*\* ↔ \[\[案例1-2016-甲案\]\]——" + re.escape(REASON))
            self.assertRegex(text1, r"\d+\. \*\*观点2（简述二）\*\* ↔ \[\[案例2-2017-乙案\]\]——")
            self.assertRegex(text1, r"\d+\. \*\*观点3（简述三）\*\* ↔ \[\[案例3-2018-丙案\]\]——")
            self.assertRegex(text1, r"\d+\. \*\*观点1（简述一）\*\* ↔ \[\[案例4-2019-丁案\]\]——")
            self.assertIn("4. **", text1)  # 编号 1-4 连续
            self.assertIn(f"updated: {date.today().isoformat()}", text1)
            self.assertIn("（编号 1-4）", sync.stdout)
            # 备份与日志
            backups = list((wiki / ".maintenance" / "paper-case-link").rglob("作者甲-论文一.md"))
            self.assertTrue(backups, "应生成备份")
            log = (wiki / "log.md").read_text(encoding="utf-8")
            self.assertIn("论文—案例同步", log)
            # 文末章节的论文二
            paper2 = wiki / "entities" / "引用文献" / "作者乙-论文二.md"
            self.assertIn("[[案例5-2020-戊案]]", paper2.read_text(encoding="utf-8"))
            self.assertNotIn("[[案例5-2020-戊案]]", text1)  # 案例5 属于论文二，不应误同步到论文一

            # 二次同步：无变化、不再写入
            snapshot = paper1.read_bytes()
            again = run(SYNC, wiki, "--plan", plan)
            self.assertEqual(again.returncode, 0, again.stdout)
            self.assertIn("总计追加: 0 条", again.stdout)
            self.assertEqual(paper1.read_bytes(), snapshot)

            verify = run(VERIFY, wiki, "作者甲-论文一.md", "作者乙-论文二.md")
            self.assertEqual(verify.returncode, 0, verify.stdout)
            self.assertIn("理由字数超标: 无", verify.stdout)

    def test_expect_sha256_conflict_stops_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            paper1 = wiki / "entities" / "引用文献" / "作者甲-论文一.md"
            before = paper1.read_bytes()

            wrong = write_plan(tmp, [
                {"key": "作者甲-论文一", "file": "作者甲-论文一.md", "expect_sha256": "0" * 64},
                {"key": "作者乙-论文二", "file": "作者乙-论文二.md"},
            ])
            blocked = run(SYNC, wiki, "--plan", wrong)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("哈希冲突", blocked.stdout + blocked.stderr)
            self.assertEqual(paper1.read_bytes(), before)
            self.assertFalse(list((wiki / ".maintenance").rglob("作者甲-论文一.md")))

            real_hash = hashlib.sha256(before).hexdigest()
            good = write_plan(tmp, [
                {"key": "作者甲-论文一", "file": "作者甲-论文一.md", "expect_sha256": real_hash},
            ])
            ok = run(SYNC, wiki, "--plan", good)
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            self.assertIn("[[案例1-2016-甲案]]", paper1.read_text(encoding="utf-8"))

    def test_reason_counting_shared_with_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            cases = wiki / "entities" / "案例"
            papers = wiki / "entities" / "引用文献"
            # 100 个 CJK + 200 个 ASCII：len() 会误判为 300，cjk_len 为 100
            long_reason = "理" * 100 + "a" * 200
            (cases / "案例9-2026-壬案.md").write_text(
                "---\ntitle: 案例9\ncreated: 2026-10-01\nupdated: 2026-10-01\ntype: case\n---\n\n"
                "## 与论文的关联\n\n"
                f"- **[[作者丙-论文三]]**：本文观点1（说明）以本案要旨为支撑——{long_reason}\n",
                encoding="utf-8",
            )
            (papers / "作者丙-论文三.md").write_text(
                "---\ntitle: 论文三\ncreated: 2026-01-01\nupdated: 2026-01-01\ntype: paper\n"
                "tags: [标签一]\nsources: []\n---\n\n# 论文三\n\n"
                "## 与案例的关联\n\n> 按“观点 ↔ 案例主旨”对应建立：该论文的印证关系。\n\n"
                "## 与其他论文的关联\n\n- 无。\n",
                encoding="utf-8",
            )
            plan = write_plan(tmp, [{"key": "作者丙-论文三", "file": "作者丙-论文三.md"}])

            prev = run(SYNC, wiki, "--plan", plan, "--dry-run")
            self.assertEqual(prev.returncode, 0, prev.stderr)
            self.assertIn("| 100字", prev.stdout)

            sync = run(SYNC, wiki, "--plan", plan)
            self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)
            verify = run(VERIFY, wiki, "作者丙-论文三.md")
            self.assertEqual(verify.returncode, 0, verify.stdout)  # 与同步同一口径 → 不误报
            self.assertIn("理由字数超标: 无", verify.stdout)

    def test_insert_norm_plan_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            norm_dir = wiki / "entities" / "法规范"
            norm_dir.mkdir(parents=True)
            (norm_dir / "某法.md").write_text("# 某法\n", encoding="utf-8")
            (norm_dir / "某规定.md").write_text("# 某规定\n", encoding="utf-8")
            concepts = wiki / "concepts"
            concepts.mkdir()
            page = concepts / "甲.md"
            page.write_text(
                "---\ntitle: 甲\ncreated: 2026-01-01\nupdated: 2026-01-01\ntype: concept\n"
                "tags: [标签一]\nsources: []\n---\n\n# 甲\n\n"
                "## 与比较页的关联\n\n- [[某比较页]]\n",
                encoding="utf-8",
            )
            plan = Path(tmp) / "norm-plan.json"
            plan.write_text(json.dumps({"pages": {"concepts/甲.md": [
                ["某法", "说明" * 20],
                ["某规定", "补充" * 15],
            ]}}, ensure_ascii=False), encoding="utf-8")
            before = page.read_bytes()

            dry = run(INSERT, wiki, "--plan", plan, "--dry-run")
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertIn("[预演]", dry.stdout)
            self.assertIn("规范依据", dry.stdout)
            self.assertEqual(page.read_bytes(), before)

            real = run(INSERT, wiki, "--plan", plan)
            self.assertEqual(real.returncode, 0, real.stdout + real.stderr)
            text = page.read_text(encoding="utf-8")
            self.assertIn("## 规范依据", text)
            self.assertIn("- [[某法]]——", text)
            self.assertIn(f"updated: {date.today().isoformat()}", text)
            self.assertLess(text.index("## 规范依据"), text.index("## 与比较页的关联"))
            log = (wiki / "log.md").read_text(encoding="utf-8")
            self.assertIn("规范依据小节插入", log)

            second = run(INSERT, wiki, "--plan", plan)
            self.assertEqual(second.returncode, 0)
            self.assertIn("跳过-已存在", second.stdout)


if __name__ == "__main__":
    unittest.main()
