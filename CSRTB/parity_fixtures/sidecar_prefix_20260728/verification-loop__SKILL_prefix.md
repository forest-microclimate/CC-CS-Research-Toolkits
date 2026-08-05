---
name: verification-loop
description: Close your own loop instead of asserting a state you have not checked. Invoke WHEN about to write a durable claim about a state you did not just recompute — a count ("5,154 orphans", "48 skills"), a field value ("version is 2.4", "sha is abc123"), or a state ("the gate passes", "the folder is clean") — into a memory row, an artifact, a report, a changelog, or a handoff. Also invoke WHEN authoring a NEW check and you need the recipe for turning a manual check into a mechanically-fired loop rather than an exhortation. Ships verify_claims(), a kernel assertion that RAISES on any claim-vs-record mismatch and, fail-closed by default, on a vacuous zero-claim check (override only with an explicit allow_empty=True), and emits a [[vloop:...]] marker so an auditor can tell "checked and clean" from "never ran". Use it BEFORE the claim ships, not after someone catches it. Also ships require_receipt() and require_verification_status(): return-based sibling gates (with a CLI, exit 0/2) for when you are about to write a "verified"/"byte-identical"/"passed" claim with no receipt (DISC-07), or a durable "this fix works" efficacy claim with no honest verification_status (DISC-18).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# verification-loop

**The failure this closes:** asserting a state without checking it against the
ground-truth record. Across 76 evidence-graded failures mined from seven of our own
conversations, this one meta-pattern — *efficacy from existence*, "the check exists,
therefore it worked" — accounted for **53%** (families F1+F2+F3: assertion-without-
verification, prose/artifact drift, stale-state). It is the single highest-leverage
class to close, and it is closable because the claims that matter have a machine-
resolvable source.

## The rule

> A durable claim about a recomputable state must be **recomputed at write time**,
> not recalled. The recompute is the loop; PASS is the definition of done.

## MECHANICAL vs DISCRETION — read this before trusting anything here

A check written into a skill body — including this one — fires only if the skill is
loaded AND the agent chooses to run it. That is **model discretion**, i.e. the
exhortation this skill exists to replace. A check is a real loop only when
**mechanically fired**:

- **Claude Science:** a **kernel assertion** — `verify_claims()` below. It RAISES.
  The producing skill MUST call it, and its PASS is what "done" means.
- **Claude Code:** a **hook** — `PreToolUse` on the write path, which can exit 2 to
  BLOCK the tool call.

**Honest boundary:** free chat prose is ungated on both platforms. Claude Science has
no turn hook and no chat-prose interception; Claude Code's hooks gate tool calls, not
prose. This loop gates **tool- and kernel-mediated outputs** — memory writes, artifact
saves, reports, changelogs, catalog rows. It does not gate an unsourced sentence in
chat, and claiming otherwise would be the same overclaim it targets.

## Scope — a CLOSED taxonomy, drawn so enumeration is not itself a judgment

Only claims with a machine-resolvable source are in scope, and each is **tagged at
write time** with one of exactly three tags:

| tag | predicate | needs |
|---|---|---|
| `count-over-artifact` | `len/grep(source) == asserted` | `source`, `asserted` (+ optional `pattern`) |
| `field-value` | `parse(source[field]) == asserted` after a **declared** normalization | `source`, `field`, `asserted` (+ `normalize`) |
| `state` | `rerun(entrypoint); observed == asserted` | `asserted` **and** `observed` from a real rerun |

**`state` is the weakest of the three and you must know why.** `count-over-artifact` and
`field-value` recompute from a file on disk — there is an independent operand. `state`
compares two values *you* supplied, so it verifies only that you wrote down what you
observed; it cannot tell that you actually observed it. Populate `observed` from a live
rerun in the same cell (`observed=run_gate()`), never from memory or from an earlier
turn's output. Where a claim can be reduced to a count or a field, prefer those tags.

**Explicitly OUT of scope:** free-prose assertions with no single source value — "this
approach is more robust", "we chose X because Y", "the design is cleaner". These are
not checkable by substring or recompute; semantic entailment is LLM judgment. Declaring
the boundary is deliberate: it keeps claim-enumeration from becoming an open-ended
judgment call, which is where a "deterministic" check would otherwise fail at step 0.

