#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# install.sh — install the Claude Research Toolkit into ~/.claude/ (global; loads for EVERY session).
# Idempotent · tiered · backs up before any write · deep-merges settings.json (never clobbers).
# Runs from a plain shell (NOT Claude's Bash tool), so the safety deny-list it installs does not block it.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PAYLOAD="$SCRIPT_DIR/payload"
PAYLOAD_PROJECT="$SCRIPT_DIR/payload-project"     # project-specialty carriers (routed per-project, never into ~/.claude)
PROJECT_MANIFEST="$PAYLOAD_PROJECT/project_manifest.tsv"
# The fillable project-routes MASTER lives IN THE BUNDLE (repo-owned, authoritative). It ships BLANK;
# the user fills it once, here, and install APPLIES it. CRT_ROUTES_MASTER overrides the path (testing).
ROUTES_MASTER="${CRT_ROUTES_MASTER:-$PAYLOAD_PROJECT/project_routes.tsv}"
LIB="$SCRIPT_DIR/lib"
CLAUDE_DIR="${CLAUDE_HOME:-$HOME/.claude}"        # CLAUDE_HOME override aids testing
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP="$CLAUDE_DIR/backups/pre-toolkit-$TS"

usage() {
  cat <<'U'
install.sh [tiers] [options]
  Tiers (NO tier flag => --core --ergonomics --memories):
    --core        rules, skills, agents, methodology docs, global CLAUDE.md, 9 dev hooks (incl. ambient-time, claim-verify-guard, plan-routing-gate), permissions.deny
    --ergonomics  xbeep beep hooks + /xbeep command + beep registrations
    --memories    append the folded feedback/preference block to the global CLAUDE.md
    --personal    your personal defaults (model=claude-fable-5[1m], theme, tui, effort=max, alwaysThinking, plugin, default persona=planner)
    --all         every tier (core + ergonomics + memories + personal)   <- full replica of the source setup
  Selection (default: install ALL skills+agents; these narrow to a coupled subset):
    --select LIST         comma-list of agents and/or skills; installs each PLUS its manifest
                          closure (an agent pulls its required skills). Fail-closed on unknown names.
    --manifest-subset F   install exactly the names listed in file F (one per line; # comments ok)
    --allow-deferred      permit selecting a DEFERRED-tier skill (baton/folio); off by default
    --root DIR            per-root scoping: install into DIR instead of ~/.claude (repo-local toolkit)
    --discipline-trees M  M=auto|copy|skip (default auto). Controls the always-on discipline trees
                          (rules/ methodology/ docs/). auto: copy them EXCEPT in a stacked --root
                          install that already inherits a global ~/.claude/rules (skip → avoid an
                          unguarded project-local shadow of the global rules). copy: always copy
                          (self-contained/portable root — the escape hatch). skip: never copy.
                          A global (~/.claude) install ALWAYS copies them regardless of M.
  Interactive:
    --interactive, -i     numbered-menu front-end: interactively pick components (drives --select)
                          and scope (global, then optional per-root sets drive --root/--discipline-trees).
                          Composes + runs one install.sh call per scope pass. Combine with --dry-run to preview.
  Project routing (route project-specialty items to a project's OWN .claude/, not ~/.claude):
    --project-items LIST  comma-list of project-specialty item names from payload-project/ (agents
                          and/or skills), validated against payload-project/project_manifest.tsv.
                          Unknown name => fail-closed (exit 2, NOTHING written). Requires --project-dest.
    --project-dest DIR    the project root; each item installs into DIR/.claude/{agents,skills}/
                          (mkdir -p; any pre-existing same-name target is backed up first). Usable
                          ALONE or alongside tiers: general tiers install to ~/.claude, while project-
                          specialty items route per project (their tokens are project-specific by
                          design and never enter the general payload).
    --project-bundle LIST comma-list of BUNDLE names (project_manifest.tsv col 6). Expands to every member
                          item, then behaves like --project-items (requires --project-dest; unknown bundle
                          => exit 2, NOTHING written, valid names listed). Unioned with --project-items.
    --apply-project-routes  route every bundle declared in the fillable MASTER that ships in the bundle,
                          payload-project/project_routes.tsv, to its project root(s). That repo master is
                          authoritative (edit it there); it ships BLANK. Rows are `bundle<TAB>dest` (leading
                          ~ expanded; one bundle may have many dest rows). Every row is validated (unknown
                          bundle / missing dest dir => exit 2, nothing written) before any routing. A tier
                          install AUTO-applies the master when it has active rows, so this flag is the
                          explicit on-demand trigger (usable alone or with tiers). On apply, ~/.claude/
                          project_routes.tsv is (over)written as a DERIVED applied-record (a receipt, read
                          by nothing). Honors --dry-run; re-runs idempotent. Deleting a master row stops
                          future refreshes (already-placed items stay).
  Options:
    --dry-run     print actions, write nothing
    --no-verify   skip the scrub_verify.sh + doc-status + coupling gates
    -h, --help
U
}

CORE=0; ERGO=0; MEM=0; PERSONAL=0; DRY=0; VERIFY=1
SELECT=""; SUBSET=""; ALLOW_DEFERRED=0; ROOT=""; DISCIPLINE_MODE=auto; INTERACTIVE=0
PROJECT_ITEMS=""; PROJECT_DEST=""; PROJECT_BUNDLES=""; APPLY_ROUTES=0
while [ $# -gt 0 ]; do
  case "$1" in
    --core) CORE=1;; --ergonomics) ERGO=1;; --memories) MEM=1;; --personal) PERSONAL=1;;
    --all) CORE=1; ERGO=1; MEM=1; PERSONAL=1;;
    --select) SELECT="$2"; CORE=1; shift;;
    --manifest-subset) SUBSET="$2"; CORE=1; shift;;
    --allow-deferred) ALLOW_DEFERRED=1;;
    --root) ROOT="$2"; shift;;
    --discipline-trees|--discipline)
      DISCIPLINE_MODE="$2"; shift
      case "$DISCIPLINE_MODE" in auto|copy|skip) ;; *) echo "error: --discipline-trees must be auto|copy|skip (got '$DISCIPLINE_MODE')" >&2; exit 2;; esac;;
    --project-items) PROJECT_ITEMS="$2"; shift;;
    --project-dest)  PROJECT_DEST="$2"; shift;;
    --project-bundle) PROJECT_BUNDLES="$2"; shift;;
    --apply-project-routes) APPLY_ROUTES=1;;
    --interactive|-i) INTERACTIVE=1;;
    --dry-run) DRY=1;; --no-verify) VERIFY=0;;
    -h|--help) usage; exit 0;;
    *) echo "unknown arg: $1" >&2; usage; exit 2;;
  esac; shift
done

