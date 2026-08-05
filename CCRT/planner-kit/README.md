<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# planner-kit

The planner-kit packages a portable way of running a multi-agent job from one project root, so that
a working method travels to the next project instead of being rebuilt by hand each time. It installs
generic standing rules that teach a fresh agent how to operate in that root: a planner that only
decomposes, routes, synthesizes, and decides; isolated worker subagents that do the domain work; code
as a co-equal participant; and durable files as the only channel between them. Around that loop sit
the disciplines that keep it honest — reuse and persist any code you write, run a two-stage quality
check, preserve plans, verify from receipts rather than assertions, retire a superseded file by
tombstoning it in place rather than quietly moving it, and surface a new-capability candidate when
one keeps proving necessary. The kit anchors itself to whatever root you install it into, writes
generic rules and empty structure only, and never touches your data.

The kit ships inside the Claude Code toolkit, at `CCRT/planner-kit/`, and the two installers are
deliberately separate because they do different jobs: install the CCRT once into `~/.claude` for the
global capability — agents, skills, rules, hooks — then run this kit's own `install.sh` separately in
each project root that adopts the supervisory workflow, where it writes the project-level `CLAUDE.md`
contract, the advisory hooks, and the model-routing set. They are designed to be used together.

By default the install is two files at the project root plus a small `.claude/` set. The root gets a
`CLAUDE.md` carrying the rules and a
`STRUCTURE_RULES.machine.md` carrying the folder contract — what each standard folder is for, what
triggers its creation, and which rule governs it. The folder tree itself is not pre-created. The
agent materializes each folder the moment a task first needs it, so a folder's absence means "not
needed yet" rather than "something is broken", and a project never accumulates empty directories it
will not use.

Alongside those, `.claude/` receives two advisory hooks and the `settings.json` entries that register
them. One checks, at the moment a subagent is launched, that the brief it references exists and has
every slot filled; the other asks once, when a turn that collected subagent results ends without
naming an outcome, which of the six outcomes applies. Both only add a note; neither refuses an
action, and both fail open rather than interrupt a session on their own error. Setting
`PLANNER_KIT_HOOKS=off` silences them. Where a `settings.json` already exists the installer deep-merges into it, keeping your
keys and any hook you already had, and saves a dated copy of the original first.

Since v1.4 the same `.claude/` set also receives the model-routing capability: two executor agents,
`fable-executor` and `opus5-executor`, which are the constructed routes for model-sensitive subagent
work, and the `model-verification` skill, which audits which model actually served each child turn.
Each agent body carries its full contract; the rules file the kit installs tells a fresh session when
to reach for them.

## Install

Run it from your project root, never from inside the kit — the installer refuses to act on itself.

```bash
cd /path/to/your/project
bash /path/to/CCRT/planner-kit/install.sh                  # minimal: front-door files + hooks + routing set
bash /path/to/CCRT/planner-kit/install.sh --full           # classic: pre-scaffold the whole tree and seeds
bash /path/to/CCRT/planner-kit/install.sh --upgrade-rules  # upgrade: replace an installed rules block in place
bash /path/to/CCRT/planner-kit/install.sh --dry-run        # preview only; composes with the others
```

The installer performs zero deletes and zero overwrites. If your root already has a `CLAUDE.md`, the
rules are appended inside a marker block and everything outside that block is left byte-for-byte
unchanged; if the marker is already present, the run is a no-op. To upgrade an already-installed
project, re-run with `--upgrade-rules`: it saves a dated backup of your `CLAUDE.md`, then replaces
the marker block with the current rules while touching nothing outside it, and it refuses when no
block exists. `--full` additionally creates the standard working directories and seeds the ledger,
memory, and tool templates, but only where they are absent. It runs on bash 3.2 and later.

## Where to read next

- [`docs/human_md/KIT_RATIONALE.md`](docs/human_md/KIT_RATIONALE.md) — the design reasoning, one
  decision at a time, each paired with the friction it resolves.
- [`docs/human_md/KIT_ADOPTION.md`](docs/human_md/KIT_ADOPTION.md) — a walkthrough of installing the
  kit into a real project and putting it to work.
- [`docs/machine_md/`](docs/machine_md/) also holds the standalone system logic, written for an
  implementing agent with no prior context, and the operating-logic skill that pairs each mechanism
  with the failure it prevents.
- [`../../Documentation/PDF/WORKFLOW_GUIDE.pdf`](../../Documentation/PDF/WORKFLOW_GUIDE.pdf) explains the loop itself and how you steer it.

This README is the human face of the kit. [`README.machine.md`](README.machine.md) is the
machine-facing contract beside it — the precise installer behavior, marker and merge semantics,
version-mismatch migration, and a file-by-file account of the payload. It complements this document
rather than being replaced by it; where the two differ in detail, the machine file is the exact one.

## Honest efficacy

These principles were derived and measured in one origin project, and the numbers cited in `docs/`
are that project's. The principles are portable, but their effect in your project is unmeasured
until you measure it, so treat every rule as untested here until a run in your own project produces a
before-and-after number. That discipline is one of the kit's own rules.
