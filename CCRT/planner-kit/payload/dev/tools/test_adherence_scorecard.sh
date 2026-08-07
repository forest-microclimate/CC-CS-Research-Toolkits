#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# test_adherence_scorecard.sh -- fixture guard for dev/tools/adherence_scorecard.py.
#
# PAYLOAD COPY (planner-kit v1.8) -- the PORTABILITY delta of its authoring master,
# dev/tools/test_adherence_scorecard.sh in the kit's origin workspace. ONE delta: the LINEAGE
# fixtures are built from a SYNTHETIC project slug (exported as CLAUDE_PROJECT_DIR, which is
# what the tool derives MAIN/ARENA from) instead of the origin workspace's literal path, so
# the guard is green from any checkout -- plus two arms proving that derivation is
# load-bearing. Run it from anywhere: bash dev/tools/test_adherence_scorecard.sh
#
# RED BEFORE GREEN, two ways, both printed:
#   (1) the VIOLATING fixture -- a briefless launch, no certification, a collect with no
#       outcome -- must score miss_count > 0. A scorecard that cannot see a violation
#       measures nothing.
#   (2) the STRIPPED fixture -- byte-for-byte the COMPLIANT session with only the
#       certification and outcome TOKENS removed -- must flip D3 and D4 from 1/1 to 0/1.
#       That is what proves those two cells are keyed to the tokens and not to the shape.
# Then the green arm: every n/N cell on both fixtures, dir-mode, malformed-line tolerance,
# empty-file skip, --since, and --append idempotency (run twice => one row per session).
#
# Z9b ADDS a second block (--split / lineage), fixtured in its OWN directories so the Z9
# dir-mode counts above stay untouched: a STRADDLING session whose cells must land on the
# correct side of the split instant (and whose no-split totals must still be the Z9 sums),
# an UNDATED-record arm proving an undateable opportunity is dropped from N rather than
# guessed onto a side, LINEAGE classification from the slug-dir shape, the ARENA exclusion
# from the ITS headline, --append under the new session_id+phase key, and the
# non-destructive old-schema log migration.
#
# KP2 ADDS a third block (D6 tier-explicitness), again in its OWN dir so the counts above do
# not move: an explicit-model launch and a pinned/probe type score compliant, a generic launch
# with no model param scores a MISS, and the dimension's n/N is asserted over a mixed fixture.
# Its red side is the shipped tool BEFORE D6 existed: the TSV header carried no D6 column at
# all (receipt: sandbox/KP2_scratch/_KP2_red_receipts.txt (r3)), so nothing measured whether a
# launch's tier was ever chosen. CHANGED AT KP2 (2026-08-07): eleven count expectations in the
# Z9/Z9b blocks move by exactly the number of delegate-class launches in their fixture — D6
# adds one opportunity per launch. No D1-D5 CELL changes; only the totals that sum across
# dimensions (opportunity_count, miss/opp pairs, the composite line, the N=0 line count).
#
# Fixtures are synthesized inline into a mktemp workspace and removed on exit; the guard
# writes NOTHING inside the project tree. Exit 0 iff all green.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL="$HERE/adherence_scorecard.py"
[ -f "$TOOL" ] || { echo "FATAL: $TOOL missing"; exit 1; }

WS="$(mktemp -d "${TMPDIR:-/tmp}/adh_fixt.XXXXXX")"
trap 'rm -rf "$WS"' EXIT
T="$WS/transcripts"
mkdir -p "$T" "$WS/dev/briefs"
# LINEAGE keys on the PROJECT ROOT, so the guard names a synthetic one and points the tool at
# it: tail "A-Fake-Project" for every fixture slug below. Nothing else in this guard reads it.
FIXTURE_ROOT="$WS/A Fake Project"; mkdir -p "$FIXTURE_ROOT"
export CLAUDE_PROJECT_DIR="$FIXTURE_ROOT"
export ADH_FIXTURE_TAIL="A-Fake-Project"                 # what the tool derives from the root
export ADH_FIXTURE_SLUG="-tmp-adh-$ADH_FIXTURE_TAIL"     # a session slug ENDING in that tail
printf '# ZT-demo brief\nROLE: fixture\n' > "$WS/dev/briefs/ZT-demo.md"

PASS=0; FAIL=0
check() {  # check <label> <expected> <actual>
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); printf '  ok   %-46s %s\n' "$1" "$2"
  else FAIL=$((FAIL+1)); printf '  FAIL %-46s expected=[%s] actual=[%s]\n' "$1" "$2" "$3"; fi
}
cells() {  # cells <transcript> <session_id> <field> <slug>   (explicit --project-slug)
  # --project-slug=VALUE, not a separate arg: a slug may legitimately START with "-".
  python3 "$TOOL" "$1" "--project-slug=$4" --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin)
