#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# planner-kit installer (v1.4) — LAZY-SCAFFOLD: minimal by default, --full for the classic tree.
# Idempotent & non-destructive: a re-run changes nothing it already did; ZERO deletes, ZERO overwrites
# (the ONE deliberate exception: --upgrade-rules rewrites the planner-kit block inside the root
#  CLAUDE.md IN PLACE, after keeping a dated backup — everything outside the block stays byte-untouched).
#
# Run FROM your PROJECT ROOT (not from inside the kit):
#     cd /your/project && bash /path/to/planner-kit/install.sh [--full] [--dry-run]
#
# TWO MODES:
#   DEFAULT (minimal) — install ONLY the two front-door files at the project root:
#       (1) root CLAUDE.md  and  (2) STRUCTURE_RULES.machine.md — plus the two advisory
#       workflow hooks + their .claude/settings.json registration, and the model-routing set
#       (two executor agents + the model-verification skill; see BOTH MODES below).
#     The folder tree is NOT pre-created; the agent materializes each folder ON DEMAND per
#     STRUCTURE_RULES.machine.md (a folder's absence = not yet needed, never an error). This
#     removes the speculative clutter of pre-creating folders a given project never uses.
#   --full — the classic layout up front: scaffold the whole standard tree (mkdir -p; idempotent)
#     + a .gitkeep in each created dir that stays empty + seed the ledger/memory/tool templates
#     (only-if-absent), PLUS STRUCTURE_RULES.machine.md. Same outcome as v1.1 + the structure doc.
#
# BOTH MODES do (mechanism unchanged from v1.1):
#   (c) ROOT CLAUDE.md: create if absent (payload rules wrapped in planner-kit markers), else append
#       the rules block behind a marker if not already present, else no-op ("already installed"). Also
#       seed .claude/CLAUDE.md as a <=2-line pointer stub to the root file, only if absent. If a
#       planner-kit marker is found INSIDE .claude/CLAUDE.md (a v1 install put the rules there) print
#       migration advice — never auto-move user content.
#   Seed STRUCTURE_RULES.machine.md (only-if-absent), recording THIS kit's absolute path into its SEEDS
#       section so an on-demand materialization can find the seed templates later.
#   Install the two advisory workflow hooks into .claude/hooks/ (mode 755) and register them in
#       .claude/settings.json: seeded when absent, else DEEP-MERGED via lib/merge_settings.py so
#       your own settings and any foreign hook survive intact (a dated backup is kept before the
#       first merge). Both hooks advise only — neither ever refuses an action.
#   Seed the MODEL-ROUTING capability set (v1.4/K10, only-if-absent): .claude/agents/
#       {fable-executor,opus5-executor}.md (the two constructed model routes) and
#       .claude/skills/model-verification/ (the serving-stamp audit skill + instrument) — so a
#       fresh project can both KNOW the model-control doctrine (CLAUDE.md) and DO it.
#   (d) print a did/skipped summary.
#   (e) ZERO deletes, ZERO overwrites — a re-run changes nothing it already did. .DS_Store is never copied.
#
# --upgrade-rules (v1.4) — UPGRADE an already-installed project: replace the FIRST
#   `<!-- planner-kit:BEGIN … -->` … `<!-- planner-kit:END -->` span inside the root CLAUDE.md with
#   this kit's current marker-wrapped rules block, IN PLACE. A dated backup of CLAUDE.md is kept
#   FIRST; every byte outside the span is untouched. REFUSES when no planner-kit block exists
#   (upgrade ≠ install — run without the flag to install). Without this flag the merge stays the
#   never-overwrite no-op it has always been.
# --dry-run composes with all modes (prints actions, writes nothing). -h/--help documents all flags.
#
# Portability: bash 3.2+ (macOS default); no `timeout`; no GNU-only flags; no realpath / readlink -f.
# `set -u` + pipefail catch real bugs; `set -e` is deliberately NOT used, so one skipped/failed file is
# logged and never aborts the rest (fail-open on non-critical steps). Quote every path — paths may hold spaces.

set -u
set -o pipefail

