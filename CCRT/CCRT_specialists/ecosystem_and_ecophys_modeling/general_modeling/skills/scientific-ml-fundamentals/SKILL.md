---
name: scientific-ml-fundamentals
description: The discipline layer for any scientific-ML or data-driven model on a tall-forest flux-tower forcing reconstruction — scope ML to where it earns its place (large multi-year gaps, multi-source fusion, joint time×height reconstruction, NOT short-gap bridging), benchmark every model against the existing brms/mgcv product before trusting it, score gap-fill on a QUALITY composite (accuracy + variability fidelity + calibrated coverage + seam-freeness) never RMSE alone, and ship calibrated uncertainty by default. Use when starting, scoping, or evaluating any ML or data-driven gap-fill, fusion, reconstruction, or emulator model; when choosing an error metric or reporting model skill; when about to split data, optimize RMSE or MAE, or ship a point prediction; or when deciding whether ML is the right tool for a given gap regime.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-16).

# scientific-ml-fundamentals — earn ML's place, then score it on the right metric

The default ML reflex — random split, minimize RMSE, ship a point prediction — leaks across autocorrelation, rewards an over-smoothed mean that flattens the diel signal, and pays nothing down on ML's opacity cost. This skill is the discipline that keeps a data-driven flux-tower forcing product honest, benchmarked, and shippable.

This skill's scorer and helpers (`quality_report`, `variability_fidelity`, `seam_magnitude`) ship in the named script `quality_metrics.py` — run `python3 <skill_dir>/quality_metrics.py` (not auto-loaded).

## When to invoke
Starting, scoping, or judging any ML / data-driven model for the tower forcing — gap-fill, multi-source fusion, joint time×height reconstruction, or emulator/surrogate. Also the moment you pick an error metric, size a train/test split, or call a point prediction "done."

## The discipline (decision order)

1. **Scope gate — is this an ML job at all?** Classify the gap regime before reaching for ML; it is not a universal upgrade.
   - Short gaps ≤6 h (~92% of gap events) → NOT ML. Closed-form conditional simulation (OU / Brownian-bridge / GP / Kalman simulation-smoother) already wins on edge-continuity and traceability — leave it to the Bayesian gap-fill strand.
   - Large multi-year gaps (~37% of record, tier T0) → ML + multi-source fusion. Within-record memory e-folds ≤33 h, so it carries zero information across a multi-year span; fusion is the only signal source.
   - Joint high-time × high-height field (half-hourly × a fine vertical grid) → ML spatiotemporal; the statistical engine walls on the joint surface.
   - Detectable trigger: gap length + whether the incumbent pipeline already emits a non-NA fill. If it does and the gap is short, ML re-fights a settled battle and trips the CLARITY/TRACEABILITY mandate.

2. **Baseline first — name what ML must beat.** WHEN proposing any ML model → name the incumbent it must beat (the existing brms/mgcv product for that variable/regime) BEFORE fitting. ML carries an opacity cost against CLARITY/TRACEABILITY/REPRODUCIBILITY; it earns that cost only by a clear win on the QUALITY composite (step 4), not a marginal RMSE tie. The win can be real — xgboost beat the `t2` bam on 45/46 height folds when refit locally. Run baseline and ML head-to-head through the SAME `quality_report` on the SAME blocked folds; if ML doesn't win the composite, keep the statistical product.

3. **Evaluate without leaking.** WHEN building folds → defer to **temporal-block-cv**: blocked contiguous folds + an embargo ≈ the autocorrelation length, never a random iid split (it leaks across the ≤33 h memory and reports optimistic, wrong skill). Then validate by TRANSFER to a held-out nonstationary regime — a drought/anomaly regime, where the gap fraction rises to ~43–52% vs ~5% baseline, is the named transfer fold — not in-sample fit. A model that only interpolates its own regime is not a reconstruction.

