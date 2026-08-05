---
name: capability-audit
description: Audit installed agents/skills for duplication + placement, and RECOMMEND (never auto-act) which to retire or relocate. Invoke WHEN the user has agent/skill "clutter" and wants to decide what to remove (duplicates of each other or of the toolkit) or where a capability belongs (global vs project). Runs on BOTH Claude Code (walks ~/.claude files) and Claude Science (host.agents/host.skills). Retire/relocate is COMMIT-CLASS: copy-then-confirm, reversible, user-gated — the audit flags candidates, it never deletes.
tags: [housekeeping, agents, skills, declutter, portability]
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# capability-audit — declutter + placement advisor

# STATUS: CURRENT (2026-07-12). First doc of this capability. Built per DESIGN_BRIEF_T21 (register T-21).

WHAT: an occasional housekeeping PASS. Inventory every installed agent + skill, classify each by
ownership, cluster overlapping/duplicate capabilities, and emit a RECOMMENDATION of what to retire
(remove from the active load path) or relocate (global↔project). It never mutates on its own: the
audit RECOMMENDS, a COMMIT-CLASS gate + copy-then-confirm makes every action reversible, and the
user (or an explicit list-confirm) commits.

WHY-A-SKILL-NOT-AN-AGENT: this tool's job is to REDUCE agent/skill clutter — shipping it as a new
profile would add to the clutter it exists to cut. It is a bounded procedure (inventory→cluster→
flag→recommend→gated-commit), not a persona. And a skill is the ONE capability type native to BOTH
Claude Code and Claude Science, so one doc serves both surfaces.

# ─── RUNTIME BRANCH (pick the adapter matching where you are) ──────────────────
BRANCH:
- IF `host.skills` / `host.agents` are reachable (you are on CLAUDE SCIENCE, via the repl tool)
  ⇒ run the SCIENCE ADAPTER.
- ELSE IF you have Bash + a `~/.claude/` tree (you are in CLAUDE CODE)
  ⇒ run the CC ADAPTER, driven by `~/.claude/lib/capability-audit.sh`.
The SHARED CORE (audit heuristic) is identical on both; only the ACTION VERBS differ, because the
platforms genuinely differ (CC = files you move; Science = SDK records you delete-with-restore).

# ═══════════════════════════════════════════════════════════════════════════
# SHARED CORE — the audit (identical on both surfaces)
# ═══════════════════════════════════════════════════════════════════════════
STEP.1_inventory: enumerate the full capability set — every agent AND every skill. Compare across
  the UNION {agents ∪ skills}, NOT within-type: an agent can duplicate a skill (real + common).
STEP.2_classify_ownership: tag each item so only USER-OWNED items are eligible to retire/relocate.
  Toolkit-authored (install-managed) and third-party items are NEVER touched here.
STEP.3_cluster_overlap (PROC.dedup, layered cheap-first — never a brute O(n²) LLM pass):
  - LAYER 1 · NAME COLLISION (cheapest): normalize each name (lowercase, `_`↔`-`, strip suffixes
    `-improved`/`-v2`/`-draft`/`-copy`) and group exact matches. Catches port-source-vs-target pairs.
  - LAYER 2 · DESCRIPTION SIMILARITY (PRIMARY signal): Jaccard on the lowercased description
    word-set for every pair. FLAG a pair as a DUPLICATE candidate at Jaccard ≥ 0.6; flag as an
    OVERLAP candidate at ≥ 0.4 WHEN the two share a leading trigger phrase. CALIBRATION (measured on
    a live 67-item corpus, 2026-07-12): the one true duplicate sat at Jaccard 1.0 and the next real
    pair at 0.36 — a wide empty margin, so 0.6 isolates duplicates with zero false positives; 0.4+
    shared-trigger is the softer overlap net. Re-check the margin on the target inventory; the
    corpus is tiny (~2k comparisons) so the full O(n²) string sweep is sub-second.
  - LAYER 3 · BODY SIMILARITY (only for L1/L2 candidates): read the two bodies and compare with
    difflib ratio / shingle-Jaccard. Confirms real-duplicate vs coincidental description overlap.
  - LAYER 4 · DUPLICATES-OF-TOOLKIT (the specific ask): match each user item against the toolkit's
    own capability set (the MANIFEST.tsv agents+skills rows = ground truth). A match ⇒ flag
    "duplicates toolkit capability"; show BOTH and let the user pick (the toolkit one is
    install-managed; the standalone may be a stale hand-copy, or a deliberate fork).
  - LAYER 5 · LLM ADJUDICATION (optional, ONLY the borderline shortlist from L1/L2): host.llm a
    per-PAIR judgment {duplicate | overlap | subset | distinct}. Cheap fan-out on the shortlist,
    NEVER an O(n²) LLM pass over all pairs.