# ── INTERACTIVE FRONT-END (--interactive|-i) ─────────────────────────────────
# A THIN DRIVER, not a second installer. It runs the numbered-menu picker
# (lib/interactive_select.py), which composes install.sh arg-lines (one per scope pass) and prints
# them on its stdout; the driver then re-execs THIS script once per line. The picker adds no copy
# logic — every actual install goes through the normal (non-interactive) path below, so --dry-run,
# the shadow guard, coupling gate, and discipline auto all behave identically to a hand-typed call.
# Menus/prompts go to stderr and the picker reads our stdin, so piping a canned selection (CI / §6
# tests) drives the exact same arg-lines as an interactive tty (no hang: EOF terminates the loop).
if [ "$INTERACTIVE" = 1 ]; then
  # Fail-closed on mis-invocation: --interactive COMPOSES its own tier/selection/root flags per pass,
  # so combining it with hand-typed ones would silently drop the user's intent. Reject instead.
  if [ "$CORE" = 1 ] || [ "$ERGO" = 1 ] || [ "$MEM" = 1 ] || [ "$PERSONAL" = 1 ] \
     || [ -n "$SELECT" ] || [ -n "$SUBSET" ] || [ -n "$ROOT" ] || [ "$ALLOW_DEFERRED" = 1 ] \
     || [ -n "$PROJECT_ITEMS" ] || [ -n "$PROJECT_DEST" ] || [ -n "$PROJECT_BUNDLES" ] || [ "$APPLY_ROUTES" = 1 ] \
     || [ "$DISCIPLINE_MODE" != auto ]; then
    echo "error: --interactive composes its own tier/selection/root/routing flags per pass; do not combine it with" >&2
    echo "       --core/--ergonomics/--memories/--personal/--all/--select/--manifest-subset/--root/--allow-deferred/" >&2
    echo "       --discipline-trees/--project-items/--project-dest/--project-bundle/--apply-project-routes. (--dry-run and --no-verify ARE allowed.)" >&2
    exit 2
  fi
  _picker="$LIB/interactive_select.py"
  [ -f "$_picker" ] || { echo "FATAL: interactive front-end not found: $_picker" >&2; exit 1; }
  _prc=0
  _lines="$(python3 "$_picker" --manifest "$PAYLOAD/coupling_manifest_v1.tsv" --resolver "$LIB/select_resolve.py" \
            --project-manifest "$PROJECT_MANIFEST" --routes-file "$ROUTES_MASTER")" || _prc=$?
  if [ "$_prc" -ne 0 ]; then
    echo "interactive selection aborted (exit $_prc) — nothing installed." >&2
    exit "$_prc"
  fi
  if [ -z "$_lines" ]; then
    echo "interactive selection produced no invocations — nothing installed." >&2
    exit 1
  fi
  SELF="$SCRIPT_DIR/$(basename -- "${BASH_SOURCE[0]}")"
  _n=0
  while IFS= read -r _line; do
    [ -z "$_line" ] && continue
    _n=$((_n + 1))
    echo "== interactive install $_n: install.sh $_line ==" >&2
    eval "set -- $_line"   # re-split the shlex-quoted arg-line into argv (root DIRs w/ spaces survive)
    # forward only the passthrough flags that apply per-invocation (avoids bash 3.2 empty-array trap).
    # `</dev/null` severs each child's stdin from the heredoc feed: without it a future install.sh step
    # that reads stdin would consume the loop's remaining arg-lines and silently drop invocations.
    if   [ "$DRY" = 1 ] && [ "$VERIFY" = 0 ]; then bash "$SELF" "$@" --dry-run --no-verify </dev/null
    elif [ "$DRY" = 1 ];                       then bash "$SELF" "$@" --dry-run </dev/null
    elif [ "$VERIFY" = 0 ];                    then bash "$SELF" "$@" --no-verify </dev/null
    else                                            bash "$SELF" "$@" </dev/null
    fi
  done <<EOF
$_lines
EOF
  exit 0
fi
# DEFAULT: if no component-selecting flag was given (only --root/--dry-run/--no-verify or nothing),
# install the standard set (core+ergonomics+memories). A selection (--select/--manifest-subset) sets
# CORE=1 itself, so it is excluded here. --project-items is ALSO excluded: a pure project-routing call
# routes ONLY to the named project (no implicit ~/.claude install). This must run AFTER parsing so
# `--root DIR` alone still installs the full set (the earlier `$#-eq 0` test wrongly treated `--root DIR` as an explicit selection).
if [ "$CORE" = 0 ] && [ "$ERGO" = 0 ] && [ "$MEM" = 0 ] && [ "$PERSONAL" = 0 ] && [ -z "$SELECT" ] && [ -z "$SUBSET" ] && [ -z "$PROJECT_ITEMS" ] && [ -z "$PROJECT_BUNDLES" ] && [ "$APPLY_ROUTES" = 0 ]; then
  CORE=1; ERGO=1; MEM=1
fi
[ "$MEM" = 1 ] && CORE=1   # memories append to the core CLAUDE.md, which must exist
# --root: per-root scoping — install into a repo-local dir instead of the global ~/.claude
[ -n "$ROOT" ] && CLAUDE_DIR="$ROOT"
BACKUP="$CLAUDE_DIR/backups/pre-toolkit-$TS"   # recompute after any --root override
ROUTES_RECORD="$CLAUDE_DIR/project_routes.tsv"                     # DERIVED applied-record (a receipt; overwritten from the master on apply; read by nothing)
[ -n "$SELECT" ] && [ -n "$SUBSET" ] && { echo "error: --select and --manifest-subset are mutually exclusive" >&2; exit 2; }

# CLI project routing (--project-items and/or --project-bundle) requires --project-dest, and a bare
# --project-dest with no routing request is an error. (--apply-project-routes carries its own dests
# from the repo project-routes master, so it does NOT require --project-dest.)
_routing_req=0
{ [ -n "$PROJECT_ITEMS" ] || [ -n "$PROJECT_BUNDLES" ]; } && _routing_req=1
if { [ "$_routing_req" = 1 ] && [ -z "$PROJECT_DEST" ]; } || { [ "$_routing_req" = 0 ] && [ -n "$PROJECT_DEST" ]; }; then
  echo "error: project routing (--project-items/--project-bundle) and --project-dest must be given together (got only one)" >&2; exit 2
fi
# ANY_TIER: did the user ask for a ~/.claude tier install at all? A PURE project-routing call
# (--project-items with no tier) must NOT create the ~/.claude backup / managed-set snapshot below.
ANY_TIER=0
if [ "$CORE" = 1 ] || [ "$ERGO" = 1 ] || [ "$MEM" = 1 ] || [ "$PERSONAL" = 1 ]; then ANY_TIER=1; fi

