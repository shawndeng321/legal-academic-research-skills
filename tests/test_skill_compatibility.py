from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - 缺依赖时跳过相关测试，而不是模块导入失败
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "law-paper-writing",
    "legal-research-wiki",
    "legal-wiki-audit-repair",
)
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "metadata"}
# Descriptions drive automatic skill selection in Claude Code and Codex, so
# they carry Chinese trigger phrases. Codex allows up to 1024 characters; we
# keep them short enough (<= 300) to stay within Hermes' routing budget.
DESCRIPTION_MAX_LENGTH = 300
DESCRIPTION_TRIGGERS = {
    "law-paper-writing": ("CSSCI", "改稿", "期刊适配", "Not for"),
    "legal-research-wiki": ("建库", "摄入", "知识库查询", "legal-wiki-audit-repair"),
    "legal-wiki-audit-repair": ("updating its Bundle", "全库体检", "每日检修", "检查法学技能更新"),
}
# 版本号单一来源是 bundle-release.json； tools/bump_version.py 同步其余位置。
EXPECTED_VERSIONS = json.loads(
    (ROOT / "bundle-release.json").read_text(encoding="utf-8")
)["skills"]
# 项目专属词表放在本机文件 tests/.project_terms.local.json（不入库）：
# 公开仓库不出现词表内容，每台机器维护自己的词表；文件缺省时词表扫描跳过。
PROJECT_TERMS_FILE = ROOT / "tests" / ".project_terms.local.json"


def _load_project_terms() -> tuple[str, ...]:
    if not PROJECT_TERMS_FILE.exists():
        return ()
    data = json.loads(PROJECT_TERMS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(
        isinstance(item, str) and item for item in data
    ):
        raise ValueError("tests/.project_terms.local.json 必须是非空字符串数组")
    return tuple(data)
MULTIMODAL_FILES = (
    "law-paper-writing/references/multimodal-citation-format.md",
    "legal-research-wiki/references/multimodal-audio-ingest.md",
    "legal-research-wiki/references/multimodal-bulk-refs.md",
    "legal-research-wiki/references/multimodal-image-ingest.md",
    "legal-research-wiki/references/multimodal-obsidian-headless.md",
    "legal-research-wiki/references/multimodal-pdf-extraction.md",
    "legal-wiki-audit-repair/references/multimodal-reingest-stubs.md",
    "legal-wiki-audit-repair/references/multimodal-sha256-bulk-fix.md",
    "legal-wiki-audit-repair/scripts/multimodal_audit.py",
)


def _require_yaml() -> None:
    if yaml is None:
        raise unittest.SkipTest(
            "需要 PyYAML：python3 -m pip install -r requirements-dev.txt"
        )


def load_yaml(path: Path) -> dict:
    _require_yaml()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path} must contain a YAML mapping")
    return data


def load_skill(path: Path) -> tuple[dict, str]:
    _require_yaml()
    content = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    if not match:
        raise AssertionError(f"{path} has invalid frontmatter fences")
    frontmatter = yaml.safe_load(match.group(1))
    if not isinstance(frontmatter, dict):
        raise AssertionError(f"{path} frontmatter must be a mapping")
    return frontmatter, content[match.end():]


