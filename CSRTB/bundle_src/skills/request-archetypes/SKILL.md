---
name: request-archetypes
description: Invoke WHEN about to plan or fulfil a user request and you need to recognize its TASK ARCHETYPE and reach for the right carriers FIRST — a lookup of common request types (handoff document, planning, skill/agent authoring, code review, data indexing, figure, methods doc, stats-method choice, manuscript, …) ⇒ which specialists to consider, which skills to load, and which OUTPUT FORM actually works (e.g. a handoff request ⇒ ALWAYS machine-md via handoff-brief, never freehand prose). Fires during /plan (RULE.route_the_plan names the archetype first) and any time you must map a request to carriers. Empirically grounded in 1471 mined user requests across the corpus.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# request-archetypes — recognize the request TYPE, reach for the right carriers first

## What this is
A lookup table: **common user-request archetype ⇒ (specialists to consider first, skills to load, canonical output FORM, worked example).** It exists to make archetype recognition a REQUIRED, explicit step before planning or execution — so a request is matched to its proven carriers instead of handled ad hoc.

## How to use (the recognition step)
WHEN about to plan or fulfil a request ⇒ FIRST name its archetype from the tells below, THEN adopt that row's specialists/skills/output-form as the default. If a request spans two archetypes, apply both rows. If NO row matches ⇒ say so and treat as generic (do NOT force-fit — see Anti-over-fire).

## THE load-bearing rule (read first)
**A handoff / consolidation / "don't lose what we learned" / durable-resume-point request ⇒ the output FORM is ALWAYS machine-md (LLM-facing), authored via `handoff-brief` + `machine-md`, NEVER freehand narrative prose.** This is the single most-missed mapping (it caused a real /plan failure: a handoff doc was planned as "narrative prose (the load-bearing content)" instead of machine-md). Recognizing "handoff" ⇒ machine-md is the highest-value line in this file.

## The registry (17 actionable archetypes, frequency-ranked from 1471 mined requests)

### explain/answer question  (empirical n=172)
- TRIGGER TELLS: "please explain to me how we will address the issues of diel " · "whatever the most rigorous, accurate versions of the VPD cal" · "Bayesian is also the appropriate tool, to deal with … skew/k" · "before [building], first, please explain …"
- ⇒ SPECIALISTS (consider first): **(context specialist)**
- ⇒ SKILLS (load): —
- ⇒ OUTPUT FORM: an in-chat conceptual explanation (no artifact) — answer from knowledge, cite if verifying a specific claim
- NOTE: Descriptive, not analytic ⇒ usually no delegation, no artifact. Route to the domain specialist only if deep.

### planning/decomposition  (empirical n=120)
- TRIGGER TELLS: "Please propose a plan to respond to my points" · "what's our next obvious step from here?" · "Ok, what is the next step in the plan?" · "And where are we in the plan?"
- ⇒ SPECIALISTS (consider first): **PLANNER**
- ⇒ SKILLS (load): `plan`, `delegation-planning`
- ⇒ OUTPUT FORM: an approved, routed, gated step-list plan (each phase: OWNER + EXECUTION + TRADEOFF)
- NOTE: Fire /plan; the routing mandate requires naming specialists/skills + topology per phase.

### skill/agent authoring  (empirical n=116)
- TRIGGER TELLS: "'ecophysiology + carbon-optimality modeler, reproduce-from-l" · "we may want to consider a SEPARATE, even broader … profile" · "any biological-systems / dynamical model … profile" · "please create a purely "science writing" style agent, based "
- ⇒ SPECIALISTS (consider first): **AGENT_TOOLING_ENGINEER, LLM_DOC_ARCHITECT**
- ⇒ SKILLS (load): `customize`, `skill-creator`, `machine-md`, `eliciting-llm-behavior`
- ⇒ OUTPUT FORM: a new/edited skill SKILL.md or agent profile system_prompt (machine-md style), structurally gated + published
- NOTE: Authoring the customization layer itself ⇒ AGENT_TOOLING_ENGINEER + customize/skill-creator.

