---
name: countermeasure-audit
description: The efficacy-measurement owner — invoke WHEN it is time to measure whether shipped countermeasures actually reduced their failure classes (periodically, after a batch of sessions, or when a ledger row's status is questioned), or WHEN about to upgrade any COUNTERMEASURES_LEDGER row from attempted-untested. Owns the sweep → grade → propose loop: run lib/countermeasure-audit.py for the mechanical counts (gate fired/blocked rates pre/post by build_id, marker usage, candidate excerpts), then GRADE the candidates yourself (the judgement half), then PROPOSE ledger/log updates as a reviewable diff — never auto-claim verified-working. Fires on "did the fixes work", "measure the failure rates", "update the countermeasures ledger", "is X still attempted-untested". NOT capability inventory/dedup (-> capability-audit) and NOT authoring new fixes (-> the owning carriers).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-28). Authored in the verification-integrity pass. This skill exists because every shipped fix is honestly tagged efficacy=attempted-untested pending "future FAILURE_CLASS_LOG appends" — and without an owner for that measurement, the tag is unfalsifiable forever (the corpus's own contamination story: countermeasures assumed effective, never measured). The measurement instrument, made a carrier.

# countermeasure-audit — turn attempted-untested into measured, honestly

## When to invoke
Periodically (a batch of sessions accumulated since the last audit), after any major pass ships, or WHEN anyone is about to cite a countermeasure as working. Also WHEN a ledger row's efficacy status is challenged.

## The loop (mechanical half = code; judgement half = you)
1. RUN THE INSTRUMENT (code, not prose): `python3 ~/.claude/lib/countermeasure-audit.py --since <last-audit date|build_id> --out <dir>` (script absent from ~/.claude/lib ⇒ REPORT that and stop — do not hand-count; the guarded install line only copies it when present) — it computes, read-only: per-gate fired/blocked/pass event COUNTS from the structured logs (timeline/adversary-gate/claim-verify-guard), partitioned pre/post by `build_id` (YOU compute the rates at step 3); gate-marker usage swept from the vault session records; CANDIDATE excerpts matching class tell-regexes (labeled candidates — the script never grades); and a PROPOSED skeleton of history rows. It never writes the ledger or the failure log.
2. GRADE THE CANDIDATES (the judgement half — yours): for each candidate excerpt, open the session record it points at (proof-of-reach: the record, not the excerpt, is the evidence), decide instance vs false-positive, and grade real instances per the log's enum (worked / suboptimal / tried-but-failed / unresolved) with caught= attribution. The tell-regex table UNDER-approximates — also skim for classes with no regex (the script's report names which classes it cannot see).
3. RECOMPUTE per-class rates: instances-per-session (or per-arc) in the post window vs the pre baseline (2026-07-27/28 ship dates; `build_id` partitions this mechanically). Small numbers stay small claims — a 1-vs-0 is an anecdote, not a trend; say so.
4. PROPOSE, never auto-write: emit (a) FAILURE_CLASS_LOG HISTORY append lines (its row format is documented in its own header — comment-prefixed, two-space key=value, block-count bump required), (b) ledger STATE row edits — an efficacy upgrade to verified-working REQUIRES the citation (the computed rate table + window); a null or adverse result is recorded just as loudly (efficacy-refuted beats efficacy-unknown). The lead/user reviews and applies the diff — three-writes-under-two-currency-disciplines is not safely scriptable.

## Honesty rules (each inverts a recorded failure)
- The script's green run is NOT the measurement (efficacy-from-existence, DISC-18); the measurement is the graded rate comparison.
- Marker PRESENCE measures gate USAGE, not failure reduction — report both, conflate neither.
- A class with zero candidates in-window is "no instances DETECTED (tell-regex under-approximates)", never "class eliminated".
- Every graded instance cites its session + line (proof-of-reach); an excerpt alone grades nothing.

REF: COUNTERMEASURES_LEDGER.machine.md in the dev root's failure-analysis folder — resolve it the way the script does, via CRT_REPO or an explicit --ledger path (the ledger this feeds; its row format + enums are documented in-file) · FAILURE_CLASS_LOG.machine.md (the DDC-17 log; HISTORY append-only) · `capability-audit` (the sibling audit with a different object: installed capabilities, not failure rates) · `testing-discipline` (the same red-before-green epistemics applied to code).
