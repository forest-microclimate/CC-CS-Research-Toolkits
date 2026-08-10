#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# install.sh — install the Claude Research Toolkit into ~/.claude/ (global; loads for EVERY session).
# Idempotent · tiered · backs up before any write · deep-merges settings.json (never clobbers).
# Runs from a plain shell (NOT Claude's Bash tool), so the safety deny-list it installs does not block it.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PAYLOAD="$SCRIPT_DIR/payload"
# [RETIRED 2026-08-09, PC3] PROJECT-SPECIALTY ROUTING — the whole feature is gone from this installer:
# `payload-project/` was DELETED and its carriers moved to the sibling `CCRT_specialists/` tree.
# REPLACEMENT MODEL: MANUAL install — copy the wanted item out of `CCRT_specialists/<bucket>/{agents,skills}/`
# into the project's own `.claude/{agents,skills}/`. That tree has VARIABLE DEPTH (some buckets hold
# agents/ + skills/ directly, others nest a sub-bucket), which is one reason it is browsed by hand rather
# than routed by name. Retired here: $PAYLOAD_PROJECT · $PROJECT_MANIFEST · $ROUTES_MASTER ·
# --project-items · --project-dest · --project-bundle · --apply-project-routes · route_project_items() ·
# apply_project_routes() · project_routes.tsv (both the master and the derived applied-record).
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
  Project specialists (RETIRED 2026-08-09 — now a MANUAL install):
    The --project-items / --project-dest / --project-bundle / --apply-project-routes flags are GONE
    along with payload-project/. To give ONE project a specialist, copy it yourself out of
    CCRT_specialists/<bucket>/{agents,skills}/ into that project's own .claude/{agents,skills}/.
    Passing a retired flag exits 2 with this same pointer and writes nothing.
  Options:
    --dry-run     print actions, write nothing
    --no-verify   skip the scrub_verify.sh + doc-status + coupling gates
    -h, --help
U
}

CORE=0; ERGO=0; MEM=0; PERSONAL=0; DRY=0; VERIFY=1
SELECT=""; SUBSET=""; ALLOW_DEFERRED=0; ROOT=""; DISCIPLINE_MODE=auto; INTERACTIVE=0
# [RETIRED 2026-08-09, PC3] PROJECT_ITEMS / PROJECT_DEST / PROJECT_BUNDLES / APPLY_ROUTES lived here.
retired_project_flag(){   # the in-band tombstone that fires where the flag was actually USED
  echo "error: '$1' was RETIRED 2026-08-09 — project-specialty routing is gone from install.sh." >&2
  echo "       payload-project/ was deleted; its carriers live in CCRT_specialists/ and install MANUALLY:" >&2
  echo "         cp -R \"$SCRIPT_DIR/CCRT_specialists/<bucket>/agents/<name>.md\" <project>/.claude/agents/" >&2
  echo "         cp -R \"$SCRIPT_DIR/CCRT_specialists/<bucket>/skills/<name>\"    <project>/.claude/skills/" >&2
  echo "       (buckets vary in depth — browse the tree; nothing written.)" >&2
  exit 2
}
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
    --project-items|--project-dest|--project-bundle|--apply-project-routes) retired_project_flag "$1";;
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
  # (the retired --project-* flags exit 2 at parse time, so they can never reach this guard.)
  if [ "$CORE" = 1 ] || [ "$ERGO" = 1 ] || [ "$MEM" = 1 ] || [ "$PERSONAL" = 1 ] \
     || [ -n "$SELECT" ] || [ -n "$SUBSET" ] || [ -n "$ROOT" ] || [ "$ALLOW_DEFERRED" = 1 ] \
     || [ "$DISCIPLINE_MODE" != auto ]; then
    echo "error: --interactive composes its own tier/selection/root flags per pass; do not combine it with" >&2
    echo "       --core/--ergonomics/--memories/--personal/--all/--select/--manifest-subset/--root/--allow-deferred/" >&2
    echo "       --discipline-trees. (--dry-run and --no-verify ARE allowed.)" >&2
    exit 2
  fi
  _picker="$LIB/interactive_select.py"
  [ -f "$_picker" ] || { echo "FATAL: interactive front-end not found: $_picker" >&2; exit 1; }
  _prc=0
  _lines="$(python3 "$_picker" --manifest "$PAYLOAD/coupling_manifest_v1.tsv" --resolver "$LIB/select_resolve.py")" || _prc=$?
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
# CORE=1 itself, so it is excluded here. This must run AFTER parsing so `--root DIR` alone still
# installs the full set (the earlier `$#-eq 0` test wrongly treated `--root DIR` as an explicit selection).
# [RETIRED 2026-08-09, PC3] the retired --project-items/--project-bundle/--apply-project-routes were
# also excluded here, because a PURE project-routing call installed nothing into ~/.claude. With the
# feature gone every invocation is a tier install, which is why ANY_TIER disappeared below.
if [ "$CORE" = 0 ] && [ "$ERGO" = 0 ] && [ "$MEM" = 0 ] && [ "$PERSONAL" = 0 ] && [ -z "$SELECT" ] && [ -z "$SUBSET" ]; then
  CORE=1; ERGO=1; MEM=1
