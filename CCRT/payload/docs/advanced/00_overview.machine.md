# 00_overview.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: THE HUB for the ADVANCED set — orientation + the ONE governing idea (the harness beats the model; context is the master budget) + the MAP of docs 01-10 + the consolidated REFERENCES + the advanced GLOSSARY.
# FOR: a user past QUICKSTART / USAGE_DETAILED who wants to EXTEND + orchestrate Claude Code. START HERE for the big picture + the tying idea, then open the numbered doc for the depth.
# STYLE: machine-terse, front-loaded, POSITIVE action-first; per-unit shape FOR -> HANDLE -> mechanics -> INVARIANT -> FEEDS.

> WHAT THIS IS: the ADVANCED guide to Claude Code — its EXTENSION ARCHITECTURE (the files you add under `.claude/`) + advanced ORCHESTRATION (agents, loops, dynamic workflows, context engineering). ELEVEN docs: this hub + `01`–`10`. Read this hub for the big picture and the one idea that ties it together, then open the numbered doc for the depth.

## 00.1 · ORIENTATION
- FOR: placing yourself in the set — who it's for, the two halves it splits into, and how every doc reads.
- WHO: a user PAST QUICKSTART / USAGE_DETAILED who wants to EXTEND Claude Code (add files under `.claude/`) + ORCHESTRATE it (agents, loops, workflows) — not "how do I start", but "how do I get the most out of it".
- TWO HALVES:
  - THE EXTENSION SURFACE (`01` `02` `03` `10`) — the FILES you add under `.claude/` + WHAT each customizes. Answers *what can I change?*
  - METHODS & ORCHESTRATION (`04` `05` `06` `07` `08` `09`) — how to WIELD that surface. Answers *how do I get the most out of it?*
