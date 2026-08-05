# TOOLKIT_ROSTER_CCRT_vs_CSRTB

FORM: machine-md · durable reference · LLM-read · owner-of-record for "what specialists+skills exist in each toolkit, and which are DESIGNED to work together and WHY"
STATUS: CURRENT (2026-07-27) · derived at CCRT v2.7 (17 agents / 39 skills) · CSRTB v2.7 (17 profiles / 44 skills)
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
PURPOSE: single roster of both sibling toolkits + the recovered collaboration rationale (§4) + the code-built side-by-side (§5). Per-item descriptions are VERBATIM lead-fragments of each source file's own `description` (exact prefixes — condensed by truncation, never reworded). §4 is a rational reconstruction: each working-set carries a grade (stated/inferred) and scope (instance/schema) tag; the full grounding ledger is APPENDIX A.
AUTHORITY (do not duplicate — cite): `TWIN_ARCHITECTURE.machine.md` (tiers S/C/P). §5 table is CODE-BUILT — pasted verbatim, not retyped.
READ-ORDER: §1 (platforms) → §4 (the WHY — core content) → §5 (side-by-side) → §2/§3 (per-item rosters, reference) → §6 (cross-platform model).

---

## §1. THE TWO PLATFORMS IN ONE PARAGRAPH

One research methodology, carried across two Anthropic agent platforms. **CCRT (Claude Research Toolkit)** customizes **Claude Code** — a LOCAL process on the user's Mac: it can run local shell, and its customizations install into `~/.claude/` via `install.sh` as agents (`.md` bodies), skills, and **hooks** (bash/python that fire on real Stop/Notification/PreToolUse events and can deterministically BLOCK an action via exit-code 2). **CSRTB (Claude Science bundle)** customizes **Claude Science** — a REMOTE sandbox whose only channel to the user is the browser: it has NO hook surface and NO local audio, but exposes the **`host.*` SDK** (host.delegate async multi-wave subagents, host.query/artifacts/lineage metadata DB, host.mcp connectors) and a **background reviewer** that scores turns after the fact. This single platform distinction — deterministic local hooks vs a soft remote reviewer, synchronous tree-shared Task subagents vs async `host.delegate`, native audio vs in-browser Web Audio — drives every CC↔CS divergence catalogued below.

---

## §2. CCRT ROSTER (Claude Code)

### §2.1 — 17 AGENTS
Format: `name` [model/color] — verbatim role lead · uses: referenced skills (`*` = loaded by default).

