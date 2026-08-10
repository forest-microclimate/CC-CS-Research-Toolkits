---
name: amplicon-community-diversity
description: >
  Compute and TEST alpha- and beta-diversity from amplicon (ITS/16S) OTU/ASV
  tables — the community-ecology core of a microbiome study. Use WHEN analyzing
  phyllosphere/soil/gut amplicon diversity, choosing between rarefaction and
  other normalizations, picking an alpha metric (Fisher's alpha, Shannon, Chao1,
  Hill numbers) or a beta distance (Bray-Curtis, Aitchison, UniFrac), running
  PERMANOVA / dbRDA / CAP, or when a reviewer questions whether a diversity
  result is a library-size artifact. Carries the depth/compositionality gotchas
  that vegan/phyloseq docs assume you already know. NOT for functional-guild
  assignment (fungal-guild-assignment), co-occurrence networks
  (microbial-cooccurrence-network), or deterministic-vs-stochastic assembly
  (community-assembly-null-models).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# amplicon-community-diversity

Alpha- and beta-diversity from an amplicon OTU/ASV table, done so the number you
report reflects biology and not sequencing depth. The library docs (`vegan`,
`phyloseq`) give you the function calls; this skill gives you the decisions those
calls silently depend on — the ones that, made wrong, produce a fully
significant, fully wrong result.

## The one trap under everything: depth + compositionality
An amplicon library has an arbitrary total (the sequencer returns a roughly fixed
read count, split among taxa). So two facts govern every metric:
- **Richness rises with depth.** Deeper libraries find more rare OTUs. Comparing
  raw richness across samples of different depth measures the sequencer, not the
  community.
- **Counts are compositional.** An OTU's read count is a *fraction* of an
  arbitrary total, not an absolute abundance. Ratios between taxa are the only
  depth-stable quantity (Gloor et al. 2017, *Microbiome datasets are
  compositional: and this is not optional*).

Every choice below is downstream of handling these two. WHEN you are about to
compare a diversity number across samples ⇒ first state how depth was
controlled, or the comparison is uninterpretable.

## Decision 1 — normalize before you compare (and know the debate)
There is no free lunch; pick the least-bad option for the question and say so.
- **Rarefaction** (subsample every library to a common depth): standardizes
  sampling effort, which is what richness comparison needs, but discards reads
  and injects subsampling noise. McMurdie & Holmes 2014 (*Waste not, want not*)
  showed rarefying is statistically inadmissible **for differential-abundance
  testing**. That verdict does NOT extend cleanly to alpha richness: for
  richness across uneven depths some effort-standardization is still required,
  and rarefaction remains a defensible (if lossy) way to get it (Willis 2019
  argues instead for coverage-based estimators). Report the rarefaction depth
  and how many samples it drops — dropping the low-depth tail is a real change to
  the sampled population, not a formality.
- **Coverage-based rarefaction** (Chao & Jost 2012): equalize *sample
  completeness* rather than raw read count — usually the more defensible
  effort standard, since equal reads ≠ equal coverage across uneven communities.
- **CLR / relative abundance** (no subsampling): keep all data, work in ratio
  space. The right choice for beta-diversity and abundance; see Decisions 3-4.
- **Model-based** (offset for library size in a GLM/negative-binomial): the right
  choice when you are testing per-taxon effects (see the differential-abundance
  note in Decision 4).

## Decision 2 — alpha diversity: match the metric to the question
Metrics are not interchangeable; each weights richness vs evenness differently.
- **Richness (observed / Chao1 / ACE):** count of taxa. Maximally depth-sensitive
  — never compare across un-standardized depths. Chao1/ACE *estimate* unseen taxa
  but are unstable with singleton-inflated data (especially DADA2 ASVs, where
  singletons are largely removed — Chao1 then degenerates toward observed).
- **Shannon / Simpson:** fold in evenness; less depth-sensitive than richness but
  not immune. Simpson (dominance-weighted) is the most depth-robust common
  choice.
- **Fisher's alpha:** a log-series parameter, relatively stable across sample
  sizes — a reasonable default when depths are uneven and you still want a
  richness-flavoured scalar (it is why many phyllosphere studies use it). It
  *assumes* a log-series abundance distribution; check that assumption isn't
  wildly violated before leaning on it.
- **Hill numbers (qD):** the unifying frame — q=0 richness, q=1 exp(Shannon),
  q=2 inverse-Simpson — one diversity profile instead of arguing over metrics
  (Chao et al. 2014). Prefer reporting a Hill profile over a single scalar when
  reviewers may contest metric choice.
- **Faith's PD:** phylogenetic richness — only meaningful with a trustworthy
  tree. For ITS see the alignment caveat in `community-assembly-null-models`;
  ITS PD is fragile.

Then model the alpha value with the right structure (log-link for
right-skewed diversity, random effect for host individual / plot) — the
*modelling* mechanics (GAMM k-selection, mixed-effect specification) are the
Research Stats Advisor's + `mgcv-temporal-gam` / `brms-hierarchical-fitting`, not
this skill. This skill picks the metric; those fit it.

## Decision 3 — beta diversity: the distance IS an assumption
- **Bray-Curtis:** abundance-weighted dissimilarity, the phyllosphere default —
  but computed on raw counts it is depth-biased. Use it on rarefied or
  relative-abundance data, and say which.
