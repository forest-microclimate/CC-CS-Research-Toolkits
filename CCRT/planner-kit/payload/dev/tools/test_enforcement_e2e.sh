#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# test_enforcement_e2e.sh — red-team the INSTALLED enforcement surfaces of THIS project (the live hook
# copies + their registrations), not the kit masters (the kit's own guards own those).
# One command; exit 0 = every arm behaved. A SKIPped arm never fails the run.
#
# PAYLOAD COPY (planner-kit v1.8) — the PORTABILITY delta of its authoring master, `dev/tools/
# test_enforcement_e2e.sh` in the kit's origin workspace. Three deltas, all so an ADOPTER project gets a
# meaningful battery instead of a wall of false failures: (1) the project root comes from
# ${CLAUDE_PROJECT_DIR:-$(pwd)} — this copy is RUN FROM the project root, not from two levels down;
# (2) the arms that need the CCRT GLOBAL install (~/.claude plan-routing-gate, the global opus-guard
# matcher) SKIP loudly when it is absent; (3) the live-plan arm SKIPs when plans/current_active/ holds no
# plan. A SKIP is loud and honest; a false FAIL teaches adopters to ignore the tool.
#
# RUN FROM YOUR PROJECT ROOT:   bash dev/tools/test_enforcement_e2e.sh
#
# ARMS — the violation set replayed against:
#   G1  fable-dispatch-gate.sh   (project .claude/hooks; the ONE deny-capable gate)
#   G2  fable-launch-scaffold.sh (project .claude/hooks; prints the watchdog command)
#   PRG plan-routing-gate.sh     (~/.claude/hooks, driven via the CRT_PLANS_DIR extraction path)
#   G4  collect_outcome_gate.sh  (project .claude/hooks; the uncertified-turn one-shot block)
#   G5  plan-state-inject.sh     (project .claude/hooks; the SessionStart ACTIVE-plan injector)
#   plus the settings.json registration greps (the delivery layer a tool rename can silently kill).
set -u
WS="${CLAUDE_PROJECT_DIR:-$(pwd)}"
G1="$WS/.claude/hooks/fable-dispatch-gate.sh"; G2="$WS/.claude/hooks/fable-launch-scaffold.sh"
PRG="$HOME/.claude/hooks/plan-routing-gate.sh"; COG="$WS/.claude/hooks/collect_outcome_gate.sh"
PSI="$WS/.claude/hooks/plan-state-inject.sh";  QA="$WS/.claude/hooks/subagent_qa_gate.sh"
OPG="$HOME/.claude/hooks/opus-dispatch-guard.sh"   # the CCRT global install's tell (arm 6b)
pass=0; fail=0; skip=0
ok(){ pass=$((pass+1)); echo "  PASS  $1"; }
bad(){ fail=$((fail+1)); echo "  FAIL  $1"; }
nope(){ skip=$((skip+1)); echo "  SKIP  $1"; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT

# ---- G1 (deny gate), tool_name=Agent throughout (the live harness name) ----
out=$(printf '{"tool_name":"Agent","cwd":"%s","tool_input":{"subagent_type":"fable-executor","prompt":"do a thing"}}' "$T" | bash "$G1")
echo "$out" | grep -q '"permissionDecision": "deny"' && ok "(1a) briefless fable launch => DENY" || bad "(1a) expected deny, got: ${out:0:80}"
mkdir -p "$T/dev/briefs"
printf '# bad brief\n## 1. ASSIGNMENT\nWARMUP first: read x\n' > "$T/dev/briefs/bad.md"   # no ROLE line
out=$(printf '{"tool_name":"Agent","cwd":"%s","tool_input":{"subagent_type":"fable-executor","prompt":"Execute the brief at dev/briefs/bad.md"}}' "$T" | bash "$G1")
echo "$out" | grep -q '"permissionDecision": "deny"' && ok "(1b) ROLE-less brief => DENY" || bad "(1b) expected deny, got: ${out:0:80}"
printf '# good brief\nROLE: specialist persona by READ-POINTER (payload/agents/agent-tooling-engineer.md)\n## 1. ASSIGNMENT\nWARMUP first: read the 4 files\n' > "$T/dev/briefs/good.md"
out=$(printf '{"tool_name":"Agent","cwd":"%s","tool_input":{"subagent_type":"fable-executor","prompt":"Execute the brief at dev/briefs/good.md"}}' "$T" | bash "$G1")
[ -z "$out" ] && ok "(1c) compliant brief => silent pass" || bad "(1c) expected silence, got: ${out:0:80}"
out=$(printf '{"tool_name":"Agent","cwd":"%s","tool_input":{"subagent_type":"probe-skill","prompt":"read files"}}' "$T" | bash "$G1")
[ -z "$out" ] && ok "(1d) probe allowlist => silent" || bad "(1d) expected silence, got: ${out:0:80}"
out=$(printf '{"tool_name":"Agent","cwd":"%s","tool_input":{"subagent_type":"general-purpose","model":"sonnet","prompt":"hi"}}' "$T" | bash "$G1")
[ -z "$out" ] && ok "(1e) sonnet launch => untriggered" || bad "(1e) expected silence, got: ${out:0:80}"

# ---- G2 (scaffold) ----
err=$(printf '{"tool_name":"Agent","cwd":"%s","tool_input":{"subagent_type":"fable-executor","prompt":"x"},"tool_response":[{"type":"text","text":"output_file: /tmp/child-e2e.jsonl"}]}' "$T" | bash "$G2" 2>&1 >/dev/null)
echo "$err" | grep -q "fable_watchdog.py '/tmp/child-e2e.jsonl' --watch" && ok "(2a) scaffold prints exact watchdog cmd" || bad "(2a) got: ${err:0:100}"

# ---- plan-routing-gate LIVE via extraction path 3 (CCRT global install only) ----
if [ -f "$PRG" ]; then
  P="$T/plans"; mkdir -p "$P"
  cat > "$P/v.md" <<'EOF'
# Plan: bare owner
## Waves
one
```routing
[{"id":"D1","task":"t","archetype":"a","owner":"fable-executor","executor":"delegate:fable-executor","topology":"single-thread","model_tier":"T1","effort":"high","detached":false,"brief_ref":"b","record_access":"r","recon_done":"r","reserved_for_user":false,"scope_ref":"s","tradeoff":"t","concurrency":1}]
```
EOF
  out=$(printf '{"tool_name":"ExitPlanMode","cwd":"%s","tool_input":{}}' "$WS" | CRT_PLANS_DIR="$P" bash "$PRG")
  echo "$out" | grep -q "L7 owner-completeness" && ok "(3a) bare-owner plan => DENY at L7 (live gate, path 3)" || bad "(3a) got: ${out:0:100}"
  cat > "$P/v.md" <<'EOF'
# Plan: steps-less cascade
## Waves
one
```routing
[{"id":"D1","task":"t","archetype":"a","owner":"reviewer persona on fable-executor","executor":"delegate:fable-executor","topology":"parallel-wave","model_tier":"T1","effort":"high","detached":false,"brief_ref":"b","record_access":"r","recon_done":"r","reserved_for_user":false,"scope_ref":"s","tradeoff":"t","concurrency":2}]
```
EOF
  out=$(printf '{"tool_name":"ExitPlanMode","cwd":"%s","tool_input":{}}' "$WS" | CRT_PLANS_DIR="$P" bash "$PRG")
  echo "$out" | grep -q "L8" && ok "(3b) steps-less cascade => DENY at L8" || bad "(3b) got: ${out:0:100}"
  # (3c) LIVE plan self-test — a real approved plan must satisfy the whole gate. Conditional: an
  # adopter may have no plan yet (SKIP), and any ONE passing plan proves the arm (plans under
  # authoring alongside it are not this arm's business).
  live_found=0; live_ok=0; live_name=""; live_out=""
  for p in "$WS"/plans/current_active/*.md; do
    [ -f "$p" ] || continue
    live_found=1
    cp "$p" "$P/v.md"
    out=$(printf '{"tool_name":"ExitPlanMode","cwd":"%s","tool_input":{}}' "$WS" | CRT_PLANS_DIR="$P" bash "$PRG")
    if [ -z "$out" ]; then live_ok=1; live_name="$(basename "$p")"; break; fi
    [ -n "$live_out" ] || live_out="$(basename "$p"): ${out:0:100}"
  done
  if [ "$live_found" -eq 0 ]; then
    nope "(3c) live-plan self-test — plans/current_active/ holds no plan file"
  elif [ "$live_ok" -eq 1 ]; then
    ok "(3c) live plan $live_name => FULL PASS"
  else
    bad "(3c) no live plan passes the gate; first: $live_out"
  fi
  out=$(printf '{"tool_name":"ExitPlanMode","cwd":"%s","tool_input":{}}' "$WS" | CRT_PLANS_DIR="$T/nodir" bash "$PRG")
  [ -z "$out" ] && ok "(3d) no plans dir => fail-open silent" || bad "(3d) got: ${out:0:100}"
else
  nope "(3a-3d) plan-routing-gate arms — no \"$PRG\" (install the CCRT into ~/.claude to exercise them)"
fi

# ---- G4 (uncertified fable turn, one-shot) on a synthetic transcript ----
TR="$T/turn.jsonl"
{ printf '{"type":"user","message":{"role":"user","content":[{"type":"text","text":"please do the task"}]}}\n'
  printf '{"message":{"role":"assistant","content":[{"type":"tool_use","name":"Agent","input":{"subagent_type":"fable-executor","prompt":"Execute the brief at dev/briefs/good.md"}}]}}\n'
  printf '{"message":{"role":"assistant","content":[{"type":"text","text":"launched the child and collected its output; done."}]}}\n'; } > "$TR"
out=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"transcript_path":"%s","cwd":"%s"}' "$TR" "$WS" | PLANNER_KIT_HOOKS=on bash "$COG")
echo "$out" | grep -q '"decision": *"block"' && ok "(4a) uncertified fable turn => one-shot block" || bad "(4a) got: ${out:0:120}"
out=$(printf '{"hook_event_name":"Stop","stop_hook_active":true,"transcript_path":"%s","cwd":"%s"}' "$TR" "$WS" | PLANNER_KIT_HOOKS=on bash "$COG")
[ -z "$out" ] && ok "(4b) stop_hook_active => released (one-shot)" || bad "(4b) got: ${out:0:100}"
printf '{"message":{"role":"assistant","content":[{"type":"text","text":"watchdog: FAITHFUL calls=1-5 model=claude-fable-5; outcome: CONTINUE"}]}}\n' >> "$TR"
out=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"transcript_path":"%s","cwd":"%s"}' "$TR" "$WS" | PLANNER_KIT_HOOKS=on bash "$COG")
[ -z "$out" ] && ok "(4c) certified turn => silent" || bad "(4c) got: ${out:0:120}"

# ---- G5 (plan-state injector) ----
mkdir -p "$T/proj/plans"
printf '| Z-demo: a plan | ACTIVE (x) | plans/current_active/PLAN_demo.md | slot | notes | started 2026-08-07 |\n' > "$T/proj/plans/PLAN_LEDGER.machine.md"
out=$(CLAUDE_PROJECT_DIR="$T/proj" bash "$PSI" < /dev/null)
echo "$out" | grep -q "\[plan-state\] ACTIVE" && ok "(5a) ACTIVE ledger => injects pointer+digest" || bad "(5a) got: ${out:0:100}"
rm "$T/proj/plans/PLAN_LEDGER.machine.md"
out=$(CLAUDE_PROJECT_DIR="$T/proj" bash "$PSI" < /dev/null)
[ -z "$out" ] && ok "(5b) no ledger => silent" || bad "(5b) got: ${out:0:80}"

# ---- registrations (the delivery layer a tool rename kills silently) ----
if [ -f "$WS/.claude/settings.json" ]; then
  python3 - "$WS" <<'EOF' && ok "(6a) project registrations present w/ Task|Agent matchers" || bad "(6a) registration check failed"
import json,os,sys
root=sys.argv[1]
s=json.load(open(root+"/.claude/settings.json"))
h=s["hooks"]
def cmds(ev): return json.dumps(h.get(ev,[]))
assert "fable-dispatch-gate.sh" in cmds("PreToolUse") and "Task|Agent" in cmds("PreToolUse")
assert "fable-launch-scaffold.sh" in cmds("PostToolUse") and "Task|Agent" in cmds("PostToolUse")
assert "collect_outcome_gate.sh" in cmds("Stop")
assert "plan-state-inject.sh" in cmds("SessionStart")
assert "subagent_qa_gate.sh" in cmds("SubagentStop")
EOF
else
  bad "(6a) no \"$WS/.claude/settings.json\" — run the planner-kit installer from this project root"
fi
if [ -f "$OPG" ] && [ -f "$HOME/.claude/settings.json" ]; then
  grep -q '"matcher": "Task|Agent"' "$HOME/.claude/settings.json" && ok "(6b) global opus-guard matcher Task|Agent" || bad "(6b) global matcher not fixed"
else
  nope "(6b) global opus-guard matcher — no CCRT global install at ~/.claude"
fi

echo "=== $pass passed, $fail failed, $skip skipped ==="
[ "$fail" -eq 0 ]
