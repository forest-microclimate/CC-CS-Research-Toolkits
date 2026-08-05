---
name: sci-file-index
description: Build/update a catalog of a scientific-literature folder (books, chapters, theses, articles, supplements, datasets) into a confidence-tiered metadata index -- extract per-file metadata, RESOLVE cryptic publisher-code filenames (stem=>DOI) and scanned/image-only PDFs (OCR => DOI, or gated CrossRef title-search), keep a last-wins override layer, link supplements to parents, flag duplicates, validate corpus completeness and audit row-identity consistency (missing-field standing alarm; borrowed-/cited-DOI detection), and NEVER fabricate. Use when indexing or cataloging a folder of PDFs/papers, resolving cryptic or scanned documents, building a paper_index, curating bibliographic metadata at scale, or auditing an existing index for missing or inconsistent identity fields (missing author/year/publication, borrowed or cited-reference DOIs). Metadata cataloging only -- NOT paper-content reading, summarizing, figure extraction, or literature review.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# sci-file-index — catalog a literature folder; resolve cryptic names + scanned PDFs; never fabricate

Catalogs ANY folder of scientific literature into a confidence-tiered metadata index. Covers the hard cases: cryptic publisher-code filenames (`BF00385604.pdf`) and old scanned/image-only PDFs (OCR). NEVER fabricates — a blank field + a WHY note beats a plausible guess.

BUNDLED TOOL: `scripts/sci_file_index.py` (pure py3 stdlib + poppler CLI). Loading this skill runs `kernel.py`, which defines wrappers: `sfi_extract(folder)`, `sfi_build(folder)`, `sfi_resolve(folder, mailto=)`, `sfi_ocr(folder, mailto=)`, `sfi_apply(folder)`, and `sfi_rename(folder, apply=, undo=, config=)` (PROC.10 — the ONE wrapper that renames files on disk; dry-run by default). Call them in a `python` cell in the env that has poppler.

## When to invoke
- User asks to index / catalog / inventory a folder of papers, PDFs, books, theses, supplements into a metadata table.
- Cryptic publisher-code filenames or old scanned/image-only PDFs to identify.
- Build/update a `paper_index.csv`, resolve weak rows via DOI/CrossRef, link supplements to parents, flag duplicates.
- RECURRING use: re-index a growing library — the tool is idempotent + incremental (re-run = update).
- OUT of scope (redirect): reading/summarizing/analyzing paper CONTENT, figure extraction, literature review => `literature-review`. This is file-level METADATA cataloging ONLY.

## Environment (Science-specific)
The tool needs poppler on PATH (`pdfinfo pdftotext pdffonts pdftoppm`); OCR additionally needs `ocrmypdf` or `tesseract`. The default `python` env does NOT have these. Create/reuse a conda env once:
`manage_environments(mode="create", name="sci-index", packages=["poppler"])` (add `tesseract`/`ocrmypdf` for the OCR path). Then pass `environment="sci-index"` to every `python`/`bash` cell that calls the `sfi_*` wrappers, and load THIS skill in that env so `kernel.py` binds there.
The folder to index is usually a host-granted path — `request_host_access(host_path=...)` first (ro is enough for indexing; the index/override/sidecar artifacts are WRITTEN INTO the folder, so rw if you want them to persist there, else point `--index`/`--overrides` at the workspace).

## Pipeline (3 artifacts: raw <= extract | overrides <= curation | index <= merge)
ALL index outputs live in `<dir>/index/` [FACT.index_subdir] — the articles folder stays clean; the scan EXCLUDES `index/` so it never catalogs its own output.
- `_sfi_raw.csv`      <= `sfi_extract`: one row/file (pages, chars_page1, n_fonts, embedded title/author, producer, DOI, snippet). Blanks expected. NEVER hand-edit.
- `_sfi_overrides.tsv` <= curation: the ONLY hand-edit surface. 8 TAB cols, `#` header, LAST-WINS.
- `paper_index.csv`   <= `sfi_build`: the PRODUCT (merge of raw + overrides). Hand-edits CLOBBERED on rebuild.
- `_sfi_review.tsv`   <= `sfi_resolve`/`sfi_ocr`: staging surface for CrossRef/OCR results BEFORE overrides (audit against mis-hits). `sfi_apply` promotes it.
ORDER: `sfi_extract` -> `sfi_build` -> (`sfi_resolve` and/or `sfi_ocr`) -> review `_sfi_review.tsv` -> `sfi_apply` -> `sfi_build` -> (OPTIONAL) `sfi_rename` (dry-run -> review -> apply). Re-run on an unchanged folder => NO diff.

