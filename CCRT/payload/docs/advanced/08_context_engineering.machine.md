# 08_context_engineering.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: CONTEXT ENGINEERING — the discipline beneath every context tactic: curate the smallest high-signal token set. The THEORY the tactical levers implement.
# FOR: a user who wants the master principle behind /clear, /compact, subagents, skills, memory. Part of the ADVANCED set — map + REFERENCES in 00_overview.machine.md.
# STYLE: machine-terse, front-loaded, POSITIVE action-first; per-unit shape FOR -> HANDLE -> mechanics -> INVARIANT -> FEEDS. Paraphrased facts carry an inline hyperlink citation.

## 08 · CONTEXT ENGINEERING
- FOR: the DISCIPLINE beneath every context tactic in this guide — curating the SMALLEST set of high-signal tokens that steers Claude to the right outcome. It is the SUCCESSOR to prompt engineering: prompt engineering wrote the words of one turn; context engineering curates the WHOLE token set the model sees each turn ([Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
- HANDLE: the context window is a finite, DEPLETING working memory — a BUDGET, not a bucket. You are its curator; every token admitted dilutes the attention paid to the rest.
- SUCCESSOR, not rename: context engineering ⊃ prompt engineering ⇒ it governs the system prompt + tool set + retrieved data + message history + memory TOGETHER, across a multi-turn agent loop — not just one clever instruction in isolation.
- WHY SMALL WINS: attention is a finite budget that DEGRADES as the window grows ("context rot") ⇒ more tokens = LOWER signal per token + diminishing marginal returns. Optimize for the smallest high-signal set, never the largest context.
- ALTITUDE — tune the system prompt to the GOLDILOCKS zone: too LOW = brittle hardcoded if-else logic that overfits + snaps; too HIGH = vague guidance that gives no real steer. Aim concrete-enough-to-direct, general-enough-to-transfer.
- JUST-IN-TIME context: keep lightweight IDENTIFIERS in the window — file paths, queries, links — and LOAD the underlying data at RUNTIME when a step needs it, rather than pre-loading everything up front. Mirrors a person working from a filesystem: hold the path, open the file on demand.
- COMPACTION (long-horizon tasks): as history nears the window limit, SUMMARIZE it + reinitialize a fresh window seeded with that summary. PRESERVE the load-bearing atoms (architectural decisions, unresolved bugs, the contract) + DROP the redundant (stale tool output, resolved detours).
- STRUCTURED NOTE-TAKING: persist durable notes OUTSIDE the window (memory / files) + pull them back only when relevant ⇒ long-horizon state without paying its token cost every turn.
- FEWER, SHARPER TOOLS: a bloated or ambiguous tool set spends tokens + invites wrong calls ⇒ curate tools like context (self-contained, minimally-overlapping, token-efficient).
- INVARIANT: treat context as a FINITE, depleting resource with diminishing marginal returns ⇒ the objective is always the SMALLEST set of high-signal tokens that maximizes the odds of the desired behavior — admit a token only when it earns its slot.
- FEEDS: this is the THEORY the tactical levers implement — `/clear` (drop stale history), `/compact` (compaction on demand), subagents (each a SEPARATE window ⇒ fan-out that keeps intermediate exploration off the main thread), skills (PROGRESSIVE DISCLOSURE ⇒ just-in-time: only the `description` loads until you invoke), memory + `.claude/rules` (structured notes that live OUTSIDE the window). ONE discipline; those are its instruments. Extending Claude Code further ⇒ 09_going_further.
<!--FIG: the context window as a finite budget across four sources (system prompt · tools · memory · history); just-in-time load-on-demand vs pre-load-everything | 80% -->

## SOURCES
In-text hyperlinks cite each paraphrased source; the full consolidated reference list lives in 00_overview.machine.md (§ REFERENCES).
