# refactor-invariants.machine.md  (machine-optimized; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# RULE: when a change DISSOLVES/REPLACES a core abstraction, RE-DERIVE the full invariant set under the NEW structure — REPLACE the old mental model wholesale, rather than carrying it and patching its pieces as symptoms surface.
# ORIGIN: user, 2026-07-01 — named as the cause of some of the most frustrating + intractable slow-downs across MANY sessions/projects. Cross-project ⇒ lives at the global rules level.

RULE.rederive_on_refactor: a change that DISSOLVES or REPLACES a core abstraction (a dichotomy, a data structure, a coordinate / "currency", a level of aggregation, a shared assumption) => the HIGHEST-VALUE + most-often-SKIPPED step is to RE-DERIVE the full invariant / machinery set under the NEW structure. Anything the OLD abstraction special-cased or guaranteed for a SUBSET now applies to a DIFFERENT (usually LARGER / ALL) set of members — enumerate them and re-apply UNIFORMLY. ADOPT the re-derived (new-structure) model in full, rather than keeping the old one and patching its pieces one symptom at a time.

WHY: patching-symptoms-of-a-dissolved-abstraction is a RECURRING, HIGH-COST failure — each patch fixes ONE surfacing symptom while the root (old-"currency" machinery living in a new-"currency" world) keeps generating fresh ones ⇒ a long debug/convergence "saga" that never converges because it is chasing symptoms of ONE un-propagated change. Exemplar: a refactor that DISSOLVED a binary layer dichotomy (sun/shade) into per-unit CONTINUOUS fractions; months of convergence patches (skips, thresholds, coupling fixes, a gate still written in the OLD variable) were largely symptoms of that one un-propagated refactor.

TELLS (output-DETECTABLE — the only reliable triggers; abstract "think structurally" does NOT fire):
  - RECURRING-PATCH SAGA: ~3+ patches (thresholds / skips / special-cases / stabilizers) to the SAME subsystem over a stretch ⇒ STOP; suspect a dissolved abstraction not fully propagated; AUDIT the whole subsystem rather than adding patch #4. (This is the strongest tell — the saga itself is the signal.)
  - OLD-CURRENCY quantity: a gate / check / weight / index still written in the PRE-refactor variable while the state/solve moved to the NEW one (e.g. the gate reads the PRE-refactor variable but the solve now uses the POST-refactor one) ⇒ grep EVERY use of the old variable; each is a candidate artifact.
  - MIRROR-knob / value-BRACKET: symptom-level tells of the same root — a new knob "mirroring" an existing one, or a search over threshold values, means a structural question got mis-framed as tuning.

CHECKPOINT (run AT the refactor, or the moment a TELL fires): (1) name the OLD abstraction + what it special-cased/guaranteed; (2) name the NEW structure that replaced it; (3) for EACH old special-case / piece of machinery / invariant, ask "under the new structure, which members does this now apply to?" (usually MORE / all) and re-apply uniformly; (4) grep the old-currency variable for residual gates.

CAVEAT (LLM limits): no reliable introspection or self-modification ⇒ this rule REDUCES (not eliminates) recurrence, and only if it is LOADED and a TELL actually fires. Hence the TELLS are phrased as detectable output-states, not exhortations.

REF: verification-principles.md (verify-don't-assume); doc-style.machine.md (style). Symptom-level companion: handle an edge case by UNIFYING with the sibling mechanism, not a parallel tuned knob — a mirror-knob or a value-bracket search = a structural question mis-framed as tuning.
