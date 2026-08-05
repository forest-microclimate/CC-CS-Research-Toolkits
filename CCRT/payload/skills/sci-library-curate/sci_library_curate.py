#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""sci-library-curate — dedup, migrate-copy, and topic-organize a scientific-literature
index produced by sci-file-index. Companion tool to sci-file-index.

Pipeline (each step reads the previous step's output; all steps are idempotent):
  dedup     Cluster the index, keep article+SI together, flag TRUE duplicates only,
            pick the cleanest version per cluster, and flag likely wrong-DOI phantoms
            for human review. Writes _dedup_decisions.csv + DEDUP_REPORT.md.
  migrate   Copy the keep-set (everything except drop_as_duplicate) to a clean folder
            with canonical Author_Year_JournalAbbrev_TitleSlug.pdf names. Drift-resistant:
            resolves each index name to its real disk file by exact-then-stem match, so
            an ongoing Papers.app _N rename does not break the copy. Writes _MIGRATION_MANIFEST.csv.
  organize  Classify each file into a Topic/Subtopic taxonomy (regex on title+journal),
            let supplements inherit their parent's topic, and move the clean files into a
            nested folder tree. Regex leaves a tail unclassified — export it for an LLM pass
            (see SKILL.md) and re-run with --llm-assignments to place the rest.
  catalog   Regenerate the one-row-per-WORK clean lookup table (_index_clean_lookup_table.csv)
            from the master index: collapse supplements/datasets/book-sections onto their parent
            work, list each work's clean path + its supplements inline. A materialized VIEW of the
            master (regenerate, never hand-edit); with --lib it re-runs the disk 1:1 reconciliation
            so the catalog cannot silently drift. Run it after any build/dedup/migrate/manual edit.

Design principles (carried from the manual run this tool was distilled from):
  * An article and its supplement share a DOI but are NOT duplicates — cluster MAIN vs SUPP
    in separate namespaces; key SUPP by DOI + supplement-number so distinct SIs never merge.
  * NEVER silently join on a guessed key. A DOI is only used as a cluster key if its suffix
    contains a digit (guards truncated DOIs). Wrong-DOI phantoms (filename author/year
    disagrees with metadata inside a cluster) are FLAGGED, never auto-merged or auto-deleted.
  * There are typically ZERO byte-identical duplicates (Papers re-encodes every copy), so the
    "cleanest version" pick is by filename quality -> confidence -> size, not by hash.
"""
import argparse, csv, os, re, sys, shutil, difflib, json, time, unicodedata, urllib.parse, urllib.request
from collections import Counter, defaultdict

csv.field_size_limit(10 * 1024 * 1024)

# ----------------------------- shared identity primitives -----------------------------
# Single source of truth: scripts/sci_lib_common.py (built from the canonical module;
# NEVER hand-edit a shipped copy — edit the canonical + rebuild). The underscore aliases
# below preserve every existing call-site name in this file.
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


# ===== helpers/constants ported from Claude Science for I16-I19 (2026-07-24) =====
SUPP_DATASET_TYPES = {"supplement", "dataset"}          # I16/I18 scope: companion documents with a parent
_DOI_SUPPL_SUFFIX_RE = re.compile(r"(-supplement|-suppl\w*|\.s0*\d+|_ac|[._]v\d+|v\d+)$", re.I)
_AUTHOR_YEAR_RE = re.compile(r"^[A-Z][A-Za-z\u00C0-\u017F'\-]+_(1[6-9]\d\d|20[0-2]\d)(_|$)")
_CRYPTIC_LEADDIGIT_RE = re.compile(r"^\d")
_CRYPTIC_PUBCODE_RE = re.compile(r"^[a-z]{2,6}\d{4,6}")
_DOI_FIND_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")   # SI page-text DOI miner (mirrors indexer DOI_RE)
_REPO_DOI_PREFIXES = (
    "10.5061/",   # Dryad
    "10.5281/",   # Zenodo
    "10.6084/",   # figshare
    "10.6078/",   # UC/Merritt
    "10.18140/",  # FLUXNET / ICOS
    "10.5285/",   # NERC/CEDA
    "10.25573/",  # Smithsonian figshare
    "10.15486/",  # NGT
    "10.7910/",   # Harvard Dataverse
    "10.17605/",  # OSF
    "10.1594/",   # PANGAEA
    "10.24435/",  # materialscloud
    "10.15468/",  # GBIF
    "10.6073/",   # EDI / LTER
    "10.5066/",   # USGS ScienceBase
    "10.25919/",  # CSIRO
    "10.21232/", "10.48434/", "10.26197/", "10.20383/",   # further data repos seen in corpus
    "10.64898/",   # preprint server (SI is preprint version of a published parent)
)

def _cn_stem(cn):
    return re.sub(r"\.[A-Za-z0-9]+$", "", str(cn or ""))


def is_cryptic_name(cn):
    r"""True if clean_name matches the CRYPTIC pattern: leading publisher/DOI code (^\d,
    ^[a-z]{2,6}\d{4,6}), contains _MOESM or -sup-, OR is a bare non-Author_Year stem.
    Author_Year_... names are NOT cryptic."""
    s = _cn_stem(cn)
    if _CRYPTIC_LEADDIGIT_RE.match(s):
        return True
    if _CRYPTIC_PUBCODE_RE.match(s):
        return True
    if "_MOESM" in cn or "MOESM" in cn:
        return True
    if "-sup-" in cn.lower():
        return True
    return not bool(_AUTHOR_YEAR_RE.match(s))       # bare non-Author_Year stem


def _note_blob(r):
    """Row's free-text note surface. Checks BOTH the index `notes` column (indexer product) and the
    master `dedup_note` column (curator product) so a flag token stamped in either satisfies I16/I17."""
    return ((r.get("notes", "") or "") + " " + (r.get("dedup_note", "") or ""))


def _norm_doi_cmp(d):
    """Normalize a DOI for SI<->parent comparison: real-DOI-gate (via real_doi), then repeatedly strip a
    trailing supplement/version suffix ('...-supplement', '.v1', '_AC', '.s01'), lowercase. '' if not real."""
    d = real_doi(d)
    if not d:
        return ""
    prev = None
    while prev != d:
        prev = d
        d = _DOI_SUPPL_SUFFIX_RE.sub("", d)
    return d


def _is_repo_doi(d):
    d = (d or "").strip().lower()
    return any(d.startswith(p) for p in _REPO_DOI_PREFIXES)


def _find_under_lib(lib, clean_name):
    """Locate a file by clean_name anywhere under `lib` (files sit in per-article bundle folders)."""
    for dp, _dirs, fs in os.walk(lib):
        if clean_name in fs:
            return os.path.join(dp, clean_name)
    return None


def _mine_si_dois(path, pdftotext=None, pages=2, timeout=60):
    """I18 --lib: return the SET of DOIs mined from an SI PDF's first `pages` pages, or None if
    unreadable (non-PDF, missing, no text layer, or no pdftotext). Reuses the poppler primitive the
    rest of the module already depends on. Never OCRs (an image-only SI simply returns None -> skip)."""
    exe = pdftotext or _probe_poppler_bin("pdftotext")
    if not exe or not path or not os.path.exists(path) or not path.lower().endswith(".pdf"):
        return None
    import subprocess
    try:
        r = subprocess.run([exe, "-f", "1", "-l", str(pages), "-layout", path, "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
        txt = r.stdout or ""
    except Exception:
        return None
    if not txt.strip():
        return None
    # MASTHEAD ZONE ONLY (I18 anti-citation-bleed, defect #61): an SI states its OWN identity DOI in
    # the header ("Supporting Information for <title> https://doi.org/<self>"); DOIs deeper in the page
    # are CITED references (e.g. a peer-review file quoting other works) and must NOT count as the SI's
    # identity. Restrict mining to the masthead: text before the first reference/bibliography/figure-list
    # marker, capped at 600 chars. A body-only DOI (no masthead DOI) yields an EMPTY set -> I18 skips
    # (cannot fail an SI whose own identity DOI is not printed), which is the safe, no-false-positive path.
    _cut = len(txt)
    for _mk in ("references", "bibliography", "literature cited", "works cited", "supplementary references"):
        _p = txt.lower().find(_mk)
        if _p != -1:
            _cut = min(_cut, _p)
    txt = txt[:min(_cut, 600)]
    if not txt.strip():
        return None
    return {m.group(0).rstrip(".,;)]}>") for m in _DOI_FIND_RE.finditer(txt)}


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

# call-site aliases (preserved from the shared-module contract)
_JSTOP        = _JSTOP
_asciify      = asciify
_family_name  = family_name
_surname_sep  = surname_sep
_name_features = name_features
_camel        = _camel
norm_title    = norm_title
real_doi      = real_doi
journal_abbrev = journal_abbrev
canonical_stem = canonical_stem
blocking_keys = blocking_keys
write_atomic   = write_atomic
format_author  = format_author
abbreviate_authors = abbreviate_authors

# ----------------------------- master schema (author columns, v5) -----------------------------
AUTHOR_COLS = ["authors", "n_authors", "last_author"]
# FM4/FM5 provenance columns, APPENDED after AUTHOR_COLS so every pre-existing column keeps its EXACT
# position. `pages` = the indexer's pdfinfo page count (drives the truncation flag + I12/I13); it is
# APPEND-only, so existing rows without it simply carry a blank. `content_sim` = the indexer's 64-bit
# SimHash fingerprint (drives the FM5 near-dup signal + I13 checks); blank when the source had no text.
PROVENANCE_COLS = ["pages", "content_sim"]
# Canonical master column order. The three AUTHOR_COLS are APPENDED at the END (after
# date_time_added) so every pre-existing column keeps its EXACT position — nothing shifts.
MASTER_COLS = [
    "clean_name", "bundle_folder", "origin", "record_type", "first_author",
    "first_author_ascii", "surname_sep", "name_features", "year", "title", "journal",
    "doi", "confidence", "parent_file", "dedup_note", "original_disk_name", "date_time_added",
] + AUTHOR_COLS + PROVENANCE_COLS
# Record types that carry a byline (authors are meaningful). Supplements/datasets do NOT.
AUTHOR_RECORD_TYPES = {"article", "book", "book_chapter", "preprint", "manual",
                       "thesis", "report", "conference"}
# Closed 11-type record-type vocabulary. Every row's record_type MUST be one of these; validator I14
# catches typos / stray types before the main/non-main split relies on them. peer_review (FM2) is the
# type added this cycle for reviewer/editorial files. Keep in sync with the indexer's typing.
RECORD_TYPE_VOCAB = {"article", "supplement", "dataset", "peer_review", "book", "book_chapter",
                     "preprint", "thesis", "report", "conference", "manual"}
# Shared FM4/FM5 thresholds (dedup args default to these; validator I13 reuses DPG_MIN_DEFAULT).
DPG_MIN_DEFAULT = 3          # min page gap for a fuller twin to count as a truncation candidate
SIM_K_DEFAULT = 3            # content_sim SimHash Hamming threshold for near-duplicate detection
# Non-main record types: distinct companion documents to an article (SI / dataset / peer-review file)
# that must never be merged into a dup_article KEEP/drop decision. Shared by cmd_dedup (_is_main) and
# validator I13 (mains-only truncation check).
NON_MAIN_TYPES = {"supplement", "dataset", "peer_review"}

# ---- shared author-family matching (defects #58/#59) -------------------------------------------
# The Stage-2 four-field arbiter and the populate_authors content-gate BOTH need to decide whether a
# candidate author-family agrees with the (content-verified) first_author. That decision must be the
# SAME rule the I10 validator applies, or a populate could write a row I10 then rejects. This is a
# module-level TWIN of cmd_validate's inline _au_norm/_i10_ok (which stays exactly as shipped — not
# weakened, not moved): casefold + NFKD-strip-accents + unify every Unicode dash to ASCII '-', then
# PASS on any of corporate-author / equality / containment / whitespace-token-overlap.
_I10_DASHES = "‐‑‒–—−"   # hyphen, non-breaking/figure/en/em dash, minus
_I10_CORP = ("consortium", "initiative", "group", "team", "network", "collaboration")


def _au_norm(s):
    s = str(s or "")
    for _d in _I10_DASHES:
        s = s.replace(_d, "-")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.casefold()


def _i10_author_match(a0, fa):
    """True iff author-family `a0` agrees with first_author `fa` under the I10 tolerance. `a0` may be
    a full 'Family, G.' name (family = substring before the first comma) or a bare family token."""
    if not str(a0).strip():
        return True                                    # blank -> nothing to contradict
    if any(k in str(a0).lower() for k in _I10_CORP):
        return True                                    # corporate/consortium author
    fam = str(a0).split(",", 1)[0]
    nf, nfa = _au_norm(fam), _au_norm(fa)
    if not nfa:
        return True
    if nf == nfa:
        return True
    if nf and (nf in nfa or nfa in nf):
        return True
    toks_fa = set(nfa.split())
    toks_a0 = set(_au_norm(str(a0).replace(",", " ")).split())
    return bool(toks_fa & toks_a0)

def master_fieldnames(rows, ensure_authors=False):
    """Column order for writing the master back. Preserves the EXISTING schema exactly (union of
    keys across ALL rows in first-seen order, minus the internal _rid) so no existing column can
    move or be dropped. With ensure_authors=True (the populate path) the three AUTHOR_COLS are
    APPENDED at the end if absent — introducing them without disturbing any existing column."""
    seen = []
    for r in rows:
        for k in r:
            if k != "_rid" and k not in seen:
                seen.append(k)
    if ensure_authors:
        for c in AUTHOR_COLS:
            if c not in seen:
                seen.append(c)
    return seen

def _write_master(path, rows, ensure_authors=False):
    """Atomic master write with the schema preserved (see master_fieldnames). Used by every stage
    that writes the master back so column order can never silently drift."""
    cols = master_fieldnames(rows, ensure_authors=ensure_authors)
    def _w(f):
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    write_atomic(path, _w)

def title_sim(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

def supp_marker(fn):
    """Extract a stable supplement identity from a filename, or '' if none."""
    # canonical curator form first: "..._suppl<N>.<ext>" (the stem this script itself emits)
    m = re.search(r"_suppl(\d+)(?:\.[A-Za-z0-9]+)?$", fn)
    if m: return "suppl" + m.group(1)
    m = re.search(r"supplement(?:ary)?[\s_-]*(\d+)", fn, re.I)
    if m: return "suppl" + m.group(1)
    m = re.search(r"[\s_-]si[\s_-]*(\d+)", fn, re.I)
    if m: return "SI" + m.group(1)
    m = re.search(r"(figure|fig|table|dataset|appendix|movie|video)[\s_-]*s?(\d+)", fn, re.I)
    if m: return m.group(1).lower()[:3] + m.group(2)
    if re.search(r"supplement|supporting", fn, re.I): return "suppl"
    return ""

def cryptic_score(fn):
    """Higher = worse filename (more cryptic). Used to prefer clean names when picking canonical."""
    s = 0
    if re.search(r"watermark-silverchair|ezproxy|\.ezproxy", fn): s += 3
    if re.search(r"^\d+\.full", fn): s += 2
    if re.search(r"pdf\.sciencedirect|semanticscholar|onlinelibrary-|www[.\-]|link\.springer|apsjournals|bsapubs|agupubs|storage\.googleapis", fn): s += 3
    if re.search(r"^[0-9a-f]{8}-[0-9a-f]{4}-", fn): s += 4
    if re.search(r"Untitled Article", fn): s += 3
    if re.search(r"\(\d+\)\.pdf$", fn): s += 1
    if re.search(r"_\d+\.pdf$", fn): s += 1
    if re.match(r"^[A-Z][A-Za-z\u00C0-\u017F'\-]+_\d{4}", fn): s -= 2
    if re.search(r"[A-Z][a-z]+_\d{4}_[A-Z]", fn): s -= 1
    return s

def stem_key(f):
    """Drop trailing _N copy-suffix and extension — the identity that survives Papers renames."""
    s = f[:-4] if f.lower().endswith(".pdf") else f
    return re.sub(r"_\d+$", "", s)

def safe_dir(s):
    s = re.sub(r'[<>:"/\\|?*]', "", str(s)).strip()
    s = re.sub(r"\s*&\s*", "_and_", s)
    s = re.sub(r"\s+", "_", s)
    return s or "Unsorted"

def _read_index(path):
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Stable UNIQUE id per row (collision-safe). file_name alone is NOT unique once two source
    # folders' indices merge (the user's documented workflow) — two "paper.pdf" rows would collide
    # and one would be silently lost in migrate. Positional prefix guarantees uniqueness within the
    # index file both dedup and migrate read; the file_name tail keeps it human-readable. _rid is
    # internal only (every writer below uses explicit fieldnames or extrasaction="ignore").
    for i, r in enumerate(rows):
        # FM7: master-schema alias. The migrated master's primary key is `clean_name` (MASTER_COLS) and
        # it carries NO `file_name` column, but every dedup consumer below (_rid, _size, supp_marker,
        # fname_surname, cryptic_score, _distinct_works) reads `file_name`. Alias it once here so dedup
        # runs directly against the master without touching any call site. A source-index row already
        # has `file_name`, so the alias is a no-op there. cmd_validate does the same alias at its head.
        if not r.get("file_name") and r.get("clean_name"):
            r["file_name"] = r["clean_name"]
        r["_rid"] = "%d::%s" % (i, r.get("file_name", ""))
    return rows

# ----------------------------- dedup -----------------------------
def _base_key(r):
    """Cluster key spanning ALL record types (article + its SI share this key)."""
    d = real_doi(r.get("doi"))
    if d: return "DOI::" + d
    au = str(r.get("first_author", "")).lower().strip()
    yr = str(r.get("year", "")).strip()
    nt = norm_title(r.get("title", ""))
    if au and yr and len(nt) >= 10:
        return "AYT::%s|%s|%s" % (au, yr, nt[:40])
    return None

def _is_corrigendum(fn):
    return bool(re.search(r"corrigendum|erratum|correction", fn, re.I))

def fname_surname(fn):
    """Surname from an Author_Year-style filename, else '' (cryptic/Untitled names return '')."""
    m = re.match(r"^([A-Za-z\u00C0-\u017F'\-]+)_\d{4}", fn) or re.match(r"^([A-Za-z\u00C0-\u017F'\-]+)_\d{4}", fn.replace(" ", "_"))
    if m and m.group(1).lower() not in ("untitled", "unknown"):
        return m.group(1).lower()
    return ""

def _authors_disagree(members):
    """True if the members carry ≥2 DIFFERENT parseable filename surnames — a wrong-DOI phantom
    signal (two different papers merged under one DOI). Files with no parseable surname don't count."""
    names = {fname_surname(m["file_name"]) for m in members}
    names.discard("")
    return len(names) >= 2

def _pick_cleanest(members):
    """KEEP the cleanest member; corrigenda/errata are kept alongside the article. Returns a set of
    _rid (NOT file_name) so a same-basename collision in a merged index can never mis-key KEEP/drop."""
    if (any(_is_corrigendum(m["file_name"]) for m in members)
            and any(not _is_corrigendum(m["file_name"]) for m in members)):
        return set(m["_rid"] for m in members), "keep_all_corrigendum"
    ranked = sorted(members, key=lambda m: (cryptic_score(m["file_name"]),
                                            {"high": 0, "medium": 1, "low": 2}.get(m.get("confidence"), 3),
                                            -(m["_size"] or 0)))
    return {ranked[0]["_rid"]}, "keep_cleanest"

def _titles_agree(a, b):
    """True if two normalized titles are the SAME WORK. Beyond a fuzzy-ratio >= 0.80, a strict
    CONTAINMENT (one title is a prefix/substring of the other, both >= 20 chars) counts as agreement:
    extraction frequently truncates a title, so 'Leaf warming ... reduced photosynthesis due to' and
    the full-length title are the same paper, not a wrong-DOI phantom. Genuinely different titles
    (a real DOI collision) still fail both tests and are flagged."""
    a, b = (a or "").strip(), (b or "").strip()
    if not a or not b:
        return False
    if title_sim(a, b) >= 0.80:
        return True
    lo, hi = sorted((a, b), key=len)
    return len(lo) >= 20 and lo in hi          # truncated-title containment

# FM3: distinct-work guard. Two MAIN rows can share a title-only blocking key (fuzzy titles agree) yet
# be DIFFERENT works — companion papers ("... Part 1" / "... Part 2") or two articles that a wrong shared
# DOI collapsed. Merging them would DROP a distinct paper, which the module must never do. This predicate
# returns True when the mains are provably distinct, so the caller routes them to FLAG/phantom instead of
# a KEEP/drop merge. Two independent signals, NO page-range branch (a non-overlapping printed range does
# NOT imply distinct works — a same-article near-dup can carry different ranges, so a range test would
# regress a correct drop):
#   (1) conflicting Part-N tokens: >= 2 distinct normalized "Part <ivx0-9>" tokens across title/file_name.
#   (2) >= 2 distinct REAL DOIs AND the normalized titles are NOT identical. The title guard is decisive:
#       a genuine companion pair (Part 1 vs Part 2) has DISTINCT titles + distinct DOIs -> distinct; but a
#       same-article near-dup whose fuller copy carries a mis-mined citation DOI has an IDENTICAL title, so
#       distinct-DOIs-alone must NOT flag it (that would turn a correct near-dup DROP into a FLAG). A blank
#       DOI vs a real DOI is never "distinct" (preserves same-paper truncations whose short copy has no DOI).
# A REAL "Part N" companion marker requires a separator (space / . / - / _) between "part" and the
# number and a trailing word boundary: "Part 1", "Part-2", "Part_3", "Part IV". This deliberately does
# NOT match "partitioning", "particle", "partial", "particular" (no separator -> the [ivx]+ branch would
# otherwise grab the leading 'i'), nor "apart"/"department" (\b before "part" fails). Underscores are
# normalized to spaces first so filename forms ("..._Part_2_...") tokenize like titles.
_PARTN_RE = re.compile(r"\bpart[\s.\-]+([ivx]+|\d+)\b", re.I)
def _partn_tokens(*texts):
    toks = set()
    for t in texts:
        for m in _PARTN_RE.findall((t or "").replace("_", " ")):
            toks.add(m.lower())
    return toks
def _distinct_works(mains):
    parts = set()
    for m in mains:
        parts |= _partn_tokens(m.get("title", ""), m.get("file_name", ""))
    if len(parts) >= 2:
        return True
    dois = {real_doi(m.get("doi", "")) for m in mains}
    dois.discard("")
    if len(dois) >= 2:
        ntitles = {norm_title(m.get("title", "")) for m in mains}
        ntitles.discard("")
        if len(ntitles) >= 2:                  # distinct DOIs AND non-identical titles => distinct works
            return True
    return False

# FM5: stamp-robust near-dup test over the indexer's `content_sim` 64-bit SimHash column. Two MAIN rows
# in one cluster whose fingerprints differ in <= K bits (Hamming distance) are the SAME article even when
# their raw page-1 cosine is misleadingly low (download stamps / re-typeset mastheads). Consulted ONLY
# after _distinct_works / _authors_disagree / truncation have cleared the pair, so a low Hamming can never
# merge two genuinely different documents. A blank/0 fingerprint means "no signal" and never matches.
def _sim_hamming(a, b):
    try:
        x, y = int(a), int(b)
    except (TypeError, ValueError):
        return None
    if x == 0 or y == 0:
        return None
    return bin(x ^ y).count("1")
def _near_dup_by_content(mains, k):
    sims = [str(m.get("content_sim", "")).strip() for m in mains]
    sims = [s for s in sims if s and s != "0"]
    if len(sims) < 2:
        return False
    for i in range(len(sims)):
        for j in range(i + 1, len(sims)):
            h = _sim_hamming(sims[i], sims[j])
            if h is not None and h <= k:
                return True
    return False

def cmd_dedup(args):
    idx = _read_index(args.index)
    sizes = {}
    if args.hashes and os.path.exists(args.hashes):
        with open(args.hashes, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                try: sizes[r["file_name"]] = int(r.get("size_bytes") or 0)
                except Exception: pass
    for r in idx:
        r["_size"] = sizes.get(r["file_name"], 0)
        r["_key"] = _base_key(r)
        r["_ntitle"] = norm_title(r.get("title", ""))

    # FIELD-PRIMACY dedup grouping (the user's pervasive bug fix). MAIN-article duplicates are
    # clustered by DOI-AGNOSTIC union-blocking (sci_lib_common.blocking_keys): two rows group if
    # their key-SETS intersect on {folded-author+title} OR {same real DOI} OR {title-only}. Year,
    # DOI and publication CORROBORATE but never GATE — so a blank-DOI twin, a year-split copy
    # (Kumarathunge 2018/2019), and a missing-year row all still co-cluster. This REPLACES the old
    # scalar _base_key for MAIN grouping (which returned a single DOI-first key and silently split
    # any true duplicate whose DOI was blank or whose year differed). The scalar _base_key is KEPT
    # for the SI-namespace + article<->SI linking logic below, which correctly needs DOI-keying.
    _uf = {}
    def _find(x):
        _uf.setdefault(x, x)
        while _uf[x] != x:
            _uf[x] = _uf[_uf[x]]; x = _uf[x]
        return x
    def _union(a, b):
        ra, rb = _find(a), _find(b)
        if ra != rb: _uf[rb] = ra
    _key2rows = defaultdict(list)
    for i, r in enumerate(idx):
        _find(i)
        for k in blocking_keys(r):
            _key2rows[k].append(i)
    for _k, _rows in _key2rows.items():
        for _j in _rows[1:]:
            _union(_rows[0], _j)
    groups = defaultdict(list)
    for i, r in enumerate(idx):
        groups["G::%d" % _find(i)].append(r)

    decisions, asi_rows, phantom_rows, truncation_rows = [], [], [], []
    n_dup_article = n_dup_supp = n_asi = n_truncation = 0
    K_SIM = getattr(args, "sim_k", None) or 3          # FM5 SimHash Hamming threshold (default 3)
    DPG_MIN = getattr(args, "dpg_min", None) or 3       # FM4 truncation min page gap (default 3)
    aggressive_trunc = bool(getattr(args, "aggressive_truncation", False))
    def _pages_int(m):
        try:
            v = str(m.get("pages", "")).strip()
            return int(v) if v else None
        except (TypeError, ValueError):
            return None
    for key, members in groups.items():
        if len(members) < 2:
            continue
        # FM8 record-type consumption: a MAIN article is anything NOT in the NON_MAIN vocabulary and
        # NOT carrying a supplement filename marker. NON_MAIN spans the closed record types that are
        # distinct companion documents to an article and must never be merged into a dup_article
        # KEEP/drop: supplement (SI), dataset, and peer_review (reviewer/editorial file, typed by the
        # indexer's FM2 page-1 banner). Typing an SI or peer-review file correctly (indexer FM1/FM2)
        # is what keeps article+SI and article+peer-review groups from masquerading as duplicate
        # articles; the filename supp_marker is retained as a backstop for files Papers mistyped.
        NON_MAIN = NON_MAIN_TYPES
        def _is_main(m):
            return (m.get("record_type") not in NON_MAIN) and not supp_marker(m["file_name"])
        mains = [m for m in members if _is_main(m)]
        supps = [m for m in members if not _is_main(m)]

        # (1) duplicate MAIN articles within the cluster. Layered decision (safest verdict first; a rule
        #     that cannot decide FLAGs, never auto-drops a distinct item):
        #       (a) titles disagree / authors disagree / _distinct_works  -> FLAG phantom  (FM3)
        #       (b) content SimHash Hamming <= K (same-article near-dup)   -> DROP keep-cleanest (FM5)
        #       (c) a strictly-fuller same-key twin (pages gap >= DPG_MIN) -> FLAG truncation, or DROP the
        #           shorter under --aggressive-truncation                   (FM4)
        #       (d) otherwise (titles agree, small page gap)               -> DROP keep-cleanest (dup_article)
        if len(mains) >= 2:
            titles = [m["_ntitle"] for m in mains if len(m["_ntitle"]) >= 8]
            # every pair of titles must AGREE (fuzzy>=0.80 OR truncated-title containment); a single
            # disagreeing pair -> wrong-DOI phantom. Containment handles extraction-truncated titles.
            titles_ok = all(_titles_agree(titles[i], titles[j])
                            for i in range(len(titles)) for j in range(i + 1, len(titles)))
            distinct = _distinct_works(mains)          # FM3: companion papers / Part-N / distinct DOIs
            if not titles_ok or _authors_disagree(mains) or distinct:
                # titles disagree, authors disagree, or provably distinct works (companion Part-N /
                # distinct DOIs with non-identical titles) -> FLAG, never merge. A distinct-works FLAG
                # carries its own reason so the reviewer sees WHY (not a "wrong-DOI" mislabel).
                reason = ("distinct works under one title-only key (companion Part-N or distinct DOIs) — "
                          "keep both, never merge" if distinct else
                          "titles disagree under one DOI/key — verify DOI before treating as dup")
                for m in mains:
                    phantom_rows.append(dict(cluster_id="MAIN::" + key, file_name=m["file_name"],
                                             first_author=m.get("first_author", ""), year=m.get("year", ""),
                                             title=(m.get("title") or "")[:70], doi=m.get("doi", ""),
                                             reason=reason))
            else:
                # same work. Decide near-dup DROP vs truncation FLAG vs plain dup DROP.
                near = _near_dup_by_content(mains, K_SIM)      # FM5 stamp-robust same-article signal
                pgs = [p for p in (_pages_int(m) for m in mains) if p is not None]
                gap = (max(pgs) - min(pgs)) if len(pgs) >= 2 else 0
                truncated = (gap >= DPG_MIN)                   # FM4: a strictly-fuller same-key twin
                if not near and truncated and not aggressive_trunc:
                    # DEFAULT: a fuller same-work twin exists but we cannot prove the shorter is a
                    # redundant copy vs a legitimately shorter document (SI excerpt / Views&Comments
                    # vs truncated fragment) — FLAG for the human, never auto-drop.
                    n_truncation += 1
                    pg_by_rid = {m["_rid"]: _pages_int(m) for m in mains}
                    for m in mains:
                        truncation_rows.append(dict(cluster_id="MAIN::" + key, file_name=m["file_name"],
                                                    pages=(pg_by_rid[m["_rid"]] if pg_by_rid[m["_rid"]] is not None else ""),
                                                    first_author=m.get("first_author", ""), year=m.get("year", ""),
                                                    title=(m.get("title") or "")[:70], doi=m.get("doi", ""),
                                                    reason="fuller same-key twin (page gap >= %d) — verify truncated copy vs SI/excerpt before dropping" % DPG_MIN))
                else:
                    # near-dup (FM5), OR small-gap dup, OR --aggressive-truncation: DROP the redundant
                    # copy. Under aggressive truncation with a real page gap, KEEP the FULLER copy
                    # explicitly (more pages = more complete); otherwise keep the cleanest by name/size.
                    n_dup_article += 1
                    if truncated and aggressive_trunc and not near:
                        fuller = max(mains, key=lambda m: (_pages_int(m) or -1))
                        keep, decision = {fuller["_rid"]}, "keep_fuller_aggressive_truncation"
                    else:
                        keep, decision = _pick_cleanest(mains)
                    cat = "near_dup_article" if near else "dup_article"
                    for m in mains:
                        decisions.append(dict(cluster_id="MAIN::" + key, category=cat, decision=decision,
                                              row_id=m["_rid"], file_name=m["file_name"],
                                              action=("KEEP" if m["_rid"] in keep else "drop_as_duplicate"),
                                              record_type=m.get("record_type", ""), first_author=m.get("first_author", ""),
                                              year=m.get("year", ""), title=m.get("title", ""), journal=m.get("journal", ""),
                                              doi=m.get("doi", ""), size_bytes=m["_size"], confidence=m.get("confidence", "")))

        # (2) duplicate SUPPLEMENTS. This is the highest-risk call: dropping a DISTINCT supplement
        #     (e.g. Supplementary Data 2 mistaken for a copy of Supplementary Data 1) loses unique
        #     content. So the bar is deliberately high and conservative:
        #       * cluster must be keyed by a REAL DOI (not an author|year|title fallback — SI files
        #         have weak/duplicated author metadata that AYT would over-merge);
        #       * the two files must carry the SAME NUMBERED marker (bare "suppl" with no number is
        #         not enough to prove identity);
        #       * their sizes must be within 3x (a large size gap suggests genuinely different SIs).
        #     Pairs that share a numbered marker but FAIL the size test are FLAGGED for review, never
        #     auto-dropped.
        # SI-namespace preserved after the union-blocking rewrite (coverage-gap #5): the union
        # group may span an article + its SIs, so we do NOT gate on the outer group key. Instead we
        # sub-group SIs by their OWN real-DOI base key and only ever dedup SIs that share a REAL DOI
        # (never an author|year|title fallback — SI author metadata is weak and would over-merge).
        if len(supps) >= 2:
            by_marker = defaultdict(list)
            for s in supps:
                sk = _base_key(s)                    # the SI's own key; require a REAL DOI
                if not (sk and sk.startswith("DOI::")):
                    continue
                mk = supp_marker(s["file_name"])
                if mk and re.search(r"\d", mk):      # numbered markers only
                    by_marker[(sk, mk)].append(s)    # DOI + numbered marker: distinct SIs never merge
            for (_sidoi, marker), grp in by_marker.items():
                if len(grp) < 2:
                    continue
                szs = [m["_size"] for m in grp if m["_size"]]
                size_ok = (not szs) or (max(szs) <= 3 * max(1, min(szs)))
                authors_bad = _authors_disagree(grp)
                if not size_ok or authors_bad:
                    why = ("filename surnames disagree — likely a wrong-DOI phantom, not a copy"
                           if authors_bad else
                           "same SI number but sizes differ >3x — verify these are copies, not distinct SIs")
                    for m in grp:
                        phantom_rows.append(dict(cluster_id="SUPP::%s::%s" % (_sidoi, marker), file_name=m["file_name"],
                                                 first_author=m.get("first_author", ""), year=m.get("year", ""),
                                                 title=(m.get("title") or "")[:70], doi=m.get("doi", ""),
                                                 reason=why))
                    continue
                n_dup_supp += 1
                keep, decision = _pick_cleanest(grp)
                for m in grp:
                    decisions.append(dict(cluster_id="SUPP::%s::%s" % (_sidoi, marker), category="dup_supplement",
                                          decision=decision, row_id=m["_rid"], file_name=m["file_name"],
                                          action=("KEEP" if m["_rid"] in keep else "drop_as_duplicate"),
                                          record_type=m.get("record_type", ""), first_author=m.get("first_author", ""),
                                          year=m.get("year", ""), title=m.get("title", ""), journal=m.get("journal", ""),
                                          doi=m.get("doi", ""), size_bytes=m["_size"], confidence=m.get("confidence", "")))

        # (3) informational: 1 article + its SI(s), no duplicates -> keep all (NOT a dedup target)
        if len(mains) <= 1 and (len(mains) + len(supps)) >= 2 and len(supps) >= 1:
            n_asi += 1
            for m in members:
                asi_rows.append(dict(cluster_id=key, file_name=m["file_name"],
                                     record_type=m.get("record_type", ""), title=(m.get("title") or "")[:70]))

    keep_n = sum(1 for d in decisions if d["action"] == "KEEP")
    drop_n = sum(1 for d in decisions if d["action"] == "drop_as_duplicate")
    _dec_cols = (list(decisions[0].keys()) if decisions else
                 ["cluster_id","category","decision","action","file_name","record_type",
                  "first_author","year","title","journal","doi","size_bytes","confidence"])
    _dec_sorted = sorted(decisions, key=lambda d: (d["cluster_id"], d["action"]))
    def _wdec(f):
        w = csv.DictWriter(f, fieldnames=_dec_cols); w.writeheader(); w.writerows(_dec_sorted)
    write_atomic(args.out, _wdec)          # atomic: a crash leaves the prior decisions file intact
    # asi path: derive robustly whether or not "decisions" is in the out name (coverage-gap: the old
    # .replace("decisions",...) was a silent no-op for any out path lacking that literal, clobbering out).
    _base = os.path.splitext(args.out)[0]
    asi_path = (_base.replace("decisions", "article_plus_SI_groups") if "decisions" in _base
                else _base + "_article_plus_SI_groups") + ".csv"
    def _wasi(f):
        w = csv.DictWriter(f, fieldnames=["cluster_id","file_name","record_type","title"]); w.writeheader(); w.writerows(asi_rows)
    write_atomic(asi_path, _wasi)
    if phantom_rows:
        ph_path = _base + "_PHANTOMS_review.csv"
        def _wph(f):
            w = csv.DictWriter(f, fieldnames=list(phantom_rows[0].keys())); w.writeheader(); w.writerows(phantom_rows)
        write_atomic(ph_path, _wph)
    # FM4: truncation FLAGs (default outcome). A separate review file so the human resolves KEEP-vs-DROP
    # for each fuller/shorter same-work pair; migrate never touches these rows (no KEEP/drop decision was
    # recorded for them), so a flagged pair is preserved intact until the user rules on it.
    if truncation_rows:
        tr_path = _base + "_TRUNCATION_review.csv"
        def _wtr(f):
            w = csv.DictWriter(f, fieldnames=list(truncation_rows[0].keys())); w.writeheader(); w.writerows(truncation_rows)
        write_atomic(tr_path, _wtr)

    n_clusters = n_dup_article + n_dup_supp
    if args.report:
        _nph = len(set(p["cluster_id"] for p in phantom_rows))
        def _wrep(f):
            f.write("# Dedup Report\n\n| Metric | Value |\n|---|---|\n")
            f.write("| Total files indexed | %d |\n" % len(idx))
            f.write("| True duplicate clusters | **%d** |\n" % n_clusters)
            f.write("| Extra copies to drop | **%d** |\n" % drop_n)
            f.write("| Files after keep-1 | %d |\n" % (len(idx) - drop_n))
            f.write("| Article+SI groups (kept intact) | %d |\n" % n_asi)
            f.write("| Wrong-DOI phantom clusters flagged | %d |\n\n" % _nph)
            f.write("Duplicate = same paper, different bytes (Papers re-encodes copies). Cleanest version kept "
                    "by filename quality -> confidence -> size. Article+SI groups and distinct supplements are "
                    "NOT duplicates and are all kept. Phantom clusters (titles disagree under one DOI) are flagged "
                    "for you to verify the DOI — never auto-merged.\n")
        write_atomic(args.report, _wrep)
    print("DEDUP clusters=%d dup_article=%d dup_supplement=%d article_plus_SI=%d phantom_flagged=%d truncation_flagged=%d KEEP=%d drop=%d"
          % (n_clusters, n_dup_article, n_dup_supp, n_asi, len(set(p["cluster_id"] for p in phantom_rows)),
             n_truncation, keep_n, drop_n))
    print("WROTE %s (+ article_plus_SI_groups%s%s)" % (args.out,
          " + PHANTOMS_review" if phantom_rows else "",
          " + TRUNCATION_review" if truncation_rows else ""))

# ----------------------------- migrate -----------------------------
def link_supplements(keep_rows):
    """Group each supplement under its parent ARTICLE for bundle-foldering at export.

    Two linkage signals, merged, with a surname guard against false merges:
      (1) the index's `parent_file` field (filename-stem link from sci-file-index) — PRIMARY,
          because it links a supplement to its article regardless of DOI: it catches SIs with no
          DOI, and the few that carry their OWN DOI (a Dryad/Zenodo/FLUXNET data-repository DOI, or
          a versioned bioRxiv DOI) that a shared-DOI cluster would split away from the paper;
      (2) a shared DOI / author|year|title cluster with exactly one main article — FALLBACK.
    A link is REJECTED when both sides have a parseable filename surname and they disagree (guards
    the wrong-parent links Papers.app sometimes writes), and a whole group is dropped when its
    anchor article has a CRYPTIC name (no parseable surname, e.g. 'Unknown_2004') AND its supplements
    carry >=2 distinct real authors — that is a stem-collision false merge, not a real article+SI set.

    Returns {article_file_name: [supplement_file_name, ...]} for articles that have >=1 real SI.
    Files with no confident parent stay OUT of the mapping (they export flat)."""
    def is_supp(r):
        return (r.get("record_type") == "supplement") or bool(supp_marker(r["file_name"]))
    arts = {r["file_name"]: r for r in keep_rows if not is_supp(r)}
    supps = [r for r in keep_rows if is_supp(r)]
    art_names = set(arts)

    # cluster key -> single main article file_name (for the fallback)
    key_main = {}
    keyed = defaultdict(list)
    for r in keep_rows:
        k = _base_key(r)
        if k:
            keyed[k].append(r)
    for k, members in keyed.items():
        mains = [m for m in members if not is_supp(m)]
        if len(mains) == 1:
            key_main[k] = mains[0]["file_name"]

    def _key_author(k):
        return k.split("|", 1)[0].split("::", 1)[-1] if (k and k.startswith("AYT::")) else ""

    assign, reason = {}, {}
    for s in supps:
        sn = s["file_name"]; pf = s.get("parent_file", ""); a = None
        if pf and pf in art_names:                         # (1) parent_file
            a_sn, s_sn = fname_surname(pf), fname_surname(sn)
            if not (a_sn and s_sn and a_sn != s_sn):
                a = pf
        if a is None:                                      # (2) shared-key fallback
            k = _base_key(s); cand = key_main.get(k)
            if cand:
                a_sn, s_sn = fname_surname(cand), fname_surname(sn)
                if not (a_sn and s_sn and a_sn != s_sn):
                    a = cand
        if a is not None:
            assign[sn] = a; reason[sn] = a

    grp = defaultdict(list)
    for sn, a in assign.items():
        grp[a].append(sn)
    # drop cryptic-anchor false merges (multiple distinct real authors under a nameless article)
    for a in list(grp):
        if fname_surname(a):
            continue
        si_auth = {_key_author(_base_key(next(x for x in supps if x["file_name"] == sn))) for sn in grp[a]}
        si_auth.discard(""); si_auth.discard("unknown")
        if len(si_auth) >= 2:
            del grp[a]
    return dict(grp)


def cmd_migrate(args):
    idx = _read_index(args.index)
    # Drop-set keyed by row_id (collision-safe). Fall back to file_name only for a legacy decisions
    # file written before the row_id column existed (then basenames are assumed unique, as they were).
    with open(args.decisions, encoding="utf-8") as f:
        drows = list(csv.DictReader(f))
    _has_rid = bool(drows) and ("row_id" in drows[0])
    if _has_rid:
        drop = set(r["row_id"] for r in drows if r["action"] == "drop_as_duplicate")
        keep = [r for r in idx if r["_rid"] not in drop]
    else:
        drop_fn = set(r["file_name"] for r in drows if r["action"] == "drop_as_duplicate")
        keep = [r for r in idx if r["file_name"] not in drop_fn]
    by_rid = {r["_rid"]: r for r in idx}

    # canonical names + supplement markers — keyed by _rid so two same-basename keep rows never
    # overwrite each other in the stems/final maps.
    stems = {}
    for r in keep:
        stem = canonical_stem(r)
        sm = supp_marker(r["file_name"])
        if sm and sm != "suppl":
            stem = "%s_%s" % (stem, sm)
        elif sm == "suppl" or r.get("record_type") == "supplement":
            stem = stem + "_suppl"
        stems[r["_rid"]] = stem
    # collision suffixes (-2,-3,...) — deterministic by (stem, rid) order
    final, used = {}, set()
    for rid in sorted(stems, key=lambda k: (stems[k].lower(), k)):
        base, name, n = stems[rid], stems[rid], 2
        while name.lower() in used:
            name = "%s-%d" % (base, n); n += 1
        used.add(name.lower()); final[rid] = name + ".pdf"

    # drift-resistant resolution to real disk files. Each keep ROW resolves to its own source file
    # (by the row's recorded file_name, then a stem-key fallback), keyed by _rid so two same-basename
    # rows resolve independently and one can never shadow the other.
    disk = set(f for f in os.listdir(args.src) if f.lower().endswith(".pdf"))
    disk_by_stem = defaultdict(list)
    for f in disk: disk_by_stem[stem_key(f)].append(f)
    resolved, unresolved = {}, []
    for r in keep:
        rid, fn = r["_rid"], r["file_name"]
        if fn in disk:
            resolved[rid] = fn; continue
        cands = disk_by_stem.get(stem_key(fn), [])
        free = [c for c in cands if c not in resolved.values()]
        if len(free) == 1: resolved[rid] = free[0]
        elif len(cands) == 1: resolved[rid] = cands[0]
        else: unresolved.append(fn)
    if unresolved:
        sys.exit("FATAL: %d keep-files could not be resolved on disk (e.g. %s). Re-extract the index first."
                 % (len(unresolved), unresolved[:3]))

    # BUNDLE (default): an article WITH >=1 accompanying supplement is exported into its OWN folder
    # (named after the article's canonical stem) holding the article + all its supplements. Articles
    # with no SI, and orphan supplements whose parent isn't in the library, export FLAT at the root.
    # This keeps each article+SI set as one atomic unit for later topic-foldering. Opt out: --no-bundle.
    # link_supplements returns file_name-keyed groups; map back to _rid (unique keeps -> unique rid).
    fn2rid = defaultdict(list)
    for r in keep: fn2rid[r["file_name"]].append(r["_rid"])
    subdir = {}                         # keep-file _rid -> relative subfolder ("" = flat root)
    n_bundles = n_bundled_files = 0
    if not args.no_bundle:
        grp = link_supplements(keep)    # {article_file_name: [supp_file_name, ...]}
        n_bundles = len(grp)
        for a, ss in grp.items():
            a_rids = fn2rid.get(a, [])
            if not a_rids: continue
            folder = final[a_rids[0]][:-4] if final[a_rids[0]].lower().endswith(".pdf") else final[a_rids[0]]
            for member in [a] + ss:
                for mrid in fn2rid.get(member, []):
                    subdir[mrid] = folder
                    n_bundled_files += 1

    os.makedirs(args.dst, exist_ok=True)
    manifest, copied, errors = [], 0, []
    for rid in sorted(final, key=lambda k: (final[k].lower(), k)):
        sub = subdir.get(rid, "")
        destdir = os.path.join(args.dst, sub) if sub else args.dst
        src = os.path.join(args.src, resolved[rid]); dst = os.path.join(destdir, final[rid])
        r = by_rid[rid]
        try:
            if not args.dry_run:
                if sub:
                    os.makedirs(destdir, exist_ok=True)
                shutil.copy2(src, dst)
                if os.path.getsize(dst) != os.path.getsize(src):
                    errors.append((final[rid], "size mismatch"))
            copied += 1
        except Exception as e:
            errors.append((final[rid], str(e)[:60]))
        manifest.append(dict(clean_name=final[rid], bundle_folder=sub, original_disk_name=resolved[rid],
                             index_name=r.get("file_name", ""), record_type=r.get("record_type", ""),
                             first_author=r.get("first_author", ""), year=r.get("year", ""),
                             title=r.get("title", ""), journal=r.get("journal", ""),
                             doi=r.get("doi", ""), confidence=r.get("confidence", ""),
                             parent_file=r.get("parent_file", ""),
                             pages=r.get("pages", ""),          # FM4: carry the page count into the master
                             content_sim=r.get("content_sim", ""),  # FM5: carry the SimHash fingerprint
                             src_size=os.path.getsize(src)))
    mpath = os.path.join(args.dst, "_MIGRATION_MANIFEST.csv")
    def _wman(f):
        w = csv.DictWriter(f, fieldnames=list(manifest[0].keys())); w.writeheader(); w.writerows(manifest)
    write_atomic(mpath, _wman)             # atomic: migration manifest never left half-written
    bundle_msg = ("" if args.no_bundle else
                  " | bundles=%d (%d files in article+SI folders, %d flat)"
                  % (n_bundles, n_bundled_files, len(final) - n_bundled_files))
    print("MIGRATE keep=%d copied=%d dropped_dups=%d errors=%d%s%s"
          % (len(final), copied, sum(1 for d in drows if d["action"] == "drop_as_duplicate"), len(errors), bundle_msg, " (DRY RUN)" if args.dry_run else ""))
    for e in errors[:5]: print("  ERR", e)
    print("WROTE %s" % mpath)

# ----------------------------- bundle -----------------------------
def bundle_library(rows, papers_dir, dry_run=False):
    """IDEMPOTENT, in-place article+supplement bundling on the LIVE library + master.

    WHY THIS EXISTS (root cause): folder-bundling of article+SI lived ONLY inside
    cmd_migrate (a full source->dst re-migration). The incremental add-flow copies an
    article + its supplements FLAT to the papers root with bundle_folder="" and never
    bundles, so 108 historical + 106 incremental loose supplements accumulated at root.
    This routine bundles them IN PLACE without a re-migration, and is the function the
    add-flow should call after every incremental add so the defect cannot recur.

    Contract
    --------
    rows       : the master-index rows (list of dicts, one per file), each carrying at
                 least clean_name, record_type, parent_file, bundle_folder. MUTATED in
                 place: bundle_folder is set on every relocated/relabelled row (unless
                 dry_run). clean_name is the primary key and is always a basename.
    papers_dir : the flat clean-library papers root (PAPERS). Members are MOVED (atomic
                 os.replace within the same filesystem) into PAPERS/<folder>/.
    dry_run    : compute and return the full plan WITHOUT creating folders, moving files,
                 or mutating rows.

    Folder name = the article's EXISTING clean_name minus extension (os.path.splitext),
    identical to how cmd_migrate names it (final[a_rid][:-4]). It is NOT re-derived from
    canonical_stem(): the canonical scheme has evolved across defects, so ~72% of already
    -foldered articles would re-derive to a DIFFERENT stem and a re-derive would break both
    idempotency and validate invariant I6 (folder == article stem).

    Pairing is link_supplements (parent_file PRIMARY + shared-key fallback, surname/cryptic
    guards). Solo articles (no SI) and true orphan supplements (no resolvable parent) are
    never in the grouping -> they STAY FLAT.

    Idempotency: a member already at bundle_folder==target is skipped (0 moves, 0 updates).
    A second run on a clean library is a no-op. Partial-run recovery: if the file is already
    at the destination but the master row is stale, the row is relabelled with no move.

    Returns a plan dict:
      {n_articles, actions:[{clean_name, kind:'move'|'relabel', from_folder, to_folder}],
       folders_to_create:[...], already_ok:int, reports:[(clean_name, reason), ...]}
    'move'   = a physical relocation happened/planned; 'relabel' = row-only reconciliation.
    files_to_move = [a for a in actions if a['kind']=='move']; every action is a row update.
    """
    by_name = {}
    for r in rows:
        by_name.setdefault(r["clean_name"], r)      # clean_name is the unique primary key (I1)

    def is_supp(r):
        return (r.get("record_type") == "supplement") or bool(supp_marker(r["clean_name"]))

    # PAIRING — reuse the mandated engine. It keys on file_name; the master keys on
    # clean_name, so shim file_name=clean_name. grp -> {article_clean_name: [supp_clean_name, ...]}
    shim = [{**r, "file_name": r["clean_name"]} for r in rows]
    grp = link_supplements(shim)

    # existing folder claims (folder -> owning article clean_name) for collision avoidance,
    # taken from the master (which the disk<->index invariant keeps in sync with real folders).
    claimed = {}                                     # lower(folder) -> owning article clean_name
    for r in rows:
        bf = (r.get("bundle_folder") or "").strip()
        if bf and not is_supp(r):
            claimed.setdefault(bf.lower(), r["clean_name"])
    reserved = set(claimed)                          # folder names taken (lowercased), extended per run

    plan = {"n_articles": len(grp), "actions": [], "folders_to_create": [],
            "already_ok": 0, "reports": []}
    created = set()                                  # folders we've decided to create this run

    def _choose_folder(a_row):
        cur = (a_row.get("bundle_folder") or "").strip()
        if cur:
            return cur                               # edge (a): parent already foldered -> reuse it
        base = os.path.splitext(a_row["clean_name"])[0]
        name, n = base, 2                            # collision suffix -2,-3,... like cmd_migrate
        while name.lower() in reserved and claimed.get(name.lower()) not in (None, a_row["clean_name"]):
            name = "%s-%d" % (base, n); n += 1
        return name

    def _classify(src, dst):
        dst_ex, src_ex = os.path.exists(dst), os.path.exists(src)
        if dst_ex and not src_ex:
            return "relabel"                         # already moved by a prior partial run; row stale
        if dst_ex and src_ex:
            return "conflict"                        # a copy in BOTH places -> never clobber
        if src_ex:
            return "move"
        return "missing"

    grouped_supps = {s for ss in grp.values() for s in ss}
    for a in sorted(grp):
        a_row = by_name.get(a)
        if a_row is None or is_supp(a_row):
            # edge (b): anchor missing, or (defensively) supplement-typed -> report, never crash
            plan["reports"].append((a, "anchor row missing or supplement-typed; group skipped"))
            continue
        target = _choose_folder(a_row)
        reserved.add(target.lower()); claimed.setdefault(target.lower(), a)
        target_dir = os.path.join(papers_dir, target)
        for m in [a] + list(grp[a]):
            m_row = by_name.get(m)
            if m_row is None:
                plan["reports"].append((m, "member row missing; skipped")); continue
            cur = (m_row.get("bundle_folder") or "").strip()
            if cur == target:
                plan["already_ok"] += 1              # already correctly foldered -> no-op
                continue
            if cur:
                # SCOPE GUARD: this member already lives in a DIFFERENT folder. That is a
                # PRE-EXISTING split/mis-named-folder (defect #51/#53 class: article renamed after
                # bundling, or article+SI landed in two differently-named folders), NOT the
                # loose-at-root bundling defect this routine targets. Auto-shuffling it would empty
                # its source folder and make cross-author-variant moves that need human judgment.
                # Report it and LEAVE IT IN PLACE (safe-by-default).
                plan["reports"].append((m, "already foldered in %r != target %r (pre-existing split); left in place for review" % (cur, target)))
                continue
            src_rel = os.path.join(cur, m) if cur else m
            dst_rel = os.path.join(target, m)
            src = os.path.join(papers_dir, src_rel)
            dst = os.path.join(papers_dir, dst_rel)
            status = _classify(src, dst)
            if status == "conflict":
                plan["reports"].append((m, "file exists at BOTH %r and %r; not clobbering" % (src_rel, dst_rel)))
                continue
            if status == "missing":
                plan["reports"].append((m, "file not found at %r or %r; row left unchanged" % (src_rel, dst_rel)))
                continue
            if status == "move":
                if target not in created and not os.path.isdir(target_dir):
                    plan["folders_to_create"].append(target)
                created.add(target)
                if not dry_run:
                    os.makedirs(target_dir, exist_ok=True)
                    os.replace(src, dst)             # atomic within the papers filesystem
                plan["actions"].append({"clean_name": m, "kind": "move",
                                        "from_folder": cur, "to_folder": target})
            else:                                    # relabel (file already in place)
                plan["actions"].append({"clean_name": m, "kind": "relabel",
                                        "from_folder": cur, "to_folder": target})
            if not dry_run:
                m_row["bundle_folder"] = target

    # edge (b) informational: loose supplements whose parent_file points to a SUPPLEMENT-typed
    # row (a broken/chained pointer). link_supplements correctly refuses these as anchors, so
    # they legitimately STAY FLAT — surface them for human review rather than force-bundling.
    for r in rows:
        if not is_supp(r) or (r.get("bundle_folder") or "").strip():
            continue
        cn = r["clean_name"]
        if cn in grouped_supps:
            continue
        pf = (r.get("parent_file") or "").strip()
        if pf and pf in by_name and is_supp(by_name[pf]):
            plan["reports"].append((cn, "parent_file -> supplement-typed row %r; left flat for review" % pf))
    return plan


def cmd_bundle(args):
    """CLI wrapper: idempotently bundle the LIVE library + master in place.

    Reads --index (the master), bundles under --papers, and writes the master back with its
    EXACT original columns (dropping the internal _rid). --dry-run prints/writes the full plan
    and mutates NOTHING. --report PATH writes a machine-readable plan CSV (action,clean_name,
    from_folder,to_folder). Run it after every incremental add so loose SI can never accumulate.
    """
    rows = _read_index(args.index)
    if not rows:
        print("BUNDLE: empty index, nothing to do"); return
    plan = bundle_library(rows, args.papers, dry_run=args.dry_run)
    moves = [a for a in plan["actions"] if a["kind"] == "move"]
    relabels = [a for a in plan["actions"] if a["kind"] == "relabel"]

    if not args.dry_run and plan["actions"]:
        _write_master(args.index, rows)   # preserve the master's exact schema/order (incl. author cols if present)

    if args.report:
        def _wr(f):
            w = csv.writer(f)
            w.writerow(["action", "clean_name", "from_folder", "to_folder"])
            for a in plan["actions"]:
                w.writerow([a["kind"], a["clean_name"], a["from_folder"], a["to_folder"]])
            for cn, reason in plan["reports"]:
                w.writerow(["review", cn, "", reason])
        write_atomic(args.report, _wr)

    tag = " (DRY RUN)" if args.dry_run else ""
    print("BUNDLE%s: articles_with_SI=%d | folders_to_create=%d | files_to_move=%d | rows_relabelled=%d | already_ok=%d | reports=%d"
          % (tag, plan["n_articles"], len(plan["folders_to_create"]), len(moves),
             len(relabels), plan["already_ok"], len(plan["reports"])))
    cap = None if args.dry_run else 20
    for fdir in plan["folders_to_create"][:cap]: print("  +dir", fdir)
    for a in moves[:cap]: print("  mv  [%s] -> %s/" % (a["from_folder"] or "<root>", a["to_folder"]), a["clean_name"])
    for a in relabels[:cap]: print("  set bundle_folder=%s (in place)" % a["to_folder"], a["clean_name"])
    for cn, reason in plan["reports"][:cap]: print("  review", cn, "::", reason)
    if cap is not None:
        extra = max(0, len(moves) - cap) + max(0, len(relabels) - cap) + max(0, len(plan["reports"]) - cap)
        if extra: print("  ... (%d more; pass --report for the full plan)" % extra)
    if args.report: print("WROTE %s" % args.report)

# ----------------------------- organize -----------------------------
def default_taxonomy():
    """Topic -> {Subtopic: regex}. EDIT THIS to match the target library's research domains.
    Patterns run case-insensitively against 'title journal'; primary folder = most hits."""
    return {
     "Leaf energy balance": {
        "Boundary layer & conductance": r"boundary layer|leaf boundary|aerodynamic conductance",
        "Leaf temperature & thermal stress": r"leaf temperature|leaf thermal|thermoregulat|heat dissipat|leaf cooling|thermal tolerance|thermal safety|critical temperature|tcrit|heat stress|thermal damage|leaf-to-air|leaf energy",
        "Transpiration & latent heat": r"transpirat|latent heat|evaporative cool|sensible heat|leaf evaporation",
        "Radiation & leaf optics": r"leaf absorptance|leaf reflectance|leaf optic|radiation balance|leaf angle|shortwave|longwave|net radiation"},
     "Stomata & gas exchange": {
        "Stomatal conductance & regulation": r"stomatal conductance|stomatal regulat|stomatal behavio|stomatal response|stomatal control|stomatal closure|stomatal opening",
        "Stomatal anatomy & density": r"stomatal densit|stomatal size|stomatal morpholog|stomatal anatomy|guard cell|stomatal pore",
        "Gas exchange & WUE": r"gas exchange|water use efficiency|water-use efficiency|intrinsic wue|carbon-water"},
     "Plant water relations & hydraulics": {
        "Xylem hydraulics & embolism": r"xylem|embolism|cavitation|hydraulic conduct|vessel|tracheid|hydraulic failure|hydraulic safety|conduit",
        "Water potential & turgor": r"water potential|turgor|osmotic|pressure-volume|leaf water|tissue water",
        "Drought response": r"drought|water stress|water deficit|dry season|water limitation|desiccat",
        "Sap flow & whole-plant water use": r"sap flow|sap flux|whole-plant water|transpiration stream|water transport|root water"},
     "Photosynthesis & carbon": {
        "Photosynthetic capacity & biochemistry": r"photosynthetic capacit|vcmax|jmax|rubisco|carboxylation|electron transport|light-saturated|quantum yield|light use efficiency|carbon assimilation|net assimilation",
        "Respiration & carbon balance": r"respiration|carbon balance|carbon flux|npp|gpp|carbon uptake|carbon cycl|carbon budget|leaf respiration|dark respiration",
        "Light & shade acclimation": r"shade|light acclimat|sun leaf|light gradient|light environment|photoinhibition|light response",
        "Photosynthesis modeling": r"photosynthesis model|farquhar|coupled model|canopy photosynthesis|a-ci|biochemical model"},
     "Leaf traits & economics": {
        "Leaf economic spectrum": r"leaf economic|leaf mass per area|specific leaf area|\bsla\b|\blma\b|leaf lifespan|leaf longevit|leaf dry mass|trait spectrum|trait trade",
        "Nutrients (N, P)": r"nitrogen|phosphorus|nutrient|\bn:p\b|foliar nutrient|leaf nitrogen|nutrient resorption|stoichiometr",
        "Phenology & leaf age": r"phenolog|leaf age|leaf development|leaf expansion|leaf flush|leaf senescence|budburst|leafing",
        "Functional traits & variation": r"functional trait|trait variation|intraspecific|trait-based|plant strateg"},
     "Canopy & forest structure": {
        "Canopy structure & light": r"canopy structure|leaf area index|\blai\b|canopy cover|crown|vertical gradient|vertical stratif|canopy gradient|canopy layer|light interception|canopy height",
        "Tropical forest ecology": r"tropical forest|tropical tree|rainforest|amazon|neotropical|tropical rain|lowland forest|tropical canopy",
        "Forest function & productivity": r"forest productiv|forest carbon|ecosystem function|forest ecosystem|stand-level|forest dynamics|forest growth"},
     "Microbial ecology": {
        "Phyllosphere & leaf microbiome": r"phyllosphere|leaf microbiome|leaf-associated|epiphyt|leaf surface microb|foliar microb|foliar fungal|leaf endophyt",
        "Endophytes & plant-microbe": r"endophyt|plant-microbe|plant-associated|mutualis|symbiot|colonization by|host-microbe|plant defense",
        "Microbial community & diversity": r"microbial communit|microbial diversit|bacterial communit|fungal communit|community assembly|microbial biogeograph|16s|amplicon|metagenom|microbial ecolog",
        "Soil microbiology": r"soil bacteri|soil fungal|soil microb|soil communit|rhizosphere|soil biogeochem"},
     "Microclimate & micrometeorology": {
        "Canopy microclimate": r"microclimat|canopy climate|within-canopy|understory climate|forest climate|leaf wetness|canopy humidity",
        "Micrometeorology & fluxes": r"micrometeorolog|eddy covariance|flux tower|surface energy|evapotranspiration|vapor pressure deficit|\bvpd\b|atmospheric|humidity|wind speed"},
     "Remote sensing & modeling": {
        "Remote sensing": r"remote sens|satellite|reflectance spectr|hyperspectral|\bndvi\b|solar-induced|thermal imaging|lidar|imaging spectroscop",
        "Ecosystem & land-surface modeling": r"land surface model|ecosystem model|earth system model|dynamic global veget|\bdgvm\b|process-based model|scaling|upscal"},
     "Climate change & global ecology": {
        "Warming & thermal acclimation": r"climate warming|global warming|thermal acclimat|temperature response|warming experiment|heat wave|elevated temperature",
        "Elevated CO2 & global change": r"elevated co2|\bface\b|global change|rising co2|carbon dioxide enrichment",
        "Biogeography & macroecology": r"biogeograph|macroecolog|latitudinal|global pattern|species distribution|range shift|global scale"},
    }

CATCHALL_TOPIC = "Other"
CATCHALL_SUB = "General ecology"
CATCHALL_CAT = "Other/General ecology"   # single clean slash -> splits to (CATCHALL_TOPIC, CATCHALL_SUB)

def classify_regex(title, journal, taxonomy):
    """Return (topic, subtopic, tags[]) — primary = most keyword hits; tags = all matches."""
    text = ("%s %s" % (title, journal)).lower()
    scores, tags = {}, []
    for top, subs in taxonomy.items():
        for sub, pat in subs.items():
            n = len(re.findall(pat, text, re.I))
            if n:
                scores[(top, sub)] = n
                tags.append("%s/%s" % (top, sub))
    if not scores:
        return "", "", []
    (top, sub), _ = max(scores.items(), key=lambda kv: kv[1])
    return top, sub, tags

def cmd_organize(args):
    idx = _read_index(args.index)
    by_name = {r["file_name"]: r for r in idx}
    with open(args.manifest, encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))
    tax = default_taxonomy()
    if args.taxonomy and os.path.exists(args.taxonomy):
        tax = json.load(open(args.taxonomy, encoding="utf-8"))

    topic, sub, tags = {}, {}, {}
    for r in idx:
        t, s, tg = classify_regex(r.get("title", ""), r.get("journal", ""), tax)
        if t:
            topic[r["file_name"]] = t; sub[r["file_name"]] = s; tags[r["file_name"]] = "; ".join(tg)
    # optional LLM assignments for the regex-unclassified tail
    if args.llm_assignments and os.path.exists(args.llm_assignments):
        la = json.load(open(args.llm_assignments, encoding="utf-8"))
        for fn, cat in la.items():
            if fn in topic: continue
            if "/" in cat:
                t, s = cat.split("/", 1); topic[fn], sub[fn] = t.strip(), s.strip()
            else: topic[fn], sub[fn] = CATCHALL_TOPIC, cat.strip()
    # supplements inherit parent topic
    for r in idx:
        if r["file_name"] in topic: continue
        if r.get("record_type") == "supplement" and r.get("parent_file") in topic:
            pf = r["parent_file"]
            topic[r["file_name"]], sub[r["file_name"]] = topic[pf], sub.get(pf, "")
            tags[r["file_name"]] = "(supplement of %s)" % pf[:40]

    unclassified = [m for m in manifest if m["index_name"] not in topic]
    if unclassified and not args.llm_assignments:
        cats = ["%s/%s" % (t, s) for t, subs in tax.items() for s in subs]
        out = {"categories": cats + [CATCHALL_CAT],
               "tasks": [{"index_name": m["index_name"], "title": (m["title"] or "")[:200],
                          "journal": (m["journal"] or "")[:60]} for m in unclassified]}
        uf = os.path.join(args.dst, "_unclassified_for_llm.json")
        write_atomic(uf, lambda f: json.dump(out, f))
        print("ORGANIZE regex-classified=%d unclassified=%d -> wrote %s (run the LLM pass, then re-run with --llm-assignments)"
              % (len(manifest) - len(unclassified), len(unclassified), uf))
        if not args.force:
            return

    # place files into the tree + write library index. Bundle-aware: a file that migrate put inside
    # an article+SI bundle folder (manifest 'bundle_folder') keeps that folder as an atomic unit —
    # the whole bundle moves under the ARTICLE's topic, and every member inherits the article's topic
    # so an SI never lands in a different folder than its article.
    art_topic = {}   # bundle_folder -> (topic, subtopic) taken from the article row
    for m in manifest:
        bf = m.get("bundle_folder", "")
        if bf and m.get("record_type") != "supplement" and not supp_marker(m["index_name"]):
            art_topic[bf] = (topic.get(m["index_name"], CATCHALL_TOPIC), sub.get(m["index_name"], CATCHALL_SUB))

    moved = 0; rows = []; bundles_done = set()
    for m in manifest:
        fn = m["index_name"]; cn = m["clean_name"]; bf = m.get("bundle_folder", "")
        if bf:                                   # member of an article+SI bundle
            tp, sb = art_topic.get(bf, (topic.get(fn, CATCHALL_TOPIC), sub.get(fn, CATCHALL_SUB)))
        else:
            tp, sb = topic.get(fn, CATCHALL_TOPIC), sub.get(fn, CATCHALL_SUB)
        destdir = os.path.join(args.dst, safe_dir(tp), safe_dir(sb) if sb else "_general")
        if bf:
            # move the whole bundle folder ONCE, into the topic dir
            src_bundle = os.path.join(args.dst, bf); dst_bundle = os.path.join(destdir, bf)
            if bf not in bundles_done:
                os.makedirs(destdir, exist_ok=True)
                if not args.dry_run and os.path.isdir(src_bundle):
                    shutil.move(src_bundle, dst_bundle)
                bundles_done.add(bf)
            moved += 1
            m2 = dict(m); m2["topic"] = tp; m2["subtopic"] = sb; m2["tags"] = tags.get(fn, "")
            m2["tree_path"] = "%s/%s/%s/%s" % (safe_dir(tp), safe_dir(sb) if sb else "_general", bf, cn)
        else:
            os.makedirs(destdir, exist_ok=True)
            src = os.path.join(args.dst, cn); dst = os.path.join(destdir, cn)
            if not args.dry_run and os.path.exists(src):
                shutil.move(src, dst); moved += 1
            m2 = dict(m); m2["topic"] = tp; m2["subtopic"] = sb; m2["tags"] = tags.get(fn, "")
            m2["tree_path"] = "%s/%s/%s" % (safe_dir(tp), safe_dir(sb) if sb else "_general", cn)
        rows.append(m2)
    lib = os.path.join(args.dst, "_LIBRARY_INDEX.csv")
    cols = ["clean_name","topic","subtopic","tags","tree_path","bundle_folder","record_type","first_author","year","title","journal","doi","confidence","parent_file","original_disk_name","index_name","src_size"]
    def _wlib(f):
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    write_atomic(lib, _wlib)               # atomic: final library CSV never left half-written
    dist = Counter(r["topic"] for r in rows)
    print("ORGANIZE placed=%d files into %d top-categories%s" % (moved, len(dist), " (DRY RUN)" if args.dry_run else ""))
    for t, c in dist.most_common(): print("  %5d  %s" % (c, t))
    print("WROTE %s" % lib)

def cmd_catalog(args):
    """CATALOG — regenerate the one-row-per-WORK clean lookup table from the master index.

    The master index is one row per FILE (article, book section, supplement, dataset). This
    derives a one-row-per-WORK view: supplements, datasets, and multi-section book chapters are
    COLLAPSED onto their parent work, so a reader gets a single line per article/book with its
    clean path and its supplements listed inline. It is a MATERIALIZED VIEW of the master — always
    regenerate it (never hand-edit), and it re-runs the disk 1:1 reconciliation so a stale catalog
    cannot silently drift from the files on disk (the recurring failure this tool exists to prevent).

    Clustering rule (grounded in bundle_folder, NOT the partially-stale parent_file column):
      * files sharing a bundle_folder = one work; primary = the file whose stem == folder name,
        else the shortest-named non-supplement, else (orphan folder) the shortest-named file;
      * a loose file (blank bundle_folder) = one work on its own.
    With --lib, every emitted clean_path is verified to exist on disk and the reconciliation
    (index paths missing / disk-lit files unindexed) is asserted; a non-empty mismatch exits 1.
    """
    idx = _read_index(args.index)
    if not idx:
        print("CATALOG: empty index"); sys.exit(1)
    name_col = "clean_name" if "clean_name" in idx[0] else "file_name"
    has_folder = "bundle_folder" in idx[0]
    SUPP = {"supplement", "dataset"}

    def relpath(r):
        bf = (r.get("bundle_folder") or "").strip() if has_folder else ""
        cn = (r.get(name_col) or "").strip()
        return os.path.join(bf, cn) if bf else cn

    def is_supp(r):
        # typed supplement/dataset OR filename carries a supplement marker
        return r.get("record_type") in SUPP or bool(supp_marker(r.get(name_col, "")))

    # --- cluster into works ---
    by_folder, loose = defaultdict(list), []
    for r in idx:
        bf = (r.get("bundle_folder") or "").strip() if has_folder else ""
        (by_folder[bf].append(r) if bf else loose.append(r))

    works = []  # (primary_row, [component_rows], folder)
    for bf, rs in by_folder.items():
        arts = [r for r in rs if not is_supp(r)]
        prim = next((r for r in arts if os.path.splitext((r.get(name_col) or "").strip())[0] == bf), None)
        if prim is None and arts:
            prim = min(arts, key=lambda r: len(r.get(name_col, "")))
        if prim is None:  # folder of only supplements (orphan)
            prim = min(rs, key=lambda r: len(r.get(name_col, "")))
        works.append((prim, [r for r in rs if r is not prim], bf))
    for r in loose:
        works.append((r, [], ""))

    def _desc(c):
        base = os.path.basename(relpath(c))
        t = (c.get("title") or "").strip()
        return "%s :: %s" % (base, t[:60]) if t else base

    cols = ["work_key", "first_author", "authors", "n_authors", "last_author",
            "year", "title", "journal", "record_type", "doi",
            "confidence", "pages", "date_time_added", "clean_path", "in_folder", "folder", "n_components",
            "n_supplements", "component_paths", "supplement_desc", "notes"]
    out_rows = []
    for prim, comps, bf in works:
        supp = [c for c in comps if is_supp(c)]
        other_arts = [c for c in comps if not is_supp(c)]
        note = []
        if other_arts and prim.get("record_type") != "book_chapter":
            note.append("folder has %d additional article-typed file(s) — review which is primary" % len(other_arts))
        if prim.get("record_type") == "book_chapter":
            note.append("multi-section book: %d sections total" % (len(comps) + 1))
        if is_supp(prim):
            note.append("folder contains only supplements (orphan) — no primary article")
        out_rows.append({
            "work_key": os.path.splitext((prim.get(name_col) or "").strip())[0],
            "first_author": prim.get("first_author", ""),
            "authors": prim.get("authors", ""),
            "n_authors": prim.get("n_authors", ""),
            "last_author": prim.get("last_author", ""),
            "year": prim.get("year", ""),
            "title": prim.get("title", ""), "journal": prim.get("journal", ""),
            "record_type": prim.get("record_type", ""), "doi": prim.get("doi", ""),
            "confidence": prim.get("confidence", ""),
            "pages": prim.get("pages", ""),        # FM4: surface the primary work's page count
            "date_time_added": prim.get("date_time_added", ""),
            "clean_path": relpath(prim), "in_folder": "yes" if bf else "no", "folder": bf,
            "n_components": len(comps), "n_supplements": len(supp),
            "component_paths": " | ".join(relpath(c) for c in comps),
            "supplement_desc": " | ".join(_desc(c) for c in supp),
            "notes": "; ".join(note),
        })
    out_rows.sort(key=lambda d: (str(d["first_author"]).lower(), str(d["year"]), str(d["title"])[:30]))

    # --- disk reconciliation (with --lib): every clean_path exists AND 1:1 both ways ---
    recon_fail = []
    if args.lib:
        lit_ext = (".pdf", ".txt", ".docx", ".xlsx", ".xls", ".doc")
        disk_paths = set()
        for dp, _, fs in os.walk(args.lib):
            for f in fs:
                if f.startswith("_") or f.startswith(".") or f == os.path.basename(args.index):
                    continue
                disk_paths.add(os.path.relpath(os.path.join(dp, f), args.lib))
        idx_paths = set(relpath(r) for r in idx)
        missing = idx_paths - disk_paths
        disk_lit = {p for p in disk_paths if p.lower().endswith(lit_ext)}
        unindexed = disk_lit - idx_paths
        gone = [d["clean_path"] for d in out_rows if not os.path.exists(os.path.join(args.lib, d["clean_path"]))]
        if missing:   recon_fail.append("index paths NOT on disk: %d (e.g. %s)" % (len(missing), list(missing)[:3]))
        if unindexed: recon_fail.append("disk literature files NOT in index: %d (e.g. %s)" % (len(unindexed), list(unindexed)[:3]))
        if gone:      recon_fail.append("catalog clean_path NOT on disk: %d (e.g. %s)" % (len(gone), gone[:3]))

    def _w(f):
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for d in out_rows:
            w.writerow(d)
    write_atomic(args.out, _w)

    n_supp_works = sum(1 for d in out_rows if d["n_supplements"] > 0)
    n_flag = sum(1 for d in out_rows if d["notes"])
    print("CATALOG %s -> %s: %d works from %d file-rows | %d with supplements | %d flagged"
          % (name_col, args.out, len(out_rows), len(idx), n_supp_works, n_flag))
    if args.lib:
        if recon_fail:
            print("  RECONCILE FAIL:")
            for m in recon_fail: print("   ", m)
        else:
            print("  RECONCILE ok: index<->disk 1:1, all clean_paths present")
    sys.exit(1 if recon_fail else 0)

def cmd_validate(args):
    """VALIDATE — the vaccine. Six structural invariants over the index (and, with --lib, the disk),
    each a fail-loud check. Re-running this after any mutating stage catches the drift classes that
    previously reached the user (#51 year-first folders, #53 folder!=article-stem, ALLCAPS author,
    duplicate clean_name, first_author_ascii out of sync). Exit code 0 = all pass, 1 = any FAIL.

    Invariants:
      I1  no duplicate clean_name (the primary key must be unique)
      I2  no year-first name: every clean_name matches Author_YYYY_...  (Author must not be a bare year)
      I3  first_author_ascii == asciify(first_author) for every row (derived cache in sync)
      I4  no Unknown/blank author, year, OR title on a row typed article (completeness floor)
      I5  [--lib] every index clean_name exists on disk AND every disk lit file (.pdf/.txt/.docx/.xlsx/.xls/.doc) is in the index (1:1)
      I6  [--lib] every bundle_folder on disk matches the canonical stem of the article it contains
    I7  no title<->journal swap: a title field must not be a journal/venue name (books exempt)
    I8  parent-link integrity: every supplement parent_file resolves to a real index row
    I10 authors[0] family agrees with first_author (v5 co-author cache in sync; corporate/compound tolerant)
    I11 n_authors is a non-negative integer and (absent the "[+N more]" marker) equals the displayed name count
    """
    idx = _read_index(args.index)
    name_col = "clean_name" if (idx and "clean_name" in idx[0]) else "file_name"
    fails, warns = [], []

    # I1 duplicate primary key
    from collections import Counter
    dupe = [n for n, c in Counter(r.get(name_col, "") for r in idx).items() if n and c > 1]
    if dupe:
        fails.append("I1 duplicate %s: %d (e.g. %s)" % (name_col, len(dupe), dupe[:3]))

    # I2 year-first name (Author token must not be 4 digits)
    yearfirst = [r.get(name_col, "") for r in idx
                 if re.match(r"^(1[6-9]\d\d|20[0-2]\d)_", str(r.get(name_col, "")))]
    if yearfirst:
        fails.append("I2 year-first name (Author dropped): %d (e.g. %s)" % (len(yearfirst), yearfirst[:3]))

    # I3 derived first_author_ascii in sync with asciify(first_author)
    if idx and "first_author_ascii" in idx[0]:
        drift = [(r.get(name_col, ""), r.get("first_author", ""), r.get("first_author_ascii", ""))
                 for r in idx
                 if _asciify(r.get("first_author", "")) != (r.get("first_author_ascii", "") or "")]
        if drift:
            fails.append("I3 first_author_ascii out of sync with asciify(first_author): %d (e.g. %s)"
                         % (len(drift), [d[0] for d in drift[:3]]))

    # I9 name-metadata columns (surname_sep, name_features) must equal a fresh re-derivation from
    # first_author — they are a cache, never authoritative (same discipline as I3). A blank-author
    # row must read surname_sep=NA, name_features=''.
    if idx and "surname_sep" in idx[0]:
        def _exp_sep(r):
            fa = r.get("first_author", "") or ""
            return _surname_sep(fa) if fa.strip() else "NA"
        def _exp_feat(r):
            fa = r.get("first_author", "") or ""
            return _name_features(fa) if fa.strip() else ""
        sep_drift = [r.get(name_col, "") for r in idx if (r.get("surname_sep", "") or "") != _exp_sep(r)]
        feat_drift = [r.get(name_col, "") for r in idx if (r.get("name_features", "") or "") != _exp_feat(r)]
        if sep_drift:
            fails.append("I9 surname_sep out of sync with surname_sep(first_author): %d (e.g. %s)"
                         % (len(sep_drift), sep_drift[:3]))
        if feat_drift:
            fails.append("I9 name_features out of sync with name_features(first_author): %d (e.g. %s)"
                         % (len(feat_drift), feat_drift[:3]))

    # I10/I11 co-author-column cache consistency (v5 schema; guarded so a pre-author 17-col index
    # is skipped cleanly). authors[0] and first_author are BOTH content-corroborated identity fields:
    # this invariant prevents them silently diverging (e.g. a future backfill adopting a borrowed-DOI
    # author list whose author[0] contradicts the vetted first_author). Same discipline as I3/I9:
    # derive-and-compare, report the drift list, never mutate.
    if idx and "authors" in idx[0]:
        _I10_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2212"   # hyphen, non-breaking/figure/en/em dash, minus
        def _au_norm(s):
            # casefold + NFKD-strip-accents + unify every Unicode dash to ASCII '-' (mirrors asciify's
            # dash discipline; a bare ascii-ignore would DELETE en/em dashes and fuse tokens).
            s = str(s or "")
            for _d in _I10_DASHES:
                s = s.replace(_d, "-")
            s = unicodedata.normalize("NFKD", s)
            s = "".join(c for c in s if not unicodedata.combining(c))
            return s.casefold()
        _I10_CORP = ("consortium", "initiative", "group", "team", "network", "collaboration")
        def _i10_ok(a0, fa):
            # PASS if any of: (a) corporate/consortium first author; (b) hyphen/diacritic-insensitive
            # family==first_author; (c) either contains the other; (d) whitespace-token overlap between
            # first_author and authors[0] (tolerates compound-surname splits: "Silva" vs "Silva de Araujo, C.").
            if not str(a0).strip():
                return True                                    # blank authors[0] -> I10 does not require population
            if any(k in str(a0).lower() for k in _I10_CORP):
                return True                                    # (a) corporate/consortium
            fam = str(a0).split(",", 1)[0]                     # FAMILY = substring before first comma
            nf, nfa = _au_norm(fam), _au_norm(fa)
            if not nfa:
                return True                                    # no first_author to compare against
            if nf == nfa:
                return True                                    # (b) equality
            if nf and (nf in nfa or nfa in nf):
                return True                                    # (c) containment
            toks_fa = set(nfa.split())
            toks_a0 = set(_au_norm(str(a0).replace(",", " ")).split())
            if toks_fa & toks_a0:
                return True                                    # (d) token overlap
            return False
        i10_drift = [(r.get(name_col, ""), (r.get("authors", "") or "").split("; ")[0], r.get("first_author", ""))
                     for r in idx
                     if (r.get("authors", "") or "").strip()
                     and not _i10_ok((r.get("authors", "") or "").split("; ")[0], r.get("first_author", "") or "")]
        if i10_drift:
            fails.append("I10 authors[0] family out of sync with first_author: %d (e.g. %s)"
                         % (len(i10_drift), [d[0] for d in i10_drift[:3]]))

        # I11 n_authors sanity: non-empty n_authors must be a non-negative integer string; and when
        # authors is populated WITHOUT the "[+N more]" overflow marker (i.e. the display is not capped
        # at 7), the count of "; "-delimited names must equal int(n_authors). When the marker IS present
        # the display is capped at 7 by design, so the equality check is skipped for that row.
        def _nonneg_int(s):
            return bool(re.fullmatch(r"[0-9]+", str(s or "").strip()))
        i11_badint = [r.get(name_col, "") for r in idx
                      if str(r.get("n_authors", "") or "").strip() and not _nonneg_int(r.get("n_authors", ""))]
        i11_badcount = [r.get(name_col, "") for r in idx
                        if (r.get("authors", "") or "").strip()
                        and "[+" not in (r.get("authors", "") or "")
                        and _nonneg_int(r.get("n_authors", ""))
                        and len((r.get("authors", "") or "").split("; ")) != int(str(r.get("n_authors", "")).strip())]
        if i11_badint:
            fails.append("I11 n_authors not a non-negative integer: %d (e.g. %s)"
                         % (len(i11_badint), i11_badint[:3]))
        if i11_badcount:
            fails.append("I11 n_authors != displayed author count (no overflow marker): %d (e.g. %s)"
                         % (len(i11_badcount), i11_badcount[:3]))

    # I4 completeness floor on articles (Unknown/blank author, year, or title)
    def _unk(v):
        v = str(v or "").strip().lower()
        return v in ("", "unknown", "n/a", "na", "none", "null", "tbd")
    bad = [r.get(name_col, "") for r in idx
           if r.get("record_type") == "article"
           and (_unk(r.get("first_author")) or _unk(r.get("year")) or _unk(r.get("title")))]
    if bad:
        warns.append("I4 article rows missing author/year/title: %d (e.g. %s)" % (len(bad), bad[:3]))

    # I7 title<->journal swap / venue-as-title (article & similar; books legitimately have venue-like titles)
    # Detects the Silber-class defect: a journal/venue name sitting in the title field.
    import re as _re
    def _n(s): return _re.sub(r"[^a-z0-9]", "", str(s or "").lower())
    _BOOKTYPES = {"book", "book_chapter", "bookchapter", "thesis", "report", "manual", "dataset", "supplement"}
    _VENUE = _re.compile(r"^\s*(proceedings of|journal of|annual review of|transactions of|bulletin of|"
                         r"philosophical transactions|frontiers in|trends in|methods in|the journal of|"
                         r"international journal of|reviews of|advances in|"
                         r"proceedings of the national academy)\b", _re.I)
    # real journal signatures = any journal string used by >=2 rows
    from collections import Counter as _C
    _jc = _C(_n(r.get("journal", "")) for r in idx if str(r.get("journal", "")).strip())
    _known = {j for j, c in _jc.items() if c >= 2 and len(j) >= 6}
    swap = []
    for r in idx:
        if _n(r.get("record_type", "")) in _BOOKTYPES:
            continue
        ti = str(r.get("title", "") or "").strip()
        jr = str(r.get("journal", "") or "").strip()
        if not ti:
            continue
        nti = _n(ti)
        if nti in _known or (_VENUE.match(ti) and len(ti.split()) <= 7 and not jr) or (_VENUE.match(ti) and _n(jr) == nti):
            swap.append(r.get(name_col, ""))
    if swap:
        warns.append("I7 title looks like a journal/venue name (title<->journal swap?): %d (e.g. %s)" % (len(swap), swap[:3]))

    # I8 parent-link integrity: every supplement's parent_file (when set) must resolve to a real clean_name in the index.
    # Catches stale parent pointers left behind when the parent article was renamed (journal-abbrev drift, author fix, etc.).
    _names = set(r.get(name_col, "") for r in idx)
    dangling = [r.get(name_col, "") for r in idx
                if r.get("record_type") == "supplement"
                and str(r.get("parent_file", "")).strip()
                and r.get("parent_file") not in _names]
    if dangling:
        warns.append("I8 supplement parent_file does not resolve to an index row: %d (e.g. %s)" % (len(dangling), dangling[:3]))

    # I5/I6 disk invariants (only when --lib given)
    if args.lib:
        disk = []
        _LIT_EXT = (".pdf", ".txt", ".docx", ".xlsx", ".xls", ".doc",
                    ".png", ".jpeg", ".jpg", ".zip", ".csv", ".tif", ".tiff")
        for dp, _, fs in os.walk(args.lib):
            for f in fs:
                if f.lower().endswith(_LIT_EXT) and not f.startswith("."):
                    disk.append((f, os.path.relpath(dp, args.lib)))
        disk_names = set(f for f, _ in disk)
        idx_names = set(r.get(name_col, "") for r in idx)
        only_idx = idx_names - disk_names
        only_disk = disk_names - idx_names
        if only_idx:
            fails.append("I5 index rows with NO file on disk: %d (e.g. %s)" % (len(only_idx), list(only_idx)[:3]))
        if only_disk:
            fails.append("I5 disk PDFs NOT in index: %d (e.g. %s)" % (len(only_disk), list(only_disk)[:3]))
        # I6 folder == article stem: for each non-root folder, the article file's stem must equal folder
        by_folder = defaultdict(list)
        for f, rel in disk:
            if rel and rel != ".":
                by_folder[rel].append(f)
        for folder, files in by_folder.items():
            arts = [f for f in files if not supp_marker(f)]
            if arts:
                stem = os.path.splitext(arts[0])[0]
                leaf = os.path.basename(folder)
                if leaf and stem and leaf != stem and stem not in leaf and leaf not in stem:
                    warns.append("I6 folder %r != article stem %r" % (leaf, stem))

    # ---- I12 pages integrity (FM4): every row's pages is blank or a non-negative integer ----
    badpages = [r.get(name_col, "") for r in idx
                if str(r.get("pages", "")).strip() and not str(r.get("pages", "")).strip().isdigit()]
    if badpages:
        fails.append("I12 pages not blank or a non-negative integer: %d (e.g. %s)" % (len(badpages), badpages[:3]))

    # ---- I14 record_type vocabulary: every record_type in the closed 11-type vocabulary ----
    badrt = sorted({r.get("record_type", "") for r in idx
                    if r.get("record_type", "") and r.get("record_type", "") not in RECORD_TYPE_VOCAB})
    if badrt:
        fails.append("I14 record_type outside closed vocabulary: %s" % badrt[:5])

    # ---- I13 truncation-flag completeness (FM4 vaccine) + I15 companion no-merge (FM3 vaccine) ----
    # Cluster MAIN rows by the shared blocking keys (same union-find dedup uses). I13: a pair of mains in
    # one cluster with a strictly-fuller twin (pages gap >= DPG_MIN) is a truncation candidate; it MUST
    # carry a recorded outcome (a dedup KEEP/drop decision OR a phantom/truncation FLAG). Without the
    # decisions file the validator cannot see outcomes, so it WARNs (surfaces the pair) rather than FAILs.
    # I15: no dup_article KEEP/drop decision may merge provably-distinct works (companion Part-N / distinct
    # DOIs with non-identical titles) — checked against the decisions file when supplied.
    def _is_main_row(r):
        return (r.get("record_type", "") not in NON_MAIN_TYPES) and not supp_marker(r.get(name_col, ""))
    mains_v = [r for r in idx if _is_main_row(r)]
    _uf = {}
    def _vfind(x):
        _uf.setdefault(x, x)
        while _uf[x] != x:
            _uf[x] = _uf[_uf[x]]; x = _uf[x]
        return x
    def _vunion(a, b):
        _uf[_vfind(a)] = _vfind(b)
    _key_owner = {}
    for i, r in enumerate(mains_v):
        rid = "V%d" % i
        _vfind(rid)
        for k in blocking_keys({"first_author": r.get("first_author", ""), "year": r.get("year", ""),
                                "title": r.get("title", ""), "doi": r.get("doi", "")}):
            if k in _key_owner:
                _vunion(rid, _key_owner[k])
            else:
                _key_owner[k] = rid
        r["_vrid"] = rid
    clusters_v = defaultdict(list)
    for r in mains_v:
        clusters_v[_vfind(r["_vrid"])].append(r)

    def _vpages(r):
        v = str(r.get("pages", "")).strip()
        return int(v) if v.isdigit() else None

    # recorded-outcome file-name set (decisions + sibling phantom/truncation review files), if available
    recorded = set()
    decision_clusters = defaultdict(list)      # cluster_id -> decision rows (for I15)
    dec_path = getattr(args, "decisions", None)
    if dec_path and os.path.exists(dec_path):
        with open(dec_path, encoding="utf-8") as f:
            for d in csv.DictReader(f):
                recorded.add(d.get("file_name", ""))
                decision_clusters[d.get("cluster_id", "")].append(d)
        _dbase = os.path.splitext(dec_path)[0]
        for sib in (_dbase + "_PHANTOMS_review.csv", _dbase + "_TRUNCATION_review.csv"):
            if os.path.exists(sib):
                with open(sib, encoding="utf-8") as f:
                    for d in csv.DictReader(f):
                        recorded.add(d.get("file_name", ""))

    trunc_pairs = []
    for cid, rs in clusters_v.items():
        if len(rs) < 2:
            continue
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                pi, pj = _vpages(rs[i]), _vpages(rs[j])
                if pi is None or pj is None:
                    continue
                if abs(pi - pj) >= DPG_MIN_DEFAULT:
                    trunc_pairs.append((rs[i], rs[j]))
    if trunc_pairs:
        if dec_path:
            unrec = [(a.get(name_col, ""), b.get(name_col, "")) for a, b in trunc_pairs
                     if a.get(name_col, "") not in recorded and b.get(name_col, "") not in recorded]
            if unrec:
                fails.append("I13 truncation pair with NO recorded decision/flag: %d (e.g. %s)"
                             % (len(unrec), unrec[:2]))
        else:
            warns.append("I13 truncation candidate pairs in master (no --decisions to verify review): %d (e.g. %s)"
                         % (len(trunc_pairs), [(a.get(name_col, ""), b.get(name_col, "")) for a, b in trunc_pairs][:2]))

    if decision_clusters:
        merged_distinct = []
        for cid, drows in decision_clusters.items():
            if not any(d.get("category", "") in ("dup_article", "near_dup_article") for d in drows):
                continue
            if _distinct_works(drows):
                merged_distinct.append(cid)
        if merged_distinct:
            fails.append("I15 distinct works merged inside a dup_article decision: %d (e.g. %s)"
                         % (len(merged_distinct), merged_distinct[:3]))

    # ---------- I16-I19 (ported from Claude Science sci-library-curate 2026-07-24) ----------
    # I16 unresolved supplement · I17 cryptic clean_name · I18 SI/parent DOI · I19 blank article title
    _main_names = {r.get(name_col, "") for r in idx if r.get("record_type", "") not in SUPP_DATASET_TYPES}
    # name -> row lookup, used by I16 branch-a and I18 (parent DOI compare).
    # RESTORED 2026-07-24: the I16-I19 port carried _main_names but DROPPED these two
    # lines, so _by_name was referenced at 4 sites and never bound — ANY index containing
    # a supplement with a resolving parent_file raised NameError and aborted the WHOLE
    # validator before any invariant reported, masking genuine FAILs (a real I19
    # blank-title article went unreported). Verified by tests/test_sci_library_curate_gates.py.
    # setdefault (FIRST row wins on a duplicated clean_name) is byte-for-byte the Science
    # sibling's semantics — a dict comprehension would take the LAST row instead and make
    # the two toolkits disagree on a duplicated index. Keep them identical.
    _by_name = {}
    for r in idx:
        _by_name.setdefault(r.get(name_col, ""), r)

    # ---- I16 no unresolved supplement (FAIL) ----
    # Every supplement/dataset row must (a) have a parent_file resolving to a MAIN row (record_type NOT
    # in {supplement,dataset} -- NOT another supplement), OR (b) carry the literal token
    # 'orphan_parent_absent'. WARN face: a linked SI whose bundle_folder != its parent's (loose/unbundled).
    i16_unresolved, i16_loose = [], []
    for r in idx:
        if r.get("record_type", "") not in SUPP_DATASET_TYPES:
            continue
        pf = str(r.get("parent_file", "") or "").strip()
        if pf and pf in _main_names:                       # (a) resolves to a MAIN row
            p = _by_name.get(pf)
            if p is not None:
                pbf = str(p.get("bundle_folder", "") or "").strip()
                sbf = str(r.get("bundle_folder", "") or "").strip()
                if pbf and sbf != pbf:
                    i16_loose.append(r.get(name_col, ""))
            continue
        if "orphan_parent_absent" in _note_blob(r):        # (b) explicit orphan flag
            continue
        i16_unresolved.append(r.get(name_col, ""))
    if i16_unresolved:
        fails.append("I16 supplement/dataset with no parent resolving to a MAIN row and no orphan flag: %d (e.g. %s)"
                     % (len(i16_unresolved), i16_unresolved[:3]))
    if i16_loose:
        warns.append("I16 linked SI not in its parent's bundle_folder (loose/unbundled): %d (e.g. %s)"
                     % (len(i16_loose), i16_loose[:3]))

    # ---- I17 no cryptic clean_name (FAIL) ----
    # No article/supplement clean_name may match the CRYPTIC pattern unless the row carries the literal
    # token 'cryptic_unresolved'. Author_Year_... names are never cryptic (see is_cryptic_name).
    # A LINKED supplement (parent_file resolves to a MAIN row) takes its identity from its parent,
    # so a cryptic SI filename is cosmetic — it is normalized at bundling and is NOT an identity
    # failure. I17 therefore fires on: articles (which MUST carry a real identity name), and
    # supplements that are NEITHER linked to a resolving MAIN parent NOR flagged orphan_parent_absent.
    _main_names_i17 = {r.get(name_col, "") for r in idx
                       if r.get("record_type", "") not in ("supplement", "dataset")}
    i17_bad = []
    for r in idx:
        rt = r.get("record_type", "")
        if rt not in {"article", "supplement"}:
            continue
        cn = r.get(name_col, "")
        if not is_cryptic_name(cn):
            continue
        blob = _note_blob(r)
        if "cryptic_unresolved" in blob:
            continue
        if rt == "supplement":
            pf = (r.get("parent_file", "") or "").strip()
            if pf in _main_names_i17 or "orphan_parent_absent" in blob:
                continue      # linked SI (identity from parent) or honestly-flagged orphan
        i17_bad.append(cn)
    if i17_bad:
        fails.append("I17 cryptic clean_name without cryptic_unresolved flag: %d (e.g. %s)"
                     % (len(i17_bad), i17_bad[:3]))

    # ---- I18 SI/parent DOI agreement (FAIL) ----
    # For a LINKED SI (parent_file resolves): the ROBUST check reads the document in --lib mode (mine the
    # SI PDF's own page-1..2 DOIs; drop data-repository DOIs which are legit-different; if any remaining
    # content DOI normalizes to the parent's -> agree, else a non-repo content DOI present -> FAIL -- this
    # is what catches the Seasonality_Biog mislink: SI content DOI 10.1038/s41558... vs parent stored
    # 10.5194/bg-22-1985). Non-PDF / no-minable-DOI SIs cannot fail what they cannot read -> skipped.
    # In index-only mode (no --lib, or an unreadable SI) fall back to the SI's STORED doi vs the parent's
    # stored doi (suffix-normalized) -- a lighter consistency check that still catches SIs which retained
    # a distinct stored DOI. A repo DOI on the SI side is never a disagreement in either mode.
    _pt_i18 = _probe_poppler_bin("pdftotext") if args.lib else None
    i18_lib, i18_idx = [], []
    for r in idx:
        if r.get("record_type", "") not in SUPP_DATASET_TYPES:
            continue
        pf = str(r.get("parent_file", "") or "").strip()
        if not pf or pf not in _by_name:
            continue                                       # orphan/unresolved -> I16's job, not I18
        pdoi = _norm_doi_cmp(_by_name[pf].get("doi", ""))
        if not pdoi:
            continue                                       # parent has no comparable DOI
        cn = r.get(name_col, "")
        did_lib = False
        if args.lib:
            path = _find_under_lib(args.lib, cn)
            mined = _mine_si_dois(path, _pt_i18) if path else None
            if mined is not None:
                did_lib = True
                mined_nonrepo = {_norm_doi_cmp(d) for d in mined if not _is_repo_doi(d)}
                mined_nonrepo.discard("")
                # If the PARENT row stores a data-repo DOI (Dryad/Zenodo landing page), the SI's own
                # masthead journal DOI is the real article DOI for the SAME work -> not a mislink.
                parent_is_repo = _is_repo_doi(_by_name[pf].get("doi", ""))
                if mined_nonrepo and pdoi not in mined_nonrepo and not parent_is_repo:
                    i18_lib.append(cn)                     # masthead self-DOI is a DIFFERENT paper -> mislink
        if not did_lib:                                    # index-only fallback (or --lib unreadable SI)
            if _is_repo_doi(r.get("doi", "")):
                continue                                   # SI legitimately carries its own repo DOI
            sdoi = _norm_doi_cmp(r.get("doi", ""))
            if sdoi and sdoi != pdoi:
                i18_idx.append(cn)
    if i18_lib:
        fails.append("I18 SI content-DOI disagrees with parent DOI [--lib]: %d (e.g. %s)"
                     % (len(i18_lib), i18_lib[:3]))
    if i18_idx:
        fails.append("I18 SI stored-DOI disagrees with parent stored-DOI: %d (e.g. %s)"
                     % (len(i18_idx), i18_idx[:3]))

    # ---- I19 article identity real (FAIL) ----
    # An article row must have a non-blank title (upgrade I4's article-missing-title component from WARN
    # to FAIL; author/year stay WARN under I4). A blank title means the row's identity is not real.
    def _i19_unk(v):
        return str(v or "").strip().lower() in ("", "unknown", "n/a", "na", "none", "null", "tbd")
    i19_bad = [r.get(name_col, "") for r in idx
               if r.get("record_type", "") == "article" and _i19_unk(r.get("title"))]
    if i19_bad:
        fails.append("I19 article row with blank title (identity not real): %d (e.g. %s)"
                     % (len(i19_bad), i19_bad[:3]))

    print("VALIDATE %s: %d rows | %d FAIL | %d warn"
          % (name_col, len(idx), len(fails), len(warns)))
    for m in fails: print("  FAIL", m)
    for m in warns: print("  warn", m)
    if args.report:
        def _wv(f):
            f.write("# Validate Report\n\nrows=%d  FAIL=%d  warn=%d\n\n" % (len(idx), len(fails), len(warns)))
            for m in fails: f.write("- FAIL %s\n" % m)
            for m in warns: f.write("- warn %s\n" % m)
        write_atomic(args.report, _wv)
    sys.exit(1 if fails else 0)

# ----------------------------- authors (co-author list) -----------------------------
# Gated CrossRef title-search fallback for rows with no author-list cache hit. Mirrors the
# discipline of sci-file-index's crossref_search + _pick_search_hit: a hit is accepted ONLY if its
# title matches the row's existing title (fuzzy ratio >= SEARCH_TITLE_SIM OR asymmetric containment
# >= 0.90), and — unless the title match is near-exact — the row's first_author surname must appear
# among the hit's author families. NEVER fabricates: no safe hit => authors left blank + noted.
SEARCH_TITLE_SIM = 0.85          # mirror sci-file-index FACT.crossref_search_gate
_CROSSREF_UA = "sci-library-curate/1.0"

def crossref_search(query, mailto=None, rows=3, timeout=12):
    """CrossRef bibliographic search -> list of work items (may raise on network error; callers
    catch). Sends the polite-pool mailto only when the caller supplies one."""
    url = "https://api.crossref.org/works?query.bibliographic=" + urllib.parse.quote(query) + "&rows=%d" % rows
    hdr = {"User-Agent": "%s (mailto:%s)" % (_CROSSREF_UA, mailto)} if mailto else {"User-Agent": _CROSSREF_UA}
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["message"].get("items", [])

def crossref_authors(item):
    """Ordered co-author list from a CrossRef work item, as formatted `Family, G.I.` strings, plus
    the TRUE count. CrossRef array order is authoritative. A corporate/consortium entry (has `name`,
    no `family`) renders as its name alone (format_author with given='')."""
    out = []
    for a in (item.get("author") or []):
        fam = (a.get("family") or "").strip()
        giv = (a.get("given") or "").strip()
        if not fam:
            fam = (a.get("name") or "").strip()      # corporate/consortium: whole name as family
            giv = ""
        if fam:
            out.append(format_author(fam, giv))
    return out, len(out)

def _title_match(row_title, hit_title):
    """(passes_gate, strong) for a candidate title vs the row's title. strong = near-exact / full
    containment (>=0.95 ratio or >=0.99 containment) — mirrors sci-file-index _pick_search_hit."""
    a = re.sub(r"[^a-z0-9]", "", (row_title or "").lower())
    b = re.sub(r"[^a-z0-9]", "", (hit_title or "").lower())
    if not a or not b:
        return False, False
    sim = title_sim(a, b)
    contain = 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) >= 12:                            # guard: a tiny fragment must not match anything
        blk = difflib.SequenceMatcher(None, shorter, longer).find_longest_match(0, len(shorter), 0, len(longer))
        contain = blk.size / len(shorter)
    passes = (sim >= SEARCH_TITLE_SIM) or (contain >= 0.90)
    strong = (sim >= 0.95) or (contain >= 0.99)
    return passes, strong

