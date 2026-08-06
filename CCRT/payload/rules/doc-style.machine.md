# doc-style.machine.md
# STATUS: CURRENT (2026-07-11).
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# RULE: which docs are machine-optimized vs human-prose, + ask-when-unspecified.
# HOW-TO write each style / TRANSLATE between / INVARIANT(preserve atoms): ~/.claude/methodology/DOC_STYLE_MACHINE_VS_HUMAN.machine.md.
# (self-demonstrating: this file is machine-optimized.)

RULE.style_by_primary_reader: optimize each doc for its PRIMARY reader. reader=Claude(parse+act) => MACHINE (MACHINE.rules). reader=user(read/learn/decide) => HUMAN (HUMAN.rules). ONE primary reader per doc; dual-audience => split (1 machine + a short human section), keeping each part fully in its own style (not half-both in one file).

CLASS.always_machine (reader=Claude; write per MACHINE.rules):
  - ANY `.claude/` dir + ALL subdirs: CLAUDE.md, rules/*, agents/* (subagent prompts), settings/skill/hook docs.
  - ALL CLAUDE.md at EVERY level (repo-root included).
  - ALL hand-off documents (machine-record + protocol).
  - any `*.machine.md` (name == the style signal).
  - project-specific path lists → a project-level .claude/rules/<project>-doc-style.machine.md
CLASS.always_human (reader=user; write per HUMAN.rules):
  - progress reports: `*_REPORT*` · any status write-up authored FOR the user to read.
  - onboarding · rationale/explanation · papers · human-facing READMEs (a repo published for people).
  - project-specific path lists → a project-level .claude/rules/<project>-doc-style.machine.md

RULE.ask_if_unspecified: user requests a NEW .md NOT matched by CLASS.always_* AND does not state machine|human => ASK which BEFORE writing; let their answer decide (not a silent default).

RULE.functional_pipeline (functional doc = anything a HUMAN would also read; the standard machine→human→pdf lifecycle): CLASS.always_human + any dual-audience functional/reference doc => MAINTAINED as a 3-artifact set: (1) MACHINE `*.machine.md` = the AUTHORITATIVE ROOT / single source of truth (cited, terse, atoms); (2) HUMAN `.md` = an atom-preserving TRANSLATION of the machine root (per INVARIANT.convert; human-prose); (3) `.pdf` = RENDERED from the human `.md`.
  INVARIANT.machine_is_root: EVERY update/correction lands in the MACHINE version FIRST, then propagates machine→human→re-render-pdf. Treat the human/pdf as DERIVED artifacts — regenerate them FROM the machine root, rather than editing them directly and backporting.
  INTERNAL-ONLY docs (`.claude/` rules/agents/settings/hooks — purely-Claude-read) => MACHINE-ONLY: skip the human + pdf (no other reader; a pdf of something only Claude reads is waste).
  ORIGIN: user 2026-07-04.

INVARIANT.convert (existing doc -> other style): preserve ATOMS EXACTLY — every rule/fact/step kept, none added/dropped/altered (DOC_STYLE INVARIANT + TRANSLATE.human_to_machine step6 VERIFY). Only the PACKAGING changes.
NAMING: a NEW machine doc => name it `*.machine.md`. An EXISTING doc with a REQUIRED or widely-REFERENCED name (CLAUDE.md, README.md, DEVELOPMENT_RULES.md, FORCING_PIPELINE.md, *_PROTOCOL.machine.md) keeps its name; convert the CONTENT-style in place and preserve the filename (renaming breaks cross-references).
