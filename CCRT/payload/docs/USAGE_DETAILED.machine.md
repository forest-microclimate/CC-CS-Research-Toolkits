# USAGE_DETAILED.machine.md
# STATUS: CURRENT (2026-07-12). T-24: skill/agent taxonomy normalized to the true installed set (21 skills in 4 groups; 5 subagents research-facing×3 + dev-facing×2).
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Machine-optimized ROOT for the DETAILED usage guide — the AUTHORITATIVE source. Human twin = USAGE_DETAILED.md; the .md + .pdf are DERIVED from this file (render via /folio). Edit HERE first, then propagate machine→human→pdf.
# AUDIENCE: a scientist who can launch a `claude` session but knows little else. Teaches Claude Code from near-zero → how the Claude Research Toolkit augments it → how to use it for research.
# SPINE: the skeleton IS Claude Code's functional architecture (the PRIMITIVES) ⇒ reason about capabilities, don't memorize a feature list. MAP (mental model) → PART A (base Claude Code, by function) → PART B (toolkit overlay) → PART C (in practice).
# STYLE: machine-terse, front-loaded, positive/action-first (this is the source; the human .md/.pdf are derived).

## MAP · WHAT CLAUDE CODE IS + ITS ARCHITECTURE
- ORIENTATION: two guides ship — QUICKSTART (day-one, 1-2 pp; read FIRST if new) + this DETAILED (reference). This guide teaches (a) Claude Code fundamentals, (b) the toolkit's augmentations, (c) research use. Both are machine→human→PDF artifacts — you are reading the human render of a `.machine.md` root. New term? → GLOSSARY.
- WHAT IT IS: Claude Code = an AGENT in your terminal — an agentic pair-scientist that reads/writes files + runs shell commands in your repo. Not a chat box: it edits real files + runs real code, all visible in the transcript.
- HOW IT RUNS — the TURN LOOP: you state a GOAL → it LOADS CONTEXT → PLANS → CALLS TOOLS within your PERMISSIONS → you REVIEW → repeat. Every capability below is one layer this loop passes through.
- THE PRIMITIVES (the whole mental model; PART A takes them one at a time):
  - CONTEXT ⇒ what Claude SEES (window · CLAUDE.md · memory · settings).
  - INSTRUCTIONS ⇒ how you STEER it (models · effort · slash-commands/skills · CLAUDE.md).
  - ACTIONS + GUARDRAILS ⇒ what it DOES + the permission gate (tools · edits · bash · allow/ask/deny · plan mode).
  - DELEGATION ⇒ handing bounded jobs to SUBAGENTS + running work in the BACKGROUND/parallel.
  - AUTOMATION ⇒ event-driven HOOKS + loops/workflows.
  - CONFIG/SCOPE ⇒ where settings live + how scopes MERGE (global + project + local).
- INVARIANT: everything Claude Code can do = one of these primitives inside the turn loop; learn the primitives, derive the features.
<!--FIG: the turn loop wrapping the primitive layers (goal → context-load → plan → tool-calls ↔ permission-gate → review → repeat) | 85% -->

## PART A · BASE CLAUDE CODE, BY FUNCTION
- Each unit = one primitive, in a fixed ARC: FOR (its role) · LIKE (a handle) · mechanics · INVARIANT (the one line to carry) · COUPLES (what it connects to).

