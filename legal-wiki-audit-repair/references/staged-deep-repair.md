# Staged Deep Repair for Literature Wikis

Use this reference when an existing literature corpus has already passed basic completeness checks and needs deeper maintenance such as bibliography normalization, paper–case links, or article-level statute citations.

## 1. Split a large third batch before editing

Do not treat “third batch” as permission to rewrite all 25 pages at once. Split it into independently verifiable sub-batches:

- **A — Bibliography metadata:** preferably no more than five pages; add issue/volume, printed page range, DOI or article number.
- **B — Paper–case graph:** build a page-to-case mapping first, then add bidirectional links in a small reviewed batch.
- **C — Statute precision:** extract cited instruments from the source PDF, classify each citation, and add `第X条` only when the PDF supports it.

Before any 10+ page edit, produce an affected-page list and a field/link mapping. A user’s approval of the broad phase does not remove the need for a visible mapping.

## 2. Bibliography evidence hierarchy

For each target paper, verify fields in this order:

1. PDF first page: title, author(s), affiliation, journal, year, volume/issue, article number, DOI.
2. PDF printed page footer on the first and last article pages: page range.
3. DOI or article number printed in the PDF, preserving the source’s exact identifier.
4. External catalog/search results only as secondary corroboration, never as a substitute for the PDF.

Do not trust PyMuPDF metadata or a filename alone for affiliation, volume, issue, or pages. Search output can be irrelevant or incomplete.

### Page-range conflict rule

An article number may contain a suffix that looks like a page count, while the PDF’s printed page footers show a different span. Keep the evidence separate:

- record the **printed page range** from the PDF footer;
- record the **article number** exactly as printed;
- do not infer a missing page or silently replace one field with the other;
- if uncertainty remains, mark it for later manual review rather than guessing.

## 3. Where to write bibliographic fields

If the vault's paper pages keep bibliography in a body metadata block, extend the body metadata block rather than silently inventing new YAML fields:

```markdown
> **作者**：作者（单位）
> **期刊**：期刊 | **年份**：YYYY | **卷期**：第X卷第Y期 | **页码**：起—止 | **DOI**：...
```

Use `**期号**` when there is no volume, and `**文章编号**` when the source provides an article number but no DOI. Preserve total-issue information such as `总第283期` when printed. Correct an affiliation in the same surgical edit when the PDF disproves the existing value.

Do not add bibliographic YAML keys unless `SCHEMA.md` is updated to define them and all affected pages will use the same schema.

## 4. Safe edit pattern

1. Read the current page and the relevant PDF evidence.
2. Write each replacement metadata block to a temporary file.
3. Replace only the exact current metadata block with a targeted patch.
4. Update `updated` only on pages that actually changed.
5. Preserve abstract, key arguments, methods, conclusions, links, and sources unless they are in the declared sub-batch.
6. Re-read the changed pages before moving to the next sub-batch.

This same surgical pattern applies to link and statute repairs: map first, patch only the declared section, and never reconstruct a full page from a partial read.

## 5. Acceptance checks after every sub-batch

Run both target-level and recursive vault-level checks:

- every target metadata block matches the planned mapping;
- each DOI/article number/page range is present in the cited PDF evidence;
- all `sources:` paths exist;
- YAML parses for all literature pages;
- required headings remain present and formatted as `## Heading\n\nText`;
- conclusions remain substantive and unchanged unless declared otherwise;
- no PDF artifacts (`］［】【` or replacement characters);
- no malformed or dead wikilinks, using `Path.rglob('*.md')` because entity pages are nested;
- no nested links such as `[[[[...]]]]` after link repair.

Report counts, not just a statement that the batch “looks good.” A phase is complete only when the checks pass and the log entry is appended.

## 6. Log discipline and user-facing reporting

`log.md` is append-only and may contain entries written by other sessions. Read the true tail immediately before appending; do not patch against a remembered last line. Keep the entry for the completed sub-batch separate from the next pending sub-batch.

Report in this order and keep it short:

1. sub-batch size and exact target class;
2. one concrete change per page or grouped field type;
3. key verification counts;
4. the next sub-batch, explicitly not yet started.

## Session-derived example

In the first metadata sub-batch, five papers were enough to expose a source-level affiliation correction and a page-range/article-number distinction. That is why metadata normalization should be staged and PDF-verified before broad paper–case linking or statute enrichment.