fi
[ "$MEM" = 1 ] && CORE=1   # memories append to the core CLAUDE.md, which must exist
# --root: per-root scoping — install into a repo-local dir instead of the global ~/.claude
[ -n "$ROOT" ] && CLAUDE_DIR="$ROOT"
BACKUP="$CLAUDE_DIR/backups/pre-toolkit-$TS"   # recompute after any --root override
# [RETIRED 2026-08-09, PC3] $ROUTES_RECORD (~/.claude/project_routes.tsv, the DERIVED applied-record)
# was written here-abouts on every route apply. No apply path remains, so nothing writes it; an
# already-installed copy from a pre-retirement run is inert (it was read by nothing even then).
[ -n "$SELECT" ] && [ -n "$SUBSET" ] && { echo "error: --select and --manifest-subset are mutually exclusive" >&2; exit 2; }

# [RETIRED 2026-08-09, PC3] two preconditions lived here and are gone with the flags they policed:
# the --project-items/--project-bundle <-> --project-dest pairing check, and ANY_TIER (which existed
# ONLY to tell a pure project-routing call — which touched no ~/.claude — apart from a tier install,
# so it could skip the backup snapshot). EVERY invocation is now a tier install, so the blocks ANY_TIER
# guarded (backup snapshot, DONE line, verify hint) run unconditionally.

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

# ── [RETIRED 2026-08-09, PC3] project-specialty routing helpers ──────────────────────────────
# ~172 lines lived here and are gone with the feature: project_manifest_kind / project_manifest_names /
# project_manifest_bundles / project_manifest_items_for_bundle / _bundle_missing_srcs (they parsed
# payload-project/project_manifest.tsv, a file that no longer exists), route_project_items (the copy
# into <dest>/.claude/{agents,skills}/), and the project-routes MASTER machinery — read_routes_active,
# write_routes_record, validate_routes_master, apply_project_routes.
# REPLACEMENT: MANUAL install from CCRT_specialists/<bucket>/{agents,skills}/ into a project's own
# .claude/. Nothing in this installer reads or writes project_routes.tsv any more.
# IF A ROUTED TREE IS EVER REVIVED: it needs a manifest of its own AND its own gate coverage — the
# retired tree was watched by no gate (lib/verify_models.sh scans payload/ only), which is what made
# it cheap to leave behind and expensive to trust.

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
# model-policy gate (fail-closed). FOUR distinct failure modes, not one — a fix-it message that names
# only the barred-value case teaches an incomplete contract to a blind session, which then "fixes" the
# wrong thing. The gate's own FAIL text names which mode fired; this hint enumerates the set:
#   (1) BARRED VALUE      — `claude-opus-5`, bare `opus`, or `opusplan` anywhere in payload agents or
#                           settings fragments (a bare alias resolves to Opus 5 on CC >= 2.1.219 and
#                           silently RE-resolves whenever the launcher remaps it).
#   (2) UNALLOWLISTED PIN — ANY `model:` key in a payload/agents frontmatter outside the named allowlist.
#                           Outside that list the pin ITSELF is the defect, barred value or not: a shipped
#                           rank-3 pin overrides the launcher's tier choice in every session that installs it.
#   (3) MISSING PIN       — an ALLOWLISTED route with NO pin. For those agents the pin IS the route, so its
#                           absence is as much a defect as a stray pin is on an ordinary agent.
#   (4) PARITY DRIFT      — an allowlisted route whose payload copy and kit copy are not byte-identical
#                           (`cmp`), including a kit counterpart that is missing outright.
if [ "$VERIFY" = 1 ] && [ -f "$LIB/verify_models.sh" ]; then
  bash "$LIB/verify_models.sh" "$PAYLOAD" >/dev/null || {
    echo "FATAL: model-policy gate failed — one of: a BARRED model value in payload; an UNALLOWLISTED"
    echo "       model: pin in payload/agents frontmatter; an ALLOWLISTED route MISSING the pin that IS"
    echo "       that route; or PAYLOAD<->KIT PARITY DRIFT on an allowlisted route."
    echo "       Run for the specific finding: bash lib/verify_models.sh payload"
    exit 1; }