### A · THE LOOP & DRIVING IT
- FOR: running + steering Claude turn by turn — the driver's seat.
- LIKE: pair-programming out loud — you set direction, it acts, you correct, repeat.
- START: `cd` into your project dir → run `claude`. The working dir = the repo Claude acts on; launching from the repo ROOT auto-loads that repo's `CLAUDE.md` + `.claude/rules/*` (→ CONTEXT).
- TERMINAL BASICS (only if new): terminal = a text window; `cd <path>` change dir, `ls` list, `pwd` show dir; quote spaced paths (`cd "My Folder/proj"`); Enter runs a command / submits a prompt.
- PROMPT: input box at the bottom; type an instruction + Enter. BE SPECIFIC + name deliverables — e.g. "fit a `bam` AR1 model to `sandbox/x.rds`, save the diagnostic plot to `sandbox/`". Paste FILE PATHS, not file contents. The mode label sits just above the box (→ MODES below).
- TURNS + REVIEW: state a GOAL → it plans/acts → you REVIEW. The transcript scrolls the full action history (every action shown; edits shown as diffs you approve) — nothing is hidden.
- STEER MID-TASK: type a correction + Enter while the current step runs. `Esc` = interrupt the current action (keeps the session). `Ctrl+C` = cancel input / interrupt; `Ctrl+D` = exit the session. Going wrong? `Esc` + restate the goal beats letting it run.
- INTERACTIVE by default: it PAUSES at genuine decision points — the always-on autonomy + no-check-in rules (→ PART B) keep it brisk + non-nagging (no "should I continue?" after every trivial step), so "just do it" is fine; expect periodic check-ins. Run all the way through with NO stops ⇒ hand off with `/solo` (→ INSTRUCTIONS). SHORT: default = brisk but interactive; `/solo` = run-to-completion.
- MODES (Shift+Tab CYCLES the permission posture; the LABEL above the prompt is the source of truth for which you're in):
  - normal ⇒ asks before edits/commands (most control).
  - auto-accept edits ⇒ file edits apply without a per-edit confirm (fast once you trust the plan).
  - plan mode ⇒ READ-ONLY; explores + proposes, changes NOTHING (→ GUARDRAILS deep-dive).
  - WHEN: plan for anything nontrivial/unfamiliar; auto-accept when iterating fast on a known task; normal when touching production/canonical files.
  - A deny-listed command stays BLOCKED regardless of mode (→ GUARDRAILS).
- INVARIANT: it works in reviewable TURNS on real files — you can interrupt (`Esc`) + redirect at any moment; nothing is hidden.
- COUPLES: MODES → the permission gate (→ GUARDRAILS); `/solo` + no-check-in behavior → INSTRUCTIONS + PART B; auto-load on launch → CONTEXT.

### B · CONTEXT — WHAT CLAUDE SEES
- FOR: everything Claude can see this turn — its working memory.
- LIKE: a desk — a permanent shelf always in reach + a workbench that fills up and gets tidied.
- TWO KINDS:
  - PERSISTENT (auto-loaded every turn, survives across sessions): `CLAUDE.md` files + auto-memory + settings. `CLAUDE.md` loads at EVERY level (global `~/.claude` + each repo's `.claude` + subdirs); the repo-root load happens when you launch from it (→ LOOP). This is how durable preferences + rules reach Claude (→ INSTRUCTIONS, PART B).
  - RECOMPUTED each turn (the live window): this session's turns, files read, tool outputs. Finite — `claude-fable-5[1m]` ≈ 1M tokens (large).
- AS THE WINDOW FILLS: Claude AUTO-COMPACTS — summarizes older turns; you keep the thread but detail can blur.
- CONTROLS:
  - `/context` ⇒ show current usage.
  - `/compact` ⇒ summarize NOW (keep going, smaller footprint). Same mechanism as auto-compaction ⇒ it discards older detail, so Claude can suddenly FORGET compacted specifics (a real risk on long sessions).
  - `/compact focus: <what to keep front-and-center>` ⇒ steer what survives — e.g. `/compact focus: keep the gold model formula and the file paths we're editing`. The trailing instruction cuts the forgetting risk (an example of a slash command taking trailing text → INSTRUCTIONS).
  - `/clear` ⇒ wipe the window for a fresh UNRELATED task (fastest clean separation).
- LONG/COMPLEX effort ⇒ write a handoff with `/baton` BEFORE compaction so a fresh session resumes from the doc (→ DELEGATION).
- INVARIANT: PERSISTENT context (CLAUDE.md/memory/settings) always returns; the live WINDOW is summarized as it fills ⇒ protect long work with `/compact focus:` or `/baton`, and keep one task per session (`/clear` between unrelated tasks).
- COUPLES: CLAUDE.md/memory/rules content → PART B; `/baton` handoff → DELEGATION; trailing `focus:` → INSTRUCTIONS.

### C · INSTRUCTIONS — HOW YOU STEER IT
- FOR: the dials that direct HOW Claude works — model, reasoning budget, and the `/`-commands + skills you fire.
- LIKE: a control panel — pick the engine (model), the gear (effort), and the tool you reach for (skill/command).
- MODELS (`/model` switches mid-session, does NOT clear context):
  - Fable 5 = most capable (hard reasoning / modeling); Opus 4.8 = capable workhorse; Sonnet = fast, strong for routine coding; Haiku = fastest/cheapest (trivial edits).
  - Toolkit default = `claude-fable-5[1m]` (Fable 5, 1M-token context → CONTEXT), set in `~/.claude/settings.json`.
  - MODEL POLICY (BINDING): [SUPERSEDED 2026-08-04 — constrained supervised use] ~~NEVER Claude Opus 5 (`claude-opus-5`) — much higher observed failure-mode rate.~~ — Claude Opus 5 (`claude-opus-5`) is PERMITTED in exactly ONE position: a tightly-scoped supervised CHILD launched as `delegate:opus5-executor` (a project-scoped agent carrying the pin + the supervision contract) under a Planner's ACTIVE watch for scope-drift, thrash, and false-positive over-caution — the observed failure-mode rate is exactly what that watch exists to catch. STILL BANNED: as your session default · as a coordinator or a sub-planner · any raw naming of it in a plan's routing model field. NEVER the bare `opus` alias — CC ≥2.1.219 resolves it to Opus 5, and an alias re-resolves silently whenever CC remaps it. Always full IDs (`claude-opus-4-8`, `claude-fable-5`) where you pick the SESSION's model.
  - SUBAGENT MODELS — a DIFFERENT surface from the session picker, with FOUR RANKS (documented + MEASURED 2026-08-04, highest wins): (1) the `CLAUDE_CODE_SUBAGENT_MODEL` env var overrides both of the next two — keep it at `inherit` · (2) the Task `model` param, ALIASES ONLY `{sonnet|opus|haiku|fable}`, full ids rejected (measured governing: haiku ×4, sonnet ×5) · (3) agent frontmatter `model:`, where full ids ARE legal (measured governing: a full-id pin resolved `claude-opus-5` ×3) · (4) inherit the main model. OMITTING the param is rank 4 — it requests THE MAIN MODEL, not a tier. ROUTES: name `sonnet`/`haiku` for a simpler child; for the CEILING use `delegate:fable-executor` (paramless — the BUILT route, below), or name `fable` where the child needs tools that executor lacks; a full id rides in a project-scoped frontmatter pin (`lib/crt-dev-model.sh`); `claude-opus-5` only as `delegate:opus5-executor`.
  - SERVING SUBSTITUTION (an OPEN vendor bug, filed 2026-08-04): a correct REQUEST is not yet the RUN you asked for. In the one measured session population (134 children), fable-resolved launches from FULL-TOOLS subagents were SERVED `claude-opus-5` ~94% of the time (49/52); RESTRICTED-TOOLS agents were largely faithful; every other id was faithful. Discriminator ISOLATED single-variable to the **Skill tool grant** (`Read, Grep, Skill` → opus-5 3/3 vs `Read, Grep` → fable 2/2; `+Agent`, `+Bash`, web each faithful 2/2; size exonerated to ~87k) — measured SUFFICIENT, not necessary (a ≳90k residual unprobed); mechanism vendor-side and unknown. A SECOND population on a different main model ran 9/9 substituted (0 fable stamps in 733 calls) ⇒ a different main model is NO escape; and one restricted-tools run was swapped MID-RUN with every visible request field identical ⇒ a restricted schema is a better bet, not a guarantee. THE BUILT ROUTE: `delegate:fable-executor` — project-scoped, pinned `claude-fable-5`, granted `Read, Edit, Write, Grep, Glob, Bash` with NEITHER Skill nor Agent, launched paramless — passed a 5/5 serving-stamp acceptance (`fixture-measured`) and is the first reliable fable route since the substitution epoch. Skills reach it by READ-POINTER (the brief names the `SKILL.md`; the child reads it), and so does a specialist persona, whose charter the executor's own contract outranks on conflict. Audit the stamps anyway.
  - VERIFICATION LAW: a model claim is verified by the SERVING STAMP — the API response's own `model` field on each assistant turn of the child transcript — or it is NOT verified. Child SELF-REPORT is DISQUALIFIED (wrong 3 of 5, measured); the UI header shows the launch-time RESOLVED model, which is intent. The `model-verification` skill runs the audit.
  - HEURISTIC: stay on Fable 5 / Opus 4.8 for research/modeling/debugging; drop to Sonnet/Haiku only for bulk mechanical edits to save time/cost.
- EFFORT (reasoning spent BEFORE acting): toolkit sets MAX via `CLAUDE_CODE_EFFORT_LEVEL=max` + `alwaysThinkingEnabled: true` (you'll see a thinking phase) — you need not touch it. Levels low < medium < high < xhigh < max; higher = better on hard problems, slightly slower. Lower it per-session for faster/cheaper trivial turns; max + Fable 5/Opus 4.8 for the hardest modeling/debugging.
- SLASH COMMANDS + SKILLS = ONE MECHANISM (the key idea): custom commands are MERGED INTO skills.
  - A command file `.claude/commands/x.md` AND a skill `.claude/skills/x/SKILL.md` BOTH create `/x` and work the same way. (Toolkit proof: `/xbeep` ships as `commands/xbeep.md`; the 21 skills ship as `skills/*/SKILL.md`; all fire as `/name`.) A SKILL is the superset — it adds a bundle dir for supporting files + frontmatter that lets Claude AUTO-LOAD it when relevant; on a name clash the skill wins.
  - Type `/` to see the menu. Built-ins: `/help`, `/clear`, `/compact`, `/context`, `/model`, `/config`, `/agents`.
  - TRAILING TEXT after `/name` → `$ARGUMENTS`, interpreted as instructions — the command NAMES the action, the trailing text refines it. E.g. `/xbeep off` · `/compact focus: keep the file paths` (→ CONTEXT) · `/folio docx, please use Charter` (renders the docx twin + honors the font, adjusting `mainfont`) · `/model give me the fast one for this bulk edit`. MOST commands accept this.
  - STACK them: `/code-review /fix-issue 123` loads BOTH skills + passes the trailing `123` as `$ARGUMENTS` to each.
  - AUTO-INVOKE or FORCE: describe the task and the right skill auto-loads when relevant, OR force one explicitly with `/name`.
  - THE 21 TOOLKIT SKILLS (each auto-loads on its trigger; also `/name`), in four groups — 9 DOMAIN (research method) + 5 WORKFLOW + 3 AGENCY-DIAL + 4 TOOLKIT-BUILDER (dev-facing):
    - DOMAIN (9) — fire during everyday analysis:
      - aggregation-jensen-bias ⇒ averaging/binning a NONLINEAR quantity; compute-then-average at native resolution.
      - brms-hierarchical-fitting ⇒ building a brms/Stan hierarchical model; temporal AR; stalled/split chains.
      - gap-fill-imputation ⇒ gap-filling an autocorrelated series; chunk-predict-splice (never naive-concat).
      - julia-performance-correctness ⇒ writing/debugging Julia hot loops; allocations; type instability.
      - mgcv-temporal-gam ⇒ fitting a GAM/GAMM to time series; choosing k; AR1 via `bam`.
      - preflight-parallel ⇒ before launching ≥2 independent runs; compute core headroom correctly (→ DELEGATION).
      - temporal-block-cv ⇒ CV on autocorrelated / rare-event data (never iid split); PR-AUC / calibration.
      - temporal-qc-outlier-detection ⇒ flagging spikes / drift / level-shifts in an environmental series.
      - tz-safe-timestamps ⇒ building timezone-safe timestamps; joining/resampling across timezones without silent misalignment.
    - WORKFLOW (5) — cross-cutting research work:
      - `/research-stats-advisor` ⇒ choosing/defending a statistical method; checking assumptions; interpreting a result — the WHY/WHICH, not code.
      - `/machine-md` — author/edit an LLM-facing doc ⇒ writing any `*.machine.md` or `.claude/` file.
      - `/folio` — translate a machine doc → human + render a PDF (add "docx" for a Word twin) ⇒ any dual-audience doc needing a human PDF. (Machine docs preserve ATOMS on translation ⇒ `/folio` runs an atom-check.)
      - `/baton` — write a cold-resume handoff ⇒ pausing, before a long run, context filling, session end.
    - AGENCY-DIAL (3) — one dial, three detents (→ GUARDRAILS): `/solo` (autonomy max: run-to-completion, no check-ins) · `/collab` (middle default: surface non-trivial decisions) · `/plan` (deliberation max: map + get go/no-go before scope-defining acts).
    - TOOLKIT-BUILDER (4, dev-facing) — fire when you EXTEND the toolkit, not when you do science: `bash-hook-contract` (write/debug a hook: stdin-JSON in, exit-code contract out) · `toolkit-extension-authoring` (add/modify a customization: skill/agent/rule/hook shapes + install wiring) · `capability-audit` (`/capability-audit` — inventory installed agents/skills, flag duplicates, advise retire/relocate).
- STEER PERSISTENTLY: edit any `CLAUDE.md` to add durable preferences (they auto-load every turn → CONTEXT); the toolkit's always-on rules ride the same mechanism (→ PART B).
- INVARIANT: skills ARE slash commands — DESCRIBE the task and the right one auto-loads, or FORCE any `/name`; trailing text becomes `$ARGUMENTS` and skills STACK.
- COUPLES: models/effort defaults → PART B (personal defaults); the 21 skills + rules as overlay → PART B; subagents (`/agents`) → DELEGATION.

### D · ACTIONS & GUARDRAILS
- FOR: what Claude DOES (read/write files, edit, run bash) + the permission gate every action passes through.
- LIKE: a workshop with a safety interlock — the tools are powerful; the guard decides what runs unattended.
- PERMISSION VERDICTS: allow (runs) · ask (prompts you) · deny (blocked hard). Something not pre-approved ⇒ a prompt: allow once / allow always / reject.
- SAFETY DENY-LIST (toolkit-shipped): blocks `rm`, `chmod`, `curl`, `wget`, `sudo`, and reading secret files (`.env`, `.ssh`, `.aws`, `credentials.json`) ⇒ Claude cannot quietly delete or exfiltrate. A hard boundary NO mode overrides.
- ALLOW-LIST: `settings.local.json` pre-approves safe repeat commands so they run without re-prompting; `skipAutoPermissionPrompt: true` trims prompt noise for that set. Needed command denied? run it yourself, or add an allow entry.
- SCOPES MERGE (they combine, they do NOT replace): permission rules + hooks from EVERY scope apply together — global `~/.claude/settings.json` + project `.claude/settings.json` + local `.claude/settings.local.json`; each scope ADDS its rules, and deny wins over ask wins over allow. (This is CONFIG/SCOPE from the MAP.)
- PLAN MODE (deep-dive; enter via Shift+Tab until the label reads "plan mode"):
  - READ-ONLY — reads/searches/analyzes, and holds edits/writes/state-changing commands.
  - Returns a WRITTEN plan (approach + file list + steps) to approve or refine. Approving exits plan mode + executes; a rejected plan costs nothing — your files stay exactly as they were.
  - USE for: unfamiliar code, multi-file refactors, anything you want to review before it acts. Design / stats-advisor work happens naturally here (→ DELEGATION).
- INVARIANT: a deny-listed command is BLOCKED in every mode; everything else is allow/ask/deny MERGED across scopes with deny winning ⇒ Claude acts freely inside the guard, never around it.
- COUPLES: MODES set the ask/auto posture (→ LOOP); the deny-list + local allow-list are toolkit/config (→ PART B, CONFIG/SCOPE); plan mode pairs with subagents (→ DELEGATION).

### E · DELEGATION & SCALE
- FOR: keeping the main thread clean by handing bounded jobs to SUBAGENTS, and getting more done at once via BACKGROUND + parallel runs.
- LIKE: running a lab — you (lead) delegate specialized tasks to specialists + start long instruments running while you keep working.
- SUBAGENTS (a separate context + specialized prompt for one bounded job; keeps the main thread clean). The toolkit ships 5 (they mostly AUTO-FIRE from context; you can also ask explicitly, e.g. "have the code reviewer check this function"). THREE are research-facing (fire during everyday analysis) and TWO are toolkit-builder agents (dev-facing — they fire when you are extending the toolkit itself, not doing science):
  - `code-review-debugger` ⇒ R/Python/MATLAB/Julia review, debugging, optimization; fires for code QA or to verify another agent's output. [research-facing]
  - `machine-doc-reviewer` ⇒ audits a `.machine.md`/`.claude/` doc vs LLM-writing best-practices + atom-preservation; pairs with `/machine-md` + `/folio`. [research-facing]
  - `version-control-docs` ⇒ backups before risky edits, changelogs, project structure, lineage. [research-facing]
  - `agent-tooling-engineer` ⇒ builds/maintains the customization layer itself — install tiers, settings deep-merge, hook contracts, skill/agent wiring; fires when you are extending the toolkit. [dev-facing]
  - `research-data-manager` ⇒ dataset READMEs, versioning/backup conventions, project data layout, provenance; the data-hygiene counterpart to version-control-docs' code focus. [dev-facing]
- BACKGROUND + ASYNC: long commands (model fits, bootstraps, simulations) run in the BACKGROUND while Claude keeps working; you're notified on completion (push notifications + the xbeep sound → AUTOMATION). A running job never blocks — Claude advances a different thread meanwhile.
- CONFIRM "done" from the job's OWN output/sentinel, not elapsed time — silence ≠ done (per `verify-local-state`, → PART B).
- PARALLELISM: the `parallel-runs` rule ⇒ launch independent runs CONCURRENTLY within a core cap (≤ cores−2), then batch-analyze — rather than serializing independent fits. The `preflight-parallel` skill computes safe core headroom first (→ INSTRUCTIONS).
- INVARIANT: delegate bounded work to a subagent (clean main thread) + run independent jobs in parallel in the background — but read "done" from the job's own artifacts, never the clock.
- COUPLES: subagents surface in plan mode (→ GUARDRAILS); `parallel-runs` + `verify-local-state` are always-on rules (→ PART B); completion beeps/notifs (→ AUTOMATION).

### F · AUTOMATION
- FOR: behavior the HARNESS runs automatically on events — no Claude decision, no prompt needed.
- LIKE: shop sensors — a chime when a job finishes, a checklist that pops up at the right moment.
- HOOKS = scripts the harness runs on events (hooks MERGE across scopes, like permissions → GUARDRAILS). The toolkit's set is the concrete example:
  - xbeep ⇒ plays a sound on prompt-submit, on Claude finishing, and on a permission prompt. Toggle `/xbeep` (state per-session); sound = `Glass.aiff` on macOS, terminal bell elsewhere.
  - R-edit reminder (`post-edit-review.sh`, PostToolUse) ⇒ after editing an `.R` file, prints a review nudge (grep the pattern elsewhere, check edge cases); stats-model files get a k/AR1/assertion checklist.
  - completion-claim checklist (`pre-complete-verification.sh`, UserPromptSubmit) ⇒ when you type "done/finished/fixed it", prints a verify-before-confirming checklist (completeness, pattern-search, semantic asserts, magnitude sanity).
  - F1 adversary gate (`stop-adversary-gate.sh`, Stop) ⇒ on a completion claim, forks a fast `claude -p` adversary that checks the last claim for laundered reasoning (causal-verb-without-observation, efficacy-from-existence, …) and BLOCKS the stop if it catches one. This one is a GATE, not a reminder — it fails OPEN (allows) on any timeout/error so it never wedges a session, and it is dis/observe/enable-able via `crt-mode.sh`.
  - timeline logger (`timeline-logger.sh`, PostToolUse+UserPromptSubmit+Stop) ⇒ appends one JSONL row per event (ms-precision ts + epoch_ms + session_id) to `~/.claude/logs/timeline.jsonl` for session-duration/slowest-step analysis. Silent, passive.
  - ambient-time (`ambient_time.py`, UserPromptSubmit+SessionStart) ⇒ injects one down-weighted `<ambient-time>` line (local time · UTC±HH:MM · epoch · Δ-since-last-prompt). Pure stdlib, no network.
  - So the core tier wires 5 hooks: 2 stderr REMINDERS (post-edit, pre-complete) that only nudge and let work continue, 1 GATE (adversary, fail-open), and 2 passive/injecting hooks (timeline, ambient-time).
- LOOPS + WORKFLOWS (teaser): run a prompt/command on a recurring interval (`/loop 5m /check-prs`); compose skills + subagents into dynamic multi-step harnesses for repeatable jobs. Deep-dive ⇒ the ADVANCED guide set (`~/.claude/docs/advanced/`, start at `00_overview`; loops ⇒ doc 06, dynamic workflows ⇒ doc 07) + the REFERENCES blogs.
- INVARIANT: hooks fire on EVENTS deterministically (the harness runs them, not Claude). The beeps/reminders are automatic nudges (never gates); the ONE gate is the F1 adversary Stop-hook, and it fails OPEN — so no hook can ever wedge a session, but the adversary CAN block a completion claim it judges laundered.
- COUPLES: xbeep completion sound + push notifs (→ DELEGATION); the reminders encode the always-on rules (→ PART B); loops/workflows (→ ADVANCED).

## PART B · THE TOOLKIT OVERLAY (deltas on base Claude Code)
- FRAMING: base Claude Code works WITHOUT any of this. The Claude Research Toolkit is an OVERLAY that specializes it for tower/flux research — nothing here changes the primitives; it pre-loads good defaults + domain capability onto them.
- THE OVERLAY, layer by layer (each rides a PART A primitive):
  - CLAUDE.md CONTENT (CONTEXT/INSTRUCTIONS): the global `CLAUDE.md` sets AUTONOMY (work independently) + NO-CHECK-IN (skip "continue?" after every trivial step) — brisk + non-nagging, while staying INTERACTIVE by default (periodic check-ins at real decision points; `/solo` for run-to-completion). Plus SANDBOX (test junk → a `sandbox/` dir only) + debugging lessons (clarify ambiguous terms "gaps/clean/fill/fix/test"; validate SEMANTIC properties; read function internals; systematic one-var debugging; failure-rate triage <1% / 1-10% / 10-30% / >30%). ~25 folded PREFERENCES live here too (verification, stats, workflow, notation defaults). Edit any `CLAUDE.md` to add your own.
  - 8 ALWAYS-ON RULES (`.claude/rules/*`, auto-loaded — CONTEXT; one line each):
    - root-before-bandaid ⇒ fix the ROOT before suppressing a symptom (diagnose the anomaly before clamping/filtering it).
    - reproduce-before-fixing ⇒ confirm the bug at BASELINE on the real config before building a fix.
    - refactor-invariants ⇒ when a refactor DISSOLVES an abstraction, re-derive the invariants under the new structure.
    - verify-local-state ⇒ re-read cheap facts from SOURCE; re-verify before an irreversible act (kill/rm/overwrite).
    - verification-principles ⇒ cite-or-hedge causal claims; say when unchecked.
    - parallel-runs ⇒ launch independent runs concurrently within the core cap; batch-analyze.
    - doc-style ⇒ machine-vs-human doc classing; the `.machine.md` is the authoritative root.
    - r-standards ⇒ `bam(discrete=TRUE)+rho` for AR1 (over `gamm()`); `gam.check()` k-selection; tz consistency.
  - 21 SKILLS (detailed in INSTRUCTIONS) + 5 SUBAGENTS (DELEGATION) + HOOKS/beeps/reminders (AUTOMATION) + the safety DENY-LIST (GUARDRAILS) — all live in PART A; here they are named as the overlay set that specializes base Claude Code.
- PERSONAL DEFAULTS (settings; set sensibly day one — leave as-is): model `claude-fable-5[1m]` ([SUPERSEDED 2026-08-04 — supervised use only; see MODEL POLICY] ~~NEVER Opus 5~~ — Opus 5 only as a supervised `delegate:opus5-executor` child, never your session default / never bare `opus`); `CLAUDE_CODE_EFFORT_LEVEL=max`; `alwaysThinkingEnabled: true`; theme `dark-daltonized`; `tui: fullscreen`; `agentPushNotifEnabled: true` (push on completion); `feature-dev` plugin enabled; xbeep hooks + safety deny-list active.
- INVARIANT: the overlay = defaults + domain skills/rules/agents/hooks layered onto base Claude Code ⇒ remove it and Claude Code still runs; keeping it just makes it research-ready.
<!--FIG: base Claude Code + the toolkit overlay as a layer stack | 70% -->

## PART C · IN PRACTICE

### RESEARCH WORKING PATTERNS (task ⇒ toolkit response)
- fit a hierarchical Bayesian model ⇒ describe it → `brms-hierarchical-fitting`; long fit → background + `preflight-parallel`.
- fit a big temporal GAM ⇒ `mgcv-temporal-gam` (k-selection, `bam` AR1).
- gap-fill a driver series ⇒ `gap-fill-imputation` (chunk-predict-splice, provenance tiers).
- QC a met/flux series ⇒ `temporal-qc-outlier-detection`.
- cross-validate autocorrelated data ⇒ `temporal-block-cv` (never iid).
- join UTC satellite + local gauge data ⇒ `tz-safe-timestamps`.
- debug an R/Julia result that looks wrong ⇒ `code-review-debugger` + reproduce-before-fixing + root-before-bandaid.
- choose a method / defend an analysis ⇒ `research-stats-advisor` (in plan mode).
- pause / hand off ⇒ `/baton`. Run a handed-off task unattended to completion ⇒ `/solo`. Make a shareable PDF of a doc ⇒ `/folio` (add "docx" for a Word twin).
- ALWAYS: test files → `sandbox/`; independent runs → parallel + batch.

### YOUR FIRST RESEARCH SESSION (walkthrough)
1. `cd` to the repo → `claude`.
2. Shift+Tab → plan mode.
3. State the task concretely (data path, model, output path, "save plots to `sandbox/`").
4. Read the returned plan; approve or refine.
5. Approve → it edits + runs; watch the diffs + the R-edit reminders.
6. A long fit goes background — you get a beep/push on completion.
7. Review results; if a number looks wrong, ask it to reproduce-before-fixing rather than patch.
8. `/baton` to write a handoff.
9. `/folio` if you want a PDF of the write-up.
10. `/clear` before the next unrelated task.

### TROUBLESHOOTING / FAQ
- "asked permission for something safe" ⇒ allow-always, or add to `settings.local.json`.
- "a command was blocked" ⇒ it's on the safety deny-list (`rm`/`curl`/`sudo`/…) — run it yourself or allow it.
- "PDF has boxes / missing glyphs" ⇒ the TinyTeX/MacTeX PATH-shadow; force `/Library/TeX/texbin/xelatex`; `/folio`'s QA gate catches it.
- "it forgot earlier context" ⇒ auto-compaction; `/baton` then `/clear`.
- "changed a setting, no effect" ⇒ hooks/settings load at STARTUP — restart the session.
- "it stopped and asked to continue" ⇒ expected — it's interactive by default and checks in at decision points; answer / restate the goal. Want no stops at all? run it under `/solo`.
- "no beeps" ⇒ `/xbeep status`; check the sound file.
- "wrong model / too slow" ⇒ `/model`, or lower effort for trivial work.

### GLOSSARY (1 line each)
- primitive: one of Claude Code's core capability layers (CONTEXT · INSTRUCTIONS · ACTIONS+GUARDRAILS · DELEGATION · AUTOMATION · CONFIG/SCOPE); features derive from these.
- turn loop: the cycle Claude Code runs each turn — goal → load context → plan → tool-calls within permissions → review → repeat.
- overlay: the toolkit's added defaults/skills/rules/agents/hooks layered onto base Claude Code (which runs without them).
- agent / subagent: a separate specialized context Claude delegates a bounded job to.
- skill: a packaged capability that auto-loads on a trigger; also `/name` — the SAME mechanism as a slash command.
- slash command: a `/name` action (skills + built-ins, one mechanism); accepts trailing text as `$ARGUMENTS`; commands stack (`/a /b`).
- hook: a script the harness runs on an event (beeps, reminders).
- permission (allow/ask/deny): whether a tool action runs, prompts, or is blocked.
- deny-list: commands hard-blocked for safety.
- mode (normal / auto-accept / plan): the Shift+Tab permission posture.
- model tier (Opus/Sonnet/Haiku): capability vs speed/cost.
- effort: reasoning budget spent before acting.
- context window: how much text the model holds at once.
- compaction: auto-summarizing older turns as context fills.
- `/clear`: wipe context for a fresh task.
- background task: a long job that runs while Claude keeps working.
- CLAUDE.md: an always-loaded instructions file.
- rule: an always-on machine directive under `.claude/rules/`.
- sandbox: a `sandbox/` dir for throwaway test files.
- machine doc vs human doc: LLM-optimized `.machine.md` vs human-prose `.md`.
- atom: a single preserved fact/rule/step (unchanged across machine↔human translation).
- handoff: a resume-from-nothing doc (`/baton`).
- render / `/folio`: translate a machine doc to human + produce a PDF (and a docx if you add "docx").
- autonomous-mandate mode / `/solo`: run a handed-off task to completion — decide decidable things yourself; pause only for a genuine user-only choice or a named fatal blocker.
- `[1m]`: the 1-million-token context variant of a model.

### REFERENCES
- Blogs: [How we use Skills](https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills) · [Getting started with loops](https://claude.com/blog/getting-started-with-loops) · [A harness for every task: dynamic workflows](https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code).
- Docs: [skills](https://code.claude.com/docs/en/skills) · [sub-agents](https://code.claude.com/docs/en/sub-agents) · [memory](https://code.claude.com/docs/en/memory) · [settings](https://code.claude.com/docs/en/settings) · [hooks](https://code.claude.com/docs/en/hooks) · [slash-commands](https://code.claude.com/docs/en/slash-commands).

### READY FOR MORE?
- → the ADVANCED guide set (`~/.claude/docs/advanced/`, start at `00_overview.md`) — the extension architecture, loops, dynamic workflows, context engineering, and deeper automation + config.
