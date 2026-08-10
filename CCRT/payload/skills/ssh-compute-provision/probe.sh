#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# probe.sh — BOX-SIDE readiness probe, run AS THE COMPUTE USER over a key-only SSH connection.
# Emits machine-readable lines the client greps for. Proves the account can key-login AND the
# conda env actually resolves + runs python — the two things a compute provider needs — and
# SIZES the box: it detects cores + RAM and computes the resource budgets from them.
# WHY SIZING LIVES HERE: this script runs ON THE MACHINE BEING SIZED. The client's own core
#   count and RAM are irrelevant to a remote box, so detection must happen on this side of the
#   SSH connection, never on the operator's laptop.
# INPUTS (env, passed in the remote command string — SSH does not forward env):
#   ENV_NAME              conda env to test (default: claude)
#   MAX_CONCURRENT_JOBS   how many jobs will run at once (default: 1) — the ONLY sizing input a
#                         human supplies; cores and RAM are detected, never asked for.
# OUTPUT (in order): one PROBE_SIZING line, then exactly one PROBE_OK / PROBE_FAIL line.
#   PROBE_SIZING is emitted BEFORE the conda checks, so even a failed probe reports the box's
#   capacity. An undetectable quantity prints '?' and degrades to a documented conservative
#   default named in basis= — it is never silently guessed.
# Non-fatal: prints PROBE_FAIL rather than exit!=0 so the client always sees a verdict line.
set -uo pipefail

ENV_NAME="${ENV_NAME:-claude}"
CONDA="$HOME/miniforge3/bin/conda"

# ---- portable detection: Linux first, then the macOS/BSD sysctl keys, then getconf ----------
# Each path is tried only if its tool exists and only until one ANSWERS with a plain integer;
# a tool that exists but does not know the key (e.g. Linux `sysctl hw.ncpu`) falls through.
detect_cores() {
  _v=""
  command -v nproc >/dev/null 2>&1 && _v="$(nproc 2>/dev/null || true)"
  [ -z "$_v" ] && command -v sysctl >/dev/null 2>&1 && _v="$(sysctl -n hw.ncpu 2>/dev/null || true)"
  [ -z "$_v" ] && command -v getconf >/dev/null 2>&1 && _v="$(getconf _NPROCESSORS_ONLN 2>/dev/null || true)"
  case "$_v" in ''|*[!0-9]*) echo '?' ;; *) echo "$_v" ;; esac
}

detect_mem_gib() {
  _m=""
  if [ -r /proc/meminfo ]; then
    _m="$(awk '/^MemTotal:/ {printf "%.0f", $2/1048576; exit}' /proc/meminfo 2>/dev/null || true)"
  fi
  if [ -z "$_m" ] && command -v sysctl >/dev/null 2>&1; then
    _b="$(sysctl -n hw.memsize 2>/dev/null || true)"
    case "$_b" in ''|*[!0-9]*) : ;; *) _m="$(( _b / 1073741824 ))" ;; esac
  fi
  case "$_m" in ''|*[!0-9]*) echo '?' ;; *) echo "$_m" ;; esac
}

arch="$(uname -m)"; kern="$(uname -r)"
cores="$(detect_cores)"
memg="$(detect_mem_gib)"

# ---- budgets, COMPUTED from what was detected (the operator hand-figures nothing) -----------
# K = min(cores-2, floor(cores/max_concurrent_jobs)), floor 1.
#     `cores-2` is the house cap (preflight-parallel): leave ~2 cores for the OS and whatever
#     else shares this box. The second term keeps N simultaneous jobs from thread-storming.
# H = mem_gib - reserve, reserve = mem_gib/4 clamped to [2,8] GiB, floor 1. A SOFT ceiling for
#     `systemctl set-property user-<uid>.slice MemoryHigh=<H>G` — throttles + reclaims rather
#     than OOM-killing a long job, so the reserve is headroom for the OS, not a hard wall.
# basis= carries every departure from "all three numbers came straight off the box", so a reader
# of the emitted block can tell a measured budget from a fallback one. Empty ⇒ nothing departed.
maxc="${MAX_CONCURRENT_JOBS:-1}"
basis=""
note(){ if [ -z "$basis" ]; then basis="$1"; else basis="$basis,$1"; fi; }
case "$maxc" in ''|*[!0-9]*|0) maxc=1; note "max_concurrent_invalid_coerced_to_1" ;; esac

if [ "$cores" = '?' ]; then
  threads_k=1                       # conservative documented default: single-threaded is safe anywhere
  note "cores_undetected_K_defaults_to_1"
else
  threads_k=$(( cores - 2 ))
  _share=$(( cores / maxc ))
  [ "$_share" -lt "$threads_k" ] && threads_k=$_share
  [ "$threads_k" -lt 1 ] && threads_k=1
fi

if [ "$memg" = '?' ]; then
  mem_high='unset'                  # no detected total ⇒ no ceiling invented; say so instead
  note "ram_undetected_no_memory_ceiling"
else
  _res=$(( memg / 4 ))
  [ "$_res" -lt 2 ] && _res=2
  [ "$_res" -gt 8 ] && _res=8
  mem_high=$(( memg - _res ))
  [ "$mem_high" -lt 1 ] && mem_high=1
fi
[ -z "$basis" ] && basis="detected"

echo "PROBE_SIZING cores=$cores mem_gib=$memg max_concurrent=$maxc threads_k=$threads_k mem_high_gib=$mem_high basis=$basis"

if [ ! -x "$CONDA" ]; then
  echo "PROBE_FAIL reason=no_conda path=$CONDA"; exit 0
fi
pyver="$("$CONDA" run -n "$ENV_NAME" python -c 'import platform;print(platform.python_version())' 2>/dev/null || true)"
if [ -z "$pyver" ]; then
  echo "PROBE_FAIL reason=env_unresolved env=$ENV_NAME"; exit 0
fi

echo "PROBE_OK user=$(id -un) host=$(hostname) arch=$arch kernel=$kern cores=$cores mem_gib=$memg env=$ENV_NAME python=$pyver conda=$("$CONDA" --version | awk '{print $2}')"
