# Systematic Vault Audit and Optimization Ledger

Use this reference when the user asks for a whole-vault diagnosis, classification/architecture review, representative page sampling, or an optimization plan that later agents can execute.

## 1. Scope contract: diagnose before repairing

A request such as “先不要改，只是排查” means existing content, source files, scripts, and Obsidian configuration are read-only. If the user separately requests an audit/optimization file, that new artifact is the only allowed write. State this exception before working and record it in the artifact.

Do not silently repair findings during the audit. A clean audit must preserve evidence for user review and prevent scope creep.

## 2. Orientation and corpus boundaries

Read, in order:

1. `SCHEMA.md`
2. `index.md`
3. recent `log.md`
4. the existing optimization ledger, if present
5. directory inventory, including vault root and hidden operational directories

Classify files before counting:

- formal content pages
- root metadata (`SCHEMA.md`, `index.md`, logs)
- immutable `raw/` sources
- scripts and generated reports
- Obsidian configuration
- zero-byte/root ghost notes

Do not mix schema examples or historical log links with live content defects. Do not count a newly requested optimization ledger as a formal content page unless the schema explicitly says so.

## 3. Two separate audit tracks

### A. Technical health

Check recursively:

- YAML parse and required fields
- actual source-path existence
- index coverage and count accuracy
- live dead links
- empty or thin pages and empty sections
- root-level zero-byte notes
- duplicate filenames/titles and naming anomalies
- `updated` dates versus known edit records
- raw-source coverage, duplicate hashes, and persistent manifest availability

### B. Academic usefulness

Technical correctness is not enough. Also check:

- whether claims are traceable to raw sources or verified entity pages
- whether a research hypothesis is incorrectly written as an established empirical fact
- whether factual/case-source sections are separated from agent-authored analysis
- whether concept pages contain specific literature and case examples
- whether paper, case, concept, draft, research-design, and comparison layers form useful paths
- whether cross-links state a concrete relation rather than “related/relevant”
- whether comparison/synthesis pages exist for group-case research
- whether confidence/status fields distinguish verified facts, provisional synthesis, and unresolved controversy

A page can be long, have valid YAML, and contain zero dead links while still being academically unsafe.

## 4. Graph audit: distinguish reachability from research structure

Build the inbound map from **formal content pages only**. Index links prove reachability but should not count as substantive inbound edges. Logs and documentation examples should be reported separately.

Measure at least:

- paper → draft and draft → paper
- paper ↔ paper
- paper ↔ case
- concept ↔ case
- research-design ↔ content
- comparison → evidence pages
- category-to-category edge matrix
- formal-content orphans

Inspect graph shape, not just edge counts. A star graph where dozens of cases point to the same 2–3 anchors can look dense but provide little differentiated knowledge. Never add links merely to reduce the orphan count; every edge needs a stated doctrinal, factual, procedural, temporal, or methodological relation.

## 5. Detect templated analysis and false density

For each repeated page type, compare section bodies after normalizing whitespace, numbers, and wikilinks. Useful signals:

- number of unique normalized bodies per section
- largest duplicate group
- repeated long paragraphs across many files
- duplicate “facts” and “procedural history” sections within the same case
- the same related-paper or related-case bundle across unrelated entities
- boilerplate phrases claiming comparability without naming the actual shared issue

Minimal section-fingerprint pattern:

```python
import re, hashlib

def normalize_section(text):
    text = re.sub(r'\[\[[^\]]+\]\]', '<LINK>', text)
    text = re.sub(r'\d+', '<N>', text)
    text = re.sub(r'\s+', '', text)
    return hashlib.sha256(text.encode()).hexdigest()
```

Counts only locate risk; they do not prove a substantive error. Confirm by reading one high-quality benchmark and one suspicious outlier, then compare both with the source material where factual or legal accuracy is at issue.

## 6. Sampling protocol

For each major category, inspect 1–2 pages:

- one benchmark/representative page
- one outlier chosen by thinness, size, unusual headings, low links, high template similarity, or source irregularity

For empty categories, report the architectural implication instead of inventing a sample. In group-case research, an empty `comparisons/` layer is often a meaningful gap; an empty `queries/` layer may be harmless.

Use sampled pages to illustrate system findings, but do not generalize a content error to the full category without corpus-level evidence.

## 7. Schema-drift and provenance rules

Compare actual frontmatter types, tags, and source values against SCHEMA. Distinguish:

- missing raw path: path-like value points to no file
- semantic schema drift: `sources:` contains author names, user oral input, directories, or wiki entities rather than raw files

Do not call semantic drift “source files missing.” A durable schema may separate:

