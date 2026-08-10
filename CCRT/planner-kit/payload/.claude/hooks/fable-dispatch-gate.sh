#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# fable-dispatch-gate.sh — PreToolUse, matcher=Task|Agent. THE DENY-CAPABLE LAUNCH GATE (Z6/G1).
# STATUS: CURRENT (2026-08-06). Ships in planner-kit v1.7; deny shape copied from the CCRT's
#   opus-dispatch-guard.sh, brief-path discovery copied VERBATIM from brief_gate.sh (which a
#   sibling task owns — never fold the two hooks together).
#
# WHAT: when the agent is about to LAUNCH a fable/opus5-tier child — subagent_type
#   fable-executor, fable-subplanner or opus5-executor, or model=="fable" — enforce the launch
#   conventions the docs alone keep failing to carry into sessions that never loaded them:
#     CHECK 1 (launch shape): the prompt/description names a dev/briefs/*.md brief, OR the
#       prompt opens with the WARMUP token (a legitimate no-brief warmup/probe shape).
#       Neither => DENY. A NAMED brief that is absent/unreadable => DENY (a dangling brief
#       pointer is a launch defect, not a parse error).
#     CHECK 2 (routing explicitness; when a brief resolves): the brief carries a ^ROLE: line,
#       AND anywhere in the file names ONE of the THREE legal ROLE forms — a persona pointer
#       `agents/<name>.md`, a skill pointer `skills/<name>/SKILL.md`, or the literal
#       `no specialist fits`. Missing => DENY. (Scope = the WHOLE brief — persona and skill
#       read-pointers legitimately ride the WARMUP slot, not the ROLE line.)
#     CHECK 3 (verified-launch; fable tier only, when a brief resolves): the brief carries the
#       WARMUP token — fable-tier children launch with warmup reads so serving is certifiable
#       by ~call 5 (the fable_watchdog contract). Missing => DENY.
#   ALLOWLIST: subagent_type matching ^probe- passes silently (probe cells are legitimate
#   no-brief launches by design). Anything outside the trigger set passes silently.
#
# ─── ADVISORY ARM (KP2, 2026-08-07) — the launch SHAPE, not the brief ──────────────
#   The three checks above judge the BRIEF and can deny. The advisory judges the ROUTE and
#   never denies: on the PASS path, when a launch requests model `fable` from a GENERIC agent
#   type (subagent_type outside the pinned set, ^probe- already allowlisted), it emits ONE
#   hookSpecificOutput.additionalContext note. WHY advisory and not a check: that shape is
#   the MEASURED substitution-prone class (fable requests from full-tools agent types were
#   SERVED claude-opus-5 in ~94% of one measured session population, 49/52, while the pinned
#   restricted-tools routes held) — but it is LEGAL, sometimes necessary, and the defect is a
#   vendor-side bug this gate does not own. So it names the certified alternatives
#   (`fable-executor` for executor work, `fable-subplanner` for sub-planning) and asks for
#   watchdog certification, and the launch proceeds either way. Never a deny, never nonzero.
#
# CONTRACT (per bash-hook-contract; same shape as opus-dispatch-guard.sh):
#   IN : one JSON object on STDIN. Load-bearing: tool_name, cwd,
#        tool_input.{subagent_type,model,prompt,description}.
#   OUT: STDOUT is EITHER empty (silent pass) OR exactly one JSON object carrying
#        hookSpecificOutput.permissionDecision="deny" (reason <=4 lines: the FAILED check, the
#        missing element, the fix, and the template path dev/briefs/_TEMPLATE.md). Any stray
#        echo => malformed JSON => the decision is silently dropped. Debug goes to the log only.
#   EXIT: 0 ALWAYS. The deny rides in the stdout JSON, not the exit code — the model needs the
#        structured reason to re-launch correctly, and that retry is the point. Any internal
#        error (no python3, unparseable stdin) => INDETERMINATE => FAIL-OPEN but LOGGED.
#   BLAST: read-only. Reads stdin plus the one brief file the prompt names.
#
# MASTER SWITCH: an INTERVENTION hook, so it follows the house rule — CRT_MODE "off" and
#   "observe" BOTH silence it; only "on" (the default) enforces.
# REGRESSION GUARD: tests/test_fable_dispatch_gate.sh (toolkit tests/, beside the qa-gate guard).
set -eo pipefail   # NOT set -u — maybe-unset vars are guarded with ${x:-}

