---
name: writing-science
description: Diagnose and revise science prose using Joshua Schimel's Writing Science framework (OCAR, story structures, the funnel, topic/stress positions, given-to-new flow) paired with a mechanical detector script that flags draft-level tells (nominalizations, passive voice, weak/fuzzy verbs, empty amplifiers, buried verbs, weak gap framing, undermining resolutions, and more). Load when reviewing or writing a manuscript, abstract, proposal, cover letter, or any scientific document, or when the user asks whether prose is clear, strong, sticky, or flabby, or when about to return prose you drafted yourself — the nine-tic self-scan. The script measures the draft's actual shape before any judgment; the frameworks handle the structure the script cannot see.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-29). writing-tools bundle copy of the CCRT writing-science skill, DETECTOR LAYER REFRESHED to post-P2c (this snapshot): the bundled writing_detectors.py + the detector-doc sections (### New & augmented detectors, ## The detector script) are the post-P2c engine of record — flourish SPLIT (flourish_triad/epigram/metaphor/apologetic_contrast), novelty_claims, noun_trains stacked-hyphen arm, term_drift + def-distance, pseudo_explanation, em_dashes, absolute_quantifiers B5 arms, gradient tune, compare CLI — adversarially verified TRUSTWORTHY-WITH-CORRECTIONS (dev/benchmark/P2v_review.md; two LOW candidate-only residues documented). PRESERVED from S11: the judgment-tier "Self-scan additions" section (user-31 pseudo-explanation, user-32 premature definition, the vehicle test, the closing audit, the compliance-prose discipline, class-sweep, the residual-named checks) — every addition carries a verification status. Prior provenance: ported from the Claude Science writing-science skill (reverse port); kernel.py re-shipped as the bundled writing_detectors.py CLI (functions verbatim; auto-load rewritten to explicit `python3 <skill_dir>/writing_detectors.py scan` invocation); cross-refs remapped to CC agents.


# writing-science

BUNDLED_TOOL: `writing_detectors.py` (this dir). Pure python3 stdlib (macOS 3.9.6 floor); Claude Code has no auto-load — run it explicitly as a script.
INVOKE: `python3 <skill_dir>/writing_detectors.py scan [--json] [--top N] <draft.txt|->` — `scan` prints the human tell report; `--json` emits the structured `{counts, profile, hits}` dict (draft arg `-` or omitted reads stdin). A second mode, `writing_detectors.py compare BEFORE AFTER`, surfaces hedges / field-standard terms a de-jargon pass may have wrongly stripped (BWT-007 comparison, cautious tier).

Operationalizes Joshua Schimel's *Writing Science: How to Write Papers That Get Cited and Proposals That Get Funded* (2012). Two halves, different jobs:

1. **The frameworks** (below) — structure-level craft that needs JUDGMENT (story exists? OCAR complete? opening funnels to the challenge? right word in the stress position?). No regex decides these; they are what your reading is for.
2. **The detector script** (`writing_detectors.py`, bundled in this skill dir) — sentence/word-level tells a script surfaces reliably: nominalization+light-verb, agentless passive, fuzzy verbs, empty amplifiers, buried main verbs, "little is known" gap framing, "more research is needed" endings, undefined acronyms, profile stats (sentence-length distribution, verb/word ratio, nominalization & noun-train density).

The split is load-bearing: an LLM agent reliably FORGETS the mechanical tells and reliably HALLUCINATES having checked them ("the prose is clean and direct") ⇒ the mechanical layer is a script you RUN, not a habit you recall. The script cannot judge whether a paragraph earns its place ⇒ that stays with you. **Run the script to see the draft's real shape; use the frameworks to decide what the shape means.**

## The first move, always: measure before you judge

WHEN about to characterize a draft in any way — call it "clear," "dense," "strong," "wordy" — ⇒ run the script and read the profile FIRST. Stating a verdict about text without measuring it is the single tell this skill exists to prevent (the ported "theory-before-measurement" failure). The detectors are candidate-flaggers: they surface suspects reliably; **you** decide whether each flagged item is actually a defect here, for this reader. Nothing in the script auto-edits.

```bash
# writing_detectors.py is bundled in this skill dir; run it explicitly (CC has no auto-load).
python3 <skill_dir>/writing_detectors.py scan draft.txt          # triage: profile + tell tally + top hits per tell
python3 <skill_dir>/writing_detectors.py scan --json draft.txt   # structured: JSON {counts, profile, hits}
# draft.txt may be "-" or omitted to read the draft from stdin
```

In the `scan --json` output, read `profile` first (sentence-length distribution, verb/word
ratio ~0.15 is comfortable, nominalization and noun-train density per 100 words,
em-dash/semicolon counts). Then triage `counts`, and only then open the specific
`hits[name]` lists to disposition individual sentences. (The human `scan` report prints the
same profile → tally → top-hits order for reading by eye.) A count of 90 "repeated_words" is
a place to look, not 90 edits to make.

## Work top-down: the scale-descent

Schimel builds and edits at descending scales — **story and story structure → paragraphs →
sentences → words** (p.6) — with the justification: *"If you can't deal with the big issues,
the small ones don't matter very much"* (p.6). This fixes your order of operations. Do not
polish a sentence inside a paragraph that should be cut. Establish the structure first, then
descend. When making an editing pass, Schimel's named sequence is **SCFL** (ch.17, p.~174):
**S**tructure (get the story's structure into shape), **C**larity (make ideas clear and
concrete), **F**low (link each thought to the next), **L**anguage (make it sound good). The
script's detectors live at the Clarity/Flow/Language tiers; Structure is yours alone.

## Framework 1 — OCAR, at every scale

The four story elements *"echo throughout this book, whether we are talking about whole
papers, sections, paragraphs, or even individual sentences"* (p.27):

- **O — Opening:** who/what the story is about — the characters, the setting, and the
  **larger problem** being addressed.
- **C — Challenge:** the specific question or hypothesis the characters must resolve.
- **A — Action:** what was done and found — the story's development.
- **R — Resolution:** the answer to the challenge, and what it means.

Check OCAR for completeness at the document level first (is there an opening that frames a
problem? a stated challenge? a resolution that answers it?), then recursively in each
section and paragraph. A missing element is a structural defect no sentence edit will fix.
OCAR maps onto IMRaD but is not identical to it; the mapping is a guide, not a straitjacket.

## Framework 2 — the four story structures, ranked by audience patience

Which structure to use *"depends on the audience's patience"* — how long readers will wait
for the point (p.27):

- **OCAR** — slowest, elements in sequence, challenge at the end of the introduction,
  conclusion at the end. For **patient** audiences (specialist-journal readers).
- **LDR** (Lead–Development–Resolution) — the point comes sooner; for magazine-style
  readers who want the gist early.
- **LD** (Lead–Development) — the lead carries the main result up front.
- **ABDCE** (Action, Background, Development, Climax, Ending) — fastest; front-loads the
  story most, for the least patient audiences.

Match the structure to the venue. A specialist paper can unfold as OCAR; a generalist
journal, a proposal summary, or a press release usually needs the result earlier (LDR/LD).
A challenge that appears only late in an impatient venue is a structure–venue mismatch.

## Framework 3 — the funnel (connecting Opening to Challenge)

The introduction's three load-bearing moves are the Opening (ch.5), the **Funnel** that
connects the opening to the challenge (ch.6), and the Challenge itself (ch.7). The funnel
narrows from the broad problem to the specific question without a gap or a cliff. For a
**broad** audience, use the **two-step opening**: open with an issue that engages the target
readers, then modulate to your narrower focus — *"It does take two steps, and it must be
quick — if you take more than two steps, you will stumble"* (p.44). The script flags the
**bizzwidget opening** (`bizzwidget_opening`) — a method, tool, or acronym introduced in the
first few sentences before any problem is posed — and, separately, objectives stated as
activities rather than a question (`objectives_not_question`).

## Framework 4 — topic and stress positions (the sentence-level lever)

Every sentence has two power positions, terminology Schimel credits to Joseph Williams'
*Style: Toward Clarity and Grace*:

- **Topic position (the opening):** *"Whatever you put at the beginning of a sentence,
  readers interpret as the topic"* (p.113). It should hold **old/familiar** information — a
  schema or character the reader already has. New information first confuses, because
  *"you're giving them new information but suggesting it's old."*
- **Stress position (the end of the main clause):** *"Use the power of the stress by putting
  key words there — the main message and new ideas or terms"* (p.113). The end is where the
  reader's attention lands.

This drives **given-to-new flow**: open a sentence with something established, close it on
the new idea, and let that new idea become the topic of the next sentence. Flow is what you
get when the stress of one unit becomes the topic of the next, across sentences and across
paragraphs. The script's `trailing_qualifier`, `citation_position`, and `buried_verbs` tells
all point at stress/topic misuse; disposition them by asking *what should this sentence be
about, and what should it leave the reader holding?*

## Framework 5 — transparency over performance (why "cheap cleverness" is a defect)

Both Schimel and Strunk & White run on one governing principle: **prose is a transparent
medium for a structure of thought, and anything the reader notices AS prose is friction
between them and the thought.** Schimel states it as story (reconstruct the argument with
least effort); Strunk states it as economy ("omit needless words"). They are the same claim
at two scales — a sentence is right when it spends the reader's attention only on content,
never on the writer.

This is why a **rhetorical flourish** is a defect, not a flourish: a construction chosen for
effect — a clever triplet of props, a not-X-but-Y antithesis, a showy metaphor, an over-
emphatic "the very X" — makes the reader admire the *sentence* instead of absorbing the
*point*. The writer becomes visible; the glass smudges. It is the same failure as a
nominalization or an empty amplifier, one scale up: **rhetorical** excess rather than lexical
excess. That is exactly why the older word-count detectors missed it — the excess a flourish
adds is not extra words, it is extra performance.

The boundary that makes this a JUDGMENT, not a rule: elaboration is licensed by content
delivered, not by effect achieved. A parallel triplet that enumerates three real caveats
earns its length; a metaphor kept once to close a Discussion for ring composition is load-
bearing. The identical construction can be a flourish in one place and substantive in
another. So the flourish detectors (`flourish_triad`, `flourish_epigram`, `flourish_metaphor`,
`apologetic_contrast`) are **candidate-flaggers**: they
surface the suspect and name the subclass; **you** decide whether it does real work *here*.
The one hard rule when you cut a flourish: **preserve the meaning** — an over-correction that
strips "the organisms we can see" into a claim the methods contradict is a worse defect than
the flourish was.

## Self-scan checklist — the nine authored-prose tics (bad-writing-tics register)

Framework 5 explains why the first of these is a defect; all nine share that logic — a
construction the reader notices AS prose is friction between them and the thought. This is
the self-scan the always-on rule (`rules/prose-tics-self-scan.machine.md`) mandates: **run
the detectors on your OWN draft, then work this checklist.** These nine tics (BWT-001..009)
were catalogued from Claude-authored science prose; each entry gives the **primary cue**
(what fires it), the **plain test**, and the **fix that preserves the exact claim**. Every
flag is a candidate you dispose — recast a real hit *without letting the plain version assert
more or less than the evidence supports.*

1. **cheap-cleverness / flourish (BWT-001)** — *cue:* a sentence whose structure the reader
   would notice on its own — a triplet of concrete nouns, a witty reversal, an
   attention-drawing metaphor — especially in a Results or Introduction sentence whose job is
   to state a finding or a gap. *test (effect-test):* does the vivid/witty construction
   deliver content the plain version would lose? If not, it is a flourish. *fix:* state the
   point plainly and let the content carry the interest; cut it, preserving the exact claim.
   (Rationale: Framework 5.)
2. **rule-of-threes / triadic-parallelism (BWT-002)** — *cue:* three (or more) consecutive
   clauses or sentences with the same opening word or grammatical shape — "does not… does
   not… does not", "No X. No Y. Just Z.", "It is… It is… It is". *test (cadence-vs-content):*
   if you hear a drumbeat, the reader hears performance. *fix:* vary sentence length and
   connective structure; if three items genuinely belong together, break the identical
   openings (change the verb, the connective, or split into two sentences) so the reader
   hears content, not cadence.
3. **abstruse / coined-notation (BWT-003)** — *cue:* coined notation, colons or bracketed
   tags used as private labels, or a run of three-plus stacked technical modifiers, in prose
   meant for a human reader rather than in a table or equation ("Tension:limb (a)",
   "larger-favored-low gradient"). *test (decode test):* could a domain reader who is NOT you
   parse this sentence left-to-right on first read? Stacked modifiers or coined symbols fail
   it. *fix:* write for a specific domain reader who does not share your working notation;
   spell out coined symbols and shorthand on first use or replace them with plain
   descriptions; unpack stacked modifiers into a sentence the reader can parse left to right;
   introduce any dense reference apparatus (symbol tables, item lists) at first mention, not
   after the reader already needed it. **[calibration pair with BWT-007 — see jargon-triage
   below.]**
4. **overclaim / overstatement (BWT-004)** — *cue:* absolute or superlative phrasing
   ("barely", "never", "always", "first to", "decoupled", "none") attached to a result whose
   design or sample cannot support the absolute; or a known fact framed as a doubtful
   assumption ("an artifact of assuming …?"). *test:* match every claim's strength to what
   the specific result or design supports. *fix:* prefer calibrated quantifiers ("few
   studies", "only a handful") to absolutes ("barely studied", "none"); when a design cannot
   separate two effects, report the limitation rather than the clean conclusion; state known
   facts as facts, not as improbable hypotheses. **Redirect:** you own only the *wording*;
   whether the design supports the absolute goes to the formal-argument-checker agent.
5. **code-metaphor / metaphor-leakage (BWT-005)** — *cue:* a computing or modeling term
   (foil, gate, branch, loop, cascade, pipeline, scaffold, collapse, "walk the … link by
   link") used figuratively in a sentence that is about ecology/biology/results rather than
   about actual code or model machinery. *test (real-object test):* is the sentence about
   ACTUAL code/model machinery (correct usage) or about the science (leakage)? Only the
   latter is the tic. *fix:* use only metaphors whose vehicle the reader shares; reserve
   code/model terms for describing real software or model objects; if the sentence is about
   science, restate the idea in the reader's own domain vocabulary.
6. **reading-mannerism / mannerism-recurrence (BWT-006)** — *cue:* the verb "reading" (or a
   similar figurative verb) applied to a physical gradient, axis, or spatial arrangement
   ("reading how organisms are distributed along that axis"); or any single distinctive
   construction that recurs across paragraphs or drafts. *test (favored-verb scan):* a
   favored figurative verb standing in for a plain one that names the actual operation.
   *fix:* use a plain verb — measure, map, describe how X varies with Y. **Recurrence rule:**
   when a mannerism is flagged, remove EVERY instance across the draft, not only the quoted
   one — a single-draft scan cannot catch cross-draft recurrence.
7. **over-de-jargon / jargon-over-correction (BWT-007)** — *cue:* a de-jargoning pass that
   flags field-standard terms or abbreviations, treating "unfamiliar to a general reader" as
   identical to "jargon" without checking the target venue. *test (jargon-triage):* classify
   the term before flagging it (below). *fix:* calibrate to the actual venue and target
   reader — a domain scientist, not a general audience — not to "unfamiliar to anyone".
   **[calibration pair with BWT-003.]**
8. **empty-amplifier / degree-word-filler (BWT-008)** — *cue:* an emphasis or degree word
   ("even", "sharply", "very", "significantly", "remarkably") that can be deleted without
   changing the sentence's factual content. *test (deletion test):* delete it — does the
   factual content change? *fix:* delete degree and emphasis words unless they add meaning
   the sentence would lose; let the fact, not the adverb, supply the force.
   **Against-expectation exception:** keep "even" ONLY for a genuine against-expectation
   surprise; do not reuse it once the surprise is spent ("even" is context-dependent — a
   lowest-severity candidate, not a blanket ban).
9. **false-antithesis / preemptive-apology (BWT-009)** — *cue:* an "X rather than Y" or "not
   X, but Y" construction, especially where X is one of the study's own deliberate choices
   (reads as apology) or where the antithesis adds cadence rather than a needed contrast.
   *test (positive-form test):* state the design choice as the positive decision it was; if a
   contrast is genuinely needed, make it once and plainly. *fix:* state a design choice as
   the positive decision it was, not as a concession against an alternative; do not apologize
   for purposeful choices. ("rather than" has a high legitimate rate — flag only where X is
   plausibly the study's own design choice; largely a judgment call.)

### Jargon-triage (BWT-007): classify before you flag

Before flagging a term as jargon in a de-jargoning pass, classify it into one of three —
this is the fix for BWT-007, and it is a reasoning step, not a draft-text scan:

- **Genuine jargon** a domain reader would not know ⇒ **define or replace** it. (e.g.
  "adonis2 p-value" — truly heavy jargon.)
- **A field-standard term** the target reader expects ⇒ **KEEP** it. (e.g. "Sørensen
  turnover" — a domain ecologist reads this fluently.)
- **An unexpanded abbreviation** ⇒ **spell it out on first use**, rather than removing it.
  (e.g. "gf", "disp.lim.", "β_sim" — the issue is abbreviation, not jargon.)

Calibrate to the actual venue and reader, not to "unfamiliar to anyone." **The target-reader
default is a DOMAIN SCIENTIST, not a programmer/modeler/general audience.** De-jargoning does
not mean stripping — adding a brief explanatory clause for readers with less expertise is
still fine.

### BWT-003 ↔ BWT-007 are a calibration pair

De-abstruse (BWT-003 — unpack coined notation and stacked modifiers) and do-not-over-strip
(BWT-007 — keep field-standard terms) pull in opposite directions and must be applied
**together**, keyed to the standing target-reader parameter. Applied without calibration, the
"make it legible" disposition over-shoots and strips legitimate terms — so the fix mis-fires.
The disposition must land in the middle: too-opaque (BWT-003) vs corrected-past-target
(BWT-007). De-abstruse WITHOUT over-stripping.

## Self-scan additions — validated in the two-round guide test (2026-07-29)

These items were catalogued and MEASURED in a two-stage detection loop on a real
machine-facing draft: stage 1 ran the in-development detectors + specialist passes, then the
standard-owner swept the same output for what stage 1 missed (stage 2). Across two rounds the
style-labeled residual fell **36 → 14** (−61%; read with the caveat that the flagged input
also shrank 67 → 21, so the style SHARE rose 54% → 67%). Each item below carries its
**verification status** in the ledger vocabulary — `measured-round-trend` (the class it guards
moved across the round trend), `attempted-untested` (proposed/adopted, no rate-drop measured
yet). Every item is a **candidate you dispose**, exactly like the nine tics; none auto-edits.

**Detector-layer note (2026-07-29, refresh LANDED):** the detector-documentation sections of
this skill and the bundled `writing_detectors.py` WERE upgraded to the post-P2c detector engine
by the bundle refresh pass — this snapshot carries the upgraded `writing_detectors.py` + its
detector-doc sections (`### New & augmented detectors`, `## The detector script`), and the
manifest records it. The items below are the JUDGMENT-TIER passes and named checks the
two-round test produced — they live in your reading pass and are independent of that swap.

### user-31 — pseudo-explanation (talk ABOUT explaining, in place of explaining)
*cue:* a sentence whose claim is about the act of explaining, learning, naming, understanding,
or about the document's own procedure — not about the subject matter. Three arms: **31a
generic-pedagogy** ("In learning a system, one steady name for each thing makes it easier to
follow"); **31b stage-direction** — prose narrating the reading act ("Strip it to one
sentence:", "Hold that thought —", "Read the cycle clockwise"); **31c provenance-aside** —
prose whose only claim is how the document or its materials came to be, addressed to the one
reader who already knows ("It is your own sketch of the workflow"). *test (the
swap-the-subject test):* swap the subject matter out — "In learning a system, one steady name
for each thing makes it easier to follow" is equally true of a tax code, a card game, or a
diesel engine ⇒ it says nothing about THIS subject ⇒ pseudo-explanation. Ornament's effect-test
does NOT apply: these sentences are flat, not vivid; they fail a CONTENT test — cut one and
nothing is lost, because nothing was there. *fix:* cut it, or replace it with the fact it was
standing in for. **Boundary (load-bearing):** reader-address is NOT the defect ("Now that you
understand how the system works, you can predict…" is fine); the defect is a content-free
GENERALIZATION about learning, or an aside about the document's own making. 31c is a
DOSE/placement call, not a fire-on-presence ban (a guide may legitimately open on the
author-reader frame) — judgment-tier by construction. *status:* `measured-round-trend` —
accepted round 1 (arms 31a/31b); arm 31c added round 2. 12 instances removed class-wide in
round 2 ⇒ the class fell **4 → 0** (the cleanest efficacy signal in the round table). A
remediation pass with no name for this defect manufactured a fresh instance while removing four
other tics — which is why it earned its own name. 31c itself: `attempted-untested` (one
instance, register-decision route).

### user-32 — premature definition (define at first USE, not first mention)
*cue:* a definition, gloss, or caveat introduced BEFORE the concept it governs is first used, so
the reader must hold an inert piece of vocabulary until it becomes relevant — or never does. An
ORDERING defect (the taxonomy's first exposition-order class), not an empty/ornamental/opaque
one. *test:* locate the term's first WORKING use; if the definition sits far ahead of it, it is
premature. (Measured on the guide: a "wave" definition at sentence 42, first working use at
sentence 78 — 36 sentences of inert vocabulary. A remediation pass wrote the larger instance: a
hedge placed at a definition site forward-referenced material 140 sentences later.) *fix:* the
terminology contract is **define at first USE** — move the definition to where the term is first
used; where the term is not used for many sentences after the mention, **delete the mention**
rather than defining it early. Cutting alone is NOT the fix (unlike user-31): the definition's
content is worth having, it is only misplaced. *status:* `attempted-untested` — accepted round
2, 2 instances (one remediation-manufactured); no rate-drop measured. Its detector form (a
distance query over the anchor-term registry) is a detector-layer item — see the note above.

### The VEHICLE TEST — semantic-breakage as a severity, not a class
*rule:* for every metaphor, appositive, or figure, **state the literal proposition it
asserts.** If that proposition is false, circular, or meaningless, flag
`severity=semantic-breakage` and recast it before anything else. (Worked: "tokens are the
currency of expense" → a currency measures expense, so the sentence asserts tokens are the
currency of currency → circular → semantic-breakage; the fix "the currency of memory and
labor" makes the proposition true.) *why a severity, not a class:* a class answers "what shape
is it?"; this answers "how bad is it?". No surface form separates the broken case from the sound
one ("the currency of memory" is fine, "of expense" is circular — identical grammar), so no
detector can carry it — judgment-tier BY CONSTRUCTION; do not commission a detector. *status:*
`measured-round-trend` — adopted round 1 (as the carrier when semantic-breakage was rejected as
a class). Round 2: the ornament family it guards (including both semantic-breakage instances)
fell **5 → 0** after the vehicle test ran over 8 figures and the standard-owner re-flagged none.

### The CLOSING AUDIT — a document closes once
*rule:* count the closing moves in the final section; **keep exactly one, subordinate or cut the
rest.** (Measured: a closing section ran 17 sentences with FIVE endings, none subordinated to
another — the measurable form of "it reads like you know you need to wrap up but aren't sure
how.") *why judgment-tier:* the first STRUCTURE-level item in the project; its extent is the
relation among the last paragraphs plus the coda, not a span — a fixture row cannot carry it, so
no detector. Note the mechanism: removing a stage-direction tic (user-31b) that was ALSO
subordinating the closers left the structure to be rebuilt, not merely deleted — re-express what
a removed construction was carrying, do not only delete it. *status:* `attempted-untested` —
adopted round 2, first structure-tier item, 1 instance; no subsequent round measured.

### The DIRECTIVE-SATISFACTION AUDIT + recast content-loss post-condition (the compliance-prose discipline)
The measured finding that drives these: **a remediation pass is itself a primary defect
source.** Round 1 measured 18 of 48 edits revising the reviser's OWN replacement text; round 2
measured 4 of 9 style-labeled sites as text written in the prior round specifically to satisfy a
directive. Text written to answer a comment arrives AFTER the checks ran, so it is exempt by
default — close that exemption. Four rules, each with its measured origin:
- **Re-audit newly-authored text as a fresh draft** — run the tic checklist over every sentence
  you write to satisfy a directive, not only over replacements of flagged text. *(origin: round
  2 — 4/9 flagged sites were directive-satisfying remediation text; round 3's audit
  self-reported catching 4 such defects pre-ship.)*
- **Recast content-loss post-condition** — after removing a tic, verify EMPHASIS, AGENCY,
  CONNECTIVE and COMPLETENESS survived, then re-read the replacement against the whole
  checklist. *(origin: round 1 — breaking a balanced parade into short declaratives cost
  emphasis, completeness, cohesion and agency; a de-metaphoring deleted the emphasis with the
  metaphor.)*
- **After replacing an abstraction, re-check the claim's STRENGTH; after cutting a
  self-importance marker, re-check the host sentence still carries information.** *(origin: round
  2 — compressing a nominal chain produced an unhedged absolute the abstraction had been
  carrying the hedge for; cutting "subtle and worth understanding" left a sentence announcing
  that a reason exists without giving it.)*
- **Close a fix against the exact object the instruction named.** *(origin: round 2 — a
  directive naming one specific figure was satisfied in a different figure and in prose, the
  named figure left untouched, and the directive returned verbatim the next round.)*
*status:* `attempted-untested` as a controlled efficacy check (round 3's self-report of 4
catches is cited but is not an independent measurement); the measured ORIGINS above are
round-1/round-2 counts, cited.

### REMOVE-EVERY-INSTANCE + sweep the class, not the instance
*rule:* when a defect CLASS is flagged, remove EVERY instance of that class across the whole
draft — not only the quoted one. A single-instance fix is not a class fix, and the two are
indistinguishable in a change table. (This generalizes the nine-tic checklist's recurrence rule,
item 6, from mannerisms to every class.) *status:* `measured-round-trend` — round 2 supplied a
natural experiment: every class swept draft-wide (elegant variation, pseudo-explanation,
self-importance, em-dash piling) fell to **0**; the one class fixed only at its flagged instance
(contrastive definition) came back, with ≥8 untouched siblings standing. The sharpest measured
discipline in the two rounds.

### Named checks the residual analysis identified (detector-layer — see the note above)
The two-round residual named a family of detector-shape checks: **term_drift /
anchor-term registry** (the round-1 mass — five competing names for one unit, closes user-26
elegant variation); **definition-before-use distance arm** (user-32); **absolute_resultative_verb**
(unhedged completeness verbs — avoids / prevents / eliminates / ensures — outside the
`absolute_quantifiers` lexicon); **negative_definition** (the elliptical X-not-Y form) plus a
disposition fix; **nominal_subject_predicate + agentless_gerund** (abstraction-as-subject).
POST-REFRESH STATUS (this snapshot): the post-P2c engine BUILT three of these — `term_drift`
(near-synonym drift over a caller-supplied anchor list or a workflow-term default gated on
workflow context, lemma-folded so a term's singular/plural is not counted as drift), its
definition-before-use distance arm (premature-definition on declared **bold** terms defined >10
sentences before first use), and the resultative-verb absolute (now an `absolute_quantifiers`
arm — avoids / eliminates / guarantees / never-fails in an unhedged claim); **negative_definition**
(partly surfaced by `flourish_epigram`'s X-not-Y antithesis arm; no dedicated detector) and
**nominal_subject_predicate + agentless_gerund** remain UNBUILT and stay judgment-tier for now.
Each fire is a candidate you dispose.

### New & augmented detectors (names + false-positive notes only)

The register recommends these detector changes; the detector **code is owned separately**
(this skill documents the names + guards only). Every detector is a **candidate-flagger** —
it surfaces a suspect for you to judge, and never edits. (Function names below; the hit-key
in `scan --json` output drops the `find_` prefix.)

- **`rhetorical_flourish` was SPLIT (P2) into four hit-keys** so the triage counts each cadence
  separately: `flourish_triad`, `flourish_epigram`, `flourish_metaphor`, `apologetic_contrast`.
- `flourish_triad` **(BWT-001/002, rule-of-threes)** — the article-triplet "a X, a Y, or a Z";
  the **asyndetic tricolon** (an em-dash/paren-bounded 3-item list with NO conjunction — "— planner,
  subagents, durable files —"); the clause/sentence **anaphora** ("does not… does not… does not");
  and the **reduplication** "X by X" ("taxon by taxon"). *FP guards:* anaphora needs ≥3 identical
  openers; the asyndetic arm is suppressed when the list carries "and"/"or" (an ordinary list).
- `flourish_epigram` **(BWT-001, balanced/contrastive)** — the **balanced parallel** epigram
  ("Convergence in space, divergence in time"); the antithesis "X, not Y" / "not X but Y"; the
  reversed closer ("a feature, not monotony"); the "it's not X, it's Y" comma-antithesis. Reversed
  "X, not Y" is LOW severity (guarded against "not a/the/only …").
- `flourish_metaphor` **(BWT-001)** — the showy metaphor vehicle ("the thread from which both …
  hang") and the "the very X" over-emphasis.
- `apologetic_contrast` **(BWT-009)** — "X rather than Y" / "not X but Y" framing a design choice
  as a concession. *FP guard:* GATED on a design-choice cue (we/our/makes/treat/use/define/control/
  design/variable…); a **cue-less** "rather than" (high legitimate rate) is deliberately NOT flagged.
- `find_noun_trains` **+ `stacked-hyphen-compound` kind (P2 augment, BWT-003)** — a 2-part hyphen
  compound coinage in a modifier stack ("gradient-invariant host baseline", "microclimate-correlated
  gradient"). Operates on the hyphen token directly (min_run 4→3 cannot reach it — the `-ed` rule
  excludes "…-correlated"). *FP guards:* both parts ≥7 letters, first part not an adverb (`-ly`),
  neither part a common compound head/tail (dependent/standardized/…), and it must sit in a stack.
- `absolute_quantifiers` **(BWT-004, LOW severity)** — the strength lexicon {barely, never, always,
  decoupled, none} **+ P2 arms**: near-X absolutes ("near-pure"); a GUARDED "left untouched"
  (suppressed when a sample/methods noun precedes it — "plots were left untouched"); and B5
  **resultative/verb-form absolutes** ("avoids", "eliminates", "guarantees", "never fails") in an
  UNHEDGED claim. Evidence-fit stays redirected to the formal-argument-checker.
- `novelty_claims` **(P2 SPLIT out of BWT-004)** — a novelty/priority boast by PATTERN ("to (the
  best of) our knowledge", "the first STUDY/REPORT/… to", "for the first time", "the first to VERB"),
  not a "first study to" phrase-match. LOW severity; whether it is genuinely first is redirected.
- `code_metaphor_leakage` **(BWT-005)** — a bare code word ({foil, gate, branch, loop, cascade,
  pipeline, scaffold, collapse}) flagged ONLY with formal-register evidence: a modeling/inference cue
  (gradient, coefficient, …, theorem) OR a formal labelled identifier ([A-Z]+1-3 digits, e.g. G7);
  the `walk … link/path` idiom fires independently. **P2 GRADIENT TUNE:** when the ONLY cue matched is
  the ambiguous ecology word "gradient(s)" and there is no label, a code word must be STRONG
  ({foil, scaffold, pipeline}) to fire — so "trophic cascade along the gradient" (weak word) stays
  quiet while "foil … gradient" (6.2) and the labelled G7 sentence (13.3) still fire. **P2 VEHICLE
  WIDENING (B4):** an organic/mechanical `vehicle-metaphor` arm ({heartbeat, trap door, release/
  safety/pressure valve, lifeblood, nerve center}) runs independent of the machinery gate, suppressed
  by a literal marker (cardiac/hinge/boiler/…); the note carries the VEHICLE TEST (state the literal
  proposition; recast if false/circular/empty).
- `figurative_mannerism` **(BWT-006)** — figurative "reading" + a spatial anchor. **P2:** the anchor
  group now also carries the VERB forms distribute/organize/arrange so "reading how organisms are
  distributed" fires (recovers atom 14.2 only; the interpretation-noun "reading" cases stay
  judgment-tier). Pairs with the remove-every-instance rule.
- `find_empty_amplifiers` **+ "sharply" / "even" (augment, BWT-008)** — add "sharply"; add "even" as
  the LOWEST-severity candidate. *FP guard:* "even" is context-dependent — surfaces for triage, never
  a blanket ban.
- **PART B measured checks (P2+):**
  - `term_drift` **(B1, user-26 + user-32)** — near-synonym DRIFT (≥2 competing names for one
    referent, from a caller-supplied list or a built-in workflow-term default GATED on workflow
    context) with a per-1000-word rate, AND definition-to-first-use DISTANCE for declared **bold**
    terms (premature-definition flagged when a term is defined >10 sentences before first use).
  - `pseudo_explanation` **(B2, user-31)** — two closed near-zero-FP arms: `stage-direction` (a
    sentence-initial imperative narrating the reading act — "Strip it to one sentence:", "Hold that
    thought") and `generic-pedagogy` (a content-free generalization about learning — "In learning a
    system…", "knowing X is part of understanding Y"). BOUNDARY: reader-address is NOT the defect.
  - `em_dashes` **(B3, user-9)** — promoted from profile-only to a thresholded detector with a hit
    list: a sentence with ≥2 em-dashes, plus the document em-dash rate per 1000 words.
- **BWT-007 has NO per-draft detector** — it is a reasoning tic in the de-jargon pass. **P2 adds a
  COMPARISON mode** `writing_detectors.py compare BEFORE AFTER` that surfaces hedges and
  field-standard-looking terms a BEFORE→AFTER de-jargon pass may have wrongly stripped (cautious
  tier, candidate-only); its live carrier is still the jargon-triage procedure above.

## The detector script — what it flags and how to read it

Every detector returns a list of hits; each hit carries the `sentence_idx`, the matched
text, the sentence, and a `note` with the fix. They fall in two tiers:

**High-precision flags (act on the specific hits):** `nominalizations` (light-verb +
nominalization, e.g. "perform an analysis" → "analyze"), `passive` (agentless passives are
the strongest recast candidates), `weak_verbs` (Schimel Table 14.1 fuzzy verbs),
`empty_amplifiers` (Table 16.1 — "very," "rather," "significantly"), `hype`,
`weak_gap_framing` ("little is known"), `undermining_resolution` ("more research is
needed"), `objectives_not_question`, `significance_without_effect`, `metadiscourse`
("we found that…"), `undefined_acronyms`, `trailing_qualifier`, `citation_position`.

**Rhetorical & structural flags (from the Schimel + Strunk & White mining):** the flourish split
`flourish_triad` (article/asyndetic triplet, anaphora, "X by X" reduplication), `flourish_epigram`
(balanced parallel, "X, not Y" antithesis, "it's not X, it's Y"), `flourish_metaphor` (showy
metaphor, "the very X"), and `apologetic_contrast` ("rather than" framing a design choice, cue-gated)
— all cheap cleverness, see Framework 5; `em_dashes` (≥2 em-dashes in a sentence — the aside pile-up,
now its own thresholded detector), `pseudo_explanation` (stage direction / generic-pedagogy claim),
`expletive_opener` ("There is/are … that," "It is … that" delaying the real subject —
promote it to the topic position), `naked_this` (a sentence-initial "This/These" + verb with
no noun attached — attach the noun for cohesion, Schimel ch.13), `not_positive_form`
(negations that read crisper stated positively — S&W Rule 15), `giant_paragraph` (a
>180-word wall, or a lone mid-body single-sentence paragraph that skips its own arc).

**Diction/economy flags (word scale):** `fancy_words` (Latinate-for-Anglo-Saxon: "utilize"
→ "use," "ascertain" → "find out"; Schimel ch.15, S&W Part V — a candidate, since some fields
fix "methodology"/"utilize" as jargon), `wordy_phrases` (fixed multi-word padding with a
one-word swap: "the fact that," "owing to the fact that"; S&W Rule 17), `misused_words`
(commonly-misused expressions beyond `confusables`: "comprised of," "center around," verbal
"impact," "data is"; S&W Part IV — candidates), `pseudo_suffix` ("-wise"/"-oriented"
coinages, with an established-term whitelist so `pairwise`/`stepwise`/`model-based` stay
clean), `scare_quotes` (a short quoted word used to apologize for a word choice — exempts
defined terms and identifiers/gene names).

**Density/background scans (read as a rate, then zoom — do not work the global list):**
`noun_trains` (flag list restricted to long ≥4-noun runs; `profile.noun_train_density`
reports 3+-noun runs per 100 words), `profile.nominalization_density` (per 100 words;
>~4 is noun-heavy), `prep_phrase_compounds`, `repeated_words`, `buried_verbs`. These over-
fire by design on long or technical prose; their value is the density signal and the
worst offenders, not an exhaustive fix list.

Detectors marked `approximate=True` (noun trains, buried verbs, verb ratio, the flourish split (`flourish_triad`/`flourish_epigram`/`flourish_metaphor`/`apologetic_contrast`), `code_metaphor_leakage`, `figurative_mannerism`, `pseudo_explanation`, `term_drift`, `misused_words`, `naked_this`, `pseudo_suffix`, `scare_quotes`) use POS-free
heuristics — treat them as directional candidates the reader disposes. The script strips markdown scaffolding (code
fences, mermaid blocks, tables, heading markers, link URLs) before analysis so it sees the
prose stream, not the formatting.

## Diagnostic stance

Be diagnostic, not merely corrective. When you flag something: (1) **name the level** it
fails at (structure / paragraph / sentence / word), (2) **show the revision**, and (3)
**state what changed and why** in Schimel's terms (e.g., "moved the result into the stress
position," "promoted the buried verb," "the challenge was missing from the funnel"). Cite
the book concept accurately and by page where you can; invent no rules. When the script and
your reading disagree, your reading wins — but say so, and say why the flag was a false
positive, because that is how the lexicons get better.

## Scope

This skill is prose craft. Argument validity and logical structure belong to the relevant domain reviewer; formal or quantitative claims to the formal-argument-checker agent;
machine-facing document/prompt design to the llm-doc-architect agent. The reader you are writing
for is a human.

## Complementary sources

- Joseph M. Williams, *Style: Toward Clarity and Grace* — the topic/stress and given-to-new
  machinery in depth.
- George Gopen & Judith Swan, "The Science of Scientific Writing" (*American Scientist*,
  1990) — the reader-expectation account of the same positional principles.
