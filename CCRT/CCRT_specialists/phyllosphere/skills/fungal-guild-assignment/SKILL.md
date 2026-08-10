---
name: fungal-guild-assignment
description: Assign fungal OTUs/ASVs to functional guilds / trophic modes (saprotroph, pathogen, symbiotroph, endophyte, ...) from taxonomy, via FUNGuild and FungalTraits, and interpret the result HONESTLY as the provisional, genus-level inference it is. Use WHEN mapping fungal taxa to ecological function, asking whether saprotrophs increase in older leaves or along a gradient, adding a "functional" layer to an ITS study, or turning a taxonomic table into a trophic-mode composition. Carries the confidence-ranking, taxonomic-resolution, and unassigned-fraction caveats that make or break the interpretation. NOT for the diversity pipeline (amplicon-community-diversity), networks (microbial-cooccurrence-network), or assembly processes (community-assembly-null-models).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-14). Ported from the Claude Science fungal-guild-assignment skill (toolkit refresh, from crt_science_bundle v1.3). Clean copy: genericized the Claude-Science agent-profile confound reference and the Research Stats Advisor agent ref (-> research-stats-advisor skill); method content unchanged.

# fungal-guild-assignment

Turn a fungal taxonomy table into functional guilds — decomposer, pathogen,
mutualist, endophyte — while being honest that this is a **taxonomy-to-function
inference by database lookup**, not a measurement of what the fungi were doing.
Used well it is a legitimate, publishable layer (with hedged language); used
naively it manufactures confident functional stories the data cannot support.

## Frame the provisionality as the method, not a flaw
A guild call says "fungi in this genus are *typically* saprotrophic in the
literature," not "this fungus was decomposing this leaf." Many fungi are
**plastic** — a genus can be endophytic in living tissue and saprotrophic once
the leaf senesces (the endophyte→saprotroph continuum is real biology, not a
database error; Promputtha et al. 2007). So the honest deliverable is a
*hypothesis-generating* shift in guild composition ("older leaves show a higher
relative abundance of taxa whose genera are typically saprotrophic, consistent
with an endophyte-to-saprotroph transition"), with the inferential distance
stated. WHEN you write a guild result ⇒ attach the hedge in the same sentence;
the provisionality is a feature to surface, not hide.

## Prerequisite: trustworthy taxonomy first
Guild tools are pure taxonomy lookups — garbage taxonomy in, garbage guilds out.
Before assignment:
- Assign ITS taxonomy against **UNITE** (the ITS reference; the species-hypothesis
  dynamic clusters), not a generic BLAST-nt hit. 16S guilds are far less
  developed — FAPROTAX exists but is coarse; this skill is ITS-centric.
- Guild resolution is **genus-level at best.** Species-level guild calls over the
  reference's precision are false confidence. If your OTUs are confidently
  resolved only to family, expect a large unassigned fraction — that is correct
  behavior, not a failure.

## Tool 1 — FUNGuild (Nguyen et al. 2016)
Assigns each taxon a **trophic mode** (Pathotroph / Saprotroph / Symbiotroph and
combinations) and finer **guilds** (e.g. Plant Pathogen, Wood Saprotroph,
Arbuscular Mycorrhizal, Endophyte). Two things determine whether the output is
usable:
- **Confidence ranking — filter on it, always.** Each assignment carries
  "Highly Probable / Probable / Possible." Reporting "Possible" calls as fact is
  the single most common misuse. Keep Probable+ for headline claims; report what
  the "Possible" tier would add separately, if at all.
- **Multi-guild taxa are ambiguous by design.** A genus tagged
  "Endophyte-Plant Pathogen-Saprotroph" is not noise to force into one bin — it
  reflects genuine plasticity. Decide up front how you handle multi-assignment
  (drop, split-weight, or keep as an explicit "facultative" class) and apply it
  uniformly.

## Tool 2 — FungalTraits (Polme et al. 2020) — prefer for primary lifestyle
A larger, more recent, curated genus-level trait database; generally better
coverage and more current taxonomy than FUNGuild's static file. Gives a
**primary vs secondary lifestyle** plus traits (growth form, fruitbody,
ecology). Prefer FungalTraits for the primary trophic assignment and use FUNGuild
for its finer guild vocabulary / cross-check; where they disagree, that
disagreement IS the uncertainty — report it rather than picking the convenient
one.

## The unassigned fraction is a result, not a rounding error
A large share of tropical / phyllosphere ITS OTUs will be **unassigned** (unknown
genus, or a genus absent from the trait DB). Tropical endophyte assemblages are
dark-taxa-rich (Arnold & Lutzoni 2007). Two rules:
- **Report the assigned/unassigned split explicitly** (as % of OTUs AND as % of
  reads — they differ, since abundant OTUs are better characterized). A guild
  composition computed only over the assigned fraction, presented as the whole
  community, is misleading.
- **Test whether "unassigned" itself varies with your gradient.** If older leaves
  or high-light leaves are systematically more (or less) assignable, the guild
  shift you see in the assigned fraction may be an assignability artifact, not an
  ecological one.

## How to analyze the guild layer once assigned
- Compute guild **relative abundance per sample** (on the SAME normalization you
  justified in `amplicon-community-diversity` — guilds inherit the
  compositionality problem; a guild proportion is still a proportion of an
  arbitrary total).
- Model guild proportion vs the gradient with a compositional-aware approach
  (beta-regression on the proportion, or CLR on the guild table), not a raw
  correlation. The stats mechanics are the research-stats-advisor's.
- Keep the language causal-cautious and thread the confounded-gradient caveat:
  more saprotroph-typical taxa in older or lower-canopy leaves is consistent with
  senescence-driven succession OR with the co-varying nutrient/dispersal gradient
  — guild data alone cannot separate them.

## Tooling
FUNGuild: the `FUNGuildR` package or the python `Guilds.py` script — both take a
taxonomy string column. FungalTraits: the published supplementary table joined on
genus (there is a helper in the `microeco` and `fungaltraits` R packages). Do the
taxonomy assignment upstream (UNITE via DADA2's `assignTaxonomy`, or QIIME2
`q2-feature-classifier`) — this skill starts from a taxonomy table.

## Refs
- Nguyen et al. 2016 — FUNGuild (trophic mode + guild + confidence ranking).
- Polme et al. 2020 — FungalTraits (genus-level, primary/secondary lifestyle).
- Promputtha et al. 2007 — endophyte-to-saprotroph transition (why plasticity is real).
- Arnold & Lutzoni 2007 — tropical endophyte hyperdiversity / dark taxa (why unassigned is large).
- Companion: amplicon-community-diversity (normalization the guild table inherits) ·
  community-assembly-null-models. Modelling: research-stats-advisor.
