---
name: request-archetypes
description: Invoke WHEN about to plan or fulfil a user request and you need to recognize its TASK ARCHETYPE and reach for the right carriers FIRST — a lookup of common request types (handoff document, planning, skill/agent authoring, code review, data indexing, figure, methods doc, stats-method choice, manuscript, ...) => which specialists to consider, which skills to load, and which OUTPUT FORM actually works (e.g. a handoff request => ALWAYS machine-md via baton, never freehand prose). Fires during /plan (route the plan by naming the archetype first) and any time you must map a request to carriers. Empirically grounded in 1471 mined user requests across the corpus.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-19). Authored for Claude Code from the v2.0 request-archetypes registry (reverse port); carriers remapped to the toolkit's agents+skills.

# request-archetypes — recognize the request TYPE, reach for the right carriers first

## What this is
A lookup table: **common user-request archetype => (specialists to consider first, skills to load, canonical output FORM, worked example).** It exists to make archetype recognition a REQUIRED, explicit step before planning or execution — so a request is matched to its proven carriers instead of handled ad hoc.

## How to use (the recognition step)
WHEN about to plan or fulfil a request => FIRST name its archetype from the tells below, THEN adopt that row's specialists/skills/output-form as the default. If a request spans two archetypes, apply both rows. If NO row matches => say so and treat as generic (do NOT force-fit — see Anti-over-fire).

## THE load-bearing rule (read first)
**A handoff / consolidation / "don't lose what we learned" / durable-resume-point request => the output FORM is ALWAYS machine-md (LLM-facing), authored via `baton`, NEVER freehand narrative prose.** This is the single most-missed mapping (it caused a real /plan failure: a handoff doc was planned as "narrative prose (the load-bearing content)" instead of machine-md). Recognizing "handoff" => machine-md is the highest-value line in this file.

## The registry (17 actionable archetypes, frequency-ranked from 1471 mined requests)

### explain/answer question  (empirical n=172)
- TRIGGER TELLS: "please explain to me how we will address the issues of diel ..." · "before [building], first, please explain ..."
- => SPECIALISTS (consider first): **the relevant domain-specialist agent**
- => SKILLS (load): —
- => OUTPUT FORM: an in-chat conceptual explanation (no artifact) — answer from knowledge, cite if verifying a specific claim
- NOTE: Descriptive, not analytic => usually no delegation, no artifact. Route to the domain specialist only if deep.

### planning/decomposition  (empirical n=120)
- TRIGGER TELLS: "Please propose a plan to respond to my points" · "And where are we in the plan?"
- => SPECIALISTS (consider first): **planner**
- => SKILLS (load): `plan`, `delegation-planning`
- => OUTPUT FORM: an approved, routed, gated step-list plan (each phase: OWNER + EXECUTION + TRADEOFF)
- NOTE: Fire /plan; the routing mandate requires naming specialists/skills + topology per phase.

### skill/agent authoring  (empirical n=116)
- TRIGGER TELLS: "'ecophysiology + carbon-optimality modeler, reproduce-from-l..." · "please create a purely \"science writing\" style agent, based ..."
- => SPECIALISTS (consider first): **agent-tooling-engineer, llm-doc-architect**
- => SKILLS (load): `toolkit-extension-authoring`, `machine-md`, `eliciting-llm-behavior`
- => OUTPUT FORM: a new/edited skill SKILL.md or agent markdown (frontmatter + system-prompt body, machine-md style), structurally gated + installed
- NOTE: Authoring the customization layer itself => agent-tooling-engineer + toolkit-extension-authoring.

### code review/debug  (empirical n=104)
- TRIGGER TELLS: "did we ever apply the IRGA correction ... to H2O?" · "Probably worth also checking the jsonl transcripts, to pin d..."
- => SPECIALISTS (consider first): **code-review-debugger**
- => SKILLS (load): —
- => OUTPUT FORM: a verification answer grounded in the actual code + outputs (semantic correctness, not just syntax)
- NOTE: Read internals before trusting outputs; add semantic assertions after a fix.

### data packaging/indexing  (empirical n=78)
- TRIGGER TELLS: "please save them to a named silver/gold output folder" · "make it one bundle, that I can share with another project"
- => SPECIALISTS (consider first): **research-data-manager**
- => SKILLS (load): `sci-file-index`, `sci-library-curate`
- => OUTPUT FORM: files written to a specified folder + a reproducible index/manifest with provenance
- NOTE: Save to the exact named folder; ledger the operation with provenance (never mtime).

