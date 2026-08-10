#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# opus-dispatch-guard.sh — DISPATCH-TIME alias ban (PreToolUse, matcher=Task|Agent).
# STATUS: CURRENT (2026-08-04). The third moment of the model ban, and the one that was missing.
#
# WHAT: when the agent is about to LAUNCH a subagent, read tool_input.model. If it is the bare
#   alias `opus` or `opusplan` (alone or context-suffixed, e.g. `opus[1m]`), DENY the launch.
#   Anything else — sonnet, haiku, a full id, no model key at all — passes SILENTLY.
#
# WHY IT EXISTS: the ban used to hold at exactly two moments, BUILD time (lib/verify_models.sh:
#   a barred id cannot ship in the payload) and PLAN time (plan-routing-gate.sh: a plan cannot
#   declare one). MEASURED 2026-08-04: a live `Task(model:"opus")` call fired NOTHING — neither
#   gate sits on the dispatch path, so a launch typed in the moment reached the barred model with
#   no check at all. This hook closes that hole and nothing else.
#
# WHY THE ALIASES AND ONLY THE ALIASES:
#   * `opus` resolves to Claude Opus 5 on Claude Code >=2.1.219, and `opusplan` plans on the
#     latest Opus, which is the same model. Both read to a human like a tier choice while
#     silently routing onto a barred model — and an alias re-resolves whenever Claude Code
#     remaps it, which is exactly how `opus` became barred without any file changing. There is
#     no scope, supervised or not, at which an alias is a sanctioned route. Hence: deterministic
#     DENY, the one hard deny in the O-series set.
#   * A FULL id is deliberately NOT denied here. The Task `model` param accepts ALIASES ONLY
#     (measured 2026-08-04, live InputValidationError), so a full id in this field is rejected by
#     the harness before any policy question arises; and the sanctioned supervised route names an
#     AGENT (subagent_type: opus5-executor, whose OWN frontmatter carries the pin — it ships in the
#     general payload, admitted by the build gate's NAMED allowlist of three route agents), not
#     a model. A guard that denied the model name would not touch that route anyway, and a guard
#     that denied the agent NAME would break the one shape the O-series exists to permit.
#
# CONTRACT (per bash-hook-contract; same shape as plan-routing-gate.sh):
#   IN : one JSON object on STDIN. Load-bearing: tool_name, tool_input.model.
#   OUT: STDOUT is EITHER empty (silent pass) OR exactly one JSON object carrying
#        hookSpecificOutput.permissionDecision="deny". Any stray echo => malformed JSON => the
#        decision is silently dropped. Debug text goes to stderr / the log, never stdout.
#   EXIT: 0 ALWAYS. The deny rides in the stdout JSON, not the exit code — the model needs the
#        structured reason to re-launch correctly, and that retry is the point.
#        Any internal error (no python3, unparseable stdin, unexpected shape) => INDETERMINATE
#        => FAIL-OPEN but LOGGED. A guard must never wedge a launch on its own bug.
#   BLAST: read-only. Reads stdin. Writes nothing but its own log line.
#
# MASTER SWITCH: this is an INTERVENTION hook, so it follows the house rule — CRT_MODE "off" and
#   "observe" BOTH silence it, only "on" (the default) enforces. That is a deliberate trade: an
#   operator who sets the switch has made the whole toolkit inert on purpose, and a hook that
#   ignored the switch would be a surprise. The ban still holds at build time and plan time, which
#   no env var reaches.
# REGRESSION GUARD: tests/test_opus_dispatch_guard.sh — deny on opus / opus[1m] / opusplan, silent
#   on sonnet / haiku / a full id / absent model / a non-launcher tool / garbage JSON.
set -eo pipefail   # NOT set -u — maybe-unset vars are guarded with ${x:-}

_log() {
  local d="${CLAUDE_HOME:-$HOME/.claude}/logs"
  mkdir -p "$d" 2>/dev/null || return 0
  printf '%s opus-dispatch-guard: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" \
    >> "$d/opus-dispatch-guard.log" 2>/dev/null || true
}

