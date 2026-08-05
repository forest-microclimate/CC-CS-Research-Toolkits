#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# STATUS: CURRENT (2026-07-28). New advisory prose-tics lint hook (TIER-P candidate, CC-only).
# prose-tics-lint.sh - PostToolUse ADVISORY writing-science prose linter.
#
# Fires: PostToolUse on Write|Edit|MultiEdit (register with matcher "Write|Edit|MultiEdit").
# Purpose: after a MANUSCRIPT-class prose file is written to disk, run the writing-science
#   mechanical detectors over it and SURFACE a short candidate-tell summary as an ADVISORY
#   nudge on STDERR. It is a nudge, never a gate.
#
# CONTRACT (see skills/bash-hook-contract):
#   - ADVISORY ONLY: always `exit 0`; never blocks (never exit 2). Output rides on STDERR.
#   - FAIL-OPEN ALWAYS: any error (no python3, detector missing/crash, malformed JSON,
#     unreadable/oversized file, timeout) => silent `exit 0`. A broken lint hook must never
#     break the session.
#   - SCOPE: only manuscript/report prose written to disk - *.md / *.markdown / *.rst. SKIPS
#     code, config/JSON/TSV, *.machine.md + .claude/ machine docs, CLAUDE.md, and scratch
#     trees (sandbox/, backups/, scratch/, node_modules/, .git/). HONEST BOUNDARY: no CC event
#     fires on chat-only prose, so this hook covers ONLY file-written prose - it cannot see a
#     draft the user never saved; do not read its silence as "the prose is clean".
#   - MASTER SWITCH: honors the CRT on|observe|off switch; both `off` and `observe` silence it
#     (it is an intervention hook). Only `on` emits.
#   - DETECTOR CONTRACT: consumes ONLY the CLI's `{counts, profile, hits}` JSON - no detector
#     internals. New tic classes are picked up automatically (counts keys drive the summary).
set -eo pipefail

# --- CRT MASTER SWITCH: on (default) | observe | off ---------------------------
#   INTERVENTION hook (injects an advisory), so BOTH "off" and "observe" silence it; only
#   "on" emits. $CRT_MODE env wins over ${CLAUDE_HOME:-$HOME/.claude}/crt_mode.
_crt_mode="${CRT_MODE:-}"
if [ -z "$_crt_mode" ]; then
  _cmf="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"
  [ -r "$_cmf" ] && _crt_mode="$(tr -d '[:space:]' < "$_cmf" 2>/dev/null || true)"
fi
_crt_mode="${_crt_mode:-on}"
[ "$_crt_mode" != "on" ] && exit 0

# --- read hook context from STDIN JSON (never $CLAUDE_* env; those are unset today) ---------
input="$(cat 2>/dev/null || true)"

# --- extract file_path: python3 primary, grep/sed fallback (both camelCase + snake_case) ----
file_path=""
if command -v python3 >/dev/null 2>&1; then
  file_path="$(printf '%s' "$input" | python3 -c '
import sys, json
try: d = json.load(sys.stdin)
except Exception: d = {}
ti = d.get("tool_input", {}) or {}
print(ti.get("file_path") or ti.get("filePath") or ti.get("path") or "")
' 2>/dev/null || true)"
fi
# fallback (a file path has no newlines => line-wise grep/sed is safe). The trailing `|| true`
# is load-bearing under `set -eo pipefail`: on empty/malformed input grep matches nothing and
# returns 1, which pipefail+set -e would otherwise turn into a non-fail-open hook abort.
if [ -z "${file_path:-}" ]; then
  file_path="$(printf '%s' "$input" | grep -oE '"file_?[Pp]ath"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//; s/"$//' || true)"
fi
[ -z "${file_path:-}" ] && exit 0   # nothing to scan => fail-open

# --- SCOPE GATE: manuscript-class prose only; skip everything else (all => silent exit 0) ----
# Include only prose-markup extensions (report-class reports here are .md). .txt is deliberately
# EXCLUDED: requirements.txt / data.txt / notes.txt are config/data, not manuscript prose.
case "$file_path" in
  *.md|*.markdown|*.rst) : ;;
  *) exit 0 ;;
