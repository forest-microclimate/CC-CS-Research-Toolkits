#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# brief_gate.sh — PreToolUse, matcher=Task. ADVISORY ONLY: it never refuses a launch.
#
# WHAT: before a subagent launch, check the brief the prompt references. A referenced
#   `dev/briefs/*.md` must EXIST and fill the six BRIEF CHECKLIST slots; an unreferenced
#   substantive launch gets a one-line note. Trivial launches (a read-only searcher, a
#   short prompt, or a prompt with no write intent) pass in silence.
#
# CONTRACT (bash-hook-contract):
#   IN  : one JSON object on STDIN. Load-bearing: tool_name, tool_input.{prompt,description,
#         subagent_type}, cwd. The $CLAUDE_* env vars are NOT set — never read them.
#   OUT : STDOUT is parsed as JSON on exit 0, so it is EITHER empty (silent pass) OR exactly
#         one object carrying hookSpecificOutput.additionalContext. No permissionDecision is
#         ever emitted: this gate advises, it does not deny. Debug text goes to stderr only.
#   EXIT: 0 ALWAYS. Any internal error => INDETERMINATE => fail open, and log it (a silent
#         fail-open is the bug — you cannot tell a clean pass from a broken gate).
#   BLAST: read-only. Reads stdin plus the one brief file the prompt names.
#
# SWITCH: PLANNER_KIT_HOOKS=off silences this hook (it injects context, so it must be silenceable).
set -eo pipefail   # NOT set -u — maybe-unset vars are guarded with ${x:-}

[ "${PLANNER_KIT_HOOKS:-on}" != "on" ] && exit 0

_log() {
  local d="${PLANNER_KIT_LOG_DIR:-${CLAUDE_PROJECT_DIR:-.}/.claude/logs}"
  mkdir -p "$d" 2>/dev/null || return 0
  printf '%s brief_gate: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" \
    >> "$d/planner-kit-hooks.log" 2>/dev/null || true
}

input="$(cat 2>/dev/null || true)"
[ -z "${input:-}" ] && exit 0

# fast bail: not a Task payload (cheap string test, no parse)
case "$input" in
  *Task*) : ;;
  *) exit 0 ;;
esac

command -v python3 >/dev/null 2>&1 || { _log "python3 absent => fail-open"; exit 0; }

# House pattern (never capture a heredoc inside $( ) — bash scans it for backtick balance
# before honoring the quoting, which is a hard syntax error): redirect, then read back.
_outf="${TMPDIR:-/tmp}/pkbg_out.$$"
_errf="${TMPDIR:-/tmp}/pkbg_err.$$"

set +e
python3 - "$input" <<'PYEOF' >"$_outf" 2>"$_errf"
import json, os, re, sys

# ---------- fail-open guards: anything unexpected => silent pass ----------------
try:
    obj = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
if not isinstance(obj, dict) or obj.get("tool_name") != "Task":
    sys.exit(0)
ti = obj.get("tool_input")
if not isinstance(ti, dict):
    sys.exit(0)

prompt = ti.get("prompt") if isinstance(ti.get("prompt"), str) else ""
desc = ti.get("description") if isinstance(ti.get("description"), str) else ""
sub = str(ti.get("subagent_type") or "").strip().lower()
cwd = obj.get("cwd") if isinstance(obj.get("cwd"), str) else ""
hay = prompt + "\n" + desc

# ---------- 1. does the prompt reference a brief? --------------------------------
# Quoted spans FIRST: a project path may contain spaces, so an unquoted token match
# would truncate it at the first space. Bare-token match is the fallback.
QUOTED = [re.compile(r'"([^"\n]*dev/briefs/[^"\n]*?\.md)"'),
          re.compile(r"'([^'\n]*dev/briefs/[^'\n]*?\.md)'"),
          re.compile(r"`([^`\n]*dev/briefs/[^`\n]*?\.md)`")]
BARE = re.compile(r"""([^\s"'`)\]]*dev/briefs/[^\s"'`)\]]+\.md)""")

ref = ""
for rx in QUOTED:
    m = rx.search(hay)
    if m:
        ref = m.group(1).strip()
        break
if not ref:
    m = BARE.search(hay)
    if m:
        ref = m.group(1).strip()

# ---------- 2a. NO brief referenced => triviality pass ---------------------------
# ADVISE only when all three hold: not a read-only searcher, the prompt is long enough
# to be substantive, and it names write intent. Any one failing => silent.
READONLY_TYPES = ("explore",)
WRITE_INTENT = re.compile(
    r"\b(writ|edit|creat|author|implement|build|install|modif|refactor|renam|delet|"
    r"generat|produc|stamp|rebuild|patch|append|updat|fix|add|seed|wire|merge|render)\w*\b",
    re.I)
SUBSTANTIVE_CHARS = 400


def emit(msg):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": msg}}))
    sys.exit(0)


