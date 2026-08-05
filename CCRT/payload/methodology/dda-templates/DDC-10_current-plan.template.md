<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORMAT: machine-md
# DOC_ID: <project-or-crt>/current-plan
# DOC_CURRENCY: CURRENT (STATE face) + APPEND_ONLY (HISTORY face)
# AUTHORITY_CLASS: A1_CURRENT_OWNER
# VERIFICATION_STATUS: N/A (coordination contract, not a verifiable claim)
# TASK_STATUS: ACTIVE
# AS_OF: <ISO-8601 + tz>
# TOPIC_ID: current-plan
# DDC_CATEGORY: DDC-10 (HYBRID)
# SUPERSEDES: <doc_id or ->   ; SUPERSEDED_BY: <doc_id or ->
#
# PURPOSE (DDC-10): the active plan + requested sequence, discoverable after restart/compaction from
#   ONE authoritative location, so the coordination contract (what work is authorized, in what order)
#   survives context loss.
# HYBRID CONTRACT:
#   STATE face   = the single CURRENT plan head; on replan, supersede the head IN PLACE.
#   HISTORY face = append-only dated trail of superseded plan versions (never overwrite; newest first).
# CHECKER enforces:
#   - in-band STATUS header present AND exactly one plan step-set marked CURRENT
#         [REQ: in-band STATUS header with a single CURRENT plan head]  (fail on 0 or >1 CURRENT head)
#   - every plan step carries an ordinal + state in {done,blocked,next}; blocked names BLOCKED_ON
#         [REQ: ordered prerequisites explicit and machine-checkable (done/blocked/next)]  (fail on missing/invalid state or unordered)
#   - on replan, prior head retained in HISTORY dated with SUPERSEDED_BY set
#         [REQ: superseded plan versions retained dated, not overwritten in place]  (fail if header SUPERSEDES!=- and no dated prior head in HISTORY)
#   - this DOC_ID is registered as the A1 owner of topic 'current-plan' in the DDC-02 HEAD manifest
#         [REQ: one authoritative location named in the HEAD manifest]  (fail on unregistered/duplicate owner)

## STATE face — the single CURRENT plan head (supersede IN PLACE on replan)

PLAN_HEAD_ID: <plan-vN>            <!-- bump N on replan; the old head moves to HISTORY, is not deleted -->
GOAL: <one-line objective this plan sequence delivers>
AS_OF: <ISO-8601 + tz>

Ordered prerequisites — one line per step: `N. [state] description`; state in {done, blocked, next}:

1. [done]    <step already completed — link its evidence: DDC-12 progress entry / DDC-14 claim id>
2. [next]    <the one step authorized to start now>
3. [blocked] <step> — BLOCKED_ON: <the id/decision/gate that unblocks it>
4. [next]    <subsequent authorized step, in required order>

<!-- INVARIANTS: exactly ONE plan step-set is CURRENT (no two live heads). Steps are ordinal-ordered.
     'next' = authorized to start; 'blocked' must name BLOCKED_ON; 'done' must link its evidence. -->

## HISTORY face — append-only superseded plan versions (newest first; never edit a past line)

- <ISO-8601 + tz>  PLAN_HEAD_ID <plan-v(N-1)>  SUPERSEDED_BY <plan-vN>   reason=<why replanned>  by=<who>
- <ISO-8601 + tz>  PLAN_HEAD_ID <plan-v(N-2)>  SUPERSEDED_BY <plan-v(N-1)> reason=<...>          by=<...>
