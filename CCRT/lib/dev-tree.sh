#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# ============================================================================
# dev-tree.sh — scaffold / inspect / offload the development/ record tree
# ----------------------------------------------------------------------------
# The mechanical carrier for the /development + /clean-tasks convention.
# Convention of record: methodology/DEVELOPMENT_TREE.machine.md
#
# A per-project development/ dir with three TEMPORAL drawers:
#   past/     DONE records  — dated, safe forever (offload OUT of grep scope)
#   present/  STATE         — GENERATED human+pdf only (no machine root; anti-drift)
#   future/   INTENT        — deferred backlog, each a rehydratable context bundle
#
# Layout is TIME-MAJOR, class-as-subfolder (change the constants below to switch
# to together-by-basename; nothing else hardcodes the shape):
#   development/<drawer>/{machine,human,pdf}/<item>.*     (present: human,pdf only)
#
# Portable bash 3.2 (macOS floor): no mapfile, no readarray, no sed -i, no
# process substitution. Idempotent: re-running scaffold/offload is a no-op.
#
# USAGE:
#   dev-tree.sh scaffold [ROOT]        # create development/{past,present,future}/{...}
#   dev-tree.sh status   [ROOT]        # count items per drawer
#   dev-tree.sh offload  [ROOT] [DEST] # move past/ OUTSIDE the repo (default ../<name>_records/)
#   dev-tree.sh render-present [ROOT] [PLANFILE]  # (stub) note the generate-not-maintain contract
# ROOT defaults to $PWD.
# ============================================================================
set -eu

# ─── LAYOUT CONSTANTS (DEF.layout — the ONE place the shape is defined) ──────
DRAWERS="past present future"
CLASSES_DEFAULT="machine human pdf"
CLASSES_present="human pdf"          # present has NO machine root (anti-drift; RULE.present_generated)
DEVDIR="development"

classes_for(){ # $1 drawer -> the class subdirs for that drawer
  case "$1" in
    present) printf '%s' "$CLASSES_present" ;;
    *)       printf '%s' "$CLASSES_DEFAULT" ;;
  esac
}

ROOT="${2:-$PWD}"
DEV="$ROOT/$DEVDIR"

cmd="${1:-}"
case "$cmd" in
  scaffold)
    made=0
    for d in $DRAWERS; do
      for c in $(classes_for "$d"); do
        target="$DEV/$d/$c"
        if [ ! -d "$target" ]; then mkdir -p "$target"; made=$((made+1)); fi
      done
    done
    # a README stamping the convention into the tree itself (findable by the human)
    rm="$DEV/README.md"
    if [ ! -f "$rm" ]; then
      {
        printf '# development/ — the project development record\n\n'
        printf 'Temporal drawers (see ~/.claude/methodology/DEVELOPMENT_TREE.machine.md):\n\n'
        printf -- '- **past/** — DONE records, dated, safe forever. Offloaded OUT of grep scope when archived.\n'
        printf -- '- **present/** — STATE, as GENERATED human+pdf views (no machine copy — cannot drift). Regenerate from the live plan file.\n'
        printf -- '- **future/** — deferred INTENT, each item a self-contained context bundle the human re-surfaces.\n\n'
        printf 'Each authored durable item = machine `*.machine.md` → human `.md` → rendered `.pdf` (doc-style RULE.functional_pipeline).\n'
      } > "$rm"
      made=$((made+1))
    fi
    printf 'scaffold: %s dir(s)/file(s) created under %s\n' "$made" "$DEV"
    printf 'tree:\n'
    for d in $DRAWERS; do
      printf '  %s/: %s\n' "$d" "$(classes_for "$d" | tr ' ' ',')"
    done
    ;;

  status)
    if [ ! -d "$DEV" ]; then printf 'no development/ tree at %s (run: dev-tree.sh scaffold)\n' "$ROOT"; exit 0; fi
    printf 'development/ status @ %s\n' "$ROOT"
    for d in $DRAWERS; do
      n=0
      if [ -d "$DEV/$d" ]; then
        # count files across class subdirs, exclude the drawer READMEs + dotfiles
        n=$(find "$DEV/$d" -type f ! -name '.*' ! -name 'README.md' 2>/dev/null | wc -l | tr -d ' ')
      fi
      printf '  %-8s %s item-file(s)\n' "$d/" "$n"
    done
    ;;

  offload)
    # move past/ OUTSIDE the working repo so repo-scoped grep never recurses in (RULE.past_offload)
    dest="${3:-$ROOT/../$(basename "$ROOT")_records/development/past}"
    if [ ! -d "$DEV/past" ]; then printf 'nothing to offload: no %s/past\n' "$DEVDIR"; exit 0; fi
    empty=$(find "$DEV/past" -type f ! -name '.*' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$empty" = "0" ]; then printf 'past/ is empty — nothing to offload\n'; exit 0; fi
    mkdir -p "$dest"
    # copy then remove (portable; preserves on failure). Move only regular files/subdirs.
    ( cd "$DEV/past" && find . -type f ! -name '.*' -print ) | while IFS= read -r rel; do
      mkdir -p "$dest/$(dirname "$rel")"
      cp "$DEV/past/$rel" "$dest/$rel"
    done
    printf 'offloaded past/ -> %s\n' "$dest"
    printf 'REVIEW then remove the in-repo copy manually (safety): rm -r "%s"/*\n' "$DEV/past"
    printf '(the offload COPIES; it does not delete the source — you confirm the delete)\n'
    ;;

  render-present)
    # PRESENT is generated-not-maintained. This is a documented STUB: the real
    # generator is platform-specific (CC reads ~/.claude/plans/<name>.md; a hook
    # does it on plan-file write). Here we only assert the contract + staleness stamp.
    plan="${3:-}"
    printf 'render-present: PRESENT holds GENERATED human+pdf views ONLY (RULE.present_generated).\n'
    printf '  source of truth = the live plan file%s\n' "${plan:+ ($plan)}"
    printf '  each render MUST carry a provenance line: source path + mtime/hash + render time (RULE.staleness_stamp),\n'
    printf '  so a stale present view is timestamp-detectable rather than silently divergent.\n'
    printf '  NOTE: automatic regeneration on plan-file write is a Claude-Code hook (register T-16-kin);\n'
    printf '  from here, regenerate on demand and stamp the provenance.\n'
    ;;

  *)
    printf 'usage: dev-tree.sh {scaffold|status|offload|render-present} [ROOT] [DEST|PLANFILE]\n'
    exit 2 ;;
esac
