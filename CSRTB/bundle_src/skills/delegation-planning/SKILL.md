---
name: delegation-planning
description: Invoke WHEN planning HOW to distribute a task across agents — map each subtask to the specialist PROFILE (the why/which) + SKILL (the how) that fits it, assign each delegated subtask a difficulty tier → model (kernel TIER_TABLE; never claude-opus-5), and decide whether to run a multi-agent cascade and which of the four topologies (parallel-wave / sequential-build / convergence / verify-loop) matches the work, or rule cascade OUT for tightly-coupled single-thread work. Owns the decision procedure + machine-readable routing block behind the Delegation & Routing section every /plan now requires, and the kernel gates (model_route_gate, plan_lint, route_receipt_audit). Fires on "which specialist/skill for this subtask", "should this be a cascade", "which topology", "which model for this child", "route this plan". NOT the planner persona (→ PLANNER profile) and NOT concurrency sizing (→ preflight-parallel).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# delegation-planning — route subtasks to specialists/skills and pick the cascade topology
# WHAT: the decision procedure for a plan's **Delegation & Routing** — (A) which specialist PROFILE + SKILL owns each subtask, (B) whether the work earns a cascade, (C) which of four topologies fits, (D) the section a /plan must emit. This is the HOW of routing; it does not carry the planner persona or execute anything.

## When to invoke
WHEN building a plan and about to decide who does each part ⇒ apply this. Concretely: writing the Delegation & Routing section a `/plan` now mandates · choosing between doing a step yourself vs `host.delegate` · deciding whether a step is a single-agent job or a multi-agent cascade · picking a cascade topology · matching a subtask to one of the user's specialist profiles.

## The signature error this prevents
**Reflexive cascade + charter-mismatch routing** — the two failures this skill exists to stop:
1. Fanning out tightly-COUPLED single-thread work (authoring one coherent doc, a context-heavy edit, a single-point decision) into sub-agents that each lose the context the work depends on — overhead with no parallelism gain.
2. Routing a subtask to a specialist whose ONE job does not cover it (e.g. a backward-looking rational-reconstruction specialist handed forward-looking orchestration) — a plausible-looking assignment that quietly produces the wrong kind of work.
A liberal-cascade preference makes #1 the standing risk; the fix is not fewer cascades but RIGHT ones — route by coupling and charter, not by reflex.

## Load-bearing move — route by COUPLING + INDEPENDENCE, not by reflex
The default execution mode is **single-thread (do it yourself)**. A delegation or cascade must EARN its place against its cost. Decide in this order:
1. Does the subtask name a distinct discipline/method one of the user's specialists owns? ⇒ route to that specialist + its skill (Part A).
2. Do the pieces have genuinely INDEPENDENT tracks, or does one phase bloat context before the next needs a clean slate, or does the judgment want independent viewpoints, or does the output need adversarial verification? ⇒ a cascade earns its place (Part B) — pick the topology by dependency shape (Part C).
3. Otherwise (coupled, single-thread, context-heavy, single-point) ⇒ do it yourself and file the node **EXECUTION: main-agent**. You may still name the discipline whose skill you load (**OWNER: <SPECIALIST> — discipline only**): OWNER (which expertise) and EXECUTION (who runs it) are separate facts, and a node you run yourself is main-agent — never a delegation.
Honesty is about FILING, not just reasoning: if the reason to stay single-thread is "coupled, I hold the context", file the node **EXECUTION: main-agent** — never as a delegation you then decline to run. Two symmetric fabrications are both wrong: a fabricated parallelism (spawning sub-agents to look thorough) and a fabricated delegation (a delegations node you always meant to do yourself). File the mode you will actually use.

