<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORMAT: machine-md
# DOC_ID: <project-or-crt>/deferred-register
# DOC_CURRENCY: CURRENT (STATE face) + APPEND_ONLY (HISTORY face)
# AUTHORITY_CLASS: A1_CURRENT_OWNER
# VERIFICATION_STATUS: N/A (a register of deferred work; each item self-documents)
# TASK_STATUS: ACTIVE
# AS_OF: <ISO-8601 + tz>
# TOPIC_ID: deferred-register
# DDC_CATEGORY: DDC-13 (HYBRID)
# SUPERSEDES: <doc_id or ->   ; SUPERSEDED_BY: <doc_id or ->
#
# PURPOSE (DDC-13): deferred work split three ways, each with full issue documentation, reasoning,
#   and plan, against a current OPEN/CLOSED head — so deferred work is neither lost nor silently done.
# CLASS (each item tagged into EXACTLY ONE):
#   DEFER_DEFINITE            = (a) definitely-to-do-but-deferred
#   INVESTIGATE_LATER         = (b) to-investigate-later
#   REVISIT_PENDING_DECISION  = (c) to-potentially-do, pending a revisit decision
# STATUS: OPEN | DONE | DROPPED   (DONE/DROPPED = closed with a dated outcome; an item is NEVER deleted)
#   OPEN is the coarse minimum. A project MAY refine OPEN into a richer live vocabulary (this project's
#   own DEFERRED_TASKS.machine.md uses DEFERRED|TODO|WIP|BLOCKED as OPEN-substates + SUPERSEDED as a
#   third closed state). The checker treats any status NOT IN {DONE,DROPPED,SUPERSEDED} as OPEN-class,
#   so a refined vocabulary passes as long as closed states carry a dated outcome.
# KIND (optional second axis, from the working exemplar): chore|feature|experiment|test|cleanup|deploy.
# HYBRID CONTRACT:
#   STATE face   = the standing register; each item's STATUS/fields superseded IN PLACE on transition.
#   HISTORY face = append-only dated transition/closure log (opened, OPEN->DONE, OPEN->DROPPED).
# CHECKER enforces:
#   - in-band STATUS header present (or hash-bound companion)
#         [REQ: in-band STATUS header (or hash-bound companion)]
#   - every item has CLASS in {DEFER_DEFINITE,INVESTIGATE_LATER,REVISIT_PENDING_DECISION} (exactly one)
#     AND non-empty CONTEXT, REASONING, PLAN
#         [REQ: each item tagged into exactly one of the 3 classes + full context/reasoning/plan fields]
#   - every item has a STATUS; a CLOSED status (DONE|DROPPED|SUPERSEDED) carries a dated CLOSED_OUTCOME;
#     any other status is treated as OPEN-class; no item id is ever removed
#         [REQ: a status field distinguishing OPEN/DONE/DROPPED, closed with a dated outcome (never deleted)]
#   - items with USER_DECISION_REQUIRED=yes cannot move to DONE/DROPPED without an OWNER_SIGN_OFF ref
#         [REQ: items requiring an owner decision tagged USER_DECISION_REQUIRED (agent must not silently resolve)]

## STATE face — standing register (one block per item; supersede STATUS/fields IN PLACE)

### ITEM <df-001>
- CLASS: DEFER_DEFINITE                <!-- exactly one of DEFER_DEFINITE | INVESTIGATE_LATER | REVISIT_PENDING_DECISION -->
- STATUS: OPEN                         <!-- OPEN | DONE | DROPPED -->
- USER_DECISION_REQUIRED: no           <!-- yes => agent must not silently resolve; needs OWNER_SIGN_OFF ref to close -->
- TITLE: <short imperative title>
- CONTEXT: <full issue documentation — what, where, how discovered, linked ids>
- REASONING: <why deferred rather than done now; what it depends on>
- PLAN: <the concrete plan to execute when this is picked up>
- OWNER_SIGN_OFF: -                    <!-- required only to close a USER_DECISION_REQUIRED item; else - -->
- CLOSED_OUTCOME: -                    <!-- dated outcome once DONE/DROPPED; '-' while OPEN -->

### ITEM <df-002>
- CLASS: INVESTIGATE_LATER
- STATUS: OPEN
- USER_DECISION_REQUIRED: no
- TITLE: <...>
- CONTEXT: <...>
- REASONING: <...>
- PLAN: <...>
- OWNER_SIGN_OFF: -
- CLOSED_OUTCOME: -

### ITEM <df-003>
- CLASS: REVISIT_PENDING_DECISION
- STATUS: OPEN
- USER_DECISION_REQUIRED: yes
- TITLE: <...>
- CONTEXT: <...>
- REASONING: <...>
- PLAN: <...>
- OWNER_SIGN_OFF: -
- CLOSED_OUTCOME: -

## HISTORY face — append-only dated transition log (newest first; never edit a past line)

- <ISO-8601 + tz>  <df-001>  OPEN -> DONE     outcome=<what shipped + evidence id>          by=<who>
- <ISO-8601 + tz>  <df-003>  OPEN -> DROPPED  outcome=<why dropped>  owner_sign_off=<ref>   by=<who>
- <ISO-8601 + tz>  <df-001>  opened  class=DEFER_DEFINITE                                     by=<who>
