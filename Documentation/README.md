<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Documentation — the cross-toolkit guides

Three guides explain the pair of toolkits in this repository: what each side carries, why the two
diverge where they do, and how to move an improvement from one to the other. They sit here rather
than inside either toolkit because each one is about both.

## How each guide is stored

Every guide exists three times over, and the three are not interchangeable:

- [`machine_md/`](machine_md/) holds the **machine root**, written terse for an LLM to parse. It is
  the authoritative version — corrections land here first.
- [`human_md/`](human_md/) holds the **human twin**, a translation of the machine root that preserves
  every fact while reading as prose. It is derived, not edited directly.
- [`PDF/`](PDF/) holds the **rendered PDF**, produced from the human twin.

So the update path runs machine root, then human twin, then re-render. If a PDF and a machine root
ever disagree, the machine root is the one that is current.

## The three guides

- **Roster comparison** — [`TOOLKIT_ROSTER_CCRT_vs_CSRTB`](human_md/TOOLKIT_ROSTER_CCRT_vs_CSRTB.md).
  The item-by-item reference: every agent, profile, and skill on both sides, one line each, plus the
  collaboration working-sets that explain which specialists are designed to compose. Skim it first,
  then return to it as a lookup.
- **Twin architecture** — [`TWIN_ARCHITECTURE`](human_md/TWIN_ARCHITECTURE.md). Why one methodology
  is carried on two platforms, the three-tier model that tells a shared item from a re-expressed one
  from a platform-only one, and the rule that you never copy a mechanism across the divide. This is
  the guide that teaches you to read a difference between the two sides instead of reflexively
  closing it.
- **Cross-porting guide** — [`CROSS_PORTING_GUIDE`](human_md/CROSS_PORTING_GUIDE.md). The ordered
  workflow for carrying an improvement across: decide the direction, classify each item, lay the
  items out, apply in waves, run the target's gates, rebuild from source, verify with fresh eyes,
  record the result. Worked against a real porting pass, including the step that went wrong.

## Suggested reading order

Start with **twin architecture** — it is short, and it supplies the model the other two assume. Read
**cross-porting** next if you intend to change either toolkit, since it turns that model into a
procedure. Treat the **roster comparison** as reference: skim its opening sections for the structure,
then use its tables when you need a specific item.

For the working loop these toolkits serve, see [`PDF/WORKFLOW_GUIDE.pdf`](PDF/WORKFLOW_GUIDE.pdf). For
either toolkit on its own, see [`../CCRT/`](../CCRT/) and [`../CSRTB/`](../CSRTB/), each of which
ships its own quickstart and reference set.
