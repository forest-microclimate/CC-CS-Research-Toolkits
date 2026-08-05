# 09_going_further.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# TOPIC: GOING FURTHER — building ON Claude Code. The OUTWARD extension points, BEYOND the inward `.claude/` files.
# FOR: the researcher whose inward setup already works (CLAUDE.md · rules · skills · commands · hooks · subagents) and now wants to extend the engine OUTWARD — connect it to external tools+data (MCP) · run it more autonomously+safely (sandbox) · ship a whole capability set to a team (plugin) · drive it from code/CI (Agent SDK / headless).
# AUDIENCE: primary reader = Claude (this ROOT is authoritative + terse). A HUMAN twin later renders it into Anthropic-article prose ⇒ every substance atom is PACKED here; terse packaging is intentional, not a gap to fill.
# STYLE: front-loaded · positive action-first (name the ACTION + its TRIGGER) · `⇒` · CAPS emphasis · inline `code` · `·` separators. Paraphrased facts carry an inline hyperlink citation; sources are grouped in REFERENCES at the end. Where a source did NOT confirm a specific flag/number, it is hedged or omitted — no invented syntax.

## FRAMING — Claude Code is a PLATFORM, not just a CLI

CLAIM: the interactive terminal is ONE surface of an agent ENGINE. The earlier (inward) parts of this guide customize that engine from the INSIDE — `.claude/` files shape ONE session on YOUR machine. This doc covers the FOUR OUTWARD surfaces that extend the engine BEYOND a single local session:

- TOOLS it calls ⇒ **MCP** — connect Claude to external tools + data (issue trackers · databases · design files · your own scripts).
- SANDBOX it runs in ⇒ **sandboxing** — a containment wall ⇒ more autonomy with fewer prompts.
- BUNDLE you ship ⇒ **plugins** — package commands + subagents + MCP servers + hooks into ONE installable unit for a team.
- LIBRARY you build on ⇒ **Agent SDK / headless** — the same agent loop as a CLI + Python/TypeScript libraries ⇒ Claude Code in scripts · CI · scheduled jobs.

