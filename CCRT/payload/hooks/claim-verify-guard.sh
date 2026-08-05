#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# claim-verify-guard.sh — WRITE-TIME claim-vs-record enforcement (PreToolUse).
# STATUS: CURRENT (2026-07-24). VLOOP Item 1, CCRT half.
#
# WHAT: when the agent is about to WRITE a durable payload that carries TAGGED claims,
#   recompute each claim against its named source and BLOCK (exit 2) on any mismatch.
#   This is the MECHANICAL half of the verification-loop feature: it turns the skill
#   body's "recompute before you assert" from model discretion into a fired gate.
#   Closes failure families F1+F2+F3 (53% of 76 mined failures) at the write path.
#
# WHY A HOOK AND NOT AN INSTRUCTION: a check written into a SKILL.md fires only if the
#   skill is loaded AND the agent chooses to run it. A PreToolUse hook fires on the tool
#   call regardless. That difference is the whole point of the feature.
#
# CONTRACT (per bash-hook-contract; verified against the doc-currency-guard precedent):
#   IN : one JSON object on STDIN (NOT env vars — the old $CLAUDE_* vars are unset).
#        load-bearing: tool_name, tool_input.{file_path,content}, cwd.
#   OUT: human/agent-facing reason on STDERR only. STDOUT stays EMPTY — this hook emits
#        no structured protocol, and a stray echo would be parsed as malformed JSON.
#   EXIT: 0 = PASS (no tagged claims, or every claim verified).
#         2 = BLOCK (a tagged claim mismatched, or a vacuous check was detected); the
#             stderr message tells Claude which claim and what the record actually says.
#         Any OTHER nonzero from an internal helper => INDETERMINATE => FAIL-OPEN but
#             LOG. A gate that cannot reach a verdict must not block on its own bug.
#   BLAST: read-only. Reads the payload from stdin plus the source files each claim
#        names; never writes, edits, or deletes. Never forks a network call.
#
# HOW CLAIMS ARE TAGGED: the writer embeds a fenced block in the payload:
#     ```vloop-claims
#     [{"id":"n","tag":"count-over-artifact","source":"x.txt","asserted":4}]
#     ```
#   Untagged prose is OUT OF SCOPE by design (see SKILL.md) — this hook does not
#   attempt to extract claims from free prose, because that extraction is itself an
#   LLM judgment and would make the gate non-deterministic.
#
# SEED-01 EMIT-TIME TELL ARM (added 2026-07-28; NON-BLOCKING, advisory-only):
#   In ADDITION to the deterministic arm above, when a write payload carries NO
#   vloop-claims block but DOES carry a bare version/artifact id (8-hex, vN.N,
#   claude-<name>-N-N) OR a verification token (verified / byte-identical /
#   all[ N] passed / confirmed), the hook consults THIS session's turn window in
#   the timeline log (rows after the last UserPromptSubmit for this session_id; if
#   stdin carries no session_id, after the most recent UserPromptSubmit) and asks:
#   was there any Read/Grep/Glob this turn? If NOT, the id/status was plausibly
#   RECALLED rather than read => inject a one-line ADVISORY on STDERR (exit 0).
#   DECISION (documented per request): this arm NEVER blocks. The tell is HEURISTIC
#   (a regex + a timeline heuristic), so exit-2 blocking stays RESERVED for the
#   deterministic claim-vs-record recompute of the vloop-claims arm. We emit on
#   STDERR — not stdout hookSpecificOutput.additionalContext — to preserve this
#   hook's "STDOUT stays EMPTY" invariant (a stray stdout byte is parsed as hook
#   protocol). Fail-open SILENT on any parse/absence (timeline missing, python
#   absent, no turn boundary, unreadable rows). Timeline path override: $CVG_TIMELINE.
set -eo pipefail   # NOT set -u — maybe-unset vars are guarded with ${x:-}

_log() {
  local d="${CLAUDE_HOME:-$HOME/.claude}/logs"
  mkdir -p "$d" 2>/dev/null || return 0
  printf '%s claim-verify-guard: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" \
    >> "$d/claim-verify-guard.log" 2>/dev/null || true
}

