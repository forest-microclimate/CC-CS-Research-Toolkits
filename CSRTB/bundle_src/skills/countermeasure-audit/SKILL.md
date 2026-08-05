---
name: countermeasure-audit
description: The efficacy-measurement owner — invoke WHEN it is time to measure whether shipped countermeasures actually reduced their failure classes (periodically, after a batch of sessions, or when a ledger row's status is questioned), or WHEN about to upgrade any COUNTERMEASURES_LEDGER row from attempted-untested. Owns the sweep → grade → propose loop: mechanical counts from the session record (marker occurrences via host.query/host.frames, Reviewer verification_checks rows, refusal dispositions), then GRADE candidates yourself (the judgement half), then PROPOSE ledger/log updates as a reviewable diff — never auto-claim verified-working. Fires on "did the fixes work", "measure the failure rates", "update the countermeasures ledger", "is X still attempted-untested". NOT capability inventory (owned by Claude Code's capability-audit skill; not shipped in this bundle) and NOT authoring new fixes (-> the owning carriers).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-28). Authored in the verification-integrity pass. Exists because every shipped fix is honestly tagged efficacy=attempted-untested pending future failure-log appends — without an owner for that measurement the tag is unfalsifiable forever (the corpus's own contamination story). CS twin of the Claude Code skill; the mechanical half here runs as repl queries against the host record (no filesystem logs/build_id partition on this platform — the ship DATE partitions pre/post).

# countermeasure-audit — turn attempted-untested into measured, honestly

## When to invoke
Periodically (a batch of conversations accumulated since the last audit), after a bundle version ships, or WHEN anyone is about to cite a countermeasure as working / challenge one as useless.

## The loop (mechanical half = repl queries; judgement half = you)
1. SWEEP THE RECORD (code, not prose — repl cells): (a) marker occurrences in message spans — `[[route_gate…]] [[plan_lint…]] [[route_audit…]] [[stop_gate…]] [[assert_gate…]] [[receipt_gate…]] [[vstatus_gate…]] [[claim_check…]] [[vloop:…]]` — via the frames/messages record (`host.frames`, `summary_query` where available), counted per conversation, windowed by DATE vs the ship dates (2026-07-27/28 for the planner/builder/integrity passes); (b) the background Reviewer's `verification_checks` rows (pass/fail counts, omission flags) via `host.query` — the one scorer that fires without our choosing it; (c) refusal dispositions logged per `refusal-recovery`. Save the raw counts as an artifact BEFORE interpreting (the sweep is re-checkable evidence).
2. GRADE THE CANDIDATES (yours): a marker's ABSENCE on a qualifying span, a Reviewer fail row, a tell-shaped excerpt — each is a CANDIDATE instance of its class. Open the actual span (proof-of-reach: the record, not the excerpt, is the evidence), decide instance vs false-positive, grade per the failure log's enum (worked / suboptimal / tried-but-failed / unresolved) with caught= attribution.
3. RECOMPUTE per-class rates: instances-per-conversation post-ship vs the pre baseline. Small numbers stay small claims — 1-vs-0 is an anecdote, not a trend; say so.
4. PROPOSE, never auto-write: emit (a) FAILURE_CLASS_LOG HISTORY append lines (comment-prefixed rows, two-space key=value, block-count bump — its header documents the format), (b) COUNTERMEASURES_LEDGER STATE edits — an upgrade to verified-working REQUIRES the citation (the rate table + window + saved sweep artifact id); a null or adverse result is recorded just as loudly. The user/lead reviews and applies (the two files carry two currency disciplines; a blind script write is unsafe).

## Honesty rules (each inverts a recorded failure)
- A sweep that ran is NOT the measurement (efficacy-from-existence, DISC-18); the measurement is the graded rate comparison.
- Marker PRESENCE measures gate USAGE, not failure reduction — report both, conflate neither.
- Zero candidates in-window = "none DETECTED (the tells under-approximate)", never "class eliminated".
- Every graded instance cites its frame + message (proof-of-reach); an excerpt alone grades nothing.

REF: COUNTERMEASURES_LEDGER.machine.md + FAILURE_CLASS_LOG.machine.md (the fed registries, in the analysis folder of the dev root) · `provenance-guard` / `verification-loop` (the gates whose markers this audit counts) · `refusal-recovery` (the logged dispositions) · `testing-discipline` (the same red-before-green epistemics).
