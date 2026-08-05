# 02_skills_and_commands.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: SKILLS & SLASH COMMANDS — one merged mechanism · how to AUTHOR great skills (mastered) · the complete stock-command catalog.
# FOR: a user packaging reusable capability (skills == commands), authoring their own, + wielding the built-in verbs. Part of the ADVANCED set — map + REFERENCES in 00_overview.machine.md.
# STYLE: machine-terse, front-loaded, POSITIVE action-first; per-unit shape FOR -> HANDLE -> mechanics -> INVARIANT -> FEEDS. Paraphrased facts (SKILLS-MASTERED) carry an inline hyperlink citation.

## 02.1 · SKILLS & SLASH COMMANDS (one merged mechanism)
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
- FEEDS: skills ARE slash commands (this is the merged mechanism the basics just call "skills"); agents (03_agents) are the delegated cousin; the toolkit's own `/baton` `/folio` `/machine-md` `/solo` are skills authored exactly this way (10_authoring).

## 02.2 · SKILLS, MASTERED
- FOR: the deepest extension point — turning a general Claude into a SPECIALIST at YOUR task, cheaply, via a folder it loads only when relevant.
- HANDLE: "building a skill for an agent is like putting together an onboarding guide for a new hire" — the doc a competent generalist needs to do THIS job THIS team's way ([Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)).
- **A skill is a FOLDER, not a file.** The common misconception is that skills are "'just markdown files.' They're actually folders that can include scripts, assets, data, etc. that the agent can discover, explore and manipulate" ([How we use Skills](https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills)) — "organized folders of instructions, scripts, and resources that agents can discover and load dynamically" ([Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)).
- **Progressive disclosure = the filesystem AS context engineering.** Three load levels: (1) the `description` metadata loads at startup into the system prompt; (2) the `SKILL.md` body loads only when Claude judges the skill relevant; (3) linked `references/*` files Claude "can choose to navigate and discover only as needed." Because Claude reads files on demand, "the amount of context that can be bundled into a skill is effectively unbounded" — you organize knowledge ACROSS files and pay context ONLY for the branch a task actually touches ([Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)). This is the budget principle (00_overview · the harness mindset) made mechanical.
- THE NINE CATEGORIES — a good skill fits exactly ONE cleanly ([How we use Skills](https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills)):
  - library / API reference ⇒ how to call a specific SDK or service correctly.
  - product verification ⇒ confirm a feature actually works end-to-end.
  - data fetching / analysis ⇒ pull + crunch a dataset on demand.
  - business-process automation ⇒ a team's recurring procedure (standup, triage, reporting).
  - code scaffolding ⇒ templates for new components/modules.
  - code quality / review ⇒ your lint + review conventions.
  - CI-CD / deployment ⇒ the ship / release sequence.
  - runbooks ⇒ step-by-step incident / on-call response.
  - infra ops ⇒ provisioning + infrastructure actions.
- HIGH-LEVERAGE AUTHORING TIPS ([How we use Skills](https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills)):
  - **Lead with the Gotchas — the highest-signal section.** "The highest-signal content in any skill is the Gotchas section"; build it "from common failure points" you actually hit ⇒ encode the traps, not the happy path Claude can already do.
  - **Write the `description` FOR THE MODEL (a trigger spec, not a summary).** It is the activation criterion, the ONLY part loaded until the skill fires ⇒ include the words a user will actually say ("babysit", "deploy") so Claude recognizes the moment to invoke it.
  - **Ship scripts; don't make Claude rebuild boilerplate.** Bundle helper code so Claude "composes existing logic rather than reconstructing boilerplate"; deterministic ops (sorting, parsing) belong in a script, cheaper and exact, not re-derived each turn ([Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)) ⇒ spend turns on composition, not reconstruction.
  - **Help Claude remember (persist, then report only the DELTA).** Write logs / JSON / SQLite to a stable path (e.g. `${CLAUDE_PLUGIN_DATA}`) so the next run "reads its own history" (a standup skill keeps a `standups.log` of every post) and reports only what changed since last time.
  - **Gate with on-demand hooks (active ONLY while the skill runs).** Ship a hook inside the skill — e.g. a `/careful` PreToolUse guard that blocks `rm -rf` / `DROP TABLE` during a production task, and stops constraining you the rest of the time ⇒ enforcement scoped to the risky window.
  - **Give latitude, not rails (avoid railroading).** Provide the information + the freedom to adapt to context, not a rigid step list Claude cannot deviate from when the situation differs.
  - **Skip the obvious.** Claude already codes ⇒ don't spend context restating generic practice; spend it on what pushes Claude OUT of its defaults — your conventions, your gotchas, your non-obvious constraints.
  - **Design the setup deliberately.** Use a `config.json` plus the `AskUserQuestion` tool to gather what the skill needs up front, rather than discovering it mid-task.
