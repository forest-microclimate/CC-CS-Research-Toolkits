---
name: scanned-pdf-ocr
description: Extract text from scanned or image-only PDFs (no usable text layer, or garbled mojibake extraction) — degraded journal scans, two-column academic articles, old book chapters. Use when pypdfium2/pdfplumber text extraction returns almost nothing or unreadable control-character garbage, when a citation must be verified against a scanned primary source, or when the user says a PDF "won't extract" / "is just images". Ships a detector (pdf_needs_ocr) plus two working recipes: offline Tesseract (primary) and the in-kernel vision model (fallback, no download).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# scanned-pdf-ocr — OCR for image-only PDFs in the sandbox

Some PDFs have **no usable text layer**: pure scans (each page is an image) or a
broken font-encoding that extracts as mojibake. Normal extraction
(`pypdfium2`, `pdfplumber`) returns almost nothing or unreadable garbage. This
skill recovers the text. Both paths were validated in a measured bake-off on a
real 1994 two-column CACM scan; both recovered the target passage verbatim.

Kernel helpers auto-load on `skill({skill:"scanned-pdf-ocr"})`:
`pdf_needs_ocr`, `rasterize_pdf`, `ocr_pdf_tesseract`, `ocr_pdf_vlm`, `ocr_image_vlm`.

## Step 0 — confirm it actually needs OCR

```python
pdf_needs_ocr("paper.pdf")
# → {'needs_ocr': True, 'pages': 9, 'chars_per_page': 12.4, 'alpha_ratio': 0.11}
```
`needs_ocr=True` when the text layer is sparse (`chars_per_page` low) OR mostly
non-text glyphs (`alpha_ratio` low — the mojibake signature). If `False`, just
extract normally; don't pay for OCR.

## Path 1 — Tesseract (PRIMARY: offline, fast, light)

One-time env (tesseract ships its `eng` traineddata in the conda package — **no
model download**, so it is immune to allowlist blocks):

```
manage_environments(mode="create", name="ocr", channels=["conda-forge"],
    python_version="3.13", packages=["tesseract","pytesseract","pypdfium2","pillow","numpy"])
```

```python
# run with environment="ocr"
text = ocr_pdf_tesseract("paper.pdf", out_txt="paper_ocr.txt")   # ~2s/page, ~160 MB RAM
```
- **`psm=3` (default) reads multi-column pages in correct order. `psm=6` SCRAMBLES
  columns** (reads horizontally across them) — the single most important setting
  for journal layouts.
- Rasterizes at 300 DPI grayscale. Output carries `===PAGE n===` markers.
- Faithful raw output keeps line-break hyphens; pass `dehyphenate=True` for
  downstream NLP (leave off when you need verbatim quotes).
- Measured quality on a degraded 1994 scan: ~0.03% word error.

## Path 2 — in-kernel vision model (FALLBACK: no download, highest fidelity)

When Tesseract's character accuracy is poor (very low contrast, unusual type),
use the platform vision model. **No model download** — uses `host.llm` vision —
so it also survives an allowlist block. Needs only `pypdfium2`.

```python
# run with environment="python" (or any env with pypdfium2)
text = ocr_pdf_vlm("paper.pdf", out_txt="paper_ocr.txt")   # ~2.5s/page parallel, ~$0.04/page
```
- **Pins the REASONING model by default** (`host.reasoning_model()`). This is
  load-bearing: the utility/Haiku default produced *meaning-altering* errors on a
  hard scan ("excuse a murderer" → "execute a murderer") — usable for search,
  unsafe for quotation. Do not override to a cheaper model for citation work.
- **Content-filter blocks**: some pages deterministically return a block; the
  helper auto-retries that page split into left/right halves. That is why a
  multi-column page may be transcribed per-column.
- Rasterizes at 200 DPI (keeps input tokens ~2.3k/page).

## Choosing a path

| Situation | Use |
|---|---|
| Default — any scanned PDF | **Tesseract** (`ocr_pdf_tesseract`) — offline, fastest, lightest |
| Tesseract output has real character errors (low contrast, odd type) | **VLM** (`ocr_pdf_vlm`) — highest fidelity, no download |
| Either path, for one troublesome page | `ocr_image_vlm("ocr_pages_tess/page_04.png")` |

## When the sandbox is too constrained — the Linux/GPU escape hatch

A third approach, **neural OCR (docTR / PaddleOCR / EasyOCR)**, has the best raw
character confidence but is a poor fit for THIS sandbox: it needs a
model-weight download from a host that is **not on the allowlist** (returns HTTP
403 until a one-time `request_network_access` grant), a heavy CPU install
(torch + torchvision), and ~85–105 s/page CPU inference at ~2 GB RAM/page. If you
have a GPU or a less-constrained host (e.g. a Linux box added as a compute
target), that is where neural OCR belongs — on GPU it is seconds, not minutes.
In-sandbox, prefer Path 1 or Path 2; both won the bake-off without a download.

## RAM note

Process pages one at a time (all helpers do). Do not batch-decode a whole large
scan into memory at 300 DPI under tight headroom — a 9-page scan peaks ~160 MB
(Tesseract) / ~226 MB (VLM), but page images are ~3 MB each and add up.
