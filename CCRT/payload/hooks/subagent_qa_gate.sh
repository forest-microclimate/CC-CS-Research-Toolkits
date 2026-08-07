#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# subagent_qa_gate.sh — SubagentStop QA scan + ERROR-MODE TELEMETRY. ONE nudge, never a loop.
# STATUS: CURRENT (2026-08-06). O-series (child-QA + measurement); F1 rework (child-scoped scan +
#   registration de-dup guard + scan_scope-gated nudge); G1 refinement, build qa3-20260806, schema 2
#   (payload-direct scan text + agent_id attribution + stamp extraction decoupled from scan scope);
#   Z2 addition, build qa4-20260806, schema 2 unchanged (value-gated model-substitution finding:
#   a certified route's serving stamp checked against its shipped model promise).
#   Every row carries `build`, so an analyzer can separate pre-fix from post-fix rates instead of
#   pooling them.
#
# WHAT: fires when a SUBAGENT finishes. Reads the child's final message, scans it for known
#   error-mode shapes, appends ONE structured row per completion to the error-mode log —
#   CLEAN COMPLETIONS INCLUDED, because a rate needs a denominator — and, only when the scan
#   found something at severity 2 or worse, puts one advisory nudge in front of the model.
#   ONE check is VALUE-gated rather than text-shaped (qa4): a certified route's serving stamp
#   checked against its shipped model promise (EXPECTED_MODELS below) — a silent served-model
#   substitution gets loud with zero coordinator discipline.
#
# WHY IT EXISTS: MEASURED 2026-08-04 — SubagentStop registered: False. Nothing fired when a
#   child finished, so every child's output was judged by whatever attention the coordinator
#   had left at collect. This hook makes the automated half of that judgement deterministic and,
#   more importantly, COUNTED: the ledger question "did the fixes work" is unanswerable without
#   per-completion rows carrying their denominators.
#
# ─── SCAN SCOPE: WHOSE TEXT GETS SCANNED (F1 fix; G1 payload-direct refinement) ───
#   MEASURED 2026-08-06 over the 1108 accumulated rows: `transcript_path` on SubagentStop is
#   ALWAYS the PARENT session transcript — every row with the field (1095) carries n_records
#   between 8940 and 16223, none under 1000, and the child's own file (a few hundred records
#   at most) never appeared. So "the last assistant message in transcript_path" is usually the
#   COORDINATOR's latest text, not the finishing child's: 7 measured false flags, each of which
#   cost a turn to refute. The fix is to resolve the CHILD's own slice first and to say, in the
#   row, HOW it was resolved.
#   MEASURED 2026-08-06 13:19 (one LIVE payload captured by a since-retired debug tap; the
#   capture instrument is gone, the measurement stands): the real SubagentStop payload carries,
#   top-level, `last_assistant_message`
#   (the finishing child's final text VERBATIM), `agent_id`, `agent_type`, and
#   `agent_transcript_path` (…/subagents/agent-<id>.jsonl — the field name the shape-match was
#   built to survive not knowing). That measurement is what funds the G1 ladder below: when the
#   payload hands us the child's own text, ZERO transcript parsing is needed for the scan.
#   `scan_scope` says how the scanned text was resolved; its vocabulary, in resolution order:
#     payload-direct          the payload's own `last_assistant_message` IS the scanned text —
#                             the child's final message from the harness itself, verified by
#                             construction. No transcript is parsed for the scan; a child file,
#                             when EXACTLY attributable (payload path / agent_id-derived), is
#                             still read for the serving stamp, meta identity, and brief_ref.
#     child-payload-path      the payload itself named a child transcript (…/subagents/agent-*.jsonl).
#                             Matched by SHAPE, not by key name (measured name:
#                             `agent_transcript_path`), so it works whatever the harness calls
#                             the field.
#     child-derived-id        the payload carried an agent/task id; the child file is derived as
#                             <transcript stem>/subagents/agent-<id>.jsonl.
#     child-sidechain         no child file, but transcript_path itself holds a trailing run of
#                             isSidechain records — the in-file child boundary.
#     child-sibling-newest-fallback  LAST RESORT (relabeled from child-sibling-newest at G1): the
#                             session's subagents/ dir resolved from transcript_path, newest
#                             agent-*.jsonl by mtime, no other candidate inside the tie window.
#                             Child-scoped for certain; WHICH child is by recency. REFUSED when
#                             the payload carried an agent_id: the id's own file being absent
#                             means every sibling candidate is some OTHER child, so a recency
#                             guess would be a GUARANTEED mis-attribution, not a probable one.
#     child-sibling-ambiguous same, but a second candidate sits inside the tie window => the row
#                             is written and NO nudge fires (see below).
#     fallback-whole-file     nothing child-scoped was identifiable. The whole file is scanned so
#                             the row still carries data, the scope says so out loud, a note goes
#                             to the hook log — and NO nudge fires.
#   NUDGE GATE: a nudge fires only on a CHILD-VERIFIED scope. Nudging on text that might be the
#   parent's is the false-positive machine this fix exists to dismantle; a row on an unverifiable
#   scope is still useful data, but it is not evidence worth spending a turn on.
#   n_records counts the records of the SCANNED SCOPE (the child's slice), not the whole file;
#   it is null on payload-direct (the scan is a message, not records). n_records_file is null
#   when the parent transcript was never parsed at all — under payload-direct with identity
#   answered from the meta sidecar / payload, the 8-16k-record parent parse is SKIPPED entirely.
#
# ─── ONE ROW PER EVENT ────────────────────────────────────────────────────────────
#   MEASURED: 1108 rows over 595 distinct timestamps (~1.86x) — the same completion logged twice
#   because the hook was registered in TWO scopes whose command strings differ, and the harness
#   dedups registrations BY COMMAND STRING. That root is fixed in the settings (the $HOME-command
#   copy removed 2026-08-06; the ${CLAUDE_PROJECT_DIR} registration stands). The in-script guard
#   below is defense-in-depth ADDED AFTER that root fix, never instead of it: an identical
#   (agent, scope, text, findings) row inside a 2s window skips the write and LOGS the skip.
#
# ─── AGENT IDENTITY: WHAT THE DETECTION KEYS ON, AND HOW IT FAILS ─────────────────
#   Stated plainly because everything downstream (which pattern set runs, which row the
#   analyzer counts) hangs on it. FOUR keys, tried in order:
#     (0) the resolved child transcript's own `agent-<id>.meta.json` sidecar (`agentType`), read
#         only when a child file was resolved at all. It is the harness's own record of what it
#         launched, so it beats every heuristic below; it also carries the raw launch `model`
#         ARG, and the child's assistant rows carry the SERVING stamp, which outranks the arg.
#     (1) a top-level `agent_type` in the hook payload. MEASURED PRESENT on SubagentStop after
#         all: 263 of the 1108 accumulated rows resolved identity from this key (the header
#         previously recorded it as unmeasured here — corrected 2026-08-06 from the log).
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
#   ATTRIBUTION (G1): the row also records `agent_id` — the payload's own id of the finishing
#   child (measured key `agent_id`; task-id spellings accepted) — beside `child_id`, which stays
#   what it was: the id parsed from whichever child FILE was actually read. The pair makes a
#   mis-attribution VISIBLE in the row (agent_id != child_id) instead of silent.
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
#   BLAST: reads stdin, the transcript, and — when one resolves — the child transcript plus its
#         `agent-<id>.meta.json` sidecar; APPENDS one line to the error-mode log and keeps a
#         short-lived marker under `<log>.dedup/` for the same-event guard. The log write is
#         best-effort and fully swallowed — a telemetry failure must never break a session, so
#         its errors go to a sidecar `<log>.err` and the hook still exits 0.
#
# MASTER SWITCH (CRT_MODE): "off" = fully inert, no scan and NO row. "observe" = scan and LOG
#   but never nudge — that is exactly the arm for measuring unaided behaviour, so the telemetry
#   must keep running there. "on" (default) = scan, log, and nudge on severity 2+.
# LOG PATH: $CRT_ERROR_MODE_LOG, else ${CLAUDE_PROJECT_DIR:-$PWD}/dev/error_mode_log.jsonl.
# READER (dev-side analysis tool, NOT shipped with this hook): error_mode_rates.py in the
#   toolkit's dev tree reads the log (rates by model x class x severity, with denominators);
#   an adopter's log is plain JSONL — any reader works.
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
import json, os, re, sys, datetime, hashlib, time

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
# VALUE-gated (runs on NEITHER pass, qa4): fired from the row's own VALUES — the serving stamp
# vs the certified route's shipped promise (EXPECTED_MODELS) — never from a text shape. Its
# denominator is the completions where agent_type names a certified route AND a serving stamp
# was extracted, not the whole light-pass population.
VALUE_CLASSES = ("model-substitution",)
SEVERITY = {c: 2 for c in LIGHT_CLASSES + OPUS5_CLASSES}
SEVERITY.update({"efficacy-from-existence": 2, "assert-from-recollection": 2, "scope-breach": 3,
                 "causal-verb-without-observation": 1, "anachronism": 1,
                 "non-co-indexed-comparison": 1, "proxy-for-source": 1,
                 "premise-unfalsified": 1})
