# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""Red-team fixtures for the verification-loop emit-time gates (DISC-07 + DISC-18).

Standalone: `python3 fixtures_new_gates.py` (add -v for failure detail). No test
framework, and run SEPARATELY from any suite -- a suite-green with no shown red
run is not evidence (a check never seen failing cannot be trusted). Does NOT
import or touch the shipped delegation-planning fixtures.

Every RED fixture reproduces a REAL recorded confession shape:
  b* require_receipt              DISC-07 verification-theater, arc=55710d86 msg=5222:
                                  "'BYTE-IDENTICAL' asserted ... the probe compared only
                                  file size and four row counts -- no hash or byte comparison"
  c* require_verification_status  DISC-18 efficacy-from-existence, arc=6544bef8 msg=840:
                                  a just-written rule recorded as "a solution that worked";
                                  user: "NO! it is an attempted solution that has NOT YET
                                  BEEN THOROUGHLY TESTED" -> the verification_status field
(The sibling SEED-01 gate verify_before_assert lives in provenance-guard, with its
own fixtures -- not reproduced here.)

ATTRIBUTION, not just verdict: each red fixture also asserts WHICH check fired
(and, for the receipt gate, WHICH token). gate(known_bad) == FAIL is necessary,
not sufficient.

MUTATION (m*): monkeypatch-and-restore. Gut ONE guard constant in the in-memory
kernel module (the shipped file on disk is untouched and restored in a finally),
run the SHIPPED gate on the recorded red input, and prove the gutted gate now
PASSES it (so the red fixture WOULD catch a regression that removed the guard)
while the real gate FAILS it. That pairing is what makes the red fixture a real
test of THAT guard rather than of incidental malformation.

EXIT 0 only when every fixture behaves: no RED passing, no GREEN failing, every
attribution holding, and every mutation surviving-then-caught.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kernel  # noqa: E402  -- module object, for monkeypatching guard constants
from kernel import require_receipt, require_verification_status  # noqa: E402

VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv


# ─── attribution assertions (a FAIL for the wrong reason is a wrong fixture) ──
def _expect_check(check_id, token=None):
    """The named check must fire; optionally it must name the given token."""
    def _fn(result):
        hits = [f for f in result["failures"] if f.get("check") == check_id]
        if not hits:
            return "expected a %r failure; got %s" % (
                check_id, sorted({f.get("check") for f in result["failures"]}))
        if token is not None:
            toks = set()
            for f in hits:
                toks |= set(f.get("tokens") or [])
            if token not in toks:
                return "%s should name token %r; named %s" % (
                    check_id, token, sorted(toks))
        return ""
    return _fn


def _expect_vacuous(result):
    """A no-token receipt claim must PASS *and* be flagged vacuous (visible, not
    laundered as an ordinary green)."""
    if not result.get("vacuous"):
        return "expected vacuous=True (no verification token was claimed)"
    return ""


# ─── runner ──────────────────────────────────────────────────────────────────
def run(fid, kind, label, result, expect, extra=None):
    """Print one fixture's transcript line. -> True when the fixture behaved."""
    got = result["verdict"]
    ok = (got == expect)
    why = "" if ok else "verdict %s, expected %s" % (got, expect)
    if ok and extra is not None:
        why = extra(result) or ""
        ok = not why
    print("[%-5s] %-3s %-56s expect=%-4s got=%-4s %-5s %s"
          % (kind, fid, label[:56], expect, got, "ok" if ok else "WRONG", result["marker"]))
    if VERBOSE or not ok:
        for f in result.get("failures", [])[:4]:
            print("          - [%s] %s" % (f.get("check"), f.get("detail")))
    if not ok:
        print("          !! %s" % why)
    return ok


def mutation_check(fid, label, gate_fn, const_pairs, red_input, cite):
    """Gut kernel.<name> for every (name, gutted_value) pair in memory, run the
    SHIPPED gate on the recorded red input, and require it now PASSES (mutation
    survives => the red fixture would catch a regression that removed this guard);
    restore in finally; then require the real gate FAILS the same input.
    -> True when both hold. Pairs (not a single const) because the 2026-07-28
    sidecar-contract transform split compiled constants into a literal PATTERNS
    dict + a lazy CACHE — gutting must empty BOTH or a warm cache masks the gut."""
    if isinstance(const_pairs, tuple):
        const_pairs = [const_pairs]
    originals = [(n, getattr(kernel, n)) for n, _v in const_pairs]
    try:
        for n, v in const_pairs:
            setattr(kernel, n, v)
        gutted = gate_fn(*red_input)["verdict"]
    finally:
        for n, orig in originals:
            setattr(kernel, n, orig)                   # shipped file never touched
    restored_ok = all(getattr(kernel, n) is orig for n, orig in originals)
    real = gate_fn(*red_input)["verdict"]
    ok = (gutted == "PASS" and real == "FAIL" and restored_ok)
    print("[MUT  ] %-3s %-56s gutted=%-4s real=%-4s %-5s %s"
          % (fid, label[:56], gutted, real, "ok" if ok else "WRONG", cite))
    if not ok:
        print("          !! expected gutted=PASS (red fixture would catch the gutted "
              "gate) & real=FAIL & constant-restored; got gutted=%s real=%s restored=%s"
              % (gutted, real, restored_ok))
    return ok


