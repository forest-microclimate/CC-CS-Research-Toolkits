---
name: design-rationale
description: >
  Invoke WHEN the task is to recover the IMPLICIT rationale, design philosophy, or governing
  principles behind a body of work — a codebase, toolkit, literature, method, dataset, or
  experimental program — and state them explicitly; OR to abstract a transferable schema from
  concrete instances and say what generalizes beyond them. This is the THINKING procedure that
  recovers, grounds, and grades rationale (inventory → cluster by friction → abstract → ground to
  instance → grade stated/inferred → tag scope → falsify on an out-of-corpus case). Fires on
  "what's the design philosophy here", "reverse-engineer the rationale", "what's the transferable
  principle", "what generalizes from these examples", "why is it built this way". NOT for revising
  existing prose (→ writing-science), setting an expert register (→ expert-prose-style), or
  writing the teaching guide itself (→ teaching-narrative) — those RENDER the content this
  procedure produces.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# design-rationale

Recover the higher-order rationale a body of work runs on — the design philosophy and
governing principles implicit in it — and separate the **transferable schema** from the
specific instances that embody it. The corpus can be anything: a codebase, a toolkit, a
literature, an experimental program, a dataset, or a single complex method.

## Why this needs a procedure (the failure it prevents)

"Extract the meta-rationale" is the weakest possible instruction. Left unconstrained, a
capable model produces confident, fluent abstraction that *sounds* like the work's
governing logic but that the work does not actually support — a plausible story fitted
over the artifacts. That failure is the whole risk of this task, and prose exhortations
("be rigorous", "stay grounded") do not prevent it: a model reliably forgets to check and
reliably reports having checked. What prevents it is a **structural spine** — disciplines
that bind each stated principle to evidence, and a ledger that makes an ungrounded
principle a *hard error* rather than a matter of good intentions. Recover boldly; ground
relentlessly.

## When this fires vs its neighbors

This skill produces the grounded rationale **content**. It does not write prose and it
does not judge quality.

- **design-rationale** (this) — INPUT is a corpus; OUTPUT is its implicit logic made
  explicit and graded. The *thinking*.
- **teaching-narrative** — renders content as a guide that teaches a reader to apply it.
  The *writing*. Reach for it when the deliverable is a human-readable explainer.
- **writing-science** — revises existing prose toward publication (compress-to-cite).
- **expert-prose-style** — sets an expert flowing-prose register. A toggle, not a task.

Compose freely: recover with this, render with teaching-narrative. They fire independently.

## The procedure

Run these in order. Steps 1–2 are discovery; 3–7 produce one ledger row per principle
(the ledger is defined below). The friction each row records is the one you identified when
clustering in step 2 — carry it onto the row, grade it (`stated`/`inferred`) or mark it
`value-driven:`, and re-check it under discipline 4 when you ground.

1. **Inventory** — list the concrete instances the corpus actually contains: the
   decisions, mechanisms, conventions, repeated moves. Name them specifically enough to
   cite later (file, section, function, passage, experiment).
2. **Cluster by friction** — group instances by the *problem or friction each answers*.
   This is a discovery heuristic, done over instances, early. It is NOT the same as
   friction-grounding (discipline 4): clustering sorts raw instances; friction-grounding
   later re-checks the *finished* principle still names its problem, because abstraction
   can shed the friction on the way up.
3. **Abstract** — for each cluster, state the governing principle: the *why* the
   instances share. One claim, stated plainly.
4. **Ground** — bind the principle to ≥1 named instance from the inventory. If you cannot
   name one, you have a hypothesis about the work, not a finding *from* it — cut it or
   regrade it (step 5).
5. **Grade** — tag the principle `stated` (the work says this about itself — a comment, a
   README, a stated aim) vs `inferred` (your reading of a pattern the work does not
   articulate). Never present an inference as the work's own intent.
6. **Scope** — tag `instance` (warranted only for the named instances) vs `schema`
   (claimed to hold for any comparable case). This is the load-bearing separation; see
   the spine below.
