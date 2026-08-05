#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""fixtures_sci_file_index.py -- known-bad / known-clean fixtures for the
sci-file-index build-time gates, for the vloop verify-the-embed harness.

WHAT THE "scrub_verify" GATE ACTUALLY IS (verified by source inspection, not
docstring):
  The task refers to a "scrub_verify gate". There is NO function literally named
  scrub_verify in sci_file_index.py (that string appears only once, in a comment
  describing the *toolkit's* wikilink guard). The build-time identity validator
  is `selfcheck_identity(rows)` (def at ~L1183), called once in cmd_build (~L1156);
  an empty return renders the green surface line
  "SELF-CHECK: 0 identity disagreements". That is the gate this file fixtures as
  GATE 1 (`sci_selfcheck_identity`).

  The historical false-green -- "validator reported 0 FAIL while real defects
  existed" -- is reproduced by SELFCHECK_FALSE_GREEN_SPEC (built via
  false_green_row(), which lives in the sibling test_sci_file_index_gates.py -- not in this file): a row with a confidently-WRONG author on a CRYPTIC
  (non-well-named) filename. Because selfcheck_identity's author/title
  cross-checks only fire when wellnamed(fn) parses the filename, a cryptic
  publisher auto-name ("1-s2.0-...-main.pdf") defeats every cross-check, the row
  ships at HIGH confidence, and selfcheck returns [].
  This is a LIVE blind spot on the CURRENT module. The test file registers it as
  its own defect class in GATE 1's known_bad set, so the harness reports FALSE
  GREEN and FAILS sci_selfcheck_identity -- i.e. the blind spot is ENFORCED, not
  merely printed. The registry verdict stays FAIL until the gate is fixed to
  catch a wrong author on a cryptic filename (a module edit, out of scope here).

FLAG EMISSION IS A SEPARATE GATE (verified): `selfcheck_identity` never reads the
`notes`, `parent_file`, or `duplicate_of` columns (confirmed by inspect.getsource).
The two note stamps the task names -- `si-doi-disagrees-parent` and
`cryptic_unresolved` -- are emitted in cmd_build (the 2026-07-24 code) and consumed
by an EXTERNAL curator's I17/I18 invariants, NOT by selfcheck_identity. They are
fixtured separately as GATE 2 (`sci_flag_emission`), which drives cmd_build
end-to-end and asserts the stamp is present on the defect and absent on the clean.

