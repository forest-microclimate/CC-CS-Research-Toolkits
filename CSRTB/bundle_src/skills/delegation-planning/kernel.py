# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""delegation-planning kernel sidecar -- the routing gates (A2_ROUTING_SCHEMA v1).

Three fail-closed gates over a plan's Delegation & Routing block:
  model_route_gate(route_map, list_models=None)  pre-dispatch  -> [[route_gate ...]]
  plan_lint(routing_block)                       pre-surface   -> [[plan_lint ...]]
  route_receipt_audit(declared, dispatched)      post-wave     -> [[route_audit ...]]

Closes SEED-06 delegation theater -- a declared delegate track the lead self-ran
(FAILURE_CLASS_LOG arc=55710d86 msg=4022: "I declared a delegation track and then
wrote 'main agent does this' inside it") -- and the model bar: claude-opus-5 is
banned at every tier, and the bare alias `opus` resolves to it on CC >= 2.1.219.

PLATFORM NOTE (CC divergence 2026-08-04; the CS bar below is UNCHANGED): Claude
Code now permits claude-opus-5 in ONE constrained shape -- a supervised child
launched via a dedicated project-scoped executor agent under a Planner's active
watch, enforced by an agent-file pin carve plus dispatch-time and completion-time
hooks. Science has no agent-file or hook primitive to carry that contract, so the
ban BANNED_MODEL_IDS/BANNED_MODEL_ALIASES enforce here STANDS until a CS-native
supervision design lands; registered as a capability candidate.

HOST-INDEPENDENT: stdlib only, no host.* at import time; the live-model existence
check is INJECTED (list_models). Library functions RETURN result dicts and never
exit or print; only main() maps a verdict to an exit code (0 PASS / 2 FAIL).
Python 3.9 floor (/usr/bin/python3 3.9.6). Fixtures: fixtures_kernel.py.
"""
import argparse
import json
import re
import sys
from collections import Counter

# ─── TIER TABLE — the single source of model ids (A2 "MODEL TIERS") ──────────
# Ids live HERE only; prose elsewhere names tiers, never ids.
# INVOCATION — [SUPERSEDED 2026-08-04, both halves measured FALSE on Claude Code. The retired
# text is kept greppable, and EVERY line of it carries its own marker, because a grep lands on
# one line and must not read the retired claim as current:]
#   [SUPERSEDED] on Claude CODE, claude-fable-5 is the configured subagent DEFAULT and
#   [SUPERSEDED] is invoked by OMITTING the Task call's model param
#   [SUPERSEDED] naming it explicitly can silently resolve to the BANNED claude-opus-5
# CORRECTED (CC-MEASURED, CS-UNMEASURED — re-measure before relying): on Claude CODE an omitted
# model param requests the MAIN model, and the observed opus-5 arrivals were a SERVING-side
# substitution of fable requests (an open vendor bug), not alias resolution. NEITHER finding
# transfers here: Science delegates through host.delegate(model=...), a DIFFERENT mechanism
# whose resolution and serving behavior have NOT been measured; pass the id below explicitly.
TIER_TABLE = {
    "T1":         {"model": "claude-opus-4-8",  "effort": "max"},
    "T1_hardest": {"model": "claude-fable-5",   "effort": "max"},
    "T2":         {"model": "claude-sonnet-5",  "effort": "high"},
    "T3":         {"model": "claude-sonnet-5",  "effort": "medium"},
    "T4":         {"model": "claude-haiku-4-5", "effort": "low"},
}
TIER_MODEL_CACHE = {}

def tier_model_ids():
    """(ids, ids_lowercased) from the literal TIER_TABLE; lazy + cached so only a
    literal dict sits at module top level (sidecar-gate rule)."""
    if not TIER_MODEL_CACHE:
        ids = frozenset(v["model"] for v in TIER_TABLE.values())
        TIER_MODEL_CACHE["ids"] = ids
        TIER_MODEL_CACHE["lc"] = frozenset(m.lower() for m in ids)
    return TIER_MODEL_CACHE["ids"], TIER_MODEL_CACHE["lc"]

# BANNED (user bar, unrescuable): substring match so versioned/prefixed forms
# ("claude-opus-5[1m]", "us.anthropic.claude-opus-5-v1:0") also fail closed.
BANNED_MODEL_IDS = ("claude-opus-5",)
# Bare alias: whole-value equality only, so prose mentioning "opus" is not a hit.
BANNED_MODEL_ALIASES = ("opus",)

TOPOLOGIES = ("single-thread", "parallel-wave", "sequential-build", "convergence",
              "verify-loop")
EFFORTS = ("max", "high", "medium", "low")
NA = "n/a"

# Required on EVERY track. recon_done is presence-checked here; its NON-emptiness
# on commit-class tracks is L6's job (so the two checks stay non-redundant).
REQUIRED_ALWAYS = ("id", "task", "archetype", "owner", "executor", "topology",
                   "recon_done")
REQUIRED_DELEGATE = ("model_tier", "effort", "detached", "brief_ref", "record_access")

# L3 self-tokens: a delegate:<NAME> naming the lead itself. PLANNER is deliberately
# NOT here -- it is a real roster profile a non-planner may legitimately route to.
SELF_TOKENS = {"main-agent", "mainagent", "main", "self", "myself", "me",
               "lead", "lead-agent", "the-main-agent"}

# L3b: the recorded shape -- a delegate track whose own body says the lead runs it.
SELF_RUN_TELL_PATTERNS = (
    r"main[\s_-]*agent\s+(?:does|do|runs?|will|executes?|handles?|writes?|authors?)",
    r"(?:executed|run|written|authored|handled|done)\s+by\s+(?:the\s+)?main[\s_-]*agent",
    r"\bself[\s_-]?run\b",
    r"\bexecution\s*:\s*main[\s_-]*agent\b",
    r"\b(?:i(?:'ll)?|lead|planner)\s+(?:will\s+)?(?:do|run|write|author|handle|execut\w*)\s+(?:this|it)\b",
)
# Fields L3b reads -- the track's own descriptive body, not its executor tag.
SELF_RUN_SCAN_FIELDS = ("owner", "task", "tradeoff", "brief_ref")

MUTATION_PATTERN = (
    r"\b(writ\w*|edit\w*|overwrit\w*|delet\w*|remov\w*|rm|mv|patch\w*|appl(?:y|ies)|"
    r"install\w*|refactor\w*|commit\w*|push\w*|migrat\w*|renam\w*|publish\w*|creat\w*|"
    r"generat\w*|scrub\w*|stamp\w*|cop(?:y|ies)|move\w*|sync\w*|updat\w*|replac\w*|"
    r"append\w*|prun\w*|purg\w*|reset|rebuild\w*|regenerat\w*)\b")

ROUTING_FENCE_PATTERN = r"```+\s*routing\s*\r?\n(.*?)```+"

DP_RE_CACHE = {}

def dp_re(key):
    """Lazy-compile a module regex literal by key. Only string literals live at module
    top level (sidecar-gate rule); compiled on first use, cached module-level."""
    import re as re_
    if not DP_RE_CACHE:
        DP_RE_CACHE["self_run_tells"] = tuple(re_.compile(p, re_.I) for p in SELF_RUN_TELL_PATTERNS)
        DP_RE_CACHE["mutation"] = re_.compile(MUTATION_PATTERN, re_.I)
        DP_RE_CACHE["routing_fence"] = re_.compile(ROUTING_FENCE_PATTERN, re_.S | re_.I)
    return DP_RE_CACHE[key]


# ─── helpers ─────────────────────────────────────────────────────────────────
def norm_(value):
    """Collapse whitespace; None -> ''."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def norm_name_(value):
    """Profile-name normalization for matching: case/space/underscore-insensitive."""
    return re.sub(r"[\s_]+", "-", str(value or "").strip().lower())


def blank_(value):
    """True for None or a whitespace-only string. False/0 are NOT blank."""
    return value is None or (isinstance(value, str) and not value.strip())


def walk_strings_(obj, path=""):
    """Yield (dotted_path, string_value) for every string anywhere in obj."""
    if isinstance(obj, dict):
        for k in obj:
            sub = "%s.%s" % (path, k) if path else str(k)
            for row in walk_strings_(obj[k], sub):
                yield row
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            for row in walk_strings_(v, "%s[%d]" % (path, i)):
                yield row
    elif isinstance(obj, str):
        yield (path or "<root>", obj)


def marker_(gate, verdict, **counts):
    """Render the machine-detectable tell. Key order is fixed per gate by caller."""
    parts = ["%s=%s" % (k, counts[k]) for k in counts]
    parts.append("verdict=%s" % verdict)
    return "[[%s %s]]" % (gate, " ".join(parts))


# ─── tier resolution ─────────────────────────────────────────────────────────
def resolve_tier(tier):
    """Tier key -> model id. FAILS CLOSED (ValueError) on an unknown tier: an
    unrecognized tier must never silently degrade to a default model."""
    key = norm_(tier)
    if key not in TIER_TABLE:
        raise ValueError("unknown tier %r -- valid tiers: %s"
                         % (tier, ", ".join(sorted(TIER_TABLE))))
    return TIER_TABLE[key]["model"]


def resolve_effort(tier):
    """Tier key -> the tier's effort. Same fail-closed contract as resolve_tier."""
    key = norm_(tier)
    if key not in TIER_TABLE:
        raise ValueError("unknown tier %r -- valid tiers: %s"
                         % (tier, ", ".join(sorted(TIER_TABLE))))
    return TIER_TABLE[key]["effort"]


def is_banned_model(model_id):
    """-> (banned, reason). The user bar; NOT rescuable by list_models.
    Bare alias matches the whole value; claude-opus-5 matches as a substring so
    versioned/prefixed ids fail too. Blank ids are handled by the caller."""
    raw = str(model_id or "").strip()
    low = raw.lower()
    if not low:
        return (False, "")
    if low in BANNED_MODEL_ALIASES:
        return (True, "bare alias %r resolves to claude-opus-5 (banned at every tier)" % raw)
    for bad in BANNED_MODEL_IDS:
        if bad in low:
            return (True, "banned model id %r (%s is barred at every tier)" % (raw, bad))
    return (False, "")


def resolve_live_models_(list_models):
    """Injected live-model source -> (set_of_lowercased_ids | None, error_string).
    Accepts a zero-arg callable or any iterable of ids. Never touches host.*."""
    if list_models is None:
        return (None, "")
    try:
        got = list_models() if callable(list_models) else list_models
        ids = set()
        for m in got:
            if isinstance(m, dict):
                m = m.get("id") or m.get("model") or m.get("name")
            if m:
                ids.add(str(m).strip().lower())
        return (ids, "")
    except Exception as exc:                      # fail closed, never crash the gate
        return (None, "%s: %s" % (type(exc).__name__, exc))


# ─── GATE 1 — model_route_gate (pre-dispatch) ────────────────────────────────
def model_route_gate(route_map, list_models=None):
    """Fail-closed check of an intended {child_name: model_id} map.

    FAIL on: a barred id (claude-opus-5 in any form, bare `opus`), a blank/missing
    id, or an id absent from TIER_TABLE unless the INJECTED list_models confirms it.
    Returns {gate, verdict PASS|FAIL, n, failures, notes, checked, marker}.
    n=0 (empty map) returns PASS but is flagged vacuous -- the marker's n makes an
    empty route map visible rather than laundering as a green.
    """
    failures = []
    notes = []
    checked = {}
    if route_map is None:
        route_map = {}
    if not isinstance(route_map, dict):
        try:
            route_map = dict(route_map)
        except Exception as exc:
            failures.append({"child": None, "model": None, "check": "input",
                             "detail": "route_map is not a {child: model_id} mapping "
                                       "(%s: %s)" % (type(exc).__name__, exc)})
            return {"gate": "model_route_gate", "verdict": "FAIL", "n": 0,
                    "failures": failures, "notes": notes, "checked": checked,
                    "vacuous": False,
                    "marker": marker_("route_gate", "FAIL", n=0)}

    live, live_err = resolve_live_models_(list_models)
    if live_err:
        notes.append("injected list_models errored (%s) -- off-table ids cannot be "
                     "confirmed and fail closed" % live_err)

    for child in sorted(route_map, key=lambda c: str(c)):
        raw = route_map[child]
        mid = str(raw).strip() if raw is not None else ""
        checked[str(child)] = mid
        if not mid:
            failures.append({"child": str(child), "model": mid, "check": "missing",
                             "detail": "no model id declared for this child"})
            continue
        banned, why = is_banned_model(mid)
        if banned:
            failures.append({"child": str(child), "model": mid, "check": "banned",
                             "detail": why})
            continue
        if mid.lower() in tier_model_ids()[1]:
            continue
        if live is None:
            failures.append({"child": str(child), "model": mid, "check": "off-table",
                             "detail": "id not in TIER_TABLE (%s) and no usable "
                                       "list_models was injected to confirm it"
                                       % ", ".join(sorted(tier_model_ids()[0]))})
        elif mid.lower() in live:
            notes.append("%s: off-table id %r confirmed by injected list_models"
                         % (child, mid))
        else:
            failures.append({"child": str(child), "model": mid, "check": "off-table",
                             "detail": "id not in TIER_TABLE and not present in the "
                                       "injected list_models"})

    verdict = "FAIL" if failures else "PASS"
    return {"gate": "model_route_gate", "verdict": verdict, "n": len(route_map),
            "failures": failures, "notes": notes, "checked": checked,
            "vacuous": (len(route_map) == 0),
            "marker": marker_("route_gate", verdict, n=len(route_map))}


# ─── routing-block parsing ───────────────────────────────────────────────────
def classify_executor(executor):
    """-> (kind, name); kind in {MAIN-AGENT, CODE, delegate, invalid}."""
    s = norm_(executor)
    if not s:
        return ("invalid", "")
    up = s.upper()
    if up in ("MAIN-AGENT", "MAIN AGENT", "MAINAGENT"):
        return ("MAIN-AGENT", "")
    if up.startswith("CODE:"):
        return ("CODE", s[5:].strip())
    if s.lower().startswith("delegate:"):
        return ("delegate", s.split(":", 1)[1].strip())
    return ("invalid", s)


def is_self_delegate(name):
    """L3: True when delegate:<NAME> names the lead itself (or names nobody)."""
    n = norm_name_(name)
    return (not n) or (n in SELF_TOKENS)


def extract_routing_tracks(routing_block):
    """-> (tracks, errors). Accepts a parsed dict {"tracks":[...]}, a single track
    dict, a list of tracks, a raw string carrying one or more ```routing fenced
    JSON blocks, or a bare JSON string. Fail-closed: an unparseable or absent block
    yields an L1 error, never a silent empty pass."""
    errors = []
    if routing_block is None:
        return ([], [{"track": None, "check": "L1", "field": None,
                      "detail": "no routing block supplied"}])
    if isinstance(routing_block, str):
        fences = dp_re("routing_fence").findall(routing_block)
        if fences:
            tracks = []
            for i, body in enumerate(fences):
                try:
                    obj = json.loads(body)
                except Exception as exc:
                    errors.append({"track": None, "check": "L1", "field": None,
                                   "detail": "```routing block #%d is not parseable "
                                             "JSON (%s: %s)" % (i + 1, type(exc).__name__, exc)})
                    continue
                sub, sub_err = extract_routing_tracks(obj)
                tracks.extend(sub)
                errors.extend(sub_err)
            return (tracks, errors)
        try:
            obj = json.loads(routing_block)
        except Exception:
            return ([], [{"track": None, "check": "L1", "field": None,
                          "detail": "no ```routing fenced block found and the text is "
                                    "not bare JSON"}])
        return extract_routing_tracks(obj)
    if isinstance(routing_block, dict):
        if "tracks" in routing_block:
            tracks = routing_block.get("tracks")
            if not isinstance(tracks, list):
                return ([], [{"track": None, "check": "L1", "field": "tracks",
                              "detail": "`tracks` is %s, expected a list"
                                        % type(tracks).__name__}])
            return (list(tracks), errors)
        if "executor" in routing_block or "id" in routing_block:
            return ([routing_block], errors)
        return ([], [{"track": None, "check": "L1", "field": None,
                      "detail": "routing object carries no `tracks` key"}])
    if isinstance(routing_block, (list, tuple)):
        return (list(routing_block), errors)
    return ([], [{"track": None, "check": "L1", "field": None,
                  "detail": "unsupported routing block type %s"
                            % type(routing_block).__name__}])


def is_commit_class_(kind, topology, task_text):
    """L6 scope: delegate:* | parallel-wave | CODE:<cmd> whose task mutates."""
    if kind == "delegate":
        return True
    if topology == "parallel-wave":
        return True
    if kind == "CODE" and dp_re("mutation").search(task_text or ""):
        return True
    return False


# ─── GATE 2 — plan_lint (pre-surface, L1..L6) ────────────────────────────────
def plan_lint(routing_block, solo=None):
    """Lint the A2 routing block: L1 block-present, L2 fields-per-executor-class,
    L3 anti-theater, L4 tier-ban, L5 reserved-step, L6 recon-stated.

    routing_block: parsed dict / track list / raw ```routing fenced string.
    solo: execution mode for L5; None is treated as SOLO (fail closed) -- pass
          solo=False when the user is in the loop (collab/plan mode).
    Returns {gate, verdict PASS|FAIL, tracks, failures[{track,check,field,detail}],
             by_track, tracks_failed, marker}.
    """
    if solo is None:
        solo = True
    tracks, failures = extract_routing_tracks(routing_block)
    failures = list(failures)

    # L1 -- a plan carries >= 1 routing block with >= 1 track.
    if not tracks and not failures:
        failures.append({"track": None, "check": "L1", "field": None,
                         "detail": "routing block present but carries zero tracks"})

    for idx, track in enumerate(tracks):
        tid = None
        if isinstance(track, dict):
            tid = track.get("id")
        tid = str(tid) if tid not in (None, "") else "#%d" % (idx + 1)
        if not isinstance(track, dict):
            failures.append({"track": tid, "check": "L2", "field": None,
                             "detail": "track is %s, expected an object"
                                       % type(track).__name__})
            continue

        # --- L2 always-required fields -------------------------------------
        for field in REQUIRED_ALWAYS:
            if field not in track:
                failures.append({"track": tid, "check": "L2", "field": field,
                                 "detail": "required field missing"})
            elif field != "recon_done" and blank_(track.get(field)):
                failures.append({"track": tid, "check": "L2", "field": field,
                                 "detail": "required field is empty"})
        if "reserved_for_user" not in track:
            failures.append({"track": tid, "check": "L2", "field": "reserved_for_user",
                             "detail": "required field missing"})
        elif not isinstance(track.get("reserved_for_user"), bool):
            failures.append({"track": tid, "check": "L2", "field": "reserved_for_user",
                             "detail": "must be a JSON boolean, got %r"
                                       % (track.get("reserved_for_user"),)})

        kind, name = classify_executor(track.get("executor"))
        if kind == "invalid":
            failures.append({"track": tid, "check": "L2", "field": "executor",
                             "detail": "executor %r is not MAIN-AGENT | CODE:<cmd> | "
                                       "delegate:<NAME>" % (track.get("executor"),)})
        topology = norm_(track.get("topology"))
        if topology and topology not in TOPOLOGIES:
            failures.append({"track": tid, "check": "L2", "field": "topology",
                             "detail": "topology %r not in %s"
                                       % (topology, list(TOPOLOGIES))})

        task_text = norm_(track.get("task"))

        # --- L2 executor-class fields ---------------------------------------
        if kind == "delegate":
            for field in REQUIRED_DELEGATE:
                if field == "model_tier":
                    continue                      # owned by L4 below
                if field not in track:
                    failures.append({"track": tid, "check": "L2", "field": field,
                                     "detail": "required on a delegate:* track"})
                elif field == "detached":
                    if not isinstance(track.get("detached"), bool):
                        failures.append({"track": tid, "check": "L2", "field": "detached",
                                         "detail": "must be a JSON boolean, got %r"
                                                   % (track.get("detached"),)})
                elif blank_(track.get(field)):
                    failures.append({"track": tid, "check": "L2", "field": field,
                                     "detail": "required on a delegate:* track, is empty"})
            effort = norm_(track.get("effort"))
            if effort and effort not in EFFORTS:
                failures.append({"track": tid, "check": "L2", "field": "effort",
                                 "detail": "effort %r not in %s" % (effort, list(EFFORTS))})
            access = norm_(track.get("record_access"))
            if access and access != "self-service" and not access.startswith("precis-only:"):
                failures.append({"track": tid, "check": "L2", "field": "record_access",
                                 "detail": "must be 'self-service' or 'precis-only:<why>', "
                                           "got %r" % access})
            brief = norm_(track.get("brief_ref"))
            if brief.lower() == "inline" and track.get("detached") is True:
                failures.append({"track": tid, "check": "L2", "field": "brief_ref",
                                 "detail": "brief_ref 'inline' is allowed only with "
                                           "detached=false (a detached launch needs the "
                                           "brief persisted BEFORE dispatch)"})
        else:
            for field in ("model_tier", "effort"):
                val = norm_(track.get(field))
                if val and val.lower() != NA:
                    failures.append({"track": tid, "check": "L2", "field": field,
                                     "detail": "%r declared on a %s track -- must be "
                                               "'n/a' when nothing is delegated"
                                               % (val, kind)})

        # --- L2 topology-conditioned fields ---------------------------------
        if topology and topology != "single-thread" and blank_(track.get("tradeoff")):
            failures.append({"track": tid, "check": "L2", "field": "tradeoff",
                             "detail": "required where topology != single-thread "
                                       "(name the benefit that beats delegation cost)"})
        if topology == "parallel-wave":
            conc = norm_(track.get("concurrency"))
            if not conc or conc.lower() == NA:
                failures.append({"track": tid, "check": "L2", "field": "concurrency",
                                 "detail": "required on a parallel-wave track "
                                           "('<N> units, sized via preflight-parallel')"})

        # --- L3 anti-theater (SEED-06) --------------------------------------
        if kind == "delegate":
            if is_self_delegate(name):
                failures.append({"track": tid, "check": "L3", "field": "executor",
                                 "detail": "delegate:%s names the lead itself -- a "
                                           "delegate:<NAME> must name a real, NON-SELF "
                                           "profile" % (name or "<empty>")})
            else:
                for field in SELF_RUN_SCAN_FIELDS:
                    text = norm_(track.get(field))
                    if not text:
                        continue
                    hit = next((r for r in dp_re("self_run_tells") if r.search(text)), None)
                    if hit is not None:
                        failures.append({"track": tid, "check": "L3", "field": field,
                                         "detail": "declared delegate:%s but %s says the "
                                                   "lead runs it (%r) -- declared "
                                                   "delegation, self-run"
                                                   % (name, field, text[:120])})
                        break

        # --- L4 tier ban -----------------------------------------------------
        if kind == "delegate":
            tier = norm_(track.get("model_tier"))
            if "model_tier" not in track or not tier:
                failures.append({"track": tid, "check": "L4", "field": "model_tier",
                                 "detail": "required on a delegate:* track"})
            elif tier not in TIER_TABLE:
                failures.append({"track": tid, "check": "L4", "field": "model_tier",
                                 "detail": "tier %r not in TIER_TABLE (%s)"
                                           % (tier, ", ".join(sorted(TIER_TABLE)))})
        for path, value in walk_strings_(track):
            banned, why = is_banned_model(value)
            if banned:
                failures.append({"track": tid, "check": "L4", "field": path,
                                 "detail": why})

        # --- L5 reserved step -------------------------------------------------
        if track.get("reserved_for_user") is True and solo and dp_re("mutation").search(task_text):
            failures.append({"track": tid, "check": "L5", "field": "reserved_for_user",
                             "detail": "reserved-for-user track carries a mutating task "
                                       "(%r) scheduled for autonomous execution under "
                                       "solo -- read-only until the user weighs in"
                                       % task_text[:120]})

        # --- L6 recon stated (value not adjudicated) --------------------------
        if is_commit_class_(kind, topology, task_text) and blank_(track.get("recon_done")):
            failures.append({"track": tid, "check": "L6", "field": "recon_done",
                             "detail": "commit-class track must STATE its recon evidence "
                                       "or 'stated-none:<why>' (value not adjudicated)"})

    by_track = {}
    for f in failures:
        by_track.setdefault(str(f.get("track")), []).append(f.get("check"))
    tracks_failed = sorted(k for k in by_track if k != "None")
    verdict = "FAIL" if failures else "PASS"
    return {"gate": "plan_lint", "verdict": verdict, "tracks": len(tracks),
            "failures": failures, "by_track": by_track, "tracks_failed": tracks_failed,
            "marker": marker_("plan_lint", verdict, tracks=len(tracks))}


# ─── GATE 3 — route_receipt_audit (post-wave) ────────────────────────────────
def dispatched_name_(row):
    """Record row -> profile name. Accepts a bare string or a delegate row dict."""
    if isinstance(row, dict):
        for key in ("agent_name", "profile", "specialist", "child", "name", "agent"):
            if row.get(key):
                row = row[key]
                break
        else:
            return ""
    s = norm_(row)
    if s.lower().startswith("delegate:"):
        s = s.split(":", 1)[1].strip()
    return s


def route_receipt_audit(declared, dispatched):
    """Post-wave: declared delegate:* tracks vs the children ACTUALLY dispatched.

    declared:   the routing block, its track list, or a list of profile names.
    dispatched: the RECORD's delegate rows (strings or dicts with agent_name /
                profile / name) -- read from the record, never from memory.
    FAIL lists unhonored declarations (delegation theater) and undeclared
    dispatches. Matching is multiset + case/underscore-insensitive.
    Returns {gate, verdict, declared, dispatched, failures, matched, marker}.
    """
    tracks, parse_errors = extract_routing_tracks(declared)
    failures = [dict(e, check="L1") for e in parse_errors] if parse_errors else []

    declared_names = []           # normalized
    declared_display = {}
    declared_tracks = {}
    for idx, track in enumerate(tracks):
        if isinstance(track, str):
            kind, name = classify_executor(track)
            if kind != "delegate":
                name = track
                kind = "delegate"
            tid = "#%d" % (idx + 1)
        elif isinstance(track, dict):
            kind, name = classify_executor(track.get("executor"))
            tid = str(track.get("id") or "#%d" % (idx + 1))
        else:
            continue
        if kind != "delegate" or not name:
            continue
        key = norm_name_(name)
        declared_names.append(key)
        declared_display.setdefault(key, norm_(name))
        declared_tracks.setdefault(key, []).append(tid)

    dispatched_names = []
    dispatched_display = {}
    for row in (dispatched or []):
        name = dispatched_name_(row)
        if not name:
            failures.append({"check": "undeclared", "profile": None, "count": 1,
                             "tracks": [], "detail": "dispatch row carries no resolvable "
                                                     "child name: %r" % (row,)})
            continue
        key = norm_name_(name)
        dispatched_names.append(key)
        dispatched_display.setdefault(key, name)

    dec_c = Counter(declared_names)
    dis_c = Counter(dispatched_names)
    matched = {}
    for key in sorted(set(dec_c) | set(dis_c)):
        n_dec, n_dis = dec_c.get(key, 0), dis_c.get(key, 0)
        matched[declared_display.get(key) or dispatched_display.get(key)] = {
            "declared": n_dec, "dispatched": n_dis}
        if n_dec > n_dis:
            failures.append({
                "check": "unhonored", "profile": declared_display.get(key, key),
                "count": n_dec - n_dis, "tracks": declared_tracks.get(key, []),
                "detail": "declared delegate:%s on track(s) %s but %d of %d dispatch(es) "
                          "never happened -- delegation theater"
                          % (declared_display.get(key, key),
                             ", ".join(declared_tracks.get(key, [])), n_dec - n_dis, n_dec)})
        elif n_dis > n_dec:
            failures.append({
                "check": "undeclared", "profile": dispatched_display.get(key, key),
                "count": n_dis - n_dec, "tracks": [],
                "detail": "%d dispatch(es) of %s appear in the record with no matching "
                          "delegate: declaration in the plan"
                          % (n_dis - n_dec, dispatched_display.get(key, key))})

    verdict = "FAIL" if failures else "PASS"
    return {"gate": "route_receipt_audit", "verdict": verdict,
            "declared": len(declared_names), "dispatched": len(dispatched_names),
            "failures": failures, "matched": matched,
            "marker": marker_("route_audit", verdict, declared=len(declared_names),
                              dispatched=len(dispatched_names))}


# ─── CLI (the ONLY place that prints or exits) ───────────────────────────────
def load_json_(path):
    text = sys.stdin.read() if path in (None, "-", "") else open(path, encoding="utf-8").read()
    return text


def main(argv=None):
    """argparse CLI: one subcommand per gate, JSON in / JSON out, exit 0 PASS / 2 FAIL."""
    ap = argparse.ArgumentParser(
        prog="kernel.py",
        description="delegation-planning routing gates (A2_ROUTING_SCHEMA v1)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("route-gate", help='model_route_gate over {"child": "model_id"}')
    p.add_argument("-i", "--input", default="-", help="JSON file, or - for stdin")
    p.add_argument("--live-models", default=None,
                   help="comma-separated live model ids (injects list_models)")

    p = sub.add_parser("plan-lint", help="plan_lint over a routing block (JSON or fenced text)")
    p.add_argument("-i", "--input", default="-", help="file, or - for stdin")
    p.add_argument("--collab", action="store_true",
                   help="user is in the loop (solo=False) -- relaxes L5")

    p = sub.add_parser("route-audit",
                       help='route_receipt_audit over {"declared": …, "dispatched": [...]}')
    p.add_argument("-i", "--input", default="-", help="JSON file, or - for stdin")

    args = ap.parse_args(argv)
    try:
        raw = load_json_(args.input)
    except Exception as exc:
        print(json.dumps({"verdict": "FAIL", "failures": [
            {"check": "input", "detail": "%s: %s" % (type(exc).__name__, exc)}]}))
        return 2

    try:
        if args.cmd == "route-gate":
            live = None
            if args.live_models:
                live = [m.strip() for m in args.live_models.split(",") if m.strip()]
            result = model_route_gate(json.loads(raw), list_models=live)
        elif args.cmd == "plan-lint":
            try:
                block = json.loads(raw)
            except ValueError:
                block = raw                        # raw fenced text is a valid input
            result = plan_lint(block, solo=(not args.collab))
        else:
            payload = json.loads(raw)
            result = route_receipt_audit(payload.get("declared"),
                                         payload.get("dispatched") or [])
    except Exception as exc:
        print(json.dumps({"verdict": "FAIL", "failures": [
            {"check": "input", "detail": "%s: %s" % (type(exc).__name__, exc)}]}))
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    print(result["marker"])
    return 0 if result["verdict"] == "PASS" else 2
