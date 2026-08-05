#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# capability-audit.sh — CC-side carrier for the capability-audit skill (T-21).
# STATUS: CURRENT (2026-07-12).
#
# Verbs:
#   inventory [ROOT]        list every agent/skill/command under ROOT (default ~/.claude) with its
#                           ownership class (toolkit-authored | third-party | user-owned).
#   cluster   [ROOT]        pairwise description-Jaccard over the inventory; print candidate dup/overlap
#                           pairs (threshold 0.6 duplicate / 0.4 overlap). READ-ONLY.
#   backup PATH [DEST]      copy-then-confirm: copy PATH to DEST (default ~/.claude/_retired/<date>/),
#                           verify, then PRINT the exact `rm` the USER runs. NEVER deletes the source.
#
# The audit itself is READ-ONLY + idempotent. `backup` is the only file-writing verb and it only ever
# COPIES (skip-if-exists) — the destructive `rm` is handed to the user, never executed here.
# Portability: bash-3.2 floor + Linux; no `timeout`, no GNU-only find/sed; BSD-find-safe prune.
set -eo pipefail

CLAUDE_DIR="${CLAUDE_HOME:-$HOME/.claude}"
LIB_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- ownership walk: is_durable() kept byte-in-sync with lib/doc-status.sh --------------------------
#   NOT sourced: doc-status.sh's top level runs its default `check` mode on source (prints a report
#   + touches disk), which would pollute this tool's stdout. An inline copy is the robust reuse the
#   T-21 brief allows ("REUSE doc-status.sh's is_durable+prune logic (OR source it)"). Keep in sync.
is_durable() {
  b="${1##*/}"; case "$b" in .*) return 1 ;; esac
  case "$1" in *_REPORT*|*/xbeep/*|*.pdf) return 1 ;; esac
  case "$1" in */backups/*|*/plugins/*|*/.git/*|*/_retired/*) return 1 ;; esac
  case "$1" in
    *.machine.md) return 0 ;;
    */rules/*.md|*/agents/*.md) return 0 ;;
    */skills/*/SKILL.md) return 0 ;;
    */methodology/*.md) return 0 ;;
    *CLAUDE*.md) return 0 ;;
  esac
  return 1
}

# a MANIFEST, if present next to the toolkit, marks toolkit-authored install targets.
manifest_names() {   # print basenames listed in any MANIFEST.tsv under CLAUDE_DIR (best-effort)
  find "$CLAUDE_DIR" \( -name backups -o -name plugins -o -name .git -o -name _retired \) -prune \
       -o -name 'MANIFEST.tsv' -type f -print 2>/dev/null | while IFS= read -r m; do
    [ -r "$m" ] && cut -f1 "$m" | sed 's#.*/##'
  done
}

status_of() {   # inline copy of doc-status.sh status_of (single source of truth = doc-currency RULE.status_form)
  head -12 "$1" | grep -iE '^(#[[:space:]]*)?STATUS:' | head -1 \
    | sed -E 's/^(#[[:space:]]*)?STATUS:[[:space:]]*//I; s/[[:space:]].*$//' || true
}

# --- enumerate capability docs (agents/*.md, skills/*/SKILL.md, commands/*.md) --------------------
enumerate() {
  root="${1:-$CLAUDE_DIR}"
  find "$root" \( -name backups -o -name plugins -o -name .git -o -name _retired \) -prune -o \
    \( -path '*/agents/*.md' -o -path '*/skills/*/SKILL.md' -o -path '*/commands/*.md' \) -type f -print 2>/dev/null \
    | grep -v '/\._' | sort
}

# --- ownership class for one path -----------------------------------------------------------------
_MANIFEST_CACHE=""
classify() {   # echo: toolkit | thirdparty | user
  p="$1"; b="${p##*/}"
  case "$p" in */plugins/*|*/backups/*|*/.git/*) echo thirdparty; return ;; esac
  # toolkit-authored: has a STATUS header OR is listed in a MANIFEST
  if [ -n "$(status_of "$p")" ]; then echo toolkit; return; fi
  [ -z "$_MANIFEST_CACHE" ] && _MANIFEST_CACHE="$(manifest_names)"
  case "
$_MANIFEST_CACHE
" in *"
$b
"*) echo toolkit; return ;; esac
  echo user
}

# --- description extraction (YAML frontmatter `description:` for skills/commands; first prose for agents) ---
desc_of() {
  # skills/commands carry a `description:` in YAML frontmatter; agents carry it too (or a lead line).
  awk '
    NR==1 && $0=="---" {fm=1; next}
    fm && /^description:/ {sub(/^description:[[:space:]]*/,""); print; exit}
    fm && $0=="---" {fm=0}
  ' "$1" 2>/dev/null | head -1
}

