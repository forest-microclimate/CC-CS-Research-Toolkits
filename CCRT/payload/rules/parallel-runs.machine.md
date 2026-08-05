# parallel-runs.machine.md
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# RULE: maximize USEFUL concurrency for independent runs; batch-analyze; keep total active within the core cap (≤ cores−2, ~2 free).

RULE.parallelize_independent: independent compute / test runs => launch CONCURRENTLY in the background, not serially. Run as MANY useful runs in parallel as fit the headroom, then analyze ALL results in ONE post-run batch (not one-at-a-time).
FACT.unit_cost: measure + record your per-run core cost (it is project-/workload-specific — e.g. 1 Stan/brms chain ≈ 1 core).
CAP: ≤ (total cores − 2) concurrent (leave ~2 free).
RULE.preflight_cpu (MANDATORY before launching ANY new processes):
  - HEADROOM = compute DIRECTLY: `free ≈ (cores − 2) − N_my_runs×unit-cost` (use the verified unit cost; this is the primary check).
  - CONFIRM with the INSTANTANEOUS metric: `top -l1 | grep "CPU usage"` (macOS) / `top -bn1` / `mpstat` (Linux) → use the **idle%** (idle% × total-cores ≈ free cores), or Activity Monitor idle. `pgrep -fl <your-runner> | wc -l` for the run count.
  - Judge "cores busy" by the INSTANTANEOUS metric, NOT `uptime` LOAD AVERAGE — load avg is a lagging run-queue length (counts waiting/transient procs), NOT instantaneous core usage; it OVER-states usage (load 12 ≠ 12 cores busy). Using it caused a false "at the cap".
  - Launch only up to the remaining headroom; keep total active ≤ ~(cores − 2). Re-check before each new wave. XCHECK the headroom number against N_runs×unit-cost before trusting it.
PROC.batch: (1) preflight_cpu => headroom H. (2) launch min(H, useful_runs) in background (`&` / run_in_background). (3) poll/await completions (each notifies). (4) analyze ALL outputs together. (5) repeat for the next wave.
WHY: idle cores waste wall-clock; a long run never blocks — advance other runs in parallel + batch the analysis.
