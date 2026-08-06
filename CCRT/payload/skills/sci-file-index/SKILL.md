---
name: sci-file-index
description: Build/update a catalog of a scientific-literature folder (books, chapters, theses, articles, supplements, datasets) -- extract per-file metadata, RESOLVE cryptic publisher-code filenames (stem=>DOI) and scanned/image-only PDFs (OCR => DOI, or gated CrossRef title-search), keep a last-wins override layer, link supplements to parents, flag duplicates, tier confidence, and NEVER fabricate. Use when indexing or cataloging a folder of PDFs/papers, resolving cryptic or scanned documents, building a paper_index, or curating bibliographic metadata at scale.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-19). Validated on macOS py3.9.6.

# sci-file-index -- catalog a literature folder; resolve cryptic names + scanned PDFs; never fabricate

BUNDLED_TOOL: `sci_file_index.py` (this dir). Pure python3 stdlib + poppler CLI (pdfinfo|pdftotext|pdffonts|pdftoppm); OCR optional (ocrmypdf | tesseract). Portable macOS+Linux. 6 subcommands = the pipeline (5 read-only cataloging + `rename`, the one that WRITES to disk); run them, do NOT re-derive the logic by hand.
INVOKE: `python3 <skill_dir>/sci_file_index.py <extract|build|resolve|ocr|apply|rename> --dir <FOLDER> [--index P] [--overrides P] [--mailto ADDR] [--config P] [--apply] [--undo]`.
NEVER-FABRICATE is the prime directive: a blank field + a WHY note beats a plausible guess. Every derived row is auditable (note prefix) + re-runnable.

## When to invoke
- User asks to index / catalog / inventory a folder of papers, PDFs, books, theses, or supplements into a metadata table.
- User has cryptic publisher-code filenames (e.g. `BF00385604.pdf`, `s00442-....pdf`, `annurev-....pdf`) or old scanned/image-only PDFs to identify.
- User wants to build/update a `paper_index.csv`, resolve weak rows via DOI/CrossRef, link supplements to parents, or flag duplicates.
- RECURRING use: user re-indexes a growing library => the tool is idempotent + incremental (re-run = update, not rebuild-from-zero).
- OUT of scope (redirect): reading/summarizing/analyzing paper CONTENT, figure extraction, literature review. This is file-level METADATA cataloging ONLY.

## Pipeline (3 artifacts: raw <= extract | overrides <= curation | index <= merge)
ALL index outputs live in `<dir>/index/` [FACT.index_subdir] — the articles folder stays clean; the scan EXCLUDES `index/` so it never catalogs its own output. Paths below are relative to `<dir>/index/`. (`--index`/`--overrides` still override.) To relocate ALL outputs together (e.g. a read-only articles folder, or collecting outputs under a parent), set env `SFI_INDEX_DIR=<absolute path>` [FACT.index_env] — it overrides `<dir>/index/` for every subcommand.
- `_sfi_raw.csv`      <= `extract`: one row/file; per-file metadata (pages, chars_page1, n_fonts, embedded/body-mined title+author, producer, DOI, title_src_page, snippet). Blanks allowed + expected. NEVER hand-edit. (`extract` also writes `_sfi_progress.txt` = `done/total current_file`, readable mid-run to watch a large-corpus scan.)
- `_sfi_overrides.tsv` <= curation: the ONLY hand-edit surface. 8 TAB cols, `#` header, LAST-WINS. Fed by `apply` (from the review file) or by hand.
- `paper_index.csv`   <= `build`: the PRODUCT (merge of raw + overrides). Hand-edits here are CLOBBERED on rebuild -- edit overrides instead.
- `_sfi_review.tsv`   <= `resolve`/`ocr`: staging surface for CrossRef/OCR results BEFORE they enter overrides (audit against mis-hits). `apply` promotes it.
COMMANDS in order: `extract` -> `build` -> (`resolve` and/or `ocr`) -> review `_sfi_review.tsv` -> `apply` -> `build` again. Re-run on an unchanged folder => NO diff.

