# CS_USAGE_DETAILED.machine.md
# STATUS: CURRENT (2026-08-03). Authored for CSRTB v2.11 — bundle = 52 skills / 18 profiles (recomputed from crt_science_bundle.json this date). CS-atomized port of the CCRT USAGE_DETAILED spine (MAP → PART A → PART B → PART C); re-expressed in Claude Science primitives, never byte-copied across the platform boundary.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Machine-optimized ROOT for the DETAILED usage guide — the AUTHORITATIVE source. Human twin = ../human_md/CS_USAGE_DETAILED.md; the .md + .pdf are DERIVED from this file (render via doc-pipeline/folio-science). Edit HERE first, then propagate machine→human→pdf.
# BUNDLE MEMBERSHIP: REPO-SIDE — a bundle-dir reference doc read by a human/user/session; NOT installed into the CS account, does NOT touch bundle_src, reruns NO build/parity/manifest gate.
# AUDIENCE: a scientist who can open a Claude Science conversation but knows little else. Teaches Claude Science from near-zero → how the Research Toolkit BUNDLE augments it → how to use it for research.
# SPINE: the skeleton IS Claude Science's functional architecture (the PRIMITIVES) ⇒ reason about capabilities, don't memorize a feature list. MAP (mental model) → PART A (base Claude Science, by function) → PART B (bundle overlay) → PART C (in practice).
# STYLE: machine-terse, front-loaded, positive/action-first (this is the source; the human .md/.pdf are derived).
# DOC SET (cross-reference ONLY these): CS_README (front door) · CS_QUICKSTART (day-one, read FIRST if new) · CS_USAGE_DETAILED (this — reference) · CS_ADVANCED (deep dive) · CS_INSTALL_STARTER_v2.11 (paste-ready install, at the bundle root).

## MAP · WHAT CLAUDE SCIENCE IS + ITS ARCHITECTURE
- ORIENTATION: two guides ship — CS_QUICKSTART (day-one, 1-2 pp; read FIRST if new) + this DETAILED (reference). This guide teaches (a) Claude Science fundamentals, (b) the bundle's augmentations, (c) research use. Both are machine→human→PDF artifacts — you are reading the human render of a `.machine.md` root. New term? → GLOSSARY.
- WHAT IT IS: Claude Science = an agentic research ENVIRONMENT — a conversation joined to a Python repl (a persistent kernel) that runs code, reads/writes durable ARTIFACTS, and dispatches specialist agents, all in a remote sandbox. Not a chat box: it runs real cells + produces real artifacts, all visible in the transcript.
- HOW IT RUNS — the TURN LOOP: you state a GOAL → it LOADS CONTEXT (+ AUTO-RECALLED project memory) → PLANS → runs repl cells + calls the `host.*` API within your account PERMISSIONS → you REVIEW → repeat. Every capability below is one layer this loop passes through.
- THE PRIMITIVES (the whole mental model; PART A takes them one at a time):
  - CONTEXT ⇒ what Claude SEES (window · auto-recalled project/profile MEMORY · loaded skills+kernels · search).
  - INSTRUCTIONS ⇒ how you STEER it (PROFILES · models+tier routing · skills that auto-load · the agency dial).
  - ACTIONS + GUARDRAILS ⇒ what it DOES + the boundary (the `host.*` API + repl · account permissions · per-host network grants · sandbox isolation).
  - DELEGATION ⇒ handing bounded jobs to specialist PROFILES via `host.delegate` + running work in the BACKGROUND/parallel.
  - DURABLE RECORD ⇒ ARTIFACTS + LINEAGE — the persistent, reproducible store (the CS analog of files + version control).
  - AUTOMATION ⇒ KERNEL sidecars — loaded gate/helper functions you (or a skill) CALL (the CS analog of CC event-hooks; call-time, not harness-fired).
- NOTE.no_config_scope: base CS has NO `~/.claude`-style settings-file scope merge — the toolkit installs into your ACCOUNT (skills + profiles), and durable steering lives in MEMORY, not a per-repo `CLAUDE.md`.
- INVARIANT: everything Claude Science can do = one of these primitives inside the turn loop; learn the primitives, derive the features.
<!--FIG: the turn loop wrapping the primitive layers (goal → context+memory-load → plan → repl/host.* calls ↔ permission/grant boundary → review → repeat) | 85% -->

## PART A · BASE CLAUDE SCIENCE, BY FUNCTION
- Each unit = one primitive, in a fixed ARC: FOR (its role) · LIKE (a handle) · mechanics · INVARIANT (the one line to carry) · COUPLES (what it connects to).

