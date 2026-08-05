<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORMAT: machine-statedoc
# DOC_ID: <project>/<topic>-now
# DOC_CURRENCY: CURRENT            | one of DRAFT | CURRENT | SUPERSEDED | RETRACTED
# AUTHORITY_CLASS: A1_CURRENT_OWNER
# VERIFICATION_STATUS: <VERIFIED | PARTIALLY_VERIFIED | UNVERIFIED>   | doc-level roll-up; the load-bearing grade is PER-CLAIM below
# TASK_STATUS: <DRAFT | ACTIVE | DONE | FROZEN>
# AS_OF: <ISO-8601 + tz>
# TOPIC_ID: <the-ONE-topic-this-doc-owns>
# DDC_CATEGORY: DDC-03 (STATE)
# SUPERSEDES: <doc_id or ->   ; SUPERSEDED_BY: <doc_id or ->
#
# PURPOSE (DDC-03): what the system/project IS right now for THIS ONE topic, so a blind agent does not
#   reconstruct current state from source or history. At the moment an agent would state "the system
#   currently does X", this doc forces the reader to the LIVE object that decides X (and carries its
#   verification grade) rather than letting the prose substitute for the object. HIGHEST poisoning risk
#   of any category — every line here is read as current truth, so every line must point past itself.
# AUTHORITY: A1, one current owner per topic. (Owner-uniqueness across the project is enforced UPSTREAM
#   by the HEAD manifest, DDC-02 — it is not this doc's own checker line.)
# STATE CONTRACT (STATE = supersede-with-retract): exactly ONE current value per claim. On change,
#   supersede the claim IN PLACE and leave a dated inline retract stub (see below). No accumulation.
#   Flipping DOC_CURRENCY in the header is NOT sufficient — stale claims must be neutralized where they sit.
#
# CHECKER (check_current_documents.py enforces):
#   - in-band STATUS header present: DOC_CURRENCY / AUTHORITY_CLASS / VERIFICATION_STATUS / TASK_STATUS /
#         AS_OF / TOPIC_ID                                                    (fail on missing field)
#   - every CLAIM routes the reader to a live deciding object (code/data/run) AND carries a per-claim
#         verification grade — the doc never asserts a bare current-fact      (fail on claim missing DECIDES_VIA or VERIFICATION)
#   - self-declared authority tokens (CURRENT | DONE | FIXED | DEFAULT | canonical) appear only when
#         neutralized as claims-to-verify                                     (fail on un-neutralized authority token in a claim)
#   - on supersession, stale claims neutralized INLINE — header currency flip alone insufficient
#                                                                            (fail on DOC_CURRENCY=SUPERSEDED with un-neutralized in-body claims)
#
# ─────────────────────────────────────────────────────────────────────────────
# COPY + EDIT BELOW. One CLAIM block per current-state assertion for this topic.
#   RULE 1 — state each item as a CLAIM that points at its deciding object, never as a bare fact. The
#            prose is NOT the authority; DECIDES_VIA is.
#   RULE 2 — do NOT write "X is CURRENT / DONE / FIXED / the DEFAULT / canonical" as an assertion. If you
#            must use such a word, mark it "(claim-to-verify)" so the token scan passes.
#   RULE 3 — when a claim changes, edit it IN PLACE and add a RETRACT line; do not append a second live copy.
# ─────────────────────────────────────────────────────────────────────────────

## CLAIM: <one current-state assertion for this topic, phrased as a claim>
- DECIDES_VIA: <the live object that actually decides this — path to code / data file / run id>  (this is the authority; the sentence above is not)
- VERIFICATION: <VERIFIED | PARTIALLY_VERIFIED | UNVERIFIED> — evidence: <run id / lineage / DDC-14 claim_id or ->
- AS_OF: <ISO-8601 + tz>

## CLAIM: <next current-state assertion for this topic>
- DECIDES_VIA: <live object>
- VERIFICATION: <grade> — evidence: <ptr>
- AS_OF: <ISO-8601 + tz>

# ── RETRACT STUB (this is how the "neutralize INLINE" requirement is satisfied) ──
## CLAIM: <old assertion>   [SUPERSEDED <ISO-8601> → <new claim / doc_id>]
- RETRACTED <ISO-8601>: <old text no longer holds; why>. Current value now decided by <live object>.
