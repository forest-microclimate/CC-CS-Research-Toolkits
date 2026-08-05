# 11_references.machine.md  (machine-optimized ROOT; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# PURPOSE: the ONE collected, DEDUPLICATED list of every external source cited across `00`–`10`. Inline citations STAY where they are (they carry the claim, in context); THIS doc is the lookup surface + the link-rot surface.
# INVARIANT.unique: every entry is a CANONICAL (post-redirect) URL, listed EXACTLY ONCE. COUNTS (all three are true, of different moments): the ORIGINAL harvest found 34 raw inline URLs; rewriting the 3 DEPRECATED/restructured ones to their canonical targets leaves 33 raw URLs now cited across `00`–`10`; those resolve to 31 UNIQUE canonical refs (2 LIVE alias-collapses remain — §11.6). `CMD.canary` (§11.7) measures the 33.
# INVARIANT.verified: every URL below was RESOLVED BY FETCH on 2026-07-08. TITLES are the ACTUAL page titles, not the inline link labels (label ≠ title is noted per entry).

## 11.0 What this doc is

- TAG `[REFERENCE]` — the 12th doc of the advanced set. `00`–`10` are `[SURFACE]` / `[METHODS]`; this one is pure lookup.
- ENTRY SHAPE: **Title** — URL — what it covers — `CITED-IN:` the doc numbers whose inline text cites it.
- AUTHORITY: harvest from the `*.machine.md` ROOTS. The human twins (`.md`) + PDFs are DERIVED (doc-style `INVARIANT.machine_is_root`), so a URL that exists only in a twin is a translation DRIFT bug, not a citation.
- Docs `01_extension_architecture`, `03_agents`, `10_authoring` cite NO external sources — intentional: they describe the toolkit's OWN surface, not published prior art.
- LINK-ROT: URLs are the perishable atom here. Re-run §11.7 before any publish/release.

## 11.1 Anthropic engineering (7)

- **Building effective agents** — https://www.anthropic.com/engineering/building-effective-agents — the WORKFLOWS-vs-AGENTS distinction; the 5 building-block patterns; the simplicity thesis (add machinery only when it pays). `CITED-IN: 00, 05`
- **Effective context engineering for AI agents** — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents — context as the master finite resource; just-in-time loading; compaction; altitude (the Goldilocks system prompt). `CITED-IN: 00, 08`
- **Equipping agents for the real world with Agent Skills** — https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills — skills as progressive-disclosure capability packages (pay context only on demand). `CITED-IN: 00, 02`
- **Beyond permission prompts: making Claude Code more secure and autonomous** — https://www.anthropic.com/engineering/claude-code-sandboxing — sandboxing: filesystem + network isolation as the enabler of unattended runs. [inline label: "Claude Code sandboxing" / "Sandboxing"] `CITED-IN: 00, 09`
- **Code execution with MCP: Building more efficient agents** — https://www.anthropic.com/engineering/code-execution-with-mcp — call MCP tools THROUGH code execution to cut per-tool token overhead. `CITED-IN: 00, 09`
- **Writing effective tools for AI agents — with agents** — https://www.anthropic.com/engineering/writing-tools-for-agents — tool-design principles: naming, descriptions, token economy, error surfaces. [inline label: "Writing tools for agents"] `CITED-IN: 00, 09`
- **How we built our multi-agent research system** — https://www.anthropic.com/engineering/multi-agent-research-system — subagents operating in parallel, each with its OWN context window; orchestrator-worker in practice. [inline label: "Multi-agent research system"] `CITED-IN: 00, 07`

## 11.2 Claude blog (6)

- **Lessons from building Claude Code: How we use skills** — https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills — internal skill practice; what earns a skill vs a rule. [inline label: "How we use Skills"] `CITED-IN: 00, 02`
- **Customize Claude Code with plugins** — https://claude.com/blog/claude-code-plugins — plugin packaging + distribution (the announcement). [inline label: "Claude Code plugins"] `CITED-IN: 00, 09`
- **Steering Claude Code: when to use CLAUDE.md, skills, hooks, and subagents** — https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more — choosing among the steering surfaces. [inline label: "Steering Claude Code"] `CITED-IN: 00`
- **How Claude Code works in large codebases: Best practices and where to start** — https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start — navigating big, sprawling repos. `CITED-IN: 00`
- **Getting started with loops** — https://claude.com/blog/getting-started-with-loops — a loop = an agent repeating cycles of work until a STOP condition is met; the 4 loop types. `CITED-IN: 00, 06`
- **A harness for every task: dynamic workflows in Claude Code** — https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code — auto-generated JS harnesses; the SIX orchestration patterns; the 3 failure modes. `CITED-IN: 00, 07`

