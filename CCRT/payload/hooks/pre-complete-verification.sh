#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# Pre-Completion Verification Reminder
# Fires: UserPromptSubmit when completion language detected (register with matcher "")
# Purpose: Ensure verification before claiming done.
# 2026-07 FIX: the prompt is read from STDIN JSON (current Claude Code passes hook data on
#   stdin), NOT the old CLAUDE_PROMPT env var (no longer set → pre-fix version silently no-oped).
set -eo pipefail

# --- CRT MASTER SWITCH: on (default) | observe | off ---------------------------
#   Shared toolkit on/off control (see methodology/CRT_MASTER_SWITCH.machine.md).
#   This is an INTERVENTION hook (it injects a verification reminder), so BOTH "off"
#   and "observe" silence it: "off" = fully inert; "observe" = research shadow arm
#   where the agent runs UNPROMPTED so its unaided behaviour is measurable. Only
#   "on" emits. $CRT_MODE env wins over ~/.claude/crt_mode.
_crt_mode="${CRT_MODE:-}"
if [ -z "$_crt_mode" ]; then
  _cmf="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"
  [ -r "$_cmf" ] && _crt_mode="$(tr -d '[:space:]' < "$_cmf" 2>/dev/null || true)"
fi
_crt_mode="${_crt_mode:-on}"
[ "$_crt_mode" != "on" ] && exit 0

input="$(cat 2>/dev/null || true)"
prompt=""
if command -v python3 >/dev/null 2>&1; then
  prompt="$(printf '%s' "$input" | python3 -c 'import sys, json
try: print(json.load(sys.stdin).get("prompt",""))
except Exception: pass' 2>/dev/null || true)"
fi
[ -z "$prompt" ] && prompt="$input"   # fallback: scan the raw envelope

if printf '%s' "$prompt" | grep -qiE "(complete|done|finished|ready|all set|fixed it|found the bug)"; then
    cat >&2 <<'EOF'
═══════════════════════════════════════════════════════
⚠️  COMPLETION CLAIM DETECTED — VERIFY BEFORE CONFIRMING
═══════════════════════════════════════════════════════
□ COMPLETENESS: List requested vs delivered elements
□ PATTERN SEARCH: grep for the same pattern in other files
□ SEMANTIC CHECK: Assertions validate behaviour, not just syntax
  — stopifnot() on semantic properties
  — diagnostic output showing what code actually did
  — smell test: do numbers match expected range?
□ EDGE CASES: Tested conditional branches and boundary values
□ MAGNITUDE CHECK: If fixing a bug, is improvement in the
  expected range? (50-65% for single bug, rarely 100%)

Confirm every box is checked before declaring the task complete.
═══════════════════════════════════════════════════════
EOF
fi

exit 0
