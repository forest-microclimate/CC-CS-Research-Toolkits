# 01_extension_architecture.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: THE EXTENSION ARCHITECTURE — the scope MAP (what loads WHERE) + context/memory (CLAUDE.md) + settings/precedence + hooks. The static surface you customize.
# FOR: a user configuring WHAT loads + WHERE (scope), how settings resolve (merge vs override), and how hooks fire. Part of the ADVANCED set — map + REFERENCES in 00_overview.machine.md.
# STYLE: machine-terse, front-loaded, POSITIVE action-first; per-unit shape FOR -> HANDLE -> mechanics -> INVARIANT -> FEEDS.

## 01.1 · MAP — THE EXTENSION ARCHITECTURE
- FOR: everything that customizes Claude Code — instructions, skills, agents, commands, hooks, settings — installs as FILES under a `.claude/` dir; three SCOPES decide WHO gets them.
- HANDLE: LAYERS on a global baseline — User = your defaults everywhere · Project = this repo's additions · Managed = org policy on top.
- SCOPES (three):
  - User (`~/.claude/`) ⇒ applies to EVERY session you run.
  - Project (`<repo>/.claude/`) ⇒ applies only when you launch inside that repo.
  - Managed (enterprise/admin policy) ⇒ applies org-wide, set by an administrator.
- EACH scope holds the SAME kinds of thing: `CLAUDE.md` (instructions), `rules/*.md`, `skills/<name>/SKILL.md`, `agents/*.md`, `commands/*.md`, and `settings.json` (which is where `hooks` register).
- STACK, not replace: a Project scope ADDS to the User baseline (both load); Managed sits above both. Specific scopes STACK onto the global baseline rather than overwriting it. (Settings-key PRECEDENCE conflicts resolve per §01.3.)
- INVARIANT: scope == install LOCATION, and location alone decides reach — the SAME `x.md` under `~/.claude/skills/` is global, under `<repo>/.claude/skills/` is repo-only. Move the file ⇒ change its reach.
- FEEDS: every later section is one cell of this grid — skills/commands (02_skills_and_commands), agents (03_agents), and CLAUDE.md + memory (§01.2), settings + precedence (§01.3), hooks (§01.4) all resolve through these three scopes.
<!--FIG: the three scopes (User/Project/Managed) and what loads from each | 80% -->

## 01.2 · CONTEXT, MEMORY & CLAUDE.md
- FOR: what Claude KNOWS at the start of a turn — two channels: auto-memory (CLAUDE writes) + CLAUDE.md (YOU write).
- HANDLE: memory = a notebook Claude keeps for itself across sessions; CLAUDE.md = the standing orders YOU pin.
- AUTO-MEMORY: `~/.claude/projects/<git-root-slug>/memory/` — keyed by the git REPO ROOT, machine-local, CLAUDE writes learnings there. Only the FIRST ~200 lines / 25 KB of `MEMORY.md` load at start ⇒ keep the top dense.
- CLAUDE.md: YOU write instructions; loads in FULL (no truncation) ⇒ the place for durable directives.
- HIERARCHY CONCATENATES broad→specific: managed → `~/.claude/CLAUDE.md` → `./CLAUDE.md` or `./.claude/CLAUDE.md` → `./CLAUDE.local.md`. Every present level combines.
- `@import <path>` pulls another file's content in (nesting depth up to 4).
- `.claude/rules/*.md` load like CLAUDE.md (always-on); a `paths:` frontmatter SCOPES a rule to file globs ⇒ it loads only when a matching file is in play.
- MANAGED BLOCK: this toolkit assembles its global CLAUDE.md INSIDE markers — `<!-- >>> claude-research-toolkit (managed) >>> -->` … `<!-- <<< claude-research-toolkit (managed) <<< -->` ⇒ a re-install regenerates ONLY that block; YOUR content OUTSIDE the markers survives.
- TRANSCRIPTS: `~/.claude/projects/<slug>/<sessionId>.jsonl` = the full turn history ⇒ `claude --resume` / `--continue` / `--fork-session` re-open it; the `.jsonl` is portable across machines.
- INVARIANT: memory is TRUNCATED at load (~200 lines / 25 KB), CLAUDE.md is NOT ⇒ put anything that MUST always be seen in CLAUDE.md / a rule, not deep inside a memory file.
- FEEDS: the always-on rules ride this loader; the managed block is why the toolkit re-installs without clobbering you (§01.3); transcripts underpin resume (§10.2).

