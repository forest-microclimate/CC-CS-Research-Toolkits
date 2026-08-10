# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""km67 canonical-methods registry + drift self-check (Claude Code port).

Ships with the `km67-canonical-methods` skill; import it explicitly to use these
(it does not auto-load — Claude Code skills have no kernel.py auto-load):

    from km67_registry import km67_whatis, km67_verify_from_code, km67_registry, km67_donotuse

  km67_registry()                 -> the full registry dict
  km67_whatis(var)                -> canonical engine + product for one variable (verified facts)
  km67_donotuse()                 -> tombstoned artifacts and why
  km67_classify_arch(code)        -> architecture markers present in a block of engine/product code
  km67_verify_from_code(var,code) -> RE-DERIVE the architecture from the SHIPPED PRODUCT's source
                                     you pass in, and flag any contradiction against the registry
                                     (the anti-drift self-check, Claude-Code form)

The discipline this enforces: the canonical method for a variable is whatever the
SHIPPED PRODUCT's code actually ran -- never a standalone engine file's docstring.

PLATFORM NOTE (Claude Code): the Claude Science original re-derives architecture from a
live artifact-lineage store (`host.lineage[...]`). Claude Code has no lineage store, so the
verify step here takes the shipped product's source code as an argument — read the product's
R script (or its build log) off disk and pass it in. The registry ids below are Claude Science
artifact UUIDs, retained verbatim as the authoritative method-of-record provenance.
"""
import re

# --- REGISTRY: verified 2026-07-16 from live artifact lineage (not from file docstrings) ---
REGISTRY = {
 "co2": {
   "product_file": "co2_composite_filled_9level.csv.gz",
   "product_artifact": "63c57ffb-284c-464e-b69c-29adc7d9819d",
   "product_version": "7ab96351-79f3-419c-81d7-5cafc0d33615",
   "engine_file": "co2_composite_engine.R",
   "engine_artifact": "a1f41c15-625a-45e5-828b-e215b23c6e31",
   "engine_version": "20fe4c5b-72d7-495a-9225-acd58df47700",
   "architecture": "3-stage composite: (S1) GLOBAL hour x height diel-tensor bam priors for mu and log-sigma; (S2) FINE per-block overlapping 7d blocks (1.4d overlap), s(time_scale,k<=250) on residual-to-prior, graded COSINE tail-splice, capped +/-40 ppm & support-decayed (TAU=12=6h) so it reverts to the diel prior in long gaps; (S3) exact AR(1) Gaussian bridge on whitened HF residual, pinned to observed flanks.",
   "seam_discipline": "overlapping blocks + cosine tail-splice on the fine correction; S1 global => seam=0 by construction. NOT a butt-join.",
   "validation": "held-out variance_ratio_anom ~1.00, cov95 ~0.90, seam=0; damping d=0.90 (full-span 2002-2020).",
 },
 "tair": {
   "product_file": "tair_composite_filled_8level.csv.gz",
   "product_artifact": "ba7a5419-97f3-4f6b-a33d-f84a4e6df050",
   "product_version": "198ee29e-a9a0-4148-bc6e-0e2a9f9a91b5",
   "engine_file": "co2_composite_engine.R (SHARED; tair sources it directly)",
   "engine_artifact": "a1f41c15-625a-45e5-828b-e215b23c6e31",
   "engine_version": "20fe4c5b-72d7-495a-9225-acd58df47700",
   "architecture": "same 3-stage composite as co2 (SHARED engine).",
   "seam_discipline": "as co2.",
   "validation": "damping d=0.96 (full-span, was prov 0.72); seam=0.",
 },
 "h2o": {
   "product_file": "h2o_composite_filled_9level.csv.gz",
   "product_artifact": "3166558d-f9e1-405b-8256-1703798a5ac2",
   "product_version": "5c33c7e2-89a4-4ee2-881e-7d0f4066c6d9",
   "engine_file": "co2_composite_engine.R (SHARED)",
   "engine_artifact": "a1f41c15-625a-45e5-828b-e215b23c6e31",
   "engine_version": "20fe4c5b-72d7-495a-9225-acd58df47700",
   "architecture": "same 3-stage composite as co2 (SHARED engine). H2O safety: never impute where NO profile level has an observed H2O (require_min_obs_on_profile=1).",
   "seam_discipline": "as co2.",
   "validation": "damping d=0.75 (full-span, was prov 0.87); seam=0.",
 },
 "pamb": {
   "product_file": "pamb_composite_filled.csv.gz",
   "product_artifact": "f2940ba4-0ac8-4d8d-8848-e760db33c314",
   "product_version": "535a54ae-36b5-4d74-a5c4-905ed06447a2",
   "engine_file": "co2_composite_engine.R (local <=6h regime) + inline global Open-Meteo-anchored fit (>6h regime)",
   "engine_artifact": "a1f41c15-625a-45e5-828b-e215b23c6e31",
   "engine_version": "20fe4c5b-72d7-495a-9225-acd58df47700",
   "architecture": "TWO-REGIME: local composite fill for <=6h gaps (co2 engine), then a GLOBAL Open-Meteo (om_pa)-anchored fit for >6h gaps. VPD ingredient (not interpolated directly).",
   "seam_discipline": "local composite seam=0; global OM tier seamless by construction.",
   "validation": "OM tested as helper; two-stage local-then-global per user spec.",
 },
 "radiation": {
   "product_file": "radiation_composite_filled.csv.gz",
   "product_artifact": "e62704b6-cc36-4051-a1d7-c7b847e50a05",
   "product_version": "317d94db-4bf6-4002-8482-02a1f938b41f",
   "engine_file": "radiation_engine.R",
   "engine_artifact": "457b9e16-aead-468b-a795-fb31f0d5cfc2",
   "engine_version": "92b72a08-c67d-40c3-86d9-b7861c63ca26",
   "architecture": "ABOVE-CANOPY GLOBAL (broadcast across height, not interpolated). netrad + PAR via clearness index; qgam TOA-bounded ceiling + te(cosz,doy) seam-free floor; sibling-coupled (PAR<->netrad daytime); 6h cap unless a live tower sibling is present. om_sw helper REJECTED (fails held-out).",
   "seam_discipline": "te(cosz,doy) cyclic envelope is continuous everywhere (fixed the 40-52 umol seasonal seam).",
   "validation": "TOA ceiling + diel floor; 4-detector stuck-sensor flagging; 19 flat-day union excluded (PAR 12 + netrad 8).",
 },
 "wind": {
   "product_file": "wind_seamfree_filled_heights.csv.gz (sensor+ground) / wind_seamfree_grid_05m.csv.gz (0.5m grid)",
   "product_artifact": "047e1869-ccc7-41b8-b82e-50b135482af0",
   "product_version": "e5cf49b3-158d-45b3-a9c9-0abe4629df22",
   "engine_file": "wind_seamfree_engine.R",
   "engine_artifact": "7c804fde-6f15-4e15-b02f-3f2c890e4476",
   "engine_version": "f61c03b6-875e-4342-9a59-48ee7603de77",
   "architecture": "logistic space-time profile wind(z,t)=Asym[t]*inv_logit((z-xmid)/scal)+slope*softplus(z-ZTOP) fit per OVERLAPPING chunk (nls.lm); z=0 soft prior ~0 m/s; PARAMETERS (not predictions) cosine tail-spliced across overlaps; data-calibrated RW2 derivative prior + density-gated per-height qgam envelope hinge + q50 diel reversion (2026-07-16 spike fix); het-sigma Gamma-log draw with per-height/diel skew, damped, innovation-clipped. Wind on its OWN heights, not scalar heights.",
   "seam_discipline": "PARAMETER splice across oversized-overlap chunks; src-transition step ratio ~0.61 (seam-free).",
   "validation": "133/134 blocks converged; var_ratio_anom 0.96-1.03; ws4 draw_skew 1.51; envelope containment 99.2-99.95% data-free within, in-data exceedance <=0.21%.",
 },
}

# --- DO-NOT-USE: tombstoned artifacts (the drift traps) ---
DO_NOT_USE = {
 "silver_engine.R": {
   "artifacts": ["2179b76a-fea7-4fff-8a5c-03833331009d", "ce176773-9428-483d-b848-787472b6a286"],
   "reason": "ORPHAN candidate refactor. Its docstring says 'one GLOBAL fixed-basis driver bam' -- this is NOT the shipped scalar architecture. Referenced by ZERO shipped products. Trusting this file's docstring caused an agent to mis-state the co2/tair/h2o method as global-bam on 2026-07-16. The shipped scalars use co2_composite_engine.R (chunked composite).",
 },
}

# architecture-marker probes used by km67_verify_from_code to RE-DERIVE arch from product/engine code
ARCH_MARKERS = {
 "chunked_overlap_block": ["BLK", "OVL", "per-block", "overlapping"],
 "cosine_tail_splice": ["cos_w", "cosine", "tail-splice"],
 "ou_ar1_bridge": ["ar1_bridge", "OU-bridge", "Gaussian bridge"],
 "logistic_profile": ["plogis", "inv_logit", "Asym"],
 "qgam_toa_envelope": ["qgam", "clearness", "TOA"],
 "global_om_anchor": ["open_meteo", "om_pa", "global_OM"],
 "global_bam_only": ["one GLOBAL", "global fixed-basis", "GLOBAL => seam"],
}

def km67_registry():
    """Return the full canonical-methods registry (dict keyed by variable)."""
    return REGISTRY

def km67_donotuse():
    """Return the tombstoned (DO-NOT-USE) artifacts and the reason each is retired."""
    return DO_NOT_USE

def km67_whatis(var):
    """Print + return the canonical engine and shipped product for ONE variable.
    These are verified facts; run km67_verify_from_code(var, code) to re-confirm against the
    shipped product's source."""
    r = REGISTRY.get(var)
    if r is None:
        print("unknown variable %r; known: %s" % (var, ", ".join(REGISTRY)))
        return None
    print("=== km67 canonical method: %s ===" % var)
    print("  ENGINE : %s" % r["engine_file"])
    print("           artifact %s  v %s" % (r["engine_artifact"], r["engine_version"]))
    print("  PRODUCT: %s" % r["product_file"])
    print("           artifact %s  v %s" % (r["product_artifact"], r["product_version"]))
    print("  ARCH   : %s" % r["architecture"])
    print("  SPLICE : %s" % r["seam_discipline"])
    print("  VALID  : %s" % r["validation"])
    return r

