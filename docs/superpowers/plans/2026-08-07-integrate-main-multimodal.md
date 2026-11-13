# Integrate Main Multimodal Updates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the colleague-authored multimodal additions from `origin/main@ac08920` into `codex/hermes-codex-compatibility`, preserving the compatibility branch as the authoritative Hermes/Codex packaging and documentation layer.

**Architecture:** Create regression contracts before merging, then merge `origin/main` with the compatibility branch as first parent so both authors' histories remain intact. Resolve shared files in favor of the compatibility branch's short frontmatter descriptions, install paths, safety boundaries, tests, and `.worktrees/` ignore rule while accepting main's new multimodal references, closed-world rules, audit script, and skill versions. Adapt imported host-specific instructions and validate the audit script against a real temporary Wiki on Windows.

**Tech Stack:** Git worktrees, Markdown skill packages, Python 3.11, `unittest`, PyYAML, Codex `quick_validate.py`.

## Global Constraints

- Target branch: `codex/hermes-codex-compatibility`; do not modify local `main`.
- Merge source: fetched `origin/main@ac08920`.
- Preserve coworker commit history and authorship with a real merge; do not flatten main into copied files.
- Preserve `SKILL.md` descriptions at 60 characters or fewer and retain all `agents/openai.yaml` files.
- Preserve `.worktrees/` in `.gitignore`.
- Do not claim host tools such as `vision_analyze`, `web_extract`, or `faster-whisper` are universally available.
- Do not treat summaries or third-party pages as verified legal evidence.
- Do not push until every verification gate passes and the user authorizes publication.

---

### Task 1: Establish the Integration Checkpoint

**Files:**
- Create: `docs/superpowers/plans/2026-08-07-integrate-main-multimodal.md`

**Interfaces:**
- Consumes: clean worktree at `43c5807` and fetched `origin/main@ac08920`.
- Produces: a recoverable local ref and a committed implementation plan.

- [ ] **Step 1: Create the recovery ref**

  Run: `git branch backup/codex-compatibility-before-main-sync-20260807 43c5807`

  Expected: `git rev-parse backup/codex-compatibility-before-main-sync-20260807` prints `43c5807ba1d306184be51047ea4b1139316796bc`.

- [ ] **Step 2: Commit only this plan**

  Run: `git add -- docs/superpowers/plans/2026-08-07-integrate-main-multimodal.md` followed by `git commit -m "docs: plan main multimodal integration"`.

  Expected: one commit containing only the plan file.

### Task 2: Define Integration Behavior Before the Merge

**Files:**
- Modify: `tests/test_skill_compatibility.py`
- Modify: `tests/test_script_safety.py`

**Interfaces:**
- Consumes: existing package loaders and `ScriptSafetyTests.run_script`.
- Produces: regression tests that fail while multimodal content is absent and pass only when package references, versions, and audit behavior are integrated.

- [ ] **Step 1: Test package completeness and version consistency**

  Add literal expected versions:

  ```python
  EXPECTED_VERSIONS = {
      "chinese-law-paper-writing": "5.1.0",
      "legal-research-wiki": "4.1.0",
      "legal-wiki-audit-repair": "4.2.0",
  }
  ```

  For each skill, assert metadata equals the expected version and that the root/skill README advertises the same version. Assert the nine imported multimodal files exist and are non-empty. For each Markdown link added to the three `SKILL.md` files, resolve the relative target and assert that it exists; this catches renamed upstream references without asserting prose wording.

- [ ] **Step 2: Test the audit script with a real temporary Wiki**

  Create a temporary Wiki containing `index.md`, `SCHEMA.md`, `log.md`, `entities/Topic.md`, `raw/screenshots/sample.png`, and `raw/screenshots/sample.md`. Run `multimodal_audit.py <wiki>` and assert exit code 0, `All raw .md referenced in log`, and `sample.png — extract has 3 body lines`.

- [ ] **Step 3: Test explicit audit scope**

  Run the audit script without an argument and with `WIKI_PATH` removed from the subprocess environment. Assert a non-zero exit code and `WIKI_PATH` in stderr so the script cannot silently inspect `~/wiki`.

- [ ] **Step 4: Verify RED**

  Run: `python -X utf8 -m unittest tests/test_skill_compatibility.py tests/test_script_safety.py -v`.

  Expected: failures caused by the missing multimodal files/versions and missing audit script, while the original twelve tests remain green.

- [ ] **Step 5: Commit the tests**

  Run: `git add -- tests/test_skill_compatibility.py tests/test_script_safety.py` followed by `git commit -m "test: define multimodal integration contract"`.

### Task 3: Merge Main and Resolve Shared Files

