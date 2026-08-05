#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
r"""test_post_edit_smoke.py -- fixture-pair harness driver + targeted asserts for VLOOP Item 3.

Run:  python3 test_post_edit_smoke.py       (exit 0 = PASS, 2 = FAIL)

It does three things, in order of increasing strictness:
  1. Registers the post_edit_smoke gate with SIX real fixture modules (tests/fixtures/) and
     runs the vloop_harness fixture-pair contract (every known_bad must read DEFECTS, the
     known_clean must read CLEAN, a marker must be present on every run).
  2. Adds per-fixture asserts that each planted defect fails for its INTENDED REASON -- not
     merely that it fails. The two load-bearing ones:
        * non-exercising  : func_ok is True (NOTHING raised) yet the gate FAILs on coverage.
        * branch-miss     : func_ok is True AND every changed LINE is covered, yet the gate
                            FAILs on an untaken branch arc -> branch coverage bites on its own.
  3. Proves the changed-line SOURCES: the explicit fallback (payload is not git), a real
     git work tree (diff-parsed), and that an UNKNOWN changed-set is a hard FAIL, never a
     silent pass over nothing.
"""
import ast
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))   # post_edit_smoke.py + vloop_harness.py live one up
sys.path.insert(0, _HERE)                     # tests/ also carries a vloop_harness.py copy

import post_edit_smoke as pes
from post_edit_smoke import run_smoke, register_smoke_gate, GATE_NAME, derive_changed_lines, CannotScopeDiff
from vloop_harness import run_fixture_pair, classify, MARKER_ABSENT, CLEAN, DEFECTS, GATES

FIX = os.path.join(_HERE, "fixtures")


def func_span(path, funcname):
    """Executable line span of a top-level function, from the AST. Used as the fixture's
    'changed lines' -- a port adds whole functions, so the function body IS the changed set.
    Deriving it from source (not hand-counting) keeps the fixtures honest if edited."""
    tree = ast.parse(open(path).read())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == funcname:
            return list(range(node.lineno, node.end_lineno + 1))
    raise KeyError("no function %r in %s" % (funcname, path))


def build_specs():
    p = lambda fn: os.path.join(FIX, fn)
    return {
        # (a) hidden-dependency runtime error: the real I16-I19 shape.
        "nameerror": {
            "name": "i17_port_broken", "target_path": p("i17_port_broken.py"),
            "changed_lines": func_span(p("i17_port_broken.py"), "check_i17"),
            "driver_body": 'mod.check_i17([{"record_type": "supplement", "clean_name": "1234_MOESM1.pdf"}])',
        },
        # (b) ImportError on fresh import.
        "importerror": {
            "name": "si_miner_importerror", "target_path": p("si_miner_importerror.py"),
            "changed_lines": func_span(p("si_miner_importerror.py"), "check_i18"),
            "driver_body": 'mod.check_i18([{"x": 1}])',
        },
        # (c) NON-EXERCISING: the vacuous pass -- code runs, changed lines untouched.
        "nonexercising": {
            "name": "nonexercising", "target_path": p("nonexercising.py"),
            "changed_lines": func_span(p("nonexercising.py"), "classify_supp"),
            "driver_body": 'mod.existing_thing(1)   # NEVER calls the changed classify_supp',
        },
        # other runtime exception (not in a 3-name allowlist).
        "otherexc": {
            "name": "otherexc", "target_path": p("otherexc.py"),
            "changed_lines": func_span(p("otherexc.py"), "parse_supp"),
            "driver_body": 'mod.parse_supp({"count": 0})',
        },
        # branch-independence proof (requirement 3).
        "branchmiss": {
            "name": "branch_miss", "target_path": p("branch_miss.py"),
            "changed_lines": func_span(p("branch_miss.py"), "flag_row"),
            "driver_body": 'mod.flag_row({"orphan": True})   # only the if-True arc',
        },
        # known_clean: fixed port, every changed line + branch arc exercised.
        "clean": {
            "name": "i17_port_fixed", "target_path": p("i17_port_fixed.py"),
            "changed_lines": func_span(p("i17_port_fixed.py"), "is_cryptic_name"),
            "driver_body": (
                'for _cn in ["1234.pdf", "abc1234.pdf", "x_MOESM1.pdf", '
                '"Smith_2020_data.pdf", "randomstem.pdf"]:\n'
                '    mod.is_cryptic_name(_cn)   # hits every branch arc of is_cryptic_name'),
        },
    }