SEVERITY.update({c: 2 for c in VALUE_CLASSES})   # severity 2 => rides the EXISTING nudge gate
SCHEMA = 2
# SCHEMA 2 (G1, 2026-08-06): adds `agent_id`; makes `n_records` null on payload-direct rows and
# `n_records_file` null when the parent transcript was never parsed; renames the sibling scope
# value to `child-sibling-newest-fallback`. The reader (dev/tools/error_mode_rates.py) accepts
# schema 1 AND 2 rows — the log is append-only history, never rewritten to a new schema.
# BUILD names the hook version that wrote the row: the SCAN CHANGED across builds, so pre-fix
# and post-fix rates must not be pooled. This is the field that separates them; a rate quoted
# across a build boundary without it is two populations.
# qa4 (Z2, 2026-08-06): adds the value-gated model-substitution class; row shape unchanged
# (schema stays 2 — a new findings CLASS is a new value, not a new field).
BUILD = "qa4-20260806"
SNIPPET_MAX = 120
# Same-event guard (defense-in-depth AFTER the registration root fix): an identical row inside
# this window is the same completion arriving twice, not two completions.
DEDUP_WINDOW_S = 2.0
DEDUP_KEEP_S = 300.0        # markers older than this are pruned; the dir stays small
# Two sibling child transcripts written this close together cannot be told apart by recency.
MTIME_TIE_S = 2.0
# Scopes on which a nudge may fire: the scanned text is the finishing child's own.
# payload-direct is child-verified BY CONSTRUCTION — the harness itself handed over the text.
CHILD_VERIFIED_SCOPES = ("payload-direct", "child-payload-path", "child-derived-id",
                         "child-sidechain", "child-sibling-newest-fallback")
