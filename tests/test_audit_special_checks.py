"""深检「法学专项」检查回归测试（WIKI-10：法规范时效与案件去重）。

覆盖验收：合成样例中，缺核验日期、核验过期、被概念/比较页引用的已废止规范、
同一案号两页（括号全半角不同）均被报告；运行不产生任何写入。
（WIKI-11 的隐私格式检查见本文件下半部分。）

深检脚本依赖 PyYAML（见 requirements-dev.txt）；缺依赖时本测试显式跳过。
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "legal-wiki-audit-repair" / "scripts" / "multimodal_audit.py"

try:
    import yaml as _yaml  # noqa: F401
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def run(wiki, *flags):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), str(wiki), *flags],
        capture_output=True, text=True, encoding="utf-8",
    )


def fm(fields):
    lines = ["---"]
    lines.extend(f"{key}: {value}" for key, value in fields.items())
    lines.extend(["---", "", ""])
    return "\n".join(lines)


def make_vault(tmp):
    wiki = Path(tmp) / "wiki"
    fresh = (date.today() - timedelta(days=60)).isoformat()

    def write(rel, text):
        path = wiki / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    base_norm = {"created": "2026-01-01", "updated": "2026-01-01", "type": "norm",
                 "tags": "[规范标签]", "sources": "[raw/法规范/x.docx]"}
    write("entities/法规范/法律/某有效法.md", fm({
        **base_norm, "title": "某有效法", "规范层级": "法律", "效力状态": "现行有效",
        "生效日期": "2020-01-01", "核验日期": fresh,
    }) + "# 某有效法\n\n## 第一条\n\n> 条文原文。\n")
    write("entities/法规范/法律/某废止规定.md", fm({
        **base_norm, "title": "某废止规定", "规范层级": "司法解释", "效力状态": "已废止",
        "核验日期": "2024-01-01",
    }) + "# 某废止规定\n\n> 已废止说明。\n")
    write("entities/法规范/规章/某缺字段法.md", fm({
        **base_norm, "title": "某缺字段法", "规范层级": "规章",
    }) + "# 某缺字段法\n\n> 条文。\n")

    write("concepts/某概念.md", fm({
        "title": "某概念", "created": "2026-01-01", "updated": "2026-01-01",
        "type": "concept", "tags": "[概念标签]", "sources": "[]",
    }) + "# 某概念\n\n依 [[某废止规定]] 的判断路径展开；另见 [[某有效法]]。\n"
        "联系电话：13912345678。\n")
    write("comparisons/某比较.md", fm({
        "title": "某比较", "created": "2026-01-01", "updated": "2026-01-01",
        "type": "comparison", "tags": "[比较标签]", "sources": "[]",
    }) + "# 某比较\n\n- 依据 [[某废止规定]] 展开对比。\n")

    case_base = {"created": "2026-01-01", "updated": "2026-01-01", "type": "case",
                 "tags": "[案例标签]", "sources": "[raw/cases/x.docx]"}
    write("entities/案例/案例1-2020-甲案.md", fm({
        **case_base, "title": "案例1-2020-甲案", "case_id": "1", "docket": "（2020）最高法行申1234号",
        "court": "最高人民法院", "decision_date": "2020-06-05",
    }) + "# 甲案\n\n> 裁判要旨。\n")
    write("entities/案例/案例2-2020-乙案.md", fm({
        **case_base, "title": "案例2-2020-乙案", "case_id": "2", "docket": "(2020)最高法行申1234号",
        "court": "最高人民法院", "decision_date": "2020-06-05",
    }) + "# 乙案\n\n> 裁判要旨。\n")
    write("entities/案例/案例3-2021-丙案.md", fm({
        **case_base, "title": "案例3-2021-丙案", "case_id": "3", "docket": "（2021）京01行终999号",
        "court": "北京市第一中级人民法院", "decision_date": "2021-03-02",
    }) + "# 丙案\n\n> 裁判要旨。\n")
    write("entities/案例/案例4-2022-丁案.md", fm({
        **case_base, "title": "案例4-2022-丁案", "case_id": "4", "docket": "原文未载明",
    }) + "# 丁案\n\n> 裁判要旨。\n")
    write("entities/案例/案例5-2022-戊案.md", fm({
        **case_base, "title": "案例5-2022-戊案", "case_id": "5", "docket": "原文未载明",
    }) + "# 戊案\n\n> 裁判要旨。\n")

    write("raw/cases/某判决书节选.md",
          "# 某判决书节选\n\n原告：张三，身份证号 110101199001011234，联系电话 13812345678。\n"
          "被告账户 6222021234567890123 收到货款。\n")
    return wiki


def findings_by_rule(result):
    """运行 --json 并按规则编号分组。"""
    assert result.returncode in (0, 1), result.stderr
    data = json.loads(result.stdout)
    grouped = {}
    for finding in data["findings"]:
        grouped.setdefault(finding["rule"], []).append(finding)
    return grouped


def tree_digest(root):
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            path = Path(dirpath) / name
            digest.update(str(path.relative_to(root)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


@unittest.skipUnless(_HAS_YAML, "需要 PyYAML（见 requirements-dev.txt）")
class NormAndDedupeChecks(unittest.TestCase):
    def test_norm_missing_stale_and_referenced(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            grouped = findings_by_rule(run(wiki, "--json"))

            norm01 = {f["path"] for f in grouped.get("NORM-01", [])}
            self.assertEqual(norm01, {"entities/法规范/规章/某缺字段法.md"})
            message = grouped["NORM-01"][0]["message"]
            self.assertIn("效力状态", message)
            self.assertIn("核验日期", message)

            norm02 = {f["path"] for f in grouped.get("NORM-02", [])}
            self.assertEqual(norm02, {"entities/法规范/法律/某废止规定.md"})
            self.assertIn("复核", grouped["NORM-02"][0]["message"])

            norm03 = grouped.get("NORM-03", [])
            self.assertEqual({f["path"] for f in norm03},
                             {"entities/法规范/法律/某废止规定.md"})
            self.assertIn("某概念", norm03[0]["message"])
            self.assertIn("某比较", norm03[0]["message"])

            for rule in ("NORM-01", "NORM-02", "NORM-03"):
                for finding in grouped.get(rule, []):
                    self.assertNotEqual(finding["path"], "entities/法规范/法律/某有效法.md")

    def test_norm_verify_age_config_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            config = wiki / "wiki-audit.config.json"
            config.write_text(json.dumps({"norm_verify_max_age_days": 30}, ensure_ascii=False),
                              encoding="utf-8")
            grouped = findings_by_rule(run(wiki, "--json"))
            norm02 = {f["path"] for f in grouped.get("NORM-02", [])}
            self.assertEqual(norm02, {"entities/法规范/法律/某废止规定.md",
                                      "entities/法规范/法律/某有效法.md"})

    def test_dup_cases_normalized_docket(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            grouped = findings_by_rule(run(wiki, "--json"))
            dup = grouped.get("DUP-01", [])
            self.assertEqual(len(dup), 1, dup)
            message = dup[0]["message"]
            self.assertIn("案例1-2020-甲案.md", message)
            self.assertIn("案例2-2020-乙案.md", message)
            self.assertIn("1234", message)  # 规范化后的案号
            self.assertNotIn("案例3-2021-丙案", message)
            # 「原文未载明」不参与去重
            self.assertNotIn("案例4-2022-丁案", message)
            self.assertNotIn("案例5-2022-戊案", message)

    def test_special_check_read_only_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            before = tree_digest(wiki)
            result = run(wiki)
            self.assertIn("【检查 7｜", result.stdout)
            self.assertIn("法学专项", result.stdout)
            self.assertIn("NORM-01", result.stdout)
            self.assertIn("DUP-01", result.stdout)
            after = tree_digest(wiki)
            self.assertEqual(before, after, "深检必须只读，不得写入任何文件")


@unittest.skipUnless(_HAS_YAML, "需要 PyYAML（见 requirements-dev.txt）")
class PrivacyChecks(unittest.TestCase):
    RAW_REL = "raw/cases/某判决书节选.md"
    CONCEPT_REL = "concepts/某概念.md"

    def test_privacy_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            result = run(wiki, "--json")
            grouped = findings_by_rule(result)
            self.assertNotIn("PRIV-01", grouped)
            note = json.loads(result.stdout)["notes"].get("7", "")
            self.assertIn("未启用", note)

    def test_privacy_findings_masked(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            result = run(wiki, "--privacy", "--json")
            grouped = findings_by_rule(result)
            priv = grouped.get("PRIV-01", [])
            self.assertEqual(len(priv), 4, priv)
            self.assertEqual({f["path"] for f in priv if f["path"] == self.RAW_REL},
                             {self.RAW_REL})
            self.assertEqual({f["path"] for f in priv if f["path"] == self.CONCEPT_REL},
                             {self.CONCEPT_REL})
            categories = {f["message"].split("（")[0].replace("疑似", "") for f in priv}
            self.assertEqual(categories, {"身份证号", "手机号", "银行卡号"})
            for finding in priv:
                self.assertIn("已打码", finding["message"])
                self.assertTrue(finding["location"].startswith("L"), finding)
            raw_locations = {f["location"] for f in priv if f["path"] == self.RAW_REL}
            self.assertEqual(raw_locations, {"L3", "L4"})
            raw_messages = [f["message"] for f in priv if f["path"] == self.RAW_REL]
            self.assertTrue(any("只报告，不修改" in m for m in raw_messages))

            def mask(value):
                return value[:3] + "*" * (len(value) - 5) + value[-2:]

            for full in ("110101199001011234", "13812345678", "13912345678",
                         "6222021234567890123"):
                self.assertNotIn(full, result.stdout, "打码失败：" + full)
            for masked in (mask("110101199001011234"), mask("13812345678"),
                           mask("13912345678"), mask("6222021234567890123")):
                self.assertIn(masked, result.stdout)

    def test_privacy_extra_patterns_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            config = wiki / "wiki-audit.config.json"
            config.write_text(json.dumps(
                {"privacy": {"enabled": True, "extra_patterns": ["原告：张三"]}},
                ensure_ascii=False), encoding="utf-8")
            result = run(wiki, "--json")  # 无需 --privacy：配置已启用
            grouped = findings_by_rule(result)
            priv = grouped.get("PRIV-01", [])
            custom = [f for f in priv if "自定义模式" in f["message"]]
            self.assertEqual(len(custom), 1, priv)
            self.assertEqual(custom[0]["path"], self.RAW_REL)
            note = json.loads(result.stdout)["notes"].get("7", "")
            self.assertNotIn("未配置设计书脱敏规则", note)

    def test_privacy_invalid_regex_config_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)
            config = wiki / "wiki-audit.config.json"
            config.write_text(json.dumps(
                {"privacy": {"extra_patterns": ["["]}}, ensure_ascii=False),
                encoding="utf-8")
            result = run(wiki, "--json")
            self.assertEqual(result.returncode, 2)
            self.assertIn("非法正则", result.stderr)


if __name__ == "__main__":
    unittest.main()
