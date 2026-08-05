#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# adversary-timing-probe.sh  (machine-optimized; run in a REAL Claude Code terminal)
# WHAT: measures the F1 adversary CALL latency under each startup-strip flag combo AND
#   confirms each still AUTHENTICATES + returns a parseable verdict — so the operator
#   picks CRT_ADVERSARY_MODEL / CRT_ADVERSARY_FLAGS for stop-adversary-gate.sh from
#   MEASURED data, never a guess. Addresses beta-2: 6/9 gate firings pinned the ~60s
#   ceiling and fail-opened (real verdict on ~22%). The fix is a FASTER call; this
#   probe finds the fastest combo that still works under the operator's own auth.
# WHY a probe (not a hardcoded flag): the biggest-win flag (--bare) REQUIRES
#   ANTHROPIC_API_KEY and breaks OAuth/keychain auth → every call would error →
#   fail-open. Whether it works is auth-dependent and CANNOT be known from source;
#   it must be measured in the operator's live session. A combo that errors is
#   REJECTED here, not shipped.
# USE: run `bash lib/adversary-timing-probe.sh` in a terminal where `claude` is the
#   real CLI (NOT the Claude Science sandbox — it has no `claude`). Does REPS reps per
#   combo (default 11; override `PROBE_REPS=N`), reports min/median/max ms ranked by
#   MEDIAN (robust to the cold-start rep-1 and to right-skewed CLI latency), flags any
#   tail spike near the 60s gate ceiling, and prints the exact export line to paste.
#   Non-destructive: only ephemeral `claude -p` calls, writes nothing persistent.
# ORIGIN: claude-research-toolkit, 2026-07-11 — latency fix of record for F1.
set -uo pipefail

if ! command -v claude >/dev/null 2>&1; then
  echo "FATAL: no 'claude' CLI on PATH. Run this in a real Claude Code terminal, not the sandbox." >&2
  exit 1
fi
# portable timeout: GNU coreutils `timeout`, else Homebrew coreutils `gtimeout`, else
# none (probe still runs; a hung call must then be Ctrl-C'd). Keeps a stuck claude -p
# from pinning the run — same portability lesson as the gate's Part A python3-timeout.
if   command -v timeout  >/dev/null 2>&1; then TO="timeout 90"
elif command -v gtimeout >/dev/null 2>&1; then TO="gtimeout 90"
else TO=""; fi

# A representative FINAL CLAIM that trips pattern 1 (causal-verb-without-observation),
# so a working adversary should return {"verdict":"BLOCK",...} — lets us verify the
# call both AUTHENTICATED and REASONED, not merely exited 0.
PROBE_SYS='You are an ADVERSARIAL claim verifier. Check ONLY the final claim against: 1 causal-verb-without-observation (asserts a cause via "because"/"caused by" without observing evidence this turn). Respond ONE line strict JSON: {"verdict":"PASS"} or {"verdict":"BLOCK","reason":"<=25 words"}.'
PROBE_CLAIM='The fit converged to 52 C because it genuinely absorbs 1545 W/m2 of radiation.'

MODEL="${CRT_ADVERSARY_MODEL:-haiku}"
REPS="${PROBE_REPS:-11}"

# combos to test: label | extra flags (empty = baseline current behavior minus model pin)
run_combo() {  # $1=label  $2=flags
  local label="$1" flags="$2" ok=0 fail=0 verdict_seen=0 t0 t1 out rc samples=""
  for _ in $(seq 1 "$REPS"); do
    t0="$(python3 -c 'import time;print(int(time.time()*1000))')"
    # shellcheck disable=SC2086
    out="$(CRT_ADVERSARY_ACTIVE=1 $TO claude -p --model "$MODEL" $flags \
           "$PROBE_SYS

FINAL CLAIM:
$PROBE_CLAIM" 2>/dev/null)"; rc=$?
    t1="$(python3 -c 'import time;print(int(time.time()*1000))')"
    if [ "$rc" -ne 0 ]; then fail=$((fail+1)); continue; fi
    ok=$((ok+1)); samples="${samples}$((t1 - t0)) "
    printf '%s' "$out" | grep -q '"verdict"' && verdict_seen=$((verdict_seen+1))
  done
  # min/median/max from the per-rep samples (robust to cold-start + skew); "n/a" if none
  local stats="n/a n/a n/a"
  [ "$ok" -gt 0 ] && stats="$(printf '%s' "$samples" | python3 -c '
import sys,statistics as st
xs=sorted(int(x) for x in sys.stdin.read().split())
print(xs[0], int(st.median(xs)), xs[-1])')"
  local mn md mx; read -r mn md mx <<<"$stats"
  # machine-parseable row: label|ok|fail|reps|min_ms|median_ms|max_ms|verdict_seen
  printf 'RESULT\t%s\t%d\t%d\t%d\t%s\t%s\t%s\t%d\n' "$label" "$ok" "$fail" "$REPS" "$mn" "$md" "$mx" "$verdict_seen"
  # human line
  if [ "$fail" -gt 0 ]; then
    printf '  %-28s AUTH/CALL FAILED %d/%d — REJECT (would fail-open in the gate)\n' "$label" "$fail" "$REPS" >&2
  else
    printf '  %-28s median %6s ms  (min %s / max %s)  verdict-parsed %d/%d\n' "$label" "$md" "$mn" "$mx" "$verdict_seen" "$ok" >&2
  fi
}

