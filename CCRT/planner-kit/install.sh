#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# planner-kit installer (v1.8) — LAZY-SCAFFOLD: minimal by default, --full for the classic tree.
# Idempotent & CONTENT-CURRENT: a re-run changes nothing it already did, and ZERO deletes ever — but a
# re-run at a NEWER kit now REFRESHES the kit's OWN artifacts (v1.8, below) instead of leaving the
# adopter stranded on old content. USER-OWNED surfaces keep the never-overwrite contract unchanged.
#
# CONTENT REFRESH (v1.8) — WHY IT EXISTS: the install was file-EXISTENCE gated and therefore version-
#   BLIND. A v1.6 adopter re-running at v1.8 received the new FILENAMES while every pre-existing file
#   kept its v1.6 bytes, and .claude/settings.json went on registering them — so the project READ as
#   upgraded and BEHAVED as the old version (a collect gate with no verdict check; a brief_gate with no
#   ROLE slot). Stranded content is worse than a missing file: a missing file is visible, stale bytes
#   are not. So the artifacts the KIT OWNS — the five hooks, the dev/tools diagnostics, the
#   model-verification skill files, and EVERY agent the kit places (a GLOB over payload/.claude/agents,
#   so an agent added to the payload later is covered without editing this file) — are
#   REFRESH-IF-DIFFERENT: byte-compared against the payload source, and where they DIFFER the project's
#   copy is kept in a DATED BACKUP DIR FIRST (one dir per run, printed) and only then replaced. No
#   backup, no replace. IDENTICAL => skipped exactly as before, so a same-version re-run is still a
#   no-op that creates no backup dir at all.
#   NEVER REFRESHED — seed-if-absent, unchanged: the root CLAUDE.md outside the marker span, the
#   .claude/CLAUDE.md pointer stub, dev/briefs content, the ledger / plan / planner-memory templates,
#   STRUCTURE_RULES.md (opt in via --upgrade-rules), and anything the kit does not ship — the refresh
#   iterates PAYLOAD sources, so a file the kit never shipped is never visited, let alone written.
#
# v1.5 RENAME + MIGRATION: the installed folder contract is now STRUCTURE_RULES.md (was
#   STRUCTURE_RULES.machine.md through v1.4). Its content is unchanged and still machine-STYLE;
#   only the NAME moved. EVERY mode (default, --full, --upgrade-rules) first MIGRATES an already-
#   installed old-name file by RENAMING it in place (plain `mv`; content preserved byte-for-byte,
#   the project's own copy always wins over the payload seed), then proceeds. A root carrying BOTH
#   names is REFUSED up front, before any write — the installer cannot know which one is
#   authoritative, so it never picks, never overwrites, and changes nothing at all. A second run
#   after a migration is a no-op on this axis.
#
# Run FROM your PROJECT ROOT (not from inside the kit):
#     cd /your/project && bash /path/to/planner-kit/install.sh [--full] [--dry-run]
#
# TWO MODES:
#   DEFAULT (minimal) — install ONLY the two front-door files at the project root:
#       (1) root CLAUDE.md  and  (2) STRUCTURE_RULES.md — plus the five
#       workflow hooks + their .claude/settings.json registration, the model-routing set
#       (EVERY agent in payload/.claude/agents — fable-executor, opus5-executor, fable-subplanner —
#       plus the model-verification skill), and the dev/tools DIAGNOSTICS
#       (the enforcement e2e battery + the adherence scorecard; see BOTH MODES below).
#     The folder tree is NOT pre-created; the agent materializes each folder ON DEMAND per
#     STRUCTURE_RULES.md (a folder's absence = not yet needed, never an error). This
#     removes the speculative clutter of pre-creating folders a given project never uses.
#   --full — the classic layout up front: scaffold the whole standard tree (mkdir -p; idempotent)
#     + a .gitkeep in each created dir that stays empty + seed the ledger/memory/tool templates
#     (only-if-absent), PLUS STRUCTURE_RULES.md. Same outcome as v1.1 + the structure doc.
#
# BOTH MODES do (mechanism unchanged from v1.1):
#   (c) ROOT CLAUDE.md: create if absent (payload rules wrapped in planner-kit markers), else append
#       the rules block behind a marker if not already present, else no-op ("already installed"). Also
#       seed .claude/CLAUDE.md as a <=2-line pointer stub to the root file, only if absent. If a
#       planner-kit marker is found INSIDE .claude/CLAUDE.md (a v1 install put the rules there) print
#       migration advice — never auto-move user content.
#   MIGRATE a pre-v1.5 STRUCTURE_RULES.machine.md at the project root to STRUCTURE_RULES.md
#       (plain `mv`, content preserved) — then seed STRUCTURE_RULES.md (only-if-absent), recording
#       THIS kit's absolute path into its SEEDS section so an on-demand materialization can find
#       the seed templates later. BOTH names present => refuse up front, change nothing.
#   Install the five workflow hooks into .claude/hooks/ (mode 755), REFRESH-IF-DIFFERENT (a divergent
#       installed hook is backed up, then replaced with this kit's copy), and register them in
#       .claude/settings.json: seeded when absent, else DEEP-MERGED via lib/merge_settings.py so
#       your own settings and any foreign hook survive intact (a dated backup is kept before the
#       first merge). brief_gate + collect_outcome_gate + fable-launch-scaffold + plan-state-inject advise only;
#       fable-dispatch-gate is the ONE deny-capable gate (CRT_MODE off/observe silences it).
#   Install the MODEL-ROUTING capability set (v1.4/K10; REFRESH-IF-DIFFERENT since v1.8): .claude/agents/
#       — EVERY agent in payload/.claude/agents, taken as a GLOB (today: fable-executor, opus5-executor,
#       fable-subplanner; tomorrow whatever the payload gains) — and .claude/skills/model-verification/ (the serving-stamp
#       audit skill + instruments) — so a fresh project can both KNOW the model-control doctrine
#       (CLAUDE.md) and DO it, and an upgrading project gets the CURRENT contracts, not last version's.
#   Install the dev/tools DIAGNOSTICS (v1.8, REFRESH-IF-DIFFERENT, the source file's exec bit carried):
#       test_enforcement_e2e.sh (red-teams the installed gates + their registrations, one command)
#       + adherence_scorecard.py & test_adherence_scorecard.sh (the measurement instrument that
#       scores per-session workflow adherence, and its fixture guard) + stale_move.sh. A project
#       that ships enforcement ships the tools to VERIFY and MEASURE it, both directions; this is
#       also the one place the kit CREATES a lazy-materialized folder up front, and correctly so —
#       lazy materialization defers folders the kit has no content for, and it now has content.
#   (d) print a did/skipped/refreshed summary (naming the backup dir whenever one was made).
#   (e) ZERO deletes, ever. ZERO overwrites of USER-OWNED files. A kit-OWNED file that DIFFERS from the
#       payload is backed up and refreshed (above); one that matches is skipped, so a re-run at the same
#       kit version changes nothing it already did. .DS_Store is never copied.
#
# --upgrade-rules (v1.4) — UPGRADE an already-installed project: replace the FIRST
#   `<!-- planner-kit:BEGIN … -->` … `<!-- planner-kit:END -->` span inside the root CLAUDE.md with
#   this kit's current marker-wrapped rules block, IN PLACE. A dated backup of CLAUDE.md is kept
#   FIRST; every byte outside the span is untouched. REFUSES when no planner-kit block exists
#   (upgrade ≠ install — run without the flag to install). Without this flag the merge stays the
#   never-overwrite no-op it has always been. v1.5: the flag ALSO performs the STRUCTURE_RULES
#   migration above (it is unconditional in every mode), so ONE --upgrade-rules run fully converges
#   an old root — the block text and the file name move together.
#   v1.8: the flag ALSO refreshes STRUCTURE_RULES.md ITSELF — a whole-file replace with this kit's
#   current folder contract (this kit's path re-recorded into its SEEDS section), the project's copy
#   kept in the run's dated backup dir FIRST and named in the summary. It rides the OPT-IN, not the
#   default, because that file is an EDITABLE project surface (a project may extend its per-folder
#   contract) while the hooks/agents/skills/tools are shipped kit content. Identical => no change,
#   no backup, so a second --upgrade-rules run is a no-op on this axis too.
# --dry-run composes with all modes (prints actions, writes nothing). -h/--help documents all flags.
#
# Portability: bash 3.2+ (macOS default); no `timeout`; no GNU-only flags; no realpath / readlink -f.
# `set -u` + pipefail catch real bugs; `set -e` is deliberately NOT used, so one skipped/failed file is
# logged and never aborts the rest (fail-open on non-critical steps). Quote every path — paths may hold spaces.

