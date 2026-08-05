---
name: machine-md
description: Invoke WHEN writing or editing any doc whose primary reader is an LLM — *.machine.md, .claude/ files (CLAUDE.md, rules, agents, skills, settings), auto-memories, hand-offs. Applies LLM-writing best-practices — positive trigger-conditioned framing, output-detectable triggers, brief concrete examples, terse machine style, atom-preservation. Pair with the machine-doc-reviewer agent for a review pass.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.

# machine-md — write docs an LLM will ACT on

## When to invoke
WHEN the doc's PRIMARY reader is Claude/an LLM ⇒ apply these: `*.machine.md`, any `.claude/` file (CLAUDE.md at every level, rules/*, agents/*, skills/*, settings), auto-memories, hand-offs. (Reader = human — reports, onboarding, papers — ⇒ write HUMAN prose instead; classify per `doc-style.machine.md`.)

## Practices (apply while authoring; this file self-demonstrates them)

### 1. State the ACTION + its TRIGGER, not the prohibition
An LLM follows a positive directive bound to a trigger better than a "NEVER". Convert `NEVER X` → `WHEN <trigger> ⇒ DO <right action>`. Reserve a bare "ALWAYS" for the genuinely unconditional; most rules are trigger-conditioned.
- `NEVER state a driver level from assumption` → `WHEN about to state a driver level (SW/PAR/wind/VPD/θ/ψ) ⇒ read it from data + cite`.
- `don't oversubscribe cores` → `WHEN launching runs ⇒ keep total active within core headroom`.
- Keep a short negative clause ONLY where a hard boundary is the point (`OFF == baseline, bit-identical`).

### 2. Make the trigger OUTPUT-DETECTABLE
A rule fires only if its trigger is observable in the moment — a word about to be typed, a tool about to be called, a number not in hand — not a vague exhortation ("think structurally", which never fires).
- `WHEN about to full-run→CSV to see a value ⇒ probe instead`.
- `WHEN writing a causal verb (because/due to) ⇒ cite an observation or tag "(guessing)"`.

### 3. One brief concrete example per rule
A one-clause example binds the rule to a case faster than any abstraction. Add a few; keep each to a clause, not a paragraph.

### 4. Lead with the load-bearing atom
Put the most important rule/fact FIRST — early tokens carry more weight. ONE primary reader per doc; dual-audience ⇒ split.

### 5. Terse, parseable, atomic (reader = Claude)
Write rule/fact atoms, each line standing alone; symbols/abbrev welcome (⇒ ≤ ∥ ⊂); drop narrative connective tissue. (Per `doc-style.machine.md` MACHINE.rules.)

### 6. Preserve atoms across an edit/convert
WHEN changing framing or style ⇒ keep EVERY fact / citation / file:line / number exactly; add, drop, alter NONE. Only the packaging changes; verify the atom set is identical after.

### 7. Treat `description:` as load-bearing (memories + skills)
It is matched for recall/auto-invocation ⇒ make it a specific, positive, trigger-phrased sentence naming the situation it fires in, not a vague summary. This is the single highest-leverage line in a skill: the body only runs if the description triggered.

## Companion
WHEN a machine doc is important or was bulk-reframed ⇒ delegate a review pass to the `machine-doc-reviewer` agent (audits against these practices).

## Refs
`doc-style.machine.md` (machine vs human; ask-if-unspecified; NAMING) · `refactor-invariants.machine.md` (the output-detectable-TELL pattern, §2 exemplar) · `verification-principles.md` (cite-or-hedge).
