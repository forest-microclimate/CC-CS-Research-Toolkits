---
name: community-assembly-null-models
description: Quantify the balance of DETERMINISTIC (selection) vs STOCHASTIC (dispersal, drift) community assembly processes from amplicon data using phylogenetic-bin null models — betaNRI/betaNTI, RCbray, QPEN (Stegen), and iCAMP (Ning) — and interpret them under the assumptions they actually require. Use WHEN asking whether communities are structured by environmental filtering vs dispersal vs drift, partitioning beta diversity into ecological processes, running iCAMP / QPEN / betaNTI, or relating assembly-process fractions to environmental drivers. Carries the ITS-phylogeny alignability caveat that makes or breaks the whole framework for fungi, plus the phylogenetic-signal precondition. NOT for plain beta diversity (amplicon-community-diversity), guilds (fungal-guild-assignment), or association networks (microbial-cooccurrence-network).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-14). Ported from the Claude Science community-assembly-null-models skill (toolkit refresh, from crt_science_bundle v1.3). Clean copy: genericized the Claude-Science agent-profile confound reference and the Research Stats Advisor agent ref (-> research-stats-advisor skill); method content unchanged.

# community-assembly-null-models

These methods answer "are these communities assembled more by selection or by
chance?" by comparing observed phylogenetic/taxonomic turnover to a null
expectation. iCAMP, QPEN, and betaNTI are STANDARD, widely-used amplicon methods
— they operate directly on beta-diversity turnover (phylogenetic betaMNTD/betaNTI
and taxonomic Raup-Crick) and are a default way microbiome studies partition 16S,
and increasingly ITS, beta diversity into ecological processes. Use them. They
also rest on assumptions routinely violated in the ITS datasets people apply them
to, so this skill's job is to keep you using them CORRECTLY — test the assumption,
switch to the taxonomic mode when it fails — not to talk you out of them. The
failure to guard against is reporting a process partition the data cannot support,
NOT using the framework at all.

## The framework in one paragraph (so you know what's being assumed)
Vellend's (2010) synthesis: community differences arise from **selection**
(deterministic — environment or biotic filters), **dispersal**, **drift**, and
**speciation**. Stegen et al. (2012, 2013) operationalized this: compute
**betaNTI** (beta Nearest Taxon Index — observed phylogenetic turnover vs null).
|betaNTI|>2 ⇒ selection dominates (>+2 heterogeneous/variable selection, <-2
homogeneous selection); |betaNTI|<2 ⇒ stochastic, and then **RCbray**
(Raup-Crick on Bray-Curtis) splits the stochastic part into homogenizing
dispersal, dispersal limitation, or undominated drift. This is **QPEN**
(Quantitative Process Estimation). **iCAMP** (Ning et al. 2020) improves it by
binning OTUs phylogenetically and estimating processes **per bin**, then
abundance-weighting — more robust and giving per-bin resolution. Everything
downstream depends on one thing: **that the phylogeny is meaningful.**

## The caveat that governs everything for fungi: ITS is not alignably phylogenetic
betaNTI and iCAMP's binning require a **reliable phylogenetic tree** and, more
specifically, **phylogenetic signal in the taxa's niches** (closely related taxa
must be ecologically more similar — Stegen's own precondition). For fungal **ITS**
this is a genuine problem, not a technicality — but the conclusion is *use the
right mode*, not *avoid iCAMP on ITS*; the taxonomic binning mode below is the
standard, accepted route when the tree is untrustworthy:
- ITS is a **fast-evolving, length-variable barcode**; it aligns well within a
  genus but **cannot be reliably aligned across distant fungi** (Schoch et al.
  2012 adopted it as the barcode *because* it is variable — the same property that
  makes deep alignment untrustworthy). A tree built from a bad cross-family ITS
  alignment is largely noise, and betaNTI computed on it is meaningless even
  though the code runs and returns tidy numbers.