set -u
set -o pipefail

KIT_VERSION="v1.8"

# The installed folder contract's file name, and the pre-v1.5 name it migrates FROM. Kept as two
# variables so the name lives in ONE place: every seed, migration, guard, summary line and closing
# message below reads them, so a future rename is a one-line change instead of a grep-and-hope.
STRUCT_DOC_NAME="STRUCTURE_RULES.md"
STRUCT_DOC_OLD="STRUCTURE_RULES.machine.md"
STRUCT_MIGRATED=0   # 1 once the old-name file was renamed (real run) or is predicted to be (dry-run)

# ---- resolve locations -----------------------------------------------------
# KIT_DIR    = where this script + payload/ live (the SOURCE).
# TARGET_DIR = the project we install INTO = the current working directory.
KIT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)" || {
  printf 'planner-kit: cannot resolve kit directory from "%s"\n' "$0" >&2
  exit 2
}
TARGET_DIR="$(pwd -P)"
PAYLOAD_DIR="$KIT_DIR/payload"
INSTALL_DATE="$(date +%F 2>/dev/null || echo unknown)"

# ---- the run's ONE refresh backup dir (v1.8) --------------------------------
# Every file a refresh replaces is copied here FIRST, under its own project-relative path, so the
# adopter can diff or restore any single file. ONE dir per RUN (not per day like the CLAUDE.md /
# settings.json backups): two runs minutes apart can carry different payload content, and a
# second run must never overwrite the copy the first run rescued. Created LAZILY — the mkdir
# happens inside the first backup, so a run that refreshes nothing leaves no empty dir behind,
# which is what keeps an idempotent re-run observably inert.
INSTALL_TS="$(date +%Y%m%d-%H%M%S 2>/dev/null || echo unknown)"
REFRESH_BACKUP_REL="backups/planner-kit-refresh-$INSTALL_TS"
REFRESH_BACKUP_MADE=0   # 1 once >=1 file has been backed up into it (real run) or is predicted to be (dry-run)

DRY_RUN=0
FULL=0              # --full = classic scaffold+seed layout up front; default (0) = minimal two-file install
UPGRADE=0           # --upgrade-rules = replace the existing planner-kit block in root CLAUDE.md in place
SUMMARY=""
V1_IN_DOTCLAUDE=0   # set to 1 if a planner-kit marker is found inside .claude/CLAUDE.md (v1 install)
CLAUDE_VER_MISMATCH=""  # set to the FOUND version if the root CLAUDE.md carries a planner-kit block whose version != KIT_VERSION

usage() {
  cat <<EOF
planner-kit installer ($KIT_VERSION)
Usage: cd /your/project && bash "$KIT_DIR/install.sh" [--full] [--upgrade-rules] [--dry-run]
  (default)   MINIMAL install: root CLAUDE.md + $STRUCT_DOC_NAME, plus the five
              workflow hooks + their .claude/settings.json registration, the
              model-routing set (every .claude/agents/ route the payload ships —
              fable-executor, opus5-executor, fable-subplanner — plus .claude/skills/model-verification),
              and the dev/tools diagnostics (enforcement e2e battery + adherence scorecard).
              The folder tree is materialized ON DEMAND per $STRUCT_DOC_NAME
              (a folder's absence = not yet needed, never an error). Kit-OWNED files
              (hooks, agents, model-verification skill, dev/tools) are REFRESHED when
              they differ from this kit's payload — the replaced copy is kept in a dated
              backup dir, printed at the end. Your own files are never overwritten.
  --full      CLASSIC install: pre-scaffold the whole standard tree + .gitkeeps + seed all
              ledger/memory/tool templates, PLUS $STRUCT_DOC_NAME.
  --upgrade-rules
              UPGRADE an installed project: replace the existing planner-kit rules block in
              the root CLAUDE.md with this kit's current block, in place (dated backup kept
              first; every byte outside the block untouched), AND replace $STRUCT_DOC_NAME
              with this kit's current copy (dated backup kept first). Refuses when no block exists.
  EVERY MODE  migrates a pre-v1.5 $STRUCT_DOC_OLD at the project root to
              $STRUCT_DOC_NAME (rename in place, content preserved). Both names
              present => refuses up front and changes nothing.
  --dry-run   print the actions that WOULD be taken; change nothing (composes with the others).
  -h, --help  show this help.
Installs into the CURRENT directory ($TARGET_DIR).
EOF
}

abort() { printf 'planner-kit: %s\n' "$1" >&2; exit 2; }

# record ACTION RESULT -> appended as one aligned line to the summary table.
# (Command substitution strips a trailing newline, so the newline is a literal
#  inside the quotes below — bash-3.2-safe way to build a multi-line string.)
record() {
  local label="$1"
  # Keep the RESULT column aligned: truncate an over-long ACTION (e.g. the long
  # planner feedback-memory seed paths) to the 46-char column width, marking the cut.
  if [ "${#label}" -gt 46 ]; then label="${label:0:45}~"; fi
  SUMMARY="${SUMMARY}$(printf '  %-46s %s' "$label" "$2")
"
}

# ---- parse args ------------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --full)          FULL=1 ;;
    --upgrade-rules) UPGRADE=1 ;;
    --dry-run)       DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'planner-kit: unknown argument: %s\n' "$arg" >&2; usage >&2; exit 2 ;;
  esac
done

# ---- preconditions ---------------------------------------------------------
[ -d "$PAYLOAD_DIR" ] || abort "payload/ not found next to install.sh (looked in \"$PAYLOAD_DIR\"). Keep install.sh alongside payload/."