# …/subagents/agent-<id>.jsonl — matched by SHAPE so the payload key can be named anything.
CHILD_PATH_RX = re.compile(r"subagents[/\\]agent-([^/\\]+)\.jsonl$")
AGENT_ID_KEYS = ("agent_id", "agentId", "task_id", "taskId", "subagent_id", "subagentId",
                 "toolUseID", "tool_use_id")
# Agents whose model is fixed by their own frontmatter pin, so the model IS determinable
# without observing a Task param. Recorded with model_source="agent-pin" so the inference
# is visible in the row rather than laundered into an observation.
PINNED_AGENTS = {"opus5-executor": "claude-opus-5"}
# The SHIPPED MODEL PROMISE of the two certified routes (name-keyed; qa4). Distinct from
# PINNED_AGENTS on purpose: that map INFERS a model when no observation exists; this one is
# the promise a SERVING STAMP is checked against. An open vendor bug serves substituted models
# on requests the harness resolved correctly (measured 2026-08-04: fable-resolved children
# served claude-opus-5), so a stamp that disagrees with the route's promise is flagged as a
# model-substitution finding. Generic children carry no promise and stay coordinator-audited
# (the model-verification skill); only a serving stamp may fire the check — a launch arg or a
# pin inference is intent, not serving.
EXPECTED_MODELS = {"fable-executor": "claude-fable-5", "opus5-executor": "claude-opus-5"}

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
def read_records(path):
    """[(raw_line, parsed_or_None)] for a JSONL transcript; [] if it cannot be read.

    The raw line is kept beside the parse because the identity fallbacks match on bytes: a
    record whose structure the parser does not recognize can still carry a readable marker.
    """
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    out.append((raw, json.loads(raw)))
                except Exception:
                    out.append((raw, None))
    except Exception:
        return []
    return out


