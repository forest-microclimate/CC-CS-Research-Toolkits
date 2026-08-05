#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# subagent_qa_gate.sh — SubagentStop QA scan + ERROR-MODE TELEMETRY. ONE nudge, never a loop.
# STATUS: CURRENT (2026-08-04). O-series (child-QA + measurement).
#
# WHAT: fires when a SUBAGENT finishes. Reads the child's final message, scans it for known
#   error-mode shapes, appends ONE structured row per completion to the error-mode log —
#   CLEAN COMPLETIONS INCLUDED, because a rate needs a denominator — and, only when the scan
#   found something at severity 2 or worse, puts one advisory nudge in front of the model.
#
# WHY IT EXISTS: MEASURED 2026-08-04 — SubagentStop registered: False. Nothing fired when a
#   child finished, so every child's output was judged by whatever attention the coordinator
#   had left at collect. This hook makes the automated half of that judgement deterministic and,
#   more importantly, COUNTED: the ledger question "did the fixes work" is unanswerable without
#   per-completion rows carrying their denominators.
#
# ─── AGENT IDENTITY: WHAT THE DETECTION KEYS ON, AND HOW IT FAILS ─────────────────
#   Stated plainly because everything downstream (which pattern set runs, which row the
#   analyzer counts) hangs on it. THREE keys, tried in order:
#     (1) a top-level `agent_type` in the hook payload. MEASURED PRESENT on a SUBAGENT's
#         PreToolUse payload (see plan-routing-gate.sh's probe notes). NOT measured on
#         SubagentStop — this hook reads it if it is there and does not assume it is.
#     (2) the transcript the payload names: the `subagent_type` of the LAST Task tool_use
#         block found, or a literal `opus5-executor` occurrence in a sidechain record.
#     (3) nothing => "unknown".
#   FAILURE MODE, both directions:
#     * key (1) absent and the transcript unreadable => identity "unknown" => the LIGHT pass
#       only. An opus5-executor child is then UNDER-scanned: a false negative, never a false
#       block. That is the deliberate direction to fail in.
#     * key (2) on a transcript holding SEVERAL Task calls can attribute the LAST one rather
#       than THIS child — the row's `agent_type` is then wrong. The row also carries `pass`,
#       so the analyzer can always see which pattern set actually ran, and a mis-attributed
#       row is visible rather than silent.
#   The row records `agent_type_source` so every identity in the log says how it was reached.
#
# ─── WHAT THE PATTERNS ARE (and are not) ──────────────────────────────────────────
#   Regex CANDIDATE-flaggers over the child's final message, not verdicts. They are tuned for
#   recall and are expected to over-flag; a finding is a pointer for the coordinator's own
#   judgement at collect, which is why the nudge is advisory and the row is data. The judgement
#   tier is the coordinator appending its OWN rows for what the patterns missed — automated
#   detection first, human/coordinator judgement second, both feeding one log.
#
# CONTRACT (bash-hook-contract):
#   IN  : one JSON object on STDIN. Load-bearing: hook_event_name, stop_hook_active,
#         transcript_path, agent_type (when present).
#   OUT : STDOUT is EITHER empty (silent) OR exactly one {"decision":"block","reason":...}
#         object. A Stop-class hook has no advisory-only channel — `block` is the only way to
#         put text in front of the model, and it costs one extra turn, so it is spent only on
#         a severity-2+ finding.
#   EXIT: 0 ALWAYS. Any internal error => INDETERMINATE => fail open, and log it.
#   LOOP GUARD: stop_hook_active set => pass unconditionally. That is what makes the nudge
#         fire at most once per stop sequence.
#   BLAST: reads stdin + the transcript; APPENDS one line to the error-mode log. The log write
#         is best-effort and fully swallowed — a telemetry failure must never break a session,
#         so its errors go to a sidecar `<log>.err` and the hook still exits 0.
#
# MASTER SWITCH (CRT_MODE): "off" = fully inert, no scan and NO row. "observe" = scan and LOG
#   but never nudge — that is exactly the arm for measuring unaided behaviour, so the telemetry
#   must keep running there. "on" (default) = scan, log, and nudge on severity 2+.
# LOG PATH: $CRT_ERROR_MODE_LOG, else ${CLAUDE_PROJECT_DIR:-$PWD}/dev/error_mode_log.jsonl.
# READER: dev/tools/error_mode_rates.py (rates by model x class x severity, with denominators).
# REGRESSION GUARD: tests/test_subagent_qa_gate.sh (fixture matrix, red-before-green).
set -eo pipefail   # NOT set -u — maybe-unset vars are guarded with ${x:-}

