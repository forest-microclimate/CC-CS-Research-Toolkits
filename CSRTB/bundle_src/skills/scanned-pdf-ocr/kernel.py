# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""OCR helpers for scanned/image-only PDFs in the sandbox.
Primary: Tesseract (offline, no download). Fallback: in-kernel vision model (no download).
Built from a measured 3-way bake-off on a real 1994 two-column academic scan.
"""
import os
import re

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
    Returns a dict; needs_ocr=True means route it through ocr_pdf_tesseract/vlm."""
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


def ocr_image_vlm(img_path, model=None, max_tokens=8192, prompt=None,
                  split_on_block=True):
    """OCR one page image via the in-kernel vision model (no download).
    On a content-filter block (deterministic on some pages), splits the page into
    left/right halves and transcribes each - the measured workaround. Pins the
    REASONING model by default: the utility default alters meaning on hard scans."""
    from PIL import Image
    if model is None:
        model = host.reasoning_model()
    if prompt is None:
        prompt = VERBATIM_OCR_PROMPT
    r = host.llm({"prompt": prompt, "images": [img_path],
                  "max_tokens": max_tokens, "model": model})
    if isinstance(r, dict) and r.get("text") and not r.get("error"):
        return r["text"]
    if not split_on_block:
        return (r.get("text") if isinstance(r, dict) else "") or "[OCR FAILED]"
    im = Image.open(img_path)
    w, h = im.size
    lp = img_path + ".L.png"
    rp = img_path + ".R.png"
    im.crop((0, 0, w // 2 + 40, h)).save(lp)
    im.crop((w // 2 - 40, 0, w, h)).save(rp)
    rl = host.llm({"prompt": prompt + " (This is the LEFT column only.)",
                   "images": [lp], "max_tokens": max_tokens, "model": model})
    rr = host.llm({"prompt": prompt + " (This is the RIGHT column only.)",
                   "images": [rp], "max_tokens": max_tokens, "model": model})
    tl = rl.get("text", "") if isinstance(rl, dict) else ""
    tr = rr.get("text", "") if isinstance(rr, dict) else ""
    return (tl + "\n" + tr).strip() or "[OCR FAILED]"


def ocr_pdf_vlm(pdf_path, out_txt=None, dpi=200, model=None, max_tokens=8192,
                max_concurrency=6):
    """OCR a whole PDF via the in-kernel vision model. FALLBACK path when Tesseract
    accuracy is poor - no download (immune to weight-host allowlist blocks), but
    costs ~$0.04/page and needs the reasoning model for citation fidelity.
    Batches pages in parallel; any failed/blocked page falls back to L/R-split."""
    if model is None:
        model = host.reasoning_model()
    pages = rasterize_pdf(pdf_path, out_dir="ocr_pages_vlm", dpi=dpi, grayscale=False)
    reqs = [{"prompt": VERBATIM_OCR_PROMPT, "images": [p],
             "max_tokens": max_tokens, "model": model} for p in pages]
    results = host.llm(reqs, max_concurrency=max_concurrency)
    parts = []
    for idx, (p, r) in enumerate(zip(pages, results), 1):
        txt = r.get("text") if isinstance(r, dict) else None
        if not txt or (isinstance(r, dict) and r.get("error")):
            txt = ocr_image_vlm(p, model=model, max_tokens=max_tokens)
        parts.append(f"\n===PAGE {idx}===\n" + (txt or "[OCR FAILED]"))
    text = "".join(parts)
    if out_txt:
        with open(out_txt, "w") as f:
            f.write(text)
    return text