# MEASURED (1095 rows): this path is ALWAYS the parent session transcript, so it is the file to
# resolve the child's slice FROM, never the slice itself. Parsed LAZILY (G1): it runs 8-16k
# records per event, and under payload-direct with identity answered from the meta sidecar or
# the payload it is never needed at all — so the parse happens on first use, or not at all.
tp = obj.get("transcript_path")
tp = tp if (isinstance(tp, str) and tp) else None
_parent_cache = None


def parent_records():
    global _parent_cache
    if _parent_cache is None:
        _parent_cache = read_records(tp) if (tp and os.path.isfile(tp)) else []
    return _parent_cache


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


# ── SCAN SCOPE: resolve the finishing CHILD's own slice (the F1 fix) ─────────────
def _has_assistant_text(run):
    return any(role_of(r) == "assistant" and text_of(r).strip() for _raw, r in run)


def _payload_child_path(o):
    """Any string value in the payload SHAPED like a child transcript path.

    Matched by shape, not by key name: no live SubagentStop payload has been recorded carrying
    such a field, and a branch that waits for the field's NAME is a branch that never runs.
    Top level plus one level of nesting — deep enough for the shapes the harness uses.
    """
    def walk(d, depth):
        for v in d.values():
            if isinstance(v, str) and CHILD_PATH_RX.search(v):
                return v
            if depth and isinstance(v, dict):
                hit = walk(v, depth - 1)
                if hit:
                    return hit
        return None
    return walk(o, 1)


def _payload_agent_id(o):
    for k in AGENT_ID_KEYS:
        v = o.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _subagent_dir(transcript_path):
    """<…>/<sessionId>.jsonl -> <…>/<sessionId>/subagents — the measured harness layout."""
    if not transcript_path or not transcript_path.endswith(".jsonl"):
        return None
    d = os.path.join(transcript_path[: -len(".jsonl")], "subagents")
    return d if os.path.isdir(d) else None


def _trailing_sidechain(recs):
    """The LAST contiguous run of isSidechain records, if it carries assistant text.

    A transcript that inlines child records marks them isSidechain, and the finishing child's
    are the ones at the end. A run with no assistant text is not a scannable slice, so it does
    not win the resolution — the next branch gets its turn instead.
    """
    end = None
    for i in range(len(recs) - 1, -1, -1):
        r = recs[i][1]
        side = isinstance(r, dict) and r.get("isSidechain") is True
        if side:
            if end is None:
                end = i
        elif end is not None:
            run = recs[i + 1:end + 1]
            return run if _has_assistant_text(run) else None
    if end is not None:
        run = recs[:end + 1]
        return run if _has_assistant_text(run) else None
    return None


# ── the ladder (G1): payload-direct first; every demoted rung PRESERVED and labeled ─
scan_records, scan_scope, scan_path, child_id, scope_note = [], None, None, None, None
_sdir = _subagent_dir(tp)
_cand = _payload_child_path(obj)
_aid = _payload_agent_id(obj)
_derived = os.path.join(_sdir, "agent-%s.jsonl" % _aid) if (_sdir and _aid) else None

# Rung 0 (G1): the payload's own `last_assistant_message` IS the finishing child's final text
# (measured live 2026-08-06 13:19) — scan it directly; zero transcript parsing for the scan.
_lam = obj.get("last_assistant_message")
if isinstance(_lam, str) and _lam.strip():
    scan_scope = "payload-direct"

# The EXACTLY-ATTRIBUTED child file, when one exists: the scan source on the fallback ladder,
# and under payload-direct still the source for the serving stamp, meta identity, and brief_ref.
# Exact means payload-named or agent_id-derived — NEVER a recency guess (see the sibling rung).
child_path, child_scope_label = None, None
if _cand and os.path.isfile(_cand):
    child_path, child_scope_label = _cand, "child-payload-path"
elif _derived and os.path.isfile(_derived):
    child_path, child_scope_label = _derived, "child-derived-id"
child_records = read_records(child_path) if child_path else None

if scan_scope == "payload-direct":
    pass                                    # the scan text needs no records at all
elif child_path:
    scan_records, scan_scope, scan_path = child_records, child_scope_label, child_path
