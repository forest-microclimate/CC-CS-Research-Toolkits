# KIT_ADOPTION.machine.md — Adopting the Kit (installing the workflow into a real project, step by step)
# STATUS: CURRENT (2026-08-05). Machine root of the KIT_ADOPTION guide; human twin in ../human_md/. 2026-08-05 (kit v1.5, K12): the folder contract is named `STRUCTURE_RULES.md` throughout (renamed from `STRUCTURE_RULES.machine.md`; content unchanged) — the ../PDF/ render is now STALE on this token and owes a re-render. 2026-08-04: §6 gains the launch-time model rule (workers unpinned ⇒ the coordinator names lower tiers at launch; the ceiling is requested by OMITTING the model; safe only while default == ceiling). K11-B: §1 gains the PAIRING atoms (kit ships inside the CCRT at `CCRT/planner-kit/`; two deliberately-separate installers; `--upgrade-rules`) + MODE.minimal-default gains the v1.4 model-routing set.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORM: machine-md · durable reference · primary reader = LLM · atom-preserving translation of the human twin (INVARIANT.convert: every rule/fact/step kept; only packaging changes). SIBLINGS: WORKFLOW_GUIDE.md (the loop this guide does not repeat), KIT_RATIONALE.md (WHY the kit is shaped this way). This is the practical part — from the first command to the point where the project has begun growing its own structure as the work proceeds.

# ─── PREMISE ───────────────────────────────────────────────────────────────
PREMISE.scope: you have decided to run a project the way WORKFLOW_GUIDE.md describes + the rationale guide (KIT_RATIONALE.md) has told you why the kit is shaped the way it is ⇒ this guide walks you through installing the kit into a real project.
FACT.writes-only: everything here happens INSIDE your project, + the kit writes only generic rules + empty structure, NEVER your data.

# ─── §1 WHAT YOU NEED ──────────────────────────────────────────────────────
NEED.three: three things, none unusual. (1) the kit itself — the `planner-kit` directory, which holds the installer `install.sh` with a `payload` folder beside it; it ships INSIDE the Claude Code toolkit at `CCRT/planner-kit/`. (2) a project to install into — any directory you want to serve as the project root. (3) a shell — the installer runs on bash 3.2 + later (the macOS default) + relies on nothing exotic.
NEED.note-path: before you start, note where the kit lives on your machine, because you will name that path when you run it.
PAIRING.separate-installers: the kit + the toolkit around it install SEPARATELY, on purpose. The CCRT installs ONCE into `~/.claude` = the global capability (agents/skills/rules/hooks, applies everywhere); THIS kit's own `install.sh` runs in EACH project root adopting the supervisory workflow = that one project's operating contract. DELIBERATELY separate + designed to be used together. Upgrades: re-run the installer with `--upgrade-rules` to bring an already-installed project up to the current rules.
RULE.run-from-project-root: one habit matters more than any of this — run the installer FROM your project root, NOT from inside the kit. The installer will refuse to run against itself (for the reason the rationale guide tells), but the point is to stand in the project you are installing into, so the current directory is the target.

# ─── §2 THE TWO INSTALL MODES, AND WHEN EACH FITS ──────────────────────────
MODE.minimal-default: the installer has two modes, + the default is the MINIMAL one — it installs two files at your project root, the rules file (`CLAUDE.md`) + the folder contract (`STRUCTURE_RULES.md`), plus the two advisory hooks (§7) + the model-routing set (two executor agents + a model-verification skill under `.claude/`), + creates NO folders; the project's tree grows on demand afterward, as tasks call for it.
MODE.full: FULL mode, which you request with `--full`, also builds the entire standard tree up front + seeds every template — the classic layout that some people prefer to see all at once.
CHOOSE.which: choose the minimal default for a fresh, long-lived project whose eventual shape you cannot predict (keeping the tree empty until the work fills it is the whole point of the default). Choose `--full` when you want the complete layout visible from the start, or when bringing over a project that already expects the classic structure.
CMD.two:
```
cd /your/project && bash /path/to/planner-kit/install.sh            # MINIMAL: 2 root files + hooks, folders on demand
cd /your/project && bash /path/to/planner-kit/install.sh --full     # CLASSIC: pre-scaffold the whole tree + seeds
```
RULE.quote-spaces: if your project path or the kit path contains spaces, quote it, because an unquoted space will break the command:
```
cd "/your/project" && bash "/path/to/planner kit/install.sh"
```

