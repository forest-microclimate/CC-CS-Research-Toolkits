---
name: temporal-block-cv
description: Construct temporal / blocked cross-validation folds for autocorrelated or rare-event data (blocked, not iid CV), and evaluate with metrics that survive class imbalance (PR-AUC, calibration/reliability, Brier) rather than accuracy. Use when cross-validating a time-series, spatial, or rare-event / class-imbalanced model, selecting a model/scale/feature on such data, or when someone proposes a random iid split on autocorrelated data.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.

# temporal-block-cv — leakage-free CV for autocorrelated & rare-event data

iid random CV leaks across temporal autocorrelation and gives optimistic, wrong estimates; accuracy is meaningless under class imbalance. This builds honest folds + honest metrics.

## When to invoke
Evaluating or selecting any model on temporally/spatially autocorrelated and/or rare-event (imbalanced 0/1) data.

## Procedure
1. **Block, don't shuffle.** Partition into CONTIGUOUS blocks (e.g. by day/season/site) so each fold spans the FULL series range — not 1–2 adjacent units. Hold out WHOLE blocks.
2. **Embargo.** Leave a gap between train and held-out block ≈ the autocorrelation length, so adjacent-time leakage can't inflate skill.
3. **Stratify for rare events.** Assign blocks to folds so each fold preserves the overall base rate (event fraction ≈ equal across folds). Verify: `table(fold, y)` — every fold holds some positives (none near 0).
4. **Fit folds in parallel** via furrr/future (see preflight-parallel); persist each fold's held-out predictions (long format).
5. **Evaluate with the right metrics.** For imbalanced 0/1: **PR-AUC** (not ROC-AUC alone), **reliability/calibration curve**, **Brier score** — rely on these, never accuracy. For counts/continuous: proper scoring + coverage.
6. **Inspect the plots** (calibration curve, PR curve) before reporting any number.

## Success check
Every fold spans the series and holds the base rate (`table(fold,y)` confirms); an embargo exists; PR-AUC + calibration reported and visually inspected; splits are blocked, not random-iid, on autocorrelated data.

## Cluster-bootstrap INFERENCE (hard-won) — CV ≠ inference
- For spatially-CLUSTERED / site-level covariates, Wald t/p (even AR-corrected via gamm corARMA) are WILDLY over-optimistic (they treat all rows as independent): observed bootstrap SE ≈ 10× naive Wald; a term with Wald t≈15/p≈0 had a bootstrap CI CROSSING 0 (identified by only ~77 clusters). Use the CLUSTER/BLOCK BOOTSTRAP (resample clusters with replacement, relabel dups, refit the CHEAP `bam` — the resampling itself captures the autocorrelation, so keep each resample a plain `bam` refit, not gamm/AR) as the HEADLINE inference; report Wald as descriptive only.
- OPPOSITE blind spot: the block bootstrap UNDER-POWERS rare within-unit (time-varying) interactions — the few rare-carrying blocks get near-zero weight ⇒ every rare interaction reads "not robust." For rare WITHIN-cluster terms the full partial-pooling (Stan/brms) model is the arbiter, NOT the bootstrap. Match the tool to the estimand's scale: block-bootstrap for BETWEEN-cluster effects, hierarchical model for rare WITHIN-cluster effects.

## Selection pipeline & validation traps (hard-won)
- Selection pipeline: mgcv `bam` interaction/curvature SCREEN → two-way (unit × N-day-block) weighted-bootstrap ROBUSTNESS filter → final Bayesian GOLD. Keep a term only if its block-bootstrap 95% CI excludes 0 AND the mechanistic sign is right; drop interactions that aren't bootstrap-robust or rest on rare-event data.
- When BOTH a model and empirical estimate carry uncertainty, propagate both (posterior CrI AND empirical/bootstrap SE) with cluster-robust SE for clustered data — rather than calling their difference "bias vs truth". pp-coverage: the observed statistic should land within [.05,.95] of the posterior-predictive replicates.
- CIRCULAR-validation trap: validate a transformed predictor against an INDEPENDENT measurement, not a variable DERIVED from that transform.

## Related
preflight-parallel (fold fan-out); mgcv-temporal-gam (the fitted model); brms-hierarchical-fitting (the Bayesian gold stage); assert the per-fold event count (semantic-assertion rule); model-check by calibration/coverage when there is no ground-truth "true value".