_log() {
  local d="${PLANNER_KIT_LOG_DIR:-${CLAUDE_PROJECT_DIR:-.}/.claude/logs}"
  mkdir -p "$d" 2>/dev/null || return 0
  printf '%s fable-dispatch-gate: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" \
    >> "$d/planner-kit-hooks.log" 2>/dev/null || true
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

# House pattern (never capture a heredoc inside $( )): redirect, then read back.
_outf="${TMPDIR:-/tmp}/fdg_out.$$"
_errf="${TMPDIR:-/tmp}/fdg_err.$$"

set +e
python3 - "$input" <<'PYEOF' >"$_outf" 2>"$_errf"
import json, os, re, sys

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
prompt = ti.get("prompt") if isinstance(ti.get("prompt"), str) else ""
desc = ti.get("description") if isinstance(ti.get("description"), str) else ""
cwd = obj.get("cwd") if isinstance(obj.get("cwd"), str) else ""

# ---------- TRIGGER + ALLOWLIST --------------------------------------------------
# THE PINNED ROUTES — the allowlisted route agents whose own frontmatter carries the model, so
# the launch needs no model param. KP2 (2026-08-07) adds `fable-subplanner`: it is fable-TIER,
# so it joins FABLE_TIER_TYPES and CHECK 3's WARMUP requirement applies to it exactly as to
# the executor; it is PINNED, so it is one of the certified alternatives the advisory names.
FABLE_TIER_TYPES = ("fable-executor", "fable-subplanner")
PINNED_TYPES = ("fable-executor", "fable-subplanner", "opus5-executor")

# Prefix-with-boundary on the model (same shape as opus-dispatch-guard classify), so a
# context-suffixed variant like `fable[1m]` is still a fable request.
fable_model = bool(re.match(r"^fable([^a-z0-9-].*)?$", model))
fable_tier = (sub in FABLE_TIER_TYPES) or fable_model
if not (fable_tier or sub in PINNED_TYPES):
    sys.exit(0)                    # outside the trigger set => nothing to judge
if re.match(r"^probe-", sub):
    sys.exit(0)                    # probe cells are legitimate no-brief launches


def deny(check, missing, fix):
    reason = ("DENIED by fable-dispatch-gate — " + check + " FAILED: " + missing + "\n"
              "Fix: " + fix + "\n"
              "Brief form: dev/briefs/_TEMPLATE.md — fill every slot, persist to dev/briefs/ "
              "before launch, and name the file in the prompt.")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)


# ---------- CHECK 1: launch shape ------------------------------------------------
# Brief-path discovery COPIED VERBATIM from brief_gate.sh (quoted spans first — a project
# path may contain spaces; bare-token match is the fallback).
QUOTED = [re.compile(r'"([^"\n]*dev/briefs/[^"\n]*?\.md)"'),
          re.compile(r"'([^'\n]*dev/briefs/[^'\n]*?\.md)'"),
          re.compile(r"`([^`\n]*dev/briefs/[^`\n]*?\.md)`")]
BARE = re.compile(r"""([^\s"'`)\]]*dev/briefs/[^\s"'`)\]]+\.md)""")

hay = prompt + "\n" + desc
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

if not ref:
    if "WARMUP" in prompt:
        sys.exit(0)                # legitimate no-brief warmup/probe shape; nothing more to check
    deny("CHECK 1 (launch shape)",
         "the launch names no dev/briefs/*.md brief and the prompt carries no WARMUP token.",
         "persist a six-element brief and name its path in the prompt (or open the prompt "
         "with WARMUP reads).")

# Resolve the named path (same candidate order as brief_gate.sh): as given, joined to the
# payload's cwd, and the dev/briefs/... suffix joined to cwd. First hit wins.
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

text = None
if path:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except Exception:
        text = None