def _pick_author_hit(items, row_title, row_first_author=""):
    """Choose a CrossRef hit safe enough to lift authors from, else None. Title gate REQUIRED; for a
    non-strong title match the row's first_author surname must appear among the hit's author families
    (a title-only match to a different same-topic paper is rejected). Mirrors _pick_search_hit."""
    au_norm = re.sub(r"[^a-z]", "", _asciify(str(row_first_author or "")).lower())
    for it in items:
        cti = (it.get("title") or [""])[0]
        if not cti:
            continue
        passes, strong = _title_match(row_title, cti)
        if not passes:
            continue
        if au_norm and not strong:
            fams = _asciify(" ".join((a.get("family", "") or a.get("name", "")) for a in (it.get("author") or []))).lower()
            fams = re.sub(r"[^a-z ]", "", fams)
            if fams and au_norm not in fams.split() and au_norm not in fams.replace(" ", ""):
                continue                              # author mismatch on a non-exact title -> reject
        return it
    return None

def _load_author_cache(cache_path):
    """Read _AUTHOR_LIST_CACHE.csv -> {lowercased_doi: {ordered:[formatted names], n:int, source:str}}.
    ordered_authors is PIPE-delimited and already formatted (Track B applied format_author at
    populate-time). Missing/empty file -> {}. n_authors is trusted as the true count when present and
    consistent with the ordered list; otherwise len(ordered) wins (the names are authoritative)."""
    cache = {}
    if not cache_path or not os.path.exists(cache_path):
        return cache
    with open(cache_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            doi = real_doi(r.get("doi"))
            if not doi:
                continue
            ordered = [x.strip() for x in (r.get("ordered_authors") or "").split("|") if x.strip()]
            try:
                n = int(str(r.get("n_authors", "")).strip() or len(ordered))
            except ValueError:
                n = len(ordered)
            cache[doi] = {"ordered": ordered, "n": n, "source": (r.get("source") or "cache").strip()}
    return cache

def _stamp_note(row, note):
    """Append a note to dedup_note idempotently (never duplicate the same tag)."""
    cur = str(row.get("dedup_note", "") or "").strip()
    if note in cur:
        return
    row["dedup_note"] = (cur + "; " + note).strip("; ") if cur else note

def _authors_name2path(papers_dir):
    """Map basename -> disk path under papers_dir for the content-gate's byline reads. Skips
    stale_trash (mirrors cmd_probe). Returns {} when papers_dir is falsy or missing."""
    n2p = {}
    if papers_dir and os.path.isdir(papers_dir):
        for dp, _, fs in os.walk(papers_dir):
            if "stale_trash" in dp:
                continue
            for f in fs:
                n2p.setdefault(f, os.path.join(dp, f))
    return n2p


def _gate_doc_confirms_first_author(r, name2path, pdftotext):
    """Two-corroboration gate, DOCUMENT branch. Read the row's PDF byline and test whether the
    (content-verified) first_author appears in it. Returns one of:
      'confirmed'   - byline corroborates first_author -> safe to populate borrowed-DOI authors
      'contradicted'- byline present but first_author ABSENT -> the DOI is borrowed; reject + null it
      'needs_ocr'   - no text layer (scan) -> cannot confirm now; keep DOI, blank authors, distinct note
      'nofile'      - no papers_dir / file not on disk / non-PDF -> cannot confirm; keep DOI, blank+note
    """
    cn = str(r.get("clean_name", "") or "")
    path = name2path.get(cn)
    if not path:
        return "nofile"
    txt, needs_ocr = read_byline_text(path, pdftotext=pdftotext)
    if needs_ocr:
        return "needs_ocr"
    bc = byline_confirms(r.get("first_author", ""), txt)
    return "confirmed" if bc.get("confirmed") else "contradicted"


def populate_authors(rows, cache_path=None, crossref_mailto=None, sleep=0.3, verbose=False,
                     papers_dir=None):
    """Populate authors / n_authors / last_author on every author-bearing row (record_type in
    AUTHOR_RECORD_TYPES). Order of resolution per row:
      1. author-list cache keyed by lowercased DOI, behind a TWO-CORROBORATION CONTENT GATE;
      2. if no cache hit AND crossref_mailto-or-network available: a GATED CrossRef title-search
         (validated by _pick_author_hit), behind the SAME content gate;
      3. else: authors/last_author BLANK, n_authors=0, dedup_note += 'authors-unresolved'.
    NEVER touches first_author. Supplements/datasets (non-author record types) get BLANK author
    columns. Returns a stats dict. MUTATES rows in place.

    THE TWO-CORROBORATION CONTENT GATE (defect #59) - why a raw DOI cache hit is NOT trusted blind:
    a DOI in the master may be BORROWED (mis-assigned during an earlier merge). Writing the cache's
    author list on such a row silently adopts a DIFFERENT paper's authors - and worse, a plain re-run
    of this command would re-introduce that borrowed list every time. The document is the arbiter, so
    each hit must corroborate before it is written. But a HARD byline gate on EVERY hit is wrong: in
    the live author backfill, a hard 'byline must contain first_author' gate produced 1,760 rejections
    of which 1,733 were FALSE - the page1-4 byline scan simply missed the right region (end-of-paper
    author blocks, cover sheets, multi-column layouts). So we use TWO independent corroborations and
    require only ONE:
      (a) first_author itself is ALREADY a content-verified identity anchor. If the cache's leading
          author agrees with first_author (I10-tolerant match: casefold + strip-accents +
          dash-normalize; equality OR containment OR whitespace-token overlap; corporate author => agree),
          the DOI's author list is corroborated by that agreement - populate on the FAST PATH, NO PDF
          read. This is what rescued the 1,733: fa_agree needs no byline.
      (b) only when the leading author DISAGREES do we fall back to the DOCUMENT: read the byline and
          require it to confirm first_author. Confirmed -> populate. Contradicted (byline present,
          first_author absent) -> the DOI is borrowed: blank authors and NULL the borrowed DOI so a
          re-run cannot re-adopt it. Couldn't-check (scan needs_ocr / no papers_dir / file missing) ->
          blank + a DISTINCT note, DOI RETAINED (we have not disproven it, only failed to confirm).
    papers_dir=None keeps the fast path fully working; disagreements then degrade to blank+note
    (conservative) because there is no document to consult."""
    cache = _load_author_cache(cache_path)
    name2path = _authors_name2path(papers_dir)
    pdftotext = _probe_poppler_bin("pdftotext")
    stats = {"from_cache": 0, "from_cache_byline": 0, "from_crossref": 0, "unresolved": 0,
             "skipped_non_author": 0, "crossref_errors": 0,
             "gate_contradicted_nulled": 0, "gate_needs_ocr": 0, "gate_nofile": 0}

    def _write_authors(r, ordered):
        abbr, n, last = abbreviate_authors(ordered)
        r["authors"] = abbr; r["n_authors"] = str(n); r["last_author"] = last

    def _blank_authors(r, note, null_doi=False):
        row_title = str(r.get("title", "") or "").strip()
        r["authors"] = ""; r["n_authors"] = "0" if (row_title or r.get("first_author")) else ""
        r["last_author"] = ""
        if null_doi:
            r["doi"] = ""                                 # drop the borrowed DOI so a re-run can't re-adopt it
        _stamp_note(r, note)

    def _gate(r, ordered, byline_tag):
        """Apply the two-corroboration gate to an ordered author list, WRITE or BLANK the row, and
        return a category: 'agree' (fast-path populate, no PDF), 'byline' (document-confirmed
        populate), 'contradicted' (borrowed DOI nulled), 'needs_ocr', or 'nofile'. `byline_tag` is the
        provenance note stamped on a document-confirmed populate (differs cache vs crossref)."""
        a0fam = ordered[0] if ordered else ""
        if _i10_author_match(a0fam, r.get("first_author", "")):
            # (a) leading author agrees with the content-verified first_author -> corroborated. FAST
            #     PATH: no PDF read. (first_author is itself an identity anchor.)
            _write_authors(r, ordered)
            return "agree"
        # (b) disagreement -> require the DOCUMENT to confirm first_author.
        verdict = _gate_doc_confirms_first_author(r, name2path, pdftotext)
        if verdict == "confirmed":
            _write_authors(r, ordered)
            _stamp_note(r, byline_tag)
            return "byline"
        if verdict == "contradicted":
            _blank_authors(r, "authors-unresolved-borrowed-doi", null_doi=True)
            return "contradicted"
        if verdict == "needs_ocr":
            _blank_authors(r, "authors-needs-ocr", null_doi=False)
            return "needs_ocr"
        _blank_authors(r, "authors-unconfirmed-nofile", null_doi=False)   # nofile
        return "nofile"

    _CAT2STAT = {"contradicted": "gate_contradicted_nulled", "needs_ocr": "gate_needs_ocr",
                 "nofile": "gate_nofile"}

    for r in rows:
        rt = str(r.get("record_type", "") or "").strip().lower()
        if rt not in AUTHOR_RECORD_TYPES:
            # supplements/datasets/etc.: ensure the columns exist and are blank; inherit nothing
            r["authors"] = ""; r["n_authors"] = ""; r["last_author"] = ""
            stats["skipped_non_author"] += 1
            continue
        # 1. cache by DOI, behind the two-corroboration content gate
        doi = real_doi(r.get("doi"))
        hit = cache.get(doi) if doi else None
        if hit and hit["ordered"]:
            cat = _gate(r, hit["ordered"], "authors:byline-confirmed")
            if cat == "agree":
                stats["from_cache"] += 1
            elif cat == "byline":
                stats["from_cache_byline"] += 1
            else:
                stats[_CAT2STAT[cat]] += 1
            continue
        # 2. gated CrossRef title-search fallback (only when we can validate against a real title),
        #    then the SAME content gate before writing the borrowed-DOI-free result.
        row_title = str(r.get("title", "") or "").strip()
        resolved = False
        if crossref_mailto is not None and len(re.sub(r"[^a-z0-9]", "", row_title.lower())) >= 12:
            try:
                q = (row_title + " " + str(r.get("first_author", "") or "")).strip()
                items = crossref_search(q, mailto=crossref_mailto or None)
                if sleep:
                    time.sleep(sleep)
                chosen = _pick_author_hit(items, row_title, r.get("first_author", ""))
                if chosen is not None:
                    ordered, n = crossref_authors(chosen)
                    if ordered:
                        cat = _gate(r, ordered, "authors:crossref-byline-confirmed")
                        if cat in ("agree", "byline"):
                            stats["from_crossref"] += 1
                            _stamp_note(r, "authors:crossref-search")   # provenance for the written row
                            resolved = True
                        else:
                            # crossref-derived list failed the content gate -> treat like an unresolved
                            # borrowed hit (row already blanked+noted+doi-handled by _gate); do NOT
                            # fall through to the generic 'authors-unresolved' branch.
                            stats[_CAT2STAT[cat]] += 1
                            resolved = True
            except Exception as e:
                stats["crossref_errors"] += 1
                if verbose:
                    print("  crossref-search error on %r: %s" % (r.get("clean_name", ""), e))
        if not resolved:
            # 3. never fabricate: blank + note, RETAIN first_author
            r["authors"] = ""; r["n_authors"] = "0" if row_title or r.get("first_author") else ""
            r["last_author"] = ""
            _stamp_note(r, "authors-unresolved")
            stats["unresolved"] += 1
    return stats

def cmd_authors(args):
    """AUTHORS — populate authors / n_authors / last_author on the master from an author-list cache
    (DOI-keyed), with a gated CrossRef title-search fallback. Writes the master back with the three
    columns APPENDED (schema-preserving). --dry-run computes + reports stats, mutates nothing.
    --mailto enables the polite-pool CrossRef fallback (omit it to run cache-only)."""
    rows = _read_index(args.index)
    if not rows:
        print("AUTHORS: empty index, nothing to do"); return
    mailto = args.mailto if getattr(args, "crossref", False) else None
    papers_dir = getattr(args, "papers", None)
    stats = populate_authors(rows, cache_path=args.cache, crossref_mailto=mailto, verbose=True,
                             papers_dir=papers_dir)
    if not args.dry_run:
        _write_master(args.index, rows, ensure_authors=True)
    tag = " (DRY RUN)" if args.dry_run else ""
    print("AUTHORS%s: %d rows | from_cache(fa_agree)=%d | from_cache(byline)=%d | from_crossref=%d | unresolved=%d | non-author(blank)=%d | crossref_errors=%d"
          % (tag, len(rows), stats["from_cache"], stats["from_cache_byline"], stats["from_crossref"],
             stats["unresolved"], stats["skipped_non_author"], stats["crossref_errors"]))
    print("  content-gate: borrowed-doi contradicted+nulled=%d | needs-ocr(blank,doi kept)=%d | no-file(blank,doi kept)=%d%s"
          % (stats["gate_contradicted_nulled"], stats["gate_needs_ocr"], stats["gate_nofile"],
             "" if papers_dir else "  [no --papers: disagreements degrade to blank+note]"))
    if not args.dry_run:
        print("  WROTE %s (authors, n_authors, last_author appended)" % args.index)

# ============================ IDENTITY-ERROR PROBE (probe) ============================
# A proactive, re-runnable detector for likely MISIDENTIFICATIONS in the master index.
# TWO stages, BOTH zero-LLM-token:
#   STAGE 1 (pure code over rows): a battery of cheap cross-field checks, each emitting a
#     reason code and contributing to an additive error_likelihood in [0,1]. Deliberately
#     HIGH-RECALL — common surnames that are also English words (Field, Hall, Green, Sun, Long,
#     Rice, Wood, Bird) WILL be flagged. That is expected; Stage 2 clears them.
#   STAGE 2 (poppler only): THE ARBITER. Extract the PDF's own byline region and test whether the
#     first_author surname actually appears in it. THE DOCUMENT IS TRUTH — this stage never calls
#     CrossRef and never trusts a DOI. A surname present in the byline CORROBORATES the master
#     (likely false positive, cleared); absent-with-text-present is a likely real error (escalate);
#     no text layer -> needs_ocr (undetermined, hand off to the adjudication phase; the probe never
#     OCRs — that is expensive and belongs downstream).
#
# The probe is READ-ONLY: it emits _IDENTITY_AUDIT.csv + a terse summary and NEVER edits the master
# and NEVER proposes a fix from a DOI. It surfaces candidates + a document-based signal so a human/
# orchestrator adjudicates the small residual.

# --- Stage-1 vocab / weights (documented, tunable) ---------------------------------------------
PROBE_STOPWORDS = {
    "introduction", "monitoring", "effects", "seasonality", "sun", "abstract", "supplementary",
    "supporting", "data", "table", "figure", "appendix", "results", "methods", "discussion",
    "review", "article", "chapter", "materials", "observations", "impact", "overview", "using",
}
PROBE_CORP_CAPS = {"csiro", "nasa", "noaa", "ipcc", "usda", "who", "epa", "iucn"}

# ================================================================================================
# REUSE of sci-file-index's PROVEN four-field content miners (defect #58).
# Identity is FOUR fields - {first_author, title, publication/journal, year} - and each must be
# confirmable from the DOCUMENT. The probe's Stage-1 title/journal predicates and its Stage-2
# four-field arbiter therefore extract and judge title/journal/year/author from a document EXACTLY
# as the indexer does. Those miners are hardened across ~20 defects (multi-page front-matter scan,
# JSTOR/ILL cover sheets, body-text mining, OCR title/author/journal). We IMPORT the sibling module
# and CALL its functions - never a private re-implementation that would silently drift from it.
#
# Mechanism chosen: robust path-based import of sci_file_index.py (option b), NOT hoisting the miners
# into sci_lib_common.py (option a). Rationale: the miners depend on a deep web of ~30 module-level
# regexes/constants and internal cross-calls (mine_bibliography -> parse_cover_sheet -> _ILL_*;
# _ocr_title -> _title_line_ok / _AFFIL_KW / _SECTION_BANNER; is_junk_title -> DOI_RE; ...). Hoisting
# safely would mean relocating dozens of symbols AND re-verifying the indexer byte-for-behaviour
# across all ~20 of those defects in ONE change - too much blast radius here. The sibling module
# imports cleanly with zero import-time side effects (a guarded __main__ only), so a path-based
# import reuses the proven code at minimal risk.
# TODO(defect #58 follow-up): once a dedicated indexer regression harness exists, hoist the pure-text
# miners (mine_bibliography, parse_cover_sheet, clean_title, is_junk_title, conf_title_known,
# conf_year_known, _looks_like_journal_line, _ocr_*) into sci_lib_common.py so BOTH skills import ONE
# source of truth, update the indexer to import them from the module (no behaviour change), re-verify
# the indexer, and delete this shim.
_INDEXER_MOD = None
_INDEXER_LOAD_ERR = ""


def _indexer_candidate_paths():
    """Where sci_file_index.py may live relative to this script. Primary: the sibling skill's
    scripts dir in the shared org skills tree (../../sci-file-index/scripts/). Fallback: co-located
    (a flattened layout, and the synthetic-test workspace)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return [
        os.path.normpath(os.path.join(here, "..", "..", "sci-file-index", "scripts", "sci_file_index.py")),
        os.path.normpath(os.path.join(here, "sci_file_index.py")),
    ]


def _load_indexer():
    """Import sci-file-index ONCE (cached) for its proven content miners; return the module or None.
    Isolated import (own spec, NOT registered in sys.modules under the bare name) so a differently
    versioned sci_file_index elsewhere on sys.path can never shadow it. NEVER raises - on failure the
    probe degrades conservatively (Stage-1 title/journal predicates go silent; Stage-2 code-mined
    fields return 'uncertain'), never fabricating a verdict."""
    global _INDEXER_MOD, _INDEXER_LOAD_ERR
    if _INDEXER_MOD is not None or _INDEXER_LOAD_ERR:
        return _INDEXER_MOD
    import importlib.util
    for p in _indexer_candidate_paths():
        if not os.path.isfile(p):
            continue
        try:
            spec = importlib.util.spec_from_file_location("sci_file_index_probe", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _INDEXER_MOD = mod
            return mod
        except Exception as e:                     # pragma: no cover - defensive
            _INDEXER_LOAD_ERR = "%s: %s" % (type(e).__name__, e)
    if not _INDEXER_LOAD_ERR:
        _INDEXER_LOAD_ERR = ("sci_file_index.py not found next to the curator "
                             "(looked in ../../sci-file-index/scripts and .)")
    return None


def _mnr_is_junk_title(t):
    """indexer is_junk_title (reused): powerpoint/excel/template/running-head/PII/filename-as-title.
    Conservative fallback when the module is absent: only blank is 'junk' (never over-flags a real
    title we cannot judge)."""
    m = _load_indexer()
    if m is not None:
        try:
            return bool(m.is_junk_title(t))
        except Exception:
            pass
    return not str(t or "").strip()


def _mnr_looks_like_journal_line(s):
    """indexer _looks_like_journal_line (reused): does this string read like a journal masthead /
    citation line rather than a title? Conservative fallback when the module is absent: False (never
    flags the journal-as-title / journal-looks-like-title classes we cannot judge)."""
    m = _load_indexer()
    if m is not None:
        try:
            return bool(m._looks_like_journal_line(s))
        except Exception:
            pass
    return False


def mine_document_fields(text):
    """STAGE-2 field extraction, delegated ENTIRELY to the indexer's proven miners (defect #58):
      title / author-family / year / doi  <- mine_bibliography (which itself tries parse_cover_sheet
                                             for JSTOR/ILL covers, then body-text _ocr_title/_ocr_author)
      journal                             <- parse_cover_sheet labeled journal (covers), else the
                                             _ocr_journal masthead miner ('Journal 88(3)')
    Returns {available, title, author, year, journal, doi}. available=False iff the indexer module
    could not be imported - Stage 2 then marks the code-mined fields 'uncertain', never guessing."""
    m = _load_indexer()
    if m is None:
        return {"available": False, "title": "", "author": "", "year": "", "journal": "", "doi": ""}
    ti = au = yr = doi = jr = ""
    try:
        ti, au, yr, doi = m.mine_bibliography(text)
    except Exception:
        ti = au = yr = doi = ""
    try:
        cov = m.parse_cover_sheet(text)
        if cov and cov.get("journal"):
            jr = cov.get("journal", "")
    except Exception:
        cov = None
    if not jr:
        try:
            jr = m._ocr_journal(text)
        except Exception:
            jr = ""
    return {"available": True, "title": ti or "", "author": au or "", "year": yr or "",
            "journal": jr or "", "doi": doi or ""}


import time as _time_shim
_PROBE_CURRENT_YEAR = _time_shim.localtime().tm_year    # upper year bound = this year + 1
# A title field that carries a filename/DTP fragment or a PII-like numeric string is not a real
# title (an extension token, an underscore-joined stem, an Elsevier 'S0168...' PII, a '0002-1571'
# fragment). Distinct from is_junk_title (which flags a title that IS a filename): this catches a
# fragment embedded in an otherwise longer string.
_TITLE_FRAGMENT_RE = re.compile(
    r"\.(?:pdf|docx?|tex|indd|qxd|qxp|eps|ps|rtf|fm|html?|xml)\b"   # a file-extension token
    r"|[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+"                       # an underscore-run (filename stem)
    r"|\bS\d{6,}\b"                                                  # Elsevier PII 'S0168192391...'
    r"|\b\d{4,}-\d{3,}\b",                                           # a PII-like numeric fragment
    re.I)

# Additive weights per reason code. error_likelihood = min(1.0, sum of fired weights). Higher =
# more likely a real error. A single strong signal (>=0.4) is escalation-worthy on its own; two
# weak signals (0.30 each) compound. Pure RT_SI_MARKER lands at exactly 0.30 so --min-score 0.35
# filters the (large, benign-heavy) record_type/name-contradiction class out of an identity hunt.
PROBE_WEIGHTS = {
    "FA_HAS_DIGIT":        0.50,   # a surname never contains a digit
    "FA_STOPWORD":         0.45,   # first_author is a title/section word (Introduction, Monitoring)
    "FA_IN_TITLE":         0.40,   # first_author appears inside its own title
    "FA_IN_JOURNAL":       0.35,   # first_author inside its own journal, or a journal-vocab token
    "FA_NO_VOWEL":         0.35,   # vowel-free non-acronym (mojibake / fragment)
    "FA_LOWERCASE":        0.35,   # all-lowercase multi-char (fragment, not a surname)
    "FA_SINGLE_INITIAL":   0.35,   # a lone initial captured as the author
    "YEAR_DRIFT_DUP":      0.35,   # same author+title-prefix as a sibling with different year/doi
    "FA_TITLE_EQ_JOURNAL": 0.30,   # title field equals journal field (swap/mis-mine)
    "RT_SI_MARKER":        0.30,   # author-type row whose NAME says supplement (type contradiction)
    # --- identity fields BEYOND author (defect #58): title / journal / year each REQUIRED and each
    # confirmable from the document. A missing required identity field is a strong signal; a
    # cross-field contradiction (title==journal, journal reads like a sentence) is medium. Weights
    # stay in the existing 0.30-0.50 additive band so escalation math is unchanged for author codes.
    "TITLE_MISSING":          0.45,   # blank/whitespace title on an author-type row
    "TITLE_IS_JOURNAL":       0.45,   # title equals / is contained by the journal (the 'Silber' class)
    "TITLE_IS_JUNK":          0.45,   # indexer is_junk_title: powerpoint/template/running-head/filename
    "TITLE_TOO_SHORT":        0.35,   # < 3 real word-tokens and not a known short title
    "TITLE_HAS_FILENAME_FRAGMENT": 0.35,  # extension token / underscore-run / PII fragment in title
    "JOURNAL_MISSING":        0.40,   # blank publication/journal on an article-type row
    "JOURNAL_LOOKS_LIKE_TITLE": 0.35,   # journal field is long/sentence-like, not a masthead
    "YEAR_MISSING":           0.40,   # blank year on an article-type row
    "YEAR_OUT_OF_RANGE":      0.45,   # not in 1500..currentyear+1
    "YEAR_FILENAME_DISAGREES": 0.35,   # a 4-digit year in the filename differs from the year col by >1
}
PROBE_MIN_JVOCAB_FREQ = 3          # a journal token counts as vocabulary only if >= this many rows use it
PROBE_MIN_JVOCAB_LEN  = 5          # ... and is at least this long (guards short words)

_SI_END  = re.compile(r"(_suppl\d*|_esm\d*)(?:\.[A-Za-z0-9]+)?$", re.I)   # curator supplement-stem convention
_SI_HARD = re.compile(r"(moesm|\bmmc\d|peer-?review)", re.I)              # unambiguous publisher SI tokens
# Surname particles (leading-name HINT must skip these): mirror sci_lib_common _PARTICLES.
PROBE_PARTICLES = {"van", "von", "der", "den", "de", "del", "della", "di", "da", "dos", "das",
                   "du", "la", "le", "el", "al", "bin", "ibn", "ter", "ten"}

# --- byline region window (Stage 2 pure-logic constants) ---------------------------------------
# The byline sits in a document's FRONT MATTER: title, author list, affiliations — ABOVE the
# Abstract/Introduction. Scoping the search to that region is load-bearing: it CONFIRMS a real
# surname printed in the byline (clearing a common-word false positive like 'Field'/'Sun'), while
# NOT confirming a section word like 'Introduction' off the "1. Introduction" body header (that word
# is the region BOUNDARY, not inside it) — so a genuinely-wrong author is correctly escalated.
BYLINE_MAX_LINES = 12              # hard cap: at most N non-empty lines when no boundary marker is found
BYLINE_MAX_CHARS = 1200            # hard cap: at most N chars when no boundary marker is found
BYLINE_SCAN_CHARS_MIN = 120        # 4-page text shorter than this => no text layer => needs_ocr
# End-of-front-matter markers: the byline region is everything BEFORE the first of these. A leading
# section number ('1.') is tolerated before 'introduction'. Case-insensitive, whole-word.
_BYLINE_BOUNDARY = re.compile(
    r"(?im)^\s*(?:\d+\.?\s*)?(abstract|a\s*b\s*s\s*t\s*r\s*a\s*c\s*t|r[eé]sum[eé]|summary|"
    r"introduction|keywords?|key\s+words|received\b|\u00a9|\(c\)\s*\d|copyright)\b")
_BYLINE_STOPWORDS = {              # tokens that lead front matter but are never a surname
    "the", "by", "and", "for", "department", "departments", "university", "school", "college",
    "institute", "institut", "faculty", "laboratory", "laboratoire", "centre", "center", "division",
    "received", "accepted", "published", "abstract", "article", "research", "review", "original",
    "correspondence", "corresponding", "author", "authors", "email", "e", "doi", "http", "https",
    "vol", "volume", "no", "pp", "page", "journal", "proceedings", "letters", "letter",
}


def _pfold(s):
    """Accent-insensitive fold to lowercase alnum-with-single-spaces (probe matching key)."""
    a = _asciify(str(s or "")).lower()
    return re.sub(r"[^a-z0-9]+", " ", a).strip()


def _probe_journal_vocab(rows):
    """Build the journal-vocabulary token set: tokens (len >= PROBE_MIN_JVOCAB_LEN) that appear in
    >= PROBE_MIN_JVOCAB_FREQ DISTINCT journal strings. A first_author token that is such a token is
    very likely a mis-mined journal word, not a surname."""
    from collections import Counter
    jc = Counter()
    seen_per_token = {}
    journals = set()
    for r in rows:
        j = _pfold(r.get("journal", ""))
        if j:
            journals.add(j)
    for j in journals:
        for t in set(j.split()):
            if len(t) >= PROBE_MIN_JVOCAB_LEN:
                jc[t] += 1
    return {t for t, c in jc.items() if c >= PROBE_MIN_JVOCAB_FREQ}


def probe_row_checks(row, jvocab, drift_siblings):
    """STAGE 1 (pure, zero-token). Return (reason_codes:list[str], error_likelihood:float, note:str)
    for a single author-bearing master row. drift_siblings is a dict (fa12, ti25) -> list of sibling
    clean_names with a different year/doi (precomputed once); jvocab is the journal-vocab token set.
    NEVER consults a DOI as an arbiter — real_doi here only distinguishes two rows in the drift key."""
    codes = []
    fa_raw = str(row.get("first_author", "") or "")
    fa = _pfold(fa_raw)
    fa_tokens = [t for t in fa.split() if t]
    title = _pfold(row.get("title", ""))
    journal = _pfold(row.get("journal", ""))
    notes = []

    if any(ch.isdigit() for ch in fa_raw):
        codes.append("FA_HAS_DIGIT")
    if fa and (fa in PROBE_STOPWORDS or any(t in PROBE_STOPWORDS for t in fa_tokens)):
        codes.append("FA_STOPWORD")
    if len(fa) >= 4 and title and fa in title:
        codes.append("FA_IN_TITLE")
    in_j = (len(fa) >= 4 and journal and fa in journal)
    jv_hit = any(t in jvocab for t in fa_tokens if len(t) >= PROBE_MIN_JVOCAB_LEN)
    if in_j or jv_hit:
        codes.append("FA_IN_JOURNAL")
    if len(fa) >= 3 and not re.search(r"[aeiou]", fa) and fa.replace(" ", "") not in PROBE_CORP_CAPS:
        codes.append("FA_NO_VOWEL")
    if fa_raw.strip() and fa_raw.strip().islower() and len(fa_raw.strip()) > 3:
        codes.append("FA_LOWERCASE")
    if re.fullmatch(r"[A-Za-z]\.?", fa_raw.strip()):
        codes.append("FA_SINGLE_INITIAL")
    if title and title == journal:
        codes.append("FA_TITLE_EQ_JOURNAL")
    # RT_SI_MARKER: author-type row whose NAME says supplement (record_type vs name contradiction)
    if row.get("record_type") in {"article", "book", "book_chapter"}:
        cn = str(row.get("clean_name", ""))
        blob = cn + " " + str(row.get("original_disk_name", "")) + " " + str(row.get("parent_file", ""))
        if _SI_END.search(cn) or _SI_HARD.search(blob):
            codes.append("RT_SI_MARKER")
    # YEAR_DRIFT_DUP: precomputed cluster membership
    key = (fa[:12], title[:25])
    sibs = drift_siblings.get(key)
    if sibs:
        others = [s for s in sibs if s != row.get("clean_name", "")]
        codes.append("YEAR_DRIFT_DUP")
        if others:
            notes.append("year/doi-drift sibling(s): " + "; ".join(others[:3]))

    # ---------------------------------------------------------------------------------------------
    # IDENTITY FIELDS BEYOND AUTHOR (defect #58): title / journal / year. Author alone is not a test
    # of anything - each of the four identity fields is REQUIRED and must be confirmable. These are
    # Stage-1 zero-token code predicates; Stage-2 then confirms/contradicts each against the document.
    rt = str(row.get("record_type", "") or "")
    title_raw = str(row.get("title", "") or "")
    journal_raw = str(row.get("journal", "") or "")
    year_raw = str(row.get("year", "") or "")
    _year_req = rt in AUTHOR_RECORD_TYPES                 # every byline-bearing work has a year
    _journal_req = rt in {"article", "conference"}        # only serial-venue types reliably have one
                                                          # (book/chapter/thesis/report/preprint excluded)

    # --- TITLE ---
    title_is_junk = False
    if not title_raw.strip():
        if rt in AUTHOR_RECORD_TYPES:
            codes.append("TITLE_MISSING")
    else:
        title_is_junk = _mnr_is_junk_title(title_raw)     # reuse indexer: ppt/excel/template/pii/filename
        if title_is_junk:
            codes.append("TITLE_IS_JUNK")
        else:
            # < 3 real word-tokens (and not caught as junk) => too short to be a real title
            _tw = re.findall(r"[A-Za-z][A-Za-z'\-]+", title_raw)
            if len(_tw) < 3:
                codes.append("TITLE_TOO_SHORT")
            if _TITLE_FRAGMENT_RE.search(title_raw):
                codes.append("TITLE_HAS_FILENAME_FRAGMENT")
        # TITLE_IS_JOURNAL ('Silber' class: the journal name stored as the title). Exact title==journal
        # is already FA_TITLE_EQ_JOURNAL; here we catch containment-not-equal and title-reads-as-journal.
        if title and title != journal:
            contained = bool(journal) and (title in journal or journal in title)
            if contained or _mnr_looks_like_journal_line(title_raw):
                codes.append("TITLE_IS_JOURNAL")

    # --- JOURNAL ---
    if not journal_raw.strip():
        if _journal_req:
            codes.append("JOURNAL_MISSING")
    else:
        # inverse of _looks_like_journal_line: a long, sentence-like value in the journal field is a
        # mis-mined title, not a masthead. Require >= 6 word-tokens so short real journal names pass.
        _jw = re.findall(r"[A-Za-z][A-Za-z'\-]+", journal_raw)
        if len(_jw) >= 6 and not _mnr_looks_like_journal_line(journal_raw):
            codes.append("JOURNAL_LOOKS_LIKE_TITLE")

    # --- YEAR ---
    if not year_raw.strip():
        if _year_req:
            codes.append("YEAR_MISSING")
    else:
        _ym = re.search(r"\d{4}", year_raw)
        if _ym:
            _yv = int(_ym.group(0))
            if not (1500 <= _yv <= _PROBE_CURRENT_YEAR + 1):
                codes.append("YEAR_OUT_OF_RANGE")
            else:
                # YEAR_FILENAME_DISAGREES: a plausible 4-digit year in the filename that differs from
                # the (in-range) year column by > 1. Only fires when the filename HAS a plausible year
                # and NONE of its plausible years is within 1 of the column value.
                _fnblob = str(row.get("clean_name", "")) + " " + str(row.get("original_disk_name", ""))
                _fy = [int(y) for y in re.findall(r"(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)", _fnblob)
                       if 1500 <= int(y) <= _PROBE_CURRENT_YEAR + 1]
                if _fy and all(abs(_yv - fy) > 1 for fy in _fy):
                    codes.append("YEAR_FILENAME_DISAGREES")
                    notes.append("filename year(s) %s vs year col %d" % (sorted(set(_fy)), _yv))

    score = min(1.0, round(sum(PROBE_WEIGHTS.get(c, 0.0) for c in codes), 3))
    return codes, score, " | ".join(notes)


def build_drift_siblings(rows):
    """Precompute the YEAR_DRIFT_DUP clusters: map (fa[:12], title[:25]) -> [clean_name,...] for every
    key shared by >=2 author-bearing rows that DISAGREE on year or (real) doi. One entry per member."""
    from collections import defaultdict
    buckets = defaultdict(list)
    for r in rows:
        fa = _pfold(r.get("first_author", ""))[:12]
        ti = _pfold(r.get("title", ""))[:25]
        if fa and len(ti) >= 10:
            buckets[(fa, ti)].append(r)
    out = {}
    for k, members in buckets.items():
        if len(members) < 2:
            continue
        years = {str(m.get("year", "")).strip() for m in members}
        dois = {real_doi(m.get("doi")) for m in members if real_doi(m.get("doi"))}
        if len(years) > 1 or len(dois) > 1:
            out[k] = [m.get("clean_name", "") for m in members]
    return out


def byline_confirms(first_author, byline_text):
    """STAGE 2 pure logic (zero-token). Does the master's first_author surname actually appear in
    the document's printed byline region? Returns {'confirmed':bool, 'leading_name':str|None}.

    'confirmed' — the first_author surname (accent-folded, family-name-reduced) appears as a WHOLE
    TOKEN within the byline region: the first BYLINE_MAX_LINES non-empty lines OR first
    BYLINE_MAX_CHARS chars of byline_text, whichever is larger. Word-boundary (not substring) so a
    3-letter surname ('Sun') matches 'Jing M. Sun' but NOT 'sunlight'; scoped to FRONT MATTER (not
    the body) so a common-word surname ('Field') is confirmed by the author block, never by 'field
    capacity' downstream. Compound/particle surnames reduce via family_name ('van Breugel'->Breugel,
    'Aguiar-Campos'->Aguiar-Campos); diacritics fold ('Navar' matches 'Nvar').
    'leading_name' — best-effort HINT (NOT a verified value): the surname-looking token that leads
    the byline when the master's author is NOT confirmed. May be None."""
    st = str(first_author or "").strip()
    if not st or not byline_text:
        return {"confirmed": False, "leading_name": None}

    # byline region = everything BEFORE the first end-of-front-matter marker (Abstract/Introduction/
    # Keywords/Received/copyright), then hard-capped at BYLINE_MAX_LINES non-empty lines /
    # BYLINE_MAX_CHARS chars. This deliberately EXCLUDES the "1. Introduction" body header so a
    # section word captured as an author ('Introduction') is NOT confirmed off the body.
    m = _BYLINE_BOUNDARY.search(byline_text)
    head = byline_text[:m.start()] if m else byline_text
    nonempty = [ln for ln in head.splitlines() if ln.strip()]
    region = " ".join(nonempty[:BYLINE_MAX_LINES])[:BYLINE_MAX_CHARS]
    region_tokens = set(_pfold(region).split())

    # surname tokens: family_name-reduced first, raw first_author as fallback
    fam = _pfold(_family_name(first_author))
    surtok = [t for t in fam.split() if len(t) >= 2]
    if not surtok:
        surtok = [t for t in _pfold(first_author).split() if len(t) >= 2]
    sig = [t for t in surtok if len(t) >= 3]
    if sig:
        confirmed = all(t in region_tokens for t in sig)
    else:
        confirmed = bool(surtok) and any(t in region_tokens for t in surtok)

    leading = None
    if not confirmed:
        # HINT ONLY (never a verified value): the surname that LEADS the byline. Isolate the first
        # author chunk (before the first comma / semicolon / ' and ' / '&' / digit), then take its
        # LAST capitalized non-stopword token — the surname slot in 'Given I. Surname'. An affiliation
        # ('Dept of Ecology') sits after the author separator, so it does not leak into the hint.
        first_chunk = re.split(r"[,;&\d]|\band\b", region.strip(), maxsplit=1)[0]
        toks = re.findall(r"[A-Za-z\u00C0-\u017F][A-Za-z\u00C0-\u017F'\-]+", first_chunk)
        cap = [t for t in toks if t[:1].isupper() and _pfold(t) not in _BYLINE_STOPWORDS
               and _pfold(t) not in PROBE_PARTICLES]
        if cap:
            leading = cap[-1]
    return {"confirmed": confirmed, "leading_name": leading}