def km67_classify_arch(code):
    """Re-derive the architecture markers present in a block of engine/product code."""
    found = set()
    low = code.lower()
    for name, kws in ARCH_MARKERS.items():
        if any(kw.lower() in low for kw in kws):
            found.add(name)
    return found

def km67_verify_from_code(var, code, verbose=True):
    """ANTI-DRIFT SELF-CHECK (Claude Code form). Pass the SHIPPED PRODUCT's source code
    (read the product's R build script off disk) and this re-derives the architecture
    markers and flags any that contradict the registry -- specifically the tombstoned
    'global_bam_only' signature where the registry says a chunked composite.

    Returns {status, derived_arch, R_files_in_code, expected_engine}. status 'ok' = the
    code's architecture matches the registry; 'DRIFT' = the shipped product shows the
    global-bam-only signature -> STOP and reconcile before trusting the registry.

    (The Claude Science original pulls `code` from host.lineage[product_version]; Claude Code
    has no lineage store, so you supply the source explicitly.)"""
    r = REGISTRY.get(var)
    if r is None:
        print("unknown variable %r; known: %s" % (var, ", ".join(REGISTRY)))
        return {"status": "UNKNOWN_VAR"}
    code = code or ""
    arch = km67_classify_arch(code)
    rfiles = sorted(set(re.findall(r'/(?:v[0-9a-f]{8}_)?([A-Za-z0-9_]+\.R)', code)))
    drift = "global_bam_only" in arch
    out = {
        "status": "DRIFT" if drift else "ok",
        "derived_arch": sorted(arch),
        "R_files_in_code": rfiles,
        "expected_engine": r["engine_file"],
    }
    if verbose:
        flag = "  <-- DRIFT: shipped product shows global-bam-only!" if drift else ""
        print("%-10s %-6s arch=%s%s" % (var, out["status"], sorted(arch), flag))
    return out
