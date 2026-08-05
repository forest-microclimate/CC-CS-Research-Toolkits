# 03_agents.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-12). T-24: toolkit agent count normalized to 5 (research-facing×3 + toolkit-builder×2).
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: AGENTS & SUBAGENTS — hand a bounded job to a SEPARATE context window so the main thread stays clean.
# FOR: a user delegating work to keep context clean, and the unit that dynamic workflows (07) orchestrate at scale. Part of the ADVANCED set — map + REFERENCES in 00_overview.machine.md.
# STYLE: machine-terse, front-loaded, POSITIVE action-first; per-unit shape FOR -> HANDLE -> mechanics -> INVARIANT -> FEEDS.

## 03 · AGENTS & SUBAGENTS (the same thing)
- FOR: handing a bounded job to a SEPARATE context window so the main thread stays clean.
- HANDLE: a subagent = an agent the main agent calls; "subagent" names the RELATIONSHIP, not a different kind of thing.
- SAME THING: an agent invoked BY the main agent runs in its OWN fresh context window; only its SUMMARY returns to the main thread.
- DEFINED in `.claude/agents/*.md` — frontmatter: `name` + `description` REQUIRED; optional `tools`, `model`, `effort`, `isolation`.
- INVOKED 3 ways: (1) AUTOMATIC delegation when the `description` matches the task · (2) `@agent-<name>` to FORCE one · (3) the Agent tool programmatically (renamed from Task; `Task()` still ALIASES it).
- BUILT-INS: `Explore` (read-only search), `Plan` (design a plan), `general-purpose` (catch-all).
- FORK: a `fork` INHERITS the full parent conversation (starts WITH the main thread's context) — contrast a normal subagent, which starts FRESH (empty).
- INVARIANT: a subagent spends a SEPARATE context window ⇒ its intermediate exploration/verification does NOT accrue to the main thread; only the distilled summary returns. That isolation IS the reason to delegate.
- FEEDS: dynamic workflows (07_dynamic_workflows) orchestrate MANY subagents into a harness; the toolkit's 5 agents (research-facing: code-review-debugger, machine-doc-reviewer, version-control-docs; toolkit-builder: agent-tooling-engineer, research-data-manager) are authored this way (10_authoring); delegating keeps context clean (01_extension_architecture).
<!--FIG: main agent delegating to isolated subagent contexts, each returning a summary | 75% -->

## SOURCES
Architecture facts; the consolidated reference list (official docs + blogs) lives in 00_overview.machine.md (§ REFERENCES).
