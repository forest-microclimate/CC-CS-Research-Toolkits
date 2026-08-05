# ADVANCED.machine.md
# STATUS: CURRENT (2026-07-12). T-24: toolkit agent count normalized to 5 (research-facing×3 + toolkit-builder×2) in §A3 FEEDS.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# ⚠ SUPERSEDED 2026-07-07 → replaced by the multi-doc set in advanced/ (start at advanced/00_overview.machine.md). Retained as historical SOURCE (docs 01/03/10 derive from it); safe to delete once the set is confirmed.
# Machine-optimized ROOT for the ADVANCED guide: "Claude Code architecture & advanced use" (power-user).
# This is the AUTHORITATIVE source; the human twin = ADVANCED.md + the PDF are DERIVED from it later (render via /folio).
# AUDIENCE: a user past the basics who wants to EXTEND + orchestrate Claude Code — the architecture (scopes,
#   skills, agents, settings, hooks) + advanced automation (loops, dynamic workflows) + authoring their own.
# STYLE: machine-terse, front-loaded, POSITIVE action-first (name the action + its trigger, not a prohibition).
# METHOD per unit: FOR (role/purpose) → HANDLE (one analogy) → mechanics → INVARIANT (the one load-bearing fact) → FEEDS (how it couples).

## A0 · ORIENTATION
- This is the ADVANCED guide: Claude Code's EXTENSION ARCHITECTURE + advanced orchestration, for a user past QUICKSTART / USAGE_DETAILED.
- TWO PARTS. PART I · THE EXTENSION SURFACE (§A1–§A9) — the FILES you add under `.claude/` + what each customizes: the scope MAP (§A1), skills/commands (§A2) + the stock-command catalog (§A2b), agents (§A3), context/memory (§A4), settings (§A5), hooks (§A6), the automation-surface pointer (§A7), the methodology sources (§A8), an authoring loop (§A9). It answers *what can I change?*
- PART II · ADVANCED METHODS & ORCHESTRATION (§M1–§M8) — how to WIELD that surface: the harness mindset (§M1), core agentic workflows (§M2), skills mastered (§M3), the pattern vocabulary (§M4), loops (§M5), dynamic workflows/harnesses (§M6), context engineering (§M7), going further (§M8). It answers *how do I get the most out of it?* Then references (§A10) + glossary (§A11).
- New BASICS term? → USAGE_DETAILED glossary. New ADVANCED term? → jump to §A11.
- Every section reads the same shape: FOR (what it's for) → HANDLE (a mental model) → mechanics → INVARIANT → FEEDS.
- This guide is itself a machine→human→PDF artifact; you are reading the machine ROOT (human twin = ADVANCED.md).

## A1 · MAP — THE EXTENSION ARCHITECTURE
- FOR: everything that customizes Claude Code — instructions, skills, agents, commands, hooks, settings — installs as FILES under a `.claude/` dir; three SCOPES decide WHO gets them.
- HANDLE: LAYERS on a global baseline — User = your defaults everywhere · Project = this repo's additions · Managed = org policy on top.
- SCOPES (three):
  - User (`~/.claude/`) ⇒ applies to EVERY session you run.
  - Project (`<repo>/.claude/`) ⇒ applies only when you launch inside that repo.
  - Managed (enterprise/admin policy) ⇒ applies org-wide, set by an administrator.
- EACH scope holds the SAME kinds of thing: `CLAUDE.md` (instructions), `rules/*.md`, `skills/<name>/SKILL.md`, `agents/*.md`, `commands/*.md`, and `settings.json` (which is where `hooks` register).
- STACK, not replace: a Project scope ADDS to the User baseline (both load); Managed sits above both. Specific scopes STACK onto the global baseline rather than overwriting it. (Settings-key PRECEDENCE conflicts resolve per §A5.)
- INVARIANT: scope == install LOCATION, and location alone decides reach — the SAME `x.md` under `~/.claude/skills/` is global, under `<repo>/.claude/skills/` is repo-only. Move the file ⇒ change its reach.
- FEEDS: every later section is one cell of this grid — skills/commands (§A2), agents (§A3), CLAUDE.md + memory (§A4), settings + precedence (§A5), hooks (§A6) all resolve through these three scopes.
<!--FIG: the three scopes (User/Project/Managed) and what loads from each | 80% -->

## A2 · SKILLS & SLASH COMMANDS (one merged mechanism)
- FOR: packaging a reusable instruction/capability you trigger by name OR let Claude auto-invoke.
- HANDLE: ONE mechanism, two file shapes — a "command" is the thin form, a "skill" is the folder form; both mint the SAME `/x`.
- BOTH create `/x`: `<repo>/.claude/commands/x.md` and `<repo>/.claude/skills/x/SKILL.md` each produce a `/x` that behaves the same.
- TWO invocation paths: Claude AUTO-INVOKES when your task matches (the `description:` is ALWAYS in context) OR you FORCE it with `/name`.
- ARGUMENTS: trailing text after the name → `$ARGUMENTS` (`/fix-issue 123` ⇒ `$ARGUMENTS`=`123`); positional `$1`, `$2`, … or `$ARGUMENTS[N]`.
- STACK: chain them — `/code-review /fix-issue 123` runs both, composed in one turn.
- ORTHOGONAL frontmatter controls (two INDEPENDENT switches):
  - `disable-model-invocation: true` ⇒ Claude STOPS auto-invoking; you can STILL `/name` it.
  - `user-invocable: false` ⇒ HIDDEN from the `/` menu; Claude CAN still invoke it.
  - ⇒ 4 states: on (auto + `/name`) · name-only (disable-model-invocation) · user-invocable-only (Claude-only, hidden from menu) · off (both set).
- CONFLICT: on a name clash, the SKILL beats the command.
- AUTHORING: `~/.claude/skills/<name>/SKILL.md` with frontmatter — `name`, `description`, `argument-hint`, `allowed-tools`, `model`, … A skill is a FOLDER ⇒ it can carry references/scripts beside `SKILL.md`.
- PROGRESSIVE DISCLOSURE: only the `description` loads up front; the body loads ON DEMAND when invoked ⇒ cheap to keep many installed.
- INVARIANT: `description:` is LOAD-BEARING — it is the matcher for auto-invocation ⇒ write it as a specific, positive, trigger-phrased sentence naming WHEN it fires, not a vague summary.
- FEEDS: skills ARE slash commands (this is the merged mechanism the basics just call "skills"); agents (§A3) are the delegated cousin; the toolkit's own `/baton` `/folio` `/machine-md` `/solo` are skills authored exactly this way (§A9).

## A2b · THE STOCK SLASH COMMANDS (built-in catalog)
- FOR: the COMPLETE set of Anthropic-shipped `/commands` you can type in a 2.1.201 session — the built-in verbs of the tool (vs the skills/agents you author yourself, §A2/§A3).
- HANDLE: a control panel — one row per built-in action; type `/` to filter the live menu, this is its annotated map.
- READ each entry as `/name <args>` ⇒ what it does, then `EX:` a concrete call. `<arg>`=required, `[arg]`=optional. `[Skill]` / `[Workflow]` tags an Anthropic-BUNDLED skill/workflow (a prompt Claude can also auto-invoke) — still stock, just not a hard-coded command.
- SOURCED from the 2.1.201 binary's command registry (`type:"local"|"local-jsx"|"prompt",name:…`) cross-checked against the published `/commands` reference; ONLY enabled + user-facing entries appear.
### SESSION & CONTEXT
- `/clear [name]` ⇒ start a fresh conversation with empty context (prior stays in `/resume`); aliases `/reset` `/new`. EX: `/clear`.
- `/compact [instructions]` ⇒ summarize the conversation so far to free context; optional focus. EX: `/compact keep the AR1 model contract + the file paths we're editing`.
- `/context [all]` ⇒ visualize what is filling the context window as a colored grid. EX: `/context`.
- `/rewind` ⇒ roll code and/or conversation back to a checkpoint, or summarize from a message; aliases `/checkpoint` `/undo`. EX: `/rewind`.
- `/resume [session]` ⇒ reopen a past conversation by id/name or via the picker; alias `/continue`. EX: `/resume`.
- `/branch [name]` ⇒ fork the conversation at this point into a copy you switch into (original preserved). EX: `/branch try-brms`.
- `/fork <directive>` ⇒ spawn a background subagent that INHERITS the full conversation and works the directive while you continue. EX: `/fork draft unit tests for the gap-fill splice`.
- `/export [filename]` ⇒ export the conversation as plain text (to a file, or clipboard). EX: `/export session.txt`.
- `/copy [N]` ⇒ copy the last (or Nth-latest) assistant response to the clipboard. EX: `/copy 2`.
- `/rename [name]` ⇒ rename the session; no arg auto-generates one from history. EX: `/rename model-refit`.
- `/btw <question>` ⇒ ask an ephemeral side question (full context, no tools) that never enters history. EX: `/btw which tz did we standardize on?`.
- `/recap` ⇒ generate a one-line summary of the session on demand. EX: `/recap`.
- `/memory` ⇒ edit `CLAUDE.md` files + view/toggle auto-memory. EX: `/memory`.
- `/add-dir <path>` ⇒ grant file access to another working directory for this session. EX: `/add-dir ../shared-data`.
- `/cd <path>` ⇒ move the session to a new working directory (cache kept; the new `CLAUDE.md` is appended). EX: `/cd projects/omega`.
- `/diff` ⇒ open an interactive viewer of uncommitted changes + per-turn diffs. EX: `/diff`.
- `/focus` ⇒ toggle the focus view (last prompt + one-line tool summary + final response); fullscreen only. EX: `/focus`.
- `/tasks` ⇒ view/manage everything running in the background this session; alias `/bashes`. EX: `/tasks`.
- `/background [prompt]` ⇒ detach the whole session to run as a background agent, freeing the terminal; alias `/bg`. EX: `/background`.
- `/stop` ⇒ stop the current background session (transcript + worktree kept). EX: `/stop`.
### MODEL, REASONING & PLANNING
- `/model [model]` ⇒ switch model + save it as the default for new sessions (`s` = this session only). EX: `/model opus`.
- `/effort [level|auto]` ⇒ set reasoning effort (`low`…`max`, `ultracode`); no arg opens a slider. EX: `/effort high`.
- `/fast [on|off]` ⇒ toggle fast mode. EX: `/fast on`.
- `/advisor [model|off]` ⇒ enable/disable a second model that advises at key moments during a task. EX: `/advisor sonnet`.
- `/plan [description]` ⇒ enter plan mode, optionally seeded with a task. EX: `/plan refactor the bam AR1 wrapper`.
### CONFIG, APPEARANCE & INPUT
- `/config [key=value …]` ⇒ open the Settings UI, or set keys inline; alias `/settings`. EX: `/config theme=dark`.
- `/theme` ⇒ change the color theme (auto/light/dark/daltonized/ANSI/custom). EX: `/theme`.
- `/statusline` ⇒ configure the status line (describe it, or auto-detect from your shell prompt). EX: `/statusline show git branch + model`.
- `/keybindings` ⇒ open your keyboard-shortcuts file. EX: `/keybindings`.
- `/terminal-setup` ⇒ install Shift+Enter + other keybindings for terminals that need it (VS Code, Zed, …). EX: `/terminal-setup`.
- `/color [color|default]` ⇒ set the prompt-bar color for this session. EX: `/color cyan`.
- `/tui [default|fullscreen]` ⇒ set the renderer + relaunch (fullscreen = flicker-free alt-screen). EX: `/tui fullscreen`.
- `/scroll-speed` ⇒ adjust mouse-wheel scroll speed (fullscreen only). EX: `/scroll-speed`.
- `/voice [hold|tap|off]` ⇒ toggle voice dictation or set its mode (needs a claude.ai account). EX: `/voice tap`.
- `/ide` ⇒ manage IDE integrations + show status. EX: `/ide`.
- `/chrome` ⇒ open Claude-in-Chrome settings. EX: `/chrome`.
### EXTENSIONS, PERMISSIONS & INTEGRATIONS
- `/permissions` ⇒ manage allow/ask/deny tool rules + working dirs; alias `/allowed-tools`. EX: `/permissions`.
- `/hooks` ⇒ view hook configurations for tool events. EX: `/hooks`.
- `/mcp [reconnect|enable|disable …]` ⇒ manage MCP server connections + OAuth. EX: `/mcp`.
- `/plugin [subcommand]` ⇒ manage plugins (`list`/`install`/`enable`/`disable`). EX: `/plugin list`.
- `/reload-plugins [--force]` ⇒ reload active plugins without restarting. EX: `/reload-plugins`.
- `/reload-skills` ⇒ re-scan skill/command dirs so on-disk changes load without a restart. EX: `/reload-skills`.
- `/skills` ⇒ list available skills (filter by name; `t` sorts by tokens; `Space` toggles visibility). EX: `/skills`.
- `/agents` ⇒ print a reminder to ask Claude to create/manage subagents (or edit `.claude/agents/`). EX: `/agents`.
- `/sandbox` ⇒ toggle sandbox mode (supported platforms only). EX: `/sandbox`.
- `/init` ⇒ generate a starter `CLAUDE.md` for the repo. EX: `/init`.
- `/install-github-app` ⇒ install the Claude GitHub App (+ optional Actions setup). EX: `/install-github-app`.
- `/install-slack-app` ⇒ install the Claude Slack app via OAuth. EX: `/install-slack-app`.
- `/setup-bedrock` ⇒ configure Amazon Bedrock auth/region/model pins (shows when `CLAUDE_CODE_USE_BEDROCK=1`). EX: `/setup-bedrock`.
- `/setup-vertex` ⇒ configure Google Vertex auth/project/region (shows when `CLAUDE_CODE_USE_VERTEX=1`). EX: `/setup-vertex`.
- `/web-setup` ⇒ connect your GitHub account to Claude Code on the web via local `gh`. EX: `/web-setup`.
- `/design-login` ⇒ authorize design-system access for `/design-sync`. EX: `/design-login`.
- `/design-sync [hint]` `[Skill]` ⇒ convert your repo's React design system + upload it to Claude Design. EX: `/design-sync Acme DS`.
### INFO, ACCOUNT & DIAGNOSTICS
- `/help` ⇒ show help + available commands. EX: `/help`.
- `/status` ⇒ open Settings on the Status tab (version, model, account, connectivity); works mid-response. EX: `/status`.
- `/usage` ⇒ show session cost, plan limits, activity stats; aliases `/cost` `/stats`. EX: `/usage`.
- `/usage-credits` ⇒ configure usage credits to keep working past a limit (was `/extra-usage`). EX: `/usage-credits`.
- `/release-notes` ⇒ view the changelog in an interactive version picker. EX: `/release-notes`.
- `/doctor` ⇒ diagnose + verify the install/settings (`f` = have Claude fix the issues). EX: `/doctor`.
- `/heapdump` ⇒ write a JS heap snapshot + memory breakdown to `~/Desktop` for high-memory diagnosis. EX: `/heapdump`.
- `/insights` ⇒ report analyzing your sessions (project areas, interaction patterns, friction points). EX: `/insights`.
- `/team-onboarding` ⇒ generate a team onboarding guide from your last 30 days of usage. EX: `/team-onboarding`.
- `/login` ⇒ sign in to your Anthropic account. EX: `/login`.
- `/logout` ⇒ sign out of your Anthropic account. EX: `/logout`.
- `/upgrade` ⇒ open the plan-upgrade page (Pro/Max only). EX: `/upgrade`.
- `/privacy-settings` ⇒ view/update privacy settings (Pro/Max only). EX: `/privacy-settings`.
- `/feedback [report]` ⇒ submit feedback / report a bug / share the conversation; aliases `/bug` `/share`. EX: `/feedback the diff viewer flickers on branch switch`.
- `/desktop` ⇒ continue the session in the Claude Code desktop app (macOS/Windows + subscription); alias `/app`. EX: `/desktop`.
- `/mobile` ⇒ show a QR code to download the mobile app; aliases `/ios` `/android`. EX: `/mobile`.
- `/powerup` ⇒ learn features through quick interactive lessons with animated demos. EX: `/powerup`.
- `/passes` ⇒ share a free week of Claude Code with friends (if eligible). EX: `/passes`.
- `/stickers` ⇒ order Claude Code stickers. EX: `/stickers`.
- `/radio` ⇒ open Claude FM lo-fi radio in the browser. EX: `/radio`.
- `/exit` ⇒ exit the CLI (detaches if attached to a background session); alias `/quit`. EX: `/exit`.
### GIT & CODE REVIEW
- `/code-review [low|…|max|ultra] [--fix] [--comment] [target]` `[Skill]` ⇒ review the working diff for correctness bugs + cleanups; `--fix` applies, `--comment` posts PR comments, `ultra` = cloud. EX: `/code-review high --fix`.
- `/simplify [target]` `[Skill]` ⇒ cleanup-only review (reuse/simplify/efficiency/altitude) that applies fixes; no bug-hunt. EX: `/simplify R/gapfill.R`.
- `/review [PR]` ⇒ run the `/code-review` engine on a GitHub PR (no arg lists open PRs). EX: `/review 123`.
- `/security-review` ⇒ scan the branch's pending changes for security vulns (injection/auth/exposure). EX: `/security-review`.
- `/ultrareview [PR]` ⇒ deep multi-agent cloud review; the preferred form is now `/code-review ultra`. EX: `/code-review ultra`.
- `/autofix-pr [prompt]` ⇒ spawn a cloud session that watches the branch's PR + pushes fixes on CI/review failures. EX: `/autofix-pr only fix lint + type errors`.
### AUTOMATION & ORCHESTRATION
- `/loop [interval] [prompt]` `[Skill]` ⇒ re-run a prompt on an interval (omit interval ⇒ self-paced); alias `/proactive`. EX: `/loop 5m check if the bam fit finished`.
- `/goal [condition|clear]` ⇒ keep working across turns until a verifiable condition is met. EX: `/goal every gam.check k-index > 0.95`.
- `/schedule [description]` ⇒ create/list/run cloud routines on a cron; alias `/routines`. EX: `/schedule nightly QC report at 6am`.
- `/batch <instruction>` `[Skill]` ⇒ decompose a large codebase change into 5–30 units, one background subagent per git worktree. EX: `/batch add roxygen docs to every R/ function`.
- `/workflows` ⇒ open the workflow progress view (watch/pause/resume/save). EX: `/workflows`.
- `/deep-research <question>` `[Workflow]` ⇒ fan out web searches, cross-check sources, synthesize a cited report. EX: `/deep-research recent evidence on stomatal-optimization models`.
- `/ultraplan <prompt>` ⇒ draft a plan in a cloud session, review it in-browser, then execute remotely or send it back. EX: `/ultraplan design the next analysis phase`.
- `/remote-control` ⇒ make this local session controllable from claude.ai; alias `/rc`. EX: `/remote-control`.
- `/remote-env` ⇒ choose the default environment for cloud agents. EX: `/remote-env`.
- `/teleport` ⇒ pull a Claude-Code-on-the-web session into this terminal; alias `/tp`. EX: `/teleport`.
### BUNDLED DEV & DATA SKILLS (`[Skill]` = Anthropic-shipped skills, auto-invocable)
- `/debug [description]` `[Skill]` ⇒ enable session debug logging + troubleshoot by reading the debug log. EX: `/debug chains split at iteration 3500`.
- `/verify` `[Skill]` ⇒ confirm a change works by building + running the app + observing, not just tests. EX: `/verify`.
- `/run` `[Skill]` ⇒ launch + drive your project's app to see a change working. EX: `/run`.
- `/run-skill-generator` `[Skill]` ⇒ author a per-project skill teaching `/run` + `/verify` how to build/launch/drive the app. EX: `/run-skill-generator`.
- `/dataviz [request]` `[Skill]` ⇒ chart/dashboard design guidance (form, colorblind-safe palette, marks, a11y). EX: `/dataviz seasonal flux by sensor height`.
- `/claude-api [migrate|managed-agents-onboard]` `[Skill]` ⇒ load Claude API reference for your language; `migrate` upgrades model IDs. EX: `/claude-api`.
- `/fewer-permission-prompts` `[Skill]` ⇒ scan transcripts for common read-only calls + add a project allowlist. EX: `/fewer-permission-prompts`.
- NOT IN THIS CATALOG (in the 2.1.201 binary yet not user-facing): REMOVED — `/pr-comments` (gone since 2.1.91 ⇒ ask Claude to view PR comments) · `/vim` (gone since 2.1.92 ⇒ `/config` → Editor mode). DISABLED / flag-gated (`isEnabled` false) — `/wellbeing` `/brief` `/version` `/loops` `/update`. INTERNAL actions the harness fires (not typed) — `autocompact` `daemon` `session` `pause-memory` `skill-doctor` `pro-trial-expired` `rate-limit-options` `design-consent`/`design-revoke` `extra-usage`(legacy alias of `/usage-credits`).
- INVARIANT: availability is CONDITIONAL — an entry shows only when its `isEnabled()` passes for your platform/plan/env (`/setup-bedrock` needs `CLAUDE_CODE_USE_BEDROCK=1`; `/upgrade` is Pro/Max) ⇒ the live `/` menu is ground truth for YOUR session, and this catalog is the 2.1.201 superset.
- FEEDS: these built-ins compose with your authored skills/commands (§A2 — a `SKILL` beats a built-in on a name clash) + agents (§A3); the automation verbs (`/loop` `/goal` `/schedule` `/workflows` `/batch`) are the §A7 layer; `/config` `/permissions` `/hooks` `/mcp` are the front doors to §A5/§A6.
<!--FIG: the stock `/` menu grouped by category (session · model · config · info · git · automation · skills) | 75% -->

## A3 · AGENTS & SUBAGENTS (the same thing)
- FOR: handing a bounded job to a SEPARATE context window so the main thread stays clean.
- HANDLE: a subagent = an agent the main agent calls; "subagent" names the RELATIONSHIP, not a different kind of thing.
- SAME THING: an agent invoked BY the main agent runs in its OWN fresh context window; only its SUMMARY returns to the main thread.
- DEFINED in `.claude/agents/*.md` — frontmatter: `name` + `description` REQUIRED; optional `tools`, `model`, `effort`, `isolation`.
- INVOKED 3 ways: (1) AUTOMATIC delegation when the `description` matches the task · (2) `@agent-<name>` to FORCE one · (3) the Agent tool programmatically (renamed from Task; `Task()` still ALIASES it).
- BUILT-INS: `Explore` (read-only search), `Plan` (design a plan), `general-purpose` (catch-all).
- FORK: a `fork` INHERITS the full parent conversation (starts WITH the main thread's context) — contrast a normal subagent, which starts FRESH (empty).
- INVARIANT: a subagent spends a SEPARATE context window ⇒ its intermediate exploration/verification does NOT accrue to the main thread; only the distilled summary returns. That isolation IS the reason to delegate.
- FEEDS: dynamic workflows (§A7) orchestrate MANY subagents into a harness; the toolkit's 5 agents (research-facing: code-review-debugger, machine-doc-reviewer, version-control-docs; toolkit-builder: agent-tooling-engineer, research-data-manager) are authored this way (§A9); delegating keeps context clean (§A4).
<!--FIG: main agent delegating to isolated subagent contexts, each returning a summary | 75% -->

## A4 · CONTEXT, MEMORY & CLAUDE.md
- FOR: what Claude KNOWS at the start of a turn — two channels: auto-memory (CLAUDE writes) + CLAUDE.md (YOU write).
- HANDLE: memory = a notebook Claude keeps for itself across sessions; CLAUDE.md = the standing orders YOU pin.
- AUTO-MEMORY: `~/.claude/projects/<git-root-slug>/memory/` — keyed by the git REPO ROOT, machine-local, CLAUDE writes learnings there. Only the FIRST ~200 lines / 25 KB of `MEMORY.md` load at start ⇒ keep the top dense.
- CLAUDE.md: YOU write instructions; loads in FULL (no truncation) ⇒ the place for durable directives.
- HIERARCHY CONCATENATES broad→specific: managed → `~/.claude/CLAUDE.md` → `./CLAUDE.md` or `./.claude/CLAUDE.md` → `./CLAUDE.local.md`. Every present level combines.
- `@import <path>` pulls another file's content in (nesting depth up to 4).
- `.claude/rules/*.md` load like CLAUDE.md (always-on); a `paths:` frontmatter SCOPES a rule to file globs ⇒ it loads only when a matching file is in play.
- MANAGED BLOCK: this toolkit assembles its global CLAUDE.md INSIDE markers — `<!-- >>> claude-research-toolkit (managed) >>> -->` … `<!-- <<< claude-research-toolkit (managed) <<< -->` ⇒ a re-install regenerates ONLY that block; YOUR content OUTSIDE the markers survives.
- TRANSCRIPTS: `~/.claude/projects/<slug>/<sessionId>.jsonl` = the full turn history ⇒ `claude --resume` / `--continue` / `--fork-session` re-open it; the `.jsonl` is portable across machines.
- INVARIANT: memory is TRUNCATED at load (~200 lines / 25 KB), CLAUDE.md is NOT ⇒ put anything that MUST always be seen in CLAUDE.md / a rule, not deep inside a memory file.
- FEEDS: the always-on rules ride this loader; the managed block is why the toolkit re-installs without clobbering you (§A5); transcripts underpin resume (§A8).

## A5 · SETTINGS, SCOPES & THE DIRECTORY HIERARCHY
- FOR: configuring the harness — model, permissions, env, hooks, output style — per scope.
- HANDLE: a precedence LADDER — the closer/more-privileged the layer, the higher it wins; BUT two keys (hooks, permissions) COMBINE instead of fighting.
- PRECEDENCE high→low: Managed > CLI args > `<repo>/.claude/settings.local.json` (personal, gitignored) > `<repo>/.claude/settings.json` (shared, committed) > `~/.claude/settings.json` (global).
- IMPORTANT — MERGE, not replace, for two keys: `hooks` AND `permissions` MERGE across ALL scopes (every layer's entries combine); they do NOT override each other. (Scalar keys like `model` take the single highest-precedence value.)
- MAIN KEYS: `model`, `permissions` (allow/ask/deny), `env`, `hooks`, `outputStyle`, `autoMemoryEnabled`, `statusLine`, …
- DIFFERENT RULES PER PROJECT: shared committed guidance in each `<repo>/.claude/` (CLAUDE.md, rules, `settings.json`) · personal per-repo bits in `<repo>/.claude/settings.local.json` + `CLAUDE.local.md` (gitignored) · cross-project defaults in `~/.claude/`.
- THIS TOOLKIT deep-merges `~/.claude/settings.json` from 4 FRAGMENTS = the install tiers: core (permissions.deny + 4 dev-hook registrations across PostToolUse/UserPromptSubmit/Stop) + ambient-time (ambient_time.py on UserPromptSubmit+SessionStart) + ergonomics (xbeep hooks) + personal (model/theme/tui/effort/plugin) ⇒ a re-install adds keys without clobbering existing ones.
- INVARIANT: for `hooks` + `permissions`, MORE layers = MORE entries (union) ⇒ a deny in ANY scope still bites and a hook in ANY scope still fires; you cannot un-set them from a lower layer, only ADD.
- FEEDS: the merged `permissions.deny` is the safety boundary; the merged `hooks` are §A6; the deep-merge is why the toolkit's tiers compose (§A9).
<!--FIG: settings precedence ladder + which layers merge vs override | 70% -->

## A6 · HOOKS, DEEPLY
- FOR: deterministic automation the HARNESS runs on events — NOT Claude choosing to.
- HANDLE: event listeners for your session — a script fires on "edit happened" / "prompt submitted" / "Claude stopped", every time, mechanically.
- MECHANISM: hooks = scripts the harness executes on EVENTS (deterministic; Claude does not decide whether they run).
- CONFIGURED in `settings.json`: `hooks → <Event> → [{ matcher, hooks: [{ type: "command", command }] }]`.
- ~30 EVENTS: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `SessionStart`, `PreCompact`, `Notification`, …
- I/O CONTRACT: context arrives as JSON on STDIN. exit 0 = OK (stdout MAY carry JSON to control the harness); exit 2 = BLOCK the action + stderr is fed BACK to Claude.
- AUTHOR YOUR OWN: add a script + register it in `settings.json` under the event. LIVE examples in this toolkit: `post-edit-review.sh` (PostToolUse on `Edit|Write` ⇒ R-edit review nudge), `pre-complete-verification.sh` (UserPromptSubmit ⇒ verify-before-"done" checklist), `xbeep` (Notification / Stop / UserPromptSubmit beeps).
- READ STDIN, not env: current Claude Code passes hook data as JSON on STDIN (the old `CLAUDE_*` env vars are no longer set) ⇒ parse e.g. `tool_input.file_path` from stdin.
- INVARIANT: hooks run on the EVENT, not on Claude's judgment ⇒ they are the right tool for "ALWAYS do X when Y happens" — a memory/preference can't guarantee it; a hook can.
- FEEDS: registered via the settings `hooks` key (§A5, which MERGES across scopes ⇒ a hook in any scope fires); the toolkit ships them in the core + ergonomics tiers (§A9).

## A7 · AUTOMATION — LOOPS & DYNAMIC WORKFLOWS
- FOR: running work UNATTENDED — repeat on a schedule (loops) or orchestrate many agents to beat single-context failure modes (workflows).
- HANDLE: loops = a cron for one command; a workflow = a purpose-built assembly line of subagents.
### LOOPS
- `/loop <interval> <command>` ⇒ re-run a command every interval. EX: `/loop 5m check my PR, address review comments, fix failing CI`.
- `/schedule` ⇒ move a loop to the CLOUD (runs without your terminal open).
- `/goal <objective>, stop after N tries` ⇒ ITERATE until a VERIFIABLE condition (or N attempts).
- USE-WHEN: recurring work with CLEAR, VERIFIABLE exit criteria; prefer DETERMINISTIC tests over judgment; MANAGE tokens — pilot small, match the interval to the real change rate.
### WORKFLOWS / HARNESSES
- WHAT: a dynamic workflow AUTO-GENERATES a multi-agent HARNESS — a JS file coordinating subagents with ISOLATED contexts — to combat single-context failure modes (stopping early, self-preference bias, goal drift).
- TRIGGER: ask for a "workflow", or say `ultracode`.
- PATTERNS (5): classify-and-act (router → specialists) · fan-out-and-synthesize (split into N → agent-per-item → barrier → merge) · adversarial-verification (a FRESH agent scores each output) · tournament (N approaches, pairwise judged) · loop-until-done (spawn until "no new findings").
- USE-WHEN: COMPLEX, HIGH-VALUE tasks (higher token cost) ⇒ set a TOKEN BUDGET.
- SAVE: press "s" ⇒ stored in `~/.claude/workflows`.
- INVARIANT: the leverage is ISOLATED contexts — each subagent gets a clean window, so an adversarial verifier or a per-item worker cannot inherit the orchestrator's bias or bloat; that separation is what beats the single-context failure modes.
- FEEDS: harnesses are subagent orchestration (§A3) at scale; loops + goals are the automation layer over the whole toolkit.
<!--FIG: a fan-out-and-synthesize harness: extract → per-item subagents → adversarial verify → merge | 80% -->

## A8 · THE METHODOLOGY DOCS
- FOR: the canonical write-ups behind the toolkit's headline behaviors — shipped but currently UNDOCUMENTED in the two usage guides.
- HANDLE: the 4 "why/how" source docs that specific skills/rules DERIVE from — edit the source to change the behavior.
- LOCATION: `~/.claude/methodology/` — 3 machine docs.
- AUTONOMY_MANDATE ⇒ the canonical autonomy rule that `/solo` derives from.
- HANDOFF_PROTOCOL ⇒ how to write a resumable handoff; underpins `/baton`.
- DOC_STYLE_MACHINE_VS_HUMAN ⇒ the machine-vs-human doc method; underpins the `doc-style` rule + `/folio`.
- INVARIANT: each doc is the AUTHORITATIVE source its skill/rule points back to ⇒ change the behavior by editing the methodology doc, not the derived skill in isolation.
- FEEDS: `/solo` (§A2), `/baton`, `/folio`, the `doc-style` rule (§A4/§A5).

## A9 · AUTHORING YOUR OWN EXTENSIONS
- FOR: a repeatable loop to build your own skill / agent / rule / hook to the toolkit's own standard.
- THE LOOP: draft with `/machine-md` (applies LLM-doc best-practices) → audit with the `machine-doc-reviewer` agent → render a human/PDF twin with `/folio`.
- APPLIES to: skills, agents, rules, hooks (any `.claude/` extension).
- TYING IT TOGETHER: everything in this guide is a FILE under a scope (§A1) ⇒ authoring an extension = write the file in the right SHAPE (a skill folder §A2 / an agent `.md` §A3 / a rule with `paths:` §A4 / a hook script + a `settings.json` registration §A6), place it in the SCOPE whose reach you want (§A1/§A5), then restart the session to load it. The `/machine-md` → `machine-doc-reviewer` → `/folio` loop keeps the machine root, its audit, and its human twin in sync; the `doc-style` rule keeps the machine `.machine.md` as the authoritative source and the human `.md` / PDF as derived artifacts.

## A10 · REFERENCES
- Blogs:
  - [How we use Skills](https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills)
  - [Getting started with loops](https://claude.com/blog/getting-started-with-loops)
  - [A harness for every task: dynamic workflows](https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code)
- Docs:
  - [Skills](https://code.claude.com/docs/en/skills)
  - [Subagents](https://code.claude.com/docs/en/sub-agents)
  - [Memory](https://code.claude.com/docs/en/memory)
  - [Settings](https://code.claude.com/docs/en/settings)
  - [Hooks](https://code.claude.com/docs/en/hooks)
  - [Slash commands](https://code.claude.com/docs/en/slash-commands)
  - [Common workflows](https://code.claude.com/docs/en/common-workflows)
  - [Interactive mode](https://code.claude.com/docs/en/interactive-mode)
  - [CLI reference](https://code.claude.com/docs/en/cli-reference)

## A11 · GLOSSARY (advanced)
- scope: the install LOCATION (User `~/.claude/` · Project `<repo>/.claude/` · Managed) that decides a customization's reach (§A1).
- managed policy: enterprise/admin-set config + permissions that apply org-wide and take TOP precedence (§A5).
- fork: a subagent that INHERITS the full parent conversation (vs a fresh empty subagent) (§A3); also `--fork-session` on a transcript (§A4).
- `$ARGUMENTS`: the trailing text passed to a slash command (`/fix-issue 123` ⇒ `123`); positional `$1` / `$ARGUMENTS[N]` (§A2).
- skill stacking: chaining skills/commands so they compose in one turn (`/code-review /fix-issue 123`) (§A2).
- harness: an auto-generated JS orchestrator coordinating subagents in isolated contexts (§A7).
- orchestration pattern: a harness shape — classify-and-act / fan-out-and-synthesize / adversarial-verification / tournament / loop-until-done (§A7).
- transcript: the `~/.claude/projects/<slug>/<sessionId>.jsonl` full turn history that `--resume` / `--continue` / `--fork-session` re-open (§A4).
- managed block: the `>>> claude-research-toolkit (managed) >>>` … `<<<` markers the installer regenerates, leaving your out-of-block content intact (§A4).
- `@import`: a CLAUDE.md directive that pulls another file's content in (nesting depth up to 4) (§A4).
