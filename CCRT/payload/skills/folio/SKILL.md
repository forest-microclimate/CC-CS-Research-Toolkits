---
name: folio
description: Translate a machine-authored doc into a human twin and render it to PDF + docx. Invoke WHEN a dual-audience document needs a human-readable PDF — a *.machine.md that has or needs a human twin, or when the user asks for a PDF/docx of a doc. Runs a preflight tool-check that offers to install missing render tools (pandoc, LaTeX, typst, mermaid-cli, python3), an atom-preserving machine→human translation, the verified xelatex render (forces full MacTeX to dodge the TinyTeX glyph-drop), and a "Missing char" QA gate that must read 0. Also emits a .docx twin WHEN the invocation text includes "docx" (e.g. /folio <doc> docx); PDF-only otherwise.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-11).

# folio — machine.md ⇒ human.md ⇒ PDF + docx

The `*.machine.md` is the authoritative ROOT; folio DERIVES the human twin + the renders. Every edit lands in the `.machine.md` FIRST, then re-run folio. Regenerate the derived `.md`/`.pdf`/`.docx` from the root rather than hand-editing them — they are outputs. [doc-style.machine.md RULE.functional_pipeline + INVARIANT.machine_is_root]

## When to invoke
WHEN a dual-audience functional doc needs a human PDF: a `*.machine.md` that has/needs a human twin, or a "make a PDF/docx of X" request.
Internal-only `.claude/` docs (CLAUDE.md, rules, agents, hooks) are machine-only (no human/pdf twin) ⇒ skip folio for them.

## PIPELINE (in order)
PREFLIGHT tool-check → STAGE 1 translate → STAGE 2 render → QA gate.
ARGS: the doc (path or the doc in context). Output = PDF by default; IF the invocation text contains the word "docx" ⇒ ALSO emit a Word twin.

## PREFLIGHT — detect tools; ASK before installing anything
DETECT (read-only):
  - OS  = `uname -s` → Darwin=macos | Linux=linux
  - PKG = macos ⇒ brew ; linux ⇒ first present of {apt-get, dnf, pacman}
  - pandoc  : `command -v pandoc`
  - latex   : PREFER `test -x /Library/TeX/texbin/xelatex` (full MacTeX) ; else `command -v xelatex` (+WARN: may be the TinyTeX shadow → glyph-drop risk)
  - python3 : `command -v python3`
  - font    : `test -f "/Library/Fonts/Arial Unicode.ttf"` || `test -f "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"`
  - typst   : `command -v typst`   # REQUIRED only if the doc has a mermaid block
  - mmdc    : `command -v mmdc`     # REQUIRED only if the doc has a mermaid block
REQUIRED for THIS doc = {pandoc, latex, python3, font} + {typst, mmdc} IFF the doc contains a fenced ```mermaid``` block.
GATE (ask-before-install):
  IF any REQUIRED tool missing ⇒ PRINT the missing list + the exact per-tool install commands (below) ⇒ ASK: "install these now? [y/N]".
    y ⇒ run the installs for this OS.  N ⇒ print the manual commands and STOP — render only after the required tools are installed.
  each install surfaces a PERMISSION prompt; the toolkit deny-list BLOCKS `sudo`/`curl`/`wget` ⇒ on Linux the `sudo` lines are HANDED TO THE USER to run (or temporarily allowed).
  `brew install --cask mactex-no-gui` ≈ multi-GB / several minutes — say so before running.

INSTALL commands
  | tool        | macos (brew)                                 | linux (apt shown; dnf/pacman analog)                                   |
  |-------------|----------------------------------------------|------------------------------------------------------------------------|
  | pandoc      | `brew install pandoc`                        | `sudo apt-get install -y pandoc`                                       |
  | latex       | `brew install --cask mactex-no-gui` [PREFER] | `sudo apt-get install -y texlive-xetex texlive-luatex texlive-fonts-recommended` |
  |             | fallback `brew install --cask basictex` (small BUT is the PATH-shadow culprit; then `sudo tlmgr update --self && tlmgr install <pkgs>`) | |
  | typst       | `brew install typst`                         | `cargo install typst-cli` (or distro pkg)                             |
  | mermaid-cli | `npm i -g @mermaid-js/mermaid-cli`           | `npm i -g @mermaid-js/mermaid-cli`                                     |
  | python3     | `brew install python3`                       | `sudo apt-get install -y python3`                                     |
  | fonts       | Arial Unicode MS ships with macOS            | `sudo apt-get install -y fonts-dejavu` + a Unicode mainfont (e.g. Noto)|

