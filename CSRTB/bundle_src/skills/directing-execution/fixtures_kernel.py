#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""fixtures_kernel.py -- red/green fixtures for the two-receipts stop gate in kernel.py.

RUN SEPARATELY from any suite:  python3 fixtures_kernel.py
Exit 0 = every fixture behaved; non-zero = the gate misbehaved on at least one.

WHY THESE SHAPES (the real recorded instance, not token bad cases)
FAILURE_CLASS_LOG SEED-19, arc=55710d86 «Map Claude Science Data Storage Locations»
msg 5349: a lead STOPPED running children the user wanted finished, then stated the
child had saved nothing -- BEFORE checking. Recovery found the artifacts existed. Two
receipts were absent at the stop moment, and the fixtures below walk exactly that
cross-product: neither receipt (a), intent-but-unread (b), read-but-unauthorized (c),
both (d). (a)-(c) are RED -- the gate MUST refuse. (d) is GREEN -- the corrected shape
the recovery produced, which the gate MUST let through, so a gate that simply refuses
everything is caught here rather than in the field.

(e)/(f) are supplementary and cover the escape hatch the gate itself introduces: the
"child produced no artifacts: <how verified>" declaration. (e) is the msg-5349
mischaracterisation verbatim in shape -- the bare assertion with no check named -- and
must FAIL; (f) names the check and must PASS. An untested escape hatch is a hole in the
gate, so it is exercised here even though it is not one of the four required cases.

(g)-(j) harden three DEFENSIVE branches the four-case cross-product never reaches, each RED
and each the gate MUST refuse: a placeholder intent token ('n/a'/'tbd') dressed up as a
reference (g,h), a read-path artifact summary too thin to be evidence it was read (i), and
an unnamed/empty child -- an unattributable stop (j). A closing MUTANT-CHECK then proves
those fixtures have TEETH: it disables each branch in a FRESH in-memory kernel (the shipped
kernel.py is never touched) and confirms the matching fixture flips GREEN -- so a fixture
that silently stopped exercising its branch is caught here, not in the field.