for r in d["rows"]:
    if r["session_id"]==sys.argv[1]:
        print(r[sys.argv[2]]); break
else: print("<no-row>")' "$2" "$3"
}
cell() {   # cell <transcript-or-dir> <session_id> <field>
  python3 "$TOOL" "$1" --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin)
for r in d["rows"]:
    if r["session_id"]==sys.argv[1]:
        print(r[sys.argv[2]]); break
else: print("<no-row>")' "$2" "$3"
}

# ---------------------------------------------------------------- fixtures
python3 - "$T" "$WS" <<'PY'
import json, os, sys
T, WS = sys.argv[1], sys.argv[2]

def rec(**kw): return kw
def user(text, ts=None, cwd=None):
    r = {"type": "user", "message": {"role": "user", "content": text}}
    if ts: r["timestamp"] = ts
    if cwd: r["cwd"] = cwd
    return r
def asst(blocks, model="claude-fable-5"):
    return {"type": "assistant", "message": {"role": "assistant", "model": model,
                                             "content": blocks}}
def text(t): return {"type": "text", "text": t}
def tool_use(i, name, inp): return {"type": "tool_use", "id": i, "name": name, "input": inp}
def result(i, content, tur=None, err=False):
    blk = {"type": "tool_result", "tool_use_id": i, "content": content}
    if err: blk["is_error"] = True
    r = {"type": "user", "message": {"role": "user", "content": [blk]}}
    if tur is not None: r["toolUseResult"] = tur
    return r

RAN = {"agentId": "a1", "agentType": "fable-executor", "content": "Report body.",
       "resolvedModel": "claude-fable-5", "status": "completed",
       "totalDurationMs": 1, "totalTokens": 1, "totalToolUseCount": 1}

def write(name, rows, malformed=False):
    with open(os.path.join(T, name), "w") as fh:
        for i, r in enumerate(rows):
            fh.write(json.dumps(r) + "\n")
            if malformed and i == 1:
                fh.write('{"type":"assistant", TRUNCATED-NOT-JSON\n')

# --- VIOLATING: denied plan, briefless launch, no cert, collect with no outcome ----------
write("v-viol.jsonl", [
    user("do the thing", ts="2026-08-01T10:00:00Z", cwd=WS),
    asst([tool_use("t1", "ExitPlanMode", {"plan": "p", "planFilePath": "/x.md"})]),
    result("t1", "BLOCKED by plan-routing-gate [Z7-marker]\nThis plan does not satisfy "
                 "A2_ROUTING_SCHEMA lint checks.", err=True),
    asst([tool_use("t2", "Agent", {"subagent_type": "fable-executor", "model": None,
                                   "description": "do work",
                                   "prompt": "Go do the work now, straight through."})]),
    result("t2", "child returned", tur=RAN),
    asst([text("Child returned. Moving on to the next piece.")]),
], malformed=True)

# --- COMPLIANT: approved plan, brief-named + WARMUP launch, cert + outcome ---------------
COMP = [
    user("do the thing", ts="2026-08-07T10:00:00Z", cwd=WS),
    asst([tool_use("t1", "ExitPlanMode", {"plan": "p", "planFilePath": "/x.md"})]),
    result("t1", "User has approved your plan. You can now start coding."),
    asst([tool_use("t2", "Agent", {"subagent_type": "fable-executor", "model": None,
          "description": "run the brief",
          "prompt": 'Execute the brief at "dev/briefs/ZT-demo.md". WARMUP first: read these '
                    '4 small files, ONE Read call each.'})]),
    result("t2", "child returned", tur=RAN),
    asst([text("Watchdog verdict FAITHFUL at call 5 (exit 0). Outcome: CONTINUE — receipts "
               "spot-checked against the artifacts.")]),
]
write("c-comp.jsonl", COMP)

# --- STRIPPED: the SAME session with only the cert + outcome TOKENS removed --------------
STRIP = [json.loads(json.dumps(r)) for r in COMP]
STRIP[5] = asst([text("Watchdog checked. Receipts spot-checked against the artifacts.")])
write("s-strip.jsonl", STRIP)

# --- MISSING-BRIEF: brief named but never persisted (D5 red arm) -------------------------
write("m-missing.jsonl", [
    user("go", ts="2026-08-07T11:00:00Z", cwd=WS),
    asst([tool_use("t9", "Agent", {"subagent_type": "opus5-executor", "model": None,
          "description": "d", "prompt": 'Execute "dev/briefs/ZT-absent.md" now.'})]),
    result("t9", "ok", tur=RAN),
    asst([text("Done. Outcome: GOAL-MET.")]),
])

# --- EMPTY-ish: records but zero assistant rows; and a zero-byte file --------------------
write("e-noassistant.jsonl", [user("hello", ts="2026-08-07T12:00:00Z", cwd=WS),
                              {"type": "system", "content": "boot"}])
