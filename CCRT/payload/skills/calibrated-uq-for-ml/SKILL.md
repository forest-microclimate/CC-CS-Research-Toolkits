---
name: calibrated-uq-for-ml
description: Produce AND validate calibrated predictive uncertainty for an ML model — verify a 95% interval actually covers 95% of HELD-OUT truth (empirical coverage under blocked temporal CV, PIT histograms), then repair under-coverage with distribution-free split-conformal widening. Covers quantile regression forests, split-conformal prediction, deep ensembles, and GP posteriors. Use when a model emits predictive intervals / quantiles / error bars / a posterior and you are about to report or ship them; when cov95 looks too good or intervals look suspiciously narrow; when filling a large / multi-year gap where the model must be able to say 'I don't know' with a wide honest interval rather than hallucinate confidently; or whenever point accuracy (RMSE/MAE) is being reported for a product whose deciding metric includes calibration.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# STATUS: CURRENT (2026-07-16).

# calibrated-uq-for-ml — predictive intervals you can trust

A model that reports a 95% interval covering only 52–77% of held-out truth is confidently wrong — one tower height reconstruction did exactly this (cov95 0.52 xgb, 0.77 spline). Point error (RMSE/MAE) is silent about it; the deciding metric here is calibration + variability fidelity, not accuracy alone. This skill produces intervals, tests their coverage on held-out data, and repairs the gap distribution-free.

The functions this skill calls ship in the named script `uq_calibration.py`: `coverage_report`, `pit_values`, `conformal_calibrate`, `apply_conformal`.

## When to invoke
WHEN a model emits intervals / quantiles / σ / a posterior AND you are about to report, plot, or ship them ⇒ diagnose coverage FIRST (§2).
WHEN cov95 reads high in-sample, or intervals look tight ⇒ you are almost certainly measuring on training data; move to held-out CV.
WHEN filling a T0 multi-year gap ⇒ the interval must widen honestly out-of-support, not stay narrow (§4).

## 1 — Produce intervals (pick a method that emits uncertainty)
A point model (plain RF / xgboost mean) emits NO interval — wrap it (§3) or switch method.
- **Quantile regression forests** — fit the quantile loss at τ=0.025 & 0.975 directly; a natural first choice (in one tower reconstruction, trees beat the bam on 45/46 folds). Caveat: quantiles saturate at the training range → they do NOT widen out-of-support, so weak for T0.
- **Split-conformal** — wraps ANY point or interval model; distribution-free marginal guarantee; the repair of choice (§3).
- **Deep ensembles** — spread across N independently-trained nets; captures epistemic (out-of-support) uncertainty → grows in gaps; usually still under-dispersed alone → conformalize on top.
- **GP posteriors** — closed-form predictive σ that grows away from data (good for T0); calibrated ONLY if kernel + noise are well-specified → still PIT-check.

## 2 — Diagnose (held-out, never in-sample)
Coverage must be measured on blocked-CV held-out folds — iid CV leaks across the ≤33 h autocorrelation and inflates coverage. See temporal-block-cv for the folds + embargo.
1. **Coverage + width.** `coverage_report(y_true, lower, upper, nominal=0.95)` → {nominal, coverage, mean_width, median_width, n}. Target coverage ≈ nominal. Read width ALONGSIDE it: a method that widens everything to 100% coverage is useless — width is the counterweight that keeps intervals sharp.
2. **PIT histogram** (needs a full predictive sample, not just endpoints). `pit_values(y_true, samples)`, `samples` shape [n_obs, n_draws] → per-obs PIT ∈ [0,1]. Calibrated ⇒ PIT ~ Uniform(0,1). The shape names the defect:
   - ∪-shaped (mass piled at 0 & 1) = UNDER-dispersed / overconfident — the failure mode in the tower reconstruction above.
   - ∩-shaped (mass piled at 0.5) = OVER-dispersed / intervals too wide.
   - sloped or shifted = biased mean, not a spread problem — fix the model, not the interval.

## 3 — Fix (split-conformal widening, distribution-free)
Repairs marginal coverage with no distributional assumption. Needs a CALIBRATION set disjoint from BOTH train and test — a held-out block, embargoed per temporal-block-cv.
1. `conformal_calibrate(cal_true, cal_lower, cal_upper, nominal=0.95)` → {q, multiplier, method}: finds the half-width `multiplier` that rescales the raw interval to hit nominal coverage on the cal set.
2. `apply_conformal(lower, upper, multiplier)` → (lo, hi): rescale the TEST / production intervals with that multiplier.
3. Re-run `coverage_report` on (lo, hi) vs held-out y_true ⇒ confirm coverage ≈ nominal. If still off, cal and test were not exchangeable (§5).

## 4 — The "I don't know" rule for large gaps
Across a T0 multi-year gap the model extrapolates far from any training support (within-record memory e-folds in ≤33 h and carries zero information across years); epistemic uncertainty dominates. A calibrated interval there is WIDE — honest ignorance beats a confident hallucination.
- For T0, prefer a method whose variance GROWS out-of-support (GP posterior, deep ensemble) over quantile forests (which saturate at the training range).
- Tie interval width to the provenance tier: T0 (unreconstructable) gets the widest intervals. A T0 fill emitted with a narrow interval is a red flag, not a success.

## 5 — Exchangeability caveat (why conformal coverage can still fail)
Split-conformal guarantees MARGINAL coverage and assumes cal & test are exchangeable. The drought transfer fold — a held-out drought/anomaly regime — is nonstationary; cal blocks from wetter baseline years are NOT exchangeable with it.
- Calibrate on a block that resembles the target regime, or report that the guarantee holds in-regime only and widen further across a regime shift.
- Conformal fixes coverage ON AVERAGE, not conditionally: it can be right marginally yet miss in the tails or inside the drought. Run `coverage_report` WITHIN the drought fold separately, not just pooled.

## Success check
- Coverage computed on HELD-OUT blocked-CV folds (never in-sample); cov95 ≈ 0.95, not 0.52–0.77.
- PIT histogram rendered and inspected (≈ uniform, not ∪-shaped).
- BOTH coverage and width reported — sharp AND calibrated, not one at the other's expense.
- If conformal applied: post-hoc `coverage_report` re-confirms nominal, and the drought fold is checked on its own.
- T0 intervals are visibly wide; no confidently-narrow multi-year fill.

## Related
temporal-block-cv — the held-out folds + embargo that coverage and the cal set require; never compute coverage in-sample. tree-ensembles — quantile regression forests done right. scientific-ml-fundamentals — uncertainty-by-default, benchmark-against-baseline. gap-fill-imputation / the micromet-reconstructor agent's provenance tiers — where T0 width lives. Deciding metric = quality (accuracy + variability fidelity + calibration + seam-freeness), never RMSE alone — the metric trap where a conditional mean loses 43–78% of diel variance rewards exactly the overconfident over-smoothing this skill catches.