A suite-green with no shown RED run is not evidence: the transcript below prints the
observed verdict + marker for every case so the refusals are visible, not inferred.
"""
import importlib.util
import os
import re
import sys
import types

# Importing the kernel by path would drop a __pycache__/ INTO the shipped skill dir. The
# builder's is_ignorable() filters it out of the bundle, but it is still cruft in the
# source tree -- so a fixture run leaves no trace.
sys.dont_write_bytecode = True

# ------------------------------------------------------------------ module under test
_HERE = os.path.dirname(os.path.abspath(__file__))
MODULE_PATH = os.environ.get("DIRECTING_KERNEL_MODULE", os.path.join(_HERE, "kernel.py"))


def load_kernel(path=None):
    """Load the REAL shipped kernel by path (name != __main__, so its CLI never fires)."""
    path = path or MODULE_PATH
    if not os.path.exists(path):
        raise SystemExit("kernel not found: %s (set DIRECTING_KERNEL_MODULE to override)" % path)
    spec = importlib.util.spec_from_file_location("directing_kernel_uut", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MARKER_SHAPE = re.compile(r"^\[\[stop_gate child=\S+ verdict=(PASS|FAIL)\]\]$")

# ------------------------------------------------------------------ the fixtures
CHILD = "fid_55710d86_storage-map-scan"

FIXTURES = [
    {
        "id": "a", "phase": "RED",
        "label": "stop with NO recorded user intent and NO artifacts read",
        "why": "SEED-19 msg 5349 verbatim shape -- the stop as it actually happened",
        "case": {"child": CHILD, "user_intent_ref": None, "artifacts_read": None},
        "verdict": "FAIL", "missing": {"user_intent_ref", "artifacts_read"},
    },
    {
        "id": "b", "phase": "RED",
        "label": "user intent recorded, but the child's artifacts were never read",
        "why": "the authorized-but-unchecked stop: intent is real, the loss claim is not",
        "case": {
            "child": CHILD,
            "user_intent_ref": "arc=55710d86 msg 5344 -- user: 'stop the storage scan, we have enough'",
            "artifacts_read": None,
        },
        "verdict": "FAIL", "missing": {"artifacts_read"},
    },
    {
        "id": "c", "phase": "RED",
        "label": "artifacts read, but no recorded user intent authorizing the stop",
        "why": "the unilateral stop -- the director's own impulse, not the user's ask",
        "case": {
            "child": CHILD,
            "user_intent_ref": None,
            "artifacts_read": [
                "art_9f21_storage_paths.csv -- 412 rows: artifact/workspace/tool-result paths per org",
                "art_9f22_scan_notes.md -- what the scan covered and the 3 dirs it could not reach",
            ],
        },
        "verdict": "FAIL", "missing": {"user_intent_ref"},
    },
    {
        "id": "d", "phase": "GREEN",
        "label": "both receipts present -- the corrected shape the recovery produced",
        "why": "the gate must PASS a receipted stop, or it is a blanket refusal, not a gate",
        "case": {
            "child": CHILD,
            "user_intent_ref": "arc=55710d86 msg 5344 -- user: 'stop the storage scan, we have enough'",
            "artifacts_read": [
                "art_9f21_storage_paths.csv -- 412 rows: artifact/workspace/tool-result paths per org",
                {"id": "art_9f22_scan_notes.md",
                 "summary": "what the scan covered and the 3 dirs it could not reach"},
            ],
        },
        "verdict": "PASS", "missing": set(),
    },
    {
        "id": "e", "phase": "RED",
        "label": "supplementary -- bare 'no artifacts' assertion with no check named",
        "why": "msg 5349's mischaracterisation: 'it saved nothing' asserted before checking",
        "case": {
            "child": CHILD,
            "user_intent_ref": "arc=55710d86 msg 5344 -- user: 'stop the storage scan, we have enough'",
            "artifacts_read": "child produced no artifacts: none",
        },
        "verdict": "FAIL", "missing": {"artifacts_read"},
    },
    {
        "id": "f", "phase": "GREEN",
        "label": "supplementary -- 'no artifacts' declared WITH how it was verified",
        "why": "the escape hatch must stay usable when the check was genuinely run",
        "case": {
            "child": CHILD,
            "user_intent_ref": "PLAN_planner_upgrade §2.2 -- stop authorized once the scan is superseded",
            "artifacts_read": ("child produced no artifacts: host.frames(fid_55710d86) shows "
                               "artifacts_created == [] and the workspace ls is empty"),
        },
        "verdict": "PASS", "missing": set(),
    },
    {
        "id": "g", "phase": "RED",
        "label": "placeholder user intent ('n/a') masquerading as a reference",
        "why": "a placeholder token in the intent slot is the un-receipted stop in disguise",
        "case": {
            "child": CHILD,
            "user_intent_ref": "n/a",
            "artifacts_read": [
                "art_9f21_storage_paths.csv -- 412 rows: artifact/workspace/tool-result paths per org",
                "art_9f22_scan_notes.md -- what the scan covered and the 3 dirs it could not reach",
            ],
        },
        "verdict": "FAIL", "missing": {"user_intent_ref"},
        "reason_contains": ["placeholder"],
    },
    {
        "id": "h", "phase": "RED",
        "label": "placeholder user intent ('tbd') -- the same branch, a second spelling",
        "why": "the placeholder set must reject the whole family, not just the one token 'n/a'",
        "case": {
            "child": CHILD,
            "user_intent_ref": "tbd",
            "artifacts_read": [
                "art_9f21_storage_paths.csv -- 412 rows: artifact/workspace/tool-result paths per org",
                "art_9f22_scan_notes.md -- what the scan covered and the 3 dirs it could not reach",
            ],
        },
        "verdict": "FAIL", "missing": {"user_intent_ref"},
        "reason_contains": ["placeholder"],
    },
    {
        "id": "i", "phase": "RED",
        "label": "artifact listed, but its summary is too thin to be a read-receipt",
        "why": "a bare 'read' is the pointer-without-evidence the read-path minimum exists to reject",
        "case": {
            "child": CHILD,
            "user_intent_ref": "arc=55710d86 msg 5344 -- user: 'stop the storage scan, we have enough'",
            "artifacts_read": [
                "art_9f21_storage_paths.csv -- read",
            ],
        },
        "verdict": "FAIL", "missing": {"artifacts_read"},
        "reason_contains": ["too thin"],
    },
    {
        "id": "j", "phase": "RED",
        "label": "the child being stopped is unnamed (empty) -- an unattributable stop",
        "why": "an unnamed target cannot have had ITS artifacts read, and its marker is untraceable",
        "case": {
            "child": "",
            "user_intent_ref": "arc=55710d86 msg 5344 -- user: 'stop the storage scan, we have enough'",
            "artifacts_read": [
                "art_9f21_storage_paths.csv -- 412 rows: artifact/workspace/tool-result paths per org",
                "art_9f22_scan_notes.md -- what the scan covered and the 3 dirs it could not reach",
            ],
        },
        "verdict": "FAIL", "missing": {"child"},
        "reason_contains": ["not named"],
    },
    {
        "id": "m", "phase": "RED",
        "label": "declared-none CONTRADICTED by an actual artifact entry in the same list",
        "why": "a 'child produced no artifacts' declaration alongside a real artifact read is "
               "incoherent -- one of the two receipts is wrong; gutting the escape-hatch pattern "
               "(NO_ARTIFACTS_PATTERN) makes the declaration invisible and this case slip (found "
               "by independent verify-loop probe 2026-07-28)",
        "case": {
            "child": "c1",
            "user_intent_ref": "arc=55710d86 msg 5344 -- user authorized the stop",
            "artifacts_read": [
                "child produced no artifacts: verified via frames",
                "out.csv - 300 rows, spot-checked",
            ],
        },
        "verdict": "FAIL", "missing": {"artifacts_read"},
        "reason_contains": [],
    },
]


# ------------------------------------------------------------------ per-fixture checks
def check_one(kern, fx):
    """Return (ok, [complaint, ...], result). Never raises on a bad gate -- it reports."""
    bad = []
    try:
        res = kern.confirm_before_stop(**fx["case"])
    except Exception as exc:
        return False, ["gate RAISED in library use (%s: %s) -- it must return a verdict dict"
                       % (type(exc).__name__, exc)], None
    if not isinstance(res, dict):
        return False, ["gate returned %s, expected a result dict" % type(res).__name__], None

    got_verdict = res.get("verdict")
    if got_verdict != fx["verdict"]:
        bad.append("verdict %r != expected %r" % (got_verdict, fx["verdict"]))
    got_missing = set(res.get("missing") or [])
    if got_missing != fx["missing"]:
        bad.append("missing %s != expected %s" % (sorted(got_missing), sorted(fx["missing"])))

    marker = res.get("marker") or ""
    m = MARKER_SHAPE.match(marker)
    if not m:
        bad.append("marker %r does not match [[stop_gate child=<name> verdict=...]]" % marker)
    elif m.group(1) != got_verdict:
        bad.append("marker verdict %r disagrees with result verdict %r" % (m.group(1), got_verdict))

    if got_verdict == "FAIL":
        if not res.get("reasons"):
            bad.append("FAIL carries no reason")
        for name in fx["missing"]:
            if not any(str(r).startswith(name) for r in res.get("reasons") or []):
                bad.append("FAIL reasons do not name the missing receipt %r" % name)
        for needle in fx.get("reason_contains", []):
            if not any(needle in str(r) for r in res.get("reasons") or []):
                bad.append("FAIL reasons never mention %r -- the defensive branch is not named"
                           % needle)
        if kern.STANDING_INSTRUCTION not in (res.get("report") or ""):
            bad.append("FAIL report omits the standing instruction %r" % kern.STANDING_INSTRUCTION)
    else:
        if res.get("reasons"):
            bad.append("PASS carries reasons: %s" % res["reasons"])

    if kern.stop_gate_verdict(res.get("report") or "") != got_verdict:
        bad.append("marker does not round-trip through stop_gate_verdict()")
    return (not bad), bad, res


def check_structural(kern):
    """Reviewer-side properties that are not per-case: absence is not a pass, and a
    marker quoted inside prose is documentation, not an emission."""
    bad = []
    if kern.stop_gate_verdict("I stopped the child and moved on. No gate was run.") != "MARKER_ABSENT":
        bad.append("a stopping span with no marker must read MARKER_ABSENT, not a pass")
    quoted = 'the gate emits `[[stop_gate child=x verdict=PASS]]` when both receipts land'
    if kern.stop_gate_verdict(quoted) != "MARKER_ABSENT":
        bad.append("a quoted marker in prose must not read as an emission")
    try:
        kern.require_confirm_before_stop(CHILD)
        bad.append("require_confirm_before_stop() did not raise on a no-receipt stop")
    except AssertionError:
        pass
    return (not bad), bad


# ------------------------------------------------------------------ mutant check (teeth)
# A RED fixture earns its transcript line only if it would go GREEN against a BROKEN gate.
# For each newly covered defensive branch, load a FRESH kernel with exactly that branch
# disabled -- ONE surgical, in-memory edit; the shipped kernel.py on disk is never touched --
# and confirm the matching fixture FLIPS: the receipt the real gate flags is no longer flagged
# by the mutant. A mutation whose string is not found (source drifted) or a fixture that does
# NOT flip is itself a misbehavior -- a toothless fixture is a silent hole in the gate.
_BY_ID = {f["id"]: f for f in FIXTURES}

MUTANTS = [
    {"branch": "placeholder-intent rejection", "receipt": "user_intent_ref", "case_id": "g",
     "old": "return normalize_(text) in PLACEHOLDER_TOKENS", "new": "return False"},
    {"branch": "read-path thin-summary minimum", "receipt": "artifacts_read", "case_id": "i",
     "old": "MIN_SUMMARY_CHARS = 8", "new": "MIN_SUMMARY_CHARS = 0"},
    {"branch": "unnamed-child guard", "receipt": "child", "case_id": "j",
     "old": "if not child_txt or is_placeholder_(child_txt):", "new": "if False:"},
    {"branch": "no-artifacts escape-hatch (declared-none detection)", "receipt": "artifacts_read", "case_id": "m",
     "old": 'NO_ARTIFACTS_PATTERN = r"^\\s*child\\s+produced\\s+no\\s+artifacts\\s*:\\s*(.+)$"',
     "new": 'NO_ARTIFACTS_PATTERN = r"(?!x)x"'},
]


def _load_mutant(path, old, new):
    """Exec a fresh kernel with ONE edit, entirely in memory. Returns (module, applied); applied
    is False when the edit string is absent (a mutation that does not mutate = a vacuous check).
    __name__ is 'directing_kernel_mutant', so the module's `__main__` CLI guard never fires."""
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    mutant = src.replace(old, new, 1)
    if mutant == src:
        return None, False
    mod = types.ModuleType("directing_kernel_mutant")
    mod.__file__ = path
    exec(compile(mutant, path, "exec"), mod.__dict__)
    return mod, True


