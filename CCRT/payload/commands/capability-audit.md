---
description: Audit installed agents/skills for duplication + placement; RECOMMEND what to retire (duplicates of each other or of the toolkit) or relocate (global↔project). Flags candidates, never deletes — retire is copy-then-confirm + user-gated.
tags: [housekeeping, agents, skills, declutter, portability]
argument-hint: [optional — a ~/.claude root or project path to audit; default: ~/.claude]
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# /capability-audit — declutter + placement advisor

Run the `capability-audit` skill's procedure: inventory every installed agent + skill, classify each
by ownership, cluster overlapping/duplicate capabilities, and present a RECOMMENDATION of what to
retire or relocate. It flags candidates; it never deletes. See `~/.claude/skills/capability-audit/SKILL.md`
for the full heuristic and the two platform adapters.

**What it does (PROC):**
1. **Inventory** — `bash "$HOME/.claude/lib/capability-audit.sh" inventory` lists every agent/skill/command with its ownership class (toolkit-authored | third-party | user-owned). Only user-owned items are eligible to retire/relocate.
2. **Cluster** — `bash "$HOME/.claude/lib/capability-audit.sh" cluster` flags candidate duplicate (description Jaccard ≥ 0.6) and overlap (≥ 0.4) pairs across the union {agents ∪ skills}. Then optionally match user items against the toolkit's own MANIFEST rows to flag "duplicates toolkit capability."
3. **Recommend** — present a table: {name, kind, ownership-class, why-flagged, recommended-action}. This is the surveyed scope made explicit.
4. **Gated commit** — retire/relocate is COMMIT-CLASS (see `rules/recon-before-commitment.machine.md`). For each user-confirmed item: `capability-audit.sh backup <path>` copies it out of the load path, verifies, and PRINTS the exact `rm`/`mv` the user runs. NEVER auto-rm; the source survives until the user removes it; un-retire copies back.

**INVARIANT:** the audit RECOMMENDS; it never mutates on its own. A false-positive costs one "no," never a lost capability. Toolkit-authored + third-party items are excluded from eligibility — only user-owned capability is touchable.

Run the inventory + cluster, present the recommendation table for the audited root, then execute backups only after user confirmation.
