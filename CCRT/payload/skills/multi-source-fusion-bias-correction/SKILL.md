---
name: multi-source-fusion-bias-correction
description: Harmonize a gappy in-situ reference series (e.g. a flux tower) with satellite and reanalysis sources into ONE continuous record by bias-correcting each secondary source to the reference over their temporal OVERLAP before fusing — so no step-discontinuity seam appears where sources meet. Assess the defect first (mean bias / scale / distribution shape) with source_agreement, then match the correction to it: linear rescale for a location+scale offset, quantile mapping for a distribution-shape defect. Use when filling multi-year gaps that within-record temporal memory cannot reach (autocorrelation e-fold ≤33 h), blending tower + satellite (MSG/CERES) + ERA5 into one forcing, correcting a systematic offset/scale/distribution difference between sources of different provenance, or whenever you are about to concatenate or splice series from different sources into one variable.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-16).

# multi-source-fusion-bias-correction — carry information across gaps too long for temporal memory

Splicing tower-where-present and satellite/reanalysis-where-not injects a step-discontinuity SEAM at every source boundary: each source carries its own mean bias, scale error, and distribution-shape offset relative to the tower. Bias-correcting each secondary source to the reference over their OVERLAP — before fusion — removes the seam at its cause. It is also the ONLY route that carries information across the multi-year gaps (~37% of one tower record) where within-record autocorrelation (e-fold ≤33 h) is already dead: no tower-only or temporal method can reach a gap spanning years; only a co-located external source that observed the gap can.

## When to invoke
About to fill a tower gap from a satellite/reanalysis series, blend ≥2 provenances into one variable, or concatenate/splice sources — i.e. a `src_full` series is about to enter the forcing without a correction learned against the tower. Also when a source shows a systematic offset / scale / shape difference from the reference.

## Boundary — this is NOT short-gap bridging
≤6 h gaps (~92% of gap events) → closed-form conditional simulation / cosine tail-splice (`gap-fill-imputation`); temporal memory still lives there. THIS skill owns the LARGE-gap / cross-source regime where memory is dead. Two different seams: `gap-fill-imputation` splices chunk-prediction tails of ONE source (cosine, e-fold-scaled width); this skill removes the level/scale/shape offset BETWEEN sources.

## Procedure — assess, then correct (never correct blind)
1. **Co-index & tz-align.** Build one common half-hourly index; pair sources on identical timestamps (`tz-safe-timestamps`). `ref_overlap[i]` and `src_overlap[i]` MUST be the same instant — a misaligned pair learns a garbage correction. Identify each source's overlap-with-reference window and its gap-only span.
2. **Diagnose each source vs the tower.** `source_agreement(a_ref, b_src)` → `{bias, rmsd, corr, n}` (mean source-minus-reference offset, error magnitude, co-variation, paired-sample count). Read `corr` and `n` first.
3. **Gate on correlation & overlap.** Low `corr` ⇒ the source does not track the tower; a bias correction just injects the mean with wrong dynamics — DROP or deprioritize it, don't fuse it. Thin `n`, or an overlap that misses seasons/regimes you will apply to ⇒ the correction is extrapolation; widen the overlap or restrict where you apply it.
4. **Assess the defect SHAPE → pick the method.** Plot ref-vs-src on the overlap (QQ or scatter):
   - straight line, offset + slope only ⇒ location+scale defect ⇒ **linear** (5a).
   - curved / bowed QQ (variance wrong at one end, skew or tail mismatch, clipped ceiling) ⇒ distribution-shape defect ⇒ **quantile map** (5b).
   Prefer linear unless the shape defect is real and material — 2 transparent parameters, preserves shape and trend, extrapolates safely; quantile mapping is more flexible but higher-variance and undefined beyond the overlap's observed range.
5. **Correct each secondary source TO the tower over its overlap, apply to its full span.**
   - **5a linear:** `linear_scale_correct(ref_overlap, src_overlap, src_full)` → `{corrected, a, b, n_overlap}` — fits ref ≈ a + b·src on the overlap, applies a + b·src to the whole source. Inspect `a`,`b`: |b−1| large, or |a| large vs the signal ⇒ weak source, revisit the gate.
   - **5b quantile:** `quantile_map(ref_overlap, src_overlap, src_full, n_q=100)` → corrected array — matches the source's empirical CDF to the reference's over `n_q` quantiles. Clamp application to the overlap's support (QM cannot extrapolate past the quantiles it saw); shrink `n_q` when `n` is thin so tail bins aren't overfit.
   Always correct each source directly to the tower — never chain (ERA5→satellite→tower). Chaining compounds error and hides provenance.
