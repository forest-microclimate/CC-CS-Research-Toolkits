# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""sci_lib_common.py — canonical shared identity module for the sci-file-index /
sci-library-curate curation pipeline. ONE definition of each identity primitive,
the single source of truth imported (Claude Science) or inlined (Claude Code) by
both tools. Edit THIS file + rebuild; never hand-edit a shipped copy.

Exposes: asciify, family_name, surname_sep, name_features, format_author, abbreviate_authors,
norm_title, real_doi, journal_abbrev, canonical_stem, blocking_keys, write_atomic (+ helpers
_tokens, _camel, _alnum_component, _surname_string, _render_surname).
"""
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
