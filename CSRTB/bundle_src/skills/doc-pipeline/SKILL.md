---
name: doc-pipeline
description: >-
  Invoke WHEN the task is to PRODUCE a document as a machine-md → human-readable-md → PDF set,
  either by AUTHORING one from a spec/request or by RENDERING human+PDF twins from an existing
  .machine.md source. Runs one gated pipeline: author (optional) → translate machine-md to human
  prose → render PDF, with fail-closed gates (atom-preservation diff + LLM faithfulness check +
  blank-page QA) and an advisory prose scan. Fires on "write a machine-md doc and render it",
  "make me a PDF of this", "generate the human + PDF twins", "turn this .machine.md into a
  document", "author a doc and produce the PDF". Two modes: mode="author" (full pipeline from a
  spec) and mode="render" (twins from a trusted .machine.md, e.g. a register or handoff doc).
  REQUIRES folio-science loaded (render backbone); writing-science optional (enables the prose
  gate). NOT for revising existing prose (→ writing-science), machine-md FORM guidance alone
  (→ machine-md), or rendering a diagram/one-off PDF with no machine source (→ folio-science).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# doc-pipeline — author → translate → render, with fail-closed gates

Produces the doc-style TRIPLET — `<name>.machine.md` (authoritative, LLM-facing) → `<name>.md`
(human-readable) → `<name>.pdf` — as one gated run. Architecture: full authoring ("A") built on a
reusable translate→render CORE ("B"). The CORE is independently callable, so an existing trusted
`.machine.md` renders its twins without re-authoring.

## When to use which mode
- `mode="author"` — you have a SPEC/request, not a document. Pipeline authors the `.machine.md`,
  then runs the core. Use for a NEW doc. The authored source is a CANDIDATE (gate 1 checks its form).
- `mode="render"` — you already have a TRUSTED `.machine.md` (a register, a handoff, a hand-written
  machine doc). Pipeline treats it as authoritative (no authoring, no gate 1), regenerates the twins.
  Use to refresh a source's human/PDF twins. This is the zero-authoring path.

## Dependency (load first)
REQUIRES `folio-science` loaded in the session — it provides `render_doc` + `qa_pdf`, which this
kernel calls. WHEN folio-science is absent => `run_doc_pipeline` raises with a load instruction.
`writing-science` is OPTIONAL: loaded => gate 4 runs the real `scan_draft` prose diagnostics; absent
=> gate 4 degrades to a light word/sentence check. Load both before running for the full gate set.

## The four gates (fail-closed except gate 4)
1. **gate1_form** (author mode only) — LLM machine-writing-quality review of the candidate `.machine.md`
   (`passes`, `issues`, `has_status_header`). Render mode SKIPS it (source is authoritative).
2. **gate2_faithfulness** — TWO complementary checks, both must pass or `ok=False`:
   - `atom_diff` (mechanical, fail-closed): every HARD atom in the source — backticked code, CLI
     flags (`--core`), filenames, task-ids (`T-08`), UUIDs, dotted numbers (`0.987`), ratios (`52/52`),
     multi-digit numbers — must appear in the human twin. Reports `missing_hard` + `coverage_hard`.
     On a miss it feeds the dropped atoms back for ONE repair-translation pass, then re-checks.
   - `faithfulness_review` (LLM): flags FABRICATIONS — claims/numbers/entities in the twin NOT in the
     source. Catches semantic drift the atom set can't (e.g. a command `printf|bash hook` paraphrased
     to `printf|bash`, changing its meaning).
3. **gate3_render** — `qa_pdf` blank-page/tofu gate; `nonblank=False` => `ok=False`.
4. **gate4_prose** — ADVISORY prose diagnostics (top writing-science flags). Does NOT fail the run:
   this is where the HUMAN reads the rendered PDF and gives the final blessing (see discipline below).

## The human-review discipline (load-bearing)
The human NEVER gates the `.machine.md` — it is LLM-facing and not meant for fluent human reading.
The human reads the RENDERED output (gate 4). gate2's atom-preservation guarantees every source atom
survives into the twin, so blessing the twin's CONTENT transitively blesses the source's content; the
source's FORM is covered by gate1 (an LLM fluent in machine-md). WHEN mode="author" => `ok=True` means
the gates passed, NOT that the doc is blessed — PRESENT the PDF to the user for the gate-4 human read
before treating it as final.

## Usage
```python
# doc-pipeline's helpers auto-load with the skill; folio-science's render_doc/qa_pdf and
# writing-science's scan_draft share the same python kernel namespace, so run_doc_pipeline finds
# them automatically — no import, no bridging. Just load folio-science (and optionally
# writing-science) in the session first, then call:

# AUTHOR mode (A): spec -> triplet
rep = run_doc_pipeline("A one-page onboarding note explaining the --core/--ergonomics/--personal tiers",
                       mode="author", out_stem="onboarding", workdir=".")

# RENDER mode (B): trusted .machine.md -> refreshed twins
rep = run_doc_pipeline("DEFERRED_TASKS.machine.md", mode="render", out_stem="DEFERRED_TASKS")

assert rep["ok"], rep["gates"]           # fail-closed: inspect the failing gate
# rep["artifacts"] -> {machine_md, human_md, pdf[, docx]}; then save_artifacts + present the PDF to the user
```
Pass `render_docx=True` for a `.docx` twin too; `model=` to pin the reasoning model; `repair_attempts=`
(default 1) for extra atom-repair passes.

## Kernel functions (auto-loaded from kernel.py)
- `run_doc_pipeline(source, *, mode, out_stem, workdir, model, extra_guidance, repair_attempts, render_docx)` → report dict
- `extract_atoms(text)` / `atom_diff(machine_md, human_md)` — the mechanical faithfulness gate (standalone-usable)
- `author_machine_md(spec)` / `review_machine_md(md)` — stage 1 + gate 1
- `translate_machine_to_human(md, missing_atoms=None)` / `faithfulness_review(md, human)` — stage 2 + gate 2 LLM half
- `qc_prose(human_md)` — gate 4 (uses writing-science `scan_draft` if loaded)

## Honest limits
- atom_diff catches STRUCTURED atoms (backticked tokens, flags, ids, numbers). A bare lowercase
  tool name (e.g. `xbeep` un-backticked) is NOT mechanically catchable without over-firing on every
  word — the LLM faithfulness pass is the backstop for those. The two halves are complementary BY
  DESIGN; run both.
- author mode is NON-deterministic (LLM authoring) — re-running a spec yields a different source each
  time. render mode is idempotent on a fixed source. Isolate authoring above the deterministic tail.
- translate/author use the reasoning model — a full run is several LLM calls (seconds–minutes), not free.
