---
name: collab
description: Collaborative mode — the MIDDLE default of the agency dial, between /solo (autonomy max) and /plan (deliberation max). Fire /collab to say "back to normal working — surface the non-trivial calls, but don't gate every step." Invoke WHEN the user types /collab, says "collab / back to normal / let's work together / solo off / plan off", or asks to return to ordinary collaboration from either pole. This is the neutral resting level: no continuous-autonomy mandate, no per-step user gate — the standard interactive default every conversation starts at.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# collab — collaborative mode (the middle default of the agency dial)

INVOKED ⇒ set the dial to its neutral middle level. `/collab` is the MIDDLE detent of a single three-level AGENCY dial: `/solo` = autonomy MAX (decide everything yourself, never check in) · `/collab` = collaborative MIDDLE (this) · `/plan` = deliberation MAX (gate every scope-defining step for the user). It is where you RETURN to from either pole — the standard interactive disposition, and the level every fresh conversation starts at.

# ─── STATE (ONE shared variable across all three levels) ────────────────────
DEF.dial: the three levels are ONE frame-memory variable `AGENCY_MODE ∈ {solo, collaborative, plan}` — the SAME row read/written by skills solo, this skill, and plan. One variable holds one value ⇒ the levels are mutually exclusive by construction ("two modes at once" is unrepresentable).
DEF.state_substrate: `AGENCY_MODE` persists in FRAME memory — `write_memory(entity="frame", ...)`. Frame memory survives context compaction within THIS conversation but is per-session and invisible to other sessions ⇒ it matches the dial's "state is per-conversation, defaults to the middle" semantics exactly. (Science has no cross-session mode; each new conversation starts at collaborative.)
DEF.return_phrases (CANONICAL — solo & plan reference this set): the RETURN-TO-MIDDLE utterances that set the dial to collaborative = `/collab` · "solo off" · "plan off" · "go ahead" · "execute" · "stop planning" · "back to normal" · "step by step" · "check with me" · "let's work together". Any of these ⇒ `AGENCY_MODE=collaborative`. This is the ONE authoritative list; the pole skills point here rather than re-listing (so it can't drift out of sync).
RULE.set_mode: WHEN any DEF.return_phrase fires ⇒ in ONE write, set the frame-memory dial row to `AGENCY_MODE: collaborative (since <ts>)` (replace the single dial row; append only if absent). This one assignment leaves solo and plan — there is no separate flag to clear.
RULE.no_marker: WHILE `AGENCY_MODE=collaborative` ⇒ show NO leading mode-marker. Collaborative is the neutral default; the absence of a `— solo mode on —` / `— plan mode on —` line IS the signal that the dial is at the middle. (So the user can always read the level: solo-marker, plan-marker, or neither.)

# ─── the disposition (operative) ───────────────────────────────────────────
RULE.surface_nontrivial: WHILE collaborative ⇒ surface non-trivial decisions and genuine forks for confirmation BEFORE acting on them; use ordinary judgment for routine steps. This is BETWEEN the poles: you do NOT run unattended through every decidable question (that is /solo), and you do NOT gate every scope-defining step for explicit go/no-go (that is /plan). Decide the small stuff, raise the real forks.
RULE.ambiguity_asks: WHILE collaborative ⇒ treat genuine ambiguity as a reason to ask (ask_user), not to pick silently. A decision with real downside options the user would want to weigh ⇒ present them. (Contrast /solo, where you pre-empt such asks with your best judgment.)
NOTE.recon_floor_still_fires: the always-on commit-recon discipline (survey + self-adjudicate before a COMMIT-CLASS action — dispatch a sub-agent/cascade · a file op hitting many files or by glob/pattern/loop · a downstream-consumed artifact · remote/paid compute · a non-trivially-reversible op) fires here as in every mode. Collaborative doesn't change that floor; it only sets how much of the ordinary, non-COMMIT-CLASS decision stream you surface vs. decide.

# ─── ending ────────────────────────────────────────────────────────────────
RULE.exit: collaborative holds until the user moves the dial — fires `/solo` (⇒ autonomy max) or `/plan` (⇒ deliberation max), or gives a superseding directive. On a move ⇒ set the dial to the new level and adopt that skill's marker. The dial does NOT persist across conversations; each new conversation STARTS here at `collaborative` (so firing /collab mid-conversation is only needed to RETURN from a pole).

# REF: skill solo (autonomy-max pole) · skill plan (deliberation-max pole) · the always-on commit-recon floor (fires in every mode). AGENCY_MODE lives in frame memory (write_memory entity="frame").
INVARIANT: collaborative is the neutral middle — surface the real forks, decide the routine, show no marker; the recon floor still gates COMMIT-CLASS actions.
