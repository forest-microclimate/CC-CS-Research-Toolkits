---
name: sci-library-curate
description: Dedup, migrate-copy, and topic-organize a scientific-literature library from a sci-file-index paper_index.csv -- cluster the index so an article and its supplement are never treated as duplicates, flag only TRUE same-paper copies and keep the cleanest version, flag wrong-DOI phantoms for review instead of merging, copy the keep-set to a clean folder under canonical Author_Year_Journal_Title names (drift-resistant against ongoing Papers.app renames), then classify every file into a Topic/Subtopic folder tree (regex + LLM tail) with a tags column for cross-cutting search. Use AFTER sci-file-index has produced an index, when the goal is deduplicating, migrating/copying to a clean deduped folder, or organizing a paper library by research topic. Library curation only -- NOT metadata extraction (that is sci-file-index) or paper-content reading.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# sci-library-curate — dedup, migrate-copy, and topic-organize a literature library

Companion to **sci-file-index**. That skill builds a confidence-tiered `paper_index.csv`; THIS skill takes that finished index and does the three curation steps on top of it: **(2) dedup → (3) migrate-copy → (4) organize**. It makes the judgment calls that a naive DOI/hash dedup gets wrong, and it is safe-by-default: risky calls are flagged for human review, never auto-deleted.

BUNDLED TOOL: `scripts/sci_library_curate.py` (pure py3 stdlib). Loading this skill runs `kernel.py`, which defines wrappers: `slc_dedup(index, hashes=)`, `slc_migrate(index, decisions, src, dst)`, `slc_organize(index, manifest, dst, ...)`, `slc_bundle(index, papers, dry_run=)` (idempotent in-place article+SI foldering for the incremental add-flow), and `slc_llm_classify(unclassified_json, out_json)` (the only wrapper that needs `host.llm`). Call them in a `python` cell.

## When to invoke
- User asks to **deduplicate** a paper library, find/flag duplicate PDFs, or reconcile duplicate flags from an index.
- User asks to **migrate/copy** papers to a clean folder, rename to a consistent convention, or build a "no-duplicates" library.
- User asks to **organize papers by research topic / subject / theme**, build a nested topic folder tree, or tag a library.
- User asks to **bundle** an article with its supplement(s) into a per-article folder, or reports
  loose supplements sitting at the library root after incremental adds => run `slc_bundle` in place.
- RECURRING use: re-curate a growing library — each step is idempotent and reads the previous step's output.
- OUT of scope (redirect): building the index / extracting metadata / resolving cryptic or scanned PDFs => **sci-file-index**. Reading, summarizing, or reviewing paper CONTENT => literature-review. This skill only reorganizes files an index already describes.

## Prerequisite
A finished `paper_index.csv` from sci-file-index whose filenames are in sync with disk. The Papers.app folder drifts continuously (it appends `_N`, swaps ` - supplement ` for `_supplement_`, etc.), so **re-extract the index immediately before curating** if any time has passed. `slc_migrate` is drift-resistant (it re-resolves each name to disk by exact-then-stem match) but will FATAL rather than guess if a keep-file has drifted beyond a stem match — that is the signal to re-extract.

## Environment
Pure stdlib — the default `python` env works, or reuse the `sci-index` env from sci-file-index. Pass `environment=` consistently and load THIS skill in that env so `kernel.py` binds there. The library folders are host-granted paths: the source (`papers library`) needs only **ro**; the clean destination needs **rw**.

## The three steps

