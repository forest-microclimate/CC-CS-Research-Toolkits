# STRUCTURE_RULES.md — the lazy-materialized project-structure standard (machine-only; primary reader = the coordinating agent)
# STATUS: CURRENT (2026-08-05). AUTHORITATIVE per-folder contract: PURPOSE + WHEN⇒CREATE trigger + attached RULE + on-demand materialization protocol. Every relative path resolves against the project root that holds this file.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# NAME (kit v1.5, 2026-08-05): this file installs as `STRUCTURE_RULES.md`, renamed from `STRUCTURE_RULES.machine.md` on the user's explicit ask. The name DEVIATES from the house `*.machine.md` convention (doc-style: a machine-only doc carries the machine suffix); the CONTENT is unchanged and stays machine-STYLE — terse WHEN⇒DO atoms for a coordinating agent, not human prose. Only the NAME moved. An installer run over a root that still carries the old name RENAMES it in place (content preserved); a root carrying BOTH names is refused loudly rather than resolved by guess.

# ─── STRUCTURE MAP (canonical tree) ───
```
<project-root>/
  CLAUDE.md                    front door (ROOT; `.claude/CLAUDE.md` is a pointer stub to here)
  STRUCTURE_RULES.md           THIS doc — the per-folder contract
  .claude/                     settings.json / agents / skills / rules / agent-memory (settings.local.json is auto-ignored under git)
  src/                         primary / deliverable code
  projects/                    OPTIONAL: a sibling/parent project tree brought INSIDE this root for in-scope integration work; create only when such work exists
  dev/                         agent-exchange layer: briefs/ · tools/ (instrument code subagents produce, e.g. stale_move.sh) · benchmarks · reports · the 3 ledgers (CODE_INVENTORY · EFFICACY_LEDGER · REGISTER_DELTA)
  documents/<doc>/{machine-md,human-md,pdf}/   human-facing docs ONLY, one triplet per doc, the machine root authoritative; machine-only docs (rules/briefs/ledgers) are NOT triplets — they stay in .claude/ or dev/
  data-outputs/{source-immutable,intermediate,products}/   lifecycle tiers: source-immutable is never mutated (transforms derive NEW files); products carry provenance + env/seed
  plots-figures-tables/        rendered figure / table products, provenance-tagged
  plans/{current_active,for_later_resume,finished}/ + PLAN_LEDGER.machine.md   folder = status (RULE.plan_preservation)
  sandbox/                     scratch quarantine; NEVER a source of record
  backups/                     dated zips — belt-and-suspenders undo (keep even when the project uses git)
  Stale_Trash/                 retired items — NEVER read as context; see RULE.stale_trash for the move-AND-tombstone contract
```

# ─── PER-FOLDER CONTRACT (each: PURPOSE · WHEN⇒CREATE · RULE) ───
# A folder is materialized ONLY when its WHEN⇒CREATE trigger fires. Until then its absence is correct, not a defect.
- `.claude/` — PURPOSE: Claude Code config root (settings.json / agents / skills / rules / agent-memory). WHEN⇒CREATE: `.claude/CLAUDE.md` (pointer stub), `.claude/settings.json` and `.claude/hooks/` are installed already; materialize a further subdir the moment you first add an agent/a skill/a planner memory. RULE: commit the whole `.claude/` tree under git where the project uses git; `settings.local.json` is auto-ignored.
- `src/` — PURPOSE: primary / deliverable code. WHEN⇒CREATE: the first source file you author for the deliverable. RULE: none beyond project convention.
- `projects/` — PURPOSE: OPTIONAL import convention — a sibling/parent project tree pulled INSIDE this root for in-scope integration. WHEN⇒CREATE: ONLY when such in-scope integration work exists; never speculatively. RULE.workspace_scope still binds — imported trees are inside the root, so in-scope; anything still outside the root needs a per-excursion grant.
- `dev/` — PURPOSE: the agent-exchange layer (the durable file channel between planner + workers). WHEN⇒CREATE: the first brief, ledger, instrument script, benchmark, or report. Sub-folders, each on its own first-need: `dev/briefs/` (first persisted child brief — copy `_TEMPLATE.md` from SEEDS; BRIEF CHECKLIST — and `dev/briefs/<ID>/` when a SUB-PLANNER child needs a private area for its own children's briefs + its collect record, the shared ledgers staying the coordinator's), `dev/tools/` (first instrument script — e.g. copy `stale_move.sh` from SEEDS), `dev/reports/` (first report), `dev/benchmark/` (first benchmark). RULE: the 3 ledgers live here (CODE_INVENTORY · EFFICACY_LEDGER · REGISTER_DELTA — copy from SEEDS at first need); code-reuse reads CODE_INVENTORY first.
- `documents/<doc>/{machine-md,human-md,pdf}/` — PURPOSE: human-facing docs, one triplet per doc, machine root authoritative. WHEN⇒CREATE: the first human-facing document. RULE: machine-only docs (rules/briefs/ledgers) are NOT triplets — they stay in `.claude/` or `dev/`.
- `data-outputs/{source-immutable,intermediate,products}/` — PURPOSE: lifecycle-tiered data. WHEN⇒CREATE: the first data input or output; create only the tier you need (a source file ⇒ `source-immutable/`; a derived product ⇒ `products/`). RULE: `source-immutable/` is NEVER mutated — transforms derive NEW files into `intermediate/`/`products/`; `products/` carry provenance + env/seed.
- `plots-figures-tables/` — PURPOSE: rendered figure / table products. WHEN⇒CREATE: the first saved figure or table. RULE: provenance-tag each product (inputs + code + date).
- `plans/{current_active,for_later_resume,finished}/` + `PLAN_LEDGER.machine.md` — PURPOSE: the plan-snapshot store (folder = status). WHEN⇒CREATE: the first time you snapshot the harness plan slot before repurposing it (copy `PLAN_LEDGER.machine.md` from SEEDS). RULE.plan_preservation: snapshot VERBATIM + update the ledger; every folder move (current_active ⇄ for_later_resume ⇄ finished) pairs with a ledger row update.
- `sandbox/` — PURPOSE: scratch quarantine. WHEN⇒CREATE: the first scratch/throwaway file. RULE: NEVER a source of record; gitignored (add `sandbox/` to `.gitignore` where git is used).
- `backups/` — PURPOSE: dated-zip undo layer. WHEN⇒CREATE: the first backup-before-bulk-edit (`zip -rq "backups/<name>_pre<change>_$(date +%Y%m%d_%H%M).zip" "<target>"`). RULE: belt-and-suspenders even under git — the ONLY undo where the project uses no VCS; gitignored (dated zips are large binaries).
- `Stale_Trash/` — PURPOSE: retired items, kept for the trail. WHEN⇒CREATE: the first retirement — materialized BY `dev/tools/stale_move.sh` (copy it from SEEDS first). RULE.stale_trash: NEVER read `Stale_Trash/` as context; retire via MOVE-AND-TOMBSTONE (in-band SUPERSEDED tombstone written INTO the file + move + a REGISTER_DELTA row), never move-instead-of-tombstone; deletion is a later, separate, explicit user call.