# Refuse to install the kit into itself. Two cases:
#   (1) target is the kit dir OR anywhere inside its tree (payload/ included) — a prefix
#       match on the pwd -P-normalized paths (bash-3.2-safe; no realpath). The trailing
#       slash on TARGET_DIR makes the kit dir itself match "$KIT_DIR"/*, and the slash
#       after "$KIT_DIR" keeps a sibling like ".../planner-kit-other" from matching.
#   (2) target is a *copy* of the kit elsewhere (has both install.sh and payload/).
case "$TARGET_DIR/" in
  "$KIT_DIR"/*)
    abort "current directory is inside the kit itself (\"$TARGET_DIR\"). cd into your PROJECT ROOT first, then run: bash \"$KIT_DIR/install.sh\"" ;;
esac
if [ -f "$TARGET_DIR/install.sh" ] && [ -d "$TARGET_DIR/payload" ]; then
  abort "current directory looks like a copy of the kit (\"$TARGET_DIR\"). cd into your PROJECT ROOT first, then run: bash \"$KIT_DIR/install.sh\""
fi

# BOTH-NAMES guard (v1.5): a root that carries the pre-v1.5 STRUCTURE_RULES.machine.md AND the
# current STRUCTURE_RULES.md is AMBIGUOUS — the installer cannot know which one the project treats
# as authoritative, and the two may have diverged. Picking one silently would demote the other to
# invisible-but-still-greppable poison, and overwriting either would destroy content the kit did
# not write. So: refuse LOUDLY, here in the preconditions, BEFORE any step writes anything — a
# refused run leaves the project byte-identical. This fires in every mode, --dry-run included:
# the state is unresolvable, so there is nothing honest to predict either.
if [ -e "$TARGET_DIR/$STRUCT_DOC_OLD" ] && [ -e "$TARGET_DIR/$STRUCT_DOC_NAME" ]; then
  abort "\"$TARGET_DIR\" carries BOTH $STRUCT_DOC_OLD and $STRUCT_DOC_NAME — cannot tell which is authoritative, so nothing was changed. REMEDY: keep the one you want as \"$STRUCT_DOC_NAME\", move the other aside (e.g. into Stale_Trash/), then re-run."
fi

# --upgrade-rules preconditions: upgrade REPLACES an existing block, it never installs one.
# Refuse up front, BEFORE any other step runs, so a mistaken upgrade run changes nothing at all.
if [ "$UPGRADE" = 1 ]; then
  if [ ! -f "$TARGET_DIR/CLAUDE.md" ]; then
    abort "--upgrade-rules: no CLAUDE.md at \"$TARGET_DIR\" — nothing to upgrade. Run without the flag to install."
  elif ! grep -q -- '<!-- planner-kit:BEGIN' "$TARGET_DIR/CLAUDE.md"; then
    abort "--upgrade-rules: no planner-kit block found in \"$TARGET_DIR/CLAUDE.md\" — nothing to upgrade (upgrade replaces an existing block, it never installs one). Run without the flag to install."
  fi
fi

MODE="install"
if [ "$DRY_RUN" = 1 ]; then MODE="dry-run"; fi
VARIANT="minimal"
if [ "$FULL" = 1 ]; then VARIANT="full"; fi
if [ "$UPGRADE" = 1 ]; then VARIANT="$VARIANT+upgrade-rules"; fi
printf 'planner-kit %s (%s %s) -> %s\n\n' "$KIT_VERSION" "$VARIANT" "$MODE" "$TARGET_DIR"

# ---- helpers ---------------------------------------------------------------
ensure_dir() {  # ensure_dir RELPATH
  local d="$TARGET_DIR/$1"
  if [ -d "$d" ]; then
    record "dir  $1" "exists"
  elif [ "$DRY_RUN" = 1 ]; then
    record "dir  $1" "would create"
  elif mkdir -p "$d"; then
    record "dir  $1" "created"
  else
    record "dir  $1" "FAILED (mkdir)"
  fi
}

seed_file() {  # seed_file SRC_ABS DST_RELPATH  (only-if-absent = portable cp -n)
  local src="$1" rel="$2" dst
  dst="$TARGET_DIR/$rel"
  if [ ! -f "$src" ]; then
    record "seed $rel" "SKIPPED (no source)"
  elif [ -e "$dst" ]; then
    record "seed $rel" "skipped (exists)"
  elif [ "$DRY_RUN" = 1 ]; then
    record "seed $rel" "would seed"
  elif mkdir -p "$(dirname "$dst")" && cp "$src" "$dst"; then
    record "seed $rel" "seeded"
  else
    record "seed $rel" "FAILED (cp)"
  fi
}

seed_glob() {  # seed_glob SRC_DIR_ABS DST_RELDIR  — seed every regular file in SRC_DIR
  local srcdir="$1" reldir="$2" f base
  for f in "$srcdir"/*; do
    [ -f "$f" ] || continue          # skip literal glob (no match) / non-files
    base="$(basename "$f")"
    [ "$base" = ".DS_Store" ] && continue   # never copy macOS Finder cruft (belt-and-suspenders: * already skips dotfiles)
    seed_file "$f" "$reldir/$base"
  done
}

# ---- KIT-OWNED artifacts: refresh-if-different (v1.8) ----------------------
# The seed helpers above are EXISTENCE-gated, which is right for a template the project then owns and
# edits. It is wrong for the files the KIT owns — the hooks, the agents, the model-verification skill,
# the dev/tools diagnostics — because there the project is not the author: it is a consumer of a
# versioned artifact, and an existence gate silently pins it to whatever version it first installed.
# These three helpers are that second contract: compare, back up, replace. See the CONTENT REFRESH
# note in the header for the failure this closes.
backup_before_replace() {  # backup_before_replace DST_RELPATH -> 0 = the project's copy is safely kept
  # Copy the project's CURRENT file into THIS RUN's backup dir under its own project-relative path
  # (backups/planner-kit-refresh-<ts>/<rel>), so each rescued file's origin is readable from the path
  # alone and two same-named files (a hook and a tool) cannot collide. Never called in dry-run.
  # TWO statements, deliberately: bash expands ALL the words of a `local` builtin BEFORE binding any of
  # them, so `local rel="$1" bak="…$rel"` would read the CALLER's `rel` — which under `set -u` is a
  # fatal unbound-variable exit whenever the caller has none (measured: --upgrade-rules aborted the
  # whole install here, and it only looked fine from refresh_file because that caller happens to have
  # a `rel` of its own in dynamic scope holding the same value).
  local rel="$1"
  local bak="$TARGET_DIR/$REFRESH_BACKUP_REL/$rel"
  mkdir -p "$(dirname "$bak")" 2>/dev/null || return 1
  cp "$TARGET_DIR/$rel" "$bak" 2>/dev/null || return 1
  REFRESH_BACKUP_MADE=1
  return 0
}

refresh_file() {  # refresh_file SRC_ABS DST_RELPATH KIND MODE
  # KIND = the summary label word (hook|tool|agent|skill) — cosmetic, it keeps the table readable.
  # MODE = "755"   -> always executable (hooks: a hook that lost its +x never fires), or
  #        "carry" -> take the SOURCE's mode, so a non-executable payload file (a data sidecar
  #                   shipped beside a script) stays non-executable. Preserving, not forcing.
  local src="$1" rel="$2" kind="$3" mode="$4" dst tmp verb suffix
  dst="$TARGET_DIR/$rel"
  if [ ! -f "$src" ]; then
    record "$kind $rel" "SKIPPED (no source)"; return 0
  elif [ -e "$dst" ] && [ ! -f "$dst" ]; then
    # A directory / symlink-to-dir / device where a file belongs: refuse and say so. Replacing it
    # would need a delete, and this installer deletes nothing.
    record "$kind $rel" "SKIPPED (target is not a regular file)"; return 0
  fi
  if [ -f "$dst" ]; then
    if cmp -s "$src" "$dst"; then
      record "$kind $rel" "skipped (identical)"; return 0   # THE no-op path: same bytes => no write, no backup
    fi
    verb="refreshed"
  else
    verb="installed"
  fi
  if [ "$DRY_RUN" = 1 ]; then
    if [ "$verb" = refreshed ]; then
      REFRESH_BACKUP_MADE=1                                  # predict the backup dir the real run would make
      record "$kind $rel" "would refresh (yours backed up)"
    else
      record "$kind $rel" "would install"
    fi
    return 0
  fi
  # BACKUP FIRST — no backup, no replace. The whole permission to overwrite rests on the project's
  # copy staying recoverable, so a failed backup ABANDONS the refresh (logged) rather than completing
  # it: a stale file is a smaller loss than an unrecoverable one.
  if [ "$verb" = refreshed ] && ! backup_before_replace "$rel"; then
    record "$kind $rel" "FAILED (backup) — refresh skipped, your copy untouched"; return 0
  fi
  # Write via a temp beside the target, then rename: same filesystem => the swap is atomic, so a hook
  # firing mid-install never reads a half-written file. Copying to a NEW temp also gives it the SOURCE's
  # mode — a plain `cp` ONTO an existing file would keep the OLD file's mode — which is what carries the
  # payload's exec bit through a refresh.
  tmp="$dst.pk-refresh.tmp"
  if ! mkdir -p "$(dirname "$dst")" 2>/dev/null || ! cp "$src" "$tmp" 2>/dev/null; then
    rm -f "$tmp" 2>/dev/null
    record "$kind $rel" "FAILED (copy)"; return 0
  fi
  suffix=""
  if [ "$mode" = 755 ]; then
    if chmod 755 "$tmp" 2>/dev/null; then
      suffix=" (mode 755)"
    else
      suffix=" (NOT marked +x — chmod it if it never fires)"   # fixable; a missing file is not
    fi
  elif [ -x "$src" ]; then
    suffix=" (mode carried)"
  fi
  if mv "$tmp" "$dst" 2>/dev/null; then
    if [ "$verb" = refreshed ]; then
      record "$kind $rel" "refreshed, yours backed up$suffix"
    else
      record "$kind $rel" "installed$suffix"
    fi
  else
    rm -f "$tmp" 2>/dev/null
    record "$kind $rel" "FAILED (write)"
  fi
}

refresh_glob() {  # refresh_glob SRC_DIR_ABS DST_RELDIR KIND MODE — refresh_file every regular file in SRC_DIR
  # NON-recursive and PAYLOAD-DRIVEN: it walks the PAYLOAD's files, never the project's. That is what
  # keeps a project's own agent, its own tool, or a foreign skill file outside the refresh's reach —
  # no exclusion list to maintain, because a file the kit never shipped is never even visited. It is
  # also why a payload ADDITION (the next agent the kit ships) needs no edit here.
  local srcdir="$1" reldir="$2" kind="$3" mode="$4" f base
  for f in "$srcdir"/*; do
    [ -f "$f" ] || continue
    base="$(basename "$f")"
    [ "$base" = ".DS_Store" ] && continue
    refresh_file "$f" "$reldir/$base" "$kind" "$mode"
  done
}

# Predict whether a scaffold dir would END UP EMPTY after the --full scaffold+seed passes,
# WITHOUT touching the filesystem (dry-run creates nothing to observe). This MIRRORS the
# real-run oracle (`ls -A "$d"` at gitkeep time on a fresh target): a scaffold dir is
# non-empty iff (1) it is a PARENT of another scaffold dir (so mkdir -p left a subdir in it),
# or (2) it received >=1 seed file. Both signals come from the SAME inputs the real passes
# consume — SCAFFOLD_DIRS (the dir list) and payload/ (the seed sources map identity
# payload/<rel> -> <rel>; see the seed_glob calls below) — so this is not a parallel hardcoded
# heuristic but the same emptiness decision re-read predictively. Only called in dry-run.
scaffold_dir_would_be_empty() {  # RELPATH -> 0 (true) if it stays empty => needs a .gitkeep
  local rel="$1" other f
  # (0) if the dir ALREADY exists in the target and is non-empty, the real run keeps it non-empty
  #     (pre-existing user content, or seeds/.gitkeep from a prior install) => skip. This makes the
  #     prediction track the target's CURRENT state, so a --dry-run RE-RUN after a real install
  #     correctly predicts "nothing to add" (mirrors the idempotent real re-run) instead of blindly
  #     re-predicting already-present .gitkeeps.
  if [ -d "$TARGET_DIR/$rel" ] && [ -n "$(ls -A "$TARGET_DIR/$rel" 2>/dev/null)" ]; then
    return 1
  fi
  for other in $SCAFFOLD_DIRS; do
    case "$other" in "$rel"/*) return 1 ;; esac    # a scaffold subdir lives under $rel => non-empty
  done
  if [ -d "$PAYLOAD_DIR/$rel" ]; then
    for f in "$PAYLOAD_DIR/$rel"/*; do
      [ -f "$f" ] || continue
      [ "$(basename "$f")" = ".DS_Store" ] && continue
      return 1                                       # >=1 seed file lands here => non-empty
    done
  fi
  return 0                                           # no subdir, no seed => stays empty
}

gitkeep_if_empty() {  # gitkeep_if_empty RELPATH — drop a .gitkeep IFF the dir is/would be EMPTY.
  # A dir that got seeded (dev/, plans/, dev/tools/, agent-memory/planner/) or that parents a
  # subdir is non-empty and is skipped. The .gitkeep itself makes the dir non-empty, so a
  # re-run is a no-op. In dry-run no dir was created, so `ls -A` cannot observe emptiness, so
  # PREDICT it via scaffold_dir_would_be_empty (mirrors the real ls -A oracle on a fresh target).
  local d="$TARGET_DIR/$1"
  if [ "$DRY_RUN" = 1 ]; then
    if scaffold_dir_would_be_empty "$1"; then
      record "keep $1/.gitkeep" "would add"
    fi
    return 0
  fi
  [ -d "$d" ] || return 0            # real run, dir absent (shouldn't happen post-scaffold) => nothing to keep
  if [ -n "$(ls -A "$d" 2>/dev/null)" ]; then
    return 0                         # already non-empty (seeded, or .gitkeep already there)
  elif : > "$d/.gitkeep" 2>/dev/null; then
    record "keep $1/.gitkeep" "added"
  else
    record "keep $1/.gitkeep" "FAILED (write)"
  fi
}

migrate_structure_doc() {  # v1.5: rename an installed pre-v1.5 STRUCTURE_RULES.machine.md to STRUCTURE_RULES.md.
  # Runs in EVERY mode (default, --full, --upgrade-rules), BEFORE seed_structure_doc, so one run of any
  # mode fully converges an old root. NON-DESTRUCTIVE by construction: a rename MOVES the project's own
  # file (content preserved byte-for-byte, mtime and mode carried by mv), it never copies the payload over
  # it — so a project that edited its folder contract keeps every edit, under the new name. Plain `mv`, not
  # `git mv`: the installer must not assume the target is a git repo (staging the rename is the caller's
  # affair). ZERO deletes. The BOTH-names case aborted in preconditions, so reaching here with the old name
  # present means the new name is ABSENT and the rename cannot clobber anything. Nothing to migrate (fresh
  # root, or already migrated) => silent no-op, which is what makes a second run idempotent on this axis.
  local old="$TARGET_DIR/$STRUCT_DOC_OLD" new="$TARGET_DIR/$STRUCT_DOC_NAME"
  [ -e "$old" ] || return 0
  if [ "$DRY_RUN" = 1 ]; then
    STRUCT_MIGRATED=1
    record "migrate $STRUCT_DOC_OLD" "would rename -> $STRUCT_DOC_NAME"
  elif mv "$old" "$new"; then
    STRUCT_MIGRATED=1
    record "migrate $STRUCT_DOC_OLD" "renamed -> $STRUCT_DOC_NAME (content preserved)"
  else
    record "migrate $STRUCT_DOC_OLD" "FAILED (rename) — old name left in place"
  fi
}

seed_structure_doc() {  # install STRUCTURE_RULES.md, recording THIS kit's abs path into its SEEDS section.
  # Runs in BOTH modes (it is half of the minimal two-file default). Seed-if-absent and NEVER overwrite —
  # EXCEPT under --upgrade-rules (v1.8), which replaces it whole after a dated backup (branch below).
  # The rendering itself lives in render_structure_doc: the payload doc's placeholder line
  # "@@KIT_SEED_PATH@@" becomes a "KIT_PATH=<abs path>" line so a later on-demand materialization can
  # find the seed templates. The seed path writes by direct redirect (same non-atomicity as the
  # CLAUDE.md create path), guarded by the seed-if-absent check so it can never truncate an existing
  # file; the upgrade path writes through a temp + rename, because there it IS replacing a live file.
  # It never runs when src -ef dst (target-inside-kit is already aborted in preconditions).
  # The MIGRATED branch is tested BEFORE the exists test on purpose: in a real run the migration already
  # put the file on disk, in a dry-run it only predicted it, and both must report the SAME line — the
  # dry-run's prediction is only worth reading if it equals what the real run does.
  local src="$PAYLOAD_DIR/$STRUCT_DOC_NAME"
  local dst="$TARGET_DIR/$STRUCT_DOC_NAME"
  local tmp cur=""
  if [ ! -f "$src" ]; then
    record "$STRUCT_DOC_NAME" "SKIPPED (no payload source)"; return 0
  fi

  # --upgrade-rules (v1.8): REPLACE the installed folder contract with this kit's current copy.
  # This file rides the OPT-IN rather than the default refresh because it is an EDITABLE project
  # surface — a project may extend its own per-folder contract — so replacing it is a decision the
  # adopter makes by passing the flag, not one a routine re-run makes for them. The project's copy
  # goes into the run's dated backup dir first; identical => no write, no backup, so a second
  # --upgrade-rules run is a no-op on this axis.
  # `cur` is the file the upgrade compares against: normally the installed doc, but in a DRY-RUN
  # that PREDICTED a migration the new name is not on disk yet, so the honest comparand is the
  # old-name file the real run would have renamed into place.
  if [ -f "$dst" ]; then
    cur="$dst"
  elif [ "$DRY_RUN" = 1 ] && [ "$STRUCT_MIGRATED" = 1 ] && [ -f "$TARGET_DIR/$STRUCT_DOC_OLD" ]; then
    cur="$TARGET_DIR/$STRUCT_DOC_OLD"
  fi
  if [ "$UPGRADE" = 1 ] && [ -n "$cur" ]; then
    tmp="${TMPDIR:-/tmp}/planner-kit-struct.$$"
    if ! render_structure_doc "$tmp"; then
      rm -f "$tmp" 2>/dev/null
      record "$STRUCT_DOC_NAME" "FAILED (render)"; return 0
    fi
    if cmp -s "$tmp" "$cur"; then
      rm -f "$tmp" 2>/dev/null
      record "$STRUCT_DOC_NAME" "no change (already current)"; return 0
    fi
    if [ "$DRY_RUN" = 1 ]; then
      rm -f "$tmp" 2>/dev/null
      REFRESH_BACKUP_MADE=1
      record "$STRUCT_DOC_NAME" "would upgrade (yours backed up)"; return 0
    fi
    if ! backup_before_replace "$STRUCT_DOC_NAME"; then
      rm -f "$tmp" 2>/dev/null
      record "$STRUCT_DOC_NAME" "FAILED (backup) — upgrade skipped, your copy untouched"; return 0
    fi
    if cp "$tmp" "$dst.pk-struct.tmp" 2>/dev/null && mv "$dst.pk-struct.tmp" "$dst"; then
      record "$STRUCT_DOC_NAME" "upgraded, yours backed up (kit path recorded)"
    else
      record "$STRUCT_DOC_NAME" "FAILED (upgrade write)"
    fi
    rm -f "$tmp" "$dst.pk-struct.tmp" 2>/dev/null
    return 0
  fi

  if [ "$STRUCT_MIGRATED" = 1 ]; then
    record "$STRUCT_DOC_NAME" "skipped (migrated above — your copy kept)"
  elif [ -e "$dst" ]; then
    record "$STRUCT_DOC_NAME" "skipped (exists)"
  elif [ "$DRY_RUN" = 1 ]; then
    record "$STRUCT_DOC_NAME" "would seed (kit path recorded)"
  elif render_structure_doc "$dst"; then
    record "$STRUCT_DOC_NAME" "seeded (kit path recorded)"
  else
    record "$STRUCT_DOC_NAME" "FAILED (write)"
  fi
}

render_structure_doc() {  # render_structure_doc OUTFILE -> 0 if OUTFILE now holds the doc AS IT SHOULD BE INSTALLED
  # ONE render path, shared by the seed, the --upgrade-rules replace, and the upgrade's own
  # already-current comparison — the same single-write-path doctrine settings_merged_bytes follows,
  # so a preview can never disagree with the write. The payload's "@@KIT_SEED_PATH@@" placeholder
  # line becomes "KIT_PATH=<abs path>" so a later on-demand materialization can find the seed
  # templates. The path is passed via the ENVIRONMENT and read with awk ENVIRON[] so awk applies NO
  # escape processing to it (spaces / backslashes survive verbatim).
  PK_KIT_DIR="$KIT_DIR" awk '
        $0 == "@@KIT_SEED_PATH@@" { print "KIT_PATH=" ENVIRON["PK_KIT_DIR"]; next }
        { print }
      ' "$PAYLOAD_DIR/$STRUCT_DOC_NAME" > "$1" 2>/dev/null
}

# ---- hooks + settings (BOTH modes; default-on) ------------------------------
HOOK_NAMES="brief_gate.sh collect_outcome_gate.sh fable-dispatch-gate.sh fable-launch-scaffold.sh plan-state-inject.sh"   # fixed names, no spaces => word-split is safe
HOOKS_SRC_DIR="$PAYLOAD_DIR/.claude/hooks"
SETTINGS_SRC="$PAYLOAD_DIR/.claude/settings.json"
SETTINGS_DST="$TARGET_DIR/.claude/settings.json"
MERGE_TOOL="$KIT_DIR/lib/merge_settings.py"

seed_hook() {  # seed_hook NAME — install the hook, and REFRESH it when the installed copy differs (v1.8).
  # A hook is the kit's own shipped content, and a STALE one is the worst case this installer has:
  # registered in settings.json, firing on every launch, and enforcing last version's contract while
  # the CLAUDE.md beside it states this version's. So hooks take the refresh contract, at mode 755 —
  # a hook that lost its +x never fires, and a silent non-firing gate is indistinguishable from a
  # passing one.
  refresh_file "$HOOKS_SRC_DIR/$1" ".claude/hooks/$1" "hook" 755
}

settings_merged_bytes() {  # settings_merged_bytes OUTFILE -> 0 if OUTFILE now holds the merged result
  # THE decision oracle, shared verbatim by the SEED, the MERGE and the dry-run prediction:
  # start from whatever the target holds now (an empty file when it is absent, which the
  # merger reads as {}) and let the vendored house merger fold the kit fragment in. ONE write
  # path for all three, so the preview cannot disagree with the write, and a first install
  # already equals a re-install — the merger's own normalized output is the only thing ever
  # written, so idempotency holds by construction instead of by byte-luck. (Seeding the
  # payload file verbatim instead is what broke it: the merger re-serializes JSON, so run 2
  # rewrote run 1's literal bytes and the tree hash moved.)
  if [ -e "$SETTINGS_DST" ]; then
    cp "$SETTINGS_DST" "$1" 2>/dev/null || return 1
  else
    : > "$1" 2>/dev/null || return 1
  fi
  python3 "$MERGE_TOOL" "$1" "$SETTINGS_SRC" >/dev/null 2>&1 || return 1
  return 0
}

seed_settings() {
  local tmp bak fresh=0
  if [ ! -f "$SETTINGS_SRC" ]; then
    record ".claude/settings.json" "SKIPPED (no payload source)"; return 0
  fi
  [ -e "$SETTINGS_DST" ] || fresh=1

  # No merger reachable? A FRESH target can still be seeded verbatim (nothing to preserve);
  # an EXISTING one is left strictly alone — never clobber what cannot be merged.
  if [ ! -f "$MERGE_TOOL" ] || ! command -v python3 >/dev/null 2>&1; then
    if [ "$fresh" = 0 ]; then
      record ".claude/settings.json" "SKIPPED (deep-merge needs python3 + the kit lib/)"
    elif [ "$DRY_RUN" = 1 ]; then
      record ".claude/settings.json" "would seed (hook registrations)"
    elif mkdir -p "$(dirname "$SETTINGS_DST")" && cp "$SETTINGS_SRC" "$SETTINGS_DST"; then
      record ".claude/settings.json" "seeded (hook registrations, unmerged)"
    else
      record ".claude/settings.json" "FAILED (write)"
    fi
    return 0
  fi

  tmp="${TMPDIR:-/tmp}/planner-kit-settings.$$"
  if ! settings_merged_bytes "$tmp"; then
    rm -f "$tmp" 2>/dev/null
    record ".claude/settings.json" "SKIPPED (existing file is not valid JSON)"; return 0
  fi
  if [ "$fresh" = 0 ] && cmp -s "$tmp" "$SETTINGS_DST"; then
    rm -f "$tmp" 2>/dev/null
    record ".claude/settings.json" "no change (hooks already registered)"; return 0
  fi

  bak="$SETTINGS_DST.pre-planner-kit-$INSTALL_DATE"
  if [ "$DRY_RUN" = 1 ]; then
    rm -f "$tmp" 2>/dev/null
    if [ "$fresh" = 1 ]; then
      record ".claude/settings.json" "would seed (hook registrations)"
    else
      [ -e "$bak" ] || record "backup .claude/settings.json" "would keep (pre-merge copy)"
      record ".claude/settings.json" "would deep-merge (your settings kept, hooks added)"
    fi
    return 0
  fi

  # Keep the user's pre-merge file once, before the first rewrite of it.
  if [ "$fresh" = 0 ] && [ ! -e "$bak" ]; then
    if cp "$SETTINGS_DST" "$bak" 2>/dev/null; then
      record "backup .claude/settings.json" "kept (pre-merge copy)"
    else
      record "backup .claude/settings.json" "FAILED (backup) — merge skipped"
      rm -f "$tmp" 2>/dev/null
      return 0
    fi
  fi
  # Rename into place from a temp beside the target: same filesystem => the swap is atomic,
  # so a reader never catches a half-written settings.json.
  if mkdir -p "$(dirname "$SETTINGS_DST")" \
     && cp "$tmp" "$SETTINGS_DST.pk-merge.tmp" 2>/dev/null \
     && mv "$SETTINGS_DST.pk-merge.tmp" "$SETTINGS_DST"; then
    if [ "$fresh" = 1 ]; then
      record ".claude/settings.json" "seeded (hook registrations)"
    else
      record ".claude/settings.json" "deep-merged (your settings kept, hooks added)"
    fi
  else
    record ".claude/settings.json" "FAILED (write)"
  fi
  rm -f "$tmp" "$SETTINGS_DST.pk-merge.tmp" 2>/dev/null || true
}

# ---- dev/tools DIAGNOSTICS (BOTH modes; v1.8) ------------------------------
# The kit ships the tools that VERIFY and MEASURE the enforcement it ships: the e2e battery that
# red-teams the installed gates, the adherence scorecard that scores per-session workflow fidelity,
# that scorecard's own fixture guard, and stale_move.sh. REFRESH-IF-DIFFERENT, exec bit carried —
# a diagnostic pinned to an old version red-teams an old contract and reports green on a project
# that no longer matches it, which is the one failure a diagnostic must not have.
# POSITION IS LOAD-BEARING — this runs BEFORE the --full block, not after it. Under --full the
# gitkeep pass asks `ls -A dev/tools` and its dry-run twin asks "would any seed land here?"; seeding
# first makes the real answer match the predicted one, so a --full run and its --dry-run agree.
# Seeding after would leave a real run dropping a .gitkeep the dry-run never predicted.
# (Before v1.8 dev/tools was seeded inside the --full block; the call moved here, it did not double.)
refresh_glob "$PAYLOAD_DIR/dev/tools" "dev/tools" "tool" carry

# ---- (a/b/b2) FULL-mode scaffold + seed + gitkeep --------------------------
# Minimal (default) mode SKIPS this whole block: it pre-creates NO folders and seeds NO templates.
# The agent materializes each folder on demand per STRUCTURE_RULES.md. --full lays down the
# classic v1.1 tree up front. Both modes still install STRUCTURE_RULES.md + CLAUDE.md below.
if [ "$FULL" = 1 ]; then
  # ONE source-of-truth dir list (reused by the gitkeep pass below, so the two can never drift). These
  # are fixed kit-relative names with no spaces, so the unquoted word-split in the `for` loops is
  # intentional and safe here.
  SCAFFOLD_DIRS="src \
    dev dev/briefs dev/tools \
    documents \
    data-outputs data-outputs/source-immutable data-outputs/intermediate data-outputs/products \
    plots-figures-tables \
    sandbox backups Stale_Trash \
    plans plans/current_active plans/for_later_resume plans/finished \
    .claude/agent-memory/planner"
  for d in $SCAFFOLD_DIRS; do
    ensure_dir "$d"
  done

  # (b) seed templates + memories + tools (only-if-absent)
  # seed_glob is NON-recursive (it seeds the regular files of ONE dir), so every payload
  # subdir that ships seed content needs its own call here.
  seed_glob "$PAYLOAD_DIR/plans"      "plans"
  seed_glob "$PAYLOAD_DIR/dev"        "dev"
  seed_glob "$PAYLOAD_DIR/dev/briefs" "dev/briefs"
  # dev/tools is seeded ABOVE, in BOTH modes (v1.8) — deliberately not repeated here.
  seed_glob "$PAYLOAD_DIR/.claude/agent-memory/planner" ".claude/agent-memory/planner"

  # (b2) .gitkeep every created dir that stayed empty (after seeding)
  for d in $SCAFFOLD_DIRS; do
    gitkeep_if_empty "$d"
  done
fi

# ---- STRUCTURE_RULES.md (BOTH modes — the other half of the minimal default) ----
# MIGRATE first (rename a pre-v1.5 old-name file), THEN seed. The order is load-bearing: seeding
# first would drop the payload's pristine copy beside the project's edited one and produce exactly
# the both-names ambiguity the precondition refuses.
migrate_structure_doc
seed_structure_doc

# ---- hooks + their registration (BOTH modes — the workflow backstop is default-on) ----
for h in $HOOK_NAMES; do
  seed_hook "$h"
done
seed_settings

# ---- model-routing capability set (BOTH modes; v1.4/K10, refreshed since v1.8) ----
# The model-routing agents (fable-executor, opus5-executor, fable-subplanner — the constructed routes,
# and the GLOB below is what keeps this list from becoming the thing that has to be edited) + the model-verification skill (the serving-stamp
# audit + the live watchdog) ship with the kit so a fresh project can both KNOW the model-control
# doctrine in CLAUDE.md and DO it. REFRESH-IF-DIFFERENT: these carry contracts (grants, watch
# conditions, the launch convention) that the co-installed CLAUDE.md block cites by name, so a stale
# agent body and a current rules block disagree about the same route.
# THE AGENTS ARE TAKEN AS A GLOB, deliberately — not a name list — so an agent the payload gains
# later (a sub-planner route, say) installs and refreshes with no edit to this file. refresh_glob is
# non-recursive, so each payload subdir gets its own call.
refresh_glob "$PAYLOAD_DIR/.claude/agents" ".claude/agents" "agent" carry
refresh_glob "$PAYLOAD_DIR/.claude/skills/model-verification" ".claude/skills/model-verification" "skill" carry

# ---- (c) ROOT CLAUDE.md: create | append-behind-marker | no-op -------------
# v1.1 change: the rules front door is the ROOT CLAUDE.md (preferred by external
# GitHub Actions / Code-Review runners); .claude/CLAUDE.md becomes a pointer stub.
SRC_CLAUDE="$PAYLOAD_DIR/.claude/CLAUDE.md"
DST_CLAUDE="$TARGET_DIR/CLAUDE.md"              # ROOT front door (was .claude/CLAUDE.md in v1)
POINTER_CLAUDE="$TARGET_DIR/.claude/CLAUDE.md"  # <=2-line pointer stub -> ../CLAUDE.md
BEGIN_MARKER="<!-- planner-kit:BEGIN $KIT_VERSION installed=$INSTALL_DATE -->"
END_MARKER="<!-- planner-kit:END -->"

emit_block() {  # marker-wrapped payload rules block -> stdout
  printf '%s\n' "$BEGIN_MARKER"
  cat "$SRC_CLAUDE"
  printf '\n%s\n' "$END_MARKER"
}

# Backstop (defense-in-depth behind the kit-as-target abort above): never let a
# redirect write CLAUDE.md onto its own source. If SRC and DST resolve to the same
# file (e.g. run from inside payload/, or DST is a symlink to the payload), then
# `cat "$SRC" >> "$DST"` appends a file to itself and fills the disk. `-ef` = same
# device+inode (bash-3.2-safe). Guard immediately before BOTH redirects: abort, never write.
if [ ! -f "$SRC_CLAUDE" ]; then
  record "CLAUDE.md (root)" "SKIPPED (no payload source)"
elif [ ! -e "$DST_CLAUDE" ]; then
  if [ "$DRY_RUN" = 1 ]; then
    record "CLAUDE.md (root)" "would create (fresh, marker-wrapped)"
  elif [ "$SRC_CLAUDE" -ef "$DST_CLAUDE" ]; then
    abort "CLAUDE.md source and destination are the same file (\"$DST_CLAUDE\"). Run from your PROJECT ROOT, not from inside the kit."
  elif mkdir -p "$(dirname "$DST_CLAUDE")" && emit_block > "$DST_CLAUDE"; then
    record "CLAUDE.md (root)" "created (fresh)"
  else
    record "CLAUDE.md (root)" "FAILED (write)"
  fi
elif [ "$UPGRADE" = 1 ]; then
  # --upgrade-rules: replace the FIRST BEGIN..END span with the fresh block, IN PLACE. The
  # preconditions already guaranteed DST exists and carries a BEGIN marker, so reaching here
  # means "upgrade an installed block", never "install". Every byte OUTSIDE the span survives
  # untouched: the awk below copies lines before/after the span verbatim and swaps only the span.
  found_ver="$(grep -- '<!-- planner-kit:BEGIN' "$DST_CLAUDE" | head -n1 | sed -n 's/.*planner-kit:BEGIN \(v[^ ]*\).*/\1/p')"
  [ -n "$found_ver" ] || found_ver="unversioned"
  begin_ln="$(grep -n -- '<!-- planner-kit:BEGIN' "$DST_CLAUDE" | head -n1 | cut -d: -f1)"
  end_ln="$(awk -v s="$begin_ln" 'NR >= s+0 && index($0, "<!-- planner-kit:END -->") > 0 { print NR; exit }' "$DST_CLAUDE")"
  if [ -z "$end_ln" ]; then
    abort "--upgrade-rules: found planner-kit:BEGIN at line $begin_ln of \"$DST_CLAUDE\" but no planner-kit:END after it — the block is malformed; fix the markers by hand, then re-run."
  elif [ "$DRY_RUN" = 1 ]; then
    record "CLAUDE.md (root)" "would upgrade ($found_ver -> $KIT_VERSION; backup kept)"
  elif [ "$SRC_CLAUDE" -ef "$DST_CLAUDE" ]; then
    abort "CLAUDE.md source and destination are the same file (\"$DST_CLAUDE\"). Run from your PROJECT ROOT, not from inside the kit."
  else
    # Keep the user's pre-upgrade file once per day, before the first rewrite of it (the same
    # dated-backup pattern seed_settings uses). No backup => no upgrade.
    bak="$DST_CLAUDE.pre-planner-kit-$INSTALL_DATE"
    if [ ! -e "$bak" ]; then
      if cp "$DST_CLAUDE" "$bak" 2>/dev/null; then
        record "backup CLAUDE.md" "kept (pre-upgrade copy)"
      else
        record "CLAUDE.md (root)" "FAILED (backup) — upgrade skipped"
        bak=""
      fi
    else
      record "backup CLAUDE.md" "exists (kept earlier today)"
    fi
    if [ -n "$bak" ]; then
      blocktmp="${TMPDIR:-/tmp}/planner-kit-block.$$"
      newtmp="$DST_CLAUDE.pk-upgrade.tmp"
      # Rename into place from a temp beside the target: same filesystem => the swap is atomic,
      # so a reader never catches a half-written CLAUDE.md (same pattern as the settings merge).
      if emit_block > "$blocktmp" \
         && awk -v s="$begin_ln" -v e="$end_ln" -v blockfile="$blocktmp" '
              NR == s+0 { while ((getline line < blockfile) > 0) print line; next }
              NR > s+0 && NR <= e+0 { next }
              { print }
            ' "$DST_CLAUDE" > "$newtmp" \
         && mv "$newtmp" "$DST_CLAUDE"; then
        record "CLAUDE.md (root)" "upgraded ($found_ver -> $KIT_VERSION)"
      else
        record "CLAUDE.md (root)" "FAILED (upgrade write)"
      fi
      rm -f "$blocktmp" "$newtmp" 2>/dev/null || true
    fi
  fi