# ── SHADOW GUARD ─────────────────────────────────────────────────────────────
# A repo-local (--root) install STACKS on top of the global ~/.claude — BOTH load (per the toolkit's
# own extension-architecture invariant: scope==location, project scope ADDS to the user baseline).
# So a selective repo-local install does NOT replace the global set; the user still sees global
# skills/agents, and any name present in BOTH scopes is an ambiguous shadow. We refuse to create a
# genuine name-collision shadow silently (fail-closed); a pure stack (no name collision) only warns.
GLOBAL_DIR="${CLAUDE_HOME:-$HOME/.claude}"
if [ -n "$ROOT" ] && [ "$CLAUDE_DIR" != "$GLOBAL_DIR" ] && [ -d "$GLOBAL_DIR/skills" -o -d "$GLOBAL_DIR/agents" ]; then
  echo "SHADOW GUARD: a global toolkit exists at $GLOBAL_DIR"
  echo "  A --root install at $CLAUDE_DIR STACKS on top of it — BOTH sets load in that repo."
  # find name collisions between what WILL be installed here and what already exists globally
  # (approximate the install set: for a selection, the resolved names; else the full payload set)
  _pending_skills="$(ls "$PAYLOAD/skills" 2>/dev/null)"
  if [ -n "$SELECT" ] || [ -n "$SUBSET" ]; then
    _sel_args=(--manifest "$PAYLOAD/coupling_manifest_v1.tsv")
    [ -n "$SELECT" ] && _sel_args+=(--select "$SELECT"); [ -n "$SUBSET" ] && _sel_args+=(--manifest-subset "$SUBSET")
    [ "$ALLOW_DEFERRED" = 1 ] && _sel_args+=(--allow-deferred)
    _pending_skills="$(python3 "$LIB/select_resolve.py" "${_sel_args[@]}" 2>/dev/null | awk '/==SKILLS==/{f=1;next} /==AGENTS==/{f=0} f')"
  fi
  _collisions=""
  for s in $_pending_skills; do
    [ -d "$GLOBAL_DIR/skills/$s" ] && _collisions="$_collisions $s"
  done
  if [ -n "$_collisions" ]; then
    echo "  NAME COLLISIONS (same skill in both scopes — ambiguous which wins):$_collisions"
    if [ "${FORCE_SHADOW:-0}" != 1 ]; then
      echo "  REFUSING to create an ambiguous shadow. Re-run with FORCE_SHADOW=1 to override,"
      echo "  or install a DISJOINT selection, or install globally (no --root)."
      exit 3
    fi
    echo "  FORCE_SHADOW=1 set — proceeding despite collisions."
  else
    echo "  (no name collisions — clean stack; repo-local names are additive to the global set.)"
  fi
fi

log(){ printf '  %s\n' "$*"; }
run(){ if [ "$DRY" = 1 ]; then printf 'DRYRUN:'; printf ' %q' "$@"; echo; else "$@"; fi; }

# ── project-specialty routing helpers (payload-project/ -> a project's OWN .claude/) ──────────
# project_manifest_kind NAME -> prints the kind (agent|skill) for NAME from project_manifest.tsv, or
#   nothing if NAME is not a listed item. Skips `#` comment lines and the header row (col1 == "name").
project_manifest_kind(){
  [ -f "$PROJECT_MANIFEST" ] || return 0
  awk -F'\t' -v want="$1" '
    /^[[:space:]]*#/ { next } NF==0 { next } $1=="name" { next }
    $1==want { print $2; exit }
  ' "$PROJECT_MANIFEST"
}
# project_manifest_names -> every valid item name (one per line), for error/usage listings.
project_manifest_names(){
  [ -f "$PROJECT_MANIFEST" ] || return 0
  awk -F'\t' '/^[[:space:]]*#/ { next } NF==0 { next } $1=="name" { next } { print $1 }' "$PROJECT_MANIFEST"
}
# project_manifest_bundles -> every distinct bundle name (col 6), one per line (error listings + picker).
project_manifest_bundles(){
  [ -f "$PROJECT_MANIFEST" ] || return 0
  awk -F'\t' '/^[[:space:]]*#/ { next } NF==0 { next } $1=="name" { next } $6!="" { print $6 }' "$PROJECT_MANIFEST" | LC_ALL=C sort -u
}
# project_manifest_items_for_bundle NAME -> item names (col 1) whose bundle (col 6) == NAME, one per line
#   (empty output => NAME is not a known bundle; callers treat that as fail-closed).
project_manifest_items_for_bundle(){
  [ -f "$PROJECT_MANIFEST" ] || return 0
  awk -F'\t' -v want="$1" '/^[[:space:]]*#/ { next } NF==0 { next } $1=="name" { next } $6==want { print $1 }' "$PROJECT_MANIFEST"
}
# _bundle_missing_srcs NAME -> print " item" for each bundle member whose payload-project/ source is absent
#   (a packaging defect; keeps apply_project_routes fail-closed rather than aborting mid-copy under set -e).
_bundle_missing_srcs(){
  local m k out=""
  while IFS= read -r m; do
    [ -z "$m" ] && continue
    k="$(project_manifest_kind "$m")"
    if [ "$k" = agent ] && [ ! -f "$PAYLOAD_PROJECT/agents/$m.md" ]; then out="$out $m"; fi
    if [ "$k" = skill ] && [ ! -d "$PAYLOAD_PROJECT/skills/$m" ];   then out="$out $m"; fi
  done <<EOF
$(project_manifest_items_for_bundle "$1")
EOF
  printf '%s' "$out"
}
# route_project_items $1=comma-list-of-item-names $2=project-dest-root — copy each requested payload-project/
#   item into <dest>/.claude/, backing up any pre-existing same-name target FIRST (into
#   .claude/backups/pre-project-$TS/). Additive + idempotent (a re-run overwrites with byte-identical source;
#   the skill copy uses the `src/.` contents form so a re-run never nests). Honors --dry-run via run(). Names
#   are pre-validated in preflight. Called by the CLI path AND once per row by apply_project_routes.
route_project_items(){
  local items="$1" dest="$2"
  local dest_root="$dest/.claude"
  local pbackup="$dest_root/backups/pre-project-$TS"
  log "[project] routing specialty items -> $dest_root"
  local item kind _nl
  _nl="$(printf '%s' "$items" | tr ',' '\n')"
  while IFS= read -r item; do
    item="$(printf '%s' "$item" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [ -z "$item" ] && continue
    kind="$(project_manifest_kind "$item")"
    if [ "$kind" = agent ]; then
      if [ -f "$dest_root/agents/$item.md" ]; then      # back up a pre-existing target FIRST
        run mkdir -p "$pbackup/agents"; run cp -R "$dest_root/agents/$item.md" "$pbackup/agents/"
        log "  backed up existing agents/$item.md -> $pbackup/agents/"
      fi
      run mkdir -p "$dest_root/agents"
      run cp "$PAYLOAD_PROJECT/agents/$item.md" "$dest_root/agents/"; log "  +agent $item"
    elif [ "$kind" = skill ]; then
      if [ -d "$dest_root/skills/$item" ]; then          # back up a pre-existing target FIRST
        run mkdir -p "$pbackup/skills"; run cp -R "$dest_root/skills/$item" "$pbackup/skills/"
        log "  backed up existing skills/$item/ -> $pbackup/skills/"
      fi
      run mkdir -p "$dest_root/skills/$item"
      run cp -R "$PAYLOAD_PROJECT/skills/$item/." "$dest_root/skills/$item/"; log "  +skill $item"
    fi
  done <<EOF
$_nl
EOF
}