### A · THE LOOP & DRIVING IT
- FOR: running + steering Claude turn by turn — the driver's seat.
- LIKE: pair-science out loud — you set direction, it acts, you correct, repeat.
- START: open a Claude Science conversation in a PROJECT. The project scopes what persists — its artifacts (with lineage) and its memory carry across every session in it (→ CONTEXT, DURABLE RECORD).
- THE REPL: work runs as CELLS in a persistent Python kernel in a remote sandbox — Claude writes a cell, runs it, reads the output, iterates. You SEE each cell + result in the transcript (nothing hidden). The kernel state (variables, imports) persists across cells within a session until it restarts.
- PROMPT: type an instruction. BE SPECIFIC + name deliverables — e.g. "fit a `bam` AR1 model to artifact `x_v3`, save the diagnostic plot as an artifact". Reference ARTIFACTS by id/name, not by pasting their contents.
- TURNS + REVIEW: state a GOAL → it plans/acts (cells + `host.*` calls) → you REVIEW. The transcript scrolls the full action history — every cell + output shown.
- STEER MID-TASK: type a correction while a step runs; a running background job or delegated child receives a steer at its NEXT tool round (→ DELEGATION). Going wrong? restate the goal — it beats letting it run.
- INTERACTIVE by default: it PAUSES at genuine decision points — the agency-dial skills set the posture: `/collab` (default: surface non-trivial calls) · `/solo` (run-to-completion, no check-ins) · `/plan` (map + get go/no-go before scope-defining acts). SHORT: default = brisk but interactive; `/solo` = run-to-completion; `/plan` = deliberate first.
- INVARIANT: it works in reviewable repl TURNS producing real artifacts — you can redirect at any point; nothing is hidden.
- COUPLES: the agency dial → INSTRUCTIONS + PART B; artifacts a cell writes → DURABLE RECORD; auto-recalled memory on each turn → CONTEXT.

