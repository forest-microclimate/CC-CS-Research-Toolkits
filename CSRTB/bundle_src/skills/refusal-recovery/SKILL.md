---
name: refusal-recovery
description: Disciplined handling of a model refusal or safety-flag — invoke WHEN a delegated child (host.delegate), a host.llm call, or your own request gets refused, safety-flagged, or content-blocked. Owns the classify → one-neutral-rephrase-max → change-legitimate-levers → surface-to-user ladder, and the hard ban on reword-until-passes (evasion-by-iteration is the dark-mirror failure this skill exists to prevent, not perform). Fires on a child returning a refusal, "safeguards flagged this message", an API refusal error, a content-policy block. NOT for tool/permission errors (fix the call) and NOT for failing tests (debug them).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-28). Authored in the verification-integrity pass. Carries SEED-10 (subagent refusal, 6 arcs) with DISC-20 (safety-evasion-by-retry) as the explicitly banned mirror. Grounded case (Claude Code side, 2026-07-28): a benign config-precedence probe tripped a safeguard on the wording "probe/shadow"; ONE neutral rephrase ("local variant test", cheaper model) succeeded; no iteration loop.

# refusal-recovery — recover legitimately, or surface; never iterate past a boundary

## When to invoke
WHEN any model call refuses or is safety-flagged: a delegated child returns a refusal instead of its deliverable, a `host.llm` call is content-blocked, your own composition is flagged — and you believe the task is legitimate.

## The ladder (strictly in order; each rung at most once)
1. CLASSIFY before touching the wording. Two honest bins:
   - BENIGN-PHRASING false positive — the task is plainly legitimate (config test, security-adjacent research term, biology/chemistry vocabulary in a scientific context) and specific WORDS likely pattern-matched ("probe", "inject", "kill", "exploit", "shadow"…).
   - GENUINELY BOUNDARY-ADJACENT — a reasonable reviewer could read the request as touching a real policy line.
   WHEN in the second bin ⇒ skip to rung 4 (surface). Only the first bin earns a rephrase.
2. ONE NEUTRAL REPHRASE, maximum. Restate the same task in plain domain vocabulary — remove the trigger-adjacent words, change NOTHING about what is actually requested. The test: you would happily show both phrasings side-by-side to the user. A rephrase that narrows, launders, or obscures what the task does is not neutral — that is the banned mirror.
3. CHANGE A LEGITIMATE LEVER (may combine with rung 2, still one attempt): a different model on the dispatch (`host.delegate(model=…)` / `host.llm(model=…)` — never a banned id), a fresh child, splitting an over-broad brief into its innocuous mechanical part (run it yourself in a repl cell) and the judgement part (surface). These change the CONTEXT, not the disguise.
4. SURFACE TO THE USER — the terminal action, not a failure: report the refusal verbatim (the flagged brief + the refusal text), your classification, what you tried (the one rephrase, the lever), and what you recommend. The user holds context you don't (their account, their intent, institutional access).

## The hard ban (DISC-20 — the dark mirror)
NEVER reword-until-passes. WHEN attempt 2 (one rephrase + one lever change) has not cleared the block ⇒ STOP; iterating adversarially against a safety boundary is itself the catalogued failure — worse than the blocked task, whatever the task's legitimacy. Boundary enforcement is server-side and not yours to defeat; Claude Science has no hook surface, so this ban is carried as discipline and honestly labeled as such.

## Record discipline
Log every refusal + disposition (flagged brief, classification, rephrase-if-any, outcome) in the turn's record — refusal patterns are corpus material (SEED-10 instances), and an unlogged recovery is invisible to the countermeasure audit.

REF: `countermeasure-audit` (consumes the logged instances) · the failure catalog SEED-10/DISC-20 entries (the recorded basis) · `software-craft` (the neutral-contract habit that prevents over-broad briefs in the first place).
