---
name: preflight-parallel
description: Before launching independent compute runs (model fits, downloads, CV folds, simulations), compute CPU headroom correctly (direct core arithmetic + instantaneous idle%, not load average) and launch as many useful jobs as fit, backgrounded, then batch-analyze — keeping cores within headroom and running independent work in parallel. Use when about to start two or more independent runs, any long background job, or when tempted to run independent jobs one at a time.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-11).

# preflight-parallel — maximize useful concurrency, never oversubscribe

Idle cores waste wall-clock; oversubscription thrashes. Independent runs should go concurrently, then be analyzed in one batch.

## When to invoke
About to launch ≥2 independent runs, or any long detached job.

## Procedure
1. **Measure the per-run unit cost first.** e.g. 1 MCMC chain ≈ 1 core; a multithreaded fit ≈ its `nthreads`; a download/API pull is I/O-bound ≈ ~0 cores. Count each cost once (a bam with nthreads fanned over furrr counts once).
2. **Compute headroom by arithmetic (primary):** `HEADROOM = CAP − Σ(active runs × unit-cost)`, where `CAP = physical_cores − 2` (leave ~2 free).
3. **Confirm with the INSTANTANEOUS metric:** `top -l1 | grep "CPU usage"` (Linux: `nproc` / `top -bn1`) → idle% (idle% × ncores ≈ free cores). Read "cores busy" from that idle%, not load average — load average is a lagging run-queue length that OVER-states usage.
4. **Launch min(headroom, useful_runs) in the BACKGROUND.** Give EACH run a UNIQUE output/log path — concurrent jobs sharing an I/O file corrupt each other silently.
5. **Await completions** (each notifies) — a long run never blocks; advance others meanwhile.
6. **Batch-analyze ALL outputs together** in one post-run pass, not one-at-a-time.
7. **Re-check headroom before each new wave.**

## Success check
Total active ≤ CAP at all times (verified by direct arithmetic AND idle%, not load average); each run has a unique I/O path; results analyzed in one batch.

## Gotchas (hard-won)
- Julia unit cost is BIMODAL: a scalar-bound run ≈ 1 core, but a MATRIX-heavy run silently spawns OpenBLAS threads and grabs ALL cores — two can saturate your machine's core count while the process count reads "2". Pin `OPENBLAS_NUM_THREADS=1` (+ `OMP_NUM_THREADS=1`) per parallel Julia launch; `BLAS.get_num_threads` is a CEILING for matrix bursts, not steady load.
- Before N parallel Julia procs, do ONE warm-up load (populate the shared precompile cache) and call the julia BINARY directly — the juliaup shim's self-update check contends on `.juliaup-lock` and can deadlock all subsequent calls.
- R: `bam(nthreads=N)` is a silent NO-OP without OpenMP (always 1 core); real R parallelism is process-based (`mclapply`, cmdstan chains).
- Measure real load by SUMMED per-process CPU%, never process count — orphaned sentinel/wrapper subshells read as "alive" at <1% while the real work saturates elsewhere (and killing a sentinel can orphan its child).
- The core budget is SHARED across concurrent tasks, not per-task: subtract cores already committed by OTHER sessions. Probe with `ps -A -o comm=` (macOS `pgrep -x R` misses `.../exec/R`); cmdstan chains aren't R procs so a probe can't see them — cap manually alongside a Stan fit. A "≤N workers" rule is usually CONDITIONAL on a concurrent big fit — apply it only when that fit is running.

## Related
temporal-block-cv (fold fan-out); background-run sentinel (silence ≠ success); verify-or-hedge any resource claim — state the numbers.
