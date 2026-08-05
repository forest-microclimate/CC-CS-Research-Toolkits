<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORMAT: machine-md
# DOC_ID: <project-or-crt>/provenance-lineage
# DOC_CURRENCY: CURRENT (STATE face) + APPEND_ONLY (HISTORY face)
# AUTHORITY_CLASS: A1_CURRENT_OWNER
# VERIFICATION_STATUS: N/A (this IS the provenance record; per-record semantic assertions carried below)
# TASK_STATUS: ACTIVE
# AS_OF: <ISO-8601 + tz>
# TOPIC_ID: provenance-lineage
# DDC_CATEGORY: DDC-15 (HYBRID)
# SUPERSEDES: <doc_id or ->   ; SUPERSEDED_BY: <doc_id or ->
#
# PURPOSE (DDC-15): lineage/source/hash/currency of datasets + key outputs — where each came from,
#   how transformed, under what code/env/config, with what known limitations — so a downstream user
#   can interpret an artifact without re-deriving the project.
# HYBRID CONTRACT:
#   STATE face   = the ONE canonical current record per product; supersede IN PLACE on a new version.
#   HISTORY face = append-only run/version lineage trail (never rewrite a past run-record).
# CHECKER enforces:
#   - every product run-record carries ALL required fields, non-empty:
#         id | timestamps+tz | code_rev+dirty_fingerprint | env_identity |
#         inputs(path+role+schema+sha256)* | resolved_config | outputs(schema+row_count+sha256)* |
#         semantic_assertions | limitations | supersession_pointer
#         [REQ: in-band STATUS header / run-record required fields (id, timestamps+tz, code rev+dirty fingerprint, env identity, input paths+roles+schemas+hashes, resolved config, output schemas+row-counts+hashes, semantic assertions, limitations, supersession pointer)]
#   - source/raw records immutable: a correction is a NEW curation-layer record referencing the source
#         [REQ: raw/source immutable; corrections enter through a declared curation layer (never in-place edit)]
#   - sha256 present AND labeled byte-identity; a SEPARATE semantic_assertions field carries meaning
#         [REQ: checksum recorded but explicitly = byte identity, NOT semantic meaning]
#   - exactly one CANONICAL_OWNER=yes record per product; each generated view carries source_id + source_hash + generation_time
#         [REQ: one canonical product owner; generated views carry source id+hash+generation-time]

## STATE face — canonical current record per product (supersede IN PLACE on a new version)

### PRODUCT <prod-id>   (role: RAW_SOURCE | DERIVED | GENERATED_VIEW)
- CANONICAL_OWNER: yes                 <!-- exactly one CANONICAL_OWNER=yes record per product -->
- RUN_ID: <id>
- TIMESTAMPS: <start / end, ISO-8601 + tz>
- CODE_REV: <commit/sha>   DIRTY_FINGERPRINT: <clean | hash of uncommitted diff>
- ENV_IDENTITY: <env name + lockfile/hash>
- INPUTS:
    - path=<path|version_id>   role=<input role>   schema=<schema id/desc>   sha256=<64-hex>
    - path=<...>               role=<...>          schema=<...>              sha256=<...>
- RESOLVED_CONFIG: <the run's OWN resolved config (not inferred from another run) — path/inline>
- OUTPUTS:
    - schema=<schema id/desc>   row_count=<n>   sha256=<64-hex>
- SEMANTIC_ASSERTIONS: <what the bytes MEAN + which assertions were checked>   <!-- distinct from sha256; a hash match is NOT semantic validity -->
- LIMITATIONS: <known caveats a downstream user must respect>
- SUPERSESSION_POINTER: <version_id this record supersedes, or ->

### PRODUCT <view-id>   (role: GENERATED_VIEW)
- CANONICAL_OWNER: no                  <!-- a generated view is a derivative, never a second canonical owner -->
- SOURCE_ID: <canonical product id>   SOURCE_HASH: <64-hex>   GENERATION_TIME: <ISO-8601 + tz>
- <remaining run-record fields as above; the view points back to its canonical source id+hash+time>

## HISTORY face — append-only run/version lineage trail (newest first; never rewrite a past run-record)

- <ISO-8601 + tz>  <prod-id>  run <RUN_ID>  outputs sha256=<...>  supersedes=<prior version_id>       by=<who>
- <ISO-8601 + tz>  <prod-id>  CURATION correction of <source RUN_ID>  reason=<...>  new_sha256=<...>  by=<who>
