---
name: ssh-compute-provision
description: Provision a local-network (or any SSH-reachable) Linux box as a Claude Science SSH compute provider — dedicated key-only account + miniforge conda env — then emit the exact Compute-panel connection values. Run this from Claude Code (needs unconfined LAN SSH; a Claude Science kernel is network-sandboxed and cannot reach a LAN box). Use when the user wants to add / set up / wire a Linux machine (their own idle box, a lab server, a rebuilt host) as a remote compute target for Claude Science jobs, or to get unconfined Linux compute (e.g. headless-Chromium rendering that SIGABRTs on macOS). Idempotent + re-runnable for any host and after a host rebuild.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-08-09). Genericized for shipping (no host-specific IP / hostname residue — every example is a placeholder), and the resource budgets are now DETECTED ON THE BOX and computed at provision time instead of hand-figured by the operator.

# ssh-compute-provision — turn a Linux box into a Claude Science SSH compute provider

## When to invoke
WHEN the user wants an SSH-reachable Linux host wired as a Claude Science compute provider — their own LAN box, a lab server, a reinstalled host — OR wants unconfined Linux compute (headless Chromium / a full OS the macOS kernel-sandbox forbids). Runs from **Claude Code** (unconfined LAN SSH). A Claude Science kernel CANNOT run this (sandboxed: no arbitrary LAN SSH).