### verification/audit-correction  (empirical n=67)
- TRIGGER TELLS: "check if ... has errors or is a hallucination" · "carefully check over again... ONLY list the articles [not in..."
- => SPECIALISTS (consider first): **code-review-debugger, formal-argument-checker**
- => SKILLS (load): —
- => OUTPUT FORM: a verification result — confirmation/refutation with cited evidence (is it real or a hallucination?)
- NOTE: Compute the claim; cite the source line. formal-argument-checker for quantitative/logical claims.

### handoff document  (empirical n=60)
- TRIGGER TELLS: "consolidate everything we've learned (in a way we don't lose..." · "wrap up/store progress in a durable, easy[-to-resume] [form]"
- => SPECIALISTS (consider first): **design-rationale-analyst, research-data-manager**
- => SKILLS (load): `baton`, `machine-md`
- => OUTPUT FORM: machine-md handoff doc (LLM-facing) + paste-ready resume prompt — ALWAYS machine-md, never freehand prose
- NOTE: THE load-bearing case. A handoff/consolidation/resume-point request => machine-md via baton, NOT narrative prose. This is the exact handoff-as-narrative miss the load-bearing rule prevents.

### analysis pipeline  (empirical n=58)
- TRIGGER TELLS: "I want the chunk fitting to be Bayesian. That is a hard requ..." · "within-variable, multi-sensor drift detection"
- => SPECIALISTS (consider first): **micromet-reconstructor, machine-learning-scientist, ml-hybrid-process-modeler, ecophysiology-modeler** — [RE-POINTED 2026-08-09] all four LEFT the general payload for the `CCRT_specialists/` tree, a MANUAL-INSTALL set copied in by hand (no installer flag; browse the tree for the bucket), so they are available only where someone installed that bucket. WHEN none is installed ⇒ say so and route the work to `software-developer` under `research-stats-advisor`, rather than naming a specialist the session cannot launch.
- => SKILLS (load): —
- => OUTPUT FORM: runnable R/Stan/Python implementing the actual gap-fill / interpolation / model-fit, with QC
- NOTE: Pick the domain specialist by data type; load `research-stats-advisor` first if the METHOD is unsettled.

### config/environment setup  (empirical n=54)
- TRIGGER TELLS: "Please read the contents of [bundle] and install the toolkit" · "checking file structure in ~/.claude ..."
- => SPECIALISTS (consider first): **agent-tooling-engineer, main agent**
- => SKILLS (load): `toolkit-extension-authoring`
- => OUTPUT FORM: installed/configured bundle or compute access (verified live)

### figure/plot  (empirical n=49)
- TRIGGER TELLS: "can you produce a series of QA/QC plots, showing ... gap-fill ..." · "make a new version of that same plot, that only shows ..."
- => SPECIALISTS (consider first): **main agent**
- => SKILLS (load): —
- => OUTPUT FORM: PNG figure(s) saved to durable, tracked paths; apply publication-grade figure discipline before rendering any ship/deliverable figure
- NOTE: A quick EDA look plots plainly; a figure that ships (report/paper/export) gets the publication-grade pass first.

### documentation authoring  (empirical n=47)
- TRIGGER TELLS: "please write comprehensive methods for the entire pipeline, " · "carefully review the docs (machine and human md files) ... no "
- => SPECIALISTS (consider first): **llm-doc-architect, research-data-manager**
- => SKILLS (load): `machine-md`, `folio`
- => OUTPUT FORM: machine-md source + rendered human-md/PDF twin (a living, updated methods doc incl. rationale)
- NOTE: Author to `machine-md`; render the human/PDF twin with `folio`.

### testing/validation  (empirical n=34)
- TRIGGER TELLS: "we can do real beta-testing of this" · "When I ran the first post-verification test, I got:"
- => SPECIALISTS (consider first): **code-review-debugger, main agent**
- => SKILLS (load): —
- => OUTPUT FORM: a test/verification plan or a live end-to-end run (beta-test / dogfood), with pass/fail evidence

