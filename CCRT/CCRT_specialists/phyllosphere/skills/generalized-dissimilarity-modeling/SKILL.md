---
name: generalized-dissimilarity-modeling
description: Model how community BETA diversity (pairwise compositional dissimilarity) turns over along environmental and spatial gradients with Generalized Dissimilarity Modeling (GDM) — the beta-diversity counterpart to a GAM, using monotonic I-spline basis functions through a link. Use WHEN asking how fast / where along a gradient composition changes, partitioning turnover into environmental vs spatial (dispersal-proxy) components, fitting a GDM or multi-site GDM on zeta diversity, or relating amplicon (ITS/16S) dissimilarity to continuous predictors as a splined function rather than a constrained ordination. Carries the monotonicity, site-pair-format, permutation-testing, inherited-compositionality, and extrapolation gotchas. NOT for computing the dissimilarity or testing group differences (amplicon-community-diversity), for deterministic-vs-stochastic assembly PROCESS (community-assembly-null-models), or for co-occurrence networks (microbial-cooccurrence-network).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-14). Ported from the Claude Science generalized-dissimilarity-modeling skill (toolkit refresh, from crt_science_bundle v1.3). Clean copy: genericized the Claude-Science figure-style skill ref (-> publication-figure workflow) and the Research Stats Advisor agent ref (-> research-stats-advisor skill); method content unchanged.

# generalized-dissimilarity-modeling

GDM (Ferrier et al. 2007) regresses **pairwise community dissimilarity** onto
**environmental and geographic distance** between sites, fitting each predictor
as a monotonic spline through a link function. If your alpha analysis already
models diversity as `s(gradient)` in a GAM, GDM is the structural mirror for
beta: it expresses *turnover* as a splined, link-transformed function of the
same predictors. That is the appeal — it stays inside the GLM/GAM mindset while
answering a beta-diversity question that ordination and PERMANOVA cannot.

## What GDM answers that the other beta tools do not
- **The SHAPE and RATE of turnover along each gradient.** The fitted I-spline
  for a predictor (e.g. gap fraction) shows *where along that gradient*
  composition changes fastest — its height is the total compositional turnover
  attributable to that predictor, its slope is the local rate. dbRDA/CAP give a
  constrained-variance triplot; GDM gives the turnover function itself.
- **Environmental vs spatial partitioning.** Put geographic (or height) distance
  in as a predictor alongside the environmental ones and GDM apportions total
  turnover among them. This is the closest any beta method comes to *quantifying*
  (not resolving) the environment-vs-dispersal split — directly relevant where a
  microclimate gradient is confounded with a dispersal/immigration gradient.
  A design that decorrelates two predictors (e.g. height vs light measured
  independently) is exactly what gives GDM the leverage to separate their splines.

Contrast, so you reach for the right tool: `amplicon-community-diversity` COMPUTES
the dissimilarity and TESTS group differences (PERMANOVA) / ordinates it (dbRDA);
`community-assembly-null-models` asks WHY communities differ (selection vs
dispersal vs drift); **GDM asks HOW MUCH and ALONG WHICH gradient, as a
function.** They are complementary layers on the same turnover.

## The headline gotcha: I-splines are MONOTONIC
GDM's splines can only bend, not reverse — turnover is assumed to accumulate
monotonically with environmental distance. Unlike a free GAM smooth, **GDM cannot
represent hump-shaped or non-monotonic turnover.** If composition is most similar
at *intermediate* canopy positions (a mid-gradient optimum), GDM will misfit and
still return a tidy, plausible-looking spline. WHEN interpreting a GDM ⇒ first ask
whether monotonic turnover is biologically defensible for that predictor; if a
unimodal response is plausible, cross-check with a free-smooth GAM on a derived
turnover response or with the ordination before trusting the GDM spline.

