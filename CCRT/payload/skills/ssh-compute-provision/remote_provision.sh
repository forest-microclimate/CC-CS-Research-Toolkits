#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# remote_provision.sh — BOX-SIDE, runs as ROOT (via `sudo bash` from provision_host.sh).
# Creates a dedicated key-only compute account and a miniforge base env for it. Idempotent.
# Reads the PUBLIC key from /tmp/cc_pubkey.pub (staged by the client). No secrets are embedded.
# ARGS (positional — env does NOT survive sudo, so pass by position, not export):
#   $1 = COMPUTE_USER   $2 = ENV_NAME   $3 = ARCH (x86_64|aarch64)
set -euo pipefail

COMPUTE_USER="${1:?arg1 COMPUTE_USER}"
ENV_NAME="${2:?arg2 ENV_NAME}"
ARCH="${3:?arg3 ARCH}"
PUBKEY_FILE="/tmp/cc_pubkey.pub"
[ -f "$PUBKEY_FILE" ] || { echo "FATAL: $PUBKEY_FILE not staged" >&2; exit 1; }

echo "-- remote_provision as $(id -un): user=$COMPUTE_USER env=$ENV_NAME arch=$ARCH"

# ---- 1. dedicated compute account (create once; never touch its password) ----
if ! id -u "$COMPUTE_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$COMPUTE_USER"
  echo "   created user $COMPUTE_USER"
else
  echo "   user $COMPUTE_USER exists (leaving as-is)"
fi
HOME_DIR="$(getent passwd "$COMPUTE_USER" | cut -d: -f6)"

# ---- 2. authorized_keys = EXACTLY the one compute key (idempotent, key-only) ----
install -d -m 700 -o "$COMPUTE_USER" -g "$COMPUTE_USER" "$HOME_DIR/.ssh"
PUB="$(cat "$PUBKEY_FILE")"
AK="$HOME_DIR/.ssh/authorized_keys"
touch "$AK"
if ! grep -qxF "$PUB" "$AK" 2>/dev/null; then echo "$PUB" >> "$AK"; echo "   installed compute pubkey"; else echo "   pubkey already present"; fi
chmod 600 "$AK"; chown "$COMPUTE_USER:$COMPUTE_USER" "$AK"

# ---- 3. miniforge base env (per-user, no system Python touched; skip if present) ----
CONDA_DIR="$HOME_DIR/miniforge3"
if [ ! -x "$CONDA_DIR/bin/conda" ]; then
  case "$ARCH" in
    x86_64)  MF_ASSET="Miniforge3-Linux-x86_64.sh" ;;
    aarch64) MF_ASSET="Miniforge3-Linux-aarch64.sh" ;;
    *) echo "FATAL: unsupported arch '$ARCH' (want x86_64|aarch64)" >&2; exit 1 ;;
  esac
  MF_URL="https://github.com/conda-forge/miniforge/releases/latest/download/$MF_ASSET"
  TMP_MF="$(mktemp /tmp/miniforge.XXXXXX.sh)"
  echo "   downloading $MF_ASSET ..."
  if command -v curl >/dev/null 2>&1; then curl -fsSL "$MF_URL" -o "$TMP_MF"
  elif command -v wget >/dev/null 2>&1; then wget -qO "$TMP_MF" "$MF_URL"
  else echo "FATAL: need curl or wget on the box" >&2; exit 1; fi
  # mktemp made this root-owned mode 600; the compute user must be able to READ it to run it
  chmod 0644 "$TMP_MF"
  # install AS the compute user so all files under $CONDA_DIR are owned by that account
  sudo -u "$COMPUTE_USER" bash "$TMP_MF" -b -p "$CONDA_DIR"
  rm -f "$TMP_MF"
  echo "   miniforge installed at $CONDA_DIR"
else
  echo "   miniforge already at $CONDA_DIR"
fi