# ================================================================================================
# STAGE 2 four-field arbiter (defect #58). byline_confirms (above) judges the AUTHOR field; the
# helpers below judge TITLE / JOURNAL / YEAR by comparing the master's stored value to the value the
# indexer's proven miners extract from the DOCUMENT. Each field gets one of three verdicts:
#   confirmed    - the document agrees with the master
#   contradicted - the document shows a DIFFERENT value (escalate)
#   uncertain    - the field could not be extracted / text is a scan / the match is ambiguous
# THE DOCUMENT IS TRUTH; a DOI is never consulted here. Zero LLM tokens (poppler/OCR + code only).
def _pcmp(s):
    """Fold to lowercase alnum-with-single-spaces for field comparison (accent-insensitive)."""
    return re.sub(r"[^a-z0-9]+", " ", _asciify(str(s or "")).lower()).strip()


_PROBE_TITLE_SIM_CONFIRM = 0.80    # difflib ratio at/above which mined vs stored title = confirmed
_PROBE_TITLE_SIM_CONTRA  = 0.45    # ... and below which (no containment) = contradicted


def _verdict_title(master_title, doc_title):
    mt, dt = norm_title(master_title), norm_title(doc_title)
    if not dt or len(dt) < 8 or not mt:
        return "uncertain"                              # no usable document title to compare against
    if mt == dt or mt in dt or dt in mt:
        return "confirmed"
    if title_sim(mt, dt) >= _PROBE_TITLE_SIM_CONFIRM:
        return "confirmed"
    if len(dt) >= 20 and (dt[:20] in mt or mt[:20] in dt):
        return "confirmed"                              # mined title truncated but prefix-aligned
    if title_sim(mt, dt) < _PROBE_TITLE_SIM_CONTRA:
        return "contradicted"
    return "uncertain"