```python
# after loading this skill (env with `host` available for the LLM tail):
IDX  = f"{ROOT}/index/paper_index.csv"
HASH = f"{ROOT}/index/_sfi_filehashes.tsv"   # optional; size for cleanest-version tie-break
SRC  = f"{ROOT}/papers library"
DST  = f"{ROOT}/papers clean no dups"

# STEP 2 — dedup (read-only; writes decision + report artifacts, deletes nothing)
slc_dedup(IDX, hashes=HASH, out=f"{DST}/_dedup_decisions.csv", report=f"{DST}/DEDUP_REPORT.md")
#   -> review _dedup_decisions.csv (KEEP vs drop_as_duplicate) and, if present,
#      _dedup_decisions_PHANTOMS_review.csv (wrong-DOI / ambiguous-SI pairs to verify BY HAND)

# STEP 3 — migrate-copy the keep-set under canonical names; by DEFAULT each article WITH
#          supplement(s) is bundled into its own folder (article + its SIs). Pass no_bundle=True for flat.
slc_migrate(IDX, f"{DST}/_dedup_decisions.csv", SRC, DST, dry_run=True)   # preview names + bundle counts
slc_migrate(IDX, f"{DST}/_dedup_decisions.csv", SRC, DST)                 # copy -> writes _MIGRATION_MANIFEST.csv (bundle_folder col)

# STEP 4 — organize into a Topic/Subtopic tree (two-pass: regex, then LLM for the tail)
slc_organize(IDX, f"{DST}/_MIGRATION_MANIFEST.csv", DST)                  # 1st pass -> _unclassified_for_llm.json, stops
slc_llm_classify(f"{DST}/_unclassified_for_llm.json", f"{DST}/_llm_assignments.json")
slc_organize(IDX, f"{DST}/_MIGRATION_MANIFEST.csv", DST,
             llm_assignments=f"{DST}/_llm_assignments.json")              # 2nd pass -> moves files, writes _LIBRARY_INDEX.csv

# BUNDLE (idempotent, in-place) — fold each article + its LOOSE supplement(s) into a per-article
# folder on the LIVE library + master WITHOUT a re-migration. This is the maintenance counterpart to
# migrate's bundling: the incremental add-flow copies article+SI FLAT (bundle_folder="") and never
# bundles, so loose supplements accumulate at the papers root; run slc_bundle after EVERY add to fix
# that in place. Folder = article clean_name minus extension (matches migrate). Idempotent: 2nd run
# = 0 moves. Solo articles + true orphan supplements stay flat; a supplement already in a DIFFERENT
# folder (pre-existing split) is reported, never auto-shuffled. PAPERS = the flat clean papers root.
slc_bundle(PAPERS_MASTER, PAPERS, dry_run=True, report=f"{DST}/_BUNDLE_PLAN.csv")   # preview the move plan
slc_bundle(PAPERS_MASTER, PAPERS)                                                    # move + update bundle_folder in place

# VALIDATE (the vaccine) — run after ANY mutating stage (build, dedup, migrate, a manual edit).
# r.returncode == 0 means all structural invariants pass; 1 means a FAIL was printed. With lib= it
# also checks disk<->index 1:1 and folder==article-stem. Catches drift (year-first names, duplicate
# clean_name, first_author_ascii out of sync, missing author/year/title) at the source.
slc_validate(IDX)                                                        # index-only invariants
slc_validate(IDX, lib=DST, report=f"{DST}/VALIDATE_REPORT.md")           # + disk checks + report

# CATALOG — regenerate the one-row-per-WORK clean lookup table (the reader-facing deliverable).
# The master/index above is one row per FILE; this collapses supplements + datasets + book sections
# onto their parent work, so each article/book is a SINGLE line with its clean_path and its supplements
# listed inline (n_supplements, component_paths, supplement_desc). It also carries date_time_added,
# DERIVED from each work's primary master row (the master is the source of truth for the add-date;
# the catalog never stamps it at regen time). It is a MATERIALIZED VIEW of the master: regenerate after
# ANY build/dedup/migrate/manual edit; NEVER hand-edit it. With lib= it re-runs the disk 1:1
# reconciliation and returns returncode 1 if the catalog would drift from disk (0 = clean).
slc_catalog(IDX, out=f"{ROOT}/_index_clean_lookup_table.csv", lib=DST)

# AUTHORS — populate the co-author list columns on the master (article-grain rows).
# Adds three columns to the master (appended after date_time_added; existing schema preserved):
#   authors    — the ordered co-author list as "Family, G.I." strings, "; "-joined and BOUNDED:
#                <=7 authors show ALL; >=8 show the first 4 + "[+K more]" + the last 3 (7 names max).
#   n_authors  — the TRUE integer count, ALWAYS the real number even when `authors` is abbreviated.
#   last_author— the final (senior/PI) author's "Family, G.I."; blank when n_authors==0.
# Source: a DOI-keyed _AUTHOR_LIST_CACHE.csv (columns: doi, ordered_authors PIPE-delimited & FULL
# (not abbreviated), n_authors, source). The full list lives in the cache; the bounded display is
# re-rendered here, so a 500-author paper can never breach the schema. Rows with no cache hit get a
# GATED CrossRef title-search fallback (crossref=True + mailto) — a hit is accepted ONLY if its title
# matches the row's title (fuzzy>=0.85 OR containment>=0.90) AND the first-author surname checks out
# (unless the title match is near-exact); otherwise authors are left BLANK and dedup_note gains
# "authors-unresolved". NEVER fabricates. Supplements/datasets get BLANK author columns (they carry
# parent_file, inherit nothing). first_author is NEVER touched.
slc_populate_authors(IDX, cache=f"{ROOT}/_AUTHOR_LIST_CACHE.csv", dry_run=True)          # cache-only preview
slc_populate_authors(IDX, cache=f"{ROOT}/_AUTHOR_LIST_CACHE.csv")                         # cache-only write
slc_populate_authors(IDX, cache=f"{ROOT}/_AUTHOR_LIST_CACHE.csv", crossref=True, mailto=EMAIL)  # + gated fallback
```

