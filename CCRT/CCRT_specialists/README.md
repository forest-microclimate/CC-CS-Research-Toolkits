<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# CCRT_specialists — the domain specialists you install by hand

`install.sh` does not put anything in this folder onto your machine, and that is deliberate. The
installer ships the toolkit's **general** payload — the cross-domain agents and skills that make
sense for any research project, plus the model routes — into `~/.claude/`. The specialists in *this*
tree are the ones tied to a particular research domain: canopy and ecosystem modeling, phyllosphere
microbial ecology, philosophy of technology and AI safety, and a set of routing probes used to test
the toolkit itself. You copy the ones you want in yourself, with `cp`, and that is the whole
installation procedure.

If you came here because a specialist you expected was missing after running the installer, you are
in the right place: it was moved here. Nothing was dropped when this tree was split off — the move
was reconciled item by item against both trees, with every item accounted for.

## What is in the tree

Four top-level **buckets**, holding **18 agents** and **21 skills** between them:

| bucket | agents | skills | what it covers |
|---|---|---|---|
| `AI_philosophy/` | 2 | 0 | philosophy of technology; AI safety scholarship |
| `CCRT_QA_QC_debugging/` | 9 | 0 | the routing probe agents, used to measure which model actually answered a subagent launch |
| `phyllosphere/` | 1 | 5 | leaf-surface microbial ecology: community diversity, assembly null models, guild assignment, dissimilarity modeling, co-occurrence networks |
| `ecosystem_and_ecophys_modeling/` | 6 | 16 | ecosystem and plant-physiology modeling, micrometeorology, scientific machine learning — split across two sub-buckets, below |

An **agent** is a specialist persona: one file, one job, described in its own opening lines. A
**skill** is a procedure the agent (or you) can load: one directory holding a `SKILL.md`, sometimes
with a helper script beside it. That distinction is the toolkit's throughout — the agent owns *which
method and why*, the skill owns *how to carry it out* — and nothing about it changes because these
particular ones install by hand.

## Browse before you copy: the depth varies

The buckets are **not all the same shape**, and this is the one thing that will trip you up if you
assume. Most buckets hold `agents/` and `skills/` directly:

```
phyllosphere/
  agents/                          <- 1 agent file
  skills/                          <- 5 skill directories, each with a SKILL.md
```

But `ecosystem_and_ecophys_modeling/` holds **two sub-buckets first**, and only inside those do you
find `agents/` and `skills/`:

```
ecosystem_and_ecophys_modeling/
  general_modeling/                <- 5 agents / 14 skills: portable modeling and scientific-ML methods
    agents/
    skills/
  CliMA_km67_specific/             <- 1 agent / 2 skills: tied to one model codebase and one field site
    agents/
    skills/
```

So the rule is: `ls` the bucket, see whether you have landed on `agents/`/`skills/` or on another
layer of buckets, and only then copy. One extra `ls` costs a second; assuming a fixed depth and
copying a directory of directories into `~/.claude/agents/` produces a set of agents Claude Code
will not find, with no error to tell you why.

## The copy commands

Set one variable to this folder, then copy what you want. **Two destinations are possible, and the
choice is about reach.** Copy into `~/.claude/` and the specialist is available in *every* session
on the machine. Copy into a project's own `.claude/` and it is available only inside that project —
which is usually what you want for a specialist that only makes sense for one study system.

```bash
SPEC="/path/to/claude_research_toolkit_v2.7/CCRT_specialists"

# a whole bucket, everywhere on this machine
cp "$SPEC"/phyllosphere/agents/*.md  ~/.claude/agents/
cp -R "$SPEC"/phyllosphere/skills/*  ~/.claude/skills/

# a nested bucket — note the extra level
cp "$SPEC"/ecosystem_and_ecophys_modeling/general_modeling/agents/*.md  ~/.claude/agents/
cp -R "$SPEC"/ecosystem_and_ecophys_modeling/general_modeling/skills/*  ~/.claude/skills/

# one agent and one skill, for a single project only
cd /path/to/your/project
mkdir -p .claude/agents .claude/skills
cp "$SPEC"/phyllosphere/agents/phyllosphere-ecologist.md  .claude/agents/
cp -R "$SPEC"/phyllosphere/skills/amplicon-community-diversity  .claude/skills/
```

Three details worth knowing before you run those. Skills are **directories**, so they need `cp -R`
while agents are single files. Copying is a plain overwrite, so a file arriving with the same name
as one you already have will replace it — check first if you have edited a specialist of your own.
And if a newly copied agent is not recognized on its first launch, launch it again; a new
agent type has been seen to become available mid-session without a restart, so restarting is a
sufficient precaution rather than a necessary wait.

## Why these live outside the installed payload

This is the part worth understanding, because it explains a rule you will meet elsewhere in the
toolkit and it tells you what you may safely edit.

The general payload is **generic on purpose**. It installs into `~/.claude/`, the same content for
everyone, so it must not carry the vocabulary of any one project — a site code, an instrument name,
a particular model codebase. That is not a style preference; it is enforced. A gate named
`lib/scrub_verify.sh` scans the payload's text at install time and **fails the install** if a
project-specific token survives in it. The gate is fail-closed by design: a leaked project token in
a shared toolkit is the kind of thing nobody notices until it confuses someone six months later.

Domain specialists, however, earn their value from exactly that vocabulary. An agent that reasons
about within-canopy flux, or about a specific land-surface model's conventions, is useful *because*
it names those things. Strip the names to satisfy the gate and you have kept the file and thrown
away the specialist.

So the two requirements are genuinely in tension, and this tree is the resolution: the specialists
move **out** of the scanned payload, keep their vocabulary intact, and are installed by hand. The
payload stays generic and its gate stays strict. Neither requirement is weakened, and nothing was
lost in the move — every item was reconciled against both trees when the split was made.

One consequence follows directly, and you will see it stated in the toolkit's own routing
documentation: a file *inside* the payload may name this tree and name an item in it, but must never
write out a full `CCRT_specialists/<bucket>/...` path, because such a path spells out the bucket
names the gate refuses. Naming the tree and the item is enough for a reader to find it here.

## No installer flag reaches this tree

There used to be one, and it is gone. The `--project-items`, `--project-dest`, `--project-bundle`
and `--apply-project-routes` flags are **retired**: passing any of them exits with status 2, writes
nothing, and prints a pointer to this tree and the copy recipe above. If you find one of those flags
in an old note or script, replace it with a `cp` — that is the whole migration.

Copying by hand was chosen over a new flag deliberately. An installer flag would have to be told
which items and which destination, which is the same two decisions `cp` already expresses, in a
syntax you would have to learn and the toolkit would have to keep working. What you lose is a
progress message; what you gain is that the install path for these items is one you can read,
predict, and undo without consulting anything.

## Where to look next

- The toolkit's own `README.md`, one level up, for what the installer *does* ship and how to run it.
- Each agent file's opening description, which states that agent's one job — the reliable way to
  pick one, since names are short and jobs are specific.
- Each skill's `SKILL.md`, whose description says when the skill should fire.
- The roster reference in the toolkit documentation, for how the two trees fit together and which
  specialists and skills are designed to compose.
