#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# stale_move.sh — move-and-tombstone a retired file into Stale_Trash/.
# STATUS: CURRENT (2026-07-30). Ships in the CRT payload lib/ (installed to ~/.claude/lib/); mechanizes the move-AND-tombstone contract — see rules/project-structure-standard.machine.md RULE.stale_trash. ADAPTED 2026-07-30 (Hc) from planner-kit v1.1 dev/tools/stale_move.sh; logic byte-identical, provenance header only.
# CONTRACT (Stale_Trash, F1-grounded): MOVE-AND-TOMBSTONE, never move-instead-of-tombstone.
#   Tombstone FIRST (in-band marker written into the file), THEN relocate; content is never lost.
# INVARIANTS: bash 3.2 · spaces-in-paths safe (quote everything) · ZERO deletes of content
#   (the relocation is `mv`; the only `rm` is the script's OWN temp on the error path) · all
#   refusal cases gated · run FROM the project root.
# USAGE: bash dev/tools/stale_move.sh [--dry-run] [--stub] <file> "<superseded-by: canonical path or reason>"
#   --dry-run  print every action, write NOTHING.
#   --stub     leave a <=2-line pointer stub at the old path (default: no stub).
# EXIT: 0 ok / dry-run · 1 refusal or execution error · 2 usage error.

set -u

PROG="stale_move.sh"
tmp=""            # script-owned temp (atomic prepend); init early for the EXIT trap under `set -u`
OPEN="# "         # comment-open  (default; adapted per extension by comment_style)
CLOSE=""          # comment-close (default; "" for #, " -->" for html)

usage() {
  cat >&2 <<EOF
Usage: bash dev/tools/$PROG [--dry-run] [--stub] <file> "<superseded-by: canonical path or reason>"
  Run FROM the project root. Prepends an in-band SUPERSEDED tombstone to a retired
  regular file, moves it to Stale_Trash/<path-encoded name>, and appends a
  REGISTER_DELTA row. Content is never deleted (the move is 'mv').
    --dry-run  print all actions, write nothing.
    --stub     leave a <=2-line pointer stub at the old path (default: no stub).
  Exit: 0 ok/dry-run; 1 refusal/error; 2 usage.
EOF
}

die()    { echo "$PROG: $*" >&2; usage; exit 2; }     # usage error
refuse() { echo "$PROG: REFUSED: $*" >&2; exit 1; }   # pre-execution validation refusal
fail()   { echo "$PROG: ERROR: $*"   >&2; exit 1; }   # execution-time failure

# Set OPEN/CLOSE comment delimiters from $1's extension: html/htm => <!-- -->, else # .
comment_style() {
  local b ext extlc
  b=$(basename "$1")
  case "$b" in
    *.*) ext="${b##*.}" ;;
    *)   ext="" ;;
  esac
  extlc=$(printf '%s' "$ext" | tr 'A-Z' 'a-z')
  case "$extlc" in
    html|htm) OPEN="<!-- "; CLOSE=" -->" ;;
    *)        OPEN="# ";    CLOSE="" ;;
  esac
}

# ------------------------------------------------------------------ parse args
DRYRUN=0
STUB=0
POS=()
endopts=0
while [ "$#" -gt 0 ]; do
  if [ "$endopts" -eq 0 ]; then
    case "$1" in
      --dry-run) DRYRUN=1; shift; continue ;;
      --stub)    STUB=1;   shift; continue ;;
      -h|--help) usage; exit 0 ;;
      --)        endopts=1; shift; continue ;;
      --*)       die "unknown option: $1" ;;
    esac
  fi
  POS+=("$1"); shift
done

[ "${#POS[@]}" -eq 2 ] || die "expected exactly 2 arguments (file and superseded-by text), got ${#POS[@]}"
FILE="${POS[0]}"
SUPTEXT="${POS[1]}"

[ -n "$SUPTEXT" ] || die "superseded-by text must be non-empty"
nl=$'\n'
case "$SUPTEXT" in
  *"$nl"*) die "superseded-by text must be a single line (no newlines)" ;;
esac

# ------------------------------------------------------- resolve root + ledger
ROOT=$(pwd -P) || refuse "cannot determine project root (pwd failed)"
LEDGER="$ROOT/dev/REGISTER_DELTA.machine.md"
LEDGER_DIR="$ROOT/dev"
[ -d "$LEDGER_DIR" ] || refuse "ledger directory dev/ not found — run from the project root"
[ -f "$LEDGER" ] || refuse "ledger not found at dev/REGISTER_DELTA.machine.md — run from the project root"
# B1 pre-check: the ledger append is the LAST step, AFTER the irreversible tombstone+move.
# Validate writability HERE so a read-only ledger is refused BEFORE any mutation — never leaving
# a file moved+tombstoned with no REGISTER_DELTA row (partial completion).
[ -w "$LEDGER" ] || refuse "ledger is not writable: dev/REGISTER_DELTA.machine.md (refusing before any move so the file is never relocated without its REGISTER_DELTA row)"

# --------------------------------------------- existence / type gates (ordered)
if [ -L "$FILE" ]; then
  refuse "target is a symlink; symlinks are not supported in v1: $FILE"
elif [ ! -e "$FILE" ]; then
  refuse "target does not exist: $FILE"
elif [ -d "$FILE" ]; then
  refuse "target is a directory; directories are not supported in v1: $FILE"
elif [ ! -f "$FILE" ]; then
  refuse "target is not a regular file: $FILE"
fi

# absolute, symlink-resolved path of the target (its dir exists — -f passed)
tdir=$(cd "$(dirname "$FILE")" && pwd -P) || refuse "cannot resolve target directory"
tbase=$(basename "$FILE")
TARGET_ABS="$tdir/$tbase"

