---
name: physics-informed-ml
description: Fuse a mechanism with ML so the learned component can NEVER breach conservation — the three fusion modes (soft-penalty PINN; hard-coded gray-box where ML learns only the uncertain closure like turbulent diffusivity K, respiration, or stomatal response; and emulator/surrogate) plus the hard-vs-soft constraint decision rule. Use when building any hybrid physics+ML model, when tempted to add energy balance or mass conservation to the loss as a penalty term, when a learned flux or closure must respect Rn=H+LE+G or scalar mass balance, when generalizing an 'ANN-beats-MEP' flux estimator, or when a physics-constrained model needs validating by transfer to a held-out drought/anomaly regime rather than in-sample fit.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# STATUS: CURRENT (2026-07-16). Ported from the Claude Science skill (reverse port T-42).

# physics-informed-ml — mechanism + ML without ever breaching the budget

A physics term bolted onto the loss as a penalty is a constraint you can tune away: shrink lambda until data-fit wins and you have silently un-conserved energy or mass. Keep conservation a STRUCTURAL guarantee, not a regularizer to trade off — and prove the mechanism content by transfer to an unseen regime, not by in-sample fit.

## When to invoke
Building any model that fuses ML with a mechanism for canopy-flux / interior-profile work — PINN, gray-box, or emulator. Trigger on:
- "add energy balance / mass conservation to the loss", "make the network respect Rn=H+LE+G".
- "learn K / turbulent diffusivity / respiration / stomatal conductance", "generalize the ANN-beats-MEP flux estimator".
- the words physics-informed / PINN / hybrid / gray-box / residual / Universal-Differential-Equation.
- any time a learned flux or closure feeds a budget that must close.

## Three fusion modes — pick by how much of the physics you trust
1. **Gray-box / hybrid (DEFAULT here).** Conservation + transport hard-coded; ML parameterizes ONLY the genuinely-uncertain closure — K(z,t), soil/canopy respiration, stomatal response. Mechanism where physics is known, ML where it isn't. An 'ANN-beats-MEP' shape, generalized. Budget closes by construction.
2. **Physics-informed / PINN (soft).** Conservation enters as a penalty on the PDE/ODE residual at collocation points: `L = L_data + Sum_k lambda_k * ||residual_k||^2`. Reserve for relations that are themselves approximate, or where hard encoding is intractable. Never for a bookkeeping identity.
3. **Emulator / surrogate.** A fast ML stand-in for the expensive canopy solver — inversion, data assimilation, 20-yr uncertainty propagation. See ml-emulator-surrogate.

## Hard vs soft — the load-bearing decision
- **Conservation identities => HARD, always.** Rn=H+LE+G, water mass balance, CO2 continuity are bookkeeping, not "approximately true".
- A soft penalty on an identity is a bug: the optimizer is free to trade the identity away for data-fit. Encode it so it holds by construction.
- **Approximate / empirical / smoothness relations => SOFT.** A PDE residual you only half-believe, gradient-flow priors, the near-ground wind->0 prior. A trade-off is legitimate here because the physics itself is uncertain.

### How to hard-encode (two shapes that come up here)
- **Flux partition.** Predict a BOUNDED partition and reconstruct the rest to close exactly. E.g. evaporative fraction `EF = sigmoid(NN) in [0,1]` => `LE = EF*(Rn-G)`, `H = (1-EF)*(Rn-G)`. Closure is algebraic and un-violable. (The ANN-beats-MEP partition, done as a hard constraint.)
- **Transport.** `d(chi)/dt = -d/dz(w'chi') + S` with `w'chi' = -K * d(chi)/dz`, `K = NN(state)`. Mass conservation + flux-gradient form are exact; only K is learned (a Universal-Differential-Equation shape).

### The EC closure-gap subtlety
- Measured H+LE typically falls ~20% short of Rn-G (see biosphere-atmosphere-flux-exchange).
- So hard-close the MODEL's fluxes, but do NOT hard-fit them to raw eddy-covariance as if it closed — carry the closure gap explicitly, or you bake a ~20% bias into the learned closure.

