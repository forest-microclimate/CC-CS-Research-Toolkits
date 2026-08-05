# CRT_MASTER_SWITCH.machine.md
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# The claude-research-toolkit on/observe/off master switch — design of record + A/B protocol.
# Dual-audience: machine-optimized body (hooks + agents parse+act on this) + a HUMAN QUICKSTART
# section up top (the user reads that to turn the toolkit on/off). Per DOC_STYLE: committed to
# machine style below the quickstart.

# ============================================================================
# HUMAN QUICKSTART (read this if you just want to turn the toolkit on or off)
# ============================================================================
# The toolkit has ONE switch with THREE settings. Set it with the helper:
#
#     ~/.claude/lib/crt-mode.sh            # show current setting
#     ~/.claude/lib/crt-mode.sh on         # full toolkit (DEFAULT)
#     ~/.claude/lib/crt-mode.sh observe    # silent research shadow mode
#     ~/.claude/lib/crt-mode.sh off        # toolkit dormant, nothing runs
#
#   on       Everything works normally: the adversary gate BLOCKS shaky claims, the
#            verification/review reminders fire, ambient-time is injected, all events log.
#   observe  The toolkit goes SILENT to the agent — no blocks, no reminders, no time line —
#            but it still WATCHES and records what it WOULD have blocked. Use this to see
#            what the toolkit catches WITHOUT it changing the agent's behaviour.
#   off      The toolkit does NOTHING at all — no interventions, no logging, no overhead.
#            Use this to run Claude Code as if the toolkit were not installed.
#
#   The change takes effect on your NEXT prompt. No restart needed (hooks read the setting
#   each time they fire). To change it for just ONE session without saving, prefix the launch:
#       CRT_MODE=off claude
#
#   WHY THREE settings (not just on/off): the PRIMARY use right now is RESEARCH — comparing
#   how Claude Code performs WITH the toolkit vs WITHOUT it, on the same task. "off" gives a
#   clean no-toolkit run; "observe" gives a no-toolkit run that STILL records what the toolkit
#   would have caught (so you can count missed catches on a run the agent completed its own way).
#   See the A/B PROTOCOL below.
# ============================================================================

# ---- MACHINE BODY ----------------------------------------------------------

DEF.master_switch: single tri-state mode controlling EVERY claude-research-toolkit hook.
  values = { on (default) | observe | off }.

RESOLUTION.order (first match wins, every hook uses the SAME logic):
  1. $CRT_MODE            env var        (per-session; wins — ideal for A/B, flip per launch)
  2. $CRT_MODE_FILE file, else ~/.claude/crt_mode   (one word; persistent user/researcher setting)
  3. "on"                                (default; an UNRECOGNIZED value ALSO => on, fail-safe:
                                          stay protective rather than silently unprotected)

