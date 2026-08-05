<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# CSRTB — the Claude Science Research Toolkit Bundle

A portable set of generalizable Claude Science customizations for scientific research, coding, and
modeling — skills, agent profiles, and kernel gates — captured from a working research setup and
scrubbed of everything project-specific. Run one installer in a Claude Science repl cell and the
account inherits the same methodology and specialist roster. This is the Claude Science twin of the
Claude Code toolkit in [`../CCRT/`](../CCRT/), sharing most of its content in other primitives.

The bundle lives in this directory, and its version is carried in [`VERSION`](VERSION), with the
`bundle_version` field of `crt_science_bundle.json` staying authoritative. The front door is
[`docs/human_md/CS_README.md`](docs/human_md/CS_README.md), which points at the rest of the doc set:
`CS_README`, `CS_QUICKSTART`, `CS_USAGE_DETAILED`, and `CS_ADVANCED`, each carried as a machine root
under [`docs/machine_md/`](docs/machine_md/) and a human translation under
[`docs/human_md/`](docs/human_md/).

## Install

Upload `crt_science_bundle.json` and `install_crt_science.py` into your Science project, then run
one repl cell:

```python
exec(open("install_crt_science.py").read()); install_crt_science()
```

`host` is pre-injected in the repl kernel. That call is the non-destructive default: it creates an
item that is absent, treats a byte-identical item as a no-op, and skips and reports an item that
exists but differs. Pass `overwrite=True` to update a differing item deliberately. The paste-ready
block, including the acceptance probes that confirm the kernel gates fire and the sidecars publish,
is
[`CS_INSTALL_STARTER_v2.11.md`](CS_INSTALL_STARTER_v2.11.md).

There is no uninstall script, because the bundle installs into the account rather than into a file
tree. Re-running the installer is safe, and the live account can be re-checked against the bundle at
any time.

## What you get

Counted from the built `crt_science_bundle.json` in this repository, whose `counts` field reports
the first two, with the same totals returned by counting the `bundle_src/skills` and
`bundle_src/profiles` directories:

- **52 skills**, loaded through `host.skills`, spanning workflow and agency, domain method, and
  toolkit-builder groups.
- **18 agent profiles**, dispatched through `host.delegate`: a generalist daily driver plus 17 named
  specialists — planner, software developer, statistics advisor, the domain modelers, and the rest.
- **19 of those skills carry a `kernel.py` sidecar** (counted as the entries flagged `has_sidecar`).
  Four of them are the fail-closed gates: model routing and plan lint, confirm-before-stop,
  verify-before-assert, and require-receipt.

The complete roster, one line per item, lives in `CS_USAGE_DETAILED`, which owns it so it is not
duplicated elsewhere.

## Platform notes

Claude Science reaches you through a browser rather than a local shell, and that single fact shapes
the bundle. There is no hook surface here and no always-on rules layer, so a discipline that rides a
hook on Claude Code rides a prose gate in a profile, or a small kernel function, on this side. State
lives in an artifact store and per-specialist memory rather than in files on a disk, and work goes to
isolated workers through an asynchronous interface rather than a shared working tree. The practical
consequence: never paste a mechanism across from the Claude Code side, because a call that cannot
execute where it lands fails quietly. [`../Documentation/`](../Documentation/) covers the tier model
and the porting workflow that keep the twin honest.
