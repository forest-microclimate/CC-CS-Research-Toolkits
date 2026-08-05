FORMAT: machine-record (this doc obeys its own rules). Read as data.
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
DOC_ID: methodology/handoff-protocol
PURPOSE: after /compact the continuer has only {compaction-summary, the handoff .md, the live repo}; no working memory. Past handoffs FAILED (continuer confused / errored / needed hand-holding). This = the fix. Apply §RULES when WRITING; obey §FIRST_ACTIONS when CONTINUING.
SCOPE: write handoffs + this guide as MACHINE-RECORDS (terse KEY:value / tables / tagged lists), NOT human prose. Prose only for an irreducible relationship clause.

## FAILMODES [observed => rule that prevents]
- F1 stale/assumed fact (path/symbol/value changed or mis-remembered) => RULE_V + RULE_F.
- F2 ambiguous done-vs-not (continuer re-does or skips) => RULE_S.
- F3 missing functional relationship (edit silently breaks elsewhere) => RULE_A.
- F4 re-hits a known trap => RULE_G.
- F5 not actionable ("improve X", no entry point) => RULE_N.
- F6 over-narrative (state buried in prose) => RULE_M.
- F7 not self-contained (assumes prior context) => RULE_C.
- F8 blind-trust vs total-distrust (errors on stale, or re-derives all) => RULE_T.

## RULES [when writing]
- RULE_V verify-then-write: gather LIVE state first (git log + git status ALL repos incl nested; ls; Read each file you describe). Write every path/hash/symbol/number from that live reading, not from memory.
- RULE_S state-table spine: one row/component = id|status-tag|commit@repo|proof-fact. Single source of truth; rest elaborates.
- RULE_F tag facts: each load-bearing constant gets "verify:" (cmd/file). Stamp values verified-<date>.
- RULE_A architecture: who-calls-whom + what-reads-what + exact insertion point.
- RULE_G gotchas: every trap hit = symptom => cause => fix (exact error text helps).
- RULE_N entry-pointed next: goal + exact file:symbol(or file:line) + first concrete action + GATE proving success. Ordered. Flag user-input-required.
- RULE_M machine-first: tables/tagged-lists/KEY:value/status-tags; prose only for irreducible "why".
- RULE_C self-contained: mission + why + glossary (define every acronym once); assume zero prior memory.
- RULE_T trust-but-verify: doc=map not territory; continuer re-confirms load-bearing items, ESP file CONTENTS (this harness invalidates read-state across refresh -> Read immediately before Edit).

## STATUS_TAGS
DONE | DONE+VALIDATED | WIP | TODO | TODO=GAP | DESIGNED(not impl) | DIAGNOSED(not fixed) | BLOCKED(reason) | SUPERSEDED.

## SECTIONS [required skeleton; order]
0 FIRST_ACTIONS (trust-but-verify checklist + mandate)
1 MISSION (+ glossary; self-contained)
2 STATE (the table spine: id|component|status|commit@repo|proof)
3 RESULT(S) (payoff numbers + 1-line conclusion + caveats)
4 GIT_MAP (every repo, branch, which change -> which repo; recent hashes)
5 FILES (RELEVANT only: path :: role :: status :: key-detail)
6 FLOW (data-flow/architecture; exact insertion points)
7 FACTS (load-bearing constants; each verify:)
8 GOTCHAS (symptom => cause => fix)
9 RUN (exact copy-paste commands per reproducible action; expected output)
10 NEXT (entry-pointed, priority-ordered, gates; flag user-input)
11 PLAN_FILE (plan-vs-reality status)

## FIRST_ACTIONS [continuer; put a copy at TOP of every handoff]
- read handoff + linked running-log + MEMORY.md index (+ named memories).
- re-verify STATE spine: git log --oneline in EACH repo; confirm cited hashes.
- before EDIT: Read the file first (refresh invalidates read-state; Edit-without-Read errors by design = normal).
- spot-verify one FACT (e.g. re-run its verify: command) before relying on FACTS.
- take top NEXT: go to entry point -> first action -> run its GATE -> continue.
- mandate: keep developing; stop only at genuine can't-resolve-without-user roadblock (autonomy-mandate memory). Update handoff+log as you go.

## ANTIPATTERNS [do NOT]
- "see the code" w/o path:symbol. - list ALL scripts (list the ~10 that matter). - bury hash/number in a sentence (-> table/FACTS). - claim DONE w/o proof-fact. - omit gotchas as "obvious". - describe a plan instead of STATE (plan-vs-reality). - assume reader saw prior runs. - prose paragraphs where KEY:value / table works.