- **Jaccard:** incidence (presence/absence) — robust when abundances are
  untrustworthy. **For ITS this is often the honest choice**: fungal rDNA copy
  number varies by orders of magnitude across taxa (Lofgren et al. 2019), so ITS
  read counts are a poor abundance proxy and incidence-based beta-diversity
  sidesteps the problem.
- **Aitchison** (Euclidean on CLR-transformed counts): the compositionally
  coherent distance (Gloor et al. 2017). Prefer it when you want to defend beta
  against the compositionality critique. Needs a zero-replacement / pseudocount
  step first.
- **UniFrac** (un/weighted): phylogenetic — same ITS tree caveat as Faith's PD;
  fine for 16S, fragile for ITS.

## Decision 4 — testing beta: guard the dispersion confound, respect covariance
- **PERMANOVA** (`vegan::adonis2`): tests centroid differences among groups on a
  distance matrix. **It is confounded by dispersion** — a significant PERMANOVA
  can mean different centroids OR different within-group spread. ALWAYS pair it
  with `betadisper` / PERMDISP (Anderson 2006); report both, or a centroid
  difference may just be heteroscedasticity (Anderson & Walsh 2013).
- **Term order matters:** `adonis2` is sequential by default (`by="terms"`);
  with unbalanced designs the order changes the result. Use `by="margin"` for
  order-independent tests, and set it deliberately.
- **dbRDA / CAP** (`vegan::capscale` / `dbrda`): constrained ordination that
  handles *continuous, collinear* predictors (height, gap fraction, leaf area) —
  robust against predictor covariance where a raw ordination is not (Legendre &
  Anderson 1999; Xia, Sun & Chen 2018). This is the tool when your gradients are
  confounded (they usually are — see the profile's standing caveat). Condition
  out host species / individual with `Condition()` to get the environmental
  signal net of host. For the turnover *function* along a gradient (rate/shape,
  and environment-vs-space partitioning) rather than constrained variance, use
  **GDM** — see `generalized-dissimilarity-modeling`; it is the beta counterpart
  to a GAM and the natural next step when a dbRDA triplot answers "how much" but
  not "along which gradient, and how fast."
- **Differential abundance** (which *taxa* drive the split): do NOT t-test
  proportions. Use ANCOM-BC, DESeq2, or ALDEx2 (CLR + model). This is where
  McMurdie & Holmes' anti-rarefaction verdict fully bites.

## Decision 5 — rare vs common turnover: zeta diversity
Pairwise beta (Sorensen/Jaccard) is dominated by common species. To separate
turnover in *rare* vs *widespread* taxa across many sites, use **zeta diversity**
— the mean number of shared taxa across *i* sites, decaying with zeta order
(McGeoch et al. 2019). Zeta decay that is exponential vs power-law distinguishes
stochastic from niche-structured turnover, and **multi-site GDM on zeta**
(`zetadiv::Zeta.msgdm`) relates it to environmental distance — the spline-based
extension is in `generalized-dissimilarity-modeling`. Reach here when a single
beta number hides whether the signal is in the core or the tail.

## Decision 6 — correct known biases
- **Mock community:** sequence a known-composition control and use it to bound
  PCR/copy-number/bioinformatic bias (Bakker 2018 for a fungal ITS mock). It
  won't fully correct abundances but calibrates how far to trust them.
- **Negative/extraction controls:** decontam (prevalence or frequency method)
  before diversity — low-biomass phyllosphere washes are contamination-prone, and
  a handful of reagent OTUs can dominate a low-read sample.

## Tooling
R is the native ecosystem: `phyloseq` (object + `estimate_richness`,
`ordinate`, `rarefy_even_depth`), `vegan` (`adonis2`, `betadisper`, `capscale`,
`dbrda`, `fisher.alpha`, `vegdist`), `iNEXT` (Hill-number rarefaction/
extrapolation), `zetadiv` (zeta), `ALDEx2`/`ANCOMBC`/`DESeq2` (differential
abundance), `decontam` (controls). Python: `scikit-bio` covers most distances +
PERMANOVA if you must stay in Python. Set and report the RNG seed for any
rarefaction — it is stochastic.

## Refs
- Gloor et al. 2017 — compositionality is not optional (CLR/Aitchison rationale).
- McMurdie & Holmes 2014; Willis 2019 — the rarefaction debate, both sides.
- Chao & Jost 2012; Chao et al. 2014 — coverage-based rarefaction; Hill numbers.
- Anderson 2006; Anderson & Walsh 2013 — PERMANOVA vs PERMDISP dispersion trap.
- Legendre & Anderson 1999; Xia, Sun & Chen 2018 — dbRDA/CAP for collinear drivers.
- McGeoch et al. 2019 — zeta diversity for rare-vs-common turnover.
- Bakker 2018; Lofgren et al. 2019 — fungal mock community; ITS copy-number variation.
- Companion skills: generalized-dissimilarity-modeling (turnover-vs-gradient
  function) · fungal-guild-assignment · microbial-cooccurrence-network ·
  community-assembly-null-models. Modelling mechanics: Research Stats Advisor +
  mgcv-temporal-gam / brms-hierarchical-fitting.