- `agent-tooling-engineer` [opus/green] — Invoke to build or maintain a Claude Code toolkit customization — a bash/python hook, a skill, an agent, an install.sh tier, or a settings.json fragment — so the change installs idempotently, portably, and · uses: bash-hook-contract*, machine-md, research-stats-advisor, toolkit-extension-authoring*
- `code-review-debugger` [opus/red] — Expert code review, debugging, and optimization for R, Python, or MATLAB code. · uses: julia-performance-correctness, mgcv-temporal-gam, temporal-block-cv, tz-safe-timestamps
- `design-rationale-analyst` [opus/purple] — Rational-reconstruction specialist: recovers the implicit rationale, design philosophy, and governing principles behind any body of work and separates the transferable schema from the instances — grounded · uses: design-rationale, expert-prose-style, research-stats-advisor, teaching-narrative, writing-science
- `dynamical-systems-modeler` [opus/teal] — Invoke to build or reproduce a simulation model of how biological/ecological state EVOLVES — ODE/PDE, matrix/stage-structured, agent-based; population & community dynamics; pool-and-flux biogeochemistry (C/N · uses: reproduce-model-from-literature, research-stats-advisor
- `ecophysiology-modeler` [opus/green] — Invoke to build or reproduce a mechanistic / optimality / eco-evolutionary model of plant or ecosystem function — leaf & canopy carbon economics, Farquhar photosynthesis, Cowan–Farquhar stomatal optimality · uses: reproduce-model-from-literature, research-stats-advisor
- `formal-argument-checker` [opus/red] — Verifies the formal and quantitative claims in an argument by computing them, not by reading around them: deontic-logic validity, base-rate/PPV arithmetic, signal-detection-theory usage, and whether a · uses: (none — self-contained)
- `llm-doc-architect` [opus/cyan] — Specialist in LLM-facing docs, agent/skill prompt design, and porting Claude Code customizations onto Claude Science primitives (skills, agent profiles, host.delegate, artifacts/lineage). · uses: machine-md, plan, research-stats-advisor
- `machine-doc-reviewer` [fable] — Reviews a machine-facing doc (*.machine.md, any .claude/ file — CLAUDE.md, rule, agent, skill — auto-memory, or hand-off) against LLM-writing best-practices — positive trigger-conditioned framing · uses: machine-md
- `machine-learning-scientist` [opus/blue] — Physics-informed, Bayesian scientific-ML specialist for RECONSTRUCTION — multi-source data fusion, large multi-year gap-fill, and calibrated uncertainty. · uses: calibrated-uq-for-ml, multi-source-fusion-bias-correction, research-stats-advisor, scientific-ml-fundamentals*, temporal-block-cv*, tree-ensembles
- `micromet-reconstructor` [opus/cyan] — Invoke for gap-filling gappy multi-height tower/eddy-covariance microclimate data or interpolating drivers across HEIGHT onto a fine vertical grid. · uses: aggregation-jensen-bias, brms-hierarchical-fitting, gap-fill-imputation, mgcv-temporal-gam, micromet-height-interpolation, research-stats-advisor, temporal-block-cv, temporal-qc-outlier-detection, tz-safe-timestamps
- `ml-hybrid-process-modeler` [opus/blue] — Learns the above-canopy → within-canopy mapping THROUGH the flux mechanism: the interior emerges from transport against per-layer sources/sinks, not interpolation. · uses: biosphere-atmosphere-flux-exchange*, ml-emulator-surrogate, physics-informed-ml*, research-stats-advisor
- `planner` [opus/orange] — Decomposes a task into a routed, gated plan — maps each subtask to the specialist AGENT + SKILL that fits it and picks the execution topology (single-thread or a named cascade: parallel-wave / sequential-build · uses: baton, collab, delegation-planning, directing-execution, eliciting-llm-behavior, machine-md, plan, preflight-parallel, request-archetypes*, solo
- `prompt-engineer` [opus/yellow] — Invoke WHEN you have a DRAFT prompt to tighten - a long or prolix instruction, a subagent task brief, a slash-command or skill prompt. · uses: eliciting-llm-behavior*, machine-md
- `research-data-manager` [opus/cyan] — Invoke for research-data organization, archival and naming, keep-vs-discard decisions, or provenance judgment across long-running projects — the four-lifecycle (ephemeral/durable-intermediate/product/keepsake) · uses: research-stats-advisor
- `sci-file-indexer` [opus/green] — Index/catalog a folder of scientific literature (books, chapters, theses, articles, supplements, datasets) into a metadata table with confidence tiers. · uses: plan, sci-file-index
- `science-writing-stylist` [opus/blue] — Science-writing craft specialist grounded in Joshua Schimel's Writing Science. · uses: (none — self-contained)
- `version-control-docs` [opus/orange] — Use this agent when you need to manage code versions, create documentation, organize project structure, or preserve working code before making changes. · uses: plan

### §2.2 — 39 SKILLS (grouped by function)
Format: `name` [kernel/scripts] — verbatim description lead.

**Orchestration** (7)

- `collab` — Collaborative mode — the MIDDLE default of the agency dial, between /solo (autonomy max) and /plan (deliberation max).
- `delegation-planning` — Invoke WHEN planning HOW to distribute a task across subagents — map each subtask to the specialist AGENT (the why/which) + SKILL (the how) that fits it, and decide whether to run a multi-agent
- `directing-execution` — Invoke WHEN a multi-agent plan is RUNNING and you are directing it — a wave of subagents has been launched, results are coming back, and you must decide continue / re-route / fix-first / abort / goal-met / adapt-the-plan
- `plan` — Deliberation mode — the down-dial mirror of /solo. The user fires /plan to say "map the territory and get my go/no-go BEFORE you commit to anything scope-defining." Invoke WHEN the user types /plan
- `preflight-parallel` — Before launching independent compute runs (model fits, downloads, CV folds, simulations), compute CPU headroom correctly (direct core arithmetic + instantaneous idle%, not load average) and launch as
- `request-archetypes` — Invoke WHEN about to plan or fulfil a user request and you need to recognize its TASK ARCHETYPE and reach for the right carriers FIRST — a lookup of common request types (handoff document, planning
- `solo` — Autonomous-mandate mode. The user fires /solo to say "run this to completion, no check-ins." Invoke WHEN the user hands off a task to run unattended/autonomously, or types /solo.

**Methodology (stats / ML / modeling-method / verification)** (15)

- `aggregation-jensen-bias` — Avoid Jensen-inequality bias when aggregating a nonlinear quantity from averaged inputs — compute-then-average at native resolution, keep the tails, and treat temporal vs spatial spread as DISTINCT
- `brms-hierarchical-fitting` — Fit hierarchical / multilevel Bayesian models in brms + cmdstanr on autocorrelated ecological time series — two-scale temporal AR, custom latent effects via stanvars, diagnosing stiff-geometry chain
- `calibrated-uq-for-ml` — Produce AND validate calibrated predictive uncertainty for an ML model — verify a 95% interval actually covers 95% of HELD-OUT truth (empirical coverage under blocked temporal CV, PIT histograms)
- `gap-fill-imputation` — Impute / gap-fill autocorrelated time series (met, flux, drivers) with brms or mgcv — CHUNK long records but predict with OVERLAPPING long tails and SPLICE (splice the overlaps rather than
- `mgcv-temporal-gam` — Fit a temporal / autocorrelated additive model in mgcv, choosing smooth basis dimension k defensibly (gam.check on progressive subsets) and handling AR1 residual autocorrelation with
- `ml-emulator-surrogate` — Build and validate a fast ML surrogate (emulator) that stands in for an EXPENSIVE MECHANISTIC SIMULATOR — e.g.
- `multi-source-fusion-bias-correction` — Harmonize a gappy in-situ reference series (e.g. a flux tower) with satellite and reanalysis sources into ONE continuous record by bias-correcting each secondary source to the reference over their
- `physics-informed-ml` — Fuse a mechanism with ML so the learned component can NEVER breach conservation — the three fusion modes (soft-penalty PINN; hard-coded gray-box where ML learns only the uncertain closure like
- `reproduce-model-from-literature` — Invoke WHEN re-implementing a published model from its equations — reproducing a paper's figure or reported result before extending it, or building a mechanistic / optimality / dynamical model from a
- `research-stats-advisor` — Invoke WHEN choosing or defending a statistical method, checking model assumptions, designing a study, or interpreting a result whose validity affects the scientific conclusion — the WHY/WHICH of
- `scientific-ml-fundamentals` — The discipline layer for any scientific-ML or data-driven model on a tall-forest flux-tower forcing reconstruction — scope ML to where it earns its place (large multi-year gaps, multi-source fusion
- `temporal-block-cv` — Construct temporal / blocked cross-validation folds for autocorrelated or rare-event data (blocked, not iid CV), and evaluate with metrics that survive class imbalance (PR-AUC
- `temporal-qc-outlier-detection` — QC / outlier-detection for autocorrelated environmental time series (tower met, flux, VPD, radiation) — separate spike vs drift vs level-shift into distinct matched passes, stratify by same-half-hour
- `tree-ensembles` — Gradient-boosted trees (xgboost/lightgbm) and random forests done right for tabular environmental regression — temporal+height feature engineering, quantile objectives for predictive intervals
- `tz-safe-timestamps` — Build timezone-safe timestamps and join/resample data from multiple sources with alignment kept explicit and verified, not silently misaligned.

**Domain-science (ecology / biophysics / amplicon)** (7)

- `biosphere-atmosphere-flux-exchange` — The Monson-Baldocchi terrestrial biosphere-atmosphere flux canon — canopy turbulent transport (K-theory and why it fails inside canopies, roughness sublayer, counter-gradient flow, higher-order
- `micromet-height-interpolation` — Invoke WHEN interpolating tower/canopy microclimate drivers across HEIGHT onto a fine vertical grid (e.g.

**Doc + provenance (authoring / rationale / LLM-form / literature / handoff)** (11)

- `baton` — Author or update a machine-record handoff + resume document so a cold session (or another person) can resume the work from the doc alone.
- `design-rationale` — Invoke WHEN the task is to recover the IMPLICIT rationale, design philosophy, or governing principles behind a body of work — a codebase, toolkit, literature, method, dataset, or experimental program
- `eliciting-llm-behavior` — Invoke WHEN about to write a prompt that must make a model RELIABLY produce a specific behavior, format, or reasoning path - a subagent task brief, a slash-command or skill prompt, a tool/output
- `expert-prose-style` — Adopt an expert flowing-prose register for a domain-expert reader — prose paragraphs over bullets, no unrequested condensing, standard technical terms left undefined.
- `folio` — Translate a machine-authored doc into a human twin and render it to PDF + docx.
- `machine-md` — Invoke WHEN writing or editing any doc whose primary reader is an LLM — *.machine.md, .claude/ files (CLAUDE.md, rules, agents, skills, settings), auto-memories, hand-offs.
- `scanned-pdf-ocr` — Extract text from scanned or image-only PDFs (no usable text layer, or garbled mojibake extraction) — degraded journal scans, two-column academic articles, old book chapters.
- `sci-file-index` — Build/update a catalog of a scientific-literature folder (books, chapters, theses, articles, supplements, datasets) -- extract per-file metadata, RESOLVE cryptic publisher-code filenames (stem=>DOI)
- `sci-library-curate` — Dedup, migrate-copy, and topic-organize a scientific-literature library from a sci-file-index paper_index.csv -- cluster the index so an article and its supplement are never treated as duplicates
- `teaching-narrative` — Invoke WHEN writing a NEW explanatory or teaching document whose purpose is to make a reader UNDERSTAND and be able to APPLY a concept, method, or framework — a guide, tutorial, walkthrough
- `writing-science` — Diagnose and revise science prose using Joshua Schimel's Writing Science framework (OCAR, story structures, the funnel, topic/stress positions, given-to-new flow) paired with a mechanical detector

**Platform-ops (hooks / installer / compute / audio / migration)** (6)

- `bash-hook-contract` — Invoke WHEN writing or debugging a Claude Code hook (bash/python) or any script that reads Claude's stdin-JSON, maps hook exit codes (0 pass / 2 block / others fail-open-but-logged), enforces a
- `capability-audit` — Audit installed agents/skills for duplication + placement, and RECOMMEND (never auto-act) which to retire or relocate.
- `julia-performance-correctness` — Diagnose and fix Julia performance (allocations, type instability, dispatch) and correctness gotchas (column-major, aliasing, @inbounds, float equality).
- `toolkit-extension-authoring` — Invoke WHEN adding or modifying a Claude Code customization in the claude-research-toolkit - a hook, agent, skill, slash command, install.sh tier, or settings fragment - so the change installs

---

## §3. CSRTB ROSTER (Claude Science)

### §3.1 — 17 PROFILES
Format: `name` — verbatim role lead · uses: referenced skills (`*` = loaded by default). NOTE: `audible-alert` is referenced by ALL 17 profiles as a standing behavior (see §4.H); it is omitted from no list but its ubiquity is the point.

- `AGENT_TOOLING_ENGINEER` — Engineering specialist for the customization layer itself — Claude Science skills/profiles/kernel.py sidecars/delegation and Claude Code toolkit hooks, settings.json deep-merge, install.sh tiers, and the · uses: audible-alert, bash-hook-contract*, machine-md, toolkit-extension-authoring*
- `CODE_REVIEW_DEBUGGER` — Expert review, debugging, and optimization of scientific-computing code in R, Python, Julia, and MATLAB. · uses: audible-alert, brms-hierarchical-fitting, julia-performance-correctness, mgcv-temporal-gam, temporal-block-cv, tz-safe-timestamps
- `DESIGN_RATIONALE_ANALYST` — Rational-reconstruction specialist: recovers the implicit rationale, design philosophy, and governing principles behind any body of work and separates the transferable schema from the instances — grounded · uses: audible-alert, design-rationale, expert-prose-style, teaching-narrative, writing-science
- `DYNAMICAL_SYSTEMS_MODELER` — Simulation models of how biological/ecological state EVOLVES — ODE/PDE, matrix/stage-structured, agent-based; population & community dynamics; pool-and-flux biogeochemistry (C/N cycling); transient vs · uses: audible-alert, reproduce-model-from-literature*
- `ECOPHYSIOLOGY_MODELER` — Mechanistic and optimality/eco-evolutionary models of plant & ecosystem function — leaf/canopy carbon economics, Farquhar photosynthesis, stomatal optimality, allocation trade-offs, temperature optima. · uses: audible-alert, reproduce-model-from-literature*
- `ECOSYSTEM_MODEL_TRACER` — CliMA/Emerald land-surface-model specialist: traces mass/energy/water/carbon quantities from solve variable -> recorder -> plotted output; catches recorder-for-physics and non-co-indexed-comparison errors · uses: audible-alert
- `FORMAL_ARGUMENT_CHECKER` — Verifies the formal and quantitative claims in an argument by computing them, not by reading around them: deontic-logic validity, base-rate/PPV arithmetic, signal-detection-theory usage, and whether a · uses: audible-alert
- `GENERALIST` — Neill's full-access general-purpose research assistant — same wide reach as the default (no-profile) agent, plus the hands-free audible ping. · uses: audible-alert
- `LLM_DOC_ARCHITECT` — Specialist in LLM-facing docs, agent/skill prompt design, and porting Claude Code customizations onto Claude Science primitives (skills, agent profiles, delegation, artifacts). · uses: audible-alert, plan
- `MACHINE_LEARNING_SCIENTIST` — Physics-informed, Bayesian scientific-ML specialist for reconstructing a continuous, calibrated multi-decade forcing from fused tower + satellite + reanalysis data. · uses: audible-alert, calibrated-uq-for-ml, multi-source-fusion-bias-correction, scientific-ml-fundamentals*, temporal-block-cv*, tree-ensembles
- `MICROMET_RECONSTRUCTOR` — End-to-end pipeline owner for turning gappy multi-height tower microclimate data into a continuous, seam-free, height-resolved driver set — QC → gap-fill fitting architecture → derived variables (VPD from · uses: aggregation-jensen-bias, audible-alert, brms-hierarchical-fitting, gap-fill-imputation*, mgcv-temporal-gam, micromet-height-interpolation*, temporal-block-cv, temporal-qc-outlier-detection, tz-safe-timestamps
- `ML_HYBRID_PROCESS_MODELER` — Physics-informed and hybrid/gray-box scientific ML that learns the above-canopy → within-canopy mapping through the flux mechanism, so the interior microclimate emerges as a physically- and · uses: audible-alert, biosphere-atmosphere-flux-exchange*, ml-emulator-surrogate, physics-informed-ml*
- `PLANNER` — Decomposes a task into a routed, gated plan — maps each subtask to the specialist PROFILE + SKILL that fits it and picks the execution topology (single-thread or a named cascade: parallel-wave / · uses: audible-alert, collab, delegation-planning, eliciting-llm-behavior, handoff-brief, machine-md, plan, preflight-parallel, request-archetypes*, solo
- `PROMPT_ENGINEER` — Tightens draft prompts into higher-efficacy, lower-token versions. Feed it a long/prolix prompt; get back a paste-ready rewrite + diff-rationale + token delta. · uses: audible-alert, eliciting-llm-behavior*, machine-md
- `RESEARCH_DATA_MANAGER` — Specialist in research-data provenance, organization, and lifecycle across long-running projects — the keep-vs-sweep, naming/indexing, and provenance-narrative judgment on top of Claude Science's structural · uses: audible-alert
- `RESEARCH_STATS_ADVISOR` — Research methodology and statistical-analysis guidance — method selection, assumption checking, study design, and result interpretation on large autocorrelated hierarchical data. · uses: aggregation-jensen-bias, audible-alert, brms-hierarchical-fitting, mgcv-temporal-gam, temporal-block-cv
- `SCIENCE_WRITING_STYLIST` — Science-writing craft specialist grounded in Joshua Schimel's Writing Science. · uses: audible-alert, writing-science

### §3.2 — 44 SKILLS (grouped by function)
Format: `name` [sidecar] — verbatim description lead.

**Orchestration** (8)

- `collab` — Collaborative mode — the MIDDLE default of the agency dial, between /solo (autonomy max) and /plan (deliberation max).
- `delegation-planning` — Invoke WHEN planning HOW to distribute a task across agents — map each subtask to the specialist PROFILE (the why/which) + SKILL (the how) that fits it, and decide whether to run a multi-agent
- `directing-execution` — Invoke WHEN a multi-agent plan is RUNNING and you are directing it turn by turn — a wave of sub-agents is in flight, results are coming back, and you must decide continue / re-route / fix-first / abort / goal-met / adapt-the-plan
- `plan` — Deliberation mode — the down-dial mirror of /solo, the DELIBERATION-MAX detent of the agency dial.
- `preflight-parallel` — Before launching independent compute work (model fits, downloads, CV folds, simulations, sub-agent fan-outs), size concurrency correctly — measure per-unit cost, check real headroom with
- `request-archetypes` — Invoke WHEN about to plan or fulfil a user request and you need to recognize its TASK ARCHETYPE and reach for the right carriers FIRST — a lookup of common request types (handoff document, planning
- `solo` — Autonomous-mandate mode — the AUTONOMY-MAX detent of the agency dial. Fire /solo to say "run this to completion, no check-ins." Invoke WHEN the user hands off a task to run unattended/autonomously

**Methodology (stats / ML / modeling-method / verification)** (15)

- `aggregation-jensen-bias` — Avoid Jensen-inequality bias when aggregating a nonlinear quantity from averaged inputs — compute-then-average at native resolution, keep the tails, and treat temporal vs spatial spread as DISTINCT
- `brms-hierarchical-fitting` — Fit hierarchical / multilevel Bayesian models in brms + cmdstanr on autocorrelated ecological time series — two-scale temporal AR, custom latent effects via stanvars, diagnosing stiff-geometry chain
- `calibrated-uq-for-ml` [sidecar] — Produce AND validate calibrated predictive uncertainty for an ML model — verify a 95% interval actually covers 95% of HELD-OUT truth (empirical coverage under blocked temporal CV, PIT histograms)
- `gap-fill-imputation` — Impute / gap-fill autocorrelated time series (met, flux, drivers) with brms or mgcv — CHUNK long records but predict with OVERLAPPING long tails and SPLICE (splice the overlaps rather than
- `mgcv-temporal-gam` — Fit a temporal / autocorrelated additive model in mgcv, choosing smooth basis dimension k defensibly (gam.check on progressive subsets) and handling AR1 residual autocorrelation with
- `ml-emulator-surrogate` — Build and validate a fast ML surrogate (emulator) that stands in for an EXPENSIVE MECHANISTIC SIMULATOR — e.g.
- `multi-source-fusion-bias-correction` [sidecar] — Harmonize a gappy in-situ reference series (e.g. a flux tower) with satellite and reanalysis sources into ONE continuous record by bias-correcting each secondary source to the reference over their
- `physics-informed-ml` — Fuse a mechanism with ML so the learned component can NEVER breach conservation — the three fusion modes (soft-penalty PINN; hard-coded gray-box where ML learns only the uncertain closure like
- `reproduce-model-from-literature` — Invoke WHEN re-implementing a published model from its equations — reproducing a paper's figure or reported result before extending it, or building a mechanistic / optimality / dynamical model from a
- `scientific-ml-fundamentals` [sidecar] — The discipline layer for any scientific-ML or data-driven model on the K67 forcing reconstruction — scope ML to where it earns its place (large multi-year gaps, multi-source fusion, joint time×height
- `temporal-block-cv` — Construct temporal / blocked cross-validation folds for autocorrelated or rare-event data (blocked, not iid CV), and evaluate with metrics that survive class imbalance (PR-AUC
- `temporal-qc-outlier-detection` — QC / outlier-detection for autocorrelated environmental time series (tower met, flux, VPD, radiation) — separate spike vs drift vs level-shift into distinct matched passes, stratify by same-half-hour
- `tree-ensembles` — Gradient-boosted trees (xgboost/lightgbm) and random forests done right for tabular environmental regression — temporal+height feature engineering, quantile objectives for predictive intervals
- `tz-safe-timestamps` — Build timezone-safe timestamps and join/resample data from multiple sources with alignment kept explicit and verified, not silently misaligned.
- `verification-loop` [sidecar] — Close your own loop instead of asserting a state you have not checked.

**Domain-science (ecology / biophysics / amplicon)** (8)

- `biosphere-atmosphere-flux-exchange` [sidecar] — The Monson-Baldocchi terrestrial biosphere-atmosphere flux canon — canopy turbulent transport (K-theory and why it fails inside canopies, roughness sublayer, counter-gradient flow, higher-order
- `km67-canonical-methods` [sidecar] — Canonical gap-fill and height-interpolation method registry for the km67 Tapajos tower project — which engine and shipped product is authoritative for each variable (co2, tair, h2o, pamb
- `micromet-height-interpolation` — Invoke WHEN interpolating tower/canopy microclimate drivers across HEIGHT onto a fine vertical grid (e.g.

**Doc + provenance (authoring / rationale / LLM-form / literature / handoff)** (15)

- `design-rationale` [sidecar] — Invoke WHEN the task is to recover the IMPLICIT rationale, design philosophy, or governing principles behind a body of work — a codebase, toolkit, literature, method, dataset, or experimental program
- `doc-pipeline` [sidecar] — Invoke WHEN the task is to PRODUCE a document as a machine-md → human-readable-md → PDF set, either by AUTHORING one from a spec/request or by RENDERING human+PDF twins from an existing .machine.md
- `durable-doc-architecture` — Invoke WHEN setting up or auditing a project's durable reference documents — the cross-session docs a blind agent must find via the front door to orient (current state, canonical methods, working
- `eliciting-llm-behavior` — Invoke WHEN about to write a prompt that must make a model RELIABLY produce a specific behavior, format, or reasoning path — a host.llm call, a host.delegate sub-agent task, a tool/output schema, or
- `expert-prose-style` — Adopt an expert flowing-prose register for a domain-expert reader — prose paragraphs over bullets, no unrequested condensing, standard technical terms left undefined.
- `folio-science` [sidecar] — Invoke WHEN rendering a formatted DOCUMENT (Markdown → PDF or docx) or a text-defined DIAGRAM (Mermaid, Graphviz/dot, PlantUML, D2) into an artifact inside the Claude Science sandbox.
- `handoff-brief` [sidecar] — Write a cold-start brief so the NEXT conversation in this Claude Science project resumes with zero re-discovery.
- `machine-md` — Invoke WHEN writing or editing any text whose primary reader is an LLM — a skill's SKILL.md and its description field, an agent profile's system_prompt, durable memory rows, delegation task briefs
- `provenance-guard` [sidecar] — Invoke WHEN about to fit a model or render a figure, before a kernel restart or session end, or when hand-checking that no intermediate feeding a published result was lost to /tmp.
- `provenance-over-description` — Invoke WHEN about to assert or decide what an evolved system (a multi-session pipeline, a maintained toolkit, a shipped artifact) currently IS, DOES, USES, or SHIPS — its method-of-record
- `scanned-pdf-ocr` [sidecar] — Extract text from scanned or image-only PDFs (no usable text layer, or garbled mojibake extraction) — degraded journal scans, two-column academic articles, old book chapters.
- `sci-file-index` [sidecar] — Build/update a catalog of a scientific-literature folder (books, chapters, theses, articles, supplements, datasets) into a confidence-tiered metadata index -- extract per-file metadata, RESOLVE
- `sci-library-curate` [sidecar] — Dedup, migrate-copy, and topic-organize a scientific-literature library from a sci-file-index paper_index.csv -- cluster the index so an article and its supplement are never treated as duplicates
- `teaching-narrative` [sidecar] — Invoke WHEN writing a NEW explanatory or teaching document whose purpose is to make a reader UNDERSTAND and be able to APPLY a concept, method, or framework — a guide, tutorial, walkthrough
- `writing-science` [sidecar] — Diagnose and revise science prose using Joshua Schimel's Writing Science framework (OCAR, story structures, the funnel, topic/stress positions, given-to-new flow) paired with a mechanical detector

**Platform-ops (hooks / installer / compute / audio / migration)** (5)

- `audible-alert` [sidecar] — Produce an audible + visual alert inside Claude Science when a long task finishes — the Science-native analog of the Claude Code toolkit's xbeep hook.
- `bash-hook-contract` — Invoke WHEN writing or debugging a Claude Code hook (bash/python) or any script that reads Claude's stdin-JSON, maps hook exit codes (0 pass / 2 block / others fail-open-but-logged), enforces a
- `julia-performance-correctness` — Diagnose and fix Julia performance (allocations, type instability, dispatch) and correctness gotchas (column-major, aliasing, @inbounds, float equality).
- `toolkit-extension-authoring` — Invoke WHEN adding or modifying a Claude Code customization in the claude-research-toolkit - a hook, agent, skill, slash command, install.sh tier, or settings fragment - so the change installs

---

## §4. COLLABORATION PATTERNS — the designed working-sets and WHY (CORE CONTRIBUTION)

Rational reconstruction of which agents+skills are DESIGNED to compose, grounded in the `skills_referenced` edges each agent/profile declares in its own file. Each working-set is tagged `[grade · scope]`: grade = `stated` (the files say this of themselves) / `inferred` (this reading); scope = `instance` (warranted for these carriers) / `schema` (claimed for any comparable design). APPENDIX A is the full grounding ledger (every principle → named instances → falsification). The green ledger check certifies the spine's FORM was followed, NOT that every reading is correct — the falsification pass and the reader's judgment do that.

### §4.A — The PLANNER orchestration set  `[stated · schema]`
**Members (edges):** planner/PLANNER → `request-archetypes`* + `delegation-planning` + `preflight-parallel` + `plan` + `solo` + `collab` (+ CC also `directing-execution`, `baton`; CS also `handoff-brief`).
**Composition:** the planner persona is a ROUTING agent, not a doer. It loads ONLY `request-archetypes` by default (archetype recognition is always-on — recognize the request type first) and names the heavier routing machinery as on-demand references, loaded only when a plan is actually being built. `plan`/`solo`/`collab` are the three execution modes; `delegation-planning` maps each subtask to a specialist PROFILE+SKILL and picks one of four topologies (parallel-wave / sequential-build / convergence / verify-loop); `preflight-parallel` sizes the concurrency; `directing-execution` (CC) runs the supervise→decide→act loop once a wave is in flight. Both planner `description`s state "Loads the delegation-planning skill" and "satisfies its Delegation & Routing mandate by construction."
**Why grouped:** a monolithic planner that eager-loaded every routing skill would waste context on plans that never fan out; splitting always-on archetype-recognition from on-demand routing keeps the persona cheap until a cascade is chosen (friction: inferred). Falsifies clean against CrewAI's hierarchical-manager agent and the LangGraph supervisor pattern — both instantiate a dedicated router that holds routing logic, not task execution. (The load-by-default split is Claude-harness-specific and does not transfer — that clause is bounded here.)

### §4.B — Run-time orchestration is the largest planned CC↔CS split inside a shared persona  `[stated · instance]`
CC's planner references `directing-execution` + `baton`; CS's PLANNER references NEITHER, swapping in `handoff-brief`. The design-time routing vocabulary (four topologies, archetypes, `delegation-planning`) is platform-neutral and shared; the RUN-TIME supervise-loop is bound to each platform's subagent SDK — Task tool (synchronous, tree-shared, no mid-run steer) vs `host.delegate` (async `wait=False`, `host.collect`/`send_message`/`stop_child`). per the twin-architecture tier model, these skills diverge BY DESIGN at their run-time-SDK sections; the comparison table measures `directing-execution` at sim 0.66 (substantive-diverge) and pairs `baton`↔`handoff-brief` as TIER-C "same discipline, renamed carrier." Instance-scoped: this is a fact about these two carriers, not a universal.

### §4.C — The doc-authoring cascade  `[stated · schema]`
**Members (edges):** design-rationale-analyst/DESIGN_RATIONALE_ANALYST → `design-rationale` + `teaching-narrative` + `writing-science` + `expert-prose-style`; llm-doc-architect → `machine-md`; prompt-engineer → `eliciting-llm-behavior` + `machine-md`; machine-doc-reviewer (CC) → `machine-md`.
**Composition:** authoring is a SEPARABLE cascade of single-responsibility carriers. `design-rationale` recovers the WHY (the thinking); `teaching-narrative` renders it as a human explainer (the writing — `design-rationale`'s own REF names it "the render engine for the recovered content"); `writing-science` revises prose toward publication; `expert-prose-style` sets register (a toggle, not a task). This exact task is running that cascade: recover with `design-rationale` (this step), then render the human twin with `teaching-narrative` (next step).
**Why grouped:** a single author-everything skill couples content-recovery to prose-style — you could not reuse a recovered rationale in a machine doc, nor restyle prose without re-deriving content. Splitting lets the analyst recover once and render many ways (friction: stated). Falsifies against the Diátaxis doc framework: Diátaxis also refuses one-doc-does-everything but splits by reader-INTENT, not pipeline STAGE — so "separable carriers" holds broadly, while "recover→teach→style stages" is bounded to single-artifact authoring.

### §4.D — machine-md as the shared FORM primitive beneath every LLM-read doc role  `[stated · instance]`
`machine-md` is referenced by llm-doc-architect, prompt-engineer, machine-doc-reviewer, agent-tooling-engineer, AND both planners — it is the writing-discipline layer (positive trigger-conditioned framing, output-detectable triggers, atom-preservation) beneath role-specific doc work, never a standalone deliverable. `prompt-engineer` states it "Uses the eliciting-llm-behavior technique catalog + machine-md form"; `machine-md`'s Companion delegates a review pass to LLM_DOC_ARCHITECT. Note the form itself is platform-adapted (comparison table: `machine-md` sim 0.65, substantive-diverge) — so this is instance-scoped to this roster.

### §4.E — folio / folio-science are render backends wired BELOW the personas  `[inferred · instance]`
No agent or profile names `folio`/`folio-science` in `skills_referenced` (verified by scan). The render step is reached through `doc-pipeline` (author→translate→render) and the `folio`↔`folio-science` TIER-C rename, deliberately decoupled from the doc-authoring personas: binding a render backend into an author would couple content to one output format, whereas a downstream render skill lets the same content target local-pandoc (CC) or offline typst+pandoc (CS). Inferred (the files do not state this decoupling as intent); instance-scoped.

### §4.F — The modeling stacks: physics-owner DEFERS method-choice to a stats authority  `[stated · schema]`
**Members (edges):**
- micromet-reconstructor/MICROMET_RECONSTRUCTOR → domain skills `micromet-height-interpolation` + `gap-fill-imputation` + `aggregation-jensen-bias` + QC/stats `temporal-qc-outlier-detection` + `brms-hierarchical-fitting` + `mgcv-temporal-gam` + `temporal-block-cv` + `tz-safe-timestamps` + `research-stats-advisor`.
- ml-hybrid-process-modeler/ML_HYBRID_PROCESS_MODELER → `physics-informed-ml`* + `biosphere-atmosphere-flux-exchange`* + `ml-emulator-surrogate` (+ CC `research-stats-advisor`).
- machine-learning-scientist/MACHINE_LEARNING_SCIENTIST → `scientific-ml-fundamentals`* + `temporal-block-cv`* + `calibrated-uq-for-ml` + `multi-source-fusion-bias-correction` + `tree-ensembles` (+ CC `research-stats-advisor`).
**Composition:** each modeler OWNS the physics/mechanism (loads its domain+physics skills by default) and DEFERS statistical-method choice to a dedicated stats authority — `research-stats-advisor` (CC skill) / `RESEARCH_STATS_ADVISOR` (CS profile). micromet-reconstructor's description states this literally: "DEFERS statistical method choice to research-stats-advisor." The three modelers partition the flux problem: reconstruct the above-canopy boundary (machine-learning-scientist), map above→within-canopy through the flux mechanism (ml-hybrid-process-modeler), gap-fill+interpolate multi-height drivers (micromet-reconstructor) — their descriptions cross-reference each other's boundaries explicitly.
**Why grouped:** a modeler that also adjudicates its own CV scheme / prior / hierarchical structure conflates mechanism with method and tends to defend in-sample fit; routing method-choice to a stats authority stops the physics owner grading its own statistics (friction: inferred). Falsifies to instance-only in a fused applied-ML team (one engineer builds AND picks the CV split) — so the schema holds specifically where a dedicated stats-methodology carrier is instantiated, and weakens to a role-hygiene preference where roles are fused.
### §4.G — The QC / verification chain: COMPUTE the claim, low coupling  `[stated · schema]`
formal-argument-checker/FORMAL_ARGUMENT_CHECKER references ZERO skills — fully self-contained, because it "Verifies the formal and quantitative claims by computing them, not by reading around them." code-review-debugger/CODE_REVIEW_DEBUGGER references only the method skills it validates against (`julia-performance-correctness`, `mgcv-temporal-gam`, `temporal-block-cv`, `tz-safe-timestamps`) and the CS profile "adds validating assertions after each fix."
**Why grouped:** a checker that cites other checkers can launder an unverified claim through a chain of references; a self-contained checker that recomputes the claim has no such escape hatch (friction: inferred). Falsifies against automated type-checkers/linters (compute, do not defer — fits) vs a read-around human reviewer (does not) — bounded to compute-capable verification carriers, which is exactly this class.

### §4.H — Verification-gate HARDNESS and ubiquitous side-effects are platform-set (the TIER-C boundary)  `[stated · instance]`
Two disciplines shared in intent, split in mechanism by the platform:
1. **claim-vs-record verification.** CC enforces it with deterministic HOOKS that BLOCK (`claim-verify-guard.sh`, PreToolUse, exit 2 before a write lands) + `pre-complete-verification.sh`; CS can only APPROXIMATE with a PLANNER prose self-check that emits a `[[claim_check …]]` marker for the BACKGROUND REVIEWER to SCORE. Hard gate vs soft gate — the CC hook is the stronger form (the twin-architecture tier model). CS carriers: `verification-loop` (C†, "CC analog = claim-verify-guard hook"), `provenance-guard` (C, reads `execution_log` via host.query).
2. **completion/turn-boundary alert.** CS attaches `audible-alert` at the PROFILE layer — referenced by ALL 17/17 profiles as a standing behavior — because CS has no turn-end hook; CC fires the same beep from `xbeep` hooks on native Stop/Notification events with zero per-agent wiring. The 17/17 fan-in is the mechanical cost of the missing hook surface (friction: stated). The side-effect-per-unit schema (no shared interception point ⇒ concern re-declared per unit) falsifies clean against logging with vs without middleware/AOP; the specific 17/17 count is instance.

---

## §5. SIDE-BY-SIDE COMPARISON TABLE (CODE-BUILT — pasted verbatim)

## Side-by-side comparison — CCRT (Claude Code) vs CSRTB (Claude Science)

Tier legend: **S** = shared role/skill (same name + discipline; system-prompt/skill bodies carry platform-adapted wording) · **C** = shared discipline via a DIFFERENT carrier (never byte-copy) · **P** = platform-only (never ported). Authority: `TWIN_ARCHITECTURE.machine.md`.

> Measured note: of the 35 same-name shared skills, 0 are byte-identical across platforms; median body similarity is 0.95 (20 cosmetic ≥0.90, 7 light-adaptation, 8 substantive <0.70). "Shared" means shared name + discipline, not shared bytes.

### Roles — CCRT agents (17) ↔ CSRTB profiles (17)

| CCRT agent | CSRTB profile | Tier | Relationship |
|---|---|---|---|
| `agent-tooling-engineer` | `AGENT_TOOLING_ENGINEER` | S | shared role, same charter |
| `code-review-debugger` | `CODE_REVIEW_DEBUGGER` | S | shared role, same charter |
| `design-rationale-analyst` | `DESIGN_RATIONALE_ANALYST` | S | shared role, same charter |
| `dynamical-systems-modeler` | `DYNAMICAL_SYSTEMS_MODELER` | S | shared role, same charter |
| `ecophysiology-modeler` | `ECOPHYSIOLOGY_MODELER` | S | shared role, same charter |
| `formal-argument-checker` | `FORMAL_ARGUMENT_CHECKER` | S | shared role, same charter |
| `llm-doc-architect` | `LLM_DOC_ARCHITECT` | S | shared role, same charter |
| `machine-learning-scientist` | `MACHINE_LEARNING_SCIENTIST` | S | shared role, same charter |
| `micromet-reconstructor` | `MICROMET_RECONSTRUCTOR` | S | shared role, same charter |
| `ml-hybrid-process-modeler` | `ML_HYBRID_PROCESS_MODELER` | S | shared role, same charter |
| `planner` | `PLANNER` | S | shared role, same charter |
| `prompt-engineer` | `PROMPT_ENGINEER` | S | shared role, same charter |
| `research-data-manager` | `RESEARCH_DATA_MANAGER` | S | shared role, same charter |
| `science-writing-stylist` | `SCIENCE_WRITING_STYLIST` | S | shared role, same charter |
| `research-stats-advisor` *(SKILL)* | `RESEARCH_STATS_ADVISOR` *(profile)* | C | carrier asymmetry: CC = skill, CS = profile |
| `machine-doc-reviewer` | — | P | CCRT-only agent (CS: machine-md discipline via skill/reviewer) |
| `sci-file-indexer` | — | P | CCRT-only agent (CS: sci-file-index SKILL, no indexer profile) |
| `version-control-docs` | — | P | CCRT-only agent (Science has no local git) |
| — | `ECOSYSTEM_MODEL_TRACER` | P | P — project-local (CliMA/Emerald) |
| — | `GENERALIST` | — | CSRTB-only profile (no CC agent twin) |

### Skills — CCRT (39) ↔ CSRTB (44)

| CCRT skill | CSRTB skill | Tier | Relationship |
|---|---|---|---|
| `aggregation-jensen-bias` | `aggregation-jensen-bias` | S | shared skill (name + discipline; platform-adapted body) |
| `bash-hook-contract` | `bash-hook-contract` | S | shared skill (name + discipline; platform-adapted body) |
| `biosphere-atmosphere-flux-exchange` | `biosphere-atmosphere-flux-exchange` | S | shared skill (name + discipline; platform-adapted body) |
| `brms-hierarchical-fitting` | `brms-hierarchical-fitting` | S | shared skill (name + discipline; platform-adapted body) |
| `calibrated-uq-for-ml` | `calibrated-uq-for-ml` | S | shared skill (name + discipline; platform-adapted body) |
| `collab` | `collab` | S | shared skill (name + discipline; platform-adapted body) |
| `delegation-planning` | `delegation-planning` | S | shared skill (name + discipline; platform-adapted body) |
| `design-rationale` | `design-rationale` | S | shared skill (name + discipline; platform-adapted body) |
| `directing-execution` | `directing-execution` | S | shared skill (name + discipline; platform-adapted body) |
| `eliciting-llm-behavior` | `eliciting-llm-behavior` | S | shared skill (name + discipline; platform-adapted body) |
| `expert-prose-style` | `expert-prose-style` | S | shared skill (name + discipline; platform-adapted body) |
| `gap-fill-imputation` | `gap-fill-imputation` | S | shared skill (name + discipline; platform-adapted body) |
| `julia-performance-correctness` | `julia-performance-correctness` | S | shared skill (name + discipline; platform-adapted body) |
| `machine-md` | `machine-md` | S | shared skill (name + discipline; platform-adapted body) |
| `mgcv-temporal-gam` | `mgcv-temporal-gam` | S | shared skill (name + discipline; platform-adapted body) |
| `micromet-height-interpolation` | `micromet-height-interpolation` | S | shared skill (name + discipline; platform-adapted body) |
| `ml-emulator-surrogate` | `ml-emulator-surrogate` | S | shared skill (name + discipline; platform-adapted body) |
| `multi-source-fusion-bias-correction` | `multi-source-fusion-bias-correction` | S | shared skill (name + discipline; platform-adapted body) |
| `physics-informed-ml` | `physics-informed-ml` | S | shared skill (name + discipline; platform-adapted body) |
| `plan` | `plan` | S | shared skill (name + discipline; platform-adapted body) |
| `preflight-parallel` | `preflight-parallel` | S | shared skill (name + discipline; platform-adapted body) |
| `reproduce-model-from-literature` | `reproduce-model-from-literature` | S | shared skill (name + discipline; platform-adapted body) |
| `request-archetypes` | `request-archetypes` | S | shared skill (name + discipline; platform-adapted body) |
| `scanned-pdf-ocr` | `scanned-pdf-ocr` | S | shared skill (name + discipline; platform-adapted body) |
| `sci-file-index` | `sci-file-index` | S | shared skill (name + discipline; platform-adapted body) |
| `sci-library-curate` | `sci-library-curate` | S | shared skill (name + discipline; platform-adapted body) |
| `scientific-ml-fundamentals` | `scientific-ml-fundamentals` | S | shared skill (name + discipline; platform-adapted body) |
| `solo` | `solo` | S | shared skill (name + discipline; platform-adapted body) |
| `teaching-narrative` | `teaching-narrative` | S | shared skill (name + discipline; platform-adapted body) |
| `temporal-block-cv` | `temporal-block-cv` | S | shared skill (name + discipline; platform-adapted body) |
| `temporal-qc-outlier-detection` | `temporal-qc-outlier-detection` | S | shared skill (name + discipline; platform-adapted body) |
| `toolkit-extension-authoring` | `toolkit-extension-authoring` | S | shared skill (name + discipline; platform-adapted body) |
| `tree-ensembles` | `tree-ensembles` | S | shared skill (name + discipline; platform-adapted body) |
| `tz-safe-timestamps` | `tz-safe-timestamps` | S | shared skill (name + discipline; platform-adapted body) |
| `writing-science` | `writing-science` | S | shared skill (name + discipline; platform-adapted body) |
| `folio` | `folio-science` | C | same discipline, platform-named (render backend) |
| `baton` | — | — | CCRT-only skill |
| `capability-audit` | — | — | CCRT-only skill |
| `research-stats-advisor` | — | — | CCRT-only skill |
| — | `audible-alert` | — | CSRTB-only skill |
| — | `doc-pipeline` | — | CSRTB-only skill |
| — | `durable-doc-architecture` | — | CSRTB-only skill |
| — | `handoff-brief` | — | CSRTB-only skill |
| — | `km67-canonical-methods` | — | CSRTB-only skill |
| — | `provenance-guard` | — | CSRTB-only skill |
| — | `provenance-over-description` | — | CSRTB-only skill |
| — | `verification-loop` | — | CSRTB-only skill |

## §6. CROSS-PLATFORM MODEL (the three tiers + the invariant)

Authority: `TWIN_ARCHITECTURE.machine.md`. Every load-bearing item classifies into exactly ONE tier:
- **TIER-S — SHARED EXACTLY.** Same content + same carrier type both sides (modulo platform-vocabulary). A change to one SHOULD mirror to the other. The platform-neutral methodology skills/agents. MEASURED: of 40 same-name shared skills, 0 are byte-identical; median body similarity 0.96 — "shared" means shared NAME + DISCIPLINE, not shared bytes.
- **TIER-C — SHARED CONCEPTUALLY, DIFFERENT MECHANISM.** Same discipline, different carrier because the platforms differ. NEVER byte-copy across a TIER-C boundary — re-express the concept in the other platform's mechanism. Load-bearing rows: verification (hooks vs reviewer), completion-alert (xbeep vs audible-alert), handoff (`baton`↔`handoff-brief`), subagent orchestration (Task vs host.delegate), provenance (RULE+HOOK vs `provenance-guard` skill), render (`folio`↔`folio-science`), stats (`research-stats-advisor` skill ↔ profile). The stats skill↔profile split is a DELIBERATE carrier choice, not a gap to reconcile: per the agent-vs-skill discriminant (the twin-architecture tier model, from the 2026-07-11 user-approved DESIGN_BRIEF_agent_skill_division), a role earns the AGENT/PROFILE form only with an isolation / model / tool / review signal — `research-stats-advisor` is inline why/which guidance with none, so CC carries it as a skill; CS binds 0/17 profiles to skills and has no inline-advisor-skill equivalent, so it carries the same content as a profile. Do NOT "fix" this to 1:1 parity in a port pass.
- **TIER-P — PLATFORM-ONLY.** Meaningful on one side, inapplicable on the other. Never ported. CS-only: `ECOSYSTEM_MODEL_TRACER`. CC-only: `capability-audit`, the `xbeep` hooks + all `payload/hooks/*`.

**ROSTER-COUNT ASYMMETRY IS EXPECTED, NOT A GAP.** CCRT 17/39 vs CSRTB 17/44. The deltas are all explained by tier, never oversight: CSRTB carries a TIER-P Science-only profile (`ECOSYSTEM_MODEL_TRACER`) and the CSRTB-only `GENERALIST`. `research-stats-advisor` is a CC SKILL but a CS PROFILE (carrier asymmetry, TIER-C-like) — not missing. CCRT has agents CSRTB lacks as agents (`machine-doc-reviewer`, `sci-file-indexer`, `version-control-docs`) — some exist CS-side under a different carrier (a Science SKILL legitimately maps to a Code RULE/HOOK). Before treating any count delta as work: classify into S/C/P first; an unclassified item defaults to PORT-CANDIDATE (open work), never silently to excluded.

**THE MIRROR-OBLIGATION INVARIANT.** WHEN a load-bearing item changes on one side ⇒ classify it into a tier in the SAME session; if TIER-S or TIER-C, note the mirror obligation. For TIER-C, re-EXPRESS the discipline in the other platform's carrier — do NOT copy the mechanism (copying would drag a Science-runtime call into a Code file, or vice versa — that is a defect). Worked example: the PLANNER self-check — the CS profile gained a prose self-check gate; the CCRT port added NOT that prose but a one-line pointer to the hooks that already enforce it.

---

## APPENDIX A — COLLABORATION-RATIONALE GROUNDING LEDGER

One row per §4 principle: recovered claim → named corpus instances (the `skills_referenced` edges / description quotes / authority-doc lines it binds to) → grade → scope → friction (+ its own grade) → falsification against a real out-of-corpus case. Built and validated with the `design-rationale` spine (9/9 rows clean: every row has ≥1 instance, a grade, a scope, a graded friction, and — for schema rows — a non-empty falsification). LIMIT: this certifies the spine's FORM was followed, not that each reading is correct.

| # | Principle | Grounded in (instances) | Grade | Scope | Friction | Falsification |
|---|---|---|---|---|---|---|
| 0 | A planner persona is a ROUTING agent, not a doer: it bundles the decomposition/routing skills it needs and loads only request-archetypes by default, naming the rest (delegation-planning, preflight-parallel, plan/solo/collab) as on-demand references — so archetype recognition is always-on but the heavier routing machinery loads only when a plan is being built. | ccrt planner skills_referenced=[baton,collab,delegation-planning,directing-execution,eliciting-llm-behavior,machine-md,plan,preflight-parallel,request-archetypes,solo], loaded_by_default=[request-archetypes]; csrtb PLANNER skills_referenced=[collab,delegation-planning,eliciting-llm-behavior,handoff-brief,machine-md,plan,preflight-parallel,request-archetypes,solo], loaded_by_default=[request-archetypes]; both planner descriptions: 'Loads the delegation-planning skill' | stated | schema | a monolithic planner that eager-loads every routing skill wastes context on plans that never fan out; splitting always-on archetype recognition from on-demand routing keeps the persona cheap until a cascade is actually chosen (inferred) | Applied to CrewAI's manager/hierarchical-process agent and LangGraph supervisor pattern: both instantiate a dedicated orchestrator that routes to workers and holds routing logic rather than task execution — fits. The load-by-default split is a Claude-harness specific and does not transfer, so that clause is bounded to this corpus. |
| 1 | The run-time-orchestration carrier is the single largest planned CC↔CS divergence inside a shared persona: CC's planner names directing-execution + baton; CS's PLANNER drops directing-execution and swaps baton→handoff-brief — because the design-time routing vocabulary (four topologies, archetypes) is platform-neutral but the run-time supervise-loop is bound to each platform's subagent SDK (Task tool vs host.delegate). | ccrt planner refs directing-execution + baton; csrtb PLANNER refs neither, refs handoff-brief instead; twin-architecture tier model: delegation-planning + directing-execution SKILLS diverge BY DESIGN at their run-time-SDK sections; comparison_table: directing-execution sim 0.66 (substantive-diverge); baton↔handoff-brief tier C 'same discipline, renamed carrier' | stated | instance | Task tool is synchronous/tree-shared with no mid-run steer; host.delegate is async wait=False with collect/send_message/stop_child — a single shared run-time skill would drag one platform's SDK calls into the other's file (stated) | n/a (instance-scoped) |
| 2 | Document authoring is designed as a SEPARABLE cascade of single-responsibility carriers — recover the rationale (design-rationale), render it as a teaching explainer (teaching-narrative), revise toward publication (writing-science), set expert register (expert-prose-style) — so each stage can fire independently and compose, rather than one skill that both thinks and writes. | ccrt design-rationale-analyst skills_referenced=[design-rationale,expert-prose-style,research-stats-advisor,teaching-narrative,writing-science]; csrtb DESIGN_RATIONALE_ANALYST same set minus research-stats-advisor plus audible-alert; design-rationale SKILL.md 'When this fires vs its neighbors': design-rationale=the thinking, teaching-narrative=the writing, writing-science=revises prose, expert-prose-style=a toggle; design-rationale REF block names teaching-narrative as 'the render engine for the recovered content' | stated | schema | a single author-everything skill couples content-recovery to prose-style, so you cannot reuse the recovered rationale in a machine doc, or restyle prose without re-deriving content; splitting lets the analyst recover once and render many ways (stated) | Applied to the Diátaxis documentation framework (tutorial/how-to/reference/explanation): Diátaxis also refuses one-doc-does-everything, but splits by reader-INTENT not by pipeline STAGE — so the 'separable carriers' schema holds, but 'recover→teach→style stages' is bounded to single-artifact authoring and does not describe a whole-corpus doc taxonomy. |
| 3 | machine-md is the shared FORM primitive for every LLM-read authoring/review carrier: it is referenced by the doc-architecture and prompt agents (llm-doc-architect, prompt-engineer, machine-doc-reviewer, agent-tooling-engineer) and by both planners, functioning as the writing-discipline layer beneath role-specific doc work rather than a standalone deliverable. | skills_referenced edges: ccrt machine-md referenced by llm-doc-architect, prompt-engineer, machine-doc-reviewer, agent-tooling-engineer, planner; machine-md SKILL.md Companion: 'delegate a review pass to the LLM_DOC_ARCHITECT profile'; prompt-engineer desc: 'Uses the eliciting-llm-behavior technique catalog + machine-md form'; comparison_table: machine-md sim 0.65 (substantive-diverge) — the form itself is platform-adapted | stated | instance | LLM-read text (skill descriptions, profile system_prompts, memory rows, task briefs) fails silently when written as human prose — it does not trigger auto-invocation; a shared form primitive makes trigger-conditioned atomic writing reusable across every doc role (stated) | n/a (instance-scoped) |
| 4 | folio/folio-science are RENDER BACKENDS wired at the skill-to-skill layer, not agent-referenced carriers: no agent or profile names them in skills_referenced; they are reached through doc-pipeline (author→translate→render) and the folio↔folio-science TIER-C rename, so the render step is deliberately decoupled from the doc-authoring personas. | skills_referenced scan: folio/folio-science absent from every ccrt agent and csrtb profile edge list; comparison_table: folio↔folio-science tier C 'same discipline, renamed carrier'; doc-pipeline note 'render backend swap to folio' | inferred | instance | binding a render backend directly into an authoring persona would couple content to one output format; keeping render as a downstream skill lets the same recovered/authored content target local-pandoc (CC) or offline-typst (CS) without touching the author (inferred) | n/a (instance-scoped) |
| 5 | A domain modeler OWNS the physics/mechanism and DEFERS statistical-method choice to a dedicated stats authority: the modeling agents load their domain/physics skills by default but reference research-stats-advisor (CC skill) / RESEARCH_STATS_ADVISOR (CS profile) for the WHY/WHICH of statistics — a clean separation of mechanism-ownership from method-selection. | ccrt micromet-reconstructor desc: 'DEFERS statistical method choice to research-stats-advisor'; refs research-stats-advisor + 8 domain/stats skills; ccrt ml-hybrid-process-modeler loaded_by_default=[biosphere-atmosphere-flux-exchange,physics-informed-ml], refs research-stats-advisor; machine-learning-scientist loaded_by_default=[scientific-ml-fundamentals,temporal-block-cv], refs research-stats-advisor; comparison_table: research-stats-advisor is CC-skill ↔ CS-profile (tier C carrier asymmetry) | stated | schema | a modeler that also adjudicates its own CV scheme / prior / hierarchical structure conflates mechanism with method and tends to defend in-sample fit; routing method-choice to a stats authority keeps the physics owner from grading its own statistics (inferred) | Applied to a typical applied-ML team where one engineer both builds the model and picks the CV split: the separation degrades to instance-only there — so the schema holds specifically where a dedicated stats-methodology authority is instantiated as its own carrier, and weakens to a role-hygiene preference where roles are fused. |
| 6 | Verification carriers are designed to COMPUTE claims rather than read around them, and are deliberately low-coupling: formal-argument-checker references zero skills (fully self-contained — it recomputes the identity/probability itself), while code-review-debugger references only the temporal/tz/perf method skills it validates against. | formal-argument-checker skills_referenced=[] (both CC agent and CSRTB FORMAL_ARGUMENT_CHECKER); formal-argument-checker desc: 'Verifies the formal and quantitative claims by computing them, not by reading around them'; ccrt code-review-debugger refs=[julia-performance-correctness,mgcv-temporal-gam,temporal-block-cv,tz-safe-timestamps]; CSRTB CODE_REVIEW_DEBUGGER desc adds 'validating assertions after each fix' | stated | schema | a checker that cites other checkers can launder an unverified claim through a chain of references; a self-contained checker that recomputes the claim has no such escape hatch (inferred) | Applied to a static type-checker / linter vs a human style reviewer: the automated checker computes and does not defer (fits the schema); a human reviewer who reads-around does not — so the schema is bounded to compute-capable verification carriers, which is exactly the class these agents belong to. |
| 7 | The claim-vs-record verification DISCIPLINE is shared but its GATE HARDNESS is platform-set: CC enforces it with deterministic hooks that BLOCK (exit 2 before a write lands); CS can only APPROXIMATE with a prose self-check that emits a marker for the background reviewer to SCORE — a hard gate vs a soft gate, and the CC form is the stronger one. | twin-architecture tier model, claim-vs-record verification: CC hooks (claim-verify-guard.sh PreToolUse BLOCKS exit 2) vs CS PLANNER prose self-check + [[claim_check]] marker scored by background reviewer; comparison_table: verification-loop is CSRTB C† with 'CC analog = claim-verify-guard hook'; provenance-guard C 'CC: provenance-over-description RULE + pre-complete-verification hook'; twin-architecture tier model: CC has deterministic hooks that fire on real events and can BLOCK; CS has no hook surface | stated | instance | CS sandbox exposes no hook surface, so a hard pre-write block is mechanically impossible there; the strongest available CS approximation is a soft reviewer that scores after the fact (stated) | n/a (instance-scoped) |
| 8 | Platform-ubiquitous side-effects are attached at the PROFILE layer on CS, not the skill layer: audible-alert is referenced by all 17/17 CSRTB profiles as a standing behavior, whereas CC carries the same completion-alert need as hooks (xbeep) that fire on native events with no per-agent wiring — the carrier moves from event-hook (CC) to profile-standing-behavior (CS) because CS has no hook surface. | skills_referenced scan: audible-alert present in 17 of 17 CSRTB profile edge lists; audible-alert desc: 'the Science-native analog of the Claude Code toolkit's xbeep hook'; twin-architecture tier model, completion-alert case | stated | schema | CC fires the beep from a Stop/Notification hook with zero per-agent code; CS has no turn-end hook, so a ubiquitous side-effect must be re-declared as a standing behavior in every profile that wants it — the fan-in to 17/17 is the mechanical cost of the missing hook surface (stated) | Applied to a cross-cutting concern like logging in a framework with vs without aspect/middleware support: with middleware it is wired once (hook-like); without, it is repeated in every handler (profile-like) — the schema (no shared interception point ⇒ concern re-declared per unit) holds beyond this corpus. |
