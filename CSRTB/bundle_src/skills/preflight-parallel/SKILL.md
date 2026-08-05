---
name: preflight-parallel
description: Before launching independent compute work (model fits, downloads, CV folds, simulations, sub-agent fan-outs), size concurrency correctly — measure per-unit cost, check real headroom with host.get_local_compute_stats() (instantaneous available cores/RAM, NOT load average), dispatch detached with briefs persisted before launch, default heavy work to compute hosts, run as many useful units as fit, and batch-analyze. Use when about to start two or more independent runs, any long background cell, a host.delegate fan-out, or when tempted to run independent jobs one at a time or in-session.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# preflight-parallel — maximize useful concurrency, never oversubscribe

Idle cores waste wall-clock; oversubscription thrashes. Independent work should run concurrently, then be analyzed in one batch. In Claude Science the launch primitives are `background: true` cells (long local jobs), `host.delegate([...])` (parallel sub-agents), and `host.compute` (remote) — the sizing arithmetic below governs all three.

## When to invoke
About to launch ≥2 independent units of work, any long background cell, or a multi-request `host.delegate` fan-out.

## Procedure
1. **Measure the per-unit cost first.** 1 MCMC chain ≈ 1 core; a multithreaded fit ≈ its `nthreads`; a download/API pull is I/O-bound ≈ ~0 cores; one `host.delegate` sub-agent runs its own kernel (cost lands wherever it executes — local vs remote). Count each cost once (a `bam` with nthreads fanned over furrr counts once).
2. **Compute headroom by arithmetic (primary):** `HEADROOM = CAP − Σ(active units × unit-cost)`, where `CAP = physical_cores − 2` (leave ~2 free for the kernels + daemon).
3. **Confirm with the INSTANTANEOUS metric — `host.get_local_compute_stats()`** (in a `python`/`repl` cell): read `machine.available_gb`, `machine.cores`, and compare `machine.load1` to `machine.host_cores` (load1 ≈ host_cores ⇒ CPU already contended). `kernels.total_rss_gb` shows what your own kernels hold. Size off available cores/RAM, NOT the raw load average — load average is a lagging run-queue length that OVER-states usage. Do this before a LARGE allocation or a wide fan-out, not as a gate on ordinary work.
4. **Launch min(headroom, useful_units) — DETACHED by default.** Local long jobs → `background: true` cells (the result is delivered when done); parallel tracks → one `host.delegate([...])` call (all spawn concurrently host-side; a Python loop over single calls runs serially). Dispatch children `wait=False` with each brief PERSISTED (disk or artifact) BEFORE launch — a session restart or channel timeout must not orphan the compute or lose the brief (the recorded failure: blocking dispatches killed with their session). Give EACH unit a UNIQUE output/artifact path — concurrent jobs sharing one workspace file corrupt each other silently (truncate-mode writes have no locking).
5. **Await completions with `wait_for_notification`** — background cells and delegated children land on the same bus; a long run never blocks the turn. Advance other threads meanwhile; one call can return several completions at once (read the whole list).
6. **Batch-analyze ALL outputs together** in one post-run pass, not one-at-a-time.
7. **Re-check headroom before each new wave** (`host.delegation_stats()` for the sub-agent cap; `get_local_compute_stats()` for cores).

## Success check
Total active ≤ CAP at all times (verified by direct arithmetic AND `get_local_compute_stats`, not load average); each unit has a unique I/O/artifact path; results analyzed in one batch.

## Gotchas (hard-won)
- **The sandbox can lie about the machine (cgroup undercount):** `machine.cores` (your enforceable share) can differ from `machine.host_cores` — size local waves to the SMALLER, and RE-READ the stats at sizing time rather than reusing an earlier number. The recorded failures are waves sized to an assumed or stale core count, and RAM misjudgments that killed kernels mid-fit.
- **Default heavy work OFF the interactive session:** filesystem/DB-heavy inspection → the mac-local path; big fits and parallelizable jobs → `submit_job` / `host.compute` targets. Running work in-session and serially when a compute host could hold it in parallel is the recorded under-use failure — the interactive session is the director's seat, not the workhorse.
- **Local RAM is the tighter bound here.** The default sandbox often reports only a few GB `available_gb` even on a large-RAM host — check `host.get_local_compute_stats()['machine']['available_gb']` before an in-memory allocation and prefer out-of-core / chunked reads or a remote target when a single unit's footprint approaches it. Cores are rarely the first wall; memory is.
- **Julia unit cost is BIMODAL:** a scalar-bound run ≈ 1 core, but a MATRIX-heavy run silently spawns OpenBLAS threads and grabs ALL cores — two can saturate the machine while the process count reads "2". Pin `OPENBLAS_NUM_THREADS=1` (+ `OMP_NUM_THREADS=1`) per parallel Julia launch; `BLAS.get_num_threads` is a CEILING for matrix bursts, not steady load.
- Before N parallel Julia procs, do ONE warm-up load (populate the shared precompile cache) and call the julia BINARY directly — the juliaup shim's self-update check contends on `.juliaup-lock` and can deadlock all subsequent calls.
- R: `bam(nthreads=N)` is a silent NO-OP without OpenMP (always 1 core); real R parallelism is process-based (`mclapply`, cmdstan chains — chains as PROCESSES, not threads; cmdstanr can't fork).
- Measure real load by available cores / summed per-process CPU%, never process count — orphaned sentinel/wrapper subshells read as "alive" at <1% while the real work saturates elsewhere.
- The core + RAM budget is SHARED across every kernel and sub-agent in the session, not per-task — subtract what OTHER concurrent work already committed. A "≤N workers" rule is usually CONDITIONAL on a concurrent big fit; apply it only while that fit runs.
- **Prefer a remote target when a unit needs a GPU, >~10 min CPU, or more RAM than `available_gb`** — `list_compute` / `host.compute`; don't oversubscribe the local sandbox for work that belongs on a cluster.

## Related
temporal-block-cv (fold fan-out); brms-hierarchical-fitting (chains as processes); julia-performance-correctness (OpenBLAS pinning, precompile races). State the measured numbers on any resource claim rather than asserting.
