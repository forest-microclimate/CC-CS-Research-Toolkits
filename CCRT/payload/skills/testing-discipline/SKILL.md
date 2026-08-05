---
name: testing-discipline
description: The check-and-fixture contract — invoke WHEN authoring tests, fixtures, validators, or any gate/assertion, and WHEN about to cite a passing check as evidence. Owns red-before-green (a check must be SHOWN able to fail), fixtures-reproduce-the-REAL-defect (run separately from suites), mutation spot-checks for load-bearing gates, semantic-not-type assertions, and per-step + running-total validation for accumulating quantities. Fires on "write tests for this", "add a validator/gate", "is this green trustworthy", "build a fixture". NOT the build discipline itself (-> software-craft) and NOT reviewing code (-> code-review-debugger agent).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-28). Authored in the software-developer pass. Generalizes the failure-corpus testing contract (DISC-04 false-green, SEED-02 fixture-fitting) from toolkit gates to ALL research code.

# testing-discipline — a green light is only evidence if the check can go red

## When to invoke
WHEN writing tests/validators/assertions for any code; WHEN building a fixture for a gate or bug; WHEN about to report "tests pass" as evidence of correctness.

## The contract (each rule is a recorded failure inverted)
- RED BEFORE GREEN. A check you have never seen FAIL is a check you cannot trust. WHEN authoring any check => first run it against an input that violates the property (the red case), show it fires, THEN show the clean case passes. A validator that emits PASS without a demonstrated failing case is the false-green class — the green light itself becomes the bug.
- FIXTURES REPRODUCE THE REAL DEFECT. A fixture written to match your own probe certifies the fixture, not the behaviour. WHEN a fixture exists to catch a known/observed defect => build it from the RECORDED instance (the actual bad input/shape), not a strawman; run it SEPARATELY from the suite so a suite-level pass cannot mask it.
- MUTATION SPOT-CHECK for load-bearing gates. WHEN a check guards something important => disable/weaken its core branch in a scratch copy and confirm the fixtures go red. Fixtures that stay green against a gutted check are fixture-fitted. (Cheap: one mutation per load-bearing branch.)
- SEMANTIC, NOT TYPE. Assert the properties that distinguish right from wrong-but-running: value ranges, conservation/accounting identities, expected row/record counts, coordinate-key identity after joins (`merge` on key, then assert key equality — never positional pairing), units. `stopifnot()`/`assert` on the SEMANTIC property.
- ACCUMULATING QUANTITIES get BOTH checks: the per-step bound AND the running total (a per-step check alone lets drift through; a total alone hides which step broke).
- SCOPE THE CLAIM TO THE CHECK. "Tests pass" means exactly what the tests test. WHEN reporting => name what the suite does NOT cover; an uncovered failure class is not certified by an unrelated green.
- SAVE what re-verification needs: test outputs/fit objects/per-row predictions to disk, so diagnosing a later failure does not force a re-run.

## Anti-patterns (each fires a stop)
A suite that only ever went green since birth · a fixture authored by editing until the gate passed · asserting "verified/byte-identical/all-passed" without the receipt (hash, diff, exit code) in hand · deleting a failing test to ship · testing the mock so thoroughly the real path is never exercised.

REF: `software-craft` (the build side) · `rules/reproduce-before-fixing.machine.md` (falsify the premise first — the debugging twin of red-before-green) · `rules/about-to-author-a-data-rule.machine.md` (efficacy is a measurement, not an authoring-time assertion) · the toolkit's own gate fixtures (tests/test_*.sh, the hooks' red/green batteries) for the house marker/fixture pattern.