esac
# Exclude machine docs + scratch/vcs trees even when the extension matches.
case "$file_path" in
  *.machine.md)                 exit 0 ;;   # LLM machine doc, not manuscript prose
  */.claude/*|.claude/*)        exit 0 ;;   # toolkit machine docs/rules/agents/skills/settings
  */sandbox/*|sandbox/*)        exit 0 ;;   # scratch (RULE.sandbox: test/scratch files live here)
  */backups/*|backups/*)        exit 0 ;;   # installer dated snapshots
  */scratch/*|scratch/*)        exit 0 ;;   # generic scratch dir
  */node_modules/*|*/.git/*)    exit 0 ;;   # dependency / vcs internals
esac
case "$(basename "$file_path" 2>/dev/null || true)" in
  CLAUDE.md) exit 0 ;;   # machine doc (primary reader = Claude), not manuscript prose
esac

# --- python3 is required to run the detector; absent => cannot scan => fail-open ------------
command -v python3 >/dev/null 2>&1 || exit 0

# --- resolve the writing-science detector relative to this hook (works in payload AND
#     installed: hooks/ and skills/ are siblings both under payload/ and under ~/.claude/) ----
DETECTOR="${PROSE_TICS_DETECTOR:-}"
if [ -z "$DETECTOR" ]; then
  _sd="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
  if [ -n "$_sd" ] && [ -f "$_sd/../skills/writing-science/writing_detectors.py" ]; then
    DETECTOR="$_sd/../skills/writing-science/writing_detectors.py"
  else
    DETECTOR="${CLAUDE_HOME:-$HOME/.claude}/skills/writing-science/writing_detectors.py"
  fi
fi
[ -f "$DETECTOR" ] || exit 0   # detector missing => fail-open silent

# --- scan + summarize in ONE python3 wrapper: runs the detector as a subprocess with a
#     PORTABLE timeout ceiling (subprocess timeout, NOT the `timeout` binary - absent on stock
#     macOS), parses the {counts,...} JSON, and writes a SHORT summary to stdout. Any
#     error/timeout => writes nothing => fail-open. The `python3 -c` form (single-quoted body,
#     no heredoc, no backticks) is bash-3.2 / macOS+Linux safe and dodges the heredoc-in-$()
#     backtick trap. Detector path + file path are passed as argv, never interpolated. --------
advisory="$(python3 -c '
import sys, os, json, subprocess
det, f = sys.argv[1], sys.argv[2]
MAX = 2 * 1024 * 1024   # skip oversized files (a manuscript is small; a huge .md is generated)
try:
    if not os.path.isfile(f) or os.path.getsize(f) > MAX:
        sys.exit(0)
except Exception:
    sys.exit(0)
try:
    p = subprocess.run([sys.executable, det, "scan", "--json", f],
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=8)
except Exception:                     # TimeoutExpired, OSError, ...
    sys.exit(0)
if p.returncode != 0:
    sys.exit(0)
try:
    counts = (json.loads(p.stdout.decode("utf-8", "replace")).get("counts") or {})
except Exception:
    sys.exit(0)
nz = [(k, int(v)) for k, v in counts.items() if isinstance(v, (int, float)) and int(v) > 0]
if not nz:
    sys.exit(0)                       # no candidate tells => stay silent (no nudge)
nz.sort(key=lambda kv: (-kv[1], kv[0]))
total = sum(v for _, v in nz)
top = ", ".join("%s×%d" % (k, v) for k, v in nz[:3])
sys.stdout.write("%d candidate tell(s) in %d class(es); top: %s" % (total, len(nz), top))
' "$DETECTOR" "$file_path" 2>/dev/null || true)"

# --- emit the ADVISORY on STDERR (hook message convention); exit 0 no matter what.
#     printf with the captures as ARGUMENTS (matched by %s) so nothing in a path/summary is
#     re-expanded or read as a format directive. -----------------------------------------------
if [ -n "${advisory:-}" ]; then
  _base="$(basename "$file_path" 2>/dev/null || true)"
  [ -z "$_base" ] && _base="$file_path"
  printf '%s\n' \
    "───────────────────────────────────────────────────────" \
    "✍️  prose-tics (advisory) — ${_base}: ${advisory}" \
    "   candidates, not errors · review with the writing-science skill (/writing-science)" \
    "───────────────────────────────────────────────────────" >&2
fi

exit 0