## Venue + division of labor (do NOT cross these)
- **Claude Code** (this skill's runner): generates the keypair, drives the box over SSH, provisions account+env, probes. Needs a real local shell + LAN SSH.
- **User** (UI, not delegable): pastes the emitted values into Claude Science → Compute → Add SSH host; approves per-job cards. The skill PREPARES the values; the user enters them.
- **Claude Science** (the eventual consumer): after connect, dispatches jobs via `host.compute`. Authoring/validation lives there; provisioning does not.

## Design invariants (why the scripts are shaped as they are)
- **Private key NEVER leaves the client machine.** `ssh-keygen` on the client; only the PUBLIC key crosses to the box. No secret is ever written to a skill file, artifact, repo, or any shared bus. (G6)
- **Dedicated low-priv account** `claude-compute`, created with NO password ⇒ key-only by construction; no global sshd edit, so no lockout risk. (G4)
- **Idempotent + re-runnable.** Every step is create-once / skip-if-present. Safe to re-run after a box rebuild or to add a second host.
- **conda must resolve in a NON-INTERACTIVE LOGIN shell** — that is how Science's `submit_job` invokes `conda run -n <env>` and how the Compute-panel probe lists envs. Ubuntu's `~/.bashrc` returns early for non-interactive shells and `conda init` appends BELOW that guard, so PATH is set in `~/.bash_profile` (read unconditionally by login shells) instead. (G3 — the single most common post-setup failure.)

## Parameters (env vars; override any)
| var | default | meaning |
|---|---|---|
| `HOST` | *(required)* | `<box ip or hostname>` — a LAN address, an mDNS `<name>.local`, or any SSH-resolvable name |
| `ADMIN_USER` | *(required)* | an EXISTING account on the box WITH sudo (used once to provision) |
| `COMPUTE_USER` | `claude-compute` | the dedicated job-running account this creates |
| `KEY_PATH` | `~/.ssh/claude_compute_ed25519` | client-side keypair path (private key stays here) |
| `ENV_NAME` | `claude` | conda env name — this IS the Science `--env` value (no aliasing) |
| `ARCH` | *(auto via `uname -m`)* | `x86_64` \| `aarch64`; drives the miniforge asset |
| `MAX_CONCURRENT_JOBS` | `1` | how many jobs you intend to run at once on this box; the ONLY sizing input you supply — cores and RAM are DETECTED. Drives the thread cap K and the `set_concurrency_limit` value |

## PHASE 0 precondition — sshd must already be listening
`nc -vz $HOST 22` must succeed. If it says **"Connection refused"**, no SSH server is running on the box — and you CANNOT enable it over SSH (there is no SSH yet). Enable it **at the box console** first:
```bash
# Debian/Ubuntu (box console):
sudo apt update && sudo apt install -y openssh-server && sudo systemctl enable --now ssh
# RHEL/Fedora:  sudo dnf install -y openssh-server && sudo systemctl enable --now sshd
```
Distinguish the failure: **refused** = reached-it-nothing-there (no sshd) ⇒ install/enable above. **timeout** = firewall dropping the packet ⇒ open it (`sudo ufw allow OpenSSH` on Ubuntu). `provision_host.sh` runs this precheck and stops early with the exact fix if port 22 is dead.

## Run (from Claude Code)
```bash
cd <toolkit>/skills/ssh-compute-provision   # or ~/.claude/skills/ssh-compute-provision after install
HOST=<box ip or hostname> ADMIN_USER=<you> ./provision_host.sh
# sizing a box you will drive with several jobs at once:
HOST=<box ip or hostname> ADMIN_USER=<you> MAX_CONCURRENT_JOBS=3 ./provision_host.sh
```
It will: reachability-precheck → generate the keypair (once) → detect arch → stage `remote_provision.sh` + the pubkey on the box → run it as root (one sudo password prompt) → create `claude-compute` + install pubkey + miniforge + the `claude` env + wire conda-on-PATH → verify conda resolves in a login shell → probe as the new key-only user → **detect the box's cores + RAM and compute the resource budgets** → print the Compute-panel values and a ready-to-paste `compute_details` block with those budgets already filled in.

**PASS =** the final block prints `PROBE_OK … python=<ver>` and the connection values. That line means the account key-logs in AND the env runs python — the two things a provider needs.

**Sizing is DETECTED, not hand-figured.** `probe.sh` reads cores and RAM **on the box** (that is where the resource lives — never size a remote machine from the client's own numbers) and prints a `PROBE_SIZING` line; `provision_host.sh` turns it into the budgets and shows its arithmetic:
```
== derived resource budgets (detected on the box, not assumed) ==
   detected:  cores=8  ram_gib=16   (read on <box ip or hostname> by probe.sh, as claude-compute)
   K (per-job thread cap) = 6   <- min(cores-2, floor(cores/max_concurrent)) = min(6, 8), floor 1
   MemoryHigh             = 12G  <- detected ram 16G minus a reserve of ram/4 clamped to [2,8] GiB (OS + whatever else shares the box)
   concurrency limit      = 1   <- MAX_CONCURRENT_JOBS; K was sized for exactly this many at once
   basis: detected
```
(that block is a verbatim capture of the script's output for an 8-core / 16 GiB box, not a mock-up —
`basis:` names every departure from "all three numbers came straight off the box", and reads
`detected` when there was none.)
A value the box will not report is never guessed: an undetectable core count degrades to `K=1` (single-threaded — the one budget that is safe on any machine) and an undetectable RAM total leaves `MemoryHigh` UNSET, each announced in the output rather than silently filled.

## After it passes — hand the user the connect step (⚑ USER)
The Compute panel's "Add SSH host" dialog is **alias-based**: it has a single **Host alias** field and resolves connection details via `ssh -G <alias>` from the user's `~/.ssh/config` — there are NO raw host/username/key fields (Advanced only overrides User/Port/IdentityFile, and its shown values are grey PLACEHOLDER examples, not defaults). So the deliverable is an `~/.ssh/config` block, not loose values. If the user has no `~/.ssh/config`, the dialog says so and refuses until an alias exists. `provision_host.sh` now prints the exact block + append one-liner; relay it:
```
# 1. append to ~/.ssh/config on the client Mac (alias -> host/user/key):
printf '%s\n' "Host <alias>
    HostName $HOST
    User claude-compute
    IdentityFile ~/.ssh/claude_compute_ed25519
    IdentitiesOnly yes" >> ~/.ssh/config && chmod 600 ~/.ssh/config
# 2. test alias resolves + key-only login (expect: claude-compute / <box>, NO password):
ssh -o ConnectTimeout=5 <alias> 'whoami; hostname'
# 3. Customize -> Compute -> Add SSH host -> Host alias = <alias> -> leave Advanced EMPTY -> Add.
```
The alias in the dialog MUST match the `Host` line exactly. Then Claude Science auto-probes and lists the `claude` env. (G8)

## The REAL seal — a job dispatched FROM Claude Science (S5 gate)
Provisioning is NOT "done" on the local probe alone (that is design-on-paper). A mechanism counts only once OBSERVED to fire. In a **Claude Science** session, dispatch the sentinel job and confirm it returns:
```python
# repl tool (host.compute is not attached in the python tool)
c = host.compute.create("ssh:<host-label-from-panel>")
job = c.submit_job(
    intent="ssh-compute-provision sentinel — uname+nproc+conda env list",
    command="uname -a; nproc; free -h; conda env list",
    timeout_seconds=120,
)
print(job.job_id)   # end cell; wait_for_notification for compute_done
```
GATE: the `compute_done` payload returns the sentinel (kernel line + `claude` in the env list) ⇒ mark DONE+VALIDATED and append the `### env:` block from `compute_details.template.md` to this provider's `compute_details`.

## Shared box — be capacity-aware (self-govern; the tier is NOT enforced)
If the box also runs other things (music server, occasional long analyses), Claude MAY use most cores when load is light, but MUST NOT oversubscribe cores or drive the box into swap. On a Direct SSH host the `tier` numbers are ADVISORY — this self-governance IS the throttle. Bake into every dispatch:
- **Thread cap in `command`:** set `OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=NUMEXPR_NUM_THREADS=VECLIB_MAXIMUM_THREADS=K`, using the **K `provision_host.sh` computed and printed** for this box (it is also written into the emitted `compute_details` block, so you copy it rather than re-derive it). The rule behind that number: `K = min(cores−2, floor(cores/max_concurrent_jobs))`, floor 1 — the `cores−2` term is the house cap (`preflight-parallel`), leaving ~2 cores for the OS and whatever else the box runs. Without the cap a BLAS/torch job grabs all cores (`os.cpu_count()`), and concurrent jobs thread-storm.
- **Concurrency:** `host.compute.set_concurrency_limit(n)` once per session so parallel/delegated jobs don't collectively oversubscribe; `host.compute.status()` = live count + host ceiling. Use the same `n` you passed as `MAX_CONCURRENT_JOBS` — K was sized for exactly that many simultaneous jobs, so raising `n` afterwards silently oversubscribes.
- **Live load probe before a HEAVY job:** `c.call_command('vmstat 1 2 | tail -1; free -h; nproc', intent='load check')` — read the **idle%** (`vmstat`'s `id` column) and take the SECOND sample: the first row is a since-boot average, not the current state. Judge busy-ness by that instantaneous idle, **never by load average** — `uptime`'s load is a lagging run-queue length that over-states usage and will talk you out of work the box can do. If something is already running, scale K down or wait.
- **Memory (optional, soft):** `sudo systemctl set-property user-<uid>.slice MemoryHigh=<H>G` throttles+reclaims without OOM-killing a long job — `<H>` is the `MemoryHigh` the provisioner derived from the box's detected RAM (RAM minus a reserve of RAM/4, clamped to 2–8 GiB, for the OS and everything else). The emitted `compute_details` block carries the chosen values already filled in.

## Files in this skill
- `provision_host.sh` — CLIENT-side orchestrator (run this). Keypair, arch-detect, stage, drive-as-root, probe, emit values.
- `remote_provision.sh` — BOX-side, runs as root via sudo. Account, authorized_keys, miniforge, env, conda-on-PATH, login-shell verify. Reads the pubkey from `/tmp/cc_pubkey.pub`; embeds no secret.
- `probe.sh` — BOX-side readiness probe, run as the compute user over a key-only connection. Also DETECTS this box's cores + RAM (Linux `nproc` / `/proc/meminfo`, falling back to `sysctl hw.ncpu` / `hw.memsize`, then `getconf`) and computes the budgets from them. Emits one `PROBE_SIZING …` line, then one `PROBE_OK …` / `PROBE_FAIL …` line. Detection lives HERE because this is the machine being sized — the client's own core count is irrelevant to it.
- `compute_details.template.md` — the `### env:` block to append to the provider's `compute_details` after the S5 seal.

## Gotchas (symptom ⇒ fix)
- **auto-probe fails / host unreachable after connect** ⇒ LAN not reachable from where dispatch runs. With the Science daemon Mac-local, Mac→box SSH working ≈ dispatch working; recheck the LAN IP/mDNS name + that sshd is up. (G1)
- **key rejected / still prompts for password** ⇒ pubkey not installed for `claude-compute`. Re-run (idempotent); `ssh -i $KEY_PATH claude-compute@$HOST` should not prompt. (G2)
- **`conda: command not found` in a dispatched job** ⇒ non-login-shell / conda below the `.bashrc` interactive guard. This skill wires `~/.bash_profile`; if a job STILL can't find conda, prefix the command with `source ~/miniforge3/etc/profile.d/conda.sh`. (G3)
- **thread-storm on the box** ⇒ `os.cpu_count()` returns all host cores. Export `OMP/MKL/OPENBLAS/NUMEXPR/VECLIB` thread caps in the job preamble, set to the K the provisioner printed for this box (never to the raw core count). (G7)
- **headless Chromium still fails on the box** ⇒ install `conda install -c conda-forge chromium` (pulls headless deps); render one small `flowchart TD` before declaring the render loop closed. (G5, F8)
- **provisioning as your personal account** ⇒ don't. `ADMIN_USER` is used ONCE to create `claude-compute`; jobs run as the dedicated low-priv account. (G4)
- **"No ~/.ssh/config found" / Add-host dialog has only a Host-alias field** ⇒ this build resolves via `ssh -G <alias>`, not raw fields. Create `~/.ssh/config` with a `Host <alias>` block (HostName/User/IdentityFile/IdentitiesOnly), `chmod 600`, then re-open the dialog and type the alias. Advanced's grey values (`argocd`, `~/.ssh/id_ed25519`) are PLACEHOLDERS — leave empty. (G8) [OBSERVED 2026-07-11 reference run]

## Refs
`compute-env-setup` (the "Direct SSH host" provider shape this implements; the `### env:` template) · `remote-compute-ssh` (how Science submits jobs once connected) · `machine-md` (the authoring discipline for this doc).