### code review/debug  (empirical n=104)
- TRIGGER TELLS: "Just to check, …" · "did we ever apply the IRGA correction … to H2O?" · "are we maintaining the ~0m/s wind speed soft prior for h=0m?" · "Probably worth also checking the jsonl transcripts, to pin d"
- ⇒ SPECIALISTS (consider first): **CODE_REVIEW_DEBUGGER**
- ⇒ SKILLS (load): —
- ⇒ OUTPUT FORM: a verification answer grounded in the actual code + artifacts (semantic correctness, not just syntax)
- NOTE: Read internals before trusting outputs; add semantic assertions after a fix.

### data packaging/indexing  (empirical n=78)
- TRIGGER TELLS: "please save them to: '/Users/…/Tower output silver'" · "can you locate these prior filled outputs?" · "include a provenance readme in the bronze folder" · "make it one bundle, that I can share with another project"
- ⇒ SPECIALISTS (consider first): **RESEARCH_DATA_MANAGER**
- ⇒ SKILLS (load): `sci-file-index`, `sci-library-curate`, `provenance-over-description`
- ⇒ OUTPUT FORM: files written to a specified host folder + a reproducible index/manifest with provenance
- NOTE: Save to the exact named folder; ledger the operation.

### verification/audit-correction  (empirical n=67)
- TRIGGER TELLS: "check if ... has errors or is a hallucination" · "PDFs NOT yet in hand/download/check-whether-hallucination-or" · "find ALL phrases they use that could POSSIBLY be construed ." · "carefully check over again... ONLY list the articles [not in"
- ⇒ SPECIALISTS (consider first): **CODE_REVIEW_DEBUGGER, FORMAL_ARGUMENT_CHECKER**
- ⇒ SKILLS (load): `provenance-over-description`
- ⇒ OUTPUT FORM: a verification result — confirmation/refutation with cited evidence (is it real or a hallucination?)
- NOTE: Compute the claim; cite the source line. FORMAL_ARGUMENT_CHECKER for quantitative/logical claims.

### handoff document  (empirical n=60)
- TRIGGER TELLS: "consolidate everything we've learned (in a way we don't lose" · "we have a running document of development (current vs stale)" · "we MUST make sure ALL our methods/code are saved as durable," · "wrap up/store progress in a durable, easy[-to-resume] [form]"
- ⇒ SPECIALISTS (consider first): **DESIGN_RATIONALE_ANALYST, RESEARCH_DATA_MANAGER**
- ⇒ SKILLS (load): `handoff-brief`, `machine-md`
- ⇒ OUTPUT FORM: machine-md handoff doc (LLM-facing) + paste-ready starter prompt — ALWAYS machine-md, never freehand prose
- NOTE: THE load-bearing case. A handoff/consolidation/resume-point request ⇒ machine-md via handoff-brief, NOT narrative prose. This is the exact Givnish miss.

### analysis pipeline  (empirical n=58)
- TRIGGER TELLS: "I want the chunk fitting to be Bayesian. That is a hard requ" · "let's ALSO make sure to apply the priors for rate/speed of c" · "convert all vpd < 0 to vpd = 0" · "within-variable, multi-sensor drift detection"
- ⇒ SPECIALISTS (consider first): **MICROMET_RECONSTRUCTOR, MACHINE_LEARNING_SCIENTIST, ML_HYBRID_PROCESS_MODELER, ECOPHYSIOLOGY_MODELER**
- ⇒ SKILLS (load): —
- ⇒ OUTPUT FORM: runnable R/Stan/Python implementing the actual gap-fill / interpolation / model-fit, with QC
- NOTE: Pick the domain specialist by data type; RESEARCH_STATS_ADVISOR first if the METHOD is unsettled.