KIT_VERSION="v1.4"

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
  (default)   MINIMAL install: root CLAUDE.md + STRUCTURE_RULES.machine.md, plus the two
              advisory workflow hooks + their .claude/settings.json registration, and the
              model-routing set (.claude/agents/ executors + .claude/skills/model-verification).
              The folder tree is materialized ON DEMAND per STRUCTURE_RULES.machine.md
              (a folder's absence = not yet needed, never an error).
  --full      CLASSIC install: pre-scaffold the whole standard tree + .gitkeeps + seed all
              ledger/memory/tool templates, PLUS STRUCTURE_RULES.machine.md.
  --upgrade-rules
              UPGRADE an installed project: replace the existing planner-kit rules block in
              the root CLAUDE.md with this kit's current block, in place (dated backup kept
              first; every byte outside the block untouched). Refuses when no block exists.
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

seed_structure_doc() {  # seed STRUCTURE_RULES.machine.md, recording THIS kit's abs path into its SEEDS section.
  # Runs in BOTH modes (it is half of the minimal two-file default). Seed-if-absent, never overwrite.
  # The payload doc's placeholder line "@@KIT_SEED_PATH@@" becomes a "KIT_PATH=<abs path>" line so a later
  # on-demand materialization can find the seed templates. The path is passed via the ENVIRONMENT and read
  # with awk ENVIRON[] so awk applies NO escape processing to it (spaces / backslashes survive verbatim).
  # Same non-atomicity as the CLAUDE.md create path (direct redirect); guarded by the seed-if-absent check
  # above, so it can never truncate an existing file, and it never runs when src -ef dst (target-inside-kit
  # is already aborted in preconditions).
  local src="$PAYLOAD_DIR/STRUCTURE_RULES.machine.md"
  local dst="$TARGET_DIR/STRUCTURE_RULES.machine.md"
  if [ ! -f "$src" ]; then
    record "STRUCTURE_RULES.machine.md" "SKIPPED (no payload source)"
  elif [ -e "$dst" ]; then
    record "STRUCTURE_RULES.machine.md" "skipped (exists)"
  elif [ "$DRY_RUN" = 1 ]; then
    record "STRUCTURE_RULES.machine.md" "would seed (kit path recorded)"
  elif PK_KIT_DIR="$KIT_DIR" awk '
         $0 == "@@KIT_SEED_PATH@@" { print "KIT_PATH=" ENVIRON["PK_KIT_DIR"]; next }
         { print }
       ' "$src" > "$dst"; then
    record "STRUCTURE_RULES.machine.md" "seeded (kit path recorded)"
  else
    record "STRUCTURE_RULES.machine.md" "FAILED (write)"
  fi
}

# ---- hooks + settings (BOTH modes; default-on) ------------------------------
HOOK_NAMES="brief_gate.sh collect_outcome_gate.sh"     # fixed names, no spaces => word-split is safe
HOOKS_SRC_DIR="$PAYLOAD_DIR/.claude/hooks"
SETTINGS_SRC="$PAYLOAD_DIR/.claude/settings.json"
SETTINGS_DST="$TARGET_DIR/.claude/settings.json"
MERGE_TOOL="$KIT_DIR/lib/merge_settings.py"

