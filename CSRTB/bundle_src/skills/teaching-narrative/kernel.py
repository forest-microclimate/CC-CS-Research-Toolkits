# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# teaching-narrative — register reframe over writing-science's detector kernel
# This skill does NOT re-ship writing-science's ~30 detectors (that 33k-char kernel is
# shared infrastructure; copying it forks a maintenance liability and lets the two drift).
# Instead: load writing-science alongside for scan_draft()/report(), then pass ITS output
# through the functions here. teaching_reframe() re-buckets the ~5 compress-to-cite
# detectors whose "defect" status is specific to the paper form and does NOT transfer to
# teaching prose. Every other tell (nominalizations, passive, weak/buried verbs, noun
# trains, ...) stays a defect — those harm a teaching draft exactly as they harm a paper.
# This kernel takes the scan dict as an ARGUMENT, so it is self-contained: no import of
# writing-science, it just needs the dict scan_draft() returns.

# detector_key -> (new_status, why). Locked by the 5-voice rigor cascade (2026-07-12).
TEACHING_REFRAME = {
    "repeated_words": ("expected",
        "Anchor-term repetition aids retention; elegant variation CONFUSES a learner. "
        "Repeating the key term is a teaching instrument, not monotony. A hit here is "
        "usually a feature - verify it's the ANCHOR term being repeated, not filler."),
    "weak_gap_framing": ("advisory",
        "A paper motivates via a research gap; a teaching doc motivates via a LEARNER's "
        "need. The gap-framing premise does not apply - judge in context, do not auto-fix."),
    "objectives_not_question": ("advisory",
        "'The objective is to...' is a paper tell (pose a question instead) but a LEGIT "
        "teaching move ('by the end you will be able to...'). Judge in context."),
    "bizzwidget_opening": ("advisory",
        "A concrete hook or scenario opening is good teaching; only a JARGON-first opening "
        "is still a defect. Read the actual opening before dispositioning."),
    "undermining_resolution": ("advisory",
        "Honest caveats scaffold a learner's understanding; only a conclusion that "
        "UNDERMINES its own core claim is still a defect. Judge in context."),
    "pseudo_explanation": ("advisory",
        "Stage-direction and learning-objective phrasing ('Notice that...', 'In learning a "
        "system...') narrates the reading act - a paper tell, but often legitimate teaching "
        "scaffolding that orients a learner. Judge in context; do not auto-cut. All OTHER new "
        "P2 detector keys stay defects (they harm teaching prose too)."),
}

def teaching_reframe(scan_result):
    """Re-bucket a writing-science scan_draft() result for the TEACHING register.
    Input: the dict scan_draft(text) returns -> {counts, profile, hits}.
    Returns {defects, advisory, expected, profile}: the ~5 genre-bound detectors move
    OUT of defects per TEACHING_REFRAME; all other fired detectors stay in defects.
    Re-reads writing-science's output; does not re-run detection."""
    counts = dict(scan_result.get("counts", {}))
    hits = scan_result.get("hits", {})
    defects, advisory, expected = {}, {}, {}
    for key, n in counts.items():
        if not n or n <= 0:
            continue
        if key in TEACHING_REFRAME:
            status, why = TEACHING_REFRAME[key]
            (expected if status == "expected" else advisory)[key] = {
                "count": n, "why": why, "hits": hits.get(key, [])}
        else:
            defects[key] = {"count": n, "hits": hits.get(key, [])}
    return {"defects": defects, "advisory": advisory, "expected": expected,
            "profile": scan_result.get("profile", {})}

def teaching_report(scan_result):
    """Human-readable teaching-register triage: real defects first (fix), then advisory
    (genre-bound, judge in context), then expected (usually a feature). Print this instead
    of writing-science's report() when the draft is a teaching doc."""
    r = teaching_reframe(scan_result)
    out = ["=== TEACHING-REGISTER TRIAGE ==="]
    def block(title, d):
        out.append("\n-- " + title + " --")
        if not d:
            out.append("  (none)")
            return
        for k, v in sorted(d.items(), key=lambda x: -x[1]["count"]):
            tail = (" - " + v["why"]) if v.get("why") else ""
            out.append("  {0}: {1}{2}".format(k, v["count"], tail))
    block("DEFECTS (fix; these harm teaching too)", r["defects"])
    block("ADVISORY (genre-bound; judge in context, do NOT auto-fix)", r["advisory"])
    block("EXPECTED (usually a teaching feature)", r["expected"])
    return "\n".join(out)
