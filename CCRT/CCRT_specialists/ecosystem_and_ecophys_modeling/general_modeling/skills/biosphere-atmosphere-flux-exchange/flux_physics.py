# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""Sidecar for biosphere-atmosphere-flux-exchange.

The load-bearing flux-physics checks from the Monson & Baldocchi canon
(SKILL.md ## Energy balance, ## Coupling). These are the conservation and
coupling relations a learned above->interior mapping must respect; use them to
audit tower data (energy-balance closure as a QC signal) and to constrain or
validate any ML flux product (a model that breaks closure is wrong, however low
its RMSE).
"""
import numpy as np

CP_AIR = 1004.0        # J kg-1 K-1, specific heat of dry air at const pressure
RHO_AIR = 1.2          # kg m-3, reference air density near surface
GAMMA_PSY = 66.1       # Pa K-1, psychrometric constant at ~20C, sea level
LATENT_VAP = 2.45e6    # J kg-1, latent heat of vaporization near 20C


def energy_balance_closure(Rn, H, LE, G=None):
    """Surface energy-balance closure ratio (SKILL.md ## Energy balance).

    Returns {closure_ratio, slope, intercept, n}: ordinary-least-squares of
    (H+LE) on (Rn-G) plus the mean ratio. EC systematically closes at ~0.7-0.9;
    a closure much outside that flags data or model error. Use as a QC signal on
    tower fluxes and as a hard check on any reconstructed flux set — Rn=H+LE+G
    is conservation, not a fitting target.
    """
    Rn = np.asarray(Rn, float)
    H = np.asarray(H, float)
    LE = np.asarray(LE, float)
    G = np.zeros_like(Rn) if G is None else np.asarray(G, float)
    avail = Rn - G
    turb = H + LE
    m = np.isfinite(avail) & np.isfinite(turb)
    avail, turb = avail[m], turb[m]
    out = {"n": int(m.sum()), "closure_ratio": np.nan, "slope": np.nan, "intercept": np.nan}
    if m.sum() >= 2 and np.sum(avail != 0) > 0:
        A = np.vstack([avail, np.ones_like(avail)]).T
        slope, intercept = np.linalg.lstsq(A, turb, rcond=None)[0]
        out["slope"] = float(slope)
        out["intercept"] = float(intercept)
        denom = np.sum(avail)
        out["closure_ratio"] = float(np.sum(turb) / denom) if denom != 0 else np.nan
    return out


def bowen_ratio(H, LE):
    """Bowen ratio beta = H/LE (SKILL.md ## Partitioning). Diagnoses the
    sensible/latent split; drought pushes beta up as LE collapses (the
    collaborator's 2015-16 signal)."""
    H = np.asarray(H, float)
    LE = np.asarray(LE, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(LE != 0, H / LE, np.nan)


def omega_decoupling(g_a, g_s, s_slope=None, gamma=None):
    """McNaughton-Jarvis decoupling coefficient Omega in [0,1] (SKILL.md
    ## Coupling).

    g_a aerodynamic, g_s surface conductance (same units). Omega->0 = canopy
    tightly coupled to the atmosphere (VPD-driven, imposed evaporation);
    Omega->1 = decoupled (Rn-driven, equilibrium evaporation). Governs whether
    the interior tracks above-canopy forcing or its own energy load — decisive
    for an above->interior mapping. s_slope = d(sat vapor pressure)/dT (Pa/K);
    gamma = psychrometric constant (defaults to GAMMA_PSY).
    """
    g_a = np.asarray(g_a, float)
    g_s = np.asarray(g_s, float)
    gamma = GAMMA_PSY if gamma is None else gamma
    eps = 2.2 if s_slope is None else (s_slope / gamma)   # s/gamma; ~2.2 near 20C
    with np.errstate(divide="ignore", invalid="ignore"):
        return (eps + 1.0) / (eps + 1.0 + g_a / g_s)


def aerodynamic_conductance(u_star, wind_speed):
    """Bulk aerodynamic conductance g_a ~ u_star^2 / U (m s-1), the neutral
    momentum estimate (SKILL.md ## Transport). u_star friction velocity, U mean
    wind at reference height."""
    us = np.asarray(u_star, float)
    U = np.asarray(wind_speed, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(U > 0, us ** 2 / U, np.nan)