def _verdict_year(master_year, doc_year):
    my = re.search(r"\d{4}", str(master_year or ""))
    dy = re.search(r"\d{4}", str(doc_year or ""))
    if not dy or not my:
        return "uncertain"
    # +/-1 tolerance: online-first vs issue year legitimately differ by a year; > 1 is a real drift.
    return "confirmed" if abs(int(my.group()) - int(dy.group())) <= 1 else "contradicted"


def _verdict_journal(master_journal, doc_journal):
    mj, dj = _pcmp(master_journal), _pcmp(doc_journal)
    if not dj or not mj:
        return "uncertain"
    if mj == dj or mj in dj or dj in mj:
        return "confirmed"
    aj, adj = _pcmp(journal_abbrev(master_journal)), _pcmp(journal_abbrev(doc_journal))
    if aj and adj and (aj == adj or aj in adj or adj in aj):
        return "confirmed"                              # canonical-abbrev match ('P Natl Acad Sci')
    tm, td = set(mj.split()), set(dj.split())
    if tm and td:
        jac = len(tm & td) / float(len(tm | td))
        if jac >= 0.6:
            return "confirmed"
        if jac == 0.0 and len(tm) >= 2 and len(td) >= 2:
            return "contradicted"                       # both substantial, ZERO shared token
    # journal is the least reliably mined field (mastheads are terse / abbreviated) -> bias to uncertain
    return "uncertain"


