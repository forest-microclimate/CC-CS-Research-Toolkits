---
name: refactoring
description: The structural-change procedure — invoke WHEN a change dissolves or replaces a core abstraction (a dichotomy, data structure, coordinate/"currency", aggregation level, shared assumption), WHEN a subsystem has accumulated ~3+ patches to the same area (the recurring-patch-saga tell), or WHEN tempted to add a mirror-knob or bracket-search a threshold. Owns the re-derive-the-invariants checkpoint, the old-currency grep, and unify-over-parallel-patch. The HOW behind rules/refactor-invariants.machine.md (the rule fires; this skill executes). NOT the build discipline (-> software-craft) and NOT symptom debugging (-> code-review-debugger agent + rules/root-before-bandaid).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-28). Authored in the software-developer pass. Operationalizes rules/refactor-invariants.machine.md as a runnable procedure — the rule owns the always-on TELLS; this owns the steps.

# refactoring — replace the mental model wholesale, never patch its ghost

## When to invoke
WHEN a planned change dissolves/replaces a core abstraction · WHEN you notice the recurring-patch saga (~3+ thresholds/skips/special-cases into one subsystem) · WHEN a "new knob mirroring an existing knob" or a value-bracket search is on the table (a structural question mis-framed as tuning) · BEFORE a rename/restructure that many call-sites depend on.

## The checkpoint (run AT the refactor, or the moment a tell fires)
1. NAME the OLD abstraction and what it special-cased or guaranteed, and for WHICH subset of members.
2. NAME the NEW structure replacing it.
3. FOR EACH old special-case/guarantee/piece of machinery ask: "under the new structure, which members does this now apply to?" — usually MORE or ALL. Re-apply UNIFORMLY; enumerate, don't sample.
4. GREP THE OLD CURRENCY — every residual use of the pre-refactor variable/name/coordinate is a candidate artifact (a gate still written in the old variable while the solve moved on is the classic residue). List hits; disposition each (migrate / delete / justify).
5. RE-BASELINE: reproduce the pre-change output first (hash it), make the structural change, attribute every diff to an intended consequence. An unexplained diff is a missed invariant, not noise.
6. UPDATE THE DOCS/TESTS THAT ENCODED THE OLD MODEL in the same change (a test asserting the old invariant will either false-fail or, worse, false-pass forever).

## Decision rules
- UNIFY OVER PARALLEL-PATCH: WHEN an edge case tempts a new parallel mechanism/knob => extend the sibling mechanism to cover it instead; a mirror-knob is the tell that the structure, not the tuning, is wrong.
- A recurring-patch saga ⇒ STOP adding patch #4; audit the whole subsystem against steps 1–4 (the saga is symptoms of ONE un-propagated change).
- Renames: never leave both names live ("absent from grep" must mean absent — a half-rename creates two currencies); keep cross-references intact (widely-referenced filenames keep their names, content converts in place).

REF: `rules/refactor-invariants.machine.md` (the always-on trigger + the exemplar case) · `software-craft` (baseline-before-extend, the same move at smaller scale) · `testing-discipline` (the checks that re-encode the NEW invariants) · `rules/root-before-bandaid.machine.md` (the sibling on the symptom side).