cmd_inventory() {
  root="${1:-$CLAUDE_DIR}"
  printf '%-52s  %-11s  %s\n' "PATH (rel)" "OWNERSHIP" "KIND"
  printf '%-52s  %-11s  %s\n' "----------" "---------" "----"
  enumerate "$root" | while IFS= read -r p; do
    rel="${p#$root/}"
    case "$p" in */agents/*) kind=agent ;; */skills/*) kind=skill ;; */commands/*) kind=command ;; *) kind=? ;; esac
    printf '%-52s  %-11s  %s\n' "$rel" "$(classify "$p")" "$kind"
  done
}

# --- cluster: pairwise Jaccard on descriptions (python3 does the O(n^2); trivial for a small corpus) ---
cmd_cluster() {
  root="${1:-$CLAUDE_DIR}"
  command -v python3 >/dev/null 2>&1 || { echo "cluster needs python3" >&2; exit 0; }
  # emit "path<TAB>description" lines, feed to python3
  tmp="$(mktemp 2>/dev/null || echo /tmp/capaud.$$)"
  enumerate "$root" | while IFS= read -r p; do
    printf '%s\t%s\n' "${p#$root/}" "$(desc_of "$p")"
  done > "$tmp"
  python3 - "$tmp" <<'PY'
import sys, re
rows=[]
for line in open(sys.argv[1], encoding="utf-8"):
    if "\t" not in line: continue
    path, desc = line.rstrip("\n").split("\t", 1)
    rows.append((path, desc))
def words(s): return set(re.findall(r"[a-z0-9]+", s.lower()))
def jac(a,b):
    A,B=words(a),words(b)
    return len(A&B)/len(A|B) if A and B else 0.0
flagged=[]
for i in range(len(rows)):
    for j in range(i+1,len(rows)):
        s=jac(rows[i][1], rows[j][1])
        if s>=0.4:
            tag="DUPLICATE" if s>=0.6 else "overlap"
            flagged.append((s,tag,rows[i][0],rows[j][0]))
flagged.sort(reverse=True)
if not flagged:
    print("no candidate dup/overlap pairs (Jaccard >= 0.4)")
else:
    print("Jaccard  kind       pair")
    for s,tag,a,b in flagged:
        print("%.3f    %-9s  %s  <>  %s" % (s,tag,a,b))
PY
  rm -f "$tmp"
}

# --- backup: copy-then-confirm (never deletes the source) -----------------------------------------
cmd_backup() {
  src="$1"; [ -z "$src" ] && { echo "usage: capability-audit.sh backup PATH [DEST_DIR]" >&2; exit 2; }
  [ -e "$src" ] || { echo "no such path: $src" >&2; exit 2; }
  dest="${2:-$CLAUDE_DIR/_retired/$(date +%Y-%m-%d)}"
  mkdir -p "$dest"
  base="${src##*/}"
  target="$dest/$base"
  if [ -e "$target" ]; then
    echo "already backed up (skip-if-exists): $target"
  else
    cp -R "$src" "$target"
    echo "COPIED: $src -> $target"
  fi
  # VERIFY
  if [ -r "$target" ]; then
    echo "VERIFIED present + readable: $target"
    echo
    echo "SOURCE STILL EXISTS. To remove the now-redundant source, YOU run:"
    echo "    rm -r \"$src\""
    echo "(un-retire later with: cp -R \"$target\" \"$src\")"
  else
    echo "VERIFY FAILED — source NOT removed. Investigate before deleting anything." >&2
    exit 1
  fi
}

case "${1:-}" in
  inventory) shift; cmd_inventory "$@" ;;
  cluster)   shift; cmd_cluster "$@" ;;
  backup)    shift; cmd_backup "$@" ;;
  *) echo "usage: capability-audit.sh {inventory|cluster|backup} [args]" >&2; exit 2 ;;
esac
