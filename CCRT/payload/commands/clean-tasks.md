---
description: Excise done / far-deferred items from the active task list INTO the development/ tree, each with its context bundle — the active list shrinks, nothing is lost.
tags: [tasks, context, development, hygiene, handoff]
argument-hint: [optional — item numbers/description to clean; default: all done + agreed-deferred]
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# /clean-tasks — lean the active list without losing anything

Excise items from the active task list into the `development/` record tree, capturing each item's full context so it can be rehydrated later. The active list gets smaller; the total information does not. See `~/.claude/methodology/DEVELOPMENT_TREE.machine.md` for the convention this enforces.

**What it does (PROC.clean_tasks):**
1. **Classify** each item to excise — `done` → `development/past/`, `deferred`/far-future → `development/future/`; in-progress items STAY on the active list (never excise live work).
2. **Capture the bundle** — for a future item, assemble the micro-handoff: the item + WHY it matters + associated file paths + code/artifact refs + a re-hydration pointer (a cold reader must be able to rehydrate from the bundle alone). For a past item, ensure it is dated + self-describing.
3. **File** into the drawer following the layout in `DEVELOPMENT_TREE.machine.md` (author the machine→human→pdf triplet for a new durable item; move if it already exists).
4. **Remove** from the active list ONLY after the bundle is filed and verified present — never lose an item between steps.
5. **Report** what moved where, so the list's shrink is auditable.

**Scaffold / offload / status** (the mechanical carrier):
```bash
bash "$HOME/.claude/lib/dev-tree.sh" status      # what's in each drawer + active-list size
bash "$HOME/.claude/lib/dev-tree.sh" scaffold     # create development/{past,present,future}/ if absent
bash "$HOME/.claude/lib/dev-tree.sh" offload      # move past/ OUT of the working repo (leave the grep scope)
```

**INVARIANT:** no item leaves the active list without its context bundle landing first. A bulk excision touching many files is a COMMIT-CLASS action — survey the active list and confirm the classification before moving (see `rules/recon-before-commitment.machine.md`).

Run the classification, present what will move where for the current task list, then execute after the files are staged.
