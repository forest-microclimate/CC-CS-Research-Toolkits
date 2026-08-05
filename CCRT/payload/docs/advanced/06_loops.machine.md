# 06_loops.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: LOOPS — running the agentic cycle repeatedly + unattended until a defined STOP. The full loops treatment (the old thin A7 "loops" pointer resolves HERE).
# FOR: a user automating recurring or long-horizon work. Part of the ADVANCED set — map + REFERENCES in 00_overview.machine.md.
# STYLE: machine-terse, front-loaded, POSITIVE action-first; per-unit shape FOR -> HANDLE -> mechanics -> INVARIANT -> FEEDS. Paraphrased facts carry an inline hyperlink citation.

## 06 · LOOPS
- FOR: running the agentic cycle REPEATEDLY + unattended until a defined STOP ⇒ recurring or long-horizon work advances without you babysitting each turn.
- HANDLE: a thermostat — it keeps CYCLING (sense → act → check) until the target condition is reached, then rests.
- DEFINITION: a [loop = an agent repeating cycles of work until a STOP condition is met](https://claude.com/blog/getting-started-with-loops). Categorize ANY loop by 4 AXES:
  - TRIGGER — what STARTS a cycle (a prompt · a manual real-time ask · a time interval · an event/schedule).
  - STOP — what ENDS it (Claude judges done · goal achieved · you cancel · task completes).
  - PRIMITIVE — the Claude Code verb (`/goal` · `/loop` · `/schedule` · dynamic workflows).
  - TASK-TYPE — what it fits (exploration · verifiable goals · recurring work · autonomous streams).
- CAUTION (front-load): start with the SIMPLEST solution and use these patterns SELECTIVELY — don't wrap a one-shot task in a loop.

### THE FOUR LOOP TYPES (each: trigger · stop · best-for · manage-cost)
- TURN-BASED — the default cycle behind EVERY prompt.
  - trigger: a user PROMPT. · stop: Claude judges the task DONE or that it needs your context. · best-for: SHORT, one-off, non-routine tasks. · manage-cost: write SPECIFIC prompts; harden verification with a skill.
  - HARDEN IT ⇒ encode your manual check as a VERIFICATION SKILL so Claude self-verifies END-TO-END. EX `verify-frontend-change` SKILL.md: (1) start the dev server + open the edited page; (2) interact with the change directly + SCREENSHOT before/after; (3) check the browser console for ZERO new errors/warnings; (4) run a Chrome-DevTools performance trace + audit Core Web Vitals; (5) any step fails ⇒ fix + rerun FROM step 1 — never hand back partially-verified work.
  - PRINCIPLE: the more QUANTITATIVE the checks, the easier it is for Claude to self-verify.
- GOAL-BASED (`/goal`) — iterate to a verifiable bar.
  - trigger: a manual real-time PROMPT. · stop: the GOAL is met OR max turns reached. · best-for: tasks with a VERIFIABLE exit criterion. · manage-cost: set specific criteria + an explicit turn cap.
  - MECHANISM: an EVALUATOR MODEL re-checks YOUR condition each time Claude tries to stop, and sends it back until met ⇒ DETERMINISTIC criteria (tests passed, a score threshold) work best; it stops Claude ending early out of "is this good enough?" uncertainty.
  - EX `/goal get the homepage Lighthouse score to 90 or above, stop after 5 tries.` · `/goal` with NO args ⇒ shows turns + tokens spent so far.
- TIME-BASED (`/loop`, `/schedule`) — run on an interval.
  - trigger: a time INTERVAL. · stop: you CANCEL, or the work completes (the PR merges, the queue empties). · best-for: recurring work + interfacing with external systems. · manage-cost: lengthen the interval, or react to EVENTS instead of time.
  - `/loop <interval> <prompt>` ⇒ runs LOCALLY on your machine. EX `/loop 5m check my PR, address review comments, and fix failing CI`.
  - `/schedule` ⇒ moves the same loop to the CLOUD as a "routine" ⇒ runs even when your machine is off. Use when inputs change but the task is CONSTANT (a daily Slack summary) or when monitoring an external system (PR reviews, CI failures).
- PROACTIVE — long-running, no human in the loop.
  - trigger: an EVENT or SCHEDULE, no human present in real-time. · stop: each task exits on its OWN goal; the routine runs until you TURN IT OFF. · best-for: recurring, well-defined streams (bug reports, triage, migrations, dependency upgrades). · manage-cost: route routines to SMALLER/faster models, reserve the most capable model for JUDGMENT calls.
  - COMPOSES the other primitives — `/schedule` + `/goal` + skills + dynamic workflows + auto mode — into a standing system, plus dynamic workflows built on the fly.
  - FLAGSHIP EX: `/schedule every hour: check #project-feedback for bug reports. /goal: don't stop until every report found this run is triaged, actioned, and responded to. When fixing a bug, use a workflow to explore three solutions in parallel worktrees and have a judge adversarially review them.` ⇒ triage + fix + review, no pause for permission.
<!--FIG: four cycle diagrams side by side — turn-based (prompt→gather→act→check→respond) · goal-based (loop through an evaluator DECISION DIAMOND) · time-based (loop gated by an interval clock) · proactive (event/schedule-driven, no human node) — each a sense→act→check ring with its own distinct STOP | 80% -->

### QUALITY — make the loop's output TRUSTWORTHY
- KEEP THE CODEBASE CLEAN ⇒ Claude follows the patterns already in the repo; a clean repo COMPOUNDS each iteration.
- GIVE CLAUDE A WAY TO VERIFY ⇒ encode "what good looks like" in SKILLS (especially quantitative checks).
- MAKE DOCS REACHABLE ⇒ keep framework/library docs current + in reach.
- REVIEW WITH A SECOND AGENT ⇒ a reviewer with FRESH context is less biased + not swayed by the main agent's reasoning; use the built-in `/code-review`.
- FIX THE SYSTEM, NOT THE INSTANCE ⇒ when a result misses the standard, ENCODE the fix so every FUTURE iteration clears it — don't just patch the one case.

### TOKENS — spend where it pays
- pick the RIGHT primitive + model (small task ⇒ no loop/multi-agent; some work fits a cheaper/faster model).
- set CLEAR success + stop criteria so Claude reaches "done" sooner — "but not too soon."
- PILOT before large runs — dynamic workflows can spawn HUNDREDS of agents; gauge usage on a small slice first.
- use SCRIPTS for deterministic work (running a script costs less than reasoning through the steps — e.g. PDF form-fill).
- don't run routines MORE often than the monitored thing actually changes.
- INSPECT: `/usage` (breaks down by skill / subagent / MCP) · `/goal` no-args (turns + tokens so far) · `/workflows` (each agent's token usage; stop any agent anytime).

### SUMMARY
| Loop | You hand off | Use it when | Reach for |
|------|--------------|-------------|-----------|
| Turn-based | the CHECK | you're exploring or deciding | custom verification skills |
| Goal-based | the STOP CONDITION | you know what done looks like | `/goal` |
| Time-based | the TRIGGER | work happens outside your project on a schedule | `/loop`, `/schedule` |
| Proactive | the PROMPT | work is recurring + well-defined | all the above + dynamic workflows |

- STARTER MOVE: find ONE task where YOU are the bottleneck; ask which piece you can hand off — can you write the verification CHECK? is the GOAL clear enough? does the work arrive on a SCHEDULE? Launch it, watch where it stalls or over-reaches, then iterate without fear.
- INVARIANT: a loop is only as good as its STOP condition — a vague stop over-runs tokens OR quits early; a QUANTITATIVE, machine-checkable stop is what makes hands-off iteration safe.
- FEEDS: `/goal` = the evaluator-optimizer (05_pattern_vocabulary) given a stop; the PROACTIVE flagship already reaches into 07_dynamic_workflows (a workflow of parallel worktrees + an adversarial judge) ⇒ loops SCHEDULE the work, harnesses STRUCTURE it.

## SOURCES
In-text hyperlinks cite each paraphrased source; the full consolidated reference list lives in 00_overview.machine.md (§ REFERENCES).
