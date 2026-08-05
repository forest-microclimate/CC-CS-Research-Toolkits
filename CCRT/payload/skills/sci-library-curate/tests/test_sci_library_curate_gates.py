#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""test_sci_library_curate_gates.py -- register the sci_library_curate.py gates in the
vloop harness GATES registry and verify each FAILS its known-bad and PASSES its known-clean.

TWO gates (matching the two the module actually ships inside cmd_validate):
  orphan_i16              -- I16: a supplement/dataset with no parent resolving to a MAIN
                             row and no orphan_parent_absent flag. Motivating defect: the
                             orphan gate that "reported 0 FAIL while 5,154 orphans existed".
                             known-bad reproduces the BULK shape (8 orphans), not 1.
  curator_invariants      -- I17 cryptic clean_name, I18 SI/parent DOI disagreement,
                             I19 blank article title. One known-bad fixture PER class.

HOW TO READ THE OUTPUT
Run with no args to test the SHIPPED module. Set SCI_CURATE_MODULE to a control copy to
test a candidate fix. The script prints:
  1. the harness self-test (must PASS or nothing below is trustworthy),
  2. an ISOLATION table  -- each known-bad, run through the real gate, must fire EXACTLY its
     target invariant (n_fail==1, fired=={target}); a known-bad that also trips another
     invariant is a mis-built fixture, and one that fires nothing is a false-green,
  3. the GATES registry verdict (verbatim).

A gate that CRASHES on a fixture emits NO marker -> MARKER_ABSENT -> the harness reports
"the check did not demonstrably run (this is not a pass)". MARKER_ABSENT != CLEAN.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vloop_harness import (GATES, classify, emit_marker, print_registry_report,  # noqa: E402
                           register_gate, run_fixture_pair, selftest, verify_registry)
import fixtures_curate_gates as fx  # noqa: E402


# ---- register the two gates -------------------------------------------------------------
def register_all():
    GATES.clear()
    register_gate(
        "orphan_i16",
        runner=fx.make_runner("orphan_i16"),
        known_bad={"orphan_unresolved_bulk": fx.KNOWN_BAD_ORPHAN},
        known_clean=fx.KNOWN_CLEAN_ORPHAN,
        defect_classes=["orphan_unresolved_bulk"],
        motivating_evidence="I16 orphan gate: historical false-green reported 0 FAIL while "
                            "5,154 orphans existed (bulk unresolved supplements). "
                            "Taxonomy: vacuous-pass / efficacy-from-existence (F1).",
        target="sci_library_curate.py::cmd_validate I16",
    )
    register_gate(
        "curator_invariants",
        runner=fx.make_runner("curator_invariants"),
        known_bad={
            "I17_cryptic_clean_name": fx.KNOWN_BAD_I17,
            "I18_si_parent_doi_disagree": fx.KNOWN_BAD_I18,
            "I19_blank_article_title": fx.KNOWN_BAD_I19,
        },
        known_clean=fx.KNOWN_CLEAN_INVARIANTS,
        defect_classes=["I17_cryptic_clean_name", "I18_si_parent_doi_disagree",
                        "I19_blank_article_title"],
        motivating_evidence="I17/I18/I19 ported from Claude Science sci-library-curate "
                            "2026-07-24; I18 catches the Seasonality_Biog SI/parent DOI "
                            "mislink. Taxonomy: surfacing != enforcement (F1/F2).",
        target="sci_library_curate.py::cmd_validate I17,I18,I19",
    )


# ---- isolation check: each known-bad must fire EXACTLY its target invariant --------------
# Maps each declared defect class to the FAIL tag the real gate must emit for it.
TARGET_TAG = {
    "orphan_unresolved_bulk": "I16",
    "I17_cryptic_clean_name": "I17",
    "I18_si_parent_doi_disagree": "I18",
    "I19_blank_article_title": "I19",
}


def isolation_report():
    rows = []
    for gate in GATES.values():
        for cls, fixture in sorted(gate["known_bad"].items()):
            res = fx.run_gate(fixture)
            target = TARGET_TAG.get(cls, "?")
            crashed = res["exception"] is not None or res["n_fail"] is None
            if crashed:
                verdict = "CRASH (MARKER_ABSENT)"
            elif res["fired_tags"] == {target} and res["n_fail"] == 1:
                verdict = "ISOLATED ok"
            elif target in res["fired_tags"] and res["fired_tags"] != {target}:
                verdict = "FIRED+others %s" % sorted(res["fired_tags"])
            elif target not in res["fired_tags"]:
                verdict = "FALSE-GREEN (target %s did NOT fire; fired=%s)" % (
                    target, sorted(res["fired_tags"]) or "nothing")
            else:
                verdict = "n_fail=%s fired=%s" % (res["n_fail"], sorted(res["fired_tags"]))
            rows.append((gate["name"], cls, target, res["n_fail"],
                         sorted(res["fired_tags"]),
                         (res["exception"] or "")[:60], verdict))
    return rows


def main():
    mod_path = fx.MODULE_PATH
    print("MODULE UNDER TEST: %s" % mod_path)
    print("=" * 88)

    st = selftest(verbose=False)
    print("harness self-test: %s (%d/%d checks)"
          % (st["verdict"], st["n_checks"] - st["n_failed"], st["n_checks"]))
    if st["verdict"] != "PASS":
        print("ABORT: harness self-test failed; nothing below is trustworthy.")
        for f in st["failures"]:
            print("  -", f)
        return 2

    register_all()

    print("\nISOLATION TABLE (each known-bad through the REAL gate)")
    print("-" * 88)
    print("%-20s %-28s %-6s %-7s %-16s %s" %
          ("gate", "defect_class", "target", "n_fail", "fired_tags", "verdict"))
    for gate, cls, target, n_fail, fired, exc, verdict in isolation_report():
        print("%-20s %-28s %-6s %-7s %-16s %s"
              % (gate, cls, target, n_fail, ",".join(fired) or "-", verdict))
        if exc:
            print("      exception: %s" % exc)

    print("\nGATES REGISTRY")
    print("-" * 88)
    rep = verify_registry()
    print_registry_report(rep)
    return 0 if rep["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
