# Legal Academic Research Skills

[简体中文](README.md) · **English**

Three AI skills for Chinese legal scholarship: build a traceable research wiki, audit and repair its contents, and turn verified material into a journal-paper working draft. The skills support different legal fields and research topics without assuming a particular project.

Host adapters are provided for Codex, Hermes, Devin, Google Antigravity, DeepSeek Harness, and other hosts that load `SKILL.md`. Image reading, transcription, file access, and available tools depend on the host. The working instructions and legal examples are primarily in Chinese.

[Choose a skill](#choose-a-skill) · [Current source update](#current-source-update) · [Installation](#installation) · [Validation and limits](#validation-and-limits) · [Documentation index](docs/README.md)

## Choose a skill

| Goal | Skill | Main output |
|---|---|---|
| Organize papers, cases, statutes, and research methods | [legal-research-wiki](legal-research-wiki/) | A research wiki with source records, links, and quality checks |
| Inspect and safely repair an existing wiki | [legal-wiki-audit-repair](legal-wiki-audit-repair/) | Read-only findings, P0–P3 priorities, scoped repairs, and verification |
| Develop or revise a journal paper | [law-paper-writing](law-paper-writing/) | A research question, argument–evidence–citation chain, journal adaptation, and DOCX output with real footnotes |

For a full paper project, use the writing skill's five questions to define the problem, organize material with the wiki skill, audit the evidence, and then return to drafting and revision. Individual skills can also be used on their own.

## Current source update

The **v2611.13 release (2026-11-13)** removes the Claude Code plugin manifests, installation commands, and dedicated host adapter. It also ships the 17 reviewed improvements to wiki ingestion, auditing, and documentation. Writing rules remain based on upstream **v1.5**. See the [release scope](docs/release-v2611.13.md).

- PDF extraction is reused only when source and output fingerprints and completion status match. Uncertain or changed inputs are preserved for review; empty-text pages require OCR or manual inspection.
- Audit results distinguish passed, failed, and incomplete checks. The default console report is concise; JSON retains structured results, with full paths for index discrepancies.
- Relationship counts cover links between actual knowledge pages. Low link quantity (`LINK-08`) is an observation; broken targets, empty targets, and missing anchors remain defects.
- Machine validation can be reused only for unchanged final inputs and conditions. Pages, indexes, and logs must be saved before final validation. Source verification and page readback remain required.
- Daily checks remain full scans by default. Incremental mode is explicit and conservative; incomplete reads or parsing prevent trusted reuse. Human checks never become passed merely because a cache matched.
- The current model uses tools and independent agents when needed; no model-role registry is required for ingestion and auditing. Skill directories and wiki roots are resolved separately.

See the [detailed update and limitations](docs/nonwriting-updates-2026-11.md). A synthetic small-wiki benchmark did **not** show an advantage over the original direct full scan, so incremental mode is optional.

Download the complete skill directories from [v2611.13](https://github.com/shawndeng321/legal-academic-research-skills/releases/tag/v2611.13), or use source installation below. The bundle and skill versions are recorded in [bundle-release.json](bundle-release.json). Back up local changes before updating. Managed plugin directories remain protected from direct replacement; use the host plugin manager or a separate source installation. Older release notes are retained as historical records.

## Installation

Install each **complete skill directory**, including `references/`, `scripts/`, `assets/`, and `agents/`. Copying only `SKILL.md` is insufficient.

### Hermes Skills Hub

```bash
hermes skills install shawndeng321/legal-academic-research-skills/law-paper-writing
hermes skills install shawndeng321/legal-academic-research-skills/legal-research-wiki
hermes skills install shawndeng321/legal-academic-research-skills/legal-wiki-audit-repair
```

Add `--yes` for a non-interactive terminal. Use `hermes skills list` to confirm installation. Keep a backup before updating an installation with local changes.

### Source installation

```bash
git clone --branch main https://github.com/shawndeng321/legal-academic-research-skills.git
```

Copy the three complete skill directories into the directory scanned by your host. Choose one location per host to avoid duplicate skill names.

| Host | Common location |
|---|---|
| Codex | `~/.codex/skills/` |
| Hermes | `${HERMES_HOME:-~/.hermes}/skills/`; Windows defaults and copy commands are in the Chinese guide |
| Devin | `~/.config/devin/skills/` or `~/.agents/skills/`; install each skill in one location only |
| Google Antigravity | `~/.gemini/config/skills/` or workspace `.agents/skills/` |
| DeepSeek Harness | `~/.dsh/skills/` or project `.dsh/skills/` |

For Windows commands, migration from older skill names, local-change protection, and update rollback, see the [full installation guide](README.md#安装) and [update guide](README.md#自动更新).

### First task

```text
Use legal-wiki-audit-repair in AUDIT_ONLY mode. Inspect only the wiki root I specify.
Report issues, evidence, incomplete checks, and a proposed repair scope. Do not modify files.
```

Provide the material scope and required output. Authorize writes separately when you are ready to repair or ingest content. Start a new agent task after updating skill files.

## Validation and limits

```bash
python3 -m pip install -r requirements-dev.txt
python3 -X utf8 -m unittest discover -s tests -v
python3 tools/prepare_bundle_release.py --check
```

The earlier 17-item behavior snapshot ran **291 tests** on Windows with Python **3.14.4**: one existing fingerprint-test failure and four existing Windows symlink-permission errors remained. Comparison with the 267-test baseline found no new failing or errored test identifiers. This is not an all-green suite or a substitute for full release validation. Python 3.9 is a compatibility target; it was not executed in this verification.

Human source checks, page references, legal currency, and scholarly judgment cannot be proved by a structural scan or cache hit. The existing `NORM-03` detail list remains limited to its first six entries. See the [validation details](docs/nonwriting-updates-2026-11.md#验证与已知限制).

The skills support scholarly work, not contracts, pleadings, client legal advice, theses, or promises of publication. They do not authorize scanning an entire vault or modifying research materials without a defined scope.

## Attribution and license

The writing methods integrate [VictorTran1023/law-paper-writing-skill](https://github.com/VictorTran1023/law-paper-writing-skill), under MIT. Multimodal ingestion and note-level provenance draw on [kigner/multimodal-wiki](https://github.com/kigner/multimodal-wiki) v1.0.0.

MIT: `law-paper-writing` © VictorTran1023 and Shawn Deng; the other two skills © 2026 Shawn Deng. This project is not an official guide, certification, or acceptance guarantee from any agent vendor, Obsidian, or academic journal.
