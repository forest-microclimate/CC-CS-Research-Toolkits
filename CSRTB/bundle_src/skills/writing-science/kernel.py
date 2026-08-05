# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""
writing-science / kernel.py — mechanical draft detectors for the Science-Writing Stylist.

These functions are the *interposition-gate analogue* for prose: instead of the agent
trying to remember every craft principle, it runs the draft through these detectors and
the tells surface structurally. Every detector is a CANDIDATE-FLAGGER — it surfaces
suspects a script can reliably find; final disposition ("is this flagged thing actually
a violation, here, for this reader?") is the agent's judgment. NOTHING here auto-edits.

Grounding: each detector cites the Schimel _Writing Science_ principle/table it implements
(page numbers are book running-head pages). Lexicons are seed lists from Schimel's own
tables (14.1, 15.1, 15.2, 16.1) and are meant to be extended.

Design law (ported from the Claude-Code-improvement project): a rule fires only if it is
(a) loaded at the decision moment and (b) phrased as an output-detectable TELL, not an
exhortation. Each function name is the tell; the returned `note`/`procedure` is what to do.

Pure standard library (re only) so the skill loads in any kernel. POS-dependent checks
(noun trains, exact finite-verb location) are implemented as documented heuristics and
flagged `approximate=True`.
"""
import re
from collections import Counter

# ----------------------------------------------------------------------------- utilities

ABBREV = {"e.g", "i.e", "et al", "cf", "vs", "fig", "eq", "ref", "no", "al",
           "dr", "mr", "ms", "st", "sp", "ca", "approx", "min", "max"}

def split_sentences(text):
    """Lightweight sentence splitter tolerant of common scientific abbreviations and
    decimals. Returns a list of sentence strings."""
    # protect decimals and abbreviations from the splitter (DOT = one-dot leader U+2024)
    DOT = '\u2024'
    protected = re.sub(r'(\d)\.(\d)', lambda m: m.group(1) + DOT + m.group(2), text)
    for ab in ABBREV:
        protected = re.sub(rf'(?i)\b{re.escape(ab)}\.', ab + DOT, protected)
    out, start = [], 0
    for m in re.finditer(r'[.!?]["\')\]]?\s+(?=[A-Z0-9"\'(\[])', protected):
        out.append(protected[start:m.end()])
        start = m.end()
    if start < len(protected):
        out.append(protected[start:])
    return [s.replace('\u2024', '.').strip() for s in out if s.strip()]

def words_of(sentence):
    return re.findall(r"[A-Za-z][A-Za-z\-']*", sentence)

def clip_text(s, n=140):
    s = re.sub(r'\s+', ' ', s).strip()
    return s if len(s) <= n else s[:n] + '…'

def paragraphs(text):
    return [p for p in re.split(r'\n\s*\n', text) if p.strip()]

def strip_noncontent(text):
    """Remove markdown/code scaffolding that is not prose before analysis: fenced code and
    ```mermaid``` diagram blocks, inline code spans, ATX heading markers, table pipes, and
    image/link URL machinery. Keeps link text. The Stylist judges STRUCTURE separately;
    these detectors should see only the prose stream."""
    text = re.sub(r'```.*?```', ' ', text, flags=re.S)        # fenced code / mermaid
    text = re.sub(r'`[^`]+`', ' ', text)                       # inline code
    text = re.sub(r'^\s{0,3}#{1,6}\s*', '', text, flags=re.M)  # heading markers
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', text)          # images
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)       # links -> text
    text = re.sub(r'^\s*\|.*\|\s*$', ' ', text, flags=re.M)    # table rows
    text = re.sub(r'^[|\-:\s]+$', ' ', text, flags=re.M)       # table rules
    return text

# ------------------------------------------------------------------- WORD-LEVEL detectors

# Schimel Table 14.1 "weak/fuzzy verbs" (p.139) + documented extensions
WEAK_VERBS = {
    "occur", "occurs", "occurred", "affect", "affects", "affected", "facilitate",
    "facilitates", "facilitated", "conduct", "conducted", "implement", "implemented",
    "perform", "performed", "performs", "involve", "involves", "involved", "undergo",
    "undergoes", "underwent", "experience", "experiences", "experienced", "exhibit",
    "exhibits", "exhibited", "mediate", "mediates", "mediated", "achieve", "achieved",
    "obtain", "obtained", "utilize", "utilized", "carry out", "carried out",
    "impact", "impacts", "impacted",
}

# Schimel Table 16.1 empty amplifiers (p.165) + documented extensions
EMPTY_AMPLIFIERS = {
    "certain", "certainly", "dramatic", "dramatically", "entire", "entirely", "high",
    "highly", "quite", "rather", "real", "really", "simple", "simply", "substantial",
    "substantially", "very", "significantly", "extremely", "considerably", "greatly",
    "vast", "vastly", "clearly", "obviously", "notably", "markedly", "remarkably", "sharply",
}

# Schimel credibility / hype (ch.3, credible) — seed hype-word list
HYPE_WORDS = {
    "novel", "unprecedented", "groundbreaking", "cutting-edge", "revolutionary",
    "paradigm-shifting", "paradigm-shift", "breakthrough", "transformative",
    "game-changing", "innovative", "exciting", "unique", "remarkable", "striking",
}   # NB: bare "paradigm" excluded — "paradigm case"/"paradigmatic" is a term of art

# fuzzy/light verbs that pair with a nominalization ("make an assessment")
LIGHT_VERBS = {"make", "makes", "made", "perform", "performs", "performed", "conduct",
               "conducts", "conducted", "carry", "carries", "carried", "provide",
               "provides", "provided", "give", "gives", "gave", "do", "does", "did",
               "undertake", "undertakes", "undertook", "achieve", "achieves", "achieved"}

# pattern SOURCES are module-level literal strings (sidecar-gate safe); compiled lazily
NOMINAL_SUFFIX_SRC = r'\b\w{3,}(tion|sion|ment|ance|ence|ancy|ency|ity|ness|ism|ure)\b'
PASSIVE_SRC = (r'\b(am|is|are|was|were|be|been|being|has been|have been|had been)\b\s+'
               r'(\w+ed|shown|known|seen|done|made|found|given|taken|held|built|drawn|'
               r'grown|born|written|driven|chosen|proven|kept|left|felt|meant|sent|set)\b')

def find_passive(text, methods_ok=False):
    """TELL: a form of 'to be' + past participle. Schimel ch.14 (pp.133-139): passive is
    one of the three verb-drainers. PROCEDURE: recast as Subject(actor)-Verb-Object unless
    the passive is deliberately choosing the topic. Agentless passives (no 'by ...') in
    Methods are the top candidates for first-person active."""
    hits = []
    for i, s in enumerate(split_sentences(text)):
        for m in re.compile(PASSIVE_SRC, re.I).finditer(s):
            agentless = not re.search(r'\bby\s+[a-z]', s[m.end():m.end()+40], re.I)
            hits.append({"sentence_idx": i, "match": m.group(0),
                         "agentless": agentless, "sentence": clip_text(s),
                         "note": "agentless passive - strong candidate for active" if agentless
                                 else "passive - justify by topic-continuity or recast"})
    return hits

def find_nominalizations(text):
    """TELL (high-precision tier): a light/fuzzy verb followed by a nominalization
    ('perform an analysis', 'make a comparison') — Schimel ch.14 (pp.140-143), the single
    highest-value revision because the buried verb is right there. PROCEDURE: promote the
    buried verb ('analyze', 'compare'). Bare nominalizations everywhere else are counted by
    nominalization_density() rather than flagged, because a global list of every -tion noun
    is noise, not signal — nominalizations are dispositioned per-passage, not en masse."""
    hits = []
    pat = re.compile(
        r'\b(' + '|'.join(LIGHT_VERBS) + r')\b\s+(a|an|the)?\s*'
        r'(\w+(?:tion|sion|ment|ance|ence|ity|ness|ure)|\w{2,}[aeyo]sis|synthes[ei]s|'
        r'assessment|comparison|evaluation|estimation|calculation|determination|'
        r'characteri[sz]ation|measurement|investigation|examination)\b', re.I)
    for i, s in enumerate(split_sentences(text)):
        for m in pat.finditer(s):
            hits.append({"sentence_idx": i, "match": m.group(0),
                         "kind": "light_verb+nominalization", "sentence": clip_text(s),
                         "priority": "high",
                         "note": "light verb + nominalization - promote the buried verb"})
    return hits

def nominalization_density(text):
    """DENSITY (background scan, not a flag list): count of candidate nominalizations per
    100 words, with the commonest offending suffixes. A high density signals limp,
    noun-heavy prose (Schimel ch.14) and pairs with a low verb/word ratio; the agent then
    zooms into the heaviest paragraphs rather than editing a 400-item global list."""
    COMMON = {"function","solution","section","condition","information","population",
              "distribution","relationship","temperature","reference","difference",
              "department","university","version","conclusion","question","direction"}
    words = words_of(text)
    sfx = Counter()
    n = 0
    for w in words:
        m = re.fullmatch(r'\w{4,}(tion|sion|ment|ance|ence|ity|ness|ure)', w, re.I)
        if m and w.lower() not in COMMON:
            n += 1
            sfx[m.group(1).lower()] += 1
    per100 = round(100 * n / len(words), 1) if words else 0.0
    return {"count": n, "per_100_words": per100, "by_suffix": dict(sfx.most_common()),
            "note": "candidate nominalizations/100w; >~4 is noun-heavy — zoom to the densest paragraphs"}

def find_weak_verbs(text):
    """TELL: a fuzzy verb that says something happened but not what (Schimel Table 14.1,
    p.139). Worst in a hypothesis. PROCEDURE: replace with an action verb that shows what
    the subject does."""
    hits = []
    pat = re.compile(r'\b(' + '|'.join(sorted(WEAK_VERBS, key=len, reverse=True)) + r')\b', re.I)
    for i, s in enumerate(split_sentences(text)):
        for m in pat.finditer(s):
            hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                         "note": "fuzzy verb - name the specific action"})
    return hits

def find_empty_amplifiers(text):
    """TELL: an empty intensifier/adverb (Schimel Table 16.1, p.165). PROCEDURE: delete it,
    or replace with a specific quantity. 'The Adverb is not your friend.' 'sharply' is in the
    lexicon (Bad-Writing register BWT-008); 'even' is surfaced separately as a LOWEST-severity
    candidate because it is often a legitimate against-expectation marker (high FP - triage,
    do not nag)."""
    hits = []
    pat = re.compile(r'\b(' + '|'.join(sorted(EMPTY_AMPLIFIERS, key=len, reverse=True)) + r')\b', re.I)
    for i, s in enumerate(split_sentences(text)):
        for m in pat.finditer(s):
            hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                         "note": "empty amplifier - delete or replace with a specific magnitude"})
        # BWT-008: 'even' is context-dependent (legitimate as a genuine against-expectation
        # marker), so it is a LOWEST-severity candidate with its own note, never a blanket ban.
        for m in re.finditer(r'\beven\b', s, re.I):
            hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                         "approximate": True,
                         "note": "LOWEST severity: 'even' is often a legitimate against-expectation "
                                 "marker - keep it only for a genuine surprise (candidate for triage, "
                                 "not a nag)"})
    return hits

def find_hype(text):
    """TELL: a hype/credibility-eroding word (Schimel ch.3, credible). PROCEDURE: ground the
    claim or cut the adjective; let the result carry the weight."""
    hits = []
    pat = re.compile(r'\b(' + '|'.join(sorted(HYPE_WORDS, key=len, reverse=True)) + r')\b', re.I)
    for i, s in enumerate(split_sentences(text)):
        for m in pat.finditer(s):
            hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                         "note": "hype word - ground it or cut it"})
    return hits

def find_prep_phrase_compounds(text):
    """TELL: 'NOUN of/in/for (the) NOUN' where flipping yields a tighter compound ('rate of
    reaction' -> 'reaction rate'). Schimel Table 15.2. PROCEDURE: flip if the compound reads
    idiomatically."""
    # restrict to 'of' (the flippable case), both nouns lowercase (drop proper nouns like
    # 'University of Arizona'), and exclude a pronoun/relative second token ('position on
    # what'). Still only a candidate — the flip must read idiomatically, which is judgment.
    PRON = {"what","which","them","this","that","these","those","it","us","him","her",
            "the","a","an","our","their","its","his","whom","who"}
    hits = []
    pat = re.compile(r'\b([a-z]{4,})\s+of\s+(the\s+)?([a-z]{4,})\b')
    for i, s in enumerate(split_sentences(text)):
        for m in pat.finditer(s):
            n1, n2 = m.group(1), m.group(3)
            if n2 in PRON or n1 in PRON:
                continue
            hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                         "note": f"try '{n2} {n1}' if idiomatic"})
    return hits

# --------------------------------------------------------------- SENTENCE-LEVEL detectors

def find_buried_verbs(text, threshold=9):
    """TELL: an overlong grammatical subject that pushes the main verb past ~9 words from
    the sentence start (Schimel ch.14 'put the action early'; C6 P7). Heuristic: first
    finite-verb position approximated by first auxiliary/verb-like token. approximate=True.
    PROCEDURE: move the action into an early, strong verb."""
    hits = []
    verbish = re.compile(
        r'\b(is|are|was|were|be|been|being|has|have|had|do|does|did|can|could|will|'
        r'would|shows?|showed|found|finds?|reveals?|demonstrates?|suggests?|indicates?|'
        r'requires?|causes?|produces?|yields?|leads?|drives?|reflects?|exhibits?|'
        r'occurs?|appears?|remains?|becomes?|makes?|gives?)\b', re.I)
    for i, s in enumerate(split_sentences(text)):
        m = verbish.search(s)
        if m:
            pre = len(words_of(s[:m.start()]))
            if pre > threshold:
                hits.append({"sentence_idx": i, "words_before_verb": pre, "match": m.group(0),
                             "sentence": clip_text(s), "approximate": True,
                             "note": f"~{pre} words before the main verb - front the action"})
    return hits

def find_trailing_qualifier(text):
    """TELL: a sentence ending in a trailing illustrative/qualifier clause ('..., such as X')
    that steals the stress position from the real idea (C6 P5). PROCEDURE: move the key idea
    to the end, or relocate the qualifier."""
    hits = []
    pat = re.compile(r',\s*(such as|including|e\.g\.|for example|like|particularly|especially|as well as)\b[^.]*\.$', re.I)
    for i, s in enumerate(split_sentences(text)):
        if pat.search(s):
            hits.append({"sentence_idx": i, "sentence": clip_text(s),
                         "note": "trailing qualifier occupies the stress position - put the key idea last"})
    return hits

TRAIN_FUNC = {"the","a","an","of","in","on","for","and","or","to","with","by","from","that",
    "which","is","are","was","were","we","our","this","these","their","its","as","at",
    "than","then","not","but","rather","more","most","less","such","both","either",
    "when","where","while","also","only","very","much","many","some","any","all"}

# --- lexicons (module-level literal sets/tuples) ---

# Schimel ch.15 Anglo-Saxon-over-Latinate + S&W Part V "avoid fancy words". Conservative:
# only words with a clear plain swap and low chance of being a term of art.
FANCY_WORDS = {
    "utilize": "use", "utilizes": "uses", "utilized": "used", "utilizing": "using",
    "commence": "begin", "commenced": "began", "commences": "begins", "commencing": "beginning",
    "endeavor": "try", "endeavour": "try", "endeavors": "tries", "elucidate": "clarify",
    "elucidates": "clarifies", "ascertain": "find out", "utilization": "use",
    "methodology": "methods", "methodologies": "methods", "operationalize": "define",
    "aforementioned": "this", "heretofore": "until now", "wherein": "where",
    "myriad": "many", "plethora": "many", "cognizant": "aware",
    "terminate": "end", "terminates": "ends", "initiate": "start", "initiates": "starts",
    "initiated": "started", "subsequent": "later", "individuals": "people",
}

# S&W Rule 17 / Schimel ch.16: fixed multi-word phrases replaceable by one word. (phrase -> swap)
WORDY_PHRASES = {
    "the fact that": "that / omit", "owing to the fact that": "because",
    "due to the fact that": "because", "in spite of the fact that": "although",
    "the question as to whether": "whether", "there is no doubt but that": "no doubt",
    "call your attention to the fact that": "remind you",
    "along these lines": "like this", "of a ... nature": "(cut)",
    "in the event that": "if", "in the neighborhood of": "about",
    "for the purpose of": "for / to", "with the exception of": "except",
    "a large number of": "many", "a majority of": "most", "at this point in time": "now",
    "in the near future": "soon", "for the foreseeable future": "for now",
    "it is worth noting that": "(cut)", "it should be noted that": "(cut)",
    "in terms of": "(recast)",
    # NB "with respect to" / "with regard to" deliberately OMITTED: in math/physics "with
    # respect to" names a differentiation variable or functional dependence ("differentiate
    # with respect to T"), where "about" destroys the meaning (blind review D3).
    "in the case of": "for", "the majority of": "most", "an increased number of": "more",
}

# S&W Part IV + Strunk Ch.V misused words NOT already in find_confusables (its/affect/
# principal/complement/discrete are handled there). Each is a candidate note, never a verdict.
MISUSED_WORDS = [
    (r"\bcomprised of\b", "'comprised of' -> 'composed of' or 'comprises' (the whole comprises the parts)"),
    (r"\bcenter(s|ed|ing)? around\b", "'center around' -> 'center on' / 'revolve around'"),
    # 'factor' as a standalone filler noun, but NOT inside a hyphen compound
    # ('transcription-factor binding', 'growth-factor') nor as a '-factor' suffix (blind review D4):
    (r"(?<![\w-])factor(?!-)\b", "'factor' -> often a hackneyed filler; name the specific cause (Strunk Ch.V)"),
    (r"\bin regards to\b", "'in regards to' -> 'in regard to' / 'regarding'"),
    (r"\bequally as\b", "'equally as' -> drop one: 'equally' or 'as ... as'"),
    (r"\b(more|most|rather|quite|somewhat|very)\s+unique\b", "'unique' admits no degree — drop the qualifier"),
    (r"\bdata is\b", "'data is' -> 'data are' (datum/data), unless mass-noun house style"),
    # 'impact' as a VERB (followed by an object) -> 'affect'; the bare noun ('environmental
    # impact', 'impact assessment', 'high-impact') is legitimate, so require a following
    # determiner/possessive so only the verbal use fires (blind review D4):
    (r"\bimpact(ed|ing|s)?\s+(the|a|an|our|their|its|these|those|this|that)\b",
     "'impact' as a verb -> 'affect' / a specific verb (Schimel ch.14)"),
    (r"\birregardless\b", "'irregardless' -> 'regardless'"),
]

# Legit -ize / -wise / -ism words that must NOT be flagged as coinages.
LEGIT_WISE = {"otherwise","likewise","clockwise","counterclockwise","lengthwise","crosswise",
    "widthwise","edgewise",
    # scientific/technical -wise terms are established vocabulary, NOT coinages (blind review D1):
    "pairwise","stepwise","piecewise","pointwise","elementwise","bitwise","rowwise",
    "columnwise","coordinatewise","samplewise","genewise","sitewise","familywise",
    "byteswise","channelwise","featurewise","classwise","voxelwise","edgeswise"}

# P2 §6.3 cls-7 discriminators for the 2-part-hyphen coinage/stack arm in find_noun_trains.
# COMMON_COMPOUND_TAIL: legit scientific compound SECOND parts (suppress) — deliberately EXCLUDES the
# target tails "invariant" (7.1) and "correlated" (7.2). COMMON_COMPOUND_HEAD: common adjectival FIRST
# parts that form legit compounds — deliberately EXCLUDES the target heads "gradient"/"microclimate".
COMMON_COMPOUND_TAIL = {"dependent","independent","specific","standardized","standardised","controlled",
    "related","associated","mediated","adjusted","weighted","normalized","normalised","corrected",
    "limited","resolved","informed","oriented","balanced","constrained","derived","calibrated",
    "sensitive","enhanced","reduced","based","driven","enabled","referenced","explicit"}
COMMON_COMPOUND_HEAD = {"functional","ecological","biological","physical","chemical","statistical",
    "empirical","numerical","seasonal","spatial","temporal","regional","natural","internal","external",
    "potential","additional","individual","different","standard","specific","particular","relative",
    "absolute","overall","original","structural","molecular","cellular","genetic","climatic","observed"}

def train_candidate(t):
    """POS-free heuristic for a noun-train member: lowercase (drops proper-noun/title runs),
    4+ chars, not a function word, not an obvious adverb/participle by suffix."""
    tl = t.lower()
    return (t == tl and len(t) >= 4 and tl not in TRAIN_FUNC
            and not tl.endswith("ly") and not tl.endswith("ed") and not tl.endswith("ing"))

def find_noun_trains(text, min_run=4):
    """TELL: a long run of stacked nouns/modifiers with no function word (Ruth Yanai's
    'noun trains'; Schimel ch.16, C6 P10). Without a POS tagger this cannot reach flag-list
    precision at run>=3 (it catches adjective+noun and cross-clause runs), so the flag list
    is restricted to LONG runs (>=4) where the false-positive rate is low; shorter runs are
    summarized by noun_train_density(). Also carries the Bad-Writing register BWT-003
    coined-symbol / private-label subclass (HIGH severity): a colon-label coinage used as a
    private label in prose ('Tension:limb') or a 3+-part hyphen-chain coinage
    ('larger-favored-low'). PROCEDURE: unpack with prepositions or hyphenate a lexicalized
    unit; spell out a coined label on first use. Standard notation (e.g. beta_sim, disp.lim.)
    is deliberately NOT matched - only colon/hyphen PRIVATE labels (the BWT-007 calibration
    hazard). approximate=True."""
    hits = []
    for i, s in enumerate(split_sentences(text)):
        run = []
        for t in re.findall(r"[A-Za-z][A-Za-z\-]+", s):
            if train_candidate(t):
                run.append(t)
            else:
                if len(run) >= min_run:
                    hits.append({"sentence_idx": i, "match": " ".join(run), "sentence": clip_text(s),
                                 "approximate": True, "note": "long noun train - unpack or hyphenate"})
                run = []
        if len(run) >= min_run:
            hits.append({"sentence_idx": i, "match": " ".join(run), "sentence": clip_text(s),
                         "approximate": True, "note": "long noun train - unpack or hyphenate"})
        # BWT-003 coined-symbol / private-label subclass (HIGH severity), candidate-only. A
        # colon-label coinage ('Tension:limb') needs no space around the colon (so 'Fig. 1:'
        # and ratios/times do not fire); a 3+-part hyphen chain ('larger-favored-low') is a
        # coinage a domain reader cannot parse. Standard notation (beta_sim, disp.lim.) uses
        # underscores/dots, not colon/hyphen labels, so it is not matched.
        for m in re.finditer(r'\b[A-Za-z][A-Za-z]+:[A-Za-z][A-Za-z]+\b', s):
            hits.append({"sentence_idx": i, "match": m.group(0), "kind": "coined-colon-label",
                         "sentence": clip_text(s), "approximate": True,
                         "note": "HIGH severity: colon-label coinage used as a private label - "
                                 "spell it out or unpack it (a private label, not standard notation)"})
        for m in re.finditer(r'\b[A-Za-z]+-[A-Za-z]+-[A-Za-z]+(?:-[A-Za-z]+)*\b', s):
            hits.append({"sentence_idx": i, "match": m.group(0), "kind": "coined-hyphen-chain",
                         "sentence": clip_text(s), "approximate": True,
                         "note": "HIGH severity: 3+-part hyphen-chain coinage - unpack into a phrase "
                                 "a domain reader can parse (candidate; some 3-part chains are legit)"})
        # P2 §6.3 cls-7: a 2-PART hyphen compound stacked-modifier coinage (7.1 "gradient-invariant
        # host baseline", 7.2 "microclimate-correlated gradient"). This operates DIRECTLY on the hyphen
        # token, NOT via train_candidate (whose -ed rule @:347 excludes "microclimate-correlated"), which
        # is why min_run 4->3 CANNOT reach 7.2. FP guard (2-part hyphenates are ubiquitous & mostly
        # legitimate - the §6.3 FLAG): BOTH parts >=7 letters (technical/coined length: drops well-known,
        # long-term, large-scale, trait-based, high-resolution, co-varying), first part not an adverb
        # (-ly), neither part a COMMON legit compound head/tail, AND the compound sits in a STACK (a bare
        # content noun immediately before or after). The (?<![A-Za-z-]) / (?![A-Za-z-]) lookarounds keep
        # this to EXACTLY 2 parts so a 3+-chain (already flagged above) does not double-count.
        for m in re.finditer(r'(?<![A-Za-z-])([A-Za-z]{7,})-([A-Za-z]{7,})(?![A-Za-z-])', s):
            a, b = m.group(1).lower(), m.group(2).lower()
            if a.endswith("ly") or b in COMMON_COMPOUND_TAIL or a in COMMON_COMPOUND_HEAD:
                continue
            nxt = re.match(r'\s+([A-Za-z][A-Za-z\-]{3,})', s[m.end():m.end()+40])
            prv = re.search(r'([A-Za-z][A-Za-z\-]{3,})\s+$', s[max(0, m.start()-40):m.start()])
            in_stack = (nxt and train_candidate(nxt.group(1))) or (prv and train_candidate(prv.group(1)))
            if not in_stack:
                continue
            hits.append({"sentence_idx": i, "match": m.group(0), "kind": "stacked-hyphen-compound",
                         "sentence": clip_text(s), "approximate": True,
                         "note": "MEDIUM severity: 2-part stacked-modifier compound - unpack into a phrase "
                                 "a domain reader parses left-to-right (candidate; 2-part hyphenates are "
                                 "often legitimate - the stack + technical length is the tell)"})
    return hits

def noun_train_density(text, min_run=3):
    """DENSITY (background scan): number of 3+-token candidate runs per 100 words. High
    density = noun-heavy, hard-to-parse prose; the agent zooms to the densest sentences
    rather than working a global list. approximate=True (POS-free)."""
    runs = 0; words = words_of(text)
    for s in split_sentences(text):
        run = []
        for t in re.findall(r"[A-Za-z][A-Za-z\-]+", s):
            if train_candidate(t):
                run.append(t)
            else:
                if len(run) >= min_run:
                    runs += 1
                run = []
        if len(run) >= min_run:
            runs += 1
    return {"count_3plus": runs, "per_100_words": round(100*runs/len(words),1) if words else 0.0,
            "approximate": True, "note": "3+-noun runs/100w (POS-free estimate)"}

def find_repeated_words(text):
    """TELL: the same content stem (crudely, same 6-char lowercased prefix) used >=2x within
    one sentence (C6 P11). PROCEDURE: vary or cut."""
    hits = []
    STOP = {"which","their","there","these","those","other","study","using","between",
            "results","result","effect","effects","because","however"}
    for i, s in enumerate(split_sentences(text)):
        stems = [w.lower()[:6] for w in words_of(s) if len(w) >= 5 and w.lower() not in STOP]
        c = Counter(stems)
        rep = {w: n for w, n in c.items() if n >= 2}
        if rep:
            hits.append({"sentence_idx": i, "repeats": rep, "sentence": clip_text(s),
                         "note": "repeated content word(s) in one sentence - vary or cut"})
    return hits

def find_metadiscourse(text):
    """TELL: 'discussing the discussion' - clause-initial 'we found that', 'we argue that',
    'these data suggest that', 'it is important to note' (Schimel ch.16). PROCEDURE: state
    the finding directly; the reader knows it is yours."""
    hits = []
    pat = re.compile(
        r'(?i)\b(we\s+(found|argue|show|showed|observed|note|report|demonstrate|believe|'
        r'suggest|propose|hypothesi[sz]e)\s+that|these\s+(data|results|findings)\s+'
        r'(may\s+)?(indicate|suggest|show|demonstrate|imply)|it\s+is\s+(important|worth|'
        r'interesting)\s+to\s+note|to\s+the\s+best\s+of\s+our\s+knowledge)\b')
    for i, s in enumerate(split_sentences(text)):
        for m in pat.finditer(s):
            hits.append({"sentence_idx": i, "match": clip_text(m.group(0), 60), "sentence": clip_text(s),
                         "note": "metadiscourse - state the finding directly"})
    return hits

def find_significance_without_effect(text):
    """TELL: a significance verdict (p-value or 'significant') with no magnitude/effect-size
    token in the same sentence (Schimel ch.8, P8/P9). PROCEDURE: report the effect size and
    direction, not just the p-value; the story is in the data, not the statistics."""
    hits = []
    sig = re.compile(r'(p\s*[<=>]\s*0?\.\d+|\bsignificant(ly)?\b|\bnon-?significant\b)', re.I)
    mag = re.compile(r'(\d+(\.\d+)?\s*(x|%|percent|-?fold|times)|factor of|ratio|by\s+\d|'
                     r'\d+(\.\d+)?\s*(mg|ml|mm|cm|µm|nm|mM|µM|nM|°c|kg|g)\b)', re.I)
    for i, s in enumerate(split_sentences(text)):
        if sig.search(s) and not mag.search(s):
            hits.append({"sentence_idx": i, "sentence": clip_text(s),
                         "note": "significance without an effect size - add magnitude + direction"})
    return hits

def find_weak_gap_framing(text):
    """TELL: a gap framed as 'little is known' / 'poorly understood' / 'few studies have'
    (Schimel ch.7 P12) - fails scientifically (absence of knowledge is not a question),
    logically, and linguistically. PROCEDURE: state the specific question the gap raises."""
    hits = []
    pat = re.compile(r'(?i)\b((little|not much)\s+is\s+known|(poorly|not well|not fully|'
                     r'incompletely)\s+understood|(few|no)\s+studies\s+have|remains?\s+'
                     r'(largely\s+)?(unknown|unexplored|poorly understood|unclear))\b')
    for i, s in enumerate(split_sentences(text)):
        for m in pat.finditer(s):
            hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                         "note": "weak gap framing - state the concrete question instead"})
    return hits

def find_undermining_resolution(text):
    """TELL: 'more research is needed' / 'remains to be determined' / 'has yet to be'
    (Schimel ch.9 P20, C6 F2) - ends the story on weakness. PROCEDURE: close on what the
    work established and what it implies; put limitations in the middle, not the stress
    position."""
    hits = []
    pat = re.compile(r'(?i)\b(more\s+(research|work|study|studies)\s+(is|are|will be)\s+needed|'
                     r'remains?\s+to\s+be\s+(established|determined|assessed|elucidated|seen)|'
                     r'(has|have)\s+yet\s+to\s+be|further\s+(work|research|study)\s+is\s+(needed|required|warranted))\b')
    for i, s in enumerate(split_sentences(text)):
        for m in pat.finditer(s):
            hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                         "note": "undermining resolution - close on what was learned + implication"})
    return hits

def find_citation_position(text):
    """TELL (informational, not a defect): sentence-initial 'Smith (2003) found X' places
    the citation in the topic position vs 'X occurs (Smith 2003)' (Schimel ch.6 P16).
    Neither is wrong; the choice controls what the sentence is ABOUT. PROCEDURE: use
    author-prominent when the study is the character; content-prominent when the finding is."""
    hits = []
    pat = re.compile(r'^\s*([A-Z][a-z]+(\s+(and|&)\s+[A-Z][a-z]+)?|[A-Z][a-z]+\s+et\s+al\.?)\,?\s*'
                     r'\(?\d{4}[a-z]?\)?\s+(found|showed|reported|observed|demonstrated|argued|'
                     r'suggested|proposed|noted|described|concluded)\b')
    for i, s in enumerate(split_sentences(text)):
        if pat.search(s):
            hits.append({"sentence_idx": i, "sentence": clip_text(s),
                         "note": "author-prominent citation - the study is the topic; confirm that's intended"})
    return hits

def find_bizzwidget_opening(text, first_n_sentences=3):
    """TELL: the 'bizzwidget' opening (Schimel ch.5, Cluster2 P14) — a named method, tool,
    model, or acronym is introduced and elaborated in the opening sentences before any
    problem/question/gap is posed. The door-to-door salesperson leading with the product.
    Heuristic: within the first N sentences, an acronym definition or a 'we (propose to)
    use/develop/apply X' construction appears with NO gap/problem/question marker
    (however|unknown|unclear|question|problem|challenge|why|whether|remains) before it.
    approximate=True. PROCEDURE: open on the problem the tool addresses, then name the tool."""
    sents = split_sentences(text)[:first_n_sentences]
    hits = []
    acits = re.compile(r'\b([A-Z][a-z]+\s+){1,4}\(([A-Z]{2,7})\)|'
                       r'\bwe\s+(propose\s+to\s+|)(use|develop|apply|present|introduce|build)\b', re.I)
    gap = re.compile(r'(?i)\b(however|but|unknown|unclear|question|problem|challenge|gap|'
                     r'why|whether|remains?|little is known|poorly understood|puzzl|paradox)\b')
    for i, s in enumerate(sents):
        m = acits.search(s)
        if m and not gap.search(" ".join(sents[:i + 1])):
            hits.append({"sentence_idx": i, "match": clip_text(m.group(0), 50), "sentence": clip_text(s),
                         "approximate": True,
                         "note": "method/tool/acronym introduced before any problem is posed - "
                                 "open on the problem, then name the tool (bizzwidget opening)"})
    return hits

def find_objectives_not_question(text):
    """TELL: 'our objective was to ...' / 'we aimed to ...' with no interrogative or hypothesis
    nearby (Schimel ch.7 P18) - objectives are activities, not the question. PROCEDURE: state
    the question the objectives serve."""
    hits = []
    pat = re.compile(r'(?i)\b((our|the)\s+(objectives?|aims?|goals?|purpose)\s+(was|were|is|are)\s+to|'
                     r'we\s+(aimed|sought|set out|wanted)\s+to)\b')
    for i, s in enumerate(split_sentences(text)):
        for m in pat.finditer(s):
            hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                         "note": "objectives stated as activities - surface the underlying question"})
    return hits

def find_undefined_acronyms(text):
    """TELL: an ALL-CAPS acronym whose first occurrence has no adjacent expansion
    (Schimel ch.15). PROCEDURE: define at first use as 'Expansion (ACRONYM)'."""
    COMMON = {"DNA","RNA","ATP","PCR","USA","US","UK","CO2","CO","PH","ID","OK","AI","ML",
              "GDP","NASA","FIG","EQ","SI","3D","2D","UV","IR","LED","PDF","URL","API"}
    seen, hits = set(), []
    for i, s in enumerate(split_sentences(text)):
        for m in re.finditer(r'\b([A-Z]{2,7})\b', s):
            ac = m.group(1)
            if ac in COMMON or ac in seen:
                continue
            seen.add(ac)
            if re.search(rf'\([^)]*\b{ac}\b[^)]*\)', s) or re.search(rf'{ac}\s*\([^)]+\)', s) \
               or re.search(r'\b([A-Z][a-z]+\s+){1,5}\(' + ac + r'\)', s):
                continue
            hits.append({"sentence_idx": i, "acronym": ac, "sentence": clip_text(s),
                         "note": f"'{ac}' first used without an expansion - define at first use"})
    return hits

def find_confusables(text):
    """TELL: commonly-confused real words the spell-checker misses (Schimel ch.17 P25).
    PROCEDURE: context-check each. Reported for review, not auto-corrected."""
    hits = []
    pairs = [(r"\bits\b", "its/it's - possessive vs 'it is/has'"),
             (r"\bit's\b", "it's = 'it is/has' only"),
             (r"\baffect\b", "affect (usu. verb) vs effect (usu. noun)"),
             (r"\beffect\b", "effect (usu. noun) vs affect (usu. verb)"),
             (r"\bprincipal\b", "principal vs principle"),
             (r"\bcomplement\b", "complement vs compliment"),
             (r"\bdiscrete\b", "discrete vs discreet")]
    for i, s in enumerate(split_sentences(text)):
        for pat, note in pairs:
            if re.search(pat, s, re.I):
                hits.append({"sentence_idx": i, "match": pat, "sentence": clip_text(s), "note": note})
    return hits

# ------------------------------------------------------------------- PROFILE (not defects)

def sentence_length_profile(text, long_threshold=40, very_long=55):
    """Sentence-length distribution. Schimel ch.16: vary length; a wall of >40-word
    sentences is a fatigue signal. Returns stats + the longest sentences."""
    sents = split_sentences(text)
    lens = [len(words_of(s)) for s in sents]
    if not lens:
        return {"n": 0}
    order = sorted(range(len(lens)), key=lambda k: lens[k], reverse=True)
    return {
        "n": len(lens), "mean": round(sum(lens) / len(lens), 1), "max": max(lens),
        "n_over_long": sum(1 for L in lens if L > long_threshold),
        "n_very_long": sum(1 for L in lens if L > very_long),
        "longest": [{"idx": k, "words": lens[k], "sentence": clip_text(sents[k])} for k in order[:8]],
    }

def punctuation_density(text):
    """Em-dash and semicolon counts. High density is a voice choice, not a defect -
    reported so the agent can decide whether it has tipped into a tic."""
    # exclamation marks on declaratives (S&W Part V: 'do not use ... to emphasize') counted
    # here rather than as a separate detector — a bare '!' outside quotes is a voice tic.
    excl = len(re.findall(r'(?<!["\'])!(?!["\'])', text))
    return {"em_dashes": len(re.findall(r'—|--', text)),
            "semicolons": text.count(';'),
            "exclamations": excl,
            "words": len(words_of(text))}

def verb_to_word_ratio(text):
    """Schimel ch.16 (p.171): finite verbs / total words; ~15% ('4 of 27') is comfortable.
    Verb count is approximated by a finite-verb lexicon. approximate=True. Low ratio =
    nominalization-heavy, energy-poor prose."""
    verbish = re.compile(
        r'\b(is|are|was|were|be|been|being|has|have|had|do|does|did|can|could|will|would|'
        r'\w+ed|\w+s)\b', re.I)
    words = words_of(text)
    if not words:
        return {"ratio": None}
    v = len(verbish.findall(text))
    return {"approx_verbs": v, "words": len(words),
            "ratio": round(v / len(words), 3), "comfortable": "~0.15",
            "approximate": True}

# ----------------------------------------------------------------------------- top driver

# Schimel's SCFL top-down editing order (ch.17, p.~174) = Structure (get the story's
# structure into shape), Clarity (ideas clear and concrete), Flow (link thought to
# thought), Language (make it sound good): fix higher levels first. These detectors live
# at the Clarity/Flow/Language tiers — the leaves — and never touch Structure, which is
# the agent's judgment. Within here, sentence-level (Flow) detectors precede word-level
# (Language) ones to mirror that order.
def find_fancy_words(text):
    """TELL: a Latinate/fancy word where a plain Anglo-Saxon one carries the meaning
    (Schimel ch.15, Anglo-Saxon table; S&W Part V 'avoid fancy words'). PROCEDURE: swap the
    plain word unless the fancy one is a term of art here. A candidate — some fields fix
    'utilize'/'methodology' as jargon; the agent disposes."""
    hits = []
    keys = sorted(FANCY_WORDS, key=len, reverse=True)
    pat = re.compile(r'\b(' + '|'.join(re.escape(k) for k in keys) + r')\b', re.I)
    for i, s in enumerate(split_sentences(text)):
        for m in pat.finditer(s):
            plain = FANCY_WORDS.get(m.group(0).lower(), "")
            hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                         "note": f"fancy word - try '{plain}' unless it's a term of art here"})
    return hits

def find_wordy_phrases(text):
    """TELL: a fixed multi-word phrase that a single word replaces (S&W Rule 17 'omit needless
    words'; Schimel ch.16 condensing). PROCEDURE: make the swap in the note. High precision —
    these phrases are almost never load-bearing."""
    hits = []
    # 'of a ... nature' handled by a small pattern; the rest are literal phrases
    for i, s in enumerate(split_sentences(text)):
        low = s.lower()
        for phrase, swap in WORDY_PHRASES.items():
            if "..." in phrase:
                continue
            if phrase in low:
                hits.append({"sentence_idx": i, "match": phrase, "sentence": clip_text(s),
                             "note": f"wordy - '{phrase}' -> '{swap}'"})
        for m in re.finditer(r'\bof\s+an?\s+\w+\s+nature\b', s, re.I):
            hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                         "note": "wordy - 'of a X nature' -> the adjective X (or cut)"})
    return hits

def find_misused_words(text):
    """TELL: a commonly-misused word/expression beyond the confusables set (S&W Part IV;
    Strunk Ch.V). PROCEDURE: context-check each against the note. Candidates for review, not
    auto-corrections. approximate=True (some, e.g. 'factor'/'impact', are legitimate in
    context)."""
    hits = []
    for i, s in enumerate(split_sentences(text)):
        for pat, note in MISUSED_WORDS:
            m = re.search(pat, s, re.I)
            if m:
                hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                             "approximate": True, "note": note})
    return hits

def find_flourish_triad(text):
    """TELL (BWT-001/002, rule-of-threes / triadic parade): a repetition-for-cadence flourish - the
    reader hears a drumbeat instead of content. SPLIT out of the old find_rhetorical_flourish (P2 item 2,
    the triad/anaphora hit-key). Arms:
      - article-triplet: 'a X, a Y, or a Z' (repeated indefinite article = props for effect)
      - asyndetic tricolon (NEW): an em-dash/paren-bounded 3-item list with NO conjunction
        ('- planner, subagents, durable files -') - the triadic-parade form the article-triplet misses
        (the user-caught 4-tic exemplar's 'triad-without-articles' label)
      - anaphora (clause): >=3 comma-clauses sharing an identical 2-word opener ('does not X, does not
        Y, and does not Z')
      - anaphora (sentence): >=3 consecutive sentences with an identical opener
      - reduplication (NEW, §6.2 cls-1.3): 'X by X' ('taxon by taxon') - a bounded low-FP cadence
    CANDIDATE ONLY; a parallel triplet that enumerates three real caveats EARNS its length. approximate=True."""
    hits = []
    sents = split_sentences(text)
    ITEM = r'[A-Za-z][\w-]*(?:\s+[A-Za-z][\w-]+){0,2}'
    triplet   = re.compile(r'\b(a|an)\s+\w+,\s+(a|an)\s+\w+,\s+(?:or|and)\s+(a|an)\s+\w+\b', re.I)
    # asyndetic tricolon: 3 short items, NO 'and/or', bounded by em-dash OR paren on BOTH sides (the
    # parenthetical-parade framing) - an ordinary 3-item list uses 'and/or' before the last item.
    asyndetic = re.compile(r'(?:[—(]|--)\s*(' + ITEM + r'),\s+(' + ITEM + r'),\s+(' + ITEM +
                           r')\s*(?:[—)]|--)')
    redup     = re.compile(r'\b(\w{3,})\s+by\s+\1\b', re.I)
    anaphora_clause = re.compile(r'\b(\w+\s+\w+)\b[^,.;:]{0,60},\s*(?:and\s+|or\s+|nor\s+|but\s+)?\1\b[^,.;:]{0,60},\s*(?:and\s+|or\s+|nor\s+|but\s+)?\1\b', re.I)
    openers = [(words_of(s)[0].lower() if words_of(s) else "") for s in sents]
    j = 0
    while j < len(sents):
        op = openers[j]; k = j
        while k < len(sents) and op and openers[k] == op:
            k += 1
        if op and k - j >= 3:
            hits.append({"sentence_idx": j, "match": op, "kind": "anaphora-sentence",
                         "sentence": clip_text(sents[j]), "approximate": True,
                         "note": "rhetorical flourish (anaphora) - " + str(k - j) + " consecutive sentences "
                                 "open with '" + op + "'; vary the opener so the reader hears content, not cadence"})
        j = k if k > j else j + 1
    for i, s in enumerate(sents):
        subs = []
        m1 = triplet.search(s)
        if m1: subs.append(("article-triplet", clip_text(m1.group(0), 60), "repeated 'a/an X, a Y, or a Z' - props chosen for effect"))
        m2 = asyndetic.search(s)
        if m2 and not m1 and " and " not in m2.group(0).lower() and " or " not in m2.group(0).lower():
            subs.append(("asyndetic-triad", clip_text(m2.group(0), 60),
                         "LOW severity: asyndetic tricolon (3-item list, no conjunction, set off by dashes/parens) "
                         "- a rule-of-threes parade; confirm it earns the cadence (a plain appositive list is fine)"))
        m3 = redup.search(s)
        if m3: subs.append(("reduplication", m3.group(0), "'X by X' reduplication cadence - state it plainly"))
        m4 = anaphora_clause.search(s)
        if m4: subs.append(("anaphora-clause", clip_text(m4.group(0), 60),
                            "3+ clauses share an identical opener (rule-of-threes cadence) - vary the connective or split the series"))
        for kind, mark, note in subs:
            hits.append({"sentence_idx": i, "match": mark, "kind": kind, "sentence": clip_text(s),
                         "approximate": True,
                         "note": "rhetorical flourish (" + kind + ") - " + note + "; keep only if it does real work here"})
    return hits


def find_flourish_epigram(text):
    """TELL (BWT-001, balanced epigram / contrastive definition): a two-part balanced flourish or an
    antithesis whose symmetry the reader admires instead of absorbing the point. SPLIT out of the old
    find_rhetorical_flourish (P2 item 2, the balanced-epigram hit-key); implements §6.1 cls-2 + §6.2 cls-4.
    Arms:
      - balanced parallel epigram (NEW, §6.1 cls-2): 'Convergence in space, divergence in time' (abstract
        noun + same preposition, twice) - the paragraph-closing two-part flourish (2.1)
      - antithesis 'X, not Y' / 'not X but Y' (abstract-noun form) - 4.1
      - reversed / plain 'X, not Y' closer (NEW): 'a feature, not monotony' (the exemplar's reversed contrast)
      - 'it's not X, it's Y' comma-antithesis (NEW, §6.2 cls-4.2)
    CANDIDATE ONLY; a genuine contrast made once and plainly is fine. approximate=True."""
    hits = []
    balanced = re.compile(r'\b([A-Za-z]+ence|[A-Za-z]+ing|[A-Za-z]+tion|[A-Za-z]+ity|[A-Za-z]+ism)\s+'
                          r'(in|by|of|across|through|over|within|between|at|from)\s+\w+,\s+'
                          r'([A-Za-z]+ence|[A-Za-z]+ing|[A-Za-z]+tion|[A-Za-z]+ity|[A-Za-z]+ism)\s+\2\s+\w+', re.I)
    antithesis = re.compile(r'\b(\w+ing|\w+tion|\w+ence|\w+ance)\b[^,.;]{0,30},\s+not\s+\b(\w+ing|\w+tion|\w+ence|\w+ance)\b', re.I)
    not_but    = re.compile(r'\bnot\s+\w+\s+but\s+\w+\b', re.I)
    its_not    = re.compile(r"\b(it'?s|it\s+is)\s+not\s+\w+,?\s+(it'?s|it\s+is)\s+\w+", re.I)
    # reversed/plain 'X, not Y' - broaden beyond abstract endings, LOW severity. Guard: 3+-letter content
    # word right after 'not' (excludes 'not a X' normal negation) and not 'not only/just/merely/simply/yet'.
    reversed_contrast = re.compile(r'\b([A-Za-z]{3,}),\s+not\s+(?!only\b|just\b|merely\b|simply\b|yet\b|a\b|an\b|the\b)([A-Za-z]{3,})\b', re.I)
    # P2c guard (per P2v): the reversed-contrast arm is a CLOSER detector - a paragraph-/sentence-ending
    # 'X, not Y' epigram. Two gates keep legitimate methods/results distinctions silent so it fires only on a
    # genuine flourish-closer, mirroring find_apologetic_contrast's design-choice cue:
    #   (1) CLAUSE POSITION - fire only when 'not Y' is sentence-final (the tail is just closing quotes/parens
    #       and a terminator); a mid-sentence 'held fixed, not frozen, during spin-up' is a clarification, not a closer.
    #   (2) DESIGN-CHOICE CUE - stay silent when the sentence frames a deliberate methods/results choice
    #       (we/our/use/define/model/treat/control/approach/design/variable), e.g. 'we treat host as fixed, not frozen'.
    # A real rhetorical closer ('the same name for the same thing is a feature, not monotony.') carries neither.
    rc_choice_cue = re.compile(r'\b(we|our|makes?|made|treat(?:s|ed)?|us(?:e|es|ed|ing)|defin(?:e|es|ed|ing)|fram(?:e|es|ed|ing)|model(?:s|ed|ing)?|chose|choose|chosen|control|approach|design|variable)\b', re.I)
    rc_sentence_final = re.compile(r'^["\')\]\s]*[.!?]*["\')\]\s]*$')
    for i, s in enumerate(split_sentences(text)):
        subs = []
        m = balanced.search(s)
        if m: subs.append(("balanced-epigram", clip_text(m.group(0), 60),
                           "two-part balanced parallel ('X in A, Y in B') - a paragraph-closing epigram; state the point plainly"))
        m = antithesis.search(s) or not_but.search(s)
        has_antith = bool(m)
        if m: subs.append(("antithesis", clip_text(m.group(0), 60), "cute antithesis (X, not Y / not X but Y) - state the point plainly"))
        m = its_not.search(s)
        if m: subs.append(("its-not-x", clip_text(m.group(0), 60), "'it's not X, it's Y' antithesis - state what it IS plainly"))
        if not has_antith:
            m = reversed_contrast.search(s)
            # P2c: only a sentence-final closer with no design-choice cue counts as a flourish (see rc_* above).
            if m and rc_sentence_final.match(s[m.end():]) and not rc_choice_cue.search(s):
                subs.append(("reversed-contrast", clip_text(m.group(0), 60),
                               "LOW severity: 'X, not Y' reversed contrast-closer - often a flourish; keep only for a needed distinction"))
        for kind, mark, note in subs:
            hits.append({"sentence_idx": i, "match": mark, "kind": kind, "sentence": clip_text(s),
                         "approximate": True,
                         "note": "rhetorical flourish (" + kind + ") - " + note + "; keep only if it does real work here"})
    return hits


def find_flourish_metaphor(text):
    """TELL (BWT-001, showy figure): a metaphor vehicle or over-emphatic construction the reader notices
    AS prose. SPLIT out of the old find_rhetorical_flourish (P2 item 2, the showy-metaphor hit-key). Arms:
      - showy metaphor vehicle: 'the thread from which both ... hang/spring/flow'
      - 'the very X' over-emphasis
    CANDIDATE ONLY; a metaphor kept once for ring composition can be load-bearing. approximate=True."""
    hits = []
    very_x   = re.compile(r'\bthe very\s+\w+', re.I)
    metaphor = re.compile(r'\bthe\s+\w+\s+from which\b[^.]*\b(hang|hangs|hung|spring|springs|sprang|flow|flows|flowed|grow|grows|grew|dangle|dangles)\b', re.I)
    for i, s in enumerate(split_sentences(text)):
        subs = []
        m = metaphor.search(s)
        if m: subs.append(("showy-metaphor", clip_text(m.group(0), 60), "showy metaphor vehicle - use a plain description unless load-bearing"))
        m = very_x.search(s)
        if m: subs.append(("the-very-X", m.group(0), "'the very X' over-emphasis - drop 'very'"))
        for kind, mark, note in subs:
            hits.append({"sentence_idx": i, "match": mark, "kind": kind, "sentence": clip_text(s),
                         "approximate": True,
                         "note": "rhetorical flourish (" + kind + ") - " + note + "; keep only if it does real work here"})
    return hits


def find_apologetic_contrast(text):
    """TELL (BWT-009, false-antithesis / preemptive-apology): 'X rather than Y' / 'not X but Y' where X
    reads as the study's OWN deliberate choice, framed as a concession (5.1). SPLIT out of the old
    find_rhetorical_flourish (P2 item 2 / item 11, the rather-than gate). LOW severity; GATED on a
    design-choice cue so plain 'rather than' does not fire - a truly CUE-LESS 'rather than' has a high
    legitimate rate and is intentionally NOT flagged (cautious-FP; this is why the exemplar's cue-less
    'rather than' is the one label of four the layer does not catch). CANDIDATE ONLY."""
    hits = []
    rather_than = re.compile(r'\brather\s+than\b|\bnot\s+\w+\s+but\s+\w+\b', re.I)
    choice_cue  = re.compile(r'\b(we|our|makes?|made|treat(?:s|ed)?|us(?:e|es|ed|ing)|defin(?:e|es|ed|ing)|fram(?:e|es|ed|ing)|model(?:s|ed|ing)?|chose|choose|chosen|control|approach|design|variable)\b', re.I)
    for i, s in enumerate(split_sentences(text)):
        m = rather_than.search(s)
        if m and choice_cue.search(s):
            hits.append({"sentence_idx": i, "match": clip_text(m.group(0), 60), "kind": "rather-than",
                         "sentence": clip_text(s), "approximate": True,
                         "note": "LOW severity: 'X rather than Y'/'not X but Y' framing a deliberate design "
                                 "choice as a concession - state it as the positive decision it was "
                                 "(usually legitimate; candidate-only, cue-gated)"})
    return hits

def find_expletive_opener(text):
    """TELL: a sentence opening with an expletive that delays the real subject — 'There is/are/
    was/were X that ...' or 'It is/was ADJ that ...' (Schimel ch.13 topic/stress: the topic
    position should carry the sentence's subject; S&W 'there is/there are' weakener).
    PROCEDURE: promote the real subject to the front ('There are three factors that drive Y'
    -> 'Three factors drive Y'). Candidate — some 'there is' clauses are idiomatic."""
    hits = []
    there_is = re.compile(r'^\s*(there\s+(is|are|was|were|exists?|remain(s|ed)?)|it\s+(is|was)\s+\w+\s+that)\b', re.I)
    for i, s in enumerate(split_sentences(text)):
        m = there_is.search(s)
        if m:
            hits.append({"sentence_idx": i, "match": clip_text(m.group(0), 40), "sentence": clip_text(s),
                         "note": "expletive opener - promote the real subject to the topic position"})
    return hits

def find_not_positive_form(text):
    """TELL: a statement made by negation where a positive form is crisper (S&W Rule 15 'put
    statements in positive form'; Schimel). Patterns: 'not un-ADJ' (double negative),
    'did not ... until', 'not ... any' -> 'no', 'not the same' -> 'different', 'not many' ->
    'few', 'not ... unless'. PROCEDURE: state what IS, not what isn't. NB the sibling failure
    mode from the calibration corpus: fixing this must PRESERVE MEANING (over-correction once
    introduced a claim contradicting the methods) - so it's a candidate, the agent recasts."""
    hits = []
    # 'not un-X' double negatives: restrict to a set of genuinely un-negatable adjectives.
    # A blind 'not un\w+' matches 'not uniform / not unique / not universal / not understood /
    # not under', none of which are double negatives (blind review D2).
    NOT_UN = (r'\bnot\s+un(common|usual|likely|important|reasonable|clear|related|expected|'
              r'ambiguous|able|aware|affected|changed|known|noticed|surprising|helpful|'
              r'necessary|willing|able|complicated|controversial|familiar|interesting)\b')
    pats = [
        (NOT_UN, "double negative 'not un-X' - state positively (e.g. 'not uncommon' -> 'common')"),
        (r'\bnot\s+the\s+same\b', "'not the same' -> 'different'"),
        (r'\bnot\s+many\b', "'not many' -> 'few'"),
        (r'\bnot\s+(a|any)\s+\w+', "'not a/any X' -> 'no X'"),
        (r'\bdid\s+not\s+\w+\s+until\b', "'did not X until' -> positive form"),
        (r'\bnot\s+\w+\s+enough\b', "'not X enough' - consider a positive limit"),
    ]
    for i, s in enumerate(split_sentences(text)):
        for pat, note in pats:
            m = re.search(pat, s, re.I)
            if m:
                hits.append({"sentence_idx": i, "match": m.group(0), "sentence": clip_text(s),
                             "note": "negation - " + note + " (preserve meaning when recasting)"})
    return hits

def find_naked_this(text):
    """TELL: a sentence-initial demonstrative pronoun with no noun attached — 'This shows ...',
    'These suggest ...', 'This is because ...' — forcing the reader to resolve what 'this'
    points to (Schimel ch.13 given-to-new / cohesion). PROCEDURE: attach the noun ('This
    result shows', 'These data suggest'). approximate=True (some are clear from an adjacent
    antecedent)."""
    hits = []
    naked = re.compile(r'^\s*(This|These|That|Those)\s+(is|are|was|were|shows?|showed|suggests?|'
                       r'suggested|indicates?|indicated|means?|meant|demonstrates?|implies|implied|'
                       r'caused|reflects?|because|confirms?|confirmed|explains?|explained|'
                       r'highlights?|highlighted|reveals?|revealed|happens?|happened|occurs?|occurred)\b')
    for i, s in enumerate(split_sentences(text)):
        m = naked.search(s)
        if m:
            hits.append({"sentence_idx": i, "match": clip_text(m.group(0), 30), "sentence": clip_text(s),
                         "approximate": True,
                         "note": "naked demonstrative - attach the noun ('This " + "result/effect" + " ...') for cohesion"})
    return hits

def find_giant_paragraph(text, word_limit=180):
    """TELL: a paragraph over ~180 words (a wall that buries its own arc) OR a lone
    single-sentence paragraph that is not an obvious transition (Schimel ch.11: every
    paragraph needs its own arc). PROCEDURE: split the wall at its internal arc boundary;
    fold or expand the orphan. Operates on paragraph structure, so it reads raw text, not the
    sentence stream."""
    hits = []
    paras = paragraphs(text)
    npar = len(paras)
    for pi, p in enumerate(paras):
        wc = len(words_of(p))
        sents = split_sentences(p)
        if wc > word_limit:
            hits.append({"paragraph_idx": pi, "words": wc, "match": f"{wc}-word paragraph",
                         "sentence": clip_text(p, 100),
                         "note": f"{wc}-word paragraph (>~{word_limit}) - split at its internal arc boundary"})
        # Orphan rule is deliberately conservative (blind review): a lone single-sentence
        # paragraph is only flagged in a genuine multi-paragraph body (>=3 paragraphs) and
        # NOT at the opening or closing position (short openers/closers are legitimate), and
        # never when it is an explicit transition. A single-sentence WHOLE document is not a
        # structural orphan, so npar>=3 also filters the degenerate one-paragraph input.
        elif (len(sents) == 1 and wc > 8 and npar >= 3 and 0 < pi < npar - 1
              and not re.match(r'^\s*(However|But|Yet|Moreover|Furthermore|In (summary|short|contrast)'
                               r'|Finally|First|Second|Third|Thus|Therefore|Hence|Notably|Importantly|'
                               r'Nevertheless|Nonetheless|Conversely|Indeed|Overall|Together|Here)\b', p)):
            hits.append({"paragraph_idx": pi, "words": wc, "match": "single-sentence paragraph",
                         "sentence": clip_text(p, 100), "approximate": True,
                         "note": "lone single-sentence paragraph mid-body - fold into a neighbor or give it an arc"})
    return hits

def find_pseudo_suffix(text):
    """TELL: a manufactured '-wise' / '-ize' / '-oriented' coinage or a noun pressed into a verb
    (S&W Part IV: 'the suffix -wise ... should not be used to manufacture' / 'do not ... -ize').
    PROCEDURE: use the plain word. approximate=True with a whitelist of established forms —
    only novel coinages are flagged, and even those are candidates (fields coin useful terms)."""
    hits = []
    for i, s in enumerate(split_sentences(text)):
        for m in re.finditer(r'\b(\w{3,}-?wise)\b', s, re.I):
            token = m.group(1).lower().replace("-", "")
            if token not in LEGIT_WISE:
                hits.append({"sentence_idx": i, "match": m.group(1), "sentence": clip_text(s),
                             "approximate": True, "note": "'-wise' coinage - recast ('budget-wise' -> 'as for the budget')"})
        # (general '-ize' matcher dropped — legit '-ize' verbs vastly outnumber coinages;
        # it fired on 'quantized'. Fancy '-ize' words live in FANCY_WORDS instead.)
        # (the '-based/-driven/-oriented' arm was dropped too — blind review D1: it flagged
        # standard methodology terms 'model-based', 'trait-based', 'agent-based',
        # 'physics-based', 'evidence-based', 'gradient-based' as "cuttable padding". Only
        # '-oriented' remains, the one arm S&W actually singles out, and only as a candidate.)
        for m in re.finditer(r'\b(\w+-oriented)\b', s, re.I):
            hits.append({"sentence_idx": i, "match": m.group(1), "sentence": clip_text(s),
                         "approximate": True, "note": "'-oriented' compound - often cuttable; keep if it names a real distinction"})
    return hits

def find_scare_quotes(text):
    """TELL: a single word or short phrase in quotation marks that is not attributed speech or
    a defined term - using quotes to apologize for or wink at a word choice (S&W: 'do not use
    quotation marks around a word ... to indicate that you are using it in a special sense').
    PROCEDURE: commit to the word or replace it. approximate=True - in science, quoted spans
    are often gene names, defined terms, or verbatim labels; the note says 'if not a term'."""
    hits = []
    # short quoted spans: 1-3 words inside straight or curly double quotes
    q = re.compile(r'[\u201c"]([\w][\w\s\-]{0,30}?)[\u201d"]')
    # speech/definition context that legitimizes quotation marks. 'as' is narrowed to
    # 'known as' / 'such as' / 'referred to as' / 'defined as' — a bare 'as' guard was too
    # broad (blind review D5).
    speech_verb = re.compile(r'\b(said|says|wrote|writes|called|calls?|term(s|ed)?|labell?ed|'
                             r'(known|such|defined|referred to)\s+as|so-called|'
                             r'defin(e|es|ed|ing)|denote[sd]?|mean(s|t)?|'
                             r'refer(s|red)? to|quote[sd]?)', re.I)
    for i, s in enumerate(split_sentences(text)):
        for m in q.finditer(s):
            inner = m.group(1).strip()
            nwords = len(inner.split())
            is_label = bool(re.fullmatch(r'[A-Z0-9][A-Za-z0-9\-]*', inner)) and any(c.isdigit() or c.isupper() for c in inner[1:] or inner)
            if 1 <= nwords <= 3 and not is_label and not speech_verb.search(s):
                hits.append({"sentence_idx": i, "match": '"' + clip_text(inner, 30) + '"',
                             "sentence": clip_text(s), "approximate": True,
                             "note": "scare quotes - commit to the word or replace it (ignore if it's a defined term/label)"})
    return hits


# ============================================================================ BAD-WRITING-TICS DETECTORS
# Mined from the Bad-Writing Tics register (BWT-001..009); each lexicon seeded VERBATIM from
# the register's what_happened quotes. Same candidate-flagger contract as above: surface the
# suspect + reason, the agent disposes, nothing auto-edits. POS-free heuristics are flagged
# approximate=True like their neighbors; severity, where the hit dict has no field for it, is
# carried in the note. (The BWT-002 augment lives in find_flourish_triad, BWT-009 in
# find_apologetic_contrast, BWT-003 in find_noun_trains, BWT-008 in find_empty_amplifiers above.)

# BWT-005 code/model-workflow idioms used FIGURATIVELY in science prose (the largest detector
# gap: absent from both kernels before this). Lexicon seeded VERBATIM from the register's
# detection cue list. Inflections (collapse->collapses) are handled by the suffix group in-func.
CODE_METAPHOR_WORDS = {"foil", "gate", "branch", "loop", "cascade", "pipeline", "scaffold", "collapse"}
# A sentence genuinely ABOUT real software/model machinery is NOT the tic: these markers
# suppress that whole sentence's hits so "a staged Bayesian pipeline" / "an orchestration gate"
# / a real Makefile-or-DAG sentence never fire. The same words correctly name real software.
CODE_MACHINERY_MARKERS = {"bayesian", "mcmc", "markov", "stan", "brms", "posterior", "sampler",
    "code", "codebase", "script", "software", "compiler", "compile", "makefile", "dag",
    "repository", "git", "commit", "orchestration", "orchestrator", "container", "docker",
    "api", "sql", "database", "algorithm", "runtime", "workflow", "module"}
# HIGH-PRECISION FIRING (replaces the old fire-on-bare-PRESENCE arm, which flagged ~93% of
# realistic ecology prose: "trophic cascade" / "tree branch" / "feedback loop" carry a
# code-metaphor WORD but are the correct domain term, not the tic). A bare code word counts as
# the FIGURATIVE tic ONLY when the sentence is in a MODELING / FORMAL-ARGUMENT register,
# evidenced by EITHER a modeling/inference CUE word (below) OR a formal LABELLED identifier (a
# capital + 1-3 digits: G7, S3 - the gate/step/node labels of a decision procedure). With no
# such evidence the same word is presumed to name a real object in its home domain - an
# ecological structure OR real software ("the CI pipeline", "for loop") - and stays quiet.
CODE_METAPHOR_CONTEXT_CUES = {"gradient", "gradients", "coefficient", "coefficients",
    "parameter", "parameters", "derivative", "derivatives", "eigenvalue", "eigenvalues",
    "confirm", "confirms", "confirmed", "refute", "refutes", "refuted", "premise",
    "predicate", "lemma", "theorem", "corollary"}
# pattern SOURCEs are module-level literal strings (sidecar-gate safe); compiled lazily in-func.
CODE_METAPHOR_WALK_SRC = r'\bwalk(s|ed|ing)?\b[^.]{0,60}\b(link|path)\b'
# a formal labelled identifier: a capital immediately followed by 1-3 digits (G7, S3, T10) -
# the node/gate/step labels of a decision procedure, absent from ordinary domain prose.
CODE_METAPHOR_LABEL_SRC = r'\b[A-Z]\d{1,3}\b'

# BWT-006 recurrent figurative mannerism, built as a small EXTENSIBLE list (data, not code):
# each entry is (name, pattern_src, note); append a new (name, src, note) tuple to grow it.
# Seed = "reading" a spatial pattern (gradient/axis/distribution/layer). P2 broadening (§6.3 cls-14):
# the anchor group now also carries the VERB forms of "distribute"/"organize"/"arrange" so the
# figurative "reading how organisms are distributed" (atom 14.2, "distributed" != the noun
# "distribution") fires. §6.3 FLAG: this recovers 14.2 ONLY; 14.5-14.7 (interpretation-noun "reading"
# with NO spatial anchor) are adjudicated judgment-tier and are deliberately NOT chased with regex.
FIGURATIVE_MANNERISMS = [
    ("reading-spatial",
     r'\bread(s|ing)?\b[^.]{0,80}?(\b(?:along|across)\b|\b(?:gradient|axis|distribution|distribute[sd]?|'
     r'distributing|organi[sz]e[ds]?|organi[sz]ing|arranged?|arrayed|scattered|spread\s+(?:along|across|over)|'
     r'layer|transect|cline)\b)',
     "figurative 'read/reading' applied to a spatial pattern (gradient/axis/distribution) - "
     "use a plain verb (measure, map, describe how X varies); low-medium severity"),
]

# BWT-004 absolute / superlative quantifiers, seeded VERBATIM. LOW severity, SURFACE-only:
# whether the design licenses the absolute is an EVIDENCE-FIT judgment REDIRECTED to the
# formal-argument-checker; this detector does NOT adjudicate design. P2 SPLIT (§6.1/§6.3):
# novelty boasts move to their own detector find_novelty_claims (the "first study to" family is a
# PATTERN, not a phrase-list, so "first to" is dropped from this strength lexicon and owned there).
ABSOLUTE_QUANTIFIERS = {"barely", "never", "always", "decoupled", "none"}

# ---- P2 absolute-strength ADDITIONS (§6.3 cls-12 + round-2 form-shift) ----
# near-X absolutes (12.1 "near-pure turnover"); pattern SRC compiled lazily in-func.
NEAR_ABSOLUTE_SRC = (r'\bnear-(pure|complete|total|perfect|zero|identical|universal|constant|uniform|'
                     r'infinite|maximal|optimal)\b')
# 12.2 "left untouched" — HIGH FP (common literal methods phrase). GUARDED: suppressed when a
# concrete sample/methods noun precedes it ("plots were left untouched" = literal), else surfaced.
LEFT_UNTOUCHED_SRC = r'\bleft\s+(?:it\s+|them\s+|these\s+|those\s+|the\s+\w+\s+|entirely\s+|wholly\s+)?untouched\b'
UNTOUCHED_LITERAL_MARKERS = {"plot", "plots", "sample", "samples", "control", "controls", "soil",
    "site", "sites", "core", "cores", "replicate", "replicates", "treatment", "treatments",
    "subplot", "subplots", "quadrat", "quadrats", "specimen", "specimens", "tissue", "leaf",
    "leaves", "root", "roots", "area", "areas", "region", "regions", "surface", "surfaces"}
# B5 resultative / verb-form absolutes (round-2: "avoids" outside the 6-token lexicon measured SILENT).
# A completeness VERB asserting an absolute outcome, in an UNHEDGED claim. LOW severity, candidate-only.
ABSOLUTE_VERBS = {"avoids", "avoid", "avoided", "prevents", "prevent", "prevented", "eliminates",
    "eliminate", "eliminated", "ensures", "ensure", "ensured", "guarantees", "guarantee",
    "guaranteed", "precludes", "preclude", "precluded"}   # 'remove*' dropped - too common as a plain action verb (FP)
ABSOLUTE_VERB_PHRASE_SRC = r'\bnever\s+fails?\b|\balways\s+works?\b|\bkeeps?\s+\w+\s+from\b'
# hedge markers that DOWNGRADE a claim out of absolute-verb reach (if present, the verb is not an
# unhedged absolute). Kept small so the arm stays LOW-FP but does not nag hedged prose.
CLAIM_HEDGES = {"may", "might", "can", "could", "would", "often", "usually", "sometimes", "tend",
    "tends", "typically", "generally", "largely", "mostly", "partly", "partially", "approximately",
    "roughly", "somewhat", "occasionally", "tends", "help", "helps", "aims", "tries"}

# ---- P2 novelty-boast PATTERN (§6.3 cls-11: a PATTERN, not "first study to" whack-a-mole) ----
# Catches 11.1 "To our knowledge this is the first study to…" via the boast FRAME, and its siblings
# ("first report/paper/investigation to", "for the first time", "the first to VERB"). LOW severity.
NOVELTY_SRC = (
    r'\bto\s+(?:the\s+best\s+of\s+)?(?:our|my)\s+knowledge\b'
    r'|\bthe\s+first\s+(?:\w+\s+){0,2}?(?:study|report|paper|investigation|work|analysis|attempt|'
    r'demonstration|effort|account|examination|assessment)\s+to\b'
    r'|\bfor\s+the\s+first\s+time\b'
    r'|\bthe\s+first\s+to\s+\w+'
    r'|\bhas\s+(?:never|not)\s+(?:before\s+)?been\s+(?:\w+\s+){0,2}?(?:studied|reported|examined|measured|described)\b'
)

# ---- PART B2: pseudo-explanation (user-31) — two closed, near-zero-FP lexicons (S5 §3(a)) ----
# 31b STAGE DIRECTION: sentence-initial imperative narrating the reading act + reading-act metadiscourse.
# Atoms: C03 "Strip it to one sentence:", C08 "Hold that thought —".
STAGE_DIRECTION_SRC = (
    r'^\s*(?:strip\s+it\b|read\s+the\b|read\s+it\b|look\s+again\b|follow\s+the\b|notice\s+(?:the|how|that)\b|'
    r'recall\s+that\b|return,?\s+(?:finally,?\s+)?to\b|hold\s+that\s+thought\b|here\s+they\s+are\b|'
    r'picture\s+(?:the|a|this)\b|imagine\s+(?:the|a|that)\b|think\s+of\b|bear\s+in\s+mind\b|'
    r'keep\s+in\s+mind\b|consider\s+(?:the|how|a|again)\b|note\s+(?:that|how)\b|see\s+(?:the|how)\b|'
    r'walk\s+(?:the|through)\b)')
STAGE_DIRECTION_PHRASE_SRC = (r'\bhold\s+that\s+thought\b|\bworth\s+telling\s+apart\b|'
    r'\bas\s+noted\s+earlier\b|\bas\s+(?:we\s+)?(?:noted|mentioned|saw|said)\s+(?:earlier|above|before)\b')
# 31a GENERIC-PEDAGOGY claim: a content-free generalization about learning/understanding (BOUNDARY,
# S5 C19: reader-address is NOT the defect; only a generic generalization about learning is).
# Atoms: C04 "In learning a system, one steady name…", C18 "…knowing the limits of an idea is part
# of understanding it." Tight patterns => near-zero FP.
PEDAGOGY_SRC = (
    r'^\s*in\s+learning\s+(?:a|an|any|the)\b'
    r'|^\s*in\s+understanding\s+(?:a|an|any|the)\b'
    r'|\bknowing\s+.{1,60}?\bis\s+part\s+of\s+(?:understanding|learning|knowing)\b'
    r'|\bunderstanding\s+.{1,50}?\bis\s+part\s+of\s+(?:knowing|learning)\b')

# ---- PART B4: metaphor-lexicon widening (BWT-005 sibling) — organic/mechanical vehicle nouns ----
# The shipped code-metaphor detector saw NONE of a real draft's heartbeat/trap-door/release-valve load
# (measured 0 hits). These are candidate-only, gated to suppress obvious LITERAL uses. Vehicle-test note.
VEHICLE_METAPHOR_SRC = (r'\bheartbeat\b|\btrap\s?doors?\b|\brelease\s+valves?\b|\bsafety\s+valves?\b|'
    r'\bpressure\s+valves?\b|\blifeblood\b|\bnerve\s+cent(?:er|re)\b')   # focused on the MEASURED escapees; 'backbone'/'linchpin' dropped (near-dead metaphors, higher FP)
# literal-context markers that suppress a vehicle-metaphor fire (the sentence is really about the organ/part).
VEHICLE_LITERAL_MARKERS = {"cardiac", "cardio", "pulse", "ecg", "bpm", "arrhythmia", "atrium",
    "ventricle", "hinge", "cellar", "attic", "plumbing", "pipe", "boiler", "vertebra", "vertebrae",
    "spine", "spinal", "anatomy", "anatomical"}
# STRONG code words (rarely a home-domain object) — used to TUNE the gradient-only co-fire (§ item 4):
# when the ONLY formal-register cue matched is the ambiguous ecology word "gradient(s)" AND there is no
# labelled identifier, fire only for a STRONG code word; a WEAK one ("cascade"/"branch"/"loop") in pure
# ecology prose ("trophic cascade along the gradient") then stays quiet (the known ecology FP).
STRONG_CODE_WORDS = {"foil", "scaffold", "pipeline"}

# ---- PART B1: term_drift — anchor-term registry + drift + definition-to-first-use distance ----
# Default synonym GROUPS (one referent per group) used when NO caller list is supplied AND the document
# is a workflow doc (context-gated so general science prose does not false-positive). Seeded from the
# MEASURED round-1 census (wave 23 / loop 19 / cycle 7 / turn 3 / round 1 = five names for one unit).
DEFAULT_SYNONYM_GROUPS = [
    ["wave", "loop", "cycle", "turn", "round", "iteration", "pass"],
    ["subagent", "subagents", "sub-agent", "sub-agents", "agent", "agents", "worker", "workers", "child", "children"],
    ["planner", "orchestrator", "coordinator", "conductor", "supervisor"],
    ["durable file", "durable files", "persistent file", "persistent files", "artifact", "artifacts", "durable output", "durable outputs"],
]
WORKFLOW_CONTEXT_MARKERS = {"planner", "subagent", "subagents", "workflow", "cascade", "dispatch",
    "orchestrat", "collect", "supervised loop"}
# P2c (per P2v): fold singular/plural surface forms of ONE lemma so a term used in both numbers
# ('subagent' x49 / 'subagents' x10) counts as ONE name, not two competing names (a term-drift FP).
# Only grammatical NUMBER is folded; hyphenation/word-choice is preserved ('sub-agent' stays distinct
# from 'subagent'), so genuine elegant-variation still registers as drift.
PLURAL_IRREGULARS = {"children": "child", "analyses": "analysis", "indices": "index",
    "matrices": "matrix", "vertices": "vertex", "criteria": "criterion", "phenomena": "phenomenon"}
def singular_lemma(term):
    t = term.lower().strip()
    if t in PLURAL_IRREGULARS:
        return PLURAL_IRREGULARS[t]
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    if t.endswith("es") and len(t) > 3 and t[-3] in "sxzo":
        return t[:-2]
    if t.endswith("s") and not t.endswith("ss") and len(t) > 3:
        return t[:-1]
    return t

# ---- P2 item 3: BWT-007 over-correction, COMPARISON-ONLY (before vs after) — cautious tier ----
# Hedges a de-jargon pass may have STRIPPED (BWT-007 over-correction: a legitimate hedge cut as if jargon).
OVERCORR_HEDGES = {"may", "might", "could", "can", "possibly", "likely", "probably", "perhaps",
    "apparently", "suggests", "suggest", "appears", "appear", "seems", "seem", "tend", "tends",
    "often", "generally", "typically", "usually", "potentially", "approximately", "roughly",
    "about", "around", "some", "partial", "partially", "provisional", "provisionally", "relatively",
    "somewhat", "largely", "mostly", "presumably", "plausibly"}


def find_code_metaphor_leakage(text):
    """TELL: a code/model-workflow idiom (foil, gate, branch, loop, cascade, pipeline,
    scaffold, collapse, 'walk the ... link/path') used FIGURATIVELY in science prose (Bad-Writing
    register BWT-005). PROCEDURE: restate the idea in the reader's own domain vocabulary; keep
    the term only when it names actual software/model machinery. CANDIDATE ONLY, approximate=True.
    MECHANISM (high-precision, replaces an earlier fire-on-bare-PRESENCE arm that flagged ~93% of
    realistic ecology sentences): a bare code WORD is flagged ONLY when the sentence carries
    formal-register evidence - EITHER a modeling/inference CUE (CODE_METAPHOR_CONTEXT_CUES:
    gradient, coefficient, confirm, theorem, ...) OR a formal LABELLED identifier (a capital +
    1-3 digits: G7, S3). With no such evidence the same word is presumed to name a real object in
    its home domain, so ordinary ecology prose ('trophic cascade', 'tree branch', 'feedback
    loop') AND ordinary code prose ('the CI pipeline', 'for loop') do NOT fire. The 'walk the ...
    link/path' idiom is specific enough to fire on its own. A sentence carrying a real-machinery
    marker (Bayesian, MCMC, Makefile, DAG, orchestration, ...) is suppressed wholesale. RESIDUAL
    (accepted): a bare figurative use with NO register cue is now missed (lower recall by design),
    and a cue that is also a common domain word ('gradient') can still co-fire when domain prose
    pairs it with a code word."""
    hits = []
    word_pat = re.compile(r'\b(' + '|'.join(sorted(CODE_METAPHOR_WORDS, key=len, reverse=True)) + r')(?:s|es|ed|ing|d)?\b', re.I)
    walk_pat = re.compile(CODE_METAPHOR_WALK_SRC, re.I)
    machinery_pat = re.compile(r'\b(' + '|'.join(sorted(CODE_MACHINERY_MARKERS, key=len, reverse=True)) + r')\b', re.I)
    cue_pat = re.compile(r'\b(' + '|'.join(sorted(CODE_METAPHOR_CONTEXT_CUES, key=len, reverse=True)) + r')\b', re.I)
    label_pat = re.compile(CODE_METAPHOR_LABEL_SRC)
    vehicle_pat = re.compile(VEHICLE_METAPHOR_SRC, re.I)
    for i, s in enumerate(split_sentences(text)):
        # PART B4: organic/mechanical vehicle-metaphor arm - runs INDEPENDENT of the machinery gate (a
        # vehicle noun like 'heartbeat' is not real machinery even when the sentence also names a
        # workflow/system, which the machinery gate would otherwise suppress). Suppressed only by a clear
        # LITERAL marker (cardiac / hinge / plumbing / spinal ...).
        sl = set(w.lower() for w in words_of(s))
        if not (sl & VEHICLE_LITERAL_MARKERS):
            for m in vehicle_pat.finditer(s):
                hits.append({"sentence_idx": i, "match": clip_text(m.group(0), 40), "kind": "vehicle-metaphor",
                             "sentence": clip_text(s), "approximate": True,
                             "note": "organic/mechanical metaphor vehicle in formal prose - VEHICLE TEST: state "
                                     "the literal proposition it asserts; if false/circular/empty, recast "
                                     "(candidate; keep only a vehicle the reader shares)"})
        if machinery_pat.search(s):
            continue   # a sentence about real machinery - not the code-word/walk tic
        cue_hits = set(c.lower() for c in cue_pat.findall(s))
        has_label = bool(label_pat.search(s))
        # § item 4 TUNE (the known ecology FP): when the ONLY formal-register cue matched is the ambiguous
        # ecology word 'gradient(s)' AND there is no labelled identifier, require a STRONG code word - so a
        # WEAK code word in pure ecology prose ('trophic cascade along the gradient') stays quiet, while the
        # modeling atoms 6.2/13.2 ('foil ... gradient', foil=strong) and 13.3 (has label G7 + cue 'confirm')
        # still fire.
        gradient_only = bool(cue_hits) and cue_hits <= {"gradient", "gradients"} and not has_label
        if cue_hits or has_label:   # formal-register evidence required
            seen = set()
            for m in word_pat.finditer(s):
                tok = m.group(0).lower()
                if tok in seen:
                    continue
                seen.add(tok)
                if gradient_only and not any(tok.startswith(w) for w in STRONG_CODE_WORDS):
                    continue   # weak code word + gradient-only cue + no label => presumed ecology, suppress
                hits.append({"sentence_idx": i, "match": m.group(0), "kind": "code-word",
                             "sentence": clip_text(s), "approximate": True,
                             "note": "code/model idiom used figuratively in a modeling/argument "
                                     "sentence - restate in the reader's domain vocabulary "
                                     "(candidate; the same word can name a real object)"})
        wm = walk_pat.search(s)
        if wm:
            hits.append({"sentence_idx": i, "match": clip_text(wm.group(0), 50), "kind": "walk-idiom",
                         "sentence": clip_text(s), "approximate": True,
                         "note": "'walk the ... link/path' code/loop idiom in science prose - "
                                 "describe the actual traversal plainly (candidate)"})
    return hits


def find_figurative_mannerism(text):
    """TELL: a recurrent figurative verbal mannerism (Bad-Writing register BWT-006), seeded
    with 'reading' a spatial pattern ('reading how organisms are distributed along that axis').
    PROCEDURE: use a plain verb that names the operation (measure, map, describe how X varies);
    when a mannerism is flagged, remove EVERY instance, not only the quoted one. Driven by the
    EXTENSIBLE FIGURATIVE_MANNERISMS data list so new mannerisms append as data, not code.
    approximate=True; low-medium severity, candidate-only."""
    hits = []
    for name, src, note in FIGURATIVE_MANNERISMS:
        pat = re.compile(src, re.I)
        for i, s in enumerate(split_sentences(text)):
            m = pat.search(s)
            if m:
                hits.append({"sentence_idx": i, "match": clip_text(m.group(0), 60), "kind": name,
                             "sentence": clip_text(s), "approximate": True, "note": note})
    return hits


def find_absolute_quantifiers(text):
    """TELL: an absolute/superlative quantifier attached to a claim (BWT-004, overclaim). SURFACE-only;
    the evidence-fit judgment is REDIRECTED to the formal-argument-checker. LOW severity, candidate-only.
    P2 arms (§6.3 cls-12 + round-2 form-shift):
      - the strength lexicon {barely, never, always, decoupled, none} (novelty boasts moved to find_novelty_claims)
      - near-X absolutes ('near-pure turnover', 12.1)
      - 'left untouched' (12.2) - GUARDED: suppressed when a concrete sample/methods noun precedes it
        ('plots were left untouched' = literal), else surfaced (HIGH FP - a common literal methods phrase)
      - B5 resultative/verb-form absolutes ('avoids', 'eliminates', 'guarantees', 'never fails') in an
        UNHEDGED claim - the round-2 form-shift the 6-token quantifier lexicon could not see"""
    hits = []
    pat  = re.compile(r'\b(' + '|'.join(sorted(ABSOLUTE_QUANTIFIERS, key=len, reverse=True)) + r')\b', re.I)
    near = re.compile(NEAR_ABSOLUTE_SRC, re.I)
    left = re.compile(LEFT_UNTOUCHED_SRC, re.I)
    vpat = re.compile(r'\b(' + '|'.join(sorted(ABSOLUTE_VERBS, key=len, reverse=True)) + r')\b', re.I)
    vphr = re.compile(ABSOLUTE_VERB_PHRASE_SRC, re.I)
    for i, s in enumerate(split_sentences(text)):
        wl = set(w.lower() for w in words_of(s))
        for m in pat.finditer(s):
            hits.append({"sentence_idx": i, "match": m.group(0), "kind": "quantifier", "sentence": clip_text(s),
                         "note": "LOW severity: surface absolute quantifier - confirm the design supports it; "
                                 "the evidence-fit judgment is the formal-argument-checker's, not this detector's"})
        for m in near.finditer(s):
            hits.append({"sentence_idx": i, "match": m.group(0), "kind": "near-absolute", "sentence": clip_text(s),
                         "note": "LOW severity: 'near-X' absolute - confirm the result supports it (surface-only)"})
        for m in left.finditer(s):
            pre = s[max(0, m.start() - 32):m.start()].lower()
            if any(re.search(r'\b' + w + r'\b', pre) for w in UNTOUCHED_LITERAL_MARKERS):
                continue   # literal methods description ('plots were left untouched') - not an overclaim
            hits.append({"sentence_idx": i, "match": m.group(0), "kind": "left-untouched", "sentence": clip_text(s),
                         "note": "LOW severity: 'left untouched' absolute - confirm it is not a literal methods "
                                 "description ('plots were left untouched'); surface-only, evidence-fit redirected"})
        if not (wl & CLAIM_HEDGES):   # B5 verb-absolutes fire only in an UNHEDGED claim
            for m in vpat.finditer(s):
                hits.append({"sentence_idx": i, "match": m.group(0), "kind": "verb-absolute", "sentence": clip_text(s),
                             "note": "LOW severity: resultative/verb-form absolute ('" + m.group(0).lower() +
                                     "') asserts a complete outcome - confirm the design supports the absolute "
                                     "(surface-only; a hedged form would not fire)"})
            for m in vphr.finditer(s):
                hits.append({"sentence_idx": i, "match": m.group(0), "kind": "verb-absolute", "sentence": clip_text(s),
                             "note": "LOW severity: absolute claim phrase - confirm the design supports it"})
    return hits


def find_novelty_claims(text):
    """TELL (BWT-004 novelty boast, SPLIT out per §6.1 cls-11 / §6.3): a novelty/priority boast, caught by
    a PATTERN (not a 'first study to' phrase list): 'to (the best of) our knowledge', 'the first
    STUDY/REPORT/PAPER/... to', 'for the first time', 'the first to VERB', 'has never been STUDIED'.
    Catches 11.1 'To our knowledge this is the first study to…'. LOW severity, candidate-only; whether
    it is genuinely first is the formal-argument-checker's judgment, not this detector's."""
    hits = []
    pat = re.compile(NOVELTY_SRC, re.I)
    # P2c guard (per P2v): the bare 'for the first time' arm also matches TEMPORAL non-boasts
    # ('For the first time in three seasons, the lake froze over.'). Gate ONLY that arm on a research-claim
    # cue (study/show/report/demonstrate family, or first-person 'we/our') in the same sentence; the other
    # arms carry their own boast frame ('to our knowledge', 'the first STUDY to', ...) and are unaffected.
    first_time = re.compile(r'\bfor\s+the\s+first\s+time\b', re.I)
    claim_cue = re.compile(
        r'\b(we|our|stud(?:y|ies|ied)|shows?|showed|shown|reports?|reported|'
        r'demonstrates?|demonstrated|presents?|presented|documents?|documented|'
        r'describes?|described|reveals?|revealed|establishe?s?|established|records?|'
        r'recorded|observes?|observed|measures?|measured|finds?|found|identif(?:y|ies|ied))\b', re.I)
    seen = set()
    for i, s in enumerate(split_sentences(text)):
        has_claim_cue = bool(claim_cue.search(s))
        for m in pat.finditer(s):
            key = (i, m.start())
            if key in seen:
                continue
            if first_time.fullmatch(m.group(0)) and not has_claim_cue:
                continue  # temporal 'for the first time' with no claim cue -> not a novelty boast
            seen.add(key)
            hits.append({"sentence_idx": i, "match": clip_text(m.group(0), 50), "sentence": clip_text(s),
                         "note": "LOW severity: novelty/priority boast - ground it or cut it; whether it is "
                                 "genuinely first is the formal-argument-checker's judgment, not this detector's"})
    return hits


def find_term_drift(text, anchors=None):
    """TELL (PART B1, user-26 elegant-variation + user-32 premature-definition): the document uses MULTIPLE
    near-synonym names for ONE referent (drift), and/or DEFINES a term far before it is first used. Two
    CANDIDATE-ONLY arms:
      - DRIFT: for each synonym GROUP (caller-supplied `anchors`, else a built-in workflow-term default
        GATED on workflow context so general science prose does not false-positive), if >=2 members occur
        (one more than once), surface the competing names + counts + per-1000-word rate. The measured
        round-1 signal was wave 23 / loop 19 / cycle 7 = five names for one unit (71% of style edits).
      - DEFINITION-TO-FIRST-USE DISTANCE (user-32): for each DECLARED term (a bold **T** or a caller anchor),
        if its definition sentence precedes its first WORKING use by > 10 sentences, flag premature definition.
    Registry: the document's own bold **term** spans (+ optional caller `anchors`). NOTE: a general
    near-synonym drift signal needs a glossary (hence the caller/default groups); definition-distance is
    fully mechanical. approximate=True."""
    hits = []
    bold = [b.strip().lower() for b in re.findall(r'\*\*([^*\n]{2,40}?)\*\*', text)]
    bold = [b for b in bold if re.search(r'[a-z]', b) and not b.replace(' ', '').isdigit()]
    clean = re.sub(r'\*\*|__', '', text)          # drop bold markers so 'T is' adjacency survives
    sents = split_sentences(clean)
    low = clean.lower()
    nwords = len(words_of(clean)) or 1
    # ---- DRIFT arm ----
    groups = [list(g) for g in anchors] if anchors else []
    if not groups and sum(1 for mk in WORKFLOW_CONTEXT_MARKERS if mk in low) >= 2:
        groups = DEFAULT_SYNONYM_GROUPS
    for g in groups:
        present = {}
        for term in g:
            n = len(re.findall(r'\b' + re.escape(term.lower()) + r'\b', low))
            if n:
                present[term] = n
        # P2c (per P2v): fold singular/plural of one lemma into a single name (shortest surface form as
        # representative, counts summed) so 'subagent'/'subagents' is not miscounted as two competing names.
        folded = {}
        for term, n in present.items():
            lem = singular_lemma(term)
            if lem not in folded:
                folded[lem] = {"rep": term, "n": 0}
            folded[lem]["n"] += n
            if len(term) < len(folded[lem]["rep"]):
                folded[lem]["rep"] = term
        present = {info["rep"]: info["n"] for info in folded.values()}
        if len(present) >= 2 and max(present.values()) >= 2:
            ordered = sorted(present.items(), key=lambda kv: -kv[1])
            rates = {t: round(1000.0 * n / nwords, 2) for t, n in present.items()}
            hits.append({"kind": "term-drift",
                         "match": ", ".join("%s x%d" % (t, n) for t, n in ordered),
                         "group": sorted(present), "counts": dict(present), "per_1000_words": rates,
                         "note": "CANDIDATE (user-26): %d competing names for one referent (%s) - pick ONE "
                                 "steady name and use it throughout (elegant variation confuses a reader)"
                                 % (len(present), ", ".join("'%s' x%d" % (t, n) for t, n in ordered))})
    # ---- DEFINITION-TO-FIRST-USE DISTANCE arm (user-32) ----
    reg_terms = set(bold)
    if anchors:
        for g in anchors:
            reg_terms.update(t.lower() for t in g)
    for term in sorted(reg_terms):
        if len(term) < 3:
            continue
        et = re.escape(term)
        tpat = re.compile(r'\b' + et + r'\b', re.I)
        def_idx = use_idx = None
        for idx, s in enumerate(sents):
            if not tpat.search(s):
                continue
            is_def = bool(
                re.search(r'\b' + et + r'\b\s*(?:is|are|means?|refers?\s+to|:)\b', s, re.I)
                or re.search(r'\b(?:a|an|the)\s+' + et + r'\b\s+(?:is|are|means?)\b', s, re.I)
                or re.search(et + r"\b[^.]*\bthis\s+guide'?s?\s+word\s+for\b", s, re.I)
                or re.search(r'\b(?:hereafter|call(?:ed)?|term(?:ed)?|defin(?:e|ed|es))\b[^.]{0,40}\b' + et + r'\b', s, re.I))
            if is_def and def_idx is None:
                def_idx = idx
            elif (not is_def) and use_idx is None and def_idx is not None:
                use_idx = idx
                break
        if def_idx is not None and use_idx is not None and (use_idx - def_idx) > 10:
            hits.append({"kind": "premature-definition", "match": term, "term": term,
                         "def_sentence_idx": def_idx, "first_use_sentence_idx": use_idx,
                         "distance": use_idx - def_idx, "sentence": clip_text(sents[def_idx]),
                         "note": "CANDIDATE (user-32): '%s' is DEFINED %d sentences before its first working "
                                 "use - move the definition to first use, or delete it if the term goes unused"
                                 % (term, use_idx - def_idx)})
    return hits


def find_pseudo_explanation(text):
    """TELL (PART B2, user-31): a sentence whose claim is about the ACT of explaining/learning or about the
    document's own procedure, not about the subject matter (it stays true if the subject is swapped out).
    Two closed, near-zero-FP arms (S5 §3(a)):
      - 31b STAGE DIRECTION: a sentence-initial imperative narrating the reading act ('Strip it to one
        sentence:', 'Hold that thought') + reading-act metadiscourse ('as noted earlier', 'worth telling apart')
      - 31a GENERIC-PEDAGOGY claim: a content-free generalization about learning/understanding ('In learning
        a system...', 'knowing X is part of understanding Y'). BOUNDARY (S5 C19): reader-address is NOT the
        defect; only a generic generalization about learning is.
    CANDIDATE ONLY, LOW severity. approximate=True."""
    hits = []
    stage  = re.compile(STAGE_DIRECTION_SRC, re.I)
    stagep = re.compile(STAGE_DIRECTION_PHRASE_SRC, re.I)
    ped    = re.compile(PEDAGOGY_SRC, re.I)
    for i, s in enumerate(split_sentences(text)):
        m = stage.search(s) or stagep.search(s)
        if m:
            hits.append({"sentence_idx": i, "match": clip_text(m.group(0), 40), "kind": "stage-direction",
                         "sentence": clip_text(s), "approximate": True,
                         "note": "LOW severity (user-31b): stage direction narrating the reading act - cut it "
                                 "or replace with the fact it stands in for (candidate)"})
        m = ped.search(s)
        if m:
            hits.append({"sentence_idx": i, "match": clip_text(m.group(0), 40), "kind": "generic-pedagogy",
                         "sentence": clip_text(s), "approximate": True,
                         "note": "LOW severity (user-31a): content-free generalization about learning/understanding "
                                 "- swap-the-subject test: if it stays true for a tax code, cut it (candidate)"})
    return hits


def find_em_dashes(text, threshold=2):
    """TELL (PART B3, user-9 em-dash piling): a sentence carrying >= threshold (default 2) em-dashes - aside
    stacked on aside. PROMOTED from profile-only (punctuation_density still reports the raw total) to a
    thresholded detector WITH A HIT LIST, because C01 ('too many em dashes') survived a full de-tic sweep
    with 54 em-dashes when nothing was ever asked to FIRE (no threshold existed). Also reports the document
    em-dash rate per 1000 words. PROCEDURE: convert some dashes to commas/periods, or recast. CANDIDATE."""
    hits = []
    total = len(re.findall(r'—|--', text))
    nwords = len(words_of(text)) or 1
    rate = round(1000.0 * total / nwords, 1)
    for i, s in enumerate(split_sentences(text)):
        n = len(re.findall(r'—|--', s))
        if n >= threshold:
            hits.append({"sentence_idx": i, "n_dashes": n, "match": "%d em-dashes" % n,
                         "sentence": clip_text(s), "doc_rate_per_1000w": rate,
                         "note": "CANDIDATE: %d em-dashes in one sentence (>= %d) - aside pile-up; convert some "
                                 "to commas/periods or recast (document em-dash rate %s/1000 words)"
                                 % (n, threshold, rate)})
    return hits


def find_overcorrection(before_text, after_text):
    """PART A item 3 (BWT-007 over-correction, COMPARISON-ONLY): compare a BEFORE draft to an AFTER draft and
    surface candidates a de-jargon pass may have wrongly STRIPPED - legitimate hedges removed, and
    field-standard-looking terms removed. CAUTIOUS tier (candidate-only; BWT-007 is a reasoning tic, so this
    only surfaces suspects to judge against the TARGET reader). Invoked as a plain callable —
    `ws.find_overcorrection(before, after)` on the auto-loaded kernel; it is NOT a per-draft
    detector and is deliberately absent from detector_map()."""
    def htoks(t):
        return [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'\-]+", t)]
    bc, ac = Counter(htoks(before_text)), Counter(htoks(after_text))
    out = {"stripped_hedges": [], "removed_field_terms": []}
    for h in sorted(OVERCORR_HEDGES):
        d = bc.get(h, 0) - ac.get(h, 0)
        if d > 0:
            out["stripped_hedges"].append({"term": h, "removed": d,
                "note": "CANDIDATE (BWT-007): hedge '%s' occurs %d fewer time(s) after - confirm a legitimate "
                        "qualification was not cut as if it were jargon" % (h, d)})
    # field-standard-looking tokens: contain greek / underscore / an internal digit / a dotted abbrev, and
    # at least one lowercase letter; present in BEFORE more than AFTER.
    field_re = re.compile(r'[Α-Ωα-ω]|_|[A-Za-z]\.[a-z]|\d')
    def ftoks(t):
        return [w.strip('.,;:()[]"“”') for w in re.findall(r'\S+', t)]
    fb, fa = Counter(ftoks(before_text)), Counter(ftoks(after_text))
    seen = set()
    for w, n in fb.items():
        wl = w.lower()
        if wl in seen or len(w) < 3 or not field_re.search(w) or not re.search(r'[a-zα-ω]', wl):
            continue
        if fa.get(w, 0) < n:
            seen.add(wl)
            out["removed_field_terms"].append({"term": w,
                "note": "CANDIDATE (BWT-007): a field-standard-looking term ('%s') was removed/reduced - keep a "
                        "term the target DOMAIN reader expects; spell out an abbreviation rather than cut it" % w})
    return out


def detector_map():
    # built lazily inside a function (module-level dict of funcs is non-literal)
        return {
    # sentence level
        "buried_verbs": find_buried_verbs,
        "trailing_qualifier": find_trailing_qualifier,
        "significance_without_effect": find_significance_without_effect,
        "metadiscourse": find_metadiscourse,
        "weak_gap_framing": find_weak_gap_framing,
        "undermining_resolution": find_undermining_resolution,
        "objectives_not_question": find_objectives_not_question,
        "bizzwidget_opening": find_bizzwidget_opening,
        "citation_position": find_citation_position,
        "repeated_words": find_repeated_words,
        "noun_trains": find_noun_trains,
    # word level
        "passive": find_passive,
        "nominalizations": find_nominalizations,
        "weak_verbs": find_weak_verbs,
        "empty_amplifiers": find_empty_amplifiers,
        "hype": find_hype,
        "prep_phrase_compounds": find_prep_phrase_compounds,
        "undefined_acronyms": find_undefined_acronyms,
        "confusables": find_confusables,
    # --- new detectors (Schimel + Strunk & White mining) ---
    # rhetorical / structural (sentence & paragraph scale)
    # P2 SPLIT of the old find_rhetorical_flourish -> three flourish hit-keys + the rather-than gate:
        "flourish_triad": find_flourish_triad,
        "flourish_epigram": find_flourish_epigram,
        "flourish_metaphor": find_flourish_metaphor,
        "apologetic_contrast": find_apologetic_contrast,
        "expletive_opener": find_expletive_opener,
        "not_positive_form": find_not_positive_form,
        "naked_this": find_naked_this,
        "giant_paragraph": find_giant_paragraph,
    # economy / diction (word scale)
        "fancy_words": find_fancy_words,
        "wordy_phrases": find_wordy_phrases,
        "misused_words": find_misused_words,
        "pseudo_suffix": find_pseudo_suffix,
        "scare_quotes": find_scare_quotes,
    # --- Bad-Writing-Tics register (BWT-005/006/004) ---
        "code_metaphor_leakage": find_code_metaphor_leakage,
        "figurative_mannerism": find_figurative_mannerism,
        "absolute_quantifiers": find_absolute_quantifiers,
        "novelty_claims": find_novelty_claims,
    # --- PART B measured checks (P2+) ---
        "term_drift": find_term_drift,
        "pseudo_explanation": find_pseudo_explanation,
        "em_dashes": find_em_dashes,
    }

def scan_draft(text, include=None, exclude=None):
    """Run every detector over a draft and return a structured report.

    Returns {counts, profile, hits}. `counts` is the tell tally (the triage view);
    `hits` maps each detector to its candidate list; `profile` carries the non-defect
    distributions (sentence length, punctuation density, verb ratio).

    This is the FIRST thing the Stylist runs on a draft - measure the draft's actual
    shape before judging it (the ported finding #10: a rule about a body of text with
    no measurement of that text is the tell). Every hit is a candidate for the agent's
    judgment, never an auto-edit.
    """
    DETECTORS = detector_map()
    names = include or list(DETECTORS)
    if exclude:
        names = [n for n in names if n not in exclude]
    text = strip_noncontent(text)   # analyse the prose stream, not markdown scaffolding
    hits = {n: DETECTORS[n](text) for n in names}
    counts = {n: len(h) for n, h in hits.items()}
    profile = {"sentence_length": sentence_length_profile(text),
               "punctuation": punctuation_density(text),
               "verb_to_word_ratio": verb_to_word_ratio(text),
               "nominalization_density": nominalization_density(text),
               "noun_train_density": noun_train_density(text),
               "n_paragraphs": len(paragraphs(text))}
    return {"counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
            "profile": profile, "hits": hits}

def report(text, top=5):
    """Human-readable triage summary: the tell tally + profile, then the top-N hits per
    fired detector. Print this, then read the specific sentences before dispositioning."""
    r = scan_draft(text)
    lines = ["# writing-science draft scan", "", "## Profile"]
    p = r["profile"]; sl = p["sentence_length"]
    lines.append(f"- sentences: {sl.get('n')}, mean {sl.get('mean')} words, max {sl.get('max')}, "
                 f"{sl.get('n_very_long')} over 55 words")
    lines.append(f"- paragraphs: {p['n_paragraphs']}")
    lines.append(f"- em-dashes: {p['punctuation']['em_dashes']}, semicolons: {p['punctuation']['semicolons']}")
    lines.append(f"- verb/word ratio: {p['verb_to_word_ratio']['ratio']} (comfortable ~0.15)")
    lines += ["", "## Tell tally (candidate flags - disposition needs your judgment)"]
    for n, c in r["counts"].items():
        if c:
            lines.append(f"- {n}: {c}")
    lines += ["", "## Top hits per tell"]
    for n, c in r["counts"].items():
        if not c:
            continue
        lines.append(f"\n### {n} ({c})")
        for h in r["hits"][n][:top]:
            mark = h.get("match") or h.get("acronym") or ""
            lines.append(f"- [{h.get('sentence_idx')}] {mark!r}: {h.get('note','')}")
            lines.append(f"    \u201c{h.get('sentence','')}\u201d")
    return "\n".join(lines)
