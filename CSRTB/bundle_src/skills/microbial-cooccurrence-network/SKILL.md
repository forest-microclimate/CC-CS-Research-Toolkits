---
name: microbial-cooccurrence-network
description: >
  Infer and interpret microbial co-occurrence / association networks from
  amplicon (ITS/16S) data WITHOUT the compositional false-correlation artifact.
  Use WHEN building a co-occurrence network, asking which taxa co-occur or
  exclude each other, computing network topology (hubs, modules, keystone taxa)
  across conditions or a gradient, or when someone proposes correlating OTU
  tables with Pearson/Spearman. Carries the compositionality artifact, the
  small-n instability limit, and the prevalence-filtering and stability-
  selection steps that separate a real network from noise. NOT for
  alpha/beta-diversity (amplicon-community-diversity), guild assignment
  (fungal-guild-assignment), or assembly-process inference
  (community-assembly-null-models).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# microbial-cooccurrence-network

A co-occurrence network is a hypothesis about which taxa associate — potential
interactions, shared niches, co-dispersal. It is easy to compute and easy to get
catastrophically wrong, because the two most natural moves (correlate the counts;
build the network from every OTU) both produce dense, confident, **fake**
networks. This skill is mostly about not doing those.

## Fatal error 1 — correlating compositional data
Amplicon counts are proportions of an arbitrary total. When one abundant taxon
rises, every other taxon's proportion must fall — so **Pearson/Spearman on
OTU counts invents negative correlations that are pure closure artifact**, not
biology (Friedman & Alm 2012; Gloor et al. 2017). This is not a small bias; it is
the dominant signal in a naive correlation network. NEVER build a microbial
network from `cor()` on a count or relative-abundance table. Use a method built
for compositional data:
- **SparCC** (Friedman & Alm 2012): estimates correlations from log-ratios,
  robust to closure. The original; still a fine baseline.
- **SPIEC-EASI** (Kurtz et al. 2015): infers *conditional independence* (a
  graphical model, not marginal correlation) on CLR-transformed data — so it
  removes indirect edges (A-C spuriously linked only because both track B), which
  correlation methods cannot. Preferred default. Two modes: neighborhood
  selection (MB) and glasso; MB is usually more stable.
- **SPRING** (Yoon et al. 2019): SPIEC-EASI's idea with a
  semiparametric rank correlation (better for the zero-inflation of ITS) — prefer
  for sparse, zero-heavy fungal tables.
- **propr** (proportionality, Quinn et al. 2017): if you want associations without
  a graphical-model assumption.
Correlation-based (CoNet-style ensemble) is acceptable only with an explicit
compositional correction; if you use it, say which.

## Fatal error 2 — inferring on n you don't have
Network inference estimates ~p2/2 parameters (all taxon pairs) from n samples.
With p in the hundreds of OTUs and n in the dozens (a typical phyllosphere
study — e.g. n≈40-75 leaves), the problem is wildly underdetermined and the
network is **unstable**: re-run on a bootstrap and half the edges move. Two
non-negotiable defenses:
- **Prevalence-filter hard before inference.** Keep only OTUs present in a
  meaningful fraction of samples (commonly ≥20-30%, or a min-count-in-min-samples
  rule). This is not optional tidying — rare-OTU pairs are the least estimable and
  the most artifact-prone edges. A phyllosphere table can drop from thousands of
  OTUs to a few hundred; that is correct.
- **Use stability selection, not a p-value threshold.** SPIEC-EASI's **StARS**
  (Liu et al. 2010) picks edge sparsity by subsampling and keeping only edges that
  recur across subsamples. Report the StARS variability threshold. An edge that
  isn't stable under subsampling is not an edge.
- **State the n-limit out loud.** With small n, interpret *topology* (is it
  modular? more connected under condition X?) cautiously and do NOT over-read
  individual edges or "keystone" calls. Say the network is exploratory.

## Comparing networks across a gradient (the usual real question)
"Is the network more connected / more modular high in the canopy vs low?" is the
interesting question and the treacherous one, because **network metrics are
sensitive to n and to OTU count per group.** Guards:
- Equalize sample size across the groups you compare (subsample the larger group),
  or the denser network may just be the better-sampled one.
- Use a null model for topology: compare observed modularity / connectance to
  randomized networks with the same degree distribution, not to zero.
- For a formal difference test, use **NetCoMi** (Peschel et al. 2021) — it does
  constructing, comparing, and differential-network analysis with permutation
  tests and handles the equalization for you. Prefer it for any across-condition
  comparison rather than eyeballing two graphs.
- Keystone/hub taxa: define the criterion (high degree + high closeness + low
  betweenness is the common "hub" definition) before looking, and treat hub calls
  from small-n networks as candidates for follow-up, not conclusions.

## What an edge does and does not mean
Co-occurrence ≠ interaction. An edge can be a true biotic interaction, a shared
environmental preference (both taxa like wet low-canopy leaves — the profile's
standing confound, now at the pairwise level), co-dispersal, or a host-driven
co-selection. A network cannot distinguish these; pair strong edges with the
guild layer (`fungal-guild-assignment`) or an assembly analysis
(`community-assembly-null-models`) to reason about mechanism, and keep the
language at "association."

## Tooling
R: `SpiecEasi` (SPIEC-EASI + SparCC + StARS), `SPRING`, `NetCoMi` (comparison +
differential nets, wraps most estimators), `igraph` (topology metrics),
`propr`. Report: estimator + parameter (MB vs glasso), prevalence filter,
StARS threshold, n per group, and the seed. Network layout/plots are a
`figure-style` job once the graph object exists.

## Refs
- Friedman & Alm 2012 — SparCC; the compositional false-correlation problem.
- Kurtz et al. 2015 — SPIEC-EASI (conditional independence, removes indirect edges).
- Yoon et al. 2019 — SPRING (rank-based, zero-inflation-aware, good for ITS).
- Liu et al. 2010 — StARS stability selection.
- Peschel et al. 2021 — NetCoMi (network construction + comparison).
- Quinn et al. 2017 — proportionality (propr).
- Companion: amplicon-community-diversity · fungal-guild-assignment ·
  community-assembly-null-models. Modelling/plots: Research Stats Advisor · figure-style.
