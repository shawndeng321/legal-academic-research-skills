# Hermes and Codex Skill Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all three repository skills use one shared source format that passes both Hermes and Codex validation.

**Architecture:** Keep one `SKILL.md` per skill and restrict its top-level frontmatter to the validators' common subset. Preserve Hermes-specific discovery data below `metadata.hermes`, add Codex-only UI metadata below `agents/openai.yaml`, and protect the contract with a portable repository test.

**Tech Stack:** Markdown, YAML, Python 3.11+, `unittest`, PyYAML, Hermes local validators, Codex `quick_validate.py`.

## Global Constraints

- Do not change any skill body below the closing frontmatter fence.
- Do not change reference files, templates, or business scripts.
- Keep one shared `SKILL.md`; do not generate separate Hermes and Codex copies.
- Keep descriptions at 60 characters or fewer, beginning with `Use when` and ending with a period.
- Do not install the skills globally, push GitHub, publish releases, or create tags.
- Stage exact paths only; do not use `git add -A`.

---

### Task 1: Common frontmatter contract

**Files:**
- Create: `tests/test_skill_compatibility.py`
- Modify: `chinese-law-paper-writing/SKILL.md:1`
- Modify: `legal-research-wiki/SKILL.md:1`
- Modify: `legal-wiki-audit-repair/SKILL.md:1`

**Interfaces:**
- Consumes: the three skill directories listed in `SKILLS`.
- Produces: `load_yaml(path: Path) -> dict` and `load_skill(path: Path) -> tuple[dict, str]`, reused by later tasks.

- [ ] **Step 1: Write the failing compatibility test**

Create `tests/test_skill_compatibility.py` with:

```python
from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "chinese-law-paper-writing",
    "legal-research-wiki",
    "legal-wiki-audit-repair",
)
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "metadata"}
EXPECTED_DESCRIPTIONS = {
    "chinese-law-paper-writing":
        "Use when planning, writing or checking Chinese legal papers.",
    "legal-research-wiki":
        "Use when building a Chinese legal research wiki.",
    "legal-wiki-audit-repair":
        "Use when auditing or repairing a legal research wiki.",
}


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path} must contain a YAML mapping")
    return data


def load_skill(path: Path) -> tuple[dict, str]:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    if not match:
        raise AssertionError(f"{path} has invalid frontmatter fences")
    frontmatter = yaml.safe_load(match.group(1))
    if not isinstance(frontmatter, dict):
        raise AssertionError(f"{path} frontmatter must be a mapping")
    return frontmatter, content[match.end():]


class SkillCompatibilityTests(unittest.TestCase):
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
                self.assertEqual(
                    frontmatter["description"],
                    EXPECTED_DESCRIPTIONS[skill_name],
                )
                self.assertLessEqual(len(frontmatter["description"]), 60)
                self.assertTrue(frontmatter["description"].startswith("Use when"))
                self.assertTrue(frontmatter["description"].endswith("."))
                self.assertEqual(frontmatter["license"], "MIT")
                metadata = frontmatter["metadata"]
                self.assertIsInstance(metadata, dict)
                self.assertRegex(str(metadata["version"]), r"^\d+\.\d+\.\d+$")
                if "hermes" in metadata:
                    self.assertIsInstance(metadata["hermes"], dict)
                self.assertTrue(body.strip())
                self.assertLessEqual(len(skill_path.read_text(encoding="utf-8")), 100_000)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -X utf8 tests/test_skill_compatibility.py -v
```

Expected: FAIL because current top-level frontmatter contains incompatible keys and the descriptions do not match the 60-character routing contract.

- [ ] **Step 3: Apply the minimal frontmatter changes**

Use these exact frontmatter values:

```yaml
# chinese-law-paper-writing/SKILL.md
---
name: chinese-law-paper-writing
description: Use when planning, writing or checking Chinese legal papers.
license: MIT
metadata:
  version: "4.0.0"
---
```

```yaml
# legal-research-wiki/SKILL.md
---
name: legal-research-wiki
description: Use when building a Chinese legal research wiki.
license: MIT
metadata:
  version: "3.0.0"
---
```

