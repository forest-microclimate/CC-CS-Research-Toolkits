# DOC_STYLE_MACHINE_VS_HUMAN.machine.md
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Guide: writing MACHINE-reading-optimized vs HUMAN-reading-optimized docs, + translating between them.
# (Self-demonstrating: this file is machine-optimized.)

DEF.machine_optimized: doc whose PRIMARY reader is an LLM (Claude Code) that will PARSE + ACT on it.
DEF.human_optimized:   doc whose PRIMARY reader is a person who will READ to UNDERSTAND / LEARN / DECIDE.
PRINCIPLE: optimize for the READER's parse path; LLM-parse != human-parse. Pick ONE primary reader per doc.

MACHINE.optimize_for = {fast unambiguous parse, high info-density, direct retrieval + action}.
MACHINE.rules:
  - STRUCTURE: key:value, bullet lists, tables, IF→THEN, labeled blocks (RULE.x / PROC.y) as anchors for reference.
  - FRONT-LOAD: rule / fact / answer FIRST; go straight to it, skipping buildup / narrative arc / conclusion paragraph.
  - TERSE: drop articles, transitions, hedges, rhetoric ("importantly", "note that", "as we saw above").
  - IMPERATIVE: directives ("do X", "X => Y"); not discussion ("one might consider X").
  - SYMBOLS: => | & {} for relations; shorthand OK if unambiguous + defined-on-first-use.
  - DEDUPE: state once; cross-reference by anchor rather than restating.
  - INLINE values: concrete numbers / paths / IDs in place rather than "see above".
  - SELF-CONTAINED: each block standalone; write each to read on its own, assuming zero surrounding prose context.
  - WHY-as-tag: "X (WHY: Y)", not a motivation paragraph.
MACHINE.smell (leaking human style) = paragraphs, topic sentences, examples-for-intuition, repetition-for-emphasis, motivation-before-rule.

HUMAN.optimize_for = {comprehension, retention, motivation, onboarding, persuasion}.
HUMAN.rules:
  - PROSE: paragraphs, narrative flow, transitions.
  - MOTIVATE FIRST: the "why" / context before the detail; progressive disclosure (build up).
  - EXAMPLES + analogies for intuition.
  - REDUNDANCY: restate key points >1 way for emphasis / retention.
  - SIGNPOST: "in short", "importantly", orienting headers.
  - SOFTEN: give rationale + caveats, not bare imperatives.
HUMAN.smell (leaking machine style) = wall of bullets/abbrevs, no motivation, no examples, reads like a config file.

CHOOSE:
  - MACHINE IF reader = Claude Code acting on it: rules, protocols, hand-offs, plans-for-resume, configs, agent prompts, checklists-to-execute.
  - HUMAN IF reader = person learning/deciding: explanations, rationale, onboarding, papers, human-facing READMEs.
  - DUAL-AUDIENCE => write 2 docs (or 1 machine doc + a short human "summary" section); commit each fully to its own style rather than half-doing both in one.

TRANSLATE.human_to_machine:
  1. EXTRACT atoms — each distinct rule / fact / step.
  2. DROP transitions, rhetoric, repetition, motivation-prose.
  3. FRONT-LOAD each atom; label/anchor it.
  4. CONVERT "should X because Y" => "X (WHY: Y)"; prose-conditionals => IF→THEN; prose-lists => bullets.
  5. INLINE concrete values; dedupe.
  6. VERIFY: every atom from the source is preserved; nothing new added.

TRANSLATE.machine_to_human:
  1. GROUP atoms into themes; ORDER as a narrative (motivate → rule → example → caveat).
  2. EXPAND shorthand/symbols to words; add transitions.
  3. ADD motivation/context up front + examples for the non-obvious.
  4. SOFTEN imperatives into rationale; add emphasis/repetition for key points.
  5. VERIFY: a first-time human reader can follow from the doc alone.

INVARIANT (both directions): preserve the ATOMS exactly — no rule added, dropped, or altered. Only the PACKAGING changes.

NOTE.default: DEFAULT = machine-optimized (`.machine.md`) for anything Claude Code reads + acts on (rules, hand-offs, protocols, plans). Use human prose ONLY for docs the user reads directly. Naming convention: `*.machine.md`.