elif grep -q -- '<!-- planner-kit:BEGIN' "$DST_CLAUDE"; then
  # A planner-kit block is already present => the rules merge is a NO-OP (never auto-rewrite the
  # user's CLAUDE.md). But DETECT a VERSION MISMATCH: a block from a different KIT_VERSION won't
  # carry this version's references (e.g. the STRUCTURE_RULES.md pointer, and before v1.5 it named
  # that file STRUCTURE_RULES.machine.md), so a freshly seeded STRUCTURE_RULES can sit unreferenced
  # beside an older block — an old block's pointer now names a file that no longer exists under that
  # name, which is exactly what --upgrade-rules converges. Extract the
  # version token (a leading 'v...') from the FIRST BEGIN marker; a version-less manual drop-in
  # ("planner-kit:BEGIN -->", per README) yields no token => no spurious warning. If it differs
  # from KIT_VERSION, flag it so the summary prints a loud, actionable upgrade warning.
  found_ver="$(grep -- '<!-- planner-kit:BEGIN' "$DST_CLAUDE" | head -n1 | sed -n 's/.*planner-kit:BEGIN \(v[^ ]*\).*/\1/p')"
  if [ -n "$found_ver" ] && [ "$found_ver" != "$KIT_VERSION" ]; then
    CLAUDE_VER_MISMATCH="$found_ver"
    record "CLAUDE.md (root)" "already installed ($found_ver != $KIT_VERSION) — no-op, see WARNING"
  else
    record "CLAUDE.md (root)" "already installed (marker present) — no-op"
  fi
