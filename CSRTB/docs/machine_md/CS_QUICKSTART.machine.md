# CS_QUICKSTART.machine.md
# STATUS: CURRENT (2026-08-03). Day-one guide for the CRT Science Customization Bundle v2.11 (52 skills / 18 profiles, recomputed from crt_science_bundle.json 2026-08-03). Machine-optimized ROOT; human twin = CS_QUICKSTART.md (this file is authoritative — edit here first).
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# AUDIENCE: brand-new Claude Science user, day one. The things to know/do. Full detail → CS_USAGE_DETAILED (functional-section pointers below).

## WHAT IT IS
Claude Science = an agentic pair-scientist in a REMOTE sandbox (the browser is its only channel to you — no local shell, no hooks, no local audio), working in turns (you set a goal → it plans/acts through the host.* API → you review). This toolkit adds 52 skills + 18 agent profiles + fail-closed kernel gates to your account, so every session inherits the same methodology. [→ The Map]

## DAY-ONE LIST
1. START: open a conversation in your Science project under an installed PROFILE — GENERALIST is the daily driver; 17 named specialists sit alongside it. No launch command: your installed skills + profiles + project-memory are already live in the account. [→ install: CS_INSTALL_STARTER_v2.11.md]
2. MEMORY-AS-CONTEXT (replaces CC's CLAUDE.md auto-load): there is no per-repo config file that loads each session — instead durable project-MEMORY auto-recalls into context. That makes memory the POISON surface — keep it current; stale memory is re-read as fact. ARTIFACTS are INERT until searched. [→ Context]
3. PROMPT: type an instruction and be specific — NAME your output artifacts. [→ The Loop]
4. AGENCY DIAL (three skills, not a keystroke): plan (deliberation max — map the territory + get your go/no-go before any scope-defining step), collab (the middle default — surface non-trivial calls, no per-step gate), solo (autonomy max — run a handed-off task to completion, no check-ins). Invoke by naming the skill. [→ The Loop; Part B]
5. PROFILES (the CS analog of CC subagents): pick one for the session; dispatch specialists as CHILDREN via host.delegate. [→ Instructions]
6. MODELS — routed at delegation, per child: host.delegate routes each child by TIER — Opus 4.8 (T1) / Fable 5 (T1 hardest) = hard problems, Sonnet 5 (T2/T3) = routine, Haiku 4.5 (T4) = trivial. NEVER claude-opus-5; NEVER the bare `opus` alias (it resolves to Opus 5) — full IDs only. [→ Instructions; delegation-planning]
7. EFFORT rides the tier (T1 max → T4 low) — nothing to preset. [→ Instructions]
8. SKILLS AUTO-LOAD: describe the task (fit a GAM, gap-fill, QC a series, build a brms model) and the right skill loads via host.skills; or load one by naming it. [→ Instructions]
9. KERNEL SIDECARS: a skill may carry a kernel.py of PLAIN CALLABLES — no CLI, no `__main__` guard. Use it in a repl cell: `exec(host.skills.read("<skill>", "kernel.py")["content"])`, then call the function (e.g. the delegation-planning routing gates). [→ Instructions; Automation]
10. DELEGATION & SCALE: host.delegate children run ASYNC — you collect their reports, steer them, or stop them; long work advances in the background while you keep going. [→ Delegation & Scale]
11. THE DISCIPLINES ride in your profile + the skills + the kernel gates (there is NO always-on rules file on CS): it verifies before saying "done", fixes root causes not symptoms, and holds the standing mandate — CLARITY ▸ ACCURACY ▸ TRACEABILITY ▸ REPRODUCIBILITY. Rely on them as given. [→ Part B]
12. COMPLETION PING: CS has no turn-end hook, so the audible-alert skill fires an AGENT-INITIATED ping at turn boundaries (it beeps itself, as its last action). [→ Automation]
13. HANDOFF / RESUME (no /baton, no file-drop on CS): durable project-MEMORY persists across sessions and SAVED ARTIFACTS carry lineage — together they are your cold-resume trail. Persist the load-bearing facts before you stop. [→ Context]
14. CONTEXT auto-summarizes as it fills; start a NEW conversation for an unrelated task. [→ Context]

## FIRST SESSION (recipe)
open a Science conversation under a profile → load `plan` → describe the task (data artifact, model, output artifact) → read + approve the plan → let it work, delegating specialists via host.delegate as needed → review results → persist durable facts to project-memory + save artifacts with lineage → new conversation for the next task. [→ Your First Research Session]

## FOR MORE
Everything above expands in CS_USAGE_DETAILED — the full 52 skills / 18 profiles roster, the host.* API surface, memory-as-poison-surface, the delegation topologies, and extension authoring on CS. Install mechanics + acceptance probes live in CS_INSTALL_STARTER_v2.11.md (at the bundle root).
