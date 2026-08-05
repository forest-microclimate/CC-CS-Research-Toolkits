# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""sci-library-curate kernel sidecar — thin wrappers around scripts/sci_library_curate.py.

Companion to sci-file-index: takes a finished paper_index.csv and (1) dedups it, (2) migrate-copies
the keep-set under canonical names to a clean folder, (3) organizes the clean folder into a
Topic/Subtopic tree. Each wrapper shells out to the bundled pure-stdlib tool; slc_llm_classify uses
host.llm to place the regex-unclassified tail before the final organize move.

Call order:
  slc_dedup(index, hashes) -> review _dedup_decisions.csv (+ *_PHANTOMS_review.csv if any)
  slc_migrate(index, decisions, src, dst)                      # copies + canonical names
  slc_organize(index, manifest, dst)                           # 1st pass: writes _unclassified_for_llm.json
  slc_llm_classify(dst + "/_unclassified_for_llm.json", dst + "/_llm_assignments.json")
  slc_organize(index, manifest, dst, llm_assignments=dst + "/_llm_assignments.json")  # 2nd pass: moves files

In-place maintenance (no re-migration): slc_bundle(index, papers) idempotently folds each article +
its loose supplement(s) into a per-article folder and updates bundle_folder in the master; run it
after every incremental add so loose supplements never accumulate at the library root.
"""
import os
import re
import sys
import json
import subprocess


def slc_tool_path():
    """Absolute path to the bundled scripts/sci_library_curate.py (resolved from this sidecar)."""
    here = os.path.dirname(sys._getframe().f_code.co_filename)
    if not here:
        raise RuntimeError("skill dir unavailable in this runtime; run scripts/sci_library_curate.py by path")
    return os.path.join(here, "scripts", "sci_library_curate.py")


def slc_run(cmd, args, quiet=False):
    """Run one sci_library_curate subcommand. args is a list of extra CLI tokens."""
    argv = [sys.executable, slc_tool_path(), cmd] + list(args)
    r = subprocess.run(argv, capture_output=True, text=True)
    if not quiet:
        if r.stdout:
            print(r.stdout, end="")
        if r.returncode != 0 and r.stderr:
            print("STDERR:", r.stderr)
    return r


def slc_dedup(index, hashes=None, out="_dedup_decisions.csv", report="DEDUP_REPORT.md", quiet=False):
    """Step 2: cluster the index, keep article+SI together, flag TRUE duplicates only, pick the
    cleanest version per cluster. Writes `out` (decisions), an article_plus_SI groups CSV, a
    DEDUP report, and — if any risky calls were found — a *_PHANTOMS_review.csv (wrong-DOI /
    ambiguous-supplement pairs to verify by hand). `hashes` is the sci-file-index _sfi_filehashes.tsv
    (optional; supplies size_bytes for the cleanest-version tie-break)."""
    a = ["--index", index, "--out", out, "--report", report]
    if hashes:
        a += ["--hashes", hashes]
    return slc_run("dedup", a, quiet=quiet)


def slc_migrate(index, decisions, src, dst, dry_run=False, no_bundle=False, quiet=False):
    """Step 3: copy the keep-set (all rows except drop_as_duplicate) from `src` to `dst` under
    canonical Author_Year_JournalAbbrev_TitleSlug.pdf names. Drift-resistant: each index name is
    resolved to its real disk file by exact-then-stem match, so an in-progress Papers _N rename
    does not break the copy. FATALs (rather than guesses) if any keep-file can't be resolved on
    disk — re-extract the index first. Writes `dst`/_MIGRATION_MANIFEST.csv.

    BUNDLING (default ON): an article that HAS accompanying supplement(s) is exported into its OWN
    folder (named after the article's canonical stem) holding the article PDF + all its supplements;
    articles with no SI and orphan supplements export flat at the root. Each article+SI set is thus
    one atomic unit (later topic-organize moves the whole folder together). Supplements are linked to
    their article by the index `parent_file` field plus a shared-DOI/author-year cluster, with a
    surname guard that rejects wrong-parent and cryptic-stem false merges. Pass no_bundle=True to
    export every file flat instead. The manifest gains a `bundle_folder` column recording each file's
    bundle (empty = flat)."""
    a = ["--index", index, "--decisions", decisions, "--src", src, "--dst", dst]
    if dry_run:
        a += ["--dry-run"]
    if no_bundle:
        a += ["--no-bundle"]
    return slc_run("migrate", a, quiet=quiet)


def slc_bundle(index, papers, dry_run=False, report=None, quiet=False):
    """BUNDLE (idempotent, in-place): fold each article that has >=1 resolvable supplement into its
    OWN per-article folder, on the LIVE library + master, WITHOUT a full re-migration. Fixes the
    recurring defect where the incremental add-flow copies an article + its supplement(s) FLAT to the
    papers root (bundle_folder="") and never bundles, so loose supplements accumulate at the root.

    For each article with >=1 loose supplement (pairing via the same link_supplements engine migrate
    uses -- parent_file PRIMARY + shared-DOI/author-year fallback, surname/cryptic guards): creates
    `papers`/<article-clean-name-stem>/, MOVES the article + its loose supplements in (atomic), and
    sets bundle_folder on every affected master row (written back to `index` preserving its exact
    columns). Folder name = the article's EXISTING clean_name minus extension (NOT re-derived), so it
    matches migrate's naming and never fights validate invariant I6.

    IDEMPOTENT: a member already in its target folder is a no-op; a second run performs 0 moves.
    SCOPE-SAFE: solo articles (no SI) and true orphan supplements stay FLAT; a supplement already
    foldered in a DIFFERENT folder (a pre-existing split) is REPORTED, never auto-shuffled; a
    both-places copy is reported, never clobbered; a folder-name collision with a different work gets
    a deterministic -2/-3 suffix. Wire this into the incremental add-flow (call after every add) so
    the loose-supplement defect cannot recur.

    dry_run=True prints/writes the full move plan and mutates nothing (the orchestrator uses this to
    preview). report=PATH writes a machine-readable plan CSV (action,clean_name,from_folder,to_folder;
    action in move/relabel/review). Returns the CompletedProcess."""
    a = ["--index", index, "--papers", papers]
    if dry_run:
        a += ["--dry-run"]
    if report:
        a += ["--report", report]
    return slc_run("bundle", a, quiet=quiet)


def slc_validate(index, lib=None, report=None, quiet=False):
    """VALIDATE (the vaccine): run six fail-loud structural invariants over the index and, with
    `lib` (library root), the disk<->index 1:1 and folder==article-stem checks. Returns the
    CompletedProcess: r.returncode == 0 means ALL invariants pass, 1 means at least one FAIL
    (the findings are printed). Run this after ANY mutating stage (build, dedup, migrate, a manual
    edit) to catch drift — year-first names, duplicate clean_name, first_author_ascii out of sync,
    missing author/year/title — at the source instead of shipping it to the user. Invariants:
    I1 unique clean_name, I2 no year-first name, I3 first_author_ascii==asciify(first_author),
    I4 article completeness floor [warn], I5 disk<->index 1:1 [lib], I6 folder==article-stem [lib]."""
    a = ["--index", index]
    if lib:
        a += ["--lib", lib]
    if report:
        a += ["--report", report]
    return slc_run("validate", a, quiet=quiet)


def slc_probe(index, papers=None, out="_IDENTITY_AUDIT.csv", min_score=0.0, quiet=False):
    """PROBE (the proactive identity-error detector): scan the WHOLE master for likely
    MISIDENTIFICATIONS and confirm each candidate against the PDF's own printed byline. Mirrors
    slc_validate — run it proactively after any build/dedup/add, like validate. TWO stages, BOTH
    zero-LLM-token:
      STAGE 1 (pure code over rows): a reason-code battery (FA_STOPWORD, FA_IN_TITLE, FA_IN_JOURNAL,
        FA_HAS_DIGIT, FA_NO_VOWEL, FA_LOWERCASE, FA_SINGLE_INITIAL, FA_TITLE_EQ_JOURNAL,
        RT_SI_MARKER, YEAR_DRIFT_DUP) scores every author-bearing row into error_likelihood [0,1].
        Deliberately HIGH-RECALL: common surnames that are also words (Field, Hall, Sun, Green,
        Long) WILL be flagged. That is expected — Stage 2 clears them.
      STAGE 2 (poppler only, `papers` given): THE ARBITER. Reads each candidate PDF's byline
        (pdftotext -f 1 -l 4 -layout) and tests whether first_author actually appears in the
        front-matter region. THE DOCUMENT IS TRUTH — never calls CrossRef, never trusts a DOI.

    READ-ONLY: writes a ranked `out` (_IDENTITY_AUDIT.csv: clean_name, record_type, first_author,
    year, title, journal, doi, reason_codes, error_likelihood, byline_confirms_first_author,
    needs_ocr, leading_name_hint, needs_human, notes) and NEVER edits the master. Verdicts:
    byline confirms first_author -> LIKELY FALSE POSITIVE (cleared); NOT confirmed with text present
    -> LIKELY REAL ERROR (escalate; leading_name_hint is a HINT, not a verified value); no text
    layer -> needs_ocr (undetermined; the probe never OCRs — that is the adjudication phase's job).

    `papers` omitted -> Stage-1 only (byline columns blank, every candidate needs_human=True).
    `min_score` drops candidates below that error_likelihood (e.g. 0.35 filters the benign-heavy
    pure-RT_SI_MARKER class out of an identity hunt). Returns the CompletedProcess."""
    a = ["--index", index, "--out", out]
    if papers:
        a += ["--papers", papers]
    if min_score:
        a += ["--min-score", str(min_score)]
    if quiet:
        a += ["--quiet"]
    return slc_run("probe", a, quiet=quiet)


def slc_catalog(index, out="_index_clean_lookup_table.csv", lib=None, quiet=False):
    """CATALOG: regenerate the one-row-per-WORK clean lookup table from the master (file-grain) index.
    Collapses supplements/datasets/book-sections onto their parent work so each article/book is a
    single row with its clean_path and its supplements listed inline (component_paths, supplement_desc,
    n_supplements). It is a MATERIALIZED VIEW of the master index — regenerate after ANY build/dedup/
    migrate/manual edit, never hand-edit. With `lib` (library root) it re-runs the disk 1:1
    reconciliation and returns returncode 1 if the catalog would drift from disk (0 = clean).
    Writes `out` (default _index_clean_lookup_table.csv at cwd)."""
    a = ["--index", index, "--out", out]
    if lib:
        a += ["--lib", lib]
    return slc_run("catalog", a, quiet=quiet)


def slc_populate_authors(index, cache=None, mailto=None, crossref=False, dry_run=False, quiet=False,
                         papers=None):
    """AUTHORS: populate authors / n_authors / last_author on the master (file-grain) index.

    For every author-bearing row (record_type in article/book/book_chapter/preprint/manual/thesis/
    report/conference) sets the three columns from the DOI-keyed _AUTHOR_LIST_CACHE.csv (columns:
    doi, ordered_authors PIPE-delimited, n_authors, source) via abbreviate_authors() — the full
    ordered list lives in the cache, the bounded 4+last-3 display is re-rendered here. Rows with no
    cache hit get a GATED CrossRef title-search fallback ONLY when crossref=True AND a mailto is
    given (the hit is accepted only if its title matches the row's title and the first-author
    surname checks out — never fabricates); otherwise authors are left BLANK and dedup_note gains
    'authors-unresolved'. first_author is NEVER touched. Supplements/datasets get blank author
    columns (they carry parent_file). The three columns are APPENDED to the master (existing schema
    preserved). dry_run=True reports stats and mutates nothing. Returns the CompletedProcess.

    CONTENT GATE (defect #59): a DOI cache/CrossRef hit is NOT written blind. When the hit's leading
    author AGREES with the (content-verified) first_author it is populated on the fast path (no PDF
    read). When it DISAGREES and `papers` (the library papers root) is given, the row's PDF byline is
    read and must confirm first_author: confirmed -> populate; contradicted -> authors blanked and the
    borrowed DOI NULLED (so a re-run cannot re-adopt it); scan/no-file -> blanked with a distinct note,
    DOI retained. `papers` omitted -> fast path still works; disagreements degrade to blank+note."""
    a = ["--index", index]
    if cache:
        a += ["--cache", cache]
    if crossref:
        a += ["--crossref"]
        if mailto:
            a += ["--mailto", mailto]
    if papers:
        a += ["--papers", papers]
    if dry_run:
        a += ["--dry-run"]
    return slc_run("authors", a, quiet=quiet)


def slc_organize(index, manifest, dst, taxonomy=None, llm_assignments=None,
                 dry_run=False, force=False, quiet=False):
    """Step 4: classify each file into a Topic/Subtopic taxonomy (regex on title+journal), let
    supplements inherit their parent's topic, then move the clean files into a nested tree and
    write `dst`/_LIBRARY_INDEX.csv. Two-pass by design: the FIRST call (no llm_assignments) writes
    `dst`/_unclassified_for_llm.json for the ~35% the regex misses and STOPS (unless force=True);
    run slc_llm_classify on it, then call again with llm_assignments to place the tail and move
    everything. `taxonomy` is an optional JSON {Topic: {Subtopic: regex}} overriding the built-in
    (edit the default in scripts/sci_library_curate.py for a different research domain)."""
    a = ["--index", index, "--manifest", manifest, "--dst", dst]
    if taxonomy:
        a += ["--taxonomy", taxonomy]
    if llm_assignments:
        a += ["--llm-assignments", llm_assignments]
    if dry_run:
        a += ["--dry-run"]
    if force:
        a += ["--force"]
    return slc_run("organize", a, quiet=quiet)


def slc_llm_classify(unclassified_json, out_json, batch_size=25, model=None, max_concurrency=8):
    """LLM-classify the regex-unclassified tail. Reads the _unclassified_for_llm.json that
    slc_organize wrote ({categories:[...], tasks:[{index_name,title,journal},...]}), batches the
    titles, asks host.llm to assign each to a category by number, and writes {index_name:
    "Topic/Subtopic"} to out_json for the second slc_organize pass. Returns (assigned, total).
    Uses the kernel utility model by default; pass model=host.reasoning_model() for harder corpora."""
    host = globals().get("host")
    if host is None:                       # sidecar module namespace lacks host; find it on the call stack
        fr = sys._getframe()
        while fr is not None:
            cand = fr.f_globals.get("host")
            if cand is not None and hasattr(cand, "llm"):
                host = cand
                break
            fr = fr.f_back
    if host is None or not hasattr(host, "llm"):
        raise RuntimeError("host.llm unavailable in this kernel; run slc_llm_classify in a `python` cell where `host` is injected")
    d = json.load(open(unclassified_json, encoding="utf-8"))
    cats = d["categories"]
    tasks = d["tasks"]
    catlist = "\n".join("%d. %s" % (i, c) for i, c in enumerate(cats))
    batches = [tasks[i:i + batch_size] for i in range(0, len(tasks), batch_size)]

    prompts = []
    for b in batches:
        lines = "\n".join("[%d] %s (%s)" % (j, (t.get("title") or "")[:180], (t.get("journal") or "")[:60])
                          for j, t in enumerate(b))
        prompts.append(
            "You are classifying scientific papers into a fixed research taxonomy.\n"
            "CATEGORIES (reply with the number):\n" + catlist + "\n\n"
            "PAPERS:\n" + lines + "\n\n"
            "For each paper output one line 'paperIndex=categoryNumber' (e.g. '0=3'). "
            "Pick the single best category. If none fit, use the last category (Other). "
            "Output ONLY the assignment lines, nothing else.")

    results = host.llm(prompts, model=model, max_concurrency=max_concurrency) if model \
        else host.llm(prompts, max_concurrency=max_concurrency)

    assign = {}
    for b, res in zip(batches, results):
        txt = res.get("text", "") if isinstance(res, dict) else ""
        txt = re.sub(r"```[a-z]*", "", txt)
        pos = {}
        for m in re.finditer(r"(\d+)\s*=\s*(\d+)", txt):
            pos[int(m.group(1))] = int(m.group(2))
        for j, t in enumerate(b):
            ci = pos.get(j)
            if ci is not None and 0 <= ci < len(cats):
                assign[t["index_name"]] = cats[ci]
    json.dump(assign, open(out_json, "w"))
    return len(assign), len(tasks)


def slc_bundle_dupes(index_csv, root, doc_thr=0.55, pg_thr=0.90, poppler_bin=None, do_scanned=True):
    """Content-based in-bundle duplicate detector (zero false positives on genuine SI).

    Scans every multi-file bundle in an index (needs a 'bundle_folder' column) and returns
    (drops, review) where drops is a list of dicts {bundle,drop,keep,drop_name,keep_name,drop_rt,
    maxcov,method} for files whose PAGE CONTENT is (near-)identical to another bundle member.
    Genuine supplements never match the article body, so they are never flagged. Nothing is moved
    or deleted -- caller decides. See SKILL.md 'In-bundle duplicate detection' for the model.
    """
    import os, re, subprocess, unicodedata, difflib, csv as _csv
    from collections import defaultdict
    import shutil as _sh
    BIN = poppler_bin or (os.path.dirname(_sh.which("pdftotext")) if _sh.which("pdftotext") else "/usr/bin")
    def _pdftotext(p, n=6):
        try: return subprocess.run([os.path.join(BIN,"pdftotext"),"-f","1","-l",str(n),p,"-"],
                                    capture_output=True,text=True,timeout=45).stdout
        except Exception: return ""
    def _pagecount(p):
        try:
            o=subprocess.run([os.path.join(BIN,"pdfinfo"),p],capture_output=True,text=True,timeout=15).stdout
            m=re.search(r"Pages:\s+(\d+)",o); return int(m.group(1)) if m else 0
        except Exception: return 0
    def _norm(t):
        t=unicodedata.normalize("NFKD",str(t)).encode("ascii","ignore").decode().lower()
        return re.sub(r"[^a-z0-9]+"," ",t).strip()
    rows=list(_csv.DictReader(open(index_csv,encoding="utf-8")))
    name2path={}
    for dpp,_,fn in os.walk(root):
        if "stale_trash" in dpp: continue
        for f in fn: name2path[f]=os.path.join(dpp,f)
    bmembers=defaultdict(list)
    for i,r in enumerate(rows):
        if r.get("bundle_folder","").strip(): bmembers[r["bundle_folder"]].append(i)
    multi=[b for b,m in bmembers.items() if len(m)>=2]
    pp={}; pc={}; scanned=set(); meta={}
    for b in multi:
        for i in bmembers[b]:
            if i in pp: continue
            p=name2path.get(rows[i]["clean_name"],""); raw=_pdftotext(p,6)
            npg=[_norm(x) for x in raw.split("\f")]
            pp[i]=[x for x in npg if len(x)>40]; pc[i]=_pagecount(p)
            if sum(len(x) for x in npg) < 150*max(1,min(pc[i],3)): scanned.add(i)
            meta[i]=dict(path=p,rt=rows[i].get("record_type",""),name=rows[i]["clean_name"],
                         size=os.path.getsize(p) if p and os.path.exists(p) else 0,
                         dup_named=bool(re.search(r"-dup\d+",rows[i]["clean_name"])),
                         p1=raw.split("\f")[0] if raw else "")
    pw={i:[frozenset(x.split()) for x in pp[i]] for i in pp}
    def _same(a,b):
        pa,pb=pp.get(a,[]),pp.get(b,[])
        if not pa or not pb: return (False,0,0)
        def cov(fl,tl,wf,wt):
            if not fl: return 0.0
            h=0
            for k2,pf in enumerate(fl):
                best=0.0
                for j,pt in enumerate(tl):
                    if pt and 0.5<=len(pf)/max(1,len(pt))<=2.0:
                        if len(wf[k2]&wt[j])/max(1,len(wf[k2]|wt[j]))<0.5: continue
                        s=difflib.SequenceMatcher(None,pf,pt).ratio()
                        if s>best: best=s
                        if best>=pg_thr: break
                if best>=pg_thr: h+=1
            return h/len(fl)
        ca=cov(pa,pb,pw[a],pw[b]); cb=cov(pb,pa,pw[b],pw[a])
        return (max(ca,cb)>=doc_thr, round(ca,3),round(cb,3))
    def _keepscore(i):
        m=meta[i]; cover=1 if re.search(r"jstor|cover",m["p1"][:200],re.I) else 0
        return (0 if m["dup_named"] else 1,0 if cover else 1,1 if m["rt"]=="article" else 0,pc.get(i,0),m["size"])
    drops=[]
    for b in multi:
        ns=[i for i in bmembers[b] if i not in scanned]; used=set()
        for a in ns:
            if a in used: continue
            grp=[a]
            for c in ns:
                if c==a or c in used: continue
                if _same(a,c)[0]: grp.append(c)
            if len(grp)>1:
                keep=max(grp,key=_keepscore)
                for d in grp:
                    if d==keep: continue
                    _,ca,cb=_same(keep,d)
                    drops.append(dict(bundle=b,drop=d,keep=keep,drop_name=meta[d]["name"],
                        keep_name=meta[keep]["name"],drop_rt=meta[d]["rt"],maxcov=max(ca,cb),method="text_match"))
                    used.add(d)
                used.add(keep)
    review=[{"bundle":b,"scanned_members":[meta[i]["name"] for i in bmembers[b] if i in scanned]}
            for b in multi if any(i in scanned for i in bmembers[b])] if do_scanned else []
    return drops, review