# ─── §3 PREVIEW IT FIRST WITH A DRY RUN ────────────────────────────────────
RULE.dry-run-first: before you change anything, run the installer with `--dry-run` — it writes nothing + prints exactly what it would do, one action at a time, marking each as a folder it would create, a template it would seed, or a marker it would add.
FACT.dry-run-composes: the dry run composes with either mode, so you can preview the full install as readily as the minimal one:
```
cd /your/project && bash /path/to/planner-kit/install.sh --dry-run
cd /your/project && bash /path/to/planner-kit/install.sh --full --dry-run
```
WHY.trustworthy: the preview is trustworthy in a specific, designed way — the dry run + the real run decide what to write from ONE shared piece of code reading the same inputs, so the list the preview prints is precisely what a real run will write. That shared decision is why the rationale guide can call the preview honest: the preview is the same decision the real run makes, run once without writing anything.
PROC.confirm-then-run: read the summary, confirm it matches what you expect, + then run the same command again without `--dry-run`.

# ─── §4 WHAT THE TWO FILES ARE ─────────────────────────────────────────────
FILE.rules: `CLAUDE.md` is the FRONT DOOR. It carries the whole operating contract: the supervised loop + the standing disciplines that keep it honest. It installs at the ROOT, rather than inside the `.claude` folder, because external code-review + continuous-integration runners look at a repository's root, + a short pointer stub is left at `.claude/CLAUDE.md` so a reader who looks there is sent to the root file.
FILE.folder-contract: `STRUCTURE_RULES.md` is the FOLDER CONTRACT, + its reader is the coordinating agent rather than you. It lists every folder the project may grow, + for each one gives the folder's purpose, the trigger that calls it into being, the rule that governs it once it exists, + the mechanical steps to create it. You rarely need to read it yourself — it is the reference the agent consults each time the work reaches for a folder that is not there yet.

# ─── §5 HOW THE AGENT GROWS THE PROJECT ────────────────────────────────────
MECH.grow-on-demand: this feels unlike an ordinary scaffold. Because the minimal install creates no folders, the coordinating agent builds each one as the work asks for it, using the folder contract to know when + how. EX: when a task first needs to persist a brief, the agent reads that the exchange folder is called into being by exactly that need, creates it, + carries on. When it first needs a ledger, it copies the ledger template into place at that moment; when it first retires a document, it brings in the retirement tool the same way.
FACT.appears-at-trigger: each folder appears the instant its trigger fires + not before, + a folder that never appears records that the project never needed it.

# ─── §6 YOUR FIRST WORKING CYCLE ───────────────────────────────────────────
FACT.begin: with the two files in place, you can begin working exactly as WORKFLOW_GUIDE.md describes (this guide will not repeat that loop). What is worth watching, the first time through, is the tree filling itself in.
WALK.cycle: you hand the coordinating agent a goal. It plans, + to brief its first subagent it persists that brief to a file ⇒ the moment the exchange folder + its briefs subfolder come into existence. The subagent does its work + writes an output, + if that output is a report, a reports folder appears to hold it. The first time the agent records that something was measured, it copies in the efficacy ledger; the first time it snapshots a plan, the plans folders appear under their status names.
FACT.exactly-what-required: after a few cycles the project has precisely the structure its work has required, + nothing beyond it. You did not lay that structure out in advance; the work + the folder contract laid it out between them.
RULE.model-at-launch (worth knowing BEFORE the first launch): the subagents carry NO model setting of their own ⇒ the coordinating agent chooses each one's model AS IT LAUNCHES IT, NAMING the tier it wants — the top tier included. MEASURE YOUR RUNTIME'S PRECEDENCE FIRST: on the runtime this kit was built against there are FOUR RANKS, highest wins — a subagent-model ENV VAR > the launch's model param > the agent file's own model field > inherit the session's model — so an OMITTED param requests THE SESSION'S OWN MODEL, not the ceiling. [SUPERSEDED 2026-08-04, measured] ~~TOP TIER = the EXCEPTION: request it by NAMING NOTHING AT ALL, since naming it can SILENTLY resolve to a model you meant to EXCLUDE.~~ — the excluded model did arrive, but by a SERVING-side substitution of top-tier requests, which naming-versus-omitting does not control. VERIFY BY THE SERVING RECORD: a model claim is verified by what the serving side stamped on the worker's own transcript, never by the launch config, the interface's display, or the worker's account of itself.
CHECK.default-is-ceiling: CHECK which model your own setup treats as the DEFAULT before relying on that. Omission is safe here ONLY BECAUSE the default + the ceiling are the SAME model — which is also why a launch that names nothing lands at the TOP of the band instead of the BOTTOM.

