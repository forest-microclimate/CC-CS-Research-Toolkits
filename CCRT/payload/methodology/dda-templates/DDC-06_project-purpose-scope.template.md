<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORMAT: machine-doc
# DOC_ID: <project>/purpose-scope
# DOC_CURRENCY: CURRENT
# AUTHORITY_CLASS: A1_CURRENT_OWNER
# VERIFICATION_STATUS: N/A (owner-stated framing; not a measured claim)
# TASK_STATUS: ACTIVE
# AS_OF: <ISO-8601 + tz>
# TOPIC_ID: purpose-scope
# DDC_CATEGORY: DDC-06 (STATE)
# SUPERSEDES: -   ; SUPERSEDED_BY: -
# (TEMPLATE: copy this file, fill <angle-bracket> stubs, set AS_OF+tz, register the owner row in the
#   DDC-02 HEAD manifest. Keep DOC_CURRENCY=DRAFT until owner-ratified, then flip to CURRENT.)
#
# PURPOSE (DDC-06): why this project exists — its scientific question, its boundary
#   (in-scope / out-of-scope / not-yet), and its authorization posture — so a blind agent shares the
#   owner's frame and does not narrow or broaden scope silently.
# STATE CONTRACT: exactly ONE current owner of the scope boundary. On change, supersede this doc IN
#   PLACE (SUPERSEDES/SUPERSEDED_BY + dated retract note in the section changed); the scope boundary
#   is OWNER-HELD — the agent cannot expand it.
# CHECKER enforces:
#   - in-band STATUS header present + all fields populated                     (fail on missing field)
#   - all three boundary sections present + non-empty: IN-SCOPE, OUT-OF-SCOPE, DEFERRED/NOT-YET   (fail on a missing or empty boundary section)
#   - an AUTHORIZATION GATES section names what requires owner sign-off        (fail on empty gate list)
#   - exactly one current owner recorded (OWNER field)                        (fail on 0 or >1 current owner)
#
# ── prose body below; replace every <angle-bracket> stub ──

## OWNER
<the ONE current owner of this project's scope boundary — name/role>

## WHY THIS PROJECT EXISTS
<one paragraph: the motivation / the problem this project addresses>

## SCIENTIFIC QUESTION
<the specific question(s) the project answers — stated so an agent can tell whether a task serves it>

## BOUNDARY

### IN-SCOPE
- <thing the project explicitly covers>
- <...>

### OUT-OF-SCOPE
- <thing deliberately excluded — and, briefly, why, so it is not silently re-added>
- <...>

### DEFERRED / NOT-YET  (in scope in principle, not now — cross-ref the DDC-13 deferred register)
- <thing set aside for later + pointer to its DDC-13 item id if tracked>
- <...>

## AUTHORIZATION POSTURE
- STANDING MANDATE (agent proceeds without asking): <classes of work — cross-ref DDC-20>
- AUTHORIZATION GATES (require owner sign-off before proceeding):
  - <gate: what the agent must pause for>
  - <...>

## SCOPE-CHANGE RULE
A change to any boundary section above is an owner decision. An agent that believes scope should
widen or narrow records the proposal (DDC-11 decisions / DDC-13 deferred) and pauses — it does NOT
edit the boundary itself. The boundary here is authoritative until the owner supersedes it.