- `sources:` immutable raw files
- `references:` wiki entities or published authorities
- `source_note:` user-provided explanation
- `derived_from:` synthesis pages
- `corpus:` aggregate directories/datasets

For legal corpora, type-specific metadata is usually necessary for Obsidian Properties/Bases: case number, decision date, court, source level, outcome, issues; and paper author, journal, year, pages, DOI/article number.

## 8. Generator-script safety audit

Any in-vault batch generator should be treated as part of the knowledge architecture. Check for:

- hard-coded absolute paths
- stale output directories
- direct `open(..., 'w')` overwrite
- absent `--dry-run`, `--no-clobber`, backup, manifest, mapping list, and acceptance tests
- automatic generation of analytical sections or generic links

Until fixed and tested in a temporary directory, mark unsafe generators “do not run.” Generators should extract source facts and structure; research judgments such as dispute focus, adjudication method, group-case position, and cross-case relations require evidence-based review.

## 9. Obsidian-specific audit

Inspect graph configuration and root-note behavior:

- color groups by directory/category
- unresolved-link and orphan display
- direction arrows for QA
- default location for new notes
- root-level zero-byte notes created from unresolved links

Recommend separate research and QA graph views. For multi-dimensional legal cases, prefer topic maps/MOCs, Bases, and faceted Chinese tags over physically moving each case into a single topic folder.

## 10. Severity and sequencing

Use:

- **P0**: data loss, raw-source modification, mass YAML breakage, widespread live dead links
- **P1**: false facts, wrong source mapping, misleading legal analysis, unsafe overwrite script
- **P2**: schema drift, provenance weakness, orphan/star graph, missing comparison layer, stale metadata
- **P3**: formatting, naming, index presentation, graph appearance

Repair order:

1. establish safety boundaries
2. pilot 5–8 high-risk pages
3. update/test schema on a small set
4. rebuild evidence-backed relationships
5. create comparison/navigation layers
6. standardize tags, dates, formatting, and graph settings
7. defer statute-level work until authoritative law materials and scope are confirmed

## 11. Optimization ledger design

A root optimization ledger should be append-only and contain:

- scope and non-modification statement
- baseline counts and passed checks
- representative-page findings
- numbered findings (`OPT-001`, etc.) with evidence, risk, proposed repair, and acceptance criteria
- phased execution order
- exact small pilot batch
- global acceptance checklist
- append-only execution records

Future run template:

```markdown
## [YYYY-MM-DD] OPT-XXX | 状态：完成/部分完成/阻塞
- 执行范围：
- 修改前证据：
- 原始材料：
- 实际修改文件：
- 具体修改：
- 未修改/延后项目：
- 验收结果：YAML、来源、死链、双向链接、内容完整性、格式
- 风险或待人工判断：
- 对未来建库规则的新增经验：
```

Keep the global action log concise; keep detailed evidence and acceptance results in the optimization ledger. Each optimization should update both without duplicating the full narrative.

### Three maintenance files, not two duplicate logs

When reorganizing a vault's audit/optimization records, give each file one role:

1. **排查修复流程与整改台账** (process manual + issue ledger): how to inspect, open findings (OPT-001-style numbered items with acceptance criteria), and a rule write-back zone. Renaming a bare `优化log.md` to this name makes the dual role explicit.
2. **`log.md`** (timeline): one line per action pointing to the ledger and `.maintenance/`; never duplicate the full execution narrative.
3. **`.maintenance/OPT-编号/`** (evidence): backups, diffs, hashes and manifests per batch.

Detailed narratives live in exactly one place. Historical log entries that mention an old filename are intentional false positives: keep them and update only live references.

### Rule write-back discipline

The agent may register rule candidates (`RULE-CANDIDATE-XXX`) but never self-confirm them. Promotion to a confirmed rule requires all of: (1) recurrence in at least two independent batches; (2) page plus raw-source evidence; (3) a passing full-vault regression; (4) no change to the research question, core classification, source credibility, legal validity or statistical definitions; (5) user confirmation, or membership in quality rules the user has already approved. This keeps project-level learning auditable without letting the model silently change the research contract.

## 12. Durable lessons

- “No empty pages” is only the first quality layer. Plausible-looking templated analysis is more dangerous than an obvious blank page.
- “Zero dead links” does not prove a meaningful network.
- “Every case has outbound links” does not prove bidirectionality or non-orphan status.
- “Every raw file is referenced” does not prove paragraph-level provenance.
- Automated relationship generation should default to no link when evidence is insufficient.
- Audit findings should be actionable by another agent: exact scope, examples, acceptance checks, and a safe batch order—not merely prose criticism.