## The dedup model (why a naive dedup is wrong)
The single most important idea: **most "duplicate" flags are not duplicates.** In a Papers.app library:
- An **article and its supplement** share a DOI. They are NOT copies — keep both. A paper with 20 distinct SIs is 21 files to keep, not 20 duplicates.
- Papers.app **re-encodes** every copy, so byte-identical duplicates are essentially ZERO. Dedup is metadata clustering + a "which version is cleanest" pick, never an md5 match.
- Papers.app sometimes assigns a **wrong or truncated DOI**, which then merges two genuinely different papers into one cluster (a "phantom").

So the tool:
1. Clusters by **real DOI** (suffix must contain a digit — guards truncated DOIs) else by `author|year|title[:40]`.
2. Splits each cluster into MAIN vs SUPPLEMENT **by filename marker** (`_supplement_1`, `- supplement`, `SI 2`, `figS3`, …) OR record_type — because Papers frequently mistypes an SI as `article`. Only same-marker SI files are dedup candidates; distinct SIs (suppl1 vs suppl2) are always kept.
3. Flags, rather than drops, anything ambiguous: MAIN files whose titles disagree (<0.80 sim) or whose filename surnames disagree; SI pairs whose sizes differ >3× or whose surnames disagree. These go to `*_PHANTOMS_review.csv`.
4. For a TRUE duplicate cluster, KEEPs the **cleanest** file by: least-cryptic filename (a clean `Author_Year_Journal_Title` beats `watermark-silverchair…`, `…ezproxy…`, `NNN.full`, hex-UUID, `Untitled Article`) → highest confidence → largest size. An article + its corrigendum/erratum are BOTH kept.

Rule of thumb from the reference corpus: a raw flag count of ~450 collapsed to ~29 true clusters. If your dedup keeps hundreds of clusters, the SI-vs-article split is probably misfiring — check that supplement filenames carry a recognizable marker.

## In-bundle duplicate detection (content-based — the ONE case filename markers miss)
A file can wear an SI marker (`_suppl1`, `- supplement`) or even a `-dup` tag yet actually BE a copy of
the main article — a duplicate hiding in the supplement slot. The filename/record_type split in the
dedup model above cannot catch this (it trusts the marker). The robust discriminator is **content page
coverage**, and it has a ZERO-false-positive guarantee on genuine SI because of how the two populations
separate:

**Principle (empirically verified on the reference corpus):**
- A genuine supplement's pages (figures, tables, methods, appendices) NEVER match the article's body
  pages. Even a coversheet copy (JSTOR/ILL) or an accepted-vs-final version has matching *body* pages.
- So: for every pair of members in a bundle, compute per-page text similarity (SequenceMatcher on
  ASCII-folded page text) and the **page coverage** = fraction of the shorter file's pages that have a
  >=0.90 match in the other. Two files are the SAME DOCUMENT iff coverage >= a threshold in the gap.
- Measured distribution (525 bundles): genuine SIs had page-coverage-vs-article of **mean 0.003,
  median 0.000, max 0.833 for a coversheet-copy that was itself a dup**; TRUE in-bundle duplicates sat
  at **0.667-1.0**. After removing the coversheet dups, kept-SI coverage max was **0.000**. Set the
  threshold at **0.55** (dead center of the empty [0.05, 0.66) gap). Nothing genuine lives there.

**Procedure:**
1. Extract per-page normalized text (`pdftotext` split on form-feed; ASCII-fold + collapse whitespace).
   Flag members with <~150 chars/page as SCANNED (handle separately, step 4).
2. For each bundle, cluster non-scanned members: two are the same document iff
   `max(cov(a in b), cov(b in a)) >= 0.55`. A fast word-set Jaccard pre-screen (<0.5 => skip the
   expensive difflib) makes genuine-different SI pages drop out instantly.
3. KEEP one per cluster (prefer NOT `-dup`-named, NOT coversheet, `record_type==article`, most pages,
   largest size); the rest are duplicates. NEVER drop a bundle's only article-class file; a keeper
   must never itself be in the drop set (assert both).
4. SCANNED members: same page-coverage logic but on **perceptual image hashes** (`pdftoppm` at ~100 dpi
   => `imagehash.phash`; pages match at hamming <= 8). This catches a scanned photocopy of the article
   sitting under an `_suppl` name (e.g. an old JAppMet paper). Visually confirm the matched page before
   dropping when sizes differ a lot.

**Hard safety rules (this is REALLY important — never false-positive a genuine SI):**
- The decision is CONTENT ONLY. Never infer "duplicate" from shared DOI/author/year/title — an SI
  legitimately shares all four with its article.
- A high page-coverage is the ONLY trigger. If coverage is below the gap, KEEP (it is genuine SI or a
  different paper), even if filenames look similar.
- Different-paper misfiles (two unrelated papers in one bundle, e.g. a stray SI from another study) show
  LOW coverage => correctly kept; flag them for re-bundling, do not drop.
- Move drops to `stale_trash/`, never hard-delete; write a `_DUPLICATE_IN_BUNDLE_review.csv` with
  keep/drop names + coverage + method so every call is auditable.

## Bundle hygiene after dedup (collapse singletons)
Removing an in-bundle duplicate can leave a bundle folder holding a SINGLE file — a folder that no
longer earns its existence (the whole point of a bundle folder is to group an article WITH its
supplement(s)). After any dedup pass, collapse them:
- A folder with exactly ONE document file (no subfolders) => move that file back to the flat library
  root and move the now-empty folder to `stale_trash/` (never hard-delete). Clear the file's
  `bundle_folder` in the index.
- This also catches PRE-EXISTING single-file "bundles" (an orphan SI that was foldered alone) — those
  are equally pointless as folders; flatten them too. Distinguish the two origins in your report
  (dedup-caused vs pre-existing) but treat both the same.
- Safety: a dedup that is working correctly NEVER orphans an article-class file, so every
  dedup-caused singleton should be the article keeper; assert this (if a dedup-caused singleton is a
  bare supplement, the dedup dropped the wrong file — stop and investigate).

