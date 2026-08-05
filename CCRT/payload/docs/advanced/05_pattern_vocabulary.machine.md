# 05_pattern_vocabulary.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: THE PATTERN VOCABULARY — the shared names (workflows vs agents; the five building blocks) that LOOPS + HARNESSES read as instances of.
# FOR: a user who wants the reusable vocabulary before scaling into loops (06) + dynamic workflows (07). Part of the ADVANCED set — map + REFERENCES in 00_overview.machine.md.
# STYLE: machine-terse, front-loaded, POSITIVE action-first; per-unit shape FOR -> HANDLE -> mechanics -> INVARIANT -> FEEDS. Paraphrased facts carry an inline hyperlink citation.

## 05 · THE PATTERN VOCABULARY (workflows vs agents)
- FOR: the shared NAMES for the ways an LLM + tools compose ⇒ so LOOPS (M5) and HARNESSES (M6) read as INSTANCES of five reusable blocks, not one-off magic.
- HANDLE: a parts bin, not a blueprint — five building blocks you COMBINE; reach for the FEWEST that solve the task.
- THE ONE DISTINCTION (everything hangs off it) — [WORKFLOWS vs AGENTS](https://www.anthropic.com/engineering/building-effective-agents):
  - WORKFLOW ⇒ LLMs + tools orchestrated through PREDEFINED code paths — YOU wrote the control flow.
  - AGENT ⇒ the model DYNAMICALLY DIRECTS its own process + tool use, keeping control of HOW it accomplishes the task — the control flow is decided at RUNTIME, by the model.
  - the split is control-flow OWNERSHIP: fixed-by-you = workflow; decided-by-model = agent. Most production value is workflows; reach for a full agent only when the path can't be pre-drawn.
- FOUNDATION — the AUGMENTED LLM: the atom under every pattern is one LLM augmented with RETRIEVAL + TOOLS + MEMORY — it generates its own search queries, selects tools, decides what to retain. Build the patterns on THIS atom.
- THE FIVE BUILDING BLOCKS (name ⇒ one-line ⇒ WHEN):
  - PROMPT-CHAINING ⇒ decompose into FIXED sequential steps, each call consumes the last's output (+ an optional programmatic gate between). WHEN: the task cleanly splits into fixed subtasks; trades latency for accuracy.
  - ROUTING ⇒ CLASSIFY the input, then dispatch to a SPECIALIST handler. WHEN: distinct categories are better handled separately.
  - PARALLELIZATION ⇒ run LLM calls CONCURRENTLY, aggregate. Two forms — SECTIONING (independent subtasks at once) + VOTING (same task N times, aggregate for confidence). WHEN: subtasks parallelize for speed, OR multiple perspectives/attempts raise confidence.
  - ORCHESTRATOR-WORKERS ⇒ a LEAD LLM DYNAMICALLY splits the task, delegates to workers, then SYNTHESIZES their results. WHEN: you CAN'T predict the subtasks up front — they're determined at runtime by the orchestrator (the workflow that shades into an agent).
  - EVALUATOR-OPTIMIZER ⇒ one LLM GENERATES, a second CRITIQUES against criteria, LOOP until it passes. WHEN: you have clear eval criteria AND iterative refinement measurably helps.
- RUNNABLE: all five ship as minimal executable implementations in the [agents cookbook](https://github.com/anthropics/claude-cookbooks/tree/main/patterns/agents) — `basic_workflows.ipynb` (chaining · routing · parallelization) · `orchestrator_workers.ipynb` · `evaluator_optimizer.ipynb` · `async_multi_agent_orchestration.ipynb` ⇒ read the CODE, not just the names.
- THESIS (front-load it): find the SIMPLEST thing that works; add agentic complexity ONLY when it DEMONSTRABLY improves outcomes. Success isn't the most sophisticated system — it's the RIGHT system for the need. Frameworks speed the START; drop abstraction layers as you productionize.
- INVARIANT: agents are NOT exotic — an agent is "typically just an LLM using tools based on environmental feedback in a loop." ⇒ the loops (06_loops) and harnesses (07_dynamic_workflows) are NOT new primitives; they are these five blocks NAMED, SCALED, and AUTOMATED.
- FEEDS: LOOPS (06_loops) = evaluator-optimizer + a stop condition, run over time; HARNESSES (07_dynamic_workflows) = orchestrator-workers + parallelization + adversarial evaluator-optimizer, AUTO-ASSEMBLED per task. Carry this vocabulary into both.
<!--FIG: the orchestrator-workers pattern — a lead LLM splitting a task into runtime-determined worker calls, workers running in parallel, then the lead synthesizing their results | 75% -->

## SOURCES
In-text hyperlinks cite each paraphrased source; the full consolidated reference list lives in 00_overview.machine.md (§ REFERENCES).
