#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# provision_host.sh — CLIENT-SIDE orchestrator. Runs on the SSH-CLIENT host (the Mac where the
#   Claude Science daemon runs), invoked by Claude Code (which has unconfined LAN SSH).
# WHAT: turn an SSH-reachable Linux box into a Claude Science SSH compute provider — a dedicated
#   key-only `claude-compute` account + a miniforge base env — by driving the box's EXISTING
#   admin account over SSH. Idempotent: safe to re-run, and safe to re-run after a box rebuild.
# PRIVATE KEY stays on THIS machine; only the PUBLIC key crosses to the box (G6 key-handling).
# PHASE 0 PRECOND: sshd must already be listening on the box (`nc -vz <host> 22` succeeds). If
#   not, enable it AT THE BOX CONSOLE first (cannot be done over SSH — there is no SSH yet):
#     sudo apt install -y openssh-server && sudo systemctl enable --now ssh   # Debian/Ubuntu
# VENUE: run from Claude Code. A Claude Science kernel is network-sandboxed and cannot LAN-SSH.
set -euo pipefail

# ---- params (override via env) ----
HOST="${HOST:?set HOST=<box ip or hostname> — a LAN address, an mDNS <name>.local, or any SSH-resolvable name}"
ADMIN_USER="${ADMIN_USER:?set ADMIN_USER=<existing account WITH sudo on the box>}"
COMPUTE_USER="${COMPUTE_USER:-claude-compute}"
KEY_PATH="${KEY_PATH:-$HOME/.ssh/claude_compute_ed25519}"
ENV_NAME="${ENV_NAME:-claude}"
# The ONLY sizing input a human supplies. Cores and RAM are DETECTED on the box (probe.sh) —
# never asked for, never taken from this client machine, which may be nothing like the target.
MAX_CONCURRENT_JOBS="${MAX_CONCURRENT_JOBS:-1}"
case "$MAX_CONCURRENT_JOBS" in
  ''|*[!0-9]*|0) echo "   note: MAX_CONCURRENT_JOBS='$MAX_CONCURRENT_JOBS' is not a positive integer — using 1"; MAX_CONCURRENT_JOBS=1 ;;
esac
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

echo "== ssh-compute-provision =="
echo "   host=$HOST admin=$ADMIN_USER compute_user=$COMPUTE_USER env=$ENV_NAME key=$KEY_PATH"
echo "   max_concurrent_jobs=$MAX_CONCURRENT_JOBS (sizing input; cores+RAM are detected on the box)"

# ---- phase-0 reachability precheck (fail early with the fix, not a cryptic ssh hang) ----
if command -v nc >/dev/null 2>&1 && ! nc -z -G 5 "$HOST" 22 2>/dev/null; then
  echo "FATAL: nothing listening on $HOST:22. Enable sshd AT THE BOX CONSOLE first:" >&2
  echo "   sudo apt install -y openssh-server && sudo systemctl enable --now ssh" >&2
  exit 1
fi

# ---- one authenticated SSH connection, reused (admin password entered once) ----
CM_SOCK="$(mktemp -u "${TMPDIR:-/tmp}/cc_cm.XXXXXX")"
SSH=(ssh -o ControlMaster=auto -o ControlPath="$CM_SOCK" -o ControlPersist=120 -o ConnectTimeout=10)
SCP=(scp -o ControlPath="$CM_SOCK")
# PROBE_OUT is created later; `:-` keeps the trap safe under `set -u` if we exit before then,
# and the explicit `return 0` keeps cleanup from ever changing the script's exit status.
cleanup(){ "${SSH[@]}" -O exit "$ADMIN_USER@$HOST" 2>/dev/null || true
           [ -n "${PROBE_OUT:-}" ] && rm -f "$PROBE_OUT"; return 0; }
trap cleanup EXIT

# ---- 1. keypair on the CLIENT (private key never leaves this machine) ----
if [ ! -f "$KEY_PATH" ]; then
  mkdir -p "$(dirname "$KEY_PATH")"; chmod 700 "$(dirname "$KEY_PATH")"
  ssh-keygen -t ed25519 -f "$KEY_PATH" -N "" -C "$COMPUTE_USER@$HOST"
  echo "   generated keypair: $KEY_PATH(.pub)"
