---
name: baton
description: Author or update a machine-record handoff + resume document so a cold session (or another person) can resume the work from the doc alone. Use when pausing work, before a compaction, before exiting to update/restart Claude Code (exit+resume), before starting a long background run, when context is filling, at the end of a work session, or when asked to write a handoff / resume / status-for-continuation / "where we left off" doc. EVERY invocation also (a) locates and re-attaches the active plan file + task list, (b) emits a paste-ready RESUME PROMPT to send right after exit/resume, and (c) checks whether running monitored/background processes survive /exit and WARNS about any that will die — no extra arguments needed.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-08-03). Pointer-verification rules added 2026-07-28 (verification-integrity pass). Scope: the same-machine resume DOCUMENT.

# baton — write a resume-from-nothing handoff doc

A good handoff lets a fresh session with NO prior memory continue the work correctly. The doc IS the durable state — make it complete enough that neither silence, a half-state, a KILLED background process, nor a DROPPED plan/task list can strand the continuer.

## Default actions — do ALL FOUR on every `/baton`, no arguments required
Trailing text after `/baton` is EXTRA instruction, never a precondition. With bare `/baton`, still run:
- **A. WRITE/REFRESH the resume doc** — the full Procedure below, to a stable tracked path.
- **B. RE-ATTACH the plan + task list** — locate the active plan-mode doc AND the session task list, name both by path/id in the doc so resume RE-ATTACHES them instead of re-deriving. If none is found, say so explicitly (don't omit silently).
- **C. EMIT the RESUME PROMPT** — print, in chat, the exact paste-ready message to send in the NEXT session right after `/exit`+resume (see ## Resume prompt). This is a REQUIRED output, not the doc alone.
- **D. PROCESS-SURVIVAL CHECK + WARN** — enumerate running monitored/background processes, decide per process whether it survives `/exit`, capture each one's restart command in the doc, and WARN the user in chat about any that will DIE on exit (see ## Process-survival check).

## When to invoke
Pausing, context filling, before a compaction, before exiting to update/restart Claude Code (exit+resume), before a long detached run, session end, or an explicit request for a handoff/resume/status doc.

## Procedure
1. **Pick style + location.** Machine-record (terse KEY:value / tables / IF⇒THEN), reader = the next Claude. Write to a STABLE tracked path (e.g. `docs/HANDOFF_<project>.machine.md`), not a scratch dir. Follow any project `HANDOFF_PROTOCOL.machine.md`.
2. **FIRST_ACTIONS** — what the continuer must read + verify (trust-but-verify) before acting; env re-checks.
3. **STATE spine** — a table `id | component | status | proof/path`; status ∈ {DONE, DESIGNED, TODO, GAP(⚑ user-input)}; every DONE cites a proof path. EVERY id/path written into this column must have been RESOLVED this session (the file listed, the artifact fetched) — a pointer transcribed from memory or an earlier doc is tagged `(unverified)`. RUN the ## Proof-path integrity audit on that column before the doc leaves your hands.
4. **Running jobs + RESTART pointers** (default action D) — for every long/background run: its command, log path, expected output + count, and its completion SENTINEL (silence alone ≠ success). Run the ## Process-survival check: mark each process SURVIVES or DIES on `/exit`, and for every DIES process give the EXACT restart command. Dying processes — shell/monitoring `watch` loops, `/loop`s, `tail -f` monitors, background agents/tasks, foreground-shell `&` jobs — do NOT survive an exit / Claude update; this doc is the only place that restart knowledge lives.
5. **PLAN + TASK LIST re-attach** (default action B) — locate the active plan-mode doc (e.g. `~/.claude/plans/<name>.md`) AND the session TASK LIST (the TaskList/TaskCreate store). Name the plan file by path, the CURRENT in-progress task, and the ordered NEXT tasks, so the continuer RE-ATTACHES/ACTIVATES them rather than re-deriving. An exit+resume (e.g. for a Claude update) DROPS the live task list and plan; this pointer is how they come back. If you cannot find a plan file, state that explicitly.
6. **NEXT** — priority-ordered, entry-pointed, GATE each step (the observable that proves it worked); mark ⚑ user-input blockers explicitly.
7. **FACTS / DECISIONS** — load-bearing constants (each with a `verify:` note) + decisions locked vs open.
8. **GIT_MAP** — branch, landed vs uncommitted, how to resume.
9. **PLAN vs REALITY** — what was planned, what actually exists, gaps.
10. **RESUME PROMPT** (default action C) — compose + PRINT the paste-ready prompt per ## Resume prompt.

## Resume prompt (always emit in chat)
After writing the doc, print a fenced, paste-ready message the user sends in the next session right after resume. Keep it self-contained and compact:
- Points at the handoff doc by path ("Read `<doc path>` first").
- Names the ONE immediate next action (from NEXT).
- Lists processes to RESTART (from action D) with their commands.
- Re-attaches the plan: "re-open plan `<plan path>` and re-activate the task list; current task = `<...>`".
- Ends with the gate that proves the resume worked.
Emit it EVEN IF the user gave no extra instruction — it is a default output.

## Process-survival check (always run)
Goal: know which running processes die when Claude Code exits, so none is silently lost.
- **Enumerate**, don't guess: `ps -eo pid,ppid,stat,etime,command | grep -E 'watch|tail -f|<project run cmds>'` (each Claude Code bash call is a FRESH shell, so `jobs` won't see prior background jobs — use `ps`). Also recall any `/loop`, background agent, or `... &` job started this session.
- **Decide survival** per process: a job started as a CHILD of a Claude Code bash tool call DIES on `/exit` unless it was DETACHED — `nohup`/`setsid`/`disown`, a `tmux`/`screen` session, or a launchd/systemd service. Heuristic: PPID reparented to 1 with no controlling TTY ⇒ likely SURVIVES; PPID under the Claude Code process tree ⇒ DIES. If uncertain ⇒ treat as DIES (conservative).
- **Warn**: for every DIES process, tell the user plainly in chat ("⚠ these will NOT survive /exit: … — their restart commands are in the doc"). Never let a monitored process vanish unannounced.
- **Optional (on request):** offer to relaunch a dying process DETACHED (`setsid <cmd> &` or `nohup <cmd> & disown`) so it survives — do NOT auto-detach, since that changes runtime behavior; only on the user's OK.

## Proof-path integrity audit (run over every DONE before emitting)
A resume doc is a MULTI-CLAIM status restatement written at exit — the highest-leverage place a laundered "done" can enter, because it becomes the next session's durable starting assumption. The emit-time adversarial gate deliberately does NOT fire on `/baton` turns (wrong instrument, worst timing), so THIS audit is where a completion claim is checked. For each row you mark DONE, before writing it:
- **WHEN marking a claim DONE ⇒ name the source that PROVES it, then confirm you actually READ that source THIS session.** Not a nearby proxy. A run banner, a file's mere existence, a grep that the fix is on disk, or an earlier turn's summary is EXISTENCE, not EFFICACY — cite the verdict/measurement itself (the broad-validation result, the test output, the diff). If the authoritative source is pending or unread ⇒ status is TODO or GAP(⚑), not DONE.
- **WHEN a DONE restates a claim from earlier in the session ⇒ re-confirm it against the source as of NOW, not as of when first claimed.** State can move between the claim and the handoff (a "regression-clean" from before the broad run finished is anachronistic). Read the current verdict; don't transcribe the old one.
- **WHEN two states are compared ("matches baseline", "parity preserved") ⇒ confirm both sides were measured on the same basis** — same config, same window, same metric — before writing the comparison as settled.
- **WHEN the doc emits ANY artifact id, file path, plan-file reference, task id, or restart command — not only DONE rows ⇒ the same rule: resolved THIS session or tagged `(unverified)`.** The recorded failure (stale-pointer class, SEED-18) is a handoff whose pointer does not resolve for the next session — and nothing downstream catches it, because the emit-time gate deliberately skips `/baton` turns; author-time is the only enforcement point.
- If any DONE cannot pass these ⇒ downgrade it (DONE→TODO/GAP) and say why in the doc. A handoff that honestly marks GAP is worth more than one that laundered a "done".

## Success check
A cold session, given ONLY this doc + the repo, can name the next action and execute it without re-deriving state or re-reading old transcripts — including RESTARTING any process that died on exit + RE-ATTACHING the plan/task list. AND the user has, in chat, the paste-ready resume prompt + a clear warning about any process that won't survive `/exit`.

## Related (guardrails, already workspace rules)
Pair with a tracked background-run sentinel; verify-or-hedge any status claim you can't cite. The ## Proof-path integrity audit above is the author-time counterpart to the emit-time adversarial gate (F1), which skips `/baton` turns by design — so completion claims in a handoff are self-enforced here, not caught downstream.
