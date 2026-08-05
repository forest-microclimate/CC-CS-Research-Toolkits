#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""sci_file_index.py — catalog a folder of scientific literature into a metadata index.

Generalized, parameterized reference impl for the sci-file-index skill / sci-file-indexer agent.
Pure python3 stdlib (+ poppler CLI tools for PDF text; optional ocrmypdf/tesseract for scans).
Portable macOS + Linux. NEVER fabricates metadata: unresolved => blank field + note + low confidence.

Pipeline (3 artifacts; artifact names start `_sfi_` so they self-exclude from the index):
  extract  (PROC.1+2) : scan/classify --dir, text-layer extract  -> _sfi_raw.csv
  build    (PROC.3/4/7/8/9): merge raw + overrides -> INDEX; cryptic->DOI, supplement-link, dedupe,
                              confidence tiers, delta+confidence+residual report
  resolve  (PROC.4/6) : weak-row funnel: derive DOI (pattern table) or gated CrossRef title-search
                        -> _sfi_review.tsv  (REVIEW surface; not auto-applied)
  ocr      (PROC.5)   : OCR scanned/image-only PDFs to sidecars _ocr/, mine page-1 -> _sfi_review.tsv
  apply    (PROC.8)   : append reviewed _sfi_review.tsv rows to the overrides layer (dedup by file_name)

Overrides layer (the ONLY hand-edit surface; 8 TAB cols, `#` header, LAST-WINS):
  file_name<TAB>author<TAB>year<TAB>title<TAB>journal<TAB>record_type<TAB>parent<TAB>note
Index columns (build product; hand-edits are clobbered on rebuild):
  file_name, record_type, first_author, year, title, journal, doi, parent_file, duplicate_of, confidence, notes
