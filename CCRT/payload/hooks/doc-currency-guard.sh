#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# doc-currency-guard.sh — READ-TIME currency enforcement (PreToolUse, matcher=Read).
# STATUS: CURRENT (2026-07-12).
#
# WHAT: when the agent is about to `Read` a durable doc whose in-band STATUS header is
#   SUPERSEDED-BY:<ptr> (or HISTORICAL), inject ONE currency notice into the model's
#   context BEFORE the read result, then let the Read proceed. This is the ENFORCEMENT
#   half of the currency feature: it turns the passive STATUS header (write-time, T-14)
#   into a firing signal at the decision moment (mandate §6 structural>disciplinary).
#
# CONTRACT (verified against code.claude.com/docs/en/hooks, 2026-07):
#   IN : one JSON object on STDIN (NOT env vars — the old $CLAUDE_* vars are unset).
#        load-bearing: tool_input.file_path (accept filePath/path too), cwd.
#   OUT: the ONLY model-facing channel is STDOUT, which for a tool-loop event is PARSED
#        AS JSON on exit 0 — so stdout is EITHER empty (silent pass) OR exactly one JSON
#        object carrying hookSpecificOutput.additionalContext. Any stray echo => malformed
#        JSON => output silently dropped. All human/debug text => stderr, never stdout.
#   EXIT: 0 ALWAYS. The signal rides in stdout JSON, never in the exit code. A currency
#        hint is advisory; a broken hint must never wedge a Read (fail-open-but-logged).
#        exit 2 is deliberately NEVER used (it would block the read — wrong intent).
#   BLAST: read-only (only `head`s a file + writes stdout JSON); never writes/edits/deletes,
#        never blocks, never forks a slow subprocess. Fires only on durable-doc paths, so it
#        never intersects .env/.ssh/credentials.
set -eo pipefail   # NOT set -u — maybe-unset vars are guarded with ${x:-}

# --- CRT MASTER SWITCH: on (default) | observe | off ---------------------------
#   This is an INTERVENTION hook (it injects a notice), so BOTH "off" and "observe"
#   silence it: "off" = fully inert; "observe" = measure UNAIDED behavior. Only "on"
#   emits. $CRT_MODE env wins over ${CLAUDE_HOME:-$HOME/.claude}/crt_mode. (Exact snippet
#   shared with post-edit-review.sh / stop-adversary-gate.sh.)
_crt_mode="${CRT_MODE:-}"
if [ -z "$_crt_mode" ]; then
  _cmf="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"
  [ -r "$_cmf" ] && _crt_mode="$(tr -d '[:space:]' < "$_cmf" 2>/dev/null || true)"
fi
_crt_mode="${_crt_mode:-on}"
[ "$_crt_mode" != "on" ] && exit 0

# --- read the PreToolUse JSON from stdin ---------------------------------------
input="$(cat)"
[ -z "${input:-}" ] && exit 0

# --- extract file_path + cwd: python3 primary, grep/sed fallback ---------------
#   (a file path/cwd contains no newlines, so the line-wise grep/sed fallback is safe.)
file_path=""; cwd=""
if command -v python3 >/dev/null 2>&1; then
  # tab-separate fp+cwd so a path containing spaces survives extraction intact.
  _pair="$(printf '%s' "$input" | python3 -c '
import sys, json
try: d = json.load(sys.stdin)
except Exception: d = {}
if not isinstance(d, dict): d = {}          # null / list / scalar JSON => no fields
ti = d.get("tool_input")
if not isinstance(ti, dict): ti = {}
fp = ti.get("file_path") or ti.get("filePath") or ti.get("path") or ""
cw = d.get("cwd") or ""
sys.stdout.write(str(fp) + "\t" + str(cw))
' 2>/dev/null || true)"
  file_path="${_pair%%$'\t'*}"
  cwd="${_pair#*$'\t'}"
fi
if [ -z "${file_path:-}" ]; then
  # `|| true` on each: grep rc=1 on no-match must not propagate via pipefail (exit-0 contract).
  file_path="$(printf '%s' "$input" | grep -oE '"file_?[Pp]ath"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//; s/"$//' || true)"
  cwd="$(printf '%s' "$input" | grep -oE '"cwd"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//; s/"$//' || true)"
fi
[ -z "${file_path:-}" ] && exit 0