## The migrate model
- Canonical name = `Author_Year_JournalAbbrev_TitleSlug.pdf` (CamelCase, stopwords dropped, ≤180 chars), with a `_supplN` / `_figSN` marker appended for supplements and a `-2/-3` suffix only when two files would otherwise collide. Names come from the index; never fabricated (a nameless file falls back to a cleaned original stem).
- **Article+supplement bundling (DEFAULT ON).** An article that has accompanying supplement(s) is exported into its OWN folder — named after the article's canonical stem — holding the article PDF plus all its supplements. Articles with no SI, and orphan supplements whose parent article is absent, export flat at the root. Each article+SI set is therefore one atomic unit, so a later topic-organize moves the whole folder together and an SI never ends up in a different topic than its article. Pass `no_bundle=True` (`--no-bundle`) to export everything flat.
  - Supplements are linked to their article by **two merged signals with a surname guard**: (1) the index `parent_file` field — PRIMARY, because it links a supplement to its article regardless of DOI, catching the ~10% of SIs that a shared-DOI cluster would miss: those with no DOI, and the few that carry their OWN DOI (a Dryad/Zenodo/FLUXNET data-repo DOI, or a versioned bioRxiv DOI) that would otherwise split them from the paper; (2) a shared DOI / author|year|title cluster with a single main article — FALLBACK. A link is rejected when both filenames have a parseable surname and they disagree (guards wrong-parent links), and a whole group is dropped when its anchor has a cryptic name (e.g. `Unknown_2004`) AND its SIs carry ≥2 distinct real authors (a stem-collision false merge, not a real article+SI set).
