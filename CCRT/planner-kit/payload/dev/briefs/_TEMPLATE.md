# _TEMPLATE.md — child-brief form (machine-only; primary reader = the child agent)
# HOW TO USE: COPY to `dev/briefs/<ID>-<slug>.md`, fill EVERY slot, then launch. An EMPTY slot = NOT ready to launch.
# Slots 1-5 + SCOPE RULE = the six BRIEF CHECKLIST elements (root `CLAUDE.md`, RULE.supervisory_workflow).
# STRICTNESS IS TIER-CONDITIONAL (measured): hard-rule checkpoint blocks help Haiku-class children, are ~neutral on Sonnet-class, and HURT Opus-class — carry them in T4 briefs only; T1 briefs stay light-touch. Put NO show-your-thinking / echo-reasoning instructions in any brief (fable reasoning_extraction refusal risk, vendor-stated).
# STATUS: CURRENT (2026-08-04). Form only — drop this line from the copy; a filled brief is dated in its own title slot.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# <ID> brief — <one-line title> (<YYYY-MM-DD>)
ROLE: <specialist agent> (<model — NAME the tier on the Task call: `fable` | `sonnet` | `haiku` (aliases only; a full id needs a project shadow pin). Omitting the param is rank 4 and inherits the MAIN model, so it is not a tier choice (measured 2026-08-04); ceiling work fitting `Read, Edit, Write, Grep, Glob, Bash` ⇒ `delegate:fable-executor` PARAMLESS (routing default — its rank-3 pin governs); `claude-opus-5` ONLY as `delegate:opus5-executor` under an active planner watch (scope-drift · thrash · false-positive over-caution), never as the default and never the bare alias `opus`>, <effort — fable-tier: HIGH default, xhigh only for capability-sensitive work, medium/low for routine (vendor-stated); opus5-executor: high>).
SCOPE RULE [element 6] (verbatim): <paste RULE.workspace_scope's boundary sentence — the child inherits no context, so the boundary must travel with the brief>

## 1. ASSIGNMENT
<INTENT first — the larger task this serves and what the output enables (vendor-stated: fable performs better knowing intent) — then the task, and the DONE-condition a reader can check against an artifact>
<FABLE-TIER ONLY — VERIFIED-LAUNCH warmup (fixture-measured 2026-08-06): open the task with "WARMUP first: read these 4 small files, ONE Read call each: <4 quoted small paths>" — persona/skill Read-pointers ARE the warmup where the brief carries them (zero throwaway calls) — so serving is certifiable by ~call 5; the coordinator runs `.claude/skills/model-verification/fable_watchdog.py --watch` on the child transcript and relaunches on SWAPPED. Delete this slot for non-fable children.>

## 2. READ-PATHS (self-service: the child reads these ITSELF, never only this brief's précis)
- "<quoted path>" — <what this source decides; where two could disagree, name the authoritative one>

## 3. WRITE-PATH (every work product, code included — an unnamed path evaporates with the child)
- "<quoted in-workspace destination>" — <which deliverable; final code under `dev/` or the owning dir, scratch iterations under `sandbox/`>

## 4. REPORT CAP
<N> lines max, carrying: <the receipts each claim must quote — counts, hashes, command output — not a restatement of the claim>

## 5. STUCK RULE (verbatim)
if errors recur, the approach stops converging, or you are about to change approach — STOP and report back with what you found; do not thrash.

## CONSTRAINTS
- CODE-REUSE: read `dev/CODE_INVENTORY.machine.md` FIRST; use → adapt → build-new, in that order; REPORT which of the three you did.
- PERSIST-BY-DEFAULT: every script you write lands in-workspace before you finish; never discarded.
- <task-specific: the standards, version, or hold that binds every line you add>

## SUB-PLANNER (delete unless this child coordinates its own subagents)
- SUB-SCOPE: <the subtree(s) this planner AND every child it launches stay inside — nested inside the element-6 scope, never wider>
- PRIVATE BRIEFS/LEDGER: `dev/briefs/<ID>/` — your children's briefs + your own collect record; the shared ledgers stay the coordinator's.
- ROLL-UP: your report = your collect outcomes + the receipts you spot-checked, within the cap above — not your children's reports.