else
  echo "   reusing existing keypair: $KEY_PATH"
fi

# ---- 2. detect arch (drives the miniforge asset: x86_64 | aarch64) ----
ARCH="${ARCH:-$("${SSH[@]}" "$ADMIN_USER@$HOST" uname -m)}"
echo "   box arch: $ARCH"

# ---- 3. stage the remote provisioning script + the PUBLIC key on the box ----
"${SCP[@]}" "$SCRIPT_DIR/remote_provision.sh" "$ADMIN_USER@$HOST:/tmp/cc_remote_provision.sh"
"${SCP[@]}" "$KEY_PATH.pub" "$ADMIN_USER@$HOST:/tmp/cc_pubkey.pub"

# ---- 4. run it as root (TTY -t so sudo can prompt; positional args, no env-through-sudo) ----
"${SSH[@]}" -t "$ADMIN_USER@$HOST" \
  "sudo bash /tmp/cc_remote_provision.sh '$COMPUTE_USER' '$ENV_NAME' '$ARCH'; rc=\$?; rm -f /tmp/cc_remote_provision.sh /tmp/cc_pubkey.pub; exit \$rc"

# ---- 5. probe as the NEW compute user with the NEW key (proves key-only login works) ----
# ENV_NAME + MAX_CONCURRENT_JOBS are set on the CLIENT; SSH does not forward env vars, so pass
# them in the remote command string (single-quoted) rather than relying on -o SendEnv. bash -s
# reads probe.sh from stdin. Output is tee'd so the operator still sees it live AND we can parse
# the sizing line the box computed from its OWN cores/RAM.
echo "== probe (as $COMPUTE_USER, key-only, fresh connection) =="
PROBE_OUT="$(mktemp "${TMPDIR:-/tmp}/cc_probe.XXXXXX")"
ssh -i "$KEY_PATH" -o IdentitiesOnly=yes -o ConnectTimeout=10 "$COMPUTE_USER@$HOST" \
  "ENV_NAME='$ENV_NAME' MAX_CONCURRENT_JOBS='$MAX_CONCURRENT_JOBS' bash -s" < "$SCRIPT_DIR/probe.sh" \
  | tee "$PROBE_OUT"

# ---- 6. resource budgets, read back from what the BOX detected about ITSELF ----
# probe.sh does the detection + arithmetic on the target (that is where the cores and RAM are);
# this side only parses, shows the working, and pastes the numbers into the emitted block.
SZ="$(grep '^PROBE_SIZING ' "$PROBE_OUT" | tail -n 1 || true)"
szf(){ printf '%s\n' "${SZ:-}" | tr ' ' '\n' | awk -F= -v k="$1" '$1==k{print $2; exit}'; }
DET_CORES="$(szf cores)"; DET_MEM="$(szf mem_gib)"; MAXC="$(szf max_concurrent)"
K="$(szf threads_k)"; MEMHIGH="$(szf mem_high_gib)"; BASIS="$(szf basis)"
if [ -z "${K:-}" ]; then      # no sizing line came back (old probe.sh, or a truncated connection)
  DET_CORES='?'; DET_MEM='?'; MAXC="$MAX_CONCURRENT_JOBS"; K=1; MEMHIGH='unset'
  BASIS='no_PROBE_SIZING_line_returned,K_defaults_to_1'
fi
case "$MAXC" in ''|*[!0-9]*|0) MAXC=1 ;; esac      # guards the display arithmetic below

echo
echo "== derived resource budgets (detected on the box, not assumed) =="
echo "   detected:  cores=$DET_CORES  ram_gib=$DET_MEM   (read on $HOST by probe.sh, as $COMPUTE_USER)"
case "$DET_CORES" in
  ''|*[!0-9]*) echo "   K (per-job thread cap) = $K   <- cores UNDETECTED on this box; using the conservative default (single-threaded)" ;;
  *)           echo "   K (per-job thread cap) = $K   <- min(cores-2, floor(cores/max_concurrent)) = min($(( DET_CORES - 2 )), $(( DET_CORES / MAXC ))), floor 1" ;;
