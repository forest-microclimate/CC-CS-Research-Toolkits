#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# ============================================================================
# crt-mode.sh — read/set the claude-research-toolkit MASTER SWITCH
# ----------------------------------------------------------------------------
# The toolkit's hooks (F1 adversary gate, verification/review reminders, ambient
# time, timeline logger) all honor a single persistent mode file: ~/.claude/crt_mode
# (override path: $CRT_MODE_FILE). A per-session $CRT_MODE env var overrides the file.
#
# THREE MODES:
#   on       (default) full toolkit — the gate BLOCKS, reminders fire, everything logs.
#   observe  RESEARCH SHADOW ARM — interventions are SILENCED (no blocks, no reminders,
#            no ambient time), but the gate + timeline still LOG, so a row appears for
#            every claim the gate WOULD have blocked (event=block_suppressed, mode=observe).
#            Use to measure the counterfactual: what the toolkit WOULD catch on a run the
#            agent completes UNCORRECTED. NOTE: the adversary still forks, so this arm
#            carries the gate's latency.
#   off      FULLY INERT — no blocks, no reminders, no ambient time, and NO logging at all.
#            Use for (a) a user who wants the toolkit dormant, and (b) the clean research
#            OFF-arm: zero toolkit footprint, zero overhead.
#
# WHY (primary use right now): on-vs-off / on-vs-observe outcome comparison. Flip the mode
# between matched task runs to measure whether the toolkit helps Claude Code CATCH errors
# and converge faster — holding task and model fixed. See:
#   methodology/CRT_MASTER_SWITCH.machine.md   (design of record + A/B protocol)
#
# USAGE:
#   crt-mode.sh            # print the current mode (and where it was resolved from)
#   crt-mode.sh on         # set persistent mode = on
#   crt-mode.sh observe    # set persistent mode = observe
#   crt-mode.sh off        # set persistent mode = off
#   crt-mode.sh --help
# For a ONE-SESSION override without touching the file, set the env var instead:
#   CRT_MODE=off claude          (applies to that invocation only)
# ============================================================================
set -eo pipefail
CMF="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"

usage(){ sed -n '2,44p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

case "${1:-}" in
  ""|--show|--status)
    if [ -n "${CRT_MODE:-}" ]; then
      echo "mode = ${CRT_MODE}   (from \$CRT_MODE env — overrides the file for this session)"
    elif [ -r "$CMF" ]; then
      echo "mode = $(tr -d '[:space:]' < "$CMF")   (from $CMF)"
    else
      echo "mode = on   (default — no \$CRT_MODE env, no $CMF file)"
    fi
    ;;
  on|observe|off)
    mkdir -p "$(dirname "$CMF")"
    printf '%s\n' "$1" > "$CMF"
    echo "mode set to '$1'  ->  $CMF"
    [ -n "${CRT_MODE:-}" ] && echo "WARNING: \$CRT_MODE='${CRT_MODE}' is set in this shell and OVERRIDES the file — unset it for the file to take effect."
    echo "Takes effect on the NEXT Claude Code hook event (usually your next prompt)."
    ;;
  -h|--help) usage 0 ;;
  *) echo "crt-mode: unknown mode '$1' (expected: on | observe | off)" >&2; echo; usage 1 >&2 ;;
esac
