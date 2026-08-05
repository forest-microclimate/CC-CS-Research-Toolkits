<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Authoring Your Own Extensions — Claude Code Advanced Guide

This is the human twin of the authoritative machine root `10_authoring.machine.md`; this version and its PDF are derived from that root and rendered with `/folio`. It gives you a repeatable loop to build your own skill, agent, rule, or hook to the toolkit's own standard, and it points to the methodology source documents that the toolkit's headline behaviors derive from.

> **What this is.** The advanced set's authoring document. Having read *what* you can change and *how* to wield it, you now turn the guide back on itself and build your *own* extension — a skill, agent, rule, or hook — to the same standard the toolkit itself was built to. Two parts: the authoring loop (§10.1), and the methodology source documents behind the toolkit's headline behaviors (§10.2).

## 10.1 · Authoring Your Own Extensions

**What it's for.** A single repeatable loop to build your own skill, agent, rule, or hook to the toolkit's own standard.

**The loop.** Draft with `/machine-md` (which applies LLM-doc best-practices) → audit with the `machine-doc-reviewer` agent → render a human/PDF twin with `/folio`. It applies to any `.claude/` extension — skills, agents, rules, and hooks alike.

**Tying it together.** Everything in this guide is a *file under a scope* (`01_extension_architecture`), so authoring an extension comes down to three concrete moves. First, write the file in the right *shape*: a skill folder (`02_skills_and_commands`), an agent `.md` (`03_agents`), a rule with a `paths:` header (§01.2), or a hook script plus a `settings.json` registration (§01.4). Second, place it in the *scope* whose reach you want (§01.1 / §01.3). Third, restart the session to load it.

The loop then keeps the derived artifacts honest. The `/machine-md` → `machine-doc-reviewer` → `/folio` cycle keeps the machine root, its audit, and its human twin in sync; and the `doc-style` rule keeps the machine `.machine.md` as the authoritative source, with the human `.md` and the PDF as derived artifacts.

## 10.2 · The Methodology Docs

**What it's for.** The canonical write-ups behind the toolkit's headline behaviors — shipped, but currently undocumented in the two usage guides.

**The handle.** These are the three "why / how" source documents that specific skills and rules *derive* from — so you edit the source to change the behavior. All three live in `~/.claude/methodology/` as machine docs:

- **`AUTONOMY_MANDATE`** — the canonical autonomy rule that `/solo` derives from.
- **`HANDOFF_PROTOCOL`** — how to write a resumable handoff; underpins `/baton`.
- **`DOC_STYLE_MACHINE_VS_HUMAN`** — the machine-vs-human doc method; underpins the `doc-style` rule and `/folio`.

**The invariant.** Each of these docs is the *authoritative* source its skill or rule points back to — so you change a behavior by editing the methodology doc, not the derived skill in isolation.

Together these three feed a broad slice of the toolkit: `/solo` (`02_skills_and_commands`), `/baton`, `/folio`, and the `doc-style` rule (§01.2 / §01.3).

## Sources

Architecture facts; the consolidated reference list — official docs and blogs — lives in `00_overview`, §00.4.