def probe_confirm_identity(row, text, needs_ocr=False):
    """STAGE 2 four-field arbiter (pure; zero-token). Given the document TEXT (poppler or OCR), mine
    the four identity fields with the indexer's proven miners and return a PER-FIELD verdict vs the
    master row. Returns author_verdict / title_verdict / journal_verdict / year_verdict plus the
    document-extracted values (doc_leading_name / doc_title / doc_journal / doc_year) for one-look
    adjudication. THE DOCUMENT IS TRUTH; no DOI is consulted."""
    usable = bool(text) and len(text.strip()) >= BYLINE_SCAN_CHARS_MIN and not needs_ocr
    if usable:
        doc = mine_document_fields(text)
    else:
        doc = {"available": False, "title": "", "author": "", "year": "", "journal": "", "doi": ""}

    # --- AUTHOR: byline_confirms (front-matter scoped) is the primary arbiter, KEPT as-is (the task
    #     mandates it for the author field). A byline that the region scan CONFIRMS -> confirmed.
    #     A byline that does NOT confirm needs care: distinguish a genuine CONTRADICTION (the document
    #     affirmatively shows a DIFFERENT leading surname) from mere UNCERTAINTY (the scan simply
    #     missed the name). This is the 1,733-false-rejection lesson from the author backfill: a byline
    #     miss is NOT proof of a wrong author. So we call 'contradicted' ONLY when an alternative
    #     leading surname is evident - the indexer-mined first author, or byline's leading-name hint -
    #     AND it disagrees with first_author under the I10 tolerance; otherwise 'uncertain'.
    byline_confirmed = False
    if not usable:
        av, leading = "uncertain", ""
    else:
        bc = byline_confirms(row.get("first_author", ""), text)
        byline_confirmed = bool(bc.get("confirmed"))
        leading = bc.get("leading_name") or ""
        alt = (doc.get("author") or "").strip() or leading.strip()   # an alternative leading surname
        # GUARD (mirrors the FA_IN_TITLE failure mode + the 1,733-false-rejection lesson): a candidate
        # 'alt' surname that is itself a TOKEN OF THE MINED TITLE is a title fragment captured as an
        # author (e.g. 'Boundary' from 'Boundary layer effects...'), NOT a real competing byline. Such
        # an alt must not turn a byline MISS into a false contradiction - drop it, verdict = uncertain.
        _title_toks = set(_pcmp(doc.get("title", "")).split())
        if alt and _pcmp(alt) in _title_toks:
            alt = ""
        if byline_confirmed:
            av = "confirmed"
        elif alt and _i10_author_match(alt, row.get("first_author", "")):
            av = "confirmed"                            # region scan missed it, but the alt name agrees
        elif alt:
            av = "contradicted"                         # document shows a DIFFERENT leading author
        else:
            av = "uncertain"                            # front matter present but no author extractable

    tv = _verdict_title(row.get("title", ""), doc.get("title", "")) if usable else "uncertain"
    jv = _verdict_journal(row.get("journal", ""), doc.get("journal", "")) if usable else "uncertain"
    yv = _verdict_year(row.get("year", ""), doc.get("year", "")) if usable else "uncertain"
    return {
        "author_verdict": av, "title_verdict": tv, "journal_verdict": jv, "year_verdict": yv,
        "byline_confirmed": byline_confirmed,
        "doc_leading_name": (doc.get("author") or leading or ""),
        "doc_title": doc.get("title", ""), "doc_journal": doc.get("journal", ""),
        "doc_year": doc.get("year", ""),
    }