## PROC.1 scan + classify (exclusions)
`extract` walks `--dir` (non-recursive; one folder). EXCLUDES [FACT.exclusions]: dotfiles; `_*` (own artifacts); `~$*` (Word lock/temp; G_lock); the `index/` output subfolder + the index file itself; a `*.docx` whose same-stem `.pdf` also exists (G_twin -- the exported twin); archives `*.zip|.tar|.gz|.7z|.rar` (G_zip -- publisher bundles; unzip into the dir first if you want their contents). A data `.csv`/`.xlsx` IS indexed but as record_type=dataset, confidence=n/a (G_csv -- it is DATA, not literature).

## PROC.2 extract (pdfinfo / XMP / pdftotext / filename-parse)
Per PDF, `extract` records: `pdfinfo` Pages + embedded Title/Author + Producer/Creator; `pdffonts` embedded-font count (n_fonts; feeds the scanned test); page-1 non-space char count (chars_page1); DOI via regex `10\.\d{4,9}/[-._;()/:A-Za-z0-9]+` on page-1/2 text (strip trailing `.,;)]}>`), else the XMP/Subject/Title/Keywords metadata. FILENAME-PARSE (HIGHEST yield when present): ` - `-delimited `Journal - Year - Author - Title.pdf` (Wiley/OUP export convention) => author+year+title DIRECTLY => confidence=high, NO network needed.

## PROC.3 triage decision-tree (ORDERED else-if; earlier branch wins)
1. file_name already in overrides.tsv => SKIP (idempotence).
2. author AND year AND title present => OK; confidence=high; STOP. (A resolved file NEVER reaches the scanned test.)
3. ELSE IF chars_page1 < 100 OR n_fonts == 0 (no text layer at all) => scanned_row => PROC.5 (OCR). [FACT.scanned_threshold]
4. ELSE IF author OR year missing => weak_row: DOI captured => PROC.6 LOOKUP; else stem matches a doi_pattern => PROC.4 derive => LOOKUP; else a title-ish page-1 line => PROC.6 SEARCH (gated); else unresolved: blank + confidence=low + note=WHY.
`build` applies steps 1/2/4 (offline derivation + filename-parse); `resolve` does the network LOOKUP/SEARCH for weak rows; `ocr` does step 3. The scanned test in `ocr` is gated on step-2: candidates are files STILL weak in the current index AND passing the scanned test AND not curated.

## PROC.4 cryptic filename => DOI (pattern table; pure derivation, no network)
Applied by `build`/`resolve` to the filename stem [FACT.doi_patterns]:
- `^BF\d+`               => `10.1007/<stem>`   (Springer legacy)
- `^A_\d+`               => `10.1023/A:<digits>` (Kluwer legacy)
- `^s\d{4,5}-`           => `10.1007/<stem>`   (Springer)
- `^978-`                => `10.1007/<stem>`   (Springer book/chapter; often NO single author => medium is CORRECT, G_book)
- `^annurev`             => `10.1146/<stem>`   (Annual Reviews)
- `^(bg|gmd|acp|hess|essd)-` => `10.5194/<stem>` (Copernicus/EGU)
- Elsevier `1-s2.0-S<PII>-main` => PII != DOI => NO derivation; PREFER the page-1/XMP-captured DOI (G_pii). If absent, take journal+year ONLY; leave author/title BLANK.
- PNAS `pnas.<id>si` | `pnas.<id>.sd0N` => NOT a standalone article => supplement|dataset of `10.1073/pnas.<id>` => PROC.7.
The derived DOI is a CANDIDATE => confirm at CrossRef (PROC.6); never treat a derived DOI as fact without the lookup.