else:
    _run = _trailing_sidechain(parent_records())
    if _run:
        scan_records, scan_scope = _run, "child-sidechain"
    elif _sdir and _aid:
        # G1 ATTRIBUTION GUARD: the payload NAMED the finishing child (agent_id) and that
        # child's own file is absent — so every agent-*.jsonl in the dir is some OTHER child,
        # and picking the newest would mis-attribute BY CONSTRUCTION, not by chance. This is
        # the near-simultaneous-completion mis-attribution the sibling heuristic carried.
        # Refuse the guess; fall through to whole-file, where the nudge is already suppressed.
        scope_note = ("agent_id %s is known but its transcript is absent — sibling recency "
                      "guess REFUSED (any candidate would be another child)" % _aid)
    elif _sdir:
        try:
            _files = [(os.path.getmtime(os.path.join(_sdir, f)), os.path.join(_sdir, f))
                      for f in os.listdir(_sdir)
                      if f.startswith("agent-") and f.endswith(".jsonl")]
        except Exception:
            _files = []
        if _files:
            _files.sort(reverse=True)
            _mt, _newest = _files[0]
            # Recency picks the file; a near-simultaneous sibling means recency cannot decide
            # WHICH child, so the scope says ambiguous and the nudge stands down.
            _ties = [p for m, p in _files[1:] if _mt - m <= MTIME_TIE_S]
            scan_records, scan_path = read_records(_newest), _newest
            scan_scope = "child-sibling-ambiguous" if _ties else "child-sibling-newest-fallback"
            if _ties:
                scope_note = ("%d sibling child transcripts written within %.1fs — cannot tell "
                              "which one finished" % (len(_ties) + 1, MTIME_TIE_S))
    if scan_scope is None:
        scan_records, scan_scope = parent_records(), "fallback-whole-file"
    if scan_path and child_path is None:
        # the sibling rung resolved a file: it is the best child file in hand, so the stamp,
        # meta identity, and brief_ref read it — exactly as they did pre-G1.
        child_path, child_records = scan_path, scan_records

if child_path:
    _m = CHILD_PATH_RX.search(child_path)
    child_id = _m.group(1) if _m else None
if scan_scope == "fallback-whole-file" and not scope_note:
    scope_note = ("no child-scoped records identifiable (transcript_path=%s, %d records) — "
                  "scanned the WHOLE file; nudge suppressed" % (tp or "<none>", len(scan_records)))
if scope_note:
    sys.stderr.write("scan_scope=%s: %s\n" % (scan_scope, scope_note))

# ── identity (four keys, in order; the row says which one answered) ──────────────
agent_type, agent_src = None, "none"
observed_model = None
meta_arg_model = None
# (0) the resolved child's OWN meta sidecar — the harness's record of what it launched, so it
#     beats every heuristic below. Only exists when a child FILE was resolved (under
#     payload-direct too: the exactly-attributed file still feeds identity — G1).
if child_path:
    try:
        with open(child_path[: -len(".jsonl")] + ".meta.json", encoding="utf-8",
                  errors="replace") as _mfh:
            _meta = json.load(_mfh)
        if isinstance(_meta, dict):
            _mt2 = _meta.get("agentType")
            if isinstance(_mt2, str) and _mt2.strip():
                agent_type, agent_src = _mt2.strip(), "child-meta"
            _mm = _meta.get("model")
            if isinstance(_mm, str) and _mm.strip():
                meta_arg_model = _mm.strip()
    except Exception:
        pass
# (1) a top-level agent_type in the payload
if agent_type is None:
    at = obj.get("agent_type")
    if isinstance(at, str) and at.strip():
        agent_type, agent_src = at.strip(), "payload"
# (2)-(3) the PARENT transcript's launch records. Deliberately NOT the child's slice: a child's
#     own file records the launches IT made (grandchildren), not its own type. Reaching these
#     rungs is what triggers the parent parse at all (lazy — G1).
if agent_type is None:
    for _raw, r in parent_records():
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
    for raw, _r in parent_records():
        for m in RAW_ID.finditer(raw):
            hit = m.group(1)
    if hit:
        agent_type, agent_src = hit.strip(), "transcript-raw"
if agent_type is None:
    for raw, r in parent_records():
        if isinstance(r, dict) and r.get("isSidechain") is True and "opus5-executor" in raw:
            agent_type, agent_src = "opus5-executor", "transcript-sidechain"
            break
if agent_type is None:
    agent_type, agent_src = "unknown", "none"

