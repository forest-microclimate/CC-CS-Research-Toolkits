---
name: durable-doc-architecture
description: Invoke WHEN setting up or auditing a project's durable reference documents — the cross-session docs a blind agent must find via the front door to orient (current state, canonical methods, working rules, decisions, deferred work, bug log, verification status, provenance). Gives the 20 durable-doc categories (DDC-01..DDC-20), each with a class (STATE=supersede-in-place / HISTORY=append-only / HYBRID=both faces) and an in-band STATUS-header schema, plus the Claude Science carrier map. Enforces one-owner-per-topic and the deciding-observable discipline: an agent answers "what does it do NOW" from the one current owner, not from whatever description a keyword matched. On Science the HEAD manifest MUST pin explicit version_ids (latest is last-writer-wins).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# durable-doc-architecture — the durable reference docs every project needs

## The problem it solves (the deciding-observable gap)
The root failure: an agent states or acts on "what the system does NOW" from a source that is NOT the primary record — a description, a stale doc, a filename, or descriptive agreement between two non-authoritative sources. Every category below exists to force a specific deciding question to its ONE current owner at the decision moment. (See the provenance-over-description skill for the read-side rule this structural architecture supports.)

## The 20 categories (DDC-01..DDC-20)
Each durable doc is exactly one category, carries an in-band STATUS header, and has one current owner per topic.

**NAV / AUTHORITY**
- DDC-01 front-door router (START_HERE) — routes by the DECISION an agent is about to make, to the topic's owner; holds no topic content. [STATE]
- DDC-02 HEAD manifest / current-owner registry — for each topic, the ONE current owner + currency + content hash. The keystone the checker enforces. [STATE]

**STATE (current-truth; highest poisoning risk — supersede IN PLACE, never accumulate)**
- DDC-03 canonical current-state ("now") · DDC-04 canonical scientific methods · DDC-05 dev & epistemic working-rules · DDC-06 project purpose & scope · DDC-07 glossary + coordinate/units/currency registry · DDC-08 runbook + resolved-config self-report · DDC-09 authoritative-object/proxy map (recorder-vs-solve, raw-vs-derived) · DDC-19 change-class & limiting-mechanism contract · DDC-20 owner-authority & autonomy-gate registry.

**HYBRID (a STATE face + a HISTORY face — current values superseded in place; dated trail append-only)**
- DDC-10 current plan · DDC-11 decisions & contradiction-adjudication ledger (NO silent merge — name the winner or stay UNRESOLVED) · DDC-12 progress log · DDC-13 deferred/future-work register (3-way split: definite / investigate-later / revisit-pending-decision; OPEN/DONE/DROPPED, closed with a dated outcome, never deleted) · DDC-14 verification/test-status ledger (4 orthogonal dims: implementation·execution·validation·governance, NO cross-inference, default ATTEMPTED_UNTESTED) · DDC-15 data/artifact provenance/lineage · DDC-17 recurring failure-class log.

**HISTORY (append-only; never edit a past row; currency = "complete through <date>")**
- DDC-16 bug/incident log — episode cards (bug / how-discovered / methods-tried / ultimate-fix / status; "attempted-but-failed fix" is never read as the fix; "fixed" != "fixed-verified") · DDC-18 external-evidence / history locator.

## The STATUS-header schema (dogfood on every durable doc)
```
DOC_ID: <project>/<topic>            # stable slug
DOC_CURRENCY: CURRENT|SUPERSEDED|RETRACTED   (STATE) | APPEND_ONLY (HISTORY) | both faces (HYBRID)
AUTHORITY_CLASS: A0_VERIFIED_LIVE | A1_CURRENT_OWNER | A2_SECONDARY | A3_HISTORICAL
VERIFICATION_STATUS: VERIFIED | PARTIALLY_VERIFIED | UNVERIFIED | N/A
TASK_STATUS: DRAFT|ACTIVE|DONE|FROZEN   (DDC-14 uses the 4-dim lattice instead)
AS_OF: <ISO-8601 + tz>               # date-is-provenance
TOPIC_ID: <the ONE topic this doc owns>   # the one-owner key
DDC_CATEGORY: DDC-NN (STATE|HYBRID|HISTORY)
```

## The three invariants (the mandatory floor)
1. **in-band STATUS header** — currency lives in the doc BODY (agent retrieval greps content; a filename/folder/external manifest is out-of-band and never seen by the grep that pulls the doc).
2. **one owner per topic** — exactly one A1_CURRENT_OWNER + CURRENT doc per topic_id. Two current owners = the deciding-observable gap in documentary form.
3. **fail-closed checker** — enforce with machinery, not discipline. It checks FORM/identity, NOT content-truth (a well-formed stale/poisoned claim passes — that needs the DDC-14 ledger + authority lattice).

## Claude Science carrier map (port the principle; rebuild the enforcement — do NOT transliterate)
| Category | Claude Science carrier | Asymmetry |
|---|---|---|
| DDC-01 router | handoff-brief + project memory + a START_HERE artifact | no always-on file; router is partly session/memory |
| DDC-02 HEAD manifest | an artifact registry pinning explicit **version_ids** | **CRITICAL: `latest` is last-writer-wins — pin version_ids or a parallel session silently moves HEAD** |
| DDC-03/04/05 now/methods/rules | skills + profile guidance + machine-md docs | rules load as skills, not always-on files |
| DDC-06 purpose/scope | ## Project Context + project memory | thinner (partly platform-provided) |
| DDC-08 runbook / DDC-15 provenance | partly `host.lineage` (code+env+inputs+checksum, free) | Science gives lineage free; residual = SEMANTIC limits |
| DDC-18 history locator | `host.frames()` / `host.artifacts(before=...)` | heavily platform-provided |
| DDC-20 autonomy gates | session profile / standing behavior | thinner (partly session-configured) |

**STATE-vs-HISTORY discipline is platform-independent; its realization is not.** On Science, STATE docs → replace the one canonical memory row / re-version the pinned artifact; HISTORY docs → append inert artifacts + never rewrite. DDC-05 (working-rules), DDC-17 (failure-class log), and the meta-constitution are near-project-independent — candidates to live ONCE at platform/skill scope, each project carrying only its instantiations (N copies drift).

## Threat model (two vectors)
- **passive staleness** — a STATE doc frozen as DONE/GREEN with no guard misleads future reads (mitigate: supersede-with-retract, provenance-over-description).
- **adversarial persistent-memory poisoning** — an injection landing in a durable STATE surface (a memory row, a START_HERE artifact) persists and is re-read as current. The fail-closed checker enforces FORM not content-truth, so it does NOT catch a well-formed poisoned claim; mitigation is the authority lattice + STATE-supersede-with-retract + delegation-authority discipline, not the checker.

## Caveat
This is one mature exemplar generalized against one threat model + a user seed — not a validated universal architecture. The category count (20) is a ratified synthesis choice, not a natural constant. Cross-platform carriers are proposed; the checker enforces form, not content-truth.
