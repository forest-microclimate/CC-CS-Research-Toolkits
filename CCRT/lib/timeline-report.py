#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""timeline-report.py — durations & activity from the timeline-logger.sh JSONL log.

The timeline-logger.sh hook writes one row per session event with a DECOMPOSED,
human-readable timestamp (tz, tz_name, year, month, day, hour_min_ss — 24-hour)
plus a machine epoch_ms field. This reader uses the decomposed fields for display
and epoch_ms for EXACT duration math (the reason the numeric field is kept).

Reports, per session: wall-clock span, event counts, turn durations
(UserPromptSubmit -> Stop), and the slowest tool steps (gap between consecutive
events). No transcript mining required.

Usage:  python3 timeline-report.py [log] [--sessions] [--slowest N]
"""
import sys, json, os
from collections import defaultdict, Counter

def fmt_ms(ms):
    s = ms / 1000.0
    if s < 60:  return f"{s:.1f}s"
    if s < 3600: return f"{s/60:.1f}m"
    return f"{s/3600:.2f}h"

def main():
    args  = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    path = args[0] if args else os.environ.get(
        "CRT_TIMELINE_LOG", os.path.expanduser("~/.claude/logs/timeline.jsonl"))
    slowest_n = 10
    for f in flags:
        if f.startswith("--slowest"):
            try: slowest_n = int(f.split("=")[1])
            except Exception: pass
    if not os.path.exists(path):
        print(f"No timeline log at {path} — the logger hasn't fired yet (or CRT_TIMELINE_LOG points elsewhere).")
        return

    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception: continue
        if isinstance(r.get("epoch_ms"), (int, float)):
            rows.append(r)
    if not rows:
        print(f"Timeline log {path} has no usable rows yet.")
        return
    rows.sort(key=lambda r: r["epoch_ms"])

    ev = Counter(r.get("event","?") for r in rows)
    by_sess = defaultdict(list)
    for r in rows: by_sess[r.get("session_id","")].append(r)

    span = rows[-1]["epoch_ms"] - rows[0]["epoch_ms"]
    first, last = rows[0], rows[-1]
    print(f"=== timeline — {path} ===")
    print(f"events: {len(rows)}   sessions: {len([s for s in by_sess if s])}")
    print(f"first: {first.get('year')}-{first.get('month')}-{first.get('day')} {first.get('hour_min_ss')} {first.get('tz_name') or first.get('tz')}")
    print(f"last:  {last.get('year')}-{last.get('month')}-{last.get('day')} {last.get('hour_min_ss')} {last.get('tz_name') or last.get('tz')}")
    print(f"wall-clock span: {fmt_ms(span)}")
    print("event counts: " + ", ".join(f"{k}={v}" for k,v in ev.most_common()))

    # turn durations: each UserPromptSubmit -> next Stop in the same session
    turns = []
    for sid, evs in by_sess.items():
        evs.sort(key=lambda r: r["epoch_ms"])
        open_prompt = None
        for r in evs:
            e = r.get("event")
            if e == "UserPromptSubmit": open_prompt = r
            elif e == "Stop" and open_prompt is not None:
                turns.append(r["epoch_ms"] - open_prompt["epoch_ms"]); open_prompt = None
    if turns:
        turns_sorted = sorted(turns)
        import statistics
        print(f"\nturns (UserPromptSubmit->Stop): n={len(turns)} "
              f"median={fmt_ms(statistics.median(turns_sorted))} "
              f"min={fmt_ms(turns_sorted[0])} max={fmt_ms(turns_sorted[-1])}")

    if "--slowest" in " ".join(flags):
        gaps = []
        for sid, evs in by_sess.items():
            evs.sort(key=lambda r: r["epoch_ms"])
            for a, b in zip(evs, evs[1:]):
                gaps.append((b["epoch_ms"]-a["epoch_ms"], a, b))
        gaps.sort(key=lambda g: -g[0])
        print(f"\nslowest {slowest_n} steps (gap between consecutive events):")
        for dur, a, b in gaps[:slowest_n]:
            lbl = b.get("tool_name") or b.get("event","?")
            fp  = (" " + b["file_path"]) if b.get("file_path") else ""
            print(f"  {fmt_ms(dur):>7}  {a.get('hour_min_ss')} -> {b.get('hour_min_ss')}  {lbl}{fp}")

    if "--sessions" in flags:
        print("\nper session:")
        for sid, evs in sorted(by_sess.items(), key=lambda kv: kv[1][0]['epoch_ms']):
            evs.sort(key=lambda r: r["epoch_ms"])
            s = evs[-1]["epoch_ms"] - evs[0]["epoch_ms"]
            print(f"  {sid or '(none)'}: {len(evs)} events, span {fmt_ms(s)}, "
                  f"start {evs[0].get('hour_min_ss')}")

if __name__ == "__main__":
    main()