open(os.path.join(T, "z-zero.jsonl"), "w").close()
PY

V="$T/v-viol.jsonl"; C="$T/c-comp.jsonl"; S="$T/s-strip.jsonl"; M="$T/m-missing.jsonl"

echo "=== RED ARM 1: the VIOLATING fixture must score misses ==="
python3 "$TOOL" "$V" | sed 's/^/    /'
echo
echo "=== RED ARM 2: STRIPPED == COMPLIANT minus the cert/outcome tokens ==="
python3 "$TOOL" "$S" | sed 's/^/    /'
echo
echo "=== ASSERTIONS ==="

echo "-- violating session (red arm 1) --"
check "viol D1 plan-routing"       "0/1" "$(cell "$V" v-viol D1_plan_routing)"
check "viol D2 launch-brief"       "0/1" "$(cell "$V" v-viol D2_launch_brief)"
check "viol D3 certification"      "0/1" "$(cell "$V" v-viol D3_certification)"
check "viol D4 collect-outcome"    "0/1" "$(cell "$V" v-viol D4_collect_outcome)"
check "viol D5 brief-persistence"  "-"   "$(cell "$V" v-viol D5_brief_persistence)"
check "viol miss_count"            "4"   "$(cell "$V" v-viol miss_count)"
check "viol opportunity_count"     "5"   "$(cell "$V" v-viol opportunity_count)"
check "viol miss_count > 0 (RED)"  "yes" "$([ "$(cell "$V" v-viol miss_count)" -gt 0 ] && echo yes || echo no)"
check "viol main_model"            "claude-fable-5" "$(cell "$V" v-viol main_model)"
check "viol start_date"            "2026-08-01"     "$(cell "$V" v-viol start_date)"
check "viol malformed tolerated"   "1"   "$(cell "$V" v-viol malformed_lines)"

echo "-- compliant session (green arm) --"
check "comp D1 plan-routing"       "1/1" "$(cell "$C" c-comp D1_plan_routing)"
check "comp D2 launch-brief"       "1/1" "$(cell "$C" c-comp D2_launch_brief)"
check "comp D3 certification"      "1/1" "$(cell "$C" c-comp D3_certification)"
check "comp D4 collect-outcome"    "1/1" "$(cell "$C" c-comp D4_collect_outcome)"
check "comp D5 brief-persistence"  "1/1" "$(cell "$C" c-comp D5_brief_persistence)"
check "comp miss_count"            "0"   "$(cell "$C" c-comp miss_count)"
check "comp opportunity_count"     "6"   "$(cell "$C" c-comp opportunity_count)"

echo "-- stripped session (red arm 2: same shape, tokens gone) --"
check "strip D3 flips to 0/1"      "0/1" "$(cell "$S" s-strip D3_certification)"
check "strip D4 flips to 0/1"      "0/1" "$(cell "$S" s-strip D4_collect_outcome)"
check "strip D1 unchanged"         "1/1" "$(cell "$S" s-strip D1_plan_routing)"
check "strip D2 unchanged"         "1/1" "$(cell "$S" s-strip D2_launch_brief)"
check "strip miss_count"           "2"   "$(cell "$S" s-strip miss_count)"

echo "-- missing-brief session (D5 red arm) --"
check "missing D5 is 0/1"          "0/1" "$(cell "$M" m-missing D5_brief_persistence)"
check "missing D2 compliant"       "1/1" "$(cell "$M" m-missing D2_launch_brief)"
check "missing D4 outcome named"   "1/1" "$(cell "$M" m-missing D4_collect_outcome)"
check "missing D3 not fable-tier"  "-"   "$(cell "$M" m-missing D3_certification)"

echo "-- dir mode + empty-file skip --"
DIRJSON="$(python3 "$TOOL" "$T" --json)"
check "dir mode scores 4 sessions" "4" "$(printf '%s' "$DIRJSON" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["rows"]))')"
check "dir mode skips 2 files"     "2" "$(printf '%s' "$DIRJSON" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["skipped"]))')"
check "dir mode no read failures"  "0" "$(printf '%s' "$DIRJSON" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["failed"]))')"
check "dir rows sorted by date"    "2026-08-01,2026-08-07,2026-08-07,2026-08-07" \
  "$(printf '%s' "$DIRJSON" | python3 -c 'import json,sys;print(",".join(r["start_date"] for r in json.load(sys.stdin)["rows"]))')"
check "dir mode exit code"         "0" "$(python3 "$TOOL" "$T" >/dev/null 2>&1; echo $?)"

echo "-- --since filter --"
check "--since 2026-08-07 keeps 3" "3" \
  "$(python3 "$TOOL" "$T" --since 2026-08-07 --json | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["rows"]))')"