def main():
    print("=== verification-loop new gates -- red-team fixtures (DISC-07 + DISC-18) ===")
    print("    RED = must FAIL (reproduces a recorded confession)   GREEN = must PASS")
    print("    MUT = gut one guard: gutted gate must PASS the red input, real must FAIL\n")
    r = []

    # ── (b) require_receipt -- DISC-07 verification-theater (arc=55710d86 msg=5222) ──
    r.append(run("b1", "RED", "receipt . 'byte-identical' claim, receipts=[] (msg 5222)",
                 require_receipt("live A is byte-identical to the undo point", []),
                 "FAIL", _expect_check("no-receipt", token="byte-identical")))
    r.append(run("b2", "GREEN", "receipt . 'verified' backed by a real exit_code:0 receipt",
                 require_receipt("exit code verified", [{"kind": "exit_code", "value": "0"}]),
                 "PASS"))
    r.append(run("b3", "GREEN", "receipt . no verification token -> vacuous PASS",
                 require_receipt("we chose X because it reads cleaner", []),
                 "PASS", _expect_vacuous))
    r.append(run("b4", "RED", "receipt . 'confirmed' with an invalid-kind receipt",
                 require_receipt("all three confirmed", [{"kind": "vibes", "value": "trust me"}]),
                 "FAIL", _expect_check("no-receipt", token="confirmed")))
    r.append(run("b5", "GREEN", "receipt . 'byte-identical' backed by a hash receipt",
                 require_receipt("the two files are byte-identical",
                                 [{"kind": "hash", "value": "sha256:22fa5981b035"}]),
                 "PASS"))
    r.append(run("b6", "RED", "receipt . 'all 5 passed' claim, no receipt",
                 require_receipt("all 5 passed", []),
                 "FAIL", _expect_check("no-receipt", token="all-N-passed")))

    # ── (c) require_verification_status -- DISC-18 efficacy-from-existence (msg=840) ──
    r.append(run("c1", "RED", "vstatus . 'verified-working', no citation (msg 840)",
                 require_verification_status(
                     {"claim": "the gate works", "verification_status": "verified-working"}),
                 "FAIL", _expect_check("citation")))
    r.append(run("c2", "GREEN", "vstatus . same claim tagged attempted-untested",
                 require_verification_status(
                     {"claim": "the gate works", "verification_status": "attempted-untested"}),
                 "PASS"))
    r.append(run("c3", "GREEN", "vstatus . verified-working WITH a cited measurement",
                 require_verification_status(
                     {"claim": "the gate works", "verification_status": "verified-working",
                      "citation": "fixtures_new_gates.py b1: red FAILs, gutted PASSes"}),
                 "PASS"))
    r.append(run("c4", "RED", "vstatus . missing verification_status field",
                 require_verification_status({"claim": "the gate works"}),
                 "FAIL", _expect_check("status")))
    r.append(run("c5", "RED", "vstatus . bogus status token ('works-great')",
                 require_verification_status(
                     {"claim": "x", "verification_status": "works-great"}),
                 "FAIL", _expect_check("status")))

    # ── mutation checks (monkeypatch-and-restore; shipped kernel.py untouched) ──
    print()
    r.append(mutation_check(
        "m1", "receipt . gut PATTERNS+CACHE -> the byte-identical red slips",
        require_receipt, [("RECEIPT_TOKEN_PATTERNS", {}), ("RECEIPT_TOKEN_RES_CACHE", {})],
        ("live A is byte-identical to the undo point", []),
        "DISC-07 arc=55710d86 msg=5222"))
    r.append(mutation_check(
        "m2", "vstatus . gut VSTATUS_REQUIRE_CITATION -> the uncited red slips",
        require_verification_status, [("VSTATUS_REQUIRE_CITATION", frozenset())],
        ({"claim": "the gate works", "verification_status": "verified-working"},),
        "DISC-18 arc=6544bef8 msg=840"))

    n, bad = len(r), r.count(False)
    print("\n--- %d fixtures run separately: %d behaved, %d MISBEHAVED" % (n, n - bad, bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