# --- Stage-2 I/O wrapper (poppler; the ONLY place the probe touches a PDF) ---------------------
def _probe_poppler_bin(name):
    """Locate a poppler CLI tool (pdftotext). PATH first, then the same dirs sci-file-index probes."""
    import shutil as _sh
    p = _sh.which(name)
    if p:
        return p
    for d in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/opt/local/bin"):
        cand = os.path.join(d, name)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def read_byline_text(path, pdftotext=None, pages=4, timeout=60):
    """STAGE-2 I/O: return (byline_text, needs_ocr). Reads the FIRST `pages` pages in -layout mode
    (bylines are NOT always on p1 — cover sheets, Science special sections, and CB primers push the
    author block deeper; end-of-article author blocks also exist). byline_confirms() then scopes to
    the front-matter region. needs_ocr=True when the extracted text is shorter than
    BYLINE_SCAN_CHARS_MIN — a scan with no text layer; the probe FLAGS it and does NOT OCR (OCR is
    expensive and belongs to the downstream adjudication phase). Reuses the poppler primitive that
    sci-file-index's cmd_extract/cmd_ocr already depend on rather than rebuilding extraction."""
    exe = pdftotext or _probe_poppler_bin("pdftotext")
    if not exe or not path or not os.path.exists(path) or not path.lower().endswith(".pdf"):
        return "", True
    import subprocess
    try:
        r = subprocess.run([exe, "-f", "1", "-l", str(pages), "-layout", path, "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
        txt = r.stdout or ""
    except Exception:
        return "", True
    if len(txt.strip()) < BYLINE_SCAN_CHARS_MIN:
        return txt, True
    return txt, False


PROBE_OCR_DPI = 300                # mirror sci-file-index cmd_ocr render resolution
PROBE_OCR_PAGE_CAP = 6             # mirror sci-file-index PAGE_SCAN_CAP


def read_document_text_ocr(path, pages=PROBE_OCR_PAGE_CAP, dpi=PROBE_OCR_DPI, timeout=300,
                           workdir=None):
    """STAGE-2 OCR fallback for a SCAN (needs_ocr). Renders the first `pages` pages at `dpi` with
    pdftoppm and OCRs each with tesseract --psm 1, EXACTLY as sci-file-index cmd_ocr does, and returns
    the concatenated text (or "" if the toolchain is unavailable). Called ONLY when read_byline_text
    reported needs_ocr AND the caller opted in (--ocr) - OCR is expensive (~5-30s/page), so the fast
    poppler path above handles every text-layer PDF without ever rendering. Zero LLM tokens.

    Rendered pages are written under `workdir` (default: a scratch dir beside the CWD, mirroring
    sci-file-index cmd_ocr, which renders into <index>/_ocr - a real writable location, NEVER the
    system /tmp; some environments/OCR toolchains cannot read intermediates from /tmp)."""
    pdftoppm = _probe_poppler_bin("pdftoppm")
    import shutil as _sh
    tesseract = _sh.which("tesseract") or _probe_poppler_bin("tesseract")
    if not pdftoppm or not tesseract or not path or not os.path.exists(path):
        return ""
    import subprocess, tempfile
    out = []
    parent = workdir if (workdir and os.path.isdir(workdir)) else os.getcwd()
    wd = tempfile.mkdtemp(dir=parent, prefix="._probe_ocr_")
    try:
        base = os.path.join(wd, "pg")
        for pg in range(1, pages + 1):
            try:
                subprocess.run([pdftoppm, "-r", str(dpi), "-png", "-f", str(pg), "-l", str(pg), path, base],
                               capture_output=True, timeout=120)
            except Exception:
                break
            png = None
            for suff in ("-%d" % pg, "-%02d" % pg, "-0%d" % pg):
                cand = base + suff + ".png"
                if os.path.exists(cand):
                    png = cand; break
            if not png:
                break                                   # no more pages rendered
            try:
                r = subprocess.run([tesseract, png, "stdout", "--psm", "1", "-l", "eng"],
                                   capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=timeout)
                out.append(r.stdout or "")
            except Exception:
                pass
            finally:
                try:
                    os.remove(png)
                except OSError:
                    pass
    finally:
        import shutil as _sh2
        try:
            _sh2.rmtree(wd, ignore_errors=True)
        except Exception:
            pass
    return "\n".join(out)


# --- the subcommand -----------------------------------------------------------------------------
PROBE_OUT_COLS = [
    "clean_name", "record_type", "first_author", "year", "title", "journal", "doi",
    "reason_codes", "error_likelihood",
    "byline_confirms_first_author", "needs_ocr", "leading_name_hint", "needs_human", "notes",
    # four-field arbiter (defect #58): per-field verdict + the document-extracted value beside it, so
    # adjudication is one-look. verdict in {confirmed, contradicted, uncertain, ""(=not checked)}.
    "author_verdict", "title_verdict", "journal_verdict", "year_verdict",
    "doc_leading_name", "doc_title", "doc_journal", "doc_year",
]


def cmd_probe(args):
    """PROBE — proactive, re-runnable IDENTITY-ERROR detector. READ-ONLY: emits a ranked
    _IDENTITY_AUDIT.csv and NEVER edits the master, NEVER trusts a DOI, NEVER OCRs.

    STAGE 1 (zero-token, pure code over rows): the reason-code battery (PROBE_WEIGHTS) scores every
    author-bearing row; deliberately high-recall.
    STAGE 2 (zero-token, poppler only): for each candidate, read the PDF's own byline and test the
    master's first_author against it. THE DOCUMENT IS TRUTH.

    Verdict per candidate:
      byline confirms first_author  -> LIKELY FALSE POSITIVE (document agrees; cleared)
      NOT confirmed AND text present -> LIKELY REAL ERROR (escalate; leading_name is a HINT only)
      no text layer                  -> UNDETERMINED (needs_ocr; hand to adjudication)
    """
    rows = _read_index(args.index)
    if not rows:
        print("PROBE: empty index, nothing to do"); return
    arows = [r for r in rows if str(r.get("record_type", "") or "").strip().lower() in AUTHOR_RECORD_TYPES]
    jvocab = _probe_journal_vocab(arows)
    drift = build_drift_siblings(arows)

    # STAGE 1
    candidates = []
    reason_counter = Counter()
    for r in arows:
        codes, score, note = probe_row_checks(r, jvocab, drift)
        if codes:
            for c in codes:
                reason_counter[c] += 1
            candidates.append((r, codes, score, note))

    # resolve disk paths for byline reads (only if --papers given): name -> path (skip stale_trash)
    name2path = {}
    if args.papers and os.path.isdir(args.papers):
        for dp, _, fs in os.walk(args.papers):
            if "stale_trash" in dp:
                continue
            for f in fs:
                name2path.setdefault(f, os.path.join(dp, f))

    pdftotext = _probe_poppler_bin("pdftotext")
    want_ocr = bool(getattr(args, "ocr", False))
    _EMPTY_V = {"author_verdict": "", "title_verdict": "", "journal_verdict": "", "year_verdict": "",
                "doc_leading_name": "", "doc_title": "", "doc_journal": "", "doc_year": ""}
    # STAGE 2 (only over Stage-1 candidates; each row read at most once). FOUR-FIELD arbiter: the
    # document is truth for first_author AND title AND journal AND year (defect #58).
    out_rows = []
    cleared = escalated = need_ocr = 0
    for r, codes, score, note in candidates:
        cn = r.get("clean_name", "")
        confirms = ""      # '' = not checked (no --papers, or file not on disk, or non-PDF)
        needs_ocr = False
        leading = ""
        verdicts = dict(_EMPTY_V)
        notes = [note] if note else []
        path = name2path.get(cn)
        if args.papers:
            if not path:
                notes.append("file not found under --papers")
            else:
                txt, is_scan = read_byline_text(path, pdftotext=pdftotext)
                if is_scan and want_ocr:
                    # opt-in OCR fallback for a scan (expensive; mirrors sci-file-index cmd_ocr render)
                    otxt = read_document_text_ocr(path)
                    if otxt and len(otxt.strip()) >= BYLINE_SCAN_CHARS_MIN:
                        txt, is_scan = otxt, False
                        notes.append("scan OCR'd for confirmation (--ocr)")
                if is_scan:
                    needs_ocr = True
                    need_ocr += 1
                    notes.append("no text layer (scan) -> needs OCR in adjudication")
                    # all four verdicts remain 'uncertain' (arbiter returns uncertain when needs_ocr)
                    v = probe_confirm_identity(r, txt, needs_ocr=True)
                    verdicts.update(v)
                else:
                    v = probe_confirm_identity(r, txt, needs_ocr=False)
                    verdicts.update(v)
                    # byline_confirms_first_author column = the RAW byline result (faithful to the
                    # shipped column's meaning); clearance/escalation below use the four-field verdict.
                    confirms = bool(v.get("byline_confirmed"))
                    leading = v.get("doc_leading_name", "") or ""
                    author_ok = (v["author_verdict"] == "confirmed")
                    row_contra = any(v[k] == "contradicted" for k in
                                     ("author_verdict", "title_verdict", "journal_verdict", "year_verdict"))
                    if author_ok and not row_contra:
                        cleared += 1
                    else:
                        escalated += 1
        # ESCALATE (needs_human) unless the row is CLEARED. A row is cleared ONLY when the document
        # CONFIRMS the author AND no identity field is contradicted (title/journal/year may be
        # 'uncertain' - those miners are less reliable than the front-matter byline, and the author is
        # itself a content anchor). Escalate on: ANY field contradicted; author not confirmed with
        # text present; a code-flagged row that could not be document-checked (needs_ocr / no --papers).
        # NOTE (1,733-false-rejection lesson): we do NOT escalate on a raw byline miss alone - the
        # author_verdict already treats a byline miss with no contradicting evidence as 'uncertain',
        # and an uncertain author on a code-flagged row is escalated for a human, not auto-condemned.
        any_contra = any(verdicts[k] == "contradicted"
                         for k in ("author_verdict", "title_verdict", "journal_verdict", "year_verdict"))
        author_ok = (verdicts["author_verdict"] == "confirmed")
        if not args.papers:
            needs_human = True
        else:
            needs_human = bool(needs_ocr or any_contra or not author_ok)
        out_rows.append({
            "clean_name": cn, "record_type": r.get("record_type", ""),
            "first_author": r.get("first_author", ""), "year": r.get("year", ""),
            "title": r.get("title", ""), "journal": r.get("journal", ""), "doi": r.get("doi", ""),
            "reason_codes": ";".join(codes), "error_likelihood": "%.3f" % score,
            "byline_confirms_first_author": "" if confirms == "" else str(confirms),
            "needs_ocr": str(needs_ocr), "leading_name_hint": leading,
            "needs_human": str(needs_human), "notes": " | ".join(n for n in notes if n),
            "author_verdict": verdicts["author_verdict"], "title_verdict": verdicts["title_verdict"],
            "journal_verdict": verdicts["journal_verdict"], "year_verdict": verdicts["year_verdict"],
            "doc_leading_name": verdicts["doc_leading_name"], "doc_title": verdicts["doc_title"],
            "doc_journal": verdicts["doc_journal"], "doc_year": verdicts["doc_year"],
        })

    # rank: any-field CONTRADICTION first, then author-not-confirmed, then undetermined scan, then
    # not-checked, then cleared; error_likelihood breaks ties within a tier (desc).
    def _rank(o):
        conf = o["byline_confirms_first_author"]
        any_contra = any(o[k] == "contradicted"
                         for k in ("author_verdict", "title_verdict", "journal_verdict", "year_verdict"))
        if any_contra:
            tier = 0
        elif conf == "False":
            tier = 1
        elif o["needs_ocr"] == "True":
            tier = 2
        elif conf == "":
            tier = 3
        else:
            tier = 4
        return (-float(o["error_likelihood"]), tier, o["clean_name"])
    out_rows.sort(key=_rank)

    if args.min_score:
        out_rows = [o for o in out_rows if float(o["error_likelihood"]) >= args.min_score]

    def _w(f):
        w = csv.DictWriter(f, fieldnames=PROBE_OUT_COLS, extrasaction="ignore")
        w.writeheader(); w.writerows(out_rows)
    write_atomic(args.out, _w)

    if not args.quiet:
        print("PROBE: %d author-bearing rows | %d Stage-1 candidates | wrote %s"
              % (len(arows), len(candidates), args.out))
        print("  candidates_by_reason: " + ", ".join("%s=%d" % (c, n)
              for c, n in sorted(reason_counter.items(), key=lambda x: -x[1])))
        if args.papers:
            print("  Stage-2 (document is truth): cleared_false_positive=%d | escalated_real_error=%d | needs_ocr=%d"
                  % (cleared, escalated, need_ocr))
        else:
            print("  Stage-2 SKIPPED (no --papers): byline_confirms/needs_ocr blank; all rows need_human=True")
        top = [o for o in out_rows if o["byline_confirms_first_author"] == "False"][:5]
        if top:
            print("  top escalations (document disagrees with master):")
            for o in top:
                print("    %s  fa=%r  hint=%r  [%s]  score=%s"
                      % (o["clean_name"][:44], o["first_author"], o["leading_name_hint"],
                         o["reason_codes"], o["error_likelihood"]))

# ----------------------------- CLI -----------------------------
def main():
    ap = argparse.ArgumentParser(description="Dedup, migrate-copy, and topic-organize a sci-file-index library.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dedup"); d.add_argument("--index", required=True); d.add_argument("--hashes", default=None)
    d.add_argument("--out", default="_dedup_decisions.csv"); d.add_argument("--report", default="DEDUP_REPORT.md")
    # FM4/FM5 tunables. Truncation defaults to FLAG (review file); --aggressive-truncation opts in to
    # auto-DROP the shorter copy when a strictly-fuller same-work twin exists.
    d.add_argument("--aggressive-truncation", dest="aggressive_truncation", action="store_true",
                   help="auto-DROP the shorter copy when a fuller same-work twin exists (default: FLAG for review)")
    d.add_argument("--dpg-min", dest="dpg_min", type=int, default=3,
                   help="minimum page gap for a fuller twin to count as a truncation candidate (default 3)")
    d.add_argument("--sim-k", dest="sim_k", type=int, default=3,
                   help="content_sim SimHash Hamming threshold for near-duplicate detection (default 3)")
    d.set_defaults(func=cmd_dedup)
    m = sub.add_parser("migrate"); m.add_argument("--index", required=True); m.add_argument("--decisions", required=True)
    m.add_argument("--src", required=True); m.add_argument("--dst", required=True); m.add_argument("--dry-run", action="store_true")
    m.add_argument("--no-bundle", action="store_true",
                   help="export every file flat; default bundles each article WITH supplements into its own folder")
    m.set_defaults(func=cmd_migrate)
    o = sub.add_parser("organize"); o.add_argument("--index", required=True); o.add_argument("--manifest", required=True)
    o.add_argument("--dst", required=True); o.add_argument("--taxonomy", default=None)
    o.add_argument("--llm-assignments", default=None); o.add_argument("--dry-run", action="store_true")
    o.add_argument("--force", action="store_true", help="place files even if an unclassified tail remains")
    o.set_defaults(func=cmd_organize)
    c = sub.add_parser("catalog", help="regenerate the one-row-per-WORK clean lookup table from the master index")
    c.add_argument("--index", required=True)
    c.add_argument("--out", default="_index_clean_lookup_table.csv")
    c.add_argument("--lib", default=None, help="library root; enables the disk 1:1 reconciliation (exit 1 on mismatch)")
    c.set_defaults(func=cmd_catalog)
    v = sub.add_parser("validate", help="fail-loud structural invariants over the index (+ disk with --lib)")
    v.add_argument("--index", required=True)
    v.add_argument("--lib", default=None, help="library root; enables the disk<->index 1:1 and folder==stem checks")
    v.add_argument("--decisions", default=None,
                   help="dedup decisions CSV; enables I13 (truncation-flag completeness) and I15 (companion no-merge) to verify recorded outcomes")
    v.add_argument("--report", default=None, help="write a VALIDATE_REPORT.md")
    v.set_defaults(func=cmd_validate)
    b = sub.add_parser("bundle", help="idempotently fold each article + its supplement(s) into a per-article folder, in place")
    b.add_argument("--index", required=True, help="the master index CSV (bundle_folder column is updated in place)")
    b.add_argument("--papers", required=True, help="the flat clean-library papers root (files are MOVED into per-article folders)")
    b.add_argument("--dry-run", action="store_true", help="print/write the full plan and mutate nothing")
    b.add_argument("--report", default=None, help="write a machine-readable plan CSV (action,clean_name,from_folder,to_folder)")
    b.set_defaults(func=cmd_bundle)
    au = sub.add_parser("authors", help="populate authors/n_authors/last_author on the master from a DOI-keyed author-list cache (+ gated CrossRef fallback)")
    au.add_argument("--index", required=True, help="the master index CSV (the three author columns are appended in place)")
    au.add_argument("--cache", default=None, help="_AUTHOR_LIST_CACHE.csv (doi, ordered_authors pipe-delimited, n_authors, source)")
    au.add_argument("--crossref", action="store_true", help="enable the GATED CrossRef title-search fallback for rows with no cache hit")
    au.add_argument("--mailto", default="", help="contact email for the CrossRef polite pool (used only with --crossref)")
    au.add_argument("--papers", default=None, help="library papers root: enables the content-gate's DOCUMENT confirmation when a cache/crossref leading author disagrees with first_author (omit to run fast-path-only; disagreements then degrade to blank+note)")
    au.add_argument("--dry-run", action="store_true", help="compute + report stats, mutate nothing")
    au.set_defaults(func=cmd_authors)
    pr = sub.add_parser("probe", help="proactive identity-error probe: flag likely misidentifications by code, confirm each against the PDF byline (read-only report)")
    pr.add_argument("--index", required=True, help="the master index CSV (READ-ONLY; never modified)")
    pr.add_argument("--papers", default=None, help="library papers root for Stage-2 byline reads; omit to run Stage-1 only")
    pr.add_argument("--out", default="_IDENTITY_AUDIT.csv", help="ranked audit CSV (default _IDENTITY_AUDIT.csv)")
    pr.add_argument("--min-score", type=float, default=0.0, dest="min_score", help="drop candidates below this error_likelihood")
    pr.add_argument("--ocr", action="store_true", help="Stage-2: OCR a scan (pdftoppm+tesseract, ~5-30s/page) to confirm identity; default flags scans needs_ocr without OCRing")
    pr.add_argument("--quiet", action="store_true", help="suppress the summary print")
    pr.set_defaults(func=cmd_probe)
    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
