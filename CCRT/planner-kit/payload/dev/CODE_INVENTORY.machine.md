# CODE_INVENTORY.machine.md  (machine-optimized; authoritative-object map for CODE)
# STATUS: CURRENT (2026-08-03). Seeded template — restamp the date when you record your first row. Registry of every script/tool in this project: a child needing code USES an existing entry where it fits, ADAPTS one where close, builds NEW only where neither works — and reports which of the three. The planner appends a row at each collect where a child produced code. STATE doc: supersede a row in place when a script changes owner/interface.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# COLUMNS: path | purpose | interface | provenance | verification

| path | purpose | interface | provenance | verification |
|---|---|---|---|---|
| `dev/tools/stale_move.sh` | move-and-tombstone a retired file into `Stale_Trash/` (mechanizes RULE.stale_trash) | `bash dev/tools/stale_move.sh [--dry-run] [--stub] <file> "<superseded-by>"`; exit 0 ok/dry-run · 1 refuse/err · 2 usage | ships with planner-kit | kit QA trail |
