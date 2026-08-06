---
name: scanned-pdf-ocr
description: Extract text from scanned or image-only PDFs (no usable text layer, or garbled mojibake extraction) — degraded journal scans, two-column academic articles, old book chapters. Use when pypdfium2/pdfplumber text extraction returns almost nothing or unreadable control-character garbage, when a citation must be verified against a scanned primary source, or when the user says a PDF "won't extract" / "is just images". Ships a detector + rasterizer + offline Tesseract OCR as a bundled CLI (scanned_pdf_ocr.py); for a hard page, rasterize it and read the PNG directly with the Read tool.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-19). Reshipped as a top-level `scanned_pdf_ocr.py` CLI (no auto-load kernel). Path 1 (offline Tesseract) is verbatim; the v2.0 in-kernel vision-model path has no Claude Code equivalent and is replaced by rasterize-then-Read-the-PNG.

# scanned-pdf-ocr — OCR for image-only PDFs

Some PDFs have **no usable text layer**: pure scans (each page is an image) or a
broken font-encoding that extracts as mojibake. Normal extraction
(`pypdfium2`, `pdfplumber`) returns almost nothing or unreadable garbage. This
skill recovers the text. The primary path (offline Tesseract) was validated in a
measured bake-off on a real 1994 two-column CACM scan and recovered the target
passage verbatim (~0.03% word error).

BUNDLED_TOOL: `scanned_pdf_ocr.py` (this dir). Three subcommands — `detect`,
`rasterize`, `ocr`. Pure-stdlib CLI; needs `pypdfium2` (all three) plus
`pytesseract` + the `tesseract` binary + `pillow` (for `ocr`). Invoke it
directly — there is no auto-load.

## Step 0 — confirm it actually needs OCR

```
python3 "$HOME/.claude/skills/scanned-pdf-ocr/scanned_pdf_ocr.py" detect paper.pdf
# -> {"needs_ocr": true, "pages": 9, "chars_per_page": 12.4, "alpha_ratio": 0.11}
```
`needs_ocr=true` when the text layer is sparse (`chars_per_page` low) OR mostly
non-text glyphs (`alpha_ratio` low — the mojibake signature). If `false`, just
extract normally; don't pay for OCR.

## Path 1 — Tesseract (PRIMARY: offline, fast, light)

One-time install (the `eng` traineddata ships **in the conda package — no model
download**, so it is immune to network blocks):

```
# conda/mamba
mamba install -c conda-forge tesseract pytesseract pypdfium2 pillow numpy
# or pip (needs a system tesseract binary present)
pip install pytesseract pypdfium2 pillow numpy
```

```
python3 "$HOME/.claude/skills/scanned-pdf-ocr/scanned_pdf_ocr.py" ocr paper.pdf --out paper_ocr.txt
# ~2s/page, ~160 MB RAM
```
- **`--psm 3` (default) reads multi-column pages in correct order. `--psm 6`
  SCRAMBLES columns** (reads horizontally across them) — the single most
  important setting for journal layouts.
- Rasterizes at 300 DPI grayscale. Output carries `===PAGE n===` markers.
- Faithful raw output keeps line-break hyphens; pass `--dehyphenate` for
  downstream NLP (leave off when you need verbatim quotes).
- Measured quality on a degraded 1994 scan: ~0.03% word error.

## Path 2 — rasterize + read the page image (FALLBACK: highest fidelity, no OCR engine)

When Tesseract's character accuracy is poor (very low contrast, unusual type),
render the page to a PNG and read it directly with the **Read tool** — Claude's
own vision transcribes the page. No model download, no OCR binary.

```
python3 "$HOME/.claude/skills/scanned-pdf-ocr/scanned_pdf_ocr.py" rasterize paper.pdf --out-dir ocr_pages --dpi 200
# writes ocr_pages/page_001.png ...
```
Then `Read ocr_pages/page_004.png` and transcribe VERBATIM. Guidance for a
faithful transcription (verbatim, no summarizing/correcting; join hyphen-split
words; read each column top-to-bottom then left-to-right; mark `[illegible]`) is
carried in the `VERBATIM_OCR_PROMPT` constant at the top of the CLI file — reuse
its wording.
- **Fidelity matters for citation work**: read carefully and do not paraphrase —
  a loose transcription can alter meaning ("excuse a murderer" vs "execute a
  murderer"). Usable for search either way; for a quotation, transcribe exactly.
- **Multi-column trouble**: if a two-column page transcribes out of order, crop
  the PNG to one column (or re-`rasterize` at higher `--dpi`) and read each half
  separately.
- Rasterize at ~200 DPI to keep the image legible without a huge file.

## Choosing a path

| Situation | Use |
|---|---|
| Default — any scanned PDF | **Tesseract** (`ocr`) — offline, fastest, lightest |
| Tesseract output has real character errors (low contrast, odd type) | **rasterize + Read the PNG** — highest fidelity, no OCR engine |
| One troublesome page | `rasterize` just that PDF, then Read the single `page_0NN.png` |

## When the sandbox is too constrained — the neural-OCR escape hatch

A third approach, **neural OCR (docTR / PaddleOCR / EasyOCR)**, has the best raw
character confidence but is heavy: it needs a model-weight download, a large CPU
install (torch + torchvision), and ~85–105 s/page CPU inference at ~2 GB RAM/page.
If you have a GPU or a less-constrained host, that is where neural OCR belongs —
on GPU it is seconds, not minutes. Otherwise prefer Path 1 or Path 2; both won
the bake-off without a download.

## RAM note

Process pages one at a time (the CLI does). Do not batch-decode a whole large
scan into memory at 300 DPI under tight headroom — a 9-page scan peaks ~160 MB
(Tesseract), but page images are ~3 MB each and add up.
