#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""fixtures_curate_gates.py -- known-bad / known-clean fixtures for the two gates
inside sci_library_curate.py's cmd_validate(): the ORPHAN gate (I16) and the
curator invariants (I17 cryptic name, I18 SI/parent DOI, I19 blank title).

WHY THESE SHAPES (not token bad cases)
The orphan gate's motivating defect (Claude Science sci-library-curate, 2026-07-24 port
lineage; the historical false-green that "reported 0 FAIL while 5,154 orphans existed")
was a BULK condition. A 1-orphan fixture can pass a gate whose real 5,154-orphan condition
persists, so `KNOWN_BAD_ORPHAN` reproduces the ACTUAL shape: MANY supplements whose parent
is absent -- the realistic form (a supplement pointing at a parent article that is not in
THIS index, i.e. a DANGLING parent_file) plus the blank-parent form. Both are "unresolved".

Each known-bad isolates EXACTLY its target invariant (all other invariants clean on that
fixture) so that `n_fail` from the real gate equals 1 == the target. If the target invariant
silently stopped firing, n_fail would drop to 0 and the harness would catch the false-green
(CLEAN on a planted defect). Isolation is asserted in test_sci_library_curate_gates.py.

INPUT SHAPE (read from the module, not guessed): cmd_validate consumes an index CSV via
_read_index() -> list[dict] (csv.DictReader). Primary key column is `clean_name` when present
else `file_name`. The gate prints "VALIDATE <col>: N rows | M FAIL | W warn" then "  FAIL <tag>"
lines and sys.exit(1 if fails else 0). The runner below drives the REAL cmd_validate and
returns its stdout with a [[vloop:...]] marker appended IFF the gate ran to completion; a crash
yields NO marker (MARKER_ABSENT) -- "the check did not demonstrably run" is not a pass.
"""
import contextlib
import csv
import importlib.util
import io
import os
import re
import sys
import tempfile
import types

# ------------------------------------------------------------------ module under test
# Default = the shipped module alongside this tests/ dir. Override with
# SCI_CURATE_MODULE=/path/to/alt.py to run the fixtures against a control (e.g. a patched
# copy) -- this is how the _by_name-fixed control was proven without touching the ship file.
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_MODULE = os.path.normpath(os.path.join(_HERE, os.pardir, "sci_library_curate.py"))
MODULE_PATH = os.environ.get("SCI_CURATE_MODULE", _DEFAULT_MODULE)


def load_module(path=None):
    path = path or MODULE_PATH
    spec = importlib.util.spec_from_file_location("sci_library_curate_uut", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------ the real-gate runner
_SUMMARY_RE = re.compile(r"\|\s*(\d+)\s*FAIL\b")
_ROWS_RE = re.compile(r":\s*(\d+)\s*rows\s*\|")
_FAILTAG_RE = re.compile(r"^\s*FAIL\s+(I\d+)\b")


def run_gate(rows, *, module=None, lib=None, decisions=None):
    """Invoke the REAL cmd_validate on `rows`. Returns a dict:
      stdout, exit_code, exception (str|None), n_rows, n_fail (int|None), fired_tags (set).
    n_fail is None ONLY when the gate crashed before printing its summary."""
    module = module or load_module()
    fieldnames = []
    for r in rows:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    fd, path = tempfile.mkstemp(suffix=".csv", dir=_HERE)
    os.close(fd)
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        args = types.SimpleNamespace(index=path, lib=lib, decisions=decisions, report=None)
        buf = io.StringIO()
        exit_code, exc = None, None
        try:
            with contextlib.redirect_stdout(buf):
                module.cmd_validate(args)
        except SystemExit as e:
            exit_code = e.code
        except Exception as e:                                    # noqa: BLE001
            exc = "%s: %s" % (type(e).__name__, e)
        out = buf.getvalue()
    finally:
        os.unlink(path)

    n_fail = None
    m = _SUMMARY_RE.search(out)
    if m:
        n_fail = int(m.group(1))
    n_rows = int(_ROWS_RE.search(out).group(1)) if _ROWS_RE.search(out) else len(rows)
    fired = {t.group(1) for t in (_FAILTAG_RE.match(l) for l in out.splitlines()) if t}
    return {"stdout": out, "exit_code": exit_code, "exception": exc,
            "n_rows": n_rows, "n_fail": n_fail, "fired_tags": fired}


def make_runner(marker_name, *, module=None, lib=None):
    """Return a harness-compatible runner(fixture)->str for one gate.

    A `fixture` is a list of index rows. The runner drives the REAL gate and appends
    emit_marker(marker_name, n_claims=n_rows, n_fail=<parsed FAIL count>) ONLY if the gate
    ran to completion. A crash returns the (empty) stdout with an explanatory comment and NO
    marker -> classify() -> MARKER_ABSENT -> the harness flags "the check did not run"."""
    from vloop_harness import emit_marker

    def _runner(fixture):
        res = run_gate(fixture, module=module, lib=lib)
        if res["exception"] is not None or res["n_fail"] is None:
            # Gate did not demonstrably run: emit NO marker (MARKER_ABSENT, not a pass).
            return (res["stdout"]
                    + "\n# GATE DID NOT COMPLETE: %s -- no marker emitted (MARKER_ABSENT)"
                    % (res["exception"] or "no summary line printed"))
        return res["stdout"] + "\n" + emit_marker(marker_name, res["n_rows"], res["n_fail"])

    return _runner


# ==========================================================================================
# FIXTURES
# ==========================================================================================
# Column set mirrors what cmd_validate reads: clean_name, record_type, first_author, year,
# title, doi, journal, parent_file, notes, dedup_note, bundle_folder, pages. Any column the
# gate does not read is simply ignored.

def _art(cn, au, yr, title, doi="", journal="Jour", bundle="", pages="12", **kw):
    r = {"clean_name": cn, "record_type": "article", "first_author": au, "year": str(yr),
         "title": title, "doi": doi, "journal": journal, "parent_file": "",
         "notes": "", "dedup_note": "", "bundle_folder": bundle or _stem(cn), "pages": pages}
    r.update(kw)
    return r


def _supp(cn, parent_file="", doi="", notes="", bundle="", record_type="supplement",
          first_author="", year="", title="Supplementary information", **kw):
    r = {"clean_name": cn, "record_type": record_type, "first_author": first_author,
         "year": str(year), "title": title, "doi": doi, "journal": "",
         "parent_file": parent_file, "notes": notes, "dedup_note": "",
         "bundle_folder": bundle, "pages": ""}
    r.update(kw)
    return r


def _stem(cn):
    return re.sub(r"\.[A-Za-z0-9]+$", "", cn)


# ---- ORPHAN gate (I16) -------------------------------------------------------------------
# KNOWN-BAD: bulk (8) unresolved supplements amid healthy articles, reproducing the realistic
# 5,154 shape -- supplements orphaned because their parent article is absent from THIS index.
# Six carry a DANGLING parent_file (the parent was expected but is not present); two carry a
# blank parent_file. NONE carry the orphan_parent_absent flag. Every name uses a DIGIT-FREE
# Author_Year token (a digit in the author token trips is_cryptic_name and would make I17 fire
# too -- verified), so the gate's FAIL count is ISOLATED to the I16 orphan class. Three real
# articles populate _main_names so the fixture is not the degenerate empty-mains case; their
# DOIs/years differ so no dedup/truncation invariant trips.
_ORPHAN_SURNAMES = ["Alfa", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"]
N_ORPHANS = 8
KNOWN_BAD_ORPHAN = (
    [_art("Real%s_20%02d_Jour_StudyOf%s.pdf" % (s, 5 + i, s), s, 2005 + i,
          "A real study number %d" % i, doi="10.1000/real.%d" % i, journal="Jour")
     for i, s in enumerate(["Xray", "Yankee", "Zulu"])]           # 3 healthy articles
    + [_supp("%s_20%02d_Jour_suppl1.pdf" % (_ORPHAN_SURNAMES[i], 10 + i),
             parent_file="%s_20%02d_Jour_MissingParent.pdf" % (_ORPHAN_SURNAMES[i], 10 + i))
       for i in range(6)]                                          # 6 dangling-parent orphans
    + [_supp("%s_2019_Jour_suppl1.pdf" % _ORPHAN_SURNAMES[6 + i], parent_file="")
       for i in range(2)]                                          # 2 blank-parent orphans
)

# KNOWN-CLEAN: a HEALTHY library exercising every "must NOT fire" path of I16:
#   (1) an article + its resolving SI (matching DOI, same bundle_folder) -- a linked SI is
#       fine and must not be flagged; (2) a blank-parent SI honestly flagged
#       orphan_parent_absent -- an admitted orphan is fine. Expect 0 FAIL.
KNOWN_CLEAN_ORPHAN = [
    _art("Green_2019_Ecology_RiparianNestFlooding.pdf", "Green", 2019,
         "Flooding of riparian bird nests under warming", doi="10.1111/ecy.2019.1",
         journal="Ecology", bundle="Green_2019_Ecology_RiparianNestFlooding"),
    _supp("Green_2019_Ecology_RiparianNestFlooding_suppl1.pdf",
          parent_file="Green_2019_Ecology_RiparianNestFlooding.pdf",
          doi="10.1111/ecy.2019.1", bundle="Green_2019_Ecology_RiparianNestFlooding"),
    _supp("Loose_2018_Jour_suppl1.pdf", parent_file="",
          notes="orphan_parent_absent parent article not present in this library"),
]

# ---- I17 cryptic clean_name --------------------------------------------------------------
# KNOWN-BAD: an ARTICLE with a cryptic publisher-code name (leading digits) and NO
# cryptic_unresolved flag. Title present (so I19 stays quiet), non-year-first (I2 quiet).
# Isolated to I17. (An article never touches _by_name, so this path runs as-shipped.)
KNOWN_BAD_I17 = [
    _art("41586_2020_1234_Article.pdf", "Unknown", "2020",
         "A paper whose file kept its publisher code", doi="10.1038/s41586-020-1234",
         journal="Nature"),
    # a proper article so `_known` journal logic and I1 have >1 row and nothing else trips
    _art("Real_2021_Nature_ProperName.pdf", "Real", 2021,
         "A properly named companion article", doi="10.1038/s41586-021-9",
         journal="Nature"),
]
# KNOWN-CLEAN: same shape but the cryptic row carries the cryptic_unresolved flag AND a
# proper Author_Year article. Expect 0 FAIL.
KNOWN_CLEAN_I17 = [
    _art("41586_2020_1234_Article.pdf", "Unknown", "2020",
         "A paper whose file kept its publisher code", doi="10.1038/s41586-020-1234",
         journal="Nature", notes="cryptic_unresolved could not derive Author_Year identity"),
    _art("Real_2021_Nature_ProperName.pdf", "Real", 2021,
         "A properly named companion article", doi="10.1038/s41586-021-9",
         journal="Nature"),
]

# ---- I18 SI/parent stored-DOI disagreement (index-only path) -----------------------------
# KNOWN-BAD: a LINKED SI (parent resolves to a MAIN row) whose STORED doi disagrees with the
# parent's stored doi, neither being a data-repository DOI. This is the Seasonality_Biog
# mislink shape (SI 10.1038/s41558... vs parent 10.5194/bg-...). Reproduces I18's motivating
# defect on the index-only fallback (no --lib PDFs available here). Non-cryptic names ->
# I17 quiet; SI resolves -> I16 quiet. Isolated to I18. NOTE: requires the parent to resolve,
# which is exactly the path that touches _by_name -> crashes on the AS-SHIPPED module.
KNOWN_BAD_I18 = [
    _art("Seas_2024_Biogeosciences_SeasonalityOfX.pdf", "Seas", 2024,
         "Seasonality of biogeochemical fluxes", doi="10.5194/bg-22-1985",
         journal="Biogeosciences", bundle="Seas_2024_Biogeosciences_SeasonalityOfX"),
    _supp("Seas_2024_Biogeosciences_SeasonalityOfX_suppl1.pdf",
          parent_file="Seas_2024_Biogeosciences_SeasonalityOfX.pdf",
          doi="10.1038/s41558-024-09999",     # a DIFFERENT paper's DOI -> mislink
          bundle="Seas_2024_Biogeosciences_SeasonalityOfX"),
]
# KNOWN-CLEAN: same linked SI but its stored DOI AGREES with the parent (suffix-tolerant).
# Expect 0 FAIL.
KNOWN_CLEAN_I18 = [
    _art("Seas_2024_Biogeosciences_SeasonalityOfX.pdf", "Seas", 2024,
         "Seasonality of biogeochemical fluxes", doi="10.5194/bg-22-1985",
         journal="Biogeosciences", bundle="Seas_2024_Biogeosciences_SeasonalityOfX"),
    _supp("Seas_2024_Biogeosciences_SeasonalityOfX_suppl1.pdf",
          parent_file="Seas_2024_Biogeosciences_SeasonalityOfX.pdf",
          doi="10.5194/bg-22-1985-supplement",   # same DOI + supplement suffix -> agrees
          bundle="Seas_2024_Biogeosciences_SeasonalityOfX"),
]

# ---- I19 article with blank title --------------------------------------------------------
# KNOWN-BAD: an ARTICLE row whose title is blank (identity not real). Author/year present so
# only I19 fires (I4's author/year components stay quiet; I4 is WARN anyway). Non-cryptic
# name -> I17 quiet. Isolated to I19. Runs as-shipped (articles don't touch _by_name).
KNOWN_BAD_I19 = [
    _art("Blank_2021_Nature_MissingTitle.pdf", "Blank", 2021, "",
         doi="10.1038/s41586-021-blank", journal="Nature"),
    _art("Titled_2022_Nature_HasATitle.pdf", "Titled", 2022,
         "This article has a real title", doi="10.1038/s41586-022-9", journal="Nature"),
]
# KNOWN-CLEAN: both articles titled. Expect 0 FAIL.
KNOWN_CLEAN_I19 = [
    _art("Blank_2021_Nature_MissingTitle.pdf", "Blank", 2021,
         "Now this article has a title too", doi="10.1038/s41586-021-blank", journal="Nature"),
    _art("Titled_2022_Nature_HasATitle.pdf", "Titled", 2022,
         "This article has a real title", doi="10.1038/s41586-022-9", journal="Nature"),
]

# Convenience: the invariants-gate clean fixture exercises I17+I18+I19 "must-not-fire" paths
# at once (a healthy multi-row index). Reused as the known_clean for the invariants gate.
KNOWN_CLEAN_INVARIANTS = [
    _art("Green_2019_Ecology_RiparianNestFlooding.pdf", "Green", 2019,
         "Flooding of riparian bird nests under warming", doi="10.1111/ecy.2019.1",
         journal="Ecology", bundle="Green_2019_Ecology_RiparianNestFlooding"),
    _supp("Green_2019_Ecology_RiparianNestFlooding_suppl1.pdf",
          parent_file="Green_2019_Ecology_RiparianNestFlooding.pdf",
          doi="10.1111/ecy.2019.1", bundle="Green_2019_Ecology_RiparianNestFlooding"),
    _art("Real_2021_Nature_ProperName.pdf", "Real", 2021,
         "A properly named companion article", doi="10.1038/s41586-021-9", journal="Nature"),
]
