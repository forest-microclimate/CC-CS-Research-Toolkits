---
name: tree-ensembles
description: Gradient-boosted trees (xgboost/lightgbm) and random forests done right for tabular environmental regression — temporal+height feature engineering, quantile objectives for predictive intervals, refit-locally-not-frozen-global, and honest blocked-temporal-CV evaluation. Use when fitting, tuning, or evaluating an xgboost / lightgbm / random-forest regressor on tower or gridded environmental data, deciding height-as-feature vs per-height models, engineering lag/harmonic features from timestamps, pulling predictive intervals out of a tree model, or when trees are proposed to bridge a large multi-year gap (a piecewise-constant learner structurally cannot — that is the fusion boundary).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# STATUS: CURRENT (2026-07-16). Ported from the Claude Science skill (reverse port T-42).

# tree-ensembles — gradient-boosted trees & random forests done right for tabular environmental regression

Trees are the one ML family already proven in one tower reconstruction — xgboost beat the `t2(time,height)` bam on MAE in 45/46 height folds when refit locally — but naive use leaks under autocorrelation, over-smooths under RMSE-only tuning, ships uncalibrated point predictions, or gets pointed at gaps a piecewise-constant learner cannot cross. This skill makes trees earn that win: honest folds, refit-local, calibrated intervals, and a clear extrapolation boundary.

## When to invoke
Fitting / tuning / evaluating a gradient-boosted-tree or random-forest regressor on tabular environmental data (tower met, height profiles, gridded drivers), or choosing tree architecture — height-as-feature, lags, harmonics, intervals — for such a fit.

## Why trees, and their one hard limit
- **Reach for trees first** on tabular environmental regression: mixed continuous covariates + cyclical encodings + height, invariant to monotone transforms, no feature scaling, native NA handling (xgboost/lightgbm learn a default split direction for a missing feature — useful when covariates are co-gapped). `lightgbm` (histogram, leaf-wise) scales to large n; `xgboost` is the established sibling; random forest / quantile regression forest is the low-variance baseline and an interval source.
- **The hard limit — piecewise-constant.** A tree's prediction is the mean of training targets in the matching leaf. Off the training envelope (a covariate beyond every split threshold, a time span with no rows) it returns the nearest leaf's constant — flat, never a trend. Trees INTERPOLATE inside the envelope; they do NOT extrapolate. See the boundary section.

## Feature engineering for temporal + height structure
1. **Cyclical harmonics, never a raw datetime index.** A monotone time integer is the extrapolation trap in miniature — trees cap at the max timestamp seen. Encode the diel + seasonal cycle as sin/cos of hour-of-day and day-of-year (paired terms). Build the clock on UTC-safe timestamps (tz-safe-timestamps) so a DST/offset slip never phase-shifts a harmonic.
2. **Lags within the memory horizon only.** Within-record memory e-folds at <=33 h, so lag features beyond a few multiples of that carry ~no signal and only widen the envelope you must stay inside at predict time. Add short lags/leads of the target and of co-measured drivers; drop the long ones.
3. **Height as a feature vs per-height models.** A SINGLE model with height as a column pools strength across a fine vertical grid and learns a smooth-in-height dependence — in one reconstruction this fed the instantaneous vertical profile and beat the per-surface bam. Per-height models fragment the data and lose cross-height coherence; prefer height-as-feature unless a level is physically distinct (e.g. below- vs above-canopy) and data-rich enough to stand alone.
4. **Derive per level; do not predict-then-combine a nonlinear quantity.** VPD = f(Tair, H2O, pamb) computed at each height from predicted Tair/H2O — never a tree fit on VPD directly, and never averaged across levels before the nonlinear step (aggregation-jensen-bias).

