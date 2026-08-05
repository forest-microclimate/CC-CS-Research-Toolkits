# 07_dynamic_workflows.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: DYNAMIC WORKFLOWS & HARNESSES — Claude assembles a multi-agent harness per task to beat single-context failure modes. The full harness treatment (the old thin A7 "workflows" pointer resolves HERE).
# FOR: a user tackling complex, high-value tasks that exceed one context window. Part of the ADVANCED set — map + REFERENCES in 00_overview.machine.md.
# STYLE: machine-terse, front-loaded, POSITIVE action-first; per-unit shape FOR -> HANDLE -> mechanics -> INVARIANT -> FEEDS. Paraphrased facts carry an inline hyperlink citation.

## 07 · DYNAMIC WORKFLOWS & HARNESSES
- FOR: beating the failure modes of SINGLE-CONTEXT work on complex, high-value tasks by having Claude ASSEMBLE a multi-agent harness tailored to THIS task.
- HANDLE (lead with the capability): Claude writes its OWN [harness on the fly, custom-built for the task at hand](https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code) — you don't pick a template, Claude FABRICATES the assembly line.
- TRIGGER: ask for a "workflow", or say the keyword `ultracode`.
- MECHANICS: the harness IS a JAVASCRIPT file that runs SPECIAL functions to SPAWN + COORDINATE subagents, alongside standard JSON / Math / Array for data wrangling. Per subagent, Claude PICKS the model and can optionally ISOLATE it in its own git WORKTREE. It is RESUMABLE — interrupt it (a user action, or quitting the terminal) and resuming the session picks up where it left off.
- WHY — the 3 named FAILURE MODES of single-context work it fixes:
  - AGENTIC LAZINESS ⇒ Claude STOPS before finishing a complex, multi-part task (e.g. addresses 35 of 50 security-review items).
  - SELF-PREFERENTIAL BIAS ⇒ Claude PREFERS its own results/findings, especially when asked to VERIFY them.
  - GOAL DRIFT ⇒ fidelity to the original objective DECAYS across many turns; WORSENED by lossy COMPACTION — each summarization step drops detail, so edge-case requirements slip.
  - the fix in one line: give each job a SEPARATE agent with a CLEAN context, so no single window carries the laziness, the bias, or the drift.
- STATIC vs DYNAMIC:
  - STATIC ⇒ a harness you pre-build (Claude Agent SDK, `claude -p`); necessarily GENERIC — it must cover all edge cases.
  - DYNAMIC ⇒ Opus 4.8 writes a TAILOR-MADE harness for YOUR use case, at request time.

### THE SIX PATTERNS (name ⇒ purpose)
- CLASSIFY-AND-ACT ⇒ route each item by TYPE to the right agent/behavior.
- FAN-OUT-AND-SYNTHESIZE ⇒ SPLIT the work into parallel steps, an agent per step, then MERGE the results.
- ADVERSARIAL-VERIFICATION ⇒ a SEPARATE verifier agent checks each output against a RUBRIC.
- GENERATE-AND-FILTER ⇒ ideate broadly, then FILTER by quality + DEDUPE, keep the best.
- TOURNAMENT ⇒ N agents COMPETE on the same task; judges pick a winner PAIRWISE (comparative judgment is more reliable than absolute scoring).
- LOOP-UNTIL-DONE ⇒ keep SPAWNING agents until a STOP condition — for work of UNKNOWN size.
<!--FIG: THE SIX-PATTERN PANEL (single most important figure) — six small flow diagrams: (1) classify-and-act = a router fanning to typed handlers; (2) fan-out-and-synthesize = a split → per-step agents → JOIN; (3) adversarial-verification = a producer → a separate verifier-vs-rubric pair; (4) generate-and-filter = generate → filter → dedupe; (5) tournament = a pairwise BRACKET narrowing to one winner; (6) loop-until-done = a self-looping SPAWN cycle with a stop test | 90% -->