elif [ "$DRY_RUN" = 1 ]; then
  record "CLAUDE.md (root)" "would append behind marker (existing content untouched)"
elif [ "$SRC_CLAUDE" -ef "$DST_CLAUDE" ]; then
  abort "CLAUDE.md source and destination are the same file (\"$DST_CLAUDE\"). Run from your PROJECT ROOT, not from inside the kit."
elif { printf '\n'; emit_block; } >> "$DST_CLAUDE"; then
  record "CLAUDE.md (root)" "appended behind marker (existing content untouched)"
else
  record "CLAUDE.md (root)" "FAILED (append)"
fi

# ---- (c2) .claude/CLAUDE.md pointer stub (only-if-absent) + v1 detection ----
# The stub is a <=2-line note pointing at the ROOT CLAUDE.md. It is seeded ONLY
# if .claude/CLAUDE.md is absent (never overwrite). If .claude/CLAUDE.md EXISTS
# and carries a planner-kit marker, a v1 install put the rules there: flag it so
# the summary can print migration advice. The stub text deliberately contains NO
# "planner-kit:BEGIN" marker, so a fresh install never mis-detects its own stub.
# v1.3: the stub is ONE operative line — the provenance/justification second line was
# slop (it fired at no decision); the pointer itself is the whole job.
emit_pointer() {  # <=2-line pointer stub -> stdout
  printf '%s\n' "# .claude/CLAUDE.md — pointer stub. The front door + rules live in the ROOT ../CLAUDE.md — read that first."
}
if [ -e "$POINTER_CLAUDE" ]; then
  if grep -q -- '<!-- planner-kit:BEGIN' "$POINTER_CLAUDE"; then
    V1_IN_DOTCLAUDE=1
    record ".claude/CLAUDE.md pointer" "v1 block present — see migration note"
  else
    record ".claude/CLAUDE.md pointer" "skipped (exists)"
  fi