4. **Score with the QUALITY composite — never RMSE alone.** The metric trap: RMSE/MAE are minimized by the conditional MEAN, which is over-smoothed — in one tower reconstruction it lost 43–78% of diel variance. A model can win RMSE and be useless as a forcing realization (wrong variance, flattened diel cycle, seam jumps). Score four axes at once → `quality_report(y_true, y_pred, filled_mask=, lower=, upper=, nominal=0.95, period=)` (see next section). The product must be a realistic *realization*, not the conditional mean.

5. **Ship calibrated uncertainty, not a point.** Every forcing product ships predictive intervals — a point prediction is not shippable, because the deciding metric includes coverage and the T0 fills must carry their uncertainty honestly into a mechanistic canopy/land-surface model. Defer the interval mechanics (quantile regression forests, conformal, deep ensembles, PIT recalibration) to **calibrated-uq-for-ml**. Feed the resulting `lower`/`upper` into `quality_report` so coverage is scored, not assumed. Why it is not optional: in one tower reconstruction, height interpolation landed cov95 0.52–0.77 — badly under-covered — so intervals are recalibrated, never trusted raw.

## The QUALITY metric — four axes, one report
`quality_report(y_true, y_pred, filled_mask=None, lower=None, upper=None, nominal=0.95, period=None)` returns one dict scoring all four axes; evaluate on the FILLED region (pass `filled_mask`). Read every axis before calling a model good — a single-axis pass is the trap.

- **Accuracy** — `rmse`, `mae`, `bias`. Necessary, never sufficient. Low RMSE with a poor variability ratio *is* the metric trap, not a good model.
- **Variability fidelity** — `variability.sd_ratio`, `variability.diel_amp_ratio` (or directly via `variability_fidelity(y_true, y_pred, period=)`). Target ≈ 1.0. sd_ratio < 1 = over-smoothed; the 43–78% diel-variance loss surfaces as sd_ratio and diel_amp_ratio falling well below 1. Pass `period` = samples per day (48 for half-hourly) so the diel amplitude is measured on the right cycle.
- **Calibrated coverage** — `calibration.coverage` vs `calibration.nominal`, plus `calibration.mean_width` (requires `lower`/`upper`). coverage should ≈ nominal (0.95); the 0.52–0.77 range is the failure to avoid. Narrow intervals that miss coverage are worse than honest wide ones.
- **Seam-freeness** — `seam.seam_ratio`, `seam.n_seams` (or directly via `seam_magnitude(y_pred, filled_mask)`). Compute chunking/discretization must not leave a step the physical signal lacks — no butt-join; use a cosine tail-splice with e-fold-scaled width. seam_ratio ≈ 1 means fill↔observed boundary jumps match the natural signal step; ≫ 1 flags an artifact.

## Ship gate
An ML forcing product ships only when ALL hold: (a) the regime is in ML's scope, not short-gap (step 1); (b) it beat the brms/mgcv baseline on the composite, same folds (step 2); (c) folds were blocked + embargoed and it held up on the drought transfer fold (step 3); (d) `quality_report` shows adequate accuracy AND sd_ratio/diel_amp_ratio ≈ 1 AND coverage ≈ nominal AND seam_ratio ≈ 1 — not RMSE alone (step 4); (e) intervals are calibrated, not raw (step 5). Miss any one → not shippable; report which axis failed.

## Related
- **temporal-block-cv** — the leakage-safe blocked-CV + embargo discipline and the fold constructor step 3 defers to; also the honest-metric philosophy for imbalanced data.
- **calibrated-uq-for-ml** — quantile / conformal / deep-ensemble interval construction + PIT recalibration (step 5); produces the `lower`/`upper` that `quality_report` scores for coverage.
- **gap-fill-imputation** — the closed-form / statistical strand that owns short gaps and the cosine tail-splice discipline (the step-1 boundary and the seam target).
- **physics-informed-ml** — constraint-based learning for the mechanism-interior mapping; shared with the ml-hybrid-process-modeler agent where fluxes generate the interior profile.
- **aggregation-jensen-bias** — when scoring a nonlinear quantity (VPD, fluxes), compute-then-average at native resolution; don't average the inputs first.