### USE CASES (task ⇒ pattern that bites)
- MIGRATIONS / REFACTORS ⇒ a subagent PER FIX in its own worktree → adversarial review → merge (Bun's Zig→Rust rewrite used workflows; tell agents to avoid resource-intensive commands so they parallelize cleanly).
- DEEP RESEARCH ⇒ the `/deep-research` skill fans out web searches, fetches sources, adversarially VERIFIES their claims, and synthesizes a CITED report.
- DEEP VERIFICATION ⇒ one agent extracts factual CLAIMS → a checker per claim → a "check-the-checker" pass on source quality.
- SORTING ⇒ rank a big list by TOURNAMENT (pairwise) or parallel bucket-rank — comparative judgment beats absolute scoring.
- MEMORY / RULE-ADHERENCE ⇒ forward: ONE verifier per rule + a SKEPTIC persona (kills false positives). reverse: MINE your recent sessions + code-review comments for corrections you keep making, cluster them with parallel agents, DISTILL the survivors into `CLAUDE.md`.
- ROOT-CAUSE ⇒ spawn hypotheses from DISJOINT evidence (logs, files, data); each hypothesis faces a PANEL of verifiers + refuters.
- TRIAGE-AT-SCALE ⇒ classify → dedupe → act; with the SECURITY QUARANTINE pattern — agents that read UNTRUSTED public content are BARRED from privileged actions; SEPARATE agents do the acting.
- MODEL ROUTING ⇒ a classifier agent researches task complexity, then routes to Sonnet or Opus accordingly.

### SCALING LESSONS (from the multi-agent research system)
- ORCHESTRATOR-WORKERS AT SCALE ⇒ a lead agent plans + spawns [subagents that operate in parallel, each with its OWN context window](https://www.anthropic.com/engineering/multi-agent-research-system), exploring different aspects, returning distilled findings for the lead to compile.
- IT COSTS ⇒ agents use ~4× the tokens of chat; multi-agent ~15× ⇒ justified ONLY when the task's VALUE pays for the added performance.
- WHY IT WORKS ⇒ token usage ALONE explains ~80% of performance variance — multi-agent wins mainly by SPENDING ENOUGH TOKENS on a problem that exceeds one context window.
- DELEGATE EXPLICITLY ⇒ each subagent needs an OBJECTIVE, an output format, tool/source guidance, and CLEAR BOUNDARIES — vague briefs make agents duplicate work + leave gaps.
- SCALE EFFORT TO COMPLEXITY ⇒ simple fact-find = 1 agent / 3–10 tool calls; comparison = 2–4 subagents; hard research = 10+ subagents with divided responsibilities.
- MINIMIZE THE "GAME OF TELEPHONE" ⇒ have subagents WRITE outputs to the filesystem + pass lightweight REFERENCES back, rather than routing everything through the coordinator's context.

### WHEN NOT TO USE
- most traditional coding tasks do NOT need a panel of 5 reviewers. Before reaching for a harness, ask: "does it REALLY need more compute?" Workflows burn far more tokens ⇒ reserve them for COMPLEX, HIGH-VALUE tasks.

### TIPS
- PROMPT in detail — name the pattern you want; for a small ask, request a "quick workflow."
- PAIR with the loop primitives — `/goal` for a hard completion bar, `/loop` for regular intervals.
- BUDGET tokens by prompting "use 10k tokens."
- SAVE with `s` in the workflow menu ⇒ stored in `~/.claude/workflows`. Or SHIP in a skill: put the JS in the skill folder + reference it in SKILL.md — and prompt Claude to treat the workflow as a TEMPLATE, not a verbatim script, so it adapts to the case.
- INVARIANT: the leverage is ISOLATED CONTEXTS — a fresh verifier can't inherit the producer's bias, a per-fix worker can't inherit the orchestrator's drift or bloat ⇒ that separation is precisely what defeats laziness, self-preference, and goal drift. A harness is the orchestrator-workers pattern (05_pattern_vocabulary), AUTO-WRITTEN per task.
- FEEDS: harnesses are the STRUCTURE a PROACTIVE loop (06_loops) schedules + a `/goal` bounds; the six patterns are the five blocks (05_pattern_vocabulary) specialized + composed; author your own by shipping a workflow template inside a skill (10_authoring).
<!--FIG: how a harness works — Claude writes a JS file → special SPAWN functions launch subagents (each with a chosen model, some isolated in their own worktree) → agents run in PARALLEL → results COORDINATE back to the orchestrator → whole run is RESUMABLE if interrupted | 80% -->

## SOURCES
In-text hyperlinks cite each paraphrased source; the full consolidated reference list lives in 00_overview.machine.md (§ REFERENCES).
