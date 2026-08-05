---
name: toolkit-extension-authoring
description: Invoke WHEN adding or modifying a Claude Code customization in the claude-research-toolkit - a hook, agent, skill, slash command, install.sh tier, or settings fragment - so the change installs idempotently and non-destructively. Holds the 3-step hook recipe, the FRAGS/merge_settings deep-merge contract, copy_tree additive semantics, the scrub-verify fail-closed gate, and MANIFEST discipline. Pair with bash-hook-contract for the hook script itself.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-12). Auto-stamped by doc-status.sh; refine the note on next edit.
# toolkit-extension-authoring - add a toolkit extension so it installs correctly

## When to invoke
WHEN about to add or change a customization in `claude-research-toolkit/payload/` (hook / agent / skill / command / settings fragment / install tier) => follow the matching recipe below. The toolkit installs into the global `~/.claude/`; the invariant is that `install.sh` stays IDEMPOTENT (re-run changes nothing it already did) and NON-DESTRUCTIVE (backs up + deep-merges, never clobbers). A new extension that breaks that invariant is a regression even if it "works" once.

## The install model (the frame every recipe rests on)
- `payload/` MIRRORS `~/.claude/` exactly. Directory extensions (`rules/ skills/ agents/ methodology/ docs/ commands/ hooks/`) install by `copy_tree` - ADDITIVE, never `--delete`; a file lands at the same relative path under `~/.claude/`.
- `settings.json` changes install by FRAGMENT: a `payload/settings/<name>.fragment.json` deep-merged into the user's live `settings.json` via `lib/merge_settings.py`.
- Every run first backs up `~/.claude/{CLAUDE.md,settings.json,rules,skills,agents,commands,hooks,methodology}` to `~/.claude/backups/pre-toolkit-<ts>/`, THEN writes.
- Tiers gate what installs: `--core` (rules, skills, agents, methodology, CLAUDE.md, 5 dev hooks, permissions.deny) | `--ergonomics` (xbeep) | `--memories` (folded CLAUDE.md block) | `--personal` (model/theme/tui/effort/plugin) | `--all`. No flag => `--core --ergonomics --memories`.

## Recipe A - add a HOOK (3 steps; miss one and it silently no-ops)
1. DROP the script at `payload/hooks/<name>.sh` (or `.py`). Author it to the `bash-hook-contract` skill (stdin-JSON in, exit-code contract, portable timeout, CRT gate). Keep the executable bit: `chmod 755` (an `edit_file` rewrite DROPS +x - restore it).
2. AUTHOR `payload/settings/<name>.fragment.json` registering it under the right hook EVENT with a `matcher` and `command` using a `$HOME`-relative path (never a machine-absolute home path - it must resolve on any machine):
```json
{ "hooks": { "PostToolUse": [ { "matcher": "Edit|Write",
  "hooks": [ { "type": "command", "command": "bash \"$HOME/.claude/hooks/<name>.sh\"", "timeout": 5 } ] } ] } }
```
3. WIRE it into `install.sh`: `FRAGS+=("$PAYLOAD/settings/<name>.fragment.json")` inside the tier that should ship it (core hooks go in the `--core` block, next to `core.fragment.json` / `ambient-time.fragment.json`). `install.sh` passes all `FRAGS` to `merge_settings.py` in one call.
- The `copy_tree hooks hooks` in `--core` already carries the script file; step 3 only registers it. VERIFY after: `printf '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/x.R"}}' | bash payload/hooks/<name>.sh` fires from stdin.

## merge_settings.py contract (why re-running never duplicates)
`merge_settings.py TARGET FRAG...` deep-merges each fragment in place, atomically (`os.replace`):
- Objects merge recursively.
- HOOK-EVENT arrays (items shaped `{matcher, hooks:[...]}`) merge BY `matcher`, and hooks within a matcher dedup BY `command` => re-running the installer never duplicates a hook; two fragments both adding a `UserPromptSubmit` hook collapse into ONE matcher group.
- Other string arrays (`permissions.deny`/`allow`/`ask`) UNION, order-preserving.
- Scalar / type-clash => the FRAGMENT wins.
- CONSEQUENCE: to make a hook idempotent, keep its `command` string byte-identical across fragments; a whitespace change makes it read as a second, distinct hook.

## Recipe B - add an AGENT (subagent)
DROP `payload/agents/<name>.md` with YAML frontmatter: `name`, `description` (LOAD-BEARING - it is matched for auto-invocation; make it a specific, positive, trigger-phrased sentence naming when to invoke, per `machine-md`), optional `model`, `color`, `tools`, `memory`. `copy_tree agents agents` in `--core` installs it; no fragment needed. VERIFY: it appears in the subagent picker in a fresh session.

## Recipe C - add a SKILL (= a slash command too)
DROP `payload/skills/<name>/SKILL.md` with `name` + `description` frontmatter (author to `machine-md`). Each skill is ALSO a `/name` slash command automatically. Ship reusable helpers as scripts the SKILL.md points at (CC side). `copy_tree skills skills` in `--core` installs it. VERIFY in a fresh session: "list your skills" shows it; `/name` is available.

## Recipe D - add or change an INSTALL TIER
Tiers are simple flags (`CORE=1` ...) each guarding a block that runs `copy_tree` calls + appends `FRAGS`. To add a tier: parse its flag in the `case` (`--all` sets every tier), add its guarded block, and DOCUMENT it in the `usage()` heredoc + README table + MANIFEST. Keep tiers ORTHOGONAL - one job each; `--all` = union.

## Ship discipline (do NOT skip - the fail-closed gate has teeth)
- MANIFEST.tsv: add a row for every new payload file: `target | source | scrub | notes`. It is the human-auditable map of what lands where and what was scrubbed.
- SCRUB gate: `install.sh` runs `lib/scrub_verify.sh "$PAYLOAD"` and ABORTS (`exit 1`) if any dangling / project-specific reference survives. WHEN authoring payload content => keep it GENERALIZABLE - no project physics, site/data facts, absolute personal paths, or dead cross-refs. A dangling reference fails the build; it does not ship. Run `bash lib/scrub_verify.sh payload` before considering a change done.
- Idempotency check: run `./install.sh --all --dry-run` then a real run twice; the second run must add nothing new (no duplicate hooks, no duplicate deny entries).
