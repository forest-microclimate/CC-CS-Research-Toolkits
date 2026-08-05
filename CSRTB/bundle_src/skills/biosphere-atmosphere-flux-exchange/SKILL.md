---
name: biosphere-atmosphere-flux-exchange
description:  The Monson-Baldocchi terrestrial biosphere-atmosphere flux canon
  — canopy turbulent transport (K-theory and why it fails inside canopies, roughness sublayer,
  counter-gradient flow, higher-order closure), energy-balance closure (the systematic ~20%
  eddy-covariance gap and its causes), leaf->canopy->ecosystem flux scaling (big-leaf / two-leaf /
  multilayer, sunlit-shaded), surface-atmosphere coupling (Penman-Monteith, the conductance
  network, McNaughton-Jarvis Omega decoupling), and eddy-covariance method (WPL, footprint,
  u-star filter, storage). Use when reasoning about canopy fluxes (H, LE, G, NEE/Fc), computing or
  interpreting energy-balance closure or using it as a data-quality/QC signal, modeling turbulent
  transport inside or above a canopy, scaling leaf fluxes to canopy/ecosystem, judging whether
  evaporation is radiation- or stomata-controlled (coupling vs decoupling), or trusting tower
  eddy-covariance data.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# biosphere-atmosphere-flux-exchange — the atmospheric-exchange physics of the canopy

The within-canopy microclimate is vertical turbulent transport acting against the leaf sources/sinks distributed through the canopy. Reason about it with the wrong transport model (local down-gradient K-theory), or treat the eddy-covariance energy-balance gap as something to fit away rather than a measurement artifact, and you get fluxes that look right and are wrong. This is the connective tissue — canopy transport + scaling + coupling as atmospheric-exchange physics — that the paradigm-partitioned specialists each touch an edge of but none own.

## When to invoke
Reasoning about canopy/ecosystem fluxes (H, LE, G, NEE), energy-balance closure, turbulent transport in/above a canopy, leaf->canopy scaling, surface-atmosphere coupling, or the trustworthiness of tower eddy-covariance data.
Loaded by **ML_HYBRID_PROCESS_MODELER** (its mechanistic foundation — the emergent interior *is* transport vs distributed sources/sinks), by **MACHINE_LEARNING_SCIENTIST** (energy-balance closure as a QC / trust signal on tower flux data), and by **ECOPHYSIOLOGY_MODELER** (the transport side of leaf->canopy scaling).

## 0. Three questions before any flux claim
State them or the number is a sentence that sounds like a result:
1. **WHICH flux + sign convention** — H, LE, G, S(torage), NEE/Fc; is upward positive? Conventions differ across datasets and models — name yours.
2. **MEASURED or MODELED** — EC observations carry the closure gap, storage, and u\*/footprint handling; model output does not. Never compare the two as if both were truth.
3. **Does it CLOSE** — Rn = H + LE + G + S (+ minor). Closure is the first sanity check (§2), not an afterthought.

## 1. Canopy turbulent transport — local K-theory fails inside canopies
- **Flux-gradient (K-theory, 1st-order closure):** F = -K d(C_bar)/dz. Valid in the inertial sublayer / free atmosphere where eddies are small vs the gradient length scale.
- **Why it fails IN-canopy:** transport is dominated by large, intermittent, coherent eddies (sweeps & ejections) with length scale >= canopy depth, so transport is **non-local** — not local down-gradient diffusion.
- **Counter-gradient flow:** observed flux can run *up* the mean gradient (heat/CO2 in the upper canopy) — a direct falsification of local K-theory. WHEN a modeled in-canopy flux is forced down-gradient => suspect it.
- **Roughness sublayer (RSL):** ~h to 2-3h above ground, Monin-Obukhov similarity (MOST) breaks down and transport is enhanced; flux-gradient needs an RSL enhancement factor. Above ~2-3h = inertial sublayer, MOST holds.
- **Mixing-layer analogy** (Raupach-Finnigan-Brunet): canopy-top shear behaves as a plane mixing layer (inflection-point instability), not a boundary layer — origin of the coherent eddies and the ~exponential in-canopy wind profile.
- **Fixes for non-local transport:** higher-order closure (2nd-order: prognose the variances/covariances) or Lagrangian localized near-field theory (Raupach 1989).
- **K67:** the emergent interior profile *is* this transport acting against §3's sources/sinks. A single global eddy-diffusivity / AR coefficient over the 0-55 m x 111-level grid over-smooths near-ground scalars (the corpus CO2 over-smoothing) — near-ground transport is intermittent & non-local, not one constant K.

