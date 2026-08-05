# QUICKSTART.machine.md
# STATUS: CURRENT (2026-07-12). T-24: skill/agent counts normalized to the true installed set (21 skills + 5 agents).
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Machine-optimized ROOT for the QUICKSTART. Human twin = QUICKSTART.md (render via /folio).
# AUDIENCE: brand-new user, day one. The 15 things to know/do. Full detail → USAGE_DETAILED (functional-section pointers below).

## WHAT IT IS
Claude Code = an agentic pair-scientist in your terminal that reads/writes files + runs code in your repo, in
turns (you set a goal → it plans/acts → you review). Safe by default: the toolkit blocks destructive commands. [→ The Map]

## DAY-ONE LIST (15)
1. LAUNCH: `cd` into your project, run `claude`. The repo's `CLAUDE.md` + rules auto-load. [→ The Loop]
2. PROMPT: type an instruction + Enter; Esc interrupts; steer by typing mid-task. Be specific, name output paths. [→ The Loop]
3. MODES (the one keystroke): Shift+Tab cycles normal / auto-accept edits / PLAN. Use PLAN for anything nontrivial; the label above the box tells you which. [→ The Loop; Actions & Guardrails]
4. MODELS: `claude-fable-5[1m]` is preset; `/model` to switch. Fable 5 / Opus 4.8 = hard problems, Sonnet = routine, Haiku = trivial. [SUPERSEDED 2026-08-04 — constrained supervised use; see USAGE_DETAILED MODEL POLICY] ~~NEVER `claude-opus-5`~~ — `claude-opus-5` runs ONLY as a supervised `delegate:opus5-executor` child under a Planner's active watch; never your session default, never a coordinator or sub-planner. NEVER bare `opus` (resolves to Opus 5) — full IDs only for the SESSION picker. SUBAGENT models are a separate surface with FOUR RANKS (measured 2026-08-04): `CLAUDE_CODE_SUBAGENT_MODEL` env (keep `inherit`) > the Task `model` param (ALIASES ONLY) > agent frontmatter `model:` (full ids legal) > inherit the main model — so NAME the tier (`fable`/`sonnet`/`haiku`); omitting it requests the MAIN model, not a tier. CEILING children go to `delegate:fable-executor` (paramless, its own pin governs) — the built, acceptance-passed fable route that dodges the serving substitution; skills reach it by naming the `SKILL.md` for it to read. And verify by the SERVING STAMP in the child transcript, never by the child's self-report. [→ Instructions, USAGE_DETAILED MODEL POLICY]
5. EFFORT: preset to MAX — nothing to do. [→ Instructions]
6. PERMISSIONS: you'll get prompts; the toolkit BLOCKS `rm`/`curl`/`sudo`/… for safety — allow the safe ones, or add them to `.claude/settings.local.json`. [→ Actions & Guardrails]
7. SLASH COMMANDS: `/help`, `/clear` (new topic), `/context`, `/model`, `/baton` (handoff), `/folio` (make a PDF; add "docx" for a Word file), `/solo` (run autonomously, no check-ins), `/xbeep` (beeps). Type `/` for the menu. Commands also take trailing text as instructions (e.g. `/compact focus: keep the file paths we're editing`) — detail under Instructions. [→ Instructions]
8. SKILLS AUTO-FIRE: just describe the task (fit a GAM, gap-fill, QC, brms model) and the right skill loads; force one with `/name`. [→ Instructions]
9. INTERACTIVE BY DEFAULT: give a clear goal and it moves briskly — the autonomy + no-check-in rules keep it from asking "should I continue?" after every trivial step (no nagging), but expect periodic check-ins at decision points. Want it fully hands-off, run-to-completion with no stops? `/solo`. [→ The Loop; Part B]
10. SANDBOX: all test/scratch files → a `sandbox/` dir; keep the repo clean. [→ Part B]
11. ALWAYS-ON RULES do the worrying for you: it verifies before saying "done", fixes root causes not symptoms, checks facts from source. Rely on them as given. [→ Part B]
12. BEEPS mean: prompt sent / Claude done / needs a permission. `/xbeep` toggles. [→ Automation]
13. CONTEXT auto-summarizes as it fills; `/baton` (write a handoff) then `/clear` between unrelated tasks. [→ Context]
14. LONG RUNS go BACKGROUND — you get a beep/push on completion; Claude keeps working meanwhile. [→ Delegation & Scale]
15. RESTART to apply setting/hook changes (they load at startup). [→ Troubleshooting]

## FIRST SESSION (recipe)
`cd` repo → `claude` → Shift+Tab to plan mode → describe the task (data path, model, output path) → read + approve the plan → let it work → review results → `/baton` → `/clear` for the next task. [→ Your First Research Session]

## FOR MORE
Everything above expands in USAGE_DETAILED (the detailed guide) — see the cited functional sections. Start there for permissions
internals, the full 21 skills + 5 agents, effort levels, context tools, hooks, research patterns, and the glossary.
