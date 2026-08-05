<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# CCRT — the Claude Code Research Toolkit

A portable set of generalizable Claude Code customizations for scientific research, coding, and
modeling, extracted from a working research setup and scrubbed of everything project-specific. Run
one script and every Claude Code session on that machine inherits the same methodology, skills,
agents, and workflow ergonomics. It installs into your global `~/.claude/`, so it applies to all
projects with no per-project copying.

The toolkit lives in this directory, and [`INSTALL.md`](INSTALL.md) is the detailed reference: the
full flag list, the interactive picker, what each tier writes, the verification checklist, and how to
uninstall. The release version is carried in [`VERSION`](VERSION); the directory name no longer
carries it.

## Install

```bash
cd CCRT
bash install.sh --all        # add --dry-run first to preview every action, writing nothing
```

Start a new Claude Code session afterwards — rules, skills, agents, and hooks are read at startup.

The installer is idempotent and non-destructive: it backs up your existing `~/.claude/` files before
writing, deep-merges `settings.json` rather than overwriting it, and keeps its own content inside a
managed marker block so anything you wrote yourself survives a re-run.

**Tiers in one line.** With no tier flag you get `--core --ergonomics --memories`, which is
everything universal. `--core` is the rules, skills, agents, methodology docs, global `CLAUDE.md`,
dev hooks, and the safety deny-list; `--ergonomics` adds the audible-notification hooks;
`--memories` appends the folded feedback and preference block; `--personal` adds machine-specific
defaults (model, theme, effort level, and the planner default persona); and `--all` is every tier,
the full replica. `--select` and `--manifest-subset` narrow the install to chosen agents and skills
plus whatever skills those require.

## Planner-first by design

The toolkit's default primary persona is the **planner**, and that choice shapes the rest. The
planner does not perform the domain work. It recognizes what kind of request it has, decomposes the
task, routes each part to the specialist agent and skill that fit it, and picks a model by
difficulty tier. Then it runs a supervisory loop: launch a wave, read what comes back, and decide
whether to continue, re-route, revise the plan, or stop. Specialists stay specialists, and the coordination
lives in one place instead of being re-improvised per task. The persona is a settings default that
`--personal` (and therefore `--all`) sets; it is removable, and any session can select a different
agent.

## Where the docs live

Each guide is a triple: an authoritative machine root, its derived human translation, and a PDF.

- [`payload/docs/`](payload/docs/) holds the reading set, installed to `~/.claude/docs/`:
  `QUICKSTART` for a first session, `USAGE_DETAILED` for the full reference, and a 12-document
  [`advanced/`](payload/docs/advanced/) set on the extension architecture and orchestration — start
  at `advanced/00_overview`.
- The three faces of each guide sit side by side in `payload/docs/` rather than in the
  `machine_md/`, `human_md/`, and `PDF/` subdirectories the rest of this repository uses. That
  layout is what `install.sh` copies into `~/.claude/docs/`, so it is fixed by the installer, not by
  documentation convention.
- [`DOCS_POINTER.md`](DOCS_POINTER.md) is the one-line signpost to the same set.
- For how this toolkit relates to its Claude Science twin, see
  [`../Documentation/`](../Documentation/).

Counted from `payload/` in this repository: **46 skills** (one directory each, every one holding a
`SKILL.md`), **18 agents**, 16 always-on rules, and 4 slash commands.
