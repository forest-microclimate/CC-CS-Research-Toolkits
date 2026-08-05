---
name: temporal-qc-outlier-detection
description: QC / outlier-detection for autocorrelated environmental time series (tower met, flux, VPD, radiation) — separate spike vs drift vs level-shift into distinct matched passes, stratify by same-half-hour bin so the diurnal cycle is preserved, not mass-flagged, use a windowed median with a POOLED MAD, and layer detectors that degrade gracefully. Use when flagging outliers/spikes/drift in an environmental series, building a QC pipeline, or when a single rolling-window (Hampel) filter mass-flags dawn/dusk transitions or whole climate-anomaly years.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.

# temporal-qc-outlier-detection — QC autocorrelated env series without laundering real signal

## When to invoke
Outlier/spike/drift flagging or a QC pipeline on an autocorrelated environmental series (tower met, flux, VPD, radiation); a single rolling/Hampel filter mass-flagging real diurnal transitions or anomaly years.

## Separate the failure modes into DISTINCT passes
- Spikes vs drift vs level-shifts each need a MATCHED method + window length. A single Hampel window is a length compromise — short windows miss drift; long windows mass-flag real dawn/dusk transitions. Keep them as three separate matched passes rather than collapsing into one tuning problem.

## Kill the diurnal confound
- Raw temporal windows > ~1.5 h confound the diurnal cycle → use SAME-HALF-HOUR-BIN stratification for anything longer.
- Near-zero nighttime values are physically expected → apply an ABSOLUTE FLOOR (leave a point unflagged when BOTH the obs and the rolling median fall below it).

## Reference design: windowed MEDIAN, pooled MAD
- MEDIAN from a ±45-day day-of-year window, POOLED ACROSS YEARS (seasonal context, no interannual bias) — do NOT pool years for the median or you mass-flag genuine climate-anomaly years (e.g. ENSO drought).
- MAD (dispersion) pooled across ALL years within a (bin, month) stratum — sensor dispersion is stationary, so pooling is valid and stabilizes the threshold.
- Require a minimum N years/obs in the window; else widen the threshold or mark "insufficient-reference" rather than flag blindly.

## Layer detectors that degrade gracefully
- Cross-height ENSEMBLE residuals (MAD across sensors) + CUSUM on those residuals (flag runs ≥4) needs ≥N heights; FALL BACK to the per-sensor same-bin filter when fewer sensors are available.

## Success check
Spike/drift/level-shift each in a separate matched pass; windows >1.5 h bin-stratified + a night floor; median windowed (not pooled across years), MAD pooled within (bin,month); insufficient-reference marked not blind-flagged; detectors fall back gracefully.

## Related
tz-safe-timestamps (diel binning must be tz-correct); gap-fill-imputation (QC before you fill); mgcv-temporal-gam / temporal-block-cv; aggregation-jensen-bias.