_log() {
  local d="${CLAUDE_HOME:-$HOME/.claude}/logs"
  mkdir -p "$d" 2>/dev/null || return 0
  printf '%s subagent_qa_gate: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" \
    >> "$d/subagent-qa-gate.log" 2>/dev/null || true
}

_crt_mode="${CRT_MODE:-}"
if [ -z "$_crt_mode" ]; then
  _cmf="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"
  [ -r "$_cmf" ] && _crt_mode="$(tr -d '[:space:]' < "$_cmf" 2>/dev/null || true)"
fi
_crt_mode="${_crt_mode:-on}"
[ "$_crt_mode" = "off" ] && exit 0

input="$(cat 2>/dev/null || true)"
[ -z "${input:-}" ] && exit 0
command -v python3 >/dev/null 2>&1 || { _log "python3 absent => fail-open"; exit 0; }

QA_LOG="${CRT_ERROR_MODE_LOG:-${CLAUDE_PROJECT_DIR:-$PWD}/dev/error_mode_log.jsonl}"

_outf="${TMPDIR:-/tmp}/sqag_out.$$"
_errf="${TMPDIR:-/tmp}/sqag_err.$$"

set +e
CRT_MODE_RESOLVED="$_crt_mode" QA_LOG="$QA_LOG" python3 - "$input" <<'PYEOF' >"$_outf" 2>"$_errf"
import json, os, re, sys, datetime

# ══ TAXONOMY (the class list; every row's `class` is one of these) ═════════════════
# LIGHT = run on EVERY child completion.  FULL = LIGHT + the rest, run only when the
# child is identified as a supervised opus-5 executor. Keeping the two sets explicit is
# what lets the analyzer divide each class by the RIGHT denominator: a FULL-only class
# was never looked for on a light-pass completion, and counting those completions in its
# denominator would silently deflate its rate.
LIGHT_CLASSES = ("verification-theater", "count-contagion")
HOUSE_CLASSES = ("causal-verb-without-observation", "efficacy-from-existence", "anachronism",
                 "non-co-indexed-comparison", "proxy-for-source", "assert-from-recollection",
                 "premise-unfalsified", "scope-breach")
OPUS5_CLASSES = ("scope-drift", "thrash", "timidity")     # the three the watch exists for
FULL_CLASSES = LIGHT_CLASSES + HOUSE_CLASSES + OPUS5_CLASSES
SEVERITY = {c: 2 for c in LIGHT_CLASSES + OPUS5_CLASSES}
SEVERITY.update({"efficacy-from-existence": 2, "assert-from-recollection": 2, "scope-breach": 3,
                 "causal-verb-without-observation": 1, "anachronism": 1,
                 "non-co-indexed-comparison": 1, "proxy-for-source": 1,
                 "premise-unfalsified": 1})
SCHEMA = 1
SNIPPET_MAX = 120
# Agents whose model is fixed by their own frontmatter pin, so the model IS determinable
# without observing a Task param. Recorded with model_source="agent-pin" so the inference
# is visible in the row rather than laundered into an observation.
PINNED_AGENTS = {"opus5-executor": "claude-opus-5"}

mode = os.environ.get("CRT_MODE_RESOLVED", "on")
log_path = os.environ.get("QA_LOG") or ""


def fail_open(note=""):
    if note:
        sys.stderr.write(note + "\n")
    sys.exit(0)


try:
    obj = json.loads(sys.argv[1])
except Exception:
    fail_open("stdin not JSON")
if not isinstance(obj, dict):
    fail_open("stdin not an object")

if obj.get("hook_event_name") not in (None, "SubagentStop"):
    fail_open("not a SubagentStop payload")

already_nudged = bool(obj.get("stop_hook_active"))