esac
case "$DET_MEM" in
  ''|*[!0-9]*) echo "   MemoryHigh             = (none) <- RAM UNDETECTED on this box; no ceiling invented — set one by hand if you want a soft cap" ;;
  *)           echo "   MemoryHigh             = ${MEMHIGH}G  <- detected ram ${DET_MEM}G minus a reserve of ram/4 clamped to [2,8] GiB (OS + whatever else shares the box)" ;;
esac
echo "   concurrency limit      = $MAXC   <- MAX_CONCURRENT_JOBS; K was sized for exactly this many at once"
echo "   basis: $BASIS"

THREAD_ENV="OMP_NUM_THREADS=$K MKL_NUM_THREADS=$K OPENBLAS_NUM_THREADS=$K NUMEXPR_NUM_THREADS=$K VECLIB_MAXIMUM_THREADS=$K"
if [ "$MEMHIGH" = 'unset' ]; then
  MEM_LINE="memory: RAM was not detectable on this box, so no MemoryHigh is proposed. Size each job by hand."
else
  MEM_LINE="memory: soft ceiling (throttles + reclaims, never OOM-kills a long job):
  \`sudo systemctl set-property user-\$(id -u $COMPUTE_USER).slice MemoryHigh=${MEMHIGH}G\`"
fi

# The Compute panel's "Add SSH host" dialog resolves connection details from ~/.ssh/config
# (it shows a Host-ALIAS field, not raw host/user/key fields — it runs `ssh -G <alias>`).
# So the deliverable is an ~/.ssh/config block, not loose values. Emit a ready-to-paste block
# and the one-liner to append it. ALIAS defaults to a slug of the hostname; override with ALIAS=.
ALIAS="${ALIAS:-$(echo "$HOST" | tr '.' '-')}"
CFG_BLOCK="Host $ALIAS
    HostName $HOST
    User $COMPUTE_USER
    IdentityFile $KEY_PATH
    IdentitiesOnly yes"
cat <<EOF

== DONE — add this host to Claude Science ==
This build's Compute panel resolves SSH hosts via ~/.ssh/config aliases (Host-alias field,
not raw host/user/key). Append this block to ~/.ssh/config on THIS Mac:

$CFG_BLOCK

  Run:   printf '%s\n' "$CFG_BLOCK" >> ~/.ssh/config && chmod 600 ~/.ssh/config
  Test:  ssh -o ConnectTimeout=5 $ALIAS 'whoami; hostname'   # expect: $COMPUTE_USER / <box>, no password
  Then:  Customize -> Compute -> Add SSH host -> Host alias = $ALIAS -> leave Advanced empty -> Add.

The private key $KEY_PATH stays on THIS machine (never copied). After the panel auto-probe
lists the '$ENV_NAME' env, a Claude Science session dispatches a probe job via host.compute to
seal validation (S5 gate).
EOF

# ---- 8. the load-management block, already filled in with THIS box's numbers ----
# compute_details.template.md documents the shape; the operator pastes what is printed here
# rather than re-deriving K and H by hand.
cat <<EOF
== compute_details '### load management' block for this provider (paste after the S5 seal) ==

### load management  — SHARED BOX: be capacity-aware, self-govern, do not oversubscribe
detected: cores=$DET_CORES, ram_gib=$DET_MEM (read on the box $(date +%Y-%m-%d)); basis=$BASIS
core_budget: set ALL of $THREAD_ENV
  in every job \`command\`. K=$K = min(cores-2, floor(cores/max_concurrent)), floor 1. Without the
  cap a NumPy/BLAS/torch job reads os.cpu_count() = ALL $DET_CORES cores and, with any concurrency,
  thread-storms.
concurrency: \`host.compute.set_concurrency_limit($MAXC)\` once per session. K above was sized for
  exactly $MAXC simultaneous job(s) — raising the limit later silently oversubscribes.
$MEM_LINE
live_probe: before a HEAVY dispatch, \`c.call_command('vmstat 1 2 | tail -1; free -h; nproc',
  intent='load check')\` and read the idle% from the SECOND sample (the first row is a since-boot
  average). Judge busy-ness by that instantaneous idle, never by load average. If something is
  already running, scale K down or wait.
scratch: <path owned by $COMPUTE_USER, on the disk with the most free space>
EOF
