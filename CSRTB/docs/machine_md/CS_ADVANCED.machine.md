# CS_ADVANCED.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-08-03). The architecture + extension + orchestration guide for Claude Science (CSRTB bundle v2.11; 52 skills / 18 profiles). Folds the PORTABLE content of the CCRT advanced/00–11 chapter set, CS-atomized (profiles / skills / kernels / host.*), per DC1_doc_equivalence_matrix rows R4 + A00–A11. Machine root = authoritative; the human twin CS_ADVANCED.md is a derived, atom-preserving translation.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: how to EXTEND + ORCHESTRATE Claude Science — the profiles/skills/kernels architecture · the host.* API surface · orchestration via host.delegate · memory-as-poison-surface + currency · authoring your own extensions to the bundle contract.
# FOR: a user past CS_QUICKSTART / CS_USAGE_DETAILED who wants to get the most out of Claude Science and add their own capability — not "how do I start" but "how do I get the most out of it + change it".
# DOC SET (cross-reference ONLY these): CS_README · CS_QUICKSTART · CS_USAGE_DETAILED · CS_ADVANCED · CS_INSTALL_STARTER_v2.11.
# STYLE: machine-terse, front-loaded, positive action-first; per-section shape FOR → HANDLE → mechanics → INVARIANT → FEEDS (inherited from the source chapters).
# COUNTS (recomputed 2026-08-02 from crt_science_bundle.json — `python3 -c "import json; b=json.load(open('crt_science_bundle.json')); print(len(b['skills']), len(b['profiles']))"` prints `52 18`): 52 skills / 18 profiles. NEVER carry CC's "21 skills + 5 agents".
# SOURCING NOTE: sourced from the advanced/00–11 chapter files (the LIVE owner), NOT the self-superseded top-level ADVANCED monolith (matrix DELTA-2). CC-only atoms (settings/scopes/hooks, stock slash-commands, /loop mechanics, MCP/plugins/headless/sandbox, CC doc links) are OMITTED and named honestly in §8; the A09 host.* custom-tool analogue is DEFERRED (§8).

> WHAT THIS IS: the ADVANCED guide to Claude Science — its EXTENSION ARCHITECTURE (the skills + profiles you ship in the bundle) and advanced ORCHESTRATION (delegation, loops, dynamic workflows, memory + context engineering). Read §0 for the big picture and the one tying idea, then the numbered section for depth.

## 0 · ORIENTATION — THE ONE IDEA + THE MAP