- **Compose skills by name.** Reference another installed skill inside your instructions and Claude "will invoke them as needed without explicit dependency management" ([How we use Skills](https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills)) ⇒ build small single-purpose skills and let them chain.
- **Distribute by scale.** Small team / few repos ⇒ check skills into `.claude/skills`. Scaling up ⇒ "publish plugins to internal or public marketplaces, letting users install selectively" ([How we use Skills](https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills)).
- **Measure with a usage log.** A PreToolUse hook that logs every skill invocation company-wide reveals which skills are popular and which "under-trigger" and need a better `description` or better discovery ([How we use Skills](https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills)).
- INVARIANT: the `description` is the ONLY part loaded until a trigger fires ⇒ it alone decides whether the skill EVER activates; a precise, trigger-worded description outweighs a perfect body Claude never reaches.
- FEEDS: skills ARE the §02.1 slash-command mechanism; their on-demand hooks + `/careful` guard + usage log are §01.4 (hooks); plugin distribution rides §02.3 `/plugin` + a marketplace; the authoring loop is §10.1 (`/machine-md` → `machine-doc-reviewer` → `/folio`).
<!--FIG: the nine skill categories as a 3×3 taxonomy grid, each cell naming the category + one example skill | 70% -->
<!--FIG: progressive disclosure — `SKILL.md` at the root fanning out to `references/api.md`, `references/stuck-jobs.md`, `scripts/deploy.sh`; each edge labeled with the SITUATION that triggers the load (e.g. "hit a stuck job" ⇒ stuck-jobs.md) | 80% -->