elif [ "$DRY_RUN" = 1 ]; then
  record ".claude/CLAUDE.md pointer" "would seed (pointer stub)"
elif mkdir -p "$(dirname "$POINTER_CLAUDE")" && emit_pointer > "$POINTER_CLAUDE"; then
  record ".claude/CLAUDE.md pointer" "seeded (pointer stub)"
else
  record ".claude/CLAUDE.md pointer" "FAILED (write)"
fi

# ---- (d) summary -----------------------------------------------------------
printf '%s\n' "----- planner-kit summary -----"
printf '  %-46s %s\n' "ACTION" "RESULT"
printf '%s' "$SUMMARY"
printf '%s\n' "-------------------------------"

# The refresh backup dir is named ONCE, here, instead of on every refreshed row: an adopter who needs
# it needs the PATH, and repeating it per row would push the table past a readable width. Silent when
# nothing was refreshed — in that case no dir was created at all.
if [ "$REFRESH_BACKUP_MADE" = 1 ]; then
  if [ "$DRY_RUN" = 1 ]; then
    printf '\nrefresh backups WOULD be kept under: %s/%s\n' "$TARGET_DIR" "$REFRESH_BACKUP_REL"
  else
    printf '\nrefresh backups kept under: %s/%s\n' "$TARGET_DIR" "$REFRESH_BACKUP_REL"
    printf '  (each replaced file under its own project-relative path — diff or restore any of them)\n'
  fi
