---
name: brms-hierarchical-fitting
description: Fit hierarchical / multilevel Bayesian models in brms + cmdstanr on autocorrelated ecological time series — two-scale temporal AR, custom latent effects via stanvars, diagnosing stiff-geometry chain splits, and choosing variance-vs-transform. Use when building a brms/Stan hierarchical model, adding temporal AR structure, hitting stalled/split chains or high Rhat, deciding a partial-effect plot, or when a random-slope/interaction verdict is at stake.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-11).

# brms-hierarchical-fitting — hierarchical Bayes on autocorrelated eco data

## When to invoke
Building a brms/cmdstanr multilevel model on time-series/clustered data; adding AR; chains stalling, splitting, or Rhat high; partial-effect prediction; variance-vs-transform decisions.

## Two-scale temporal AR
- Within-day AR(2) via `ar(time, gr, p=2)` + a CUSTOM latent day-to-day AR(1) daily effect via `stanvars` (non-centered; inject at the likelihood `position="start"` so within-day residuals form AFTER the day effect).
- RESET AR blocks at TRUE sampling gaps (>~7-day breaks), not at generic season boundaries.
- MOTIVATE the AR order from the iid-random-effect residual ACF (lag2 ≈ lag1² ⇒ AR(1) suffices).

## Prediction / partial effects
- `posterior_epred` is R-side and IGNORES `stanvars` terms (correct for partial-effect plots) — but `validate_newdata` still REQUIRES the AR index/series columns in every prediction grid: inject dummies.
- `s(x, by=continuous)` breaks Stan fits (thin-plate null space carries the continuous main effect ⇒ non-identified, chains in different modes, Rhat 3+). mgcv's REML pins the ridge; Stan's prior can't — use parametric `poly(x,2)` for Stan-bound models.

## Diagnosing stiff geometry
- 2-fast/2-slow chain SPLIT (some chains stall in warmup at ~zero progress; detect via flat per-chain CSV size) = stiff hierarchical geometry. Fix: `init=0.2` (small inits) + DROP the finest-grained (per-unit) random slopes (the main funnel, weakly identified) BEFORE touching priors/treedepth.
- Project ETA from the POST-adaptation rate, not the early-warmup rate — early warmup (identity metric) is the slowest stretch; rate jumps 2–3× after the mass-matrix adaptation windows, so extrapolating the early rate over-estimates ETA.
- cmdstanr can't fork — parallelize PROCESSES (chains), not threads. Check divergences / Rhat / ESS BEFORE trusting any marginal contrast; floor a sigmoid steepness so it can't collapse to a degenerate near-step.

## Variance vs transform
- A log-response can win huge ΔAIC (e.g. −3969) yet that's an ERROR-STRUCTURE (heteroscedastic-variance) win, NOT mean curvature. Model the variance explicitly (`σ ~ s(hour)` + Student-t) on the IDENTITY scale rather than transforming the response, when the mean's interpretability matters.

## Success check
AR order justified from residual ACF + reset at true gaps; Stan fits keep continuous main effects parametric (no `s(x,by=continuous)`); chains converged (Rhat/ESS/divergences checked, not extrapolated); variance modeled explicitly where the response scale matters.

## Chunked fits for long records
- If the model is too complex to fit/predict over the whole record, chunk into ~20–90-day pieces — but the fill PREDICTIONS must use OVERLAPPING long tails + SPLICE, never butt-joined at chunk edges (else seam-offset artifacts). See `gap-fill-imputation`.

## More Bayesian workflow (hard-won)
- A wide-magnitude RAW response FUNNELS the sampler (Rhat ~4, 100s of divergences) — fix the GEOMETRY: standardize the response AND add a log-linear scale submodel (`sigma ~ x`); standardizing alone can leave the funnel. `adapt_delta` 0.9–0.95 + small `init` (0.2) are secondary. A Gamma IDENTITY-link fails to sample at large magnitude — reparameterize to smaller units or Gaussian-on-standardized.
- A single-parameter skew family (Gamma/Beta) ties variance to the mean/skew and UNDER-fits conditional SD in sparse regions — decouple with a distributional model (separate `mu`/`sigma` smooths) or a location-scale-shape family (shash, skew-t).
- max-treedepth warnings = EFFICIENCY only (a smooth can be fine at 25% hits); divergences = VALIDITY. Reserve `adapt_delta` increases for divergences, not treedepth warnings.
- SEQUENCE refinements (fix mean → fix variance → re-check residual skew; the skew submodel is often then unnecessary); COMPILE+sample a tiny case FIRST before a multi-hour fit. Per-refit gate: Rhat<1.01, 0 divergences, RE-SD estimable, ESS adequate, pp-check of sd/skew/kurtosis ~0.5, LOO improvement recorded.
- Ship the fitted `.rds` WRAPPER (fit + data + transforms), lock transforms; downstream reads the wrapper instead of casually re-running multi-hour fits.

## Related
mgcv-temporal-gam (the frequentist counterpart + k/AR); gap-fill-imputation (chunk+splice, source tiering); temporal-block-cv (+ cluster-bootstrap for the rare-within-cluster arbiter role); aggregation-jensen-bias; preflight-parallel (chains as processes).