check "--since bad format exits 2" "2" "$(python3 "$TOOL" "$T" --since 08/07/26 >/dev/null 2>&1; echo $?)"

echo "-- --append idempotency --"
LOG="$WS/ADHERENCE_LOG.tsv"
python3 "$TOOL" "$T" --append "$LOG" >/dev/null
N1="$(wc -l < "$LOG" | tr -d ' ')"
H1="$(head -1 "$LOG")"
python3 "$TOOL" "$T" --append "$LOG" >/dev/null
N2="$(wc -l < "$LOG" | tr -d ' ')"
check "log header once"            "session_id" "$(printf '%s' "$H1" | cut -f1)"
check "log rows after run 1"       "5" "$N1"                  # header + 4 sessions
check "log rows after run 2"       "$N1" "$N2"                # idempotent: no duplication
check "no duplicate session ids"   "4" "$(tail -n +2 "$LOG" | cut -f1 | sort -u | wc -l | tr -d ' ')"
check "log byte-stable on re-run"  "same" \
  "$(cp "$LOG" "$WS/l1"; python3 "$TOOL" "$T" --append "$LOG" >/dev/null; cmp -s "$WS/l1" "$LOG" && echo same || echo differs)"
check "append creates missing dir" "0" \
  "$(python3 "$TOOL" "$C" --append "$WS/new/deep/L.tsv" >/dev/null 2>&1; echo $?)"
check "log replaces, never dupes"  "1" \
  "$(python3 "$TOOL" "$C" --append "$LOG" >/dev/null; tail -n +2 "$LOG" | cut -f1 | grep -c '^c-comp$')"

echo "-- input errors --"
check "missing path exits 2"       "2" "$(python3 "$TOOL" "$WS/nope" >/dev/null 2>&1; echo $?)"
check "non-jsonl file exits 2"     "2" "$(python3 "$TOOL" "$WS/dev/briefs/ZT-demo.md" >/dev/null 2>&1; echo $?)"
check "empty dir exits 2"          "2" "$(mkdir -p "$WS/emptydir"; python3 "$TOOL" "$WS/emptydir" >/dev/null 2>&1; echo $?)"


# ================================================================= Z9b: --split + lineage
SPLIT="2026-08-07T07:00:00Z"
SP="$WS/split"                 # its OWN dir: the Z9 dir-mode counts above must not move
mkdir -p "$SP"

cellp() {  # cellp <transcript> <session_id> <phase> <field>   (split-mode, phase-keyed)
  python3 "$TOOL" "$1" --split "$SPLIT" --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin)
for r in d["rows"]:
    if r["session_id"]==sys.argv[1] and r["phase"]==sys.argv[2]:
        print(r[sys.argv[3]]); break
else: print("<no-row>")' "$2" "$3" "$4"
}

python3 - "$SP" "$WS" <<'PY'
import json, os, sys
SP, WS = sys.argv[1], sys.argv[2]

def user(text, ts=None, cwd=None):
    r = {"type": "user", "message": {"role": "user", "content": text}}
    if ts: r["timestamp"] = ts
    if cwd: r["cwd"] = cwd
    return r
def asst(blocks, ts=None, model="claude-fable-5"):
    r = {"type": "assistant", "message": {"role": "assistant", "model": model,
                                          "content": blocks}}
    if ts: r["timestamp"] = ts
    return r
def text(t): return {"type": "text", "text": t}
def tool_use(i, name, inp): return {"type": "tool_use", "id": i, "name": name, "input": inp}
def result(i, content, tur=None, err=False, ts=None):
    blk = {"type": "tool_result", "tool_use_id": i, "content": content}
    if err: blk["is_error"] = True
    r = {"type": "user", "message": {"role": "user", "content": [blk]}}
    if tur is not None: r["toolUseResult"] = tur
    if ts: r["timestamp"] = ts
    return r

RAN = {"agentId": "a1", "agentType": "fable-executor", "content": "Report body.",
       "resolvedModel": "claude-fable-5", "status": "completed",
       "totalDurationMs": 1, "totalTokens": 1, "totalToolUseCount": 1}