# ── project-routes MASTER helpers (the bundle -> project-dest map lives in the bundle: $ROUTES_MASTER) ──
# read_routes_active FILE — emit one `bundle<TAB>expanded_dest` line per ACTIVE row of FILE (skips `#`
#   comments + blank lines; trims surrounding whitespace on each field; expands a leading `~`/`~/` in the
#   dest to $HOME at read time). Internal spaces in a dest path are preserved (project dirs have spaces).
#   Parameterized on the file so it reads the repo master (and, in tests, a CRT_ROUTES_MASTER override).
read_routes_active(){
  local _f="$1"
  [ -f "$_f" ] || return 0
  awk -F'\t' -v home="$HOME" '
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    {
      b=$1; d=$2
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", b)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", d)
      if (b=="") next
      if (d=="~") d=home
      else if (substr(d,1,2)=="~/") d=home substr(d,2)
      printf "%s\t%s\n", b, d
    }
  ' "$_f"
}
# write_routes_record ROWS — write the DERIVED applied-record to $ROUTES_RECORD (~/.claude): a receipt of
#   what was just applied, overwritten on every apply and READ BY NOTHING. It is NOT a second master —
#   its header points back at the repo master as the one thing to edit. Honors --dry-run.
write_routes_record(){
  local _rows="$1"
  if [ "$DRY" = 1 ]; then log "DRYRUN: write derived applied-record -> $ROUTES_RECORD"; return 0; fi
  run mkdir -p "$CLAUDE_DIR"
  { printf '# project_routes.tsv — DERIVED APPLIED-RECORD (do NOT edit; overwritten on every apply).\n'
    printf '# The authoritative master is payload-project/project_routes.tsv in the toolkit repo — edit\n'
    printf '# THAT, then re-run: install.sh --apply-project-routes\n'
    printf '# Applied %s. Rows below are the bundle<TAB>dest routes applied this run (~ already expanded).\n' "$TS"
    printf '%s\n' "$_rows"
  } > "$ROUTES_RECORD"
  log "[routes] wrote derived applied-record -> $ROUTES_RECORD"
}
# validate_routes_master — READ-ONLY fail-closed validation of the project-routes master's ACTIVE rows:
#   unknown bundle / nonexistent dest dir / missing member source => print the offending row(s) + exit 2.
#   A blank or absent master passes (return 0; nothing to validate). Runs BOTH in PREFLIGHT (so an invalid
#   master aborts the WHOLE command before any tier write — atomic) AND as apply_project_routes' PHASE 1
#   (ONE definition of the rules, reused — never duplicated).
validate_routes_master(){
  [ -f "$ROUTES_MASTER" ] || return 0
  local active; active="$(read_routes_active "$ROUTES_MASTER")"
  [ -n "$active" ] || return 0
  local _tab; _tab="$(printf '\t')"
  local bad="" _b _d _miss
  while IFS="$_tab" read -r _b _d; do
    [ -z "$_b" ] && continue
    if [ -z "$(project_manifest_items_for_bundle "$_b")" ]; then bad="$bad
  unknown bundle '$_b' -> '$_d'"; continue; fi
    if [ ! -d "$_d" ]; then bad="$bad
  dest does not exist: '$_d' (bundle '$_b')"; continue; fi
    _miss="$(_bundle_missing_srcs "$_b")"
    [ -n "$_miss" ] && bad="$bad
  missing source(s) for bundle '$_b':$_miss"
  done <<EOF
$active
EOF
  if [ -n "$bad" ]; then
    echo "error: invalid route(s) in the project-routes master $ROUTES_MASTER (nothing written):" >&2
    printf '%s\n' "$bad" >&2
    echo "       valid bundles: $(project_manifest_bundles | tr '\n' ' ')" >&2
    exit 2
  fi
  return 0
}
# apply_project_routes — route every ACTIVE row of the repo MASTER ($ROUTES_MASTER). Validate ALL rows FIRST
#   (unknown bundle / nonexistent dest dir / missing member source => fail-closed exit 2, NOTHING written),
#   THEN route each (bundle,dest) through route_project_items so every existing guarantee holds (backup-first,
#   idempotent, --dry-run), THEN write the derived applied-record. Deleting a master row stops future
#   refreshes; it never uninstalls already-placed items.
apply_project_routes(){
  if [ ! -f "$ROUTES_MASTER" ]; then log "[routes] no project-routes master at $ROUTES_MASTER — nothing to apply."; return 0; fi
  local active; active="$(read_routes_active "$ROUTES_MASTER")"
  if [ -z "$active" ]; then log "[routes] project-routes master $ROUTES_MASTER has no active rows — nothing to apply."; return 0; fi
  local _tab; _tab="$(printf '\t')"
  # PHASE 1 — validate EVERY row before ANY write (reuses validate_routes_master; exits 2, nothing routed).
  # For a tier install this ALSO ran in preflight (so the whole command already aborted atomically on a bad
  # master); re-running here is cheap defense-in-depth and covers the pure --apply-project-routes path.
  validate_routes_master
  # PHASE 2 — route each validated row through the existing per-project path, with a per-row summary
  log "[routes] applying project-routes master ($ROUTES_MASTER):"
  while IFS="$_tab" read -r _b _d; do
    [ -z "$_b" ] && continue
    local _items; _items="$(project_manifest_items_for_bundle "$_b" | tr '\n' ',' | sed 's/,$//')"
    route_project_items "$_items" "$_d"
    log "  applied: $_b -> $_d/.claude/"
  done <<EOF
$active
EOF
  # PHASE 3 — record what was applied (a derived receipt in ~/.claude; the master stays the source of truth)
  write_routes_record "$active"
}

# write_build_stamp — record WHICH toolkit build this install deployed + WHEN, to a
#   known file the hooks read at runtime so every log row self-identifies its build
#   (a mixed log then self-partitions by version with zero manual bookkeeping).
#   build_id = git short-SHA (if the source is a git repo) ELSE a content hash of the
#   deployed hook sources (works without git) — both suffixed with the install timestamp.
write_build_stamp(){
  local sha short desc dirty
  sha="$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || true)"
  short="$(git -C "$SCRIPT_DIR" rev-parse --short HEAD 2>/dev/null || true)"
  desc="$(git -C "$SCRIPT_DIR" describe --tags --always --dirty 2>/dev/null || true)"
  [ -n "$(git -C "$SCRIPT_DIR" status --porcelain 2>/dev/null)" ] && dirty=1 || dirty=0
  CRT_SHA="$sha" CRT_SHORT="$short" CRT_DESC="$desc" CRT_DIRTY="$dirty" CRT_TS="$TS" \
  CRT_HOOKS="$PAYLOAD/hooks" CRT_TIERS="core=$CORE ergo=$ERGO mem=$MEM personal=$PERSONAL" \
  python3 - "$CLAUDE_DIR/toolkit_build.json" <<'PY'
import os, sys, json, time, datetime, hashlib, glob
# content hash of the behavior-determining hook sources (git-independent version signal)
hh = ""
try:
    hd = os.environ.get("CRT_HOOKS", "")
    parts = [open(p, "rb").read() for p in sorted(glob.glob(os.path.join(hd, "*.sh")) + glob.glob(os.path.join(hd, "*.py")))]
    if parts: hh = hashlib.sha256(b"".join(parts)).hexdigest()[:8]
except Exception:
    hh = ""
short = os.environ.get("CRT_SHORT", "")
dirty = os.environ.get("CRT_DIRTY", "") == "1"
ts = os.environ.get("CRT_TS", "")
if short:   bid = "g" + short + ("-dirty" if dirty else "") + "-" + ts
elif hh:    bid = "h" + hh + "-" + ts
else:       bid = "nogit-" + ts
dt = datetime.datetime.now().astimezone()
rec = {
    "build_id": bid,
    "git_sha": os.environ.get("CRT_SHA", ""),
    "git_short": short,
    "git_describe": os.environ.get("CRT_DESC", ""),
    "git_dirty": dirty,
    "hooks_sha256_8": hh,
    "installed_at": dt.strftime("%Y-%m-%dT%H:%M:%S") + dt.strftime("%z"),
    "installed_epoch_ms": int(time.time() * 1000),
    "install_ts": ts,
    "tiers": os.environ.get("CRT_TIERS", ""),
}
open(sys.argv[1], "w").write(json.dumps(rec, indent=2) + "\n")
print("  build stamp:", bid)
PY
}