## 11.3 Claude Code documentation (15)

All under `https://code.claude.com/docs/en/`.

- **Best practices for Claude Code** — https://code.claude.com/docs/en/best-practices — explore→plan→code→commit; TDD; visual iteration; multi-Claude; "give Claude a check it can run." MOST-CITED source in the set (11 inline citations). **[MIGRATED]** — was `www.anthropic.com/engineering/claude-code-best-practices`; that URL now issues a 308 to this one (§11.6). `CITED-IN: 00, 04`
- **Connect Claude Code to tools via MCP** — https://code.claude.com/docs/en/mcp — `CITED-IN: 00, 09`
- **Create plugins** — https://code.claude.com/docs/en/plugins — `CITED-IN: 00, 09`
- **Run Claude Code programmatically** — https://code.claude.com/docs/en/headless — headless `claude -p`. **Absorbs** the legacy `docs.anthropic.com/en/docs/claude-code/sdk/sdk-headless` (§11.6). `CITED-IN: 00, 09`
- **Agent SDK overview** — https://code.claude.com/docs/en/agent-sdk/overview — the SDK library docs; DISTINCT page from `/headless` (the CLI surface). `CITED-IN: 00, 09`
- **Create custom subagents** — https://code.claude.com/docs/en/sub-agents — `CITED-IN: 00`
- **Extend Claude with skills** — https://code.claude.com/docs/en/skills — **alias:** `/slash-commands` serves THIS page and declares `/skills` canonical (custom commands merged into skills — the "skills ARE slash commands" claim in `02_skills_and_commands`). `CITED-IN: 00`
- **Claude Code settings** — https://code.claude.com/docs/en/settings — `CITED-IN: 00`
- **Output styles** — https://code.claude.com/docs/en/output-styles — `CITED-IN: 00`
- **How Claude remembers your project** — https://code.claude.com/docs/en/memory — CLAUDE.md loading + precedence. `CITED-IN: 00`
- **Interactive mode** — https://code.claude.com/docs/en/interactive-mode — `CITED-IN: 00`
- **Hooks reference** — https://code.claude.com/docs/en/hooks — `CITED-IN: 00`
- **Claude Code GitHub Actions** — https://code.claude.com/docs/en/github-actions — `CITED-IN: 00`
- **Common workflows** — https://code.claude.com/docs/en/common-workflows — `CITED-IN: 00`
- **CLI reference** — https://code.claude.com/docs/en/cli-reference — `CITED-IN: 00`

## 11.4 Model Context Protocol (2)

- **What is the Model Context Protocol (MCP)?** — https://modelcontextprotocol.io/docs/getting-started/intro — the protocol intro. CANONICAL: both `modelcontextprotocol.io` (site root) and `modelcontextprotocol.io/introduction` resolve to this content (§11.6). `CITED-IN: 00, 09`
- **Notion remote MCP server** (endpoint) — https://mcp.notion.com/mcp — an MCP SERVER ENDPOINT, not a documentation page: it answers `401 Unauthorized` (an auth challenge = it exists). Cited only as the concrete `claude mcp add` example. `CITED-IN: 09`

## 11.5 Code (1)

- **claude-cookbooks — agent patterns** — https://github.com/anthropics/claude-cookbooks/tree/main/patterns/agents — executable notebooks for the 5 building-block patterns: `basic_workflows.ipynb` (chaining, routing, parallelization), `orchestrator_workers.ipynb`, `evaluator_optimizer.ipynb`, `async_multi_agent_orchestration.ipynb`. Read the CODE, not just the names. [inline labels: "agents cookbook" / "Anthropic cookbook — agent patterns"] `CITED-IN: 00, 05`

## 11.6 Alias-collapses + migrations (34 harvested ⇒ 33 now cited ⇒ 31 unique)

Resolving each raw URL to its canonical target collapses three PAIRS and relocates one page. Deduplicating the raw STRINGS alone would have left 34 entries, 3 of them duplicates — identity has to be established in the DESTINATION space (after redirects), not the source space.

Of the 5 rows below: 3 were DEPRECATED or restructured and have been REWRITTEN to their canonical targets in `00`–`10` — two of those targets are URLs new to the set, while the third (`/headless`) was already cited by `09` — netting the harvested 34 raw URLs down to the 33 now cited. The remaining 2 rows are LIVE aliases, left in place because they still resolve and read correctly in context; they collapse 33 raw ⇒ 31 unique canonical entries.