# --- DURABLE-DOC PATH GUARD (string test, NO file I/O yet) ----------------------
#   Proceed only if the path CAN carry a STATUS header — the same durable-doc set
#   doc-status.sh stamps (lib/doc-status.sh is_durable()). This glob test is the perf
#   key: every source/data/notebook/image Read short-circuits here with no disk touch.
case "$file_path" in
  *.machine.md|*/rules/*.md|*/agents/*.md|*/skills/*/SKILL.md|*/methodology/*.md|*CLAUDE*.md) : ;;
  *) exit 0 ;;
esac
# exclude derived/non-doc coincidences that the glob could catch (mirror is_durable()):
b="${file_path##*/}"
case "$b" in .*) exit 0 ;; esac                      # AppleDouble ._foo / dotfiles
case "$file_path" in *_REPORT*|*/xbeep/*|*.pdf|*/backups/*|*/plugins/*|*/.git/*) exit 0 ;; esac
# a human .md with a *.machine.md sibling is DERIVED (the root carries the header) — skip:
case "$file_path" in
  *.machine.md) : ;;
  *.md) [ -f "${file_path%.md}.machine.md" ] && exit 0 ;;
esac

# --- resolve a relative path against cwd (no readlink -f; a prefix is enough to head) ---
f="$file_path"
case "$f" in /*) : ;; *) [ -n "${cwd:-}" ] && f="$cwd/$f" ;; esac
[ -r "$f" ] || exit 0

# --- PARSE the STATUS token (INLINE copy of lib/doc-status.sh status_of()) -------
#   SINGLE SOURCE OF TRUTH = payload/rules/doc-currency.machine.md RULE.status_form,
#   which FREEZES this format; doc-status.sh status_of() and this line are two readers
#   of that one spec. Keep byte-identical to doc-status.sh. (Brief Q3: inline now — zero
#   touch to the deployed stamper — extract a shared lib later if drift ever appears.)
#   `|| true`: grep exits 1 when a doc carries NO STATUS line (the common case), which
#   pipefail would otherwise propagate into this assignment and surface as a nonzero hook
#   exit — violating the "exit 0 ALWAYS" contract. A missing header is a pass, not an error.
status="$(head -12 "$f" | grep -iE '^(#[[:space:]]*)?STATUS:' | head -1 \
  | sed -E 's/^(#[[:space:]]*)?STATUS:[[:space:]]*//I; s/[[:space:]].*$//' || true)"
[ -z "${status:-}" ] && exit 0        # no header / unparsable => pass silent (most Reads)

# --- DISPATCH on the token -----------------------------------------------------
notice=""
case "$status" in
  SUPERSEDED-BY:*)
    ptr="${status#SUPERSEDED-BY:}"
    [ -z "$ptr" ] && exit 0           # malformed (no pointer) => never guess; pass silent
    notice="⚠ CURRENCY: ${b} is STATUS: SUPERSEDED-BY:${ptr}. Live claims are owned by ${ptr}. Prefer reading ${ptr}; treat this doc as superseded unless you specifically need the old version." ;;
  HISTORICAL)
    # firing on HISTORICAL is opt-out via CRT_CURRENCY_HISTORICAL=off (brief Q4/EDGE.HISTORICAL)
    [ "${CRT_CURRENCY_HISTORICAL:-on}" != "on" ] && exit 0
    notice="⚠ CURRENCY: ${b} is STATUS: HISTORICAL — a closed record that owns no live claim. Do not treat it as current; find the active doc for live state." ;;
  CURRENT) exit 0 ;;                  # the common healthy case — no noise on live docs
  *) exit 0 ;;                        # unknown/malformed token => pass silent (fail-open)
esac
[ -z "$notice" ] && exit 0

# --- EMIT one JSON object on stdout (python3 json.dumps primary; printf fallback) ---
#   additionalContext WITHOUT permissionDecision => the notice injects but the Read's
#   permission posture is untouched. hookEventName is REQUIRED inside hookSpecificOutput.
#   (Brief Q1: the alone-form is the documented/recommended shape; if a live CC session
#   shows it does not inject without a decision, pair with permissionDecision:"allow".)
if command -v python3 >/dev/null 2>&1; then
  CTX="$notice" python3 -c '
import os, json
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": os.environ.get("CTX", "")}}))' 2>/dev/null && exit 0
fi
# fallback: the notice contains no JSON metacharacters that need escaping beyond quotes;
# the pointer token is a filename/artifact-id (no spaces/quotes). Hand-build safely.
esc="$(printf '%s' "$notice" | sed 's/\\/\\\\/g; s/"/\\"/g')"
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}\n' "$esc"
exit 0