class SkillCompatibilityTests(unittest.TestCase):
    def test_bundle_updater_is_wired_identically_into_all_skills(self) -> None:
        updaters = [
            ROOT / name / "scripts" / "legal_skills_update.py"
            for name in SKILLS
        ]
        self.assertTrue(all(path.exists() for path in updaters))
        self.assertEqual(len({path.read_bytes() for path in updaters}), 1)

        descriptions = {}
        for skill_name in SKILLS:
            frontmatter, body = load_skill(ROOT / skill_name / "SKILL.md")
            descriptions[skill_name] = frontmatter["description"]
            self.assertIn("legal_skills_update.py check --json", body)
            self.assertIn("6 小时", body)
            self.assertIn("update_available", body)
            self.assertIn("明确确认", body)

        self.assertIn("updating its Bundle", descriptions["legal-wiki-audit-repair"])
        for skill_name in SKILLS[:-1]:
            self.assertNotIn("updating its Bundle", descriptions[skill_name])

    def test_common_frontmatter_contract(self) -> None:
        for skill_name in SKILLS:
            with self.subTest(skill=skill_name):
                skill_path = ROOT / skill_name / "SKILL.md"
                frontmatter, body = load_skill(skill_path)
                self.assertEqual(frontmatter["name"], skill_name)
                self.assertEqual(
                    set(frontmatter) - ALLOWED_FRONTMATTER_KEYS,
                    set(),
                )
                description = frontmatter["description"]
                self.assertLessEqual(len(description), DESCRIPTION_MAX_LENGTH)
                self.assertTrue(description.startswith("Use when"))
                # Hermes truncates descriptions in its system-prompt skill index
                # to 57 characters + "..." (agent/skill_utils.py,
                # SKILL_PROMPT_DESC_LIMIT = 60), so the first sentence must be
                # a complete summary on its own.
                first_sentence = description.split(". ", 1)[0] + "."
                self.assertLessEqual(len(first_sentence), 57)
                self.assertIn("Chinese legal", first_sentence)
                self.assertRegex(description, r"[\u4e00-\u9fff]")
                for trigger in DESCRIPTION_TRIGGERS[skill_name]:
                    self.assertIn(trigger, description)
                self.assertTrue(frontmatter["description"].endswith("."))
                self.assertEqual(frontmatter["license"], "MIT")
                metadata = frontmatter["metadata"]
                self.assertIsInstance(metadata, dict)
                self.assertRegex(str(metadata["version"]), r"^\d+\.\d+\.\d+$")
                self.assertEqual(
                    str(metadata["version"]),
                    EXPECTED_VERSIONS[skill_name],
                )
                if "hermes" in metadata:
                    self.assertIsInstance(metadata["hermes"], dict)
                self.assertTrue(body.strip())
                self.assertLessEqual(
                    len(skill_path.read_text(encoding="utf-8")),
                    100_000,
                )

    def test_codex_openai_yaml_contract(self) -> None:
        for skill_name in SKILLS:
            with self.subTest(skill=skill_name):
                data = load_yaml(ROOT / skill_name / "agents" / "openai.yaml")
                self.assertEqual(set(data), {"interface"})
                interface = data["interface"]
                self.assertEqual(
                    set(interface),
                    {"display_name", "short_description", "default_prompt"},
                )
                self.assertTrue(interface["display_name"].strip())
                self.assertGreaterEqual(len(interface["short_description"]), 25)
                self.assertLessEqual(len(interface["short_description"]), 64)
                self.assertIn(f"${skill_name}", interface["default_prompt"])

    def test_installation_docs_use_real_skill_identifiers(self) -> None:
        repository = (
            "shawndeng321/"
            "legal-academic-research-skills"
        )
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for skill_name in SKILLS:
            self.assertIn(
                f"hermes skills install {repository}/{skill_name}",
                root_readme,
            )
        self.assertIn(".codex\\skills", root_readme)
        self.assertIn("Copy-Item", root_readme)
        self.assertIn("--yes", root_readme)
        self.assertIn("$hermesHome", root_readme)
        self.assertIn("复制完整技能目录", root_readme)
        self.assertIn("## 2026-09 更新内容", root_readme)
        self.assertIn(
            "claude plugin marketplace add "
            "shawndeng321/legal-academic-research-skills",
            root_readme,
        )
        self.assertIn(
            "claude plugin install legal-academic-research@legal-academic-research",
            root_readme,
        )
        self.assertIn(".claude/skills", root_readme)
        self.assertIn(".agents/skills", root_readme)
        self.assertIn("git clone", root_readme)
        self.assertIn("#安装", root_readme)
        for phrase in (
            "每 6 小时",
            "检查法学技能更新",
            "稍后提醒",
            "忽略此版本",
            "一次性升级",
            "本地修改",
            "自动回滚",
            "新建一个 Agent 任务",
        ):
            self.assertIn(phrase, root_readme)
        self.assertNotIn("hermes skills install <本仓库地址>", root_readme)
        for skill_name in SKILLS:
            skill_readme = (ROOT / skill_name / "README.md").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("git clone <本仓库地址>", skill_readme)
            self.assertIn("../README.md#安装", skill_readme)
            self.assertIn("../README.md#自动更新", skill_readme)
            self.assertIn("--yes", skill_readme)

    def test_claude_code_plugin_manifests_expose_all_skills(self) -> None:
        import json

        plugin = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(plugin["name"], "legal-academic-research")
        self.assertEqual(
            sorted(plugin["skills"]), sorted(f"./{name}" for name in SKILLS)
        )
        release = json.loads((ROOT / "bundle-release.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], release["bundle_version"])
        self.assertEqual(marketplace["name"], "legal-academic-research")
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertEqual(entries["legal-academic-research"]["source"], "./")
        self.assertIn("owner", marketplace)

    def test_skills_are_host_neutral(self) -> None:
        for skill_name in SKILLS:
            with self.subTest(skill=skill_name):
                body = (ROOT / skill_name / "SKILL.md").read_text(encoding="utf-8")
                adapters = (ROOT / skill_name / "references" / "host-adapters.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn("## 预检与运行环境", body)
                self.assertIn("update_channel", body)
                self.assertIn("python3 -X utf8 scripts/legal_skills_update.py check --json", body)
                self.assertNotIn("`python -X utf8 scripts/legal_skills_update.py", body)
                self.assertIn("claude plugin update", adapters)
                self.assertIn("Claude Code 插件安装时跳过预检", body)
                self.assertIn("/plugins/cache/", body)

    def test_skills_document_devin_host_mapping(self) -> None:
        adapter_bodies = {
            skill_name: (ROOT / skill_name / "references" / "host-adapters.md").read_bytes()
            for skill_name in SKILLS
        }
        self.assertEqual(len(set(adapter_bodies.values())), 1)
        for skill_name in SKILLS:
            with self.subTest(skill=skill_name):
                adapters = adapter_bodies[skill_name].decode("utf-8")
                body = (ROOT / skill_name / "SKILL.md").read_text(encoding="utf-8")
                for section in ("## Claude Code", "## Google Antigravity", "## Devin"):
                    self.assertIn(section, adapters)
                self.assertIn("~/.config/devin/skills/", adapters)
                self.assertIn("Base directory", adapters)
                self.assertIn("ask_user_question", adapters)
                self.assertIn("同一会话", body)
                self.assertIn("](references/host-adapters.md)", body)

    def test_skills_document_dsh_host_mapping(self) -> None:
        adapter_bodies = {
            skill_name: (ROOT / skill_name / "references" / "host-adapters.md").read_bytes()
            for skill_name in SKILLS
        }
        self.assertEqual(len(set(adapter_bodies.values())), 1)
        adapters = next(iter(adapter_bodies.values())).decode("utf-8")
        for expected in (
            "## DeepSeek Harness（DSH）",
            "~/.dsh/skills/",
            "~/.agents/skills/",
            "/law-paper-writing",
            "ask_user_question",
            "read_image",
            "Base directory",
            "workspace-write",
            "update_channel",
        ):
            self.assertIn(expected, adapters)
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("| DeepSeek Harness（DSH） |", root_readme)
        self.assertIn("~/.dsh/skills/", root_readme)
        self.assertIn("/law-paper-writing", root_readme)

    def test_skill_files_contain_no_project_specific_terms(self) -> None:
        terms = _load_project_terms()
        if not terms:
            self.skipTest(
                "未配置 tests/.project_terms.local.json（本机项目词表），词表扫描跳过"
            )
        for skill_name in SKILLS:
            for path in sorted((ROOT / skill_name).rglob("*")):
                if path.suffix not in {".md", ".py", ".yaml"}:
                    continue
                relative = path.relative_to(ROOT).as_posix()
                if "/evals/" in relative or relative.endswith("legal_skills_update.py"):
                    continue
                text = path.read_text(encoding="utf-8")
                for term in terms:
                    with self.subTest(path=relative):
                        self.assertNotIn(term, text)

    def test_wiki_page_templates_are_complete_and_parse(self) -> None:
        templates = ROOT / "legal-research-wiki" / "assets" / "templates"
        schema = (templates / "SCHEMA.md").read_text(encoding="utf-8")
        types = set(
            re.search(r"^type: (.+?)\s*$", schema, re.M).group(1).replace(" ", "").split("|")
        )
        required = {
            "title", "created", "updated", "type", "tags", "sources",
            "source_confidence", "analysis_status",
        }
        expected = {
            "case.md": "case", "paper.md": "paper", "concept.md": "concept",
            "comparison.md": "comparison", "norm.md": "norm", "norm-entity.md": "norm",
            "norm-version.md": "norm", "norm-clause-version.md": "norm",
            "research-design.md": "research-design",
            "claim-evidence-matrix.md": "research-design",
            "journal-style-card.md": "methodology", "model-article.md": "model-article",
            "anchor-draft.md": "draft", "moc.md": "moc", "handoff.md": "handoff",
            "writing-outline.md": "query",
            "wiki-design-brief.md": "research-design",
        }
        for name in ("SCHEMA.md", "index.md", "log.md", "README.md"):
            self.assertTrue((templates / name).exists(), name)
        for name, page_type in expected.items():
            with self.subTest(template=name):
                frontmatter, body = load_skill(templates / name)
                self.assertEqual(frontmatter["type"], page_type)
                self.assertIn(page_type, types)
                self.assertEqual(required - set(frontmatter), set())
                self.assertTrue(body.strip())
        brief = (templates / "wiki-design-brief.md").read_text(encoding="utf-8")
        for group in ("## A 目的", "## B 研究问题", "## C 未来怎么用", "## 加深模式", "## 落地决定"):
            self.assertIn(group, brief)
        skill = (ROOT / "legal-research-wiki" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/wiki-design-interview.md", skill)
        interview = (
            ROOT / "legal-research-wiki" / "references" / "wiki-design-interview.md"
        ).read_text(encoding="utf-8")
        for group in "ABCDEFGHIJ":
            self.assertIn(f"### {group} ", interview)
        self.assertIn("加深模式", interview)
        readme = (templates / "README.md").read_text(encoding="utf-8")
        for name in expected:
            self.assertIn(f"`{name}`", readme)

    def test_cross_skill_references_do_not_assume_a_shared_directory(self) -> None:
        cross_link = re.compile(
            r"\]\(\.\./\.\./(?:" + "|".join(SKILLS) + r")/"
        )
        for skill_name in SKILLS:
            body = (ROOT / skill_name / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=skill_name):
                self.assertIn("## 配套技能", body)
                self.assertIn("未安装时", body)
                self.assertIn("按**技能名**找到该技能", body)
            for path in (ROOT / skill_name).rglob("*.md"):
                with self.subTest(path=path.relative_to(ROOT).as_posix()):
                    self.assertIsNone(cross_link.search(path.read_text(encoding="utf-8")))

    def test_every_skill_has_behavioral_pressure_tests(self) -> None:
        for skill_name in SKILLS:
            with self.subTest(skill=skill_name):
                text = (ROOT / skill_name / "evals" / "pressure-tests.md").read_text(
                    encoding="utf-8"
                )
                scenarios = re.findall(r"^#{2,3} \d+\. ", text, re.M)
                self.assertGreaterEqual(len(scenarios), 9)
                self.assertGreaterEqual(text.count("**必须**"), len(scenarios))
        for skill_name in ("legal-research-wiki", "legal-wiki-audit-repair"):
            text = (ROOT / skill_name / "evals" / "pressure-tests.md").read_text(encoding="utf-8")
            self.assertGreaterEqual(text.count("**不得**"), 15)

    def test_documentation_has_no_known_stale_metadata_or_placeholders(self) -> None:
        readmes = [ROOT / "README.md"]
        readmes.extend(ROOT / skill_name / "README.md" for skill_name in SKILLS)
        combined = "\n".join(path.read_text(encoding="utf-8") for path in readmes)
        root_readme = readmes[0].read_text(encoding="utf-8")
        paper_readme = (ROOT / "law-paper-writing" / "README.md").read_text(
            encoding="utf-8"
        )
        paper_skill = (ROOT / "law-paper-writing" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("Obisidian", root_readme)
        self.assertIn("SKILL.md", root_readme)
        self.assertIn("agents/openai.yaml", root_readme)
        self.assertIn("X.Y.Z", root_readme)
        self.assertIn("Claude Code、Codex、Hermes、Devin", root_readme)
        self.assertNotIn("兼容性测试 8/8", root_readme)
        self.assertNotIn("脚本安全测试 9/9", root_readme)
        self.assertIn("兼容性、脚本安全与 Bundle 更新器测试", root_readme)
        self.assertNotIn("尚未合并到 `main`", combined)
        self.assertNotIn("当前优化分支", combined)
        self.assertNotIn("合并到 `main` 后", combined)
        self.assertNotIn("<本技能包仓库地址>", paper_readme)
        self.assertIn("版本号格式：X.Y.Z", paper_skill)

    def test_large_skill_uses_reference_for_pitfalls(self) -> None:
        skill_path = ROOT / "legal-research-wiki" / "SKILL.md"
        skill_content = skill_path.read_text(encoding="utf-8")
        pitfalls_reference = (
            ROOT / "legal-research-wiki" / "references" / "pitfalls-and-lessons.md"
        )
        self.assertIn("references/pitfalls-and-lessons.md", skill_content)
        self.assertLessEqual(len(skill_content), 95_000)
        self.assertTrue(pitfalls_reference.exists())
        self.assertTrue(pitfalls_reference.read_text(encoding="utf-8").strip())

    def test_multimodal_package_is_complete_and_versions_are_consistent(self) -> None:
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for skill_name, version in EXPECTED_VERSIONS.items():
            with self.subTest(skill=skill_name):
                skill_readme = (ROOT / skill_name / "README.md").read_text(
                    encoding="utf-8"
                )
                # 机器字段仍是三段；公开日期标签的首版省略当天序号 0。
                public_tag = f"v{version.rsplit('.', 1)[0]}" if version.endswith(".0") else f"v{version}"
                self.assertIn(public_tag, root_readme)
                self.assertIn(public_tag, skill_readme)
                self.assertIn(version, root_readme)
                self.assertIn(version, skill_readme)

        for relative_path in MULTIMODAL_FILES:
            with self.subTest(path=relative_path):
                path = ROOT / relative_path
                self.assertTrue(path.exists(), relative_path)
                self.assertTrue(path.read_text(encoding="utf-8").strip())

    def test_obsidian_headless_guidance_protects_credentials_and_concurrent_edits(
        self,
    ) -> None:
        guidance = (
            ROOT
            / "legal-research-wiki"
            / "references"
            / "multimodal-obsidian-headless.md"
        ).read_text(encoding="utf-8")
        self.assertIn("\nob login\n", guidance)
        self.assertNotRegex(guidance, r"ob login[^\n]*--(?:email|password)")
        self.assertIn("并发", guidance)
        self.assertIn("备份", guidance)

    def test_local_markdown_links_in_integrated_skills_resolve(self) -> None:
        documents = [ROOT / skill_name / "SKILL.md" for skill_name in SKILLS]
        documents.extend(
            ROOT / relative_path
            for relative_path in MULTIMODAL_FILES
            if relative_path.endswith(".md")
        )
        for document in documents:
            with self.subTest(document=document.relative_to(ROOT)):
                self.assertTrue(document.exists(), document)
                content = document.read_text(encoding="utf-8")
                for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
                    if "://" in target or target.startswith("#"):
                        continue
                    resolved = (document.parent / target.split("#", 1)[0]).resolve()
                    self.assertTrue(
                        resolved.exists(),
                        f"{document.relative_to(ROOT)} -> {target}",
                    )


if __name__ == "__main__":
    unittest.main()