## 2. Energy-balance closure — a HARD check, never a fitting target
- **Budget:** Rn = H + LE + G + S + minor(photosynthesis, advection). Available energy (Rn - G - S) *should* equal turbulent (H + LE).
- **EC under-measures systematically:** (H+LE)/(Rn-G) ~= 0.7-0.9, mean ~0.8 => the **~20% gap**. Compute with `energy_balance_closure(Rn, H, LE, G=None)` -> `{n, closure_ratio, slope, intercept}`; the OLS slope of (H+LE) vs (Rn-G) ~0.8 with a small intercept is the standard closure diagnostic.
- **Causes are measurement/sampling — energy IS conserved:** low-frequency mesoscale / secondary-circulation eddies missed by 30-min point EC; horizontal advection a single tower cannot see; **neglected storage** (canopy-air heat/H2O/CO2 + biomass — large for tall forests like K67); footprint mismatch between the Rn, G, and EC source areas; high-frequency instrument losses.
- **HARD check, not a target:** closure diagnoses *data quality* and *physical consistency*. Never tune model parameters or ML weights to force closure -> 1 — that launders measurement error into the physics.
  - **Data side (MACHINE_LEARNING_SCIENTIST):** use closure as a QC signal — trust/weight tower H, LE more in well-closing periods; the gap means tower turbulent fluxes are biased **low**, so they are evidence, not ground truth.
  - **Mechanism side (ML_HYBRID_PROCESS_MODELER):** enforce Rn = H + LE + G as a **hard conservation constraint** on the *modeled* interior (see `physics-informed-ml`), but do **not** expect raw EC obs to satisfy it — compare closed model fluxes against gap-/storage-corrected obs.
- **Bowen ratio** beta = H/LE via `bowen_ratio(H, LE)`: closure-correction schemes (Twine et al. 2000) either preserve beta (scale H, LE up together) or assign the residual to LE. K67 wet tropical forest is LE-dominated (beta < 1).

## 3. Leaf->canopy->ecosystem scaling — big-leaf / two-leaf / multilayer
- **Big-leaf:** canopy = one leaf x LAI at mean light. **Biased high** for photosynthesis — the light response is saturating (concave), so applying mean light over-predicts: a Jensen-inequality error => see `aggregation-jensen-bias`.
- **Two-leaf (sunlit/shaded):** split into a sunlit (direct + diffuse) and a shaded (diffuse-only) fraction; sunlit is often light-saturated, shaded light-limited (linear regime). Captures the dominant nonlinearity at ~big-leaf cost, reaching ~multilayer accuracy (de Pury & Farquhar 1997). Sunlit fraction ~ exp(-k*L) (Beer's law, direct beam).
- **Multilayer:** N layers, each with its own light / T / VPD / wind / physiology; integrate. Required for the **vertical profile** — exactly K67's 111-level interior; this is the scaling engine the mechanism side rides.
- **Scale the flux, derive per level:** integrate the flux (CO2, H2O, heat) layer-by-layer; compute VPD and other derived quantities *per layer* from that layer's T, q, p — never interpolate VPD directly (matches the project's per-level-derived rule).

