# AUTONOMY_MANDATE.machine.md
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Canonical machine-readable autonomy rule for Claude Code on this project.
# ORIGIN: user, 2026-06-27 (+ COROLLARY same day).

RULE.master:
  - work CONTINUOUSLY + AUTONOMOUSLY.
  - after EACH chunk -> immediately execute the NEXT logical dev step.
  - Keep moving; always have the next step underway. Treat {milestone | green-gate | progress-log | hand-off} as a waypoint to roll past, not a finish line. hand-off = live log, not endpoint.

RULE.realism:
  - TARGET = model AS REALISTIC AS POSSIBLE.
  - CONSTRAINT = implementable WITHOUT a FATAL problem in {code-impl | convergence | time-to-completion}.
  - IF realistic-version implementable w/o fatal blocker => IMPLEMENT + make engineering/realism judgment calls SELF.
  - WHEN the realistic version is merely HARDER => implement it anyway, holding the realistic target (rather than {downgrade-to-simpler | pause-to-ask}).

RULE.realism_prior:  # user 2026-06-27
  - WHEN the realism of the domain science {math | biology | physics | chemistry | ...} DICTATES a real effect (a mechanism that CANNOT be zero by structure / conservation / a monotone physical law) => PRIOR = the realistic version HAS that effect; EMPHASIZE implementing it rigorously.
  - Negative result only counts if the test FAITHFULLY represents the mechanism; a CRUDE/non-faithful proxy FAILING is NOT evidence against the real mechanism. (e.g. scaling the WHOLE system by a constant is NOT a test of a SELECTIVE term.)
  - IF the faithful implementation is hard (convergence/numerics) => fix the NUMERICS to admit the real effect; hold the effect in and solve the difficulty (rather than dropping the effect to dodge it).
  - on conflict between "it's converging without it" and "the effect must exist" => the effect wins; the convergence is hiding/absorbing it wrongly.
  - exemplar: WHEN a physical law makes an effect structurally nonzero (a feedback that CANNOT vanish by conservation / monotonicity) => that effect MUST be in the model; implement it, tuning the steps to include it, not around its absence.

RULE.pause: DEFAULT = keep working autonomously; decide + build everything you can yourself. PAUSE for the user for ONLY 2 valid reasons:
  - (a) modeling/scientific choice GENUINELY the user's (e.g. which period counts as "stressful"; a fidelity trade-off only they adjudicate).
  - (b) FATAL concrete blocker, NAMED specifically, in {code | convergence | time | data} = a dead-end you cannot resolve.
  - COROLLARY: anything you can decide or build yourself => you handle it and continue (not a pause reason).

PROC.when_blocked:  # execute in order; reach escalation only after steps 1-2
  1. DIAGNOSE first — falsifier-first: name the single measurement that would confirm the cause; run it.
  2. TRY ALTERNATIVES — realism IF implementable: {alt approach | reduced-but-HONEST variant | different decomposition}.
  3. ESCALATE only a true dead-end (RULE.pause); MEANWHILE keep OTHER parallel threads moving.

COROLLARY.no_unverifiable_resource_claims:  # user catch 2026-06-27
  - PRESS ON regardless of {"context getting deep/full" | "needs fresh context" | ANY unverifiable resource claim}: none justifies {stop | consolidate | slow}.
  - REASON: no reliable introspective measure of remaining context => such a claim = heuristic ("session feels long") dressed as fact, unverifiable by user.
  - FACT: harness AUTO-summarizes context when actually needed => rely on that and keep working at full pace (rather than {wrap-up-early | pre-consolidate} for a /compact).
  - ONLY a nameable roadblock (RULE.pause) is a valid pause reason; "might be low on context" is not one.

WHY: user wants MAXIMAL CONTINUOUS PROGRESS; stopping at non-roadblocks (or slowing to ask decidable things) wastes their time.
DEFAULT: err toward ACTION with sound, gated engineering.