def write(d, name, rows):
    with open(os.path.join(d, name), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

# --- STRADDLING: starts the DAY BEFORE the split, runs past it. Z9 filed all of this ------
#     under start_date 2026-08-06 (= PRE); per-turn dating must split it 3 pre / 5 post.
#     PRE  side: denied plan, briefless opus5 launch (gated, NOT fable-tier => no D3),
#                its completed result closed by a genuine user message with no outcome.
#     POST side: approved plan, brief-named fable launch, certification + outcome, close.
write(SP, "x-strad.jsonl", [
    user("start", ts="2026-08-06T23:00:00Z", cwd=WS),
    asst([tool_use("t1", "ExitPlanMode", {"plan": "p"})], ts="2026-08-06T23:01:00Z"),
    result("t1", "BLOCKED by plan-routing-gate [Z7-marker]", err=True,
           ts="2026-08-06T23:01:30Z"),
    asst([tool_use("t2", "Agent", {"subagent_type": "opus5-executor", "model": None,
          "description": "d", "prompt": "Go do it, straight through."})],
         ts="2026-08-06T23:02:00Z"),
    result("t2", "child returned", tur=RAN, ts="2026-08-06T23:03:00Z"),
    user("next thing please", ts="2026-08-06T23:30:00Z"),
    asst([tool_use("t3", "ExitPlanMode", {"plan": "p2"})], ts="2026-08-07T08:01:00Z"),
    result("t3", "User has approved your plan. You can now start coding.",
           ts="2026-08-07T08:01:30Z"),
    asst([tool_use("t4", "Agent", {"subagent_type": "fable-executor", "model": None,
          "description": "run the brief",
          "prompt": 'Execute the brief at "dev/briefs/ZT-demo.md".'})],
         ts="2026-08-07T08:02:00Z"),
    result("t4", "child returned", tur=RAN, ts="2026-08-07T08:03:00Z"),
    asst([text("Watchdog verdict FAITHFUL at call 5. Outcome: CONTINUE.")],
         ts="2026-08-07T08:04:00Z"),
    user("done", ts="2026-08-07T08:30:00Z"),
])

# --- UNDATED: only the session's FIRST record carries a timestamp. Under --split the three
#     opportunities whose carrying record is undateable must leave N entirely; the segment
#     closed at EOF is dated by the last timestamped record seen (the documented EOF rule).
write(SP, "u-undated.jsonl", [
    user("go", ts="2026-08-07T06:00:00Z", cwd=WS),
    asst([tool_use("t1", "ExitPlanMode", {"plan": "p"})]),
    result("t1", "User has approved your plan. You can now start coding."),
    asst([tool_use("t2", "Agent", {"subagent_type": "fable-executor", "model": None,
          "description": "d", "prompt": "Just go."})]),
    result("t2", "child returned", tur=RAN),
    asst([text("Outcome: CONTINUE.")]),
])

# --- LINEAGE: the same transcript filed under three slug-dir SHAPES ----------------------
BASE = os.environ["ADH_FIXTURE_SLUG"]
for slug in (BASE, BASE + "-sandbox-test-project", BASE + "-projects-CCRT"):
    d = os.path.join(WS, "slugs", slug)
    os.makedirs(d)
    with open(os.path.join(SP, "x-strad.jsonl")) as src, \
         open(os.path.join(d, "x-strad.jsonl"), "w") as dst:
        dst.write(src.read())
PY

X="$SP/x-strad.jsonl"; U="$SP/u-undated.jsonl"
SLUGS="$WS/slugs"
LMAIN="$SLUGS/$ADH_FIXTURE_SLUG"
LARENA="$LMAIN-sandbox-test-project"
LOTHER="$LMAIN-projects-CCRT"

echo
echo "=== Z9b: straddling session, --split $SPLIT ==="
python3 "$TOOL" "$X" --split "$SPLIT" | sed 's/^/    /'
echo
echo "=== Z9b ASSERTIONS ==="

echo "-- straddling session splits into two rows --"
check "strad emits 2 rows"         "2" \
  "$(python3 "$TOOL" "$X" --split "$SPLIT" --json | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["rows"]))')"
check "strad phases pre,post"      "pre,post" \
  "$(python3 "$TOOL" "$X" --split "$SPLIT" --json | python3 -c 'import json,sys;print(",".join(r["phase"] for r in json.load(sys.stdin)["rows"]))')"
check "strad one session_id"       "1" \
  "$(python3 "$TOOL" "$X" --split "$SPLIT" --json | python3 -c 'import json,sys;print(len({r["session_id"] for r in json.load(sys.stdin)["rows"]}))')"
check "strad start_date is PRE-day" "2026-08-06" "$(cellp "$X" x-strad post start_date)"

echo "-- PRE cells (all before the split instant) --"
check "strad pre  D1 denied"       "0/1" "$(cellp "$X" x-strad pre D1_plan_routing)"
check "strad pre  D2 briefless"    "0/1" "$(cellp "$X" x-strad pre D2_launch_brief)"
check "strad pre  D3 none (opus5)" "-"   "$(cellp "$X" x-strad pre D3_certification)"
check "strad pre  D4 no outcome"   "0/1" "$(cellp "$X" x-strad pre D4_collect_outcome)"
check "strad pre  D5 no brief"     "-"   "$(cellp "$X" x-strad pre D5_brief_persistence)"
check "strad pre  miss/opp"        "3/4" \
  "$(cellp "$X" x-strad pre miss_count)/$(cellp "$X" x-strad pre opportunity_count)"

echo "-- POST cells (all after the split instant) --"
check "strad post D1 approved"     "1/1" "$(cellp "$X" x-strad post D1_plan_routing)"
check "strad post D2 brief named"  "1/1" "$(cellp "$X" x-strad post D2_launch_brief)"
check "strad post D3 certified"    "1/1" "$(cellp "$X" x-strad post D3_certification)"
check "strad post D4 outcome"      "1/1" "$(cellp "$X" x-strad post D4_collect_outcome)"
check "strad post D5 brief exists" "1/1" "$(cellp "$X" x-strad post D5_brief_persistence)"
check "strad post miss/opp"        "0/6" \
  "$(cellp "$X" x-strad post miss_count)/$(cellp "$X" x-strad post opportunity_count)"

echo "-- ADDITIVE: no --split reproduces the Z9 whole-session sums --"
check "strad nosplit 1 row"        "1" \
  "$(python3 "$TOOL" "$X" --json | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["rows"]))')"
check "strad nosplit phase=all"    "all" "$(cell "$X" x-strad phase)"
check "strad nosplit D1"           "1/2" "$(cell "$X" x-strad D1_plan_routing)"
check "strad nosplit D2"           "1/2" "$(cell "$X" x-strad D2_launch_brief)"
check "strad nosplit D3"           "1/1" "$(cell "$X" x-strad D3_certification)"
check "strad nosplit D4"           "1/2" "$(cell "$X" x-strad D4_collect_outcome)"
check "strad nosplit D5"           "1/1" "$(cell "$X" x-strad D5_brief_persistence)"
check "strad nosplit miss/opp"     "3/10" \
  "$(cell "$X" x-strad miss_count)/$(cell "$X" x-strad opportunity_count)"
check "strad split totals = nosplit" "10" \
  "$(( $(cellp "$X" x-strad pre opportunity_count) + $(cellp "$X" x-strad post opportunity_count) ))"

echo "-- undated opportunities: EXCLUDED from N, never guessed onto a side --"
check "undated nosplit counts all" "5" "$(cell "$U" u-undated opportunity_count)"
check "undated nosplit D1"         "1/1" "$(cell "$U" u-undated D1_plan_routing)"
check "undated split drops D1"     "-"   "$(cellp "$U" u-undated pre D1_plan_routing)"
check "undated split drops D2"     "-"   "$(cellp "$U" u-undated pre D2_launch_brief)"
check "undated split drops D3"     "-"   "$(cellp "$U" u-undated pre D3_certification)"
check "undated split keeps D4/EOF" "1/1" "$(cellp "$U" u-undated pre D4_collect_outcome)"
check "undated split opp count"    "1"   "$(cellp "$U" u-undated pre opportunity_count)"
check "undated counted separately" "4"   "$(cellp "$U" u-undated pre undated_opportunities)"
check "undated: no row invented"   "1" \
  "$(python3 "$TOOL" "$U" --split "$SPLIT" --json | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["rows"]))')"

echo "-- lineage from the slug-dir shape --"
check "lineage MAIN  (exact slug)"  "MAIN"  "$(cell "$LMAIN/x-strad.jsonl"  x-strad lineage)"
check "lineage ARENA (-sandbox-)"   "ARENA" "$(cell "$LARENA/x-strad.jsonl" x-strad lineage)"
check "lineage OTHER (sub-slug)"    "OTHER" "$(cell "$LOTHER/x-strad.jsonl" x-strad lineage)"
check "lineage OTHER (non-slug dir)" "OTHER" "$(cell "$X" x-strad lineage)"
check "lineage slug DERIVED not fixed" "OTHER" "$(cells "$LMAIN/x-strad.jsonl" x-strad lineage some-other-project)"
check "lineage --project-slug wins"    "MAIN"  "$(cells "$LMAIN/x-strad.jsonl" x-strad lineage "$ADH_FIXTURE_TAIL")"
check "lineage survives the split"  "ARENA,ARENA" \
  "$(python3 "$TOOL" "$LARENA/x-strad.jsonl" --split "$SPLIT" --json | python3 -c 'import json,sys;print(",".join(r["lineage"] for r in json.load(sys.stdin)["rows"]))')"

echo "-- ARENA is kept in the rows but excluded from the ITS headline --"
check "ARENA row keeps its opps"   "10" \
  "$(python3 "$TOOL" "$LARENA/x-strad.jsonl" --split "$SPLIT" --json | python3 -c 'import json,sys;print(sum(r["opportunity_count"] for r in json.load(sys.stdin)["rows"]))')"
check "ARENA headline all N=0"     "7" \
  "$(python3 "$TOOL" "$LARENA/x-strad.jsonl" --split "$SPLIT" | grep -c 'N=0).*N=0)')"
check "ARENA exclusion is stated"  "1" \
  "$(python3 "$TOOL" "$LARENA/x-strad.jsonl" --split "$SPLIT" | grep -c 'EXCLUDED from this headline: 2 non-MAIN rows')"
check "MAIN headline is populated" "1" \
  "$(python3 "$TOOL" "$LMAIN/x-strad.jsonl" --split "$SPLIT" | grep -c 'composite  *1/4 *25.0% *6/6 *100.0%')"

echo "-- --append under the session_id+phase key --"
LOG2="$WS/L_split.tsv"
python3 "$TOOL" "$X" --split "$SPLIT" --append "$LOG2" >/dev/null
N1S="$(wc -l < "$LOG2" | tr -d ' ')"
cp "$LOG2" "$WS/l2"
python3 "$TOOL" "$X" --split "$SPLIT" --append "$LOG2" >/dev/null
check "split log: header + 2 rows"  "3" "$N1S"
check "split log idempotent"        "3" "$(wc -l < "$LOG2" | tr -d ' ')"
check "split log byte-stable"       "same" "$(cmp -s "$WS/l2" "$LOG2" && echo same || echo differs)"
check "split log keeps both phases" "post,pre" \
  "$(tail -n +2 "$LOG2" | cut -f3 | sort | paste -sd, -)"
check "split log header has phase"  "phase" "$(head -1 "$LOG2" | cut -f3)"
check "split log header has lineage" "lineage" "$(head -1 "$LOG2" | cut -f4)"

echo "-- old-schema log is set aside, never overwritten in place --"
LOG3="$WS/L_old.tsv"
printf 'session_id\tstart_date\tmain_model\tD1_plan_routing\tD2_launch_brief\tD3_certification\tD4_collect_outcome\tD5_brief_persistence\tmiss_count\topportunity_count\n' > "$LOG3"
printf 'z-legacy\t2026-08-01\tclaude-fable-5\t-\t-\t-\t-\t-\t0\t0\n' >> "$LOG3"
python3 "$TOOL" "$X" --split "$SPLIT" --append "$LOG3" >/dev/null
check "old log preserved beside"    "yes" "$([ -f "$LOG3.pre-z9b" ] && echo yes || echo no)"
check "old log content intact"      "z-legacy" "$(tail -1 "$LOG3.pre-z9b" | cut -f1)"
check "new log carries new header"  "phase" "$(head -1 "$LOG3" | cut -f3)"
check "new log dropped stale rows"  "0" "$(tail -n +2 "$LOG3" | grep -c '^z-legacy' || true)"

echo "-- --split input validation --"
check "--split bad format exits 2"  "2" "$(python3 "$TOOL" "$X" --split "not-a-date" >/dev/null 2>&1; echo $?)"
check "--split good exits 0"        "0" "$(python3 "$TOOL" "$X" --split "$SPLIT" >/dev/null 2>&1; echo $?)"
check "--split offset form == Z form" "same" \
  "$(python3 "$TOOL" "$X" --split "2026-08-07T00:00:00-07:00" --tsv > "$WS/o1"; \
     python3 "$TOOL" "$X" --split "$SPLIT" --tsv > "$WS/o2"; \
     cmp -s "$WS/o1" "$WS/o2" && echo same || echo differs)"

# ================================================================= KP2: D6 tier-explicitness
D6D="$WS/d6"                   # its OWN dir again: the Z9 dir-mode counts must not move
mkdir -p "$D6D"

python3 - "$D6D" "$WS" <<'PY'
import json, os, sys
D6D, WS = sys.argv[1], sys.argv[2]

def user(text, ts=None, cwd=None):
    r = {"type": "user", "message": {"role": "user", "content": text}}
    if ts: r["timestamp"] = ts
    if cwd: r["cwd"] = cwd
    return r
def asst(blocks, ts="2026-08-07T09:00:00Z"):
    return {"type": "assistant", "timestamp": ts,
            "message": {"role": "assistant", "model": "claude-opus-4-8", "content": blocks}}
def tool_use(i, inp):
    return {"type": "tool_use", "id": i, "name": "Agent", "input": inp}
def result(i, tur=None, ts="2026-08-07T09:01:00Z"):
    r = {"type": "user", "timestamp": ts,
         "message": {"role": "user",
                     "content": [{"type": "tool_result", "tool_use_id": i, "content": "ok"}]}}
    if tur is not None: r["toolUseResult"] = tur
    return r

RAN = {"agentId": "a1", "status": "completed", "content": "Report body."}

# The four launch SHAPES D6 judges. Only the tier-explicitness question differs between them.
GENERIC = {"subagent_type": "general-purpose", "description": "d",
           "prompt": "Do the synthesis and write it up."}                   # MISS: no param
EXPLICIT = dict(GENERIC, model="sonnet")                                    # ok: named model
PINNED = {"subagent_type": "fable-executor", "description": "d",
          "prompt": 'Execute the brief at "dev/briefs/ZT-demo.md". WARMUP first.'}  # ok: pin
PROBE = {"subagent_type": "probe-skill", "description": "d",
         "prompt": "Return the single word ready."}                          # ok: probe cell

def write(name, launches):
    rows = [user("go", ts="2026-08-07T09:00:00Z", cwd=WS)]
    for n, inp in enumerate(launches):
        rows.append(asst([tool_use("t%d" % n, inp)]))
        rows.append(result("t%d" % n, tur=RAN))
    with open(os.path.join(D6D, name), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

write("d6-generic.jsonl", [GENERIC])
write("d6-model.jsonl", [EXPLICIT])
write("d6-pinned.jsonl", [PINNED])
write("d6-probe.jsonl", [PROBE])
write("d6-mix.jsonl", [GENERIC, EXPLICIT, PINNED, PROBE])
PY

echo
echo "=== KP2: D6 tier-explicitness ==="
python3 "$TOOL" "$D6D/d6-mix.jsonl" | sed 's/^/    /'
echo
echo "-- D6: the four launch shapes --"
check "D6 generic, no model = MISS"  "0/1" "$(cell "$D6D/d6-generic.jsonl" d6-generic D6_tier_explicitness)"
check "D6 explicit model param ok"   "1/1" "$(cell "$D6D/d6-model.jsonl"   d6-model   D6_tier_explicitness)"
check "D6 pinned subagent_type ok"   "1/1" "$(cell "$D6D/d6-pinned.jsonl"  d6-pinned  D6_tier_explicitness)"
check "D6 probe- type ok"            "1/1" "$(cell "$D6D/d6-probe.jsonl"   d6-probe   D6_tier_explicitness)"
check "D6 mixed fixture n/N"         "3/4" "$(cell "$D6D/d6-mix.jsonl"     d6-mix     D6_tier_explicitness)"

echo "-- D6: N is WIDER than D2's gated trigger set (that is the point) --"
# The probe launch is allowlisted out of D2 and the generic ones are outside its trigger set,
# so D2 sees ONE opportunity where D6 sees four: D1-D5 measure how the fable/opus5 launches
# were RUN, D6 measures whether the tier was CHOSEN, which is asked of every child.
check "D6 counts all 4 launches"     "4" "$(cell "$D6D/d6-mix.jsonl" d6-mix D6_tier_explicitness | cut -d/ -f2)"
check "D2 counts only the gated one" "1/1" "$(cell "$D6D/d6-mix.jsonl" d6-mix D2_launch_brief)"

echo "-- D6: schema + column position --"
check "D6 column in the TSV header"  "D6_tier_explicitness" \
  "$(python3 "$TOOL" "$D6D/d6-mix.jsonl" --tsv | head -1 | cut -f11)"
check "miss/opp still the last two"  "miss_count,opportunity_count" \
  "$(python3 "$TOOL" "$D6D/d6-mix.jsonl" --tsv | head -1 | cut -f12,13 | tr '\t' ',')"
check "D6 in the rendered table"     "1" \
  "$(python3 "$TOOL" "$D6D/d6-mix.jsonl" | grep -c '| D4 | D5 | D6 | miss | opp |')"
check "D6 in the ITS headline"       "1" \
  "$(python3 "$TOOL" "$D6D/d6-mix.jsonl" --split "$SPLIT" | sed -n '/ITS HEADLINE/,$p' | grep -c 'D6_tier_explicitness')"

echo "-- KP2: a SECOND schema migration never overwrites the first set-aside --"
OLDHDR='session_id\tstart_date\tmain_model\tD1_plan_routing\tD2_launch_brief\tD3_certification\tD4_collect_outcome\tD5_brief_persistence\tmiss_count\topportunity_count\n'
LOG4="$WS/L_twice.tsv"
printf "$OLDHDR" > "$LOG4"; printf 'z-first\t2026-08-01\tclaude-fable-5\t-\t-\t-\t-\t-\t0\t0\n' >> "$LOG4"
python3 "$TOOL" "$D6D/d6-mix.jsonl" --append "$LOG4" >/dev/null
printf "$OLDHDR" > "$LOG4"; printf 'z-second\t2026-08-02\tclaude-fable-5\t-\t-\t-\t-\t-\t0\t0\n' >> "$LOG4"
python3 "$TOOL" "$D6D/d6-mix.jsonl" --append "$LOG4" >/dev/null
check "first set-aside still intact"  "z-first"  "$(tail -1 "$LOG4.pre-z9b" | cut -f1)"
check "second set aside beside it"    "z-second" "$(tail -1 "$LOG4.pre-z9b.2" | cut -f1)"
check "live log carries the new rows" "d6-mix"   "$(tail -1 "$LOG4" | cut -f1)"

echo
echo "=== $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
