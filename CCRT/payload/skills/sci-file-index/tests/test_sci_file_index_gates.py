#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""test_sci_file_index_gates.py -- verify-the-embed harness driver for the
sci-file-index build-time gates.

Run:  python3 test_sci_file_index_gates.py

EXIT CONTRACT -- read this before wiring the file into CI. The exit code reports
AS-DESIGNED vs UNEXPECTED, *not* registry PASS vs FAIL, because this suite deliberately
enforces a blind spot that is STILL LIVE in the module under test:

  exit 0 = AS-DESIGNED. The known live false-green (`false_green_wrong_author`) is
           enforced as a gate FAIL and nothing ELSE failed. Expect the run to print
           "REGISTRY VERDICT: FAIL" alongside exit 0 -- that pairing is correct here.
  exit 2 = UNEXPECTED. Either the false-green stopped being enforced, or some other
           gate broke. Both need a human.

Consequence worth stating plainly: once someone FIXES the selfcheck_identity blind spot,
this suite starts exiting 2 ("the false-green is no longer reproducible"). That is the
signal to flip `false_green_wrong_author` from an enforced-defect fixture to an ordinary
known-bad -- not a regression. Do NOT read exit 0 as "all gates PASS".

Registers TWO gates and runs each against its known-bad / known-clean fixture
pair through vloop_harness. A gate that greens on a planted defect, fires on the
clean fixture, or emits no marker FAILS -- the harness enforces that mechanically.

  GATE 1  sci_selfcheck_identity  -- the build-time identity validator
          selfcheck_identity(rows) (the "scrub_verify" gate). 9 classes the gate
          currently catches, PLUS the historical FALSE-GREEN class
          ("false_green_wrong_author") which the gate currently does NOT catch.
          The false-green is registered in known_bad, so the harness reports a
          FALSE GREEN and this gate FAILS on the current module -- the blind spot
          is ENFORCED (mechanically caught), not merely printed. Expect
          sci_selfcheck_identity == FAIL and REGISTRY VERDICT == FAIL until the
          gate is fixed to catch a wrong author on a cryptic filename.

  GATE 2  sci_flag_emission       -- the cmd_build I17/I18 note stamps
          (`si-doi-disagrees-parent`, `cryptic_unresolved`). Drives cmd_build
          end-to-end; n_fail = count of stamped I17/I18 flags.

