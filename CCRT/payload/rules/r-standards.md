---
globs: ["*.R", "*.r", "*.Rmd"]
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.

## RULE.ar1 — AR1 correlation in large temporal datasets

WHEN: n_obs > 100K & temporal autocorrelation present
USE: `bam(discrete=TRUE)` with rho param | NOT `gamm()`
WHY: bam ~10× faster + numerically stable; gamm() fails via Cholesky error on ANY correlation structure (trigger = correlation structure, not row count)

PROC.bam_ar1:
1. estimate: `rho <- acf(resid(preliminary_model))$acf[2]`
2. create: `AR.start` = logical vector (TRUE at first obs of each time series) — MUST be logical, not numeric
3. pass: `rho = rho_est, AR.start = data$AR_start`
4. grouping in correlation structures: use pipe operator

## RULE.silent_failures — R silent-failure patterns

RULE.seq_operator:
- `2:1` => `c(2,1)` NOT `integer(0)` (decreasing, not empty)
- IF for-loop iterates `2:n` => guard with `if (n >= 2L)` before loop | OR use `seq_len(n)[-1]`

RULE.tz_consistency:
- mixed tz args in `complete()` / joins => SILENT failure (timestamps identical when printed, differ internally)
- FIX: define tz ONCE at script top; use consistently throughout
- DOCUMENTED: Etc/GMT+3 vs UTC mismatch produced 1 block instead of 3

RULE.co_index (co-index-before-compare; tz_consistency is one instance of it):
- an IS-vs-SHOULD (or ANY) comparison of two series/values is valid ONLY if they share the SAME coordinate (step·time·height·bin·unit). The defect is the PAIRING, not the values — a mis-pairing spawns a PHANTOM discrepancy (2026-07-06: engine sza@step117 vs my geometry@step116 => a fake 7° "sza bug" nearly named a root).
- FIX: JOIN on the coordinate key, NEVER positionally pair — `merge(engine, ref, by="step")` NOT `engine$sza - ref$sza`; then `stopifnot(nrow(j) > 0L, identical(j$coord_x, j$coord_y))`. Reliable form = assert-by-construction in the analysis/probe TEMPLATE (a static "positional-pair" lint is high-FP => rely on the template assertion, not a grep).
- DISCIPLINE (prose + analysis): tag every value with its FULL coordinate AT THE SOURCE — emit `(step,UTC,local,height,bin,value,unit)` tuples so you pair TUPLES not bare numbers ("put the coordinate IN the value").
## RULE.gam_k — GAM smooth k selection

METHOD: `gam.check()` diagnostics on progressive temporal subsets | NOT extrapolation

CRITERIA (all three must pass per candidate k):
- k-index > 0.95
- edf/k-prime < 0.9
- p-value > 0.05

SELECT: lowest AIC among models passing all criteria
SAFETY MARGIN: max(k across subsets) × 1.2–1.5 for full dataset
FALLBACK (no models pass strict): relax k-index threshold to > 0.9 & increase safety margin

DOCUMENTED RESULT: 51-year dataset => k_trend=60, k_season=20, k_interact=8; AIC improvement 2,087 units vs naive k