Each fixture is plain data; builders here mirror the exact row/raw schemas the
real module reads. No import of the module -- the test file wires runners to it.
"""

# ---- schema of a paper_index.csv row, as selfcheck_identity reads it ----
INDEX_FIELDS = ("file_name", "record_type", "first_author", "first_author_ascii",
                "year", "title", "journal", "doi", "parent_file", "duplicate_of",
                "confidence", "notes", "pages", "content_sim")

# ---- schema of the _sfi_raw.csv row cmd_build consumes (from cmd_extract) ----
RAW_FIELDS = ("file_name", "ext", "n_pages", "chars_page1", "n_fonts",
              "embedded_title", "embedded_author", "producer", "doi", "doi_source",
              "title_src_page", "snippet", "page1_head", "content_sim")


def index_row(fold_ascii, **kw):
    """Build one index row. `fold_ascii` is the module's folder (injected by the
    test so first_author_ascii is derived exactly as cmd_build derives it)."""
    r = {f: "" for f in INDEX_FIELDS}
    r["record_type"] = "article"
    r.update(kw)
    if not r["first_author_ascii"]:
        r["first_author_ascii"] = fold_ascii(r["first_author"])
    return r


def raw_row(**kw):
    r = {f: "" for f in RAW_FIELDS}
    r["ext"] = "pdf"
    r["n_pages"] = "10"
    r.update(kw)
    return r


# ==========================================================================
# GATE 1 -- selfcheck_identity: one KNOWN-BAD per defect CLASS it claims.
# Each entry is (kwargs-for-index_row, the-defect-class-token that MUST appear
# in the emitted reasons). The test builds the row via index_row(fold_ascii,...)
# and asserts selfcheck flags it AND the class token is in the reasons string.
# ==========================================================================
# HIGH-severity classes
SELFCHECK_BAD_SPECS = {
    # title field == journal field
    "title=journal": dict(
        file_name="Jones_2018_Oecologia_Physiology.pdf",
        first_author="Jones", year="2018", journal="Oecologia",
        title="Oecologia", doi="10.1007/s00442-018-1"),
    # title made only of journal-vocabulary words
    "title=journalwords": dict(
        file_name="crypticstem-noyear.pdf",   # cryptic => no filename cross-check
        first_author="White", year="2011", journal="PNAS",
        title="Journal Proceedings Review"),
    # mojibake in author (double-encoded UTF-8) -- cryptic filename isolates it
    "author=mojibake": dict(
        file_name="10.1038_s41477abc.pdf",
        first_author="Ara\u00c3\u00bajo", year="2020", journal="Nature Plants",
        title="Canopy Water Flux Dynamics"),
    # digit inside an author token
    "author=digit": dict(
        file_name="pnas.1900abc.pdf",
        first_author="Lee2", year="2017", journal="Science",
        title="Photosynthesis Under Warming"),
    # placeholder author string
    "author=placeholder": dict(
        file_name="nph.99999.pdf",
        first_author="Anonymous", year="2015", journal="New Phytologist",
        title="Some Ecological Study"),
    # author IS a journal word
    "author=journalword": dict(
        file_name="1-s2.0-Sxxxx-main.pdf",
        first_author="Nature", year="2010", journal="Nature",
        title="A Perfectly Ordinary Article Title Here"),
    # filename author disagrees with index author (well-named filename REQUIRED)
    "author!=filename": dict(
        file_name="Kasting_1993_Science_EarlyEarthAtmosphere.pdf",
        first_author="Wilson", year="1993", journal="Science",
        title="Early Earth Atmosphere Evolution"),
    # MED-severity classes
    # HTML markup in a field
    "markup": dict(
        file_name="Brown_2012_Ecology_WarmingEffects.pdf",
        first_author="Brown", year="2012", journal="Ecology",
        title="Warming effects <i>in situ</i>"),
    # filename title disagrees with index title (token overlap < 0.4); well-named
    "title!=filename": dict(
        file_name="Green_2016_AmNat_TropicalForestCarbonFluxDynamics.pdf",
        first_author="Green", year="2016", journal="American Naturalist",
        title="Completely Unrelated Words About Marine Plankton Chemistry Oceans"),
}

# The single KNOWN-CLEAN fixture (a whole realistic index the gate must NOT fire
# on): well-named article; diacritic author (accent vs ASCII filename must match);
# compound surname (filename keeps first token only); a front-matter/section file
# (author is a SECTION word => cross-check skipped); a supplement that inherited
# parent identity cleanly.
def selfcheck_clean_specs():
    return [
        dict(file_name="Smith_2019_NewPhytologist_LeafAgePhotosynthesis.pdf",
             first_author="Smith", year="2019", journal="New Phytologist",
             title="Leaf Age And Photosynthetic Seasonality", doi="10.1111/nph.12345"),
        dict(file_name="Araujo_2020_NaturePlants_CanopyWaterFlux.pdf",
             first_author="Ara\u00fajo", first_author_ascii="Araujo", year="2020",
             journal="Nature Plants", title="Canopy Water Flux Dynamics",
             doi="10.1038/s41477-020-1"),
        dict(file_name="Aguirre_2018_ISMEJ_SoilMicrobiome.pdf",
             first_author="Aguirre de Carcer", year="2018", journal="ISME Journal",
             title="Soil Microbiome Assembly Processes", doi="10.1038/s41396-018-1"),
        dict(file_name="Appendix_2015_Textbook_SymbolsAndNomenclature.pdf",
             record_type="book_chapter", first_author="Chen", year="2015",
             journal="Textbook", title="Symbols And Nomenclature Appendix"),
        dict(file_name="Smith_2019_NewPhytologist_LeafAge - supplement.pdf",
             record_type="supplement", first_author="Smith", year="2019",
             journal="New Phytologist",
             title="Leaf Age And Photosynthetic Seasonality", doi="10.1111/nph.12345",
             parent_file="Smith_2019_NewPhytologist_LeafAgePhotosynthesis.pdf"),
    ]


# The HISTORICAL FALSE-GREEN, reproduced as a GATE-1 defect class. A confidently
# WRONG first_author on a CRYPTIC (non-well-named) filename: wellnamed() returns
# None, so selfcheck_identity's author!=filename / title!=filename cross-checks
# never run and the row passes silently at HIGH confidence. On the CURRENT module
# this is a LIVE blind spot -- selfcheck_identity returns [] -- so the harness
# reports a FALSE GREEN and the sci_selfcheck_identity gate FAILS. That is the
# intended state: the finding is ENFORCED (mechanically caught by the registry),
# not merely printed. The verdict flips to PASS only once the gate is fixed to
# catch a wrong author on a cryptic filename (a module edit, out of scope here).
SELFCHECK_FALSE_GREEN_SPEC = dict(
    file_name="1-s2.0-S0034425719300abc-main.pdf",
    first_author="CompletelyWrongPerson", year="2019",
    journal="Remote Sensing of Environment",
    title="Some Plausible Title About Canopy Reflectance",
    doi="10.1016/j.rse.2019.01234")


# ==========================================================================
# GATE 2 -- cmd_build flag emission (I17/I18 feeds). One KNOWN-BAD raw-input
# scenario per flag class; the gate runs cmd_build and counts stamped flags.
# ==========================================================================
def flag_bad_sidoi_raw():
    """A linked supplement whose OWN stored DOI disagrees with its parent's =>
    build must stamp `si-doi-disagrees-parent` (feeds curator I18)."""
    return [
        raw_row(file_name="Adams_2016_Nature_Canopy.pdf", doi="10.1038/nature12345",
                embedded_author="Adams, J", embedded_title="Canopy Flux Dynamics"),
        raw_row(file_name="Adams_2016_Nature_Canopy - supplement.pdf",
                doi="10.1038/DIFFERENT999", embedded_author="Adams, J",
                embedded_title="Canopy Flux Supplement"),
    ]


def flag_bad_cryptic_raw():
    """A cryptic-named non-supplement row that resolves to NO author => build must
    stamp `cryptic_unresolved` (feeds curator I17)."""
    return [
        raw_row(file_name="1-s2.0-S0034425719300abc-main.pdf",
                doi="10.1016/j.rse.2019.01234", embedded_author="",
                embedded_title="Canopy Reflectance Study"),
    ]


def flag_clean_raw():
    """Neither flag should be stamped: a well-named article with a real author,
    plus a supplement whose DOI AGREES with its parent."""
    return [
        raw_row(file_name="Smith_2019_NewPhytologist_LeafAge.pdf",
                doi="10.1111/nph.12345", embedded_author="Smith, A",
                embedded_title="Leaf Age Photosynthesis"),
        raw_row(file_name="Smith_2019_NewPhytologist_LeafAge - supplement.pdf",
                doi="10.1111/nph.12345", embedded_author="Smith, A",
                embedded_title="Leaf Age Photosynthesis SI"),
    ]
