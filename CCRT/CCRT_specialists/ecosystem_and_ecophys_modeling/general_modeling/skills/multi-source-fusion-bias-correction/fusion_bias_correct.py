# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""Sidecar for multi-source-fusion-bias-correction.

Cross-source bias correction (SKILL.md ## Correct). Satellite (MSG/CERES) and
reanalysis (ERA5) each carry their own mean and variance bias against the tower;
naively concatenating them injects step artifacts at source boundaries. These
functions correct a secondary source onto the tower reference over their overlap
before fusion, so the fused series has no source-driven seams.
"""
import numpy as np


def linear_scale_correct(ref_overlap, src_overlap, src_full):
    """Variance-preserving linear rescale of a source onto the reference.

    Fit src -> a*src+b by least squares on the overlap where BOTH are finite,
    apply to src_full. Returns {corrected, a, b, n_overlap}. Cheapest correction;
    fixes mean+scale but not distribution shape. Use when overlap is short.
    """
    r = np.asarray(ref_overlap, float)
    s = np.asarray(src_overlap, float)
    m = np.isfinite(r) & np.isfinite(s)
    if m.sum() < 2:
        return {"corrected": np.asarray(src_full, float), "a": np.nan, "b": np.nan, "n_overlap": int(m.sum())}
    A = np.vstack([s[m], np.ones(m.sum())]).T
    a, b = np.linalg.lstsq(A, r[m], rcond=None)[0]
    return {"corrected": a * np.asarray(src_full, float) + b,
            "a": float(a), "b": float(b), "n_overlap": int(m.sum())}


def quantile_map(ref_overlap, src_overlap, src_full, n_q=100):
    """Empirical quantile mapping (distribution-matching bias correction).

    Maps the source CDF onto the reference CDF over the overlap, then applies it
    to src_full with linear interpolation and flat extrapolation past the edges.
    Corrects the whole distribution shape, not just mean/scale — the right tool
    when the source mis-represents variability or tails. Returns corrected array.
    """
    r = np.asarray(ref_overlap, float)
    s = np.asarray(src_overlap, float)
    sf = np.asarray(src_full, float)
    m = np.isfinite(r) & np.isfinite(s)
    if m.sum() < 2:
        return sf.copy()
    qs = np.linspace(0, 100, n_q)
    r_q = np.percentile(r[m], qs)
    s_q = np.percentile(s[m], qs)
    # source value -> its quantile -> reference value at that quantile
    order = np.argsort(s_q)
    s_qs, r_qs = s_q[order], r_q[order]
    out = np.interp(sf, s_qs, r_qs, left=r_qs[0], right=r_qs[-1])
    out[~np.isfinite(sf)] = np.nan
    return out


def source_agreement(a, b):
    """Bias/scatter of source b vs reference a on their overlap (SKILL.md
    ## Assess). Returns {bias, rmsd, corr, n} — inspect BEFORE correcting so the
    correction method matches the defect (offset vs scale vs shape)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 2:
        return {"bias": np.nan, "rmsd": np.nan, "corr": np.nan, "n": int(m.sum())}
    d = b[m] - a[m]
    return {"bias": float(np.mean(d)),
            "rmsd": float(np.sqrt(np.mean(d ** 2))),
            "corr": float(np.corrcoef(a[m], b[m])[0, 1]),
            "n": int(m.sum())}
