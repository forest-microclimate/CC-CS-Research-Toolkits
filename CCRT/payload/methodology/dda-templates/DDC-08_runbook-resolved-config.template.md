<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORMAT: machine-doc
# DOC_ID: <project>/runbook
# DOC_CURRENCY: CURRENT
# AUTHORITY_CLASS: A1_CURRENT_OWNER
# VERIFICATION_STATUS: VERIFIED (procedures should be re-run-checked; stamp last-verified per section)
# TASK_STATUS: ACTIVE
# AS_OF: <ISO-8601 + tz>
# TOPIC_ID: runbook
# DDC_CATEGORY: DDC-08 (STATE)
# SUPERSEDES: -   ; SUPERSEDED_BY: -
# (TEMPLATE: copy this file, fill <angle-bracket> stubs, set AS_OF+tz, register the owner row in the
#   DDC-02 HEAD manifest. Keep DOC_CURRENCY=DRAFT until owner-ratified, then flip to CURRENT.)
#
# PURPOSE (DDC-08): how to operate / inspect / reproduce — commands, environment, configuration
#   precedence, validation ladder — PLUS the discipline that every run reports its OWN resolved
#   configuration and run identity (never inferred from another run, a shell, or intent).
# STATE CONTRACT: exactly ONE current runbook per operational topic; supersede IN PLACE on change
#   (SUPERSEDES/SUPERSEDED_BY + dated note). The run's OWN fresh log is the A0 evidence a verdict reads.
# CHECKER enforces:
#   - in-band STATUS header present + all fields populated                                  (fail on missing field)
#   - CONFIGURATION PRECEDENCE stated unambiguously (a total order, no ties)                (fail on absent/ambiguous precedence)
#   - a REQUIRED per-decisive-run record: resolved-config + input-hash + exit-status        (fail on a decisive run with no such record)
#   - RUN-IDENTITY fields enumerated: id, timestamps+tz, code/env revision, resolved config, input+output hashes  (fail on a missing required identity field)
#   - a VALIDATION LADDER distinguishing exit-zero from semantic correctness               (fail if the ladder collapses exit-0 into "correct")
#
# ── prose body below; replace every <angle-bracket> stub ──

## ENVIRONMENT
- <interpreter / conda env / container image + how to activate it>
- <key dependencies + pinned versions, or pointer to the lockfile>

## COMMANDS (operate / inspect / reproduce)
- Run:      <command>
- Inspect:  <command>
- Reproduce a decisive result: <command>

## CONFIGURATION PRECEDENCE  (state a TOTAL order — highest wins; no ties)
1. <highest-precedence source, e.g. explicit CLI flag>
2. <e.g. run-local config file>
3. <e.g. project default>
4. <lowest, e.g. built-in default>
Ambiguity is a defect: two sources setting the same key MUST resolve by this order, and the run must
report which source won (see RESOLVED-CONFIG SELF-REPORT).

## RESOLVED-CONFIG SELF-REPORT  (required per DECISIVE run)
Every run whose output feeds a decision MUST emit its OWN record — never inferred from another run,
a shell, or intent. Required fields:
- run_id:            <unique id>
- timestamps+tz:     <start / end, ISO-8601 + tz>
- code/env revision: <commit sha + dirty flag; env identity>
- resolved config:   <the fully-resolved key->value set actually used, with winning source per key>
- input hashes:      <path -> sha256 for each input>
- output hashes:     <path -> sha256 + row-count for each output>
- exit status:       <process exit code>

## VALIDATION LADDER  (exit-zero != correct — climb explicitly)
1. RAN:      process exited 0.                          <- necessary, NOT sufficient
2. PRODUCED: expected outputs exist + schema matches.
3. SANE:     values within declared physical/range bounds (cross-ref DDC-07 currency).
4. CORRECT:  semantic assertions pass on named cases (the deciding check).
A verdict of "works" requires rung 4 with evidence; a green rung 1 alone is reported as RAN, never CORRECT.
