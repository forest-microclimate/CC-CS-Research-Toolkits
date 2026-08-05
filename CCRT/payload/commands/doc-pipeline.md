---
description: Produce a document as the machine.md ⇒ human.md ⇒ PDF triplet — AUTHOR one from a spec, or RENDER twins from an existing .machine.md. Full authoring layered on the folio render core, with fail-closed faithfulness + blank-page gates and a human read of the rendered output.
tags: [docs, authoring, machine-md, render, pipeline, folio]
argument-hint: "[author <spec> | render <path.machine.md>] [docx]"
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# /doc-pipeline — author ⇒ translate ⇒ render, one gated run

Produce the doc-style TRIPLET — `<name>.machine.md` (authoritative, LLM-facing) ⇒ `<name>.md` (human-readable) ⇒ `<name>.pdf`. Architecture: full AUTHORING ("A") layered on the `folio` translate+render CORE ("B"). This command owns the authoring stage folio lacks; it REUSES `/folio` for translate + render + QA rather than duplicating it. [doc-style.machine.md RULE.functional_pipeline + INVARIANT.machine_is_root]

## Two modes (from the first arg; default = author)
- **`author <spec>`** — you have a REQUEST, not a document. This command authors the `.machine.md` (STAGE 1 + GATE 1), then hands to folio for the tail. Use for a NEW doc. The authored source is a CANDIDATE until the gates pass + the human reads the render.
- **`render <path.machine.md>`** — you already have a TRUSTED `.machine.md` (a register, a handoff, a hand-written machine doc). SKIP authoring + gate 1; invoke `/folio <path>` directly to regenerate the twins. This is the zero-authoring path. Add `docx` to also emit a Word twin.

## PIPELINE (in order)
STAGE 1 author (author mode only) → GATE 1 form → hand to /folio {STAGE 2 translate → STAGE 3 render → QA} → GATE 4 prose + HUMAN read.

## STAGE 1 — AUTHOR the machine.md (author mode only)
Author `<name>.machine.md` per the `machine-md` skill: terse machine style; positive trigger-conditioned framing (`WHEN (condition) ⇒ (action)`); output-detectable triggers; high atom-density (name specific identifiers, numbers, files, thresholds); NO filler prose. Wrap every code-like token in backticks — CLI flags (`--core`), commands, filenames, function names, config keys — so they are unambiguous atoms. First two lines: a `# <TITLE>` heading, then the literal line `# STATUS: CURRENT` (doc-currency). The doc MUST be complete + self-contained for its stated purpose. Write the `.machine.md` to disk as the authoritative ROOT.

## GATE 1 — FORM review (author mode only)  [fail-closed]
Invoke the `machine-doc-reviewer` agent (or apply the `machine-md` rubric) on the candidate: is it terse machine style (NOT human prose), trigger-conditioned + output-detectable, atom-dense, `# STATUS:`-headed, self-contained? WHEN gate 1 fails ⇒ revise the `.machine.md` and re-review before proceeding. The human does NOT read the machine.md here — its reader is an LLM (see the human-review discipline below).

## STAGES 2–3 — hand to /folio (the render CORE)
Invoke `/folio <name>.machine.md` (append `docx` if requested). Folio runs its preflight tool-check, the atom-preserving machine→human TRANSLATE (STAGE 2), the verified render (STAGE 3), and its "Missing char" QA gate. Folio IS the B-core — do not re-implement translation or rendering here.

## GATE 2 — FAITHFULNESS  [fail-closed, enforced inside folio + here]
The human twin MUST preserve every source ATOM (each identifier, number, filename, id, flag, threshold appears, expanded not dropped) AND fabricate NOTHING (no claim/number/entity absent from the source). Folio's translate step preserves atoms; additionally CHECK the twin against the source for (a) any dropped atom, (b) any fabricated addition, (c) semantic drift of a command/identifier (e.g. `printf JSON | bash hook` paraphrased to `printf JSON | bash` — a different command). WHEN a drop or fabrication is found ⇒ fix the twin (regenerate from the root, never hand-patch) + re-check.

## GATE 3 — RENDER  [fail-closed, inside folio]
Folio's QA gate must read 0 missing characters / no blank page. WHEN it fails ⇒ folio's trap guidance applies (absolute MacTeX engine, etc.); do not ship a blank/tofu PDF.

## GATE 4 — PROSE + the HUMAN read  [advisory + human gate]
Optionally scan the human twin for prose defects (the `writing-science` skill's tells). Then PRESENT the rendered PDF to the user: this is where the HUMAN reads and blesses the output. `author` mode passing the gates means the machinery succeeded, NOT that the doc is blessed — surface the PDF and wait for the human read before treating it as final.

## The human-review discipline (load-bearing)
The human NEVER gates the `.machine.md` — it is LLM-facing and not meant for fluent human reading. The human reads the RENDERED output (gate 4). Gate 2's atom-preservation guarantees every source atom survives into the twin, so blessing the twin's CONTENT transitively blesses the source's content; the source's FORM is covered by gate 1 (machine-doc-reviewer, an LLM fluent in machine-md). Two LLM checks at OPPOSITE ends, different competencies: machine-doc quality at the top (gate 1), human-prose quality at the bottom (gate 4).

## Notes
- author mode is NON-deterministic (LLM authoring) — re-running a spec yields a different source each time. render mode is idempotent on a fixed source. This is why authoring is isolated ABOVE the deterministic folio tail.
- Internal-only `.claude/` docs (CLAUDE.md, rules, agents, hooks) are machine-only ⇒ no human/pdf twin ⇒ do NOT run this pipeline on them (same carve-out folio makes).

Run the mode + stage the `.machine.md`, present the plan for the current request, then execute — surfacing the rendered PDF for the human read at the end.
