<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Claude Research Toolkit

A portable bundle of **generalizable** Claude Code customizations for scientific research, coding, and
modeling — extracted from a working research setup and scrubbed of everything project-specific. Run one
script and every Claude Code session on the new machine inherits the same methodology, skills, agents,
and workflow ergonomics.

It installs into your **global `~/.claude/`**, so it applies to *all* projects — no per-project copying.

---

## Quick start

```bash
cd claude-research-toolkit
./install.sh --all      # full replica: methodology + ergonomics + folded memories + personal defaults
# then RESTART Claude Code (start a new session) — rules/skills/agents/hooks load at startup.
```

Prefer a smaller footprint? Run `./install.sh` with no flags for methodology + ergonomics + memories
(everything universal, no machine-specific personal defaults), or pick tiers explicitly (see below).
Try `./install.sh --all --dry-run` first to see exactly what it will do without writing anything.

Requirements: macOS or Linux, `bash`, and `python3` (used for the safe settings merge; on macOS,
`xcode-select --install` if missing).

---

## Interactive install (`--interactive` / `-i`)

Don't want to remember flag names? Run the picker:

```bash
./install.sh --interactive        # or:  ./install.sh -i
./install.sh -i --dry-run         # preview every composed call, write nothing
```

It's a **numbered-menu prompt loop** — no curses, works over SSH and in any terminal — that runs in
**two passes**:

1. **Global pass** — a numbered list of all agents and skills (with tier and skill-count). Type numbers
   and ranges to toggle (`1,4,7-9`), `all` to install everything, `none`/`done`/`help` as needed, then
   confirm. This becomes your global `~/.claude` install.
2. **Project-root pass** (optional) — add one or more project directories; for each, pick a specialist
   subset. Each root installs into its own `<DIR>/.claude` that *stacks on top of* the global set, and by
   default inherits the global discipline trees (rules/methodology/docs) rather than re-copying them. Ask
   for a self-contained/portable root and it copies them in.

The picker is a **thin front-end**: it only *composes and runs `install.sh` calls* (one per scope pass) —
it adds no copy logic and resolves no coupling. Picking an agent pulls its required skills through the
same engine a hand-typed `--select` uses, so the result is identical to the equivalent CLI call. It always
shows you the exact invocations and asks before running, and it never hangs on a non-tty stdin (pipe a
canned selection for CI). Under the hood it maps your choices onto the selection flags below.

**Selection flags** (what the picker drives — also usable directly):

| Flag | Effect |
|---|---|
| `--select LIST` | comma-list of agents/skills; installs each **plus** its manifest closure (fail-closed on unknown names) |
| `--manifest-subset F` | install exactly the names in file `F` (one per line; `#` comments ok) |
| `--allow-deferred` | permit selecting a DEFERRED-tier skill (`baton`/`folio`) |
| `--root DIR` | install into `DIR/.claude` (a project-local toolkit that stacks on global) instead of `~/.claude` |
| `--discipline-trees auto\|copy\|skip` | rules/methodology/docs copy policy; `auto` (default) skips them for a stacked root that already inherits a global set, `copy` forces a portable root |

---

## What's included

**Always-on rules** (16, recounted 2026-08-03) → `~/.claude/rules/*.md` (auto-loaded every session):
`about-to-author-a-data-rule`, `doc-currency`, `doc-style`, `durable-doc-architecture`, `parallel-runs`,
`project-structure-standard`, `prose-tics-self-scan`, `provenance-over-description`, `r-standards`,
`recon-before-commitment`, `refactor-invariants`, `reproduce-before-fixing`, `root-before-bandaid`,
`standing-mandate`, `verification-principles`, `verify-local-state`.

**Global `~/.claude/CLAUDE.md`** — an always-on working agreement (autonomy / no-check-in / sandbox /
realism-prior) plus generalized debugging lessons (clarify-before-implementing, validate-semantic-correctness,
read-function-internals, systematic-debugging, resolve-contradictions, failure-rate-diagnostics). With
`--memories`/`--all`, a folded block of ~25 durable feedback/preference atoms is appended.