- **Drift resistance:** every keep-file is matched to a real disk file by exact name, then by `stem_key` (trailing `_N` + extension stripped). A single unambiguous stem match wins; anything unresolved is FATAL (re-extract, don't guess).
- Copies (`copy2`, size-verified), never moves — the source is Papers-synced and must stay intact.
- The manifest carries a `bundle_folder` column (empty = flat) recording each file's bundle. Deliverable `_ARTICLE_SI_BUNDLES.csv` is optional context you can derive from it.

## The bundle model (in-place maintenance — why migrate's bundling is not enough)
`migrate` bundles article+SI only during a full source->dst copy. The **incremental add-flow** (adding
a few new papers to an already-migrated clean library) copies each article and its supplement(s) FLAT
to the papers root with `bundle_folder=""` and never folders them — so over many add batches, loose
supplements pile up at the library root next to their article. `slc_bundle` (subcommand `bundle`) is
the fix: it bundles **in place** on the live library + master, no re-migration.
- **Pairing** reuses `link_supplements` (the exact engine migrate uses): `parent_file` PRIMARY, a
  shared-DOI / author|year|title cluster as FALLBACK, with a surname guard rejecting wrong-parent
  links and a cryptic-anchor guard dropping stem-collision false merges.
- **Folder name = the article's EXISTING `clean_name` minus its extension** — NOT a fresh
  `canonical_stem()`. The canonical scheme has evolved across defects, so re-deriving would rename
  ~72% of already-bundled folders and break both idempotency and validate invariant I6. The folder is
  always single-level; `clean_name` stays a basename; the folder lives only in the `bundle_folder`
  column.
- **Idempotent + safe-by-default.** Only currently-LOOSE members (`bundle_folder=""`) are moved. A
  member already in its target folder is a no-op (a second run performs **0 moves**). A supplement
  already foldered in a *different* folder is a PRE-EXISTING split (article renamed after bundling, or
  article+SI split across two folders) — it is **reported for review, never auto-shuffled** (that
  belongs to a separate re-bundle pass, and moving it would empty its source folder). A both-places
  copy is reported, never clobbered. A folder-name collision with a different work gets a
  deterministic `-2/-3` suffix (like migrate).
- **Stays flat:** solo articles (no SI), true orphan supplements (no resolvable parent), and loose
  supplements whose `parent_file` points at a supplement-typed row (a broken/chained pointer that
  `link_supplements` correctly refuses as an anchor) — all reported, all left flat.
- **Wiring (so the defect cannot recur):** call `slc_bundle` at the END of every incremental add
  flow, after the new files are copied flat to `PAPERS` and their rows appended to the master. It is
  the article+SI counterpart of running `slc_validate` after every mutating stage.
- Deliverable `_BUNDLE_PLAN.csv` (`--report`) lists every planned action (move / relabel / review)
  with from/to folders — the orchestrator previews it via `dry_run=True` before the live run.

## The organize model
- **Taxonomy** = `{Topic: {Subtopic: regex}}`. The built-in default (in `scripts/sci_library_curate.py`, `default_taxonomy()`) is plant-ecophysiology + microbial-ecology; **edit it, or pass a `--taxonomy` JSON, to match a different research domain.** The user's own framing should drive the top categories and subtopics.
- **Two-pass classification:** high-precision regex on `title + journal` handles the clear ~60%; the rest go to `host.llm` in batches (`slc_llm_classify`). Supplements then inherit their parent article's topic. Files that still fall through land in an "Other / general ecology" catch-all.
- **Folder + tags, not folder alone:** each file moves into ONE primary `Topic/Subtopic/` folder (its top keyword hit), but `_LIBRARY_INDEX.csv` carries a `tags` column listing ALL matching themes, so a multi-topic paper filed under one folder is still findable under the others.
- **Off-domain flagging:** genuinely unrelated papers (mis-synced into the library) are better flagged in the library index than force-filed — surface them for the user's delete decision rather than burying them in a topic.

## Deliverables (written into the clean folder)
- `_dedup_decisions.csv` — every clustered file marked KEEP or drop_as_duplicate, with cluster id + reason.
- `_dedup_decisions_PHANTOMS_review.csv` — (if any) risky calls to verify by hand; NONE are auto-dropped.
- `DEDUP_REPORT.md` — the headline counts + method + why the raw flag count collapsed.
- `_MIGRATION_MANIFEST.csv` — clean_name ← original_disk_name ← index_name, full provenance per file.
- `_LIBRARY_INDEX.csv` — the master catalog: topic, subtopic, tags, tree_path, and bibliographic fields for every file.

## Guardrails
- Deletes NOTHING. Dedup writes a decision file; migrate COPIES; organize MOVES only within the clean destination. The source library is never touched.
- Never merges an ambiguous cluster or drops a distinct supplement — it flags for review. Dropping unique content is worse than keeping a redundant copy.
- Never fabricates a name or a topic. Missing metadata → cleaned-original-stem fallback; unclassifiable → catch-all, not a guess.


## UPDATE 2026-07-21 — dedup safety hardening (defect #59, FM3/FM5/FM6/FM7/FM8 + validators)
Durable curator fixes, all deterministic; the governing rule is unchanged and now enforced structurally: **NEVER auto-drop a distinct item; when a rule cannot decide, it FLAGs.**
- **record_type consumption is now explicit.** `NON_MAIN = {supplement, dataset, peer_review}`; `_is_main(m) = record_type not in NON_MAIN and not supp_marker(file_name)`; only mains are dedup targets. A file mistyped at ingestion can no longer become a phantom "second main" and get its twin dropped. `peer_review` files are excluded from mains (kept, not deduped).
- **Companion-work guard `_distinct_works` (FM3).** Two mains sharing a title-only blocking key are treated as DISTINCT WORKS — never merged — iff (≥2 conflicting Part-N tokens) OR (≥2 distinct real DOIs AND non-identical normalized titles). The title conjunction is load-bearing: a same-title pair whose fuller copy carries a mis-mined citation DOI is still ONE work (drops correctly); a Part-1/Part-2 companion pair with distinct DOIs and different titles is two works (FLAG, never merged). Part-N regex is boundary-anchored (`\bpart[\s.\-]+([ivx]+|\d+)\b`) so "partitioning"/"particle" never trigger.
- **Truncation flag (FM4).** A main is a truncation candidate ONLY when a fuller same-blocking-key MAIN twin exists (pages gap ≥ DPG_MIN=3, short contained). Default outcome = FLAG (`_TRUNCATION_review.csv`); `--aggressive-truncation` opts into DROP-the-shorter / KEEP-the-fuller. A small page count with NO fuller twin (errata, corrigenda, one-page letters) is NEVER flagged.
- **Content near-dup signal (FM5).** `content_sim` SimHash thresholded at Hamming ≤ K (default 3), consulted ONLY after the distinct-work/author/truncation guards clear — so it can never override a distinct-works FLAG. (Conservative by design; K≥5 would over-merge a keep-both, so K=3 is the over-merge-safe floor.)
- **Master-schema compatibility (FM7).** `_read_index` aliases `clean_name→file_name` once at read, so dedup/migrate/validate run directly on the master (which keys on clean_name) — no schema drift.
- **Retired the ad-hoc agent similarity metric (FM6).** The near-dup signal lives in `content_sim`, the SI signal in `record_type`; nothing is scored in agent code at runtime.
- **New validator invariants:** I12 (pages blank or non-neg int), I13 (truncation-flag completeness — every truncated-vs-fuller main pair has a recorded KEEP/drop/FLAG), I14 (record_type in the closed 11-type vocabulary), I15 (companion no-merge — distinct-DOI/Part-N works never inside one dup_article decision). I1–I11 unchanged. Optional `validate --decisions <file>` cross-checks I13/I15 against a dedup decision file.
Independently audited (fresh reviewer, 19/19 routing, 5/5 adversarial, 0 over-merge on the live 5,125-row master; baseline dropped 11 files, 9 wrongly → fixed code drops 2, both true near-dups). `sci_lib_common` UNCHANGED (primitives only). Post-fix curator sha16 32692b6e61bf217b.

## UPDATE 2026-07-24 — validator false-green closed (defect #61): I16–I19
The shipped `cmd_validate` enforced only I1–I15, none of which caught orphan supplements, cryptic publisher-code names, or cross-paper mislinks — so it reported `0 FAIL` on a library holding 289 broken files. Four deterministic FAIL invariants close that blind spot (I1–I15 unchanged):
- **I16** — every supplement/dataset resolves to a MAIN parent (not another supplement) OR carries the literal note token `orphan_parent_absent` (a genuine orphan is kept-and-flagged, never dropped). WARN face: a linked SI not co-located in its parent's `bundle_folder`.
- **I17** — no article, and no *unlinked/unflagged* supplement, may keep a cryptic clean_name (leading publisher/DOI code, `_MOESM`, `-sup-`, bare non-Author_Year stem) without the token `cryptic_unresolved`. A LINKED supplement is exempt (its identity comes from its parent; the cryptic filename is normalized at bundling).
- **I18** — a linked SI's DOI must agree with its parent's. `--lib` mode reads the SI PDF's **masthead zone only** (DOIs before the first references/bibliography marker, capped 600 chars) so cited-reference DOIs don't false-fire; a data-repository DOI on either side is exempt (Dryad/Zenodo/figshare landing DOIs legitimately differ from the parent journal DOI). Index-only mode falls back to stored-DOI comparison.
- **I19** — an article row must have a non-blank title (a fragment/graphical-abstract stem with no title is not a real identity).
Also in this ship: a `link_supplements` content-DOI gate (reject a DOI-cluster link when both sides carry disagreeing non-repo DOIs); the indexer gained a DOI-broadcast guard (never overwrite an SI's own mined DOI during citation inheritance; stamp `si-doi-disagrees-parent`) and a `cryptic_unresolved` FLAG on identity-unresolved rows; and defect #60's `_LIT_EXT` widening (24 exts incl `.r`/`.html`) was re-applied after a login-reseed had reverted it. Independently audited (SHIP): 0 FAIL on the full --lib validate over 5,354 rows, regression suite 7/7. Post-fix curator sha16 9d64d5e9d5e11fa0.
DURABLE-PUBLISH DISCIPLINE: every skill edit MUST end with host.skills.publish(overwrite=True) while logged into the active org — a disk-only edit (or one published under another org) is reverted by the next login's cloud-catalog sync. That reseed is what silently reverted I7–I15 and defect #60 before this fix.