## Gotchas the gdm docs assume you know
- **It inherits compositionality; it does not fix it.** The response is a
  dissimilarity matrix computed on your amplicon table, so every normalization
  decision in `amplicon-community-diversity` (rarefy vs CLR, which distance)
  happens FIRST and propagates. GDM adds no compositional correction of its own.
- **Incidence (Sorensen) is often the honest input for ITS.** GDM's canonical use
  is with Bray-Curtis or Sorensen. Given fungal ITS copy-number variation, the
  presence/absence Sorensen response is frequently the defensible choice over an
  abundance dissimilarity — state which you used.
- **Site-pair table format is mandatory and easy to get wrong.** GDM does not take
  a site-by-species matrix directly; it needs the "site-pair" format
  (`gdm::formatsitepair`) that expands sites into all pairwise rows with the
  distance response and paired predictor columns. Feeding it a raw matrix, or
  mismatching the biological and predictor site orders, silently corrupts the
  fit. Build it with `formatsitepair` and check row count = n(n-1)/2.
- **Significance and importance are PERMUTATION-based — run them, report them.**
  A fitted GDM's deviance-explained means little without `gdm::gdm.varImp`, which
  permutes to test overall model and per-predictor significance and quantifies
  predictor importance. It is slow (many permutations x matrix refits) but it is
  the inference step; a GDM reported without it is descriptive only.
- **Do not extrapolate.** The I-splines are fit within the observed range of each
  predictor; turnover predicted beyond that range is unsupported. Relevant if you
  project to gradient values you did not sample.
- **Report deviance explained, not R^2**, and interpret it as the model's share of
  total compositional turnover — not variance in a Gaussian sense.

## The MRM / multi-site (zeta) family — same mindset, different resolution
- **MRM** (Multiple Regression on distance Matrices; Lichstein 2007,
  `ecodist::MRM`): the *linear* cousin — regresses the dissimilarity matrix on
  multiple distance matrices without splines. Simpler and more transparent when
  you do not need the non-linear turnover shape; a reasonable first pass before
  committing to GDM's splines, and the same tool `community-assembly-null-models`
  uses to relate assembly metrics to drivers.
- **Multi-site GDM on zeta diversity** (`zetadiv::Zeta.msgdm`): applies GDM's
  spline machinery to **zeta** orders (multi-site shared-taxa turnover) rather
  than pairwise dissimilarity — unifying GDM with the zeta-diversity approach
  covered in `amplicon-community-diversity` (Decision 5). Reach here when the
  question is how *rare-vs-common* turnover (not just pairwise turnover) relates
  to environmental distance across many sites; it separates the environmental
  dependence of common vs rare taxa that a single pairwise GDM blends.

## Tooling
R is the home: `gdm` (`formatsitepair`, `gdm`, `gdm.varImp`, `isplineExtract`
for plotting the fitted splines, `predict`), `zetadiv` (`Zeta.msgdm` for the
multi-site/zeta extension), `ecodist`/`vegan` (`MRM`). Report: the input
dissimilarity + its normalization, the predictors, deviance explained,
`gdm.varImp` permutation results, and the number of permutations. Plot the fitted
I-splines (partial-response of turnover vs each predictor) — that plot, not a
coefficient table, is the GDM result. Spline plotting is a publication-figure task.

## Refs
- Ferrier et al. 2007 — GDM (I-spline dissimilarity regression).
- Lichstein 2007 — MRM (linear distance-matrix regression).
- Fitzpatrick & Keller 2015 — GDM applied to genomic/community turnover (a clear
  worked template; "community-level modelling" framing).
- Latombe et al. 2017; McGeoch et al. 2019 — multi-site GDM on zeta diversity.
- Companion: amplicon-community-diversity (computes + normalizes the dissimilarity,
  and the zeta paragraph this extends) · community-assembly-null-models (process,
  not pattern) · microbial-cooccurrence-network. Modelling mechanics + free-smooth
  cross-check: research-stats-advisor / mgcv-temporal-gam. Spline plots: any publication-figure workflow.
