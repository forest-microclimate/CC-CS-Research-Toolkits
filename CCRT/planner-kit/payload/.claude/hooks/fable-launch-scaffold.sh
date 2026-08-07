#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# fable-launch-scaffold.sh — PostToolUse, matcher=Task|Agent. ZERO-THOUGHT WATCHDOG SCAFFOLD (Z6/G2).
# STATUS: CURRENT (2026-08-06). Ships in planner-kit v1.7. ADVISORY ONLY — stderr text, never
#   blocks, never exits nonzero (the post-edit-review stderr precedent).
#
# WHAT: when a fable/opus5-tier (or probe-*) Task|Agent launch RETURNS, find the child transcript
#   path in the launch result (`output_file: <path>`) and print, to stderr, the ready-to-run
#   verified-launch certification command:
#       python3 .claude/skills/model-verification/fable_watchdog.py '<path>' --watch
#   plus the exit-code legend, so the coordinator's next action requires zero recall:
#       FAITHFUL(0)=certified · SWAPPED@k(1)=relaunch or proceed knowingly (log it) ·
#       UNDETERMINED(2)=investigate
#   No path in the response => fully silent. Probes are INCLUDED in the trigger on purpose
#   (the scaffold is harmless-to-useful on a probe cell; G1's allowlist logic does not apply
#   here because nothing is being denied).
#
# CONTRACT (bash-hook-contract):
#   IN  : one JSON object on STDIN. Load-bearing: tool_name,
#         tool_input.{subagent_type,model}, tool_response (string OR structured content —
#         both shapes are walked defensively for the output_file token).
#   OUT : STDOUT stays EMPTY (PostToolUse stdout is parsed; this hook decides nothing).
#         The scaffold text goes to STDERR only.
#   EXIT: 0 ALWAYS. Any internal error => silent fail-open. Advisory hooks never wedge a turn.
#   BLAST: read-only. Reads stdin; writes nothing but stderr.
#
# SWITCH: PLANNER_KIT_HOOKS=off silences it (kit advisory-hook convention, same as brief_gate).
# REGRESSION GUARD: tests/test_fable_dispatch_gate.sh (G2 arms).
set -eo pipefail   # NOT set -u — maybe-unset vars are guarded with ${x:-}

[ "${PLANNER_KIT_HOOKS:-on}" != "on" ] && exit 0

input="$(cat 2>/dev/null || true)"
[ -z "${input:-}" ] && exit 0

# fast bail: not a subagent-launch payload (cheap string test, no parse)
# Task|Agent compat: CC renamed the launcher tool to Agent (measured 2026-08-07: an Agent-named launch slipped the Task-only check); accept BOTH so a flip-back survives.
case "$input" in
  *'"Task"'*|*'"Agent"'*) : ;;
  *) exit 0 ;;
esac

command -v python3 >/dev/null 2>&1 || exit 0

_outf="${TMPDIR:-/tmp}/fls_out.$$"

set +e
python3 - "$input" <<'PYEOF' >"$_outf" 2>/dev/null
import json, re, sys

# ---------- fail-open guards: anything unexpected => silent pass ----------------
try:
    obj = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
# Task|Agent compat: CC renamed the launcher tool to Agent (measured 2026-08-07); accept BOTH names.
if not isinstance(obj, dict) or obj.get("tool_name") not in ("Task", "Agent"):
    sys.exit(0)
ti = obj.get("tool_input")
if not isinstance(ti, dict):
    sys.exit(0)

sub = str(ti.get("subagent_type") or "").strip().lower()
model = str(ti.get("model") or "").strip().strip("`\"'").lower()
fable_model = bool(re.match(r"^fable([^a-z0-9-].*)?$", model))

# Same trigger set as fable-dispatch-gate, INCLUDING probes (harmless-to-useful there).
if not (sub in ("fable-executor", "opus5-executor") or fable_model
        or re.match(r"^probe-", sub)):
    sys.exit(0)

# ---------- find the child transcript path in the launch result -----------------
# The result text carries `output_file: <path>`. tool_response may be a plain string or a
# structured content object/array — walk every string in it defensively.
texts = []


def walk(x, depth=0):
    if depth > 8:
        return
    if isinstance(x, str):
        texts.append(x)
    elif isinstance(x, dict):
        for v in x.values():
            walk(v, depth + 1)
    elif isinstance(x, list):
        for v in x:
            walk(v, depth + 1)


walk(obj.get("tool_response"))

path = ""
rx = re.compile(r"output_file:\s*([^\n\r]+)")
for t in texts:
    m = rx.search(t)
    if m:
        path = m.group(1).strip().strip("`\"'")
        break
if not path:
    sys.exit(0)

# Single-quote the path for the shell; an embedded single quote gets the standard '\'' escape.
q = "'" + path.replace("'", "'\\''") + "'"
print("python3 .claude/skills/model-verification/fable_watchdog.py " + q + " --watch")
print("FAITHFUL(0)=certified · SWAPPED@k(1)=relaunch or proceed knowingly (log it) "
      "· UNDETERMINED(2)=investigate")
sys.exit(0)
PYEOF
rc=$?
set -e

out="$(cat "$_outf" 2>/dev/null || true)"
rm -f "$_outf" 2>/dev/null || true

[ "$rc" -ne 0 ] && exit 0
if [ -n "${out:-}" ]; then
  printf '%s\n' "$out" >&2    # stderr only — stdout stays empty (the advisory channel)
fi
exit 0
