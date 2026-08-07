#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# plan-state-inject.sh — SessionStart hook (matchers: startup, resume, compact). G5 (Z8).
# STATUS: CURRENT (2026-08-07). Ships in planner-kit v1.7.
#
# WHAT: make plan state survive session boundaries for ~100 tokens per boundary EVENT
#   (startup / resume / post-compaction) instead of a per-prompt tax. Reads
#   plans/PLAN_LEDGER.machine.md under the project dir (CLAUDE_PROJECT_DIR, else cwd);
#   when a table row contains "| ACTIVE" it emits TWO lines to stdout (the SessionStart
#   context channel): the active plan's name (truncated) + its snapshot path, then the
#   one-line resume protocol including the fable verified-launch reminder. Multiple
#   ACTIVE rows => the LAST one is named, plus "(+N more active)".
#
# CONTRACT (bash-hook-contract):
#   IN  : stdin is drained and IGNORED (the ledger + env are the only inputs).
#   OUT : STDOUT is EITHER empty (no ledger / no ACTIVE row / any parse doubt) OR at
#         most ~120 tokens of plan-state context. Nothing else, ever.
#   EXIT: 0 ALWAYS. Any internal error => silent fail-open. NO writes, ever — no log
#         file, no state: a session-boundary hook must be a pure reader.
#   BLAST: read-only. Reads the ledger file only.
#
# SWITCH: PLANNER_KIT_HOOKS=off silences this hook (kit hook convention).
set -eo pipefail   # NOT set -u — maybe-unset vars are guarded with ${x:-}

[ "${PLANNER_KIT_HOOKS:-on}" != "on" ] && exit 0
cat >/dev/null 2>&1 || true   # drain stdin; content unused

command -v python3 >/dev/null 2>&1 || exit 0
_ledger="${CLAUDE_PROJECT_DIR:-$PWD}/plans/PLAN_LEDGER.machine.md"
[ -f "$_ledger" ] || exit 0

set +e
python3 - "$_ledger" <<'PYEOF'
import re, sys

try:
    with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()

    active = []
    for ln in lines:
        s = ln.strip()
        if not s.startswith("|") or "| ACTIVE" not in s:
            continue
        cells = [c.strip() for c in s.split("|")]
        # cells[0] is the empty pre-pipe slot; plan=1, status=2, snapshot=3.
        if len(cells) < 4 or not cells[1]:
            continue
        active.append(cells)
    if not active:
        sys.exit(0)

    row = active[-1]
    name = row[1]
    if len(name) > 80:
        name = name[:77].rstrip() + "..."
    snap_cell = row[3]
    m = re.search(r"\S+\.md\b", snap_cell)
    if m:
        snap = m.group(0)
    else:
        parts = snap_cell.split()
        snap = parts[0] if parts else "(no snapshot path in the row)"
    more = " (+%d more active)" % (len(active) - 1) if len(active) > 1 else ""

    print("[plan-state] ACTIVE: %s → %s%s" % (name, snap, more))
    print("resume: read that file + its ledger row; fable children ⇒ verified-launch "
          "(warmup + fable_watchdog certify ~call 5).")
except SystemExit:
    raise
except Exception:
    pass   # malformed ledger => silent fail-open: no output beats wrong output
PYEOF
exit 0
