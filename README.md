<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# CC-CS Research Toolkits

**One research methodology, carried on two agent platforms.**

This repository holds a single body of research practice, together with the two toolkits that carry
it. The practice covers decomposing and routing a piece of work, checking a claim against the record
instead of asserting it, and writing so a reader can follow. The **Claude Code Research Toolkit (CCRT)**
expresses that practice in Claude Code's own primitives: files under `~/.claude/`, always-on rules,
hooks that fire on real events, and subagents. The **Claude Science Research Toolkit Bundle
(CSRTB)** expresses the same practice in Claude Science's primitives: skills, agent profiles, and
kernel gates installed into an account from a repl cell. The methodology is authored once, so it
cannot fork; each mechanism stays native to the platform it runs on. That means the two sides do
*not* match line for line, and most of the differences are design rather than gaps.
[`TWIN_ARCHITECTURE`](Documentation/human_md/TWIN_ARCHITECTURE.md) explains how to read any
difference correctly, and is the place to start if you plan to change either side.

Beside the twin sit a portable per-project operating kit and a set of human-facing guides.

## What is here

| Path | What it is |
|---|---|
| [`CCRT/`](CCRT/) | The Claude Code toolkit: skills, agents, rules, hooks, and an idempotent installer that writes into `~/.claude/`. The planner-kit ships inside it. |
| [`CSRTB/`](CSRTB/) | The Claude Science bundle: skills, agent profiles, and fail-closed kernel gates, installed into a Science account from a repl cell. |
| [`Documentation/`](Documentation/) | The cross-toolkit guides: what each side carries, why the twin is built this way, and how to port an improvement across it. |
| [`CCRT/planner-kit/`](CCRT/planner-kit/) | A portable kit that teaches any project root how to run a supervised multi-agent job. Its own installer runs per project, separately from the CCRT's global one. |
| [`Documentation/PDF/WORKFLOW_GUIDE.pdf`](Documentation/PDF/WORKFLOW_GUIDE.pdf) | The workflow itself: the planner-and-subagents loop, and how you steer it. |

## Quick start

**Claude Code.** From this repository:

```bash
cd CCRT
bash install.sh --all        # add --dry-run first to preview every action, writing nothing
```

Then start a new Claude Code session: rules, skills, agents, and hooks are read at startup. `--all`
is the full replica and includes the personal tier — model, theme, effort level, and the planner
default persona. With no tier flag the installer writes the universal set instead (core, ergonomics,
and the folded memories) and leaves machine-specific defaults alone. The tier table, the selection
flags, and the interactive picker are in [`CCRT/README.md`](CCRT/README.md).

**Claude Science.** Upload `crt_science_bundle.json` and `install_crt_science.py` into your Science
project, then run one repl cell:

```python
exec(open("install_crt_science.py").read()); install_crt_science()
```

That is the non-destructive default. The paste-ready block with its acceptance probes is
[`CS_INSTALL_STARTER_v2.11.md`](CSRTB/CS_INSTALL_STARTER_v2.11.md),
and [`CSRTB/README.md`](CSRTB/README.md) orients you first.

## What is inside, by the numbers

Counted from the trees in this repository, not copied from prose:

- **CCRT** — **46 skills** and **18 agents**, plus 16 always-on rules and 4 slash commands.
  (`ls payload/skills` returns 46 directories, each holding a `SKILL.md`; `payload/agents` holds 18
  `.md` files.)
- **CSRTB** — **52 skills** and **18 profiles**, of which **19 skills carry a `kernel.py` sidecar**
  of fail-closed gate functions. (All three read from the built `crt_science_bundle.json`, whose
  `counts` field reports 52 and 18; the same totals come back from counting `bundle_src/skills` and
  `bundle_src/profiles`, and 19 entries carry `has_sidecar`.)

The totals differ by design, and a matched pair would tell you nothing: every delta traces to a
platform-only item, a role carried in a different form on each side, or a mechanism that only one
platform can host. Counts also drift as the toolkits grow, so recount from the trees before citing a
number rather than trusting one written into prose.

## Documentation

Every human-facing guide is maintained as a triple — a machine-readable root that is authoritative, a
human translation derived from it, and a rendered PDF.

- [`Documentation/`](Documentation/) holds the three cross-toolkit guides: the **roster comparison**
  (what each side carries, item by item), the **twin architecture** (why the two diverge and how to
  read a difference), and the **cross-porting guide** (how to move an improvement from one side to
  the other without breaking it).
- Each toolkit also ships its own set. Claude Code's lives at
  [`CCRT/payload/docs/`](CCRT/payload/docs/)
  — a quickstart, a full usage guide, and a 12-document `advanced/` set on the extension
  architecture. Claude Science's lives at
  [`CSRTB/docs/`](CSRTB/docs/)
  — front door, quickstart, full reference, and architecture.
- The planner kit ships inside the Code toolkit at [`CCRT/planner-kit/`](CCRT/planner-kit/). Install
  the CCRT once into `~/.claude` for the global capability, then run the kit's own `install.sh`
  separately in each project root that adopts the supervisory workflow; the two installers are
  deliberately separate — global capability on one side, per-project workflow on the other — and are
  designed to be used together. The kit's reasoning and its step-by-step adoption walkthrough are in
  [`CCRT/planner-kit/docs/`](CCRT/planner-kit/docs/).

If you are new here, read [`WORKFLOW_GUIDE.pdf`](Documentation/PDF/WORKFLOW_GUIDE.pdf) for the working loop, then
[`TWIN_ARCHITECTURE`](Documentation/human_md/TWIN_ARCHITECTURE.md) for the architecture, then the
quickstart for whichever platform you use.

## License

MIT — see [`LICENSE`](LICENSE). Every source and documentation file carries the same grant in its own
comment syntax (`SPDX-License-Identifier: MIT`); data and binary files are covered by the root
`LICENSE` alone.