echo "== F1 adversary timing probe ==  model=$MODEL  reps=$REPS  (lower median ms = clears the 60s ceiling better)" >&2
echo "   testing flag combos; a combo that errors even ONCE is rejected (it would fail-open live)." >&2
{
  run_combo "baseline (model-pin only)" ""
  run_combo "strict-mcp (OAuth-safe)"   '--strict-mcp-config --mcp-config {"mcpServers":{}}'
  run_combo "bare (needs API key)"      "--bare"
} | sort -t"$(printf '\t')" -k7 -n > /tmp/crt_probe_results.tsv || true

echo >&2
echo "== RANKED (fastest working combo first) ==" >&2
python3 - <<'PY'
rows=[]
try:
    for ln in open("/tmp/crt_probe_results.tsv"):
        if not ln.startswith("RESULT"): continue
        _,label,ok,fail,reps,mn,md,mx,vseen = ln.rstrip("\n").split("\t")
        rows.append(dict(label=label,ok=int(ok),fail=int(fail),reps=int(reps),
                         mn=(None if mn=="n/a" else int(mn)),
                         md=(None if md=="n/a" else int(md)),
                         mx=(None if mx=="n/a" else int(mx)),vseen=int(vseen)))
except FileNotFoundError:
    rows=[]
CEILING_MS=60000            # the gate's fail-open ceiling
WARN_FRAC=0.5               # warn if any single call's max exceeds this fraction of the ceiling
working=[r for r in rows if r["fail"]==0 and r["md"] is not None and r["vseen"]==r["ok"]]
working.sort(key=lambda r:r["md"])
if not working:
    print("  NO combo both authenticated AND returned a parseable verdict on every rep.")
    print("  Keep CRT_ADVERSARY_FLAGS empty (safe default); investigate auth before tuning.")
else:
    best=working[0]
    print(f"  {'combo':28s} {'median':>8} {'min':>8} {'max':>8}   (ranked by median)")
    for r in working:
        star=" <= FASTEST WORKING" if r is best else ""
        print(f"  {r['label']:28s} {r['md']:>6} ms {r['mn']:>6} {r['mx']:>6}{star}")
    # tail-risk check: does ANY working combo ever approach the fail-open ceiling?
    spikes=[r for r in working if r["mx"] >= CEILING_MS*WARN_FRAC]
    print()
    if spikes:
        for r in spikes:
            print(f"  ! TAIL WARNING: {r['label']} max {r['mx']} ms is >= {int(WARN_FRAC*100)}% of the {CEILING_MS} ms ceiling")
        print("    a call that slow risks a live fail-open; prefer the lowest-max combo, not just lowest-median.")
    else:
        print(f"  tail OK: every working combo's slowest call stayed under {int(WARN_FRAC*100)}% of the {CEILING_MS} ms ceiling.")
    print()
    print("  PASTE to adopt the fastest working combo (add to your shell / CC env):")
    print(f"    export CRT_ADVERSARY_MODEL={__import__('os').environ.get('CRT_ADVERSARY_MODEL','haiku')}")
    if best["label"].startswith("baseline"):
        print("    # (no extra flags — baseline model-pin was already fastest/safe)")
        print("    unset CRT_ADVERSARY_FLAGS 2>/dev/null || true")
    elif best["label"].startswith("strict"):
        print('    export CRT_ADVERSARY_FLAGS=\'--strict-mcp-config --mcp-config {"mcpServers":{}}\'')
    elif best["label"].startswith("bare"):
        print("    export CRT_ADVERSARY_FLAGS=--bare   # NOTE requires ANTHROPIC_API_KEY in the gate's env")
PY
echo >&2
echo "Raw rows: /tmp/crt_probe_results.tsv" >&2