```python
# in env sci-index, after loading this skill:
folder = "/path/to/granted/library"
mail = host.get_user_email()            # CrossRef polite pool; omit if unavailable
sfi_extract(folder); sfi_build(folder)  # offline pass: filename-parse + cryptic->DOI + classify
sfi_resolve(folder, mailto=mail)        # weak rows -> CrossRef -> _sfi_review.tsv
# inspect _sfi_review.tsv, then:
sfi_apply(folder); sfi_build(folder)    # fold reviewed rows into the index
# OPTIONAL canonical rename (PROC.10) — needs a rw-granted folder:
sfi_rename(folder)                      # DRY-RUN: writes index/_sfi_rename_plan.tsv (review it)
sfi_rename(folder, apply=True)          # execute; ledgered + reversible
# sfi_rename(folder, undo=True)         # reverse the most recent apply batch
```

## PROC.1 scan + classify (exclusions)
Non-recursive; one folder. EXCLUDES: dotfiles; `_*` (own artifacts); `~$*` (Word lock/temp); the index file; a `*.docx` whose same-stem `.pdf` exists (the exported twin); archives `*.zip|.tar|.gz|.7z|.rar` (publisher bundles). A data `.csv`/`.xlsx` IS indexed as record_type=dataset, confidence=n/a.

## PROC.2 extract (pdfinfo / XMP / pdftotext / filename-parse)
Per PDF: pdfinfo Pages + embedded Title/Author + Producer; pdffonts embedded-font count (feeds the scanned test); page-1 non-space char count; DOI regex `10\.\d{4,9}/[-._;()/:A-Za-z0-9]+` on page-1/2 text, else XMP/Subject/Title/Keywords. FILENAME-PARSE (highest yield): ` - `-delimited `Journal - Year - Author - Title.pdf` (Wiley/OUP) => author+year+title DIRECTLY, confidence=high, NO network.

## PROC.3 triage (ORDERED else-if; earlier branch wins)
1. in overrides => SKIP (idempotence).
2. author AND year AND title present => OK; confidence=high; STOP. (A resolved file NEVER reaches the scanned test.)
3. ELSE IF chars_page1 < 100 OR n_fonts == 0 => scanned_row => OCR (PROC.5).
4. ELSE IF author OR year missing => weak_row: DOI => LOOKUP; else stem matches a doi_pattern => derive => LOOKUP; else title-ish page-1 line => gated SEARCH; else unresolved: blank + confidence=low + note=WHY.

## PROC.4 cryptic filename => DOI (pure derivation, no network)
`^BF\d+`=>`10.1007/<stem>` | `^A_\d+`=>`10.1023/A:<digits>` | `^s\d{4,5}-`=>`10.1007/<stem>` | `^978-`=>`10.1007/<stem>` (book; blank author => medium is CORRECT) | `^annurev`=>`10.1146/<stem>` | `^(bg|gmd|acp|hess|essd)-`=>`10.5194/<stem>`. Elsevier `1-s2.0-S<PII>-main`: PII != DOI => prefer the captured DOI. PNAS `pnas.<id>si`/`.sd0N` => supplement|dataset of `10.1073/pnas.<id>`. A derived DOI is a CANDIDATE => confirm at CrossRef.