# ---- preflight (read-only; safe under --dry-run) ----
command -v python3 >/dev/null 2>&1 || { echo "FATAL: python3 required (macOS: xcode-select --install)"; exit 1; }
if find "$PAYLOAD" -name '*.icloud' 2>/dev/null | grep -q .; then
  echo "FATAL: iCloud placeholder(s) in payload/ (files not downloaded). In Finder right-click the toolkit -> Download Now, then retry."; exit 1
fi
if [ -s "$CLAUDE_DIR/settings.json" ] && ! python3 -m json.tool "$CLAUDE_DIR/settings.json" >/dev/null 2>&1; then
  echo "FATAL: existing $CLAUDE_DIR/settings.json is not valid JSON; fix or move it aside first."; exit 1
fi
if [ "$VERIFY" = 1 ] && [ -f "$LIB/scrub_verify.sh" ]; then
  bash "$LIB/scrub_verify.sh" "$PAYLOAD" >/dev/null || { echo "FATAL: scrub_verify failed (dangling refs in payload). Run: bash lib/scrub_verify.sh"; exit 1; }
fi
if [ "$VERIFY" = 1 ] && [ -f "$LIB/doc-status.sh" ]; then
  # currency gate: every durable doc must carry an in-band STATUS header (payload/rules/doc-currency.machine.md).
  bash "$LIB/doc-status.sh" check "$PAYLOAD" --strict >/dev/null || { echo "FATAL: doc-status check failed (durable docs missing a STATUS header). Run: bash lib/doc-status.sh check payload --strict"; exit 1; }
fi
# coupling gate (fail-closed): the frozen manifest MUST match the live payload before any copy, so a
# --select can never install a skill/agent set the manifest doesn't actually describe.
COUPLING_MANIFEST="$PAYLOAD/coupling_manifest_v1.tsv"
if [ "$VERIFY" = 1 ] && [ -f "$LIB/verify_coupling.sh" ] && [ -f "$COUPLING_MANIFEST" ]; then
  bash "$LIB/verify_coupling.sh" "$PAYLOAD" "$COUPLING_MANIFEST" >/dev/null || { echo "FATAL: coupling gate failed (manifest drifted from payload). Run: bash lib/verify_coupling.sh payload payload/coupling_manifest_v1.tsv"; exit 1; }
fi
# DDA category-contract gate (fail-closed): every durable doc carrying a DDC_CATEGORY header must satisfy
# its category contract (status-header floor, class faces, one-owner-per-topic). Layers above the currency
# gate — doc-status checks a header EXISTS; this checks the DDA CONTRACT holds. Convention: payload/rules/durable-doc-architecture.machine.md.
if [ "$VERIFY" = 1 ] && [ -f "$LIB/check_current_documents.py" ]; then
  python3 "$LIB/check_current_documents.py" "$PAYLOAD" >/dev/null || { echo "FATAL: DDA category-contract check failed (a durable doc violates its DDC category contract). Run: python3 lib/check_current_documents.py payload"; exit 1; }
fi
# model-policy gate (fail-closed): no agent frontmatter or settings fragment may name a barred model value
# (claude-opus-5, bare `opus`, `opusplan` — the bare alias resolves to Opus 5 in Claude Code >=2.1.219).
if [ "$VERIFY" = 1 ] && [ -f "$LIB/verify_models.sh" ]; then
  bash "$LIB/verify_models.sh" "$PAYLOAD" >/dev/null || { echo "FATAL: model-policy gate failed (a barred model value survives in payload). Run: bash lib/verify_models.sh payload"; exit 1; }
fi

# --project-bundle: expand each requested bundle -> its member items (fail-closed on an unknown bundle),
# then UNION with any --project-items. Runs in preflight (before any write) so an unknown bundle exits 2
# with NOTHING written; the unioned item list then flows through the name-validation + copy below unchanged.
if [ -n "$PROJECT_BUNDLES" ]; then
  [ -f "$PROJECT_MANIFEST" ] || { echo "FATAL: project manifest not found: $PROJECT_MANIFEST" >&2; exit 2; }
  _bad_b=""; _bundle_items=""
  _nlb="$(printf '%s' "$PROJECT_BUNDLES" | tr ',' '\n')"
  while IFS= read -r _bn; do
    _bn="$(printf '%s' "$_bn" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [ -z "$_bn" ] && continue
    _members="$(project_manifest_items_for_bundle "$_bn")"
    if [ -z "$_members" ]; then _bad_b="$_bad_b $_bn"; continue; fi
    _bundle_items="$_bundle_items
$_members"
  done <<EOF
$_nlb
EOF
  if [ -n "$_bad_b" ]; then
    echo "error: unknown --project-bundle name(s):$_bad_b" >&2
    echo "       valid bundles (from $PROJECT_MANIFEST):" >&2
    project_manifest_bundles | sed 's/^/         /' >&2
    exit 2
  fi
  # union bundle members into PROJECT_ITEMS (dedup, preserving first-seen order)
  PROJECT_ITEMS="$(printf '%s\n%s\n' "$(printf '%s' "$PROJECT_ITEMS" | tr ',' '\n')" "$_bundle_items" \
    | awk '{ gsub(/^[[:space:]]+|[[:space:]]+$/,"") } NF && !seen[$0]++' | tr '\n' ',' | sed 's/,$//')"
fi

# project-items name validation (fail-closed; runs EVEN under --no-verify — an unknown name must never
# reach the copy). Validates EVERY requested name against project_manifest.tsv BEFORE any write; any
# unknown (or a name whose source file/dir is missing) => exit 2 with NOTHING written. Covers bundle
# members too (they were unioned into PROJECT_ITEMS above).
if [ -n "$PROJECT_ITEMS" ]; then
  [ -f "$PROJECT_MANIFEST" ] || { echo "FATAL: project manifest not found: $PROJECT_MANIFEST" >&2; exit 2; }
  _bad=""
  _nlv="$(printf '%s' "$PROJECT_ITEMS" | tr ',' '\n')"
  while IFS= read -r _nm; do
    _nm="$(printf '%s' "$_nm" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [ -z "$_nm" ] && continue
    _k="$(project_manifest_kind "$_nm")"
    if [ -z "$_k" ]; then _bad="$_bad $_nm"; continue; fi
    if [ "$_k" = agent ] && [ ! -f "$PAYLOAD_PROJECT/agents/$_nm.md" ]; then _bad="$_bad $_nm(missing-src)"; fi
    if [ "$_k" = skill ] && [ ! -d "$PAYLOAD_PROJECT/skills/$_nm" ];   then _bad="$_bad $_nm(missing-src)"; fi
  done <<EOF
$_nlv
EOF
  if [ -n "$_bad" ]; then
    echo "error: unknown or unavailable --project-items name(s):$_bad" >&2
    echo "       valid names (from $PROJECT_MANIFEST):" >&2
    project_manifest_names | sed 's/^/         /' >&2
    exit 2
  fi
fi