"""
import argparse, csv, difflib, json, os, re, shutil, subprocess, sys, time, unicodedata, urllib.parse, urllib.request, tempfile

# --- shared identity primitives (single source of truth: sci_lib_common.py;
#     built from the canonical module — NEVER hand-edit a shipped copy). The indexer carries
#     the block for sci_lib_common sync-gate compliance and keeps its OWN indexer-specific
#     _tokens, _alnum_component, _camel_words, _journal_abbrev, compute_canonical_stem, _asciify
#     (defined later, which shadow the generic ones for names the indexer specializes). ---
# ==== BEGIN GENERATED sci_lib_common v5 sha=f004f407 -- DO NOT EDIT; edit sci_lib_common.py + rebuild ====
__version__ = "5"
import unicodedata, re, os, tempfile, csv

_JSTOP = {"of","and","the","for","in","on","a","an","de","der","und","et","la","le","to","with","from"}

# ---------------------------------------------------------------- asciify
_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"          # hyphen, NB-hyphen, figure/en/em dash, minus
_SPECIAL_LETTERS = str.maketrans({
    "ø":"o","Ø":"O","đ":"d","Đ":"D","ð":"d","Ð":"D","þ":"th","Þ":"Th",
    "ł":"l","Ł":"L","ß":"ss","æ":"ae","Æ":"AE","œ":"oe","Œ":"OE","ı":"i","ŋ":"ng",
})

def asciify(s):
    """Deterministic fold to pure ASCII, filesystem-safe. Three stages so nothing is silently
    fused or dropped: (1) map non-combining special letters NFKD misses (ø->o, ß->ss, Ł->L,
    æ->ae); (2) unify every Unicode dash glyph to ASCII '-' (a bare encode('ascii','ignore')
    DELETES U+2010/en/em dashes, fusing 'Aguirre‐Gutierrez'->'AguirreGutierrez' and
    'Plant–archaea'->'Plantarchaea'); (3) NFKD-fold, drop combining marks, drop any remaining
    non-ASCII. 'Büker'->'Buker', 'Kiørboe'->'Kiorboe', 'Weißbecker'->'Weissbecker'."""
    if not s:
        return ""
    s = str(s).translate(_SPECIAL_LETTERS)
    s = re.sub("[" + _DASHES + "]", "-", s)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).encode("ascii", "ignore").decode("ascii")

# ---------------------------------------------------------------- family_name
def _tokens(s):
    return [t for t in re.split(r"\s+", s.strip()) if t]

# A name token = one or more Capitalized-or-ALLCAPS segments joined by hyphen/apostrophe
# (compound surnames: Aguirre-Gutierrez, Benlloch-Gonzalez, O'Brien). Tested AFTER asciify.
_NAME_SEG = r"(?:[A-Z][a-zA-Z'.]*|[A-Z]{2,})"   # allow internal caps: McAdam, DeLong, StPaul
_NAME_TOK = re.compile(r"^" + _NAME_SEG + r"(?:['-]" + _NAME_SEG + r")*$")

# Surname particles (nobiliary / patronymic prefixes). SPACE-separated => dropped from the filename
# token (legacy corpus convention: "van Breugel" -> Breugel) but always recorded in name_features.
# A HYPHEN-bound particle is NEVER dropped (Del-Saz, El-Naggar are whole surnames).
_PARTICLES = {"van","von","der","den","de","del","della","di","da","dos","das","du",
              "la","le","el","al","bin","ibn","ter","ten"}

def _surname_string(author):
    """FIRST author's surname STRING, preserving internal space + hyphen (pre-render), so compound
    surnames ('Lombo Sanchez') survive. Comma-form => full pre-comma surname; bare two-word
    no-initial => both words; particle-led no-comma => legacy last token (+ a directly-preceding
    particle, van Breugel)."""
    s = str(author or "").strip()
    if not s:
        return ""
    s = re.sub("[" + _DASHES + "]", "-", s)                    # unify all dash glyphs to ASCII '-'
    s = re.sub(r"\bet al\.?\b", "", s, flags=re.I).strip(" .,")
    sep = re.search(r"\s+(and|&)\s+|;", s)
    comma = s.find(",")
    if comma != -1 and (sep is None or comma < sep.start()):
        return s.split(",")[0].strip()                         # comma-form: full pre-comma surname
    first = re.split(r"\s+(?:and|&)\s+|;", s)[0].strip()
    toks = [t for t in _tokens(first) if _NAME_TOK.match(asciify(t))]
    if not toks:
        # never blank a real surname: fall back to the last raw word (strip trailing junk like '*')
        raw = _tokens(first)
        return re.sub(r"[^A-Za-z'\- ]", "", raw[-1]).strip() if raw else ""
    has_initial = any(len(t.rstrip(".")) == 1 for t in toks)
    if has_initial or len(toks) == 1:
        return toks[-1]
    lower = [t.lower() for t in toks]
    if len(toks) == 2 and lower[0] not in _PARTICLES:
        return " ".join(toks)                                  # bare compound: Lombo Sanchez
    if len(toks) >= 2 and lower[-2] in _PARTICLES:
        return " ".join(toks[-2:])                             # van Breugel
    return toks[-1]

def _has_only_particles(surname_str):
    ws = [w.lower() for w in re.split(r"[ \-]+", (surname_str or "").strip()) if w]
    return bool(ws) and all(w in _PARTICLES for w in ws)

def _titlecase_seg(a):
    """Title-case a name segment, STRIPPING apostrophe (filename convention: O'Brien -> OBrien;
    every existing clean_name has 0 apostrophes). Preserves a meaningful INTERNAL capital
    (McAdam, DeJonge, MacLeod, StPaul) — only ALLCAPS or all-lowercase segments are re-cased."""
    out = []
    for p in a.split("'"):
        if not p:
            continue
        if p.isupper() or p.islower():
            out.append(p[:1].upper() + p[1:].lower())   # ARAUJO->Araujo, smith->Smith
        else:
            out.append(p[:1].upper() + p[1:])           # McAdam/DeJonge -> keep internal caps
    return "".join(out)

def _render_surname(surname_str, drop_particles=True):
    """(filename_token, sep_kind). Hyphen kept, apostrophe stripped, each non-particle word
    Title-cased and words joined by '-'. A particle is dropped ONLY when SPACE-separated
    (van Breugel -> Breugel), NEVER when hyphen-bound (Del-Saz stays whole). sep_kind in
    {'hyphen','space','NA'} records the original join glyph of a multi-word surname (the reversal
    key: the filename hyphen-joins both, so Lombo-Sanchez alone is ambiguous)."""
    if not surname_str:
        return "", ""
    had_space = " " in surname_str
    had_hyphen = "-" in surname_str
    kept, n_seg = [], 0
    only_particles = _has_only_particles(surname_str)
    for w in surname_str.strip().split():
        if w.lower() in _PARTICLES and drop_particles and not only_particles:
            continue                                           # drop only SPACE-separated particles
        rendered = []
        for s in w.split("-"):                                 # hyphen-bound segments stay atomic
            a = re.sub(r"[^A-Za-z']", "", asciify(s))
            if a:
                rendered.append(_titlecase_seg(a)); n_seg += 1
        if rendered:
            kept.append("-".join(rendered))
    token = "-".join(kept)
    if n_seg <= 1:
        sep = "NA"
    elif had_hyphen and not had_space:
        sep = "hyphen"
    else:
        sep = "space"                                          # space, or mixed -> space dominates
    return token, sep

def family_name(author):
    """FIRST author's family name as a filesystem-safe token. Handles 'Surname, F.' / 'F. Surname'
    / 'A and B' / 'et al.', DIACRITIC-, COMPOUND-, and PARTICLE-safe. Hyphen preserved
    (Aguirre-Gutierrez), spaced compound hyphen-joined (Lombo Sanchez -> Lombo-Sanchez), apostrophe
    stripped (O'Brien -> OBrien), diacritics folded (Büker -> Buker), space-separated particle
    dropped (van Breugel -> Breugel). The ORIGINAL (accents, particles, original hyphen) lives
    verbatim in first_author; surname_sep() records the original join glyph."""
    return _render_surname(_surname_string(author))[0]

def surname_sep(author):
    """Reversal key for a compound surname's filename token: 'hyphen' | 'space' | 'NA'. Given token
    'Lombo-Sanchez' you cannot tell if the original was hyphen or space; this preserves it.
    Re-derived from first_author; kept honest by validator invariant."""
    return _render_surname(_surname_string(author))[1]

def name_features(author):
    """Compact greppable tag of what is non-plain about the ORIGINAL first_author ('' = plain):
    'diacritic', 'special-letter', 'particle=van', 'apostrophe', 'compound-space', 'compound-hyphen'
    (';'-joined). Re-derived from first_author; kept honest by validator invariant."""
    s = str(author or "").strip()
    if not s:
        return ""
    feats = []
    if any(unicodedata.combining(ch) for ch in unicodedata.normalize("NFD", s)):
        feats.append("diacritic")
    if re.search(r"[\u00f8\u00d8\u0111\u0110\u00f0\u00d0\u00fe\u00de\u0142\u0141\u00df\u00e6\u00c6\u0153\u0152\u0131\u014b]", s):
        feats.append("special-letter")
    ss = _surname_string(s)
    parts = [x.lower() for x in re.split(r"[ \-]+", ss.strip()) if x]
    prt = [p for p in parts if p in _PARTICLES]
    if prt:
        feats.append("particle=" + "|".join(prt))
    if "'" in s or "\u2019" in s:
        feats.append("apostrophe")
    if " " in ss.strip() and not prt:
        feats.append("compound-space")
    if "-" in ss or any(ch in s for ch in _DASHES):
        feats.append("compound-hyphen")
    return ";".join(feats)


# ---------------------------------------------------------------- author list (co-author display)
def format_author(family, given):
    """One author rendered as the canonical display string `Family, G.I.` per the shared spec.

      family="Aguiar-Campos", given="Rodrigo"      -> "Aguiar-Campos, R."
      family="van der Meer",   given="Jan Willem"  -> "van der Meer, J.W."
      family="CSIRO",          given=""            -> "CSIRO"        (corporate/single-entity)
      family="Smith",          given=None          -> "Smith"        (given missing -> family alone)

    The FAMILY is preserved VERBATIM (only stripped) — particles, internal spaces, hyphens, and
    diacritics survive ('van der Meer', 'Aguiar-Campos'); this is a DISPLAY string, not the
    filesystem-safe token family_name() produces. Given initials are the first letter of every
    maximal letter-run (unicode-aware), each uppercased + '.', no separating spaces: 'Jean-Paul'
    -> 'J.P.', 'Jan Willem' -> 'J.W.', 'J. W.' -> 'J.W.', 'Rodrigo' -> 'R.'. A given with no
    usable letters (corporate name, or empty) yields the family alone. A blank family yields ''."""
    family = str(family or "").strip()
    given = str(given or "").strip()
    if not family:
        return ""
    segs = re.findall(r"[^\W\d_]+", given, flags=re.UNICODE)   # maximal letter-runs, unicode-aware
    initials = "".join(s[0].upper() + "." for s in segs)
    if not initials:                                            # corporate / single-entity / no given
        return family
    return "%s, %s" % (family, initials)

def abbreviate_authors(ordered):
    """Apply the shared abbreviation rule to an ORDERED list of already-formatted author strings.
    Returns a TUPLE (authors_abbreviated, n_authors, last_author) — n_authors is ALWAYS the true
    count regardless of truncation; last_author is the final name (senior/PI); authors is the
    display string, ALWAYS bounded at <=7 names for any N:

      N == 0           -> ("", 0, "")
      1 <= N <= 7      -> all N names joined by "; ", no omission, no sentinel; last = names[-1]
      N >= 8           -> names[0:4] + [f"[+{N-7} more]"] + names[-3:], joined by "; " (7 names
                          shown, exactly N-7 omitted); the first-4 / last-3 slices are always
                          disjoint (4+3=7 < N) so no name is ever duplicated; last = names[-1]

    Because the display is bounded at 7 for ANY N and n_authors carries the true count, the schema
    can never be breached by a large author list (a 500-author paper renders identically bounded)."""
    ordered = list(ordered)
    n = len(ordered)
    if n == 0:
        return "", 0, ""
    if n <= 7:
        return "; ".join(ordered), n, ordered[-1]
    sentinel = "[+%d more]" % (n - 7)
    shown = ordered[:4] + [sentinel] + ordered[-3:]
    return "; ".join(shown), n, ordered[-1]

# ---------------------------------------------------------------- norm_title
def norm_title(t):
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def real_doi(d):
    """A DOI is real only if it has a '/' AND a suffix (after the last '/') containing a digit.
    Guards defect #3: a truncated DOI like '10.1073/pnas' (registrant only, no article id)
    would otherwise merge every distinct paper from that publisher into one cluster."""
    d = (d or "").strip().lower()          # DOIs are case-insensitive; lowercase for stable keying
    if not d or "/" not in d:
        return ""
    suffix = d.rsplit("/", 1)[1]
    if not any(ch.isdigit() for ch in suffix):
        return ""
    return d

# ---------------------------------------------------------------- camel / journal / canonical_stem
def _camel(text, cap_words=None, drop_stop=False):
    words = [w for w in re.split(r"[^A-Za-z0-9]+", asciify(text)) if w]
    if drop_stop:
        words = [w for w in words if w.lower() not in _JSTOP] or words
    if cap_words:
        words = words[:cap_words]
    return "".join(w[:1].upper() + w[1:] for w in words)

def _alnum_component(s):
    """A single clean alphanumeric stem component (ASCII, no separators)."""
    return re.sub(r"[^A-Za-z0-9]", "", asciify(str(s or "")))

def journal_abbrev(journal):
    """Compact journal signature: first 4 letters of each non-stopword token, capitalized."""
    sig = [w for w in re.split(r"[^A-Za-z0-9]+", asciify(journal)) if w and w.lower() not in _JSTOP]
    return "".join(w[:4].capitalize() for w in sig) if sig else ""

def canonical_stem(row, max_len=180, title_words=9):
    """Build the CURATOR's bundle-folder stem: Author_Year_JournAbbrevTitle. Carries the defect-#41
    guard (a diacritic/hyphen/apostrophe author must NEVER drop to a year-first stem) and the
    matching hard assertion. Never fabricates: falls back to a cleaned original stem, and RAISES
    if a known author is silently lost.

    SCOPE (single-source-of-truth boundary): this fixed-order stem is the CURATOR's scheme only.
    The INDEXER deliberately does NOT use it — it keeps its own template-driven compute_canonical_stem
    (default '{author}_{year}_{journal_abbrev}_{type}_{pages}', config-parameterized) because file
    rename and bundle-folder naming are different schemes by design. Both share only the PRIMITIVES
    below (asciify/family_name/_tokens/_camel/_alnum_component/journal_abbrev/real_doi/norm_title) —
    those are the true single source of truth; do NOT merge the two higher-level stem builders."""
    raw_author = str(row.get("first_author", "")).strip()
    au = family_name(raw_author)                                # already filesystem-safe: hyphen kept,
                                                                # apostrophe stripped, compound joined
    if raw_author and not au:                                   # #41 author-restore fallback chain
        au = family_name(str(row.get("first_author_ascii", "")).strip()) \
             or _camel(re.sub(r"[^A-Za-z0-9\- ]", "", raw_author))
    yr = str(row.get("year", "")).strip()
    jr = journal_abbrev(row.get("journal", ""))
    ti = _camel(row.get("title", ""), cap_words=title_words, drop_stop=True)
    parts = [p for p in (au, yr, jr, ti) if p]
    stem = "_".join(parts)
    stem = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "", stem)
    if not stem:                                                # never-fabricate fallback
        stem = re.sub(r'[/\\:*?"<>|]', "_", os.path.splitext(row.get("file_name", "paper"))[0])[:120]
    if raw_author and re.match(r"^\d{4}(_|$)", stem):           # #41 assert: known author -> never year-first
        raise ValueError("canonical_stem dropped known author %r -> year-first stem %r" % (raw_author, stem))
    return stem[:max_len]

# ---------------------------------------------------------------- blocking_keys (P1 core)
def blocking_keys(row):
    """DOI-AGNOSTIC union blocking. Returns a SET of candidate keys; two rows are candidate
    duplicates if their key-sets INTERSECT. DOI and year CORROBORATE, never GATE.
    Union of three passes:
      (1) folded-author + normalized-title   (primary, year-agnostic, DOI-agnostic)
      (2) same-DOI (inclusion-only)          (adds pairs; never the sole key)
      (3) title-only                          (catches mis-mined / blank authors)
    No row is ever unkeyable-and-dropped: a row with a title always gets key (3)."""
    keys = set()
    au = re.sub(r"[^a-z]", "", asciify(str(row.get("first_author", ""))).lower())
    nt = norm_title(row.get("title", ""))
    if au and len(nt) >= 10:
        keys.add("AT::%s|%s" % (au, nt[:40]))          # (1)
    d = real_doi(row.get("doi"))
    if d:
        keys.add("DOI::" + d)                           # (2) inclusion-only
    if len(nt) >= 10:
        keys.add("T::" + nt[:40])                       # (3) title-only
    return keys

# ---------------------------------------------------------------- write_atomic (P0/P3)
def write_atomic(path, write_fn, mode="w", encoding="utf-8", newline=""):
    """Write via a temp file in the same dir, fsync, then os.replace (atomic on POSIX).
    write_fn(file_handle) does the actual writing. A crash leaves the prior file intact."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".part")
    try:
        with os.fdopen(fd, mode, encoding=encoding, newline=newline) as f:
            write_fn(f)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try: os.unlink(tmp)
        except OSError: pass
        raise
# ==== END GENERATED sci_lib_common ====
_asciify = asciify
_family_name = family_name

DOI_RE = re.compile(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+')
RAW_NAME = "_sfi_raw.csv"
OVERRIDES_NAME = "_sfi_overrides.tsv"
REVIEW_NAME = "_sfi_review.tsv"
OVERRIDES_HEADER = "# file_name\tauthor\tyear\ttitle\tjournal\trecord_type\tparent\tnote\n"
INDEX_COLS = ["file_name","record_type","first_author","first_author_ascii","year","title","journal","doi",
              "parent_file","duplicate_of","confidence","notes","pages","content_sim"]
EXCLUDE_ARCHIVE = (".zip",".tar",".gz",".7z",".rar")
SCANNED_CHAR_THRESHOLD = 100      # FACT.scanned_threshold: <100 non-space chars page-1 => scanned
OCR_TITLE_MIN = 8                 # FACT.ocr_title_gate
OCR_TITLE_MAX_NONALPHA = 0.15
SEARCH_TITLE_SIM = 0.85           # FACT.crossref_search_gate
SEARCH_YEAR_DELTA = 1
PAGE_SCAN_CAP = 6                 # FACT.front_matter_scan: scan up to N leading pages for the first
                                  # page with a strong title/author signal (cover sheets / blank
                                  # leaves / scanned cover images can precede the real title page).
INDEX_SUBDIR = "index"            # FACT.index_subdir: ALL index outputs live in <dir>/index/, never
                                  # scattered in the articles folder; the scan excludes this subdir.

def index_dir(d):
    """Return the index-output directory (created on demand). All index detritus — paper_index.csv,
    _sfi_*.csv/tsv, _ocr/ sidecars — lives here so the articles folder stays clean; the extract scan
    excludes <d>/index. Default is <d>/index; set the SFI_INDEX_DIR env var to an ABSOLUTE path to
    relocate ALL outputs together (e.g. to a parent folder), leaving the articles folder itself clean."""
    override = os.environ.get("SFI_INDEX_DIR", "").strip()
    p = override if override else os.path.join(d, INDEX_SUBDIR)
    os.makedirs(p, exist_ok=True)
    return p

# ---- portable tool discovery (macOS /opt/homebrew, Linux /usr/bin, /usr/local) ----
_TOOL_DIRS = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
def tool(name):
    p = shutil.which(name)
    if p:
        return p
    for d in _TOOL_DIRS:
        cand = os.path.join(d, name)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None

def run(cmd, timeout):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except Exception as e:
        class R:  # noqa
            pass
        r = R(); r.stdout = ""; r.stderr = str(e); r.returncode = -1
        return r

def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

def fold_ascii(s):
    """ASCII-fold a name for matching: strip diacritics/accents AND normalize
    unicode punctuation (curly quotes, en/em/unicode hyphens, fraction slash,
    nbsp) to plain ASCII. Keeps hyphen/apostrophe/space structure so surnames
    stay readable. Written to first_author_ascii so index<->filename<->DOI
    matching never false-positives on an accent (Araujo vs Araujo).
    Ground-truth author display stays in first_author (accents preserved)."""
    import unicodedata as _ud
    s = str(s)
    s = re.sub(r"[\u2010-\u2015\u2212]", "-", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u02bc", "'").replace("\u00b4", "'")
    s = s.replace("\u2044", "/").replace("\u00a0", " ")
    s = _ud.normalize("NFKD", s)
    s = "".join(c for c in s if not _ud.combining(c))
    s = s.encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip()

# ==================================================================== journal map (offline convenience)
# Generic DOI-prefix -> journal-name lookup (NO filenames = not corpus seed). CrossRef LOOKUP is
# authoritative for journal; this is only the offline fallback when no network / no DOI hit.
JR = [("10.1111/nph.","New Phytologist"),("10.1111/j.1469-8137","New Phytologist"),
("10.1111/gcb.","Global Change Biology"),("10.1111/j.1365-2486","Global Change Biology"),("10.1046/j.1365-2486","Global Change Biology"),
("10.1111/1365-2745","Journal of Ecology"),("10.1111/j.1365-2745","Journal of Ecology"),
("10.1111/1365-2435","Functional Ecology"),("10.1111/j.1365-2435","Functional Ecology"),("10.1046/j.1365-2435","Functional Ecology"),
("10.1111/ele.","Ecology Letters"),("10.1111/j.1461-0248","Ecology Letters"),
("10.1111/pce.","Plant, Cell & Environment"),("10.1111/j.1365-3040","Plant, Cell & Environment"),("10.1046/j.1365-3040","Plant, Cell & Environment"),
("10.1111/btp.","Biotropica"),("10.1111/j.1744-7429","Biotropica"),
("10.1111/2041-210x","Methods in Ecology and Evolution"),("10.1111/j.1469-185x","Biological Reviews"),
("10.1002/ece3","Ecology and Evolution"),("10.1002/ecs2","Ecosphere"),("10.1002/hyp","Hydrological Processes"),("10.1002/2014wr","Water Resources Research"),
("10.1016/j.agrformet","Agricultural and Forest Meteorology"),("10.1016/0168-1923","Agricultural and Forest Meteorology"),("10.1016/s0168-1923","Agricultural and Forest Meteorology"),
("10.1016/j.rse","Remote Sensing of Environment"),("10.1016/s0034-4257","Remote Sensing of Environment"),
("10.1016/j.solener","Solar Energy"),("10.1016/0038-092x","Solar Energy"),
("10.1016/j.envexpbot","Environmental and Experimental Botany"),("10.1016/0098-8472","Environmental and Experimental Botany"),
("10.1016/j.jag","Int J Applied Earth Observation and Geoinformation"),("10.1016/j.scienta","Scientia Horticulturae"),
("10.1016/j.renene","Renewable Energy"),("10.1016/j.tree","Trends in Ecology & Evolution"),
("10.1016/0002-1571","Agricultural Meteorology"),("10.1016/s0378-1127","Forest Ecology and Management"),
("10.1038/s41586","Nature"),("10.1038/nature","Nature"),("10.1038/s41558","Nature Climate Change"),
("10.1038/s41559","Nature Ecology & Evolution"),("10.1038/s41477","Nature Plants"),("10.1038/nplants","Nature Plants"),
("10.1038/s41467","Nature Communications"),("10.1038/s42003","Communications Biology"),("10.1038/ngeo","Nature Geoscience"),
("10.1093/jxb","Journal of Experimental Botany"),("10.1093/treephys","Tree Physiology"),("10.1093/aob","Annals of Botany"),
("10.1126/science","Science"),("10.1098/rstb","Philosophical Transactions of the Royal Society B"),("10.1103/physrevlett","Physical Review Letters"),
("10.5194/bg","Biogeosciences"),("10.5194/hess","Hydrology and Earth System Sciences"),
("10.3390/rs","Remote Sensing"),("10.3390/f","Forests"),("10.3390/s","Sensors"),
("10.3389/ffgc","Frontiers in Forests and Global Change"),("10.3389/fpls","Frontiers in Plant Science"),
("10.1371/journal.pone","PLoS ONE"),
("10.1007/s00442","Oecologia"),("10.1007/s00468","Trees"),("10.1007/s004680","Trees"),("10.1007/s004420","Oecologia"),("10.1007/bf00","Oecologia"),
("10.1007/s00376","Advances in Atmospheric Sciences"),("10.1007/s10021","Ecosystems"),("10.1007/s10546","Boundary-Layer Meteorology"),
("10.1007/s10310","Journal of Forest Research"),("10.1007/s11120","Photosynthesis Research"),("10.1007/s11258","Plant Ecology"),
("10.1007/s11284","Ecological Research"),("10.1007/978","book / edited volume"),
("10.1063/","J Renewable and Sustainable Energy"),("10.1071/fp","Functional Plant Biology"),("10.1071/pp","Australian Journal of Plant Physiology"),
("10.1080/17550874","Plant Ecology & Diversity"),("10.1080/01431161","International Journal of Remote Sensing"),
("10.2134/agronj","Agronomy Journal"),("10.3732/ajb","American Journal of Botany"),("10.3354/cr","Climate Research"),
("10.32615/ps","Photosynthetica"),("10.1104/pp","Plant Physiology"),("10.1146/annurev","Annual Review of Plant Physiology"),
("10.1364/ao","Applied Optics"),("10.1139/x","Canadian Journal of Forest Research"),("10.1073/pnas","PNAS")]

def jfromdoi(doi):
    d = (doi or "").lower().strip()
    if not d:
        return ""
    if d.startswith("10.1029/"):
        tail = d.split("10.1029/")[1][:11]
        for k, v in (("gl","Geophysical Research Letters"),("jg","JGR Biogeosciences"),
                     ("jd","JGR Atmospheres"),("gb","Global Biogeochemical Cycles"),("wr","Water Resources Research")):
            if k in tail:
                return v
    for pre, jn in JR:
        if d.startswith(pre):
            return jn
    return ""

def clean_title(t):
    t = (t or "").strip(); tl = t.lower()
    if len(t) < 12:
        return ""
    junk = ["untitled",".qxd",".vp",".fm ","pii:","iso 15930","microsoft ","oup_","unbekannt",
            "science journals","pone.","nplants201","law.vp","doi:"]
    if any(j in tl for j in junk):
        return ""
    if re.match(r"^(er[a-z]\d|mc[a-z]\d|tp[a-z]\d|bf\d|s\d{4,}|\d{3,}|460\d|27\d{4}|160139)", tl):
        return ""
    return t

def wellnamed(fn):
    """Recognize a 'well-named' reference-export filename and return (author, year, journal, title)
    — a HIGH-confidence, network-free metadata source — or None. Two conventions are supported:
      1. Wiley/OUP export:                 `Journal - Year - Author - Title.pdf`   (space-dash-space)
      2. Reference-manager (Papers/Zotero): `Author_Year_Journal_Title.pdf`        (underscore)
    Only the fields the pattern actually yields are returned; a missing tail field is "". The year
    must be a 19xx/20xx token, and (convention 2) an author token must precede it (year never in
    position 0), so a leading-year or cryptic stem does not false-match."""
    b = re.sub(r"\.pdf$", "", fn, flags=re.I)
    # --- Convention 1: Wiley/OUP  Journal - Year - Author - Title ---
    parts = b.split(" - ")
    if len(parts) >= 4:
        toks = parts[1].replace("-", " ").split()
        yrs = [w for w in toks if len(w) == 4 and w.isdigit() and w[:2] in ("19", "20")]
        if yrs:
            return (parts[2].strip(), yrs[0], parts[0].strip(), " - ".join(parts[3:]).strip())
    # --- Convention 2: Author_Year_Journal_Title (underscore-delimited) ---
    us = b.split("_")
    if len(us) >= 3:
        for i, p in enumerate(us[:3]):
            s = p.strip()
            if len(s) == 4 and s.isdigit() and s[:2] in ("19", "20"):
                if i >= 1:                                  # author token must precede the year
                    journal = us[i + 1].strip() if len(us) > i + 1 else ""
                    title = "_".join(us[i + 2:]).strip() if len(us) > i + 2 else ""
                    return (us[0].strip(), s, journal, title)
                break                                       # year in position 0 => not this convention
    # --- Convention 3: SHORT Author_Year (reference manager, no journal/title captured) ---
    # Papers/Zotero often export just "Surname_YYYY.pdf" (optionally with a "_N" copy-index or a
    # " - supplement[ N]" tail that b has already kept). Recover author+year — the two most reliable
    # fields — leaving journal/title blank for embedded/body-mining to fill. Author must be a plausible
    # surname (starts with a letter, ≥2 chars, not all digits), year a 19xx/20xx token in position 1.
    core = re.split(r"\s+-\s+", b)[0]                       # drop " - supplement..." tail if present
    core = re.sub(r"_\d{1,2}$", "", core)                   # drop a trailing "_2" copy-index (1-2 digits,
                                                            # never a 4-digit year)
    su = core.split("_")
    if len(su) == 2:
        au, yr = su[0].strip(), su[1].strip()
        if (len(yr) == 4 and yr.isdigit() and yr[:2] in ("19", "20")
                and re.match(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'.\-]+$", au) and not au.isdigit()):
            return (au, yr, "", "")
    return None

TYPE_MAP = {"journal-article":"article","book-chapter":"book_chapter","book":"book","monograph":"book",
            "proceedings-article":"conference","posted-content":"preprint","report":"report",
            "dissertation":"thesis"}

# ==================================================================== PROC.4 cryptic filename -> DOI
def derive_doi(fn):
    """Pure derivation, no network. Returns (doi, note) or ('', reason)."""
    b = re.sub(r"\.pdf$", "", fn, flags=re.I)
    if re.match(r"^BF\d+$", b):                      return ("10.1007/" + b, "cryptic:springer-legacy")
    if re.match(r"^A_\d+$", b):                       return ("10.1023/A:" + b[2:], "cryptic:kluwer-legacy")
    if re.match(r"^s\d{4,5}-", b):                    return ("10.1007/" + b, "cryptic:springer")
    if re.match(r"^978-", b):                         return ("10.1007/" + b, "cryptic:springer-book")
    if b.startswith("annurev"):                       return ("10.1146/" + b, "cryptic:annual-reviews")
    if re.match(r"^(bg|gmd|acp|hess|essd)-", b):       return ("10.5194/" + b, "cryptic:copernicus")
    return ("", "no-doi-derivable")

def is_pnas_supp(fn):
    b = re.sub(r"\.pdf$", "", fn, flags=re.I).lower()
    m = re.match(r"^pnas\.(\d+)(si|\.sd\d+)", b) or re.match(r"^pnas\.(\d{6,})", b) if ("si" in b or ".sd" in b) else None
    if m:
        pid = m.group(1)
        rt = "dataset" if (".sd" in b or fn.lower().endswith((".xlsx",".csv"))) else "supplement"
        return (rt, "10.1073/pnas." + pid)
    return None

SUPP_PATTERNS = [r"-sup-", r"moesm", r"_suppl_", r"si\.pdf$", r"\.sd\d+\.", r"supinfo", r"supplementary",
                 r"supplement", r"\bsupporting information\b", r"_si_\d", r"-si-\d"]  # ref-manager exports:
                 # "_supplement_N", " - supplement N", "supporting information" (Papers/Zotero attach names)
def is_supplement(fn):
    low = fn.lower()
    if any(re.search(p, low) for p in SUPP_PATTERNS):
        return "dataset" if low.endswith((".xlsx",".csv")) else "supplement"
    return None

# Front-of-document banners that mark a PDF as supplementary material, split by strength. STRONG banners
# are SECTION-OPENERS ("Supporting Information", "Supplementary Methods") that only head an SI document.
# WEAK banners ("Supplementary Table/Figure") are ALSO printed in the body/first page of MAIN articles
# (as captions or cross-references), so they flip a record only when the document does NOT open with an
# article-type masthead word. All checks are against the first ~90 chars of page-1 text (the masthead
# region) so a real article that merely cites its SI deeper in the body is never misread as SI.
_SI_BANNERS_STRONG = ("supporting information", "supplementary material", "supplementary information",
                      "supplemental material", "supplemental information", "supplementary data",
                      "supplementary methods", "supplementary note", "supplementary text",
                      "electronic supplementary", "supplementary materials for",
                      "in the format provided by the authors", "appendix s")
_SI_BANNERS_WEAK = ("supplementary figures", "supplementary table", "supplementary figure")
# Article-type labels Nature/Science/Cell print as the FIRST token of a MAIN article's page 1
# ("Article https://doi…", "Letters https://doi…"). A genuine SI leads with the journal NAME, a URL,
# or a "Supplementary/Supporting" banner — never a bare article-type label — so a leading label + a
# nearby DOI/URL identifies a main article and vetoes a WEAK-only flip.
_ART_MASTHEAD = re.compile(r"^(article|letters?|reports?|research|analysis|review|perspective|"
                           r"brief communication)s?\b.{0,60}(https?://|doi[:\s])", re.I)
def si_by_content(snippet, embedded_title):
    """True when PDF CONTENT decisively opens as supplementary material. Ground-truth signal that
    OVERRIDES a CrossRef DOI-type of 'journal-article' — an SI PDF often embeds its PARENT's DOI, so a
    DOI-type lookup wrongly reports it as an article. Content is authoritative; filename and DOI-type
    are weaker priors. Never fabricates: no banner in the head => returns False (no change)."""
    s = (snippet or "").lower(); t = (embedded_title or "").lower()
    head = s[:90]
    # STRONG opener anywhere in the head, or the New-Phytologist SI header, or an SI embedded-title:
    if any(b in head for b in _SI_BANNERS_STRONG):
        return True
    if head.strip().startswith("article title:") or "supporting information article title" in s:
        return True
    if "supporting information" in t or "supplementary material" in t or "supplementary information" in t:
        return True
    # WEAK banner: only decisive when the doc does NOT open as a main article (no leading masthead label).
    if any(b in head for b in _SI_BANNERS_WEAK) and not _ART_MASTHEAD.match(head):
        return True
    return False

# Front-of-document banners that mark a PDF as a PEER-REVIEW / editorial-decision file rather than an
# article: journals (Nature Comms, Communications Biology, ...) bundle the reviewer correspondence as a
# separate download whose FIRST PAGE opens with one of these openers. Such a file shares the article's
# author+title+DOI (so it groups as a "duplicate") but is a DISTINCT document that must be KEPT, never
# merged into the article. Checked against the true page-1 head only (masthead region), so an article
# that merely quotes "reviewer comments" deeper in its body is never mistyped. Filename tokens are a
# second, weaker signal for files that carry no text banner (e.g. "..._peer-review-file.pdf").
_PEERREVIEW_BANNERS = ("reviewers' comments", "reviewers comments", "reviewer #", "reviewer#",
                       "remarks to the author", "editorial note:", "decision letter",
                       "response to review", "rebuttal", "peer review file", "peer-review file",
                       "author response", "reviewer comments", "reviewer report")
_PEERREVIEW_FN = re.compile(r"peer[-_ ]?review|_review[-_ ]?file\b|reviewer[-_ ]?comments", re.I)
def peerreview_by_content(page1_head):
    """True when the document's TRUE page-1 head opens as a peer-review / editorial-decision file.
    Ground-truth signal: such a file embeds the parent article's DOI/title (so DOI-type lookup and
    title-matching both call it an 'article'), but it is a distinct companion document. Anchored to the
    first ~200 chars of page 1 so a body-text mention of 'reviewer comments' never triggers it."""
    h = (page1_head or "").lower()[:200]
    return any(b in h for b in _PEERREVIEW_BANNERS)
def peerreview_by_filename(file_name):
    """Weak backstop: filename carries an explicit peer-review token."""
    return bool(_PEERREVIEW_FN.search(file_name or ""))

# ---- FM5: stamp-robust content fingerprint (64-bit SimHash) --------------------------------------
# A download stamp, a re-typeset masthead, or an added figure page changes the RAW page-1 cosine of two
# copies of the SAME article enough to defeat naive similarity (a real observed case scored cosine 0.42
# for a near-identical pair). SimHash over boilerplate-stripped, whitespace-collapsed, digit-dropped
# 3-word shingles of the front matter is robust to those local edits: two copies of one article share
# almost all shingles, so their 64-bit hashes differ in only a few bits (small Hamming distance), while
# distinct works differ in most bits. The indexer emits this as the `content_sim` column; the curator
# thresholds the Hamming distance (default K=3) as a SECONDARY near-dup signal, consulted only after the
# distinct-work / author / truncation guards so it can never merge two genuinely different documents.
# Boilerplate is stripped INLINE (matched substrings removed) rather than by dropping whole lines, so a
# masthead line that mixes real content with a stamp/URL ("Annals of Botany 128 ... available online at
# www.acad...") keeps its content tokens instead of being nuked entirely. Robust to both raw multi-line
# front matter and an already-cleaned single-line head.
_SIM_BOILER = re.compile(r"downloaded from|brought to you by|this content downloaded|for personal use only|"
                         r"unauthenticated|ezproxy|all use subject|terms and conditions|jstor|"
                         r"provided by|see discussions, stats|researchgate|https?://\S*|www\.\S*", re.I)
def _sim_tokens(text):
    s = _SIM_BOILER.sub(" ", (text or "")).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return [t for t in s.split() if not t.isdigit()]      # drop digit-only tokens (page nos, stamps)
def content_simhash(text, k=3):
    """64-bit SimHash of boilerplate-stripped, digit-dropped, 3-word-shingled `text`. Returns an int in
    [0, 2**64). Empty/near-empty text returns 0 (the curator treats 0 as 'no fingerprint' and skips it)."""
    toks = _sim_tokens(text)
    if len(toks) >= k:
        shingles = [" ".join(toks[i:i + k]) for i in range(len(toks) - k + 1)]
    else:
        shingles = [" ".join(toks)] if toks else []
    if not shingles:
        return 0
    import hashlib as _hl
    v = [0] * 64
    for sg in shingles:
        h = int.from_bytes(_hl.blake2b(sg.encode("utf-8"), digest_size=8).digest(), "big")
        for b in range(64):
            v[b] += 1 if (h >> b) & 1 else -1
    out = 0
    for b in range(64):
        if v[b] > 0:
            out |= (1 << b)
    return out

# ==================================================================== overrides / review IO
def load_overrides(path):
    ov = {}
    if not os.path.exists(path):
        return ov
    for line in open(path, encoding="utf-8"):
        if not line.strip() or line.startswith("#"):
            continue
        c = line.rstrip("\n").split("\t"); c += [""] * (9 - len(c))
        ov[c[0]] = dict(author=c[1], year=c[2], title=c[3], journal=c[4], rt=c[5],
                        parent=c[6], note=c[7], doi=c[8])   # col8 optional doi
    return ov

def overrides_filenames(path):
    s = set()
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            if ln.strip() and not ln.startswith("#"):
                s.add(ln.split("\t")[0])
    return s

# ==================================================================== EXTRACT (PROC.1 + PROC.2)

# ===================================================================
# A-SIDE CONFIDENCE / IDENTITY SUBSYSTEM (merged from forest.microclimate@ fork)
# Single-source-of-truth confidence tiers + author-plausibility gates + copyright-line
# detection (defect #44). These feed derive_confidence() and the DOI-free search path.
# ===================================================================
_CONF_AUTHOR_PLACEHOLDER = {"unknown","anonymous","anon","anon.","author","authors","user","team",
    "editor","editors","admin","guest","na","n/a","n.a.","none","null","tbd","tbc",
    "et al","et al.","fig","figure","table","data","supplement"}
_BAD_AUTHOR_TOKENS = {"karen","user","admin","guest","author","authors","editor","forestry","team",
                      "abstract","summary","introduction","copyright","untitled","microsoft","word",
                      "acrobat","distiller","ventura","quark","preface","index","contents"}
_COPYRIGHT_KW = re.compile(r"(©|\(c\)|copyright|\ball rights reserved\b|\bpublishing\b|"
                           r"\bpublishers?\b|\buniversity press\b|\bpress[,.]|heron publishing|"
                           r"springer|elsevier|wiley|blackwell|kluwer|taylor\s*&\s*francis)", re.I)
_JOURNAL_ABBR = {"proc","natl","acad","sci","nat","j","am","amer","soc","bot","biol","ecol",
                 "evol","phys","chem","physiol","rev","annu","ann","res","trans","bull","q",
                 "int","zool","agric","for","meteorol","hydrol","geophys","atmos","clim","funct",
                 "plant","cell","environ","new","phytol","tree","glob","chang","appl","exp"}

# crash-safe atomic write (from sci_lib_common; inlined to keep this script self-contained)
def write_atomic(path, write_fn, mode="w", encoding="utf-8", newline=""):
    """Write via a temp file in the same dir, fsync, then os.replace (atomic on POSIX).
    write_fn(file_handle) does the actual writing. A crash leaves the prior file intact."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".part")
    try:
        with os.fdopen(fd, mode, encoding=encoding, newline=newline) as f:
            write_fn(f)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try: os.unlink(tmp)
        except OSError: pass
        raise

def conf_author_known(s):
    s = (s or "").strip()
    if s == "" or s.lower() in _CONF_AUTHOR_PLACEHOLDER: return False
    if re.fullmatch(r"[A-Za-z]\.?", s): return False    # single letter "L." = truncated
    return True
def conf_title_known(s):
    s = (s or "").strip()
    if s == "" or len(s) < 8: return False
    if s.startswith("\u00a9"): return False
    if re.match(r"^[A-Z][a-z]+.*,\s*\d+\s*\(\s*\d{4}\s*\)", s): return False
    if re.search(r"publishing.*(canada|victoria)", s, re.I): return False
    return True
def conf_year_known(s):
    return bool(re.fullmatch(r"(1[6-9]\d\d|20[0-2]\d)", (s or "").strip()))
def conf_pub_known(s):
    s = (s or "").strip()
    return not (s == "" or s.lower() in _CONF_AUTHOR_PLACEHOLDER)
def _plausible_author(fam):
    """A mined family name is usable as a SEARCH GATE only if it looks like a real surname:
    >=3 letters, not a known typesetter/role artifact, not a journal keyword. Junk (a typesetter
    'Karen', a single initial, 'Forestry') is dropped so the search falls back to title(+year) —
    which is then content-verified before writing (never fabricates)."""
    f = (fam or "").strip()
    if len(re.sub(r"[^A-Za-z]", "", f)) < 3: return False
    if f.lower() in _BAD_AUTHOR_TOKENS: return False
    if _JOURNAL_KW.search(f): return False
    return True
def _author_in_text(hit, text):
    """Content-gate for a TITLE-ONLY search hit (no mined author to verify against): the hit's
    first-author family name must appear in the file's own page-1 text. Upholds never-fabricate on
    the title-only path — a strong title match to a DIFFERENT paper whose author is absent is rejected."""
    if not text: return False
    fams = [(a.get("family","") or "") for a in (hit.get("author") or [])]
    tl = text.lower()
    return any(len(fm) >= 3 and fm.lower() in tl for fm in fams[:3])
def _looks_like_copyright(s):
    # A publisher / copyright / imprint line ("(c) 2000 Heron Publishing-Victoria, Canada",
    # "(c) The Authors 2019", "Springer-Verlag 2004") is NOT a title. These sit directly under the
    # journal masthead on the first page of many publishers (Tree Physiology, Springer, Wiley) and a
    # naive first-title-like-line grab captures them instead of the real title (defect #44).
    return bool(_COPYRIGHT_KW.search(s))

def derive_confidence(row):
    """Confidence tier from identity fields AND note semantics — the SINGLE SOURCE OF TRUTH used by
    both cmd_build and the kernel QA re-derivation (sfi_recompute_confidence), so the stored column
    can never drift from what the data implies. DOI-neutral, placeholder-aware.

    Structure (A-side identity tiers) fused with note-awareness (B-side):
      - dataset                                             -> n/a
      - OCR/mined-but-UNVALIDATED note                      -> low   (mined != externally verified)
      - missing author OR missing title                    -> low
      - author+title present, but a note signals UNCERTAINTY-> medium
      - author+title(+year) present, note absent or a
        TRUSTWORTHY resolution marker (CrossRef/search/
        cryptic-DOI/SI-link/cover-sheet/review-verdict)    -> high
      - author+title present but no year                   -> medium
    """
    if (row.get("record_type") or "").strip().lower() == "dataset":
        return "n/a"
    note_l = (row.get("notes") or "").lower()
    # An OCR/mined row whose fields were mined-but-not-externally-validated is LOW no matter how many
    # columns are filled — mined-from-the-scan is not the same as verified.
    if "unvalidated" in note_l or "ocr: image-only" in note_l:
        return "low"
    A = conf_author_known(row.get("first_author"))
    Y = conf_year_known(row.get("year"))
    P = conf_pub_known(row.get("journal"))
    T = conf_title_known(row.get("title"))
    # Identity floor: without a real author OR a real title the row cannot be trusted.
    if not A and not T:
        return "very low"
    if not A or not T:
        return "low"
    # author+title present. Weigh the note: genuine-uncertainty markers cap at MEDIUM; a validated
    # resolution (or no note at all) is eligible for HIGH.
    uncertain = any(k in note_l for k in ("guess", "unverified", "approx", "ambiguous",
                                          "no-doi", "gate-fail", "check", "uncertain"))
    trustworthy_note = (not row.get("notes")) or any(k in note_l for k in
        ("crossref:", "search:", "cryptic", "si of", "si/dataset", "doi-truncated-dropped",
         "filename-stem", "review-verdict:", "verified from", "jstor-cover:"))
    if uncertain:
        return "medium"
    if A and Y and P and T and trustworthy_note:
        return "high"
    if A and T and Y and trustworthy_note:
        return "high"
    if row.get("notes") and not trustworthy_note:
        return "medium"
    # author+title (+maybe year/journal) present, benign/no note -> high; missing year alone -> medium
    return "high" if Y else "medium"

def cmd_extract(args):
    d = args.dir
    out = os.path.join(index_dir(d), RAW_NAME)
    pdfinfo, pdftotext, pdffonts = tool("pdfinfo"), tool("pdftotext"), tool("pdffonts")
    if not pdftotext:
        sys.exit("FATAL: pdftotext (poppler) not found on PATH. Install poppler-utils / poppler.")
    files = sorted(os.listdir(d))
    rows = []
    # live progress heartbeat: <index_dir>/_sfi_progress.txt = "done/total current_file" (readable
    # mid-run for large corpora). Count the candidate files first so the total is exact.
    _prog_path = os.path.join(index_dir(d), "_sfi_progress.txt")
    _cands = [f for f in files
              if not (f.startswith(".") or f.startswith("_") or f.startswith("~$"))
              and f != INDEX_SUBDIR and os.path.isfile(os.path.join(d, f))]
    _ntot = len(_cands)
    _done = 0
    for fn in files:
        if fn.startswith(".") or fn.startswith("_") or fn.startswith("~$"):
            continue
        if fn == INDEX_SUBDIR:                       # never catalog our own output subfolder
            continue
        path = os.path.join(d, fn)
        if not os.path.isfile(path):                 # also skips the index/ dir (and any subdir)
            continue
        _done += 1
        if _done == 1 or _done % 20 == 0 or _done == _ntot:
            try:
                with open(_prog_path, "w", encoding="utf-8") as _pf:
                    _pf.write("%d/%d %s\n" % (_done, _ntot, fn))
            except Exception:
                pass
        ext = os.path.splitext(fn)[1].lower().lstrip(".")
        # n_fonts: embedded-font count. "" = not a pdf / pdffonts unavailable; the scanned test
        # treats n_fonts=="0" (explicit no-text-layer) as a hard scanned signal (PROC.5 DETECT).
        row = {"file_name": fn, "ext": ext, "n_pages": "", "chars_page1": "", "n_fonts": "",
               "embedded_title": "", "embedded_author": "", "producer": "", "doi": "", "doi_source": "",
               "title_src_page": "", "snippet": "", "page1_head": "", "content_sim": ""}
        if ext == "pdf":
            info = {}
            if pdfinfo:
                r = run([pdfinfo, path], 30)
                for line in r.stdout.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1); info[k.strip()] = v.strip()
            row["n_pages"] = info.get("Pages", "")
            row["embedded_title"] = clean(info.get("Title", ""))
            row["embedded_author"] = clean(info.get("Author", ""))
            row["producer"] = clean(info.get("Producer", "") or info.get("Creator", ""))
            p1 = run([pdftotext, "-f", "1", "-l", "1", "-layout", path, "-"], 60).stdout
            # chars_page1 counts REAL text only: strip download/access boilerplate first, so a
            # scanned offprint carrying only a watermark over an image body is still detected as
            # scanned (defect #42 — a raw count would hide it and skip OCR).
            _wm = re.compile(r"downloaded from|brought to you by|this content downloaded|for personal use only|"
                             r"unauthenticated|ezproxy|all use subject|terms and conditions|jstor|"
                             r"provided by|see discussions, stats|researchgate|https?://|www\.", re.I)
            _p1_real = " ".join(ln for ln in p1.splitlines() if ln.strip() and not _wm.search(ln))
            row["chars_page1"] = str(len(re.sub(r"\s", "", _p1_real)))
            if pdffonts:
                fr = run([pdffonts, path], 30)
                # pdffonts prints a 2-line header then one row per embedded font
                if fr.returncode == 0:
                    row["n_fonts"] = str(max(0, len([ln for ln in fr.stdout.splitlines()[2:] if ln.strip()])))
            # FRONT-MATTER FORWARD-SCAN (text layer): read up to PAGE_SCAN_CAP leading pages split
            # per-page (form-feed \f), then lock onto the FIRST strong-signal page — cover sheets and
            # blank leaves score ~0 and are skipped. Title/author may not be on page 1.
            try:
                npages = int(row["n_pages"] or "0")
            except ValueError:
                npages = 0
            last = min(PAGE_SCAN_CAP, npages) if npages else 2
            multi = run([pdftotext, "-f", "1", "-l", str(last), "-layout", path, "-"], 90).stdout
            pages = multi.split("\f")
            # FM1: capture the TRUE page-1 head (first ~200 clean chars of the actual first page),
            # INDEPENDENT of the front-matter miner below. The miner (scan_pages_for_signal) may lock
            # onto a later page (cover sheets / blank leaves precede the title page), so `snippet` is NOT
            # a reliable page-1 signal. record_type reclassification (SI / peer-review banners) must key
            # off the document's genuine opening, which is exactly this: an SI or peer-review file OPENS
            # with its banner, whereas an article that merely appends its SI still opens with the article
            # masthead. Clean-then-slice so the 200-char window is 200 chars of real text.
            row["page1_head"] = clean(pages[0] if pages else "")[:200]
            # FM5: stamp-robust content fingerprint over the true page-1 head (boilerplate-stripped
            # inside the helper). Threaded to the master so the curator can detect same-article near-dups
            # whose raw page-1 cosine is misleadingly low (download stamps / re-typeset mastheads). Keyed
            # to page1_head (not the miner's page) so it fingerprints the document's genuine opening and
            # is reproducible from that column. "" when there is no usable text — never a fabricated hash.
            row["content_sim"] = (str(content_simhash(row["page1_head"]))
                                  if row["page1_head"].strip() else "")
            si, stext = scan_pages_for_signal(pages)
            if si:
                row["title_src_page"] = str(si + 1)   # 1-indexed page the signal came from
            # DOI: from the strong page first, then any scanned page, then metadata keys
            m = DOI_RE.search(stext) or DOI_RE.search(multi); srclbl = "text"
            if not m:
                for key in ("Subject", "Title", "Keywords"):
                    mm = DOI_RE.search(info.get(key, "") or "")
                    if mm:
                        m, srclbl = mm, "meta:" + key; break
            if m:
                row["doi"] = m.group(0).rstrip(".,;)]}>"); row["doi_source"] = srclbl
            # BODY-TEXT MINING (A): if embedded PDF metadata gave no title/author — OR a JUNK title
            # (a PII string / bare DOI / filename, which publisher exports routinely stuff into the
            # Title field) — mine them from the strong page's own body text (gated miners, never
            # fabricated). This feeds the DOI-free title+author resolution path for text PDFs like
            # Elsevier PII exports whose real title is on the page but not in usable metadata.
            title_is_junk = is_junk_title(row["embedded_title"])
            if title_is_junk:
                row["embedded_title"] = ""                 # drop the junk so the miner (and build) ignore it
            # Skip body-mining on SCANNED pages (near-empty text layer) — pdftotext returns only
            # boilerplate/garble there; those files go to the OCR stage, which mines from real image
            # text. Body-mining is for text-layer PDFs whose metadata is blank/junk.
            try:
                scanned = int(row["chars_page1"] or "0") < SCANNED_CHAR_THRESHOLD
            except ValueError:
                scanned = False
            if not scanned and (not row["embedded_title"] or not row["embedded_author"]):
                bti, bau, byr, _ = mine_bibliography(stext)
                if not row["embedded_title"] and bti:
                    row["embedded_title"] = bti
                if not row["embedded_author"] and bau:
                    row["embedded_author"] = bau
            row["snippet"] = clean(stext or multi)[:400]
        rows.append(row)
    cols = ["file_name","ext","n_pages","chars_page1","n_fonts","embedded_title","embedded_author",
            "producer","doi","doi_source","title_src_page","snippet","page1_head","content_sim"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows:
            w.writerow(r)
    print("WROTE %s  (%d rows; %d pdf)" % (out, len(rows), sum(1 for r in rows if r["ext"] == "pdf")))

# ==================================================================== BUILD (PROC.3/4/7/8/9 merge)
def cmd_build(args):
    d = args.dir
    ixd = index_dir(d)
    index_path = args.index or os.path.join(ixd, "paper_index.csv")
    ov_path = args.overrides or os.path.join(ixd, OVERRIDES_NAME)
    raw_path = os.path.join(ixd, RAW_NAME)
    if not os.path.exists(raw_path):
        sys.exit("FATAL: %s not found — run `extract` first." % raw_path)
    raw = {r["file_name"]: r for r in csv.DictReader(open(raw_path, encoding="utf-8"))}
    ov = load_overrides(ov_path)
    index_name = os.path.basename(index_path)

    prev = {}
    if os.path.exists(index_path):
        prev = {r["file_name"]: r for r in csv.DictReader(open(index_path, encoding="utf-8"))}

    rows = []
    for fn, r in raw.items():
        if fn.startswith("_") or fn.startswith("~$") or fn == index_name:
            continue
        if fn.lower().endswith(".docx") and (fn[:-5] + ".pdf") in raw:
            continue
        if fn.lower().endswith(EXCLUDE_ARCHIVE):
            continue
        o = ov.get(fn, {}); ext = r["ext"]
        if o.get("rt") == "exclude":            # explicit review verdict: file does not belong in the library
            continue
        doi = o.get("doi") or r.get("doi", "")
        note = o.get("note", "")
        # GUARD: drop a TRUNCATED DOI captured from wrapped body text — a suffix with no digit at all
        # (e.g. "10.1371/journal", "10.1073/pnas", "10.1016/j") is a line-break artifact, not a real
        # article DOI, and would otherwise collapse unrelated papers into one phantom duplicate group.
        # Blank it (never fabricate) and note it; the row still resolves from the filename parse. Real
        # article DOIs carry a digit in the suffix.
        if doi and "/" in doi and not re.search(r"\d", doi.split("/", 1)[1]):
            note = (note + "; " if note else "") + "doi-truncated-dropped(" + doi + ")"
            doi = ""
        # PROC.4: cryptic-name DOI derivation when extraction found none and it's not overridden
        if not doi and not o:
            dd, dnote = derive_doi(fn)
            if dd:
                doi = dd; note = note or dnote
        wn = wellnamed(fn)
        # author/title/journal priority: override > wellname-parse > embedded/body-mined (extract).
        # A wellname parse of a reference-manager export (Author_Year_Journal_Title) is a clean,
        # deliberately-curated source, so it takes priority over embedded PDF metadata — which is
        # routinely blank or junk (journal running-heads, "available at www...", a bare PII/DOI) for
        # these publisher exports. The embedded_* fields still back-fill when the filename is not
        # well-named (they also carry extract's body-text-mined title/author for the DOI-free path).
        # embedded_author is often a FULL author list ("A; B; C" / "Surname, Init., Next...") —
        # reduce it to the first-author surname (the first_author key). An override or a
        # wellname parse already yields a single name, so only the embedded fallback needs it.
        author = o.get("author") or (wn[0] if wn else "") or _family_name(clean(r.get("embedded_author", "")))
        year = o.get("year") or (wn[1] if wn else "")
        title = o.get("title") or (wn[3] if wn else "") or clean_title(r.get("embedded_title", ""))
        journal = o.get("journal") or (wn[2] if wn else "") or jfromdoi(doi)
        # record_type: override > supplement/dataset pattern > dataset ext > default article
        rt = o.get("rt")
        if not rt:
            supp = is_supplement(fn) or (is_pnas_supp(fn)[0] if is_pnas_supp(fn) else None)
            if supp:
                rt = supp
            elif ext in ("csv", "xlsx"):
                rt = "dataset"
            else:
                rt = "article"
        # FM2 CONTENT OVERRIDE (peer-review): a peer-review / editorial-decision file embeds the parent
        # article's DOI+title (so DOI-type lookup and title-matching both call it 'article'), but it is a
        # DISTINCT companion document that must be kept, never merged. Its TRUE page-1 head opens with a
        # reviewer/editorial banner ("Reviewers' comments", "Editorial Note:", ...); a filename token is a
        # weaker backstop. Checked BEFORE the SI override (a peer-review file is not an SI). Only flips
        # article->peer_review, stamps an auditable note. Anchored to page1_head so a body-text mention of
        # "reviewer comments" in a real article never triggers it.
        page1_head = r.get("page1_head", "")
        if (rt == "article" and not o.get("rt") and ext not in ("csv", "xlsx")
                and (peerreview_by_content(page1_head) or peerreview_by_filename(fn))):
            rt = "peer_review"
            note = (note + "; " if note else "") + "reclassified-article->peer_review:content-peer-review-banner"
        # FM1 CONTENT OVERRIDE (SI): a decisive "Supporting Information" banner at the document head forces
        # 'supplement' even when an override/CrossRef DOI-type said 'article' (SI PDFs embed the PARENT's
        # DOI, so a DOI-type lookup misreports them). Content is ground truth here. Gated on the TRUE
        # page-1 head (page1_head), NOT the miner's snippet: an SI OPENS with its banner (-> supplement),
        # whereas an article that merely APPENDS its SI still opens with the article masthead (-> article).
        # Only flips article->supplement (never the reverse) and stamps a note so the reclass is auditable.
        elif (rt == "article" and not o.get("rt") and ext not in ("csv", "xlsx")
                and si_by_content(page1_head, r.get("embedded_title", ""))):
            rt = "supplement"
            note = (note + "; " if note else "") + "reclassified-article->supplement:content-SI-banner"
        parent = o.get("parent", "")
        rows.append(dict(file_name=fn, record_type=rt, first_author=author, year=year, title=title,
                         journal=journal, doi=doi, parent_file=parent, duplicate_of="",
                         confidence="", notes=note, pages=clean(r.get("n_pages", "")),
                         content_sim=clean(r.get("content_sim", ""))))

    byname = {r["file_name"]: r for r in rows}
    # PROC.7 supplement parent auto-link. Two linkers, in order of reliability for reference-manager
    # libraries: (A) shared DOI stem; (B) FILENAME-STEM fallback — a Papers/Zotero export names a
    # supplement after its parent ("Adams_2016 - supplement 2.pdf" <- "Adams_2016...pdf"), so the
    # text before the supplement marker is the parent's stem. (B) catches the many supplements with
    # NO DOI, which (A) cannot. Both never fabricate: a supplement with no DOI-match and no stem-match
    # stays unlinked (parent_file blank).
    _supp_split = re.compile(r"\s*-\s*supplement|_supplement|\s*-\s*supporting information|_si_\d|-si-\d", re.I)
    def _parent_stem(fn):
        b = re.sub(r"\.pdf$", "", fn, flags=re.I)
        return _supp_split.split(b)[0].strip()
    # index non-supplement rows by their filename stem (longest-first so the most specific wins)
    _art_by_stem = {}
    for cand in rows:
        if cand["record_type"] not in ("supplement", "dataset"):
            _art_by_stem[re.sub(r"\.pdf$", "", cand["file_name"], flags=re.I)] = cand["file_name"]
    _art_stems = sorted(_art_by_stem, key=len, reverse=True)
    for r in rows:
        if r["record_type"] in ("supplement", "dataset") and not r["parent_file"]:
            pnas = is_pnas_supp(r["file_name"])
            stem = pnas[1] if pnas else (r["doi"] or "")
            # (A) shared DOI stem
            if stem:
                for cand in rows:
                    if cand is r:
                        continue
                    if cand["doi"] and (stem in cand["doi"] or cand["doi"] in stem) and cand["record_type"] not in ("supplement","dataset"):
                        r["parent_file"] = cand["file_name"]
                        if not r["notes"]:
                            r["notes"] = "SI of " + cand["file_name"]
                        break
            # (B) filename-stem fallback (only if DOI linking found nothing)
            if not r["parent_file"]:
                ps = _parent_stem(r["file_name"])
                if ps and len(ps) >= 4:
                    hit = _art_by_stem.get(ps)          # exact stem match first
                    if not hit:
                        for cs in _art_stems:            # else the longest article stem this supp starts with
                            if cs.startswith(ps) or ps.startswith(cs):
                                hit = _art_by_stem[cs]; break
                    if hit and hit != r["file_name"]:
                        r["parent_file"] = hit
                        if not r["notes"]:
                            r["notes"] = "SI of " + hit + " (filename-stem)"
    # supplements inherit citation fields from parent when blank
    def _norm_doi_si(d):
        d = (d or "").strip().lower()
        return re.sub(r"[-.](supplement|suppl\d*|s0*\d+)$", "", d)
    for r in rows:
        if r["record_type"] == "supplement" and r["parent_file"] in byname:
            p = byname[r["parent_file"]]
            # I18 feed (ported from Claude Science, 2026-07-24): before inheriting blanks, if the SI
            # carries its OWN stored DOI that disagrees with the parent's, stamp the note so validator
            # I18 has an explicit signal instead of silently overwriting it during inheritance.
            own_doi = (r.get("doi") or "").strip()
            if own_doi and _norm_doi_si(own_doi) != _norm_doi_si(p.get("doi","")) and _norm_doi_si(p.get("doi","")):
                if "si-doi-disagrees-parent" not in (r["notes"] or ""):
                    r["notes"] = (r["notes"] + "; " if r["notes"] else "") + "si-doi-disagrees-parent"
            for k in ("first_author","year","title","journal","doi"):
                if not r[k]:
                    r[k] = p[k]
    # PROC.7 dedupe by DOI (flag only — never remove)
    bydoi = {}
    for r in rows:
        dd = r["doi"].lower().strip()
        if dd and r["record_type"] != "supplement":
            bydoi.setdefault(dd, []).append(r)
    for dd, grp in bydoi.items():
        if len(grp) > 1:
            for r in grp:
                r["duplicate_of"] = "; ".join(x["file_name"] for x in grp if x is not r)
    # confidence (FACT.confidence) — SINGLE SOURCE OF TRUTH: derive_confidence() (also used by
    # the kernel QA re-derivation, so the stored column can never drift from the data fields).
    # It fuses A-side identity tiers with B-side note-awareness (CrossRef/search/cover-sheet =
    # trustworthy; guess/unverified/no-doi = uncertain; OCR-mined-unvalidated = low).
    for r in rows:
        r["confidence"] = derive_confidence(r)
    # CRYPTIC-NAME FLAG (ported from Claude Science, 2026-07-24): when identity resolution leaves a
    # non-supplement row with no real author (blank/Unknown), its canonical clean_name cannot be built
    # and would ship as a raw publisher/DOI code. Stamp `cryptic_unresolved` so validator I17 has its
    # explicit escape flag instead of the name shipping cryptic and silently failing I17.
    for r in rows:
        if r["record_type"] not in ("supplement", "dataset"):
            fa = (r.get("first_author") or "").strip().lower()
            if (not fa or fa in ("unknown", "untitled")) and "cryptic_unresolved" not in (r["notes"] or ""):
                r["notes"] = (r["notes"] + "; " if r["notes"] else "") + "cryptic_unresolved"
    # Populate the ASCII-folded author (diacritic-free) for every row so that
    # downstream index<->filename<->DOI matching is transparent and accent-safe.
    for r in rows:
        r["first_author_ascii"] = fold_ascii(r.get("first_author", ""))

    rows.sort(key=lambda r: r["file_name"].lower())
    def _windex(f):
        w = csv.DictWriter(f, fieldnames=INDEX_COLS); w.writeheader()
        for r in rows:
            w.writerow(r)
    write_atomic(index_path, _windex)      # atomic: a crash/interrupt can never truncate the master index

    # PROC.9 report
    from collections import Counter
    conf = Counter(r["confidence"] for r in rows)
    now = {r["file_name"] for r in rows}
    added = sorted(now - set(prev)) if prev else []
    changed = []
    if prev:
        for r in rows:
            p = prev.get(r["file_name"])
            if p and any((r.get(k, "") or "") != (p.get(k, "") or "") for k in INDEX_COLS):
                changed.append(r["file_name"])
    print("WROTE %s  rows: %d" % (index_path, len(rows)))
    print("CONFIDENCE: high=%d medium=%d low=%d n/a=%d" %
          (conf.get("high",0), conf.get("medium",0), conf.get("low",0), conf.get("n/a",0)))
    print("DELTA: +%d new, %d changed%s" % (len(added), len(changed),
          "" if prev else " (no prior index — first build)"))
    dups = sum(1 for r in rows if r["duplicate_of"])
    supp = sum(1 for r in rows if r["record_type"] == "supplement")
    print("supplements linked: %d | duplicates flagged: %d" % (supp, dups))

    # SELF-CHECK GUARD: surface index<->filename<->DOI disagreements so a
    # corrupted identity row cannot pass silently. Verify HIGH flags against
    # printed PDF content (arbiter) > filename > CrossRef, then add overrides.
    sc = selfcheck_identity(rows)
    if sc:
        hi = [x for x in sc if x[1] == "HIGH"]
        print("SELF-CHECK: %d identity flags (%d HIGH) — verify vs printed content, then override:" % (len(sc), len(hi)))
        for fn, sev, why in ([x for x in sc if x[1]=="HIGH"][:25]):
            print("  [%s] %s :: %s" % (sev, fn[:58], why))
        if len(hi) > 25:
            print("  ... +%d more HIGH (see full list via selfcheck_identity)" % (len(hi)-25))
    else:
        print("SELF-CHECK: 0 identity disagreements (index<->filename<->DOI consistent)")
    resid = [r for r in rows if r["confidence"] == "low"]
    if resid:
        print("RESIDUAL-UNRESOLVED (%d) — file :: why :: what would fix:" % len(resid))
        for r in resid:
            note = (r["notes"] or "").lower()
            if "title mined" in note:
                why = "image-only; title mined (UNVALIDATED)"
                fix = "confirm/correct the mined title in an override row (no DOI to auto-verify)"
            elif "ocr" in note:
                why = "image-only+no-DOI"
                fix = "install OCR + re-run ocr" if "unresolved" in note else "user supplies citation / add override"
            elif not r["doi"]:
                why = "no-DOI-derivable"; fix = "user supplies citation / add override"
            else:
                why = "no-single-author"; fix = "expected (edited volume)"
            print("  %s :: %s :: %s" % (r["file_name"][:60], why, fix))

def selfcheck_identity(rows):
    """Build-time self-check: flag index<->filename<->DOI DISAGREEMENTS so a
    corrupted row (wrong paper, title=journal, mojibake, junk author) cannot
    pass silently. Uses the ASCII-folded author for accent-safe matching and
    the same wellnamed() filename parse the build already trusts. This is a
    CHEAP surfacing pass (index columns + filename only); it never reads PDFs
    or calls CrossRef. Returns a list of (file_name, severity, reasons).

    TRUST ORDER when a human resolves a flag: printed PDF content > filename >
    CrossRef/DOI (a wrong/truncated DOI can point CrossRef at a DIFFERENT paper,
    so DOI metadata is corroboration, never the arbiter)."""
    JOURNAL_WORDS = set("journal proc proceedings review annales bulletin transactions science "
                        "sciences nature plants cell environment physiology ecology letters "
                        "phytologist meteorology hydrology forest advances frontiers oecologia "
                        "biotropica mycologia".split())
    SECTION = set("appendix index preface prefaces copyright bibliography symbols acknowledgments "
                  "acknowledgements frontmatter contents nomenclature glossary foreword introduction "
                  "chapter references dedication eds majorequations".split())
    MOJI = re.compile(r"\u00c3[\x80-\xbf\u00a0-\u00ff]|\u00c3.|\u00e2\u0080|\u00c5[\x80-\xbf]|\u00c2[\x80-\xbf]|\ufffd")
    HTMLENT = re.compile(r"<[a-z/][^>]*>|&[a-z]+;|&#\d+;", re.I)
    def _n(s): return re.sub(r"[^a-z0-9]", "", fold_ascii(s).lower())
    def _ttok(s):
        # title tokens: fold to ASCII, SPLIT CamelCase (canonical slugs are CamelCase),
        # keep alnum tokens >3 chars. Used for a token-subset title comparison that is
        # robust to word-order, dropped stopwords, and slug truncation.
        z = fold_ascii(s)
        z = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", z)
        return set(t for t in re.findall(r"[a-z0-9]+", z.lower()) if len(t) > 3)
    def _surn(s):
        s = re.split(r"[;,&]| and ", str(s))[0]
        toks = [t for t in re.split(r"[\s\-]+", fold_ascii(s)) if t]
        return _n(toks[-1]) if toks else _n(s)
    out = []
    for r in rows:
        rt = r.get("record_type", ""); ti = r.get("title", ""); jr = r.get("journal", "")
        au = r.get("first_author", ""); au_a = r.get("first_author_ascii", "") or fold_ascii(au)
        yr = str(r.get("year", "")); doi = str(r.get("doi", "")); fn = r.get("file_name", "")
        reasons = []
        articleish = rt in ("article", "book_chapter", "book", "preprint", "thesis", "conference", "manual")
        nti, njr = _n(ti), _n(jr)
        if articleish and nti and njr and (nti == njr or (len(nti) > 8 and (nti in njr or njr in nti) and abs(len(nti)-len(njr)) < 10)):
            reasons.append("title=journal")
        if articleish:
            toks = [t for t in fold_ascii(ti).lower().split() if len(t) > 2]
            if toks and all(t in JOURNAL_WORDS for t in toks): reasons.append("title=journalwords")
        if au and MOJI.search(au): reasons.append("author=mojibake")
        if au and re.search(r"\d", au): reasons.append("author=digit")
        if au.strip() in ("A","The","Author","Authors","Anonymous","Is","Eds","Introduction"): reasons.append("author=placeholder")
        if fold_ascii(au).lower() in JOURNAL_WORDS: reasons.append("author=journalword")
        if HTMLENT.search(ti) or HTMLENT.search(au): reasons.append("markup")
        wn = wellnamed(fn)
        if wn:
            f_au, f_yr, f_jr, f_ti = wn
            head = _n(re.split(r"[-_\s]", f_au)[0]) if f_au else ""
            is_section = _n(f_au) in SECTION or head in SECTION
            if not is_section:
                if f_au and au_a:
                    ka, kb = _surn(f_au), _surn(au_a)
                    # compound-surname tolerance: filename often keeps only the FIRST token
                    # ("Aguirre" for index "Aguirre de Carcer"), so also compare the index's
                    # FIRST surname token and accept a prefix relationship either way.
                    ka0 = _n(re.split(r"[\s\-]+", fold_ascii(f_au))[0]) if f_au else ""
                    kb0 = _n(re.split(r"[\s\-]+", fold_ascii(au_a))[0]) if au_a else ""
                    match = (ka[:5] == kb[:5] or ka in kb or kb in ka or
                             (ka0 and kb0 and (ka0 == kb0 or ka0[:5] == kb0[:5])))
                    if ka and kb and not match:
                        reasons.append("author!=filename")
                if f_ti and ti:
                    # token-subset comparison (order-independent, stopword/truncation-robust):
                    # a canonical slug drops stopwords + truncates, so require only that the
                    # smaller token set substantially overlaps the larger. Low overlap means
                    # the title field holds something OTHER than the paper title (journal name,
                    # a reference citation, body text, OCR garbage) -- a real disagreement.
                    ft, it = _ttok(f_ti), _ttok(ti)
                    if len(ft) >= 3 and len(it) >= 3:
                        if len(ft & it) / min(len(ft), len(it)) < 0.4:
                            reasons.append("title!=filename")
        if reasons:
            hi = {"title=journal","title=journalwords","author=mojibake","author=digit","author=journalword","author!=filename","author=placeholder"}
            sev = "HIGH" if (set(reasons) & hi) else "MED"
            out.append((fn, sev, "; ".join(reasons)))
    return out

# ==================================================================== RESOLVE (PROC.4 + PROC.6)
def crossref_lookup(doi, mailto, ua="sci-file-indexer/1.0"):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    hdr = {"User-Agent": "%s (mailto:%s)" % (ua, mailto)} if mailto else {"User-Agent": ua}
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r)["message"]

def crossref_search(query, mailto, ua="sci-file-indexer/1.0", rows=3):
    url = "https://api.crossref.org/works?query.bibliographic=" + urllib.parse.quote(query) + "&rows=%d" % rows
    hdr = {"User-Agent": "%s (mailto:%s)" % (ua, mailto)} if mailto else {"User-Agent": ua}
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r)["message"].get("items", [])

def parse_crossref(m):
    au = ""
    if m.get("author"):
        au = m["author"][0].get("family", "") or m["author"][0].get("name", "")
    yr = ""
    for k in ("published-print","published-online","issued","created"):
        # empty-nested-list default (double-open-bracket then close): avoids a letter right
        # after the double-open-bracket, which the toolkit scrub_verify wikilink guard flags.
        dp = m.get(k, {}).get("date-parts") or [[]]
        if dp and dp[0] and dp[0][0]:
            yr = str(dp[0][0]); break
    ti = (m.get("title") or [""])[0]
    if ti:
        ti = re.sub(r"\s+", " ", ti)[:200]
    jr = (m.get("container-title") or [""]); jr = jr[0] if jr else ""
    rt = TYPE_MAP.get(m.get("type", ""), "article")
    return au, yr, ti, jr, rt

def cmd_resolve(args):
    d = args.dir
    ixd = index_dir(d)
    index_path = args.index or os.path.join(ixd, "paper_index.csv")
    ov_path = args.overrides or os.path.join(ixd, OVERRIDES_NAME)
    raw_path = os.path.join(ixd, RAW_NAME)
    review_path = os.path.join(ixd, REVIEW_NAME)
    raw = {r["file_name"]: r for r in csv.DictReader(open(raw_path, encoding="utf-8"))}
    idx = {r["file_name"]: r for r in csv.DictReader(open(index_path, encoding="utf-8"))} if os.path.exists(index_path) else {}
    done = overrides_filenames(ov_path)
    mailto = args.mailto
    weak = [fn for fn, r in idx.items()
            if (not r["first_author"].strip() or not r["year"].strip())
            and not fn.lower().endswith((".csv", ".xlsx")) and fn not in done]
    out, un = [], []
    # live progress heartbeat: <index_dir>/_sfi_resolve_progress.txt = "done/total current_file"
    # (readable mid-run — resolve is a network pass over the weak set and can take many minutes).
    _rprog = os.path.join(ixd, "_sfi_resolve_progress.txt")
    _rn = len(weak); _ri = 0
    for fn in sorted(weak):
        _ri += 1
        if _ri == 1 or _ri % 20 == 0 or _ri == _rn:
            try:
                with open(_rprog, "w", encoding="utf-8") as _pf:
                    _pf.write("%d/%d %s\n" % (_ri, _rn, fn))
            except Exception:
                pass
        # PNAS supplement / dataset => route as supplement row (no crossref)
        pnas = is_pnas_supp(fn)
        if pnas:
            out.append([fn, "", "", "", "", pnas[0], "", "SI/dataset of " + pnas[1]]); continue
        doi = (raw.get(fn, {}).get("doi", "") or "").strip()
        note = "crossref:"
        if not doi:
            doi, dnote = derive_doi(fn)
            note = "cryptic+crossref:" if doi else note
        if doi:
            # Try the DOI and its variants (OCR char-confusion + OUP/Silverchair article-id suffix
            # strip): a raw "10.1093/treephys/tpab100/6330026" 404s but "10.1093/treephys/tpab100"
            # resolves. First variant that returns a record wins.
            m = None; used_doi = doi; last_err = ""
            for cand_doi in _ocr_doi_variants(doi):
                try:
                    m = crossref_lookup(cand_doi, mailto); time.sleep(0.3)
                    used_doi = cand_doi; break
                except Exception as e:
                    last_err = str(e)[:28]; m = None
            if m is None:
                un.append((fn, "xref-fail:" + last_err)); continue
            au, yr, ti, jr, rt = parse_crossref(m)
            note = note + ("doi-suffix-stripped:" if used_doi != doi else "")
            out.append([fn, au, yr, ti, jr, rt, "", note + used_doi]); continue
        # NO DOI: try the DOI-free title(+author,+year) path (pre-DOI / grey lit). Use the best
        # bibliographic signal already on the index row — embedded title + author, or the wellname
        # parse. Verified by the same gate as OCR ("if you get them right"): title fuzzy + year +
        # the row's surname must appear among the hit's authors. Never fabricates: a gate-fail => no-doi.
        row = idx.get(fn, {})
        cand_ti = (row.get("title", "") or "").strip()
        cand_au = _family_name(row.get("first_author", "") or "")
        cand_yr = (row.get("year", "") or "").strip()
        # A mined author that is a typesetter/role artifact (e.g. "Karen", "Forestry") must NOT gate
        # the search — it would veto a correct title-only hit (defect #45). Read the file's own page-1/2
        # text ONCE as content-truth: (a) trust the mined surname as a search GATE only if it is
        # plausible AND actually appears in the document; (b) content-verify a title-only hit's author
        # against the same text (never fabricate).
        ptext = ""
        try:
            _ptt = tool("pdftotext")
            if _ptt:
                ptext = run([_ptt, "-f", "1", "-l", "2", "-layout", os.path.join(d, fn), "-"], 60).stdout
        except Exception:
            ptext = ""
        use_au = ""
        if _plausible_author(cand_au) and ptext and cand_au.lower() in ptext.lower():
            use_au = cand_au
        if cand_ti and _title_ok(cand_ti) and not _looks_like_copyright(cand_ti):
            try:
                q = cand_ti + (" " + use_au if use_au else "") + (" " + cand_yr if cand_yr else "")
                items = crossref_search(q, mailto); time.sleep(0.3)
                hit = _pick_search_hit(items, cand_ti, cand_yr, use_au)
                if hit and not use_au:
                    if not _author_in_text(hit, ptext):
                        hit = None
                if hit:
                    au, yr, ti, jr, rt = parse_crossref(hit)
                    hit_doi = (hit.get("DOI") or "").strip()
                    gate = ("search:title+author+year" if (use_au and cand_yr)
                            else ("search:title+author" if use_au else "search:title-only+content-verified"))
                    out.append([fn, au, yr, ti, jr, rt, hit_doi, gate]); continue
            except Exception:
                pass
        un.append((fn, "no-doi; title+author search gate-failed" if cand_ti else "no-doi")); continue
    with open(review_path, "w", encoding="utf-8") as f:
        f.write("".join("\t".join(r) + "\n" for r in out))
    print("RESOLVED %d | UNRESOLVED %d -> %s (REVIEW before apply)" % (len(out), len(un), review_path))
    for r in out:
        print("  + %-46s | %-16s %-6s | %.42s" % (r[0][:46], r[1][:16], r[2], r[3]))
    for fn, w in un:
        print("  - %-46s | %s" % (fn[:46], w))

# ==================================================================== OCR (PROC.5 — S3)
# ── ILL / document-delivery COVER-SHEET parser ───────────────────────────────────────────────────
# Scanned PDFs from interlibrary loan (Arizona "Document Delivery", RapidILL, Odyssey, Ariel) carry a
# librarian-entered cover sheet as page 1 with LABELED fields — the most accurate metadata source in
# the whole pipeline (better than body-text mining, better than a DOI-type guess). The generic title
# miner grabs the delivery-service banner ("University of Arizona Document Delivery") instead, so parse
# the labels explicitly. Two layouts: inline "Label: value" (Arizona) and column-separated label-block/
# value-block (RapidILL). Never fabricates: a field with no label match stays blank.
_ILL_MARKERS = re.compile(r"document delivery|rapid #|rapidill|interlibrary|odyssey|ariel|"
                          r"this material may be protected|article title\s*:|chapter title\s*:|"
                          r"\blender\s*:|\bborrower\s*:", re.I)
_ILL_FIELD_PATS = [("title",   [r"article title", r"chapter title"]),
                   ("author",  [r"article author", r"chapter author", r"book author"]),
                   ("journal", [r"user journal title", r"user book title", r"journal title", r"book title"]),
                   ("year",    [r"month/year", r"\byear\b", r"\bdate\b"])]
_ILL_STOP = re.compile(r"(trans\.?\s*#|location\s*:|call\s*#|item\s*#|volume\s*:|issue\s*:|isbn|issn|oclc|"
                       r"lender\s*:|borrower\s*:|type\s*:|pages?\s*:|edition\s*:|publisher\s*:|reason not|"
                       r"paged by|customer info|status\s*:|imprint\s*:|month/year|user (journal|book)|"
                       r"journal title|book title|article (title|author)|chapter (title|author)|book author|"
                       r"cross ref|rapid #|\bLIBRARY\b|call number)", re.I)
_ILL_LABEL_ANY = re.compile(r"[\s.\-*•]*(" + "|".join(p for _, ps in _ILL_FIELD_PATS for p in ps) +
                            r")\s*:\s*(.*)", re.I)
def _ill_clean(v):
    m = _ILL_STOP.search(v)
    if m:
        v = v[:m.start()]
    return re.sub(r"\s+", " ", v).strip(" :.-•*")
def _parse_jstor_cover(text):
    """JSTOR delivers a standard cover page: the article TITLE (one or more lines), then labeled
    "Author(s):", "Source: <journal>, <year>, Vol...", "Published by:", "Stable URL: .../stable/<id>".
    Highly regular and a common source, so parsed directly. Returns author(family)/year/title/journal
    or None."""
    tl = text.lower()
    if "stable url" not in tl or "jstor" not in tl:
        return None
    lines = [l.strip() for l in text.splitlines()]
    title_lines = []
    for l in lines:                                          # title = non-empty lines before Author(s):
        if re.match(r"author\(s\)\s*:", l, re.I):
            break
        if re.match(r"(source|published by|stable url|reviewed work)\s*:", l, re.I):
            break
        if l:
            title_lines.append(l)
    got = {}
    if title_lines:
        ti = _ill_clean(" ".join(title_lines[:4]))
        ti = re.sub(r"^\d{1,4}\s+(?=[A-Za-z])", "", ti)     # strip a leading page-number token ("454 ")
        got["title"] = ti
    for l in lines:
        m = re.match(r"author\(s\)\s*:\s*(.+)", l, re.I)
        if m:
            got["author"] = m.group(1).split(" and ")[0].split(",")[0].split(";")[0].strip()
        m = re.match(r"source\s*:\s*(.+)", l, re.I)
        if m:
            src = m.group(1)
            ym = re.search(r"\b(18|19|20)\d{2}\b", src)
            if ym:
                got["year"] = ym.group(0)
            jm = re.match(r"([A-Za-z\u00c0-\u00ff .&'\-]+?)[ ,]+(?:\d|Vol|No\b)", src)
            if jm:
                got["journal"] = jm.group(1).strip(" ,.")
    if not (got.get("title") or got.get("author")):
        return None
    return dict(author=_family_name(got.get("author", "")) if got.get("author") else "",
                year=got.get("year", ""), title=got.get("title", ""),
                journal=got.get("journal", ""), rt="article")

def parse_cover_sheet(text):
    """Extract labeled metadata from an ILL/document-delivery or JSTOR cover sheet. Returns a dict
    with any of author (family name)/year/title/journal/rt found, or None if not a cover sheet."""
    if not text:
        return None
    js = _parse_jstor_cover(text)
    if js:
        return js
    if not _ILL_MARKERS.search(text):
        return None
    lines = [ln.rstrip() for ln in text.splitlines()]
    got = {}
    for i, ln in enumerate(lines):
        m = _ILL_LABEL_ANY.match(ln)
        if not m:
            continue
        lab = m.group(1).lower(); val = m.group(2)
        fld = next((f for f, ps in _ILL_FIELD_PATS if any(re.search(p, lab, re.I) for p in ps)), None)
        if not fld:
            continue
        this_rank = next((k for f, ps in _ILL_FIELD_PATS if f == fld
                          for k, p in enumerate(ps) if re.search(p, lab, re.I)), 99)
        if fld in ("title", "journal"):                      # title/journal may wrap to next lines
            j = i + 1
            while j < len(lines) and lines[j].strip():
                nx = lines[j].strip()
                if _ILL_LABEL_ANY.match(nx) or _ILL_STOP.match(nx):
                    break
                seg = _ill_clean(nx)
                if seg:
                    val += " " + seg
                if len(val) > 250:
                    break
                j += 1
        cv = _ill_clean(val)
        if cv and (fld not in got or this_rank < got.get(fld + "__rank", 99)):
            got[fld] = cv; got[fld + "__rank"] = this_rank
    # COLUMN-SEPARATED fallback (RapidILL book records): a block of bare "LABEL:" lines followed by a
    # block of values, paired in order.
    if not got.get("title") and not got.get("author"):
        labs, vals = [], []
        for ln in lines:
            s = ln.strip()
            mm = re.fullmatch(r"([A-Z][A-Z /]{2,}):", s)
            if mm:
                key = mm.group(1).lower()
                labs.append(next((f for f, ps in _ILL_FIELD_PATS if any(re.search(p, key, re.I) for p in ps)), None))
            elif s and not _ILL_STOP.match(s) and s.lower() not in ("book chapter", "article", "article cc:ccl"):
                vals.append(s)
        for k, fld in enumerate(labs):
            if fld and k < len(vals) and fld not in got:
                got[fld] = _ill_clean(vals[k])
    if "year" in got:
        ym = re.search(r"(19|20)\d{2}", got["year"]); got["year"] = ym.group(0) if ym else ""
    if not (got.get("title") or got.get("author")):
        return None
    rt = "book_chapter" if re.search(r"book chapter|chapter title|book author|book title", text, re.I) else "article"
    return dict(author=_family_name(got.get("author", "")) if got.get("author") else "",
                year=got.get("year", ""), title=got.get("title", ""),
                journal=got.get("journal", ""), rt=rt)

def cmd_ocr(args):
    d = args.dir
    ixd = index_dir(d)
    raw_path = os.path.join(ixd, RAW_NAME)
    review_path = os.path.join(ixd, REVIEW_NAME)
    ov_path = args.overrides or os.path.join(ixd, OVERRIDES_NAME)
    mailto = args.mailto
    workdir = os.path.join(ixd, "_ocr"); os.makedirs(workdir, exist_ok=True)
    ocrmypdf, tesseract, pdftoppm, pdftotext, pdffonts = (
        tool("ocrmypdf"), tool("tesseract"), tool("pdftoppm"), tool("pdftotext"), tool("pdffonts"))
    if not (ocrmypdf or (tesseract and pdftoppm)):
        sys.exit("FATAL: need `ocrmypdf` (preferred) OR `tesseract`+`pdftoppm`. Install: "
                 "brew install ocrmypdf tesseract  (macOS)  |  apt-get install ocrmypdf tesseract-ocr  (Linux)")
    raw = {r["file_name"]: r for r in csv.DictReader(open(raw_path, encoding="utf-8"))} if os.path.exists(raw_path) else {}
    index_path = args.index or os.path.join(ixd, "paper_index.csv")
    idx = {r["file_name"]: r for r in csv.DictReader(open(index_path, encoding="utf-8"))} if os.path.exists(index_path) else {}
    done = overrides_filenames(ov_path)
    # PROC.3 TRIAGE ordering: step-2 (author AND year AND title => OK; STOP) precedes step-3 (scanned).
    # So a file that already resolved is NEVER an OCR candidate. Candidate == still WEAK in the
    # current index AND passes the scanned test (chars_page1 < threshold OR n_fonts == 0 => no text
    # layer at all) AND not already curated. Absent an index (ocr run before build), fall back to
    # the scanned test alone so the stage still works standalone.
    def weak_in_index(fn):
        r = idx.get(fn)
        if r is None:
            return True  # not yet built => let the scanned test decide
        return (not r.get("first_author", "").strip()) or (not r.get("year", "").strip()) or (not r.get("title", "").strip())
    cand = []
    for fn, r in raw.items():
        if r.get("ext") != "pdf" or fn in done:
            continue
        cp1 = r.get("chars_page1", "")
        try:
            sparse = int(cp1) < SCANNED_CHAR_THRESHOLD if cp1 != "" else False
        except ValueError:
            sparse = False
        no_fonts = r.get("n_fonts", "") == "0"     # explicit no-text-layer (strong signal)
        if (sparse or no_fonts) and weak_in_index(fn):
            cand.append(fn)
    out, un = [], []
    for fn in sorted(cand):
        stem = re.sub(r"\.pdf$", "", fn, flags=re.I)
        txtpath = os.path.join(workdir, stem + ".txt")
        if os.path.exists(txtpath):                       # cache: skip already-OCR'd
            text = open(txtpath, encoding="utf-8", errors="replace").read()
            pages = text.split("\f") if "\f" in text else [text]   # cache stores all pages, FF-joined
        else:
            pages = []
            inpath = os.path.join(d, fn)
            if ocrmypdf:
                sidecar = os.path.join(workdir, stem + ".pdf")
                run([ocrmypdf, "--skip-text", "--rotate-pages", "--deskew", "--language", "eng",
                     "--output-type", "pdf", inpath, sidecar], 900)
                # FRONT-MATTER SCAN (OCR): read up to PAGE_SCAN_CAP pages, lock onto first strong page.
                multi = run([pdftotext, "-f", "1", "-l", str(PAGE_SCAN_CAP), "-layout", sidecar, "-"], 180).stdout if os.path.exists(sidecar) else ""
                pages = [p for p in multi.split("\f") if p.strip()] if multi else []
                _si, text = scan_pages_for_signal(pages) if pages else (0, "")
            else:
                # FRONT-MATTER SCAN (OCR, page-by-page): rendering is expensive (~5-30s/page), so
                # render+OCR one page at a time and STOP at the first strong title/author signal —
                # skips cover sheets / blank leaves without paying to OCR the whole document.
                base = os.path.join(workdir, stem)
                pages = []
                best_score, best_text = -1, ""
                # Render+OCR page by page (expensive: ~5-30s/page). KEEP every page's text — metadata is
                # not always on the first strong page: an ILL cover sheet precedes the real title page,
                # a book's title/author/year can be split across a title page and a copyright page, and a
                # DOI may sit in a footer on any page. So accumulate all pages up to the cap, still
                # short-circuit RENDERING once we've locked a strong title page AND seen a cover sheet or
                # DOI (enough to resolve), to avoid OCRing an entire long scan.
                seen_cover, seen_doi, strong_hit = False, False, False
                for pgnum in range(1, PAGE_SCAN_CAP + 1):
                    run([pdftoppm, "-r", "300", "-png", "-f", str(pgnum), "-l", str(pgnum), inpath, base], 120)
                    png = None
                    for suff in ("-%d" % pgnum, "-%02d" % pgnum, "-%d" % pgnum, "-0%d" % pgnum):
                        cand_png = base + suff + ".png"
                        if os.path.exists(cand_png):
                            png = cand_png; break
                    if not png:
                        break                                   # no more pages
                    ptext = run([tesseract, png, "stdout", "--psm", "1", "-l", "eng"], 300).stdout
                    try:
                        os.remove(png)
                    except OSError:
                        pass
                    pages.append(ptext)
                    sc = page_signal(ptext)
                    if sc > best_score:
                        best_score, best_text = sc, ptext       # best single page (title/author source)
                    if sc >= 2:
                        strong_hit = True
                    if _ILL_MARKERS.search(ptext):
                        seen_cover = True
                    if DOI_RE.search(ptext):
                        seen_doi = True
                    # stop RENDERING once we have a strong title page plus a resolution key already seen
                    if strong_hit and (seen_doi or seen_cover) and pgnum >= 2:
                        break
                text = best_text
            # cache ALL pages (form-feed joined) so a re-run has the full front matter, not one page
            open(txtpath, "w", encoding="utf-8").write("\f".join(pages) if pages else text)
        # MINE metadata (priority order). `text` is the best single title page; `pages` (when present)
        # is every scanned front-matter page — search DOI/year across ALL of them, since either can sit
        # on a page other than the title page.
        au = yr = ti = jr = ""; rt = "article"; doi = ""; ti_ocr = ""; au_ocr = ""
        allpages = pages if pages else [text]
        alltext = "\n".join(allpages)
        # (0) COVER SHEET (ILL/document-delivery): librarian-entered labeled fields beat everything.
        # Scan each page (the cover sheet is usually page 1 but not always) and take the first parse.
        cover = None
        for _pg in allpages:
            cover = parse_cover_sheet(_pg)
            if cover:
                break
        # DOI/year across all pages (title page may lack the DOI that a footer/copyright page carries)
        m = DOI_RE.search(alltext)
        if m:
            doi = m.group(0).rstrip(".,;)]}>")
        ym = re.search(r"\b(19|20)\d{2}\b", alltext)
        if ym:
            yr = ym.group(0)
        if cover and cover.get("year"):
            yr = cover["year"]              # cover-sheet year is librarian-entered => authoritative
        # try CrossRef by DOI (best), then gated title search
        resolved = False
        if doi:
            for cand_doi in _ocr_doi_variants(doi):
                try:
                    mm = crossref_lookup(cand_doi, mailto); time.sleep(0.3)
                    au, yr2, ti, jr, rt = parse_crossref(mm)
                    yr = yr2 or yr
                    out.append([fn, au, yr, ti, jr, rt, "", "ocr+crossref:" + cand_doi]); resolved = True; break
                except Exception:
                    continue
        if not resolved:
            # DOI-FREE resolution path (the primary path for pre-DOI + grey literature): recover the
            # canonical record from title + author (+ year). This is NOT a fallback for a missing DOI —
            # for a 1970s report or a scanned journal article there IS no DOI, yet title+author is a
            # sufficient bibliographic key. The _pick_search_hit gate verifies the match ("if you get
            # them right"): title fuzzy + year proximity + the mined surname must be among the hit's authors.
            # Prefer cover-sheet title/author (labeled, exact) over body-text mining for the search key.
            ti_ocr = (cover.get("title") if cover and cover.get("title") else "") or _ocr_title(text)
            au_ocr = (cover.get("author") if cover and cover.get("author") else "") or _ocr_author(text)
            if ti_ocr and _title_ok(ti_ocr):
                try:
                    q = ti_ocr + (" " + au_ocr if au_ocr else "") + (" " + yr if yr else "")
                    items = crossref_search(q, mailto); time.sleep(0.3)
                    hit = _pick_search_hit(items, ti_ocr, yr, au_ocr)
                    if hit:
                        au, yr2, ti, jr, rt = parse_crossref(hit)
                        yr = yr2 or yr
                        gate = "ocr:title+author+year" if (au_ocr and yr) else \
                               ("ocr:title+author" if au_ocr else "ocr:title-only")
                        out.append([fn, au, yr, ti, jr, rt, "", gate]); resolved = True
                except Exception:
                    pass
        if not resolved:
            # UNVALIDATED but keep ALL correct mined bits: year + journal-head + mined title + mined
            # author (the document's own page-1 text — correct-but-unvalidated, NOT fabricated). The
            # confidence guard keeps the row LOW because the note is marked UNVALIDATED, regardless of
            # how many fields are filled. For grey lit that never entered CrossRef, these mined fields
            # are the best metadata that will ever exist; discarding them loses real, correct signal.
            if cover and (cover.get("title") or cover.get("author")):
                # ILL cover sheet gives labeled, librarian-entered metadata — the best that will ever
                # exist for a scan with no DOI and no CrossRef hit. Emit it (still UNVALIDATED => LOW).
                c_ti = cover.get("title", ""); c_au = cover.get("author", "")
                c_jr = cover.get("journal", "") or _ocr_journal(text)
                c_rt = cover.get("rt", "article")
                un.append((fn, "cover-sheet; labeled fields (UNVALIDATED)"))
                out.append([fn, c_au, cover.get("year", "") or yr, c_ti, c_jr, c_rt, "",
                            "ocr: ILL cover-sheet labeled fields, UNVALIDATED (not found in CrossRef)"])
            else:
                jr_head = _ocr_journal(text)
                mined_ti = ti_ocr if (ti_ocr and _title_ok(ti_ocr)) else ""
                if mined_ti or au_ocr:
                    un.append((fn, "image-only; mined title/author (UNVALIDATED)"))
                    out.append([fn, au_ocr, yr, mined_ti, jr_head, "article", "", "ocr: image-only; mined title/author, UNVALIDATED (not found in CrossRef)"])
                else:
                    un.append((fn, "image-only; ocr-unresolved"))
                    out.append([fn, "", yr, "", jr_head, "article", "", "ocr: image-only; unresolved"])
    with open(review_path, "a" if os.path.exists(review_path) else "w", encoding="utf-8") as f:
        f.write("".join("\t".join(r) + "\n" for r in out))
    print("OCR candidates=%d | resolved=%d | unresolved=%d -> %s (REVIEW)" % (len(cand), len(out) - len(un), len(un), review_path))
    for r in out:
        print("  %s %-40s | %.40s" % ("+" if r[3] or r[1] else "-", r[0][:40], (r[7] if len(r) > 7 else "")))

def _ocr_doi_variants(doi):
    seen = set()
    def emit(v):
        if v and v not in seen:
            seen.add(v); return True
        return False
    if emit(doi):
        yield doi
    subs = [("l", "1"), ("O", "0"), ("o", "0"), (",", ".")]
    for a, b in subs:
        v = doi.replace(a, b)
        if emit(v):
            yield v
    # PUBLISHER ARTICLE-ID SUFFIX: OUP / Silverchair (Tree Physiology, etc.) append a numeric
    # article-id path segment to the real DOI — "10.1093/treephys/tpab100/6330026" 404s, while
    # "10.1093/treephys/tpab100" resolves. Peel trailing "/segment" one at a time, keeping at least
    # prefix + one path segment (10.xxxx/yyyy). Also try dropping a trailing ".<digits>" fragment.
    parts = doi.split("/")
    while len(parts) > 2:
        parts = parts[:-1]
        v = "/".join(parts)
        if emit(v):
            yield v
    v2 = re.sub(r"\.\d+$", "", doi)
    if v2 != doi and emit(v2):
        yield v2

_FUNCTION_WORDS = {"a","an","the","of","for","and","on","in","to","with","by","from",
                   "at","as","or","via","into","over","under","between","during"}
_AFFIL_KW = re.compile(r"\b(institute|univers|department|laborator|centre|center|"
                       r"national|corporation|company|\binc\b|\bltd\b|academy|"
                       r"foundation|society|administration|bureau|division)\b", re.I)
_HEADER_KW = re.compile(r"\b(technical report|working paper|preprint|memo(randum)?|draft|"
                        r"discussion paper|white paper|proceedings|reprinted|"
                        r"downloaded from|all rights reserved|doi:)\b", re.I)

def _tokens(s):
    return [t for t in re.split(r"[\s,]+", s.strip()) if t]

def _looks_like_authors(s):
    # STOP-at-author detection for the title assembler. Three signals, tuned so a title tail like
    # "Horizontal Surfaces" (Title-Case, no initials) is NOT mistaken for an author line, while
    # "Richard E. Bird" / "Jane Q Testperson" / "MASSMAN, W. J." ARE.
    if re.search(r"\b[A-Z]\.\s*[A-Z]", s):          # period-initials: "Richard E. Bird", "R. E. Bird"
        return True
    if re.search(r"\bet al\.?\b", s, re.I):         # "Smith et al."
        return True
    toks = _tokens(s)
    if not (2 <= len(toks) <= 6) or len(s) > 60:
        return False
    # no lowercase function words (titles carry "for/and/of/on"; name lists do not)
    if any(t.lower() in _FUNCTION_WORDS for t in toks):
        return False
    # name-shaped: every token capitalised or an initial, AND at least one BARE single-letter
    # initial present ("Q" in "Jane Q Testperson") — the discriminator vs a Title-Case title tail.
    cap_or_init = all(re.match(r"^[A-Z]([a-z'’.-]+|\.?)$", t) or re.match(r"^[A-Z]{2,}$", t) for t in toks)
    has_bare_initial = any(re.match(r"^[A-Z]\.?$", t) for t in toks)
    return cap_or_init and has_bare_initial

def _looks_like_header(s):
    # running-heads / report codes / boilerplate that sit ABOVE the title on scanned first pages
    if _HEADER_KW.search(s):
        return True
    if re.search(r"\b[A-Z]{2,}[/-]\S*\d", s):       # report number "SERI/TR-642-761"
        return True
    letters = [c for c in s if c.isalpha()]
    if len(letters) >= 4 and all(c.isupper() for c in letters) and len(_tokens(s)) <= 3:
        return True                                  # ALL-CAPS SHORT line (<=3 words) = running-head
    # A longer ALL-CAPS line is usually the TITLE itself (journals set titles in caps), NOT a header —
    # unless it is a known section/document-type banner.
    if _SECTION_BANNER.match(s.strip()):
        return True
    return False

# Section / document-type banners that OCR miners must NOT grab as a title ("GENERAL ARTICLE",
# "REVIEW ARTICLES", "RESEARCH ARTICLE", "LETTERS TO NATURE", "Abstract:", "Introduction").
_SECTION_BANNER = re.compile(r"^(special\s+feature|special\s+issue|original|research|review|feature)?[:\s]*"
                             r"(general|research|review|original|short|brief|invited|feature|rapid|regular)?\s*"
                             r"(article|articles|communication|communications|letter|letters|report|reports|"
                             r"review|reviews|perspective|note|notes|editorial|correspondence|paper|papers|"
                             r"research\s+article)\b\s*$"
                             r"|^(letters?\s+to\s+\w+)\s*$"
                             r"|^(special\s+feature|news\s*(&|and)\s*views)\b.*$"
                             r"|^(abstract|introduction|summary|keywords?|contents|acknowledge?ments?)\b\s*:?\s*$",
                             re.I)

_REPO_COVER = re.compile(r"open repository|institutional repository|open archive|"
                         r"(this is|is) the (author|accepted|submitted|postprint|pre-?print|published) "
                         r"(version|manuscript|accepted)|"
                         r"downloaded from .{0,60} by .{0,40} (user|library) on|"
                         r"\beprints\b|escholarship|hal[- ]archives|"
                         r"posted (with permission|at)|deposited (in|at)", re.I)
def _is_repo_cover(text):
    if not text:
        return False
    return bool(_REPO_COVER.search(text[:600]))

def _title_line_ok(s):
    # a title line (to START a block): >=2 words, alpha-dominant, not a bare code/number/month/header
    if " " not in s or len(s) < 8:
        return False
    if sum(c.isalpha() or c.isspace() for c in s) / max(len(s), 1) <= 0.7:
        return False
    if _looks_like_header(s):
        return False
    return True

def _title_cont_ok(s):
    # a title CONTINUATION line (block already started): same alpha/word floor, but ALL-CAPS is
    # allowed — a caps line following a caps title line is title continuation ("BENEATH FOREST
    # CANOPIES"), NOT a running-head. Still reject report-codes and boilerplate keyword headers.
    if " " not in s or len(s) < 8:
        return False
    if sum(c.isalpha() or c.isspace() for c in s) / max(len(s), 1) <= 0.7:
        return False
    if _HEADER_KW.search(s) or re.search(r"\b[A-Z]{2,}[/-]\S*\d", s):   # boilerplate / report-code only
        return False
    return True

def _ocr_title(text):
    # ASSEMBLE a (possibly multi-line) title block. Skip leading headers/running-heads, find the first
    # title-like line, then append contiguous title-like lines until a blank line, an author or
    # affiliation line, 5 lines, or 200 chars. Grey-lit titles routinely wrap across 3-4 OCR lines;
    # a first-line-only grab truncates them (and a too-short title fails the CrossRef search gate).
    lines = [ln.strip() for ln in text.splitlines()]
    block, started, blanks = [], False, 0
    for idx, s in enumerate(lines):
        if not started:
            if _title_line_ok(s) and not _looks_like_authors(s) and not _AFFIL_KW.search(s) \
               and not _looks_like_journal_line(s) and not _SECTION_BANNER.match(s):
                block.append(s); started = True
            continue
        # in-block stop conditions (author/affil/journal/length). A blank line does NOT immediately
        # stop the block: OCR frequently inserts a blank between the two lines of a wrapped title
        # ("... in dry" / blank / "tropics"). Allow ONE blank, then require the next line to continue.
        if not s:
            blanks += 1
            if blanks > 1:
                break
            # peek: is the previous title line dangling (ends in a connective) OR is the next non-blank
            # a short continuation? if neither, the title is complete -> stop.
            prev = block[-1] if block else ""
            nxt = next((l for l in lines[idx + 1:] if l.strip()), "")
            dangling = bool(re.search(r"\b(in|of|and|the|a|an|for|to|with|on|from|by|as|or)$", prev, re.I))
            short_cont = nxt and len(_tokens(nxt)) <= 3 and not _looks_like_authors(nxt) \
                         and not _looks_like_journal_line(nxt) and not _AFFIL_KW.search(nxt) \
                         and not _SECTION_BANNER.match(nxt) and nxt[:1].islower()
            if not (dangling or short_cont):
                break
            continue
        if _looks_like_authors(s) or _AFFIL_KW.search(s) or _looks_like_journal_line(s) \
           or _SECTION_BANNER.match(s) or len(" ".join(block)) > 200 or len(block) >= 6:
            break
        # accept a continuation line: normal cont-ok, OR a short line right after a blank/dangling line
        if _title_cont_ok(s) or (blanks and len(s) >= 3 and sum(c.isalpha() or c.isspace() for c in s) / max(len(s), 1) > 0.7):
            block.append(s); blanks = 0
        else:
            break
    if block:
        t = re.sub(r"\s+", " ", " ".join(block))[:200]
        t = re.sub(r"^(abstract|summary|introduction|keywords?)\s*:?\s*", "", t, flags=re.I)  # strip section prefix
        return t.strip()
    # fallback: original first-qualifying-line behavior (never regress a single-line title)
    for ln in lines:
        if len(ln) >= 12 and sum(c.isalpha() or c.isspace() for c in ln) / max(len(ln), 1) > 0.7 \
           and not _looks_like_header(ln):
            return re.sub(r"\s+", " ", ln)[:200]
    return ""

def _ocr_author(text):
    # Mine the FIRST author's family name from page-1 OCR — the second half of the title+author key.
    # Walk past the title block, return the surname of the first author-like line. Blank if none
    # (blank is safe: the search then gates on title+year only, never fabricates an author).
    lines = [ln.strip() for ln in text.splitlines()]
    ti = _ocr_title(text)
    ti_norm = re.sub(r"\s+", " ", ti).lower()
    passed_title = not ti
    for s in lines:
        if not passed_title:
            if s and s.lower() in ti_norm:
                continue
            if s and _title_line_ok(s) and s.lower() in ti_norm:
                continue
            # once we hit a line that is NOT part of the title, allow author matching
            if s and re.sub(r"\s+", " ", s).lower() not in ti_norm:
                passed_title = True
        if passed_title and s and _looks_like_authors(s) \
           and not _AFFIL_KW.search(s) and not _looks_like_journal_line(s):
            return _family_name(s)
    return ""

_JOURNAL_KW = re.compile(r"\b(journal|review|letters|proceedings|transactions|bulletin|annals|"
                         r"acta|phytologist|nature|science|ecology|physics|chemistry|biology|"
                         r"quarterly|annual|advances|reports|research|studies)\b", re.I)

def _looks_like_journal_line(s):
    # A citation/journal line ("New Phytologist, 2019", "J. Ecol. 88(3)") is NOT an author line and is
    # not a title. Distinguishing it from a TITLE is delicate: journal-name words ("ecology", "nature",
    # "biology", "research") appear constantly INSIDE article titles ("Leaf-colonizing lichens: their
    # diversity, ecology"). So a journal keyword ALONE is not enough — it must co-occur with citation
    # STRUCTURE (a year, a volume(issue), or a page range), OR the line must be dominated by the journal
    # name (short line, journal keyword, no sentence-like title punctuation).  [MERGED: B's
    # citation-structure gate + A's abbreviated-masthead journal-vocabulary gate, defect #45.]
    has_year = bool(re.search(r"\b(19|20)\d{2}\b", s))
    has_volissue = bool(re.search(r"\b\d+\s*\(\d+\)", s))          # "88(3)"
    has_pages = bool(re.search(r"\b\d+\s*[-\u2013]\s*\d+\b", s))        # "135-147"
    has_kw = bool(_JOURNAL_KW.search(s))
    if re.search(r"\b(19|20)\d{2}\b\s*$", s.strip()):               # ends in a year => citation
        return True
    if has_volissue:                                                  # explicit vol(issue) => citation
        return True
    if has_kw and (has_year or has_volissue or has_pages):            # journal word + citation numbers
        return True
    if has_kw and len(_tokens(s)) <= 4 and ":" not in s and "," not in s:   # short line ~= bare journal name
        return True
    # Abbreviated-journal masthead ("Proc. Natl. Acad. Sci. USA", "J. Am. Chem. Soc.", "Trends Ecol.
    # Evol."): >=2 tokens drawn from a KNOWN journal-abbreviation vocabulary. Anchored on journal words
    # specifically so it never fires on a personal-initials author line ("MARK D. HUNTER, GEORGE C.
    # VARLEY") — those initials are single letters, not journal words (defect #45; A-side gate).
    toks = re.findall(r"[A-Za-z]+", s)
    if len(toks) >= 2:
        jabbr = sum(1 for t in toks if t.lower() in _JOURNAL_ABBR)
        if jabbr >= 2:
            return True
    return False

def _family_name(s):
    # Return the FIRST author's family name (the first-author key).
    # "Bird, R. E." -> Bird ; "Richard E. Bird" -> Bird ; "MASSMAN, W. J." -> Massman ;
    # "Jane Q Testperson" -> Testperson ; "J. A. Smith and R. Jones" -> Smith (FIRST, not last).
    s = re.sub(r"\bet al\.?\b", "", s, flags=re.I).strip(" .,")
    # A leading "Surname, Initials" (comma BEFORE any author separator) is surname-first form.
    sep = re.search(r"\s+(and|&)\s+|;", s)
    comma = s.find(",")
    if comma != -1 and (sep is None or comma < sep.start()):
        cand = (_tokens(s.split(",")[0]) or [""])[-1]     # "Bird, R. E." -> Bird
    else:
        first = re.split(r"\s+(?:and|&)\s+|;", s)[0]       # first author of an "A and B" list
        multi = [t for t in _tokens(first) if re.match(r"^[A-Z][a-z'’.-]+$", t) or re.match(r"^[A-Z]{2,}$", t)]
        cand = multi[-1] if multi else ""                 # last name-token of the FIRST author
    cand = re.sub(r"[^A-Za-z'’-]", "", cand)
    return cand[:1].upper() + cand[1:].lower() if cand else ""

def _title_ok(t):
    if len(t) < OCR_TITLE_MIN:
        return False
    nonalpha = sum(1 for c in t if not (c.isalnum() or c.isspace())) / max(len(t), 1)
    return nonalpha <= OCR_TITLE_MAX_NONALPHA

def _ocr_journal(text):
    m = re.search(r"([A-Z][A-Za-z ]{4,40})\s+\d+\s*\(\d+\)", text)
    return clean(m.group(1)) if m else ""

def page_signal(text):
    """Score a single page's text for a strong title/author signal (0-3). Used by the front-matter
    forward-scan: a cover sheet / blank leaf / running-head-only page scores ~0; the real title
    page scores high. Signals: a DOI present, a gate-passing mined title, a mined author surname."""
    if not text or not text.strip():
        return 0
    # ILL cover sheets and repository/proxy cover pages precede the real title page. Score them 0 so
    # the forward-scan skips them — UNLESS the page ALSO carries a gate-passing title (some cover
    # sheets embed the title), in which case fall through to normal scoring. A cover page's own
    # labeled fields are still mined later via parse_cover_sheet(); here we only want the scanner to
    # prefer the real article page when one exists.
    if _is_repo_cover(text) or _ILL_MARKERS.search(text):
        ti0 = _ocr_title(text)
        # A cover page's mined "title" is usually the repository/service name itself ("Zurich Open
        # Repository and", "University of Arizona Document Delivery"). Score 0 unless the mined title
        # is a REAL article title — i.e. gate-passes AND does not itself read as repository/publisher
        # boilerplate. This makes the forward-scan prefer the real article page that follows.
        looks_boilerplate = bool(_is_repo_cover(ti0) or _ILL_MARKERS.search(ti0) or
                                 re.search(r"\b(repository|archive|library|delivery|university|"
                                           r"downloaded|permission)\b", ti0, re.I)) if ti0 else True
        if not (ti0 and _title_ok(ti0)) or looks_boilerplate:
            return 0
    s = 0
    if DOI_RE.search(text):
        s += 1
    ti = _ocr_title(text)
    if ti and _title_ok(ti):
        s += 1
    if _ocr_author(text):
        s += 1
    return s

def scan_pages_for_signal(pages):
    """Given an ordered list of per-page texts, return (best_index, best_text) for the title page.
    Front-matter (covers / blank leaves) scores low and is skipped; the real title page wins.

    Selection order (defect #45 — was: first page to reach composite signal >=2, which let a later
    BODY page's spurious fragment-title+garbage-author score 2 and beat page 1's genuine title):
      1) EARLIEST page whose mined title passes the title gate AND is not a copyright/masthead line
         AND does not look like a mid-sentence body fragment — this is the title page. Its author may
         be un-mineable (full-name bylines, OCR-mangled initials) and that is fine; title+year resolves.
      2) else the earliest page with composite signal >=2,
      3) else the highest composite score, else the first non-empty page.
    Never fabricates — it only picks WHICH page's own text to mine from."""
    def _is_body_fragment(ti):
        # a real title does not open mid-sentence: lowercase-leading, or opening with a reference/
        # continuation token, or containing an inline citation marker, is a body fragment not a title.
        if not ti: return True
        if ti[:1].islower(): return True
        if re.match(r"^(and|but|the first|presented|stand|levels|their|because|however|thus|in )\b", ti, re.I):
            return True
        if re.search(r"\(\s*(19|20)\d{2}\s*\)|\[\d+\]", ti):   # "(1996)" or "[9]" inline cite
            return True
        return False
    for i, t in enumerate(pages):          # (1) earliest genuine title page
        ti = _ocr_title(t)
        if ti and _title_ok(ti) and not _looks_like_copyright(ti) and not _is_body_fragment(ti):
            return i, t
    best_i, best_score, best_txt = None, -1, ""
    for i, t in enumerate(pages):          # (2)/(3) composite-signal fallback
        sc = page_signal(t)
        if sc >= 2:
            return i, t
        if sc > best_score:
            best_i, best_score, best_txt = i, sc, t
    if best_i is None:
        return 0, (pages[0] if pages else "")
    return best_i, best_txt

def is_junk_title(t):
    """True if an embedded-metadata Title is not a real title but a machine identifier — a PII string
    ('PII: 0002-1571(71)90004-5'), a bare DOI, 'untitled', 'Microsoft Word - ...', a filename, or a
    string with too few real words. Publisher exports routinely stuff these into the Title field;
    treating them as a real title blocks body-text mining of the actual title on the page."""
    if not t:
        return True
    tl = t.strip().lower()
    if tl.startswith(("pii:", "doi:", "untitled", "microsoft word", "microsoft powerpoint",
                      "microsoft excel", "http", "10.", "iso ", "layout ", "template")):
        return True
    if DOI_RE.search(t) and len(t) < 60:
        return True
    if re.match(r"^[\w .\-]+\.(pdf|doc|docx|tex|indd|qxd|qxp|eps|ps|rtf|fm)\b", tl):  # a filename / DTP source
        return True
    if re.search(r"\biso\s?\d{4,5}\b", tl):               # PDF/A conformance string "ISO 15930 …"
        return True
    if re.search(r"\.(indd|qxd|qxp|fm|tmp)\b", tl):         # DTP source-file name anywhere in the title
        return True
    # A journal running-head / citation stub as a "title": mostly a journal name + volume/pages, or a
    # page-range prefix ("735-745 News and Views"), with little sentence content.
    if re.match(r"^\d{1,4}\s*[-–]\s*\d{1,4}\b", tl) and len(re.findall(r"[A-Za-z]{4,}", t)) < 5:
        return True
    if re.search(r"\b\d{1,4}\s*[-–,]\s*\d{1,4}\b", tl) and len(re.findall(r"[A-Za-z]{4,}", t)) <= 3:
        return True                                         # "Tree Physiology 00, 1–14"
    words = [w for w in re.split(r"\s+", t) if len(w) >= 3 and w.isalpha()]
    return len(words) < 2                                  # fewer than 2 real words => not a title

def mine_bibliography(text):
    """Mine (title, author_family, year, doi) from a page's BODY text — for text-layer PDFs whose
    embedded PDF metadata (Title/Author) is blank OR junk but whose page shows the real title/author.
    Uses the same gated miners as the OCR path. Returns only what passes the gates; blanks otherwise."""
    doi = ""
    m = DOI_RE.search(text)
    if m:
        doi = m.group(0).rstrip(".,;)]}>")
    # A JSTOR / ILL / document-delivery cover page carries exact LABELED metadata — far more reliable
    # than free-text mining. Try it first (text-layer covers, e.g. JSTOR downloads, reach here).
    cover = parse_cover_sheet(text)
    if cover and (cover.get("title") or cover.get("author")):
        cyr = cover.get("year", "")
        if not cyr:
            ym2 = re.search(r"\b(19|20)\d{2}\b", text)
            cyr = ym2.group(0) if ym2 else ""
        return (cover.get("title", ""), cover.get("author", ""), cyr, doi)
    ti = _ocr_title(text)
    ti = ti if (ti and _title_ok(ti)) else ""
    au = _ocr_author(text)
    ym = re.search(r"\b(19|20)\d{2}\b", text)
    yr = ym.group(0) if ym else ""
    return ti, au, yr, doi

def _pick_search_hit(items, ti_ocr, yr_ocr, au_ocr=""):
    # Gate a DOI-FREE title(+author,+year) search hit. "IF YOU GET THEM RIGHT" is enforced here:
    # title fuzzy>=SEARCH_TITLE_SIM (required), year within SEARCH_YEAR_DELTA (if mined), AND the
    # mined family name must appear among the hit's authors (if mined). A record that clears the
    # title gate but whose author list does NOT contain the mined surname is a DIFFERENT paper -> reject.
    for it in items:
        cti = (it.get("title") or [""])[0]
        if not cti:
            continue
        a = re.sub(r"[^a-z0-9]", "", ti_ocr.lower())
        b = re.sub(r"[^a-z0-9]", "", cti.lower())
        sim = difflib.SequenceMatcher(None, a, b).ratio()
        # Asymmetric containment: a mined title is often a running-head or a truncated form of the
        # canonical CrossRef title ("Measuring...black spruce at three" vs "Measuring...black spruce
        # (Picea mariana...) and jack pine..."). A symmetric ratio penalizes the length gap and rejects
        # a correct match, so ALSO accept when the shorter string is a high-fidelity prefix/substring of
        # the longer one (defect #45). Both are anchored on the SHORTER string to stay strict.
        contain = 0.0
        if a and b:
            shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
            if len(shorter) >= 12:  # guard: don't let a tiny fragment match anything
                blk = difflib.SequenceMatcher(None, shorter, longer).find_longest_match(0, len(shorter), 0, len(longer))
                contain = blk.size / len(shorter)
        if sim < SEARCH_TITLE_SIM and contain < 0.90:
            continue
        if yr_ocr:
            _, yh, _, _, _ = parse_crossref(it)
            if yh and abs(int(yh) - int(yr_ocr)) > SEARCH_YEAR_DELTA:
                continue
        # STRONG title match (near-exact or full containment) is sufficient on its own — a mined
        # surname that is slightly corrupt ("Oberbauer\u2019" with a stray apostrophe) or simply wrong
        # (a fragment mis-mined as the author) must NOT veto an otherwise-exact title hit (defect #45).
        strong_title = (sim >= 0.95) or (contain >= 0.99)
        if au_ocr and not strong_title:
            au_norm = re.sub(r"[^a-z]", "", au_ocr.lower())
            fams = re.sub(r"[^a-z ]", "", " ".join((a.get("family", "") or a.get("name", ""))
                          for a in (it.get("author") or [])).lower())
            if fams and au_norm and au_norm not in fams.split() and au_norm not in fams.replace(" ", ""):
                continue   # author mismatch on a NON-exact title => different paper, reject
        return it
    return None

# ==================================================================== APPLY (PROC.8)
def cmd_apply(args):
    d = args.dir
    ixd = index_dir(d)
    ov_path = args.overrides or os.path.join(ixd, OVERRIDES_NAME)
    review_path = os.path.join(ixd, REVIEW_NAME)
    if not os.path.exists(review_path):
        sys.exit("nothing to apply: %s not found (run resolve/ocr first)" % review_path)
    if not os.path.exists(ov_path):
        with open(ov_path, "w", encoding="utf-8") as f:
            f.write(OVERRIDES_HEADER)
    existing = overrides_filenames(ov_path)
    add = []
    for ln in open(review_path, encoding="utf-8"):
        if not ln.strip():
            continue
        fn = ln.split("\t")[0]
        if fn in existing:
            continue
        add.append(ln.rstrip("\n")); existing.add(fn)
    with open(ov_path, "a", encoding="utf-8") as f:
        f.write("".join(a + "\n" for a in add))
    print("appended %d override line(s) to %s" % (len(add), ov_path))

# ==================================================================== RENAME (PROC.10 — canonical rename)
# Pure downstream consumer of paper_index.csv: read the finished index, compute a canonical filename
# per row from a customizable template, and rename ON DISK — ledgered + reversible. Inherits the
# never-fabricate rule: a row below the confidence floor, or one with no real fields to name from,
# is SKIPPED (never force-named into a meaningless string). Rides the same dry-run -> review -> apply
# rail as resolve/ocr; a plan is written to _sfi_rename_plan.tsv for inspection before --apply.
RENAME_CFG_NAME = "_sfi_rename.json"
RENAME_PLAN_NAME = "_sfi_rename_plan.tsv"
RENAME_LEDGER_NAME = "_sfi_renames.tsv"
DEFAULT_RENAME_CFG = {
    "template": "{author}_{year}_{journal_abbrev}_{type}_{pages}",
    "separator": "_",
    "case": "none",                 # none | lower | upper
    "missing_field": "drop",        # drop (omit the token) | placeholder (use `placeholder`)
    "placeholder": "NA",
    "confidence_floor": "medium",   # rename rows at this tier or better: high > medium > low; n/a always excluded
    "rename_datasets": False,       # datasets (record_type=dataset, confidence n/a) are excluded unless True
    "collision": "suffix",          # on a name clash, append -2, -3, ...
    "max_stem_len": 180,            # cap the stem (pre-extension) length for filesystem safety
    "journal_abbrev": {             # OPTIONAL exact overrides: full journal name -> abbreviation.
        "Agricultural and Forest Meteorology": "AgForMeteorol",   # (illustrative — extend as you like;
        "Global Change Biology": "GlobChangeBiol"                 #  unmapped journals get a deterministic
    }                                                             #  abbreviation fallback, never fabricated)
}
_CONF_RANK = {"high": 3, "medium": 2, "low": 1, "n/a": 0, "": 0}
_JSTOP = {"of", "and", "the", "for", "in", "on", "a", "an", "de", "der", "und", "et", "la", "le"}
_FS_BAD = re.compile(r'[/\\:*?"<>|\x00-\x1f]')

def load_rename_cfg(path):
    """Load _sfi_rename.json; write the default file (and return it) if absent. Missing keys are
    back-filled from the default so an old/partial config still works."""
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_RENAME_CFG, f, indent=2, ensure_ascii=False)
        cfg = dict(DEFAULT_RENAME_CFG)
        cfg["_written_default"] = True
        return cfg
    try:
        user = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        sys.exit("FATAL: could not parse %s: %s" % (path, e))
    cfg = dict(DEFAULT_RENAME_CFG)
    cfg.update({k: v for k, v in user.items() if v is not None})
    return cfg

def _asciify(s):
    """NFKD-fold to ASCII (drop diacritics/combining marks); never fabricates, only transliterates."""
    if not s:
        return ""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

def _alnum_component(s):
    """Reduce a resolved token to a filesystem-safe, separator-free alphanumeric chunk.
    O'Brien -> OBrien ; Smith-Jones -> SmithJones. Keeps letters/digits only after ASCII-folding."""
    s = _asciify(s)
    s = _FS_BAD.sub("", s)
    return re.sub(r"[^A-Za-z0-9]", "", s)

def _camel_words(text, drop_stop=False, cap_words=None):
    words = [w for w in re.split(r"[^A-Za-z0-9]+", _asciify(text or "")) if w]
    if drop_stop:
        words = [w for w in words if w.lower() not in _JSTOP] or words
    if cap_words:
        words = words[:cap_words]
    return "".join(w[:1].upper() + w[1:] for w in words)

def _journal_abbrev(journal, cfg):
    """Exact map hit if present, else a deterministic fallback: significant words (stopwords dropped),
    first 4 letters of each, Title-cased and concatenated. Deterministic, never fabricated."""
    j = clean(journal or "")
    if not j:
        return ""
    amap = cfg.get("journal_abbrev") or {}
    if j in amap:
        return _alnum_component(amap[j])
    sig = [w for w in re.split(r"[^A-Za-z0-9]+", _asciify(j)) if w and w.lower() not in _JSTOP]
    if not sig:
        return ""
    return "".join((w[:4]).title() for w in sig)

def _resolve_token(tok, row, cfg):
    if tok == "author":
        return _alnum_component(_family_name(row.get("first_author", "") or ""))
    if tok == "year":
        return re.sub(r"[^0-9]", "", row.get("year", "") or "")
    if tok == "journal":
        return _camel_words(row.get("journal", ""))
    if tok == "journal_abbrev":
        return _journal_abbrev(row.get("journal", ""), cfg)
    if tok == "type":
        rt = (row.get("record_type", "") or "").strip()
        rt = {"book_chapter": "chapter"}.get(rt, rt)   # readability alias; every other type verbatim
        return _alnum_component(rt)
    if tok == "pages":
        p = re.sub(r"[^0-9]", "", row.get("pages", "") or "")
        return (p + "p") if p else ""
    if tok == "title_slug":
        return _camel_words(row.get("title", ""), drop_stop=True, cap_words=8)[:60]
    if tok == "doi_slug":
        return re.sub(r"[^A-Za-z0-9]+", "-", _asciify(row.get("doi", "") or "")).strip("-")
    return ""   # unknown token -> empty (dropped); never a literal "{tok}" in a filename

def compute_canonical_stem(row, cfg):
    """Build the canonical stem from the template. The template is a list of `{token}` placeholders
    joined by the configured separator (literal glue other than the separator is not used — the
    separator field is the single source of joining). Each token is resolved to a clean alphanumeric
    component; an empty token is DROPPED (missing_field=drop) or replaced by the placeholder. Returns
    '' if nothing real remains (=> the caller SKIPS the file: never-fabricate).

    Token names are matched whole via \\{(\\w+)\\} — `\\w` includes `_`, so a multi-word token like
    `{journal_abbrev}` is parsed as ONE token, never split on the separator inside its name."""
    sep = cfg.get("separator", "_")
    tmpl = cfg.get("template", DEFAULT_RENAME_CFG["template"])
    placeholder = _alnum_component(cfg.get("placeholder", "NA"))
    use_ph = cfg.get("missing_field") == "placeholder"
    vals = []
    for tok in re.findall(r"\{(\w+)\}", tmpl):
        v = _alnum_component(_resolve_token(tok, row, cfg))
        if not v:
            if use_ph:
                vals.append(placeholder)
            continue
        vals.append(v)
    stem = sep.join(v for v in vals if v)
    case = cfg.get("case", "none")
    if case == "lower":
        stem = stem.lower()
    elif case == "upper":
        stem = stem.upper()
    return stem[: int(cfg.get("max_stem_len", 180))].strip(sep + "-_")

def _eligible_for_rename(row, cfg):
    """(ok, reason) — apply the confidence floor + dataset policy. A row that fails is reported, never renamed."""
    rt = (row.get("record_type", "") or "").strip()
    conf = (row.get("confidence", "") or "").strip().lower()
    if rt == "dataset" and not cfg.get("rename_datasets"):
        return (False, "dataset (rename_datasets=false)")
    floor = _CONF_RANK.get(str(cfg.get("confidence_floor", "medium")).lower(), 2)
    if _CONF_RANK.get(conf, 0) < floor:
        return (False, "below confidence floor (%s < %s)" % (conf or "none", cfg.get("confidence_floor")))
    return (True, "")

def load_ledger(path):
    rows = []
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            if not ln.strip() or ln.startswith("#"):
                continue
            c = ln.rstrip("\n").split("\t")
            if len(c) >= 4:
                rows.append({"batch": c[0], "ts": c[1], "original": c[2], "canonical": c[3]})
    return rows

def _plan_renames(idx, cfg, d):
    """Compute the rename plan from the index. Returns a list of dicts:
    {file_name, target, action in {rename, skip}, reason}. Collisions get a deterministic -N suffix.
    Incremental: a file already AT its canonical name (or gone from disk) is a no-op skip."""
    disk = set(fn for fn in os.listdir(d) if os.path.isfile(os.path.join(d, fn)))
    # names that must NOT be collided with: every on-disk file we are NOT renaming away this pass
    proposals = []
    for fn in sorted(idx.keys(), key=str.lower):
        row = idx[fn]
        if fn not in disk:
            proposals.append({"file_name": fn, "target": "", "action": "skip", "reason": "not on disk (already moved / missing)"})
            continue
        ok, why = _eligible_for_rename(row, cfg)
        if not ok:
            proposals.append({"file_name": fn, "target": "", "action": "skip", "reason": why})
            continue
        ext = os.path.splitext(fn)[1]
        stem = compute_canonical_stem(row, cfg)
        if not stem:
            proposals.append({"file_name": fn, "target": "", "action": "skip", "reason": "no nameable fields (never-fabricate)"})
            continue
        target = stem + ext.lower()
        if target == fn:
            proposals.append({"file_name": fn, "target": target, "action": "skip", "reason": "already canonical"})
            continue
        proposals.append({"file_name": fn, "target": target, "action": "rename", "reason": "", "_stem": stem, "_ext": ext.lower()})
    # collision resolution over the set of ACTIVE renames + the on-disk files not being renamed
    renaming_from = set(p["file_name"] for p in proposals if p["action"] == "rename")
    taken = set(fn for fn in disk if fn not in renaming_from)
    for p in [p for p in proposals if p["action"] == "rename"]:
        tgt = p["target"]
        if tgt in taken:
            i = 2
            while ("%s-%d%s" % (p["_stem"], i, p["_ext"])) in taken:
                i += 1
            tgt = "%s-%d%s" % (p["_stem"], i, p["_ext"])
            p["target"] = tgt
            p["reason"] = "collision -> suffixed"
        taken.add(tgt)
        # IDEMPOTENCE: if collision-resolution landed the target back on the file's own current name
        # (a previously-suffixed file whose base stem is taken by a sibling), it is already canonical
        # for this corpus — a no-op, NOT a rename. Without this, re-running would perpetually re-flag
        # the -N sibling and `apply` would refuse it (the "re-run = no diff" invariant would fail).
        if p["target"] == p["file_name"]:
            p["action"] = "skip"; p["reason"] = "already canonical"
    return proposals

def _rewrite_key_in_overrides(ov_path, old_fn, new_fn):
    """Follow curation across a rename: rewrite the file_name key (col 0) of any override row."""
    if not os.path.exists(ov_path):
        return
    out = []
    for ln in open(ov_path, encoding="utf-8"):
        if ln.startswith("#") or not ln.strip():
            out.append(ln); continue
        cols = ln.rstrip("\n").split("\t")
        if cols and cols[0] == old_fn:
            cols[0] = new_fn
            out.append("\t".join(cols) + "\n")
        else:
            out.append(ln)
    with open(ov_path, "w", encoding="utf-8") as f:
        f.writelines(out)

def _rewrite_key_in_index(index_path, old_fn, new_fn):
    """Keep paper_index.csv coherent immediately after apply (a later rebuild reproduces it)."""
    if not os.path.exists(index_path):
        return
    rows = list(csv.DictReader(open(index_path, encoding="utf-8")))
    for r in rows:
        if r.get("file_name") == old_fn:
            r["file_name"] = new_fn
    def _windex2(f):
        w = csv.DictWriter(f, fieldnames=INDEX_COLS); w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in INDEX_COLS})
    write_atomic(index_path, _windex2)

