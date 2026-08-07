#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""adherence_scorecard.py -- per-session workflow-adherence scorecard for CC transcripts.

PAYLOAD COPY (planner-kit v1.8) -- the PORTABILITY delta of its authoring master,
dev/tools/adherence_scorecard.py in the kit's origin workspace. ONE delta: the lineage
MAIN/ARENA slug patterns are DERIVED from THIS project's root (--project-slug, else
$CLAUDE_PROJECT_DIR, else the cwd) instead of hardcoding the origin workspace's folder
name, so an adopter's own sessions read MAIN and its sandbox/ probe projects read ARENA.
Every dimension, count and column below is the master unchanged.

USAGE:
  python3 dev/tools/adherence_scorecard.py <session.jsonl | dir-of-jsonl> [--json|--tsv]
  python3 dev/tools/adherence_scorecard.py <dir> --append            # -> dev/ADHERENCE_LOG.tsv
  python3 dev/tools/adherence_scorecard.py <dir> --append <log> --since 2026-08-01
  python3 dev/tools/adherence_scorecard.py <dir> --append --split 2026-08-07T07:00:00Z
  python3 dev/tools/adherence_scorecard.py <dir> --project-slug my-project   # lineage tail
  Scores five greppable dimensions D1..D5 as n/N (n = compliant, N = opportunities; "-" = no
  opportunity) and appends one idempotent row per session+phase. Self-test: test_adherence_scorecard.sh

WHY: the Z-series shipped deterministic enforcement gates (deny at plan approval, deny at
fable-tier launch, one-shot block at uncertified turn end, loud flag at swapped completion).
Whether they IMPROVE working-session fidelity is an efficacy question answered only by an
interrupted time-series of per-session adherence, before vs after the gates. This is the
instrument, not a verdict: it MEASURES; it never blocks, never edits, never writes outside
its named outputs, and fails soft on every unreadable input.