# --- CRT MASTER SWITCH: on (default) | observe | off ---------------------------
#   This is an INTERVENTION hook (it can block), so BOTH "off" and "observe" silence
#   it: "off" = fully inert; "observe" = measure UNAIDED behavior. Only "on" enforces.
_crt_mode="${CRT_MODE:-}"
if [ -z "$_crt_mode" ]; then
  _cmf="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"
  [ -r "$_cmf" ] && _crt_mode="$(tr -d '[:space:]' < "$_cmf" 2>/dev/null || true)"
fi
_crt_mode="${_crt_mode:-on}"
[ "$_crt_mode" != "on" ] && exit 0

input="$(cat)"
[ -z "${input:-}" ] && exit 0

# python3 is a hard dep of both arms below (moved up from the old vloop-only spot so
# the SEED-01 tell arm is guarded too). Absent => fail-open, logged.
command -v python3 >/dev/null 2>&1 || { _log "python3 absent => fail-open"; exit 0; }

# Timeline consulted by the SEED-01 tell arm below. Overridable for tests and to honor
# the logger's own $CRT_TIMELINE_LOG; defaults under $CLAUDE_HOME/logs.
CVG_TIMELINE="${CVG_TIMELINE:-${CRT_TIMELINE_LOG:-${CLAUDE_HOME:-$HOME/.claude}/logs/timeline.jsonl}}"

# --- ARM SELECT: a vloop-claims block => the deterministic verifier (below).
#     No block => the SEED-01 emit-time TELL arm (non-blocking advisory), then exit. -
case "$input" in
  *vloop-claims*) : ;;
  *)
    # No tagged claims, but the payload may still assert a bare id/status from
    # recollection. Emit a heuristic ADVISORY (never a block) when a tell token is
    # present AND the timeline shows no fresh read in this turn window. House pattern:
    # python stdout -> temp file, never captured via $( ) (heredoc-in-$() landmine).
    _tell_out="${TMPDIR:-/tmp}/cvg_tell.$$"
    set +e
    python3 - "$input" "$CVG_TIMELINE" <<'PYEOF' >"$_tell_out" 2>/dev/null
import json, os, re, sys

payload = sys.argv[1]
timeline = sys.argv[2] if len(sys.argv) > 2 else ""
try:
    obj = json.loads(payload)
except Exception:
    sys.exit(0)                         # not our shape -> silent

ti = obj.get("tool_input") or {}
content = ""
for k in ("content", "new_string", "command", "text", "new_source"):
    v = ti.get(k)
    if isinstance(v, str) and v:
        content += "\n" + v
for listkey in ("edits", "changes", "cells"):
    seq = ti.get(listkey)
    if isinstance(seq, list):
        for e in seq:
            if isinstance(e, dict):
                for k in ("new_string", "new_source", "content", "text"):
                    v = e.get(k)
                    if isinstance(v, str) and v:
                        content += "\n" + v
            elif isinstance(e, str) and e:
                content += "\n" + e

# A vloop-claims block belongs to the deterministic arm; never double-handle it.
if "vloop-claims" in content or not content.strip():
    sys.exit(0)

# TELL tokens: a bare version/artifact id, or a verification-status word.
ID_RE = re.compile(r"\b[0-9a-f]{8,}\b|\bv[0-9]+\.[0-9]+(?:\.[0-9]+)?\b|\bclaude-[a-z]+-[0-9]+-[0-9]+\b", re.I)
VERIF_RE = re.compile(r"\b(?:verified|byte[\s_\u2014\u2013-]?identical|all(?: [0-9]+)? passed|all[- ]green|confirmed)\b", re.I)
m_id = ID_RE.search(content)
m_vf = VERIF_RE.search(content)
if not m_id and not m_vf:
    sys.exit(0)                         # no tell -> nothing to advise (the common case)

# A tell is present: consult the timeline for a fresh read in THIS turn window.
if not timeline or not os.path.isfile(timeline):
    sys.exit(0)                         # timeline absent -> fail-open silent