**Skills** (46) → `~/.claude/skills/` (each is also a **slash command** — type `/name`). A representative
selection follows, in four groups; `ls payload/skills` is the authoritative list:
- *Workflow* — `baton` (write a cold-resume handoff doc — `/baton`),
  `machine-md` (author LLM-facing docs — `/machine-md`), `folio` (translate a machine doc to a human twin + render a PDF, add `docx` for a Word file — `/folio`),
  `research-stats-advisor` (choose/defend a statistical method — `/research-stats-advisor`).
- *Agency dial* (one dial, three detents) — `solo` (autonomy max: run a handed-off task to completion, no check-ins — `/solo`),
  `collab` (middle default: surface non-trivial decisions — `/collab`), `plan` (deliberation max: map + get go/no-go first — `/plan`).
- *Domain* (research method) — `aggregation-jensen-bias`, `brms-hierarchical-fitting`, `gap-fill-imputation`, `julia-performance-correctness`,
  `mgcv-temporal-gam`, `preflight-parallel`, `temporal-block-cv`, `temporal-qc-outlier-detection`, `tz-safe-timestamps`.
- *Toolkit-builder* (dev-facing — for extending the toolkit itself) — `bash-hook-contract`, `toolkit-extension-authoring`,
  `capability-audit` (inventory installed agents/skills, flag duplicates + advise retire/relocate — `/capability-audit`).

**Subagents** (18) → `~/.claude/agents/` — a selection; *research-facing:* `code-review-debugger`, `machine-doc-reviewer`,
`version-control-docs`; *toolkit-builder (dev-facing):* `agent-tooling-engineer`, `research-data-manager`.

**Methodology reference docs** → `~/.claude/methodology/` (NOT auto-loaded — the rules point at them on
demand, so they cost no per-session context): `DOC_STYLE_MACHINE_VS_HUMAN`, `HANDOFF_PROTOCOL`,
`AUTONOMY_MANDATE`.

**Usage guides** → `~/.claude/docs/` (installed with `--core`; not auto-loaded): a beginner-oriented
`QUICKSTART`, a comprehensive `USAGE_DETAILED` guide to using Claude Code *with this toolkit*, and an
12-document `advanced/` set (start at `advanced/00_overview`) on the extension architecture and advanced
orchestration — skills, agents, loops, dynamic workflows, context engineering, MCP, and authoring your own.
Each is built as a machine root (`.machine.md`) → human twin (`.md`) → rendered `.pdf` (via the `folio` skill itself).

**Ergonomics** (tier `--ergonomics`): the `xbeep` audible-notification hooks + the `/xbeep` toggle command,
and two workflow hooks — an R-edit review reminder and a completion-claim verification checklist.

**Safety `deny`-list** (part of `--core`): blocks destructive/foot-gun Bash for Claude's Bash tool
(`rm`, `chmod`, `sudo`, `curl`, `wget`, `nc`, `reboot`, …) and reading of secrets (`.env`, `.ssh`, `.aws`,
`credentials.json`).

**Personal defaults** (tier `--personal`, opt-in): `model`, `theme`, `tui: fullscreen`,
`CLAUDE_CODE_EFFORT_LEVEL=max`, `alwaysThinkingEnabled`, and the `feature-dev` plugin.

**Not included** (deliberately): anything tied to a specific research project — domain physics, site/data
facts, project pipelines, per-project rules. This is the reusable methodology layer only.

---

## Tiers

| Flag | Installs |
|---|---|
| *(none)* | `--core --ergonomics --memories` |
| `--core` | rules, skills, agents, methodology docs, global CLAUDE.md, 5 dev hooks, safety deny-list |
| `--ergonomics` | xbeep beep hooks + `/xbeep` + beep registrations |
| `--memories` | append the folded feedback/preference block to CLAUDE.md |
| `--personal` | your personal defaults (model / theme / tui / effort=max / plugin) |
| `--all` | everything |

Options: `--interactive`/`-i` (numbered-menu picker — see above), `--dry-run` (write nothing),
`--no-verify` (skip the dangling-reference gate), `-h`.

---

## How it works (why it's just a file-drop)