# ---- project-routes MASTER validation (fail-closed, read-only) — run in PREFLIGHT, BEFORE any tier write,
#      so an invalid master row makes the WHOLE command fail fast + ATOMIC (exit 2, nothing written anywhere:
#      no ~/.claude backup/settings/copy, no routing, no record). Runs EVEN under --no-verify (a safety gate,
#      not a verify gate). Gated to the runs that will apply the master: an explicit --apply-project-routes,
#      or ANY tier install (a tier auto-applies an active master). A blank master no-ops; a pure
#      --project-items CLI call never applies the master, so it is not validated here (keeps ~/.claude isolation).
if [ "$APPLY_ROUTES" = 1 ] || [ "$ANY_TIER" = 1 ]; then
  validate_routes_master
fi

# ~/.claude setup + managed-set backup — ONLY when a tier install is happening. A pure project-routing
# call (--project-items with no tier) does not touch $CLAUDE_DIR, so it makes no backup snapshot here.
if [ "$ANY_TIER" = 1 ]; then
  run mkdir -p "$CLAUDE_DIR" "$BACKUP"
  # ---- back up the managed set ONCE, before any write ----
  for t in CLAUDE.md settings.json rules skills agents commands hooks methodology docs; do
    [ -e "$CLAUDE_DIR/$t" ] && { run cp -R "$CLAUDE_DIR/$t" "$BACKUP/"; log "backed up $t"; }
  done
  log "backup -> $BACKUP"
fi

copy_tree(){ # $1 payload subdir, $2 target subdir  (additive; never --delete)
  run mkdir -p "$CLAUDE_DIR/$2"
  if command -v rsync >/dev/null 2>&1; then run rsync -a "$PAYLOAD/$1/" "$CLAUDE_DIR/$2/"
  else run cp -R "$PAYLOAD/$1/." "$CLAUDE_DIR/$2/"; fi
}

# copy_selected — copy ONLY the resolved agents+skills (from --select/--manifest-subset). Falls back
# to full copy_tree of both trees when no selection is active. Resolution reads the frozen manifest
# via lib/select_resolve.py (one source), so a selection can never diverge from the coupling gate.
copy_selected(){
  if [ -z "$SELECT" ] && [ -z "$SUBSET" ]; then
    copy_tree skills skills; copy_tree agents agents; return
  fi
  local args=(--manifest "$COUPLING_MANIFEST")
  [ -n "$SELECT" ] && args+=(--select "$SELECT")
  [ -n "$SUBSET" ] && args+=(--manifest-subset "$SUBSET")
  [ "$ALLOW_DEFERRED" = 1 ] && args+=(--allow-deferred)
  local resolved; resolved="$(python3 "$LIB/select_resolve.py" "${args[@]}")" || {
    echo "FATAL: selection failed (see error above). Nothing installed."; exit 2; }
  # parse the ==AGENTS==/==SKILLS== sections
  local sec="" a s
  run mkdir -p "$CLAUDE_DIR/skills" "$CLAUDE_DIR/agents"
  while IFS= read -r line; do
    case "$line" in
      ==AGENTS==) sec=agents; continue;; ==SKILLS==) sec=skills; continue;; "") continue;;
    esac
    if [ "$sec" = agents ]; then
      [ -f "$PAYLOAD/agents/$line.md" ] && { run cp "$PAYLOAD/agents/$line.md" "$CLAUDE_DIR/agents/"; log "  +agent $line"; }
    elif [ "$sec" = skills ]; then
      [ -d "$PAYLOAD/skills/$line" ] && { run cp -R "$PAYLOAD/skills/$line" "$CLAUDE_DIR/skills/"; log "  +skill $line"; }
    fi
  done <<EOF
$resolved
EOF
}

assemble_claude_md(){   # managed-block: regenerate our block, preserve any user content outside it
  local target="$CLAUDE_DIR/CLAUDE.md"
  local B="<!-- >>> claude-research-toolkit (managed) >>> -->"
  local E="<!-- <<< claude-research-toolkit (managed) <<< -->"
  if [ "$DRY" = 1 ]; then log "DRYRUN: assemble CLAUDE.md (memories=$MEM)"; return; fi
  local tmp; tmp="$(mktemp)"
  if [ -f "$target" ]; then
    awk -v b="$B" -v e="$E" 'BEGIN{s=0} $0==b{s=1;next} $0==e{s=0;next} s==0{print}' "$target" > "$tmp"
  fi
  { printf '%s\n' "$B"
    cat "$PAYLOAD/CLAUDE.core.md"
    if [ "$MEM" = 1 ]; then printf '\n'; cat "$PAYLOAD/CLAUDE.memories.md"; fi
    printf '%s\n' "$E"
  } >> "$tmp"
  cp "$tmp" "$target"; rm -f "$tmp"
  log "assembled CLAUDE.md (memories: $([ "$MEM" = 1 ] && echo on || echo off))"
}

FRAGS=()