## 4. Surface-atmosphere coupling — Penman-Monteith, conductances, Omega
- **Penman-Monteith:** LE = [s(Rn-G) + rho*c_p*D*g_a] / [s + gamma(1 + g_a/g_s)] — a radiative (energy) term plus an aerodynamic (VPD-driven) term. Kernel constants `CP_AIR`, `RHO_AIR`, `GAMMA_PSY` (psychrometric gamma), `LATENT_VAP` back the psychrometric algebra.
- **Conductance network (Ohm analogy, in series):** g_a aerodynamic (surface -> reference height) from `aerodynamic_conductance(u_star, wind_speed)` (neutral g_a ~= u\*^2 / U); g_s surface/canopy (stomatal); resistance r = 1/g.
- **McNaughton-Jarvis Omega decoupling** via `omega_decoupling(g_a, g_s, s_slope=None, gamma=None)` -> Omega in [0,1], Omega = (s/gamma + 1) / (s/gamma + 1 + g_a/g_s):
  - **Omega -> 1 decoupled:** g_a << g_s (smooth/short vegetation, weak wind) => LE radiation-controlled (~= Omega * LE_eq), weakly sensitive to stomata.
  - **Omega -> 0 coupled:** g_a >> g_s (aerodynamically rough / tall vegetation) => LE stomata- and VPD-controlled ("imposed" evaporation).
  - **K67 is a tall tropical forest => strongly coupled (Omega ~ 0.1-0.3):** transpiration is VPD/stomata-driven, *not* radiation-limited. An interior mapping that makes LE track Rn is wrong here — VPD is the lever, which is why the VPD/drought-hysteresis regime and the Oct 2015-Mar 2016 drought fold matter.

## 5. Eddy-covariance methodology — what the tower numbers actually are
- **Flux = <w'c'>** — the covariance of vertical-wind and scalar fluctuations (10-20 Hz over ~30 min).
- **WPL (Webb-Pearman-Leuning):** density correction for open-path H2O/CO2 — heat and H2O fluxes perturb air density, so apparent flux /= true flux; omit it and CO2/LE are wrong.
- **Footprint:** the upwind source area (grows with measurement height, shrinks with roughness & instability, rotates with wind direction) — match it to the target forest; off-footprint data contaminate.
- **u\* filter:** on calm, stable nights (low friction velocity) EC under-measures respiration — drainage/advection removes CO2 and storage builds; filter data below a u\* threshold and gap-fill. Central to Amazon / LBA towers.
- **Storage:** the below-sensor air column stores/releases scalar; NEE = F_EC + storage change; largest at night (CO2 build-up) and in the dawn flush; needs a profile system to measure. For a tall forest like K67, storage is non-negligible for **both** energy (§2) and carbon.
- **Consequence for ML:** tower H, LE, Fc are not clean truth — they carry the closure gap, WPL, u\*/storage handling, and footprint. Provenance/trust tiers must reflect this (data side; see `scientific-ml-fundamentals`, `temporal-block-cv`).

## Kernel functions (kernel.py, auto-loaded with this skill)
- `energy_balance_closure(Rn, H, LE, G=None)` -> `{n, closure_ratio, slope, intercept}` — closure ratio + the OLS (H+LE ~ Rn-G) diagnostic (§2).
- `bowen_ratio(H, LE)` -> beta = H/LE (§2).
- `omega_decoupling(g_a, g_s, s_slope=None, gamma=None)` -> McNaughton-Jarvis Omega in [0,1] (§4); pass the saturation-vapor-pressure-curve slope and psychrometric gamma, or omit for defaults.
- `aerodynamic_conductance(u_star, wind_speed)` -> neutral g_a ~= u\*^2 / U (§4).
- constants `CP_AIR`, `RHO_AIR`, `GAMMA_PSY`, `LATENT_VAP` — for Penman-Monteith / psychrometry.

## Related
`aggregation-jensen-bias` (big-leaf scaling bias; block-averaging of nonlinear quantities) · `physics-informed-ml` (conservation as a hard/soft constraint — the mechanism side) · `calibrated-uq-for-ml` (coverage on reconstructed fluxes) · `scientific-ml-fundamentals` + `temporal-block-cv` (how flux-data quality enters training) · `reproduce-model-from-literature` (reproduce Penman-Monteith / a two-leaf model against its source before extending). Hands off to DYNAMICAL_SYSTEMS_MODELER (transport PDEs, boundary-layer dynamics) and ECOPHYSIOLOGY_MODELER (the leaf physiology inside the scaling).