## PROC.5 scanned => OCR (detect | ocrmypdf or pdftoppm+tesseract | mine page-1 | quality gates | sidecars | cost control)
DETECT (any 1 => scanned): page-1 non-space chars < 100; OR `pdffonts` lists no fonts (no text layer at all).
NEVER modify the user's original [G_never_delete]. OCR output => SIDECAR `<dir>/index/_ocr/<stem>.pdf` (+ `<stem>.txt`).
- PREFERRED: `ocrmypdf --skip-text --rotate-pages --deskew --language eng --output-type pdf <in> <index/_ocr/stem.pdf>` (adds a text layer to a COPY), then pdftotext the sidecar.
- FALLBACK (no ocrmypdf; needs only tesseract+poppler): render one page at a time `pdftoppm -r 300 -png -f N -l N <in> <index/_ocr/stem>` => `tesseract <png> stdout --psm 1 -l eng`.
FRONT-MATTER FORWARD-SCAN [FACT.front_matter_scan]: title/author may NOT be on page 1 (cover sheets, blank leaves, scanned cover images precede the real title page). Scan up to PAGE_SCAN_CAP=6 leading pages, LOCK onto the FIRST page with a strong title/author signal (page_signal>=2: a DOI, a gate-passing title, a mined author); cover/blank pages score ~0 and are skipped. FALLBACK path renders+OCRs one page at a time and STOPS at the first strong page (skips paying to OCR front-matter).
COST CONTROL: 300 dpi suffices (600 = slower, no gain); OCR is SLOW (~5-30 s/page) => the tool runs it, but for a large scanned corpus run the `ocr` subcommand in BACKGROUND to a log + poll [G_harness_stall]; CACHE => any file with an existing `index/_ocr/<stem>.txt` is skipped.
MINE the strong page's text, PRIORITY order: (1) DOI regex -- on a CrossRef 404 RETRY with char-confusion substitutions l/1 O/0 ,/. [G_ocrdoi]; (2) year `\b(19|20)\d{2}\b`; (3) journal running-head; (4) TITLE = multi-line block: skip headers/running-heads, assemble contiguous title lines (ALL-CAPS wrap lines kept), stop at author/affiliation/journal line; (5) AUTHOR = first author's family name from the first author-like line below the title.
QUALITY GATE [FACT.ocr_title_gate / FACT.crossref_search_gate]: REJECT an OCR title if len<8 OR non-alpha ratio>0.15; ACCEPT a CrossRef SEARCH hit IFF fuzzy title similarity >=0.85 (difflib on lowercased alnum) AND (no OCR year OR |year_hit - year_ocr|<=1) AND (no mined author OR the mined family name appears among the hit's authors — "if you get them right"); FAIL => do NOT write the hit, leave BLANK + note. STAMP every OCR-derived row note with prefix `ocr:` (auditable + re-runnable with better tooling later). Outcomes: DOI found => LOOKUP => medium note=`ocr+crossref`; gated title+author(+year) search hit => medium note=`ocr:title+author+year` (or `ocr:title+author`/`ocr:title-only`); else keep mined title+author UNVALIDATED, confidence=low, note=`ocr: image-only; mined title/author, UNVALIDATED`.
INSTALL is a USER-INPUT gate: OCR tools are not always present. ASK before installing -- `brew install ocrmypdf tesseract` (macOS; pulls tesseract+ghostscript) | `apt-get install ocrmypdf tesseract-ocr` (Linux). The `ocr` subcommand prints the exact install line + exits if neither tool is found.

## PROC.6 CrossRef (exact lookup + GATED bibliographic search)
DOI IS ONE VALIDATION PATH, NOT A PREREQUISITE [FACT.doi_not_required]. Pre-DOI papers and grey literature often have NO DOI anywhere, yet title+author(+year) is a SUFFICIENT bibliographic key. So `resolve` (text PDFs) AND `ocr` (scanned) BOTH try: (1) DOI lookup if a DOI is derivable, ELSE (2) a gated title+author search on the row's title+author (embedded metadata OR body-text-mined — see FACT.body_mine). A row with no DOI is NOT given up on while it has a gate-passing title.
Done by `resolve`/`ocr` [FACT.crossref]. LOOKUP (have a DOI): GET `https://api.crossref.org/works/{quote(doi)}` => `.message`. SEARCH (no DOI): GET `https://api.crossref.org/works?query.bibliographic={quote(title+" "+author+" "+year)}&rows=3` => `.message.items[]` => apply the search gate (incl. author-verification); take the first PASS, else none. Gate labels: `search:title+author+year` / `search:title+author` / `search:title-only`.
BODY-TEXT MINING [FACT.body_mine]: a text-layer PDF whose embedded Title/Author is blank OR JUNK (a PII string, bare DOI, filename — publisher exports stuff these into the Title field; is_junk_title drops them) gets title+author mined from the strong page's BODY text, so the DOI-free search fires. Skipped on scanned pages (those go to `ocr`). HEADERS: `User-Agent: sci-file-indexer/1.0 (mailto:<user-addr>)` (polite pool -- pass `--mailto`); SLEEP 0.3 s; TIMEOUT 12 s. PARSE: first_author=`author[0].family` (else `.name`); year = first present of `published-print|published-online|issued|created` `.date-parts[0][0]`; title=`title[0]`; journal=`container-title[0]`; record_type via FACT.type_map (journal-article=>article | book-chapter=>book_chapter | book|monograph=>book | proceedings-article=>conference | posted-content=>preprint | report=>report | dissertation=>thesis | else article). OUTPUT to `_sfi_review.tsv` (NOT straight into overrides -- the review file is the audit surface), then `apply`.

## PROC.7 supplements => parent; duplicates => flag (never remove)
`build` links a supplement/dataset to its parent by shared DOI stem (PNAS id, or DOI substring) when parent not explicitly set, and a supplement inherits the parent's citation fields when blank. DUPLICATE detection: two non-supplement rows with the same DOI => set `duplicate_of` on each (flag only). NEVER remove or overwrite a user's file [G_never_delete] -- flag `duplicate_of`; all derived artifacts go to sidecars (`_ocr/`).

## PROC.8 overrides (8-col TAB, last-wins) => rebuild
The override layer [FACT.override_schema]: `file_name<TAB>author<TAB>year<TAB>title<TAB>journal<TAB>record_type<TAB>parent<TAB>note`; `#` comment header; short rows padded; LAST-WINS. ALL curation enters at ONE point: `apply` appends reviewed `_sfi_review.tsv` rows to overrides (dedup by file_name), OR hand-add a row. NEVER edit raw.csv or index.csv [G_clobber -- the index is a build product]. Then `build` again to fold overrides into the index.

## PROC.9 report
`build` prints: rows written; CONFIDENCE table (high/medium/low/n-a); DELTA (+N new, M changed) vs the prior index (idempotence check -- a clean re-run = +0/0); supplements linked; duplicates flagged; RESIDUAL-UNRESOLVED list = each low-confidence file :: WHY :: what would fix it. Never dump the whole table -- the delta summary is the report.

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
`rename` is a downstream CONSUMER of `paper_index.csv`: it reads the finished index, computes a canonical filename per row from a customizable template, and renames the real files. It NEVER re-extracts and NEVER fabricates — a row it cannot name from real fields is skipped, not force-named.
- SAFETY RAIL (mirrors resolve/ocr): `rename --dir F` = DRY-RUN => writes the plan to `index/_sfi_rename_plan.tsv` (`original<TAB>proposed<TAB>status<TAB>reason`) and prints it; NOTHING moves. Review it, then `rename --dir F --apply` executes. `rename --dir F --undo` reverses the most recent apply batch from the ledger.
- LEDGER [FACT.rename_ledger]: every applied rename is recorded in `index/_sfi_renames.tsv` (`batch<TAB>ts<TAB>original<TAB>canonical`). `--undo` reverses the last batch (canonical=>original) and pops it from the ledger. This is what makes renaming reversible + auditable (the traceability the never-delete rule otherwise gives via flags).
- CONFIG [FACT.rename_cfg]: `index/_sfi_rename.json`, auto-written with defaults on first run, then a hand-edit surface (like overrides). Keys: `template` (default `{author}_{year}_{journal_abbrev}_{type}_{pages}`), `separator`, `case` (none|lower|upper), `missing_field` (drop|placeholder) + `placeholder`, `confidence_floor` (default `medium`: high>medium>low; n/a always excluded), `rename_datasets` (default false), `collision` (suffix `-2`,`-3`,…), `max_stem_len`, and `journal_abbrev` (a full-name=>abbrev MAP you extend; unmapped journals get a deterministic stopword-dropped 4-letter-per-word fallback, never fabricated). `--config P` points elsewhere; the CLI has no per-token flags — edit the JSON.
- TOKENS: `{author}` (first-author surname), `{year}`, `{journal}` / `{journal_abbrev}`, `{type}` (article|book|chapter|thesis|supplement|dataset|preprint|report), `{pages}` (=>`16p`), `{title_slug}` (CamelCase, stopwords dropped, ≤8 words), `{doi_slug}`. Template = these joined by `separator`; a token that resolves EMPTY is dropped (no stray separators) unless `missing_field=placeholder`. Original extension always preserved (lower-cased). Non-ASCII folded to ASCII (NFKD).
- APPLY keeps the whole index coherent: on each rename it rewrites the `file_name` key in `_sfi_overrides.tsv` (curation follows the file), rewrites the key in `paper_index.csv`, and moves the `_ocr/<stem>.{pdf,txt}` sidecars (OCR cache follows — no re-OCR). It REFUSES to overwrite a pre-existing unrelated target (collision => deterministic `-N` suffix instead). Re-run `extract`+`build` afterward to refresh derived fields against the new names.
- INCREMENTAL [G_rename_idempotent]: a file already AT its canonical name is skipped; a re-run on an already-renamed folder = 0 to rename (the "NO diff" invariant holds for rename too). Only genuinely new/renamable files appear in a later plan — never re-processes.
- ORDER: run rename LAST, after the index is as resolved as it will get (`extract`->`build`->resolve/ocr->apply->`build`->**`rename` (dry-run, review, --apply)**). Renaming first would bake weak/low metadata into names.

## Confidence tiers [FACT.confidence]
Derived by a SINGLE SOURCE OF TRUTH — `derive_confidence(row)` in `sci_file_index.py`, used by both `build` (to stamp the column) and any QA re-derivation, so the stored column can never drift from the data fields. It fuses identity tiers with note-awareness:
- **high** = author + title present (+ year, and usually publication) AND the note is ABSENT or a trustworthy resolution marker (`crossref:`, `search:`, `cryptic`, `si of`, `si/dataset`, `filename-stem`, `review-verdict:`, `jstor-cover:`, `verified from`, `doi-truncated-dropped`).
- **medium** = author + title present but the year is missing, OR a note signals genuine uncertainty (`guess`, `unverified`, `approx`, `ambiguous`, `no-doi`, `gate-fail`, `check`, `uncertain`), OR any other non-empty note that is not a recognized trustworthy marker (an unknown note is treated as mild uncertainty and caps the row at medium).
- **low** = missing author OR missing title, OR an OCR/mined-but-UNVALIDATED note (`ocr: image-only`, `UNVALIDATED`) — mined-from-the-scan is never treated as verified, however many columns are filled.
- **very low** = neither author NOR title recoverable.
- **n/a** = dataset / non-paper.

A NOTE never fabricates confidence: an externally-validated resolution (CrossRef lookup, gated title search, cryptic-DOI derivation) is trustworthy; a bare mined field is not.

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
  declare an honest-limit — RENDER the page to an image (`pdftoppm -r 200 -png -f N -l N`) and
  READ it visually before flagging (per defect #29). This is not just for image-only scans; it applies to
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

## NEVER-fabricate rule
A blank field + a note is ALWAYS correct over a plausible-but-unverified value. A near-miss CrossRef hit is a DIFFERENT paper (that is what the gate + review file guard). Blank beats wrong. Every derived value is stamped so a later, better-tooled pass can improve it.

## Hard-won gotchas
- G_scan: pdftotext ~empty => image-only scan => OCR; no OCR tool => confidence=low + note; do NOT guess.
- G_ocrjunk/G_ocrdoi: OCR noise => the title + search gates; retry an OCR'd DOI with l/1 O/0 ,/. substitutions before declaring unresolved.
- G_cryptic/G_pii: publisher-code filename => PROC.4 derive; Elsevier PII is NOT a DOI => use the captured DOI.
- G_twin/G_lock/G_zip: exclude the `.docx` twin, `~$*` locks, and archives.
- G_csv: a data csv => dataset/n-a, not a paper.
- G_book: a `978-*` row with blank author => edited volume => medium is CORRECT.
- G_clobber: a hand-edit to index.csv vanishes => edit overrides.tsv ONLY.
- G_never_delete: never remove a "duplicate" => flag `duplicate_of`; derived files => sidecars. The ONE sanctioned modification of an original is `rename` (PROC.10) — and it stays safe by being dry-run-gated, ledgered, and reversible (`--undo`); it renames, never deletes, and refuses to clobber an existing file.
- G_rename_floor: `rename` obeys the confidence floor — do NOT lower `confidence_floor` to `low` to force-name unresolved files; a low row has no verified author/title, so the name would be fabricated. Resolve the row first (override/resolve/ocr), then rename.
- G_harness_stall: a long extract/OCR/CrossRef batch can hang the harness => background heavy/network work to a log, then poll; the tool persists to disk as it goes.

## Success check
Every file => a row OR an intentional exclusion; all DOI-derivable weak rows resolved; scanned files OCR'd or flagged low WITH a reason; supplements linked to parents; duplicates flagged (NONE removed); confidence honest; re-run on an unchanged folder produces NO diff (idempotent). If `rename` was run: a dry-run plan was reviewed before `--apply`; only rows at/above the confidence floor were renamed; the ledger + `--undo` make it reversible; a re-run of `rename` = 0 to rename.

## UPDATE 2026-07-21 — classification hardening (defect #59, FM1/FM2/FM4/FM5)
Durable indexer fixes, all deterministic (no agent judgment at runtime):
- **record_type is CONTENT-gated on the true page-1 head, not the mining page.** The front-matter scanner picks the page that best yields a title to MINE; a separate `page1_head = clean(pages[0])[:200]` is now captured for CLASSIFICATION. An SI that OPENS with a banner ("Supplemental Information for…", "Supplementary methods…") → `record_type=supplement`; an article that merely APPENDS its SI (opens with its own title) STAYS `article`. This closed the dominant mislabel class where an SI's mineable title made it look like an article.
- **New `record_type=peer_review`** for reviewer-comments / decision-letter / editorial-note / rebuttal / author-response files. Detected by `_PEERREVIEW_BANNERS` on page-1 head (+ filename `peer[-_ ]?review`), gated BEFORE the SI override. These repeat the article's title but are distinct documents — typing them peer_review keeps the curator from treating them as duplicate articles.
- **Closed record_type vocabulary (11):** article, supplement, dataset, peer_review, book, book_chapter, preprint, thesis, report, conference, manual. Validator I14 enforces membership.
- **`pages` column** (from pdfinfo) is now threaded to the master and catalog (append-only; existing columns unmoved). It powers the curator's truncation detection (a short copy coexisting with a fuller same-work copy).
- **`content_sim` column** — a stamp-robust 64-bit SimHash over the boilerplate-stripped, digit-dropped page-1 head. Lets the curator catch near-duplicate copies that differ only by a download stamp/watermark, which raw text-cosine misses.
Design boundary preserved: the indexer keeps its OWN template stem builder; only `_asciify`/`_family_name` are shared from `sci_lib_common`. Post-fix indexer sha16 49d04d7297bbba8e.

## UPDATE 2026-07-24 — I17/I18 flag emission (parity with Claude Science sibling)
Two deterministic `notes`-column stamps ported from the Claude Science indexer so the curator's new I17/I18 invariants have their explicit signals (without them, every cryptic name would fail I17 for lack of an escape flag):
- **`si-doi-disagrees-parent`** — in the supplement→parent field-inheritance loop, BEFORE inheriting blanks: if a linked supplement carries its own stored DOI that disagrees with its parent's (supplement-suffix-normalized), the note is stamped instead of silently overwriting during inheritance. Feeds curator **I18**.
- **`cryptic_unresolved`** — after confidence derivation: a non-supplement/dataset row left with a blank/Unknown first_author (its canonical clean_name cannot be built, so it would ship as a raw publisher/DOI code) is stamped so curator **I17** has its explicit escape flag rather than the cryptic name shipping silently. Feeds curator **I17**.
These match the Science indexer's emission by logic (parallel implementation, not a byte-copy).
