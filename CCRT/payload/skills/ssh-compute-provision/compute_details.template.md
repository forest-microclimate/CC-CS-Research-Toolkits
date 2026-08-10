<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# compute_details `### env:` block — paste after the S5 seal

AFTER a probe job dispatched FROM Claude Science returns the sentinel (S5 gate in SKILL.md),
append the block below to THIS provider's durable doc:
`compute_details({provider:"ssh:<label>", mode:"append", text:"<block>"})`.
Fill the <angle> fields from the probe output. This is what lets the NEXT Science session
dispatch here without re-probing.

```
### env: claude
how: conda env "claude" on host <HOST>, run as user claude-compute
     (submit_job does `conda run -n claude ...` under a login shell)
tier: {cpus: <cores= from PROBE_SIZING>, mem_gib: <mem_gib= from PROBE_SIZING>, gpus: <0 or count>}   # ADVISORY on a Direct SSH host — NOT enforced
arch: <x86_64|aarch64>   kernel: <uname -r>
weights: n/a (general compute; add a CACHE_VAR=path line per tool that needs one)
validated: <date> (S5 sentinel returned from Science: uname+nproc+conda env list)
gotcha: conda resolves via ~/.bash_profile PATH (Ubuntu .bashrc returns early for
        non-interactive login shells); if a job can't find conda, prefix with
        `source ~/miniforge3/etc/profile.d/conda.sh`

### load management  — SHARED BOX: be capacity-aware, self-govern, do not oversubscribe
### ⚑ DO NOT HAND-FILL THIS BLOCK. `provision_host.sh` PRINTS it with K, MemoryHigh and the
###   detected cores/RAM already substituted — paste what it printed. The shape below is the
###   reference (what each field means and where its number came from), not a worksheet.
shared_with: <e.g. a light media server + occasional long analyses>. Load is light, so Claude
  MAY use most cores — but on a Direct SSH host the `tier` numbers are ADVISORY (nothing enforces
  them), so this self-governance IS the throttle, not a nicety. Two rules: never spawn more threads
  than cores, never drive the box into swap.
detected: cores=<detected on the box>, ram_gib=<detected on the box>; basis=<how each number was
  obtained, incl. any value that could NOT be detected and what was used instead>
core_budget: set ALL of OMP_NUM_THREADS, MKL_NUM_THREADS, OPENBLAS_NUM_THREADS, NUMEXPR_NUM_THREADS,
  VECLIB_MAXIMUM_THREADS = <the K the provisioner computed> in every job `command`. A NumPy/BLAS/torch
  job otherwise reads os.cpu_count() = ALL cores and, with any concurrency, thread-storms (cores × jobs
  threads fighting for the same cores). THE RULE BEHIND K: min(cores-2, floor(cores/max_concurrent_jobs)),
  floor 1 — `cores-2` is the house cap, leaving ~2 cores for the OS and whatever else the box runs.
  Cores undetectable ⇒ K=1 (single-threaded), announced rather than guessed.
concurrency: `host.compute.set_concurrency_limit(<the max_concurrent_jobs K was sized for>)` once per
  session so parallel jobs / delegated sub-agents don't collectively oversubscribe; `host.compute.status()`
  shows live count + host ceiling. Raising this above the value K was sized for silently oversubscribes.
memory: size each job to fit in FREE RAM with headroom for everything else the box runs. Optional SOFT
  backstop (throttles + reclaims, never OOM-kills a long job — unlike a hard MemoryMax):
  `sudo systemctl set-property user-<uid>.slice MemoryHigh=<H>G`, where H = detected RAM minus a
  reserve of RAM/4 clamped to [2,8] GiB. RAM undetectable ⇒ no ceiling is proposed at all.
live_probe: before a HEAVY dispatch, `c.call_command('vmstat 1 2 | tail -1; free -h; nproc',
  intent='load check')` and read the idle% (`vmstat`'s `id` column) from the SECOND sample — the first
  row is a since-boot average. Judge busy-ness by that instantaneous idle, NEVER by load average
  (`uptime`'s figure is a lagging run-queue length that over-states usage). If something is already
  hammering the box, scale K down or wait.
scratch: <path owned by claude-compute, on the disk with the most free space> — job workdirs land here.
```

## Notes for filling it
- `<label>` = whatever name the user gave the host in the Compute panel; it becomes the
  `host.compute.create("ssh:<label>")` argument.
- `tier.cpus` / `tier.mem_gib` come from the probe's `PROBE_SIZING` line (detected ON the box); no
  hand-reading of `nproc` / `free -h`, and no substituting the client machine's numbers.
- If you later `conda install`/`pip install` packages into the `claude` env for a specific
  workload, add a one-line `packages:` note here so the next session knows what's present.
- If you add GPU tooling, record `sm_range:` (the CUDA arch) so jobs route to compatible hardware.