# ─── MATERIALIZATION PROTOCOL (the mechanical how) ───
# WHEN⇒a rule or task first requires a folder in the STRUCTURE MAP ⇒ materialize it, then obey its RULE:
1. `mkdir -p "<project-root>/<dir>"` — idempotent; safe to call even if a parent already exists. Quote the path (project roots may hold spaces).
2. `.gitkeep` ONLY IF the project uses git AND the dir starts EMPTY (so the empty dir survives the first commit): `: > "<dir>/.gitkeep"`. If the dir is created already non-empty (you are placing a file in it now), SKIP the .gitkeep. Not using git ⇒ no .gitkeep.
3. NEVER pre-create a folder speculatively — create it at the moment of first need, not before.
4. If a folder needs a SEED template (a ledger, a memory, `stale_move.sh`) ⇒ copy it from SEEDS (below) at the same moment.

# ─── SEEDS (machine-local convenience — copy-if-needed at first use, NEVER a hard dependency) ───
# Copy a seed INTO the target ONLY when its folder's WHEN⇒CREATE trigger fires. The kit path below is
# MACHINE-LOCAL and NON-PORTABLE — never propagate it into a doc, and never treat it as authority beyond
# "where the seed templates live":
@@KIT_SEED_PATH@@
# Seed sources (relative to the KIT_PATH recorded on the line above) ⇒ target-relative destination:
#   payload/plans/PLAN_LEDGER.machine.md        ⇒ plans/PLAN_LEDGER.machine.md
#   payload/dev/CODE_INVENTORY.machine.md       ⇒ dev/CODE_INVENTORY.machine.md
#   payload/dev/EFFICACY_LEDGER.machine.md      ⇒ dev/EFFICACY_LEDGER.machine.md
#   payload/dev/REGISTER_DELTA.machine.md       ⇒ dev/REGISTER_DELTA.machine.md
#   payload/dev/briefs/_TEMPLATE.md             ⇒ dev/briefs/_TEMPLATE.md   (the six-element child-brief form)
#   payload/dev/tools/stale_move.sh             ⇒ dev/tools/stale_move.sh   (SCRIPT ⇒ see code-reuse note below)
#   payload/.claude/agent-memory/planner/*.md   ⇒ .claude/agent-memory/planner/   (seed planner memories + MEMORY.md index)
# WHEN⇒COPY: `mkdir -p "<target-parent>" && cp "<KIT_PATH>/payload/<src>" "<target>/<dst>"`. Quote every path.
# WHEN you copy a SCRIPT (e.g. stale_move.sh) ⇒ append a `dev/CODE_INVENTORY.machine.md` row for it (RULE.code_reuse: the inventory registers every script; a copied instrument is registered like a built one).
# IF the recorded KIT_PATH is UNREACHABLE (kit moved/deleted, or you are on a different machine) ⇒ do NOT block:
#   author an equivalent from the SPEC in the root CLAUDE.md rules — each ledger's format and stale_move.sh's
#   full contract are specified there (RULE.stale_trash, the LEDGERS convention).

# ─── INVARIANT ───
# A folder's ABSENCE = "not yet needed", NEVER an error. Materialize on demand (mkdir -p at need), never speculatively.
# This doc is the authoritative per-folder contract; the root CLAUDE.md carries the rules those contracts reference.
