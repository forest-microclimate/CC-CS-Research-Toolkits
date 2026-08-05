#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""vloop_harness.py -- the verify-the-embed harness (VLOOP Item 2's substrate).

WHY THIS EXISTS
The improvement plan validates every loop it builds with "verify-the-embed": run the
check and confirm it fired. The adversarial review's deepest finding was that this was
itself an exhortation -- "confirm it fires" names no output-detectable predicate, so an
agent eyeballing a transcript and judging "it seems to have checked" reproduces the exact
efficacy-from-existence failure the plan exists to close. This module makes the meta-check
mechanical.

THE THREE VERDICTS (the distinction that makes this non-vacuous)
A check's output resolves to exactly one of:
  MARKER_ABSENT  -- no [[vloop:...]] marker at all. The check did NOT run (or ran and
                    emitted nothing). This is NOT a pass. Conflating it with "0 failures"
                    is the false-green this harness is built to prevent.
  CLEAN          -- marker present with n_fail == 0.
  DEFECTS        -- marker present with n_fail >= 1.

THE FIXTURE-PAIR CONTRACT
A gate is only trusted once it has BOTH:
  known_bad   -- reproduces the historical defect that motivated the gate (cite the
                 lesson/frame id), and there is >= 1 known_bad per defect CLASS the gate
                 claims to catch. `gate(known_bad) == FAIL` is necessary, not sufficient:
                 a trivial bad case passes that test while the real condition persists
                 (the orphan gate reported 0 of 5,154).
  known_clean -- the gate must NOT fire on it (guards against a gate that fails everything,
                 which would also satisfy the known_bad test).
A registered gate MISSING either fixture is itself a FAIL -- an unfixtured gate cannot
silently escape by never being tested.

USAGE
  from vloop_harness import (emit_marker, parse_markers, GATES, register_gate,
                             run_fixture_pair, verify_registry, selftest)