fi

# ── [RETIRED 2026-08-09, PC3] project preflight validation ───────────────────────────────────
# Three fail-closed preflight blocks lived here (~63 lines): --project-bundle expansion into member
# items, --project-items name validation against project_manifest.tsv (which ran even under
# --no-verify, since an unknown name must never reach a copy), and validate_routes_master. All three
# policed inputs that can no longer be supplied — the flags now exit 2 at parse time — so the
# fail-closed property they carried is preserved by that earlier refusal, not lost with them.

# ~/.claude setup + managed-set backup, taken ONCE before any write.
# [RETIRED 2026-08-09, PC3] this was guarded by ANY_TIER, because a pure project-routing call
# touched no $CLAUDE_DIR and had to skip the snapshot. Every invocation is a tier install now,
# so the snapshot is unconditional.
run mkdir -p "$CLAUDE_DIR" "$BACKUP"
# ---- back up the managed set ONCE, before any write ----
for t in CLAUDE.md settings.json rules skills agents commands hooks methodology docs; do
  [ -e "$CLAUDE_DIR/$t" ] && { run cp -R "$CLAUDE_DIR/$t" "$BACKUP/"; log "backed up $t"; }
done
log "backup -> $BACKUP"

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

# ── [RETIRED 2026-08-09, PC3] project-specialty routing execution ────────────────────────────
# Two execution blocks lived here: the one-shot CLI copy (--project-items/--project-bundle) and the
# auto/explicit apply of the project-routes MASTER, plus the DONE lines that reported them. Specialists
# now install BY HAND from CCRT_specialists/ into a project's own .claude/, so this installer's only
# destination is $CLAUDE_DIR and the DONE line no longer has a routing-only variant to distinguish.

echo
echo "DONE. Backup: $BACKUP"
[ "$DRY" = 1 ] && echo "(dry run — nothing was written)"
echo "RESTART Claude Code (start a NEW session) — rules/skills/agents/hooks load at startup."
# scope-aware verify hint. A stacked --root install with skipped discipline trees has NO local rules/
# (by design — it inherits global), so don't tell the user to ls a path that correctly doesn't exist.
if [ "${_disc_eff:-copy}" = skip ]; then
  echo "Verify: see INSTALL.md; quick check -> ls \"$CLAUDE_DIR\"/{CLAUDE.md,skills,agents}  (rules/methodology/docs inherit from global $GLOBAL_DIR)"
else
  echo "Verify: see INSTALL.md for the post-install checklist; quick check -> ls \"$CLAUDE_DIR\"/{CLAUDE.md,rules,skills,agents}"
fi
