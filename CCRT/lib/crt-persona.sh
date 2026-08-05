#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# STATUS: CURRENT (2026-07-27). Primary-persona default helper (settings.json "agent" key).
# ============================================================================
# crt-persona.sh — set / clear the DEFAULT PERSONA of every new Claude Code session
# ----------------------------------------------------------------------------
# CONTRACT. Claude Code's settings.json carries a top-level "agent" key naming the agent a
# session starts as. Merging {"agent":"planner"} therefore makes the toolkit's PLANNER agent
# the DEFAULT PERSONA of the whole install — not something you opt into per task, but the
# voice Claude Code boots with on EVERY new session until you say otherwise. That is a
# deliberately heavy default, so it is deliberately cheap to escape: `claude --agent <name>`
# overrides it for ONE session (per `claude --help`: "Agent for the current session. Overrides
# the 'agent' setting"), `claude --safe-mode` starts with all customizations off, and
# `crt-persona.sh off` removes the key entirely. `on` is ADDITIVE — it deep-merges the one-key
# fragment via lib/merge_settings.py, so nothing else in settings.json is touched. `off` is a
# DELETE, and delete is exactly why it must NOT route through merge_settings.py: that tool
# merges (a fragment can add or overwrite a key, never remove one) and has no delete path, so
# `off` owns a small inline python3 that pops the key and atomically os.replace()s the file.
#
# PATH RESOLUTION (first hit wins; the two layouts below, checked in this order):
#   merge_settings.py      1. <dir of this script>/merge_settings.py                        (toolkit repo: lib/)
#                          2. $CLAUDE_DIR/lib/merge_settings.py                             (installed)
#   persona.fragment.json  1. <dir of this script>/../payload/settings/persona.fragment.json (toolkit repo)
#                          2. $CLAUDE_DIR/settings-fragments/persona.fragment.json           (installed)
#   settings.json          $CLAUDE_DIR/settings.json  (the one file this script ever writes)
#   $CLAUDE_DIR defaults to ${CLAUDE_HOME:-$HOME/.claude} (house convention, cf. crt-mode.sh);
#   an explicit $CLAUDE_DIR always wins. Only `on` needs the two assets, so `off`/`show` still
#   work on a machine where neither layout is present.
#
# SAFETY: settings.json is validated as JSON BEFORE any write (a corrupt file is never
# clobbered) and backed up to settings.json.bak-<TS> before every mutation. `off` on a file
# with no "agent" key writes nothing at all.
#
# USAGE:
#   crt-persona.sh on      # deep-merge {"agent":"planner"} into $CLAUDE_DIR/settings.json
#   crt-persona.sh off     # remove the "agent" key (the ONLY delete path)
#   crt-persona.sh show    # print the current "agent" value (or "unset") + the escapes
#   crt-persona.sh --help
# EXIT: 0 ok · 1 environment/IO error (missing asset, corrupt settings.json) · 64 usage.
# NOTE: unlike crt-mode.sh, a BARE invocation is a usage error (exit 64), not an implicit
# --show — a persona default is heavy enough that the verb should always be explicit.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" && pwd -P)"
CLAUDE_DIR="${CLAUDE_DIR:-${CLAUDE_HOME:-$HOME/.claude}}"
SETTINGS="$CLAUDE_DIR/settings.json"
SELF="$(basename "${BASH_SOURCE[0]:-$0}")"

usage(){ sed -n '2,/^[^#]/p' "${BASH_SOURCE[0]:-$0}" | sed -n 's/^# \{0,1\}//p'; exit "${1:-0}"; }

die(){ echo "$SELF: $1" >&2; exit "${2:-1}"; }

ts(){ date +%Y%m%d-%H%M%S; }

need_python(){
  command -v python3 >/dev/null 2>&1 || die "python3 not found on PATH (required to edit settings.json)"
}

# Resolve the two assets `on` needs. Lazy: never called by off/show.
MERGE=""; FRAG=""
resolve_assets(){
  local c
  for c in "$SCRIPT_DIR/merge_settings.py" "$CLAUDE_DIR/lib/merge_settings.py"; do
    if [ -f "$c" ]; then MERGE="$c"; break; fi
  done
  for c in "$SCRIPT_DIR/../payload/settings/persona.fragment.json" \
           "$CLAUDE_DIR/settings-fragments/persona.fragment.json"; do
    if [ -f "$c" ]; then FRAG="$c"; break; fi
  done
  if [ -z "$MERGE" ]; then
    echo "$SELF: cannot find merge_settings.py. Searched:" >&2
    echo "  $SCRIPT_DIR/merge_settings.py" >&2
    echo "  $CLAUDE_DIR/lib/merge_settings.py" >&2
    exit 1
  fi
  if [ -z "$FRAG" ]; then
    echo "$SELF: cannot find persona.fragment.json. Searched:" >&2
    echo "  $SCRIPT_DIR/../payload/settings/persona.fragment.json" >&2
    echo "  $CLAUDE_DIR/settings-fragments/persona.fragment.json" >&2
    exit 1
  fi
}

