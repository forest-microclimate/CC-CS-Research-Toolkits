---
name: micromet-height-interpolation
description: Invoke WHEN interpolating tower/canopy microclimate drivers across HEIGHT onto a fine vertical grid (e.g. 0.5 m) — Tair, VPD, CO2, H2O, wind — from sensors at a few discrete heights, to force a height-resolved ecosystem model. Covers climatology+anomaly vertical decomposition, soft physical priors (wind→0 at ground with no near-ground sensor), above-canopy-only globals broadcast across height, deriving VPD per level (not interpolating it), and benchmarking the interpolator against a held-out level.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# micromet-height-interpolation — resolve drivers onto a vertical grid, physically

## When to invoke
WHEN turning a few discrete-height sensor series into a continuous vertical profile on a fine grid (e.g. 0.5 m, ground → above-canopy) to force a height-resolved model. Each driver is interpolated by its OWN physics — NOT one generic spatial smooth for all of them.

## The load-bearing rule
Interpolate each driver by its own physics; derive what should be derived; never fabricate a level a physical prior can constrain instead.

## 1. Decompose; don't fit one spatial smooth (temperature-like scalars)
- A single `s(height)` smooth over few levels over-smooths and extrapolates badly to unobserved heights.
- WHEN a good-record climatology exists ⇒ use climatology(height, hour, season) + the per-timestep observed ANOMALY interpolated across height, added back. The climatology is a prior SHAPE, never the sole value.
- In a held-out-level benchmark this decomposition beat a single Bayesian spatial tensor for unobserved-level recovery — prefer it for Tair-like fields.

## 2. Soft physical priors where a sensor is missing
- WHEN a variable has a known physical boundary value but no sensor there ⇒ add it as a SOFT pseudo-observation (a value + a finite SE), not a hard clamp.
- Canonical case: no near-ground wind sensor ⇒ a z=0 pseudo-obs of ~0 m/s with a small SE (e.g. y≈0.01, se≈0.10) inside the vertical wind-profile fit. Soft, so real data can pull it; present, so the ground does not extrapolate to nonsense.

## 3. Above-canopy-only globals: broadcast, don't interpolate
- Some drivers are measured ONLY at/near canopy top (ambient pressure; the incoming radiation forcing).
- WHEN a driver has one above-canopy source ⇒ apply it across height as a single boundary value (ambient pressure varies <~2% over a canopy) OR as the top boundary of a vertical model (wind) — NOT as a fitted vertical smooth.

## 4. Derive VPD per level — never interpolate a VPD profile directly
- VPD is a nonlinear function of Tair and humidity. WHEN building VPD(z) ⇒ compute it from interpolated Tair(z) + H2O(z) + (broadcast) ambient pressure at each level, using a named saturation-vapor-pressure formula.
- Interpolating a VPD profile directly double-counts the Tair nonlinearity — a Jensen-type bias (⇒ aggregation-jensen-bias).
- Dependency order is fixed: ambient-pressure fill → THEN VPD, because VPD needs pressure.

## 5. Benchmark the interpolator against a HELD-OUT level
- WHEN choosing or trusting a height interpolator ⇒ hold out an entire sensor level and predict it from the others; report per-level error. Do not assume the temporally-best gap-filler is also the best vertical interpolator — in a head-to-head, a gradient-boosting interpolator beat a Bayesian tensor for fully-unobserved levels.
- A method that needs ≥3 heights cannot fill a timestamp with only 1–2 levels present — gate on level count and fall back.

## Hand-offs
- Temporal gap-filling of each series BEFORE height interpolation, incl. the chunk + overlap + tail-splice seam rule ⇒ gap-fill-imputation.
- QC / outlier passes on the raw series ⇒ temporal-qc-outlier-detection.
- Nonlinear-aggregation (Jensen) bias in general ⇒ aggregation-jensen-bias.
- Method selection (bam vs brms, k, AR1, blocked CV) ⇒ the research-stats-advisor guidance.