def _move_ocr_sidecars(ixd, old_stem, new_stem):
    """Rename _ocr/<old>.pdf/.txt sidecars so the OCR cache follows the file (no re-OCR)."""
    ocrd = os.path.join(ixd, "_ocr")
    if not os.path.isdir(ocrd):
        return
    for suff in (".pdf", ".txt"):
        src = os.path.join(ocrd, old_stem + suff)
        if os.path.exists(src):
            dst = os.path.join(ocrd, new_stem + suff)
            if not os.path.exists(dst):
                os.rename(src, dst)

def cmd_rename(args):
    d = args.dir
    ixd = index_dir(d)
    index_path = args.index or os.path.join(ixd, "paper_index.csv")
    ov_path = args.overrides or os.path.join(ixd, OVERRIDES_NAME)
    cfg_path = args.config or os.path.join(ixd, RENAME_CFG_NAME)
    ledger_path = os.path.join(ixd, RENAME_LEDGER_NAME)
    plan_path = os.path.join(ixd, RENAME_PLAN_NAME)
    cfg = load_rename_cfg(cfg_path)
    if cfg.get("_written_default"):
        print("WROTE default config %s — review/edit it, then re-run rename." % cfg_path)

    # ---- UNDO: reverse the most recent rename batch from the ledger ----
    if args.undo:
        led = load_ledger(ledger_path)
        if not led:
            print("nothing to undo: %s is empty/absent." % ledger_path); return
        last_batch = max(l["batch"] for l in led)
        batch = [l for l in led if l["batch"] == last_batch]
        done = 0
        for l in reversed(batch):
            cur = os.path.join(d, l["canonical"]); orig = os.path.join(d, l["original"])
            if os.path.exists(cur) and not os.path.exists(orig):
                os.rename(cur, orig)
                _rewrite_key_in_overrides(ov_path, l["canonical"], l["original"])
                _rewrite_key_in_index(index_path, l["canonical"], l["original"])
                _move_ocr_sidecars(ixd, os.path.splitext(l["canonical"])[0], os.path.splitext(l["original"])[0])
                done += 1
            else:
                print("  ! skip undo %s (target exists or source missing)" % l["canonical"][:60])
        remaining = [l for l in led if l["batch"] != last_batch]
        with open(ledger_path, "w", encoding="utf-8") as f:
            f.write("# batch\tts\toriginal\tcanonical\n")
            for l in remaining:
                f.write("\t".join((l["batch"], l["ts"], l["original"], l["canonical"])) + "\n")
        print("UNDO batch %s: reversed %d rename(s); %d batch(es) remain in ledger." % (last_batch, done, len(set(l["batch"] for l in remaining))))
        return

    if not os.path.exists(index_path):
        sys.exit("FATAL: %s not found — run `extract` then `build` first (rename consumes the index)." % index_path)
    idx = {r["file_name"]: r for r in csv.DictReader(open(index_path, encoding="utf-8"))}
    plan = _plan_renames(idx, cfg, d)
    to_rename = [p for p in plan if p["action"] == "rename"]

    # ---- DRY-RUN (default): write the plan for review ----
    if not args.apply:
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("# original\tproposed\tstatus\treason\n")
            for p in plan:
                f.write("\t".join((p["file_name"], p["target"], p["action"], p["reason"])) + "\n")
        skipped = [p for p in plan if p["action"] == "skip"]
        print("DRY-RUN: %d to rename | %d skipped -> %s (review, then re-run with --apply)" % (len(to_rename), len(skipped), plan_path))
        for p in to_rename:
            print("  %-46s -> %s%s" % (p["file_name"][:46], p["target"], ("  (%s)" % p["reason"] if p["reason"] else "")))
        # surface WHY the skips were skipped (grouped) — honest reporting, never a silent drop
        from collections import Counter
        reasons = Counter(p["reason"] for p in skipped)
        for why, n in reasons.most_common():
            if why != "already canonical":
                print("  skip[%d]: %s" % (n, why))
        return

    # ---- APPLY: rename on disk + follow keys + ledger ----
    if not to_rename:
        print("APPLY: nothing to rename (all files already canonical or skipped)."); return
    batch = time.strftime("%Y%m%dT%H%M%S")
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(ledger_path):
        with open(ledger_path, "w", encoding="utf-8") as f:
            f.write("# batch\tts\toriginal\tcanonical\n")
    done = 0
    with open(ledger_path, "a", encoding="utf-8") as led:
        for p in to_rename:
            src = os.path.join(d, p["file_name"]); dst = os.path.join(d, p["target"])
            if os.path.exists(dst):
                print("  ! refuse %s -> %s (target already exists)" % (p["file_name"][:40], p["target"])); continue
            os.rename(src, dst)
            _rewrite_key_in_overrides(ov_path, p["file_name"], p["target"])
            _rewrite_key_in_index(index_path, p["file_name"], p["target"])
            _move_ocr_sidecars(ixd, os.path.splitext(p["file_name"])[0], os.path.splitext(p["target"])[0])
            led.write("\t".join((batch, ts, p["file_name"], p["target"])) + "\n")
            done += 1
    print("APPLY batch %s: renamed %d file(s); ledger -> %s ; index+overrides keys updated." % (batch, done, ledger_path))
    print("  (re-run `extract` + `build` to refresh derived fields; re-run `rename` => no-op, incremental.)")