STEP.4_recommend: emit a table — one row per flagged item: {name, kind, ownership-class,
  why-flagged (which overlap/duplication + the other member), recommended-action}. This table IS
  "the surveyed scope made explicit" that the commit-class gate requires.
INVARIANT.recommend_not_enforce: the output is a RECOMMENDATION, never an auto-action. A
  false-positive costs the user one "no," never a lost capability. Cheap-first, false-positive-
  tolerant-but-flagged.

# ═══════════════════════════════════════════════════════════════════════════
# COMMIT-CLASS GATE (applies to any retire/relocate, both surfaces)
# ═══════════════════════════════════════════════════════════════════════════
Retire/relocate MOVES or DELETES user capability ⇒ COMMIT-CLASS (see
`rules/recon-before-commitment.machine.md`): survey + self-adjudicate FIRST, make the surveyed
scope explicit (STEP.4 table), and the COMMIT is user-gated. INVARIANT.never_destroy_first: on
NEITHER surface does a delete/rm precede a verified copy. Every retire is reversible.

# ═══════════════════════════════════════════════════════════════════════════
# CC ADAPTER  (Claude Code — files under ~/.claude; driven by lib/capability-audit.sh)
# ═══════════════════════════════════════════════════════════════════════════
CC.inventory: `bash "$HOME/.claude/lib/capability-audit.sh" inventory` — walks
  `~/.claude/{agents,skills,commands}` (+ a project `<proj>/.claude/` if given), reusing
  doc-status.sh's `is_durable` + prune (backups/ plugins/ .git/) for the ownership walk.
CC.ownership (3 classes; ONLY class-3 is eligible):
  1. TOOLKIT-AUTHORED — carries the in-band STATUS header AND/OR is in MANIFEST.tsv ⇒ install-managed;
     manage via install.sh/uninstall.sh, NOT here (a re-run would restore a hand-deleted one).
  2. THIRD-PARTY — under plugins/ or backups/ ⇒ not yours; pruned from the inventory entirely.
  3. USER-OWNED — the residual (durable doc, no STATUS header, not plugins/backups) ⇒ the target class.
CC.retire (PROC — mirrors dev-tree.sh `offload`: copy → verify → USER removes; source never auto-deleted):
  1. RECON + classify (only class-3 eligible).
  2. PROPOSE the retire/relocate list (STEP.4 table).
  3. COPY-THEN-CONFIRM — for each user-confirmed item: `capability-audit.sh backup <path>` copies it
     to `~/.claude/_retired/<YYYY-MM-DD>/` (retire) or to the project `.claude/` (relocate). SOURCE STILL EXISTS.
  4. VERIFY the copy is present + readable at the destination.
  5. HAND THE DELETE TO THE USER — print the exact `rm`/`mv` to remove the now-redundant source. NEVER auto-rm.
  6. REVERSE — un-retire = copy back from `_retired/`. Nothing was destroyed.
CC.relocate: global (`~/.claude/`) ↔ project (`<proj>/.claude/`) is a first-class reversible file move
  (offload model: copy to destination, verify, print the user-run rm of the source).

# ═══════════════════════════════════════════════════════════════════════════
# SCIENCE ADAPTER  (Claude Science — host.agents/host.skills via the repl tool)
# ═══════════════════════════════════════════════════════════════════════════
SCI.inventory: `host.agents.list()` + `host.skills.list()` (repl tool). Agent records carry
  `source` + `enabled`; skill records carry `origin`.
