---
name: aggregation-jensen-bias
description: Avoid Jensen-inequality bias when aggregating a nonlinear quantity from averaged inputs — compute-then-average at native resolution, keep the tails, and treat temporal vs spatial spread as DISTINCT marginals (keep them separate rather than collapsing to a single per-bin median or sum). Use when averaging/binning/aggregating any quantity that is nonlinear in its inputs (energy-balance fluxes, wind speed, ratios, back-transformed fits), when calibrating across sensors/sites where the disagreement IS the signal, or when a mean-state summary might hide heterogeneity.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# aggregation-jensen-bias — F(mean) ≠ mean(F); keep the marginals

## When to invoke
Aggregating/binning/averaging a quantity nonlinear in its inputs; cross-sensor / cross-site calibration where spread is the science; any "compute at a mean state" shortcut.

## The core rule
- F(x̄) ≠ mean(F(x)) whenever F is nonlinear — bias ≈ ½·F″·σ² (+ higher moments under skew). So COMPUTE-THEN-AVERAGE at native high frequency and KEEP THE TAILS; averaging inputs first injects a systematic, magnitude-growing bias.
- Recurring instances: energy-balance fluxes are convex in leaf-T (F(T̄)≠Σwᵢ·F(Tᵢ) — the "determine-at-finest, aggregate-as-outcome" rule); scalar wind √(ū²+v̄²) UNDER-estimates mean(√(u²+v²)) by the within-window variance; a log-fit + exp back-transform biases a ratio high.

## Temporal vs spatial are DISTINCT marginals
- Cross-sensor/site (SPATIAL) spread and per-sensor (TEMPORAL) fluctuation are different Jensen marginals — keep each as its own marginal rather than collapsing to a single per-hour median or summing them naively.
- SPATIAL facet is static/structural (predictable from geometry, e.g. sun position) — treat structured diel disagreement as CONFIRMATION, not discovery. TEMPORAL facet is dynamic (induction/stomatal lags) — the static ½F″σ² correction is WRONG for it.
- TAG every aggregation as "temporal", "spatial", or "joint"; the correction/interpretation differs.

## Calibration must preserve the signal, not launder it
- When cross-instrument disagreement IS the science, pool ONLY the genuinely-shared terms (e.g. above-canopy spectral gains) and keep the microsite/FOV/heterogeneity term FREE. Pooling the heterogeneity term erases the very signal you're after.

## Plotting skewed/heteroscedastic spread
- For per-bin variance/CV/sd of skewed signals, default to a quantile-regression median + Q25/Q75 envelope (+ hex density), NOT a GAM mean (biased high under right-skew, and it hides heteroscedasticity). Drive the decision off a rank metric (Spearman); use a GAM mean only after a symmetry check.

## Success check
No nonlinear quantity computed at a mean state it's nonlinear in; aggregation done compute-then-average at native resolution with tails kept; temporal/spatial/joint tagged; calibration keeps the heterogeneity term free; skewed spread shown via quantiles not a mean smooth.

## Quantifying the bias (hard-won)
- Partition spatial+temporal ANOVA-style rather than double-counting: a cell averaged over space AND time carries spatial + temporal + interaction variance — use `σ²_eff = σ²_temporal + (1 − cor_st)·σ²_spatial` (empirical cor_st ~0.3–0.6), NOT the plain sum.
- The static `½·f″·σ²` correction is valid ONLY for the SPATIAL (quasi-steady) facet; the TEMPORAL facet is DYNAMIC — process response times (qE 15–60 s, RuBP 2–3 min, stomata minutes, leaf thermal mass) low-pass-filter fluctuations, so steady-state can OVER-estimate integrated photosynthesis ~35%/day. Weight temporal variance by a transfer function `H(ω)=1/(1+(ωτ)²)`.
- Propagation choice by variance SIZE: two-point mean+var cuts Jensen bias ~10× vs mean-only; use 3–5-node Gauss–Hermite / MC / full-distribution when σ is large vs the response range (right-skewed canopy light ⇒ usually the latter).
- Change-of-support: rescale point/boom variance to the true footprint via a decorrelation length L — `σ²_foot ≈ σ²_boom·(1−e^{−d_foot/L})/(1−e^{−d_boom/L})` (large L ⇒ boom OVER-states footprint variance).
- Calibration is COUPLED to Jensen: use an errors-in-variables likelihood (latent true flux) to avoid attenuation bias.

## Smooth-then-combine & validation (hard-won)
- smooth-then-combine ≠ combine-then-smooth: fitting separate smooths and multiplying/adding them (`s(P)·A + s(I)·B`) is BIASED vs fitting the combined target directly (penalization widens the gap) — use the empirical conditional mean of the COMBINED quantity when it feeds a downstream model.
- Generating on a transformed scale (logit/log/cbrt) then back-transforming injects Jensen bias — if the quantity is an INPUT to another model, model it on the NATIVE scale, or draw on the link scale and back-transform EACH DRAW then average (unbiased by simulation).
- VALIDATE conditional bias by subgroup/tertile, never aggregate-only (an aggregate-unbiased fit can be strongly conditionally biased). Aggregate to the level where the signal LIVES (91% between-group variance ⇒ aggregate to the group, not the sub-unit — avoids pseudoreplication). Draw CI bands as bound-respecting 5–95% quantile envelopes, not symmetric mean±σ (which spills past physical limits).

## Related
gap-fill-imputation (don't average away resolved structure); temporal-qc-outlier-detection; mgcv-temporal-gam (quantile vs GAM-mean for skewed scatter).
