#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""model_run_audit.py -- per-run INTENT-vs-SERVED model audit for Claude Code transcripts.

WHAT: point it at a project dir, a session JSONL, or a session dir; it catalogs every
run (the main loop + every subagent) and reports, per run, what model was REQUESTED,
what the harness RESOLVED, and what the API actually SERVED -- with a MATCH / MISMATCH /
UNKNOWN verdict and a gate-able exit code.

WHY: only one of those layers is downstream of what actually ran. The four harness
record layers per child run are:
  (1) subagents/agent-<id>.meta.json  .model        = the RAW LAUNCH ARG (absent if omitted)
  (2) <any>.jsonl  .toolUseResult.resolvedModel     = the harness's launch-time RESOLUTION
                                                      (the only field carrying a `[1m]`
                                                      display suffix; the UI header's source)
                                                      -> INTENT, not serving
  (3) child jsonl  .message.model (assistant rows)  = the API RESPONSE's own model field,
                                                      written per call by the serving side
                                                      -> the SERVING STAMP: the one
                                                         authoritative layer
  (4) the model's own self-report                   -> DISQUALIFIED (measured wrong 3 of 5)
A model claim is verified by layer (3) or it is not verified. See
dev/reports/METHODS_model_verification.md for the full method and the measured failure
modes of each apparent layer.

INPUT (one positional path, auto-discovered):
  project dir   ~/.claude/projects/<slug>/        -> mains = <slug>/*.jsonl
                                                     children = <slug>/*/subagents/agent-*.jsonl
  session JSONL <slug>/<sessionId>.jsonl          -> that main + its sibling
                                                     <sessionId>/subagents/agent-*.jsonl
  session dir   <slug>/<sessionId>/               -> its subagents + the sibling main JSONL

INTENT INDEX: resolvedModel rows are harvested from EVERY discovered transcript, not just
the main one -- a depth-2 launch (a sub-planner child launching its own child) records its
async_launched row in the SUB-PLANNER's JSONL, so a main-only scan silently loses it
(measured: 4 of 137 runs in the origin session).

OUTPUT: md table + a SUMMARY block on stdout (default), --json, or --tsv.
EXIT: 0 = no MISMATCH | 1 = at least one MISMATCH | 2 = input/parse error.
  UNKNOWN does NOT gate: a main-loop run has no intent layer by construction, so every
  main row is UNKNOWN and a project-dir audit would otherwise never exit 0.

ENGINEERING: stdlib only; every transcript is STREAM-parsed line by line (they reach
25 MB); malformed lines are counted and reported, never fatal; output ordering is
deterministic (sorted by session, then main-before-children, then run id).

USAGE:
  python3 dev/tools/model_run_audit.py "$HOME/.claude/projects/<slug>/"
  python3 dev/tools/model_run_audit.py "$HOME/.claude/projects/<slug>/<sessionId>.jsonl"
  python3 dev/tools/model_run_audit.py <path> --json > audit.json
  python3 dev/tools/model_run_audit.py <path> --tsv
Self-test: python3 dev/tools/test_model_run_audit.py
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys

SYNTHETIC = "<synthetic>"
# Display suffixes the harness appends to a resolved id, e.g. claude-opus-5[1m].
_SUFFIX_RE = re.compile(r"\[[^\]]*\]\s*$")

MATCH, MISMATCH, UNKNOWN = "MATCH", "MISMATCH", "UNKNOWN"


class InputError(Exception):
    """Raised for an unusable input path -> exit 2."""


# ---------------------------------------------------------------- normalization
def normalize_model(name):
    """Strip display suffixes so an intent id compares to a served id.

    'claude-opus-5[1m]' -> 'claude-opus-5'.  Never collapses distinct model ids.
    """
    if name is None:
        return None
    return _SUFFIX_RE.sub("", str(name).strip()).strip()


# ---------------------------------------------------------------- discovery
def discover(path):
    """Return (mains, children, scope_label). Raises InputError on an unusable path."""
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        raise InputError("path does not exist: %s" % path)

    if os.path.isfile(path):
        if not path.endswith(".jsonl"):
            raise InputError("not a .jsonl transcript: %s" % path)
        mains = [path]
        stem = path[: -len(".jsonl")]
        children = _subagent_files(stem)
        return mains, children, "session-jsonl"

    if not os.path.isdir(path):
        raise InputError("neither a file nor a directory: %s" % path)

    # session dir: holds subagents/
    if os.path.isdir(os.path.join(path, "subagents")):
        children = _subagent_files(path)
        sibling = path.rstrip(os.sep) + ".jsonl"
        mains = [sibling] if os.path.isfile(sibling) else []
        return mains, children, "session-dir"

    # project dir: *.jsonl at the top level and/or */subagents/
    mains = sorted(
        os.path.join(path, f) for f in os.listdir(path) if f.endswith(".jsonl")
    )
    children = []
    for entry in sorted(os.listdir(path)):
        sub = os.path.join(path, entry)
        if os.path.isdir(sub):
            children.extend(_subagent_files(sub))
    if not mains and not children:
        raise InputError("no transcripts found under: %s" % path)
    return mains, sorted(children), "project-dir"


def _subagent_files(session_dir):
    d = os.path.join(session_dir, "subagents")
    if not os.path.isdir(d):
        return []
    return sorted(
        os.path.join(d, f)
        for f in os.listdir(d)
        if f.startswith("agent-") and f.endswith(".jsonl")
    )


# ---------------------------------------------------------------- parsing
def scan_transcript(path, intent_index, counters):
    """Stream one transcript. Returns the served-model Counter for that file.

    Also harvests any toolUseResult.resolvedModel rows into intent_index (a launch row
    can live in ANY transcript, including a sub-planner child's).
    """
    served = collections.Counter()
    try:
        fh = open(path, "r", errors="replace")
    except OSError as exc:
        counters["unreadable"].append("%s (%s)" % (path, exc))
        return served
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            # cheap pre-filter: only these two keys can carry what we need
            has_model = '"model"' in line
            has_resolved = '"resolvedModel"' in line
            if not (has_model or has_resolved):
                continue
            try:
                row = json.loads(line)
            except ValueError:
                counters["malformed"] += 1
                continue
            if not isinstance(row, dict):
                counters["malformed"] += 1
                continue

            if has_resolved:
                tur = row.get("toolUseResult")
                if isinstance(tur, dict):
                    agent_id = tur.get("agentId")
                    resolved = tur.get("resolvedModel")
                    if agent_id and resolved and agent_id not in intent_index:
                        intent_index[agent_id] = resolved

            if has_model and row.get("type") == "assistant":
                msg = row.get("message")
                if isinstance(msg, dict):
                    model = msg.get("model")
                    if isinstance(model, str) and model:
                        if model == SYNTHETIC:
                            counters["synthetic"] += 1
                        else:
                            served[model] += 1
    return served


def read_meta(jsonl_path, counters):
    """Return (agentType, raw_arg) for a child transcript.

    raw_arg is the literal launch arg, 'omitted' when the meta exists without one, and
    '(no meta)' when the sidecar itself is missing -- three distinct facts, kept distinct.
    """
    meta_path = jsonl_path[: -len(".jsonl")] + ".meta.json"
    if not os.path.isfile(meta_path):
        return "(unknown)", "(no meta)"
    try:
        with open(meta_path, "r", errors="replace") as fh:
            meta = json.load(fh)
    except (ValueError, OSError):
        counters["bad_meta"] += 1
        return "(unreadable)", "(no meta)"
    if not isinstance(meta, dict):
        counters["bad_meta"] += 1
        return "(unreadable)", "(no meta)"
    agent_type = meta.get("agentType") or "(unknown)"
    arg = meta.get("model")
    return agent_type, (arg if arg else "omitted")


# ---------------------------------------------------------------- verdict
def decide(intent, served):
    """MATCH iff every served call carries the (normalized) resolved id."""
    if not served:
        return UNKNOWN
    if not intent:
        return UNKNOWN
    want = normalize_model(intent)
    got = {normalize_model(m) for m in served}
    return MATCH if got == {want} else MISMATCH


def served_str(served):
    if not served:
        return "(no API calls)"
    parts = sorted(served.items(), key=lambda kv: (-kv[1], kv[0]))
    return ", ".join("%s x%d" % (m, n) for m, n in parts)


# ---------------------------------------------------------------- audit
def audit(path):
    mains, children, scope = discover(path)
    counters = {"malformed": 0, "synthetic": 0, "bad_meta": 0, "unreadable": []}
    intent_index = {}
    runs = []

    # Pass 1 harvests intent from EVERY transcript while tallying served models, so a
    # depth-2 launch row (recorded in a sub-planner child's file) is not lost.
    scanned = []
    for p in mains:
        scanned.append(("main", p, scan_transcript(p, intent_index, counters)))
    for p in children:
        scanned.append(("child", p, scan_transcript(p, intent_index, counters)))

    for kind, p, served in scanned:
        base = os.path.basename(p)[: -len(".jsonl")]
        if kind == "main":
            session = base
            run_id = base
            agent_type, arg, intent = "(main loop)", None, None
        else:
            session = os.path.basename(os.path.dirname(os.path.dirname(p)))
            run_id = base[len("agent-"):] if base.startswith("agent-") else base
            agent_type, arg = read_meta(p, counters)
            intent = intent_index.get(run_id)
        runs.append(
            {
                "kind": kind,
                "session": session,
                "run_id": run_id,
                "path": p,
                "agentType": agent_type,
                "arg": arg,
                "resolved": intent,
                "served": dict(served),
                "calls": sum(served.values()),
                "verdict": decide(intent, served),
            }
        )

    runs.sort(key=lambda r: (r["session"], 0 if r["kind"] == "main" else 1, r["run_id"]))
    return {"scope": scope, "root": os.path.abspath(os.path.expanduser(path)),
            "runs": runs, "counters": counters}


def summarize(result):
    runs = result["runs"]
    totals = collections.Counter()
    by_kind = {"main": collections.Counter(), "child": collections.Counter()}
    verdicts = collections.Counter()
    signature = collections.Counter()
    sig_calls = collections.Counter()
    for r in runs:
        verdicts[r["verdict"]] += 1
        for m, n in r["served"].items():
            totals[m] += n
            by_kind[r["kind"]][m] += n
        if r["verdict"] == MISMATCH:
            for m, n in r["served"].items():
                if normalize_model(m) != normalize_model(r["resolved"]):
                    signature[(r["resolved"], m)] += 1
                    sig_calls[(r["resolved"], m)] += n
    comparable = verdicts[MATCH] + verdicts[MISMATCH]
    return {
        "runs_total": len(runs),
        "runs_main": sum(1 for r in runs if r["kind"] == "main"),
        "runs_child": sum(1 for r in runs if r["kind"] == "child"),
        "served_totals": dict(totals),
        "served_main": dict(by_kind["main"]),
        "served_child": dict(by_kind["child"]),
        "verdicts": dict(verdicts),
        "unknown_main": sum(1 for r in runs if r["verdict"] == UNKNOWN and r["kind"] == "main"),
        "comparable": comparable,
        "mismatch": verdicts[MISMATCH],
        "mismatch_rate": (verdicts[MISMATCH] / comparable) if comparable else None,
        "signature": {"%s -> %s" % k: {"runs": v, "calls": sig_calls[k]}
                      for k, v in sorted(signature.items())},
        "synthetic_excluded": result["counters"]["synthetic"],
        "malformed_lines": result["counters"]["malformed"],
        "bad_meta": result["counters"]["bad_meta"],
        "unreadable": result["counters"]["unreadable"],
    }


# ---------------------------------------------------------------- rendering
def _short(run_id):
    return run_id[:8]


def render_md(result, summ):
    out = []
    out.append("| run | agentType | arg | resolved (intent) | served x calls | verdict |")
    out.append("|---|---|---|---|---|---|")
    for r in result["runs"]:
        out.append(
            "| %s | %s | %s | %s | %s | %s |"
            % (_short(r["run_id"]), r["agentType"], r["arg"] or "-",
               r["resolved"] or "-", served_str(r["served"]), r["verdict"])
        )
    out.append("")
    out.extend(render_summary(result, summ))
    return "\n".join(out)


def render_summary(result, summ):
    """The paste-able SUMMARY block (identical text in md and tsv modes)."""
    L = []
    L.append("SUMMARY  (scope=%s  root=%s)" % (result["scope"], result["root"]))
    L.append("  runs: %d total = %d main-loop + %d child"
             % (summ["runs_total"], summ["runs_main"], summ["runs_child"]))
    L.append("  served-model totals (API calls, <synthetic> excluded):")
    for m, n in sorted(summ["served_totals"].items(), key=lambda kv: (-kv[1], kv[0])):
        L.append("      %-32s %7d   (main %d / child %d)"
                 % (m, n, summ["served_main"].get(m, 0), summ["served_child"].get(m, 0)))
    L.append("  verdicts: MATCH %d | MISMATCH %d | UNKNOWN %d  (%d of the UNKNOWN are "
             "main-loop runs, which carry no intent layer)"
             % (summ["verdicts"].get(MATCH, 0), summ["verdicts"].get(MISMATCH, 0),
                summ["verdicts"].get(UNKNOWN, 0), summ["unknown_main"]))
    if summ["comparable"]:
        L.append("  mismatch rate: %d/%d comparable runs = %.1f%%"
                 % (summ["mismatch"], summ["comparable"], 100.0 * summ["mismatch_rate"]))
    else:
        L.append("  mismatch rate: n/a (no run carried both an intent and a serving layer)")
    if summ["signature"]:
        L.append("  mismatch signature (resolved -> served):")
        for k, v in sorted(summ["signature"].items()):
            L.append("      %-46s %3d runs, %6d calls" % (k, v["runs"], v["calls"]))
    else:
        L.append("  mismatch signature: none")
    L.append("  synthetic rows excluded: %d | malformed lines: %d | unreadable meta: %d"
             % (summ["synthetic_excluded"], summ["malformed_lines"], summ["bad_meta"]))
    for u in summ["unreadable"]:
        L.append("  UNREADABLE: %s" % u)
    L.append("  NOTE: the served column is the API's own per-call stamp -- the only "
             "authoritative layer. resolved/arg are intent.")
    return L


def render_tsv(result, summ):
    out = ["run_id\tkind\tsession\tagentType\targ\tresolved\tserved\tcalls\tverdict"]
    for r in result["runs"]:
        out.append("\t".join([
            r["run_id"], r["kind"], r["session"], r["agentType"], r["arg"] or "-",
            r["resolved"] or "-", served_str(r["served"]), str(r["calls"]), r["verdict"],
        ]))
    out.append("")
    out.extend("# " + line for line in render_summary(result, summ))
    return "\n".join(out)


# ---------------------------------------------------------------- cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="model_run_audit.py",
        description="Per-run intent-vs-served model audit for Claude Code transcripts. "
                    "Exit 0 = no MISMATCH, 1 = a MISMATCH, 2 = input/parse error.",
    )
    ap.add_argument("path", help="project dir, session JSONL, or session dir")
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="machine-readable output")
    fmt.add_argument("--tsv", action="store_true", help="tab-separated rows + commented summary")
    ap.add_argument("--summary-only", action="store_true",
                    help="print only the SUMMARY block (md mode)")
    args = ap.parse_args(argv)

    try:
        result = audit(args.path)
    except InputError as exc:
        sys.stderr.write("model_run_audit: input error: %s\n" % exc)
        return 2

    summ = summarize(result)
    if args.json:
        print(json.dumps({"scope": result["scope"], "root": result["root"],
                          "runs": result["runs"], "summary": summ},
                         indent=2, sort_keys=True))
    elif args.tsv:
        print(render_tsv(result, summ))
    elif args.summary_only:
        print("\n".join(render_summary(result, summ)))
    else:
        print(render_md(result, summ))
    return 1 if summ["mismatch"] else 0


if __name__ == "__main__":
    sys.exit(main())