# ── the transcript ────────────────────────────────────────────────────────────────
records = []
tp = obj.get("transcript_path")
if isinstance(tp, str) and tp and os.path.isfile(tp):
    try:
        with open(tp, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    records.append((raw, json.loads(raw)))
                except Exception:
                    records.append((raw, None))
    except Exception:
        records = []


def _msg(rec):
    if not isinstance(rec, dict):
        return {}
    m = rec.get("message")
    return m if isinstance(m, dict) else rec


def role_of(rec):
    m = _msg(rec)
    return m.get("role") or (rec.get("type") if isinstance(rec, dict) else None)


def blocks(rec):
    c = _msg(rec).get("content")
    return c if isinstance(c, list) else []


def text_of(rec):
    c = _msg(rec).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


# ── identity (three keys, in order; the row says which one answered) ──────────────
agent_type, agent_src = None, "none"
at = obj.get("agent_type")
if isinstance(at, str) and at.strip():
    agent_type, agent_src = at.strip(), "payload"
observed_model = None
if agent_type is None:
    for _raw, r in records:
        for b in blocks(r):
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Task":
                ti = b.get("input") if isinstance(b.get("input"), dict) else {}
                st = ti.get("subagent_type")
                if isinstance(st, str) and st.strip():
                    agent_type, agent_src = st.strip(), "transcript-task"
                mdl = ti.get("model")
                if isinstance(mdl, str) and mdl.strip():
                    observed_model = mdl.strip()
if agent_type is None:
    # RAW fallback. MEASURED 2026-08-04 (first live rows): SubagentStop's transcript_path can
    # resolve to a transcript in which the structured Task tool_use block above is NOT present
    # — 10/10 live completions came back agent_type_source="none" while brief_ref DID resolve,
    # so the file was readable and simply held no parseable Task record. A raw line match over
    # the same bytes degrades gracefully where the structured shape differs (the same layering
    # collect_outcome_gate.sh uses). LAST match, not first: a transcript that holds several
    # launches ends with the most recent one.
    RAW_ID = re.compile(r'"(?:subagent_type|agent_type)"\s*:\s*"([^"]+)"')
    hit = None
    for raw, _r in records:
        for m in RAW_ID.finditer(raw):
            hit = m.group(1)
    if hit:
        agent_type, agent_src = hit.strip(), "transcript-raw"
if agent_type is None:
    for raw, r in records:
        if isinstance(r, dict) and r.get("isSidechain") is True and "opus5-executor" in raw:
            agent_type, agent_src = "opus5-executor", "transcript-sidechain"
            break
if agent_type is None:
    agent_type, agent_src = "unknown", "none"

if observed_model:
    model, model_src = observed_model, "task-param"
elif agent_type in PINNED_AGENTS:
    model, model_src = PINNED_AGENTS[agent_type], "agent-pin"
else:
    model, model_src = None, "undetermined"

full = agent_type in PINNED_AGENTS          # the supervised executors get the full set
which_pass = "full" if full else "light"

# ── the child's final message ─────────────────────────────────────────────────────
final = ""
for _raw, r in records:
    if role_of(r) == "assistant":
        t = text_of(r)
        if t.strip():
            final = t

# ── brief_ref: the persisted brief this child was launched from ───────────────────
# LAST match, not first: in a transcript covering several launches the FIRST brief path is the
# OLDEST one. MEASURED 2026-08-04 — the first live rows attributed a stale brief from an earlier
# wave, which is what sent this scan to last-wins.
BRIEF_RX = re.compile(r"(?:dev/briefs/[\w./-]+\.md)")
brief_ref = None
for raw, _r in records:
    for m in BRIEF_RX.finditer(raw):
        brief_ref = m.group(0)
if final:
    for m in BRIEF_RX.finditer(final):
        brief_ref = m.group(0)      # the child's OWN final message beats anything upstream

# ══ DETECTORS ═════════════════════════════════════════════════════════════════════
# Each returns a matched span or None. RECEIPT_RX is the shared "this claim carries the
# thing it rests on" test — a hash, an exit code, a tally, a file:line, a command.
RECEIPT_RX = re.compile(
    r"(exit[= ]\s*\d|rc=\d|\b[0-9a-f]{7,}\b|\b\d+\s*(?:/\s*\d+|passed|failed|rows?|lines?)\b"
    r"|sha\d*|\bdiff\b|:\d+:|`[^`]+`|\bwc -l\b|\bgrep -c\b)", re.I)
WINDOW = 220


def near_receipt(text, span):
    lo = max(0, span[0] - WINDOW)
    hi = min(len(text), span[1] + WINDOW)
    return bool(RECEIPT_RX.search(text[lo:hi]))


def snippet(text, span):
    lo = max(0, span[0] - 30)
    s = " ".join(text[lo:span[1] + 60].split())
    return s[:SNIPPET_MAX]


VERIF_RX = re.compile(r"\b(verified|byte[- ]identical|hash[- ]matched|all \d+ passed|all passed|"
                      r"all[- ]green|tests? pass(?:ed)?|reproduced|confirmed|validated)\b", re.I)
COUNT_RX = re.compile(r"\b(?:all|every)?\s*\d{1,4}\s+(agents?|skills?|hooks?|files?|rows?|"
                      r"tests?|fixtures?|rules?|fragments?|assertions?)\b", re.I)
HEDGE_OK_RX = re.compile(r"\b(guess|guessing|unverified|hypothesis|not checked|unchecked)\b", re.I)
CAUSAL_RX = re.compile(r"\b(because|due to|caused by|the reason is|which is why)\b", re.I)
EFFICACY_RX = re.compile(r"\b(added|wrote|built|created|implemented|shipped|installed|registered)\b"
                         r"[^.\n]{0,90}\b(so|therefore|which means|now)\b[^.\n]{0,90}"
                         r"\b(works?|is fixed|is guarded|is covered|is safe|prevents?|ensures?)\b", re.I)
ANACHRON_RX = re.compile(r"\b(the (?:rule|doc|file|README|guide) (?:says|states|shows))\b"
                         r"[^.\n]{0,90}\b(so|therefore)\b[^.\n]{0,90}"
                         r"\b(violated|should have|had access|was already|knew)\b", re.I)
COMPARE_RX = re.compile(r"\b(compared (?:to|with)|versus|vs\.?|difference between)\b", re.I)
COINDEX_RX = re.compile(r"\b(same (?:coordinate|key|basis|step|window)|joined|merged on|"
                        r"matched on|co-?indexed|aligned|by=)\b", re.I)
PROXY_RX = re.compile(r"\b(?:according to|per|from) the (summary|report|readme|docstring|memory|"
                      r"index|log|manifest)\b|\bthe (summary|docstring|readme|index) says\b", re.I)
RECALL_RX = re.compile(r"\b(as I recall|from memory|if (?:I remember|memory serves)|iirc|"
                       r"I believe the|I recall that)\b", re.I)
PREMISE_RX = re.compile(r"\b(assuming|it must be|clearly the|obviously the|presumably)\b", re.I)
# scope-BREACH is about crossing a stated BOUNDARY; "I also refactored X" is scope-DRIFT and
# belongs to that class alone. Keeping the two disjoint matters: a class that always co-fires
# with another adds no information to the log and inflates both rates.
BREACH_RX = re.compile(r"\b(while I was (?:there|at it)|went ahead and|took the liberty|"
                       r"outside the (?:scope|workspace|brief)|beyond what (?:was|the brief) )\b", re.I)
DRIFT_RX = re.compile(r"\b(I also (?:added|built|created|fixed|refactored)|additionally,? I|"
                      r"beyond the brief|expanded the scope|went further than|"
                      r"in addition,? I (?:added|built|created))\b", re.I)
THRASH_RX = re.compile(r"\b(instead,? I|actually,? I|on second thought|let me try (?:a )?different|"
                       r"switching to|reverted|backed out|changed approach|scrap(?:ped)? that|"
                       r"new approach|that did ?n[o']t work,? so)\b", re.I)
THRASH_MIN = 3        # the COUNT is the signal; one course-correction is not thrash
DECLINE_RX = re.compile(r"\b(I (?:did not|didn't|chose not to|opted not to|refrained from|"
                        r"held off|stopped short of)|rather than risk|out of caution|"
                        r"to be (?:safe|conservative))\b", re.I)
HEDGE_RX = re.compile(r"\b(may|might|could|possibly|potentially|perhaps|it seems|appears to)\b", re.I)
HEDGE_MIN = 8


def scan(text, full):
    out = []

    def add(cls, span):
        out.append({"class": cls, "severity": SEVERITY[cls],
                    "evidence_snippet": snippet(text, span)})

    for m in VERIF_RX.finditer(text):
        if not near_receipt(text, m.span()):
            add("verification-theater", m.span())
            break
    for m in COUNT_RX.finditer(text):
        if not near_receipt(text, m.span()):
            add("count-contagion", m.span())
            break
    if not full:
        return out
    for m in CAUSAL_RX.finditer(text):
        lo, hi = max(0, m.start() - WINDOW), min(len(text), m.end() + WINDOW)
        if not near_receipt(text, m.span()) and not HEDGE_OK_RX.search(text[lo:hi]):
            add("causal-verb-without-observation", m.span())
            break
    for rx, cls in ((EFFICACY_RX, "efficacy-from-existence"), (ANACHRON_RX, "anachronism"),
                    (PROXY_RX, "proxy-for-source"), (RECALL_RX, "assert-from-recollection"),
                    (PREMISE_RX, "premise-unfalsified"), (BREACH_RX, "scope-breach"),
                    (DRIFT_RX, "scope-drift")):
        m = rx.search(text)
        if m:
            add(cls, m.span())
    for m in COMPARE_RX.finditer(text):
        lo, hi = max(0, m.start() - WINDOW), min(len(text), m.end() + WINDOW)
        if not COINDEX_RX.search(text[lo:hi]):
            add("non-co-indexed-comparison", m.span())
            break
    flips = list(THRASH_RX.finditer(text))
    if len(flips) >= THRASH_MIN:
        add("thrash", flips[-1].span())
    dec = DECLINE_RX.search(text)
    if dec and len(HEDGE_RX.findall(text)) >= HEDGE_MIN:
        add("timidity", dec.span())
    return out


findings = scan(final, full) if final.strip() else []

# ══ THE ROW (written for EVERY completion — clean ones are the denominator) ═══════
row = {
    "schema": SCHEMA,
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "agent_type": agent_type,
    "agent_type_source": agent_src,
    "model": model,
    "model_source": model_src,
    "pass": which_pass,
    # n_records distinguishes the two ways identity can come back "unknown": 0 = the transcript
    # was missing or unreadable, >0 = it was read and simply held no identity record. Without it
    # the two are indistinguishable in the log, and they need opposite fixes.
    "n_records": len(records),
    "brief_ref": brief_ref,
    "findings": findings,
    "clean": not findings,
}
if log_path:
    try:
        d = os.path.dirname(log_path)
        if d:
            os.makedirs(d, exist_ok=True)
        # One line, opened in append mode: a short append is atomic enough on POSIX that
        # concurrent children do not interleave, and a partial line is recoverable by the
        # analyzer (it skips unparseable lines and counts them).
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    except Exception as exc:
        # Telemetry NEVER breaks a session: swallow to a sidecar and carry on.
        try:
            with open(log_path + ".err", "a", encoding="utf-8") as eh:
                eh.write("%s %r\n" % (row["ts"], exc))
        except Exception:
            pass

# ══ THE NUDGE (advisory; one, never a loop; severity 2+ only) ═════════════════════
if mode != "on" or already_nudged:
    sys.exit(0)
worst = [f for f in findings if f["severity"] >= 2]
if not worst:
    sys.exit(0)

lines = ["A child (%s) just finished and its final message carries %d flagged shape(s) at "
         "severity 2+. These are CANDIDATES from a regex scan, not verdicts — check each "
         "against the artifact it names before you accept or dismiss it:" % (agent_type, len(worst))]
for f in worst:
    lines.append("  - %s (sev %d): %s" % (f["class"], f["severity"], f["evidence_snippet"]))
lines.append("Spot-check the receipts, then record your OWN judgement of what the scan missed "
             "in the collect row. This nudge fires once.")
print(json.dumps({"decision": "block", "reason": "\n".join(lines)}))
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
  case "$verdict" in
    \{*\}) printf '%s\n' "$verdict"
           _log "nudge emitted: $(printf '%s' "$verdict" | head -c 160)" ;;
    *)     _log "INDETERMINATE: gate stdout was not a JSON object => fail-open" ;;
  esac
fi
exit 0