### config/environment setup  (empirical n=54)
- TRIGGER TELLS: "Please read the contents of [bundle] and install the Claude " · "checking file structure in /.claude-science ... via Claude C" · "Please save all outputs to [folder]" · "do file exploration THROUGH Claude Code via mac-local"
- ⇒ SPECIALISTS (consider first): **AGENT_TOOLING_ENGINEER, GENERALIST**
- ⇒ SKILLS (load): `customize`, `remote-compute-ssh`
- ⇒ OUTPUT FORM: installed/configured bundle or compute access (verified live)

### figure/plot  (empirical n=49)
- TRIGGER TELLS: "can you produce a series of QA/QC plots, showing … gap-fill " · "make a new version of that same plot, that only shows …" · "the same plot, but excluding the low-mid canopy species (Cou" · "Can you show the same plots, but filtered to daytime?"
- ⇒ SPECIALISTS (consider first): **GENERALIST**
- ⇒ SKILLS (load): `figure-style`, `figure-composer`
- ⇒ OUTPUT FORM: PNG figure(s) saved as durable artifacts; publication-grade via figure-style; multi-panel via figure-composer
- NOTE: Load figure-style for any ship/deliverable figure BEFORE rendering.

### documentation authoring  (empirical n=47)
- TRIGGER TELLS: "make sure we have a dynamic, consistently updated document o" · "please write comprehensive methods for the entire pipeline, " · "For the final PDF, make sure to include figures for explaini" · "carefully review the docs (machine and human md files) … no "
- ⇒ SPECIALISTS (consider first): **LLM_DOC_ARCHITECT, RESEARCH_DATA_MANAGER**
- ⇒ SKILLS (load): `doc-pipeline`, `durable-doc-architecture`, `machine-md`
- ⇒ OUTPUT FORM: machine-md source + rendered human-md/PDF twin (a living, updated methods doc incl. rationale)
- NOTE: doc-pipeline for author⇒translate⇒render; durable-doc-architecture for the project's reference-doc set.

### testing/validation  (empirical n=34)
- TRIGGER TELLS: "we can do real beta-testing of this" · "it would be good to test the Claude Code toolkit on a Linux " · "we'll do all live testing on the OSX side in one go" · "When I ran the first post-verification test, I got:"
- ⇒ SPECIALISTS (consider first): **CODE_REVIEW_DEBUGGER, GENERALIST**
- ⇒ SKILLS (load): —
- ⇒ OUTPUT FORM: a test/verification plan or a live end-to-end run (beta-test / dogfood), with pass/fail evidence

### manuscript/scientific writing  (empirical n=26)
- TRIGGER TELLS: "start to flesh out our first full rough draft manuscript … S" · "Run the figure-story analysis … write Results backwards from" · "we need to ground the writing with the plots … the plots got" · "a SEPARATE manuscript skeleton outline … that logs the impor"
- ⇒ SPECIALISTS (consider first): **SCIENCE_WRITING_STYLIST**
- ⇒ SKILLS (load): `writing-science`
- ⇒ OUTPUT FORM: prose/manuscript text (draft or revised sections), Schimel Writing-Science craft applied
- NOTE: Reader=human ⇒ writing-science, NOT machine-md.

### statistical-method decision  (empirical n=24)
- TRIGGER TELLS: "in the Bayesian model, are we using the right approach … sin" · "are we log-transforming raw richness, or modeling in log spa" · "run all tests with both sample_mass alone, and sample_mass +" · "we should actually try cube-root transform for gap fraction"
- ⇒ SPECIALISTS (consider first): **RESEARCH_STATS_ADVISOR**
- ⇒ SKILLS (load): —
- ⇒ OUTPUT FORM: a method recommendation + rationale (which model/transform/approach + why); may change the pipeline
- NOTE: Method SELECTION lives here, NOT with the pipeline implementer (CODE_REVIEW_DEBUGGER does not do method choice).