# inside the project root?
case "$TARGET_ABS" in
  "$ROOT"/*) : ;;
  *) refuse "target is outside the project root: $TARGET_ABS" ;;
esac
# never re-process something already retired
case "$TARGET_ABS" in
  "$ROOT"/Stale_Trash/*) refuse "target is already under Stale_Trash/: $TARGET_ABS" ;;
esac

# relative path -> path-encoded destination (origin recoverable: '/' => '__')
REL="${TARGET_ABS#$ROOT/}"
ENCODED="${REL//\//__}"
DEST="$ROOT/Stale_Trash/$ENCODED"
DEST_REL="Stale_Trash/$ENCODED"

# already carries a tombstone? (first line holds the SUPERSEDED marker)
first_line=""
IFS= read -r first_line < "$TARGET_ABS" || true
case "$first_line" in
  *"STATUS: SUPERSEDED (moved to Stale_Trash"*)
    refuse "target already carries a SUPERSEDED tombstone (already staled/moved): $REL" ;;
esac

# retain-don't-delete: never clobber a file already retained under the encoded name
if [ -e "$DEST" ]; then
  refuse "destination already exists (would clobber a retained stale file): $DEST_REL"
fi

# ---------------------------------------------- compose tombstone + ledger row
DATE=$(date +%Y-%m-%d)
comment_style "$TARGET_ABS"
CORE="STATUS: SUPERSEDED (moved to Stale_Trash ${DATE}). ${SUPTEXT}. Do not use as current context."
TOMB="${OPEN}${CORE}${CLOSE}"

# REGISTER_DELTA is a 5-column table (date | change | files touched | register impact | efficacy
# row); carry the brief's atoms (date, STALE-MOVED old->new, reason) into that schema, escaping
# any pipe in the free text so the row stays well-formed.
esc_text="${SUPTEXT//|/\\|}"
CHANGE="STALE-MOVED ${REL} → ${DEST_REL}. ${esc_text}"
ROW="| ${DATE} | ${CHANGE} | ${DEST_REL} | none | — |"

# --------------------------------------------------- dry-run: plan, write none
if [ "$DRYRUN" -eq 1 ]; then
  if [ "$STUB" -eq 1 ]; then stub_desc="yes (pointer stub left at $REL)"; else stub_desc="no"; fi
  cat <<EOF
DRY-RUN — no changes written.
  target file : $REL
  tombstone   : $TOMB
  move        : $REL  →  $DEST_REL
  stub        : $stub_desc
  ledger row  : $ROW
    (would append to dev/REGISTER_DELTA.machine.md)
EOF
  exit 0
fi

# ------------------------------------------------------------------- execute
# Cleanup removes ONLY the script's own temp, and only if it survives (i.e. an
# error struck before the temp was consumed by mv). Never touches user content.
cleanup() { if [ -n "$tmp" ] && [ -e "$tmp" ]; then rm -f "$tmp"; fi; return 0; }
trap cleanup EXIT

# (1) Prepend the tombstone in place, atomically: build tombstone+original into a
#     temp on the SAME filesystem, then rename over the target (atomic, non-lossy).
tmp=$(mktemp "$tdir/.stale_move_tmp.XXXXXX") || fail "cannot create temp file in $tdir"
{ printf '%s\n' "$TOMB" && cat "$TARGET_ABS"; } > "$tmp" || fail "failed writing tombstoned content"
mv "$tmp" "$TARGET_ABS" || fail "failed to update target with tombstone"
tmp=""   # consumed by mv; trap is now a no-op

# (2) Relocate into Stale_Trash — the move is a pure `mv`; content is preserved.
mkdir -p "$(dirname "$DEST")" || fail "cannot create Stale_Trash destination dir"
mv "$TARGET_ABS" "$DEST" || fail "move to Stale_Trash failed (file remains tombstoned at $REL)"

# (3) Optional <=2-line pointer stub at the old path (line 1 carries the marker so
#     a re-run is refused as already-stale).
if [ "$STUB" -eq 1 ]; then
  {
    printf '%s\n' "${OPEN}STATUS: SUPERSEDED (moved to Stale_Trash ${DATE}). Relocated to ${DEST_REL}. ${SUPTEXT}. Do not use as current context.${CLOSE}"
    printf '%s\n' "${OPEN}Pointer stub — original content retained at ${DEST_REL}.${CLOSE}"
  } > "$TARGET_ABS" || fail "failed to write pointer stub at $REL"
fi

# (4) Append the ledger row (append-only; ensure the last existing row is newline-terminated).
#     Writability was pre-validated above (B1); this is the TOCTOU belt — if the ledger became
#     unwritable AFTER the move, name the completed relocation and the row to add by hand.
if [ -n "$(tail -c1 "$LEDGER" 2>/dev/null)" ]; then
  printf '\n' >> "$LEDGER" || fail "moved+tombstoned $REL → $DEST_REL, but the ledger could not be written (trailing-newline normalize failed); manually add this row to dev/REGISTER_DELTA.machine.md: $ROW"
fi
printf '%s\n' "$ROW" >> "$LEDGER" || fail "moved+tombstoned $REL → $DEST_REL, but appending the REGISTER_DELTA row FAILED; manually add this row to dev/REGISTER_DELTA.machine.md: $ROW"

# ------------------------------------------------------------------- report
if [ "$STUB" -eq 1 ]; then stub_done="left at $REL"; else stub_done="none"; fi
cat <<EOF
STALE-MOVED (ok):
  tombstoned  : line 1 = $TOMB
  moved       : $REL  →  $DEST_REL
  stub        : $stub_done
  ledger      : appended 1 row to dev/REGISTER_DELTA.machine.md
EOF
exit 0
