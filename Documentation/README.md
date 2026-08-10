<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Documentation — the cross-toolkit guides

Five guides explain the pair of toolkits in this repository: what each side carries, why the two
diverge where they do, how to move an improvement from one to the other, what one measured
model-serving failure taught about verification, and the five kinds of safeguard that keep the
work honest. They sit here rather than inside either toolkit because each one is about both.

## How each guide is stored

Every guide exists three times over, and the three are not interchangeable:

- [`machine_md/`](machine_md/) holds the **machine root**, written terse for an LLM to parse. It is
  the authoritative version — corrections land here first.
- [`human_md/`](human_md/) holds the **human twin**, a translation of the machine root that preserves
  every fact while reading as prose. It is derived, not edited directly.
- [`PDF/`](PDF/) holds the **rendered PDF**, produced from the human twin. The PDF filenames carry
  the suggested reading order as a numeric prefix.

So the update path runs machine root, then human twin, then re-render. If a PDF and a machine root
ever disagree, the machine root is the one that is current.

## The five guides, in reading order

1. **Twin architecture** — [`TWIN_ARCHITECTURE`](human_md/TWIN_ARCHITECTURE.md)
   (`PDF/00_TWIN_ARCHITECTURE.pdf`). Why one methodology is carried on two platforms, the
   three-tier model that tells a shared item from a re-expressed one from a platform-only one, and
   the rule that you never copy a mechanism across the divide. Start here: it is short, and it
   supplies the model every other guide assumes.
2. **Cross-porting guide** — [`CROSS_PORTING_GUIDE`](human_md/CROSS_PORTING_GUIDE.md)
   (`PDF/01_CROSS_PORTING_GUIDE.pdf`). The ordered workflow for carrying an improvement across:
   decide the direction, classify each item, lay the items out, apply in waves, run the target's
   gates, rebuild from source, verify with fresh eyes, record the result. Worked against a real
   porting pass, including the step that went wrong.
3. **Roster comparison** — [`TOOLKIT_ROSTER_CCRT_vs_CSRTB`](human_md/TOOLKIT_ROSTER_CCRT_vs_CSRTB.md)
   (`PDF/02_TOOLKIT_ROSTER_CCRT_vs_CSRTB.pdf`). The item-by-item reference: every agent, profile,
   and skill on both sides, one line each, plus the collaboration working-sets that explain which
   specialists are designed to compose. Skim its opening sections, then return to its tables as a
   lookup.
4. **Model substitution and verified launch** —
   [`MODEL_SUBSTITUTION_AND_VERIFIED_LAUNCH`](human_md/MODEL_SUBSTITUTION_AND_VERIFIED_LAUNCH.md)
   (`PDF/03_MODEL_SUBSTITUTION_AND_VERIFIED_LAUNCH.pdf`). One measured failure — subagents answered
   by a model nobody asked for — everything measured about it, and the working verification
   construction built around it. Read it if you delegate work to subagents and your judgment
   depends on which model did that work.
5. **Assurance architecture** — [`ASSURANCE_ARCHITECTURE`](human_md/ASSURANCE_ARCHITECTURE.md)
   (`PDF/04_ASSURANCE_ARCHITECTURE.pdf`). The five kinds of safeguard these toolkits use — record,
   convention, advise, enforce, measure — which one just acted on you, and where a check of your
   own belongs.

For the working loop these toolkits serve, see [`PDF/WORKFLOW_GUIDE.pdf`](PDF/WORKFLOW_GUIDE.pdf). For
either toolkit on its own, see [`../CCRT/`](../CCRT/) and [`../CSRTB/`](../CSRTB/), each of which
ships its own quickstart and reference set.