## PROC.5 scanned => OCR (detect | ocrmypdf or pdftoppm+tesseract | mine page-1 | quality gates | sidecars)
DETECT (any 1): page-1 non-space chars < 100 AFTER stripping download/access boilerplate (watermark lines — 'Downloaded from', 'Brought to you by', 'This content downloaded', 'For personal use only', proxy/ezproxy/JSTOR stamps, bare URLs); OR pdffonts lists no fonts. [FACT.watermark_scan] (defect #42): a scanned offprint often carries ONLY a text watermark over an image body — a raw char-count > 100 then hides an image-only file whose identity a text search CANNOT see. Strip boilerplate BEFORE the count (the merged `cmd_extract` does this) so these route to OCR. NEVER modify the original — OCR => SIDECAR `<dir>/index/_ocr/<stem>.pdf` (+ `.txt`). PREFERRED `ocrmypdf --skip-text --rotate-pages --deskew -l eng`; FALLBACK renders one page at a time `pdftoppm -r 300 -png -f N -l N` => `tesseract --psm 1 -l eng`. FRONT-MATTER SCAN [FACT.front_matter_scan]: title/author may not be on page 1 (cover sheets/blank leaves/scanned covers precede it) — scan up to PAGE_SCAN_CAP=6 leading pages, LOCK onto the FIRST strong page (page_signal>=2: DOI, gate-passing title, or mined author); FALLBACK renders+OCRs page-by-page and STOPS at the first strong page. COST: 300 dpi; OCR is slow (~5-30 s/page) — run `sfi_ocr` in a `background: true` cell for a large scanned corpus; CACHE skips any file with an existing `index/_ocr/<stem>.txt`. MINE the strong page (priority): DOI (retry l/1 O/0 ,/. on 404); year; journal running-head; TITLE = multi-line block (skip headers, keep ALL-CAPS wrap lines, stop at author/affiliation/journal); AUTHOR = first author's family name. GATE: REJECT an OCR title if len<8 OR non-alpha>0.15; ACCEPT a CrossRef SEARCH hit IFF fuzzy title >=0.85 AND |year_delta|<=1 AND (no mined author OR the family name appears among the hit's authors); FAIL => blank + note. Stamp every OCR row note `ocr:`. Outcomes: DOI => LOOKUP => medium `ocr+crossref`; gated title+author(+year) search => medium `ocr:title+author+year`; else keep mined title+author UNVALIDATED, low, `ocr: image-only; mined title/author, UNVALIDATED`.
OCR-tool install is a USER gate: if neither tool is present, `sfi_ocr` prints the install line and exits. In Science: `manage_packages(mode="install", environment="sci-index", packages=["tesseract"])` (or ocrmypdf) — ASK first.

## PROC.6 CrossRef (exact lookup + GATED search)
DOI IS ONE VALIDATION PATH, NOT A PREREQUISITE [FACT.doi_not_required]: pre-DOI + grey lit often have NO DOI, yet title+author(+year) is a sufficient key. `sfi_resolve` (text) AND `sfi_ocr` (scanned) BOTH try DOI-lookup ELSE a gated title+author search (labels `search:title+author+year` etc.). CONTENT-VALIDATION GATE — a resolved identity must match the FILE, not a paper it CITES [FACT.doi_content_gate] (defect #42): before trusting a title-only search hit, the merged `cmd_resolve` reads the file's OWN page-1/2 text (OCR text for scans) and requires the hit's author to appear there (`_author_in_text`); a mined author is used as a search gate only if it is plausible AND present in that text (`_plausible_author`). Two traps this catches: (1) a DOI/author MINED from body text is often a CITED reference (a method DOI in an SI reference list, a `10.2307/...` in a discussion) — it resolves fine but describes a different paper; (2) a title-SEARCH returns a same-author/same-year NEAR-miss (sim can be 1.0 on a truncated query). On gate-fail: leave DOI blank + low confidence, never write the guess. NEVER hardcode a disambiguating term (a place name, a keyword) into the search query — it biases toward one wrong record. BODY-TEXT MINING [FACT.body_mine]: a text PDF whose embedded Title/Author is blank OR junk (PII string/bare DOI/filename — is_junk_title drops them) gets title+author mined from the strong page's body text, feeding the DOI-free search; skipped on scanned pages (=> `sfi_ocr`).
LOOKUP `https://api.crossref.org/works/{doi}` => `.message`. SEARCH `...works?query.bibliographic={title+author+year}&rows=3` => gate the top hits (incl. author-verification). UA `sci-file-indexer/1.0 (mailto:<addr>)`; sleep 0.3 s; timeout 12 s. PARSE first_author=`author[0].family`; year=first of published-print|published-online|issued|created; title=`title[0]`; journal=`container-title[0]`; type via map. OUTPUT to `_sfi_review.tsv`, then `sfi_apply`. (`api.crossref.org` is on the Science allowlist.)

## PROC.7 supplements => parent; duplicates => flag (never remove)
`sfi_build` links a supplement/dataset to its parent by shared DOI stem; a supplement inherits the parent's citation fields when blank. Two non-supplement rows with the same DOI => `duplicate_of` on each (flag only). NEVER remove/overwrite a file — flag; derived artifacts => sidecars.

## PROC.8 overrides (8-col TAB, last-wins) => rebuild
`file_name<TAB>author<TAB>year<TAB>title<TAB>journal<TAB>record_type<TAB>parent<TAB>note`; `#` header; short rows padded; LAST-WINS. All curation enters at ONE point: `sfi_apply` (from the review file) or a hand-added row. NEVER edit raw.csv or index.csv (the index is a build product). Then `sfi_build` again.

## PROC.9 report
`sfi_build` prints rows written; CONFIDENCE table; DELTA (+N new, M changed) vs prior index (idempotence check); supplements linked; duplicates flagged; RESIDUAL-UNRESOLVED = each low file :: WHY :: fix. Never dump the whole table.

## PROC.9b self-check guard (index<->filename<->DOI integrity) + dual-author schema
`sfi_build` also emits a **SELF-CHECK** line: `selfcheck_identity(rows)` surfaces rows
where the index disagrees with the filename or carries a corrupt field, so a wrong-paper /
journal-as-title / mojibake / placeholder-author row cannot pass silently. HIGH =
identity-level disagreement (author!=filename, title=journal, mojibake, digit-in-author,
placeholder author); MED = title!=filename (token-subset overlap < 0.4) — a title field
holding a journal masthead, a reference citation, body text, or an SI figure/table caption
instead of the paper title. CHEAP index+filename pass (no PDF read, no CrossRef); verify
each HIGH against printed PDF content before overriding.

**Trust order when resolving a flag: printed PDF content > original filename > CrossRef/DOI.**
A wrong/truncated DOI can point CrossRef at a *different* paper, so DOI metadata is
corroboration, never the arbiter.

**Dual author columns:** `first_author` = canonical display form, diacritics PRESERVED
(Araújo, Vårhammar); `first_author_ascii` = ASCII-folded (Araujo, Varhammar), unicode
punctuation normalized. Use `first_author_ascii` for ALL matching/joining/dedup so an
accent never false-positives. `fold_ascii()` is the shared folder.

**Known SI metadata trap:** a supplement PDF's embedded `/Author` is often the SI preparer
or template designer (e.g. `/Author='Lennon, Sarah'`, `/Title='New Phytologist SI template'`),
NOT the paper's lead author. For `record_type=supplement`, prefer identity from the parent
article (or the SI page's printed "Article title:"/"Authors:" line) over embedded metadata.

## PROC.10 rename (canonical, ledgered, reversible) — the ONLY subcommand that writes to disk
`sfi_rename` is a downstream CONSUMER of `paper_index.csv`: reads the finished index, computes a canonical filename per row from a customizable template, and renames the real files. NEVER re-extracts, NEVER fabricates — a row it cannot name from real fields is SKIPPED, not force-named. NEEDS a rw-granted folder (`request_host_access(..., mode="rw")`); dry-run alone only reads.
- RAIL (mirrors resolve/ocr): `sfi_rename(folder)` = DRY-RUN => writes `index/_sfi_rename_plan.tsv` (`original<TAB>proposed<TAB>status<TAB>reason`), moves nothing; review it, then `sfi_rename(folder, apply=True)`. `sfi_rename(folder, undo=True)` reverses the last apply batch.
- LEDGER: `index/_sfi_renames.tsv` (`batch<TAB>ts<TAB>original<TAB>canonical`) — every applied rename recorded; `undo` reverses the last batch + pops it. This makes renaming reversible + auditable.
- CONFIG: `index/_sfi_rename.json`, auto-written with defaults on first run, then a hand-edit surface. Keys: `template` (default `{author}_{year}_{journal_abbrev}_{type}_{pages}`), `separator`, `case`, `missing_field` (drop|placeholder)+`placeholder`, `confidence_floor` (default `medium`; n/a always excluded), `rename_datasets` (false), `collision` (suffix `-2`,…), `max_stem_len`, `journal_abbrev` (full-name=>abbrev MAP you extend; unmapped => deterministic 4-letter-per-significant-word fallback, never fabricated). `config=` points elsewhere.
- TOKENS: `{author}` `{year}` `{journal}`/`{journal_abbrev}` `{type}` `{pages}`(=>`16p`) `{title_slug}` `{doi_slug}`; joined by `separator`; an EMPTY token drops out (no stray separators) unless `missing_field=placeholder`. Extension preserved; non-ASCII NFKD-folded.
- APPLY keeps the index coherent: rewrites the `file_name` key in `_sfi_overrides.tsv` (curation follows) + `paper_index.csv`, moves `_ocr/<stem>.{pdf,txt}` sidecars (no re-OCR), REFUSES to clobber an existing target (=> `-N` suffix). Re-run `sfi_extract`+`sfi_build` after to refresh derived fields.
- INCREMENTAL: a file already at its canonical name is skipped; a re-run = 0 to rename. Only new/renamable files appear later — never re-processes.
- ORDER: run rename LAST (after the index is as resolved as it gets). Confidence floor guards against baking weak metadata into names — do NOT lower it to `low` to force unresolved files (that would fabricate a name); resolve the row first, then rename.

## PROC.11 validate completeness (STANDING ALARM — run after every build/apply)
`sfi_validate_completeness(index_csv, write_report=True)` (kernel.py) alarms on ANY row whose core
identity — **AUTHOR, YEAR, or PUBLICATION** — is unknown, however the gap arose (bad extraction, a
manual edit, a partial run). A corpus-wide INVARIANT check, not a tripwire on one code path — run it
as the last step of every session that touches the index. Two tiers keep it from crying wolf
[FACT.completeness_alarm] (defect #43):
- **CRITICAL** — barely identified: a garbage title (copyright line, a `Journal, vol(year)` citation
  line captured as title, a mid-sentence fragment, empty/`<8` chars), OR >=2 core fields missing.
  Extraction failures — re-resolve (deeper pages / OCR / gated CrossRef) before trusting.
- **WARN** — identity intact, exactly ONE recoverable core field missing (usually publication).
- **Deliberately NOT flagged** (valid values a naive check false-positives): ALL-CAPS source names
  (`BALDOCCHI`), 2-char CJK surnames (`Wu`, `Xu`), and `name: subtitle` software titles carrying a DOI
  (`tealeaves: ...`). Flagging these IS the crying-wolf failure — don't.
Writes `index/_METADATA_ALARM.csv` (CRITICAL first, each row led by its full citation). Batch-recoverable
clusters hide here (11 copyright-line files were all *Tree Physiology*). Returns
`{total, ok, warn, critical, report, rows}`.

## PROC.12 identity-consistency audit (catches the borrowed-DOI / cited-ref-identity class)
`sfi_audit_identity(index_csv, crossref_fetch=None, write_report=True)` (kernel.py) flags rows whose
fields are all PRESENT but mutually INCONSISTENT — the signature PROC.11 (missing-field) and the
title-token audit both miss. The motivating case (defect #42 / Condit-1996): a row had the CORRECT
title yet wrong author + year + journal + DOI, because the DOI was borrowed from a sibling paper the
file merely cites. Two tiers:
- **HARD** — a within-row contradiction that is almost always real: the filename's leading
  `Author_YYYY` token disagrees with the recorded author/year (the Dolph/Galloway cited-ref signature,
  after ASCII-folding so `Aragao`==`Aragão` is NOT flagged); or, when a `crossref_fetch(doi)->dict|None`
  callback is supplied, the recorded author-surname/year is absent from the DOI's OWN CrossRef metadata.
- **SOFT** — a shape smell (a bare common-given-name author on a non-CJK row); reported, never changed.
Pure-stdlib for the HARD-offline + SOFT tiers (always runnable); pass a CrossRef fetcher for the
definitive network cross-check. Writes `index/_IDENTITY_AUDIT.csv` (HARD first, each row led by its full
citation). NEVER mutates the index — reports only; the agent/human verifies and fixes. Lesson learned
the hard way (defect #42 close-out): do NOT try to mine a year from the DOI STRING — DOIs embed ISSNs
and article numbers (Elsevier `0168-1923(91)...` reads as 1923, not the true 1991), so that heuristic
false-positives on nearly every Elsevier row. The DOI string is an identifier, not a year source.

## Confidence tiers
Derived by a SINGLE SOURCE OF TRUTH — `derive_confidence(row)` in `scripts/sci_file_index.py`, mirrored byte-for-logic by `mc_derive_confidence(row)` in `kernel.py` (so the QA re-derivation can never drift from the stored column). It fuses A-side identity tiers with B-side note-awareness:
- **high** = author + title present (+ year, and usually publication) AND the note is ABSENT or a trustworthy resolution marker (`crossref:`, `search:`, `cryptic`, `si of`, `si/dataset`, `filename-stem`, `review-verdict:`, `jstor-cover:`, `verified from`, `doi-truncated-dropped`).
- **medium** = author + title present but the year is missing, OR a note signals genuine uncertainty (`guess`, `unverified`, `approx`, `ambiguous`, `no-doi`, `gate-fail`, `check`, `uncertain`), OR any other non-empty note that is not a recognized trustworthy marker (an unknown note is treated as mild uncertainty and caps the row at medium).
- **low** = missing author OR missing title, OR an OCR/mined-but-UNVALIDATED note (`ocr: image-only`, `UNVALIDATED`) — mined-from-the-scan is never treated as verified, however many columns are filled.
- **very low** = neither author NOR title recoverable.
- **n/a** = dataset / non-paper.

A NOTE never fabricates confidence: an externally-validated resolution (CrossRef lookup, gated title search, cryptic-DOI derivation) is trustworthy; a bare mined field is not.

## NEVER-fabricate rule
A blank field + a note is ALWAYS correct over a plausible-but-unverified value. A near-miss CrossRef hit is a DIFFERENT paper. Blank beats wrong. Every derived value is stamped for a later better-tooled pass.

## Hard-won gotchas
image-only scan => OCR, no tool => low + note (never guess) · an honest-limit `low` is EARNED per-file only after vision-OCR escalation (defect #29/#39): text present but title looks like a citation/journal string AND expected title tokens absent => render + `host.view_image` BEFORE flagging (a display-font title can be absent from an otherwise-text-rich page) · OCR noise => title+search gates, retry OCR'd DOI with l/1 O/0 ,/. · publisher-code => derive; Elsevier PII != DOI => use captured DOI · exclude the docx twin, `~$*` locks, archives · data csv => dataset/n-a · `978-*` blank author => medium is CORRECT · hand-edit to index.csv vanishes => edit overrides ONLY · never remove a "duplicate" => flag · long OCR/CrossRef batch => run `sfi_ocr`/`sfi_resolve` in a `background: true` cell · `sfi_rename` is the ONE sanctioned original-file modification — safe because dry-run-gated + ledgered + `undo`; never lower `confidence_floor` to `low` to force-name unresolved rows (that fabricates a name).

## Title-source traps (page-1 is not always the title page)
When the `title` field disagrees with the filename/author, the first extracted page is often
NOT the article's title page. Before flagging low or accepting a wrong title, check these — each
is a real defect this corpus produced:
- **Reference-list / back-matter first.** A page opening with numbered citations ("34 McIntyre, S.
  ...") or a `REFERENCES` header is back-matter; the title page may be absent from the PDF
  entirely (a partial scan). Look for the article's OWN citation footer — publisher PDFs (Science,
  many Wiley) print a `Title / Author / Journal vol(issue), pages / DOI:` block on the LAST page;
  that DOI is the paper's own, not a cited ref. (Kasting 1993: title recovered from the Science
  footer on the last page after page 1 was references.)
- **Title line dropped by pdftotext.** A masthead page can extract journal+authors+abstract but
  SKIP the title (font/encoding). Do not accept the masthead as the title. Resolve by EXACT
  citation lookup: `query.bibliographic` filtered to the printed volume+issue+page range returns
  one hit. (Wilson & Lindow 1994: title absent from text; recovered by AEM vol60(7):2232 match.)
- **ILL / document-delivery cover as page 1.** A first page of OCR garbage with `ILL Number:`,
  `Call #:`, `Rapid #:`, `LENDER:`/`BORROWER:` is an interlibrary-loan cover; the real content
  starts on page 2+. Mine identity from page 2 onward (often a book-chapter `In: <book>, Editor:
  ..., pp. X-Y, ISBN` block => `record_type=book_chapter`). (Ogilvie 2010.)
- **DOI/author+year is corroboration, not the arbiter.** A tempting same-author-same-year
  CrossRef hit can be a DIFFERENT paper — verify the returned title against the file's own
  reference profile / abstract before applying, and if nothing matches, flag rather than force
  (a wrong-topic Oikos hit for "Fraser 1997" was rejected before the file was correctly identified).
- **Display-font title absent from the text layer (escalate to VISION-OCR).** The most dangerous
  trap: a large stylised/display-font TITLE heading can be rendered as vector art or an image and
  never enter the text layer, while the body text + references extract perfectly. So the page is
  NOT scanned (`pdftotext` returns plenty of text) yet the title is unrecoverable by text tools,
  and the miner grabs a references-block citation instead. The "does this page have text?" check
  PASSES and hides the problem. **Rule:** if the mined title reads like a citation/reference or
  journal string AND the author/title tokens you expect are NOT found in the page's text, do not
  declare an honest-limit — render the page and read it with vision-OCR (`host.view_image` /
  `_vision_ocr`, per defect #29). This is not just for image-only scans; it applies to
  text-bearing PDFs whose *title* is the only non-text element. (Fraser & Keddy 1997, TREE
  12(12):478 — title "The role of experimental microcosms in ecological research" was a display
  heading absent from the text layer; the filename had mined a reference citation; vision-OCR of
  the rendered page recovered it, CrossRef-confirmed.)

## Orphan-SI title sourcing (supplement whose parent is absent from the library)
A supplement whose `title` is a bare figure/table caption ("Table S1...", "Figure S8...") needs
its PARENT article title. In priority order: (1) the SI's own printed header often states it —
"Supporting Information for <TITLE>", "Supplementary text and tables for '<TITLE>'"; (2) else
CrossRef by author+year+topic and verify; (3) a standalone data table with no parent in the
library and no confident match stays flagged (never fabricate a parent). Inheriting the parent
title frequently also corrects a wrong SI year (Xu 2004=>2019, Gerlein-Safdi 2004=>2018 — the
"2004" came from the encyclopedia-template metadata, not the paper).

## Success check
Every file => a row OR an intentional exclusion; all DOI-derivable weak rows resolved; scanned files OCR'd or flagged low WITH a reason; supplements linked; duplicates flagged (NONE removed); confidence honest; re-run on an unchanged folder => NO diff (idempotent). If `sfi_rename` was run: dry-run plan reviewed before apply=True; only rows at/above the confidence floor renamed; ledger + undo=True make it reversible; a re-run = 0 to rename.


## UPDATE 2026-07-21 — classification hardening (defect #59, FM1/FM2/FM4/FM5)
Durable indexer fixes, all deterministic (no agent judgment at runtime):
- **record_type is CONTENT-gated on the true page-1 head, not the mining page.** The front-matter scanner picks the page that best yields a title to MINE; a separate `page1_head = clean(pages[0])[:200]` is now captured for CLASSIFICATION. An SI that OPENS with a banner ("Supplemental Information for…", "Supplementary methods…") → `record_type=supplement`; an article that merely APPENDS its SI (opens with its own title) STAYS `article`. This closed the dominant mislabel class where an SI's mineable title made it look like an article.
- **New `record_type=peer_review`** for reviewer-comments / decision-letter / editorial-note / rebuttal / author-response files. Detected by `_PEERREVIEW_BANNERS` on page-1 head (+ filename `peer[-_ ]?review`), gated BEFORE the SI override. These repeat the article's title but are distinct documents — typing them peer_review keeps the curator from treating them as duplicate articles.
- **Closed record_type vocabulary (11):** article, supplement, dataset, peer_review, book, book_chapter, preprint, thesis, report, conference, manual. Validator I14 enforces membership.
- **`pages` column** (from pdfinfo) is now threaded to the master and catalog (append-only; existing columns unmoved). It powers the curator's truncation detection (a short copy coexisting with a fuller same-work copy).
- **`content_sim` column** — a stamp-robust 64-bit SimHash over the boilerplate-stripped, digit-dropped page-1 head. Lets the curator catch near-duplicate copies that differ only by a download stamp/watermark, which raw text-cosine misses.
Design boundary preserved: the indexer keeps its OWN template stem builder; only `_asciify`/`_family_name` are shared from `sci_lib_common`. Post-fix indexer sha16 49d04d7297bbba8e.

