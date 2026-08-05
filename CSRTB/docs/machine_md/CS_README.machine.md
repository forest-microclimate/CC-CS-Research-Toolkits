# CS_README.machine.md
# STATUS: CURRENT (2026-08-03). Front-door orientation for the CRT Science Customization Bundle v2.11 (52 skills / 18 profiles). Machine-optimized ROOT; human twin = CS_README.md (this file is authoritative — edit here first).
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# AUDIENCE: a user or agent arriving at the bundle. What it IS, what's in it, how to install + verify, how it's laid out. Day-one usage → CS_QUICKSTART; full reference → CS_USAGE_DETAILED.

## WHAT IT IS
A portable bundle of GENERALIZABLE Claude Science customizations for scientific research, coding, and modeling — skills + agent profiles + kernel gates — captured from a working research setup and scrubbed of everything project-specific. Run one installer in a Science repl cell and the account inherits the same methodology, skills, and agent roster. This is the Claude SCIENCE twin of the Claude Research Toolkit (the Claude Code carrier); the two share most methodology content, re-expressed in each platform's own primitives.

## WHAT'S INCLUDED (counts recomputed from crt_science_bundle.json 2026-08-02: 52 skills / 18 profiles; v2.11)
- SKILLS (52) → auto-load via host.skills; some carry a kernel.py SIDECAR of plain callables (no CLI, no `__main__`). Groups: workflow/agency (plan · collab · solo · supervisory-workflow · …), domain method (mgcv-temporal-gam, brms-hierarchical-fitting, gap-fill-imputation, …), toolkit-builder (bash-hook-contract, toolkit-extension-authoring, software-craft, …).
- PROFILES (18) → agent personas dispatched via host.delegate; GENERALIST (daily driver, full reach) + 17 named specialists (PLANNER, SOFTWARE_DEVELOPER, RESEARCH_STATS_ADVISOR, LLM_DOC_ARCHITECT, the domain modelers, …).
- KERNEL GATES → fail-closed routing/verification gates carried as skill sidecars: delegation-planning (model-route + plan-lint), directing-execution (confirm-before-stop), provenance-guard (verify-before-assert), verification-loop (require-receipt).
- FULL ROSTER (every skill + profile, one line each) → CS_USAGE_DETAILED (single source; not duplicated here to avoid drift).

## INSTALL (mechanics + paste-ready block live in CS_INSTALL_STARTER_v2.11.md — referenced, not duplicated)
Upload crt_science_bundle.json + install_crt_science.py into the Science project, then in a repl cell:
  `exec(open("install_crt_science.py").read()); install_crt_science()`   (non-destructive default; `overwrite=True` to update an item that exists but DIFFERS).
`host` is pre-injected in the repl kernel. The installer is idempotent: create-if-absent, byte-identical = no-op, exists-but-differs = SKIPPED + reported unless overwrite=True. The full paste-ready block and its acceptance probes are in CS_INSTALL_STARTER_v2.11.md.

## POST-INSTALL VERIFICATION (summarized from CS_INSTALL_STARTER steps 3–5)
1. PRESENCE: the installer reports 52 skills / 18 profiles updated/created, no InstallVerificationError (a content-hash manifest re-reads the live account and fails closed on residual drift).
2. KERNEL-GATE SMOKE (host-independent — must pass identically to the dev-side fixtures): model_route_gate FAILs on claude-opus-5 and PASSes on a valid tier map; confirm_before_stop FAILs with no receipts; verify_before_assert FAILs on a memory-only source; require_receipt FAILs with no receipt.
3. LIVE ROUTING: one host.delegate probe on a T4 model (claude-haiku-4-5) runs on the requested model. (Never dispatch any probe to claude-opus-5 — the ban applies to probes too.)
4. SIDECAR ACCEPTANCE: the four sidecar skills (delegation-planning, directing-execution, provenance-guard, verification-loop) re-probe the publish gate and return ok=True.

## LAYOUT (bundle dir)
```
CSRTB/
├── bundle_src/                       SOURCE OF TRUTH (edit here, then rebuild)
│   ├── skills/     (52)              one dir per skill: SKILL.md (+ optional kernel.py sidecar)
│   └── profiles/   (18)              one JSON per agent profile
├── crt_science_bundle.json          BUILT artifact (build_crt_science_bundle.py from bundle_src) — NEVER hand-edit
├── build_config.json                bundle_version (authoritative) + build metadata
├── VERSION                          the bundle version, mirroring build_config.json's bundle_version
├── install_crt_science.py           the installer (run in a Science repl cell)
├── check_bundle_parity.py · check_sidecar_contract.py · check_currency.py   ship/verify gates
├── CS_INSTALL_STARTER_v2.11.md      paste-ready USER-RUN install + acceptance probes
└── docs/{machine_md,human_md}/      this doc set (CS_README · CS_QUICKSTART · CS_USAGE_DETAILED · CS_ADVANCED)
```

## THE DOC SET (where to go next)
- CS_README (this) = orientation front door — points you to the rest.
- CS_QUICKSTART = day-one recipe for a new Science user.
- CS_USAGE_DETAILED = full reference + the complete 52/18 roster.
- CS_ADVANCED = architecture (profiles/skills/kernels), host.* API, memory-as-poison-surface, extension authoring.
- CS_INSTALL_STARTER_v2.11.md (bundle root) = the paste-ready user-run install + acceptance probes.

## UNINSTALL / REPLAY
There is no uninstall.sh (CS installs into the account, not a file tree). Re-running install_crt_science.py is safe: byte-identical items are no-ops, and an item that exists but DIFFERS is skipped-and-reported unless overwrite=True — so a re-run never silently clobbers the account's own same-named item. `verify_against_manifest(bundle_path)` re-checks the live account against the bundle at any time.

## NOT INCLUDED (deliberately)
Anything tied to a specific research project — domain physics, site/data facts, project pipelines, per-project rules. This is the reusable methodology layer only.