### interpret results  (empirical n=18)
- TRIGGER TELLS: "what are the headline results, in terms of the conceptual fr" · "hadn't you said s(height) was best? … why don't these look l" · "from a "functional" perspective, we would expect the opposit" · "still striking, how similar they are (epiphytic CFU vs endop"
- ⇒ SPECIALISTS (consider first): **(domain specialist for the data)**
- ⇒ SKILLS (load): —
- ⇒ OUTPUT FORM: an explanation of what a result MEANS against the hypotheses/framework (no new artifact)

### data/code migration/porting  (empirical n=10)
- TRIGGER TELLS: "fully merge/share all the projects from the two different 'o" · "port all the projects and all the skills/specialists ... to " · "push everything ... back to user/org account A" · "copy-migrate to [folder]"
- ⇒ SPECIALISTS (consider first): **RESEARCH_DATA_MANAGER, AGENT_TOOLING_ENGINEER**
- ⇒ SKILLS (load): `provenance-over-description`
- ⇒ OUTPUT FORM: a cross-account/org merge runbook + helper scripts, content-hash verified
- NOTE: Determine canonical by content-hash + provenance, NOT mtime (see additive-install postmortem).

### prompt engineering  (empirical n=7)
- TRIGGER TELLS: "Please re-write the prompt below (this is the project-level " · "Please re-work and improve this prompt, which will be the ag" · "overwrite with the new expert-prose-style from the bundle" · "split into two separate documents ... durable invariant 'glo"
- ⇒ SPECIALISTS (consider first): **PROMPT_ENGINEER, LLM_DOC_ARCHITECT**
- ⇒ SKILLS (load): `machine-md`, `eliciting-llm-behavior`
- ⇒ OUTPUT FORM: a rewritten, tighter, lower-token prompt/context (machine-md style if LLM-facing)

## Request MODIFIERS (recognize, but they don't name a deliverable)
These recur heavily but steer an EXISTING task rather than name a new deliverable — do NOT route them to a carrier:
- **session flow control** ("continue", "proceed", "go ahead", "pause here", "resume") ⇒ obey the dial (/solo /collab /plan); no artifact, no delegation.
- **substantive steering / course-correction** ("actually, do X instead", "pause at a safe point") ⇒ adjust in-flight work; if directing a running plan, see `directing-execution`.
- **scope/constraint-setting** ("must cover ALL regions", "render as PDF too", "v3 should…") ⇒ a binding constraint to honor, not a task type.
- **context/resource provision** ("use mac-local for heavy CPU", "≤6 cores", "always parallelize") ⇒ a HOW/WHERE directive; route compute accordingly.

## Anti-over-fire (do NOT force-fit)
- A request that matches NO archetype ⇒ name that it's novel and handle generically; never bend it to the nearest row for the sake of routing.
- Trigger tells are EVIDENCE of a type, not a keyword trap — a prompt containing "plan" inside a data request is still a data request.
- The specialists/skills are "consider FIRST", not mandatory — a simple in-chat answer needs no delegation and no skill load.
- Frequencies are descriptive (what the user asked for historically), not a priority ranking.

## Non-goals
- This is the WHAT (which archetype ⇒ which carriers). The HOW of distributing across agents + choosing cascade topology lives in `delegation-planning`; the run-time supervise loop in `directing-execution`; the /plan mandate that CALLS this recognition step lives in the `plan` skill.
- Not a method-selection authority: statistical/experimental METHOD choice routes to RESEARCH_STATS_ADVISOR, it is not decided here.

## Provenance
Built from 1471 classified user requests mined across 56 root conversations / 12 projects (user-side prompts isolated + clustered). Frequency = empirical count. Refresh by re-mining when the corpus grows materially.

## Refs
`plan` (the mandate that fires this) · `delegation-planning` (routing HOW) · `directing-execution` (run-time) · `handoff-brief`/`machine-md` (the load-bearing carrier) · `customize`/`skill-creator` (authoring) · PLANNER profile (loads this by default).