Claude Code auto-loads config from `~/.claude/` at three scopes; the **User** scope is your home directory.
Verified against the Claude Code binary, the rule loader scans `~/.claude/rules/` for every session (the same
User scope that loads `~/.claude/CLAUDE.md`, `~/.claude/skills/`, `~/.claude/agents/`, and
`~/.claude/commands/`). So porting is just "put the scrubbed files in the right `~/.claude/` subdir" — no
imports, no per-project wiring.

The installer is **idempotent** and **non-destructive**: before writing anything it backs up your existing
`~/.claude/{CLAUDE.md,settings.json,rules,skills,agents,commands,hooks,methodology}` to
`~/.claude/backups/pre-toolkit-<timestamp>/`, and it **deep-merges** `settings.json` (via `lib/merge_settings.py`)
rather than overwriting it — your existing keys and hooks are preserved, and re-running keeps every hook unique.
The global CLAUDE.md content lives inside a managed marker block, so re-running regenerates just that block and
leaves any of your own CLAUDE.md content intact.

---

## Post-install verification checklist

Files landed and settings valid:
```bash
ls ~/.claude/{CLAUDE.md,rules,skills,agents,methodology}
python3 -m json.tool ~/.claude/settings.json >/dev/null && echo "settings.json OK"
```

The two workflow hooks fire from stdin (proves the env→stdin fix — they work even with the env vars unset):
```bash
printf '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/x.R"}}' | bash ~/.claude/hooks/post-edit-review.sh
printf '{"prompt":"all done"}' | bash ~/.claude/hooks/pre-complete-verification.sh
```

Beeps play (macOS) or degrade to the terminal bell:
```bash
printf '{}' | bash ~/.claude/hooks/xbeep/stop-beep.sh
```

In a **fresh** Claude Code session:
- Ask *"list your available skills"* → you should see `baton`, `machine-md`, and the others; typing `/` shows
  them as slash commands (`/baton`, `/machine-md`).
- Ask *"what does the root-before-bandaid rule say, and which rule files are in your context?"* → it answers
  from the loaded rule and lists the 16.
- The 18 agents are available in the subagent picker.
- Submit any prompt → beep on submit + beep on stop; `/xbeep off` silences, `/xbeep on` restores.

---

## Two things worth knowing

**The `deny`-list is assertive.** It globally blocks `curl`/`wget`/`chmod`/`rm`/… for Claude's Bash tool.
That's a deliberate safety default; if a project needs one of these, allow it per-project in that project's
`.claude/settings.local.json`. (Your own shell is unaffected — this only constrains Claude's Bash tool.)

**The `--personal` tier assumes your accounts/plugins.** `model` and the `feature-dev` plugin resolve
on a fresh machine once you've signed in / installed them; `theme` and `tui` are cosmetic. If a personal key
misbehaves, edit `~/.claude/settings.json` (or re-run without `--personal`).

**Beeps are macOS-first.** The scripts try `afplay` → `paplay` → `aplay` → terminal bell, so on Linux they
fall back to the bell — install `pulseaudio-utils` (`paplay`) or `alsa-utils` (`aplay`) for full sound; you can also
point them at a sound with `export XBEEP_SOUND=/path/to.wav`.

**Restart required.** Rules, skills, agents, and hooks are read at startup — start a new session after installing.

---

## Uninstall

```bash
./uninstall.sh    # restores the most recent ~/.claude/backups/pre-toolkit-* backup
```

Items that didn't exist before you installed (e.g. a freshly created `CLAUDE.md`) aren't in the backup, so the
script leaves them and tells you which to remove by hand for a fully clean removal.

---

## Layout

```
CCRT/
├── install.sh    uninstall.sh    README.md    INSTALL.md    VERSION    MANIFEST.tsv
├── lib/
│   ├── merge_settings.py    # safe JSON deep-merge (no clobber)
│   └── scrub_verify.sh      # fail-closed gate: no dangling project reference may survive
└── payload/                 # mirrors ~/.claude/ exactly
    ├── CLAUDE.core.md   CLAUDE.memories.md
    ├── settings/{core,ergonomics,personal}.fragment.json
    ├── rules/  skills/  agents/  commands/  hooks/{,xbeep/}  methodology/
```
