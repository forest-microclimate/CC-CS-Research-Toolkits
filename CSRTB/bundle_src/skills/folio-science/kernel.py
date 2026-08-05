# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""folio-science kernel helpers — render diagrams + documents inside the Claude Science sandbox.

Two verified paths (see SKILL.md):
  * kroki_render()  — Mermaid/Graphviz/PlantUML/etc. via the Kroki HTTP service
                      (needs a one-time request_network_access('kroki.io')).
  * render_doc()    — Markdown -> PDF (typst) / docx (pandoc native), no browser/LaTeX.
  * qa_pdf()        — page-count + blank-page gate (pypdfium2 + PIL, no numpy).

All run in the `render-docs` conda env (pandoc + typst + graphviz + pypdfium2 + pillow).
Third-party imports are deferred into function bodies so this file loads on any kernel.
"""

import os
import subprocess

KROKI_URL = "https://kroki.io"
KROKI_UA = "folio-science/1.0 (diagram render)"  # any non-'Python-urllib' UA passes Cloudflare 1010


def kroki_render(source, diagram_type="mermaid", fmt="svg", out_path=None,
                 timeout=60, background=None):
    """Render diagram `source` text to bytes via Kroki HTTP (POST). Writes to out_path if given.

    diagram_type: mermaid | graphviz | plantuml | d2 | ... ; fmt: svg | png | pdf
    NOTE mermaid supports svg/png only (pdf -> HTTP 400); graphviz supports svg/png/pdf.
    background="white" (PNG only): flatten the transparent Kroki background onto solid
      white BEFORE returning/writing. Kroki's mermaid PNG has a TRANSPARENT background;
      embedding it as-is over a dark or non-white page shows through, and naive RGB
      conversion turns transparency BLACK. Pass background="white" whenever the image
      goes into a white document (the usual case) so it matches a local mmdc render.
    Requires a prior request_network_access('kroki.io'). Sends source to a public
    third-party service — do NOT use for confidential content (self-host Kroki instead).
    """
    import urllib.request
    url = f"{KROKI_URL}/{diagram_type}/{fmt}"
    req = urllib.request.Request(
        url, data=source.encode("utf-8"),
        headers={"Content-Type": "text/plain", "User-Agent": KROKI_UA},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if background == "white" and fmt == "png":
        import io
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        flat = Image.alpha_composite(bg, im).convert("RGB")
        buf = io.BytesIO(); flat.save(buf, format="PNG"); data = buf.getvalue()
    if out_path:
        with open(out_path, "wb") as f:
            f.write(data)
    return data


def flatten_white(src, dst=None):
    """Composite a transparent PNG onto solid white; overwrite in place if dst is None.

    Use on any already-saved Kroki PNG before embedding it in a white document — the
    same fix kroki_render(..., background='white') applies at render time.
    """
    from PIL import Image
    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):
        rgba = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, rgba)
    out = dst or src
    im.convert("RGB").save(out)
    return out


def render_doc(md_path, out_path, to=None, pdf_engine="typst", extra_args=None):
    """Render a Markdown file to PDF or docx via pandoc. Returns out_path.

    to: 'pdf' | 'docx' (inferred from out_path extension if None).
    PDF uses --pdf-engine=typst (broad Unicode, no LaTeX). docx uses pandoc's native writer.
    Run in the `render-docs` env (pandoc + typst on PATH). Raises CalledProcessError with
    .stderr on failure (glyph/font warnings also land on stderr).
    """
    if to is None:
        to = os.path.splitext(out_path)[1].lstrip(".").lower()
    cmd = ["pandoc", md_path, "-o", out_path]
    if to == "pdf":
        cmd += ["--pdf-engine=" + pdf_engine]
    if extra_args:
        cmd += list(extra_args)
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    render_doc.last_stderr = proc.stderr  # glyph warnings, if any
    return out_path


def qa_pdf(pdf_path, dpi=144, min_ink=0.0008):
    """QA gate: return {pages, mean_px, ink_frac, nonblank, bytes}.

    Rasterizes page 1 and flags a truly blank page (mean_px==255, ink==0). A real page
    has ink_frac > min_ink. Uses pypdfium2 + PIL only (no numpy). `nonblank` False => the
    render silently produced an empty page — investigate before shipping.
    """
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(pdf_path)
    n = len(pdf)
    img = pdf[0].render(scale=dpi / 72.0).to_pil().convert("L")
    hist = img.histogram()
    total = sum(hist) or 1
    mean_px = sum(i * c for i, c in enumerate(hist)) / total
    ink = sum(hist[:250]) / total
    return {"pages": n, "mean_px": round(mean_px, 2), "ink_frac": round(ink, 4),
            "nonblank": ink > min_ink, "bytes": os.path.getsize(pdf_path)}


def qa_raster(source_bytes_or_path, min_ink=0.0008):
    """QA gate for a rendered PNG (e.g. from kroki_render fmt='png'): valid, non-empty, has ink."""
    import io
    from PIL import Image
    if isinstance(source_bytes_or_path, (bytes, bytearray)):
        img = Image.open(io.BytesIO(source_bytes_or_path))
    else:
        img = Image.open(source_bytes_or_path)
    img.load()
    w, h = img.size
    # composite onto white so a transparent background doesn't read as "ink" (black in L mode)
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, rgba)
    g = img.convert("L")
    hist = g.histogram(); total = sum(hist) or 1
    ink = sum(hist[:250]) / total
    return {"width": w, "height": h, "ink_frac": round(ink, 4),
            "ok": w > 10 and h > 10 and ink > min_ink}