EXIT (as a script): 0 = PASS, 2 = FAIL.
"""
import json
import os
import re
import sys

MARKER_RE = re.compile(
    r"\[\[vloop:(?P<name>[A-Za-z0-9_.\-]+)"
    r"(?P<kv>(?:\s+[a-z_]+=-?\d+)*)"
    r"\s*\]\]"
)
_KV_RE = re.compile(r"([a-z_]+)=(-?\d+)")

MARKER_ABSENT = "MARKER_ABSENT"
CLEAN = "CLEAN"
DEFECTS = "DEFECTS"


def emit_marker(name, n_claims, n_fail, **extra):
    """Render the machine-detectable tell. This exact string is what
    verify-the-embed greps for -- a check that does not emit it is, by
    definition, unverifiable."""
    if not re.fullmatch(r"[A-Za-z0-9_.\-]+", str(name) or ""):
        raise ValueError("marker name must be [A-Za-z0-9_.-]+, got %r" % (name,))
    parts = ["n_claims=%d" % int(n_claims), "n_fail=%d" % int(n_fail)]
    for k in sorted(extra):
        parts.append("%s=%d" % (k, int(extra[k])))
    return "[[vloop:%s %s]]" % (name, " ".join(parts))


def parse_markers(text, name=None, ignore_quoted=True):
    """Find every marker in `text`. Returns a list of dicts
    {name, n_claims, n_fail, ...extra, raw, offset}.

    ignore_quoted borrows provenance-guard's pg_marker_hit insight: a marker
    immediately preceded by a quote character is string DATA (e.g. this very
    docstring, or a spec that mentions the format) and is NOT a real emission.
    Without this, a module that merely DOCUMENTS the marker format would appear
    to have emitted one."""
    out = []
    if not text:
        return out
    for m in MARKER_RE.finditer(text):
        i = m.start()
        if ignore_quoted and i > 0 and text[i - 1] in ("'", '"', "`"):
            continue
        rec = {"name": m.group("name"), "raw": m.group(0), "offset": i}
        for k, v in _KV_RE.findall(m.group("kv") or ""):
            rec[k] = int(v)
        if name is None or rec["name"] == name:
            out.append(rec)
    return out


def classify(text, name=None):
    """-> (verdict, marker_or_None). The three-way verdict, never a bare bool."""
    ms = parse_markers(text, name=name)
    if not ms:
        return MARKER_ABSENT, None
    # If a check emitted several markers, any defect dominates.
    worst = max(ms, key=lambda r: r.get("n_fail", 0))
    if worst.get("n_fail") is None:
        return MARKER_ABSENT, None
    return (DEFECTS if worst["n_fail"] >= 1 else CLEAN), worst


# --------------------------------------------------------------------------
# GATES registry -- makes "every gate" a deterministic, enumerable set.
# --------------------------------------------------------------------------
GATES = {}


def register_gate(name, runner, known_bad, known_clean, defect_classes,
                  motivating_evidence, target=None):
    """Register a gate + its REQUIRED fixture pair.

    runner(fixture) -> str : the gate's output text (must contain a marker)
    known_bad       : {defect_class: fixture} -- one per class the gate claims
    known_clean     : a single fixture the gate must NOT fire on
    defect_classes  : the classes this gate claims to catch (>=1 fixture each)
    motivating_evidence : the frame/lesson id of the real defect that motivated it
    """
    if not callable(runner):
        raise TypeError("runner must be callable")
    if not defect_classes:
        raise ValueError("a gate must declare >=1 defect class")
    GATES[name] = {
        "name": name, "runner": runner, "known_bad": dict(known_bad or {}),
        "known_clean": known_clean, "defect_classes": list(defect_classes),
        "motivating_evidence": motivating_evidence, "target": target,
    }
    return GATES[name]


def run_fixture_pair(name):
    """Execute a gate against its whole fixture set. Returns a result dict with
    an explicit `verdict`; a gate that greens on its own known-bad, fires on its
    known-clean, or emits no marker at all, FAILS."""
    g = GATES.get(name)
    if g is None:
        return {"gate": name, "verdict": "FAIL",
                "problems": ["gate %r is not registered" % name]}
    problems, detail = [], {}

    # Contract: fixtures must exist, and cover every declared defect class.
    missing_classes = [c for c in g["defect_classes"] if c not in g["known_bad"]]
    if missing_classes:
        problems.append("no known-bad fixture for declared defect class(es): %s"
                        % ", ".join(missing_classes))
    if not g["known_bad"]:
        problems.append("NO known-bad fixture -- an unfixtured gate cannot be trusted")
    if g["known_clean"] is None:
        problems.append("NO known-clean fixture -- cannot rule out a gate that fails "
                        "everything")

    for cls, fx in sorted(g["known_bad"].items()):
        try:
            out = g["runner"](fx)
        except Exception as exc:                                  # noqa: BLE001
            problems.append("known_bad[%s] raised %s: %s" % (cls, type(exc).__name__, exc))
            detail[cls] = {"verdict": "ERROR"}
            continue
        verdict, mk = classify(out)
        detail[cls] = {"verdict": verdict, "marker": (mk or {}).get("raw")}
        if verdict == MARKER_ABSENT:
            problems.append("known_bad[%s]: NO MARKER emitted -- the check did not "
                            "demonstrably run (this is not a pass)" % cls)
        elif verdict == CLEAN:
            problems.append("known_bad[%s]: gate reported n_fail==0 on a PLANTED DEFECT "
                            "-- FALSE GREEN" % cls)

    if g["known_clean"] is not None:
        try:
            out = g["runner"](g["known_clean"])
            verdict, mk = classify(out)
            detail["__clean__"] = {"verdict": verdict, "marker": (mk or {}).get("raw")}
            if verdict == MARKER_ABSENT:
                problems.append("known_clean: NO MARKER emitted -- cannot distinguish "
                                "'checked and clean' from 'never ran'")
            elif verdict == DEFECTS:
                problems.append("known_clean: gate FIRED on a clean fixture -- false "
                                "positive, so its known-bad pass proves nothing")
        except Exception as exc:                                  # noqa: BLE001
            problems.append("known_clean raised %s: %s" % (type(exc).__name__, exc))

    return {"gate": name, "verdict": "FAIL" if problems else "PASS",
            "problems": problems, "detail": detail,
            "defect_classes": g["defect_classes"],
            "motivating_evidence": g["motivating_evidence"]}


def verify_registry(names=None):
    """Run every registered gate's fixture pair. Fail-closed aggregate."""
    todo = list(GATES) if names is None else list(names)
    results = [run_fixture_pair(n) for n in sorted(todo)]
    failed = [r for r in results if r["verdict"] != "PASS"]
    return {"n_gates": len(results), "n_failed": len(failed),
            "verdict": "FAIL" if failed else "PASS", "results": results}


def print_registry_report(rep):
    print("GATES registry -- %d gate(s)" % rep["n_gates"])
    for r in rep["results"]:
        print("  [%s] %s  (classes: %s)"
              % (r["verdict"], r["gate"], ", ".join(r.get("defect_classes") or [])))
        for p in r.get("problems") or []:
            print("      - %s" % p)
    print("\nREGISTRY VERDICT: %s%s"
          % (rep["verdict"], "" if rep["verdict"] == "PASS"
             else " (%d gate(s) failed)" % rep["n_failed"]))