# --- CRT MASTER SWITCH: on (default) | observe | off ---------------------------
_crt_mode="${CRT_MODE:-}"
if [ -z "$_crt_mode" ]; then
  _cmf="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"
  [ -r "$_cmf" ] && _crt_mode="$(tr -d '[:space:]' < "$_cmf" 2>/dev/null || true)"
fi
_crt_mode="${_crt_mode:-on}"
[ "$_crt_mode" != "on" ] && exit 0

input="$(cat 2>/dev/null || true)"
[ -z "${input:-}" ] && exit 0

# fast bail: not a subagent-launch payload (cheap string test, no parse)
# Task|Agent compat: CC renamed the launcher tool to Agent (measured 2026-08-07: an Agent-named launch slipped the Task-only check); accept BOTH so a flip-back survives.
case "$input" in
  *'"Task"'*|*'"Agent"'*) : ;;
  *) exit 0 ;;
esac

command -v python3 >/dev/null 2>&1 || { _log "python3 absent => fail-open"; exit 0; }

_outf="${TMPDIR:-/tmp}/odg_out.$$"
_errf="${TMPDIR:-/tmp}/odg_err.$$"

set +e
python3 - "$input" <<'PYEOF' >"$_outf" 2>"$_errf"
import json, re, sys

# ---------- fail-open guards: anything unexpected => silent pass ----------------
try:
    obj = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
if not isinstance(obj, dict):
    sys.exit(0)

# The matcher should guarantee this; a mis-registered fragment must not let this guard
# deny unrelated tool calls.
# Task|Agent compat: CC renamed the launcher tool to Agent (measured 2026-08-07); accept BOTH names.
if obj.get("tool_name") not in ("Task", "Agent"):
    sys.exit(0)

ti = obj.get("tool_input")
if not isinstance(ti, dict):
    sys.exit(0)

m = ti.get("model")
if not isinstance(m, str):
    sys.exit(0)          # no model param => the configured subagent default => nothing to judge
low = m.strip().strip("`\"'").lower()
if not low:
    sys.exit(0)

# Same shape as lib/verify_models.sh classify() and plan-routing-gate.sh banned_model():
# match by PREFIX-with-boundary, not equality, so an unknown suffixed variant is treated as
# barred rather than let through.
if re.match(r"^opus([^a-z0-9-].*)?$", low):
    why = ("the bare alias `opus` resolves to Claude Opus 5 on Claude Code >=2.1.219")
elif re.match(r"^opusplan([^a-z0-9-].*)?$", low):
    why = ("the alias `opusplan` plans on the latest Opus, which resolves to Claude Opus 5 "
           "on Claude Code >=2.1.219")
else:
    sys.exit(0)

reason = (
    "BLOCKED by opus-dispatch-guard: this subagent launch names model=%r, and %s — a barred model "
    "reached by a name that reads like a tier choice.\n"
    "\n"
    "Relaunch one of these ways:\n"
    "  - model: `fable`  |  model: `sonnet`  |  model: `haiku`   (the param takes aliases "
    "only; name the tier you want)\n"
    "  - OMIT the model param => you inherit the MAIN model, which is rank 4 of the precedence "
    "and is NOT a tier choice (measured 2026-08-04)\n"
    "  - supervised opus-5 work: do NOT name a model. Launch subagent_type "
    "\"opus5-executor\" (an allowlisted route agent whose own frontmatter carries the pin) from a "
    "plan whose routing track declares \"supervised\": true.\n"
    "An alias is never the sanctioned route at any scope: it re-resolves silently whenever "
    "Claude Code remaps it, which is how `opus` became barred with no file changing."
) % (m, why)

print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": reason}}))
sys.exit(0)
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
  # Guard the shape: a partial/garbled payload on stdout parses as malformed JSON and is
  # silently dropped, turning a DENY into a phantom pass.
  case "$verdict" in
    \{*\}) printf '%s\n' "$verdict"
           _log "DENY: $(printf '%s' "$verdict" | head -c 200)" ;;
    *)     _log "INDETERMINATE: guard stdout was not a JSON object => fail-open" ;;
  esac
fi
exit 0
