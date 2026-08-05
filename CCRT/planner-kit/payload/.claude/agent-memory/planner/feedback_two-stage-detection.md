---
name: two-stage-detection-protocol
description: STANDING PROTOCOL — every testing round that outputs a product a standard covers only partly runs two-stage detection: (1) the in-development agents/skills/code detect first; (2) the user (standard-owner) manually sweeps for what stage 1 missed. User-caught misses = labeled fixtures + efficacy evidence.
metadata:
  type: feedback
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

Rule: WHEN a round of testing produces a product a standard covers only PARTLY (a generated draft, a revision, a pilot reading-pass output, fixture prose) ⇒ detection runs in TWO stages, in order: (1) the tools under development (detectors/skills/agents) scan and disposition first, results recorded; (2) THEN the user — or whoever owns the standard — manually reviews the same output hunting anything stage 1 missed. Never present test output as "clean" on stage-1 evidence alone.

**Why:** A product can pass the mandated tool self-scan and still carry defects the tools flag 0 of. Stage 2 measures the residual the tools cannot see; the residual per round, tracked over rounds, IS the rate-drop evidence the EFFICACY_LEDGER honesty floor requires (fixture-measured → measured-working needs exactly this).

**How to apply:** Build stage-2 explicitly into every phase gate that emits such a product (pilot reading passes, revision rounds, fixture batches): after the tool pass + synthesis, hand the artifact to the user labeled "ready for your stage-2 sweep" with the stage-1 findings attached (so their time goes to the frontier, not to what the tools already flag). Every user-caught miss: (a) append to `dev/REGISTER_DELTA.machine.md`, (b) add as a labeled fixture atom, (c) route to the next build round (detector-shape) or the judgment checklist (the detector-shape vs judgment-checklist split). Track per-round residual counts in `dev/EFFICACY_LEDGER.machine.md`. See [[feedback-supervisory-workflow]].
