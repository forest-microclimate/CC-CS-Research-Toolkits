
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
<preferences>
# Folded from auto-memories. Auto-memory is keyed by project PATH, so it can't be made global —
# these durable, cross-project preferences live here instead (always-on). Deduped against ~/.claude/rules/*:
# root-before-bandaid, reproduce-before-fixing, verify-local-state, refactor-invariants, verification-principles,
# parallel-runs are RULES already — not repeated here.

EPISTEMIC-HONESTY:
- Claim evidence ONLY for a verified hypothesis. Call an untested claim an "unsupported hypothesis", NOT "assumed" / "likely" / "the cause". Verify before asserting.
- When listing candidate hypotheses, ALWAYS include an explicit "or something else" — closing the hypothesis space implies a false completeness.
- model-check-no-true-mean: with no ground-truth mean to validate against, validate via diagnostics + physics/theory + uncertainty (posterior-predictive coverage / CI overlap) rather than against a presumed "true" value; label a model−comparator difference a "difference", not a "bias".

DEBUGGING-DISCIPLINE (companions to the rules):
- fully-fix / pull-the-thread: a CONFIRMED-real bug ⇒ fix the ROOT + add a gated (logged) guard, rather than symptom-clamping or parking it.
- chain-walk IS-vs-SHOULD: a wrong end-of-chain value ⇒ walk each link computing IS vs an INDEPENDENT should; the first divergence localizes the defect.
- unify-over-parallel-patch: handle an edge case by UNIFYING with the sibling mechanism, not a parallel tuned knob; a mirror-knob or a value-bracket search = a structural question mis-framed as tuning.

ANALYSIS-&-STATS:
- per-unit-then-aggregate: compute ratios / nonlinear quantities at the FINEST unit THEN average — never ratio-of-averages (F(mean) ≠ mean(F)); for differences, PAIR the same unit (join on the coordinate key, never positionally). [see the aggregation-jensen-bias skill]
- knot-placement-skewed-predictor: quantile spline knots STARVE a right-skewed predictor's sparse tail; validate CONDITIONAL bias across the predictor range (per-tertile), not just aggregate.
- skewed-scatter-smoother: for a skewed / heteroscedastic per-bin scatter, prefer a quantile-regression median + Q25/Q75 envelope over a GAM mean (the GAM mean biases high and hides heteroscedasticity).
- uncertainty-representation-consistency: use ONE interval construction across all bars (observed + projected); include sampling uncertainty; a single full-record mean reference.
- bam-discrete-predict gotcha: mgcv `predict.bam(discrete=TRUE)` gives jagged predictions on mixed-level grids → use `discrete=FALSE` when predicting for plots.

DATA-&-TIMESTAMP-INTEGRITY:
- verify the timestamp convention EMPIRICALLY before any diel/seasonal analysis (anchor to solar-noon / dawn-dusk) rather than trusting an upstream tz LABEL; check each source separately before joins. [see tz-safe-timestamps]
- reconstruct date_time from y/m/d/h/m/s components with an EXPLICIT tz (e.g. "UTC"; machine-portable + unambiguous) rather than trusting an on-disk datetime column.
- data-pipeline-silent-failures — four clean-but-wrong traps: `grep(...)[1]` returns COLUMN ORDER not a match; a derived-product silently SUBSET; the WRONG quality metric; un-cross-checked aggregates.
- read hierarchical / decimal-string IDs as CHARACTER — `fread` silently collapses `1.10`→`1.1`.

COMMUNICATION-&-SCOPE:
- Write "iWUE and WUE", NEVER "iWUE/WUE" — the slash reads as a ratio; keep paired ratios conceptually separate (generalizes to ANY paired ratio).
- Surface CONFLICTS and keep scope intact: when a request doesn't fit the data/code, state the conflict + offer options; change scope, substitute, or broaden only after surfacing it — never silently.
- "process all X" means EVERY X — settle any decidable sub-choice yourself rather than letting it become a silent scope cut.

WORKFLOW-&-OUTPUT-HYGIENE:
- Always PRODUCE diagnostic plots for key findings (diel / scatter / distribution / faceted), and always VISUALLY INSPECT the saved image yourself before reporting — numeric summaries miss broken panels and visual patterns.
- Save test/benchmark outputs to disk (fit objects + per-row predictions, not just scalar metrics) so diagnostics don't force a re-run; save at the FINEST resolution (long format), never pre-aggregate at write time (aggregation is irreversible).
- Validate any code edit on a MINIMAL interactive step BEFORE launching a batch / full run.
- When editing a `.md` that has `.docx`/`.pdf` twins, regenerate the renders in the SAME session (concordance; re-derive the local TeX/font paths on this machine).
- Paper paywalled (401/403) ⇒ ask the user to download it (they have institutional access) rather than fighting the fetch.

DELEGATION:
- Delegate by task SHAPE, not size: a read-only sweep that returns a CONCLUSION → an agent; iterative / visual / slow-to-verify work → do it yourself. Match model + effort to the reasoning difficulty.
- Delegate IMPLEMENTATION; run slow VERIFICATION yourself rather than letting a sub-agent background-wait on work it launched itself.

COMPUTE-&-LONG-RUNS:
- mgcv `bam(nthreads=)` is effectively a NO-OP — only PROCESS-based parallelism (mclapply / Stan chains) actually parallelizes. (Core-cap discipline: ~/.claude/rules/parallel-runs.machine.md.)
- Launch long runs DETACHED so they survive terminal-close / agent exit: `nohup … </dev/null > log 2>&1 &` (macOS has no `setsid`); PAIR it with a Claude-tracked `run_in_background` sentinel (detached runs are invisible and send no completion signal); silence ≠ success — need a DONE sentinel + a guard; count ALL procs (workers + master + wrapper).
- reproduce-baseline-before-overwrite: before extending a committed pipeline step, reproduce its output BYTE-IDENTICAL (sha256) to prove exact duplication, then gate the extension on the match.

ENVIRONMENT (carry only if the new machine also iCloud-syncs its home):
- iCloud-synced `~/Documents` can intermittently REVERT just-written files (conflict `* 2/` dirs) — verify writes persisted.
</preferences>