# ---- 4. named env (create once; Claude Science submit_job does `conda run -n $ENV_NAME`) ----
# NB: `sudo -iu` (full login), NOT `sudo -u`/`-H`. Plain -u/-H keep the INVOKING user's cwd
# (/home/<admin>) and XDG_CONFIG_HOME, both of which point into the admin's PRIVATE home (mode 750)
# that $COMPUTE_USER cannot enter. conda then spawns a worker that chdir()s back to that cwd and
# dies with `PermissionError: [Errno 13] ... /home/<admin>` (and a second denial reading the admin's
# ~/.config/conda/.condarc) — surfacing as conda's generic "An unexpected error has occurred", UPSTREAM
# of channels/solver so no -c/--solver flag helps. `-iu` resets cwd to the compute user's home and
# clears the inherited env. (OBSERVED 2026-07-11 on the reference box.)
if ! sudo -iu "$COMPUTE_USER" "$CONDA_DIR/bin/conda" env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  sudo -iu "$COMPUTE_USER" "$CONDA_DIR/bin/conda" create -y -n "$ENV_NAME" python=3.13 pip
  echo "   created conda env '$ENV_NAME' (python 3.13)"
else
  echo "   conda env '$ENV_NAME' exists"
fi

# ---- 5. make conda discoverable in NON-INTERACTIVE LOGIN shells (how Science dispatches jobs) ----
# Claude Science submit_job runs `conda run -n <env>` under a LOGIN shell, and the Compute-panel
# probe lists envs the same way. Ubuntu's ~/.bashrc returns early for NON-interactive shells
# (the `case $- in *i*) ;; *) return;;` guard), and `conda init bash` appends its block BELOW
# that guard — so on dispatch the block never runs and `conda` is not found. Put miniforge on
# PATH via ~/.bash_profile, which login shells read UNCONDITIONALLY, before any interactive guard.
# PRIMARY mechanism: symlink conda into /usr/local/bin, which is on the DEFAULT PATH in every shell
# context — including the non-interactive login shell Science's `conda run -n <env>` uses. `conda run`
# resolves its install root from the symlink target, so this one line alone makes dispatch work,
# independent of any shell-init file. Quoting-free and idempotent (-f overwrites a stale link).
ln -sf "$CONDA_DIR/bin/conda" /usr/local/bin/conda
echo "   symlinked conda -> /usr/local/bin/conda (system-wide, non-interactive-safe)"
# BELT-AND-SUSPENDERS: also expose conda via ~/.bash_profile (login shells read it unconditionally,
# before Ubuntu ~/.bashrc's `case $- in *i*) ;; *) return` interactive guard that hides conda init).
BP="$HOME_DIR/.bash_profile"
MARK="# >>> claude-compute conda path >>>"
if ! grep -qF "$MARK" "$BP" 2>/dev/null; then
  cat >> "$BP" <<PROFILE
$MARK
export PATH="$CONDA_DIR/bin:\$PATH"
[ -f "\$HOME/.bashrc" ] && . "\$HOME/.bashrc"
# <<< claude-compute conda path <<<
PROFILE
  chown "$COMPUTE_USER:$COMPUTE_USER" "$BP"
  echo "   wrote conda-on-PATH to ~/.bash_profile (non-interactive login dispatch)"
else
  echo "   ~/.bash_profile conda path already present"
fi
# also run conda init for interactive humans SSHing in (harmless; appends to ~/.bashrc)
sudo -iu "$COMPUTE_USER" "$CONDA_DIR/bin/conda" init bash >/dev/null 2>&1 || true

# ---- 6. verify conda resolves in a NON-INTERACTIVE LOGIN shell exactly as Science will invoke it ----
if sudo -iu "$COMPUTE_USER" bash -lc "conda run -n '$ENV_NAME' python -c 'import sys; print(sys.version.split()[0])'" >/tmp/cc_verify 2>&1; then
  echo "   VERIFY OK: login-shell conda run resolves (python $(cat /tmp/cc_verify))"
else
  echo "   VERIFY WARN: login-shell conda run did not resolve; see:" >&2; cat /tmp/cc_verify >&2
fi
rm -f /tmp/cc_verify

echo "-- remote_provision OK: $COMPUTE_USER can key-login; env '$ENV_NAME' ready under $CONDA_DIR"
