---
name: teaching-narrative
description: >
  Invoke WHEN writing a NEW explanatory or teaching document whose purpose is to make a reader
  UNDERSTAND and be able to APPLY a concept, method, or framework — a guide, tutorial,
  walkthrough, explainer, or onboarding doc. Deep-teaching register: flowing expert prose on an
  arc (hook → what it is → why it works → the general schema), every abstraction grounded by a
  worked example, the anchor term repeated deliberately, the reasoning made explicit. Inverts
  writing-science's compress-to-cite instinct into EXPAND-to-teach while keeping its OCAR / topic-
  stress mechanics and its detector kernel (re-read through a teaching reframe). Fires on "write a
  tutorial/guide/explainer", "teach X so a reader can apply it", "walk through how Y works". NOT
  for revising a manuscript toward publication (→ writing-science), setting an expert register (→
  expert-prose-style), reshaping a figure deck's story (→ paper-narrative), or recovering
  rationale from a corpus (→ design-rationale).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# teaching-narrative

Write a document that TEACHES — one whose success is measured by whether the reader can
afterward *apply* the concept, not by whether it reads well or gets cited. The output is a
guide, tutorial, walkthrough, explainer, or onboarding doc, in flowing expert prose.

## The core move: invert compress-to-cite into expand-to-teach

`writing-science` optimizes prose to get **cited**: compress, cut redundancy, funnel to the
claim fast, because a busy reviewer's patience is the binding constraint. Teaching optimizes
for **transfer**, and the binding constraint is different — a learner who loses the thread
stops learning. So the instinct **inverts**:

- **Redundancy is a tool, not a defect.** Restate the anchor idea at each new scale; repeat
  the *same term* for the same concept (elegant variation confuses a learner — it reads as a
  new concept). writing-science flags repetition; teaching *deploys* it.
- **Scaffold before you compress.** Introduce one new idea at a time, each resting on the
  last. A dense sentence that a reviewer would praise can be the one that loses a learner.
- **Ground every abstraction in a worked example.** No principle ships without ≥1 concrete
  case the reader can trace. The example is not illustration; it is the load-bearing teaching.
- **Make the reasoning visible.** State *why* each move works, not just what to do — the
  reader is learning to make the move themselves, on a case you will never see.

What does NOT change: the mechanics. OCAR, topic/stress positions, given-to-new flow, and
the draft-level tells (nominalizations, passive voice, weak verbs, buried verbs, noun trains)
harm a teaching draft exactly as they harm a paper. Keep all of that. Only the
compression instinct and a handful of genre-bound detectors flip (see the kernel section).

## The arc

Structure a teaching document on this arc — it is OCAR retuned for transfer:

1. **Hook** — the boldest defensible reason this matters to *the reader*, concretely. Not a
   literature gap; a stake the learner already feels ("your installer silently double-applies
   on a re-run — here's why, and how to make that impossible").
2. **What it is** — name the concept plainly and give the shortest true definition, then the
   first worked example immediately. Definition-then-instance, never definition alone.
3. **Why it works** — the mechanism. This is the section a paper would compress and a teaching
   doc must expand: walk the causal chain, show the failure the mechanism prevents, make the
   reasoning inspectable.
4. **The general schema** — lift from the worked instances to the transferable pattern, and
   say explicitly what generalizes vs what was specific to the example. (If you are teaching
   rationale recovered via `design-rationale`, this is where its instance/schema split gets
   rendered — the analysis decided the boundary; you display it here.)

Each abstraction in every section carries its worked example. An arc with no examples is a
summary, not a teaching document.

## The mechanical layer — reference writing-science, do not copy it

This skill ships a small `kernel.py` (auto-loaded). It does **not** re-ship
writing-science's ~30 detectors — that kernel is shared infrastructure, and a copy would
drift. Instead:

```python
# 1. load writing-science alongside this skill; its kernel auto-injects scan_draft() into scope
scan = scan_draft(draft_text)          # {counts, profile, hits}  (bare name; alias: writing_science__scan_draft)
# 2. re-read that result through the teaching reframe (this skill's kernel)
print(teaching_report(scan))           # defects / advisory / expected
```

`teaching_reframe(scan)` re-buckets the fired detectors into three groups:

- **defects** — every register-neutral tell (nominalizations, passive, weak/buried verbs,
  noun trains, empty amplifiers, hype, …). Fix these; they harm teaching too.
- **advisory** — the five genre-bound detectors whose premise is the paper form:
  `weak_gap_framing` (teaching motivates by learner-need, not a research gap),
  `objectives_not_question` (learning objectives are legitimate), `bizzwidget_opening` (a
  concrete hook is good; only jargon-first openings are bad), `undermining_resolution`
  (honest caveats scaffold; only self-undermining conclusions are bad), and
  `pseudo_explanation` (P2 — stage-direction / learning-objective phrasing narrates the
  reading act, a paper tell, but often legitimate teaching scaffolding that orients a
  learner; all OTHER new P2 detector keys stay defects). Judge these in
  context — do NOT auto-fix.
- **expected** — `repeated_words` **flips to a feature**: anchor-term repetition aids
  retention; elegant variation confuses. Verify the repeated token is the *anchor term*,
  not filler, and move on.

`teaching_reframe` takes the scan dict as an argument, so it is self-contained — it needs
the dict, not writing-science's code in scope. If writing-science is not loaded, load it
first (it provides `scan_draft`); this skill only re-reads its output.

## Diagnostic stance

Measure before you judge, exactly as writing-science teaches — run `scan_draft`, read
`teaching_report`, then read the actual sentences before changing anything. The reframe
tells you which fired detectors to ignore for this register; it does not tell you the draft
teaches well. Whether the *arc* lands, whether each abstraction truly has a worked example,
whether a learner could apply the result — that is judgment the kernel cannot see. The
kernel clears the register-noise so your attention lands on the teaching.

## Scope

For NEW teaching/explanatory prose. For revising a manuscript toward publication →
`writing-science`. For merely setting an expert flowing-prose register (no teaching arc) →
`expert-prose-style`. For reshaping the story a figure deck tells → `paper-narrative`. To
*recover* the rationale you are about to teach from a body of work → `design-rationale`
(this skill renders what that one recovers).

## Complementary sources

- `writing-science` — the parent: OCAR, story structures, the funnel, topic/stress, and the
  detector kernel this skill re-reads. Load it alongside.
- `expert-prose-style` — the register floor (prose over bullets, no unrequested condensing);
  teaching-narrative assumes it and adds the transfer arc.
- `design-rationale` — the content engine when the thing being taught is recovered rationale.
- `machine-md` — if the teaching doc's reader is an LLM, not a human.