SCI.ownership: ELIGIBLE = agents `source=="user"`; skills `origin ∈ {personal, draft}`.
  PROTECTED (delete refuses anyway) = agents `source=="bundled"`; skills `origin=="anthropic"`.
SCI.location_axis (asymmetric vs CC — no project relocate exists): Science profiles are ORG-GLOBAL
  (the record carries NO project_id) and skills are CATALOG-GLOBAL once published, so the CC
  "relocate global↔project" lever HAS NO SCIENCE ANALOG. The Science location axis is only:
  skills = published↔draft (unpublish = reversible retire-lite); agents = there is NO retire-lite
  (see SCI.oq1_resolved) → delete-with-restore is the only profile retire.
SCI.oq1_resolved (probed 2026-07-12): `host.agents.update` accepts ONLY
  {display_name, description, system_prompt, skill_names, unrestricted, icon_key, color_key} — it
  does NOT accept `enabled`, even though the record carries it. So "disable-instead-of-delete" is
  NOT available for profiles via the SDK; the profile retire path is delete-with-restore-bundle.
SCI.retire (PROC — host.*.delete is DESTRUCTIVE + there is no user-shell ⇒ restore-bundle FIRST):
  1. RECON — list + classify by tag (eligible vs protected).
  2. COPY (restore-bundle-first — this IS the copy-then-confirm "copy"): BEFORE any delete, serialize
     the full record to a dated restore artifact + a human RESTORE.md naming the exact rebuild calls.
     - SKILL: host.skills.read(name, path) for EVERY file (SKILL.md + kernel.py/kernel.R + scripts).
     - AGENT: the full profile from host.agents.get(name) — systemPrompt, description, displayName,
       skillNames, connectors, excludedTools/excludedToolsDetail, iconKey, colorKey, unrestricted.
  3. PROPOSE + LIST-CONFIRM — ask_user with the FULL retire list BEFORE any delete. RATIONALE: the
     platform's own delete consent is one coarse "Allow for this project" card; the skill's own
     up-front list makes that card a confirm, not a surprise.
  4. COMMIT — ONLY after the restore bundle is VERIFIED saved (host.artifacts shows it): call
     host.skills.delete / host.agents.delete per confirmed item.
  5. RETIRE-LITE PREFERENCE — where a reversible lever exists, prefer it over delete: skills →
     unpublish to draft (reversible via publish) instead of delete. (Profiles have no such lever —
     SCI.oq1_resolved — so a profile retire is delete-with-restore.)
  6. REVERSE — RESTORE.md documents the rebuild: host.agents.create / host.skills.edit+publish from the bundle.

# ═══════════════════════════════════════════════════════════════════════════
# PORTABILITY / IDEMPOTENCY / BLAST-RADIUS
# ═══════════════════════════════════════════════════════════════════════════
PORTABILITY (CC lib): bash-3.2 floor + Linux — no `timeout` binary, no GNU-only find/sed flags;
  prune via the doc-status.sh `\( -name backups -o -name plugins -o -name .git \) -prune` idiom.
IDEMPOTENCY: the audit is READ-ONLY + repeatable (re-run = same report on unchanged state). backup
  copies are skip-if-exists (re-copy to the same dated dir is a no-op).
BLAST-RADIUS: retire/relocate is the ONLY mutating path — COMMIT-CLASS-gated, copy-then-confirm,
  recommend-not-enforce, reversible on both surfaces. NEVER auto-rm. Only user-owned/user-origin
  items are eligible; toolkit-authored + third-party are excluded.

# REF: rules/recon-before-commitment.machine.md (COMMIT-CLASS gate) · lib/dev-tree.sh offload
# (copy-then-confirm precedent) · lib/doc-status.sh (ownership walk + BSD-find prune) ·
# commands/clean-tasks.md (the task-declutter twin) · standing-mandate (CLARITY+TRACEABILITY
# applied to the toolkit's own surface).