**Files:**
- Modify: `README.md`
- Modify: `chinese-law-paper-writing/SKILL.md`
- Modify: `legal-research-wiki/SKILL.md`
- Modify: `legal-wiki-audit-repair/SKILL.md`
- Create: `chinese-law-paper-writing/references/multimodal-citation-format.md`
- Create: `legal-research-wiki/references/multimodal-audio-ingest.md`
- Create: `legal-research-wiki/references/multimodal-bulk-refs.md`
- Create: `legal-research-wiki/references/multimodal-image-ingest.md`
- Create: `legal-research-wiki/references/multimodal-obsidian-headless.md`
- Create: `legal-research-wiki/references/multimodal-pdf-extraction.md`
- Create: `legal-wiki-audit-repair/references/multimodal-reingest-stubs.md`
- Create: `legal-wiki-audit-repair/references/multimodal-sha256-bulk-fix.md`
- Create: `legal-wiki-audit-repair/scripts/multimodal_audit.py`
- Resolve: `tests/test_skill_compatibility.py`
- Resolve: `tests/test_script_safety.py`

**Interfaces:**
- Consumes: `origin/main@ac08920` and the red integration contracts.
- Produces: a staged merge tree with main's multimodal files and the compatibility branch's packaging contract.

- [ ] **Step 1: Start a non-committing merge**

  Run: `git merge --no-ff --no-commit origin/main`.

  Expected: nine multimodal files stage automatically; conflicts are limited to README, three skills, and the two add/add test files.

- [ ] **Step 2: Resolve frontmatter and README**

  Keep these exact descriptions:

  ```yaml
  description: Use when planning, writing or checking Chinese legal papers.
  description: Use when building a Chinese legal research wiki.
  description: Use when auditing or repairing a legal research wiki.
  ```

  Set versions to `5.1.0`, `4.1.0`, and `4.2.0`; keep the compatibility branch's decision table, install paths, verification section, and branch-difference explanation; add main's multimodal overview and correct the audit version to `v4.2.0`.

- [ ] **Step 3: Preserve compatibility tests**

  Resolve both add/add test conflicts with the compatibility branch plus Task 2 additions. Confirm `rg -n '^(<<<<<<<|=======|>>>>>>>)'` returns no conflict markers.

### Task 4: Adapt Imported Multimodal Content

**Files:**
- Modify: `chinese-law-paper-writing/README.md`
- Modify: `legal-research-wiki/README.md`
- Modify: `legal-wiki-audit-repair/README.md`
- Modify: all nine imported multimodal files from Task 3.
- Modify: `legal-wiki-audit-repair/SKILL.md`

**Interfaces:**
- Consumes: upstream multimodal workflows and the repository's legal-evidence/dual-host constraints.
- Produces: cross-host instructions, resolvable references, consistent advertised versions, and a Windows-safe audit script.

- [ ] **Step 1: Align package documentation**

  Advertise `v5.1.0`, `v4.1.0`, and `v4.2.0` in the three skill READMEs. Add the multimodal capabilities to the relevant capability/script sections and remove the nonexistent `references/daily-maintenance.md` pointer.

- [ ] **Step 2: Repair imported references and evidence boundaries**

  Point citation guidance to `citation-integrity.md`, audio/image provenance to `chinese-law-paper-writing/references/multimodal-citation-format.md`, bulk extraction to `multimodal-pdf-extraction.md`, and stub repair to `multimodal-bulk-refs.md`. State that summaries remain discovery stubs and cannot support verified legal propositions, quotations, case numbers, dates, or page references.

- [ ] **Step 3: Make host capability statements conditional**

  Explain that Hermes and Codex may expose different image, audio, web, and code-execution tools. Require capability checks before use; retain the original raw file and mark work pending when no supported tool is available.

- [ ] **Step 4: Fix audit behavior**

  Normalize raw keys with `f"{directory}/{filename}"`, require an argument or `WIKI_PATH`, reject nonexistent roots with exit code 2, remove the duplicate shebang, and update the script usage text.

- [ ] **Step 5: Verify GREEN**

  Run: `python -X utf8 -m unittest tests/test_skill_compatibility.py tests/test_script_safety.py -v`.

  Expected: all integration and existing tests pass.

### Task 5: Verify and Commit the Merge

**Files:**
- Verify: every file staged by the merge and Tasks 2-4.

**Interfaces:**
- Consumes: the resolved merge tree.
- Produces: a local merge commit ready for user review and optional push.

- [ ] **Step 1: Run full repository tests**

  Run both unittest files separately with `-v` and confirm zero failures.

- [ ] **Step 2: Run all skill validators**

  Run `python -X utf8 "$HOME\.codex\skills\.system\skill-creator\scripts\quick_validate.py" <skill-directory>` for each of the three skills and require `Skill is valid!` three times.

- [ ] **Step 3: Run artifact and diff checks**

  Run `python -X utf8 -m py_compile legal-wiki-audit-repair/scripts/multimodal_audit.py`, `git diff --check HEAD`, `git status --short --branch`, `git diff --cached --stat`, and a conflict-marker scan.

- [ ] **Step 4: Commit exact intended paths**

  Stage the explicit README, skill, reference, script, and test paths; commit with `git commit -m "merge: integrate main multimodal updates"`.

- [ ] **Step 5: Report branch state without pushing**

  Report first/second parent hashes, ahead/behind counts, file statistics, test counts, and any remaining review risks. Do not push until the user requests it.