### B · CONTEXT — WHAT CLAUDE SEES
- FOR: everything Claude can see this turn — its working memory.
- LIKE: a desk — a permanent shelf that auto-restocks (memory) + a workbench that fills up and gets tidied (the window).
- TWO KINDS:
  - PERSISTENT (survives across sessions): PROJECT / PROFILE MEMORY. Memory AUTO-RECALLS into context each turn — this is how durable preferences, rules, and lessons reach Claude (the CS analog of CC's always-loaded `CLAUDE.md`). Each profile accrues its own memory; project memory is shared across the project's conversations.
  - RECOMPUTED each turn (the live window): this session's turns, cell outputs, artifacts read, search results. Finite — large, but not unlimited.
- POISON SURFACE (the CS-critical discipline): on CS, MEMORY is the poison surface — ONLY memory auto-recalls; ARTIFACTS are inert until searched/opened. A stale memory row re-injects itself as "current" every turn. So: keep ONE canonical per-topic memory row (supersede in place; retract the old claim when it changes), and keep done-records / closed state as inert ARTIFACTS, NOT memory rows (→ DURABLE RECORD, and the `durable-doc-architecture` + `provenance-over-description` skills in PART B).
- SEARCH: Claude retrieves artifacts + records by SEARCH — an artifact contributes to context only when found. Name/tag artifacts so the search that should pull them actually does.
- AS THE WINDOW FILLS: Claude auto-summarizes older turns — you keep the thread but detail can blur. LONG/COMPLEX effort ⇒ write a cold-start brief with `/handoff-brief` (a POINTER the next session loads targeted, referencing canonical artifacts by id) BEFORE the window fills (→ DELEGATION).
- INVARIANT: PERSISTENT context is MEMORY (auto-recalls — and is the poison surface); the live WINDOW is summarized as it fills ⇒ protect long work with `/handoff-brief`, keep one canonical memory row per topic, and let closed state live in inert artifacts.
- COUPLES: memory content + currency → PART B (`durable-doc-architecture`); `/handoff-brief` → DELEGATION; artifacts vs memory → DURABLE RECORD.

### C · INSTRUCTIONS — HOW YOU STEER IT
- FOR: the dials that direct HOW Claude works — the PROFILE it wears, the model + reasoning budget, and the skills it fires.
- LIKE: a control panel — pick the specialist persona (profile), the engine (model), the gear (effort), and the tool you reach for (skill).
- PROFILES (the CS analog of a CC subagent's specialized prompt, but for the MAIN persona too): a profile = a system-prompt PERSONA with a curated skill set + tool access. Pick a profile to specialize the whole conversation, or dispatch one as a delegated child (→ DELEGATION). The bundle ships 18 (PART B). `GENERALIST` = the wide-reach daily driver; the rest are domain specialists.
- MODELS + TIER ROUTING:
  - Capability ladder (hardest → cheapest): Fable 5 (hardest reasoning/modeling) · Opus 4.8 (capable workhorse) · Sonnet (fast, routine coding) · Haiku (fastest/cheapest, trivial).
  - MODEL POLICY (BINDING): NEVER Claude Opus 5 (`claude-opus-5`); NEVER the bare `opus` alias (resolves to Opus 5). Always full IDs (`claude-opus-4-8`, `claude-fable-5`). The ban applies to delegated children AND probes.
  - Per-child routing on delegation uses a difficulty TIER → model table (the `delegation-planning` kernel `TIER_TABLE` / `resolve_tier`); `host.delegate(model=…)` sets a child's model (→ DELEGATION).
- EFFORT (reasoning spent BEFORE acting): higher = better on hard problems, slightly slower. Stay high for research/modeling/debugging; lower it only for bulk mechanical work.
- SKILLS = auto-loading capabilities (the CS one mechanism — NO separate slash-command CLI layer): describe a task and the matching skill AUTO-LOADS via `host.skills` on its trigger; a few (the agency dial, some workflow skills) you also fire by name (e.g. "switch to /plan"). A skill may ship a KERNEL sidecar (→ AUTOMATION). The 52 bundle skills are cataloged by FAMILY in PART B — route by DESCRIPTION, not name-guess.
- STEER PERSISTENTLY: write a durable preference/rule into MEMORY (it auto-recalls every turn → CONTEXT); the bundle's discipline skills ride the same auto-load mechanism (→ PART B).
- INVARIANT: pick a PROFILE for the persona, a MODEL by difficulty (never Opus 5), and let skills AUTO-LOAD on trigger (or name one) — the profile + skills + model together are the steering.
- COUPLES: model tier table + Opus-5 ban → PART B + DELEGATION; the 52 skills / 18 profiles as overlay → PART B; delegating a profile → DELEGATION.

### D · ACTIONS & GUARDRAILS
- FOR: what Claude DOES (run cells, call the `host.*` API, read/write artifacts) + the boundary every action sits inside.
- LIKE: a workshop sealed in a clean room — powerful tools, but the room's walls (the sandbox) and its supply lines (network grants) define what can reach in or out.
- THE `host.*` API (the action surface — what Claude calls): `host.delegate` (dispatch profiles → DELEGATION) · `host.skills` (read/load/edit skills + kernels) · `host.agents` (the installed profiles) · `host.artifacts` (the durable store → DURABLE RECORD) · `host.lineage` (reproduction code per artifact version → DURABLE RECORD) · `host.frames` / `host.query` (the session record — events, prior turns) · `host.llm` (a raw model call) · `host.get_local_compute_stats` (compute headroom → DELEGATION).
- GUARDRAILS (CS-true — NOT a CC-style deny-list, NOT hooks):
  - SANDBOX ISOLATION: cells run in a remote sandbox with no access to your local machine's files or audio device by default. (This is why an "alert when done" must reach you via the BROWSER — the `audible-alert` skill — not a local beep.)
  - NETWORK GRANTS: outbound network is gated per host — a skill that needs the network (e.g. `folio-science`'s Kroki diagram render → `kroki.io`) requires an explicit grant; without it, the call is blocked.
  - ACCOUNT PERMISSIONS: some operations run against your live account / local machine rather than the sandbox (e.g. `preflight-parallel` routes filesystem-heavy inspection to the `mac-local` path, NOT the sandbox) — these run outside the sandbox by design and are gated accordingly.
- PLAN POSTURE: `/plan` (a skill, PART B) is the deliberation-max detent — for a scope-defining or expensive step it maps the territory + gets your go/no-go BEFORE committing; cheap/local/reversible acts still proceed. (The CS analog of CC plan mode — a SKILL, not a harness mode.)
- INVARIANT: Claude acts through the `host.*` API + repl, INSIDE a sandbox whose walls are isolation + per-host network grants + account permissions — it acts freely inside the boundary, never around it; there is no deny-list to override because the boundary is structural.
- COUPLES: `host.delegate` → DELEGATION; `host.artifacts`/`host.lineage` → DURABLE RECORD; `/plan` posture → INSTRUCTIONS + PART B.

### E · DELEGATION & SCALE
- FOR: keeping the main thread clean by handing bounded jobs to specialist PROFILES, and getting more done at once via BACKGROUND + parallel runs.
- LIKE: running a lab — you (lead) delegate specialized tasks to specialists + start long instruments running while you keep working.
- DELEGATION (`host.delegate`): dispatch one or more child agents, each a PROFILE with its own fresh context + a bounded task + a model. `host.delegate([{task, name, model}, …])` runs children (parallel by default); you COLLECT their results + read the ARTIFACTS they wrote. Children are steerable mid-run (a message lands at the child's next tool round); a child returns its report ONCE (a redesign = re-dispatch, a correction = a queued steer).
- TOPOLOGIES (the four, owned by `delegation-planning`): parallel-wave (independent fan-out) · sequential-build (each stage feeds the next) · convergence (many drafts → one synthesis) · verify-loop (builder + adversarial reviewer). Rule a cascade OUT for tightly-coupled single-thread work.
- BACKGROUND + ASYNC: long compute (model fits, bootstraps, simulations) runs detached while Claude keeps working; a running job never blocks — Claude advances a different thread meanwhile.
- CONFIRM "done" from the job's OWN artifacts/record (`host.frames`, the written artifact), not elapsed time — silence ≠ done (per `verification-loop`, → PART B).
- PARALLELISM: `preflight-parallel` sizes concurrency correctly — measure per-unit cost, read real headroom from `host.get_local_compute_stats()` (instantaneous cores/RAM, NOT load average), dispatch detached with briefs persisted first, then batch-analyze.
- INVARIANT: delegate bounded work to a specialist PROFILE (clean main thread) + run independent jobs in parallel in the background — but read "done" from the job's own artifacts, never the clock; and NEVER route a child to Opus 5.
- COUPLES: profiles + tier→model routing → INSTRUCTIONS; children write ARTIFACTS you collect → DURABLE RECORD; `preflight-parallel` / `supervisory-workflow` / `directing-execution` → PART B.

### F · THE DURABLE RECORD — ARTIFACTS & LINEAGE
- FOR: the persistent, reproducible store — how work survives a session and stays re-runnable (the CS analog of files + version control).
- LIKE: a lab notebook with a photocopier — every result filed with the exact procedure that made it.
- ARTIFACTS: durable objects (data, figures, docs, fit objects) Claude writes + retrieves via `host.artifacts`. They persist across sessions in the project. Each carries VERSION_IDs; `latest` is LAST-WRITER-WINS ⇒ PIN an explicit `version_id` when a downstream step must read a specific version (per `durable-doc-architecture`).
- LINEAGE: `host.lineage[version_id]["code"]` returns the REPRODUCTION code that produced an artifact version — the PRIMARY RECORD of what the system actually did. To answer "what does it do NOW / which method is canonical", read the lineage, NOT a docstring/memory row/handoff that only DESCRIBES it (per `provenance-over-description`).
- PROVENANCE HYGIENE: save every intermediate another cell will READ as an artifact BEFORE you fit — a file written to `/tmp` is lost on kernel restart and never enters lineage (the `provenance-guard` `/tmp`-linter + `checkpoint_frame` guard this; hand off between kernels through `./handoff/`, never `/tmp`).
- INVARIANT: results live as ARTIFACTS with LINEAGE (not loose files); pin explicit version_ids for anything downstream; and answer "what is it now" from the lineage (the record), never from a description of it.
- COUPLES: artifacts are inert until SEARCHED → CONTEXT; children's outputs → DELEGATION; provenance/currency discipline → PART B (`provenance-guard`, `provenance-over-description`, `durable-doc-architecture`).

### G · AUTOMATION — KERNEL SIDECARS
- FOR: reusable, deterministic gate/helper functions a skill ships and Claude CALLS — the CS analog of CC event-hooks (but call-time, not harness-fired).
- LIKE: a bench of calibrated jigs — you pick one up and use it at the right step; it does not fire itself.
- KERNELS: 19 of the 52 skills ship a `kernel.py` SIDECAR that AUTO-LOADS with the skill, exposing named functions. Load explicitly with `exec(host.skills.read("<skill>", "kernel.py")["content"])`, then call the function. Examples (all from the bundle): `verify_claims()` / `require_receipt()` (verification-loop) · `model_route_gate()` / `resolve_tier()` (delegation-planning) · `confirm_before_stop()` (directing-execution) · `verify_before_assert()` / `checkpoint_frame()` (provenance-guard) · `emit_alert()` (audible-alert) · `render_doc()` / `qa_pdf()` (folio-science).
- WHAT REPLACES CC HOOKS: CC fires hooks on EVENTS (the harness runs them). CS has NO event-hook layer — instead the kernel gates fire when INVOKED (you call them in a cell, or a skill's own procedure calls them before it emits a claim). So "automation" on CS is a called GATE, not an ambient trigger. A gate returns a verdict + a marker (e.g. `[[vloop:…]]`) so an auditor can tell "checked + clean" from "never ran".
- INVARIANT: automation on CS = KERNEL functions you CALL at the right step (not events the harness fires) ⇒ the discipline is to actually invoke the gate before the claim ships; a gate that never ran protects nothing.
- COUPLES: the verification kernels encode the always-on discipline → PART B + PART C; sidecar authoring rules → PART B (`toolkit-extension-authoring`) + the sidecar contract below.

## PART B · THE BUNDLE OVERLAY (deltas on base Claude Science)
- FRAMING: base Claude Science works WITHOUT any of this. The Research Toolkit BUNDLE (CSRTB v2.11) is an OVERLAY that specializes it for tower/flux research + verification-disciplined multi-agent work — nothing here changes the primitives; it pre-loads specialist profiles, domain skills, and kernel gates onto them.
- COUNTS (recomputed from `crt_science_bundle.json`, 2026-08-02): 52 SKILLS · 18 PROFILES · 19 of the skills ship a kernel sidecar. (Do NOT carry the CC toolkit's own roster figures — that is a different carrier.)
- FULL ROSTER (authoritative, primary record — do NOT hand-copy a table that drifts): the live `host.skills` + `host.agents` enumeration in your session, and the shipped `crt_science_bundle.json`. Below = the FAMILY map (route by description); the record above = the exact current membership.
- THE 18 PROFILES, BY FAMILY (dispatch via `host.delegate` or wear as the persona; route by DESCRIPTION):
  - VERIFICATION / REVIEW (2): `CODE_REVIEW_DEBUGGER` (R/Python/Julia/MATLAB review + the adversarial reviewer in a verify-loop) · `FORMAL_ARGUMENT_CHECKER` (computes an argument's formal/quantitative claims — deontic validity, base-rate/PPV, SDT).
  - WRITING & DOCS (4): `SCIENCE_WRITING_STYLIST` (Schimel OCAR revision) · `LLM_DOC_ARCHITECT` (machine-facing docs + agent/skill design + CC→CS porting) · `PROMPT_ENGINEER` (tighten a draft prompt) · `DESIGN_RATIONALE_ANALYST` (recover implicit rationale/schema).
  - PLANNER / GENERAL (2): `PLANNER` (decompose → route → tier → topology; the `/plan` persona) · `GENERALIST` (wide-reach daily driver).
  - DOMAIN MODELERS & STATS (7): `DYNAMICAL_SYSTEMS_MODELER` (how state EVOLVES — ODE/PDE/biogeochem) · `ECOPHYSIOLOGY_MODELER` (what the system SHOULD be — optimality/Farquhar) · `ECOSYSTEM_MODEL_TRACER` (CliMA/Emerald solve→recorder→plot tracing) · `MACHINE_LEARNING_SCIENTIST` (fusion + large-gap reconstruction + calibrated UQ) · `MICROMET_RECONSTRUCTOR` (gappy multi-height micromet → seam-free height-resolved drivers) · `ML_HYBRID_PROCESS_MODELER` (physics-informed / gray-box above→interior flux mapping) · `RESEARCH_STATS_ADVISOR` (the why/which of a method, not code).
  - SOFTWARE / BUILD (2): `SOFTWARE_DEVELOPER` (build to a spec; hands to CODE_REVIEW_DEBUGGER) · `AGENT_TOOLING_ENGINEER` (the customization layer itself — skills/profiles/kernels/installers/gates).
  - DATA MANAGEMENT (1): `RESEARCH_DATA_MANAGER` (provenance + four-lifecycle keep-vs-sweep on top of lineage).
- THE 52 SKILLS, BY FAMILY (each auto-loads on its trigger; route by DESCRIPTION):
  - VERIFICATION & INTEGRITY LOOPS (8) — the CS-distinctive engine: `verification-loop` (verify_claims/require_receipt) · `provenance-guard` (/tmp-linter, verify_before_assert) · `provenance-over-description` (read the record, not the description) · `count-enumeration-contagion` (recount before you relay an N) · `countermeasure-audit` (measure whether a fix worked) · `testing-discipline` (red-before-green, fixtures) · `durable-doc-architecture` (one-owner-per-topic, pin version_ids) · `refusal-recovery` (the refusal ladder).
  - WRITING & DOCUMENT ENGINE (9): `writing-science` (Schimel + detector kernel) · `machine-md` (LLM-facing doc form) · `expert-prose-style` · `teaching-narrative` · `design-rationale` · `doc-pipeline` (machine→human→PDF, gated) · `folio-science` (render PDF/docx/diagrams) · `eliciting-llm-behavior` (prompt technique catalog) · `figure-qa` (render-and-LOOK).
  - PLANNER / SUPERVISORY / ORCHESTRATION (9): `delegation-planning` (route+tier+topology) · `directing-execution` (run-time supervise loop) · `supervisory-workflow` (the operating logic) · `request-archetypes` (task → carriers) · `handoff-brief` (cold-start brief) · `preflight-parallel` (concurrency sizing) · the AGENCY DIAL: `solo` · `plan` · `collab`.
  - DOMAIN MODELERS & SCIENTIFIC METHOD (17): stats fitting — `brms-hierarchical-fitting` · `mgcv-temporal-gam` · `temporal-block-cv` · `temporal-qc-outlier-detection` · `tz-safe-timestamps` · `gap-fill-imputation` · `aggregation-jensen-bias` · `tree-ensembles`; scientific ML — `scientific-ml-fundamentals` · `calibrated-uq-for-ml` · `ml-emulator-surrogate` · `multi-source-fusion-bias-correction` · `physics-informed-ml` · `micromet-height-interpolation`; domain physics — `biosphere-atmosphere-flux-exchange`; method reproduction — `reproduce-model-from-literature`; compute — `julia-performance-correctness`.
  - LITERATURE & DATA CURATION (3): `sci-file-index` (metadata catalog) · `sci-library-curate` (dedup + topic-organize) · `scanned-pdf-ocr`.
  - TOOLKIT-BUILDER & EXTENSION / INSTALL+GATES (4): `toolkit-extension-authoring` · `bash-hook-contract` (CC-hook authoring) · `software-craft` · `refactoring`.
  - PROJECT-CANONICAL (1): `km67-canonical-methods` (the km67/Tapajós canonical-method registry + lineage self-check).
  - UTILITY (1): `audible-alert` (browser-channel "beep when done").
- THE SIDECAR CONTRACT (one paragraph): a skill's `kernel.py` sidecar auto-loads with the skill and exposes plain-name gate/helper functions. Its TOP LEVEL is restricted so it publishes cleanly: plain-name `def`s + imports + LITERAL-constant assigns ONLY — NO computed values (`re.compile`/`frozenset`/any call), NO `_`-prefixed names, NO top-level `if` (including the `__main__` guard); the `SKILL.md` `description:` is ≤1024 folded chars. `check_sidecar_contract.py` must exit 0 before any build. Author a new kernel to this contract from the start (owned by `toolkit-extension-authoring` + `AGENT_TOOLING_ENGINEER`).
- INVARIANT: the overlay = specialist profiles + domain skills + verification kernels layered onto base Claude Science ⇒ remove it and Claude Science still runs; keeping it makes it research-ready and verification-disciplined.
<!--FIG: base Claude Science + the CSRTB v2.11 overlay (52 skills / 18 profiles / 19 kernels) as a layer stack | 70% -->

## PART C · IN PRACTICE

### RESEARCH WORKING PATTERNS (task ⇒ bundle response)
- fit a hierarchical Bayesian model ⇒ describe it → `brms-hierarchical-fitting`; long fit → background + `preflight-parallel`.
- fit a big temporal GAM ⇒ `mgcv-temporal-gam` (k-selection, `bam` AR1).
- gap-fill a driver series ⇒ `gap-fill-imputation` (chunk-predict-splice, provenance tiers); large multi-year gap / fusion ⇒ `MACHINE_LEARNING_SCIENTIST` + `multi-source-fusion-bias-correction`.
- QC a met/flux series ⇒ `temporal-qc-outlier-detection`. Cross-validate autocorrelated data ⇒ `temporal-block-cv` (never iid). Join UTC + local data ⇒ `tz-safe-timestamps`.
- debug an R/Julia result that looks wrong ⇒ `CODE_REVIEW_DEBUGGER` (reproduce-before-fixing; root-before-bandaid).
- choose / defend a method ⇒ `RESEARCH_STATS_ADVISOR` (in `/plan`).
- state "the canonical method for X" ⇒ `provenance-over-description` (read `host.lineage`) — for km67, `km67-canonical-methods` FIRST.
- decompose a big job across agents ⇒ `PLANNER` + `delegation-planning` (route+tier+topology) → `directing-execution` while it runs.
- hand off / pause ⇒ `/handoff-brief`. Run a handed-off task unattended ⇒ `/solo`. Make a shareable PDF/docx of a doc ⇒ `doc-pipeline` / `folio-science`.
- ALWAYS: save intermediates as ARTIFACTS before you fit (never `/tmp`); independent runs → parallel + batch.

### A WORKED SESSION SHAPE
1. Open the project conversation → PICK A PROFILE (e.g. `MICROMET_RECONSTRUCTOR` for a driver-reconstruction task, or `GENERALIST`).
2. State the task concretely (source artifact id, method, output artifact name, "save plots as artifacts").
3. SKILLS FIRE on trigger (e.g. `temporal-qc-outlier-detection`, `gap-fill-imputation`, `preflight-parallel`); named-fire the agency dial as needed (`/plan` first for anything scope-defining).
4. DELEGATE bounded sub-jobs via `host.delegate` to specialist profiles (parallel-wave / verify-loop); a long fit goes to background compute.
5. COLLECT via ARTIFACTS + `host.frames` (read "done" from the written artifact, not the clock); pin the version_id downstream steps depend on.
6. RECORD durable outcomes: one canonical MEMORY row per topic (supersede in place), closed/done state as an inert ARTIFACT (not a memory row).
7. Before shipping any state claim ("N skills", "the gate passes", "byte-identical"), run the verification kernel (`verify_claims` / `require_receipt`) — see below.

### VERIFICATION-INTEGRITY DISCIPLINE (the bundle's spine)
- RECEIPTS: a "verified / passed / byte-identical" claim carries its RECEIPT (the count, the hash, the exit code, the artifact id) in the same breath. `require_receipt()` (verification-loop) is the return-based gate for a receiptless claim.
- NO "WORKS" WITHOUT MEASUREMENT: a shipped fix defaults to `attempted-untested` efficacy until a MEASUREMENT says otherwise — existence ≠ efficacy. `countermeasure-audit` measures failure-class rates before any row is upgraded to `verified-working`; `require_verification_status()` gates a "this fix works" claim with no honest status.
- VERIFY BEFORE ASSERT: every asserted value/count/ID/status names the READ that grounds it — `verify_before_assert()` (provenance-guard) is the assert-from-recollection gate; `verify_claims()` RAISES on any claim-vs-record mismatch and emits a `[[vloop:…]]` marker (and fails closed on a vacuous zero-claim check).
- WHERE THE GATES LIVE + WHEN A USER RUNS THEM:
  - AUTHOR-TIME (dev-side, run against `bundle_src/` when EXTENDING the bundle): `check_sidecar_contract.py` (kernels contract-clean) → `build_crt_science_bundle.py` (rebuild the JSON from source) → `check_bundle_parity.py` (build + strict-bytes + manifest). NEVER hand-edit `crt_science_bundle.json`.
  - SHIP / INSTALL-TIME (user-run in a Science session, per CS_INSTALL_STARTER_v2.11): `install_crt_science(overwrite=True)` → the kernel-gate SMOKE tests (`model_route_gate` rejects Opus-5; `confirm_before_stop` FAILs with no receipts; `verify_before_assert` FAILs on a memory-sourced value; `require_receipt` FAILs receiptless) → the sidecar acceptance re-probe.
  - RUNTIME (session-time, author-run): the verify_claims / require_receipt / verify_before_assert kernels above — called BEFORE the claim ships. (There is no CC-style Stop adversary HOOK on CS; the runtime backstop is these CALLED kernels, so the discipline is to actually invoke them.)
- GATE HONESTY: some checks CANNOT run from a given context (e.g. a live `sidecar_gate` re-probe needs the Science account). NAME what ran; never claim the unrunnable green.

### YOUR FIRST RESEARCH SESSION (walkthrough)
1. Install once, in a Science repl cell (per CS_INSTALL_STARTER_v2.11): `exec(open("install_crt_science.py").read()); install_crt_science(overwrite=True)` → confirm 52 skills / 18 profiles, no `InstallVerificationError`.
2. Open the project conversation → pick a profile → `/plan` for the first nontrivial task.
3. State the task concretely (artifact ids in, artifact names out, "save plots as artifacts").
4. Read the returned plan; approve or refine.
5. Approve → it runs cells + writes artifacts; watch the outputs.
6. A long fit goes to background/`host.delegate` — collect from the artifact when done.
7. If a number looks wrong, ask it to reproduce-before-fixing rather than patch.
8. `/handoff-brief` to write a cold-start brief before the window fills.
9. `doc-pipeline` / `folio-science` for a PDF of the write-up.
10. Record one canonical memory row per durable outcome; leave closed state as an inert artifact.

### TROUBLESHOOTING / FAQ
- "it re-asserted a stale fact" ⇒ MEMORY is the poison surface — supersede the canonical row in place + retract the old claim; don't leave two "current" rows.
- "a network call was blocked" ⇒ that host needs a NETWORK GRANT (e.g. `kroki.io` for `folio-science` diagrams) — grant it or use an offline path.
- "no sound when the run finished" ⇒ the sandbox has no audio device — `audible-alert` reaches you via the BROWSER (open the emitted HTML artifact).
- "which method do we actually use for X?" ⇒ read `host.lineage` (the record), not a docstring/memory (`provenance-over-description`); for km67, `km67-canonical-methods` first.
- "it forgot earlier context" ⇒ window auto-summarized; `/handoff-brief` then a fresh session, and rely on artifacts + memory to reload.
- "an intermediate vanished on restart" ⇒ it was written to `/tmp` — save cell intermediates as ARTIFACTS / to `./handoff/` (`provenance-guard`).
- "wrong model / too slow" ⇒ switch the profile's model (full IDs only; never Opus 5), or lower effort for trivial work.

### GLOSSARY (1 line each)
- primitive: one of Claude Science's core capability layers (CONTEXT · INSTRUCTIONS · ACTIONS+GUARDRAILS · DELEGATION · DURABLE RECORD · AUTOMATION); features derive from these.
- turn loop: the cycle Claude Science runs each turn — goal → load context+memory → plan → repl/`host.*` calls within permissions → review → repeat.
- overlay: the bundle's added profiles/skills/kernels layered onto base Claude Science (which runs without them).
- profile: a system-prompt persona with a curated skill set + tool access — worn as the main persona or dispatched as a delegated child (the CS analog of a CC subagent).
- skill: a packaged capability that auto-loads on a trigger (`host.skills`); some ship a kernel sidecar.
- kernel / sidecar: a skill's `kernel.py` of callable gate/helper functions (the CS analog of a CC hook — call-time, not event-fired).
- repl / cell: the persistent Python kernel; work runs as cells in a remote sandbox.
- artifact: a durable, versioned object (data/figure/doc/fit) in `host.artifacts` — the CS unit of the durable record.
- lineage: the reproduction code per artifact version (`host.lineage`) — the PRIMARY RECORD of what produced a result.
- memory: durable project/profile notes that AUTO-RECALL into context each turn (the persistent layer — and the poison surface).
- `host.delegate`: dispatch specialist PROFILES as child agents (parallel by default); collect via artifacts.
- model tier (Fable/Opus 4.8/Sonnet/Haiku): capability vs speed/cost; per-child via `resolve_tier` — never Opus 5.
- effort: reasoning budget spent before acting.
- network grant: per-host permission for an outbound call from the sandbox.
- agency dial (`/solo` `/collab` `/plan`): the autonomy posture — run-to-completion · surface non-trivial calls · deliberate-first.
- verification kernel: a called gate (`verify_claims`/`require_receipt`/`verify_before_assert`) that checks a claim against the record before it ships.
- attempted-untested vs verified-working: a fix's efficacy is future-dated until MEASURED (`countermeasure-audit`).
- handoff brief (`/handoff-brief`): a pointer doc so the next session loads targeted instead of re-exploring.
- machine doc vs human doc: LLM-optimized `.machine.md` (authoritative root) vs human-prose `.md` (derived twin).
- atom: a single preserved fact/rule/step (unchanged across machine↔human translation).

### READY FOR MORE?
- → CS_ADVANCED — the profiles/skills/kernels architecture, the `host.*` API surface, memory-as-poison-surface, orchestration topologies, and extension authoring on Claude Science.
- → CS_INSTALL_STARTER_v2.11 (at the bundle root) — the paste-ready user-run install + its acceptance probes.
