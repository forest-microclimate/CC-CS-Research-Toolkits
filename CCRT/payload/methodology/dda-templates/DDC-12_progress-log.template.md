<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORMAT: machine-md
# DOC_ID: <project-or-crt>/progress-log
# DOC_CURRENCY: CURRENT (STATE face) + APPEND_ONLY (HISTORY face)
# AUTHORITY_CLASS: A1_CURRENT_OWNER
# VERIFICATION_STATUS: <VERIFIED|PARTIALLY_VERIFIED|UNVERIFIED>   (independent field — do NOT infer from TASK_STATUS or DOC_CURRENCY)
# TASK_STATUS: ACTIVE
# AS_OF: <ISO-8601 + tz>
# TOPIC_ID: progress-log
# DDC_CATEGORY: DDC-12 (HYBRID)
# SUPERSEDES: <doc_id or ->   ; SUPERSEDED_BY: <doc_id or ->
#
# PURPOSE (DDC-12): the dated record of what was done, regularly updated — a single current
#   'where we are' head against append-only dated history, so progress is neither lost nor asserted
#   staler-than-true.
# HYBRID CONTRACT:
#   STATE face   = the single current-position HEAD; supersede IN PLACE as position advances.
#   HISTORY face = append-only dated entries (self-dating), never rewritten; newest first.
# CHECKER enforces:
#   - in-band STATUS header present AND exactly one current-position HEAD block
#         [REQ: in-band STATUS header with a single current-position head]  (fail on 0 or >1 HEAD)
#   - every HISTORY entry carries an ISO date; append-only, newest-first, past bytes unchanged
#         [REQ: entries dated (self-dating history), append-only, not rewritten]  (fail on undated / rewritten / order break)
#   - HEAD AS_OF is not older than the newest HISTORY entry date
#         [REQ: current head regularly reconciled to the deciding live state]  (flag AS_OF age vs activity)
#   - TASK_STATUS, DOC_CURRENCY, VERIFICATION_STATUS present as three independent header fields
#         [REQ: TASK_STATUS distinct from DOC_CURRENCY distinct from VERIFICATION_STATUS]  (fail if any omitted or inferred from another)

## STATE face — current-position HEAD (supersede IN PLACE as position advances)

WHERE_WE_ARE: <one paragraph: what is done, what is in flight, what is next>
AS_OF: <ISO-8601 + tz>              <!-- must be >= the newest HISTORY entry date below -->
DECIDING_LIVE_STATE: <the live object (run/test/artifact id) this head was last reconciled against>
TASK_STATUS: <DRAFT|ACTIVE|DONE|FROZEN>   DOC_CURRENCY: CURRENT   VERIFICATION_STATUS: <VERIFIED|PARTIALLY_VERIFIED|UNVERIFIED>

<!-- ORTHOGONAL: ACTIVE work can sit in a CURRENT doc carrying UNVERIFIED claims. Never read one of
     these three fields off another. -->

## HISTORY face — append-only dated entries (newest first; never rewrite a past entry)

- <ISO-8601 + tz>  <what was done this session/step>            evidence=<artifact/run/lineage id>  by=<who>
- <ISO-8601 + tz>  <prior dated entry, left byte-for-byte unchanged>  evidence=<...>                by=<...>