if [ "$CORE" = 1 ]; then
  log "[core] rules / skills / agents / methodology / docs + dev hooks + safety-deny + CLAUDE.md"
  # discipline trees (rules/methodology/docs) — tri-state DISCIPLINE_MODE (auto|copy|skip).
  # auto resolves IN-ENGINE (never precomputed by any front-end) from the already-set ROOT/GLOBAL_DIR:
  #   skip ONLY for a STACKED root (--root set AND target != global baseline) that already inherits a
  #   global ~/.claude/rules — that project-local copy would be an UNGUARDED shadow of the global rules
  #   (the shadow guard covers skills/agents only). Otherwise COPY. A global install (CLAUDE_DIR==GLOBAL_DIR)
  #   or a root with no global rules ALWAYS copies — it must carry its own discipline.
  _disc_eff="$DISCIPLINE_MODE"
  if [ "$_disc_eff" = auto ]; then
    if [ -n "$ROOT" ] && [ "$CLAUDE_DIR" != "$GLOBAL_DIR" ] && [ -d "$GLOBAL_DIR/rules" ]; then
      _disc_eff=skip; else _disc_eff=copy; fi
  fi
  if [ "$_disc_eff" = copy ]; then
    log "[discipline] rules/methodology/docs: COPY (mode=$DISCIPLINE_MODE)"
    for d in rules methodology docs; do copy_tree "$d" "$d"; done
  else
    log "[discipline] rules/methodology/docs: SKIP (mode=$DISCIPLINE_MODE) — inheriting global $GLOBAL_DIR/rules"
    # never prune (honor copy_tree's never-delete invariant); but a pre-existing local copy WOULD shadow global.
    for d in rules methodology docs; do
      [ -d "$CLAUDE_DIR/$d" ] && log "  WARNING: pre-existing $CLAUDE_DIR/$d left in place — it SHADOWS global $d (remove it manually to fully inherit global, or re-run with --discipline-trees copy)"
    done
  fi
  copy_selected   # skills+agents: full trees by default, or the resolved closure under --select/--manifest-subset
  run mkdir -p "$CLAUDE_DIR/hooks"
  run cp "$PAYLOAD/hooks/post-edit-review.sh" "$PAYLOAD/hooks/pre-complete-verification.sh" "$PAYLOAD/hooks/stop-adversary-gate.sh" "$PAYLOAD/hooks/timeline-logger.sh" "$PAYLOAD/hooks/ambient_time.py" "$PAYLOAD/hooks/doc-currency-guard.sh" "$PAYLOAD/hooks/transcript_archive.py" "$CLAUDE_DIR/hooks/"
  run chmod +x "$CLAUDE_DIR/hooks/post-edit-review.sh" "$CLAUDE_DIR/hooks/pre-complete-verification.sh" "$CLAUDE_DIR/hooks/stop-adversary-gate.sh" "$CLAUDE_DIR/hooks/timeline-logger.sh" "$CLAUDE_DIR/hooks/ambient_time.py" "$CLAUDE_DIR/hooks/doc-currency-guard.sh" "$CLAUDE_DIR/hooks/transcript_archive.py"
  # claim-verify-guard — write-time claim-vs-record recompute (BLOCKS on mismatch). Wired 2026-07-27:
  # the hook + fragment existed in payload but were never installed (DISC-06-a in the countermeasures ledger).
  [ -f "$PAYLOAD/hooks/claim-verify-guard.sh" ] && { run cp "$PAYLOAD/hooks/claim-verify-guard.sh" "$CLAUDE_DIR/hooks/"; run chmod +x "$CLAUDE_DIR/hooks/claim-verify-guard.sh"; }
  # plan-routing-gate — ExitPlanMode Delegation & Routing lint (SEED-06 anti-theater; blocking, crt-mode escape).
  [ -f "$PAYLOAD/hooks/plan-routing-gate.sh" ] && { run cp "$PAYLOAD/hooks/plan-routing-gate.sh" "$CLAUDE_DIR/hooks/"; run chmod +x "$CLAUDE_DIR/hooks/plan-routing-gate.sh"; }
  # prose-tics-lint — PostToolUse advisory prose-tic scan on manuscript-class files written to disk (fail-open, never blocks; TIER-P CC-only).
  [ -f "$PAYLOAD/hooks/prose-tics-lint.sh" ] && { run cp "$PAYLOAD/hooks/prose-tics-lint.sh" "$CLAUDE_DIR/hooks/"; run chmod +x "$CLAUDE_DIR/hooks/prose-tics-lint.sh"; }
  # opus-dispatch-guard — PreToolUse/Task alias ban at DISPATCH time (the moment the build-time and
  # plan-time gates never covered: a live Task(model:"opus") fired nothing, measured 2026-08-04).
  [ -f "$PAYLOAD/hooks/opus-dispatch-guard.sh" ] && { run cp "$PAYLOAD/hooks/opus-dispatch-guard.sh" "$CLAUDE_DIR/hooks/"; run chmod +x "$CLAUDE_DIR/hooks/opus-dispatch-guard.sh"; }
  # subagent_qa_gate — SubagentStop QA + error-mode telemetry (advisory; one nudge, never a loop).
  [ -f "$PAYLOAD/hooks/subagent_qa_gate.sh" ] && { run cp "$PAYLOAD/hooks/subagent_qa_gate.sh" "$CLAUDE_DIR/hooks/"; run chmod +x "$CLAUDE_DIR/hooks/subagent_qa_gate.sh"; }
  # telemetry readers (user-invoked log analysis; the hooks write logs to ~/.claude/logs/):
  #   python3 ~/.claude/lib/gate-log-report.py        — F1 adversarial-gate block-rate / latency
  #   python3 ~/.claude/lib/timeline-report.py        — session durations / slowest steps
  run mkdir -p "$CLAUDE_DIR/lib"
  run cp "$LIB/gate-log-report.py" "$LIB/timeline-report.py" "$CLAUDE_DIR/lib/"
  # countermeasure-audit.py — the efficacy-measurement instrument (skill countermeasure-audit invokes it from ~/.claude/lib).
  [ -f "$LIB/countermeasure-audit.py" ] && run cp "$LIB/countermeasure-audit.py" "$CLAUDE_DIR/lib/"
  # crt-mode.sh — the master on/observe/off switch (user disable + research A/B arm).
  run cp "$LIB/crt-mode.sh" "$CLAUDE_DIR/lib/"
  run chmod +x "$CLAUDE_DIR/lib/crt-mode.sh"
  # doc-status.sh — currency-header check/stamp tool (payload/rules/doc-currency.machine.md).
  run cp "$LIB/doc-status.sh" "$CLAUDE_DIR/lib/"
  run chmod +x "$CLAUDE_DIR/lib/doc-status.sh"
  # coupling gate + resolver + frozen manifest — so the installed toolkit can self-verify its coupling.
  [ -f "$LIB/verify_coupling.sh" ] && { run cp "$LIB/verify_coupling.sh" "$CLAUDE_DIR/lib/"; run chmod +x "$CLAUDE_DIR/lib/verify_coupling.sh"; }
  [ -f "$LIB/select_resolve.py" ] && { run cp "$LIB/select_resolve.py" "$CLAUDE_DIR/lib/"; run chmod +x "$CLAUDE_DIR/lib/select_resolve.py"; }
  [ -f "$PAYLOAD/coupling_manifest_v1.tsv" ] && run cp "$PAYLOAD/coupling_manifest_v1.tsv" "$CLAUDE_DIR/lib/"
  # DDA category-contract checker — so the installed toolkit can self-verify its durable-doc set (payload/rules/durable-doc-architecture.machine.md).
  [ -f "$LIB/check_current_documents.py" ] && run cp "$LIB/check_current_documents.py" "$CLAUDE_DIR/lib/"
  # dev-tree.sh — scaffold/status/offload the development/ record tree (methodology/DEVELOPMENT_TREE.machine.md; /clean-tasks).
  run cp "$LIB/dev-tree.sh" "$CLAUDE_DIR/lib/"
  run chmod +x "$CLAUDE_DIR/lib/dev-tree.sh"
  # stale_move.sh — move-and-tombstone a retired file into Stale_Trash/ (rules/project-structure-standard.machine.md RULE.stale_trash).
  [ -f "$LIB/stale_move.sh" ] && { run cp "$LIB/stale_move.sh" "$CLAUDE_DIR/lib/"; run chmod +x "$CLAUDE_DIR/lib/stale_move.sh"; }
  # capability-audit.sh — inventory/cluster/backup carrier for the capability-audit skill (T-21; /capability-audit).
  run cp "$LIB/capability-audit.sh" "$CLAUDE_DIR/lib/"
  run chmod +x "$CLAUDE_DIR/lib/capability-audit.sh"
  # crt-persona.sh — primary-persona default manager (the "agent" settings key; on|off|show). Needs
  # merge_settings.py + the persona fragment reachable from the installed tree (its documented fallbacks).
  [ -f "$LIB/crt-persona.sh" ] && { run cp "$LIB/crt-persona.sh" "$CLAUDE_DIR/lib/"; run chmod +x "$CLAUDE_DIR/lib/crt-persona.sh"; }
  [ -f "$LIB/merge_settings.py" ] && run cp "$LIB/merge_settings.py" "$CLAUDE_DIR/lib/"
  run mkdir -p "$CLAUDE_DIR/settings-fragments"
  [ -f "$PAYLOAD/settings/persona.fragment.json" ] && run cp "$PAYLOAD/settings/persona.fragment.json" "$CLAUDE_DIR/settings-fragments/"
  # verify_models.sh — the model-policy gate, installed so the live toolkit can self-check its agents.
  [ -f "$LIB/verify_models.sh" ] && { run cp "$LIB/verify_models.sh" "$CLAUDE_DIR/lib/"; run chmod +x "$CLAUDE_DIR/lib/verify_models.sh"; }
  # crt-dev-model.sh — per-project/per-machine model switch for the software-developer agent (fable|opus48|show).
  [ -f "$LIB/crt-dev-model.sh" ] && { run cp "$LIB/crt-dev-model.sh" "$CLAUDE_DIR/lib/"; run chmod +x "$CLAUDE_DIR/lib/crt-dev-model.sh"; }
  # /clean-tasks — CORE command (the excision verb for the development/ tree). xbeep stays ergonomics-gated.
  run mkdir -p "$CLAUDE_DIR/commands"
  run cp "$PAYLOAD/commands/clean-tasks.md" "$CLAUDE_DIR/commands/"
  # /capability-audit — declutter + placement advisor (T-21; skill capability-audit + lib capability-audit.sh).
  run cp "$PAYLOAD/commands/capability-audit.md" "$CLAUDE_DIR/commands/"
  # /doc-pipeline — author ⇒ translate ⇒ render triplet; authoring layered on the folio render core.
  run cp "$PAYLOAD/commands/doc-pipeline.md" "$CLAUDE_DIR/commands/"
  # build/version provenance: hooks stamp this build_id into every JSONL log row
  run write_build_stamp
  FRAGS+=("$PAYLOAD/settings/core.fragment.json")
  FRAGS+=("$PAYLOAD/settings/ambient-time.fragment.json")
  FRAGS+=("$PAYLOAD/settings/doc-currency-guard.fragment.json")
  FRAGS+=("$PAYLOAD/settings/transcript-vault.fragment.json")
  [ -f "$PAYLOAD/settings/claim-verify-guard.fragment.json" ] && FRAGS+=("$PAYLOAD/settings/claim-verify-guard.fragment.json")
  [ -f "$PAYLOAD/settings/plan-routing-gate.fragment.json" ] && FRAGS+=("$PAYLOAD/settings/plan-routing-gate.fragment.json")
  [ -f "$PAYLOAD/settings/prose-tics-lint.fragment.json" ] && FRAGS+=("$PAYLOAD/settings/prose-tics-lint.fragment.json")
  [ -f "$PAYLOAD/settings/opus-dispatch-guard.fragment.json" ] && FRAGS+=("$PAYLOAD/settings/opus-dispatch-guard.fragment.json")
  [ -f "$PAYLOAD/settings/subagent-qa.fragment.json" ] && FRAGS+=("$PAYLOAD/settings/subagent-qa.fragment.json")
  assemble_claude_md