6. **Correct per regime when the defect is regime-dependent.** Radiation bias varies with solar geometry; a single global affine leaves a diel-structured residual seam and distorts diel amplitude (the metric trap — a conditional/global mean loses 43–78% of diel variance). Stratify the fit (hour-of-day or zenith bin; clear vs cloudy), keeping strata large enough for a stable fit / QM.
7. **Correct base variables at native resolution; derive nonlinear quantities after.** Bias-correct SW, LW, Tair, H₂O/RH, wind, pressure directly; compute VPD = f(Tair, H₂O, pamb) per timestamp AFTER correction — never bias-correct VPD or any nonlinear derived variable (Jensen; see `aggregation-jensen-bias`).
8. **Fuse by tiered priority, one realization per timestamp.** Tower observed > best-agreeing corrected satellite > corrected reanalysis (order by `corr`/`rmsd` from step 2). Where sources overlap, PICK the higher-ranked corrected source or use a variance-preserving blend — do NOT point-wise average two sources into a smoothed mean (that flattens variability, the metric trap again). The fused series must be a realistic realization carrying the tower's variability, not the conditional mean.
9. **Enforce physical bounds after correction.** Clamp SW, LW, precip ≥ 0 and SW ≤ clear-sky/TOA; RH ∈ [0,100]; hold SW = 0 at night (correction must not create phantom nighttime radiation). Bounds go on the base variables, before deriving VPD etc.
10. **Preserve long-term trend.** Over 20 yr, stationary quantile mapping can erase a real climate trend the overlap does not represent — correct anomalies (detrend, or delta-mapping) when the reference carries a trend.

## Seam & transfer verification (before shipping)
- **Seam check at every source boundary.** Compare a window just before vs just after each boundary: no persistent level step, and matching diel amplitude / variance. A residual step ⇒ correction incomplete or regime-dependent → redo per-regime (step 6). A ≤6 h edge gap remaining at the join is a tail-splice job (`gap-fill-imputation`), not a bias problem.
- **Validate by transfer to a held-out regime, not in-sample fit.** Hold out an overlap window from a regime unlike the mean state — a held-out drought/anomaly regime (in one tower reconstruction the gap fraction there rose to ~43–52% vs ~5% baseline) — learn the correction on the rest, check it transfers there. Blocked, not random-iid folds (`temporal-block-cv`).
- **Emit provenance + uncertainty.** Tag each filled timestamp with its source and correction method; fusion reclassifies a was-NA large gap into a source-tagged fill — coordinate the canonical T0–T3 tier labels with the tower pipeline (micromet-reconstructor agent / `gap-fill-imputation`). The corrected-source residual over the overlap IS the empirical error model for that source in the gap — hand it to `calibrated-uq-for-ml` for calibrated intervals (bias correction fixes the mean/shape; it does not by itself calibrate spread).

## Functions (`fusion_bias_correct.py`)
Import the three functions below from `fusion_bias_correct.py`:
- `source_agreement(a_ref, b_src)` → `{bias, rmsd, corr, n}` — diagnostic; run first (step 2).
- `linear_scale_correct(ref_overlap, src_overlap, src_full)` → `{corrected, a, b, n_overlap}` — affine correction (step 5a).
- `quantile_map(ref_overlap, src_overlap, src_full, n_q=100)` → corrected array — CDF matching (step 5b).
All three learn on the co-indexed overlap pair and apply to the full source. Proven route: in one tower reconstruction, a ~20-year SW record was rebuilt by fusing tower `Raw` + `MSG` (Meteosat) + `SYN1DEG` (CERES) + `ERA5-Single`, ML-harmonized to the tower, with the same treatment for LW, net radiation, Tair, humidity, wind, pressure, precipitation.

## Success check
Every secondary source is co-indexed and gated on `corr`/`n`; the correction method matches the diagnosed defect (linear for offset+scale, quantile for shape); no level step or amplitude change across any source boundary; physical bounds hold and nights are zero; the correction transfers to the held-out drought fold; each timestamp carries a source/method provenance tag and a calibrated interval.

## Related
`gap-fill-imputation` (short-gap / same-source splice boundary) · `temporal-block-cv` (blocked transfer folds) · `calibrated-uq-for-ml` (coverage on the fused product) · `tz-safe-timestamps` (co-indexing) · `aggregation-jensen-bias` (derive nonlinear vars after correction) · `scientific-ml-fundamentals` (benchmark vs baseline, leakage) · `physics-informed-ml` / `biosphere-atmosphere-flux-exchange` (physical-closure sanity on radiation/energy).