# Fail closed: refuse to touch a settings.json we cannot parse (never clobber a corrupt file).
validate_settings(){
  [ -f "$SETTINGS" ] || return 0
  [ -s "$SETTINGS" ] || return 0
  if ! python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$SETTINGS" 2>/dev/null; then
    die "$SETTINGS is not valid JSON — refusing to edit it. Fix or restore it first."
  fi
}

backup_settings(){
  local bak
  if [ -f "$SETTINGS" ]; then
    bak="$SETTINGS.bak-$(ts)"          # stamp ONCE — two ts() calls can straddle a second boundary
    cp "$SETTINGS" "$bak"
    echo "backup: $bak"
  fi
}

cmd_on(){
  need_python
  resolve_assets
  validate_settings
  mkdir -p "$CLAUDE_DIR"
  backup_settings
  python3 "$MERGE" "$SETTINGS" "$FRAG"
  echo "persona default set: agent = planner  ->  $SETTINGS"
  echo "  fragment: $FRAG"
  echo "Takes effect on the NEXT new session. Per-session override: claude --agent <name>.  Remove: $SELF off"
}

cmd_off(){
  need_python
  if [ ! -f "$SETTINGS" ]; then
    echo "no settings.json at $SETTINGS — nothing to remove."
    return 0
  fi
  validate_settings
  python3 - "$SETTINGS" "$SETTINGS.bak-$(ts)" <<'PY'
# DELETE PATH — deliberately NOT merge_settings.py. That tool deep-MERGES: a fragment can add or
# overwrite a key, never remove one, so it has no way to express this operation. Here: read, pop,
# write a sibling .tmp using merge_settings.py's exact formatting (indent=2 + trailing newline, so
# an on -> off round-trip is byte-clean), then os.replace() it over the target — atomic on POSIX,
# so a crash mid-write can never leave a truncated settings.json. Nothing is written, and no
# backup is taken, when the key is already absent.
import json, os, shutil, sys

path, bak = sys.argv[1], sys.argv[2]
with open(path) as f:
    raw = f.read()
data = json.loads(raw) if raw.strip() else {}
if not isinstance(data, dict):
    sys.stderr.write("crt-persona: %s is not a JSON object - refusing to edit\n" % path)
    sys.exit(1)
if "agent" not in data:
    print('agent: unset already - nothing to remove  (%s)' % path)
    sys.exit(0)
old = data.pop("agent")
shutil.copy2(path, bak)
print("backup: %s" % bak)
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.replace(tmp, path)
print('removed "agent": %s  ->  %s' % (json.dumps(old), path))
PY
  echo "New sessions start with no default persona. Re-enable: $SELF on"
}

cmd_show(){
  need_python
  python3 - "$SETTINGS" <<'PY'
import json, os, sys

path = sys.argv[1]
val = None
if os.path.exists(path) and os.path.getsize(path) > 0:
    try:
        with open(path) as f:
            data = json.load(f)
    except ValueError as e:
        sys.stderr.write("crt-persona: %s is not valid JSON (%s)\n" % (path, e))
        sys.exit(1)
    if not isinstance(data, dict):
        sys.stderr.write("crt-persona: %s is not a JSON object\n" % path)
        sys.exit(1)
    val = data.get("agent")
shown = "unset" if val is None else (val if isinstance(val, str) else json.dumps(val))
print("agent = %s   (%s)" % (shown, path))
PY
  cat <<NOTE
  This is the DEFAULT persona of every NEW session, not a per-task choice.
  per-session override : claude --agent <name>   ("Overrides the 'agent' setting" - claude --help)
  escapes              : claude --agent <other>  |  claude --safe-mode  (all customizations off)
  remove the default   : $SELF off
NOTE
}

if [ "$#" -gt 1 ]; then
  echo "$SELF: too many arguments (expected exactly one of: on | off | show)" >&2; echo >&2
  usage 64 >&2
fi

case "${1:-}" in
  on)                   cmd_on ;;
  off)                  cmd_off ;;
  show|--show|--status) cmd_show ;;
  -h|--help)            usage 0 ;;
  "")                   echo "$SELF: missing subcommand (expected: on | off | show)" >&2; echo >&2; usage 64 >&2 ;;
  *)                    echo "$SELF: unknown subcommand '$1' (expected: on | off | show)" >&2; echo >&2; usage 64 >&2 ;;
esac
