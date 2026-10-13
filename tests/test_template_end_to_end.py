"""WIKI-08 模板端到端：直接使用仓库模板的结构，验证
摄入（用模板搭页）→ 检查（深检 + 死链）→ 同步（论文—案例）→ 幂等 → 恢复。

深检脚本依赖 PyYAML；缺依赖时整体显式跳过。
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
TEMPLATES = ROOT / "legal-research-wiki" / "assets" / "templates"
AUDIT = ROOT / "legal-wiki-audit-repair" / "scripts" / "multimodal_audit.py"
CHECK = ROOT / "legal-research-wiki" / "scripts" / "check_wikilinks.py"
SYNC = ROOT / "legal-wiki-audit-repair" / "scripts" / "sync_paper_case_links.py"
VERIFY = ROOT / "legal-wiki-audit-repair" / "scripts" / "verify_case_link_sections.py"

try:
    import yaml as _yaml  # noqa: F401
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

REASON = "理由说明" * 25


def run(script, *args):
    return subprocess.run([PY, "-X", "utf8", str(script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def template_headings(name):
    """读取仓库模板的章节骨架（## 级标题），证明页面结构来自模板。"""
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.startswith("## ")]


def build_sections(name, contents):
    chunks = []
    for heading in template_headings(name):
        chunks.append(heading + "\n\n" + contents.get(heading, "（本节内容。）") + "\n")
    return "\n".join(chunks)


def fm(**kw):
    return "\n".join(["---"] + [f"{k}: {v}" for k, v in kw.items()] + ["---", "", ""])


def make_vault(tmp):
    wiki = Path(tmp) / "wiki"

    def write(rel, text):
        path = wiki / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    case_body = build_sections("case.md", {
        "## 与论文的关联": "> 按“观点 ↔ 案例主旨”对应建立：本页条目由案例页展开，镜像到论文页。\n\n"
                           "- **[[测试作者-测试论文]]**：本文观点1（模板端到端验证）以本案要旨为支撑——" + REASON,
        "## 相关概念": "- [[某概念]]",
    })
    write("entities/案例/案例1-2026-测试案.md", fm(
        title="案例1-2026-测试案", created="2026-01-01", updated="2026-01-01", type="case",
        case_id="1", docket="（2026）测试初1号", court="测试法院", decision_date="2026-03-01",
        tags="[案例标签]", sources="[]") + "# 案例1-2026-测试案\n\n" + case_body + "\n")

    paper_body = build_sections("paper.md", {
        "## 与案例的关联": "> 按“观点 ↔ 案例主旨”对应建立：论文核心论点与库内案例裁判要旨的印证关系。\n",
        "## 与其他论文的关联": "- 与 [[测试作者-测试论文二]]：方法上的呼应。\n",
        "## 相关概念": "- [[某概念]]",
    })
    write("entities/引用文献/测试作者-测试论文.md", fm(
        title="测试作者-测试论文", created="2026-01-01", updated="2026-01-01", type="paper",
        tags="[论文标签]", sources="[]") + "# 测试作者-测试论文\n\n" + paper_body)

    write("entities/引用文献/测试作者-测试论文二.md", fm(
        title="测试作者-测试论文二", created="2026-01-01", updated="2026-01-01", type="paper",
        tags="[论文标签]", sources="[]") + "# 测试作者-测试论文二\n\n## 摘要\n\n正文。\n"
        "- 参见 [[测试作者-测试论文]]。\n")

    write("entities/法规范/法律/测试法.md", fm(
        title="测试法", created="2026-01-01", updated="2026-01-01", type="norm",
        tags="[规范标签]", sources="[]", **{"规范层级": "法律", "效力状态": "现行有效",
        "核验日期": "2026-09-01"}) + "# 测试法\n\n## 第一条\n\n> 原文。\n"
        "**与本项目的关联**：见 [[案例1-2026-测试案]]。\n")

    write("concepts/某概念.md", fm(
        title="某概念", created="2026-01-01", updated="2026-01-01", type="concept",
        tags="[概念标签]", sources="[]") + "# 某概念\n\n## 规范依据\n\n- [[测试法]]——第一条确立构成要件。\n"
        "\n## 与比较页的关联\n\n- [[测试比较]]\n\n## 相关概念\n\n- [[案例1-2026-测试案]]\n")

    write("comparisons/测试比较.md", fm(
        title="测试比较", created="2026-01-01", updated="2026-01-01", type="comparison",
        tags="[比较标签]", sources="[]") + "# 测试比较\n\n## 案例表\n\n| 案例 | 争点 |\n|---|---|\n"
        "| [[案例1-2026-测试案]] | 测试争点 |\n\n## 可支持的论文主张\n\n- 见 [[测试作者-测试论文]]。\n")

    pages = ["案例1-2026-测试案", "测试作者-测试论文", "测试作者-测试论文二", "测试法", "某概念", "测试比较"]
    write("index.md", "# 索引\n\n总页数：6\n\n" + "\n".join(f"- [[{p}]]" for p in pages) + "\n")
    write("log.md", "# 操作日志\n\n## [2026-10-01] 摄入｜模板端到端\n\n- 做了什么：建立测试页。\n")
    return wiki


@unittest.skipUnless(_HAS_YAML, "需要 PyYAML（见 requirements-dev.txt）")
class TemplateEndToEndTests(unittest.TestCase):
    def test_templates_check_sync_idempotent_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = make_vault(tmp)

            # 检查：深检无阻断、死链严格口径为零
            scan = run(AUDIT, wiki, "--json")
            self.assertIn(scan.returncode, (0, 1), scan.stderr)
            findings = json.loads(scan.stdout)["findings"]
            noisy = [f for f in findings
                     if f["rule"] in ("FM-01", "LINK-01", "LINK-02", "LINK-03", "LINK-04")]
            self.assertEqual(noisy, [], noisy)
            check = run(CHECK, wiki, "--strict")
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

            # 同步：预演 → 正式 → 幂等
            paper = wiki / "entities" / "引用文献" / "测试作者-测试论文.md"
            before = paper.read_bytes()
            plan = wiki.parent / "plan.json"
            plan.write_text(json.dumps({"papers": [
                {"key": "测试作者-测试论文", "file": "测试作者-测试论文.md"}]},
                ensure_ascii=False), encoding="utf-8")

            preview = run(SYNC, wiki, "--plan", plan, "--dry-run")
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertIn("[预演 diff]", preview.stdout)
            self.assertEqual(paper.read_bytes(), before)

            sync = run(SYNC, wiki, "--plan", plan)
            self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)
            text = paper.read_text(encoding="utf-8")
            self.assertIn("[[案例1-2026-测试案]]", text)

            again = run(SYNC, wiki, "--plan", plan)
            self.assertEqual(again.returncode, 0)
            self.assertIn("总计追加: 0 条", again.stdout)

            verify = run(VERIFY, wiki, "测试作者-测试论文.md")
            self.assertEqual(verify.returncode, 0, verify.stdout)

            # 恢复：备份可原样回滚
            backups = list((wiki / ".maintenance" / "paper-case-link").rglob("测试作者-测试论文.md"))
            self.assertTrue(backups)
            self.assertEqual(backups[0].read_bytes(), before)
            paper.write_bytes(backups[0].read_bytes())
            self.assertEqual(paper.read_bytes(), before)
            scan2 = run(AUDIT, wiki, "--json")
            self.assertIn(scan2.returncode, (0, 1), scan2.stderr)


if __name__ == "__main__":
    unittest.main()
