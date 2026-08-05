#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""scanned_pdf_ocr.py -- OCR for scanned/image-only PDFs, for Claude Code.

Some PDFs have no usable text layer: pure scans (each page is an image) or a
broken font-encoding that extracts as mojibake. Normal extraction (pypdfium2,
pdfplumber) returns almost nothing or unreadable garbage. This tool recovers the
text via offline Tesseract, and rasterizes pages so a page image can be read
directly when Tesseract's character accuracy is poor.

Re-shipped from the v2.0 scanned-pdf-ocr kernel as a standalone CLI
(Claude Code has no auto-loaded kernel). The detector + rasterizer + Tesseract
functions are VERBATIM from that kernel; only the argparse CLI is added. The
in-kernel vision-model path has NO Claude Code equivalent and is NOT
shipped -- for a hard page, rasterize it and read the PNG with the Read tool
(see SKILL.md, Path 2).

Bundled in this skill's directory. Invoke it directly -- there is no auto-load:
    python3 "$HOME/.claude/skills/scanned-pdf-ocr/scanned_pdf_ocr.py" detect    paper.pdf
    python3 "$HOME/.claude/skills/scanned-pdf-ocr/scanned_pdf_ocr.py" rasterize paper.pdf --out-dir ocr_pages --dpi 300
    python3 "$HOME/.claude/skills/scanned-pdf-ocr/scanned_pdf_ocr.py" ocr       paper.pdf --out paper_ocr.txt

  detect    : report whether the PDF lacks a usable text layer (JSON). Exit 0
              always; needs_ocr=true means route it through `ocr`.
  rasterize : render each page to a PNG (for the Read-the-image fallback, or to
              feed another OCR engine). Prints the written paths.
  ocr       : offline Tesseract OCR of the whole PDF. Prints (or writes with
              --out) the text with ===PAGE n=== markers.

Needs pypdfium2 (detect/rasterize/ocr) + pytesseract + the tesseract binary +
pillow (ocr). See SKILL.md for the one-line install. Pure stdlib CLI otherwise;
portable macOS + Linux.
"""
import argparse, os, re, sys

VERBATIM_OCR_PROMPT = (
    "You are performing OCR on a scanned page from an academic document. "
    "Transcribe the text VERBATIM - every word exactly as printed. Do NOT "
    "summarize, correct, comment, or add anything. Output ONLY the transcribed "
    "text. If a word is split across a line by a hyphen, join it into the whole "
    "word. Preserve paragraph breaks with a blank line. If the page has multiple "
    "columns, read each column fully top-to-bottom, then move left-to-right. "
    "Mark truly illegible text [illegible]."
)


def pdf_needs_ocr(pdf_path, min_chars_per_page=100, min_alpha_ratio=0.5):
    """Detect whether a PDF lacks a usable text layer (scanned image or mojibake).
    Returns a dict; needs_ocr=True means route it through ocr_pdf_tesseract."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(pdf_path)
    n = len(pdf)
    total = 0
    good = 0
    allowed = set(".,;:'\"()[]-/%&$#@!?")
    for i in range(n):
        pg = pdf[i]
        tp = pg.get_textpage()
        t = tp.get_text_range()
        tp.close()
        pg.close()
        total += len(t)
        good += sum(1 for ch in t if ch.isalnum() or ch.isspace() or ch in allowed)
    pdf.close()
    cpp = total / max(1, n)
    ratio = good / max(1, total)
    needs = (cpp < min_chars_per_page) or (ratio < min_alpha_ratio)
    return {"needs_ocr": bool(needs), "pages": n,
            "chars_per_page": round(cpp, 1), "alpha_ratio": round(ratio, 3)}