# ── which model actually ran ─────────────────────────────────────────────────────
# Precedence follows the project's verification law: the SERVING STAMP (the API's own per-call
# `model` on the child's assistant rows) is the only layer downstream of what ran, so it wins
# whenever the child's file is in hand. The `claude-` prefix is load-bearing — a bare alias in
# that field is a launch ARGUMENT, never a serving stamp. Then the recorded launch args
# (task-param, meta-arg), and only last the agent-pin INFERENCE, which was measured
# mis-attributing on 2026-08-04 (a pinned agent whose run was served a different model).
# Decoupled from the scan scope (G1): the stamp reads whatever child FILE is in hand — under
# payload-direct that is the exactly-attributed file, on the fallback ladder the scanned one.
# FAIL-SOFT by contract: any error here leaves the model null/"undetermined"; it must never
# break the row write. LAST stamp wins — the final assistant turn is the one that answered.
served_model = None
try:
    if child_records:
        for _raw, r in child_records:
            if isinstance(r, dict) and r.get("type") == "assistant":
                _sm = _msg(r).get("model")
                if isinstance(_sm, str) and _sm.startswith("claude-"):
                    served_model = _sm
except Exception:
    served_model = None

if served_model:
    model, model_src = served_model, "serving-stamp"
elif observed_model:
    model, model_src = observed_model, "task-param"
elif meta_arg_model:
    model, model_src = meta_arg_model, "meta-arg"
elif agent_type in PINNED_AGENTS:
    model, model_src = PINNED_AGENTS[agent_type], "agent-pin"
else:
    model, model_src = None, "undetermined"

full = agent_type in PINNED_AGENTS          # the supervised executors get the full set
which_pass = "full" if full else "light"

# ── the child's final message ────────────────────────────────────────────────────
# payload-direct: the payload's own text, VERBATIM — the harness's record of exactly what the
# child said last. Otherwise: the last assistant text of the SCANNED SCOPE, as before.
final = ""
if scan_scope == "payload-direct":
    final = _lam
else:
    for _raw, r in scan_records:
        if role_of(r) == "assistant":
            t = text_of(r)
            if t.strip():
                final = t

# ── brief_ref: the persisted brief this child was launched from ───────────────────
# LAST match, not first: in a transcript covering several launches the FIRST brief path is the
# OLDEST one. MEASURED 2026-08-04 — the first live rows attributed a stale brief from an earlier
# wave, which is what sent this scan to last-wins.
# SCOPED 2026-08-06 (F1): last-wins over the WHOLE parent file attributes whichever brief was
# mentioned most recently in the SESSION — under concurrency that is routinely another child's.
# Last-wins now runs inside the child's own slice, where the last brief path IS this child's.
BRIEF_RX = re.compile(r"(?:dev/briefs/[\w./-]+\.md)")
brief_ref = None
# G1: prefer the exactly-attributed child file's records (in hand under payload-direct too);
# on the fallback ladder they ARE the scanned records, so the pre-G1 behavior is unchanged.
for raw, _r in (child_records if child_records is not None else scan_records):
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

# ── VALUE-gated model-substitution (qa4): the "fail loudly" half ──────────────────
# A certified route's serving stamp disagreeing with its shipped promise IS the open vendor
# substitution bug landing on THIS child. Checked from the row's own values — no text shape,
# no coordinator discipline needed — and APPENDED to findings so the EXISTING row write and
# the EXISTING severity-2+ nudge gate carry it (no parallel nudge path). served_model is only
# ever a real serving stamp (a claude-* value from the child's own assistant rows), so an
# extraction failure stands the check down: fail-soft, the hook's standing direction. The
# bracket suffix strip mirrors model_run_audit's normalize (a capacity tag like `[1m]` is not
# a model). Nothing here may ever cost the row write.
try:
    _expected = EXPECTED_MODELS.get(agent_type)
    if _expected and served_model:
        _served_norm = re.sub(r"\s*\[[^\]]*\]\s*$", "", served_model.strip())
        if _served_norm != _expected:
            findings.append({
                "class": "model-substitution",
                "severity": SEVERITY["model-substitution"],
                "evidence_snippet": (
                    "%s expected %s, serving stamp says %s — served-model substitution — "
                    "treat this child's output accordingly; relaunch with verified-launch "
                    "(warmup + watchdog) if fidelity matters."
                    % (agent_type, _expected, served_model))})
except Exception:
    pass

