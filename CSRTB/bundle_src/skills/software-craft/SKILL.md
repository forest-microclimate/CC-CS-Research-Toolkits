---
name: software-craft
description: The build discipline for research software — invoke WHEN about to implement, extend, or restructure code (a pipeline, module, CLI, analysis script) so the result is correct-by-construction and checkable. Owns spec-before-code (the 5-line contract), semantic-tests-with-the-code, reproduce-baseline-before-extend, interface/dependency hygiene, and the measure-before-optimizing protocol. Fires on "implement/build/write this pipeline/module/script", "extend this code", "port this". NOT the fixture/verification contract (→ testing-discipline), NOT invariant re-derivation on a structural change (→ refactoring), NOT reviewing finished code (→ CODE_REVIEW_DEBUGGER profile).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-28). Authored in the software-developer pass; the inline-loadable half of that agent's discipline (skills serve the main agent too — the discipline binds whoever writes code, delegated or not).

# software-craft — build it so correctness is checkable

## When to invoke
WHEN about to write or extend non-trivial code — anything beyond a one-liner: a script with steps, a module, a pipeline stage, a CLI. Also WHEN handed a build brief and deciding whether it is buildable as specified.

## The contract-first move (the load-bearing habit)
WHEN the task lacks a written contract => write the **5-line contract** BEFORE any code, and build against it:
1. INPUTS — what arrives, with types/units/coordinate conventions named (tz, height, id-as-character…).
2. OUTPUTS — what is produced, where it lands (exact paths), at what resolution (finest — never pre-aggregated at write time).
3. INVARIANTS — the semantic properties that must hold (conservation identities, monotonicity, row-count relations, value ranges).
4. FAILURE MODES — what can go wrong and what the code DOES then (fail loudly; a sentinel/clamp that hides a crash is not handling).
5. PROOF — the observable that shows it worked (the check a reviewer can re-run).
A request too vague to contract ⇒ a question back to the requester, not a guess (ambiguous verbs — "clean", "fill", "fix" — are the recorded rework generator).

## Build rules
- SEMANTIC TESTS SHIP WITH THE CODE — checks that would catch the wrong-but-running version (invariants from the contract, per-step bounds AND running totals for accumulating quantities, join-on-key-never-positional). The fixture/verification contract itself — red-before-green, real-defect fixtures — is owned by `testing-discipline`; load it when authoring the checks.
- REPRODUCE BASELINE BEFORE EXTEND — WHEN modifying working code => reproduce its current output first (hash/number-identical), gate your extension on the match, and understand WHY it works before changing it.
- INTERFACES SMALL, DEPENDENCIES EXPLICIT — no silent globals; one concern per function/cell; pure core + thin I/O edge where feasible (pure parts are the testable parts); deterministic re-runs (seed where randomness enters; record versions).
- VALIDATE ON A MINIMAL INTERACTIVE STEP before any batch/full run; save outputs at the finest resolution, as artifacts (`save_artifacts` — a file another cell or session reads must be a saved artifact, never workspace-only).
- OPTIMIZE ONLY WHAT YOU MEASURED — profile first; language-specific performance/correctness traps live in `julia-performance-correctness` (Julia: BLAS threads, precompile races) and the R statistical-computing standards the toolkit carries (bam-vs-gamm, silent-failure patterns — e.g. via `mgcv-temporal-gam` / `brms-hierarchical-fitting`) — reach for those, do not re-derive.
- ONE VARIABLE PER TEST CYCLE while iterating; keep scratch/diagnostics out of the deliverable artifact set (workspace scratch is fine; only deliverables get saved as artifacts).

## Handoff
A substantial or high-consequence build ends with an adversarial review by a FRESH party (CODE_REVIEW_DEBUGGER, verify-loop topology) — the author's own green suite is not certification. State in the deliverable what was NOT verified.

REF: `testing-discipline` (the check contract) · `refactoring` (structural changes) · `julia-performance-correctness` · `provenance-guard` (every input feeding a durable output is a tracked artifact) · the falsify-first debugging discipline (reproduce an anomaly at baseline before building fixes).
