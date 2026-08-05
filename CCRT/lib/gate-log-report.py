#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""gate-log-report.py — summarize the F1 adversarial-gate telemetry log.

The stop-adversary-gate.sh hook appends one JSONL event per firing to
~/.claude/logs/adversary-gate.jsonl (override with $CRT_GATE_LOG or arg 1).
This reads that live log and prints the interrupted-time-series numbers the
in-vivo efficacy test needs — no transcript mining required.

Events: fired (a claim survived the pre-filter) · block (adversary interposed)
        · block_suppressed (observe/shadow arm: WOULD have blocked, allowed through)
        · pass (adversary cleared it) · timeout (ceiling hit, fail-open, NO verdict)
        · error (fork bad-flag/auth, fail-open, NO verdict) · degraded (no claude CLI,
        reminder only) · skipped (handoff/baton turn).

MODES (master switch, see methodology/CRT_MASTER_SWITCH.machine.md): each row carries
  "mode" = on | observe. "on" rows include real `block`s; "observe" rows are the research
  shadow arm and record `block_suppressed` (the counterfactual catch) instead. "off" writes
  no rows at all, so it never appears here.

Usage:  python3 gate-log-report.py [path-to-log] [--by-day] [--patterns] [--by-build] [--by-mode]
"""
import sys, json, os
from collections import Counter, defaultdict

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    path = args[0] if args else os.environ.get(
        "CRT_GATE_LOG", os.path.expanduser("~/.claude/logs/adversary-gate.jsonl"))
    if not os.path.exists(path):
        print(f"No gate log at {path} — the gate hasn't fired yet (or CRT_GATE_LOG points elsewhere).")
        return
    ev = Counter(); pats = Counter(); by_day = defaultdict(Counter); sessions = set(); n = 0
    latencies = []; ts_span = []
    builds = defaultdict(lambda: {"rows": 0, "epochs": [], "ev": Counter(), "lat": []})  # build_id -> provenance
    modes = defaultdict(Counter)   # mode(on|observe) -> event Counter, for the research A/B split
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception: continue
        n += 1
        e = r.get("event", "?"); ev[e] += 1
        sessions.add(r.get("session_id", ""))
        by_day[r.get("ts", "")[:10]][e] += 1
        b = r.get("build_id") or "(unstamped)"   # rows from before provenance was added
        builds[b]["rows"] += 1
        builds[b]["ev"][e] += 1
        if isinstance(r.get("epoch_ms"), (int, float)):
            builds[b]["epochs"].append(r["epoch_ms"])
        if isinstance(r.get("latency_ms"), (int, float)):
            builds[b]["lat"].append(r["latency_ms"])
        modes[r.get("mode") or "(unstamped)"][e] += 1   # research arm this row belongs to
        if e in ("block", "block_suppressed") and r.get("pattern_or_reason"):
            pats[r["pattern_or_reason"][:60]] += 1
        if isinstance(r.get("latency_ms"), (int, float)):
            latencies.append(r["latency_ms"])
        if isinstance(r.get("epoch_ms"), (int, float)):
            ts_span.append(r["epoch_ms"])

    fired = ev.get("fired", 0)
    blocked = ev.get("block", 0)
    suppressed = ev.get("block_suppressed", 0)   # observe/shadow arm: would-have-blocked
    passed = ev.get("pass", 0)
    timed_out = ev.get("timeout", 0)             # fork hit the ceiling — fail-open, NO verdict
    errored = ev.get("error", 0)                 # fork errored (bad flag/auth) — fail-open, NO verdict
    failed_open = timed_out + errored            # firings that reached NO verdict and were allowed through
    judged = blocked + suppressed + passed  # firings that reached an LLM verdict (either arm) — excludes fail-opens
    print(f"=== F1 adversarial-gate telemetry — {path} ===")
    print(f"events: {n}   sessions: {len([s for s in sessions if s])}")
    # build/version provenance: which toolkit build(s) emitted these rows, and their spans.
    # Lets a mixed log be read per-version instead of pooling across a reinstall boundary.
    if builds:
        def _fmt_span(epochs):
            if not epochs: return "no timestamps"
            import datetime as _dt
            a, b = min(epochs), max(epochs)
            fa = _dt.datetime.fromtimestamp(a/1000).strftime("%Y-%m-%d %H:%M")
            fb = _dt.datetime.fromtimestamp(b/1000).strftime("%m-%d %H:%M")
            return f"{fa} … {fb}" if b > a else fa
        multi = len(builds) > 1
        print(f"  build(s): {len(builds)}" + ("  ⚠ MIXED — numbers below POOL across builds; use --by-build" if multi else ""))
        for b in sorted(builds, key=lambda k: min(builds[k]["epochs"] or [0])):
            info = builds[b]
            print(f"    {b:26s} {info['rows']:4d} rows   [{_fmt_span(info['epochs'])}]")
    # research-arm summary: which master-switch modes produced these rows.
    if modes and (len(modes) > 1 or "observe" in modes):
        arms = ", ".join(f"{m}:{sum(c.values())}" for m, c in sorted(modes.items()))
        print(f"  modes present: {arms}   (on = live/blocking · observe = shadow/research arm)")
    print(f"  fired (claim hit pre-filter):        {fired}")
    print(f"  block (adversary interposed, on):    {blocked}")
    if suppressed:
        print(f"  block_suppressed (observe/shadow):   {suppressed}  ← WOULD have blocked; agent ran uncorrected")
    print(f"  pass  (adversary cleared):           {passed}")
    if failed_open:
        print(f"  timeout (ceiling hit, fail-open):    {timed_out}  ← NO verdict; allowed through")
        if errored:
            print(f"  error   (bad flag/auth, fail-open):  {errored}  ← NO verdict; allowed through")
        reach = judged / fired if fired else 0
        print(f"  ⚠ REAL-VERDICT REACH: {judged}/{fired} firings = {reach:.0%} "
              f"({failed_open} fail-opened — the latency-cap problem)")
    print(f"  skipped (handoff/baton turn):        {ev.get('skipped',0)}")
    print(f"  degraded (no CLI, reminder):         {ev.get('degraded',0)}")
    if judged:
        caught = blocked + suppressed   # catches in EITHER arm
        print(f"  CATCH RATE among judged claims: {caught}/{judged} = {caught/judged:.0%}"
              + ("   (pools on+observe; use --by-mode to separate)" if suppressed else ""))
    print("  (catch rate ~= the in-vivo error-incidence proxy; watch it fall as rules take hold.)")
    if latencies:
        import statistics
        med = statistics.median(latencies)   # correct for both even and odd n
        med = int(med) if float(med).is_integer() else round(med, 1)
        print(f"  adversary latency (ms): n={len(latencies)} min={min(latencies)} median={med} max={max(latencies)}")
    if len(ts_span) >= 2:
        span_h = (max(ts_span) - min(ts_span)) / 3_600_000
        print(f"  log spans {span_h:.1f}h  ({fired} firings => {fired/span_h:.2f}/h)" if span_h > 0 else "")
    if "--patterns" in flags and pats:
        print("\ntop block reasons (patterns caught):")
        for p, c in pats.most_common(10):
            print(f"  {c:3d}  {p}")
    if "--by-day" in flags:
        print("\nby day (fired / block / pass / degraded):")
        for d in sorted(by_day):
            c = by_day[d]
            print(f"  {d}  {c.get('fired',0):3d} / {c.get('block',0):3d} / {c.get('pass',0):3d} / {c.get('degraded',0):3d}")
    if "--by-mode" in flags and modes:
        print("\nby mode — the on-vs-observe research split (fired / block / block_suppressed / pass · catch-rate):")
        for m in sorted(modes):
            c = modes[m]
            mj = c.get("block", 0) + c.get("block_suppressed", 0) + c.get("pass", 0)
            caught = c.get("block", 0) + c.get("block_suppressed", 0)
            cr = f"{caught}/{mj}={caught/mj:.0%}" if mj else "n/a"
            print(f"  {m:12s} {c.get('fired',0):3d} / {c.get('block',0):3d} / {c.get('block_suppressed',0):3d} / "
                  f"{c.get('pass',0):3d}   catch-rate {cr}")
        print("  (on vs observe catch-rate on matched tasks = does the toolkit's presence change what gets caught.)")
    if "--by-build" in flags and builds:
        print("\nby build (fired / block / pass / skipped / degraded · block-rate · median-latency):")
        for b in sorted(builds, key=lambda k: min(builds[k]["epochs"] or [0])):
            c = builds[b]["ev"]; lat = builds[b]["lat"]
            bj = c.get("block", 0) + c.get("pass", 0)
            br = f"{c.get('block',0)}/{bj}={c.get('block',0)/bj:.0%}" if bj else "n/a"
            ml = f"{int(__import__('statistics').median(lat))}ms" if lat else "n/a"
            print(f"  {b:26s} {c.get('fired',0):3d} / {c.get('block',0):3d} / {c.get('pass',0):3d} / "
                  f"{c.get('skipped',0):3d} / {c.get('degraded',0):3d}   block-rate {br:12s} median-lat {ml}")

if __name__ == "__main__":
    main()