def main():
    fails = []

    def want(label, cond, detail=None):
        if not cond:
            fails.append("%s%s" % (label, (" :: %r" % (detail,)) if detail is not None else ""))
        print("  [%s] %s" % ("ok" if cond else "FAIL", label))

    specs = build_specs()

    # ---- 2. per-fixture: fails for the INTENDED reason -------------------------------
    print("\n-- per-fixture intended-reason checks --")
    r = run_smoke(specs["nameerror"])
    want("nameerror: func_ok is False", r["func_ok"] is False, r["func_ok"])
    want("nameerror: exc is NameError (unported _cn_stem)", r["exc_type"] == "NameError", r["exc_type"])

    r = run_smoke(specs["importerror"])
    want("importerror: func_ok is False", r["func_ok"] is False, r["func_ok"])
    want("importerror: exc is ImportError-family",
         r["exc_type"] in ("ImportError", "ModuleNotFoundError"), r["exc_type"])

    r = run_smoke(specs["otherexc"])
    want("otherexc: func_ok is False", r["func_ok"] is False, r["func_ok"])
    want("otherexc: caught a NON-allowlist exc (ZeroDivisionError)",
         r["exc_type"] == "ZeroDivisionError", r["exc_type"])
    want("otherexc: proves top-level catch is not {NameError,ImportError,AttributeError}",
         r["exc_type"] not in ("NameError", "ImportError", "AttributeError"), r["exc_type"])

    # THE load-bearing one: non-exercising is a VACUOUS PASS for a functional-only gate.
    r = run_smoke(specs["nonexercising"])
    want("nonexercising: func_ok is True (nothing raised)", r["func_ok"] is True, r["func_ok"])
    want("nonexercising: n_fail >= 1 anyway (coverage bites)", r["n_fail"] >= 1, r["n_fail"])
    want("nonexercising: the uncovered set is the changed function body",
         len(r["uncovered_changed"]) >= 1 and set(r["uncovered_changed"]) <= set(r["changed_lines"]),
         r["uncovered_changed"])
    want("nonexercising: a functional-only gate WOULD have passed it",
         r["func_ok"] is True and r["n_fail"] >= 1)
    NONEXERCISING_FAILED = (r["func_ok"] is True and r["n_fail"] >= 1
                            and len(r["uncovered_changed"]) >= 1)

    # branch coverage bites INDEPENDENTLY: runs fine, all lines covered, an arc missed.
    r = run_smoke(specs["branchmiss"])
    want("branchmiss: func_ok is True", r["func_ok"] is True, r["func_ok"])
    want("branchmiss: no changed line is uncovered (line coverage is 100%)",
         r["uncovered_changed"] == [], r["uncovered_changed"])
    want("branchmiss: a changed-line branch arc is untaken", len(r["changed_missing_branches"]) >= 1,
         r["changed_missing_branches"])
    want("branchmiss: n_fail >= 1 from the branch dimension alone", r["n_fail"] >= 1, r["n_fail"])

    r = run_smoke(specs["clean"])
    want("clean: func_ok is True", r["func_ok"] is True, r["func_ok"])
    want("clean: no uncovered changed lines", r["uncovered_changed"] == [], r["uncovered_changed"])
    want("clean: no missing changed-line branch arcs", r["changed_missing_branches"] == [],
         r["changed_missing_branches"])
    want("clean: n_fail == 0", r["n_fail"] == 0, r["n_fail"])

    # every fixture emitted a marker (never MARKER_ABSENT).
    for kind, s in specs.items():
        v, _ = classify(pes.smoke_gate_runner(s))
        want("marker present for fixture %s (verdict %s)" % (kind, v), v != MARKER_ABSENT, v)

    # ---- 3. changed-line SOURCES -----------------------------------------------------
    print("\n-- changed-line source checks --")
    # explicit fallback (the CCRT payload is not a git repo).
    want("explicit changed_lines used verbatim",
         derive_changed_lines("/nonexistent.py", explicit=[5, 3, 5, 9]) == [3, 5, 9])
    # unknown changed-set -> hard FAIL, never a silent empty pass.
    raised = False
    try:
        derive_changed_lines("/tmp/not_a_repo_file.py", repo_root="/tmp")
    except CannotScopeDiff:
        raised = True
    want("no git + no explicit -> CannotScopeDiff (no vacuous empty set)", raised)
    # empty changed-set is itself a fail inside run_smoke (certifying coverage over nothing).
    r = run_smoke({"name": "empty", "target_path": specs["clean"]["target_path"],
                   "changed_lines": [], "driver_body": specs["clean"]["driver_body"]})
    want("empty changed-set -> n_fail >= 1 (vacuous-pass guard)", r["n_fail"] >= 1, r["n_fail"])
    want("empty changed-set -> a SCOPE problem is reported",
         any("SCOPE" in p for p in r["problems"]), r["problems"])

    # a REAL git work tree: derive_changed_lines parses the diff.
    git_ok = _git_diff_roundtrip(want)

    # ---- 1. the vloop_harness fixture-pair contract ----------------------------------
    print("\n-- vloop_harness registry verdict --")
    register_smoke_gate(specs, target="sci_library_curate.py::check_i17 (I16-I19 port)")
    rep = run_fixture_pair(GATE_NAME)
    from vloop_harness import verify_registry
    reg = verify_registry([GATE_NAME])
    print("  gate verdict:", rep["verdict"])
    for p in rep.get("problems", []):
        print("    -", p)
    want("registry fixture-pair verdict is PASS", rep["verdict"] == "PASS", rep.get("problems"))
    want("registry aggregate verdict is PASS", reg["verdict"] == "PASS")

    print("\n=== SUMMARY ===")
    print("NON-EXERCISING FIXTURE FAILED AS REQUIRED:", NONEXERCISING_FAILED)
    print("git-mode diff derivation exercised:", git_ok)
    verdict = "PASS" if not fails else "FAIL"
    if fails:
        print("FAILURES:")
        for f in fails:
            print("  -", f)
    print("TEST VERDICT:", verdict)
    return 0 if verdict == "PASS" else 2


def _git_diff_roundtrip(want):
    """Create a throwaway git repo, commit a file, edit two lines, and confirm
    derive_changed_lines recovers exactly those new-side line numbers from the diff."""
    if not shutil_which("git"):
        want("git available for diff-mode test", False, "git not on PATH")
        return False
    d = tempfile.mkdtemp(prefix="smoke_git_")
    try:
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        run = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, env=env)
        run("init", "-q")
        fp = os.path.join(d, "m.py")
        open(fp, "w").write("def f(x):\n    return x\n\ndef g(y):\n    return y\n")
        run("add", "-A"); run("commit", "-qm", "base")
        # edit line 2 and add a new line 5 area.
        open(fp, "w").write("def f(x):\n    return x + 1\n\ndef g(y):\n    z = y * 2\n    return z\n")
        changed = derive_changed_lines(fp, repo_root=d)
        # new-side changed lines: line 2 (edited), lines 5-6 (added). Exact set may include 5,6.
        ok = 2 in changed and any(n in changed for n in (5, 6))
        want("git-mode: derive_changed_lines parses the diff hunks (got %s)" % changed, ok, changed)
        return ok
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def shutil_which(name):
    import shutil
    return shutil.which(name)


if __name__ == "__main__":
    sys.exit(main())
