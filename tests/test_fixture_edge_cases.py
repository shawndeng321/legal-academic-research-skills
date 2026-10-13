"""WIKI-08 基础夹具：错误 YAML、多行列表、重复文件名、多层目录、空目标、
合法别名与附件、原件与提取物哈希、疑似重复案号、过期核验日期。

深检脚本依赖 PyYAML；缺依赖时整体显式跳过。
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
AUDIT = ROOT / "legal-wiki-audit-repair" / "scripts" / "multimodal_audit.py"
CHECK = ROOT / "legal-research-wiki" / "scripts" / "check_wikilinks.py"
EXTRACT = ROOT / "legal-research-wiki" / "scripts" / "batch_extract_papers.py"

try:
    import yaml as _yaml  # noqa: F401
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def run(script, *args):
    return subprocess.run([PY, "-X", "utf8", str(script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def fm(**kw):
    return "\n".join(["---"] + [f"{k}: {v}" for k, v in kw.items()] + ["---", "", ""])


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_vault(tmp):
    wiki = Path(tmp) / "wiki"

    def write(rel, text):
        path = wiki / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    # 错误 YAML
    write("entities/案例/错yaml案.md", "---\ntitle: [未闭合\ncreated: 2026-01-01\n---\n\n正文\n")
    # 多行列表
    write("entities/引用文献/多行标签论文.md", "---\ntitle: 多行标签论文\ncreated: 2026-01-01\n"
          "updated: 2026-01-01\ntype: paper\ntags:\n  - 标签甲\n  - 标签乙\nsources: []\n---\n\n## 摘要\n\n正文。\n")
    # 重复文件名（同名不同目录）与多层目录案例
    base_case = {"created": "2026-01-01", "updated": "2026-01-01", "type": "case",
                 "tags": "[案例标签]", "sources": "[]"}
    write("entities/案例/子甲/案例1-2016-甲案.md", fm(title="案例1-甲", **base_case,
          docket="（2016）最高法行申1号") + "# 甲\n\n要旨。\n")
    write("entities/案例/子乙/深层/案例2-2016-乙案.md", fm(title="案例2-乙", **base_case,
          docket="(2016)最高法行申1号") + "# 乙\n\n要旨。\n")
    write("entities/案例/子丙/案例9-同名案.md", fm(title="案例9-同名案（丙）", **base_case,
          docket="（2017）甲1号") + "# 丙\n\n要旨。\n")
    write("entities/案例/子丁/更深/案例9-同名案.md", fm(title="案例9-同名案（丁）", **base_case,
          docket="（2017）甲2号") + "# 丁\n\n要旨。\n")
    # 空目标 + 合法别名 + 合法附件
    write("concepts/某概念.md", fm(title="某概念", created="2026-01-01", updated="2026-01-01",
          type="concept", tags="[概念标签]", sources="[]") +
          "# 某概念\n\n- 指向 [[案例1-2016-甲案|简称甲]]；\n- 另见 [[空目标页]]；\n"
          "- 嵌入 ![[示意图.png]]；\n- 依据 [[某有效法]]；\n- 同名参照 [[案例9-同名案]]。\n")
    write("concepts/空目标页.md", "")
    write("raw/assets/示意图.png", "png-bytes")
    # 过期核验日期
    write("entities/法规范/法律/某有效法.md", fm(title="某有效法", created="2026-01-01", updated="2026-01-01",
          type="norm", tags="[规范标签]", sources="[]", **{"规范层级": "法律", "效力状态": "现行有效",
          "核验日期": "2024-01-01"}) + "# 某有效法\n\n## 第一条\n\n> 原文。\n")
    # 原件与提取物哈希
    raw = wiki / "raw" / "papers"
    raw.mkdir(parents=True, exist_ok=True)
    good_src = "%PDF-1.4 fake-甲"
    (raw / "甲文.pdf").write_bytes(good_src.encode())
    (raw / "乙文.pdf").write_bytes("%PDF-1.4 fake-乙".encode())
    ok_body = "# 甲文\n\n提取正文。\n"
    (raw / "甲文.md").write_text("---\nsource_path: raw/papers/甲文.pdf\ningested: 2026-01-01\n"
        f"source_sha256: {sha(good_src)}\ntext_sha256: {sha(ok_body)}\nextractor: test\n---\n\n" + ok_body,
        encoding="utf-8")
    bad_body = "# 乙文\n\n提取正文。\n"
    (raw / "乙文.md").write_text("---\nsource_path: raw/papers/乙文.pdf\ningested: 2026-01-01\n"
        f"source_sha256: {'0' * 64}\ntext_sha256: {sha(bad_body)}\nextractor: test\n---\n\n" + bad_body,
        encoding="utf-8")
    return wiki


@unittest.skipUnless(_HAS_YAML, "需要 PyYAML（见 requirements-dev.txt）")
class EdgeFixtureTests(unittest.TestCase):
    def test_deep_scan_reports_expected_edge_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            result = run(AUDIT, wiki, "--json")
            self.assertEqual(result.returncode, 1, result.stderr)
            findings = json.loads(result.stdout)["findings"]
            by_rule = {}
            for finding in findings:
                by_rule.setdefault(finding["rule"], []).append(finding)

            self.assertEqual({f["path"] for f in by_rule.get("FM-01", [])},
                             {"entities/案例/错yaml案.md"})
            self.assertEqual({f["path"] for f in by_rule.get("LINK-02", [])},
                             {"concepts/某概念.md"})
            ambiguity = " ".join(f["message"] for f in by_rule.get("LINK-03", []))
            self.assertIn("案例9-同名案", ambiguity)
            self.assertIn("子丙", ambiguity)
            self.assertIn("子丁", ambiguity)
            dup = " ".join(f["message"] for f in by_rule.get("DUP-01", []))
            self.assertIn("案例1-2016-甲案.md", dup)
            self.assertIn("案例2-2016-乙案.md", dup)
            self.assertEqual({f["path"] for f in by_rule.get("NORM-02", [])},
                             {"entities/法规范/法律/某有效法.md"})

            # 负例：合法别名、合法附件、多行列表不得误报
            fm_errors = {f["path"] for f in by_rule.get("FM-01", [])} | {
                f["path"] for f in by_rule.get("FM-02", [])}
            self.assertNotIn("entities/引用文献/多行标签论文.md", fm_errors)
            all_messages = " ".join(f["message"] for f in findings)
            self.assertNotIn("示意图.png", all_messages)
            dead = by_rule.get("LINK-01", [])
            self.assertEqual(dead, [])

    def test_hash_pair_and_checker_consistency(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            verify = run(EXTRACT, wiki / "raw" / "papers", "--verify")
            self.assertEqual(verify.returncode, 1)
            self.assertIn('"status": "source_drift"', verify.stdout)
            self.assertIn('"status": "ok"', verify.stdout)

            check = run(CHECK, wiki)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("Empty: 1", check.stdout)
            self.assertIn("空目标页", check.stdout)


if __name__ == "__main__":
    unittest.main()