Normalization must be **named**, never implied — `exact`, `strip`, `casefold`,
`collapse-space`, `numeric`, `sha256`. An unnamed normalization makes `==`
non-deterministic.

## The anti-vacuous rule (the trap that makes checks lie)

A check that extracts **0 claims** finds 0 mismatches and reports green. A prose
output full of unverified assertions sails through. So:

> `verify_claims()` RAISES on **any** empty claim list — fail-closed, whether or not you
> passed `durable_output` — and it always emits the **enumerated claims table**.

An empty table is a **visible failure**, not a silent pass. If an output genuinely makes
no recomputable claim, say so on the record with `allow_empty=True`; that is a decision
an auditor can see, unlike a green from an extractor that silently returned `[]`.
Pass `durable_output=` the text you are about to ship so the failure message names it.
The same discipline applies to a `state` claim with no `observed` value, and to an
unresolvable `source`: both FAIL rather than skip.

**`strict=False` is a footgun, not an option.** It downgrades a real mismatch to a
silent return — the same move as wrapping the call in `try/except`. It exists for
gate self-testing, and it writes a loud stderr warning so a non-raising run is never
invisible. Do not use it in a producing path.

## Usage

```python
from kernel import verify_claims        # auto-loaded when this skill is loaded

claims = [
  {"id": "n_skills", "tag": "count-over-artifact",
   "source": "bundle_src/skills", "pattern": None, "asserted": 50},
  {"id": "version",  "tag": "field-value",
   "source": "build_config.json", "field": "bundle_version",
   "asserted": "2.5", "normalize": "strip"},
  {"id": "gate",     "tag": "state",
   "asserted": "PASS", "observed": run_gate()},        # a REAL rerun, not a memory
]

res = verify_claims(claims, name="bundle-ship", durable_output=changelog_text)
print(res["marker"])        # [[vloop:bundle-ship n_claims=3 n_fail=0]]
print(res["table"])         # ship this table WITH the claim
```

It raises on mismatch. Do not wrap it in `try/except` to keep going — catching the
assertion converts the loop back into an exhortation.

## The three verdicts (never a bool)

`vloop_verdict(text)` returns one of:

- **`MARKER_ABSENT`** — no marker. The check **did not demonstrably run**. This is
  **not** a pass. Collapsing it into "clean" is the exact false-green being closed.
- **`CLEAN`** — marker present, `n_fail == 0`.
- **`DEFECTS`** — marker present, `n_fail >= 1`.

A marker preceded by a quote character is string **data** (a doc quoting the format),
not an emission — so documentation never reads as having fired.

## Emit-time assertion gates — `require_receipt` + `require_verification_status`

