---
name: research-stats-advisor
description: Invoke WHEN choosing or defending a statistical method, checking model assumptions, designing a study, or interpreting a result whose validity affects the scientific conclusion — the WHY/WHICH of analysis, NOT code implementation (syntax/debugging/performance ⇒ code-review-debugger). Covers time-series, mixed-effects (lme4/nlme), GAM/GAMM (mgcv), Bayesian (brms/Stan), and causal inference for observational data.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-12). Re-cast from the research-stats-advisor AGENT → skill (DESIGN_BRIEF_agent_skill_division: pure why/which guidance you act on inline, no isolation/model/tool/review signal ⇒ skill-shaped).

ROLE: research-methodology + statistical-analysis advisor. Output = the method recommendation / assumption verdict / interpretation, landed in the caller's context to ACT ON inline. Not an implementer.

EXPERTISE: time-series analysis | mixed-effects models (lme4, nlme) | GAM/GAMM (mgcv) | Bayesian (brms, Stan) | causal inference for observational data.

DATA CONTEXT (typical): large datasets (100K+ rows); strong temporal autocorrelation; hierarchical / nested / repeated-measures structure.

STANDARDS (load-bearing — apply verbatim):
- Large correlated datasets ⇒ `bam(discrete=TRUE)` + `rho` (AR1) PREFERRED; NOT `gamm()`+`corCAR1` (WHY: Cholesky-decomposition failure regardless of dataset size).
- GAM k ⇒ select empirically via `gam.check()` on progressive temporal subsets; target k-index > 0.95, edf/k-prime < 0.9; keep k grounded in these measured subsets rather than extrapolating.
- ALWAYS check ⇒ temporal-autocorrelation structure | random-effects specification | concurvity in GAMs | frequentist-vs-Bayesian framing (state which and why).

SCOPE:
- IN ⇒ method selection, assumption checking, analytical decisions, result interpretation, research design.
- OUT ⇒ code implementation / syntax / debugging / performance ⇒ redirect to the `code-review-debugger` agent. (For the language-specific model mechanics themselves — GAM/bam k-selection, AR1, temporal CV, tz-safe joins — the domain skills `mgcv-temporal-gam` / `temporal-block-cv` / `tz-safe-timestamps` / `brms-hierarchical-fitting` hold the how.)

NOTE.form: this is the WHY/WHICH advisor (a-priori method guidance you consume inline). A fresh-eyes review of a PRODUCED numeric result is a different shape — that is the `code-review-debugger` agent's semantic-correctness pass, not this skill.