## 01.3 · SETTINGS, SCOPES & THE DIRECTORY HIERARCHY
- FOR: configuring the harness — model, permissions, env, hooks, output style — per scope.
- HANDLE: a precedence LADDER — the closer/more-privileged the layer, the higher it wins; BUT two keys (hooks, permissions) COMBINE instead of fighting.
- PRECEDENCE high→low: Managed > CLI args > `<repo>/.claude/settings.local.json` (personal, gitignored) > `<repo>/.claude/settings.json` (shared, committed) > `~/.claude/settings.json` (global).
- IMPORTANT — MERGE, not replace, for two keys: `hooks` AND `permissions` MERGE across ALL scopes (every layer's entries combine); they do NOT override each other. (Scalar keys like `model` take the single highest-precedence value.)
- MAIN KEYS: `model`, `permissions` (allow/ask/deny), `env`, `hooks`, `outputStyle`, `autoMemoryEnabled`, `statusLine`, …
- DIFFERENT RULES PER PROJECT: shared committed guidance in each `<repo>/.claude/` (CLAUDE.md, rules, `settings.json`) · personal per-repo bits in `<repo>/.claude/settings.local.json` + `CLAUDE.local.md` (gitignored) · cross-project defaults in `~/.claude/`.
- THIS TOOLKIT deep-merges `~/.claude/settings.json` from 4 FRAGMENTS = the install tiers: core (permissions.deny + 4 dev-hook registrations across PostToolUse/UserPromptSubmit/Stop) + ambient-time (ambient_time.py on UserPromptSubmit+SessionStart) + ergonomics (xbeep hooks) + personal (model/theme/tui/effort/plugin) ⇒ a re-install adds keys without clobbering existing ones.
- INVARIANT: for `hooks` + `permissions`, MORE layers = MORE entries (union) ⇒ a deny in ANY scope still bites and a hook in ANY scope still fires; you cannot un-set them from a lower layer, only ADD.
- FEEDS: the merged `permissions.deny` is the safety boundary; the merged `hooks` are §01.4; the deep-merge is why the toolkit's tiers compose (§10.1).
<!--FIG: settings precedence ladder + which layers merge vs override | 70% -->

## 01.4 · HOOKS, DEEPLY
- FOR: deterministic automation the HARNESS runs on events — NOT Claude choosing to.
- HANDLE: event listeners for your session — a script fires on "edit happened" / "prompt submitted" / "Claude stopped", every time, mechanically.
- MECHANISM: hooks = scripts the harness executes on EVENTS (deterministic; Claude does not decide whether they run).
- CONFIGURED in `settings.json`: `hooks → <Event> → [{ matcher, hooks: [{ type: "command", command }] }]`.
- ~30 EVENTS: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `SessionStart`, `PreCompact`, `Notification`, …
- I/O CONTRACT: context arrives as JSON on STDIN. exit 0 = OK (stdout MAY carry JSON to control the harness); exit 2 = BLOCK the action + stderr is fed BACK to Claude.
- AUTHOR YOUR OWN: add a script + register it in `settings.json` under the event. LIVE examples in this toolkit: `post-edit-review.sh` (PostToolUse on `Edit|Write` ⇒ R-edit review nudge), `pre-complete-verification.sh` (UserPromptSubmit ⇒ verify-before-"done" checklist), `xbeep` (Notification / Stop / UserPromptSubmit beeps).
- READ STDIN, not env: current Claude Code passes hook data as JSON on STDIN (the old `CLAUDE_*` env vars are no longer set) ⇒ parse e.g. `tool_input.file_path` from stdin.
- INVARIANT: hooks run on the EVENT, not on Claude's judgment ⇒ they are the right tool for "ALWAYS do X when Y happens" — a memory/preference can't guarantee it; a hook can.
- FEEDS: registered via the settings `hooks` key (§01.3, which MERGES across scopes ⇒ a hook in any scope fires); the toolkit ships them in the core + ergonomics tiers (§10.1).

## SOURCES
Architecture facts; the consolidated reference list (official docs + blogs) lives in 00_overview.machine.md (§ REFERENCES).