seed_hook() {  # seed_hook NAME — only-if-absent, executable at copy time.
  # `install -m 755` sets the mode AS PART of the copy, so the hook is runnable even where a
  # separate chmod is denied. Fall back to a plain cp (portable everywhere) and SAY SO, rather
  # than failing: a copied-but-unmarked hook is fixable, a missing hook is not.
  local name="$1" src="$HOOKS_SRC_DIR/$1" dst="$TARGET_DIR/.claude/hooks/$1"
  if [ ! -f "$src" ]; then
    record "hook .claude/hooks/$name" "SKIPPED (no payload source)"
  elif [ -e "$dst" ]; then
    record "hook .claude/hooks/$name" "skipped (exists)"
  elif [ "$DRY_RUN" = 1 ]; then
    record "hook .claude/hooks/$name" "would install (mode 755)"
  elif mkdir -p "$(dirname "$dst")" && install -m 755 "$src" "$dst" 2>/dev/null; then
    record "hook .claude/hooks/$name" "installed (mode 755)"
  elif cp "$src" "$dst" 2>/dev/null; then
    record "hook .claude/hooks/$name" "copied (not marked +x — chmod it if it never fires)"
  else
    record "hook .claude/hooks/$name" "FAILED (copy)"
  fi
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

# ---- (a/b/b2) FULL-mode scaffold + seed + gitkeep --------------------------
# Minimal (default) mode SKIPS this whole block: it pre-creates NO folders and seeds NO templates.
# The agent materializes each folder on demand per STRUCTURE_RULES.machine.md. --full lays down the
# classic v1.1 tree up front. Both modes still install STRUCTURE_RULES.machine.md + CLAUDE.md below.
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
  seed_glob "$PAYLOAD_DIR/dev/tools"  "dev/tools"
  seed_glob "$PAYLOAD_DIR/.claude/agent-memory/planner" ".claude/agent-memory/planner"

  # (b2) .gitkeep every created dir that stayed empty (after seeding)
  for d in $SCAFFOLD_DIRS; do
    gitkeep_if_empty "$d"
  done
fi

# ---- STRUCTURE_RULES.machine.md (BOTH modes — the other half of the minimal default) ----
seed_structure_doc

# ---- hooks + their registration (BOTH modes — the workflow backstop is default-on) ----
for h in $HOOK_NAMES; do
  seed_hook "$h"
done
seed_settings

# ---- model-routing capability set (BOTH modes; v1.4/K10) --------------------
# The two executor agents (the constructed model routes) + the model-verification skill
# (the serving-stamp audit) ship with the kit so a fresh project can both KNOW the
# model-control doctrine in CLAUDE.md and DO it. Only-if-absent, like every seed;
# seed_glob is non-recursive, so each payload subdir gets its own call.
seed_glob "$PAYLOAD_DIR/.claude/agents" ".claude/agents"
seed_glob "$PAYLOAD_DIR/.claude/skills/model-verification" ".claude/skills/model-verification"

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
  # carry this version's references (e.g. the STRUCTURE_RULES.machine.md pointer added in v1.2),
  # so a freshly seeded STRUCTURE_RULES can sit unreferenced beside an older block. Extract the
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
# a freshly seeded STRUCTURE_RULES.machine.md is left unreferenced by it.
if [ -n "$CLAUDE_VER_MISMATCH" ]; then
  printf '\n'
  printf 'WARNING (planner-kit version mismatch):\n'
  printf '  "%s/CLAUDE.md" carries a planner-kit %s block, but this installer is %s.\n' "$TARGET_DIR" "$CLAUDE_VER_MISMATCH" "$KIT_VERSION"
  printf '  The rules merge was a NO-OP: your CLAUDE.md was NOT modified (the installer never\n'
  printf '  rewrites your content). But the older %s block will NOT carry %s references\n' "$CLAUDE_VER_MISMATCH" "$KIT_VERSION"
  printf '  (e.g. the STRUCTURE_RULES.machine.md pointer), so a freshly seeded\n'
  printf '  STRUCTURE_RULES.machine.md may now sit UNREFERENCED beside it.\n'
  printf '  To upgrade to %s: re-run this installer with --upgrade-rules (it replaces the block\n' "$KIT_VERSION"
  printf '  in place, keeping a dated backup of CLAUDE.md first) — or delete the whole\n'
  printf '  "planner-kit:BEGIN %s ... planner-kit:END" block by hand and re-run without flags.\n' "$CLAUDE_VER_MISMATCH"
fi

if [ "$DRY_RUN" = 1 ]; then
  printf '\ndry-run: nothing was written. Re-run without --dry-run to apply.\n'
elif [ "$FULL" = 1 ]; then
  printf '\ndone (full). Rules front door: %s/CLAUDE.md; folder contract: %s/STRUCTURE_RULES.machine.md.\n' "$TARGET_DIR" "$TARGET_DIR"
  printf 'Re-running is safe: seeds skip existing files; CLAUDE.md is a no-op once the marker is present.\n'
else
  printf '\ndone (minimal). Root files: %s/CLAUDE.md + %s/STRUCTURE_RULES.machine.md (pointer stub at .claude/CLAUDE.md).\n' "$TARGET_DIR" "$TARGET_DIR"
  printf 'Advisory hooks live in .claude/hooks/ and are registered in .claude/settings.json; PLANNER_KIT_HOOKS=off silences them.\n'
  printf 'The folder tree is materialized on demand per STRUCTURE_RULES.machine.md. Want the classic tree up front? Re-run with --full.\n'
  printf 'Re-running is safe: STRUCTURE_RULES + seeds skip existing files; CLAUDE.md is a no-op once the marker is present.\n'
fi
exit 0