DIMENSIONS (each n/N; denominator = opportunities OBSERVED in that session):
  D1 plan-routing      N = ExitPlanMode tool_use calls.
                       n = calls whose PAIRED tool_result carries NEITHER
                           /permissionDecision.*deny/ NOR "BLOCKED by plan-routing-gate".
                       JSON also carries d1_final_undenied -- the FINAL call un-denied is
                       the "compliant-at-approval" fact; a denied-then-approved session
                       scores 1/2 because the denial IS the gate correcting, not a silent miss.
  D2 launch-brief      N = Task|Agent tool_use with subagent_type in {fable-executor,
                           opus5-executor} or a fable model arg (^fable boundary form),
                           minus the ^probe- allowlist -- the fable-dispatch-gate's own
                           trigger set, mirrored so gate and scorecard agree on "compliant".
                       n = prompt+description names a dev/briefs/*.md brief (the gate's
                           QUOTED-then-BARE regexes, verbatim) OR the prompt carries WARMUP.
                       d2_denials counts gate denials separately.
  D3 certification     N = those D2 launches that actually RAN (paired tool_result carrying
                           an agentId) and are FABLE-tier.
                       n = a certification appears AFTER the launch result and before the
                           session ends: /FAITHFUL|SWAPPED@|UNDETERMINED|"model":"claude-/
                           in DECODED content text only (collect_outcome_gate's deep_texts
                           rule -- a record's own envelope model field is never a receipt).
  D4 collect-outcome   N = turn segments (split at GENUINE user messages: role=user, no
                           tool_result block, not a <task-notification>, not a sidechain)
                           that hold a COMPLETED subagent result (a toolUseResult with an
                           agentId and status != async_launched, or a <task-notification>).
                       n = segments whose ASSISTANT text names one of the six outcomes
                           CONTINUE | RE-ROUTE (REROUTE) | FIX-FIRST | ABORT | GOAL-MET | ADAPT.
                       DEVIATION, stated: matched CASE-SENSITIVELY. collect_outcome_gate uses
                       re.I because a fail-open nudge should not annoy; a measurement whose
                       token "continue" fires on ordinary prose measures nothing.
  D5 brief-persistence N = briefs named in D2 launches whose path is RESOLVABLE (absolute, or
                           a session cwd is on record); unresolvable ones are EXCLUDED from N
                           and counted as d5_unresolvable.
                       n = the resolved brief exists on disk. Best-effort by construction: a
                           brief deleted or renamed after the session reads as a miss.
  D6 tier-explicitness N = EVERY delegate-class launch -- all Task|Agent tool_use rows, not
                           just the gated ones. D1-D5 measure how well the FABLE/OPUS5 launches
                           were run; D6 measures whether the TIER was decided at all, which is
                           a question about every child.
                       n = the launch input carries a `model` param, OR its subagent_type is a
                           PINNED type (fable-executor | fable-subplanner | opus5-executor) or
                           matches ^probe-. A pinned/probe type IS an explicit tier choice --
                           the model comes from that agent's own frontmatter pin, so naming the
                           type names the tier. Everything else is an OMITTED param, which is
                           rank 4: it requests whatever the main model happens to be. That is
                           a legal launch and sometimes the right one; the dimension measures
                           how often the choice was RECORDED, never whether it was wise.

KP2 ADDITION (2026-08-07; additive -- D1..D5 definitions untouched, their cells reproduce
Z9b exactly): D6 above, plus `fable-subplanner` joining the pinned/gated type sets so D2's
trigger set keeps MIRRORING the fable-dispatch-gate's (the gate gained the type the same day;
a mirror that lags is a mirror that disagrees). No historical session carries such a launch,
so every pre-KP2 D2 cell is unchanged.

Z9b ADDITIONS (both additive -- no dimension definition changed; without --split every
number reproduces Z9 byte-for-byte):

  --split <ISO-8601>  PER-TURN PHASE. Z9's interrupted time-series was not interpretable
    because a session was filed whole under its START date: one straddling session put 469
    of 471 pre-gate opportunities on the PRE side while running hours past the gates' ship
    instant. So an OPPORTUNITY, not a session, is now the dated unit -- each is dated by the
    transcript record that CARRIES it:
      D1 the ExitPlanMode tool_use record | D2, D5 the launch tool_use record
      D3 the launch RESULT record -- the record that OPENS the certification window (a
         certification is a fact about the window, so the window's opening instant dates it)
      D4 the record that CLOSES the segment (the next genuine user message; EOF => the last
         timestamped record seen).
    A session emits up to two rows, same session_id, phase pre | post; the --append replace
    key is session_id+phase. Phase is "all" when --split is absent. UNDATED opportunities (no
    parseable timestamp on their carrying record) are EXCLUDED from N under --split and
    counted in undated_opportunities -- never guessed onto a side. Without --split nothing
    needs dating, so nothing is excluded. A session with ZERO opportunities emits one row
    placed by its own start timestamp (nothing to date; it contributes 0/0 either way).
    Timestamps parse as ISO-8601 (trailing Z and fractional seconds included); a tz-less
    stamp is read as UTC, stated here because a convention is not a guess.

  lineage  COLUMN, from the transcript's slug directory, so arena traffic cannot masquerade
    as working sessions: MAIN = a slug ENDING in THIS project's own slug tail
    (--project-slug, else $CLAUDE_PROJECT_DIR, else the cwd) | ARENA = a slug carrying
    "<tail>-sandbox-", i.e. a probe project under this project's sandbox/ quarantine
    (briefless by construction; in the origin workspace they were 70% of the post-gate
    opportunities) | OTHER = anything else.
    The ITS HEADLINE is MAIN-only; ARENA and OTHER rows stay in the log and the exclusion is
    printed with the headline.

ENGINEERING: stdlib only; every transcript is STREAM-parsed line by line (they reach 25MB);
malformed lines are counted and reported, never fatal; files with zero assistant rows are
skipped; output ordering is deterministic (start-date, then session id).
EXIT: 0 = scored (or nothing to score) | 2 = input/parse error. Never gates on adherence --
a scorecard that failed a build would stop being a measurement and start being a gate.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

DEFAULT_LOG = os.path.join("dev", "ADHERENCE_LOG.tsv")
SYNTHETIC = "<synthetic>"

COLUMNS = ["session_id", "start_date", "phase", "lineage", "main_model",
           "D1_plan_routing", "D2_launch_brief", "D3_certification",
           "D4_collect_outcome", "D5_brief_persistence", "D6_tier_explicitness",
           "miss_count", "opportunity_count"]
DIM_KEYS = COLUMNS[5:11]
PHASE_RANK = {"pre": 0, "post": 1, "all": 2, "-": 3}
UTC = datetime.timezone.utc

# ---- token sets (greppable-stable; a future session reproduces today's numbers) ----------
FABLE_TIER_TYPES = ("fable-executor", "fable-subplanner")
GATED_TYPES = ("fable-executor", "fable-subplanner", "opus5-executor")
# D6 (KP2): naming a pinned type IS naming a tier -- the model rides on that agent's own
# frontmatter pin, so such a launch needs no model param and is not an omitted decision.
PINNED_TYPES = GATED_TYPES
FABLE_MODEL_RE = re.compile(r"^fable([^a-z0-9-].*)?$")          # gate's boundary form
PROBE_RE = re.compile(r"^probe-")                                # gate's allowlist
PLAN_DENY_RE = re.compile(r"permissionDecision.*deny")
PLAN_DENY_MARKER = "BLOCKED by plan-routing-gate"
LAUNCH_DENY_MARKER = "DENIED by fable-dispatch-gate"
CERT_RE = re.compile(r'FAITHFUL|SWAPPED@|UNDETERMINED|"model":"claude-')
OUTCOME_RE = re.compile(r"(?<![A-Za-z0-9])(CONTINUE|RE-ROUTE|REROUTE|FIX-FIRST|ABORT|"
                        r"GOAL-MET|ADAPT)(?![A-Za-z0-9])")      # case-SENSITIVE (see docstring)
TASK_NOTIFICATION = "<task-notification>"

# brief-path discovery -- COPIED VERBATIM from fable-dispatch-gate.sh CHECK 1
QUOTED = [re.compile(r'"([^"\n]*dev/briefs/[^"\n]*?\.md)"'),
          re.compile(r"'([^'\n]*dev/briefs/[^'\n]*?\.md)'"),
          re.compile(r"`([^`\n]*dev/briefs/[^`\n]*?\.md)`")]
BARE = re.compile(r"""([^\s"'`)\]]*dev/briefs/[^\s"'`)\]]+\.md)""")

# cheap line pre-filter: a line carrying none of these cannot contribute to any dimension.
PREFILTER = ('"tool_use"', '"tool_result"', 'toolUseResult', '"user"', '"assistant"',
             'task-notification', 'FAITHFUL', 'SWAPPED@', 'UNDETERMINED', '"model":"claude-',
             'CONTINUE', 'RE-ROUTE', 'REROUTE', 'FIX-FIRST', 'ABORT', 'GOAL-MET', 'ADAPT')


# lineage classification (Z9b) -- read from the transcript's SLUG DIRECTORY, never its content.
# PORTABILITY (payload copy): the two patterns are BUILT from this project's own root, not
# hardcoded. Claude Code names a session directory after the project PATH with every
# non-alphanumeric run collapsed to "-", so the project's own slug TAIL identifies its
# sessions: MAIN = a slug ENDING in the tail; ARENA = a slug carrying "<tail>-sandbox-", i.e.
# a probe project under this project's sandbox/ quarantine -- a structural fact of the folder
# contract, not a naming accident. A root whose basename yields NO alphanumeric tail leaves
# both patterns unmatchable and every row reads OTHER: unclassified is honest, whereas a
# pattern that matched everything would silently relabel foreign traffic as this project's.
NEVER_RE = re.compile(r"(?!x)x")            # matches nothing (the honest empty-tail fallback)


def normalize_slug(s):
    """Claude Code's session-dir naming: every non-alphanumeric run collapses to "-"."""
    return re.sub(r"[^A-Za-z0-9]+", "-", s or "").strip("-")


def slug_tail(path):
    """A project root's own slug tail: '/a b/My Proj' -> 'My-Proj'."""
    return normalize_slug(os.path.basename(os.path.abspath(path)))


def lineage_patterns(tail):
    """(arena_re, main_re) for a slug tail; unmatchable patterns when the tail is empty."""
    if not tail:
        return NEVER_RE, NEVER_RE
    esc = re.escape(tail)
    return re.compile(esc + r"-sandbox-"), re.compile(esc + r"$")


PROJECT_SLUG = slug_tail(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
ARENA_SLUG_RE, MAIN_SLUG_RE = lineage_patterns(PROJECT_SLUG)


def set_project_slug(value):
    """Rebind the lineage patterns to VALUE (a slug tail OR a project path -- both normalize
    to the same token, since a CC slug is just the path with non-alphanumerics collapsed)."""
    global PROJECT_SLUG, ARENA_SLUG_RE, MAIN_SLUG_RE
    PROJECT_SLUG = normalize_slug(value)
    ARENA_SLUG_RE, MAIN_SLUG_RE = lineage_patterns(PROJECT_SLUG)
    return PROJECT_SLUG

# ISO-8601 fallback: 'YYYY-MM-DDTHH:MM:SS[.frac][Z|±HH:MM|±HHMM]'
TS_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})"
                   r"(?:\.(\d+))?\s*(Z|z|[+-]\d{2}:?\d{2})?$")


class InputError(Exception):
    """Unusable input path -> exit 2."""


def classify_lineage(path):
    """MAIN | ARENA | OTHER from the slug dir holding the transcript (ARENA checked first:
    an arena slug also ends in a workspace-derived suffix, so exactness alone cannot split
    them and order is the discriminator)."""
    slug = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if ARENA_SLUG_RE.search(slug):
        return "ARENA"
    if MAIN_SLUG_RE.search(slug):
        return "MAIN"
    return "OTHER"


def parse_ts(s):
    """ISO-8601 string -> aware UTC datetime, or None. NEVER guesses: anything unparseable
    comes back None and its opportunity is excluded from N rather than placed on a side."""
    if not isinstance(s, str) or not s.strip():
        return None
    t = s.strip()
    iso = t[:-1] + "+00:00" if t[-1:] in ("Z", "z") else t
    try:
        dt = datetime.datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        m = TS_RE.match(t)
        if not m:
            return None
        y, mo, d, h, mi, se, frac, off = m.groups()
        try:
            dt = datetime.datetime(int(y), int(mo), int(d), int(h), int(mi), int(se),
                                   int((frac or "0").ljust(6, "0")[:6]))
        except ValueError:
            return None
        if off and off not in ("Z", "z"):
            sign = -1 if off[0] == "-" else 1
            hh, mm = off[1:].replace(":", "")[:2], off[1:].replace(":", "")[2:4]
            try:
                dt = dt.replace(tzinfo=datetime.timezone(
                    sign * datetime.timedelta(hours=int(hh), minutes=int(mm or 0))))
            except ValueError:
                return None
        else:
            dt = dt.replace(tzinfo=UTC)
    if dt.tzinfo is None:            # tz-less stamp read as UTC (stated convention, not a guess)
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def phase_of(ts, split):
    """'all' with no split; 'pre'/'post' relative to the split instant; None when undated."""
    if split is None:
        return "all"
    if ts is None:
        return None
    return "pre" if ts < split else "post"


# ---------------------------------------------------------------- record helpers
def _msg(rec):
    m = rec.get("message")
    return m if isinstance(m, dict) else rec


def blocks(rec):
    c = _msg(rec).get("content")
    return c if isinstance(c, list) else []


def role_of(rec):
    return _msg(rec).get("role") or rec.get("type")


def assistant_text(rec):
    """Text blocks only -- thinking blocks are not the reply the reader sees."""
    c = _msg(rec).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


def deep_texts(x, acc, depth=0):
    """Every DECODED content string in a record (collect_outcome_gate's rule, mirrored).

    Deliberately NOT the record's own metadata fields (model, id, ...) and NOT tool_use
    inputs -- a serving-stamp receipt must come from content someone actually put in front
    of the coordinator, not from the transcript's own envelope.
    """
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


def result_text(rec, blk):
    """The paired tool_result's readable text plus a string-valued toolUseResult."""
    c = blk.get("content")
    parts = [c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)]
    tur = rec.get("toolUseResult")
    if isinstance(tur, str):
        parts.append(tur)
    return "\n".join(p for p in parts if p)


def find_brief_ref(prompt, desc):
    """fable-dispatch-gate CHECK 1 discovery: quoted spans first, bare token as fallback."""
    hay = (prompt or "") + "\n" + (desc or "")
    for rx in QUOTED:
        m = rx.search(hay)
        if m:
            return m.group(1).strip()
    m = BARE.search(hay)
    return m.group(1).strip() if m else ""


def resolve_brief(ref, cwd):
    """(status, path) -- status in {'exists', 'missing', 'unresolvable'}."""
    if not ref:
        return "unresolvable", ""
    cands = []
    if os.path.isabs(ref):
        cands.append(ref)
    elif cwd:
        tail = ref[ref.find("dev/briefs/"):] if "dev/briefs/" in ref else ref
        for p in (os.path.join(cwd, ref), os.path.join(cwd, tail)):
            if p not in cands:
                cands.append(p)
    else:
        return "unresolvable", ref
    for p in cands:
        try:
            if os.path.isfile(p):
                return "exists", p
        except OSError:
            continue
    return "missing", cands[0]


# ---------------------------------------------------------------- the scorer
def score_session(path, split=None):
    """Score one session transcript. Returns a LIST of row dicts -- one per phase present
    (Z9b: a straddling session emits two) -- or None when there is nothing to score (no
    assistant rows). Never raises on transcript content."""
    session_id = os.path.basename(path)[: -len(".jsonl")]
    st = {"malformed": 0, "first_model": None, "start_ts": None, "cwd": ""}

    pending = {}          # tool_use id -> info, for ExitPlanMode / Task / Agent only
    epm = []              # one dict per ExitPlanMode call, in call order
    launches = []         # one dict per gated launch opportunity
    d6 = []               # one dict per DELEGATE-CLASS launch (wider than `launches`)
    segments = []         # one dict per CLOSED segment that held a completed subagent result
    max_cert_idx = -1
    seg = {"completed": False, "outcome": False}
    last_ts = None        # most recent PARSED record timestamp (EOF closes on it)
    saw_assistant = False

    def close_segment(ts):
        if seg["completed"]:
            segments.append({"ok": seg["outcome"], "ts": ts})
        seg["completed"] = seg["outcome"] = False

    try:
        fh = open(path, "r", errors="replace")
    except OSError as exc:
        raise InputError("unreadable transcript %s (%s)" % (path, exc))

    idx = 0
    with fh:
        for line in fh:
            idx += 1
            line = line.strip()
            if not line:
                continue
            if not any(tok in line for tok in PREFILTER):
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                st["malformed"] += 1
                continue
            if not isinstance(rec, dict):
                st["malformed"] += 1
                continue

            if isinstance(rec.get("cwd"), str) and rec["cwd"]:
                st["cwd"] = rec["cwd"]
            if st["start_ts"] is None and isinstance(rec.get("timestamp"), str):
                st["start_ts"] = rec["timestamp"]
            rec_ts = parse_ts(rec.get("timestamp"))     # None => this record dates nothing
            if rec_ts is not None:
                last_ts = rec_ts

            rtype = rec.get("type")
            if rtype == "assistant":
                saw_assistant = True
                if st["first_model"] is None:
                    mm = _msg(rec).get("model")
                    if isinstance(mm, str) and mm and mm != SYNTHETIC:
                        st["first_model"] = mm

            # ---- certification hits: DECODED text only, anywhere in the transcript ------
            if CERT_RE.search(line):
                acc = []
                deep_texts(rec, acc)
                if CERT_RE.search("\n".join(acc)):
                    max_cert_idx = idx

            # ---- D4 segmentation ---------------------------------------------------------
            body = blocks(rec)
            has_tool_result = any(isinstance(b, dict) and b.get("type") == "tool_result"
                                  for b in body)
            raw_content = _msg(rec).get("content")
            is_notification = (isinstance(raw_content, str)
                               and TASK_NOTIFICATION in raw_content)
            if (rtype == "user" and not has_tool_result and not is_notification
                    and rec.get("isSidechain") is not True):
                close_segment(rec_ts)      # strictly the CLOSING record's own instant
            if is_notification:
                seg["completed"] = True
            if rtype == "assistant" and OUTCOME_RE.search(assistant_text(rec)):
                seg["outcome"] = True

            tur = rec.get("toolUseResult")
            if isinstance(tur, dict) and tur.get("agentId"):
                if tur.get("status") != "async_launched":
                    seg["completed"] = True

            # ---- tool_use / tool_result pairing -------------------------------------------
            for b in body:
                if not isinstance(b, dict):
                    continue
                btype = b.get("type")
                if btype == "tool_use":
                    name = b.get("name")
                    if name == "ExitPlanMode":
                        epm.append({"denied": False, "ts": rec_ts})
                        pending[b.get("id")] = {"kind": "epm", "slot": len(epm) - 1}
                    elif name in ("Task", "Agent"):
                        ti = b.get("input") if isinstance(b.get("input"), dict) else {}
                        sub = str(ti.get("subagent_type") or "").strip().lower()
                        model = str(ti.get("model") or "").strip().strip("`\"'").lower()
                        # D6 (KP2): every delegate-class launch is a tier-explicitness
                        # opportunity, counted HERE -- before the two filters below, which
                        # deliberately narrow D2/D3/D5 to the gate's own trigger set.
                        d6.append({"ok": (bool(model) or sub in PINNED_TYPES
                                          or bool(PROBE_RE.match(sub))),
                                   "ts": rec_ts})
                        if PROBE_RE.match(sub):
                            continue
                        fable_tier = (sub in FABLE_TIER_TYPES) or bool(FABLE_MODEL_RE.match(model))
                        if not (fable_tier or sub in GATED_TYPES):
                            continue
                        prompt = ti.get("prompt") if isinstance(ti.get("prompt"), str) else ""
                        desc = ti.get("description") if isinstance(ti.get("description"), str) else ""
                        ref = find_brief_ref(prompt, desc)
                        launches.append({
                            "idx": idx, "subagent_type": sub, "model_arg": model,
                            "fable_tier": fable_tier,
                            "compliant": bool(ref) or ("WARMUP" in prompt),
                            "brief_ref": ref, "cwd": st["cwd"], "ts": rec_ts,
                            "denied": False, "ran": False, "result_idx": None,
                            "result_ts": None,
                        })
                        pending[b.get("id")] = {"kind": "launch", "slot": len(launches) - 1}
                elif btype == "tool_result":
                    info = pending.pop(b.get("tool_use_id"), None)
                    if not info:
                        continue
                    text = result_text(rec, b)
                    if info["kind"] == "epm":
                        if PLAN_DENY_MARKER in text or PLAN_DENY_RE.search(text):
                            epm[info["slot"]]["denied"] = True
                    else:
                        L = launches[info["slot"]]
                        if LAUNCH_DENY_MARKER in text:
                            L["denied"] = True
                        agent_id = tur.get("agentId") if isinstance(tur, dict) else None
                        if agent_id:
                            L["ran"] = True
                            L["result_idx"] = idx
                            L["result_ts"] = rec_ts    # opens the certification window

    close_segment(last_ts)             # EOF: the last timestamped record seen (docstring rule)
    if not saw_assistant:
        return None

    # ---- one dated OPPORTUNITY per scorable event (Z9b: the opportunity is the unit) -----
    opps = []          # {"dim", "ok", "ts"}  -- counted in n/N
    notes = []         # {"kind", "ts"}       -- phase-scoped extras, never counted in N
    for e in epm:
        opps.append({"dim": "D1_plan_routing", "ok": not e["denied"], "ts": e["ts"]})
    for L in launches:
        opps.append({"dim": "D2_launch_brief", "ok": L["compliant"], "ts": L["ts"]})
        if L["denied"]:
            notes.append({"kind": "d2_deny", "ts": L["ts"]})
        if L["ran"] and L["fable_tier"]:
            opps.append({"dim": "D3_certification",
                         "ok": max_cert_idx > (L["result_idx"] or 0), "ts": L["result_ts"]})
        if L["brief_ref"]:
            status, _p = resolve_brief(L["brief_ref"], L["cwd"])
            if status == "unresolvable":
                notes.append({"kind": "d5_unres", "ts": L["ts"]})
            else:
                opps.append({"dim": "D5_brief_persistence",
                             "ok": status == "exists", "ts": L["ts"]})
    for s in segments:
        opps.append({"dim": "D4_collect_outcome", "ok": s["ok"], "ts": s["ts"]})
    for L in d6:
        opps.append({"dim": "D6_tier_explicitness", "ok": L["ok"], "ts": L["ts"]})

    # ---- bucket by phase; UNDATED opportunities are excluded, never placed ---------------
    groups, undated = {}, 0
    for o in opps:
        ph = phase_of(o["ts"], split)
        if ph is None:
            undated += 1
            continue
        groups.setdefault(ph, {"opps": [], "notes": []})["opps"].append(o)
    for nt in notes:
        ph = phase_of(nt["ts"], split)
        if ph is not None:
            groups.setdefault(ph, {"opps": [], "notes": []})["notes"].append(nt)
    if not groups:                     # no opportunities: place the empty row by session start
        ph = phase_of(parse_ts(st["start_ts"]), split) or "-"
        groups[ph] = {"opps": [], "notes": []}

    lineage = classify_lineage(path)
    rows = []
    for ph in sorted(groups, key=lambda p: PHASE_RANK.get(p, 9)):
        g = groups[ph]
        dims = [(k, sum(1 for o in g["opps"] if o["dim"] == k and o["ok"]),
                 sum(1 for o in g["opps"] if o["dim"] == k)) for k in DIM_KEYS]
        d1 = [o for o in g["opps"] if o["dim"] == "D1_plan_routing"]
        row = {
            "session_id": session_id,
            "start_date": (st["start_ts"] or "")[:10] or "-",
            "phase": ph, "lineage": lineage,
            "main_model": st["first_model"] or "-",
            "miss_count": sum(dd - nn for _k, nn, dd in dims),
            "opportunity_count": sum(dd for _k, _n, dd in dims),
            "path": path, "cwd": st["cwd"],
            "malformed_lines": st["malformed"],
            "d1_final_undenied": d1[-1]["ok"] if d1 else None,
            "d2_denials": sum(1 for n in g["notes"] if n["kind"] == "d2_deny"),
            "d5_unresolvable": sum(1 for n in g["notes"] if n["kind"] == "d5_unres"),
            # session-scoped, carried on the FIRST row only so a sum over rows is the truth
            "undated_opportunities": undated if not rows else 0,
            "counts": {k: [n, d] for k, n, d in dims},
        }
        for k, n, d in dims:
            row[k] = ("%d/%d" % (n, d)) if d else "-"
        rows.append(row)
    return rows


# ---------------------------------------------------------------- discovery / driving
def discover(path):
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        raise InputError("path does not exist: %s" % path)
    if os.path.isfile(path):
        if not path.endswith(".jsonl"):
            raise InputError("not a .jsonl transcript: %s" % path)
        return [path]
    if not os.path.isdir(path):
        raise InputError("neither a file nor a directory: %s" % path)
    found = sorted(os.path.join(path, f) for f in os.listdir(path) if f.endswith(".jsonl"))
    if not found:
        raise InputError("no *.jsonl transcripts under: %s" % path)
    return found


def run(paths, since=None, split=None):
    rows, skipped, failed = [], [], []
    for p in paths:
        try:
            got = score_session(p, split)
        except InputError as exc:
            failed.append(str(exc))
            continue
        except Exception as exc:                     # fail-soft: one bad file never stops a sweep
            failed.append("%s (%s: %s)" % (p, type(exc).__name__, exc))
            continue
        if got is None:
            skipped.append(p)
            continue
        for row in got:
            if since and row["start_date"] < since:
                continue
            rows.append(row)
    rows.sort(key=lambda r: (r["start_date"], r["session_id"],
                             PHASE_RANK.get(r["phase"], 9)))
    return rows, skipped, failed


# ---------------------------------------------------------------- log (idempotent)
def append_log(rows, log_path):
    """Write/create the TSV trend log: header once, one row per SESSION+PHASE (Z9b: the
    replace key gained phase, so a straddling session keeps both of its rows), re-run
    replaces an existing row instead of duplicating it. Atomic; deterministic order.

    A log written under an OLDER column set cannot be keyed by the new key, so it is set
    aside as <log>.pre-z9b (renamed, never deleted) and the log is written fresh -- the
    non-destructive form of the wholesale regeneration the schema change forces.

    KP2 (2026-08-07): the set-aside name is now COLLISION-SAFE. A second schema change (D6)
    would have os.replace'd onto the FIRST migration's file and destroyed it, which is the
    one thing "renamed, never deleted" promises not to do -- so a taken name falls through
    to .pre-z9b.2, .pre-z9b.3, ... The first migration still lands on the documented name."""
    existing, migrated = {}, None
    header = "\t".join(COLUMNS)
    if os.path.isfile(log_path):
        with open(log_path, "r", errors="replace") as fh:
            lines = fh.read().split("\n")
        first = lines[0] if lines else ""
        if first and first.startswith(COLUMNS[0]) and first != header:
            migrated = log_path + ".pre-z9b"
            n = 1
            while os.path.exists(migrated):
                n += 1
                migrated = "%s.pre-z9b.%d" % (log_path, n)
            os.replace(log_path, migrated)
        else:
            for i, line in enumerate(lines):
                line = line.rstrip("\r")
                if not line or (i == 0 and line.startswith(COLUMNS[0])):
                    continue
                cells = line.split("\t")
                if cells:
                    existing[(cells[0], cells[2] if len(cells) > 2 else "")] = cells
    replaced = 0
    for r in rows:
        key = (r["session_id"], r["phase"])
        if key in existing:
            replaced += 1
        existing[key] = [str(r[c]) for c in COLUMNS]
    ordered = sorted(existing.values(),
                     key=lambda c: ((c[1] if len(c) > 1 else ""), c[0],
                                    PHASE_RANK.get(c[2] if len(c) > 2 else "", 9)))
    d = os.path.dirname(log_path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    tmp = log_path + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(header + "\n")
        for cells in ordered:
            fh.write("\t".join(cells) + "\n")
    os.replace(tmp, log_path)
    return {"written": len(rows), "replaced": replaced, "total_rows": len(ordered),
            "migrated_old_log_to": migrated}


# ---------------------------------------------------------------- rendering
def render_tsv(rows):
    out = ["\t".join(COLUMNS)]
    for r in rows:
        out.append("\t".join(str(r[c]) for c in COLUMNS))
    return "\n".join(out)


def render_table(rows, skipped, failed, split=None):
    out = ["| session | date | phase | lineage | main model | D1 | D2 | D3 | D4 | D5 | D6 | miss | opp |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %d | %d |" % (
            r["session_id"][:8], r["start_date"], r["phase"], r["lineage"], r["main_model"],
            r["D1_plan_routing"], r["D2_launch_brief"], r["D3_certification"],
            r["D4_collect_outcome"], r["D5_brief_persistence"], r["D6_tier_explicitness"],
            r["miss_count"], r["opportunity_count"]))
    out.append("")
    out.extend(render_summary(rows, skipped, failed, split))
    return "\n".join(out)


def tally(rows):
    """(per-dimension {k: [n, d]}, misses, opps) over a row subset."""
    per = {k: [sum(r["counts"][k][0] for r in rows),
               sum(r["counts"][k][1] for r in rows)] for k in DIM_KEYS}
    return per, sum(r["miss_count"] for r in rows), sum(r["opportunity_count"] for r in rows)


def render_summary(rows, skipped, failed, split=None):
    per, misses, opps = tally(rows)
    lin = {}
    for r in rows:
        lin[r["lineage"]] = lin.get(r["lineage"], 0) + 1
    L = ["SUMMARY",
         "  rows: %d over %d sessions  (skipped, no assistant rows: %d; unreadable: %d)"
         % (len(rows), len(set(r["session_id"] for r in rows)), len(skipped), len(failed)),
         "  lineage: %s   (project slug: %s)"
         % ("  ".join("%s=%d" % (k, lin[k]) for k in sorted(lin)) or "-",
            PROJECT_SLUG or "<none: every row reads OTHER>")]
    for k in DIM_KEYS:
        n, d = per[k]
        L.append("  %-22s %s" % (k, ("%d/%d = %.1f%% compliant" % (n, d, 100.0 * n / d))
                                 if d else "- (no opportunities observed)"))
    L.append("  composite: %d misses / %d opportunities%s"
             % (misses, opps, ("  = %.1f%% miss rate" % (100.0 * misses / opps)) if opps else ""))
    L.append("  malformed transcript lines tolerated: %d"
             % sum(r["malformed_lines"] for r in rows))
    und = sum(r.get("undated_opportunities", 0) for r in rows)
    if und:
        L.append("  UNDATED opportunities EXCLUDED from every N (never placed): %d" % und)
    for f in failed[:5]:
        L.append("  UNREADABLE: %s" % f)
    L.append("  NOTE: a cell is n/N over opportunities OBSERVED; '-' means none observed, "
             "which is not compliance.")
    if split is not None:
        L.extend(render_its(rows, split))
    return L


def render_its(rows, split):
    """The interrupted-time-series headline: MAIN lineage only, pre vs post the split."""
    main = [r for r in rows if r["lineage"] == "MAIN"]
    other = len(rows) - len(main)
    L = ["", "ITS HEADLINE  split=%s  MAIN lineage ONLY" % split.isoformat(),
         "  EXCLUDED from this headline: %d non-MAIN rows (ARENA arena-probe projects + "
         "OTHER sub-slugs). They remain in the log." % other,
         "  %-22s %14s %14s" % ("", "PRE", "POST")]
    for k in DIM_KEYS + ["composite"]:
        cells = []
        for ph in ("pre", "post"):
            sub = [r for r in main if r["phase"] == ph]
            per, misses, opps = tally(sub)
            n, d = (opps - misses, opps) if k == "composite" else per[k]
            cells.append("%d/%d %5.1f%%" % (n, d, 100.0 * n / d) if d else "%12s" % "- (N=0)")
        L.append("  %-22s %14s %14s" % (k, cells[0], cells[1]))
    L.append("  cells are COMPLIANT/opportunities; the composite % is 100 - the miss rate.")
    return L


# ---------------------------------------------------------------- cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="adherence_scorecard.py",
        description="Per-session workflow-adherence scorecard for Claude Code transcripts. "
                    "Measures only: exit 0 = scored, 2 = input error.")
    ap.add_argument("path", help="a session .jsonl or a directory of them")
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="machine-readable output")
    fmt.add_argument("--tsv", action="store_true", help="the log's own columns, tab-separated")
    ap.add_argument("--append", nargs="?", const=DEFAULT_LOG, default=None, metavar="LOG",
                    help="append rows to LOG (default %s), idempotent per session" % DEFAULT_LOG)
    ap.add_argument("--since", metavar="YYYY-MM-DD", help="score only sessions starting on/after")
    ap.add_argument("--split", metavar="ISO8601", default=None,
                    help="phase each OPPORTUNITY pre/post this instant "
                         "(e.g. 2026-08-07T07:00:00Z); a straddling session emits two rows")
    ap.add_argument("--project-slug", metavar="TAIL", default=None,
                    help="lineage tail for this project (default: the basename of "
                         "$CLAUDE_PROJECT_DIR or the cwd, non-alphanumerics collapsed to '-'); "
                         "MAIN = a session slug ending in it, ARENA = one carrying "
                         "'<TAIL>-sandbox-'")
    args = ap.parse_args(argv)

    if args.project_slug is not None:
        set_project_slug(args.project_slug)

    if args.since and not re.match(r"^\d{4}-\d{2}-\d{2}$", args.since):
        sys.stderr.write("adherence_scorecard: --since wants YYYY-MM-DD\n")
        return 2
    split = None
    if args.split is not None:
        split = parse_ts(args.split)
        if split is None:
            sys.stderr.write("adherence_scorecard: --split wants an ISO-8601 datetime, "
                             "e.g. 2026-08-07T07:00:00Z (got %r)\n" % args.split)
            return 2
    try:
        paths = discover(args.path)
    except InputError as exc:
        sys.stderr.write("adherence_scorecard: input error: %s\n" % exc)
        return 2

    rows, skipped, failed = run(paths, args.since, split)

    log_info = None
    if args.append is not None:
        try:
            log_info = append_log(rows, args.append)
        except OSError as exc:
            sys.stderr.write("adherence_scorecard: cannot write log %s (%s)\n"
                             % (args.append, exc))
            return 2

    if args.json:
        print(json.dumps({"rows": rows, "skipped": skipped, "failed": failed,
                          "log": log_info,
                          "split": split.isoformat() if split else None},
                         indent=2, sort_keys=True))
    elif args.tsv:
        print(render_tsv(rows))
    else:
        print(render_table(rows, skipped, failed, split))
        if log_info:
            print("  LOG %s: %d rows written (%d replaced), %d rows total"
                  % (args.append, log_info["written"], log_info["replaced"],
                     log_info["total_rows"]))
            if log_info.get("migrated_old_log_to"):
                print("  LOG SCHEMA CHANGED: prior log set aside as %s (not deleted)"
                      % log_info["migrated_old_log_to"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
