#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""fixtures_assert_gate.py -- standalone red/green + mutation runner for
verify_before_assert (provenance-guard kernel.py, the SEED-01 gate).

Run directly:  python3 fixtures_assert_gate.py
Exit 0 = every fixture behaved as specified; non-zero = a fixture MISBEHAVED.

Kept SEPARATE from any suite (testing-discipline: a fixture that reproduces a recorded
defect runs on its own so a suite-level green cannot mask it). Each case is RED (must
return verdict=FAIL) or GREEN (must return verdict=PASS). The mutation block proves each
guard is LOAD-BEARING (neuter it -> the matching red flips green) with the SHIPPED
kernel.py left untouched (only the in-memory module attribute is reassigned).

Recorded defects reproduced BY ID (not strawmen):
  RED-1  SEED-01 assert-from-recollection -- frame 45171f5d, msg 514/624: three artifact
         version-ids invented from memory (source_read_ref "memory"/"").
  RED-2  a fact whose ref is not among this turn's reads (the stronger mode).
"""
import importlib.util
import os
import sys


def load_kernel():
    """Import the sibling kernel.py as a MODULE (not exec-as-__main__), so its __main__
    guard never fires and ASSERT_PLACEHOLDER_REFS is monkeypatchable. kernel.py is
    stdlib-only at module scope, so this needs no pandas/pyarrow."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "kernel.py")
    spec = importlib.util.spec_from_file_location("provenance_guard_kernel", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── recorded fixtures ─────────────────────────────────────────────────────────
# RED-1: the SEED-01 confession shape -- three version-ids invented from memory.
SEED01_FACTS = [
    {"claim": "artifact version_id for guild_additive_modelframe",
     "value": "ver_9f3a1c", "source_read_ref": "memory"},
    {"claim": "artifact version_id for canopy_energy_fit",
     "value": "ver_2b77e0", "source_read_ref": "memory"},
    {"claim": "artifact version_id for flux_partition_frame",
     "value": "ver_c14d55", "source_read_ref": ""},
]

# RED-2: a real-looking ref that is NOT among this turn's reads (strong mode).
NOTINREADS_FACTS = [
    {"claim": "row count of the merged model frame",
     "value": 12840, "source_read_ref": "read of frame_B.parquet"},
]
NOTINREADS_READS = ["read of frame_A.parquet", "read of frame_C.parquet"]

# GREEN: real refs, incl. the tricky "read of memory_map.json" -- contains the substring
# "memory" but is NOT the placeholder token, so it must PASS. Valid in BOTH modes.
GREEN_FACTS = [
    {"claim": "row count of the model frame",
     "value": 4096, "source_read_ref": "read of memory_map.json"},
    {"claim": "artifact id feeding figure 3",
     "value": "art_88f2", "source_read_ref": "execution_log id 45171f5d cell 12"},
]
GREEN_READS = ["read of memory_map.json", "execution_log id 45171f5d cell 12"]


def _check(results, label, kind, result, expect_named=None):
    """Record one fixture outcome. kind='RED' expects verdict FAIL, 'GREEN' expects PASS.
    expect_named: substrings that must EACH appear in the failures (proves a red NAMES
    each offending fact)."""
    want = "FAIL" if kind == "RED" else "PASS"
    got = result["verdict"]
    verdict_ok = (got == want)
    named_ok = True
    missing = []
    if expect_named:
        blob = repr(result.get("failures"))
        for token in expect_named:
            if token not in blob:
                named_ok = False
                missing.append(token)
    ok = verdict_ok and named_ok
    results.append(ok)
    print("  [%-5s] %-46s expect=%-4s got=%-4s %s  %s"
          % (kind, label, want, got, result["marker"],
             "OK" if ok else "*** MISBEHAVED ***"))
    if not verdict_ok:
        print("        verdict mismatch: wanted %s, got %s" % (want, got))
    if not named_ok:
        print("        failures did not name: %s" % ", ".join(missing))
    return ok


def main():
    k = load_kernel()
    results = []
    kpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kernel.py")
    print("fixtures_assert_gate -- verify_before_assert (SEED-01 gate)")
    print("kernel: %s" % kpath)
    print("shipped ASSERT_PLACEHOLDER_REFS = %s" % sorted(k.ASSERT_PLACEHOLDER_REFS))

    print("\n-- RED cases (each MUST return verdict=FAIL) --")
    # RED-1: SEED-01 confession, weaker mode (the agent had NO this-turn reads; it recalled).
    r1 = k.verify_before_assert(SEED01_FACTS)                       # reads=None
    _check(results, "SEED-01 confession (frame 45171f5d msg514/624)", "RED", r1,
           expect_named=["ver_9f3a1c", "ver_2b77e0", "ver_c14d55"])
    # RED-2: ref not among the provided this-turn reads (stronger mode).
    r2 = k.verify_before_assert(NOTINREADS_FACTS, reads=NOTINREADS_READS)
    _check(results, "ref not in this-turn reads (strict mode)", "RED", r2,
           expect_named=["read of frame_B.parquet"])

    print("\n-- GREEN cases (each MUST return verdict=PASS) --")
    # GREEN presence-only (reads=None): real refs, the weaker mode passes.
    g0 = k.verify_before_assert(GREEN_FACTS)
    _check(results, "real refs, presence-only mode", "GREEN", g0)
    # GREEN strict: same refs, all present among this-turn reads (incl. memory_map.json).
    g1 = k.verify_before_assert(GREEN_FACTS, reads=GREEN_READS)
    _check(results, "real refs incl memory_map.json, strict mode", "GREEN", g1)
    # Vacuous: empty facts -> PASS, n=0, flagged vacuous.
    g2 = k.verify_before_assert([])
    vac_ok = (g2["verdict"] == "PASS" and g2["n"] == 0 and g2["vacuous"] is True)
    results.append(vac_ok)
    print("  [%-5s] %-46s expect=%-4s got=%-4s %s  %s"
          % ("GREEN", "vacuous (empty facts), n=0", "PASS", g2["verdict"], g2["marker"],
             "OK" if vac_ok else "*** MISBEHAVED ***"))

    print("\n-- MUTATION spot-checks (prove each guard is load-bearing; "
          "shipped kernel.py untouched) --")
    # MUT-A -- the placeholder-set constant the spec names. Empty it IN MEMORY; the
    # SEED-01 confession (governed ONLY by that set, reads=None) must flip to PASS.
    orig = k.ASSERT_PLACEHOLDER_REFS
    try:
        k.ASSERT_PLACEHOLDER_REFS = frozenset()
        m1 = k.verify_before_assert(SEED01_FACTS)
    finally:
        k.ASSERT_PLACEHOLDER_REFS = orig
    mutA_ok = (m1["verdict"] == "PASS")
    results.append(mutA_ok)
    print("  [%-5s] %-46s neutered->PASS got=%-4s  %s"
          % ("MUT-A", "placeholder-set := frozenset() flips RED-1", m1["verdict"],
             "OK" if mutA_ok else "*** MISBEHAVED ***"))
    # Confirm the shipped constant was restored -- RED-1 must be red again, and the
    # on-disk file was never touched (we only reassigned the in-memory attribute).
    restored = k.verify_before_assert(SEED01_FACTS)
    restore_ok = (restored["verdict"] == "FAIL" and k.ASSERT_PLACEHOLDER_REFS == orig)
    results.append(restore_ok)
    print("  [%-5s] %-46s restored->FAIL got=%-4s  %s"
          % ("MUT-A", "shipped set restored, RED-1 red again", restored["verdict"],
             "OK" if restore_ok else "*** MISBEHAVED ***"))
    # MUT-B -- the SECOND guard's operand is the INJECTED `reads`, not a module constant.
    # Withdraw it (reads=None) and RED-2 must flip to PASS, proving the not-in-reads FAIL
    # genuinely depended on that guard and not on the placeholder set.
    m2 = k.verify_before_assert(NOTINREADS_FACTS)                   # reads=None
    mutB_ok = (m2["verdict"] == "PASS")
    results.append(mutB_ok)
    print("  [%-5s] %-46s reads:=None->PASS got=%-4s  %s"
          % ("MUT-B", "withdraw reads flips RED-2", m2["verdict"],
             "OK" if mutB_ok else "*** MISBEHAVED ***"))

    passed = sum(1 for x in results if x)
    total = len(results)
    print("\n%d/%d fixtures behaved as specified." % (passed, total))
    if passed != total:
        print("RESULT: *** MISBEHAVED *** -- a fixture did not match its spec.")
        return 1
    print("RESULT: all red cases fired, all green cases passed, both guards shown "
          "load-bearing; shipped kernel.py untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