fi

if [ "$ERGO" = 1 ]; then
  log "[ergonomics] xbeep hooks + /xbeep command + beep registrations"
  copy_tree hooks/xbeep hooks/xbeep
  if [ "$DRY" != 1 ]; then chmod +x "$CLAUDE_DIR"/hooks/xbeep/*.sh; fi
  run mkdir -p "$CLAUDE_DIR/commands"
  run cp "$PAYLOAD/commands/xbeep.md" "$CLAUDE_DIR/commands/"
  FRAGS+=("$PAYLOAD/settings/ergonomics.fragment.json")
  if ! command -v afplay >/dev/null 2>&1 && ! command -v paplay >/dev/null 2>&1 && ! command -v aplay >/dev/null 2>&1; then
    log "NOTE: no afplay/paplay/aplay found -> beeps fall back to the terminal bell (enable your terminal's audible bell, or set XBEEP_SOUND / install pulseaudio-utils | alsa-utils)."
  fi
fi

if [ "$PERSONAL" = 1 ]; then
  log "[personal] model=claude-fable-5[1m] / theme / tui / effort=max / alwaysThinking / plugin / default persona=planner (crt-persona off to remove; claude --agent <name> per-session)"
  FRAGS+=("$PAYLOAD/settings/personal.fragment.json")
  [ -f "$PAYLOAD/settings/persona.fragment.json" ] && FRAGS+=("$PAYLOAD/settings/persona.fragment.json")
fi

# ---- merge settings.json (deep-merge; never clobber) ----
if [ "${#FRAGS[@]}" -gt 0 ]; then
  [ -e "$CLAUDE_DIR/settings.json" ] && run cp "$CLAUDE_DIR/settings.json" "$CLAUDE_DIR/settings.json.bak-$TS"
  run python3 "$LIB/merge_settings.py" "$CLAUDE_DIR/settings.json" "${FRAGS[@]}"
  log "settings merged"
fi

# ---- route project-specialty items into a project's OWN .claude/ (independent of the ~/.claude install) ----
# The one-shot CLI path (--project-items/--project-bundle). Runs AFTER any tier install so a combined call
# does BOTH; runs alone for a pure project-routing call. Stays isolated from ~/.claude (routes no master).
if [ -n "$PROJECT_ITEMS" ]; then
  route_project_items "$PROJECT_ITEMS" "$PROJECT_DEST"
fi

# ---- apply the project-routes MASTER: route every declared bundle to its dest(s) (validated fail-closed) --
# Triggered EXPLICITLY by --apply-project-routes, OR AUTOMATICALLY on a tier install when the master has
# active rows (a blank master is a no-op; a pure CLI --project-items call never auto-applies the master).
APPLIED_MASTER=0
if [ "$APPLY_ROUTES" = 1 ]; then
  apply_project_routes; APPLIED_MASTER=1
elif [ "$ANY_TIER" = 1 ] && [ -n "$(read_routes_active "$ROUTES_MASTER")" ]; then
  log "[routes] tier install + active master rows => auto-applying project routes"
  apply_project_routes; APPLIED_MASTER=1
fi

echo
if [ "$ANY_TIER" = 1 ]; then
  echo "DONE. Backup: $BACKUP"
elif [ "$APPLY_ROUTES" = 1 ]; then
  echo "DONE (project routes applied — ~/.claude untouched except the derived applied-record)."
else
  echo "DONE (project-routing only — ~/.claude was not touched)."
fi
[ -n "$PROJECT_ITEMS" ] && echo "Project items routed to: $PROJECT_DEST/.claude/{agents,skills}/ (any overwritten target backed up under $PROJECT_DEST/.claude/backups/pre-project-$TS)"
if [ "$APPLIED_MASTER" = 1 ]; then
  echo "Applied project routes from master: $ROUTES_MASTER"
  echo "  (derived applied-record: $ROUTES_RECORD — a receipt; edit the master, not this copy)"
fi
[ "$DRY" = 1 ] && echo "(dry run — nothing was written)"
echo "RESTART Claude Code (start a NEW session) — rules/skills/agents/hooks load at startup."
# scope-aware verify hint (tier installs only; a pure project-routing call did not touch ~/.claude).
# A stacked --root install with skipped discipline trees has NO local rules/ (by design — it inherits
# global), so don't tell the user to ls a path that correctly doesn't exist.
if [ "$ANY_TIER" = 1 ]; then
  if [ "${_disc_eff:-copy}" = skip ]; then
    echo "Verify: see INSTALL.md; quick check -> ls \"$CLAUDE_DIR\"/{CLAUDE.md,skills,agents}  (rules/methodology/docs inherit from global $GLOBAL_DIR)"
  else
    echo "Verify: see INSTALL.md for the post-install checklist; quick check -> ls \"$CLAUDE_DIR\"/{CLAUDE.md,rules,skills,agents}"
  fi
fi