def check_mutants(kern, path):
    """Prove each new RED fixture pins its own branch: real gate flags the receipt, mutant does not."""
    bad = []
    for mt in MUTANTS:
        case = _BY_ID[mt["case_id"]]["case"]
        real = kern.confirm_before_stop(**case)
        if mt["receipt"] not in (real.get("missing") or []):
            bad.append("%s: the REAL gate did not flag %r -- fixture %s is not exercising this branch"
                       % (mt["branch"], mt["receipt"], mt["case_id"]))
            continue
        mod, applied = _load_mutant(path, mt["old"], mt["new"])
        if not applied:
            bad.append("%s: mutation string %r not found -- kernel.py drifted, teeth check is vacuous"
                       % (mt["branch"], mt["old"]))
            continue
        mut = mod.confirm_before_stop(**case)
        if mt["receipt"] in (mut.get("missing") or []):
            bad.append("%s: disabling the branch did NOT flip fixture %s (%r still flagged) -- no teeth"
                       % (mt["branch"], mt["case_id"], mt["receipt"]))
    return (not bad), bad


# ------------------------------------------------------------------ transcript
def main():
    kern = load_kernel()
    print("=" * 78)
    print("two-receipts stop gate (SEED-19) -- red/green fixtures, run standalone")
    print("module : %s" % MODULE_PATH)
    print("=" * 78)

    failures = 0
    for fx in FIXTURES:
        ok, bad, res = check_one(kern, fx)
        print("")
        print("[%-5s %s] %s" % (fx["phase"], fx["id"], fx["label"]))
        print("        why      : %s" % fx["why"])
        print("        child    : %s" % (fx["case"].get("child") or "<empty/unnamed>"))
        print("        intent   : %s" % (fx["case"]["user_intent_ref"] or "<none supplied>"))
        arts = fx["case"]["artifacts_read"]
        print("        artifacts: %s" % (arts if arts else "<none supplied>"))
        print("        expect   : %s, missing=%s" % (fx["verdict"], sorted(fx["missing"]) or "[]"))
        if res is None:
            print("        observed : <no result>")
        else:
            print("        observed : %s, missing=%s" % (res.get("verdict"),
                                                         sorted(res.get("missing") or [])))
            print("        marker   : %s" % res.get("marker"))
            head = (res.get("reasons") or [res["receipts"]["artifacts_read"]["detail"]])[0]
            print("        reason   : %s" % head)
        print("        RESULT   : %s" % ("ok" if ok else "MISBEHAVED"))
        for b in bad:
            print("                   ! %s" % b)
        failures += 0 if ok else 1

    ok, bad = check_structural(kern)
    print("")
    print("[STRUCT  ] marker-absence is not a pass; quoted marker is not an emission; "
          "strict wrapper raises")
    print("        RESULT   : %s" % ("ok" if ok else "MISBEHAVED"))
    for b in bad:
        print("                   ! %s" % b)
    failures += 0 if ok else 1

    ok, bad = check_mutants(kern, MODULE_PATH)
    print("")
    print("[MUTANT  ] each new RED fixture flips GREEN when its OWN defensive branch is disabled")
    print("        RESULT   : %s" % ("ok" if ok else "MISBEHAVED"))
    for b in bad:
        print("                   ! %s" % b)
    failures += 0 if ok else 1

    print("")
    print("=" * 78)
    n = len(FIXTURES) + 2
    print("%d/%d checks behaved as specified (%d RED refusals, %d GREEN passes)"
          % (n - failures, n, sum(1 for f in FIXTURES if f["phase"] == "RED"),
             sum(1 for f in FIXTURES if f["phase"] == "GREEN")))
    print("VERDICT: %s" % ("GATE OK" if not failures else "GATE MISBEHAVED"))
    print("=" * 78)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
