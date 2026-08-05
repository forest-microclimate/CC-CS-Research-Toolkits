#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# ============================================================================
# Timeline Logger Hook — durable, decomposed-timestamp record of session events
# ----------------------------------------------------------------------------
# WHY: AI agents have a poor internal sense of elapsed time. This writes one
#   JSONL row per session event (user prompt, each tool use, turn end) so there
#   is a durable, cheap-to-read record of WHAT happened WHEN and HOW LONG it took
#   — without mining the giant transcripts.
#
# REGISTER (in core.fragment.json) on multiple events, passing the event name as
#   an explicit ARG (do not rely on a stdin field being present):
#     UserPromptSubmit -> bash ".../timeline-logger.sh" UserPromptSubmit
#     PostToolUse      -> bash ".../timeline-logger.sh" PostToolUse
#     Stop             -> bash ".../timeline-logger.sh" Stop
#   (SessionStart/SessionEnd/PreToolUse may be added the same way.)
#
# TIMESTAMP SCHEMA (decomposed + one machine field):
#   tz "UTC+10:00" · tz_name "AEST" · year "2026" · month "07" · day "10"
#   · hour_min_ss "22:12:18"   (all human-readable, group-able, no parsing)
#   · epoch_ms 1783685538000   (integer — exact duration math: t1 - t0;
#                               = 2026-07-10 22:12:18 UTC+10:00, matches the fields above)
#   The tz field is written EXPLICITLY as UTC±HH:MM (reference + direction stated)
#   so it can't be misread; a bare "+10:00" is correct ISO but convention-dependent,
#   and POSIX Etc/GMT+X is sign-inverted — this form sidesteps both. epoch_ms is the
#   unambiguous machine value for any duration computation.
# Human reads the decomposed fields; the reader computes durations off epoch_ms.
#
# GUARANTEES: never breaks the session (any error => exit 0); cheap (one python3
#   process per event — python3 is already a hard install.sh dependency); log
#   path overridable via $CRT_TIMELINE_LOG (default ~/.claude/logs/timeline.jsonl).
# ORIGIN: claude-research-toolkit, 2026-07. Companion reader: lib/timeline-report.py
# ============================================================================
set -eo pipefail

# --- (0) recursion guard: skip logging inside a `claude -p` adversary fork
#         (mirrors stop-adversary-gate.sh §0). Without it, each forked adversary's
#         OWN hook events leak into this log keyed to the fork's session_id,
#         inflating the session/turn counts a naive reader computes. ------------
if [ -n "${CRT_ADVERSARY_ACTIVE:-}" ]; then exit 0; fi

# --- (0a) CRT MASTER SWITCH: on (default) | observe | off ----------------------
#   Shared toolkit on/off control (see methodology/CRT_MASTER_SWITCH.machine.md).
#   This hook is a PURE OBSERVER, not an intervention — so it keeps logging in BOTH
#   "on" and "observe" (the shadow arm still needs its timeline). Only "off" silences
#   it, giving the research OFF-arm a run with NO toolkit footprint at all. Every row
#   carries "mode" so a mixed log self-partitions by arm (parallel to build_id).
#   $CRT_MODE env wins over ~/.claude/crt_mode.
_crt_mode="${CRT_MODE:-}"
if [ -z "$_crt_mode" ]; then
  _cmf="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"
  [ -r "$_cmf" ] && _crt_mode="$(tr -d '[:space:]' < "$_cmf" 2>/dev/null || true)"
fi
_crt_mode="${_crt_mode:-on}"
[ "$_crt_mode" = "off" ] && exit 0

EVENT="${1:-unknown}"
CRT_TIMELINE_LOG="${CRT_TIMELINE_LOG:-$HOME/.claude/logs/timeline.jsonl}"
input="$(cat 2>/dev/null || true)"

# Emit one JSONL row. House pattern (cf. post-edit-review.sh): feed the hook input
#   on STDIN via a pipe and pass the script as a SINGLE-QUOTED `-c` literal, so the
#   script text and the JSON data travel on SEPARATE channels. (`python3 - <<HEREDOC`
#   plus a stdin pipe collides on the stdin fd and silently drops the enrichment.)
#   The script below therefore contains NO single quotes.
{ mkdir -p "$(dirname "$CRT_TIMELINE_LOG")" 2>/dev/null
  printf '%s' "$input" | CRT_EVENT="$EVENT" CRT_MODE_VAL="${_crt_mode:-on}" python3 -c '
import sys, os, json, time, datetime
try: d = json.load(sys.stdin)
except Exception: d = {}
now = time.time()
dt  = datetime.datetime.now().astimezone()
off = dt.strftime("%z")                       # e.g. +1000  (ISO %z; NOT inverted)
# Human-facing offset, made EXPLICIT: "UTC+10:00" states reference (UTC) and
# direction (+ = ahead of UTC). A bare "+10:00" is correct ISO but forces the
# reader to know the convention (and the POSIX Etc/GMT+X form is sign-INVERTED,
# a well-known trap). epoch_ms below is the unambiguous machine field regardless.
tz_expl = ("UTC" + off[:3] + ":" + off[3:]) if len(off) == 5 else ("UTC" + off if off else "UTC+00:00")
rec = {
    "tz":          tz_expl,                   # UTC+10:00 / UTC-05:00 / UTC+05:30
    "tz_name":     dt.strftime("%Z"),         # e.g. AEST
    "year":        dt.strftime("%Y"),         # XXXX
    "month":       dt.strftime("%m"),         # XX
    "day":         dt.strftime("%d"),         # XX
    "hour_min_ss": dt.strftime("%H:%M:%S"),   # XX:XX:XX (%H is 24-hour 00-23, no AM/PM)
    "epoch_ms":    int(now * 1000),           # machine field for exact durations
    "event":       os.environ.get("CRT_EVENT", ""),
    "session_id":  d.get("session_id", ""),
    "mode":        os.environ.get("CRT_MODE_VAL", "on"),   # on|observe — which switch arm produced this row
}
# build/version provenance: which toolkit build emitted this row (install.sh writes
# toolkit_build.json; a mixed log then self-partitions by version). Best-effort: an
# absent/unreadable stamp just omits the field — never break the row over it.
try:
    _bf = os.environ.get("CRT_BUILD_FILE") or os.path.join(os.path.expanduser("~"), ".claude", "toolkit_build.json")
    with open(_bf) as _fh:
        _bid = (json.load(_fh) or {}).get("build_id", "")
    if _bid: rec["build_id"] = _bid
except Exception:
    pass
# event-specific enrichment (best-effort; omit keys that are absent)
tn = d.get("tool_name")
if tn: rec["tool_name"] = tn
ti = d.get("tool_input") or {}
if isinstance(ti, dict):
    fp = ti.get("file_path") or ti.get("filePath") or ti.get("path")
    if fp: rec["file_path"] = fp
print(json.dumps(rec))
' >>"$CRT_TIMELINE_LOG" 2>/dev/null
} 2>/dev/null || true
exit 0
