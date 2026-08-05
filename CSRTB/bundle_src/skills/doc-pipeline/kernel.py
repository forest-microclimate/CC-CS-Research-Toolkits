# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""doc-pipeline kernel — orchestrate author -> translate -> render with fail-closed gates.

ARCHITECTURE: full A (authoring) built on a reusable B-core (translate->render).
  mode="author" (A): spec string        -> author machine-md -> [gate1] -> translate -> [gate2] -> render -> [gate3] -> [gate4]
  mode="render" (B): path to .machine.md ->            (trusted source)  -> translate -> [gate2] -> render -> [gate3] -> [gate4]

GATES (see SKILL.md for who-checks-what):
  gate1 form         : review_machine_md()  — LLM machine-writing-quality (author mode only; render-mode source is already authoritative)
  gate2 faithfulness : atom_diff() mechanical + faithfulness_review() LLM   — fail-closed, with one repair attempt
  gate3 render       : qa_pdf() nonblank/tofu — fail-closed
  gate4 prose        : qc_prose() via writing-science scan_draft — advisory; the HUMAN reads the rendered output here

DEPENDENCY: folio-science must be loaded in the same session (provides render_doc, qa_pdf).
  writing-science is optional (enables gate4); absent -> gate4 degrades to a light check.
"""
import re, os, datetime

# ----------------------------------------------------------------------------- constants
DOC_CURRENCY_HEADER = "# STATUS: CURRENT"      # doc-currency in-band header (line after title)

SOFT_STOPWORDS = {  # structural machine-md ALL-CAPS that need not survive verbatim into prose
    "WHEN","THEN","ELSE","IF","NOT","AND","OR","DO","USE","ADD","DEF","RULE","WHY","HOW",
    "NOTE","KEY","ALL","ONE","TWO","YES","STATUS","CURRENT","VERIFY","MUST","NEVER","ALWAYS",
}

# hard atoms MUST appear verbatim in the human twin (omission = fabrication risk); order = priority
HARD_ATOM_PATTERNS = [
    (r"`[^`\n]+`",                                   "code"),      # `render_doc`, `--core`
    (r"(?<!\w)--[A-Za-z][\w-]*",                     "flag"),      # --core, --dry-run (long CLI flags; high-precision)
    (r"\bT-\d+\b",                                   "taskid"),    # T-08
    (r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b", "uuid"),
    (r"\b[\w./-]+\.(?:md|py|sh|json|tsv|pdf|txt|csv|toml|ya?ml|jl|R)\b", "filename"),
    (r"\b\d+(?:\.\d+)+\b",                           "dotted"),    # 1.2.3 / 0.987
    (r"\b\d+/\d+\b",                                 "ratio"),     # 52/52
    (r"\b\d{2,}(?:[eE][+-]?\d+)?\b",                 "number"),    # 1361, 108070  (multi-digit only)
]

# ----------------------------------------------------------------------------- atom gate (mechanical)
def extract_atoms(text):
    """Return {'hard': {atom: kind}, 'soft': set}. hard=must-survive-verbatim; soft=ALL-CAPS domain terms (advisory)."""
    hard = {}
    for pat, kind in HARD_ATOM_PATTERNS:
        for m in re.findall(pat, text):
            a = m.strip("`").strip() if kind == "code" else m
            if a and a not in hard:
                hard[a] = kind
    # De-dup: a bare 'number' atom that is a substring of a richer atom (0.987 -> 987,
    # 52/52 -> 52, T-08 -> 08) is NOT independent — drop it so the missing-report lists each drop once.
    richer = [a for a, k in hard.items() if k != "number"]
    for a, k in list(hard.items()):
        if k == "number" and any(a in r and a != r for r in richer):
            del hard[a]
    soft = {s for s in re.findall(r"\b[A-Z][A-Z0-9_]{2,}\b", text) if s not in SOFT_STOPWORDS}
    return {"hard": hard, "soft": soft}

def atom_diff(machine_md, human_md):
    """Fail-closed faithfulness gate: every HARD atom in the source must appear in the human twin.
    Returns {ok, missing_hard:[{atom,kind}], missing_soft:[...], n_hard, n_soft, coverage_hard}."""
    src = extract_atoms(machine_md)
    hay = human_md.lower()
    missing_hard = [{"atom": a, "kind": k} for a, k in src["hard"].items() if a.lower() not in hay]
    missing_soft = sorted(s for s in src["soft"] if s.lower() not in hay)
    n_hard = len(src["hard"])
    return {"ok": len(missing_hard) == 0,
            "missing_hard": missing_hard, "missing_soft": missing_soft,
            "n_hard": n_hard, "n_soft": len(src["soft"]),
            "coverage_hard": (1.0 if n_hard == 0 else round((n_hard - len(missing_hard)) / n_hard, 3))}

# ----------------------------------------------------------------------------- LLM helpers
def resolve_model(m=None):
    return m or host.reasoning_model()

def structured_verdict(prompt, schema_props, required, *, system, model=None, max_tokens=1500):
    """Force structured output via a tool schema (plain prompts answer conversationally — unreliable)."""
    tool = {"name": "verdict", "input_schema": {"type": "object", "properties": schema_props, "required": required}}
    r = host.llm({"prompt": prompt, "system": system, "tools": [tool],
                  "tool_choice": {"type": "tool", "name": "verdict"},
                  "model": resolve_model(model), "max_tokens": max_tokens})
    tu = r.get("tool_use") or {}
    return tu.get("input", {}) or {}

# ----------------------------------------------------------------------------- stage 1 (A): author
def author_machine_md(spec, *, model=None, extra_guidance=""):
    """Stage 1 (A only): generate a .machine.md from a document request/spec, per machine-md conventions."""
    system = (
        "You author 'machine-md' documents whose PRIMARY READER is an LLM, not a human. Apply "
        "machine-md best practice: terse machine style, positive trigger-conditioned framing "
        "(WHEN (condition) => (action)), output-detectable triggers, brief concrete examples, "
        "high atom-density (name specific identifiers, numbers, files, thresholds), no filler prose. "
        "Wrap every code-like token in backticks — command-line flags (`--core`), commands, "
        "filenames, function names, identifiers, config keys — so they are unambiguous atoms. "
        "First two lines: a '# <TITLE>' heading, then the literal line '# STATUS: CURRENT'. "
        "Use clear headings. The document must be COMPLETE and self-contained for its stated purpose. "
        "Output ONLY the machine-md document body, no preamble.")
    prompt = f"{extra_guidance}\n\nDOCUMENT REQUEST / SPEC:\n{spec}\n\nWrite the machine-md document now."
    return host.llm(prompt, system=system, model=resolve_model(model), max_tokens=8000).get("text", "")

def review_machine_md(machine_md, *, model=None):
    """Gate 1 (author mode): LLM machine-writing-quality review (LLM_DOC_ARCHITECT-style rubric)."""
    system = ("You audit machine-md (LLM-facing) documents for FORM quality only. Judge: terse machine "
              "style (not human prose); trigger-conditioned + output-detectable; atom-density; a "
              "'# STATUS:' currency header present; self-contained. You are the fluent machine-doc reader "
              "the human is not.")
    props = {"passes": {"type": "boolean", "description": "true if machine-writing quality is acceptable"},
             "issues": {"type": "array", "items": {"type": "string"}, "description": "concrete form defects, empty if none"},
             "has_status_header": {"type": "boolean"}}
    return structured_verdict(f"MACHINE-MD:\n\n{machine_md}\n\nAudit its FORM.", props,
                        ["passes", "issues", "has_status_header"], system=system, model=model)

# ----------------------------------------------------------------------------- stage 2 (B-core): translate + faithfulness
def translate_machine_to_human(machine_md, *, model=None, missing_atoms=None):
    """Stage 2: rewrite machine-md -> human-readable Markdown. Preserves every atom, adds prose."""
    system = (
        "You translate LLM-facing 'machine-md' into human-readable Markdown for a general reader. "
        "Machine-md is terse, atom-dense, trigger-conditioned (WHEN/THEN), abbreviation-heavy. Your output MUST: "
        "(1) preserve EVERY atom — each identifier, number, filename, id, task-id, threshold, and named term "
        "appears, expanded not dropped; (2) add prose connective tissue so it reads as flowing explanation; "
        "(3) expand each abbreviation on first use; (4) turn trigger notation into readable conditional sentences; "
        "(5) NEVER introduce a claim, number, or entity absent from the source. Keep the heading structure. "
        "Do not editorialize. Output ONLY the Markdown translation.")
    repair = ""
    if missing_atoms:
        repair = ("\n\nPRIOR ATTEMPT DROPPED these required atoms — you MUST include every one, verbatim, "
                  "in this translation: " + ", ".join(f"`{a}`" for a in missing_atoms))
    prompt = f"MACHINE-MD SOURCE:\n\n{machine_md}{repair}\n\nWrite the human-readable Markdown translation now."
    return host.llm(prompt, system=system, model=resolve_model(model), max_tokens=16000).get("text", "")

def faithfulness_review(machine_md, human_md, *, model=None):
    """Gate 2 (LLM half): does the human twin FABRICATE anything not supported by the source?"""
    system = ("You check a human-readable translation against its machine-md source for FAITHFULNESS. "
              "Flag ONLY fabrications: any claim, number, entity, or relationship in the translation that "
              "is NOT supported by the source. Do not flag stylistic expansion or added connective prose.")
    props = {"faithful": {"type": "boolean", "description": "true if no fabrications"},
             "fabrications": {"type": "array", "items": {"type": "string"}, "description": "unsupported additions, empty if none"}}
    return structured_verdict(f"SOURCE:\n\n{machine_md}\n\n---\nTRANSLATION:\n\n{human_md}\n\nCheck faithfulness.",
                        props, ["faithful", "fabrications"], system=system, model=model, max_tokens=2000)

# ----------------------------------------------------------------------------- stage 4: prose QC (advisory)
def qc_prose(human_md):
    """Gate 4 (advisory): prose diagnostics via writing-science scan_draft if loaded; else a light check."""
    if "scan_draft" in globals():
        try:
            res = globals()["scan_draft"](human_md)                      # noqa
            counts = res.get("counts", res) if isinstance(res, dict) else {}
            top = sorted(((k, v) for k, v in counts.items() if isinstance(v, int) and v),
                         key=lambda kv: -kv[1])[:6]
            return {"available": True, "top_flags": top}
        except Exception as e:
            return {"available": True, "error": f"{type(e).__name__}: {e}"}
    words = human_md.split()
    sents = [s for s in re.split(r"[.!?]\s", human_md) if s.strip()]
    return {"available": False, "words": len(words),
            "mean_sentence_words": round(len(words) / max(1, len(sents)), 1)}

# ----------------------------------------------------------------------------- orchestration
def require_render_backend():
    for name in ("render_doc", "qa_pdf"):
        if name not in globals():
            raise RuntimeError(f"doc-pipeline needs folio-science loaded ('{name}' missing). "
                               f"Load folio-science in this session, then retry.")

def run_doc_pipeline(source, *, mode="author", out_stem="document", workdir=".",
                     model=None, extra_guidance="", repair_attempts=1,
                     render_docx=False):
    """Run the pipeline. Returns a report dict with artifact paths + per-gate results.

    mode="author": `source` is a spec string.  mode="render": `source` is a path to a .machine.md.
    Fail-closed: gate2/gate3 failures are surfaced (ok=False), never silently passed. The caller
    (per SKILL.md) presents the rendered output + report to the HUMAN for the final gate-4 blessing.
    """
    require_render_backend()
    os.makedirs(workdir, exist_ok=True)
    rep = {"mode": mode, "out_stem": out_stem, "when": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "gates": {}, "artifacts": {}, "ok": True}

    # ---- obtain the machine-md source ----
    if mode == "author":
        machine_md = author_machine_md(source, model=model, extra_guidance=extra_guidance)
        rep["gates"]["gate1_form"] = g1 = review_machine_md(machine_md, model=model)
        if not g1.get("passes", False):
            rep["ok"] = False
    elif mode == "render":
        with open(source, encoding="utf-8") as fh:
            machine_md = fh.read()
        rep["gates"]["gate1_form"] = {"skipped": "render mode: source is authoritative"}
    else:
        raise ValueError("mode must be 'author' or 'render'")
    mpath = os.path.join(workdir, out_stem + ".machine.md")
    if mode == "author":                      # never rewrite a user-supplied authoritative source
        with open(mpath, "w", encoding="utf-8") as fh:
            fh.write(machine_md)
        rep["artifacts"]["machine_md"] = mpath
    else:
        rep["artifacts"]["machine_md"] = os.path.abspath(source)

    # ---- stage 2: translate + faithfulness gate (with repair loop) ----
    missing = None
    for attempt in range(repair_attempts + 1):
        human_md = translate_machine_to_human(machine_md, model=model, missing_atoms=missing)
        ad = atom_diff(machine_md, human_md)
        if ad["ok"] or attempt == repair_attempts:
            break
        missing = [m["atom"] for m in ad["missing_hard"]]      # feed drops back for a repair pass
    fr = faithfulness_review(machine_md, human_md, model=model)
    rep["gates"]["gate2_faithfulness"] = {"atom_diff": ad, "llm_review": fr, "repair_passes": attempt}
    if not ad["ok"] or not fr.get("faithful", True):
        rep["ok"] = False
    hpath = os.path.join(workdir, out_stem + ".md")
    with open(hpath, "w", encoding="utf-8") as fh:
        fh.write(human_md)
    rep["artifacts"]["human_md"] = hpath

    # ---- stage 3: render + blank-page gate ----
    ppath = os.path.join(workdir, out_stem + ".pdf")
    globals()["render_doc"](hpath, ppath)
    q = globals()["qa_pdf"](ppath)
    rep["gates"]["gate3_render"] = q
    rep["artifacts"]["pdf"] = ppath
    if not q.get("nonblank", False):
        rep["ok"] = False
    if render_docx:
        dpath = os.path.join(workdir, out_stem + ".docx")
        globals()["render_doc"](hpath, dpath)
        rep["artifacts"]["docx"] = dpath

    # ---- stage 4: prose QC (advisory; the human reads the PDF here) ----
    rep["gates"]["gate4_prose"] = qc_prose(human_md)
    return rep
