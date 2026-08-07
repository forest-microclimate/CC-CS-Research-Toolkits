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
#   named Task|Agent, an `isSidechain` record, or the same pair found by raw-line match when the
#   structured shape differs. No tell => silent. The gate never blocks on a turn it cannot
#   read.
#
# VERDICT CHECK (G4, Z8 — layered AFTER the outcome check): when the same segment holds a
#   Task|Agent tool_use whose input.subagent_type is fable-executor, it must ALSO hold a serving
#   certification — /FAITHFUL|SWAPPED@|UNDETERMINED/ or a serving-stamp receipt line
#   ("model":"claude-…), searched in DECODED content text only, so a transcript record's
#   own model field can never read as a receipt and the user's own prompt (which the
#   segment strictly excludes) can never certify a child it merely mentions. Absent => the
#   SAME one-shot block, naming the ready-to-run fable_watchdog command with the child
#   transcript path substituted from the launch result's `output_file:` line when present.
#   stop_hook_active covers BOTH checks: at most one block per stop sequence, never two.
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
# Task|Agent compat: CC renamed the launcher tool to Agent (measured 2026-08-07: Agent-named
# tool_use records slipped the Task-only detection); match BOTH so a flip-back survives.
RAW_TASK = re.compile(r'"name"\s*:\s*"(?:Task|Agent)"')
RAW_SIDE = re.compile(r'"isSidechain"\s*:\s*true')

saw = False
for raw, r in window:
    if isinstance(r, dict) and r.get("isSidechain") is True:
        saw = True
        break
    for b in blocks(r):
        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Task", "Agent"):
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
if not OUTCOME.search(final):
    print(json.dumps({"decision": "block", "reason": (
        "This turn collected subagent results but the reply names no COLLECT outcome. Name "
        "exactly one — CONTINUE | RE-ROUTE | FIX-FIRST | ABORT | GOAL-MET | ADAPT — with the "
        "receipts you spot-checked, then stop. An unnamed outcome defaults silently to "
        "CONTINUE, which is how a plan outlives the evidence that justified it.")}))
    sys.exit(0)

# ---------- G4 VERDICT CHECK: a fable-executor launch demands a certification -----
# Segment = strictly AFTER the last genuine user message (window[0] when one exists),
# so the user's own prompt text cannot certify a child it merely talks about.
vseg = window[1:] if window and role_of(window[0][1]) == "user" else window

RAW_FABLE = re.compile(r'"subagent_type"\s*:\s*\\?"fable-executor')
launched = False
for raw, r in vseg:
    for b in blocks(r):
        if (isinstance(b, dict) and b.get("type") == "tool_use"
                and b.get("name") in ("Task", "Agent")
                and isinstance(b.get("input"), dict)
                and b["input"].get("subagent_type") == "fable-executor"):
            launched = True
            break
    if launched:
        break
    if RAW_TOOLUSE.search(raw) and RAW_TASK.search(raw) and RAW_FABLE.search(raw):
        launched = True
        break

if not launched:
    sys.exit(0)


def deep_texts(x, acc, depth=0):
    """Every DECODED content string in a record: text blocks, string content, nested
    tool_result content. Deliberately NOT the record's own metadata fields (model,
    id, …) and NOT tool_use inputs — a serving-stamp receipt must come from content
    someone actually put in front of the coordinator, not from the transcript's own
    envelope (whose every assistant record carries a "model" field)."""
    if depth > 8:
        return
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("text", "content") and isinstance(v, str):
                acc.append(v)
            elif k != "input":
                deep_texts(v, acc, depth + 1)
    elif isinstance(x, list):
        for v in x:
            deep_texts(v, acc, depth + 1)


texts = []
for raw, r in vseg:
    if isinstance(r, dict):
        deep_texts(r, texts)
    else:
        texts.append(raw)   # unparseable line: raw fallback (errs toward fail-open)
seg_text = "\n".join(texts)

CERT = re.compile(r'FAITHFUL|SWAPPED@|UNDETERMINED|"model":"claude-')
if CERT.search(seg_text):
    sys.exit(0)

path = ""
for m in re.finditer(r"output_file:\s*([^\n\r]+)", seg_text):
    path = m.group(1).strip().strip("`\"'")   # last launch result wins
cmd_path = ("'" + path.replace("'", "'\\''") + "'") if path \
    else "'<the child transcript path from the launch result>'"
print(json.dumps({"decision": "block", "reason": (
    "This turn launched a fable-executor child but the segment carries no serving "
    "certification — no FAITHFUL / SWAPPED@k / UNDETERMINED verdict and no serving-stamp "
    "receipt. A fable request can be silently substituted at serving time; certify what "
    "SERVED before stopping. Run: python3 .claude/skills/model-verification/"
    "fable_watchdog.py " + cmd_path + " --watch (FAITHFUL(0)=certified · SWAPPED@k(1)="
    "relaunch or proceed knowingly, log it · UNDETERMINED(2)=investigate), then state the "
    "verdict — or quote the stamps grep — in your reply, then stop.")}))
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
           _log "nudge emitted (collect-outcome or fable-verdict check)" ;;
    *)     _log "INDETERMINATE: gate stdout was not a JSON object => fail-open" ;;
  esac
fi
exit 0