- FOR: placing yourself — who this is for, the tying idea every later tactic is a lever on, and the map of the sections.
- HANDLE: the model is an ENGINE; the harness is the whole car around it — its fuel lines = context, its dashboard = the profile system_prompt + auto-recalled memory, its attachments = skills + kernels. Tuning the car beats swapping the engine.
- **The harness beats the model.** Claude Science's behavior is shaped by a layered instruction system — the active PROFILE's system_prompt, the SKILL descriptions host.skills keeps in context, the KERNEL gates a skill runs, and the project MEMORY that auto-recalls — not the raw weights. Pick the mechanism whose context-cost + authority fit the job: an always-true directive ⇒ the profile system_prompt or an always-on skill; a procedure ⇒ a skill loaded on demand; a deterministic check ⇒ a kernel gate, not a prose instruction.
- **Budget context like it is scarce — because it is.** Context rot: as the token count in the window grows, the model's ability to accurately RECALL any given item DEGRADES (a transformer's n² attention stretched thin). Treat context as a depleting attention budget. This ONE constraint is WHY every method here exists — targeted inclusion, session hygiene, and child-context isolation are all context-preservation moves, not style preferences ([Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
- **Include on target, not on spec.** Aim for the smallest set of high-signal tokens that maximizes the odds of the desired outcome — the Goldilocks zone between too-much (dilutes attention) and too-little (navigates blind). NAME the in-scope objects up front; keep the auto-recalled memory dense; re-scope a polluted context rather than fighting it.
- **Search live; don't pre-index.** Retrieve at RUNTIME — read the workspace files, read a skill's body with `host.skills.read`, search the artifact store when a step needs it — rather than pre-loading everything or trusting a stale pre-built index. Hold the lightweight identifier (an artifact id, a skill name, a path); open the object on demand.
- INVARIANT: the finite, degrading context window is the MASTER constraint — every extension point + workflow is a lever on WHAT fills it and WHEN ⇒ judge any tactic by one question: does this spend high-signal tokens, or waste the budget?
- THE MAP (this doc): §1 the CS extension architecture (profiles/skills/kernels) · §2 the host.* API surface · §3 skills, mastered · §4 profiles & delegation · §5 orchestration & patterns · §6 memory-as-poison-surface + context engineering · §7 authoring your own extensions · §8 what Claude Code has that Science lacks (honest omissions + one defer) · §9 references + glossary.
- RE-POINT (vs Claude Code): CC's three install SCOPES (User/Project/Managed), its `~/.claude` file-drop, and its reference links have NO CS analogue — the CS structure is `bundle_src/{skills,profiles}` built into ONE account (§1); the CC-only surface is named in §8.

## 1 · THE CS EXTENSION ARCHITECTURE (pillar i)

- FOR: everything that customizes Claude Science is a SKILL or a PROFILE shipped in the bundle; kernels are the deterministic helpers skills carry.
- HANDLE: two shapes + one sidecar — a SKILL (a folder of instructions the session loads on demand), a PROFILE (a named specialist you dispatch), and a KERNEL (a `kernel.py` of gate/helper functions a skill's prose calls).
- SKILL = a FOLDER: `bundle_src/skills/<name>/SKILL.md` (frontmatter `name` + `description` + body) + optional `kernel.py` (+ `references/`, `fixtures_kernel.py`). host.skills keeps every skill's `description` in context; the body loads only when invoked (progressive disclosure, §3). 52 skills ship; 19 carry a kernel.
- PROFILE = a `.json` SPECIALIST: `bundle_src/profiles/<NAME>.json` — `name`, `display_name`, `description`, `system_prompt`, optional `skillNames`. A profile is a whole specialist persona you dispatch via host.delegate (§4). 18 profiles ship.
- KERNEL = a `kernel.py` SIDECAR: deterministic functions (gates, routing tables, helpers) a skill's instructions load and run, rather than re-reasoning them each turn. Loaded with `exec(host.skills.read("<skill>", "kernel.py")["content"])`; a gate returns a verdict dict carrying a `marker` (PASS/FAIL). This is the CS "ship scripts, don't re-derive boilerplate".
- THE BUNDLE PIPELINE: `bundle_src/{skills,profiles}` → `build_crt_science_bundle.py --src bundle_src --config build_config.json --out crt_science_bundle.json` (run FROM the bundle dir) → `install_crt_science.py` installs into the Science account. BUNDLE-LAW: the build discovers ONLY `skills/` + `profiles/` — the built JSON carries `skills[]` + `profiles[]` and NOTHING else; there is NO doc carrier in the bundle (this doc is a repo-side reference, not an installed object).
- INVARIANT: a customization's KIND is decided by its SHAPE (folder ⇒ skill · `.json` ⇒ profile · `kernel.py` ⇒ sidecar), and the bundle installs into the ONE Science account — there is no per-scope reach to choose, and no file-drop location that changes who gets it.
- FEEDS: the host.* calls that read + dispatch these objects are §2; authoring one to the contract + rebuild gates is §7; the CC-only scope/settings/hooks surface this replaces is §8.

## 2 · THE host.* API SURFACE (pillar ii)

- FOR: the action surface a Science session drives — reading + editing skills, dispatching children, running code, reaching user-side connectors, and the durable stores.
- HANDLE: everything is a `host.*` call from a `repl` cell — the CS analog of Claude Code's tool loop; the repl (Python) is where you `exec` kernels and call the API.
- host.skills — `host.skills.read(name, file)["content"]` reads a skill's `SKILL.md` or `kernel.py`; `exec(...)` the kernel content to load its functions. `host.skills.edit(name, file, content)` edits a skill file AND re-runs the sidecar gate (a bad edit is refused with the gate message — never retry-edit past it).
- host.delegate — `host.delegate([{ "task": ..., "name": ..., "model": ... }])` dispatches one or more children, each running in its OWN context window; returns each child's result (with a model field / frames record). The CS analog of the CC Task tool / subagents (§4).
- host.mcp — `host.mcp(connector, action, **kw)` calls a user-side MCP connector on the user's machine (e.g. the `hands-free-alert` audible beep). FIRE-AND-FORGET: often unreachable (tunnels churn) ⇒ wrap in `try/except Exception: pass`; a failed connector must never delay or be narrated.
- PROJECT-MEMORY — durable memory that AUTO-RECALLS across sessions. This is the CS poison surface (§6): only memory auto-recalls; a stale row is re-read as current every login.
- ARTIFACTS + LINEAGE — durable stored objects that are INERT until searched (they do NOT auto-recall). `host.lineage[vid]["code"]` reproduces a shipped artifact's own code (the primary record for a "what does it do NOW" question, §6). `host.artifacts` exposes versions, but `latest` is last-writer-wins ⇒ PIN an explicit `version_id` rather than trusting `latest`.
- INVARIANT: `host.*` is the whole action surface and permission is the ACCOUNT's, not a per-command allow/deny list you tune — an unattended run is bounded by which connectors + stores exist, not by a settings deny-list (contrast CC, §8).
- FEEDS: host.delegate drives §4–§5; project-memory + artifacts are the substrate of §6; host.skills.read/edit + the sidecar gate are the authoring loop §7. DEFER: a CS-native "author your own host.* custom tool" treatment (the A09 analogue) is out of scope here — §8.

## 3 · SKILLS, MASTERED (pillar iv foundation)

- FOR: the deepest extension point — turning a generalist into a SPECIALIST at YOUR task, cheaply, via a folder the session loads only when relevant.
- HANDLE: building a skill is like writing an onboarding guide for a new hire — the doc a competent generalist needs to do THIS job THIS team's way ([Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)).
- **A skill is a FOLDER, not a file** — it can carry `kernel.py`, `references/*`, fixtures beside `SKILL.md`, discovered + loaded on demand.
- **Progressive disclosure = the filesystem AS context engineering.** Three load levels: (1) the `description` loads at session start (host.skills keeps it in context); (2) the `SKILL.md` body loads only when the skill is judged relevant; (3) `references/*` load only as a task branch needs them. The context a skill can bundle is effectively unbounded because you pay only for the branch touched ([Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)). `description` ≤ 1024 folded chars (the sidecar contract, §7).
- INVARIANT (description is load-bearing): the `description` is the ONLY part loaded until a trigger fires ⇒ it alone decides whether the skill EVER activates. Write it as a specific, positive, trigger-phrased sentence naming WHEN it fires (include the words a user will actually say), not a vague summary — a precise description outweighs a perfect body the model never reaches.
- THE NINE CATEGORIES — a good skill fits exactly ONE cleanly: library/API reference · product verification · data fetching/analysis · business-process automation · code scaffolding · code quality/review · CI-CD/deployment · runbooks · infra ops.
- HIGH-LEVERAGE AUTHORING (from How we use Skills):
  - **Lead with the Gotchas** — the highest-signal section; encode the traps you actually hit, not the happy path the model already handles.
  - **Ship a kernel, don't make the model rebuild boilerplate** — deterministic ops (sorting, parsing, a gate) belong in `kernel.py` (cheaper + exact), loaded + run in a repl cell; spend turns on composition, not reconstruction. (The CS twist on "ship scripts".)
  - **Compose skills by name** — reference another installed skill inside your instructions; build small single-purpose skills and let them chain.
  - **Give latitude, not rails** — provide the information + freedom to adapt, not a rigid step list that snaps when the situation differs.
  - **Skip the obvious** — spend context on YOUR conventions + gotchas + non-obvious constraints, not generic practice the model already knows.
- FEEDS: skills are dispatched-cousin to profiles (§4); their kernels are gates in the orchestration loop (§5); the authoring loop that keeps a skill's machine root, audit, and human twin in sync is §7.

## 4 · PROFILES & DELEGATION (fold of A03)

- FOR: handing a bounded job to a SEPARATE context window so the main thread stays clean.
- HANDLE: a profile = a named specialist; "delegation" names the RELATIONSHIP (the main thread calls it), not a different kind of thing — the CS analog of a Claude Code subagent (same mechanism, CS atoms).
- SAME THING: a profile dispatched via `host.delegate` runs in its OWN fresh context window; only its distilled RESULT returns to the main thread.
- DEFINED in `bundle_src/profiles/<NAME>.json` — `name`, `display_name`, `description` (the auto-match text), `system_prompt` (the persona), optional `skillNames` (skills it should load). 18 profiles ship; `GENERALIST` is the catch-all.
- DISPATCH: `host.delegate([{ "task", "name", "model" }, ...])` — one call can fan out several children. Pick the child's `model` per task difficulty via the delegation-planning kernel's tier table; NEVER `claude-opus-5` and never bare `opus` (a TIER-S ban — the `model_route_gate` kernel returns verdict=FAIL on it).
- INVARIANT: a delegated child spends a SEPARATE context window ⇒ its intermediate exploration/verification does NOT accrue to the main thread; only the distilled summary returns. That isolation IS the reason to delegate.
- FEEDS: many children orchestrated into a harness = §5; the isolation that keeps the main thread clean = the context discipline of §6; profiles are authored like skills, to the same contract + rebuild gates = §7.

## 5 · ORCHESTRATION & PATTERNS (fold of A04 + A05 + A06 loop-types + A07)

- FOR: the repeatable ways to compose one model + tools + children into production work — picked by the SHAPE of the task.
- SPINE — **give the child a check it can run.** With no verifiable check, YOU are the verification loop and every mistake waits for you to notice. Give a pass/fail signal — a test suite, a gate exit code, a KERNEL marker (PASS/FAIL), a fixture diff, a screenshot — and the loop closes on its own. Every pattern below is a way to MANUFACTURE that check.
- THE ONE DISTINCTION ([Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)): WORKFLOW = LLMs + tools through PREDEFINED code paths (YOU own the control flow) · AGENT = the model DYNAMICALLY DIRECTS its own process at runtime (the model owns it). Most production value is workflows; reach for a full agent only when the path can't be pre-drawn.
- THE FIVE BUILDING BLOCKS (combine the fewest that solve the task):
  - PROMPT-CHAINING ⇒ fixed sequential steps, each consuming the last's output (+ an optional gate between). WHEN the task cleanly splits into fixed subtasks.
  - ROUTING ⇒ CLASSIFY the input, dispatch to a specialist handler. WHEN distinct categories are better handled separately.
  - PARALLELIZATION ⇒ concurrent calls, aggregate — SECTIONING (independent subtasks at once) + VOTING (same task N times for confidence).
  - ORCHESTRATOR-WORKERS ⇒ a lead DYNAMICALLY splits the task, delegates to children, then SYNTHESIZES. WHEN you can't predict the subtasks up front.
  - EVALUATOR-OPTIMIZER ⇒ one generates, a second CRITIQUES against criteria, LOOP until it passes. WHEN you have clear eval criteria and iteration measurably helps.
- CORE WORKFLOWS: explore→plan→code→commit (separate research from execution — the `plan` skill) · test-first (hand the child the pass/fail check it demands) · writer/reviewer (a FRESH child can't inherit the producer's bias — dispatch `CODE_REVIEW_DEBUGGER` as the adversarial reviewer; tell it to flag ONLY correctness/requirement gaps, else a gap-seeker drives over-engineering) · parallelize independent workstreams.
- THE FOUR LOOP TYPES (repeat-until-STOP; each: what you hand off):
  - TURN-BASED — hand off the CHECK (encode your manual check as a verification skill so the child self-verifies end-to-end); best for short one-off work.
  - GOAL-BASED — hand off the STOP CONDITION (a deterministic, machine-checkable bar); an evaluator re-checks it each time the child tries to stop.
  - TIME-BASED — hand off the TRIGGER (an interval / event); best for recurring work + external systems.
  - PROACTIVE — hand off the PROMPT (a standing, well-defined stream); no human in the loop.
  - CS MAPPING: these map to the four host.delegate TOPOLOGIES named by the `delegation-planning` skill — parallel-wave · sequential-build · convergence · verify-loop. (The CC `/loop` `/goal` `/schedule` slash commands themselves are CC-only — §8.)
- THE SIX DYNAMIC-WORKFLOW PATTERNS (a harness = orchestrator-workers auto-composed per task): classify-and-act · fan-out-and-synthesize · adversarial-verification (a separate verifier vs a rubric) · generate-and-filter · tournament (pairwise judgment beats absolute scoring) · loop-until-done (for work of unknown size).
- WHY ISOLATED CHILDREN — the 3 single-context failure modes a harness fixes: AGENTIC LAZINESS (stops before finishing a multi-part task) · SELF-PREFERENTIAL BIAS (prefers its own results, especially when asked to verify them) · GOAL DRIFT (fidelity to the objective decays across turns, WORSENED by lossy compaction). The fix in one line: give each job a SEPARATE child with a CLEAN context.
- SCALING LESSONS ([Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)): DELEGATE EXPLICITLY — each child needs an objective, an output format, tool/source guidance, and CLEAR boundaries (vague briefs make children duplicate work + leave gaps) · SCALE EFFORT TO COMPLEXITY (a simple fact-find = 1 child; a comparison = 2–4; hard research = 10+ with divided responsibilities) · MINIMIZE THE GAME OF TELEPHONE — have children WRITE outputs to ARTIFACTS / workspace files and pass lightweight REFERENCES back, rather than routing everything through the coordinator's context (the supervisory-workflow discipline). ECONOMICS: agents use ~4× the tokens of chat, multi-agent ~15×; token usage ALONE explains ~80% of performance variance ⇒ a harness is justified ONLY when the task's VALUE pays for the added spend.
- QUALITY + SIMPLICITY: FIX THE SYSTEM, NOT THE INSTANCE — when a result misses the standard, ENCODE the fix (into the skill / kernel / profile) so every FUTURE child clears it. Find the SIMPLEST thing that works; add machinery only when it DEMONSTRABLY improves outcomes; don't wrap a one-shot in a loop; PILOT before a large fan-out (a harness can spawn many children).
- INVARIANT: the leverage is ISOLATED CONTEXTS — a fresh verifier can't inherit the producer's bias, a per-task child can't inherit the orchestrator's drift ⇒ that separation is precisely what defeats laziness, self-preference, and goal drift.
- FEEDS: the loop TYPES schedule the work, the six patterns STRUCTURE it, the five blocks NAME it; all run on host.delegate (§4) and are bounded by the context budget (§6).

## 6 · MEMORY AS A POISON SURFACE + CONTEXT ENGINEERING (pillar iii; fold of A08 + A01 memory-half)

- FOR: the master discipline beneath every context tactic — curate the smallest high-signal token set — AND the CS-specific hazard that durable MEMORY is what auto-recalls, so a stale memory row poisons every future session.
- CONTEXT ENGINEERING = the SUCCESSOR to prompt engineering: prompt engineering wrote one turn's words; context engineering curates the WHOLE token set the model sees each turn — system prompt + skills + retrieved data + history + memory, across a multi-turn loop ([Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
- WHY SMALL WINS: attention is a finite budget that DEGRADES as the window grows (context rot) ⇒ more tokens = lower signal per token + diminishing returns. Optimize for the smallest high-signal set, never the largest context.
- THE LEVERS: ALTITUDE — tune the system prompt to the Goldilocks zone (too low = brittle if-else that overfits; too high = vague guidance that gives no steer) · JUST-IN-TIME — hold lightweight identifiers (artifact ids, skill names, paths) in the window, load the underlying data at runtime · COMPACTION — as history nears the limit, summarize + reinitialize a fresh window, PRESERVING the load-bearing atoms (decisions, unresolved bugs, the contract) and DROPPING the redundant · STRUCTURED NOTE-TAKING — persist durable state OUTSIDE the window and pull it back only when relevant.
- THE CS POISON SURFACE (the pillar — this is where CS differs sharply from CC): on Claude Science, durable MEMORY auto-recalls across sessions, while ARTIFACTS are INERT until searched. ⇒ a durable STATE memory row frozen as "DONE / GREEN / 51 skills" is re-read as CURRENT every login, silently misleading the session (passive staleness); an injection that lands in a durable memory surface persists and is re-read as current (the adversarial vector). The currency discipline:
  - ONE canonical memory row PER TOPIC — supersede it IN PLACE. Never append a second "current" row that disagrees with the first; two current rows that diverge are the WORST poison (the divergence is undetectable to a future reader).
  - Keep done-records, snapshots, and closed logs as INERT ARTIFACTS, NOT memory rows — so they do not auto-recall as if live.
  - PROVENANCE OVER DESCRIPTION — answer a "what does it do NOW" question from the PRIMARY RECORD (the shipped skill/profile bytes; `host.lineage[vid]["code"]`), not from a memory row that DESCRIBES it. Agreement among several memory rows is ZERO additional evidence until one is confirmed to be the record — non-independent descriptions echo, they do not corroborate.
  - VERIFY THE VERIFIER (the VLOOP principle) — a count or status written into memory is a CLAIM ABOUT A FILE and goes stale silently ("N skills" is true until someone adds the N+1th; the sentence does not update itself). Never hardcode such a number ⇒ re-derive it at check time and compare against what you just measured (the `check_currency` / `provenance-guard` / `verification-loop` gates), and never trust a gate you have not shown catches its target defect.
- INVARIANT: on CS the durable-memory surface IS the poison surface ⇒ keep ONE canonical row per topic, supersede in place, hold inert records as artifacts not memory, and re-derive every count/status at read time from the primary record.
- FEEDS: this is the theory the levers of §0 implement; the primary-record habit is the substrate of the authoring loop's "change the source, not the description" (§7); child-context isolation (§4–§5) is just this discipline applied per delegate.

## 7 · AUTHORING YOUR OWN EXTENSIONS ON CS (pillar iv; fold of A10)

- FOR: a repeatable loop to build your own skill / profile / kernel to the bundle's own standard.
- THE DOC LOOP: draft with the `machine-md` skill (applies LLM-doc best-practices — positive trigger-conditioned framing, output-detectable triggers, atom-preservation) → AUDIT via the `LLM_DOC_ARCHITECT` profile (CS ships NO separate machine-doc-reviewer profile — the audit role folds into LLM_DOC_ARCHITECT) → render the human/PDF twin with `folio-science` (offline pandoc + typst) and the `doc-pipeline` skill. The machine root stays the authoritative source; the human `.md` + PDF are DERIVED (doc-style INVARIANT.machine_is_root).
- AUTHOR A NEW SKILL: create `bundle_src/skills/<name>/SKILL.md` (frontmatter `name` + a trigger-phrased `description` ≤ 1024 folded chars) + optional `kernel.py`.
- THE SIDECAR CONTRACT (the 2026-07-28 install-breaker — author to it from the START): a `kernel.py` module TOP LEVEL holds plain-name function defs + imports + literal-constant assigns ONLY — NO computed values (`re.compile` / `frozenset` / any Call), NO `_`-prefixed names (defs or assigns), NO top-level `if` including the `__main__` guard. `check_sidecar_contract.py` must exit 0 BEFORE any build.
- AUTHOR A NEW PROFILE: create `bundle_src/profiles/<NAME>.json` — `name`, `display_name`, `description` (trigger-phrased), `system_prompt` (the persona), optional `skillNames`.
- REBUILD + GATE (the mirror discipline): a `bundle_src/` edit ⇒ rebuild via `build_crt_science_bundle.py --src bundle_src --config build_config.json --out crt_science_bundle.json` (run FROM the bundle dir) ⇒ `check_bundle_parity.py` (build + `--strict-bytes` + manifest) ⇒ `check_sidecar_contract.py`. NEVER hand-edit `crt_science_bundle.json`. Then `install_crt_science(overwrite=True)` into the account (differing profiles are silently SKIPPED without `overwrite`). Carrier skill: `toolkit-extension-authoring`.
- A TIER-C content change owes its CC twin the RE-EXPRESSION in that platform's atoms (host.delegate ↔ Task tool; artifacts ↔ files) — never a byte-copy across the boundary. (TIER-C per the twin-architecture tier model; TIER-S items share content AND carrier, so a change propagates as the same change.)
- INVARIANT: the machine root / source object is the authoritative source; the human twin + PDF + built JSON are DERIVED ⇒ change behavior by editing the source skill/profile + rebuilding, never by editing the built JSON or a description of it.
- EFFICACY DISCIPLINE: a new fix ships `attempted-untested` until a MEASUREMENT (the `countermeasure-audit` sweep) shows the failure rate dropped — existence is not efficacy; no "works" without a cited measurement.
- FEEDS: the sidecar gate + build gates are the §5 "verifiable check" applied to the toolkit itself; the "edit the source, not the description" rule is §6's provenance discipline; every authored object is a §1 skill/profile in the bundle.

## 8 · WHAT CLAUDE CODE HAS THAT SCIENCE LACKS (honest omissions + one defer)

Platform honesty, not silence — these Claude Code chapters have NO CS analogue and are OMITTED above; naming them keeps the port trustworthy:
- INSTALL SCOPES + FILE-DROP + SETTINGS + PERMISSIONS (CC advanced 01) — CC's three scopes (User/Project/Managed), the `~/.claude` file-drop, `settings.json` precedence + deep-merge, and the `permissions` allow/ask/deny list have no CS equivalent. CS installs into the ONE account; permission is the account's, not a per-command deny-list you tune (§2).
- HOOKS (CC advanced 01–02) — CC's deterministic event scripts (PreToolUse / PostToolUse / UserPromptSubmit / Stop / …, ~30 events, stdin-JSON I/O) do NOT exist on CS. There is NO turn-end or event hook ⇒ anything CC does with a hook, CS must do agent-initiated (e.g. the turn-end audible beep is the `audible-alert` skill fired by the profile itself, not a Stop hook).
- THE STOCK SLASH-COMMAND CATALOG (CC advanced 02) — CC's built-in `/`-verbs are CLI built-ins; CS surfaces only the few authored as skills (`solo`, `plan`, `collab`).
- THE `/loop` `/goal` `/schedule` LOOP-COMMAND MECHANICS (CC advanced 06) — the loop TYPES fold into §5 as host.delegate topologies, but the CC slash-command primitives themselves are CC-only.
- MCP SERVERS · PLUGINS/MARKETPLACES · HEADLESS `claude -p` / AGENT SDK · OS-LEVEL SANDBOXING (CC advanced 09) — all CC-platform, no CS analogue. (`host.mcp` reaches a single user-side connector; it is NOT the MCP client/server ecosystem, plugin bundling, or a sandbox wall.)
- CC-SPECIFIC DOC LINKS (CC advanced 11) — the `code.claude.com/docs/en/…` product URLs are CC-only and are dropped from §9.
- DEFER (the one real CS analogue held for later): the transferable A09 kernel — "the platform exposes tools you design FOR agents" — maps to the CS `host.*` / custom-tool surface. A CS-native "author your own host.* tool" treatment is DEFERRED to a later wave (source principle: [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)); it is NOT a byte-port of the CC MCP chapter.

## 9 · REFERENCES + GLOSSARY (fold of A11 portable half)

REFERENCES — the platform-agnostic sources the folded concepts genuinely rest on (the CC-product doc links are dropped as CC-only, per §8):
- **Building effective agents** — https://www.anthropic.com/engineering/building-effective-agents — the workflows-vs-agents distinction; the 5 building blocks; the simplicity thesis.
- **Effective context engineering for AI agents** — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents — context as the master finite resource; context rot; just-in-time loading; compaction; altitude.
- **Equipping agents for the real world with Agent Skills** — https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills — skills as progressive-disclosure capability packages (pay context only on demand).
- **How we built our multi-agent research system** — https://www.anthropic.com/engineering/multi-agent-research-system — orchestrator-workers at scale; the economics + scaling lessons.
- **Writing effective tools for AI agents** — https://www.anthropic.com/engineering/writing-tools-for-agents — tool-design principles (the DEFERRED host.* authoring source, §8).

GLOSSARY (advanced; re-termed to CS):
- profile: a named specialist persona (`bundle_src/profiles/<NAME>.json`) dispatched via host.delegate — the CS analog of a CC subagent (§4).
- skill: a FOLDER (`SKILL.md` + optional `kernel.py` + `references/`) whose `description` auto-loads and whose body loads on demand (§3).
- kernel (sidecar): a skill's `kernel.py` of deterministic gate/helper functions, loaded via `exec(host.skills.read(...)["content"])`; a gate returns a `marker` verdict (§1).
- sidecar contract: the top-level `kernel.py` rule (plain defs/imports/literal assigns only; no computed values, no `_`-names, no top-level `if`/`__main__`); `check_sidecar_contract.py` exit 0 before build (§7).
- host.delegate: the API call that dispatches a profile into its own context window and returns its result — the CS analog of the CC Task tool (§2, §4).
- host.skills: the API to read/edit a skill's files (`.read` / `.edit`); `.edit` re-runs the sidecar gate (§2).
- project-memory: durable memory that AUTO-RECALLS across sessions — the CS poison surface (§6).
- artifact + lineage: durable stored objects, INERT until searched; `host.lineage[vid]["code"]` reproduces the shipped bytes (the primary record); pin an explicit `version_id`, not `latest` (§2, §6).
- progressive disclosure: a skill loads only its `description` up front; the body + references load on demand ⇒ pay context only on demand (§3).
- context rot: as the token count in the window grows, the model's accurate RECALL of any given item DEGRADES ⇒ the reason to budget context (§0, §6).
- context engineering: curating the smallest high-signal token set the model sees each turn — the successor to prompt engineering (§6).
- the four topologies: parallel-wave · sequential-build · convergence · verify-loop — the host.delegate shapes the loop types map to (delegation-planning skill; §5).
- the six patterns: classify-and-act · fan-out-and-synthesize · adversarial-verification · generate-and-filter · tournament · loop-until-done (§5).
- the five blocks: prompt-chaining · routing · parallelization · orchestrator-workers · evaluator-optimizer (§5).
- VLOOP (verify the verifier): re-derive a count/status at check time + never trust a gate not shown to catch its defect (§6).

## SOURCES
In-text hyperlinks cite the paraphrased platform-agnostic sources; the CC-product operational docs are intentionally omitted (§8). The authoritative record for what the bundle currently IS = the shipped `crt_science_bundle.json` (recount, header), not this prose (§6, provenance over description).