def rasterize_pdf(pdf_path, out_dir="ocr_pages", dpi=300, grayscale=True):
    """Render each PDF page to a PNG at the given DPI. Returns the list of paths."""
    import pypdfium2 as pdfium
    os.makedirs(out_dir, exist_ok=True)
    pdf = pdfium.PdfDocument(pdf_path)
    paths = []
    for i in range(len(pdf)):
        bmp = pdf[i].render(scale=dpi / 72.0, grayscale=grayscale)
        p = os.path.join(out_dir, f"page_{i + 1:03d}.png")
        bmp.to_pil().save(p)
        paths.append(p)
    pdf.close()
    return paths


def ocr_pdf_tesseract(pdf_path, out_txt=None, dpi=300, psm=3, lang="eng",
                      dehyphenate=False):
    """Offline OCR via Tesseract. PRIMARY path - no network, ~2s/page, low RAM.
    psm=3 (auto page segmentation) reads multi-column pages in correct order;
    psm=6 SCRAMBLES columns (reads horizontally across them) - do not use it for
    journal layouts. Requires an env with tesseract + pytesseract (see SKILL.md).
    Returns the full text with ===PAGE n=== markers."""
    import pytesseract
    from PIL import Image
    pages = rasterize_pdf(pdf_path, out_dir="ocr_pages_tess", dpi=dpi, grayscale=True)
    cfg = f"--oem 1 --psm {psm} -l {lang}"
    parts = []
    for idx, p in enumerate(pages, 1):
        t = pytesseract.image_to_string(Image.open(p), config=cfg)
        if dehyphenate:
            t = re.sub(r"([A-Za-z])-\n([a-z])", r"\1\2", t)
        parts.append(f"\n===PAGE {idx}===\n" + t)
    text = "".join(parts)
    if out_txt:
        with open(out_txt, "w") as f:
            f.write(text)
    return text


def cmd_detect(args):
    import json
    print(json.dumps(pdf_needs_ocr(args.pdf,
                                   min_chars_per_page=args.min_chars_per_page,
                                   min_alpha_ratio=args.min_alpha_ratio)))
    return 0


def cmd_rasterize(args):
    paths = rasterize_pdf(args.pdf, out_dir=args.out_dir, dpi=args.dpi,
                          grayscale=not args.color)
    for p in paths:
        print(p)
    return 0


def cmd_ocr(args):
    text = ocr_pdf_tesseract(args.pdf, out_txt=args.out, dpi=args.dpi,
                             psm=args.psm, lang=args.lang,
                             dehyphenate=args.dehyphenate)
    if not args.out:
        sys.stdout.write(text)
    else:
        print(f"wrote {args.out} ({len(text)} chars)")
    return 0


def main():
    ap = argparse.ArgumentParser(
        prog="scanned_pdf_ocr.py",
        description="OCR for scanned/image-only PDFs (offline Tesseract + rasterizer).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("detect", help="report whether the PDF needs OCR (JSON)")
    d.add_argument("pdf")
    d.add_argument("--min-chars-per-page", type=float, default=100)
    d.add_argument("--min-alpha-ratio", type=float, default=0.5)
    d.set_defaults(func=cmd_detect)

    r = sub.add_parser("rasterize", help="render each page to a PNG")
    r.add_argument("pdf")
    r.add_argument("--out-dir", default="ocr_pages")
    r.add_argument("--dpi", type=int, default=300)
    r.add_argument("--color", action="store_true", help="render in color (default grayscale)")
    r.set_defaults(func=cmd_rasterize)

    o = sub.add_parser("ocr", help="offline Tesseract OCR of the whole PDF")
    o.add_argument("pdf")
    o.add_argument("--out", default=None, help="write text here (else stdout)")
    o.add_argument("--dpi", type=int, default=300)
    o.add_argument("--psm", type=int, default=3,
                   help="Tesseract page-seg mode; 3=multi-column safe, 6 SCRAMBLES columns")
    o.add_argument("--lang", default="eng")
    o.add_argument("--dehyphenate", action="store_true",
                   help="join line-break hyphens (leave off for verbatim quotes)")
    o.set_defaults(func=cmd_ocr)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
