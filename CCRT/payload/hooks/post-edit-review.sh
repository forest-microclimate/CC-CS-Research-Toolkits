#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# Post-Edit Review Hook (merged with stats-check)
# Fires: PostToolUse on Edit/Write for R files (register with matcher "Edit|Write")
# Purpose: Prompt review and flag statistical model edits.
# 2026-07 FIX: hook context is read from STDIN JSON (current Claude Code passes hook data on
#   stdin), NOT the old CLAUDE_TOOL / CLAUDE_FILE_PATH env vars (which are no longer set, so the
#   pre-fix version silently no-oped). Mirrors the stdin-read pattern in clamp-guard.sh.
set -eo pipefail

# --- CRT MASTER SWITCH: on (default) | observe | off ---------------------------
#   Shared toolkit on/off control (see methodology/CRT_MASTER_SWITCH.machine.md).
#   This is an INTERVENTION hook (it injects a review reminder), so BOTH "off" and
#   "observe" silence it: "off" = user/research fully-inert; "observe" = research
#   shadow arm where the agent must run UNPROMPTED so we can measure its unaided
#   behaviour. Only "on" emits the reminder. $CRT_MODE env wins over ~/.claude/crt_mode.
_crt_mode="${CRT_MODE:-}"
if [ -z "$_crt_mode" ]; then
  _cmf="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"
  [ -r "$_cmf" ] && _crt_mode="$(tr -d '[:space:]' < "$_cmf" 2>/dev/null || true)"
fi
_crt_mode="${_crt_mode:-on}"
[ "$_crt_mode" != "on" ] && exit 0

input="$(cat 2>/dev/null || true)"

# --- extract file_path from the PostToolUse JSON: python3 if present, else grep/sed fallback ---
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
# fallback (a file path contains no newlines, so a line-wise grep/sed is safe here):
# The trailing `|| true` is load-bearing under `set -eo pipefail`: on empty/malformed input
# grep matches nothing and returns 1, which pipefail propagates and `set -e` would turn into
# an rc=1 hook abort (a non-fail-open exit). The python-primary path above is already guarded
# the same way; this keeps the fallback fail-open too.
if [ -z "${file_path:-}" ]; then
  file_path="$(printf '%s' "$input" | grep -oE '"file_?[Pp]ath"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//; s/"$//' || true)"
fi

# --- (Slice D1) ADVISORY sibling-propagation matcher -----------------------------
#   SEED-04 (forgetting to propagate a just-derived fix to its sibling call-sites — the
#   canonical `sudo -u`->`sudo -iu` case): when THIS edit looks like a FIX that ELIMINATED
#   a distinctive pattern, grep the project tree for sibling files that still carry it and
#   NAME them. INFORM-ONLY: writes to stderr, never blocks, never changes exit semantics;
#   fail-open (any error / no python3 => stay silent). Runs for ALL edited file types
#   (propagation is language-agnostic; the canonical case is a shell script), BEFORE the
#   R-only gate below — it never disturbs the existing R reminders.
#
#   HEURISTIC (documented; "when unsure, stay silent"):
#     needle = the replaced pattern (tool_input.old_string, or a MultiEdit's first edit).
#       - short single-line snippet (4..100 chars with >=1 distinctive >=4-char non-stopword
#         token) => use the LITERAL phrase (precise; catches a copy-pasted `sudo -u ...`).
#       - long / multi-line => reduce to its LONGEST distinctive identifier token.
#       - otherwise (empty / all-stopword / too short / generic) => SILENT.
#     FIX signal = the needle is present in old_string but ABSENT from new_string (the edit
#       removed/replaced it here) — so a rename/extension that keeps the token, or a pure
#       insertion (no old_string, e.g. Write), never fires.
#     Noise cap: <=5 sibling locations; edited file + common noise dirs excluded; binary /
#       oversized files skipped; walk bounded. python3 -c form (no heredoc, no backticks)
#       mirrors the file_path extractor above and is bash-3.2 / macOS+Linux safe.
if command -v python3 >/dev/null 2>&1; then
  sib_hits="$(printf '%s' "$input" | python3 -c '
import sys, os, json, re
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input", {}) or {}
old = ti.get("old_string"); new = ti.get("new_string")
if old is None:                                  # MultiEdit: use its first edit
    edits = ti.get("edits") or []
    if isinstance(edits, list) and edits and isinstance(edits[0], dict):
        old = edits[0].get("old_string"); new = edits[0].get("new_string")
