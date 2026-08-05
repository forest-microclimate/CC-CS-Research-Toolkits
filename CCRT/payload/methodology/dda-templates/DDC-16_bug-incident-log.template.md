<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORMAT: machine-bug-log
# DOC_ID: <project>/bug-incident-log
# DOC_CURRENCY: APPEND_ONLY
# AUTHORITY_CLASS: A3_HISTORICAL
# VERIFICATION_STATUS: N/A
# TASK_STATUS: ACTIVE
# AS_OF: <ISO-8601 + tz>          # for HISTORY, AS_OF = "complete through" date, NOT "correct now"
# TOPIC_ID: bug-incident-log
# DDC_CATEGORY: DDC-16 (HISTORY)
# SUPERSEDES: -   ; SUPERSEDED_BY: -
#
# PURPOSE (DDC-16): the dated, append-only record of concrete bugs/incidents in analysis, methods, and
#   code, each as an EPISODE CARD -- the bug, how it was discovered, the methods tried, the ultimate fix
#   that worked (or an explicit not-yet-fixed) -- tied to a verification grade. Self-dating, safe to
#   keep forever.
# HISTORY CONTRACT (append-only): entries are newest-first CARDS; a card is never rewritten or deleted.
#   Each card is dated + provenance-tagged. A card's ATTEMPTS and OUTCOME_LOG are append-only sub-logs
#   (add a line; never edit or remove a past line). Superseded findings (e.g. a fix later found to be a
#   misdiagnosis) are RETAINED, not erased -- append a newer line that supersedes them.
# AUTHORITY: A3_HISTORICAL (brief: H1 dated history, provenance-only). The OPTIONAL head below MAY
#   summarize open bugs but is NOT authority -- the dated cards are the record.
#
# CARD FIELD MAP (task episode-card field -> brief required field):
#   bug -> SYMPTOM   how-discovered -> DISCOVERY_METHOD   methods-tried -> ATTEMPTS
#   ultimate-fix -> ULTIMATE_FIX   status -> OUTCOME (+ VERIFICATION_GRADE)
#
# OUTCOME vocabulary (closed):        FIXED_VERIFIED | NOT_YET_FIXED | RETRACTED_MISDIAGNOSIS
# ATTEMPT result vocabulary (closed): WORKED | FAILED | PARTIAL | ABANDONED
#
# CHECKER enforces:
#   - STATUS header well-formed; DOC_CURRENCY=APPEND_ONLY; DDC_CATEGORY=DDC-16 (HISTORY)                      [REQ: D7-floor STATUS-HEADER SCHEMA + HISTORY class contract]
#   - every card has a non-empty OPENED date (ISO-8601); fail on any undated card                            [REQ: each entry dated -- no undated bug entries]
#   - every card carries all required fields non-empty: SYMPTOM, DISCOVERY_METHOD, ATTEMPTS(>=1),
#     ULTIMATE_FIX, OUTCOME; fail on a missing field                                                          [REQ: required fields symptom/discovery-method/attempts/outcome]
#   - every card is PROVENANCE-tagged (frame/session id, file:line, or run id); fail on missing provenance   [REQ: HISTORY contract -- each entry provenance-tagged]
#   - OUTCOME drawn from the closed vocabulary; a bare "FIXED" fails                                          [REQ: outcome (fixed-verified/not-yet-fixed/retracted-misdiagnosis)]
#   - OUTCOME=FIXED_VERIFIED requires a non-empty VERIFICATION_GRADE + evidence ptr (test/run/artifact
#     id); "fixed" without a grade fails                                                                      [REQ: outcome tied to a verification grade -- fixed != fixed-verified]
#   - each ATTEMPT names what was tried + a result token from the closed vocabulary + a date, so an
#     attempted-but-failed fix is never read as the fix                                                       [REQ: attempts field made checkable; PURPOSE: methods tried vs. the fix that worked]
#   - ATTEMPTS and OUTCOME_LOG are append-only: no line removed/edited/renumbered across versions; a
#     correction is a NEW dated line                                                                          [REQ: append-only; entries never rewritten (superseded findings retained)]
#   - OUTCOME (single field) == the newest OUTCOME_LOG line's value; fail on divergence                       [REQ: outcome -- one current status, superseded findings retained in the log]
#   - cards ordered newest-first (OPENED descending); BUG ids unique and never reused                         [REQ: HISTORY contract -- newest-first; append-only]
#   - IF the OPTIONAL head is present, it is marked SUMMARY_ONLY; fail on a head asserting authority          [REQ: AUTHORITY -- compact head may summarize but entries are historical]
#
# -----------------------------------------------------------------------------
# OPTIONAL HEAD (SUMMARY_ONLY -- non-authoritative; the dated cards below are the record)
#   open bugs: <count>  |  newest card: BUG-<NNNN> (<date>)  |  <one-line pointer to hottest open bug>
# -----------------------------------------------------------------------------
# CARDS -- newest-first. Prepend a NEW card immediately below this line. Copy the stub; fill <...>.

## BUG-<NNNN> - <one-line title>
- OPENED: <ISO-8601 + tz>
- SYMPTOM: <the observable wrong behavior -- what was seen, not the guessed cause>
- DISCOVERY_METHOD: <how it surfaced -- failing test / assertion / user report / run-log line>
- PROVENANCE: <where/who -- frame or session id, file:line, run id>
- ATTEMPTS: (append-only; each line dated + result token; chronological within the card)
    - <date> <what was tried> -> <WORKED|FAILED|PARTIAL|ABANDONED>: <one-line result>
    - <date> <what was tried> -> <WORKED|FAILED|PARTIAL|ABANDONED>: <one-line result>
- ULTIMATE_FIX: <the change that resolved it + pointer (commit/artifact/lineage id), or "-" while NOT_YET_FIXED>
- OUTCOME: <FIXED_VERIFIED | NOT_YET_FIXED | RETRACTED_MISDIAGNOSIS>   # == newest OUTCOME_LOG line
- VERIFICATION_GRADE: <required iff OUTCOME=FIXED_VERIFIED: what proved the fix + evidence ptr (test/run/artifact id); else "-">
- OUTCOME_LOG: (append-only; newest last; retains superseded findings)
    - <date> <OUTCOME value> <optional note / "supersedes finding of <date>">

# (next-older card follows)
