# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""sci-file-index kernel sidecar — thin wrappers around the bundled scripts/sci_file_index.py.

Each wrapper shells out to the bundled tool (pure py3 stdlib + poppler CLI). The tool must find
poppler (pdftotext/pdfinfo/pdffonts/pdftoppm) on PATH — create/activate a conda env that has it
(see SKILL.md ## Environment). OCR additionally needs ocrmypdf or tesseract.
Call order: sfi_extract -> sfi_build -> (sfi_resolve / sfi_ocr) -> review _sfi_review.tsv -> sfi_apply -> sfi_build.
"""
import os
import sys
import subprocess

# (metadata-completeness validator appended at end of file)


def sfi_tool_path():
    """Absolute path to the bundled scripts/sci_file_index.py (resolved from this sidecar's location)."""
    here = os.path.dirname(sys._getframe().f_code.co_filename)
    if not here:
        raise RuntimeError("skill dir unavailable in this runtime; run scripts/sci_file_index.py by path")
    return os.path.join(here, "scripts", "sci_file_index.py")


def sfi_run(cmd, folder, index=None, overrides=None, mailto=None,
            config=None, apply=False, undo=False, quiet=False):
    """Run one sci_file_index subcommand. cmd in {extract, build, resolve, ocr, apply, rename}.

    folder: the literature directory to index (a host-granted path in Science).
    index/overrides: optional explicit paths (default <folder>/paper_index.csv and <folder>/_sfi_overrides.tsv).
    mailto: contact address for the CrossRef polite pool (resolve/ocr) — pass host.get_user_email().
    config/apply/undo: rename-only — config JSON path, execute the plan (else dry-run), reverse last batch.
    Returns the subprocess CompletedProcess; prints stdout unless quiet.
    """
    argv = [sys.executable, sfi_tool_path(), cmd, "--dir", folder]
    if index:
        argv += ["--index", index]
    if overrides:
        argv += ["--overrides", overrides]
    if mailto:
        argv += ["--mailto", mailto]
    if config:
        argv += ["--config", config]
    if apply:
        argv += ["--apply"]
    if undo:
        argv += ["--undo"]
    r = subprocess.run(argv, capture_output=True, text=True)
    if not quiet:
        if r.stdout:
            print(r.stdout, end="")
        if r.returncode != 0 and r.stderr:
            print("STDERR:", r.stderr)
    return r


def sfi_extract(folder, **kw):
    """PROC.1+2: scan/classify the folder, extract per-file metadata -> _sfi_raw.csv."""
    return sfi_run("extract", folder, **kw)


def sfi_build(folder, **kw):
    """PROC.3/4/7/8/9: merge raw + overrides -> paper_index.csv; prints the delta + confidence report."""
    return sfi_run("build", folder, **kw)


def sfi_resolve(folder, **kw):
    """PROC.4/6: weak-row funnel -> CrossRef -> _sfi_review.tsv (REVIEW before apply). Pass mailto=."""
    return sfi_run("resolve", folder, **kw)


def sfi_ocr(folder, **kw):
    """PROC.5: OCR scanned/image-only PDFs to _ocr/ sidecars, mine page-1 -> _sfi_review.tsv. Pass mailto=."""
    return sfi_run("ocr", folder, **kw)


def sfi_apply(folder, **kw):
    """PROC.8: append reviewed _sfi_review.tsv rows into the overrides layer (dedup by file_name)."""
    return sfi_run("apply", folder, **kw)


def sfi_rename(folder, apply=False, undo=False, config=None, **kw):
    """PROC.10: canonically RENAME files from paper_index.csv (ledgered + reversible). The ONE wrapper
    that writes to disk — needs a rw-granted folder.

    Default (apply=False, undo=False) = DRY-RUN: writes index/_sfi_rename_plan.tsv (review it), moves nothing.
    apply=True  = execute the plan (rename on disk; follow override/index keys + _ocr sidecars; append the
                  _sfi_renames.tsv ledger; refuse to clobber an existing target).
    undo=True   = reverse the most recent apply batch from the ledger.
    config=     = explicit rename-config JSON path (default <folder>/index/_sfi_rename.json, auto-written
                  with defaults on first run; edit it to customize template / journal_abbrev map / floor).
    """
    return sfi_run("rename", folder, apply=apply, undo=undo, config=config, **kw)


# ------------------------- metadata-completeness alarm (defect #43) -------------------------
# STANDING CHECK: alarm on ANY file whose AUTHOR, YEAR, or PUBLICATION is unknown — however the
# gap arose (bad extraction, manual edit, partial run). Two tiers so it does not cry wolf:
#   CRITICAL = barely identified (garbage title, or >=2 core fields missing) -> extraction failure
#   WARN     = identity intact, exactly ONE recoverable core field missing (usually publication)
# Valid names that a naive check would false-flag are DELIBERATELY passed: ALL-CAPS source names
# (BALDOCCHI), 2-char CJK surnames (Wu, Xu), "name: subtitle" software titles with a DOI.
import re
import csv

MC_AUTHOR_PLACEHOLDER = {"unknown","anonymous","anon","anon.","author","authors","user","team",
    "editor","editors","admin","guest","na","n/a","n.a.","none","null","tbd","tbc",
    "et al","et al.","fig","figure","table","data","supplement"}

def mc_author_unknown(s):
    s = (s or "").strip()
    if s == "": return True
    if s.lower() in MC_AUTHOR_PLACEHOLDER: return True
    if re.fullmatch(r"[A-Za-z]\.?", s): return True            # single letter "L." = truncated
    return False                                                 # ALL-CAPS + 2-char CJK are VALID

def mc_year_unknown(s):
    return not bool(re.fullmatch(r"(1[6-9]\d\d|20[0-2]\d)", (s or "").strip()))

def mc_pub_unknown(s):
    s = (s or "").strip()
    return (s == "" or s.lower() in MC_AUTHOR_PLACEHOLDER)

def mc_title_hard_garbage(s):
    s = (s or "").strip()
    if s == "" or len(s) < 8: return True
    if s.startswith("\u00a9"): return True                        # copyright-line-as-title
    if re.match(r"^[A-Z][a-z]+.*,\s*\d+\s*\(\s*\d{4}\s*\)", s): return True   # "Journal, vol (year)"
    if re.search(r"publishing.*(canada|victoria)", s, re.I): return True     # Heron/Tree Physiol cover
    return False

def mc_title_soft(s):
    s = (s or "").strip()
    return bool(re.match(r"^[a-z]", s) and ":" not in s[:20])    # lowercase fragment, not "name: subtitle"

def mc_well_identified(row):
    has_doi = bool(re.match(r"10\.\d{4,9}/\S+", (row.get("doi") or "").strip()))
    return has_doi or (not mc_pub_unknown(row.get("journal")))

def sfi_validate_completeness(index_csv, write_report=True, report_path=None):
    """STANDING alarm: flag every row whose AUTHOR / YEAR / PUBLICATION is unknown.

    index_csv: path to the index (paper_index.csv or _MASTER_INDEX.csv). Reads first_author, year,
               journal, title, doi, record_type, clean_name (or file_name).
    Returns dict(total, ok, warn, critical, rows=[...]) where each flagged row carries
    severity + missing_fields + full citation. If write_report, also writes a CRITICAL-first CSV
    next to the index (default <dir>/index/_METADATA_ALARM.csv). No pandas dependency.
    """
    with open(index_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    name_col = "clean_name" if (rows and "clean_name" in rows[0]) else "file_name"
    flagged = []
    ok = 0
    for r in rows:
        uA = mc_author_unknown(r.get("first_author"))
        uY = mc_year_unknown(r.get("year"))
        uP = mc_pub_unknown(r.get("journal"))
        uT = mc_title_hard_garbage(r.get("title")) or (mc_title_soft(r.get("title")) and not mc_well_identified(r))
        ncore = sum([uA, uY, uP])
        if ncore == 0 and not uT:
            ok += 1; continue
        # AUTHOR-unknown is ALWAYS critical: author is the primary identity field, and a stored
        # confidence can never be trusted to have caught it (defect: Unknown_* rows read 'high').
        if uA or uT or ncore >= 2:
            sev = "CRITICAL"
        else:
            sev = "WARN"
        missing = "+".join([f for f, c in [("AUTHOR",uA),("YEAR",uY),("PUBLICATION",uP),("TITLE",uT)] if c])
        flagged.append({"severity": sev, "missing_fields": missing,
                        "first_author": r.get("first_author",""), "year": r.get("year",""),
                        "title": r.get("title",""), "publication": r.get("journal",""),
                        "doi": r.get("doi",""), "record_type": r.get("record_type",""),
                        name_col: r.get(name_col,""), "confidence": r.get("confidence","")})
    flagged.sort(key=lambda x: (x["severity"], x["missing_fields"], x["first_author"].lower()))
    ncrit = sum(1 for x in flagged if x["severity"]=="CRITICAL")
    nwarn = len(flagged) - ncrit
    if write_report and flagged:
        if report_path is None:
            d = os.path.join(os.path.dirname(os.path.abspath(index_csv)), "index")
            os.makedirs(d, exist_ok=True)
            report_path = os.path.join(d, "_METADATA_ALARM.csv")
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(flagged[0].keys())); w.writeheader(); w.writerows(flagged)
    return {"total": len(rows), "ok": ok, "warn": nwarn, "critical": ncrit,
            "report": report_path if (write_report and flagged) else None, "rows": flagged}


# ---------------------------------------------------------------------------
# PROC.12 — identity-consistency audit (defect #42 / Condit-1996 class, shipped)
# ---------------------------------------------------------------------------
# The completeness alarm (PROC.11) catches MISSING fields. This catches a subtler,
# more dangerous failure: fields that are all PRESENT but mutually INCONSISTENT —
# the signature of a DOI/metadata borrowed from a cited or sibling paper. The
# Condit-1996 case had a correct title yet wrong author+year+journal+DOI (the DOI
# was Condit's DIFFERENT 2002 Science paper). A title-token audit misses it because
# the title matched; only a cross-field consistency check flags it.
#
# Two tiers, both pure-stdlib (no network) so they are always runnable:
#   HARD  = a within-row contradiction that is almost always a real error:
#           - DOI encodes a 4-digit year (e.g. .../j.foo.2018... or (91)90002-8=1991)
#             that disagrees with the recorded year by >1, OR
#           - the filename's leading Author_YYYY token disagrees with recorded
#             first_author/year (the Dolph/Galloway cited-ref signature).
#   SOFT  = a shape smell worth a look but often benign (given-name-shaped author
#           on a non-CJK row, etc.). Reported, never auto-changed.
# For the definitive check, the caller passes a `crossref_fetch(doi)->dict|None`
# callback (network); when supplied, a row whose recorded (author-surname, year)
# is absent from the DOI's OWN CrossRef metadata is escalated to HARD. Never
# mutates the index — it only reports; the human/agent verifies and fixes.

MC_GIVEN_NAMES = {"david","john","thomas","james","robert","michael","richard","paul",
                  "peter","mark","daniel","stephen","andrew","william","george","charles"}

def sfi_audit_identity(index_csv, crossref_fetch=None, write_report=True, report_path=None):
    """PROC.12: flag rows whose PRESENT fields are mutually inconsistent (borrowed-DOI /
    cited-ref-identity signature). Pure-stdlib; pass crossref_fetch=lambda doi: {...}|None
    to add the definitive DOI-metadata cross-check. Returns {total, hard, soft, rows} and
    writes index/_IDENTITY_AUDIT.csv (HARD first, each row led by its full citation).
    Never mutates the index."""
    import csv as _csv, os as _os, re as _re
    with open(index_csv, encoding="utf-8") as fh:
        rows = list(_csv.DictReader(fh))
    out = []
    for r in rows:
        au = (r.get("first_author") or "").strip()
        yr = (r.get("year") or "").strip()
        doi = (r.get("doi") or "").strip()
        cn = (r.get("clean_name") or "").strip()
        flags = []
        # (An earlier draft mined a 4-digit "year" from the DOI string; removed — DOIs embed ISSNs,
        #  article numbers and arbitrary digits (e.g. Elsevier "0168-1923(91)..." reads as 1923, not
        #  the true 1991), so it false-positived on nearly every Elsevier row. The filename-token and
        #  network-CrossRef checks below are precise; the DOI string itself is not a year source.)
        # 1) filename Author_YYYY token vs recorded author/year (cited-ref signature)
        m = _re.match(r"^([A-Za-z][A-Za-z'’-]+)_(\d{4})_", cn)
        if m:
            fn_au, fn_yr = m.group(1), m.group(2)
            # ascii-fold + strip non-letters on BOTH sides: the filename token is intentionally the
            # ASCII form of a diacritic surname (dual-author schema), so "Aragao"=="Aragão" is NOT a
            # disagreement. Only a genuinely different surname is flagged (the Galloway/Dolph signature).
            def _fold(s):
                import unicodedata as _u
                return _re.sub(r"[^a-z]", "", _u.normalize("NFKD", s).encode("ascii", "ignore").decode().lower())
            fa_fold, fn_fold = _fold(au), _fold(fn_au)
            if au and fa_fold and fn_fold and fn_fold not in fa_fold and fa_fold not in fn_fold \
               and not fn_au.lower().startswith(("suppl", "figure", "dataset", "table")):
                flags.append(("SOFT", "filename_author=%s != recorded=%s" % (fn_au, au)))
            if yr.isdigit() and fn_yr != yr and abs(int(fn_yr) - int(yr)) > 1:
                flags.append(("HARD", "filename_year=%s != recorded_year=%s" % (fn_yr, yr)))
        # 2) bare given-name-shaped author (non-CJK): soft smell
        if au.lower() in MC_GIVEN_NAMES:
            flags.append(("SOFT", "author '%s' is a common given name — verify it is the surname" % au))
        # 3) definitive: DOI's own CrossRef metadata disagrees with recorded author/year
        if crossref_fetch and doi and au:
            try:
                m2 = crossref_fetch(doi)
            except Exception:
                m2 = None
            if m2:
                fams = " ".join((a.get("family", "") or "") for a in (m2.get("author") or [])).lower()
                dp = (((m2.get("published-print") or m2.get("issued") or {}).get("date-parts") or [[None]])[0])
                cy = dp[0] if dp else None
                surn = _re.sub(r"[^a-z]", "", au.lower())
                if surn and fams and surn not in fams:
                    flags.append(("HARD", "recorded author '%s' absent from DOI's CrossRef authors" % au))
                if cy and yr.isdigit() and abs(int(cy) - int(yr)) > 1:
                    flags.append(("HARD", "DOI CrossRef year=%s != recorded_year=%s" % (cy, yr)))
        if flags:
            sev = "HARD" if any(s == "HARD" for s, _ in flags) else "SOFT"
            cite = "%s (%s) %s [%s]" % (au or "(no author)", yr or "n.d.",
                                        (r.get("title") or "(no title)")[:80], r.get("journal") or "")
            out.append({"severity": sev, "clean_name": cn, "citation": cite,
                        "doi": doi, "reasons": "; ".join("%s:%s" % (s, m) for s, m in flags)})
    out.sort(key=lambda x: (0 if x["severity"] == "HARD" else 1, x["clean_name"]))
    hard = sum(1 for x in out if x["severity"] == "HARD")
    if write_report:
        rp = report_path or _os.path.join(_os.path.dirname(index_csv), "index", "_IDENTITY_AUDIT.csv")
        _rpdir = _os.path.dirname(rp)
        if _rpdir:
            _os.makedirs(_rpdir, exist_ok=True)
        with open(rp, "w", newline="", encoding="utf-8") as fh:
            w = _csv.DictWriter(fh, fieldnames=["severity", "clean_name", "citation", "doi", "reasons"])
            w.writeheader(); w.writerows(out)
    return {"total": len(rows), "hard": hard, "soft": len(out) - hard, "rows": out}


# ---------------------------------------------------------------------------
# CANONICAL confidence derivation + QA re-derivation (defect: confidence-column drift)
# ---------------------------------------------------------------------------
# PRINCIPLE (user-stated, standing): confidence is a DERIVED CACHE, never a source of truth.
# Any QA/QC check must RE-DERIVE it from the data fields via mc_derive_confidence() rather than
# trust the stored column — the fields that DETERMINE confidence have primacy. Both cmd_build
# (writes) and this helper (checks) call the same rule, so they cannot drift. DOI-NEUTRAL: a DOI
# never raises confidence (identity fields alone decide).
#   HIGH     = author + year + publication + full title  (all present)
#   MEDIUM   = author + full title present, missing year and/or publication
#   LOW      = exactly ONE of {author, full title} missing
#   VERY LOW = BOTH author AND title missing
#   n/a      = datasets

def mc_derive_confidence(row):
    # SINGLE SOURCE OF TRUTH — must stay byte-for-byte equivalent to scripts/sci_file_index.py
    # derive_confidence(). Kernel QA (sfi_recompute_confidence) and the script build both call their
    # respective copy; if they diverge, a QA pass "corrects" a correctly-LOW OCR row back up and the
    # stored column drifts. Both fuse A-side identity tiers with B-side note-awareness.
    if (row.get("record_type") or "").strip().lower() == "dataset":
        return "n/a"
    note_l = (row.get("notes") or "").lower()
    # OCR/mined-but-UNVALIDATED is LOW no matter how many fields are filled (mined != verified).
    if "unvalidated" in note_l or "ocr: image-only" in note_l:
        return "low"
    A = not mc_author_unknown(row.get("first_author"))
    Y = not mc_year_unknown(row.get("year"))
    P = not mc_pub_unknown(row.get("journal"))
    T = not mc_title_hard_garbage(row.get("title"))     # "full title" = present & not garbage
    if (not A) and (not T): return "very low"
    if (not A) or (not T):  return "low"
    uncertain = any(k in note_l for k in ("guess", "unverified", "approx", "ambiguous",
                                          "no-doi", "gate-fail", "check", "uncertain"))
    trustworthy_note = (not row.get("notes")) or any(k in note_l for k in
        ("crossref:", "search:", "cryptic", "si of", "si/dataset", "doi-truncated-dropped",
         "filename-stem", "review-verdict:", "verified from", "jstor-cover:"))
    if uncertain:
        return "medium"
    if A and Y and P and T and trustworthy_note:
        return "high"
    if A and T and Y and trustworthy_note:
        return "high"
    if row.get("notes") and not trustworthy_note:
        return "medium"
    return "high" if Y else "medium"

def sfi_recompute_confidence(index_csv, write=False, report_path=None):
    """QA: re-derive confidence from the data fields for every row; report drift vs the stored column.

    NEVER trusts the stored confidence. Returns dict(total, changed, dist_stored, dist_rederived,
    rows=[{clean_name, stored, rederived, first_author, year, title, journal, doi, record_type}]).
    If write=True, rewrites index_csv in place (atomic) with the re-derived confidence and writes a
    full-citation change ledger next to it (default <dir>/index/_CONFIDENCE_RECOMPUTE_ledger.csv).
    Run it as a standing QA step whenever the index has been edited by anything other than cmd_build.
    """
    import os, tempfile
    with open(index_csv, encoding="utf-8") as f:
        rd = csv.DictReader(f); fieldnames = rd.fieldnames; rows = list(rd)
    name_col = "clean_name" if (rows and "clean_name" in rows[0]) else "file_name"
    changed = []
    from collections import Counter
    ds, dr = Counter(), Counter()
    for r in rows:
        stored = (r.get("confidence") or "").strip() or "(blank)"
        new = mc_derive_confidence(r)
        ds[stored] += 1; dr[new] += 1
        if stored != new:
            changed.append({name_col: r.get(name_col,""), "stored": stored, "rederived": new,
                            "first_author": r.get("first_author",""), "year": r.get("year",""),
                            "title": r.get("title",""), "journal": r.get("journal",""),
                            "doi": r.get("doi",""), "record_type": r.get("record_type","")})
    if write and changed:
        for r in rows:
            r["confidence"] = mc_derive_confidence(r)
        d = os.path.dirname(os.path.abspath(index_csv))
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp"); os.close(fd)
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(rows)
        os.replace(tmp, index_csv)
        if report_path is None:
            rd_ = os.path.join(d, "index"); os.makedirs(rd_, exist_ok=True)
            report_path = os.path.join(rd_, "_CONFIDENCE_RECOMPUTE_ledger.csv")
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            cols = ["change","citation",name_col,"record_type","doi"]
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
            for c in changed:
                au = c["first_author"] or "?"
                w.writerow({"change": f'{c["stored"]} -> {c["rederived"]}',
                            "citation": f'"{c["title"]}" - {au} ({c["year"] or "?"}), {c["journal"] or "?"}',
                            name_col: c[name_col], "record_type": c["record_type"], "doi": c["doi"]})
    return {"total": len(rows), "changed": len(changed),
            "dist_stored": dict(ds), "dist_rederived": dict(dr),
            "report": report_path if (write and changed) else None, "rows": changed}