INVARIANT.one_engine: the SAME agent loop · tool-execution · context manager · permission system sits under ALL FOUR — the Agent SDK "gives you the same tools, agent loop, and context management that power Claude Code" ([Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)). ⇒ what you learn on ONE surface (a tool's permission rule · a subagent · a hook) TRANSFERS to the others: they are DIFFERENT DOORS INTO ONE ROOM, not four separate products. Read this doc as "four ways to move the same engine," not four unrelated features.

<!--FIG: the shared agent engine at center (loop · tool-execution · context manager · permission system) with the four outward surfaces around it — MCP (tools flow IN) · sandbox (containment wall AROUND) · plugin (bundle ships OUT) · SDK (drive from code) | 90% -->

---

## MCP & CUSTOM TOOLS

FOR: give Claude a UNIFORM way to reach the tools + data that live OUTSIDE the chat — an issue tracker · a database · a monitoring dashboard · a design file · your own analysis scripts — so it reads and acts on those systems DIRECTLY instead of you copy-pasting into the prompt. REACH for a server the moment you notice yourself pasting data from another tool into chat ([Claude Code MCP](https://code.claude.com/docs/en/mcp)).
HANDLE: MCP = "a USB-C port for AI applications" — one standardized plug; any compliant tool connects to any compliant app ([MCP intro](https://modelcontextprotocol.io/docs/getting-started/intro)).

### WHAT MCP IS

DEF: the **Model Context Protocol** = an OPEN, open-source standard for connecting AI applications to external systems — data sources · tools · workflows ([MCP intro](https://modelcontextprotocol.io/docs/getting-started/intro)). ONE protocol replaces N bespoke integrations ⇒ "build once and integrate everywhere."
ARCH — CLIENT ⇄ SERVER:
- a HOST application (Claude Code · Claude Desktop · an IDE) embeds an **MCP CLIENT**.
- the client connects to one or more **MCP SERVERS**; each server fronts some external system (local files · a database · a remote SaaS API).
- Claude Code IS an MCP client ⇒ it CONSUMES servers; you do not implement the protocol to use one.
PRIMITIVES a server exposes (exactly THREE):
- **TOOLS** ⇒ ACTIONS the model can CALL (search · create · query · update). Every call is GATED by the permission system before it runs.
- **RESOURCES** ⇒ DATA/context the model can READ (a file · an issue · a schema). `@`-mentionable like a file.
- **PROMPTS** ⇒ reusable workflow TEMPLATES, surfaced as slash-commands.
WHY it exists: before MCP, every app×tool pair needed a custom integration (N×M explosion). MCP collapses that to N+M — a tool author writes ONE server · an app author writes ONE client · they interoperate across a broad ecosystem (Claude · ChatGPT · VS Code · Cursor · more) ([MCP intro](https://modelcontextprotocol.io/docs/getting-started/intro)).

<!--FIG: MCP host/client/server model — HOST app (Claude Code) contains an MCP CLIENT; arrows to N MCP SERVERS; each server wraps a backing system (files · DB · SaaS API); callout on the three primitives a server exposes (tools · resources · prompts) | 85% -->

### HOW TO USE in Claude Code

ADD a server ⇒ `claude mcp add` in one of three transport forms ([Claude Code MCP](https://code.claude.com/docs/en/mcp)):
- REMOTE HTTP (recommended for cloud services) ⇒ `claude mcp add --transport http <name> <url>` · e.g. `claude mcp add --transport http notion https://mcp.notion.com/mcp` · add a token with `--header "Authorization: Bearer <token>"`. (In JSON config, `type` accepts `streamable-http` as an alias for `http`.)
- REMOTE SSE (DEPRECATED — prefer HTTP) ⇒ `claude mcp add --transport sse <name> <url>`.
- LOCAL stdio (a subprocess on your machine — direct system access · custom scripts) ⇒ `claude mcp add [options] <name> -- <command> [args...]` · everything AFTER `--` is passed to the server untouched (separate the server's own flags from Claude's).
- (also: `claude mcp add-json <name> '<json>'` for a raw config · a WebSocket server via `add-json` with `type:"ws"` for servers that push events unprompted.)
MANAGE ⇒ `claude mcp list` (all) · `claude mcp get <name>` (one server's detail) · `claude mcp remove <name>` · and INSIDE a session `/mcp` (status · connect · authenticate). The `/mcp` panel shows each connected server's tool count.
SCOPES — WHERE the config lives + WHO sees it (`--scope`) ([Claude Code MCP](https://code.claude.com/docs/en/mcp)):
- `local` (DEFAULT) ⇒ this project · you only · stored in `~/.claude.json`. Use for personal/experimental servers or ones holding private credentials.
- `project` ⇒ this project · SHARED with the team via a `.mcp.json` file COMMITTED to the repo root ⇒ everyone gets the same servers. Claude Code PROMPTS for approval before using project servers from `.mcp.json` (a trust gate; a cloned repo can't auto-approve its own servers).
- `user` ⇒ ALL your projects · you only.
- PRECEDENCE (highest wins, whole entry, fields NOT merged): local > project > user > plugin-provided > claude.ai connectors.
AUTH remote servers ⇒ OAuth 2.0. A server that answers `401/403` is flagged in `/mcp`; run `/mcp` (or, from the shell, `claude mcp login <name>`) and complete the browser flow ([Claude Code MCP](https://code.claude.com/docs/en/mcp)). Tokens are stored securely + auto-refreshed. In NON-interactive mode there is no `/mcp` panel ⇒ authorize from an interactive session first.
IMPORT from Claude Desktop ⇒ `claude mcp add-from-claude-desktop` (macOS + WSL) — reuse servers you already configured.
ENV-VAR EXPANSION in `.mcp.json` ⇒ `${VAR}` and `${VAR:-default}` inside `command` · `args` · `env` · `url` · `headers` ⇒ share ONE config while keeping machine-specific paths + secrets OUT of version control (put the key in `${API_KEY}`, not the committed file).
USE what a server exposes:
- TOOLS ⇒ Claude calls them like any built-in tool, GATED by the permission system (your allow/deny rules apply). Full callable form `mcp__<server>__<tool>`; a plugin-bundled server's tool is `mcp__plugin_<plugin>_<server>__<tool>`.
- RESOURCES ⇒ `@`-mention them with `@server:protocol://resource/path` · e.g. `@github:issue://123` · `@docs:file://api/authentication` · fuzzy-searchable in the `@` autocomplete; fetched + attached automatically.
- PROMPTS ⇒ appear as slash-commands `/mcp__<server>__<prompt>` · pass args space-separated · e.g. `/mcp__github__pr_review 456`.
CONTEXT COST is managed by DEFAULT **tool search** ⇒ only tool NAMES + server instructions load at session start; full tool DEFINITIONS are DEFERRED until Claude searches for them ⇒ adding servers barely touches your context window ([Claude Code MCP](https://code.claude.com/docs/en/mcp)). Tune with the `ENABLE_TOOL_SEARCH` env var · force a small always-needed set visible with `alwaysLoad:true`. Large tool outputs warn at 10,000 tokens; default cap 25,000 (raise with `MAX_MCP_OUTPUT_TOKENS`).

### HOW TO OPTIMIZE (design + scale tools FOR agents)

DESIGN for the AGENT, not the API ([writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)):
- FEW HIGH-VALUE WORKFLOW TOOLS > many thin endpoint wrappers ("More tools don't always lead to better outcomes"). CONSOLIDATE: `schedule_event` (finds availability + books) NOT `list_users`+`list_events`+`create_event` · `search_logs` (returns relevant lines with context) NOT raw `read_logs` · `get_customer_context` NOT three separate getters.
- NAMESPACE by service + resource ⇒ `asana_search` · `jira_search` (service) · `asana_projects_search` · `asana_users_search` (resource) ⇒ the agent picks the right tool when dozens exist.
- RETURN NATURAL IDENTIFIERS ⇒ human-readable names over opaque alphanumeric UUIDs ⇒ measurably better retrieval precision.
- LET THE AGENT CONTROL ITS OWN TOKEN SPEND ⇒ pagination · filtering · range selection · truncation with sane defaults · a response-format enum (`concise` vs `detailed`). (Claude Code restricts tool responses to ~25,000 tokens by default.)
- WRITE TOOL DESCRIPTIONS LIKE ONBOARDING a new teammate ⇒ make implicit domain knowledge explicit · name params unambiguously (`user_id` not `user`) · make error messages GUIDE toward a fix, not return opaque codes.
EVAL-DRIVEN LOOP ⇒ prototype tools → generate realistic agent-run eval tasks → run programmatic evals → analyze results WITH CLAUDE ITSELF → refine definitions/descriptions → repeat ([writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)).
AT SCALE — CODE EXECUTION WITH MCP ([code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)):
- PROBLEM: loading many tool definitions UPFRONT burns context — connect thousands of tools ⇒ hundreds of thousands of tokens before the first request; and every intermediate result flows THROUGH the model context (a 2-hour meeting transcript passed between two tools ⇒ +~50,000 tokens).
- PATTERN: present each MCP server as a CODE API (files/modules in a filesystem, e.g. `./servers/google-drive/getDocument.ts`) that the agent IMPORTS ON DEMAND and orchestrates by WRITING CODE run in a sandbox. ⇒ tool definitions load ONLY when the code imports them · intermediate results STAY IN the execution environment, never entering model context.
- PAYOFF: a reported case dropped from 150,000 → 2,000 tokens = **98.7%** saved.
- ALSO gains: PRIVACY (keep/tokenize PII inside the sandbox, out of the model) · CONTROL FLOW (loops · conditionals · error-handling in familiar code, not chained tool calls) · STATE (write intermediate results to files · resume · save reusable skill functions).
- REQUIRES a SECURE sandbox (resource limits + monitoring) — see SANDBOXING below; this is the direct coupling between the two sections.
CURATE what's ENABLED ⇒ connect only servers you use · disable the rest · at org scale restrict with managed `allowedMcpServers` / `deniedMcpServers` ⇒ bound BOTH context cost AND attack surface.
SECURITY — untrusted MCP content ⇒ PROMPT-INJECTION risk. VERIFY you trust each server before connecting; "Servers that fetch external content can expose you to prompt injection" ([Claude Code MCP](https://code.claude.com/docs/en/mcp)). QUARANTINE pattern ⇒ an agent that READS untrusted external content is BARRED from privileged actions — reader-of-untrusted ≠ actor-with-credentials. Enforce it by composing SANDBOXING (credentials live OUTSIDE the sandbox ⇒ injected code cannot exfiltrate them) with a permissions DENY-list (forbid the privileged action).

<!--FIG: code-execution-with-MCP token savings — LEFT: direct tool-calling loads all N tool defs upfront + every intermediate result passes through model context (150,000 tokens); RIGHT: servers as importable code APIs, defs load on demand + intermediate results stay in the sandbox (2,000 tokens, 98.7% saved) | 90% -->

INVARIANT.mcp: a server exposes exactly THREE primitives — TOOLS (call) · RESOURCES (read) · PROMPTS (template) — and Claude Code is a CLIENT that consumes them; every tool call still passes the PERMISSION system. Adding tools is CHEAP in context (tool search defers them) but NOT free in TRUST (each server is attack surface) ⇒ curate + quarantine.
FEEDS: MCP tools become the VOCABULARY for the pattern + dynamic-workflow orchestration layer (see 05_pattern_vocabulary + 07_dynamic_workflows) — a subagent fleet or a code-execution loop composes MCP tools into pipelines. Tool CALLS are gated by the same allow/deny rules as built-ins (see 01_extension_architecture). Servers bundle INTO plugins (see PLUGINS below) and are drivable from the SDK (see AGENT SDK / HEADLESS below).

---

## SANDBOXING

FOR: run Claude AUTONOMOUSLY with FEWER permission prompts by making a CONTAINMENT WALL — not a per-command human gate — the safety boundary ([Claude Code sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)).
HANDLE: a blast-shield around the agent — it works freely INSIDE the wall; the wall (not a person clicking "allow" each time) stops it reaching OUT.
WHAT is isolated (two boundaries):
- FILESYSTEM ⇒ read/write the current working directory · BLOCK modification of anything outside it ⇒ a prompt-injected process can't alter system files.
- NETWORK ⇒ reach only APPROVED servers, via a unix-domain socket to a proxy running OUTSIDE the sandbox ⇒ blocks data exfiltration + malware download.
HOW ⇒ OS-level primitives — Linux `bubblewrap` · macOS Seatbelt — enforce the wall, covering not just Claude's own calls but ANY script/subprocess it spawns ([Claude Code sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)). ENABLE with the `/sandbox` command inside Claude Code.
PAYOFF ⇒ autonomy WITHOUT the click-fatigue: Anthropic reports internal usage where "sandboxing safely reduces permission prompts by 84%" — Claude operates freely within the boundary instead of stopping to ask on every action.
CREDENTIAL SAFETY (the load-bearing security property) ⇒ secrets — git credentials · signing keys · API tokens — live OUTSIDE the sandbox; a proxy handles authentication externally ⇒ a compromised OR prompt-injected process INSIDE cannot READ or EXFILTRATE them ([Claude Code sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)). This is precisely what makes "let it run" safe rather than reckless.
FRAME — two knobs, use BOTH:
- sandbox = the UP knob for autonomy (raise the wall ⇒ safely grant MORE freedom, fewer prompts).
- permissions deny-list = the DOWN knob (forbid specific dangerous actions even INSIDE the wall).
WHEN to reach for it ⇒ long autonomous runs · CODE-EXECUTION-WITH-MCP (it IS the "secure sandbox" that pattern requires) · anything reading untrusted external content · batch/headless jobs you won't babysit.
INVARIANT.sandbox: the sandbox is the SAFETY BOUNDARY that REPLACES per-command approval; because CREDENTIALS live OUTSIDE it, code inside can be wrong or hijacked without leaking secrets or escaping the working directory. Fewer prompts is the SYMPTOM; CONTAINMENT is the cause — do not chase the symptom by loosening permissions without the wall.
FEEDS: sandboxing is the UP-knob twin of the permissions DENY-list DOWN-knob (see 01_extension_architecture) · it is the "secure execution environment" that CODE EXECUTION WITH MCP (above) depends on · it is what makes unattended SDK/headless runs (below) safe to leave alone.

<!--FIG: sandboxing = two-boundary containment — a box labeled "working directory" with Claude + spawned subprocesses inside; FILESYSTEM boundary (write only inside) + NETWORK boundary (out only via proxy to approved servers); credentials + signing keys drawn OUTSIDE the box, unreachable from within | 85% -->

---

## PLUGINS

FOR: package "any combination of slash commands · subagents · MCP servers · hooks" into ONE installable, versioned, shareable unit ⇒ a teammate installs ONCE and has your whole setup on day one — no per-file copying ([Claude Code plugins](https://claude.com/blog/claude-code-plugins)).
HANDLE: an APP-BUNDLE for Claude Code — install an app instead of hand-copying its files into place.
WHAT a plugin bundles (components, each at the plugin ROOT) ([create plugins](https://code.claude.com/docs/en/plugins)):
- `skills/<name>/SKILL.md` ⇒ skills (legacy flat commands live in `commands/`; prefer `skills/` for new plugins).
- `agents/` ⇒ custom subagents.
- `hooks/hooks.json` ⇒ event hooks.
- `.mcp.json` (at plugin root) ⇒ bundled MCP servers — they start AUTOMATICALLY when the plugin is enabled; reference bundled files with `${CLAUDE_PLUGIN_ROOT}`.
- (+ `.lsp.json` language servers · `monitors/` background watchers · `bin/` executables added to PATH · `settings.json` defaults.)
MANIFEST ⇒ `.claude-plugin/plugin.json` at the plugin root defines identity: `name` (also the skill NAMESPACE) · `description` · optional `version` · optional `author`. GOTCHA: ONLY `plugin.json` goes inside `.claude-plugin/`; ALL component directories sit at the plugin ROOT (a common mistake is nesting `commands/`/`agents/`/`skills/`/`hooks/` inside `.claude-plugin/`).
NAMESPACING ⇒ plugin skills are ALWAYS namespaced `/plugin-name:skill` ⇒ no collisions when multiple plugins ship a same-named skill.
BUNDLED-ASSET VARIABLES ⇒ `${CLAUDE_PLUGIN_ROOT}` for files shipped inside the plugin (e.g. an MCP server's `command`) · `${CLAUDE_PLUGIN_DATA}` for state that survives updates · `${CLAUDE_PROJECT_DIR}` for the project root.
INSTALL + MANAGE ⇒ the `/plugin` command (install · enable · disable). Plugins are "designed to toggle on and off as needed" — enable a capability set when you need it, disable when you don't ([Claude Code plugins](https://claude.com/blog/claude-code-plugins)).
MARKETPLACES ⇒ a marketplace = a git/GitHub repo (or URL) carrying a `.claude-plugin/marketplace.json` catalog of plugins. Add one with `/plugin marketplace add <owner/repo>`, then install from it. Host a PRIVATE marketplace repo to keep a team's plugins internal.
AUTHOR + TEST ⇒ create a directory + manifest · test locally with `claude --plugin-dir ./my-plugin` (loads without installing) · run `/reload-plugins` to pick up edits live.
WHY (team distribution) ⇒ "standardize Claude Code environments around a set of shared best practices" · "ensure consistency across their team" — install once ⇒ identical capability for everyone, versioned + updatable ([Claude Code plugins](https://claude.com/blog/claude-code-plugins)). Contrast standalone `.claude/`: personal, single-project, must be manually copied to share.
INVARIANT.plugin: a plugin is the DISTRIBUTION UNIT for the inward customizations — the SAME skills · subagents · hooks · MCP servers you build one-by-one in `.claude/`, packaged so install-once == everyone-identical. It adds no new capability KIND; it makes the existing kinds SHIPPABLE + versioned.
FEEDS: plugins bundle the SKILLS + COMMANDS (see 02_skills_and_commands) · the HOOKS (see 01_extension_architecture) · and the MCP SERVERS (above) into one unit ⇒ the outward packaging of everything inward. The Agent SDK can load plugins programmatically (a `plugins` option), and a `claude -p` run can load one with `--plugin-dir`.

<!--FIG: a plugin = one box wrapping four inner tiles (slash commands · subagents · MCP servers · hooks) + a `.claude-plugin/plugin.json` manifest tab; an arrow "install once via /plugin" from a marketplace repo to N identical teammates | 80% -->

---

## AGENT SDK / HEADLESS

FOR: drive the SAME agent — its loop · tools · context manager · permission system — from OUTSIDE the interactive terminal: a CLI for scripts/CI · Python + TypeScript libraries for full programmatic control ⇒ Claude Code as a LIBRARY you build on ([Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)).
HANDLE: Claude Code as a function call — `claude -p "..."` (or `query(...)` in code) instead of a person typing at a prompt.
WHAT ⇒ "the same tools, agent loop, and context management that power Claude Code," exposed as ([Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)):
- a CLI ⇒ `claude -p "<prompt>"` (`-p` / `--print`, non-interactive) — accepts any CLI option.
- libraries ⇒ `pip install claude-agent-sdk` (Python 3.10+) · `npm install @anthropic-ai/claude-agent-sdk` (the TS package bundles a Claude Code binary). Core call = `query(prompt, options)`; options carry `allowed_tools` · `permission_mode` · `mcp_servers` · `agents` (subagents) · `hooks` · `resume` — the whole feature set, programmable. It also loads the same `.claude/` config (skills · commands · CLAUDE.md · plugins) by default.
HOW (headless CLI mechanics) ([run programmatically](https://code.claude.com/docs/en/headless)):
- OUTPUT FORMAT ⇒ `--output-format text|json|stream-json`. `text` (default) = plain text. `json` = structured result + session ID + metadata incl. `total_cost_usd` ⇒ parse with `jq -r '.result'`. `stream-json` + `--verbose` (+ `--include-partial-messages`) ⇒ newline-delimited JSON events for real-time streaming. (Schema-constrained output via `--output-format json --json-schema '<schema>'` ⇒ result in a `structured_output` field.)
- SCOPE TOOLS ⇒ `--allowedTools "Bash,Read,Edit"` pre-approves tools so an unattended run doesn't BLOCK on a prompt; uses permission-rule syntax, e.g. `--allowedTools "Bash(git diff *)"` (prefix match — mind the space before `*`). For a whole-session baseline instead ⇒ `--permission-mode acceptEdits` (auto-approve edits + common fs commands) or `dontAsk` (locked-down CI: denies anything not in your allow rules or the read-only set).
- SYSTEM PROMPT ⇒ `--append-system-prompt "<...>"` (ADD, keep Claude Code defaults) · `--system-prompt` (REPLACE the default entirely).
- CONTINUE ⇒ `--continue` (most recent conversation) · `--resume <session_id>` (a specific one; capture the id from `--output-format json`).
- PIPE stdin ⇒ `cat build-error.txt | claude -p 'explain the root cause' > out.txt` · `git diff main | claude -p "you are a typo linter ..."` (piping the diff means no Bash permission needed to read it).
- REPRODUCIBLE CI ⇒ `--bare` skips auto-discovery of hooks · skills · plugins · MCP servers · auto memory · CLAUDE.md ⇒ same result on every machine; only flags you pass explicitly take effect ([run programmatically](https://code.claude.com/docs/en/headless)).
AUTH ⇒ headless/programmatic authenticates via the `ANTHROPIC_API_KEY` env var (= API billing), NOT the interactive claude.ai OAuth login; Anthropic states third-party SDK agents must use API-key auth rather than claude.ai login/rate-limits ([Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)). (Bedrock · Vertex/Google Cloud · Foundry supported via `CLAUDE_CODE_USE_*` env vars.)
GOTCHA (billing) ⇒ interactive Claude Code on a SUBSCRIPTION plan (claude.ai OAuth `/login`) and headless runs on `ANTHROPIC_API_KEY` are DISTINCT, precedence-ordered authentication methods — a session using `ANTHROPIC_API_KEY` does NOT draw on your claude.ai subscription (claude.ai connectors "aren't loaded when `ANTHROPIC_API_KEY` ... is active, even if you previously ran `/login`", [Claude Code MCP](https://code.claude.com/docs/en/mcp)). ⇒ a headless run BILLS TO API CREDITS — its `total_cost_usd` is real API spend — so BUDGET for it SEPARATELY from your interactive subscription seat.
WHEN ⇒ CI/CD pipelines · pre-commit hooks + build-script linters/reviewers (`git diff main | claude -p "..."`) · fan-out BATCH jobs (many `claude -p` in parallel) · scheduled automation · building custom agents. Rule of thumb ([Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)): interactive development + one-off tasks ⇒ CLI · CI/CD + production automation + custom apps ⇒ SDK; many teams use BOTH (CLI for daily work, SDK for production).
INVARIANT.sdk: headless is the SAME engine minus the human keyboard ⇒ everything interactive (subagents · hooks · MCP · permissions · skills) is available programmatically, AND everything you would decide interactively (a tool approval) you must PRE-DECIDE via flags (`--allowedTools` · `--permission-mode`) or the run BLOCKS/ABORTS. Unattended ⇒ scope tools + sandbox + budget API spend UP FRONT.
FEEDS: the SDK is the engine under the loops + schedules layer (see 06_loops) — a recurring or cloud run is just this SDK loop off your terminal. Unattended runs lean on SANDBOXING (safe autonomy) + pre-scoped PERMISSIONS (see 01_extension_architecture), and load the same `.claude/` files + PLUGINS the interactive engine does.

<!--FIG: interactive vs headless = one engine, two front-ends — LEFT a person at a terminal answering permission prompts (claude.ai subscription/OAuth); RIGHT a script/CI calling `claude -p` with pre-scoped `--allowedTools` + `ANTHROPIC_API_KEY` (API billing); the identical agent-loop box shared between them | 85% -->

---

## REFERENCES

MCP — the protocol:
- [Model Context Protocol — Introduction](https://modelcontextprotocol.io/docs/getting-started/intro) (fallback: [modelcontextprotocol.io](https://modelcontextprotocol.io))

MCP — use in Claude Code:
- [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp)

Optimizing MCP + tools:
- [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)

Sandboxing:
- [Claude Code sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)

Plugins:
- [Claude Code plugins (announcement)](https://claude.com/blog/claude-code-plugins)
- [Create plugins](https://code.claude.com/docs/en/plugins)

Agent SDK / headless:
- [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [Run Claude Code programmatically (headless)](https://code.claude.com/docs/en/headless)