## Refit locally — the hard-won lesson
- A global tree pretrained on OTHER years and applied cold to a new fold is out of envelope and loses. The engine is not the point — SCOPE is: at EQUAL scope (both refit on the same fold's kept levels) xgboost beats the `t2(time,height)` bam on MAE in 45/46 folds and the driver bam in 43/44. An earlier "Bayes 9/9" verdict was a training-regime artifact (global Bayes vs cold-frozen xgb), not an engine result.
- **Refit on the target fold / target regime; do not freeze one global model and apply it cold.** Trees are local learners — their strength is the instantaneous, in-envelope relationship, not transfer across regimes.

## Predictive intervals — quantile objective, then calibrate
- A point prediction + a Gaussian +/- is not an interval here (height cov95 hit 0.52 for xgb — badly under-covered). Fit the **quantile (pinball) objective**: xgboost `reg:quantileerror` (with `quantile_alpha`) or lightgbm `objective="quantile", alpha=tau`, at tau = 0.025 / 0.5 / 0.975 for a 95% band — or a single quantile regression forest, which reads all quantiles off the leaf distribution.
- **Guard quantile crossing** (an independently-fit upper can fall below the lower) — sort the predicted quantiles per row, or fit them jointly.
- Quantile trees give a RAW interval, not a calibrated one. Check PIT / empirical coverage and recalibrate (split-conformal) via **calibrated-uq-for-ml** — that skill owns the coverage fix; this one only produces the raw quantiles.

## Honest evaluation (defer fold construction to temporal-block-cv)
- **Never iid-CV an autocorrelated series** — adjacent half-hours are near-duplicates, so a random split trains and tests on the same event and inflates skill. Use blocked, embargoed (~e-fold ≈ 33 h), whole-block folds from **temporal-block-cv**; the early-stopping validation slice must also be a blocked hold-out, not a random tail.
- **The metric trap.** MAE/RMSE reward the conditional mean, which loses 43-78% of diel variance; a tree tuned to RMSE alone drifts toward that over-smoothed mean. Report variability fidelity (predicted-vs-observed variance ratio, diel amplitude, spectrum) ALONGSIDE the error — the target is a realistic realization, not the smoothest curve.
- **Transfer fold.** Include a held-out nonstationary regime (a held-out drought/anomaly regime, gap fraction 43-52% vs ~5% baseline) — in-sample fit is not the deciding metric.
- **Baseline discipline** (scientific-ml-fundamentals): the tree must beat the existing bam/statistical product on the QUALITY metric (accuracy + variability + calibration + seam-freeness), not RMSE alone, to earn its opacity cost.

## Tuning & interpretation that matter
- **Early stopping** on a blocked validation fold, with a small learning rate and a large `n_estimators` cap, beats hand-picking the tree count. Regularize against memorizing leaves: raise `min_child_weight` / `min_data_in_leaf`, keep `max_depth` / `num_leaves` modest, set `subsample` / `colsample` < 1.
- **Monotone constraints** (`monotone_constraints`) inject a soft physical prior (e.g. target increases with a driver over its physical range) — a cheap first step toward physics-informed-ml without leaving the tree.
- **Importance caveat.** Default gain/split importance is biased toward high-cardinality features; use permutation importance computed on held-out BLOCKS (or SHAP) when attributing.

## The extrapolation boundary — where trees stop and fusion starts
- Trees fill gaps only where the predict-time covariates fall INSIDE the training envelope (short/medium gaps, in-range regimes). They cannot bridge the large multi-year gaps (~37% of the record, tier T0): there the whole covariate regime is unobserved and a tree returns a flat nearest-leaf constant. Native NA handling fills a missing FEATURE inside a known regime — it does not conjure a target where the regime itself was never observed.
- **Detect out-of-envelope:** at predict time, flag rows whose features fall outside the per-feature training min/max (or into low training density). Do not ship those as tree fills.
- **Hand off** large-gap / cross-regime information to **multi-source-fusion-bias-correction** (satellite + reanalysis carry the signal where the tower is dark). Trees and fusion compose: fusion supplies in-envelope predictors, trees map them locally.

## Success check
Folds are blocked + embargoed (not iid); the model is refit on the target regime (not frozen-global); intervals come from a quantile objective and are handed to calibrated-uq-for-ml for coverage; variability fidelity is reported next to MAE/RMSE; a drought transfer fold is included; out-of-envelope predict rows are flagged, not silently emitted; and the tree is benchmarked against the bam baseline on the quality metric.

## Related
temporal-block-cv (fold construction + the leakage discipline); calibrated-uq-for-ml (turn raw quantiles into calibrated coverage); multi-source-fusion-bias-correction (the large-gap regime trees cannot reach); scientific-ml-fundamentals (baseline + ML-scope discipline); physics-informed-ml (harder constraints than a monotone split); aggregation-jensen-bias (per-level derived quantities); tz-safe-timestamps (the harmonic clock); preflight-parallel (fan out fold x quantile fits).