TRAP.path_shadow: `which -a xelatex` may list a TinyTeX/BasicTeX engine FIRST (`/usr/local/bin/xelatex` → silently drops glyphs) and full MacTeX SECOND (`/Library/TeX/texbin/xelatex`). ⇒ ALWAYS pass the ABSOLUTE MacTeX engine, never bare `xelatex`. The QA gate is the backstop.

## STAGE 1 — TRANSLATE  `<name>.machine.md` ⇒ `<name>.md`   [DOC_STYLE_MACHINE_VS_HUMAN.machine.md TRANSLATE.machine_to_human]
  1. GROUP atoms into themes; ORDER as a narrative (motivate → rule → example → caveat).
  2. EXPAND shorthand/symbols to words; add transitions.
  3. ADD motivation/context up front + examples for the non-obvious.
  4. SOFTEN imperatives into rationale; add emphasis/repetition for key points.
  5. VERIFY a first-time human reader can follow WITHOUT the source.
  INVARIANT: preserve EVERY atom (rule / fact / step / number / path / citation) — none added, dropped, or altered; only the PACKAGING changes. Optionally delegate the atom-equality check to the `machine-doc-reviewer` agent.
  OUTPUT: write the human twin beside the root — `<name>.machine.md` ⇒ `<name>.md`.

## STAGE 2 — RENDER
PATH-select: doc contains a ```mermaid``` block ⇒ mermaid path ; else standard path.

RENDER.standard (verified — use for prose docs):
```bash
ENGINE=/Library/TeX/texbin/xelatex   # or the detected xelatex if that absolute path is absent (then trust the QA gate)
pandoc <name>.md -o <name>.pdf --pdf-engine="$ENGINE" \
  -V geometry:margin=1in -V mainfont="Arial Unicode MS" -V monofont="DejaVu Sans Mono"
# docx twin — OPT-IN: run this line ONLY IF the invocation text contains "docx" (e.g. `/folio <doc> docx`); default = PDF only:
pandoc <name>.md -o <name>.docx      # Word handles Unicode natively, always clean
```

RENDER.mermaid (doc has a ```mermaid``` block — ported from the projects' `docs/functional/render.sh`):
```bash
mmdc -i <name>.md -o r.md -e png -s 2 -p pc.json          # pc.json = {"args":["--no-sandbox"]}
# rewrite each  <!--FIG: <caption> | <width%> -->  (immediately before a mermaid block) into a
#   centered, captioned, sized figure (comment stripped; default "Figure" @ 72%)
pandoc r.md -o <name>.pdf --pdf-engine=typst --metadata title="<title>"
pandoc r.md -o <name>.docx      # docx twin — OPT-IN (only if "docx" was requested); from the rewritten intermediate so diagrams embed as images
```

## QA GATE — "Missing char" MUST be 0
```bash
pandoc <name>.md -o /dev/null -t pdf --pdf-engine="$ENGINE" \
  -V mainfont="Arial Unicode MS" -V monofont="DejaVu Sans Mono" 2>&1 | grep -c "Missing char"
```
`-t pdf` is REQUIRED — `/dev/null` has no extension for pandoc to infer the format; without it the gate silently no-ops.
`==0` ⇒ PASS. `>0` ⇒ FAIL: a glyph was dropped — almost always the wrong engine (TinyTeX shadow) or a mainfont lacking the glyph. FIX: confirm the ABSOLUTE MacTeX engine; else swap/extend the mainfont to one carrying the glyph; re-run to 0. Ship a PDF ONLY after it passes this gate (0) — never one that fails.
(mermaid/typst path: typst has broad Unicode defaults ⇒ QA by page-raster inspection [`pdftoppm` / `render.sh --inspect`], not the xelatex Missing-char grep.)

## Success check
`<name>.md` preserves every atom of the root; `<name>.pdf` exists (+ `<name>.docx` if "docx" was requested); the QA gate reads 0.

## Refs
`~/.claude/rules/doc-style.machine.md` (RULE.functional_pipeline; INVARIANT.machine_is_root) · `~/.claude/methodology/DOC_STYLE_MACHINE_VS_HUMAN.machine.md` (TRANSLATE.machine_to_human; INVARIANT) · `machine-doc-reviewer` agent (atom-preservation audit) · the projects' `docs/functional/render.sh` (mermaid→typst path).