```yaml
# legal-wiki-audit-repair/SKILL.md
---
name: legal-wiki-audit-repair
description: Use when auditing or repairing a legal research wiki.
license: MIT
metadata:
  version: "3.1.0"
  author: Hermes Agent
  hermes:
    tags: [legal-wiki, audit, repair, obsidian, quality-control, batch, rename, wikilink, maintenance]
    related_skills: [legal-research-wiki, llm-wiki, obsidian]
---
```

- [ ] **Step 4: Run the test and verify GREEN**

Run:

```powershell
python -X utf8 tests/test_skill_compatibility.py -v
```

Expected: one test passes.

- [ ] **Step 5: Verify the skill bodies did not change**

Run:

```powershell
git diff --unified=0 e9555bc -- chinese-law-paper-writing/SKILL.md legal-research-wiki/SKILL.md legal-wiki-audit-repair/SKILL.md
```

Expected: changes appear only before the first closing `---` fence in each file.

- [ ] **Step 6: Commit the green frontmatter contract**

```powershell
git add -- tests/test_skill_compatibility.py chinese-law-paper-writing/SKILL.md legal-research-wiki/SKILL.md legal-wiki-audit-repair/SKILL.md
git commit -m "fix: share skill metadata across Hermes and Codex"
```

### Task 2: Codex UI metadata

**Files:**
- Modify: `tests/test_skill_compatibility.py`
- Create: `chinese-law-paper-writing/agents/openai.yaml`
- Create: `legal-research-wiki/agents/openai.yaml`
- Create: `legal-wiki-audit-repair/agents/openai.yaml`

**Interfaces:**
- Consumes: `load_yaml`, `ROOT`, and `SKILLS` from Task 1.
- Produces: one Codex `interface` mapping per skill with `display_name`, `short_description`, and `default_prompt`.

- [ ] **Step 1: Add the failing UI metadata test**

Add this method to `SkillCompatibilityTests`:

```python
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
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -X utf8 tests/test_skill_compatibility.py -v
```

Expected: ERROR for each missing `agents/openai.yaml` file.

- [ ] **Step 3: Generate the three metadata files**

Run the bundled Codex generator with these exact values:

```powershell
$generator = Join-Path $HOME '.codex\skills\.system\skill-creator\scripts\generate_openai_yaml.py'
python -X utf8 $generator chinese-law-paper-writing --interface 'display_name=中国法学论文写作' --interface 'short_description=以可核验来源规划、起草、修改和审核中国法学期刊论文' --interface 'default_prompt=Use $chinese-law-paper-writing to plan or review this Chinese legal journal paper.'
python -X utf8 $generator legal-research-wiki --interface 'display_name=法学研究 Wiki 建库' --interface 'short_description=构建并维护来源可追溯的中国法学研究 Obsidian Wiki' --interface 'default_prompt=Use $legal-research-wiki to build this Chinese legal research wiki.'
python -X utf8 $generator legal-wiki-audit-repair --interface 'display_name=法学 Wiki 审计修复' --interface 'short_description=审计并分批修复法学研究 Wiki 的结构、链接和内容质量' --interface 'default_prompt=Use $legal-wiki-audit-repair to audit this legal research wiki before repairs.'
```

- [ ] **Step 4: Run the test and verify GREEN**

Run:

```powershell
python -X utf8 tests/test_skill_compatibility.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Commit Codex UI metadata**

```powershell
git add -- tests/test_skill_compatibility.py chinese-law-paper-writing/agents/openai.yaml legal-research-wiki/agents/openai.yaml legal-wiki-audit-repair/agents/openai.yaml
git commit -m "feat: add Codex skill interface metadata"
```

### Task 3: Correct installation documentation

**Files:**
- Modify: `tests/test_skill_compatibility.py`
- Modify: `README.md:15`
- Modify: `chinese-law-paper-writing/README.md:86`
- Modify: `legal-research-wiki/README.md:16`
- Modify: `legal-wiki-audit-repair/README.md:20`

**Interfaces:**
- Consumes: the repository slug and `SKILLS` from Task 1.
- Produces: one authoritative root installation guide and three skill README links or exact install commands.

- [ ] **Step 1: Add the failing installation documentation test**

Add this method to `SkillCompatibilityTests`:

```python
    def test_installation_docs_use_real_skill_identifiers(self) -> None:
        repository = (
            "shawndeng321/"
            "hermes-obsidian-legal-cssci-wiki-writing-skills"
        )
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for skill_name in SKILLS:
            self.assertIn(
                f"hermes skills install {repository}/{skill_name}",
                root_readme,
            )
        self.assertIn(".codex\\skills", root_readme)
        self.assertIn("Copy-Item", root_readme)
        self.assertNotIn("hermes skills install <本仓库地址>", root_readme)
        for skill_name in SKILLS:
            skill_readme = (ROOT / skill_name / "README.md").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("git clone <本仓库地址>", skill_readme)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -X utf8 tests/test_skill_compatibility.py -v
```

Expected: FAIL because the root README lacks three exact identifiers and the skill READMEs contain placeholder clone commands.

- [ ] **Step 3: Rewrite only the installation sections**

Use these Hermes identifiers in the root README:

```text
shawndeng321/hermes-obsidian-legal-cssci-wiki-writing-skills/chinese-law-paper-writing
shawndeng321/hermes-obsidian-legal-cssci-wiki-writing-skills/legal-research-wiki
shawndeng321/hermes-obsidian-legal-cssci-wiki-writing-skills/legal-wiki-audit-repair
```

For Codex PowerShell installation, document cloning into a temporary checkout followed by exact `Copy-Item -Recurse` commands from each skill directory into `$HOME\.codex\skills\<skill-name>`. In each skill README, replace the placeholder clone block with the corresponding exact Hermes identifier and point Codex users to the root installation section.

- [ ] **Step 4: Run the full repository test and verify GREEN**

Run:

```powershell
python -X utf8 tests/test_skill_compatibility.py -v
```

Expected: all three tests pass.

- [ ] **Step 5: Commit corrected installation docs**

```powershell
git add -- tests/test_skill_compatibility.py README.md chinese-law-paper-writing/README.md legal-research-wiki/README.md legal-wiki-audit-repair/README.md
git commit -m "docs: correct Hermes and Codex skill installation"
```

### Task 4: Dual-runtime verification

**Files:**
- Verify: all files changed in Tasks 1–3.

**Interfaces:**
- Consumes: the final repository state.
- Produces: fresh Hermes, Codex, unittest, diff, and worktree evidence.

- [ ] **Step 1: Run the repository regression test**

```powershell
python -X utf8 tests/test_skill_compatibility.py -v
```

Expected: three tests pass with zero failures and zero errors.

- [ ] **Step 2: Run Codex validation for every skill**

```powershell
$validator = Join-Path $HOME '.codex\skills\.system\skill-creator\scripts\quick_validate.py'
python -X utf8 $validator chinese-law-paper-writing
python -X utf8 $validator legal-research-wiki
python -X utf8 $validator legal-wiki-audit-repair
```

Expected: `Skill is valid!` three times.

- [ ] **Step 3: Run Hermes validation for every skill**

Run an in-memory check using the installed Hermes `tools.skill_manager_tool` functions `_validate_frontmatter(content, new_skill=True)` and `_validate_content_size(content)`.

Expected: both functions return `None` for all three skills.

- [ ] **Step 4: Inspect the complete compatibility diff**

```powershell
git diff --stat e9555bc..HEAD
git diff --check e9555bc..HEAD
git status --short --branch
```

Expected: no whitespace errors; only the planned tests, three frontmatter blocks, three `agents/openai.yaml` files, four README files, and plan documentation changed. The branch is ahead of `origin/main`; no push occurs.

- [ ] **Step 5: Record final verification without another code commit**

Report exact test counts, validator results, commits, changed-file summary, and any remaining compatibility limitation. Do not claim runtime behavior beyond the validators and repository tests.