# --------------------------------------------------------------------------
# SELF-TEST -- verify-the-verifier applied to this harness itself.
# --------------------------------------------------------------------------
def selftest(verbose=True):
    """The harness must FAIL a broken check. If it greens on any of these, the
    harness is not trustworthy and nothing gated on it means anything."""
    cases, fails = [], []

    def check(label, cond, got=None):
        cases.append((label, bool(cond), got))
        if not cond:
            fails.append("%s (got %r)" % (label, got))

    # --- marker round-trip
    s = emit_marker("demo", 5, 2)
    check("emit->parse round-trip", parse_markers(s) and parse_markers(s)[0]["n_fail"] == 2, s)
    check("emit rejects a bad name", _raises(lambda: emit_marker("bad name!", 1, 0)))

    # --- the three verdicts are distinguished
    check("no marker -> MARKER_ABSENT", classify("nothing here")[0] == MARKER_ABSENT)
    check("n_fail=0 -> CLEAN", classify(emit_marker("g", 3, 0))[0] == CLEAN)
    check("n_fail=1 -> DEFECTS", classify(emit_marker("g", 3, 1))[0] == DEFECTS)
    check("MARKER_ABSENT is not CLEAN", MARKER_ABSENT != CLEAN)

    # --- quoted markers are string data, not emissions
    check("quoted marker ignored", classify('the format is "%s"' % emit_marker("g", 1, 1))[0]
          == MARKER_ABSENT)

    # --- a marker missing n_fail must not read as clean
    check("marker without n_fail -> MARKER_ABSENT",
          classify("[[vloop:g n_claims=4]]")[0] == MARKER_ABSENT)

    # --- name filtering
    check("name filter selects", len(parse_markers(emit_marker("a", 1, 0) + emit_marker("b", 1, 1),
                                                   name="b")) == 1)

    # --- registry behaviour against deliberately broken gates
    snapshot = dict(GATES)
    try:
        GATES.clear()

        register_gate("good", lambda fx: emit_marker("good", 2, 1 if fx == "bad" else 0),
                      {"cls1": "bad"}, "clean", ["cls1"], "selftest")
        check("a correct gate PASSes", run_fixture_pair("good")["verdict"] == "PASS",
              run_fixture_pair("good")["problems"])

        register_gate("silent", lambda fx: "ran, all good",
                      {"cls1": "bad"}, "clean", ["cls1"], "selftest")
        r = run_fixture_pair("silent")
        check("a gate emitting NO MARKER fails", r["verdict"] == "FAIL", r["problems"])
        check("  ...and says the check did not demonstrably run",
              any("NO MARKER" in p for p in r["problems"]))

        register_gate("falsegreen", lambda fx: emit_marker("falsegreen", 2, 0),
                      {"cls1": "bad"}, "clean", ["cls1"], "selftest")
        r = run_fixture_pair("falsegreen")
        check("a gate MISSING its planted defect fails", r["verdict"] == "FAIL")
        check("  ...and names it a FALSE GREEN",
              any("FALSE GREEN" in p for p in r["problems"]))

        register_gate("trigger_happy", lambda fx: emit_marker("trigger_happy", 2, 3),
                      {"cls1": "bad"}, "clean", ["cls1"], "selftest")
        r = run_fixture_pair("trigger_happy")
        check("a gate that fires on the CLEAN fixture fails", r["verdict"] == "FAIL")

        register_gate("nofixture", lambda fx: emit_marker("nofixture", 1, 1),
                      {}, None, ["cls1"], "selftest")
        r = run_fixture_pair("nofixture")
        check("an UNFIXTURED gate fails (cannot silently escape)", r["verdict"] == "FAIL")
        check("  ...for both missing fixtures",
              sum(1 for p in r["problems"] if "NO known" in p) == 2, r["problems"])

        register_gate("underclaimed", lambda fx: emit_marker("underclaimed", 1, 1),
                      {"cls1": "bad"}, "clean", ["cls1", "cls2"], "selftest")
        r = run_fixture_pair("underclaimed")
        check("a gate claiming a class with no fixture fails", r["verdict"] == "FAIL")

        register_gate("exploder", lambda fx: (_ for _ in ()).throw(RuntimeError("boom")),
                      {"cls1": "bad"}, "clean", ["cls1"], "selftest")
        check("a raising gate fails rather than escaping",
              run_fixture_pair("exploder")["verdict"] == "FAIL")

        check("registry aggregate is FAIL when any gate fails",
              verify_registry()["verdict"] == "FAIL")
        check("registry aggregate is PASS for only-good",
              verify_registry(["good"])["verdict"] == "PASS")
    finally:
        GATES.clear()
        GATES.update(snapshot)

    if verbose:
        for label, ok, _got in cases:
            if not ok:
                print("  FAIL %s" % label)
        print("harness self-test: %d/%d checks pass" % (len(cases) - len(fails), len(cases)))
    return {"n_checks": len(cases), "n_failed": len(fails), "failures": fails,
            "verdict": "PASS" if not fails else "FAIL"}


def _raises(fn):
    try:
        fn()
    except Exception:                                             # noqa: BLE001
        return True
    return False


if __name__ == "__main__":
    r = selftest()
    print("\nSELFTEST VERDICT:", r["verdict"])
    for f in r["failures"]:
        print("  - %s" % f)
    sys.exit(0 if r["verdict"] == "PASS" else 2)