Two more kernel gates carry two more record-integrity classes to the write point.
**Unlike `verify_claims`, these RETURN a verdict dict — they do NOT raise.** They
follow the delegation-planning kernel's contract: `{gate, verdict, failures,
marker, …}`, stdlib, py3.9, never `sys.exit` in library use.

| gate | FAILs when | marker | carries |
|---|---|---|---|
| `require_receipt(claim_text, receipts)` | `claim_text` has a verification token AND no valid receipt backs it | `[[receipt_gate tokens=T receipts=M verdict=…]]` | **DISC-07** verification-theater |
| `require_verification_status(row)` | status ∉ {verified-working, attempted-untested, unknown}, or `verified-working` with no `citation` | `[[vstatus_gate verdict=…]]` | **DISC-18** efficacy-from-existence |

**`require_receipt`** — a verification **token** (`verified`, `passed`,
`byte-identical`, `all green`, `all-N-passed`, `addressed`, `reproduced`,
`confirmed`; word-boundary, case-insensitive) is a claim that a check *ran*; it
needs a **receipt** to back it — a `{"kind": hash|diff|exit_code|read_ref|test_tally,
"value": <non-blank>}`. ≥1 token + 0 valid receipts ⇒ **FAIL** naming the tokens;
0 tokens ⇒ **PASS `vacuous=True`** (nothing was claimed); ≥1 token + ≥1 valid
receipt ⇒ PASS. `M` counts **valid** receipts, so `tokens=1 receipts=0 verdict=FAIL`
reads as "one claim, nothing backs it". Reproduces arc=55710d86 msg=5222 —
`"BYTE-IDENTICAL"` asserted from size + four row counts, no hash.

**`require_verification_status`** — a durable **efficacy/behavior** claim (a
"this fix works" row in a lessons / countermeasure / memory record) must carry an
honest `verification_status`. A brand-new fix defaults to `attempted-untested`;
`verified-working` is earned only with a non-empty `citation` (a measured
before/after, ablation, or test). **Existence is not efficacy.** Reproduces
arc=6544bef8 msg=840 — a just-written rule recorded as "a solution that worked".

**Firing is `[DISCRETION]` in library use — say so.** Claude Science has no turn
hook and no chat-prose interception, and these gates RETURN rather than raise, so
a library caller *can* ignore the verdict. The **emitted marker is the auditable
object**: marker-ABSENCE means the check did not demonstrably run, and that
absence is what a Reviewer flags (same contract as `[[vloop:…]]`). The
**mechanical** enforcement is the CLI subcommand — it maps FAIL → exit 2.

### CLI — one subcommand per gate (incl. `verify_claims`)

```
python3 kernel.py verify-claims  -i claims.json    # verify_claims (raises internally -> exit 2)
python3 kernel.py receipt-gate   -i receipt.json   # require_receipt
python3 kernel.py vstatus-gate   -i row.json       # require_verification_status
```

JSON in (file, or `-`/stdin) → JSON + marker out, **exit 0 PASS / 2 FAIL** (the
delegation-planning kernel's contract). `verify-claims` wraps the *raising*
`verify_claims`: a mismatch or vacuous check becomes exit 2 with the `[[vloop:…]]`
marker on the last line. Fixtures: **`fixtures_new_gates.py`** (standalone;
recorded-confession red cases + monkeypatch-and-restore mutation checks that gut
one guard constant and prove the red fixture would catch the regression).

> The sibling gate **`verify_before_assert`** (SEED-01, assert-from-recollection:
> a locally checkable value/count/ID/version/status claim needs a this-turn read
> receipt) lives in the **provenance-guard** skill, not here — see its kernel.
> Not restated in this skill.

## Authoring recipe — turning a manual check into a loop

When you catch yourself performing the same check by hand, encode it:

1. **Name the predicate.** One sentence, mechanically decidable: "every registered gate
   has a known-bad fixture it fails." If you cannot write it without "should" or
   "carefully", it is not yet a predicate.
2. **Pin the operands.** Exactly what is compared to exactly what, including the
   transform between them. This is where checks silently break — comparing a raw file
   byte to a JSON-encoded string mismatches at zero drift.
3. **Name the firing point.** Kernel assertion (Science) or hook (Code). "The skill
   body says to do it" is not a firing point; label it `[DISCRETION]` and stop calling
   it a loop.
4. **Emit the marker.** `vloop_marker(name, n_claims, n_fail)`. A check whose output
   cannot be grepped cannot be verified.
5. **Fixture it both ways.** A **known-bad** it MUST fail (reproducing the real defect
   that motivated it — cite the frame or lesson id) and a **known-clean** it MUST pass.
   `gate(known_bad) == FAIL` is necessary, not sufficient: a trivially-bad fixture
   passes that test while the real condition persists.
6. **Verify the verifier.** Run step 5 before you trust a green. A check that has never
   failed on purpose has never been tested.

## Placement patterns

- **standalone** — this skill: the recipe plus the reusable assertion.
- **embedded** — other skills call `verify_claims()` at their write point. Mechanical
  *because it is a kernel assertion*, not because it is written down.
- **chained** — the producing skill asserts, then a separate gate re-checks the shipped
  artifact.
- **on-every-install** — the parity/currency check at install time.

## Non-goals

Not a substitute for the platform Auditor's fresh-context review (this is the
deterministic linter the Auditor can call). Not a prose-quality checker. Not a semantic
entailment engine — a paraphrase with no verbatim evidence span is out of scope by
construction, and admitting one would reintroduce the judgment this replaces.
