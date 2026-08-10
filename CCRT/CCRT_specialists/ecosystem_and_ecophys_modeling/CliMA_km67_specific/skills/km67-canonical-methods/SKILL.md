---
name: km67-canonical-methods
description: Canonical gap-fill and height-interpolation method registry for the km67 Tapajos tower project — which engine and shipped product is authoritative for each variable (co2, tair, h2o, pamb, radiation/PAR/netrad, wind), with a code-based drift self-check. LOAD THIS BEFORE stating, comparing, editing, or building on any km67 method, or answering "what method do we use for X" / "which is the canonical engine" / "is this the latest". Prevents mis-stating the method from a stale or orphan engine file's docstring.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-28). Project-specialty carrier — installed per-project via --project-items, never into the general ~/.claude payload.

# km67 canonical methods — the authoritative method-of-record registry

**Why this skill exists.** The km67 methods were developed across many folders and
sessions with stale-vs-current versions everywhere. On 2026-07-16 an agent read one
standalone engine file (`silver_engine.R`), trusted its docstring ("one GLOBAL
fixed-basis driver bam"), and mis-stated the canonical co2/tair/h2o method — when the
SHIPPED products are actually produced by a chunked, tail-spliced, OU-bridge composite.
This skill makes that class of error hard: it pins the method-of-record per variable to
the **shipped product's actual lineage**, tombstones the traps, and ships a self-check.

## THE ONE RULE
**The canonical method for a variable is whatever the SHIPPED PRODUCT's lineage actually
ran — never a standalone engine file's docstring, filename, or your memory.** A file
named `*_engine.R` may be a candidate, a refactor, or an orphan. Confirm against the
product every time.

## How to use — before you assert, edit, or build on a km67 method
This skill ships `km67_registry.py`; import it explicitly to use these (it does not
auto-load — Claude Code skills have no kernel.py auto-load):

```python
from km67_registry import km67_whatis, km67_verify_from_code, km67_registry, km67_donotuse
```

1. `km67_whatis("co2")` — the verified engine + product + architecture for one variable.
2. `km67_verify_from_code(var, code)` — **the anti-drift self-check.** Read the shipped
   product's build source off disk (the R script that produced the product `.csv.gz`) and
   pass it as `code`; the function re-derives the architecture markers and flags any
   contradiction (e.g. a product that shows a global-bam-only signature where the registry
   says chunked composite). Run it whenever the registry might be stale, before trusting it
   in a brief, or after any re-ship. `status: "ok"` = registry matches the code; `"DRIFT"` =
   investigate.
3. `km67_registry()` / `km67_donotuse()` — full registry / tombstoned artifacts.

If `km67_verify_from_code()` returns DRIFT for any variable, STOP and reconcile before
proceeding — the registry has fallen behind the shipped artifacts.

> **Platform note (Claude Code).** The Claude Science version of this skill re-derives
> architecture from a live artifact-lineage store (`host.lineage[...]`) with a
> `km67_verify()` that pulls the product code automatically. Claude Code has no lineage
> store, so the check here (`km67_verify_from_code`) takes the product's source as an
> argument — you supply it by reading the shipped product's R build script from disk. The
> registry's artifact/version ids are Claude Science UUIDs, kept verbatim as the
> authoritative method-of-record provenance (they identify the canonical build even though
> Claude Code cannot resolve them to files).

## Method-of-record (verified 2026-07-16 from live lineage)
- **co2 / tair / h2o** — `co2_composite_engine.R` (art `a1f41c15…` / v `20fe4c5b…`), a SHARED
  3-stage composite: (S1) global hour×height diel-tensor bam priors for μ and log-σ;
  (S2) fine per-block overlapping 7-day blocks (1.4-day overlap), `s(time_scale,k≤250)` on
  the residual-to-prior, **graded COSINE tail-splice** (never butt-join), capped ±40 ppm and
  support-decayed so it reverts to the diel prior in long gaps; (S3) exact AR(1) Gaussian
  bridge on the whitened HF residual, pinned to observed flanks. Seam=0 by construction.
- **pamb** — two-regime: co2 composite engine for ≤6h gaps + a global Open-Meteo-anchored
  fit for >6h gaps. A VPD ingredient (VPD is derived per level, never interpolated).
- **radiation (netrad + PAR)** — `radiation_engine.R` (art `457b9e16…` / v `92b72a08…`).
  Above-canopy global (broadcast across height). Clearness-index, qgam TOA-bounded ceiling +
  `te(cosz,doy)` seam-free floor, sibling-coupled, 6h no-sibling cap. `om_sw` helper rejected.
- **wind** — `wind_seamfree_engine.R` (art `7c804fde…` / v `f61c03b6…`). Logistic space-time
  profile per OVERLAPPING chunk, z=0 soft prior, **PARAMETERS (not predictions) cosine
  tail-spliced**; data-calibrated RW2 derivative prior + density-gated per-height qgam envelope
  hinge + q50 diel reversion (the 2026-07-16 data-free-extension fix). Wind on its OWN heights.

## DO NOT USE (tombstoned — the drift traps)
- **`silver_engine.R`** (art `2179b76a…`, `ce176773…`) — ORPHAN candidate refactor. Docstring
  claims "one GLOBAL fixed-basis driver bam", which is **NOT** the shipped scalar architecture,
  and it is referenced by **zero** shipped products. This is the exact file that caused the
  2026-07-16 mis-statement. If you find yourself citing it as the co2/tair/h2o method, stop.

## Keeping this current
When a variable's engine or shipped product is re-shipped, update `km67_registry.py`'s `REGISTRY`
(new product/engine version ids) in the same session, then run `km67_verify_from_code()` against
the new product source to confirm the registry matches. The registry stores ids; the verify
function is the guard that the ids still describe reality. The companion prose doc lives at
`projects/Tower data gap fill and interpolation/docs/methodology/CANONICAL_METHODS.md`.
