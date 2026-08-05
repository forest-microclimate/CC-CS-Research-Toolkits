---
name: machine-md
description: Invoke WHEN writing or editing any text whose primary reader is an LLM — a skill's SKILL.md and its description field, an agent profile's system_prompt, durable memory rows, delegation task briefs, or a handoff brief. Applies LLM-writing best-practices — positive trigger-conditioned framing, output-detectable triggers, brief concrete examples, terse machine style, atom-preservation. Pair with skill-creator (skill anatomy/eval) and the LLM_DOC_ARCHITECT profile for a review pass.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# machine-md — write text an LLM will ACT on

## When to invoke
WHEN the text's PRIMARY reader is Claude/an LLM ⇒ apply these. In Claude Science that means: a skill's `SKILL.md` and especially its `description:` (the recall/auto-invocation trigger), an agent profile's `system_prompt`, durable memory rows (`write_memory`), a `host.delegate` task brief, or a handoff brief. (Reader = human — reports, papers, onboarding prose — ⇒ write HUMAN prose instead; use `writing-science` / `expert-prose-style`.)

## Practices (apply while authoring; this file self-demonstrates them)

### 1. State the ACTION + its TRIGGER, not the prohibition
An LLM follows a positive directive bound to a trigger better than a "NEVER". Convert `NEVER X` → `WHEN <trigger> ⇒ DO <right action>`. Reserve a bare "ALWAYS" for the genuinely unconditional; most rules are trigger-conditioned.
- `NEVER state a value from assumption` → `WHEN about to state a data value ⇒ read it from the source + cite`.
- `don't oversubscribe cores` → `WHEN launching runs ⇒ keep total active within core headroom`.
- Keep a short negative clause ONLY where a hard boundary is the point (`plt.savefig breaks lineage — use fig.savefig`).

### 2. Make the trigger OUTPUT-DETECTABLE
A rule fires only if its trigger is observable in the moment — a word about to be typed, a tool about to be called, a number not in hand — not a vague exhortation ("think structurally", which never fires).
- `WHEN about to full-run to see a value ⇒ probe/compute the smallest slice instead`.
- `WHEN writing a causal verb (because/due to) ⇒ cite an observation or tag "(guessing)"`.

### 3. One brief concrete example per rule
A one-clause example binds the rule to a case faster than any abstraction. Add a few; keep each to a clause, not a paragraph.

### 4. Lead with the load-bearing atom
Put the most important rule/fact FIRST — early tokens carry more weight. ONE primary reader per doc; dual-audience ⇒ split.

### 5. Terse, parseable, atomic (reader = Claude)
Write rule/fact atoms, each line standing alone; symbols/abbrev welcome (⇒ ≤ ∥ ⊂); drop narrative connective tissue.

### 6. Preserve atoms across an edit/convert
WHEN changing framing or style ⇒ keep EVERY fact / citation / path / number exactly; add, drop, alter NONE. Only the packaging changes; verify the atom set is identical after.

### 7. Treat `description:` (and memory `text`) as load-bearing
A skill's `description:` is what the harness matches to decide auto-invocation; a memory row's `text` is what gets recalled. Make each a specific, positive, trigger-phrased sentence naming the situation it fires in — not a vague summary. This is the single highest-leverage line in a skill: the body only runs if the description triggered.

## Science-specific notes
- **Skill `description` optimization** is its own craft (trigger precision, false-fire avoidance) ⇒ load `skill-creator` for the eval/optimization loop; this skill is the writing discipline, that skill is the measurement.
- **Kernel sidecars** (`kernel.py`/`kernel.R`) are code, not machine prose — the writing rules apply to the SKILL.md that explains them, not the function bodies.
- **Memory hygiene:** a durable row is machine text a FUTURE session reads cold — apply rule 7 (trigger-phrased, atomic) so auto-recall surfaces it at the right moment.

## Companion
WHEN a skill/profile/memory set is important or was bulk-reframed ⇒ delegate a review pass to the **LLM_DOC_ARCHITECT** profile (specialist in LLM-facing docs + prompt design), which audits against exactly these practices.

## Refs
`skill-creator` (skill anatomy, progressive disclosure, description eval) · `customize` (agent `system_prompt` authoring; the identity-replaces-base rule) · `handoff-brief` (a machine doc that must survive a cold start) · `writing-science` / `expert-prose-style` (the HUMAN-reader counterpart when the reader is a person).