# ─── §7 THE TWO HOOKS THAT WATCH THE WORK ──────────────────────────────────
FACT.both-modes: BOTH modes also put two small hooks into `.claude/hooks/` + register them in `.claude/settings.json`.
MECH.settings-merge: NO settings file ⇒ the installer SEEDS one. One already present ⇒ it DEEP-MERGES into it, keeping a DATED copy of your original first, + it matches on the COMMAND, so a re-run registers nothing twice.
TRIG.brief-gate: launch a subagent against a brief that still has an EMPTY slot ⇒ the FIRST hook NAMES that slot as the launch goes out.
TRIG.collect-gate: end a turn in which you collected subagent results WITHOUT naming one of the six collect outcomes `WORKFLOW_GUIDE.md` defines — CONTINUE, RE-ROUTE, FIX-FIRST, ABORT, GOAL-MET, ADAPT — ⇒ the SECOND asks you for it, ONCE.
COST.one-turn: that second nudge costs ONE EXTRA TURN each time it fires, because the interface it hangs on offers no advisory channel.
RULE.never-refuse: NEITHER hook ever REFUSES an action, BOTH let the work through if anything inside them breaks, + `PLANNER_KIT_HOOKS=off` silences both.
FORM.brief-template: what the FIRST hook reads is the BRIEF FORM, which arrives with the briefs folder — the agent copies `_TEMPLATE.md` in the first time it persists a brief, + `--full` seeds it up front.
PROC.three-steps: working from the form is THREE steps — copy it to `dev/briefs/<ID>-<slug>.md`, FILL EVERY SLOT, then LAUNCH; an empty slot means the brief is NOT ready, which is the whole bar.
BLOCK.sub-planner: the form ENDS with a sub-planner block you DELETE unless that subagent will coordinate subagents of its own. When it will, that block is where you name the SUBTREE it stays inside, the PRIVATE AREA `dev/briefs/<ID>/` those subagents' briefs go to, + the ROLLED-UP report you expect back.

# ─── §8 UPGRADING A PROJECT FROM AN EARLIER VERSION ────────────────────────
FACT.upgrade-safe: if you are installing into a project that already carries the kit from an earlier version, the installer helps you upgrade WITHOUT ever touching your content. Re-running it prints a LOUD warning that names the version it found + the version it now is, because the two differ.
WHY.warns: it warns rather than proceeding quietly for a concrete reason — an older rules block will not mention the files this version adds, such as the folder contract, so a freshly seeded folder contract could sit at your root unreferenced by the older rules beside it. The merge itself still does nothing to your file.
PROC.finish-upgrade: to finish the upgrade, do the single manual step the warning names — delete the whole marked block, from its `<!-- planner-kit:BEGIN ... -->` marker through its `<!-- planner-kit:END -->` marker, out of your `CLAUDE.md`, + run the installer again to write the current block in its place.
FACT.older-dotclaude: there is an older situation the installer also recognizes — if it finds the kit's rules living inside `.claude/CLAUDE.md`, where the earliest layout kept them, it prints migration advice + leaves that file exactly where it is, so the choice of whether + when to move it stays yours.

# ─── §9 RE-RUNNING IS ALWAYS SAFE ──────────────────────────────────────────
FACT.rerun-safe: you never have to worry about running the installer more than once. A re-run changes nothing it has already done — it deletes nothing, overwrites nothing, + seeds a template only when that template is absent, so a folder contract you have edited by hand survives a re-install intact. Once the marked rules block is present in your `CLAUDE.md`, running the installer over it again does nothing.
WHY.deliberate: this safety is deliberate + is what lets you preview, install, + later re-install after an upgrade without needing a rollback between the steps — though the workflow keeps dated backups anyway, for the reasons WORKFLOW_GUIDE.md gives.

# ─── §10 WHERE THE RECORDS LIVE AS THE WORK ACCUMULATES ────────────────────
HOME.dev: as the project runs, a few homes fill up, + knowing where they are lets you read the state of the work directly, in files you can open. The exchange layer, `dev/`, holds the briefs, the instrument scripts, the reports, + the three ledgers: the efficacy ledger that tells you what has been measured rather than merely built, the append-only change log that records everything that has happened, + the code inventory that keeps agents from rebuilding what already exists.
HOME.plans: the `plans/` folder holds plan snapshots sorted into active, parked, + finished, alongside a plan ledger that tracks their moves.
HOME.stale-trash: `Stale_Trash/` holds retired items, each one moved there only after a tombstone was written into it, + none of them ever read as current again.
FACT.two-files-enough: you do not have to hold any of this in memory. The folder contract, `STRUCTURE_RULES.md`, is the authoritative description of every folder + the rule that governs it, + the rules file, `CLAUDE.md`, carries the disciplines those rules refer to. Between them, the two files the installer put at your root are enough to teach any fresh agent — + you — how the project is meant to work.
CLOSE.three-moves: adoption is just those three moves — preview the install, put down the two files + the hooks that back them, + let the project grow its own structure as the work gives it reason to.