7. **Falsify** — for each `schema` claim, name a real out-of-corpus case and apply the
   claim to it. If it does not fit, weaken it: re-tag to `instance`, or bound it ("holds
   for X-type systems, not Y"). Ship the weakened claim, not the overreach.

## The rigor spine — 5 disciplines, 2 tiers

The disciplines are not decoration; each catches a *distinct* failure, so dropping any one
opens a specific hole. (Verified by construction: each has a private witness — an output
that fails only it.)

**Tier 1 — cheap, tagged per principle as you go:**

1. **Traceability** — every principle binds to ≥1 named instance. *Catches:* free-floating
   confabulation with no corpus basis.
2. **Evidence-grading** — `stated` vs `inferred`. *Catches:* your inference laundered as the
   work's own stated intent.
3. **Scope-of-validity** — `instance` vs `schema`. *Catches:* an instance-observation
   promoted to a universal claim without warrant (the single most common overreach — and
   the specific thing this whole capability exists to resist). *Note the name:* the
   discipline is deciding each principle's **warrant boundary**, not laying claims out in
   two columns. The visual side-by-side is presentation and belongs to teaching-narrative;
   the scope *decision* is the rigor act and lives here. You cannot render a split you
   never made.
4. **Friction-grounding** — every principle names the friction/problem it resolves, or is
   explicitly marked `value-driven:` with a reason. *Catches:* a true, well-graded,
   well-scoped **description** ("uses X") mistaken for a **rationale** ("uses X because Y
   failed"). A rationale is a reason-*for*; strip the problem and only a description
   remains.

**Tier 2 — expensive, run once on the finished schema:**

5. **Falsification** — apply each `schema` claim to a named out-of-corpus case; weaken what
   does not fit. *Catches:* a "universal" pattern overfit to its own corpus. Only
   `schema`-scoped claims carry this obligation — an `instance` claim is settled by
   enumerating the corpus, so scope-of-validity (3) is a *precondition* for this test: no
   scope tag ⇒ nothing to falsify. Ship (3) and (5) together.

### The one trap to avoid: manufactured friction

Discipline 4 has a failure mode you must actively resist. A hard "name a friction for every
principle" rule *pressures* you to invent a plausible problem when the corpus evidences
none — reverse-engineering a motive to fill the box. That is the narrative analog of
HARKing: a story fitted to the outcome always fits, so it has zero discriminating power, and
it manufactures the exact unsupported-rationale failure the spine exists to prevent. Three
defenses, all of which reuse disciplines you already apply:

- **Grade the friction itself** (`stated`/`inferred`) and bind it to an instance, exactly
  as you grade the principle. A friction you inferred is tagged `inferred` — never passed
  off as the work's own reason.
- **"No friction — value-driven, and here's why" is a valid, honest outcome.** Set
  `friction='value-driven: <reason>'`. This is load-bearing for discipline-agnosticism:
  in a literature or a method, governing principles are often goal- or value-shaped (a
  method's generality, a value like composability), not problem-shaped. Forcing a problem
  frame onto them is itself the over-narrow projection this capability warns against.
- **Prefer a friction that predicts beyond its instance.** A genuine friction predicts
  *other* observable features of the corpus ("if Y drove this, the work should also do
  Z"). One that predicts nothing beyond the choice it was invented for is confabulation.
  This turns friction-grounding into a checkable claim — and hands that prediction
  straight to the falsification step.

## The ledger — force the spine, don't trust it

The skill ships `kernel.py` (auto-loaded), a traceability ledger that makes the Tier-1
disciplines *structural* instead of advisory. Build one row per principle; the validator
fail-closes on any row missing a discipline:

```python
led = new_ledger()
add_principle(led,
    principle="Installers are idempotent — re-running never double-applies",
    instances=["install.sh merge_settings()", "copy_tree additive semantics"],
    grade="stated",                 # the README states this aim
    scope="schema",                 # claimed for any installer, not just this one
    friction="re-running a setup script corrupted state on partial failure",
    friction_grade="inferred",      # the work does not say this; you read it from the design
    falsification="Checked against Homebrew formulae: idempotent re-run holds — fits.")
report = validate_ledger(led)       # {'ok': True/False, 'violations': [...]}
assert report["ok"], report["violations"]
print(ledger_to_markdown(led))      # the grounded content, ready to render
```

`validate_ledger` enforces: ≥1 instance (traceability), grade ∈ {stated, inferred}
(grading), scope ∈ {instance, schema} (scope-of-validity), a friction or a `value-driven:`
note with a graded friction (friction-grounding), and — for `schema` rows only — a
non-empty falsification result. An ungrounded principle cannot pass.

**The honest limit — read this twice.** The validator enforces **presence, not
correctness**. It catches "this principle has no instance"; it *cannot* catch "this
principle cites the *wrong* instance" or "this friction is fabricated but non-empty." The
green check proves the *form* of the spine was followed; only the falsification pass and a
human's judgment prove the *content* is true. Never report a clean `validate_ledger` as if
it certified the rationale is correct — it certifies only that no discipline was skipped.

## Worked micro-example (why scope + falsification matter)

Corpus: three of a toolkit's hooks return exit code 2 to block an action.
- **Weak (fused, unwarranted):** "The toolkit blocks actions via exit-2, so any hook should
  use exit-2 to block." — an instance-observation and a universal welded together, the
  inductive leap unmarked.
- **Disciplined:** Principle "exit-2 signals a hard block" — `instance`-scoped, grounded in
  the three hooks, `stated` (the hook contract documents it). Separate `schema` claim "hook
  frameworks should reserve one exit code for hard-block vs soft-warn" — `inferred`,
  friction = "mixing block and warn on one code made failures ambiguous" (`inferred`),
  then *falsified* against Git's pre-commit protocol (which does exactly this) → fits, keep;
  had it not fit, bound it. The disciplined version ships two claims a reader can trust and
  lift separately; the weak version ships one they cannot.

## REF

- `eliciting-llm-behavior` — why a required non-empty field beats a prose plea (the
  structural-constraint argument the ledger rests on).
- `teaching-narrative` — the render engine for the recovered content.
- `machine-md` — if the recovered rationale is being written up for an LLM reader.
