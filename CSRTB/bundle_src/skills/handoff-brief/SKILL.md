---
name: handoff-brief
description: Write a cold-start brief so the NEXT conversation in this Claude Science project resumes with zero re-discovery. Use when the context or host.llm token budget is filling, at session end, before a long background run, before switching to a specialist profile, or when the user asks for a handoff / starter prompt / "where we left off" for a new conversation. Unlike Claude Code's baton, it does NOT bundle the transcript or rewrite paths — project artifacts (with lineage), project memory (auto-recalled), and host.frames() already persist across sessions. The brief is the POINTER that makes the next session load them targeted instead of re-exploring. ALWAYS emits (unconditionally — never merely offers) a paste-ready starter prompt alongside the brief, referencing canonical artifacts by id, the memory to trust, the immediate next step, and any kernel variables to reconstruct.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# handoff-brief — cold-start the next conversation, Claude Science-native

Claude Science shares durable state across conversations ⇒ the handoff is NOT a transcript port (Claude Code's baton, obviated here) but a short POINTER bridging only what dies at the session boundary.

## MANDATORY — every invocation emits BOTH outputs (the single home of this rule)
Complete = TWO outputs in the SAME turn: (1) the **brief**, saved as artifact `handoff_brief.md`; (2) the **paste-ready starter prompt**, emitted in chat in a copy-able block.
- WHEN you would close with "want me to also write the starter prompt?" ⇒ emit it now instead; that offer is the exact failure this skill exists to prevent.
- Brief-only ⇒ skill NOT run; both outputs are unconditional.
- Bare `/handoff-brief` (zero args) ⇒ run every step with sensible defaults; trailing user text is extra instruction, never a precondition.

## Persists across sessions (retrievable, NOT auto-in-context)
- **Artifacts + lineage** — `host.artifacts(search=...)`, `host.artifact_path(vid)`, `{{artifact:VID}}`. Every saved file + its reproduction code.
- **Project memory** — the ONLY channel that surfaces on its own (auto-recall by keyword). `read_memory`/`search_memory` for the rest.
- **Past transcripts** — `host.frames(frame_id=...)`. Expensive; last resort.

## Dies at the boundary (this is ALL the brief must bridge)
- **Kernel state** — every variable / loaded DataFrame / import (kernels are per-session). Name which artifact reloads each.
- **The live plan + in-flight reasoning.**
- **`summary_query` reach** — a new conversation CANNOT query this one's folded history.
- (`host.llm` per-frame 2M token budget RESETS fresh next session — a benefit, not a loss.)

## Procedure
1. **Flush durable facts to project memory FIRST** (`write_memory`) — current phase, decisions locked/open, gotchas. This is the highest-value step: memory is the auto-surfacing channel, so anything here re-appears next session unprompted. Prefer `replace` over near-duplicate rows.
2. **Verify work products are saved as artifacts.** Reloadable state (a big DataFrame after expensive compute) → save the `.parquet`/`.pkl` with `save_artifacts(..., checkpoints=[...])`. Confirm each returns a `version_id`.
3. **Write the brief** as an artifact `handoff_brief.md` AND emit the starter prompt in chat. Sections:
   - **GOAL** + current **PHASE**.
   - **CANONICAL ARTIFACTS** — `filename` + `{{artifact:VID}}` for each load-bearing file (base data, report). Not every artifact — the ones the next step needs. EVERY id written here must have been RESOLVED this session (`host.artifacts`/`host.artifact_path` returned it); an id transcribed from memory or an earlier brief is tagged `(unverified)` — the recorded stale-pointer failure (SEED-18) is a brief whose id does not resolve next session, and nothing downstream catches it.
   - **KERNEL STATE TO RECONSTRUCT** — e.g. "reload `user_prompts_index.parquet` (artifact X) into `U`". Explicit, because nothing carries variables.
   - **MEMORY TO TRUST** — which project-memory facts carry the durable decisions.
   - **NEXT** — priority-ordered; GATE each step with the observable that proves it worked; mark ⚑ user-input blockers.
   - **OPEN DECISIONS** — locked vs open.
4. **Emit the starter prompt** — the paste-ready text the user gives to open the next conversation. Compact: goal + phase + "load artifacts X,Y into vars U,V" + the one next action. The `draft_handoff_brief()` helper (kernel.py) auto-populates the artifacts section from `host.artifacts()`.

## Also do NOT
- WHEN tempted to bundle/re-summarize the transcript ⇒ point at artifacts/memory instead; `host.frames()` retrieves the raw record if ever truly needed.
- WHEN a fact already lives in memory ⇒ reference its `mem_id`; do not copy it into the brief.
- No path-rewriting, session-file staging, or account/machine handling — no cross-machine session port exists in Claude Science.

## Child dispatch briefs (cross-ref, not owned here)
A brief for a DELEGATED CHILD (a `host.delegate` dispatch, not a session handoff) follows the same record-pointer principle — give the child the RECORD (artifact ids, DB paths), never only a précis — plus the delegation defaults (self-service record access, brief persisted before launch, detached dispatch, report cap, the stuck-escalation rule). Those defaults are OWNED by `delegation-planning` Part D; load that, do not restate here.

## Success check
Both outputs shipped in one turn. A fresh conversation in THIS project, given ONLY the starter prompt, can name + execute the next action without re-deriving state (reloading any needed kernel variables from the named artifacts). Would have to re-explore ⇒ the brief is missing a pointer.