fi

# v1 -> v1.1 migration advice (printed whenever a v1 planner-kit block still lives
# in .claude/CLAUDE.md). Advice only — the installer NEVER moves or edits user content.
if [ "$V1_IN_DOTCLAUDE" = 1 ]; then
  printf '\n'
  printf 'MIGRATION (planner-kit v1 -> v1.1):\n'
  printf '  A v1 planner-kit block was found INSIDE "%s/.claude/CLAUDE.md".\n' "$TARGET_DIR"
  printf '  v1.1 installs the rules at the ROOT front door "%s/CLAUDE.md" instead.\n' "$TARGET_DIR"
  printf '  Your v1 .claude/CLAUDE.md was NOT moved or modified. To finish migrating (optional):\n'
  printf '    1. confirm the root CLAUDE.md now carries the current rules (created/appended above);\n'
  printf '    2. move any of YOUR OWN edits out of the .claude/CLAUDE.md planner-kit:BEGIN..END block;\n'
  printf '    3. replace .claude/CLAUDE.md with a 2-line pointer to ../CLAUDE.md, or delete that block.\n'
  printf '  Nothing breaks if you leave it as-is: Claude Code loads both files.\n'
fi

# Version-mismatch upgrade warning (printed whenever the ROOT CLAUDE.md carries a planner-kit
# block from a DIFFERENT kit version). Advice only — the installer NEVER moves or edits user
# content; the merge stayed a no-op. Without this, an older block reruns as a SILENT no-op while
# a freshly seeded STRUCTURE_RULES.md is left unreferenced by it (or, from a pre-v1.5 block, is
# referenced under the retired STRUCTURE_RULES.machine.md name that this run just migrated away).
if [ -n "$CLAUDE_VER_MISMATCH" ]; then
  printf '\n'
  printf 'WARNING (planner-kit version mismatch):\n'
  printf '  "%s/CLAUDE.md" carries a planner-kit %s block, but this installer is %s.\n' "$TARGET_DIR" "$CLAUDE_VER_MISMATCH" "$KIT_VERSION"
  printf '  The rules merge was a NO-OP: your CLAUDE.md was NOT modified (the installer never\n'
  printf '  rewrites your content). But the older %s block will NOT carry %s references\n' "$CLAUDE_VER_MISMATCH" "$KIT_VERSION"
  printf '  (e.g. the %s pointer, which a pre-v1.5 block still calls %s), so\n' "$STRUCT_DOC_NAME" "$STRUCT_DOC_OLD"
  printf '  %s may now sit UNREFERENCED beside it.\n' "$STRUCT_DOC_NAME"
  printf '  To upgrade to %s: re-run this installer with --upgrade-rules (it replaces the block\n' "$KIT_VERSION"
  printf '  in place, keeping a dated backup of CLAUDE.md first) — or delete the whole\n'
  printf '  "planner-kit:BEGIN %s ... planner-kit:END" block by hand and re-run without flags.\n' "$CLAUDE_VER_MISMATCH"
