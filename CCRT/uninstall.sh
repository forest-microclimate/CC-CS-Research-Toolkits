#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# uninstall.sh — restore the MOST RECENT pre-toolkit-* backup into ~/.claude/.
# Restores the prior state of the managed items. NOTE: items that did NOT exist before the
# install (e.g. a CLAUDE.md created fresh) are not in the backup, so they are left in place —
# delete those by hand if you want a totally clean removal (the script lists them).
set -euo pipefail
CLAUDE_DIR="${CLAUDE_HOME:-$HOME/.claude}"
BK="$(ls -1d "$CLAUDE_DIR"/backups/pre-toolkit-* 2>/dev/null | sort | tail -1 || true)"
[ -n "$BK" ] || { echo "No pre-toolkit-* backup found under $CLAUDE_DIR/backups/."; exit 1; }

MANAGED=(CLAUDE.md settings.json rules skills agents commands hooks methodology)

echo "Restoring from: $BK"
echo "This will overwrite the current ~/.claude/{$(IFS=,; echo "${MANAGED[*]}")} with their pre-install state."
printf "Proceed? [y/N] "; read -r a; case "$a" in y|Y) ;; *) echo "aborted"; exit 0;; esac

for t in "${MANAGED[@]}"; do
  if [ -e "$BK/$t" ]; then
    rm -rf "$CLAUDE_DIR/$t"; cp -R "$BK/$t" "$CLAUDE_DIR/$t"; echo "  restored $t"
  else
    echo "  (no prior $t in backup — left current in place; remove by hand for a clean uninstall)"
  fi
done
echo "Done. RESTART Claude Code."
