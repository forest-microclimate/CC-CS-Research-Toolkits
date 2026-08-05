---
name: eliciting-llm-behavior
description: Invoke WHEN about to write a prompt that must make a model RELIABLY produce a specific behavior, format, or reasoning path — a host.llm call, a host.delegate sub-agent task, a tool/output schema, or any instruction where "it sometimes ignores this" is a real risk. Supplies the TECHNIQUE catalog (which structural lever elicits which behavior). Pairs with machine-md for the text's FORM and skill-creator for MEASURING efficacy; it does NOT cover prose style — that is machine-md.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# eliciting-llm-behavior.machine.md  (machine-optimized; primary reader = the agent authoring a prompt)
# WHAT: the "which lever" catalog. Three complementary legs — machine-md = how to WRITE agent-read text (FORM); skill-creator = how to MEASURE a skill (EVAL); THIS = which STRUCTURAL DEVICE reliably elicits a target model BEHAVIOR (TECHNIQUE). REF the other two; do NOT restate them.
# WHY: an exhortation inside a prompt ("please output JSON", "be thorough", "don't forget X") is the WEAKEST lever — surfacing ≠ enforcement, same law as the standing mandate. A structural device that constrains the decode space fires BY CONSTRUCTION. Measured: forcing a tool/output schema fixed ~72% parse-failure; an emit-time adversarial gate cut a failure mode 100%→12%. Reach for the device, not the plea.

## TECHNIQUE TRIGGERS  (each = WHEN <the behavior you need> ⇒ DO <the lever>)
- WHEN you need PARSEABLE / fixed-shape output (named fields, a table, a verdict) ⇒ FORCE a schema — `host.llm(..., tools=[schema], tool_choice=...)` or `host.delegate(output_schema=...)` — never request the format in prose. A constrained decode space cannot drift. This is the STRONGEST lever; prefer it over every softer one below.
- WHEN the answer must be ONE OF a fixed set ⇒ put the allowed values in an enum/schema, not a prose list ("reply high|med|low" drifts; an enum cannot emit a fourth value).
- WHEN the task has a reliable INPUT→OUTPUT shape the model keeps missing ⇒ give 1–3 FEW-SHOT exemplars of the exact transform (show, don't tell); match the exemplar's format to the wanted output byte-for-byte (the model copies what it sees, including stray formatting).
- WHEN the task is COMPOUND / multi-step ⇒ DECOMPOSE — ordered explicit steps in one prompt, or separate chained calls — rather than one leap; a model asked to do five things at once silently drops some.
- WHEN correctness needs REASONING before the answer ⇒ scaffold it: ask for the working FIRST, the answer LAST. BUT for utility extraction/classification prefer schema-forcing over free chain-of-thought (cheaper, parseable, and the reasoning-model default already reasons internally).
- WHEN expertise or a viewpoint frames the task ⇒ ASSIGN the role in the SYSTEM slot ("You are X…"), not buried mid-prompt; the system position weights hardest.
- WHEN the model keeps doing an UNWANTED thing ⇒ state the fix as a POSITIVE redirect (do Y instead), not a bare prohibition — positive trigger-conditioned framing fires better than "don't", and names the wanted behavior at the moment it is due (machine-md core).
- WHEN fanning out over many items ⇒ `host.llm` LIST form with `max_concurrency` (positional map-reduce), one exemplar per call — a Python loop over single `host.llm` calls runs SERIALLY and wastes wall-clock.
- WHEN a long prompt buries the ask ⇒ lead with the task in ONE line, then constraints as a scannable list, examples ADJACENT to the instruction they illustrate — primacy + recency both fire; the MIDDLE of a long prompt is where instructions get dropped.

## MEASURE  (efficacy ≠ existence — the mandatory close)
- WHEN you claim a prompt change "works" ⇒ A/B it: run OLD vs NEW N times, count the target behavior, cite the before/after rate. Do NOT assert efficacy from the fact that you added the device. REF skill-creator for the eval-loop + variance harness; for a one-off, a `host.llm` list-form harness over N trials suffices.
- CAVEAT (LLM limits): a device RAISES P(behavior); it does not guarantee it — a schema still needs valid field values, a few-shot still generalizes imperfectly. Stack a cheap verifier on high-consequence output (parse-check, assert, adversarial gate); do not trust the device alone.

# INVARIANT: reach for the structural device that constrains the output space, name the wanted behavior at the decision moment, and MEASURE the lift — never ship a prompt lever on faith.
# REF: machine-md (FORM of any agent-read text — output-detectable triggers, atom-preservation, positive framing) · skill-creator (EVAL — variance harness, description-trigger optimization) · customize (host.llm + host.delegate signatures: output_schema, tools/tool_choice, max_concurrency).
