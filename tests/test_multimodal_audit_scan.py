"""深检脚本（multimodal_audit.py）的缺陷回归测试。

对应任务书 WIKI-01 的验收点：错误 YAML、多行列表、重复 stem、多层目录、
全部 raw 目录、零出站、缺失来源路径、退出码与 --json 契约。
需要 PyYAML；缺依赖时显式跳过（见 requirements-dev.txt）。
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "legal-wiki-audit-repair" / "scripts" / "multimodal_audit.py"

try:
    import yaml as _yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

requires_yaml = unittest.skipUnless(HAVE_YAML, "需要 PyYAML（见 requirements-dev.txt）")


def write(wiki: Path, rel: str, text: str) -> Path:
    path = wiki / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def fm(title="页", created="2026-10-01", updated="2026-10-01",
       page_type="concept", tags="概念", sources="", extra=""):
    sources_line = f"sources: [{sources}]" if sources else "sources: []"
    return (
        "---\n"
        f"title: {title}\n"
        f"created: {created}\n"
        f"updated: {updated}\n"
        f"type: {page_type}\n"
        f"tags: [{tags}]\n"
        f"{sources_line}\n"
        f"{extra}"
        "---\n"
    )


def schema(text="### A. 概念类\n- 概念\n- 方法\n"):
    return text


class AuditScanTests(unittest.TestCase):
    def run_script(self, wiki, *flags):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT), str(wiki), *flags],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def run_json(self, wiki, *flags):
        result = self.run_script(wiki, "--json", *flags)
        self.assertTrue(result.stdout.strip(), "无输出；stderr=" + result.stderr)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:  # pragma: no cover - RED 阶段会触发
            self.fail(f"--json 输出不可解析：{exc}\nstdout 头 500 字：{result.stdout[:500]}")
        return result, data

    @requires_yaml
    def test_wrong_yaml_is_reported_as_parse_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(
                wiki,
                "concepts/坏页.md",
                "---\ntitle: 坏页\ncreated: 2026-10-01\nupdated: 2026-10-01\n"
                "type: concept\ntags: [甲, 乙\nsources: []\n---\n# 坏页\n",
            )

            result, data = self.run_json(wiki)
            findings = data["findings"]
            fm01 = [f for f in findings if f["rule"] == "FM-01"]
            self.assertTrue(fm01, findings)
            self.assertEqual(fm01[0]["path"], "concepts/坏页.md")
            self.assertEqual(fm01[0]["severity"], "broken")
            self.assertIn("concepts/坏页.md", data["unreadable_pages"])
            self.assertEqual(result.returncode, 1)

            human = self.run_script(wiki)
            self.assertIn("解析失败", human.stdout)

    @requires_yaml
    def test_multiline_yaml_tag_list_is_parsed_not_falsely_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema("### A. 概念类\n- 概念、方法\n"))
            write(
                wiki,
                "concepts/甲页.md",
                "---\ntitle: 甲页\ncreated: 2026-10-01\nupdated: 2026-10-01\n"
                "type: concept\ntags:\n  - 概念\n  - 方法\nsources: []\n---\n# 甲页\n",
            )

            _result, data = self.run_json(wiki)
            self.assertEqual(data["counts"]["pages"], 1)
            fm_findings = [
                f for f in data["findings"]
                if f["path"] == "concepts/甲页.md" and f["rule"].startswith("FM")
            ]
            self.assertEqual(fm_findings, [])

    @requires_yaml
    def test_same_named_pages_are_not_silently_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(wiki, "entities/案例/甲.md", fm(title="案例甲") + "# 案例甲\n")
            write(wiki, "entities/论文/甲.md", fm(title="论文甲") + "# 论文甲\n")

            _result, data = self.run_json(wiki)
            self.assertEqual(data["counts"]["pages"], 2)
            dup = [f for f in data["findings"] if f["rule"] == "LINK-03"]
            self.assertTrue(dup)
            message = dup[0]["message"]
            self.assertIn("同名页面", message)
            self.assertIn("entities/案例/甲.md", message)
            self.assertIn("entities/论文/甲.md", message)

    @requires_yaml
    def test_multilevel_directories_keep_full_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(
                wiki,
                "concepts/大类/子类/深页.md",
                "---\ntitle: 深页\ncreated: 2026-10-01\nupdated: 2026-10-01\n"
                "type: concept\ntags: [概念]\n---\n# 深页\n",
            )

            result, data = self.run_json(wiki)
            fm02 = [f for f in data["findings"] if f["rule"] == "FM-02"]
            self.assertTrue(fm02)
            self.assertEqual(fm02[0]["path"], "concepts/大类/子类/深页.md")
            self.assertEqual(result.returncode, 1)

    @requires_yaml
    def test_all_raw_subdirectories_are_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(wiki, "raw/cases/案例汇编.pdf", "%PDF-1.4\n")
            write(wiki, "raw/法规范/行政处罚法.pdf", "%PDF-1.4\n")

            _result, data = self.run_json(wiki)
            self.assertEqual(data["counts"]["raw_files"], 2)
            raw01 = [f for f in data["findings"] if f["rule"] == "RAW-01"]
            self.assertEqual(raw01, [])

    @requires_yaml
    def test_raw_manifest_is_exempt_from_frontmatter_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(wiki, "raw/MANIFEST.md", "# raw 原始材料清单\n\n- raw/papers/某论文.pdf\n")
            write(wiki, "raw/papers/无头提取.md", "正文无 frontmatter。\n")

            _result, data = self.run_json(wiki)
            flagged = {f["path"] for f in data["findings"] if f["rule"] == "RAW-05"}
            self.assertNotIn("raw/MANIFEST.md", flagged)
            self.assertIn("raw/papers/无头提取.md", flagged)

    @requires_yaml
    def test_zero_outbound_page_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(wiki, "concepts/孤页.md", fm(title="孤页") + "# 孤页\n")

            human = self.run_script(wiki)
            self.assertIn("出站链接不足（0 < 2）", human.stdout)
            self.assertNotIn("所有页面出站链接均 ≥2", human.stdout)

    @requires_yaml
    def test_missing_source_path_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(
                wiki,
                "concepts/源页.md",
                fm(title="源页", sources="raw/papers/不存在.pdf, 《示例论文》") + "# 源页\n",
            )

            _result, data = self.run_json(wiki)
            fm06 = [f for f in data["findings"] if f["rule"] == "FM-06"]
            self.assertEqual(len(fm06), 1)
            self.assertIn("不存在.pdf", fm06[0]["message"])
            self.assertEqual(fm06[0]["severity"], "warning")

    @requires_yaml
    def test_exit_codes_follow_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 0 = 通过；--strict 下提示计入 → 1
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(wiki, "index.md", "当前纳入导航的页面：3\n\n- [[概念甲]]\n- [[概念乙]]\n- [[概念丙]]\n")
            write(wiki, "concepts/概念甲.md",
                  fm(title="概念甲") + "# 概念甲\n\n[[概念乙]] [[概念丙]]\n")
            write(wiki, "concepts/概念乙.md",
                  fm(title="概念乙") + "# 概念乙\n\n[[概念甲]] [[概念乙]]\n")
            write(wiki, "concepts/概念丙.md",
                  fm(title="概念丙") + "# 概念丙\n\n[[概念甲]]\n")

            plain = self.run_script(wiki)
            self.assertEqual(plain.returncode, 0, plain.stdout[-2000:])
            strict = self.run_script(wiki, "--strict")
            self.assertEqual(strict.returncode, 1, strict.stdout[-2000:])

        with tempfile.TemporaryDirectory() as tmp:
            # 1 = 存在阻断项
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(
                wiki,
                "concepts/缺字段.md",
                "---\ntitle: 缺字段\ncreated: 2026-10-01\nupdated: 2026-10-01\n"
                "type: concept\ntags: [概念]\n---\n# 缺字段\n",
            )
            result = self.run_script(wiki)
            self.assertEqual(result.returncode, 1)
            self.assertIn("[FM-02]", result.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            # 2 = 未扫描到任何对象
            wiki = Path(tmp)
            result = self.run_script(wiki)
            self.assertEqual(result.returncode, 2)
            self.assertIn("未扫描到任何页面", result.stdout)

    @requires_yaml
    def test_zero_byte_target_and_nested_brackets_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(wiki, "concepts/空页.md", "")
            write(wiki, "concepts/乙页.md", fm(title="乙页") + "# 乙页\n")
            write(
                wiki,
                "concepts/引页.md",
                fm(title="引页") + "# 引页\n\n[[空页]]\n\n| 表 |\n|---|\n| [[甲页 [[乙页]]]] |\n",
            )

            result, data = self.run_json(wiki)
            link02 = [f for f in data["findings"] if f["rule"] == "LINK-02"]
            self.assertTrue(link02)
            self.assertIn("空目标", link02[0]["message"])
            self.assertIn("concepts/空页.md", link02[0]["message"])
            link04 = [f for f in data["findings"] if f["rule"] == "LINK-04"]
            self.assertTrue(any("嵌套方括号" in f["message"] for f in link04), link04)
            self.assertEqual(result.returncode, 1)

    @requires_yaml
    def test_json_findings_have_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(wiki, "concepts/坏页.md",
                  "---\ntitle: 坏页\ntags: [甲\n---\n# 坏页\n")

            _result, data = self.run_json(wiki)
            for key in ("schema_version", "tool", "wiki", "strict", "counts",
                        "findings", "summary", "checks", "unreadable_pages"):
                self.assertIn(key, data)
            self.assertTrue(data["findings"])
            for finding in data["findings"]:
                for key in ("rule", "severity", "scope", "path", "location", "message"):
                    self.assertIn(key, finding)
                    self.assertNotEqual(finding[key], None)
                self.assertIn(finding["severity"], ("broken", "warning"))

    @requires_yaml
    def test_duplicate_keys_reported_and_checks_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(
                wiki,
                "concepts/重键.md",
                "---\ntitle: 重键\ntitle: 重键二\ncreated: 2026-10-01\n"
                "updated: 2026-10-01\ntype: concept\ntags: [概念]\nsources: []\n---\n# 重键\n",
            )

            result, data = self.run_json(wiki)
            self.assertEqual(data["counts"]["pages"], 1)
            fm05 = [f for f in data["findings"] if f["rule"] == "FM-05"]
            self.assertTrue(fm05)
            self.assertTrue(any(
                "重复键" in f["message"] and "title" in f["message"] for f in fm05
            ))
            # 重复键属提示，不阻断；该页其余检查照常执行（无 FM-02）
            fm02 = [f for f in data["findings"] if f["rule"] == "FM-02"
                    and f["path"] == "concepts/重键.md"]
            self.assertEqual(fm02, [])
            self.assertEqual(result.returncode, 0)

    @requires_yaml
    def test_index_count_and_ghosts_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            write(wiki, "SCHEMA.md", schema())
            write(wiki, "index.md", "当前纳入导航的页面：2\n\n- [[甲页]]\n- [[不存在页]]\n")
            write(wiki, "concepts/甲页.md", fm(title="甲页") + "# 甲页\n")

            result, data = self.run_json(wiki)
            rules = {f["rule"] for f in data["findings"]}
            self.assertIn("IDX-01", rules)
            self.assertIn("IDX-03", rules)
            self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