## Part A — subtask → specialist PROFILE + SKILL (the routing move)
The customization layer splits every job in two: a **PROFILE owns the WHY/WHICH** (method selection + interpretation, disclaims implementation) and a **SKILL owns the HOW** (the hard-won procedure). So routing a subtask = name BOTH: the specialist whose one-job covers the subtask's dominant discipline, AND the skill(s) that specialist loads to do it.
- STEP ZERO — recognize the ARCHETYPE first. WHEN about to route a task/subtask ⇒ FIRST name its request archetype via the `request-archetypes` registry (handoff document, planning, skill/agent authoring, code review, data indexing, figure, methods doc, stats-method choice, manuscript, …); adopt that archetype's canonical specialists + skills + OUTPUT FORM as the default, THEN refine per the coupling rules below. The registry is the empirical shortcut to the right carriers; this Part A is how you adjust when the archetype is ambiguous or spans two. A handoff/consolidation request ⇒ output FORM is ALWAYS machine-md (via `handoff-brief`), NEVER freehand prose — the single most-missed mapping.
- WHEN a subtask names a distinct discipline/method ⇒ name the specialist + skill for it (e.g. "recover the design rationale" → DESIGN_RATIONALE_ANALYST + `design-rationale`; "tighten this prompt" → PROMPT_ENGINEER + `eliciting-llm-behavior`; "author a hook/skill/profile" → AGENT_TOOLING_ENGINEER + `machine-md`; "implement/refactor a pipeline, module, or CLI" → SOFTWARE_DEVELOPER + `software-craft` [+ `testing-discipline`/`refactoring` as the work demands], with CODE_REVIEW_DEBUGGER as the verify-loop reviewer).
- WHEN no specialist's charter fits ⇒ say so — it is main-agent / generalist work. Do NOT force-fit to the nearest-sounding specialist; charter-mismatch is the silent failure (see signature error #2).
- WHEN the subtask is purely a library/procedure with no persona judgment ⇒ a SKILL alone may suffice (load it, no delegation).
- WHEN a subtask is SINGLE-THREAD but a specialist's discipline applies ⇒ set **OWNER: <SPECIALIST> — discipline only** AND **EXECUTION: main-agent** (channel that discipline / load its skill yourself). Owner names the expertise; execution names who runs it — two separate required facts. A node with EXECUTION: main-agent is not a delegation and is never filed as one, whatever its owner.
- WHEN the main agent executes a phase but a specialist should advise ONE sub-decision (a soft/partial charter fit) ⇒ OWNER = "main agent, executing; <SPECIALIST> advises on <the sub-decision>" — owner need not be a single pick.
- WHEN the task is to AUTHOR-from-scratch but the fitting specialist's charter is REVISE (e.g. a prose stylist) and the content-context lives with the main agent ⇒ do NOT delegate authoring to a reviser that cannot know the context; keep it main-agent single-thread and load the specialist's skill for the craft. Delegating context-blind is charter-coupling mis-routing (signature error #2).
- To SEE the roster before routing: `host.agents.list()` (profiles + their one-job descriptions), `host.skills.list()` / `search_skills` (skills). Match to the description's stated job, not the name.

## Part B — should this be a cascade? (the WHETHER)
A cascade (any multi-agent structure) earns its place when AT LEAST ONE holds; otherwise stay single-thread:
- **Independence** — the work splits into tracks with no cross-dependency that can run at the same time (→ parallel-wave).
- **Context isolation** — one phase would bloat the working context before a later phase needs a clean slate (→ sequential-build across a handoff).
- **Independent viewpoints** — a judgment is stronger from several divergent lenses than one (→ convergence).
- **Adversarial check** — the output is high-consequence and checkable, so it should be attacked and repaired before shipping (→ verify-loop).
Grade the tradeoff explicitly:
- COST of delegating: a sub-agent sees ONLY its task brief + `context_summary`, never your conversation — coupled/context-heavy work loses more to that blindness than it gains; plus round-trip latency and coordination overhead.
- BENEFIT: real parallelism (wall-clock), context isolation (a clean slate per track), independent adjudication (bias reduction), or adversarial hardening.
- Cascade WHEN benefit > cost. WHEN the only "benefit" is that fanning out feels thorough ⇒ that is reflex, not benefit — stay single-thread.
- SYMMETRIC guard (the under-cascade error): WHEN work IS genuinely independent (N units, no cross-dependency), OR a judgment genuinely needs independent viewpoints, OR a high-consequence output is checkable ⇒ do NOT force single-thread out of caution — keeping earning work serial mis-routes as surely as reflexive fan-out. The single-thread default breaks TIES for COUPLED work; it is not a thumb on the scale against real independence.

## Part C — the four topologies (the WHICH)  [reference]
Pick by the dependency shape between units. All fan-out runs via `host.delegate([...])` from a `repl` cell (list form = concurrent; a Python loop over single calls runs serially). All four topologies are MULTI-AGENT (they spend delegation cost); a task you run yourself step-by-step in ONE context is single-thread — even when its steps are ordered or data-dependent — do NOT label that a cascade.

1. **PARALLEL-WAVE (fan-out)** — N units, DIFFERENT input each, SAME operation, NO inter-dependence.
   WHEN: homogeneous independent work — screen each compound family, adjudicate each transcript segment, review each scenario.
   SHAPE: one `host.delegate` list call, one request per unit; collect; batch-analyze. Size concurrency with `preflight-parallel`.

2. **SEQUENTIAL-BUILD (pipeline)** — track B CONSUMES track A's output AND the tracks should run in SEPARATE agent contexts. The bare A→B data dependency is necessary but NOT sufficient: a data-dependent pipeline ONE agent can hold in a single context is single-thread cross-phase ordering, NOT this cascade. What EARNS sequential-build is CONTEXT-ISOLATION need (Part B) on top of the data dependency — A's context would bloat or distract B.
   WHEN: recover rationale → then render the explainer in a clean slate; a heavy fetch/build-A phase whose full context B does not need. NOT: two steps that merely happen in order within one context.
   SHAPE: `host.delegate` A; then a SECOND `host.delegate` for B that references A's output artifacts by literal `{{artifact:VERSION_ID}}` marker in the task (sub-agents have SEPARATE workspaces — hand files via artifacts, never relative paths).

3. **CONVERGENCE (multi-voice adjudication)** — M agents attack the SAME input from DIFFERENT lenses, then a lead synthesizes.
   WHEN: a judgment benefits from independent viewpoints / single-reviewer bias is a risk — e.g. a multi-voice enforcement pass over a requirements set, blind readers over one document.
   SHAPE: parallel fan-out with DIVERGENT briefs (a different lens per voice — enforcer / minimalist / threat-modeler / maintainer…) → lead converges the verdicts. DISTINCT from parallel-wave: same input + different lenses + a merge step, vs different inputs + same operation. A convergence with identical briefs is just redundant parallel-wave — give each voice its own lens or drop it.

4. **VERIFY-LOOP (generate → adversarial check → patch)** — produce, hand to an ADVERSARIAL reviewer told to find fault, patch, repeat until clean.
   WHEN: output correctness is high-consequence AND checkable — a shipped artifact, a rule that must fire reliably, a composed figure.
   SHAPE: build → delegate a review sub-agent with a fault-finding brief (+ `output_schema` for a parseable verdict) → converge → re-run only the affected pieces → loop, BOUNDED (≤3 rounds). The reviewer is a FRESH instance re-tasked as adversary — a fresh copy of you, or a domain specialist (e.g. CODE_REVIEW_DEBUGGER) re-briefed to attack — NOT the roster's REVIEWER profile (never a root agent). A friendly re-read is not a verify-loop; the reviewer must be adversarial and fresh.
   TERMINAL BRANCH: WHEN output still fails at the round bound ⇒ FAIL CLOSED — escalate / surface for user decision / withhold; NEVER ship the best-effort artifact. For a SAFETY-CRITICAL output (an enforcement rule, a gate) shipping unverified is the exact failure the loop guards against.
   NOT a verify-loop: an INNER diagnostic iteration inside one coupled task — fit → check convergence → refit, edit → re-run tests — is SINGLE-THREAD self-correction. "High-consequence AND checkable" names the trigger, but a quality check you perform yourself does not earn a separate adversarial agent.

Topologies COMPOSE: a build phase (single-thread OR a sequential-build) can be FOLLOWED BY a verify-loop — the build happens-before the verify; this does NOT require the build itself to be a two-agent sequential-build. A parallel-wave's units can each be a small pipeline.

## Part D — the Delegation & Routing section a /plan must emit (the WHAT)
Every plan produced under `/plan` carries an explicit Delegation & Routing section. Minimum content, per phase/track:
- **Archetype** — the recognized request archetype (from `request-archetypes`) and thus the canonical OUTPUT FORM the phase must produce (e.g. handoff ⇒ machine-md). WHEN no archetype matches ⇒ say "novel — generic handling" rather than force-fitting.
- **Owner** — the DISCIPLINE: a specialist PROFILE + SKILL(s) (Part A), OR "main agent, no specialist fits", OR "skill-only, no delegation". Owner is WHOSE EXPERTISE the work draws on — not who runs it.
- **Execution** — a MACHINE-DETECTABLE tag, exactly one per node: `EXECUTION: main-agent` (you run it inline, single-thread) OR `EXECUTION: CODE:<cmd>` (a script/CLI computes it — the instrument test's first-class outcome) OR `EXECUTION: delegate→<PROFILE>` (dispatched via host.delegate) OR a named multi-agent TOPOLOGY (Part C), each with its one-line reason. `delegate→<PROFILE>` is a COMMITMENT: a child of that profile must actually be spawned, and after each wave you verify it with `route_receipt_audit(declared, dispatched)` from this skill's kernel — the dispatched side read from the record (`host_call_log` delegate rows / `agent_name`), never from memory. Declaring `delegate→<PROFILE>` and then running the node yourself is the laundering failure — the audit makes the mismatch mechanically detectable.
- **Tradeoff** — where a cascade is chosen, the benefit that beats the delegation cost; where single-thread is chosen for work that looked parallelizable, why.
- **Concurrency (fan-out only)** — where the execution is a parallel-wave, note the unit count and that concurrency is sized against real headroom (`preflight-parallel`); a "fan out N units" line with no sizing is incomplete.
- **Level** — a topology can hold BETWEEN phases (a sequential-build ordering the phases) while each phase is single-thread WITHIN itself; state which level a cascade label applies to. Do NOT read a cross-phase ordering as a mandate to delegate each phase.
- **Model tier + effort (delegated nodes)** — every `delegate→` node names its difficulty tier (`T1` hard/long/complex incl. CliMA-Emerald-class code, `T1_hardest` for the hardest/most novel, `T2` standard, `T3` simple-draft-code-only, `T4` mechanical fan-out) and effort; the tier→model-id table is DATA in this skill's kernel (`TIER_TABLE` / `resolve_tier`) — never hand-typed ids. `claude-opus-5` is BANNED at every tier (user bar); the kernel's `model_route_gate` fails closed on it.
  - PLATFORM NOTE (CC divergence, 2026-08-04 — the ban above is UNCHANGED here): Claude CODE now permits `claude-opus-5` in ONE constrained shape — a supervised child launched via a dedicated project-scoped executor agent under a Planner's active watch, enforced by an agent-file pin carve plus dispatch-time and completion-time hooks. Science has no agent-file or hook primitive to carry that contract, so the CS ban STANDS until a CS-native supervision design lands; registered as a capability candidate.
- **Brief + access defaults (delegated nodes)** — `record_access: self-service` (the child gets the record pointer, not a précis; deviations state why), `detached: true` (brief persisted before launch, `wait=False`), and a `brief_ref` naming where the persisted brief lives.
- **Recon** — each commit-class node STATES its `recon_done` evidence (the ls/count/read that surveyed the territory) or `stated-none:<why>`. Stated, not adjudicated — the field makes the survey's absence visible.
- **Reserved** — a node the user has reserved for collaborative mode carries `reserved_for_user: true`; in solo mode such a node is read-only until the user weighs in.
- **Unresolved fork** — WHEN a subtask's correct owner depends on a user decision not yet made (two valid specialist routes) ⇒ OWNER = "unresolved — <the fork>, pending user choice"; surface it rather than guessing.

**The machine-readable form (the A2 routing block).** Emit the section BOTH as the prose bullets above AND as one fenced `routing` JSON block the kernel can lint — the plan is thereby an artifact later gates diff against, not just prose:
```routing
{"tracks": [{"id": "1", "task": "…", "archetype": "…|novel", "owner": "<PROFILE + skills | main agent | skill-only>",
  "executor": "MAIN-AGENT | CODE:<cmd> | delegate:<PROFILE>", "topology": "single-thread | parallel-wave | sequential-build | convergence | verify-loop",
  "model_tier": "T1|T1_hardest|T2|T3|T4|n/a", "effort": "max|high|medium|low|n/a", "detached": true,
  "brief_ref": "<artifact/path|inline|n/a>", "record_access": "self-service|precis-only:<why>|n/a",
  "recon_done": "<evidence|stated-none:<why>>", "reserved_for_user": false, "scope_ref": "<plan §|n/a>",
  "tradeoff": "…", "concurrency": "<N units, sized via preflight-parallel|n/a>"}]}
```
Run `plan_lint(routing_block)` from the kernel before surfacing the plan and let its `[[plan_lint …]]` marker land in the span. The lint's load-bearing checks: every track carries an executor tag; a `delegate:` track names a NON-SELF profile plus tier/effort/detached/record_access (the anti-theater check — the recorded failure was six declared delegation tracks of which the lead self-ran four); `recon_done` present on commit-class tracks (as a stated field); `reserved_for_user` tracks are not scheduled for autonomous mutation. A plan whose tracks pass the lint has satisfied the routing mandate; prose that gestures at "we may delegate" has NOT. And do NOT manufacture sub-phases to populate the section: a single COUPLED task is ONE track with `executor: MAIN-AGENT` — a complete, compliant block, not an under-filled one.

## Kernel — the machine half (sidecar `kernel.py`)
This skill ships a kernel (auto-importable when the skill loads: `from kernel import …`; if not bound, `exec(host.skills.read("delegation-planning", "kernel.py")["content"])`). Host-independent pure functions — fixtures run under plain python3:
- `TIER_TABLE` / `resolve_tier(tier)` — the SINGLE-SOURCE difficulty-tier → model-id map (T1 default `claude-opus-4-8` max effort; `T1_hardest` `claude-fable-5`; T2/T3 `claude-sonnet-5`; T4 `claude-haiku-4-5`). Fails closed on an unknown tier. Ids live in kernel.py plus this sanctioned spec-echo (and the frozen A2 spec); all OTHER prose names tiers, not ids. INVOCATION — [SUPERSEDED 2026-08-04, both halves measured FALSE on Claude Code] ~~on Claude CODE `claude-fable-5` is the configured subagent DEFAULT and is invoked by OMITTING the Task call's model param, because naming it explicitly can silently resolve to the BANNED `claude-opus-5`.~~ CORRECTED (CC-MEASURED, CS-UNMEASURED — re-measure before relying): on Claude CODE an omitted model param requests the MAIN model, and the observed `claude-opus-5` arrivals were a SERVING-side substitution of fable requests (an open vendor bug), not alias resolution. NEITHER finding transfers here: Science delegates through `host.delegate(model=…)`, a DIFFERENT mechanism whose resolution AND serving behavior have not been measured on this platform; until they are, pass the tier's id explicitly.
- `model_route_gate(route_map)` — fail-closed check of an intended `{child: model_id}` map: FAIL on `claude-opus-5`, on any id not in the table (or not confirmed via an injected `list_models`), else PASS. Emits `[[route_gate n=N verdict=…]]`.
- `plan_lint(routing_block)` — the Part-D block checks above. Emits `[[plan_lint tracks=N verdict=…]]`.
- `route_receipt_audit(declared, dispatched)` — post-wave: declared `delegate:` tracks vs the children actually dispatched (pass the record's delegate rows in); FAIL lists unhonored declarations (delegation theater) and undeclared dispatches. Emits `[[route_audit …]]`.
FIRING (honest scope): Claude Science has no hooks — these are `[DISCRETION]`-fired by named carriers: the PLANNER profile's standing mandates (`plan_lint` at plan-emit, `model_route_gate` before dispatch, `route_receipt_audit` when a wave's results land, `confirm_before_stop` via directing-execution at any stop) and the `plan` skill's RULE.route_the_plan (lint before surfacing; audit post-wave). The auditable object is the MARKER: a dispatching or plan-emitting span with no `[[route_gate|plan_lint …]]` marker is expected to draw the background Reviewer's omission flag (extrapolated from the self-check gate's demonstrated behavior; unmeasured yet for these markers). A marker is detection + re-checkability, not prevention.

## Non-goals (redirect to the named sibling)
- The planner PERSONA and the always-fire-on-/plan mandate ⇒ the `plan` skill (owns the rule) + the PLANNER profile (owns the persona). This skill is the HOW they invoke, not the trigger.
- Sizing a fan-out's concurrency against real headroom ⇒ `preflight-parallel`.
- Writing the delegate task brief's PROSE so the sub-agent reliably complies ⇒ `eliciting-llm-behavior` (technique) + `machine-md` (form).
- The `host.delegate` / `host.agents` SDK signatures (wait, output_schema, context_summary, waves) ⇒ `customize`.
- Executing the plan / doing the domain work ⇒ the routed specialists themselves.

INVARIANT: route by coupling and independence, not by reflex; name a specialist + skill for each subtask or call it main-agent work; pick the topology that matches the dependency shape; and make every cascade earn its place against its context-loss and latency cost.
REF: `plan` (mandates the Delegation & Routing section this skill fills) · PLANNER profile (the persona that drives it) · `preflight-parallel` (concurrency sizing) · `eliciting-llm-behavior` + `machine-md` (the task-brief's technique + form) · `customize` (host.delegate / host.agents signatures).
