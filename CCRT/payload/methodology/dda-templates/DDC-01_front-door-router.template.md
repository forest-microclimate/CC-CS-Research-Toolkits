<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORMAT: machine-router
# DOC_ID: <project>/start-here
# DOC_CURRENCY: CURRENT            | STATE face: one of DRAFT (pre-ratification) | CURRENT | SUPERSEDED | RETRACTED
# AUTHORITY_CLASS: A1_CURRENT_OWNER
# VERIFICATION_STATUS: N/A         | ROUTING-ONLY — the router holds no verifiable content claims (see SCOPE-AUTHORITY)
# TASK_STATUS: ACTIVE              | one of DRAFT | ACTIVE | DONE | FROZEN
# AS_OF: <ISO-8601 + tz, e.g. 2026-07-17T14:30:00+10:00>
# TOPIC_ID: front-door-routing
# DDC_CATEGORY: DDC-01 (STATE)
# SUPERSEDES: -   ; SUPERSEDED_BY: -
#
# PURPOSE (DDC-01): the ONE known entry point a blind agent (fresh context, no session history) hits
#   first. Routes by the DECISION the agent is about to make — a trigger phrase, NOT a topic name — to
#   the single current owner of that decision. Holds NO topic content itself. It forces the FIRST
#   decision moment ("where do I read for THIS question?") to resolve to the current deciding object
#   instead of whatever doc body a keyword happens to match.
# SCOPE-AUTHORITY: ROUTING ONLY. This doc is the A1 current owner of the route map and of NOTHING else.
#   It is explicitly NOT authority for any topic's content, model behavior, defaults, or test results —
#   those live in the owners it points to.
# STATE CONTRACT (STATE = supersede-with-retract): exactly ONE current route per decision trigger. When
#   an owner is renamed / added / removed, supersede the affected row IN PLACE and leave a dated retract
#   stub (see RETRACT STUB). No accumulation of stale routes. A router is STATE, so it drifts when the
#   topic SET changes — its currency is only as good as the HEAD-manifest checker that catches dangling
#   or unregistered targets (see CHECKER).
#
# CHECKER (check_current_documents.py enforces):
#   - exactly one router doc exists                                          (fail on count != 1)
#   - in-band STATUS header present: currency / authority / as-of / topic-id (fail on missing field)
#   - every route target resolves to a doc registered in the HEAD manifest (DDC-02)
#                                                                           (fail on dangling / unregistered target)
#   - body routes by trigger phrase only — carries NO restated verdict / default / status text, so it
#         cannot itself go stale on content                                 (fail on embedded content-claim token)
#   - router is size-bounded — the always-loaded core stays small           (fail on size > <BUDGET, e.g. 120 lines / 4 KB>)
#
# ─────────────────────────────────────────────────────────────────────────────
# COPY + EDIT BELOW. Each row = one decision trigger → one owner (a DDC-02 topic_id).
#   RULE 1 — LEFT column is a DECISION the agent is about to make; phrase it "When you are about to …",
#            NEVER a topic name.
#   RULE 2 — RIGHT column is a topic_id the HEAD manifest (DDC-02) resolves, NEVER a path. Paths + hashes
#            live in DDC-02, so the router never dangles independently and the checker can cross-check it.
#   RULE 3 — put NO answer, default, or verdict anywhere. If you are tempted to write the value here, it
#            belongs in its owner, not in the router.
# ─────────────────────────────────────────────────────────────────────────────

## ROUTE TABLE

| WHEN YOU ARE ABOUT TO… (decision trigger) | READ THIS OWNER (topic_id; resolve path+hash via HEAD manifest DDC-02) |
|---|---|
| …state what the system/project currently IS or DOES | <current-state-topic-id> |
| …reason about what the science/model SHOULD compute (intended methods) | <methods-topic-id> |
| …operate / reproduce / inspect a run | <runbook-topic-id> |
| …decide whether a feature or claim is actually verified | <verification-topic-id> |
| …check what work is authorized and in what order | <current-plan-topic-id> |
| …find who is authoritative for a topic (and whether it is current) | head-manifest |
| <…your project's next decision trigger…> | <owner-topic-id> |

## RETRACT STUB
Supersede a route IN PLACE when an owner is renamed / removed — do not delete the row.

| …<old trigger>  [RETRACTED <ISO-8601>: owner moved to <new-topic-id>] | <new-topic-id> |

# NOTE: this router is ALWAYS-LOADED core context. Keep it minimal (size-bound above). If it grows
#   topic content, that content has escaped its owner — move it back out.