if not isinstance(old, str):
    sys.exit(0)
if not isinstance(new, str):
    new = ""
edited = ti.get("file_path") or ti.get("filePath") or ti.get("path") or ""
root = d.get("cwd") or os.getcwd()
STOP = set((
    "return value values result results data true false none null self path file files line "
    "text code test tests func function const class print input output error status check "
    "checked update updated change changed apply applied fixed done name type item index "
    "count size total start begin end next prev this that with from into your only just when "
    "then them they will each every some many more most less than where while here there"
).split())
def choose_needle(old, new):
    o = old.strip()
    if not o or o == new.strip():
        return None
    if "\n" not in o and 4 <= len(o) <= 100:
        toks = [t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", o) if t.lower() not in STOP]
        if not toks:
            return None
        needle = o
    else:
        toks = [t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{5,}", o) if t.lower() not in STOP]
        if not toks:
            return None
        needle = max(toks, key=len)
    if len(needle) < 4 or needle in new:         # FIX signal: needle must be ELIMINATED here
        return None
    return needle
needle = choose_needle(old, new)
if not needle:
    sys.exit(0)
try:
    edited_rp = os.path.realpath(edited) if edited else ""
except Exception:
    edited_rp = ""
NOISE = {".git","node_modules",".venv","venv","__pycache__","backups","dist","build",
         ".mypy_cache",".pytest_cache",".ruff_cache","target",".idea",".tox","coverage",
         ".next",".gradle",".svn",".hg"}
MAXB = 512 * 1024; MAXFILES = 4000
hits = []; scanned = 0; stop = False
try:
    for dp, dns, fns in os.walk(root):
        dns[:] = [x for x in dns if x not in NOISE]
        for fn in fns:
            if len(hits) >= 5 or scanned > MAXFILES:
                stop = True; break
            fp = os.path.join(dp, fn)
            try:
                if os.path.islink(fp):
                    continue
                if edited_rp and os.path.realpath(fp) == edited_rp:
                    continue
                sz = os.stat(fp).st_size
                if sz == 0 or sz > MAXB:
                    continue
            except Exception:
                continue
            scanned += 1
            try:
                with open(fp, "rb") as fh:
                    chunk = fh.read(MAXB)
                if b"\x00" in chunk:
                    continue
                txt = chunk.decode("utf-8", "replace")
            except Exception:
                continue
            if needle not in txt:
                continue
            for i, ln in enumerate(txt.splitlines(), 1):
                if needle in ln:
                    hits.append(os.path.relpath(fp, root) + ":" + str(i))
                    break
        if stop:
            break
except Exception:
    sys.exit(0)
if hits:
    sys.stdout.write(", ".join(hits[:5]))
' 2>/dev/null || true)"
  if [ -n "${sib_hits:-}" ]; then
    # printf with the capture as an ARGUMENT (not a heredoc body) so nothing inside a
    # matched path is re-expanded; stderr per the hook message convention; exit unchanged.
    printf '%s\n' \
      "───────────────────────────────────────────────────────" \
      "🔁 fix-propagation check: pattern also at ${sib_hits} — propagate or justify (SEED-04)" \
      "───────────────────────────────────────────────────────" >&2
  fi
fi

# Only trigger on R file edits
if [[ ! "$file_path" =~ \.(r|R)$ ]]; then
    exit 0
fi

# Base review reminder
cat >&2 <<EOF
───────────────────────────────────────────────────────
🔍 R CODE MODIFIED: $file_path
  → grep for changed patterns in other project files
  → check edge cases in any new conditional logic
───────────────────────────────────────────────────────
EOF

# Additional stats alert if file contains modelling functions
if [[ -f "$file_path" ]] && grep -qE "(lm\(|glm\(|lmer\(|glmer\(|gam\(|gamm\(|bam\(|gls\(|nlme\()" "$file_path" 2>/dev/null; then
    cat >&2 <<EOF
📊 Statistical model code detected — verify:
  → k values selected via gam.check() diagnostics?
  → AR1 correlation: rho estimated, AR.start is logical?
  → Assertions on semantic properties (not just syntax)?
───────────────────────────────────────────────────────
EOF
fi

exit 0
