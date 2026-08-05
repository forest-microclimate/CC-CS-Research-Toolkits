---
name: gap-fill-imputation
description: Impute / gap-fill autocorrelated time series (met, flux, drivers) with brms or mgcv — CHUNK long records but predict with OVERLAPPING long tails and SPLICE (splice the overlaps rather than naive-concatenating, which gives seam-offset artifacts), tier sources (measured > filled-of-measured > modeled), and verify the filled series (native resolution / no step-doubling, diel-correct, provenance-tagged). Use when gap-filling or imputing a time series, chunking a big model fit/predict, splicing chunk predictions into a continuous series, or assembling a forcing/driver from mixed sources.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# gap-fill-imputation — chunk+splice, source tiering, verify the fill

## When to invoke
Gap-filling/imputing a time series; a model too big to fit/predict in one pass (must chunk); splicing chunk predictions; building a forcing/driver from mixed data sources.

## Chunked prediction — OVERLAP + SPLICE (HARD-WON; a lost lesson)
- When a brms/mgcv model is too complex to fit/predict over the whole record, CHUNK into ~20–90-day pieces.
- CRITICAL: predict each chunk with LONG TAILS extending BEYOND its fill window (overlap adjacent chunks), then SPLICE — blend/crossfade the overlap — into the final series. Splice at the boundaries rather than naively concatenating chunk predictions.
- WHY: independently-predicted chunks have edge effects at their ends, so butt-joined predictions carry OFFSET / discontinuity ARTIFACTS at every seam. Long tails + splicing make the seam invisible. (This was hard-won and then LOST on the biggest/longest run — the tair/H2O/CO2 Bayesian imputation — producing seam offsets.)
- VERIFY continuity across every seam explicitly (no step at the boundary; the overlap regions of adjacent chunks agree before blending).

## Source tiering (precedence)
- Prefer MEASURED > gap-fill-OF-measured (tower-derived) > MODELED (e.g. Open-Meteo). Build an EXPLICIT precedence: measured → real half-hourly fill → model fallback (last resort only).
- Check a real native-resolution fill EXISTS before falling to a coarse model. (Documented bug: `x_filled` was NA for a window ⇒ the builder fell straight to an HOURLY model product ⇒ step-doubled SW/PAR — while a real half-hourly `x.fill` was available all along.)

## Verify the filled series (before trusting it downstream)
- Resolution: keep native resolution — consecutive timestamps with identical values flag step-doubling (an HOURLY or coarser source duplicated to the fine grid); check consecutive-equal daytime pairs per variable.
- Diel: a sun-driven variable's time-of-peak lands at solar noon (see tz-safe-timestamps); daytime fully filled, no NA remaining.
- Provenance: TAG every value's source (measured / filled / modeled) and keep it.

## Fitting mechanics (hard-won)
- SPLICE with a 0→1 linear/cosine weight across the overlap, not a hard boundary. PREFER a single GLOBAL fit where feasible (it structurally eliminates seams); if you chunk ONLY for memory, evaluate the SAME fitted model piecewise (no splice needed) + keep a few-step overlap as a continuity check.
- Target-NA and predictor/helper-NA rarely coincide — break a block only when EITHER group INDIVIDUALLY exceeds its OWN gap tolerance. An `AND` of both forces coincidence ⇒ excludes most fillable gaps ⇒ near-zero fills despite abundant data.
- Predict for ALL block rows (gaps + non-gaps), flag gaps, THEN mask where observations exist — predict across all rows first, filtering to gaps afterward.
- Order: `drop_na()` FIRST → compute scaling (mean/sd) → scale; apply the TRAINING scaling params to prediction data, reusing them rather than recomputing on it (NAs bias scaling params).
- Progressive gap-size LADDER: iterate with monotonically increasing gap tolerance AND block length (small/short first → large/long last) to catch gaps of every size.
- Tiered reconstruction is GLOBAL, not time-local: climatology backbone (diel+season+trend) + per-timestep anomaly → global anchor fill → shape-transfer model of Δscalar↔Δdriver fit on a stratified subsample across ALL good years → predict (the Δ-relationship is global structure).

## Success check
Every chunk seam continuous (overlap+splice, offsets checked, not butt-joined); source precedence enforced (measured>filled>modeled) with the fallback truly last; filled series verified (native resolution / no step-doubling, diel time-of-peak correct, no daytime NA, provenance tagged).

## Before you impute (hard-won)
- PREFER sourcing the real value over imputing — and if a "missing covariate" is never consumed by the target model, it isn't missing (check which columns the model actually uses before building any imputation patch).
- Off-grid logger timestamps (odd-minute sampling) give ~0% time-join matches — round BOTH sides to the sampling grid (nearest-10-min) before joining.
- Recover-then-audit: when one record is silently dropped, audit for ALL others lost by the same mechanism (a text-key/window bug silently dropped many series).

## Related
brms-hierarchical-fitting + mgcv-temporal-gam (the fitters + chunk-splice consumers); tz-safe-timestamps (diel/resolution verification); temporal-block-cv (evaluate the fill honestly); aggregation-jensen-bias (don't average away the resolved structure); temporal-qc-outlier-detection (QC before you fill).