Beyond the harness's own pass/fail, this file adds SEMANTIC assertions: each
GATE 1 known-bad must flag its OWN registered class (guards the vacuous pass
where a fixture triggers some OTHER class), and a MUTATION check proves the
GATE 2 fixtures exercise the real changed code (disabling the stamp lines makes
the known-bad go clean).
"""
import contextlib
import csv
import io
import os
import shutil
import sys
import tempfile
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.dirname(_HERE)
for p in (_HERE, _SKILL):
    if p not in sys.path:
        sys.path.insert(0, p)

import sci_file_index as sfi                              # noqa: E402
import fixtures_sci_file_index as fx                      # noqa: E402
from vloop_harness import (emit_marker, register_gate,    # noqa: E402
                           run_fixture_pair, verify_registry,
                           print_registry_report, classify, DEFECTS, CLEAN)

MARKER = "sci_selfcheck_identity"
FLAG_MARKER = "sci_flag_emission"
I17_I18_FLAGS = ("si-doi-disagrees-parent", "cryptic_unresolved")


# --------------------------------------------------------------------------
# GATE 1 runner: selfcheck_identity over a list of index rows.
# n_fail = number of rows flagged (the gate's own unit -- one tuple per row).
# --------------------------------------------------------------------------
def selfcheck_runner(rows):
    flags = sfi.selfcheck_identity(rows)
    return "selfcheck ran on %d row(s)\n%s" % (
        len(rows), emit_marker(MARKER, len(rows), len(flags)))


# --------------------------------------------------------------------------
# GATE 2 runner: run cmd_build end-to-end on raw rows, count I17/I18 stamps.
# n_fail = number of rows carrying either I17/I18 flag.
# --------------------------------------------------------------------------
def _build_index(module, raw_rows):
    d = tempfile.mkdtemp(prefix="sfi_gate_")
    try:
        ixd = module.index_dir(d)
        with open(os.path.join(ixd, module.RAW_NAME), "w",
                  encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(fx.RAW_FIELDS))
            w.writeheader()
            for r in raw_rows:
                w.writerow(r)
        args = types.SimpleNamespace(dir=d, index=None, overrides=None)
        with contextlib.redirect_stdout(io.StringIO()):
            module.cmd_build(args)
        with open(os.path.join(ixd, "paper_index.csv"), encoding="utf-8") as f:
            return list(csv.DictReader(f))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _count_i17_i18(rows):
    return sum(1 for r in rows
               if any(flag in (r.get("notes") or "") for flag in I17_I18_FLAGS))


def flag_runner(raw_rows):
    rows = _build_index(sfi, raw_rows)
    return "cmd_build produced %d row(s)\n%s" % (
        len(rows), emit_marker(FLAG_MARKER, len(rows), _count_i17_i18(rows)))


# --------------------------------------------------------------------------
# Assemble GATE 1 fixtures from the spec table; verify each known-bad flags its
# OWN class (semantic non-vacuousness) before handing the harness the fixtures.
# --------------------------------------------------------------------------
def _semantic_selfcheck_checks():
    """Returns (problems, known_bad_dict). Each known-bad row must (a) be flagged
    and (b) carry its registered class token in the reasons -- else the fixture is
    exercising a different defect than it claims (a vacuous pass)."""
    problems = []
    known_bad = {}
    for cls, spec in fx.SELFCHECK_BAD_SPECS.items():
        r = fx.index_row(sfi.fold_ascii, **spec)
        flags = sfi.selfcheck_identity([r])
        known_bad[cls] = [r]
        if not flags:
            problems.append("known_bad[%s]: selfcheck did NOT flag it at all" % cls)
            continue
        reasons_tokens = set()
        for _fn, _sev, why in flags:
            reasons_tokens.update(t.strip() for t in why.split(";"))
        if cls not in reasons_tokens:
            problems.append("known_bad[%s]: flagged, but reasons %s lack the class "
                            "token (fixture may exercise a DIFFERENT class)"
                            % (cls, sorted(reasons_tokens)))
    return problems, known_bad


# The historical FALSE-GREEN case, registered as its OWN GATE-1 defect class
# (FALSE_GREEN_CLASS) in known_bad so the harness ENFORCES it. On the CURRENT
# module selfcheck returns [] for this row (a LIVE blind spot), so the harness
# reports a FALSE GREEN and sci_selfcheck_identity FAILS -- which is the correct,
# honest signal. This is enforcement (the registry catches it), not surfacing
# (a printed note). The verdict flips to PASS only when the gate is fixed to
# catch a wrong author on a cryptic filename (a module edit, out of scope here).
FALSE_GREEN_CLASS = "false_green_wrong_author"


def false_green_row():
    return fx.index_row(sfi.fold_ascii, **fx.SELFCHECK_FALSE_GREEN_SPEC)


def _mutation_check_gate2():
    """Prove the GATE 2 fixtures exercise the real changed code: with the two
    2026-07-24 stamp lines disabled, the known-bad must go CLEAN."""
    src_path = os.path.join(_SKILL, "sci_file_index.py")
    src = open(src_path, encoding="utf-8").read()
    mut_src = (src
        .replace('r["notes"] = (r["notes"] + "; " if r["notes"] else "") + "si-doi-disagrees-parent"',
                 'pass  # mutation: si-doi stamp disabled')
        .replace('r["notes"] = (r["notes"] + "; " if r["notes"] else "") + "cryptic_unresolved"',
                 'pass  # mutation: cryptic stamp disabled'))
    if mut_src == src:
        return ["mutation check: could not locate BOTH stamp lines to disable"]
    mut = types.ModuleType("sci_file_index_MUTANT")
    exec(compile(mut_src, "sci_file_index_MUTANT.py", "exec"), mut.__dict__)
    problems = []
    if _count_i17_i18(_build_index(mut, fx.flag_bad_sidoi_raw())) != 0:
        problems.append("mutation check: si-doi still stamped with stamp line disabled "
                        "-> fixture does NOT exercise the changed code")
    if _count_i17_i18(_build_index(mut, fx.flag_bad_cryptic_raw())) != 0:
        problems.append("mutation check: cryptic still stamped with stamp line disabled "
                        "-> fixture does NOT exercise the changed code")
    return problems


def build_registry():
    sem_problems, known_bad = _semantic_selfcheck_checks()
    clean_rows = [fx.index_row(sfi.fold_ascii, **s) for s in fx.selfcheck_clean_specs()]

    # Register the historical false-green as its OWN class. The gate claims to
    # stop a "wrong paper / junk author" row passing silently (its docstring), so
    # a confidently-wrong author IS in scope. On the current module the gate does
    # NOT catch it -> the harness reports FALSE GREEN and this gate FAILS. That
    # FAIL is the enforced, expected signal of the live blind spot.
    known_bad[FALSE_GREEN_CLASS] = [false_green_row()]
    defect_classes = list(fx.SELFCHECK_BAD_SPECS.keys()) + [FALSE_GREEN_CLASS]

    register_gate(
        MARKER, selfcheck_runner,
        known_bad=known_bad,
        known_clean=clean_rows,
        defect_classes=defect_classes,
        motivating_evidence="sci-file-index PROC.9b self-check; historical "
                            "'SELF-CHECK: 0 disagreements' false-green",
        target="sci_file_index.selfcheck_identity")

    register_gate(
        FLAG_MARKER, flag_runner,
        known_bad={"si-doi-disagrees-parent": fx.flag_bad_sidoi_raw(),
                   "cryptic_unresolved": fx.flag_bad_cryptic_raw()},
        known_clean=fx.flag_clean_raw(),
        defect_classes=["si-doi-disagrees-parent", "cryptic_unresolved"],
        motivating_evidence="sci-file-index SKILL.md 2026-07-24 I17/I18 flag emission",
        target="sci_file_index.cmd_build (I17/I18 note stamps)")

    return sem_problems


def main():
    sem_problems = build_registry()

    print("=" * 72)
    print("sci-file-index gate verification (verify-the-embed harness)")
    print("=" * 72)

    rep = verify_registry()
    print_registry_report(rep)

    # ---- extra semantic / non-vacuousness checks (beyond harness) ----
    extra = []
    if sem_problems:
        extra += ["GATE1 semantic: " + p for p in sem_problems]
    extra += ["GATE2 " + p for p in _mutation_check_gate2()]

    # ---- explain the ENFORCED false-green (the harness caught it as a gate FAIL) ----
    fg = false_green_row()
    fg_flags = sfi.selfcheck_identity([fg])
    fg_conf = sfi.derive_confidence(fg)
    g1 = next((r for r in rep["results"] if r["gate"] == MARKER), None)
    fg_detail = (g1 or {}).get("detail", {}).get(FALSE_GREEN_CLASS, {})
    print("\nENFORCED FALSE-GREEN class %r:" % FALSE_GREEN_CLASS)
    print("  selfcheck_identity -> %r   confidence -> %r" % (fg_flags, fg_conf))
    print("  harness verdict on this class -> %r (%s)"
          % (fg_detail.get("verdict"), fg_detail.get("marker")))
    if not fg_flags:
        print("  The gate returns [] on a confidently-WRONG author because the cryptic")
        print("  filename defeats wellnamed(), so the author!=filename / title!=filename")
        print("  cross-checks never run and the row ships at '%s'. The harness reports" % fg_conf)
        print("  this as a FALSE GREEN, so sci_selfcheck_identity FAILS -- the blind spot")
        print("  is mechanically ENFORCED, not merely printed. It is the documented")
        print("  '0 FAIL while defects exist' class, STILL LIVE on this module.")

    print("\n" + "=" * 72)
    if extra:
        print("SUPPLEMENTARY CHECK FAILURES (fixture/wiring defects):")
        for e in extra:
            print("  - %s" % e)
    # Distinguish the EXPECTED gate FAIL (live blind spot) from an UNEXPECTED
    # fixture/wiring defect. The registry SHOULD be FAIL here, driven solely by
    # the false-green class on GATE 1; anything else is a fixture bug.
    g1_problems = [p for p in (g1 or {}).get("problems", [])
                   if FALSE_GREEN_CLASS not in p]
    g2 = next((r for r in rep["results"] if r["gate"] == FLAG_MARKER), None)
    g2_problems = (g2 or {}).get("problems", [])
    unexpected = extra + g1_problems + g2_problems
    fg_enforced = (fg_detail.get("verdict") == CLEAN)   # harness saw a false green
    print("EXPECTED-STATE CHECK:")
    print("  false-green ENFORCED as a gate FAIL: %s" % fg_enforced)
    print("  no OTHER (unexpected) failures: %s" % (not unexpected))
    if unexpected:
        for u in unexpected:
            print("    - UNEXPECTED: %s" % u)
    # The run is "as designed" when the ONLY failure is the enforced false-green.
    as_designed = fg_enforced and not unexpected
    print("\nREGISTRY VERDICT: %s   (expected FAIL: the live false-green is enforced)"
          % rep["verdict"])
    print("RUN STATUS: %s" % ("AS-DESIGNED (only the enforced live blind spot fails)"
                              if as_designed else "UNEXPECTED FAILURE -- investigate above"))
    print("=" * 72)
    # Exit 0 when the run is exactly as-designed (false-green enforced, nothing
    # else broken); exit 2 if any unexpected fixture/wiring defect appears or the
    # false-green stopped being enforced (e.g. the gate silently changed).
    return 0 if as_designed else 2


if __name__ == "__main__":
    sys.exit(main())
