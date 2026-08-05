# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""Sidecar for scientific-ml-fundamentals.

The gap-fill QUALITY composite (SKILL.md ## The quality metric). RMSE alone
rewards the over-smoothed conditional mean and hides three failures a
reconstruction must not have: lost variability, wrong uncertainty, visible
seams. quality_report() scores all four axes at once so a model is selected on
what matters, not on RMSE.
"""
import numpy as np
import pandas as pd


def variability_fidelity(y_true, y_pred, period=None):
    """Ratio of reproduced to observed variability (1.0 = faithful, <1 = smoothed).

    Returns {sd_ratio, diel_amp_ratio}. sd_ratio = sd(pred)/sd(true) over all
    finite pairs. diel_amp_ratio (only if period given, e.g. 48 for half-hourly
    daily cycle) = mean within-period peak-to-trough range of pred / of true —
    the direct check for the 43-78% diel-variance loss of a conditional mean.
    """
    yt = np.asarray(y_true, float)
    yp = np.asarray(y_pred, float)
    m = np.isfinite(yt) & np.isfinite(yp)
    yt, yp = yt[m], yp[m]
    out = {"sd_ratio": float(np.std(yp) / np.std(yt)) if np.std(yt) > 0 else np.nan}
    if period is not None and period > 1 and yt.size >= period:
        n = (yt.size // period) * period
        rt = yt[:n].reshape(-1, period)
        rp = yp[:n].reshape(-1, period)
        amp_t = np.nanmean(rt.max(1) - rt.min(1))
        amp_p = np.nanmean(rp.max(1) - rp.min(1))
        out["diel_amp_ratio"] = float(amp_p / amp_t) if amp_t > 0 else np.nan
    return out


def seam_magnitude(y_pred, filled_mask):
    """Discontinuity at gap edges relative to interior step size (1.0 = seamless).

    filled_mask: bool array, True where y_pred is a filled (reconstructed) value.
    Returns {seam_ratio, n_seams}: median |step| across observed<->filled
    boundaries divided by the median |step| in the observed interior. ~1 means
    the fill blends in; >>1 means visible seams at gap edges.
    """
    yp = np.asarray(y_pred, float)
    fm = np.asarray(filled_mask, bool)
    if yp.size < 3 or fm.sum() == 0 or (~fm).sum() < 2:
        return {"seam_ratio": np.nan, "n_seams": 0}
    step = np.abs(np.diff(yp))
    boundary = fm[:-1] != fm[1:]
    interior = (~fm[:-1]) & (~fm[1:])
    seam = step[boundary]
    base = np.nanmedian(step[interior]) if interior.any() else np.nan
    seam = seam[np.isfinite(seam)]
    ratio = float(np.nanmedian(seam) / base) if seam.size and base and base > 0 else np.nan
    return {"seam_ratio": ratio, "n_seams": int(seam.size)}


def quality_report(y_true, y_pred, filled_mask=None, lower=None, upper=None,
                   nominal=0.95, period=None):
    """Four-axis gap-fill QUALITY report; higher-level than any single number.

    Axes: accuracy (rmse, mae, bias), variability (variability_fidelity),
    calibration (coverage vs nominal + mean width, only if lower/upper given),
    seam-freeness (seam_magnitude, only if filled_mask given). Score models on
    this whole dict, never rmse alone. period = samples/cycle for diel amplitude.
    """
    yt = np.asarray(y_true, float)
    yp = np.asarray(y_pred, float)
    m = np.isfinite(yt) & np.isfinite(yp)
    ytm, ypm = yt[m], yp[m]
    err = ypm - ytm
    rep = {
        "n": int(m.sum()),
        "rmse": float(np.sqrt(np.mean(err ** 2))) if m.any() else np.nan,
        "mae": float(np.mean(np.abs(err))) if m.any() else np.nan,
        "bias": float(np.mean(err)) if m.any() else np.nan,
        "variability": variability_fidelity(yt, yp, period=period),
    }
    if lower is not None and upper is not None:
        lo = np.asarray(lower, float)
        hi = np.asarray(upper, float)
        mm = m & np.isfinite(lo) & np.isfinite(hi)
        inside = (yt[mm] >= lo[mm]) & (yt[mm] <= hi[mm])
        rep["calibration"] = {
            "nominal": float(nominal),
            "coverage": float(np.mean(inside)) if mm.any() else np.nan,
            "mean_width": float(np.mean(hi[mm] - lo[mm])) if mm.any() else np.nan,
        }
    if filled_mask is not None:
        rep["seam"] = seam_magnitude(yp, filled_mask)
    return rep