MODE.semantics:
  on:
    - gate: adjudicate + BLOCK + log(event=block|pass|fired, mode=on)
    - reminders (post-edit-review, pre-complete-verification): FIRE
    - ambient_time: INJECT the time line
    - timeline-logger: LOG (mode=on)
  observe:   # RESEARCH SHADOW ARM — measures the counterfactual
    - gate: adjudicate + LOG what it WOULD do, but DO NOT block
            (event=block_suppressed on a would-block; pass otherwise; mode=observe)
            (WHY still forks the adversary: we need its verdict to record the catch.
             COST: this arm carries the gate's full latency — it is NOT a zero-overhead arm.)
    - reminders: SILENT (they are interventions; the agent must run UNPROMPTED)
    - ambient_time: SILENT
    - timeline-logger: LOG (mode=observe)  # observer, not intervention => keeps logging
  off:       # FULLY INERT — user-disable AND clean research OFF-arm
    - gate: exit immediately — NO fork, NO log, NO intervention
    - reminders: SILENT
    - ambient_time: SILENT
    - timeline-logger: NO log (zero toolkit footprint)

INVARIANT.intervention_vs_observer:
  - INTERVENTION hooks (gate-block, both reminders, ambient_time) act ONLY in `on`.
    (WHY: an intervention CHANGES the agent's behaviour; observe/off must not, or the
     research arm is contaminated.)
  - OBSERVER logging (gate telemetry, timeline) runs in `on` AND `observe`, silent in `off`.
    (WHY: observe must still MEASURE; off must leave no trace.)

ROW.mode_field: every JSONL row (adversary-gate.jsonl, timeline.jsonl) carries "mode":"on|observe".
  => a mixed log SELF-PARTITIONS by arm (parallel to build_id). off writes no rows, so never appears.

EVENT.block_suppressed: NEW gate event, observe-arm only. Means "adversary returned BLOCK but the
  mode suppressed the interposition; the agent was allowed to emit uncorrected". Distinct from
  `block` (real interposition, on-arm) so the reader never conflates a shadow catch with a live one.

READER.gate-log-report.py:
  - counts block_suppressed; pooled CATCH RATE = (block + block_suppressed)/judged.
  - `--by-mode` => on-vs-observe split with per-arm catch-rate (the core A/B readout).
  - `--patterns` includes suppressed patterns (both arms' catches).

# ---- A/B PROTOCOL (the resolution/convergence experiment) -------------------
# CONTEXT: the beta interrupted-time-series showed the native error-GENERATION rate is FLAT
#   (~46-50%, the control). The open question is RESOLUTION: does the toolkit help Claude CATCH
#   errors + converge on the right solution faster (less time down wrong paths)? An observational
#   n=1 arc cannot answer it (confounded by arc-length + task-type + no control). This switch is
#   the missing control arm.

PROTOCOL.matched_task_on_off:
  GOAL: isolate the toolkit as the ONLY variable — hold task + model + day fixed.
  DESIGN: pick comparable sub-tasks; run some WITH `off` (or `observe`) and some WITH `on`;
          OR run the same task class twice, flipping only the mode.
  PREFER $CRT_MODE env per-launch (unambiguous per-run arm) over editing the file mid-experiment.
  ARMS:
    on       = full toolkit (interventions live).
    off      = clean control: no toolkit, no overhead, no log. Measure the agent's OWN trajectory.
    observe  = instrumented control: agent behaves as un-toolkit'd, but the gate RECORDS every
               would-block. Use when you want to COUNT missed catches on the control run itself.
  PREREGISTER metrics (do not read off post-hoc):
    1. time-to-resolution per error   (error-introduced ts -> verified-fixed ts; from timeline.jsonl epoch_ms)
    2. wrong-path cost                (tool-calls + minutes on a hypothesis later abandoned = "wasted work")
    3. relapse rate                   (a corrected error re-appears later same session = gravity-well recurrence)
    4. convergence                    (turns/time from task-start to final accepted solution, on vs off)
  READOUT: gate-log-report.py --by-mode  +  timeline-report.py; compare on vs off/observe on 1-4.
  CONFOUND CONTROL: same task class + same model + same session-day across arms removes the
    arc-length / task-type / no-control confounds that blocked the observational beta.

CAVEAT.observe_latency: observe still forks the adversary (~seconds-to-60s latency per firing).
  If the experiment must NOT perturb timing, use `off` for the control and accept that you lose
  the shadow catch-count. observe trades a latency perturbation for a measured counterfactual.

FILES.touched (this feature):
  payload/hooks/stop-adversary-gate.sh        (§0a switch, block_suppressed, mode field)
  payload/hooks/post-edit-review.sh           (switch: on-only)
  payload/hooks/pre-complete-verification.sh  (switch: on-only)
  payload/hooks/ambient_time.py               (crt_mode(): on-only)
  payload/hooks/timeline-logger.sh            (switch: off-silent, mode field)
  lib/crt-mode.sh                             (the show/set helper)
  lib/gate-log-report.py                      (block_suppressed, --by-mode, mode summary)
  install.sh                                  (copies lib/crt-mode.sh)
