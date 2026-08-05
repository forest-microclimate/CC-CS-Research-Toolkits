# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""sci_lib_common.py — canonical shared identity module for the sci-file-index /
sci-library-curate curation pipeline. ONE definition of each identity primitive,
the single source of truth imported (Claude Science) or inlined (Claude Code) by
both tools. Edit THIS file + rebuild; never hand-edit a shipped copy.

Exposes: asciify, family_name, norm_title, real_doi, journal_abbrev, canonical_stem,
blocking_keys, write_atomic (+ helpers _tokens, _camel, _alnum_component).
"""
__version__ = "3"
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
_NAME_SEG = r"(?:[A-Z][a-z'.]*|[A-Z]{2,})"
_NAME_TOK = re.compile(r"^" + _NAME_SEG + r"(?:['-]" + _NAME_SEG + r")*$")

def family_name(author):
    """FIRST author's family name. Handles 'Surname, F.' / 'F. Surname' / 'A and B' / 'et al.'
    DIACRITIC- and COMPOUND-safe: dehyphen (unify dash glyphs) + asciify BEFORE the name-token
    class test (the sci-file-index bug tested the raw accented token against [A-Z][a-z]+, which
    excludes accents -> empty -> author dropped; the compound bug rejected 'Aguirre-Gutierrez'
    because of the internal capital / U+2010 hyphen). Returns the folded ASCII surname."""
    s = str(author or "").strip()
    if not s:
        return ""
    s = re.sub("[" + _DASHES + "]", "-", s)                    # unify all dash glyphs to ASCII '-'
    s = re.sub(r"\bet al\.?\b", "", s, flags=re.I).strip(" .,")
    sep = re.search(r"\s+(and|&)\s+|;", s)
    comma = s.find(",")
    if comma != -1 and (sep is None or comma < sep.start()):
        cand = (_tokens(s.split(",")[0]) or [""])[-1]          # "Bird, R. E." -> Bird
    else:
        first = re.split(r"\s+(?:and|&)\s+|;", s)[0]            # first author of "A and B"
        # asciify each token BEFORE the class test, so accents/compounds don't disqualify it
        multi = [t for t in _tokens(first) if _NAME_TOK.match(asciify(t))]
        cand = multi[-1] if multi else ""
    cand = asciify(cand)                                        # fold accents to base letter: Büker->Buker
    cand = re.sub(r"[^A-Za-z'-]", "", cand)                     # then strip non-letters (keep hyphen/apostrophe)
    return cand[:1].upper() + cand[1:].lower() if cand else ""

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
    au = _camel(family_name(raw_author))
    if raw_author and not au:                                   # #41 author-restore fallback chain
        au = _camel(family_name(str(row.get("first_author_ascii", "")).strip())) \
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