### manuscript/scientific writing  (empirical n=26)
- TRIGGER TELLS: "start to flesh out our first full rough draft manuscript ... S..." · "Run the figure-story analysis ... write Results backwards from..."
- => SPECIALISTS (consider first): **science-writing-stylist**
- => SKILLS (load): `writing-science`
- => OUTPUT FORM: prose/manuscript text (draft or revised sections), Schimel Writing-Science craft applied
- NOTE: Reader=human => writing-science, NOT machine-md.

### statistical-method decision  (empirical n=24)
- TRIGGER TELLS: "in the Bayesian model, are we using the right approach ... sin..." · "we should actually try cube-root transform for gap fraction"
- => SPECIALISTS (consider first): **main agent (executing) + the `research-stats-advisor` skill**
- => SKILLS (load): `research-stats-advisor`
- => OUTPUT FORM: a method recommendation + rationale (which model/transform/approach + why); may change the pipeline
- NOTE: Method SELECTION lives here (the research-stats-advisor skill), NOT with the pipeline implementer (code-review-debugger does not do method choice).

### interpret results  (empirical n=18)
- TRIGGER TELLS: "what are the headline results, in terms of the conceptual fr..." · "hadn't you said s(height) was best? ... why don't these look l..."
- => SPECIALISTS (consider first): **the domain-specialist agent for the data**
- => SKILLS (load): —
- => OUTPUT FORM: an explanation of what a result MEANS against the hypotheses/framework (no new artifact)

### data/code migration/porting  (empirical n=10)
- TRIGGER TELLS: "fully merge/share all the projects from the two different accounts" · "port all the projects and all the skills/agents ... to ..."
- => SPECIALISTS (consider first): **research-data-manager, agent-tooling-engineer**
- => OUTPUT FORM: a cross-account/machine port + merge runbook + helper scripts, content-hash verified
- NOTE: determine canonical by content-hash + provenance, NOT mtime (see the additive-install postmortem).

### prompt engineering  (empirical n=7)
- TRIGGER TELLS: "Please re-write the prompt below (this is the project-level ..." · "split into two separate documents ... durable invariant 'glo..."
- => SPECIALISTS (consider first): **prompt-engineer, llm-doc-architect**
- => SKILLS (load): `machine-md`, `eliciting-llm-behavior`
- => OUTPUT FORM: a rewritten, tighter, lower-token prompt/context (machine-md style if LLM-facing)

## Request MODIFIERS (recognize, but they don't name a deliverable)
These recur heavily but steer an EXISTING task rather than name a new deliverable — do NOT route them to a carrier:
- **session flow control** ("continue", "proceed", "go ahead", "pause here", "resume") => obey the dial (/solo /collab /plan); no artifact, no delegation.
- **substantive steering / course-correction** ("actually, do X instead", "pause at a safe point") => adjust in-flight work; if directing a running plan, see `directing-execution`.
- **scope/constraint-setting** ("must cover ALL regions", "render as PDF too", "v3 should...") => a binding constraint to honor, not a task type.
- **context/resource provision** ("use the local machine for heavy CPU", "<=6 cores", "always parallelize") => a HOW/WHERE directive; route compute accordingly (size with `preflight-parallel`).

## Anti-over-fire (do NOT force-fit)
- A request that matches NO archetype => name that it's novel and handle generically; never bend it to the nearest row for the sake of routing.
- Trigger tells are EVIDENCE of a type, not a keyword trap — a prompt containing "plan" inside a data request is still a data request.
- The specialists/skills are "consider FIRST", not mandatory — a simple in-chat answer needs no delegation and no skill load.
- Frequencies are descriptive (what the user asked for historically), not a priority ranking.

## Non-goals
- This is the WHAT (which archetype => which carriers). The HOW of distributing across agents + choosing cascade topology lives in `delegation-planning`; the run-time supervise loop in `directing-execution`; the /plan mandate that CALLS this recognition step lives in the `plan` skill.
- Not a method-selection authority: statistical/experimental METHOD choice routes to the `research-stats-advisor` skill, it is not decided here.

## Provenance
Built from 1471 classified user requests mined across 56 root conversations / 12 projects (user-side prompts isolated + clustered). Frequency = empirical count. Refresh by re-mining when the corpus grows materially.

## Refs
`plan` (the mandate that fires this) · `delegation-planning` (routing HOW) · `directing-execution` (run-time) · `baton`/`machine-md` (the load-bearing carrier) · `toolkit-extension-authoring` (authoring) · `planner` agent (loads this by default).
