# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""Sidecar for calibrated-uq-for-ml.

Calibration diagnostics + split-conformal correction (SKILL.md ## Diagnose,
## Fix). A model whose 95% interval covers 52% of held-out truth is worse than
useless — it lies confidently across the multi-year gaps where the user needs
it to say "I don't know". These functions measure coverage honestly and widen
intervals to hit nominal by distribution-free conformal calibration.
"""
import numpy as np


def coverage_report(y_true, lower, upper, nominal=0.95):
    """Empirical coverage + interval width vs the nominal level.

    Returns {nominal, coverage, mean_width, median_width, n}. coverage far below
    nominal = overconfident (the cov95 0.52 failure); far above = wastefully
    wide. Compute on HELD-OUT data under blocked temporal CV, never in-sample.
    """
    yt = np.asarray(y_true, float)
    lo = np.asarray(lower, float)
    hi = np.asarray(upper, float)
    m = np.isfinite(yt) & np.isfinite(lo) & np.isfinite(hi)
    yt, lo, hi = yt[m], lo[m], hi[m]
    inside = (yt >= lo) & (yt <= hi)
    return {
        "nominal": float(nominal),
        "coverage": float(np.mean(inside)) if yt.size else np.nan,
        "mean_width": float(np.mean(hi - lo)) if yt.size else np.nan,
        "median_width": float(np.median(hi - lo)) if yt.size else np.nan,
        "n": int(yt.size),
    }


def pit_values(y_true, samples):
    """Probability-integral-transform values for a calibration histogram.

    samples: array (n_obs, n_draws) of predictive draws. PIT_i = fraction of
    draws <= y_true_i. A calibrated predictive gives PIT ~ Uniform(0,1);
    U-shaped = too narrow, dome = too wide. Feed the return to a histogram.
    """
    yt = np.asarray(y_true, float)
    S = np.asarray(samples, float)
    if S.ndim != 2 or S.shape[0] != yt.size:
        raise ValueError("samples must be (n_obs, n_draws) aligned to y_true")
    return np.array([np.mean(S[i] <= yt[i]) for i in range(yt.size)])


def conformal_calibrate(cal_true, cal_lower, cal_upper, nominal=0.95):
    """Split-conformal width multiplier that restores nominal coverage.

    Fit on a CALIBRATION split disjoint from train and test. Returns
    {q, multiplier, method}: scale each interval's half-width by `multiplier`
    (symmetric conformalized quantile regression) so held-out coverage meets
    nominal distribution-free. Apply with apply_conformal(). Widen, don't trust.
    """
    yt = np.asarray(cal_true, float)
    lo = np.asarray(cal_lower, float)
    hi = np.asarray(cal_upper, float)
    m = np.isfinite(yt) & np.isfinite(lo) & np.isfinite(hi)
    yt, lo, hi = yt[m], lo[m], hi[m]
    n = yt.size
    if n < 2:
        return {"q": np.nan, "multiplier": np.nan, "method": "insufficient-n"}
    mid = 0.5 * (lo + hi)
    half = 0.5 * (hi - lo)
    half = np.where(half > 0, half, np.nan)
    score = np.abs(yt - mid) / half              # conformity score
    score = score[np.isfinite(score)]
    level = np.ceil((n + 1) * nominal) / n        # finite-sample correction
    level = min(level, 1.0)
    q = float(np.quantile(score, level))
    return {"q": q, "multiplier": q, "method": "split-conformal-symmetric"}


def apply_conformal(lower, upper, multiplier):
    """Widen intervals by the conformal multiplier about their midpoint."""
    lo = np.asarray(lower, float)
    hi = np.asarray(upper, float)
    mid = 0.5 * (lo + hi)
    half = 0.5 * (hi - lo) * multiplier
    return mid - half, mid + half