- READING SHAPE: every doc + every unit reads the SAME shape — FOR (what it's for) → HANDLE (a mental model) → mechanics → INVARIANT (the one load-bearing fact) → FEEDS (how it couples to the rest).
- New BASICS term? → the USAGE_DETAILED glossary. New ADVANCED term? → § 00.5 GLOSSARY below.
- These docs are themselves machine→human→PDF artifacts: you are reading a machine ROOT (`.machine.md`, the authoritative source); the human twin (`.md`) + the PDF are DERIVED from it (render via `/folio`; method in `10_authoring` §10.2).

## 00.2 · THE ONE IDEA — THE HARNESS MINDSET
- FOR: the ONE mental model behind every tactic in this guide — why the extension points exist, and when each earns its context cost. Everything in `01`–`10` is a lever on this.
- HANDLE: the model is an ENGINE; the harness is the whole car around it — fuel lines = context, dashboard = CLAUDE.md, attachments = skills/MCP, brakes = hooks. Tuning the car beats swapping the engine.
- **The harness beats the model.** Claude Code is "built to work the way you work," and its behavior is shaped by a layered instruction system, not the raw weights ([Steering Claude Code](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more)). The extension points form a SPECTRUM by context cost + authority: always-on / high-cost (CLAUDE.md, unscoped rules — load at start, survive compaction) → on-demand / low-cost (skills, subagents — "only the name and description load at session start; the full body loads when Claude invokes the skill") → deterministic / outside-context (hooks — fire on events, bypass the window) → system-level / highest-authority (output styles, appended system prompt). ⇒ pick the mechanism whose cost + authority fit the job: an absolute constraint ⇒ a hook or managed setting ("an instruction is the wrong tool"); a procedure ⇒ a skill, not static docs ([Steering Claude Code](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more)).
- **Search live; don't pre-index (agentic > RAG).** Claude Code "traverses the file system, reads files, uses grep to find exactly what it needs, and follows references across the codebase" — it retrieves like an engineer, at runtime ([How Claude Code works in large codebases](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start)). It does NOT embed your repo into a vector index: "embedding pipelines can't keep up with active engineering teams," so "by the time a developer queries the index, it reflects the codebase as it previously existed weeks, days, or even hours before." Agentic search never goes stale — but "works best when Claude has enough starting context to know where to look." The context-engineering twin: keep "lightweight identifiers (file paths, stored queries, web links)" and "dynamically load data into context at runtime," just-in-time, the way humans use file systems and bookmarks instead of memorizing a corpus ([Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
- **Budget context like it's scarce — because it is.** "Claude's context window fills up fast, and performance degrades as it fills" ([Best practices](https://code.claude.com/docs/en/best-practices)). Root cause = *context rot*: "as the number of tokens in the context window increases, the model's ability to accurately recall information from that context decreases" — a transformer's n² pairwise relationships "get stretched thin," and models saw fewer long sequences in training ([Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)). Treat context as a depleting "attention budget." This one constraint is WHY every method in the set exists — targeted inclusion, session hygiene, subagent isolation are all context-preservation moves, not style preferences.
- **Include on target, not on spec.** Aim for "the smallest possible set of high-signal tokens that maximize the likelihood of some desired outcome" ([Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)) — the Goldilocks zone where "too much context loaded into every session degrades performance, while too little context leaves Claude to navigate blind" ([How Claude Code works in large codebases](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start)). CONCRETE moves: NAME the in-scope files/dirs up front (scope to "the part of the codebase that's actually relevant," initialize in subdirectories, `.claudeignore` the build artifacts + vendored code); keep CLAUDE.md "lean and layered"; run PER-TASK session hygiene — `/clear` between unrelated tasks, and after two failed corrections `/clear` + a sharper prompt rather than fighting a polluted window ([Best practices](https://code.claude.com/docs/en/best-practices)).
- INVARIANT: the finite, degrading context window is the MASTER constraint — every extension point + workflow is ultimately a lever on WHAT fills it and WHEN ⇒ judge any tactic by one question, "does this spend high-signal tokens, or waste the budget?"
- FEEDS: this mindset is the harness applied to a task loop (`04_agentic_workflows`) and, named as its own discipline, the whole of context engineering (`08_context_engineering` — the successor to prompt engineering: curate the WHOLE token set, not one turn's words); its purest expression is skills' progressive disclosure (`02_skills_and_commands` — pay context only on demand); the concrete knobs are subagent isolation (`03_agents`), `/clear` + `/compact` (§02.3), and a lean CLAUDE.md (§01.2).
<!--FIG: the harness — model ENGINE at center, ringed by the extension points (CLAUDE.md, rules, skills, subagents, hooks, plugins, MCP), each labeled with its context-cost tier (always-on / on-demand / deterministic / system-level) | 80% -->

## 00.3 · THE MAP — SCOPES + DOCS 01–10
- FOR: the one-glance shape of the extension architecture, then a linked index of the ten in-depth docs.
- SCOPES (three — the WHERE that decides WHO gets a customization): User (`~/.claude/`) ⇒ EVERY session · Project (`<repo>/.claude/`) ⇒ only inside that repo · Managed (enterprise/admin policy) ⇒ org-wide, top precedence. Each scope holds the SAME kinds of file (`CLAUDE.md`, `rules/*.md`, `skills/<name>/SKILL.md`, `agents/*.md`, `commands/*.md`, `settings.json`). Scopes STACK onto a global baseline; scope == install LOCATION, and location alone decides reach. Full treatment: `01_extension_architecture` §01.1.
<!--FIG: the three scopes (User/Project/Managed) and what loads from each | 80% -->
- THE TEN DOCS (numeric order; tag = which half of 00.1):
  - `01_extension_architecture` [SURFACE] — the scope MAP + context/memory (CLAUDE.md) + settings precedence (merge-vs-override) + hooks. The static surface you customize.
  - `02_skills_and_commands` [SURFACE] — skills ARE slash commands (one merged mechanism); how to author + stack them; the full stock-command CATALOG.
  - `03_agents` [SURFACE] — subagents = agents run in a SEPARATE context window; delegation, isolation, built-ins, `fork`.
  - `04_agentic_workflows` [METHODS] — the harness mindset as a task LOOP: give Claude a verifiable check; explore→plan→code→commit; TDD; visual; multi-Claude; worktrees; headless `claude -p`.
  - `05_pattern_vocabulary` [METHODS] — workflows vs agents; the 5 building-block patterns; the simplicity thesis (start simple, add machinery only when it pays).
  - `06_loops` [METHODS] — the 4 loop types; the quality + token trade-offs; when each fits.
  - `07_dynamic_workflows` [METHODS] — auto-generated HARNESSES; 3 failure modes; the SIX orchestration patterns (the key six-panel figure).
  - `08_context_engineering` [METHODS] — context as the master resource; just-in-time loading; compaction; altitude (the Goldilocks system prompt).
  - `09_going_further` [METHODS] — build ON Claude Code: MCP + custom tools · sandboxing · plugins · the Agent SDK / headless.
  - `10_authoring` [SURFACE] — build your OWN extension to the toolkit's standard: the `/machine-md` → `machine-doc-reviewer` → `/folio` loop + the methodology source docs.
  - `11_references` [REFERENCE] — every external source cited across `00`–`10`, collected ONCE, deduplicated to CANONICAL (post-redirect) URLs; plus the alias/migration table and the anti-rot canaries that keep the list honest.
- INVARIANT: this hub is NAVIGATION + the tying idea; the depth lives in the numbered docs ⇒ don't add mechanics here that belong in a leaf — link to the leaf.
- FEEDS: every `NN_*` doc opens by pointing back here for the map + references; the two halves (SURFACE / METHODS) are the §00.1 split made concrete.

## 00.4 · REFERENCES (consolidated — every source in the set; grouped by theme, all clickable)
### CORE
- [How we use Skills](https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills)
- [Getting started with loops](https://claude.com/blog/getting-started-with-loops)
- [A harness for every task: dynamic workflows](https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code)
### FOUNDATIONS
- [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices)
- [How Claude Code works in large codebases](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start)
- [Steering Claude Code](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more)
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
### SKILLS / TOOLS / MCP
- [Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Model Context Protocol — Introduction](https://modelcontextprotocol.io/docs/getting-started/intro)
- [Anthropic cookbook — agent patterns](https://github.com/anthropics/claude-cookbooks/tree/main/patterns/agents)
### SECURITY / DISTRIBUTION / SDK
- [Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Plugins](https://claude.com/blog/claude-code-plugins)
- [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [Headless — run programmatically](https://code.claude.com/docs/en/headless)
### DOCS (code.claude.com/docs/en/)
- [skills](https://code.claude.com/docs/en/skills)
- [sub-agents](https://code.claude.com/docs/en/sub-agents)
- [memory](https://code.claude.com/docs/en/memory)
- [settings](https://code.claude.com/docs/en/settings)
- [hooks](https://code.claude.com/docs/en/hooks)
- [slash-commands](https://code.claude.com/docs/en/slash-commands)
- [common-workflows](https://code.claude.com/docs/en/common-workflows)
- [interactive-mode](https://code.claude.com/docs/en/interactive-mode)
- [cli-reference](https://code.claude.com/docs/en/cli-reference)
- [plugins](https://code.claude.com/docs/en/plugins)
- [output-styles](https://code.claude.com/docs/en/output-styles)
- [github-actions](https://code.claude.com/docs/en/github-actions)
- [mcp](https://code.claude.com/docs/en/mcp)

## 00.5 · GLOSSARY (advanced)
- scope: the install LOCATION (User `~/.claude/` · Project `<repo>/.claude/` · Managed) that decides a customization's reach (`01_extension_architecture` §01.1).
- managed policy: enterprise/admin-set config + permissions that apply org-wide and take TOP precedence (§01.3).
- fork: a subagent that INHERITS the full parent conversation (vs a fresh empty subagent) (`03_agents`); also `--fork-session` on a transcript (§01.2).
- `$ARGUMENTS`: the trailing text passed to a slash command (`/fix-issue 123` ⇒ `123`); positional `$1` / `$ARGUMENTS[N]` (`02_skills_and_commands` §02.1).
- skill stacking: chaining skills/commands so they compose in one turn (`/code-review /fix-issue 123`) (§02.1).
- harness: an auto-generated JS orchestrator coordinating subagents in isolated contexts (`07_dynamic_workflows`).
- orchestration pattern: a harness shape — classify-and-act / fan-out-and-synthesize / adversarial-verification / tournament / generate-and-filter / loop-until-done (the SIX; `07_dynamic_workflows`).
- transcript: the `~/.claude/projects/<slug>/<sessionId>.jsonl` full turn history that `--resume` / `--continue` / `--fork-session` re-open (§01.2); the `.jsonl` is portable across machines.
- managed block: the `>>> claude-research-toolkit (managed) >>>` … `<<<` markers the installer regenerates, leaving your out-of-block content intact (§01.2).
- `@import`: a CLAUDE.md directive that pulls another file's content in (nesting depth up to 4) (§01.2).
- context rot: as the token count in the window grows, the model's ability to accurately RECALL any given item DEGRADES (a transformer's n² attention stretched thin) ⇒ the reason to budget context (§00.2; `08_context_engineering`).
- agentic search: retrieving at RUNTIME by traversing the filesystem + grep + following references (like an engineer), vs pre-indexing the repo into a stale vector store (RAG) (§00.2).
- context engineering: the discipline of curating the SMALLEST high-signal token set the model sees each turn — the SUCCESSOR to prompt engineering (curate the whole token set, not one turn's words) (`08_context_engineering`).
- progressive disclosure: a skill loads only its `name` + `description` at session start; the full body loads on invocation ⇒ pay context only on demand (`02_skills_and_commands`; the purest expression of §00.2).
- MCP (Model Context Protocol): an OPEN protocol that exposes external tools + data to Claude as a client — "USB-C for AI"; a server exposes TOOLS / RESOURCES / PROMPTS, Claude Code is an MCP client (`09_going_further`).
- sandbox: filesystem + network ISOLATION that contains an autonomous run so it needs fewer per-command prompts; credentials live OUTSIDE it, so a prompt-injected process inside cannot exfiltrate them (`09_going_further`).
- plugin: an installable BUNDLE of slash-commands + subagents + MCP servers + hooks, distributed via marketplaces (a git repo of plugins) ⇒ identical capability for a teammate on day one (`09_going_further`).
- Agent SDK: the SAME agent loop + tools + context manager as Claude Code, exposed as a CLI + Python / TypeScript libraries to embed in your own scripts / CI; headless = run non-interactively, driven by a program (`09_going_further`).

## SOURCES
The consolidated reference list above (§ 00.4) is the single source list for the whole ADVANCED set; each `NN_*` doc points here rather than repeating it.