## Procedure — gray-box (the default shape)
1. Write the conservation law / transport PDE as the hard scaffold. Identify the ONE closure that is genuinely uncertain (K, respiration, g_s); everything else stays mechanistic.
2. Replace only that closure with an ML term. Keep it a function of PHYSICAL STATE, not a time index — so it transfers across gaps and regimes.
3. Integrate the scaffold with a named solver + fixed timestep; train the closure THROUGH the integrator (differentiable / adjoint).
4. Fit to data. The budget closes at every step by construction — then verify it (below); never assume it.

## Procedure — PINN soft-constraint (only when a penalty is genuinely right)
1. Assemble `L = L_data + Sum_k lambda_k * L_physics_k`. Sample collocation points across the domain — including the gap interiors where data is absent and the physics must carry the reconstruction.
2. **Balance the terms.** Data and residual gradients differ by orders of magnitude; a fixed lambda lets one dominate and the other go slack. Use adaptive weighting (gradient-norm / NTK / annealing), not a hand-picked constant.
3. Advection-dominated canopy transport breaks vanilla PINNs — respect causality (time-marching / curriculum) or prefer the gray-box form.

## The conservation guarantee is a MEASUREMENT, not a hope
- After training, COMPUTE the budget residual on a grid: `Rn-(H+LE+G)` and `d(storage)/dt-(inflow-outflow)`. Report its max and RMS.
- Hard-encoded => residual ~ machine-eps. If it isn't, the encoding leaks — find where before reporting anything.
- Soft => the residual is whatever lambda bought you. Report it; never claim a closure you did not measure.
- A flux asserted without closing its budget is a leak, not a result.

## Timestep / integrator invariance (a hybrid model embeds the solver)
- A closure trained through a discretized scaffold can fit the NUMERICAL SCHEME rather than the physics.
- Before trusting it: halve dt and swap the integrator. The learned K / respiration / g_s and the resulting trajectory must be invariant.
- If they move, discretization error has been absorbed into the ML term — refit at finer dt or with an adaptive solver until the closure is stable.
- Same discipline as separating a true steady state from a slow transient: run long enough, and at more than one dt, to tell the physics from the artifact.

## Validate by TRANSFER, not in-sample fit
- Hold out a REGIME, not random rows: an unseen drought/anomaly regime (gap fraction 43-52% vs ~5% baseline). A physically-consistent model extrapolates there; a black-box overfits the training regime.
- The constrained model must BEAT its own unconstrained twin on the held-out regime. That out-of-distribution gain is the entire return on the physics; if it's absent, the constraint is mis-specified or inactive.
- This is exactly why an ANN beats MEP most clearly in such a drought regime.
- Fold construction + metrics: temporal-block-cv (blocked, embargoed, whole-regime held out — never random-iid on this autocorrelated series).

## Conservation is not the same as a good realization
- Hard closure fixes the budget, not the variability collapse.
- A constrained conditional mean still loses 43-78% of diel variance (the metric trap) and can be miscalibrated (in one tower reconstruction, height cov95 ran 0.52-0.77 = under-covered).
- Pair every constrained model with the variability-fidelity + calibration discipline (calibrated-uq-for-ml) so the output is a realistic realization, not the physically-legal mean.

## Success check
Conservation identities hard-encoded with the residual measured ~0 (not merely penalized); soft penalties reserved for genuinely-uncertain relations, each with its residual reported; the learned closure is a function of state and invariant to dt / integrator; the constrained model beats its unconstrained twin on the held-out drought regime; variability fidelity and calibration checked separately.

## Related
biosphere-atmosphere-flux-exchange (the transport + closure physics, the EC ~20% gap); temporal-block-cv (regime-held-out, embargoed folds); calibrated-uq-for-ml (coverage + variability fidelity); ml-emulator-surrogate (fusion mode 3). The gray-box scaffold IS a conservation law — close the pools and show dt/integrator invariance before reading any learned closure as biology rather than numerical artifact.
