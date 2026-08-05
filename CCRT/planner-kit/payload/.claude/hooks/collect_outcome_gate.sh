#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# collect_outcome_gate.sh — Stop hook. ONE nudge, never a loop.
#
# WHAT: when a turn collected subagent results and the reply names no COLLECT outcome,
#   ask once for it. An unnamed outcome defaults silently to CONTINUE, which is how a
#   plan outlives the evidence that justified it.
#
# CONTRACT (bash-hook-contract):
#   IN  : one JSON object on STDIN. Load-bearing: stop_hook_active, transcript_path.
#   OUT : STDOUT is EITHER empty (silent pass) OR exactly one {"decision":"block",
#         "reason":...} object. A Stop hook has no advisory-only channel — `block` is the
#         only way to put text in front of the model, and it costs one extra turn.
#   EXIT: 0 ALWAYS. Any internal error => INDETERMINATE => fail open, and log it.
#   LOOP GUARD: stop_hook_active is set once this hook has already blocked in this stop
#         sequence => pass unconditionally. That is what makes the nudge fire at most once.
#   BLAST: read-only. Reads stdin plus the transcript file the payload names.
#
# SIGNAL (stated plainly because it is the load-bearing assumption): "this turn saw
#   subagent results" is read from the TRANSCRIPT, restricted to the window after the last
#   genuine user message. Three independent tells, any one sufficient — a `tool_use` block
#   named Task, an `isSidechain` record, or the same pair found by raw-line match when the
#   structured shape differs. No tell => silent. The gate never blocks on a turn it cannot
#   read.
#
# SWITCH: PLANNER_KIT_HOOKS=off silences this hook.
set -eo pipefail   # NOT set -u — maybe-unset vars are guarded with ${x:-}

[ "${PLANNER_KIT_HOOKS:-on}" != "on" ] && exit 0

_log() {
  local d="${PLANNER_KIT_LOG_DIR:-${CLAUDE_PROJECT_DIR:-.}/.claude/logs}"
  mkdir -p "$d" 2>/dev/null || return 0
  printf '%s collect_outcome_gate: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" \
    >> "$d/planner-kit-hooks.log" 2>/dev/null || true
}

input="$(cat 2>/dev/null || true)"
[ -z "${input:-}" ] && exit 0
command -v python3 >/dev/null 2>&1 || { _log "python3 absent => fail-open"; exit 0; }

_outf="${TMPDIR:-/tmp}/pkcog_out.$$"
_errf="${TMPDIR:-/tmp}/pkcog_err.$$"

set +e
python3 - "$input" <<'PYEOF' >"$_outf" 2>"$_errf"
import json, os, re, sys

try:
    obj = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
if not isinstance(obj, dict):
    sys.exit(0)

# LOOP GUARD first: already nudged in this stop sequence => let it stop.
if obj.get("stop_hook_active"):
    sys.exit(0)

tp = obj.get("transcript_path")
if not isinstance(tp, str) or not tp or not os.path.isfile(tp):
    sys.exit(0)

records = []
try:
    with open(tp, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                r = json.loads(raw)
            except Exception:
                r = None
            records.append((raw, r))
except Exception:
    sys.exit(0)
if not records:
    sys.exit(0)


def blocks(rec):
    """content blocks of a record, whichever nesting this transcript version uses."""
    if not isinstance(rec, dict):
        return []
    m = rec.get("message") if isinstance(rec.get("message"), dict) else rec
    c = m.get("content")
    return c if isinstance(c, list) else []


def role_of(rec):
    if not isinstance(rec, dict):
        return None
    m = rec.get("message") if isinstance(rec.get("message"), dict) else rec
    return m.get("role") or rec.get("type")


def text_of(rec):
    if not isinstance(rec, dict):
        return ""
    m = rec.get("message") if isinstance(rec.get("message"), dict) else rec
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


# ---------- turn window: everything after the last GENUINE user message -----------
# A tool_result envelope is role=user too — it is mid-turn, not a new prompt.
start = 0
for i, (_raw, r) in enumerate(records):
    if role_of(r) != "user":
        continue
    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks(r)):
        continue
    start = i
window = records[start:]

# ---------- did this turn collect subagent results? -------------------------------
RAW_TOOLUSE = re.compile(r'"type"\s*:\s*"tool_use"')
RAW_TASK = re.compile(r'"name"\s*:\s*"Task"')
RAW_SIDE = re.compile(r'"isSidechain"\s*:\s*true')

saw = False
for raw, r in window:
    if isinstance(r, dict) and r.get("isSidechain") is True:
        saw = True
        break
    for b in blocks(r):
        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Task":
            saw = True
            break
    if saw:
        break
    if (RAW_TOOLUSE.search(raw) and RAW_TASK.search(raw)) or RAW_SIDE.search(raw):
        saw = True
        break

if not saw:
    sys.exit(0)

# ---------- does the final reply name an outcome? ---------------------------------
final = ""
for _raw, r in window:
    if role_of(r) == "assistant":
        t = text_of(r)
        if t.strip():
            final = t
if not final.strip():
    sys.exit(0)   # nothing to read => INDETERMINATE => fail open

OUTCOME = re.compile(r"(?<![A-Za-z0-9])(CONTINUE|RE-ROUTE|REROUTE|FIX-FIRST|ABORT|"
                     r"GOAL-MET|ADAPT)(?![A-Za-z0-9])", re.I)
if OUTCOME.search(final):
    sys.exit(0)

print(json.dumps({"decision": "block", "reason": (
    "This turn collected subagent results but the reply names no COLLECT outcome. Name "
    "exactly one — CONTINUE | RE-ROUTE | FIX-FIRST | ABORT | GOAL-MET | ADAPT — with the "
    "receipts you spot-checked, then stop. An unnamed outcome defaults silently to "
    "CONTINUE, which is how a plan outlives the evidence that justified it.")}))
PYEOF
rc=$?
set -e

verdict="$(cat "$_outf" 2>/dev/null || true)"
err="$(cat "$_errf" 2>/dev/null || true)"
rm -f "$_outf" "$_errf" 2>/dev/null || true

if [ "$rc" -ne 0 ]; then
  _log "INDETERMINATE rc=$rc => fail-open: $(printf '%s' "$err" | head -1)"
  exit 0
fi

if [ -n "${verdict:-}" ]; then
  case "$verdict" in
    \{*\}) printf '%s\n' "$verdict"
           _log "nudge emitted (outcome token absent after a subagent collect)" ;;
    *)     _log "INDETERMINATE: gate stdout was not a JSON object => fail-open" ;;
  esac
fi
exit 0