rows = []
try:
    with open(timeline, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
except Exception:
    sys.exit(0)
if not rows:
    sys.exit(0)

sid = obj.get("session_id") or ""
# Delimiter = last UserPromptSubmit row (for THIS session_id if we have one; else the
# most recent UPS row overall). Rows AFTER it are the current turn window.
delim = None
for i, r in enumerate(rows):
    if r.get("event") != "UserPromptSubmit":
        continue
    if sid and (r.get("session_id") or "") != sid:
        continue
    delim = i
if delim is None:
    sys.exit(0)                         # no turn boundary -> cannot assert "no read" -> silent
window = rows[delim + 1:]
if sid:
    window = [r for r in window if (r.get("session_id") or sid) == sid]

READ_TOOLS = {"Read", "Grep", "Glob"}
if any(r.get("tool_name") in READ_TOOLS for r in window):
    sys.exit(0)                         # a fresh read happened this turn -> no advisory

tok = (m_id or m_vf).group(0)
kind = "version/artifact id" if m_id else "verification token"
mk = "id" if m_id else "verif"
sys.stdout.write(
    "[[vloop:claim-verify-guard-tell kind=%s fresh_read=0]]\n"
    "advisory (claim-verify-guard SEED-01): this write asserts a specific %s (%r) but the\n"
    "session timeline shows NO Read/Grep/Glob in the current turn window. If it was\n"
    "recalled rather than read this turn, verify it against its source before writing.\n"
    "(advisory only -- not a block.)\n" % (mk, kind, tok))
sys.exit(10)
PYEOF
    _trc=$?
    set -e
    _tell_msg="$(cat "$_tell_out" 2>/dev/null || true)"
    rm -f "$_tell_out" 2>/dev/null || true
    if [ "$_trc" -eq 10 ] && [ -n "$_tell_msg" ]; then
      printf '%s\n' "$_tell_msg" >&2
      _log "TELL advisory: $(printf '%s' "$_tell_msg" | head -1)"
    fi
    exit 0
    ;;
esac

# The verifier runs in python3 (the claim predicates need real parsing, and
# bash-hook-contract makes python3 a hard dep of the hooks). It prints the
# human-facing reason to stderr and signals via its own exit code.
set +e
python3 - "$input" <<'PYEOF' >/dev/null 2>/tmp/cvg_reason.$$
import json, os, re, sys

payload = sys.argv[1]
try:
    obj = json.loads(payload)
except Exception:
    sys.exit(0)                     # not our shape -> pass

ti = obj.get("tool_input") or {}
content = ""
# FLAT keys: Write(content), Edit(new_string), Bash(command), generic(text).
for k in ("content", "new_string", "command", "text", "new_source"):
    v = ti.get(k)
    if isinstance(v, str) and v:
        content += "\n" + v
# NESTED payloads. ADVERSARIAL FIX 2026-07-24 (CRITICAL, confirmed by reproduction):
# MultiEdit is named in the PreToolUse matcher but nests its text in tool_input.edits[]
# .new_string, and NotebookEdit uses new_source. Reading only the flat keys made a
# ```vloop-claims``` block delivered via MultiEdit look like "no claim block", so a
# mismatched claim WROTE UNVERIFIED (observed: Write->2, Edit->2, MultiEdit->0).
for listkey in ("edits", "changes", "cells"):
    seq = ti.get(listkey)
    if isinstance(seq, list):
        for e in seq:
            if isinstance(e, dict):
                for k in ("new_string", "new_source", "content", "text"):
                    v = e.get(k)
                    if isinstance(v, str) and v:
                        content += "\n" + v
            elif isinstance(e, str) and e:
                content += "\n" + e
cwd = obj.get("cwd") or os.getcwd()

blocks = re.findall(r"```vloop-claims\s*\n(.*?)```", content, re.S)
if not blocks:
    sys.exit(0)

claims = []
for b in blocks:
    try:
        got = json.loads(b)
        claims.extend(got if isinstance(got, list) else [got])
    except Exception as exc:
        sys.stderr.write(
            "BLOCKED by claim-verify-guard: a ```vloop-claims``` block is present but "
            "does not parse as JSON (%s). A malformed claim block must not pass as "
            "'no claims' -- that is the vacuous-pass failure this gate exists to "
            "close. Fix the block or remove it.\n" % exc)
        sys.exit(2)

# Anti-vacuous: a claim block that parses to nothing, against a non-trivial payload.
if not claims and len(content.strip()) > 200:
    sys.stderr.write(
        "BLOCKED by claim-verify-guard: a vloop-claims block enumerated 0 claims "
        "against a %d-char durable payload. An empty claims table is a visible "
        "failure, not a pass.\n" % len(content.strip()))
    sys.exit(2)

TAGS = ("count-over-artifact", "field-value", "state")


def norm(v, mode):
    mode = mode or "exact"
    if v is None:
        return None
    s = str(v)
    if mode == "exact":
        return s
    if mode == "strip":
        return s.strip()
    if mode == "casefold":
        return s.strip().casefold()
    if mode == "collapse-space":
        return re.sub(r"\s+", " ", s).strip()
    if mode == "numeric":
        return repr(float(s.strip().replace(",", "")))
    raise ValueError("unknown normalization %r" % mode)


def resolve(p):
    return p if os.path.isabs(p) else os.path.join(cwd, p)


rows, fails = [], []
for c in claims:
    cid, tag = c.get("id") or "?", c.get("tag")
    if tag not in TAGS:
        fails.append("[%s] tag %r is outside the closed taxonomy %s" % (cid, tag, list(TAGS)))
        continue
    try:
        if tag == "count-over-artifact":
            p = resolve(c["source"])
            if os.path.isdir(p):
                got = len([d for d in os.listdir(p) if not d.startswith(".")])
            else:
                txt = open(p, encoding="utf-8", errors="replace").read()
                got = (len(re.findall(c["pattern"], txt)) if c.get("pattern")
                       else sum(1 for ln in txt.splitlines() if ln.strip()))
            exp = int(c["asserted"])
            ok = got == exp
        elif tag == "field-value":
            cur = json.load(open(resolve(c["source"]), encoding="utf-8"))
            for part in str(c["field"]).split("."):
                cur = cur[int(part)] if isinstance(cur, list) else cur[part]
            got, exp = norm(cur, c.get("normalize")), norm(c["asserted"], c.get("normalize"))
            ok = got == exp
        else:
            if "observed" not in c:
                fails.append("[%s] state claim carries no `observed` value from a real "
                             "rerun -- it cannot be verified and must not pass" % cid)
                continue
            got, exp = norm(c["observed"], c.get("normalize")), norm(c["asserted"], c.get("normalize"))
            ok = got == exp
        rows.append((cid, tag, got, c.get("asserted"), ok))
        if not ok:
            fails.append("[%s] %s: record says %r, payload asserts %r"
                         % (cid, tag, got, c.get("asserted")))
    except Exception as exc:
        fails.append("[%s] %s: %s: %s" % (cid, tag, type(exc).__name__, exc))

marker = "[[vloop:claim-verify-guard n_claims=%d n_fail=%d]]" % (len(claims), len(fails))
if fails:
    sys.stderr.write("BLOCKED by claim-verify-guard %s\n\n" % marker)
    sys.stderr.write("%d of %d tagged claim(s) do NOT match the record:\n" % (len(fails), len(claims)))
    for f in fails:
        sys.stderr.write("  - %s\n" % f)
    sys.stderr.write("\nRecompute from the source and correct the payload, or remove the "
                     "claim. Do not re-tag it to dodge the check.\n")
    sys.exit(2)
sys.stderr.write("claim-verify-guard %s all claims verified\n" % marker)
sys.exit(0)
PYEOF
rc=$?
set -e

reason="$(cat /tmp/cvg_reason.$$ 2>/dev/null || true)"
rm -f /tmp/cvg_reason.$$ 2>/dev/null || true

if [ "$rc" -eq 2 ]; then
  printf '%s\n' "$reason" >&2
  _log "BLOCK: $(printf '%s' "$reason" | head -1)"
  exit 2
fi
if [ "$rc" -ne 0 ]; then
  # INDETERMINATE (e.g. the verifier itself crashed) => fail-open BUT log it.
  # A silent fail-open is the bug: you cannot tell a clean pass from a broken gate.
  _log "INDETERMINATE rc=$rc => fail-open: $(printf '%s' "$reason" | head -1)"
  exit 0
fi
if [ -n "${reason:-}" ]; then
  # Re-emit the PASS marker on stderr, not just to the log. An empty output on a
  # clean run is indistinguishable from a gate that never fired (MARKER_ABSENT),
  # which is the very ambiguity this feature exists to remove: an auditor must be
  # able to tell "checked and clean" from "silently skipped". stderr is safe here —
  # only stdout is parsed as hook protocol.
  printf '%s\n' "$reason" >&2
  _log "PASS: $(printf '%s' "$reason" | head -1)"
fi
exit 0