if not ref:
    if sub in READONLY_TYPES:
        sys.exit(0)
    if len(prompt) < SUBSTANTIVE_CHARS:
        sys.exit(0)
    if not WRITE_INTENT.search(prompt):
        sys.exit(0)
    emit("This launch references no persisted brief under dev/briefs/. Copy "
         "dev/briefs/_TEMPLATE.md, fill the six slots, and name the file in the prompt — "
         "a child inherits no context, and an unpersisted brief cannot be re-launched "
         "after a crash.")

# ---------- 2b. brief referenced => resolve the path ------------------------------
# Try, in order: the reference as given; joined to the payload's cwd; and the
# dev/briefs/... suffix joined to cwd (recovers a path whose absolute prefix came
# from a different root). First hit wins.
cands, seen = [], set()
tail = ref[ref.find("dev/briefs/"):] if "dev/briefs/" in ref else ref
for p in (ref, os.path.join(cwd, ref) if cwd else "", os.path.join(cwd, tail) if cwd else ""):
    if p and p not in seen:
        seen.add(p)
        cands.append(p)

path = ""
for p in cands:
    try:
        if os.path.isfile(p):
            path = p
            break
    except Exception:
        continue

if not path:
    emit('Brief "%s" is referenced but no such file was found (checked: %s). Persist the '
         "brief to dev/briefs/ before launch, or correct the path — a brief that exists "
         "only in the launch prompt is lost the moment the session ends."
         % (ref, ", ".join('"%s"' % c for c in cands)))

try:
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
except Exception:
    sys.exit(0)   # unreadable => INDETERMINATE => fail open

# ---------- 3. the six slots ------------------------------------------------------
# Slots 1-5 are `## N. NAME` headers whose BODY must carry real content; slot 6 is the
# top-of-file SCOPE RULE line, whose content sits after its colon.
SLOTS = [
    ("1. ASSIGNMENT", re.compile(r"^##\s*1\.\s*ASSIGNMENT", re.I)),
    ("2. READ-PATHS", re.compile(r"^##\s*2\.\s*READ[- ]PATHS", re.I)),
    ("3. WRITE-PATH", re.compile(r"^##\s*3\.\s*WRITE[- ]PATH", re.I)),
    ("4. REPORT CAP", re.compile(r"^##\s*4\.\s*REPORT\s*CAP", re.I)),
    ("5. STUCK RULE", re.compile(r"^##\s*5\.\s*(STUCK|STOP)[- ]?(RULE|WHEN)", re.I)),
]
SCOPE = re.compile(r"^\s*SCOPE\s*RULE\b", re.I)
HEADER = re.compile(r"^##\s")
PLACEHOLDER = re.compile(r"<[^>]*>")
ALNUM = re.compile(r"[A-Za-z0-9]")


def filled(text):
    """Real content = something left after stripping <placeholder> spans and list/quote
    punctuation. An unedited template line is entirely placeholder, so it reads as empty."""
    t = PLACEHOLDER.sub("", text)
    t = re.sub(r"""[-*_>|:;.,"'`\s()\[\]—·]+""", "", t)
    return bool(ALNUM.search(t))


missing = []
for label, rx in SLOTS:
    idx = -1
    for i, ln in enumerate(lines):
        if rx.match(ln):
            idx = i
            break
    if idx < 0:
        missing.append(label + " (no header)")
        continue
    body_ok = False
    for ln in lines[idx + 1:]:
        if HEADER.match(ln):
            break
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if filled(s):
            body_ok = True
            break
    if not body_ok:
        missing.append(label + " (empty)")

scope_ok = False
scope_seen = False
for ln in lines:
    if SCOPE.match(ln):
        scope_seen = True
        rest = ln.split(":", 1)[1] if ":" in ln else ""
        if filled(rest):
            scope_ok = True
            break
if not scope_ok:
    missing.append("6. SCOPE RULE" + ("" if scope_seen else " (no line)"))

if not missing:
    sys.exit(0)   # complete brief => silent

emit('Brief "%s": %d of the six slots not filled — %s. An empty slot means not ready to '
     "launch (form: dev/briefs/_TEMPLATE.md)." % (ref, len(missing), "; ".join(missing)))
PYEOF
rc=$?
set -e

advice="$(cat "$_outf" 2>/dev/null || true)"
err="$(cat "$_errf" 2>/dev/null || true)"
rm -f "$_outf" "$_errf" 2>/dev/null || true

if [ "$rc" -ne 0 ]; then
  _log "INDETERMINATE rc=$rc => fail-open: $(printf '%s' "$err" | head -1)"
  exit 0
fi

if [ -n "${advice:-}" ]; then
  # Guard the shape: a garbled payload would be parsed as malformed JSON and dropped
  # silently, turning an advisory into a phantom pass.
  case "$advice" in
    \{*\}) printf '%s\n' "$advice" ;;
    *)     _log "INDETERMINATE: gate stdout was not a JSON object => fail-open" ;;
  esac
fi
exit 0