fi

if [ "$DRY_RUN" = 1 ]; then
  printf '\ndry-run: nothing was written. Re-run without --dry-run to apply.\n'
elif [ "$FULL" = 1 ]; then
  printf '\ndone (full). Rules front door: %s/CLAUDE.md; folder contract: %s/%s.\n' "$TARGET_DIR" "$TARGET_DIR" "$STRUCT_DOC_NAME"
  printf 'Re-running is safe: your files are never overwritten (seeds skip existing ones; CLAUDE.md is a no-op once the marker is present);\n'
  printf 'kit-owned files (hooks, agents, model-verification, dev/tools) refresh only when they DIFFER, and the replaced copy is backed up first.\n'
else
  printf '\ndone (minimal). Root files: %s/CLAUDE.md + %s/%s (pointer stub at .claude/CLAUDE.md).\n' "$TARGET_DIR" "$TARGET_DIR" "$STRUCT_DOC_NAME"
  printf 'Workflow hooks live in .claude/hooks/ and are registered in .claude/settings.json; PLANNER_KIT_HOOKS=off silences the advisory ones, CRT_MODE=off the deny gate.\n'
  printf 'Check them any time: bash dev/tools/test_enforcement_e2e.sh (red-teams the installed gates; arms needing a surface you do not have print SKIP, not FAIL).\n'
  printf 'The folder tree is materialized on demand per %s. Want the classic tree up front? Re-run with --full.\n' "$STRUCT_DOC_NAME"
  printf 'Re-running is safe: your files are never overwritten (%s + seeds skip existing ones; CLAUDE.md is a no-op once the marker is present);\n' "$STRUCT_DOC_NAME"
  printf 'kit-owned files (hooks, agents, model-verification, dev/tools) refresh only when they DIFFER, and the replaced copy is backed up first.\n'
fi
exit 0