- **So, before any phylogenetic null model on ITS:**
  1. **Test phylogenetic signal** on the tree you have (Mantel correlogram of
     niche vs phylogenetic distance, or Blomberg's K on key traits/optima across
     short tips — Stegen's within-bin signal test). NO signal ⇒ betaNTI/iCAMP
     phylogenetic mode is **not licensed**. Report that as the finding; do not
     run it anyway.
  2. If signal fails (common for cross-lineage ITS), **fall back to
     taxonomy-based binning**: iCAMP supports a taxonomic ("tax-iCAMP") /
     non-phylogenetic mode, and RCbray + a taxonomic beta-null (the
     Raup-Crick-on-taxa route) estimate the stochastic/deterministic balance
     WITHOUT a deep tree. This is the honest path for most phyllosphere ITS.
  3. 16S is far better-behaved here (alignable, phylogenetically informative) —
     the phylogenetic mode is defensible for bacteria. State which marker you're
     on and which mode you chose.
- **Bin depth matters:** phylogenetic signal in microbes is typically **local**
  (present within a bin, absent across the whole tree; Stegen 2013). iCAMP's
  binning exploits this — set the bin size so within-bin signal is actually
  present (iCAMP has a `ps.bin`/signal-test step; use it, report it), rather than
  assuming tree-wide signal.

## Relating processes to drivers (the reason you're doing this)
Once you have per-process fractions (or per-bin, per-sample process assignments),
the project question is usually "does selection get stronger with height/light?"
- Use **Mantel / partial Mantel** or, better, **MRM** (Multiple Regression on
  distance Matrices) to relate the process metric (e.g. betaNTI, or iCAMP's
  per-pair process) to environmental and spatial distance matrices. iCAMP ships
  helpers for this.
- **This is where confounded environmental gradients bite hardest.** Height, light,
  nutrient flux, and dispersal flux co-vary. A finding that "selection increases
  with height" cannot separate microclimate selection from the co-varying
  nutrient/immigration gradient. Worse, these null models specifically try to
  *quantify dispersal* — and your dispersal proxy (height/wind) is collinear with
  your selection proxy (microclimate/height). Say plainly that MRM coefficients
  here are associations under heavy collinearity, and consider variance
  partitioning to bound (not resolve) the shared fraction.

## Practical guards
- **These are permutation methods — they need adequate n and richness per sample.**
  Very small groups give unstable process fractions; report per-group n and treat
  small-n partitions as exploratory (same n-humility as the network skill).
- **Rarefy/normalize consistently** with the rest of the study — betaNTI and
  RCbray are computed on the community matrix and inherit the depth issue
  (`amplicon-community-diversity`).
- **Report the null model's settings**: number of randomizations (>=1000), the
  null algorithm (taxa-shuffle vs independent-swap), bin size, and signal-test
  result. A process partition without these is not reproducible.

## Tooling
R: `iCAMP` (Ning's package — QPEN, iCAMP, `ps.bin` signal test, `qpen`,
`icamp.big`, and the MRM/driver helpers), `picante` (betaNTI/betaNRI building
blocks, `ses.mntd`, phylogenetic-signal tests), `NST` (normalized stochasticity
ratio — a lighter-weight stochasticity estimate if full iCAMP is overkill),
`vegan` (RCbray building blocks). Tree-building for ITS (if you attempt the
phylogenetic mode at all): align within-genus/family blocks, don't trust one
global ITS alignment.

## Refs
- Vellend 2010 — the four-process synthesis the whole framework rests on.
- Stegen et al. 2012, 2013 — betaNTI/RCbray, QPEN, local-phylogenetic-signal.
- Ning et al. 2020 — iCAMP (per-bin process estimation + driver analysis).
- Schoch et al. 2012 — ITS as fungal barcode (why it is variable, hence deep-alignment-fragile).
- Companion: amplicon-community-diversity (the matrix + normalization) ·
  microbial-cooccurrence-network · fungal-guild-assignment. Driver-model
  mechanics: research-stats-advisor.
