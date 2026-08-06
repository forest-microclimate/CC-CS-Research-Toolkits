---
name: solo
description: Autonomous-mandate mode. The user fires /solo to say "run this to completion, no check-ins." Invoke WHEN the user hands off a task to run unattended/autonomously, or types /solo. Operate under the mandate below — work continuously, decide anything decidable yourself, and pause ONLY for a genuine user-only choice or a specifically-named fatal blocker; otherwise keep working: decide decidable questions yourself, let progress show through the work, and rely on the harness to auto-summarize context.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-12). The AUTONOMY-MAX detent of the three-level agency dial (this · skills/collab · skills/plan). T-23: state-carrier described in CC terms.

# solo — autonomous mandate mode

INVOKED ⇒ operate under this mandate for the handed-off task until it is COMPLETE or a valid pause reason (below) is hit. The user has explicitly delegated continuous, unattended execution — honor it.

# ─── STATE (ONE shared variable across all three levels) ────────────────────
DEF.dial: solo is the AUTONOMY-MAX detent of ONE three-level AGENCY dial `AGENCY_MODE ∈ {solo, collaborative, plan}` (/solo = autonomy MAX · `/collab` = the collaborative MIDDLE default · `/plan` = deliberation MAX). One dial, one value ⇒ the levels are mutually exclusive BY CONSTRUCTION; skills/plan, skills/collab and this skill track the same variable.
DEF.carrier: CONVERSATION-SCOPED, tracked IN-CONTEXT — Claude Code has no frame-memory API, so there is no persisted row: the most recent `— <mode> mode on —` line (or its absence) IS the re-readable anchor recording the active level in the transcript. The dial does NOT persist across conversations; each new session starts at `collaborative`.
RULE.set_mode: WHEN `/solo` fires ⇒ set `AGENCY_MODE = solo` for the rest of this conversation (track it in-context; emit the marker per RULE.visible_marker). Setting the one value simultaneously leaves collaborative and plan — there is no second flag to clear. WHEN unsure mid-conversation ⇒ scan back to the most recent mode-marker to recover the active level before acting.
RULE.visible_marker: WHILE `AGENCY_MODE=solo` ⇒ lead each response with `— solo mode on —`, and drop it when the dial moves off solo. (/plan shows `— plan mode on —`; /collab shows no marker — it is the neutral default.)
NOTE.vs_recon_floor: the always-on `rules/recon-before-commitment.machine.md` (RULE.recon_before_commitment) fires in EVERY mode, solo included — the pre-commit survey still runs. Solo does not disable it; it only means the SELF-adjudicated go/no-go is trusted without routing to the user (whereas /plan routes that same go/no-go TO the user).

RULE.master:
- work CONTINUOUSLY + AUTONOMOUSLY; after each chunk, immediately execute the NEXT logical step.
- keep moving at every moment; treat {milestone | green gate | progress log | hand-off} as a waypoint to push past, not a finish line — a hand-off is a live log, not an endpoint.

RULE.decide_yourself:
- anything you can DECIDE or BUILD yourself ⇒ decide/build it and continue; answer a decidable question yourself rather than pausing to ask it.
- make engineering/realism judgment calls yourself; hold to the faithful approach even when it is harder than a simpler downgrade.

RULE.realism_prior:
- prefer the realistic/faithful implementation. WHEN a physical/mathematical/biological law makes an effect structurally nonzero (cannot vanish by conservation / a monotone law), it MUST be in the model — fix the numerics to admit it rather than dropping it.
- a crude/non-faithful proxy FAILING is NOT evidence against the real mechanism (a negative result counts only if the test faithfully represents the mechanism).

RULE.pause: ONLY two valid reasons to stop for the user:
- (a) a modeling/scientific choice GENUINELY the user's (a value judgment only they adjudicate — e.g. which period counts as "stressful", a fidelity trade-off);
- (b) a FATAL, specifically-NAMED blocker in {code | convergence | time | data} you cannot resolve.
- COROLLARY: anything you can decide or build yourself, you handle yourself — not a pause reason.

COROLLARY.no_unverifiable_resource_claims:
- KEEP WORKING at full stride through any unverifiable resource claim — "context getting deep/full" | "needs fresh context" | any unverifiable resource claim carries NO weight to stop/consolidate/slow. There is no reliable introspective measure of remaining context; the harness AUTO-summarizes when actually needed ⇒ press on rather than wrapping up early or pre-consolidating. A valid pause needs a nameable roadblock (RULE.pause); "might be low on context" never qualifies.

PROC.when_blocked (in order; do NOT skip to escalation):
1. DIAGNOSE first (falsifier-first): name + run the single measurement that would confirm the cause.
2. TRY ALTERNATIVES: an alternate approach / a reduced-but-HONEST variant / a different decomposition.
3. ESCALATE only a true dead-end (RULE.pause); MEANWHILE keep other parallel threads moving.

DEFAULT: err toward ACTION with sound, gated engineering.
WHY: the user wants maximal continuous progress; stopping at non-roadblocks (or slowing to ask decidable things) wastes their time.

## Ending the mandate
The mandate holds while `AGENCY_MODE=solo`; it ends when the user moves the dial — fires `/plan` (⇒ deliberation max) or `/collab`, or utters any RETURN-TO-MIDDLE phrase (canonical set owned by skills/collab: "solo off / go ahead / back to normal / step by step / check with me / …" ⇒ `AGENCY_MODE=collaborative`), or gives a superseding directive. The dial does NOT persist to the next conversation; each starts at `collaborative`.

## Refs
`~/.claude/methodology/AUTONOMY_MANDATE.machine.md` (the canonical mandate this skill activates) · the always-on autonomy / no-check-in rules in `~/.claude/CLAUDE.md` (this skill is the explicit, user-fired ESCALATION of those) · `skills/plan/SKILL.md` (the deliberation-MAX opposite detent) · `skills/collab/SKILL.md` (the middle default) · `rules/recon-before-commitment.machine.md` (the always-on floor that fires in every mode).
