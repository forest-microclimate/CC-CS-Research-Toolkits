---
name: folio-science
description: Invoke WHEN rendering a formatted DOCUMENT (Markdown → PDF or docx) or a text-defined DIAGRAM (Mermaid, Graphviz/dot, PlantUML, D2) into an artifact inside the Claude Science sandbox. Ships verified render paths — pandoc+typst for documents (offline, no LaTeX/browser) and Kroki HTTP for diagrams (needs a kroki.io network grant) — plus a blank-page/tofu QA gate. Kernel helpers auto-load: render_doc, kroki_render, qa_pdf, qa_raster. Use when a deliverable must leave the sandbox as a polished PDF/docx or a rendered diagram image.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# folio-science — render documents & diagrams IN the sandbox

Two verified paths, both empirically confirmed on macOS/osx-arm64 (2026-07). Local-browser Mermaid (mermaid-cli/Puppeteer, Playwright) does NOT work here — Chrome-for-Testing crash-loops — so Mermaid goes through Kroki HTTP, and everything else renders natively without a browser.

The `render-docs` conda env backs this skill: `pandoc typst graphviz librsvg pypdfium2 pillow` (all conda-forge, osx-arm64). Create once if absent:
`manage_environments(mode="create", name="render-docs", channels=["conda-forge"], python_version="3.13", packages=["pandoc","typst","graphviz","librsvg","pypdfium2","pillow"])`
Run all render/QA code with `environment="render-docs"`.

## Kernel helpers (auto-loaded from kernel.py)
- `render_doc(md_path, out_path, to=None, pdf_engine="typst", extra_args=None)` → out_path. `.pdf` uses typst (broad Unicode, no LaTeX); `.docx` uses pandoc's native writer. Glyph/font warnings land on `render_doc.last_stderr`.
- `kroki_render(source, diagram_type="mermaid", fmt="svg", out_path=None, background=None)` → bytes. Diagram text → SVG/PNG/PDF via kroki.io. Pass `background="white"` for a PNG destined for a white document (see the transparency note below).
- `flatten_white(src, dst=None)` → path. Composite an already-saved transparent PNG onto white (in place if `dst` is None).
- `qa_pdf(pdf_path)` → `{pages, mean_px, ink_frac, nonblank, bytes}`. `nonblank=False` ⇒ the render silently made an empty page.
- `qa_raster(bytes_or_path)` → `{width, height, ink_frac, ok}`. Validates a rendered PNG; composites transparency onto white so a clear background isn't miscounted as ink.

## Mermaid transparency (load-bearing for embedding)
Kroki's **mermaid PNG has a TRANSPARENT background**. Two consequences WHEN embedding it in a document:
- Naive `.convert("RGB")` turns transparency BLACK — the figure renders as a black box.
- Over a white PDF/docx page the transparency is invisible but any page tint shows through.
Fix (baked in): `kroki_render(src, "mermaid", "png", out, background="white")`, or `flatten_white(path)` on an already-saved PNG. Empirically, a white-flattened Kroki PNG reproduces a local `mermaid-cli` (mmdc) render of the same source at ~0.99 low-frequency structural correlation and <1% aspect-ratio difference — i.e. visually equivalent. SVG has no transparency issue but stores Mermaid labels in `<foreignObject>` (see below), so PNG is the reliable embed format.

## Path 1 — DOCUMENT (Markdown → PDF / docx), fully offline
```python
render_doc("report.md", "report.pdf")          # typst engine
q = qa_pdf("report.pdf"); assert q["nonblank"], q   # blank-page gate BEFORE shipping
render_doc("report.md", "report.docx")
```
Then `save_artifacts(["report.pdf","report.docx"], language="python", environment="render-docs")`.
- typst covers the machine-doc glyph set with zero warnings (⇒ ≤ ∥ ⊂ σ² τ ψ ± × — “ ” and accented Latin). It replaces the LaTeX toolchain — no xelatex needed.
- WHEN you need LaTeX-specific packages ⇒ that path differs (install a TeX engine); typst is the default because it needs no TeX.
- docx Unicode is stored correctly; on-screen fidelity in Word/LibreOffice depends on the READER's fonts, not this step.

## Path 2 — DIAGRAM (Mermaid/Graphviz/PlantUML/D2)
Kroki is an HTTP service — one-time grant first:
`request_network_access(domain="kroki.io", reason="render diagrams to SVG/PNG/PDF")`
```python
svg = kroki_render(mermaid_src, "mermaid", "svg", "flow.svg")
png = kroki_render(mermaid_src, "mermaid", "png", "flow.png")
assert qa_raster(png)["ok"]
```
- Format support: mermaid ⇒ svg/png ONLY (pdf → HTTP 400, a Kroki-backend limit, not a sandbox one). graphviz ⇒ svg/png/pdf.
- **Cloudflare-UA gotcha (baked into the helper):** kroki.io sits behind Cloudflare, which 403s the stdlib `Python-urllib/*` User-Agent with body `error code: 1010`. `kroki_render` sends a plain non-urllib UA and passes — no browser-UA spoofing. WHEN a bare urllib call to kroki 403s ⇒ it is the UA, not the allowlist.
- Graphviz-native, no service: in `render-docs`, `dot -Tpng g.dot -o g.png` renders offline without a browser — prefer this over Kroki when the diagram is Graphviz and confidentiality or offline reproducibility matters.

## Choosing a path
- Document (PDF/docx) ⇒ Path 1 — offline, zero network approvals, adopt as default.
- Graphviz diagram, confidential or offline ⇒ native `dot` in render-docs (no service).
- Mermaid / PlantUML / D2, non-confidential ⇒ Path 2 (Kroki). ~0.4–2 s/diagram, one network grant.
- Confidential diagrams OR offline reproducibility OR high batch volume ⇒ do NOT use hosted Kroki: self-host it (docker `yuzutech/kroki`) on a host/remote-compute target with Docker — this sandbox has no Docker/node/chromium.

## Privacy (load-bearing)
`kroki_render` POSTs the diagram SOURCE TEXT to a public third-party service (kroki.io). WHEN the diagram content is confidential ⇒ use native `dot` (Graphviz) or a self-hosted Kroki, never the public instance.

## Provenance
Reworked from the Claude-Code `folio` skill (macOS/MacTeX render pipeline). The OS-specific machinery (TinyTeX glyph-drop, brew casks, `/Library/TeX` paths) was dropped; the atom-preserving machine→human translation idea lives in `machine-md` + `writing-science`. This skill is the Science-native RENDER backbone those pair with.