# ══ THE ROW (written for EVERY completion — clean ones are the denominator) ═══════
row = {
    "schema": SCHEMA,
    "build": BUILD,
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "agent_type": agent_type,
    "agent_type_source": agent_src,
    # agent_id (schema 2) = the payload's OWN id of the finishing child; child_id = the id
    # parsed from whichever child file was read. Divergence between them is a visible
    # mis-attribution, not a silent one.
    "agent_id": _aid,
    "child_id": child_id,
    "scan_scope": scan_scope,
    "model": model,
    "model_source": model_src,
    "pass": which_pass,
    # n_records counts the SCANNED SCOPE (the child's slice); null on payload-direct, where the
    # scan is a message, not records. n_records_file keeps the whole-file count beside it — the
    # number that distinguishes the two ways a record scan comes back empty: 0 = the transcript
    # was missing or unreadable, >0 = it was read and simply held nothing for us. It is null
    # when the parent file was never parsed at all (schema 2, the lazy parse).
    "n_records": (None if scan_scope == "payload-direct" else len(scan_records)),
    "n_records_file": (len(_parent_cache) if _parent_cache is not None else None),
    "brief_ref": brief_ref,
    "findings": findings,
    "clean": not findings,
}


def _dedup_claim(path, key):
    """True if THIS process may write the row; False if an identical one just landed.

    The same completion arriving twice is a REGISTRATION defect, fixed in the settings; this is
    the logged guard behind that fix. The claim is an O_EXCL create, so two hooks firing in the
    same instant cannot both win it — a read-then-write check would let exactly the race it
    exists to stop through.
    """
    d = path + ".dedup"
    now = time.time()
    try:
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            p = os.path.join(d, f)
            try:
                if now - os.path.getmtime(p) > DEDUP_KEEP_S:
                    os.unlink(p)
            except Exception:
                pass
        marker = os.path.join(d, key)
        try:
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.close(fd)
            return True
        except FileExistsError:
            if now - os.path.getmtime(marker) <= DEDUP_WINDOW_S:
                return False
            os.utime(marker, None)
            return True
    except Exception:
        return True          # the guard NEVER costs a row: on any doubt, write it


if log_path:
    try:
        d = os.path.dirname(log_path)
        if d:
            os.makedirs(d, exist_ok=True)
        _key = hashlib.sha1(json.dumps(
            [row["agent_type"], row["scan_scope"], row["child_id"], row["agent_id"], final,
             sorted(f["class"] for f in findings)], sort_keys=True).encode("utf-8")).hexdigest()[:20]
        if not _dedup_claim(log_path, _key):
            sys.stderr.write("duplicate event suppressed (key=%s, within %.1fs) — one row per "
                             "completion\n" % (_key, DEDUP_WINDOW_S))
            sys.exit(0)
        # One line, opened in append mode: a short append is atomic enough on POSIX that
        # concurrent children do not interleave, and a partial line is recoverable by the
        # analyzer (it skips unparseable lines and counts them).
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    except SystemExit:
        raise
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
# The scope gate: a nudge is only worth a turn if the scanned text is provably the child's own.
# On an unverifiable scope the row still carries the finding — as data, not as an accusation.
if scan_scope not in CHILD_VERIFIED_SCOPES:
    sys.stderr.write("nudge suppressed: scan_scope=%s is not child-verified\n" % scan_scope)
    sys.exit(0)
worst = [f for f in findings if f["severity"] >= 2]
if not worst:
    sys.exit(0)

if scan_scope == "payload-direct":
    _src_desc = "its OWN final message (scope=payload-direct, the harness-delivered text)"
else:
    _src_desc = "ITS OWN transcript slice (scope=%s, %d records)" % (scan_scope, len(scan_records))
lines = ["A child (%s) just finished. Scanning %s "
         "found %d flagged shape(s) at severity 2+. These are CANDIDATES from a regex scan, not "
         "verdicts — check each against the artifact it names before you accept or dismiss it:"
         % (agent_type, _src_desc, len(worst))]
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

# A note on stderr with rc=0 is not an error — it is the gate saying something OUT LOUD that the
# row alone would leave quiet (an unverifiable scan scope, a skipped duplicate). Log it either
# way: a silent degradation is indistinguishable from a clean pass, which is the failure the
# fail-open contract is otherwise prone to.
if [ -n "${err:-}" ]; then
  _log "note: $(printf '%s' "$err" | tr '\n' ' ' | cut -c1-300)"
fi

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