| Raw URL (as cited inline) | Resolves to | Kind |
|---|---|---|
| https://code.claude.com/docs/en/slash-commands | https://code.claude.com/docs/en/skills | ALIAS — same page; page declares `/skills` canonical. STILL CITED in `00` (reads correctly in context) |
| https://modelcontextprotocol.io | https://modelcontextprotocol.io/docs/getting-started/intro | ALIAS — site root serves the intro. STILL CITED in `09` as a site-root link |
| https://modelcontextprotocol.io/introduction | https://modelcontextprotocol.io/docs/getting-started/intro | ALIAS — site restructured; old path still resolves. REWRITTEN in `00`, `09` |
| https://docs.anthropic.com/en/docs/claude-code/sdk/sdk-headless | https://code.claude.com/docs/en/headless | REDIRECT (301 chain) — legacy domain, DEPRECATED. REWRITTEN in `00` |
| https://www.anthropic.com/engineering/claude-code-best-practices | https://code.claude.com/docs/en/best-practices | MIGRATION (308) — blog post absorbed into the docs. REWRITTEN in `00`, `04` (11 cites) |

NOTE: the raw URLs above are written in FULL `https://` form on purpose — the `CMD.canary` in §11.7 greps for `https?://`, so a raw URL recorded as a bare hostname would read as an UNRECORDED citation and trip the alarm.

- ACTION TAKEN (2026-07-08): the two DEPRECATED sources — the legacy `sdk-headless` URL and the migrated `claude-code-best-practices` URL — plus the restructured `modelcontextprotocol.io/introduction` path were REWRITTEN to their canonical targets in the citing docs (`00`, `04`, `09`), machine roots AND human twins, so inline cites and this list agree.
- ALIASES LEFT IN PLACE: `/slash-commands` and the bare `modelcontextprotocol.io` site-root link both still resolve and read correctly in context; they are recorded here as aliases rather than rewritten.
- CAVEAT `[partially-inferred]`: the `sdk-headless` 301 chain's literal terminal `Location` is on the `docs.claude.com` mirror host, which the fetch tool's domain-safety layer blocks. The identical content is confirmed live (HTTP 200) at `code.claude.com/docs/en/headless`, which is the canonical headless page per the current docs index — so that is what is cited. The mirror's own live status is INFERRED, not observed.

## 11.7 Regenerate + anti-rot

A references list rots SILENTLY: nothing fails when a link dies or a citation is added upstream without being recorded here. So the check is mechanical, not remembered.

`RULE.same_edit`: adding an inline citation to any of `00`–`10` ⇒ add its entry HERE in the SAME edit. The canary below is what catches you when you forget.

`CMD.harvest` — re-derive the raw URL set from the authoritative machine roots:

```bash
cd payload/docs/advanced
grep -rhoE 'https?://[^ )"`,>]+' . --include='*.machine.md' \
  | sed 's/[.,;:]*$//' | sort -u
```

`CMD.canary` — every URL cited in `00`–`10` MUST appear in this doc. Expect EMPTY output; any line printed is an unrecorded citation:

```bash
cd payload/docs/advanced
comm -23 \
  <(grep -rhoE 'https?://[^ )"`,>]+' . --include='0*.machine.md' --include='10_*.machine.md' \
      | sed 's/[.,;:]*$//' | sort -u) \
  <(grep -ohE  'https?://[^ )"`,>]+' 11_references.machine.md \
      | sed 's/[.,;:]*$//' | sort -u)
```

`CMD.twin_drift` — a URL present in a human twin but absent from its machine root violates `INVARIANT.machine_is_root`. Expect EMPTY:

```bash
cd payload/docs/advanced
comm -13 \
  <(grep -rhoE 'https?://[^ )"`,>]+' . --include='*.machine.md' | sed 's/[.,;:]*$//' | sort -u) \
  <(grep -rhoE 'https?://[^ )"`,>]+' . --include='*.md' --exclude='*.machine.md' | sed 's/[.,;:]*$//' | sort -u)
```

`PROC.reverify` (before a publish/release): fetch every URL in §11.1–§11.5; follow redirects; if a FINAL canonical URL differs from the listed one, update BOTH this doc and the citing docs, then re-render the affected PDFs (`/folio`). Record the verification date in the header.