if text is None:
    # A dangling brief pointer is a LAUNCH defect, not a parse error => DENY, not fail-open.
    deny("CHECK 1 (launch shape)",
         'brief "' + ref + '" is named but absent or unreadable — a dangling brief pointer.',
         "persist the brief file to dev/briefs/ before launch, or correct the path named in "
         "the prompt.")

# ---------- CHECK 2: routing explicitness (whole-brief scope) --------------------
if not re.search(r"^ROLE:", text, re.M):
    deny("CHECK 2 (routing explicitness)",
         "the brief has no ROLE: line.",
         "add a ROLE: line naming the persona and the model route (see the template's ROLE slot).")
# THE THREE LEGAL ROLE FORMS (HDG1, 2026-08-07). The routing doctrine permits all three —
# a persona pointer, a SKILL-ONLY pointer (the specialization rides one or more SKILL.md
# files, no agent persona fits), or the explicit no-specialist declaration — so all three
# pass here AND the deny text below names all three. WHY the text matters as much as the
# predicate: the fix-it line is what a blind session follows, so one that teaches only two
# forms denies a legal launch and then steers the retry away from the form it should use.
if not (re.search(r"agents/[A-Za-z0-9_-]+\.md", text)
        or re.search(r"skills/[A-Za-z0-9_-]+/SKILL\.md", text)
        or "no specialist fits" in text):
    deny("CHECK 2 (routing explicitness)",
         "the brief names none of the THREE legal ROLE forms.",
         "name ONE of them anywhere in the brief: a persona pointer agents/<name>.md, a "
         'skill pointer skills/<name>/SKILL.md, or the literal "no specialist fits".')

# ---------- CHECK 3: verified-launch (fable tier only; reads the BRIEF) ----------
if fable_tier and "WARMUP" not in text:
    deny("CHECK 3 (verified-launch)",
         "the brief carries no WARMUP slot — fable-tier launches open with warmup reads so "
         "serving is certifiable by ~call 5.",
         "add the WARMUP block (4 small opening reads; persona/skill read-pointers preferred) "
         "and run the watchdog on the child transcript.")

# ---------- ADVISORY (KP2): the substitution-prone launch SHAPE ------------------
# PASS PATH ONLY — every check above is satisfied, so this launch is going ahead. What is
# left is a ROUTE risk, not a defect: a `fable` request from a GENERIC agent type is the
# measured substitution-prone shape. One note, no decision field, exit 0 — the launch is
# never blocked and the exit code never moves (a deny here would break the sub-planner
# relay and every other legitimate generic-agent fable launch).
if fable_model and sub not in PINNED_TYPES:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext":
            "ADVISORY (fable-dispatch-gate): this launch requests model `fable` on the "
            "generic agent type %r. Generic-agent + fable is the MEASURED "
            "substitution-prone class: fable requests from full-tools agent types were "
            "SERVED claude-opus-5 in ~94%% of one measured session population (49/52), "
            "while the pinned restricted-tools routes held. The certified alternatives are "
            "`fable-executor` (executor work) and `fable-subplanner` (sub-planning), whose "
            "frontmatter pins carry the model so no model param is needed. Proceeding as "
            "launched is legitimate — but CERTIFY it rather than assume it: run "
            ".claude/skills/model-verification/fable_watchdog.py --watch on the child "
            "transcript (FAITHFUL/0 = certified · SWAPPED@k/1 = relaunch or proceed "
            "knowingly and log it · UNDETERMINED/2 = investigate). A correct request is "
            "not yet the run you asked for." % (sub or "<unnamed>")}}))
    sys.exit(0)

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
           # KP2: stdout now carries EITHER a deny OR the pass-path advisory — label the log
           # by which, or a future reader cannot tell a blocked launch from an advised one.
           case "$verdict" in
             *'"permissionDecision"'*) _log "DENY: $(printf '%s' "$verdict" | head -c 200)" ;;
             *)                        _log "ADVISORY: $(printf '%s' "$verdict" | head -c 200)" ;;
           esac ;;
    *)     _log "INDETERMINATE: gate stdout was not a JSON object => fail-open" ;;
  esac
fi
exit 0