## 02.3 · THE STOCK SLASH COMMANDS (built-in catalog)
- FOR: the COMPLETE set of Anthropic-shipped `/commands` you can type in a 2.1.201 session — the built-in verbs of the tool (vs the skills/agents you author yourself, §02.1/03_agents).
- HANDLE: a control panel — one row per built-in action; type `/` to filter the live menu, this is its annotated map.
- READ each entry as `/name <args>` ⇒ what it does, then (WHERE IT TEACHES) an `EX:` concrete call. `<arg>`=required, `[arg]`=optional. `[Skill]` / `[Workflow]` tags an Anthropic-BUNDLED skill/workflow (a prompt Claude can also auto-invoke) — still stock, just not a hard-coded command.
- EX POLICY: an `EX:` appears ONLY where a concrete call teaches BEYOND the syntax line (a real argument, a non-obvious form, the phrasing you'd actually type); arg-less / self-evident commands carry NONE by design — absence is intentional, not an omission.
- SOURCED from the 2.1.201 binary's command registry (`type:"local"|"local-jsx"|"prompt",name:…`) cross-checked against the published `/commands` reference; ONLY enabled + user-facing entries appear.
### SESSION & CONTEXT
- `/clear [name]` ⇒ start a fresh conversation with empty context (prior stays in `/resume`); aliases `/reset` `/new`.
- `/compact [instructions]` ⇒ summarize the conversation so far to free context; optional focus. EX: `/compact keep the AR1 model contract + the file paths we're editing`.
- `/context [all]` ⇒ visualize what is filling the context window as a colored grid.
- `/rewind` ⇒ roll code and/or conversation back to a checkpoint, or summarize from a message; aliases `/checkpoint` `/undo`.
- `/resume [session]` ⇒ reopen a past conversation by id/name or via the picker; alias `/continue`.
- `/branch [name]` ⇒ fork the conversation at this point into a copy you switch into (original preserved). EX: `/branch try-brms`.
- `/fork <directive>` ⇒ spawn a background subagent that INHERITS the full conversation and works the directive while you continue. EX: `/fork draft unit tests for the gap-fill splice`.
- `/export [filename]` ⇒ export the conversation as plain text (to a file, or clipboard). EX: `/export session.txt`.
- `/copy [N]` ⇒ copy the last (or Nth-latest) assistant response to the clipboard. EX: `/copy 2`.
- `/rename [name]` ⇒ rename the session; no arg auto-generates one from history. EX: `/rename model-refit`.
- `/btw <question>` ⇒ ask an ephemeral side question (full context, no tools) that never enters history. EX: `/btw which tz did we standardize on?`.
- `/recap` ⇒ generate a one-line summary of the session on demand.
- `/memory` ⇒ edit `CLAUDE.md` files + view/toggle auto-memory.
- `/add-dir <path>` ⇒ grant file access to another working directory for this session. EX: `/add-dir ../shared-data`.
- `/cd <path>` ⇒ move the session to a new working directory (cache kept; the new `CLAUDE.md` is appended). EX: `/cd projects/omega`.
- `/diff` ⇒ open an interactive viewer of uncommitted changes + per-turn diffs.
- `/focus` ⇒ toggle the focus view (last prompt + one-line tool summary + final response); fullscreen only.
- `/tasks` ⇒ view/manage everything running in the background this session; alias `/bashes`.
- `/background [prompt]` ⇒ detach the whole session to run as a background agent, freeing the terminal; alias `/bg`.
- `/stop` ⇒ stop the current background session (transcript + worktree kept).
### MODEL, REASONING & PLANNING
- `/model [model]` ⇒ switch model + save it as the default for new sessions (`s` = this session only). EX: `/model opus`.
- `/effort [level|auto]` ⇒ set reasoning effort (`low`…`max`, `ultracode`); no arg opens a slider. EX: `/effort high`.
- `/fast [on|off]` ⇒ toggle fast mode — Opus with FASTER output (NOT a smaller/weaker model); same model, quicker responses. EX: `/fast on`.
- `/advisor [model|off]` ⇒ enable/disable a second model that advises at key moments during a task. EX: `/advisor sonnet`.
- `/plan [description]` ⇒ enter plan mode, optionally seeded with a task. EX: `/plan refactor the bam AR1 wrapper`.
### CONFIG, APPEARANCE & INPUT
- `/config [key=value …]` ⇒ open the Settings UI, or set keys inline; alias `/settings`. EX: `/config theme=dark`.
- `/theme` ⇒ change the color theme (auto/light/dark/daltonized/ANSI/custom).
- `/statusline` ⇒ configure the status line (describe it, or auto-detect from your shell prompt). EX: `/statusline show git branch + model`.
- `/keybindings` ⇒ open your keyboard-shortcuts file.
- `/terminal-setup` ⇒ install Shift+Enter + other keybindings for terminals that need it (VS Code, Zed, …).
- `/color [color|default]` ⇒ set the prompt-bar color for this session. EX: `/color cyan`.
- `/tui [default|fullscreen]` ⇒ set the renderer + relaunch (fullscreen = flicker-free alt-screen). EX: `/tui fullscreen`.
- `/scroll-speed` ⇒ adjust mouse-wheel scroll speed (fullscreen only).
- `/voice [hold|tap|off]` ⇒ toggle voice dictation or set its mode (needs a claude.ai account). EX: `/voice tap`.
- `/ide` ⇒ manage IDE integrations + show status.
- `/chrome` ⇒ open Claude-in-Chrome settings.
### EXTENSIONS, PERMISSIONS & INTEGRATIONS
- `/permissions` ⇒ manage allow/ask/deny tool rules + working dirs; alias `/allowed-tools`.
- `/hooks` ⇒ view hook configurations for tool events.
- `/mcp [reconnect|enable|disable …]` ⇒ manage MCP server connections + OAuth.
- `/plugin [subcommand]` ⇒ manage plugins (`list`/`install`/`enable`/`disable`). EX: `/plugin list`.
- `/reload-plugins [--force]` ⇒ reload active plugins without restarting.
- `/reload-skills` ⇒ re-scan skill/command dirs so on-disk changes load without a restart.
- `/skills` ⇒ list available skills (filter by name; `t` sorts by tokens; `Space` toggles visibility).
- `/agents` ⇒ print a reminder to ask Claude to create/manage subagents (or edit `.claude/agents/`).
- `/sandbox` ⇒ toggle sandbox mode (supported platforms only).
- `/init` ⇒ generate a starter `CLAUDE.md` for the repo.
- `/install-github-app` ⇒ install the Claude GitHub App (+ optional Actions setup).
- `/install-slack-app` ⇒ install the Claude Slack app via OAuth.
- `/setup-bedrock` ⇒ configure Amazon Bedrock auth/region/model pins (shows when `CLAUDE_CODE_USE_BEDROCK=1`).
- `/setup-vertex` ⇒ configure Google Vertex auth/project/region (shows when `CLAUDE_CODE_USE_VERTEX=1`).
- `/web-setup` ⇒ connect your GitHub account to Claude Code on the web via local `gh`.
- `/design-login` ⇒ authorize design-system access for `/design-sync`.
- `/design-sync [hint]` `[Skill]` ⇒ convert your repo's React design system + upload it to Claude Design. EX: `/design-sync Acme DS`.
### INFO, ACCOUNT & DIAGNOSTICS
- `/help` ⇒ show help + available commands.
- `/status` ⇒ open Settings on the Status tab (version, model, account, connectivity); works mid-response.
- `/usage` ⇒ show session cost, plan limits, activity stats; aliases `/cost` `/stats`.
- `/usage-credits` ⇒ configure usage credits to keep working past a limit (was `/extra-usage`).
- `/release-notes` ⇒ view the changelog in an interactive version picker.
- `/doctor` ⇒ diagnose + verify the install/settings (`f` = have Claude fix the issues).
- `/heapdump` ⇒ write a JS heap snapshot + memory breakdown to `~/Desktop` for high-memory diagnosis.
- `/insights` ⇒ report analyzing your sessions (project areas, interaction patterns, friction points) — READ it to ACT: turn a recurring friction into a rule/skill, a fact you keep re-explaining into a `CLAUDE.md` line, a slow manual step into a hook. The VALUE is the follow-up, not the report.
- `/team-onboarding` ⇒ generate a team onboarding guide from your last 30 days of usage — captures the tools + workflows + conventions your team ACTUALLY uses, so a newcomer ramps on the real setup, not the docs' ideal.
- `/login` ⇒ sign in to your Anthropic account.
- `/logout` ⇒ sign out of your Anthropic account.
- `/upgrade` ⇒ open the plan-upgrade page (Pro/Max only).
- `/privacy-settings` ⇒ view/update privacy settings (Pro/Max only).
- `/feedback [report]` ⇒ submit feedback / report a bug / share the conversation; aliases `/bug` `/share`. EX: `/feedback the diff viewer flickers on branch switch`.
- `/desktop` ⇒ continue the session in the Claude Code desktop app (macOS/Windows + subscription); alias `/app`.
- `/mobile` ⇒ show a QR code to download the mobile app; aliases `/ios` `/android`.
- `/powerup` ⇒ learn features through quick interactive lessons with animated demos.
- `/passes` ⇒ share a free week of Claude Code with friends (if eligible).
- `/stickers` ⇒ order Claude Code stickers.
- `/radio` ⇒ open Claude FM lo-fi radio in the browser.
- `/exit` ⇒ exit the CLI (detaches if attached to a background session); alias `/quit`.
### GIT & CODE REVIEW
- `/code-review [low|…|max|ultra] [--fix] [--comment] [target]` `[Skill]` ⇒ review the working diff for correctness bugs + cleanups; `--fix` applies, `--comment` posts PR comments, `ultra` = cloud. EX: `/code-review high --fix`.
- `/simplify [target]` `[Skill]` ⇒ cleanup-only review (reuse/simplify/efficiency/altitude) that applies fixes; no bug-hunt. EX: `/simplify R/gapfill.R`.
- `/review [PR]` ⇒ run the `/code-review` engine on a GitHub PR (no arg lists open PRs). EX: `/review 123`.
- `/security-review` ⇒ scan the branch's pending changes for security vulns (injection/auth/exposure).
- `/ultrareview [PR]` ⇒ deep multi-agent cloud review; the preferred form is now `/code-review ultra`. EX: `/code-review ultra`.
- `/autofix-pr [prompt]` ⇒ spawn a cloud session that watches the branch's PR + pushes fixes on CI/review failures. EX: `/autofix-pr only fix lint + type errors`.
### AUTOMATION & ORCHESTRATION
- `/loop [interval] [prompt]` `[Skill]` ⇒ re-run a prompt on an interval (omit interval ⇒ self-paced); alias `/proactive`. EX: `/loop 5m check if the bam fit finished`.
- `/goal [condition|clear]` ⇒ keep working across turns until a verifiable condition is met. EX: `/goal every gam.check k-index > 0.95`.
- `/schedule [description]` ⇒ create/list/run cloud routines on a cron; alias `/routines`. EX: `/schedule nightly QC report at 6am`.
- `/batch <instruction>` `[Skill]` ⇒ decompose a large codebase change into 5–30 units, one background subagent per git worktree. EX: `/batch add roxygen docs to every R/ function`.
- `/workflows` ⇒ open the workflow progress view (watch/pause/resume/save).
- `/deep-research <question>` `[Workflow]` ⇒ fan out web searches, cross-check sources, synthesize a cited report. EX: `/deep-research recent evidence on stomatal-optimization models`.
- `/ultraplan <prompt>` ⇒ draft a plan in a cloud session, review it in-browser, then execute remotely or send it back. EX: `/ultraplan design the next analysis phase`.
- `/remote-control` ⇒ make this local session controllable from claude.ai; alias `/rc`.
- `/remote-env` ⇒ choose the default environment for cloud agents.
- `/teleport` ⇒ pull a Claude-Code-on-the-web session into this terminal; alias `/tp`.
### BUNDLED DEV & DATA SKILLS (`[Skill]` = Anthropic-shipped skills, auto-invocable)
- `/debug [description]` `[Skill]` ⇒ enable session debug logging + troubleshoot by reading the debug log. EX: `/debug chains split at iteration 3500`.
- `/verify` `[Skill]` ⇒ confirm a change works by building + running the app + observing, not just tests.
- `/run` `[Skill]` ⇒ launch + drive your project's app to see a change working.
- `/run-skill-generator` `[Skill]` ⇒ author a per-project skill teaching `/run` + `/verify` how to build/launch/drive the app.
- `/dataviz [request]` `[Skill]` ⇒ chart/dashboard design guidance (form, colorblind-safe palette, marks, a11y). EX: `/dataviz seasonal flux by sensor height`.
- `/claude-api [migrate|managed-agents-onboard]` `[Skill]` ⇒ load Claude API reference for your language; `migrate` upgrades model IDs.
- `/fewer-permission-prompts` `[Skill]` ⇒ scan transcripts for common read-only calls + add a project allowlist.
- NOT IN THIS CATALOG (in the 2.1.201 binary yet not user-facing): REMOVED — `/pr-comments` (gone since 2.1.91 ⇒ ask Claude to view PR comments) · `/vim` (gone since 2.1.92 ⇒ `/config` → Editor mode). DISABLED / flag-gated (`isEnabled` false) — `/wellbeing` `/brief` `/version` `/loops` `/update`. INTERNAL actions the harness fires (not typed) — `autocompact` `daemon` `session` `pause-memory` `skill-doctor` `pro-trial-expired` `rate-limit-options` `design-consent`/`design-revoke` `extra-usage`(legacy alias of `/usage-credits`).
- INVARIANT: availability is CONDITIONAL — an entry shows only when its `isEnabled()` passes for your platform/plan/env (`/setup-bedrock` needs `CLAUDE_CODE_USE_BEDROCK=1`; `/upgrade` is Pro/Max) ⇒ the live `/` menu is ground truth for YOUR session, and this catalog is the 2.1.201 superset.
- FEEDS: these built-ins compose with your authored skills/commands (§02.1 — a `SKILL` beats a built-in on a name clash) + agents (03_agents); the automation verbs (`/loop` `/goal` `/schedule` `/workflows` `/batch`) are the 06_loops + 07_dynamic_workflows layer; `/config` `/permissions` `/hooks` `/mcp` are the front doors to §01.3/§01.4.
<!--FIG: the stock `/` menu grouped by category (session · model · config · info · git · automation · skills) | 75% -->

## SOURCES
In-text hyperlinks cite the paraphrased sources (the SKILLS-MASTERED section); the full consolidated reference list lives in 00_overview.machine.md (§ REFERENCES).
