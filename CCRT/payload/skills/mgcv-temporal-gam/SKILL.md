---
name: mgcv-temporal-gam
description: Fit a temporal / autocorrelated additive model in mgcv, choosing smooth basis dimension k defensibly (gam.check on progressive subsets) and handling AR1 residual autocorrelation with bam(discrete,rho,AR.start), plus a guard for right-skewed predictors whose extreme tail is the region of interest. Use when fitting a GAM/GAMM to time-series data (large n or temporal autocorrelation), selecting k, hitting a gamm() Cholesky error, or when the response depends on the heavy tail of a skewed predictor.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.

# mgcv-temporal-gam — defensible k, AR1, and skewed-tail guard

## When to invoke
Fitting an additive model to autocorrelated / large-n data; choosing k; a `gamm()` correlation-structure failure; a skewed predictor whose tail drives the response.

## Procedure
1. **AR1, not gamm().** For temporal autocorrelation use `bam(discrete=TRUE)`, never `gamm()` (gamm's Cholesky fails on ANY correlation structure — trigger is the correlation structure, not row count; bam is ~10× faster + stable).
   - `rho <- acf(resid(prelim_model))$acf[2]`
   - `AR.start` = **logical** vector, TRUE at the first obs of each independent series (must be logical, NOT numeric).
   - `bam(y ~ ..., discrete=TRUE, rho=rho, AR.start=data$AR_start, family=...)`.
2. **k-selection by diagnostics, not guessing.** Fit on progressive temporal subsets; run `gam.check` on each; a candidate k passes only if ALL: k-index > 0.95, edf/k′ < 0.9, p-value > 0.05. Choose lowest AIC among passing k. Apply a safety margin max(k across subsets) × 1.2–1.5 for the full dataset. Fallback (none pass): relax k-index > 0.9 + larger margin.
3. **Skewed-predictor / heavy-tail guard.** If a right-skewed predictor's TAIL is the region of interest, quantile-placed knots STARVE the tail. Check knot coverage of the tail; validate CONDITIONAL bias IN the tail region (not aggregate fit); for a variance/CV-vs-predictor diagnostic use `quantreg::rq` median + Q25/Q75 ribbon, not a GAM mean (shows heteroscedasticity honestly).
4. **Persist.** `saveRDS()` the fit object; `fwrite()` per-row predictions (long format) — persist the resolved dimension rather than pre-aggregating it away before saving.

## Success check
No Cholesky failure; residual ACF flattened after rho; chosen k passes all three gam.check criteria on subsets and beats naive-k AIC; tail bias explicitly checked; fit + predictions persisted.

## More gotchas (hard-won)
- `predict.bam()` INHERITS `discrete=TRUE` and MIS-BINS mixed-level newdata grids ⇒ deterministic ±0.5-unit jagged scatter in fitted lines + inflated CIs off a fine mixed grid (`type="terms"` can even throw `NA/NaN argument`). Predict with `discrete=FALSE` for plotting/inference; single-level grids hide the bug.
- fREML/AIC is NOT a clean nested LRT once random effects readjust — one-at-a-time ΔAIC term screens can reverse sign vs a clustered bootstrap; "row-AIC" over-counts effects ~constant within a cluster. Trust the cluster/block bootstrap (temporal-block-cv) for FINAL term selection.
- Transform BEFORE center/scale; screen raw/sqrt/cube-root/log by ΔAIC (cube-root often beats log for right-skewed bounded-positive predictors; log over-corrects). Re-test curvature ON the transformed scale (often linear then suffices). Compare a variable AS RESPONSE across error families only on a common scale via Jacobian-adjusted logLik.
- Impose physically-required MONOTONICITY as a hard constraint — an unconstrained smooth that bends back (e.g. temp turning down at high radiation) is forbidden even if it lowers AIC; test apparent curvature against a first-principles magnitude first (usually a covariate-tail/lag artifact — fix the covariate/lag, keep the term linear).
- Judge interaction terms only in a model that ALREADY carries the relevant random SLOPES (omitting a heterogeneous random slope biases its interaction toward 0 + miscalibrates the SE). For Stan-bound models `s(x, by=continuous)` is non-identified (thin-plate null space carries the main effect ⇒ Rhat 3+) — use parametric `poly(x,2)` (mgcv's REML pins it, Stan's prior can't).

## corCAR1 / knot pitfalls (hard-won)
- corCAR1 / continuous-time correlation needs UNIQUE time values within each group, and the time covariate must match DATA resolution (a daily covariate on half-hourly data duplicates within-day ⇒ singular matrix). Nest `corCAR1(form = ~ time | group)`; a missing grouping ⇒ "sumLenSq too large". Diagnose via `n_distinct(time)` vs `n()` per group — one root cause cascades into 3 errors (uniqueness→knot→memory).
- "more knots than unique data values" is usually a WRONG-SOURCE scaling bug (e.g. `scale(yyyy)` instead of `scale(doy)`) — silent until fit time.
- Knot placement on a right-skewed predictor STARVES the sparse extreme tail (quantile knots land where data is dense, not in the tail where the rare extreme values live). Validate CONDITIONAL bias IN the tail, not aggregate fit — apparent tail flattening is often a knot-placement, not a transform, problem.

## Monotone / shape constraints (hard-won)
- Penalized MONOTONE I-spline (RW1 prior on positive increments `b[k]~N(b[k-1],τ)`, τ half-normal, dense quantile knots) lets penalty+data pick the tail shape robustly — beats fixed-knot monotone splines (which over-steepen/flatten). But reserve monotonicity for genuinely monotone physics — where the physics is hump-shaped (variance rising then falling), the constraint forces a wrong shape.
- `scam`/interaction rank-deficiency = an empty factor-combination cell; `droplevels()` / drop the empty interaction before fitting. A per-group `fs` smooth with thousands of levels is a runtime bottleneck (~2–2.5× slower + convergence risk) — weigh before adding.

## Related
temporal-block-cv + cluster-bootstrap (evaluate + infer); gap-fill-imputation (chunk+splice when predicting to fill); read-fn-internals + assertions (validate the right column/units); verify-or-hedge on any effect claim.
