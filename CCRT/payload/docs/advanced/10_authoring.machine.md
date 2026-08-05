# 10_authoring.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: AUTHORING YOUR OWN EXTENSIONS — the machine-md -> machine-doc-reviewer -> folio loop; + the methodology source docs the toolkit's behaviors derive from.
# FOR: a user building their own skill/agent/rule/hook to the toolkit's standard. Part of the ADVANCED set — map + REFERENCES in 00_overview.machine.md.
# STYLE: machine-terse, front-loaded, POSITIVE action-first; per-unit shape FOR -> HANDLE -> mechanics -> INVARIANT -> FEEDS.

## 10.1 · AUTHORING YOUR OWN EXTENSIONS
- FOR: a repeatable loop to build your own skill / agent / rule / hook to the toolkit's own standard.
- THE LOOP: draft with `/machine-md` (applies LLM-doc best-practices) → audit with the `machine-doc-reviewer` agent → render a human/PDF twin with `/folio`.
- APPLIES to: skills, agents, rules, hooks (any `.claude/` extension).
- TYING IT TOGETHER: everything in this guide is a FILE under a scope (01_extension_architecture) ⇒ authoring an extension = write the file in the right SHAPE (a skill folder [02_skills_and_commands] / an agent `.md` [03_agents] / a rule with `paths:` [§01.2] / a hook script + a `settings.json` registration [§01.4]), place it in the SCOPE whose reach you want (§01.1/§01.3), then restart the session to load it. The `/machine-md` → `machine-doc-reviewer` → `/folio` loop keeps the machine root, its audit, and its human twin in sync; the `doc-style` rule keeps the machine `.machine.md` as the authoritative source and the human `.md` / PDF as derived artifacts.

## 10.2 · THE METHODOLOGY DOCS
- FOR: the canonical write-ups behind the toolkit's headline behaviors — shipped but currently UNDOCUMENTED in the two usage guides.
- HANDLE: the 4 "why/how" source docs that specific skills/rules DERIVE from — edit the source to change the behavior.
- LOCATION: `~/.claude/methodology/` — 3 machine docs.
- AUTONOMY_MANDATE ⇒ the canonical autonomy rule that `/solo` derives from.
- HANDOFF_PROTOCOL ⇒ how to write a resumable handoff; underpins `/baton`.
- DOC_STYLE_MACHINE_VS_HUMAN ⇒ the machine-vs-human doc method; underpins the `doc-style` rule + `/folio`.
- INVARIANT: each doc is the AUTHORITATIVE source its skill/rule points back to ⇒ change the behavior by editing the methodology doc, not the derived skill in isolation.
- FEEDS: `/solo` (02_skills_and_commands), `/baton`, `/folio`, the `doc-style` rule (§01.2/§01.3).

## SOURCES
Architecture facts; the consolidated reference list (official docs + blogs) lives in 00_overview.machine.md (§ REFERENCES).