# ====================================================================
def main():
    ap = argparse.ArgumentParser(prog="sci_file_index.py", description="Catalog a scientific-literature folder.")
    ap.add_argument("cmd", choices=["extract", "build", "resolve", "ocr", "apply", "rename"])
    ap.add_argument("--dir", required=True, help="literature folder to index")
    ap.add_argument("--index", default="", help="index CSV path (default <dir>/paper_index.csv)")
    ap.add_argument("--overrides", default="", help="overrides TSV path (default <dir>/_sfi_overrides.tsv)")
    ap.add_argument("--mailto", default="", help="contact email for the CrossRef polite pool")
    ap.add_argument("--config", default="", help="rename config JSON (default <dir>/index/_sfi_rename.json)")
    ap.add_argument("--apply", action="store_true", help="rename: execute the plan (default is dry-run)")
    ap.add_argument("--undo", action="store_true", help="rename: reverse the most recent rename batch from the ledger")
    args = ap.parse_args()
    args.dir = os.path.abspath(os.path.expanduser(args.dir))
    if not os.path.isdir(args.dir):
        sys.exit("FATAL: --dir not a directory: " + args.dir)
    {"extract": cmd_extract, "build": cmd_build, "resolve": cmd_resolve,
     "ocr": cmd_ocr, "apply": cmd_apply, "rename": cmd_rename}[args.cmd](args)

if __name__ == "__main__":
    main()