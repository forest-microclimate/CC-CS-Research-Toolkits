---
name: provenance-guard
description: >-
  Invoke WHEN about to fit a model or render a figure, before a kernel restart
  or session end, or when hand-checking that no intermediate feeding a
  published result was lost to /tmp. Guards against the provenance-failure
  class where a file feeding a durable output is written to an untracked
  scratch path (/tmp) and lost on kernel restart — auto-capture and lineage
  never see it. Ships three auto-loaded helpers: audit_tmp_provenance() (the
  /tmp-fit linter — scans this project's execution_log for the bug fingerprint),
  checkpoint_frame(df, name) (save-the-frame-before-you-fit, one call to
  ./handoff/), and verify_before_assert(facts) (the SEED-01 assert-from-
  recollection gate — every asserted value/count/ID/status names the read that
  grounds it). Encodes the rule "save every file another cell will READ, before
  the fit" and "never hand off between kernels through /tmp — use ./handoff/".
  Additive and non-destructive: it warns, it never deletes or auto-grants.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# provenance-guard

Mechanical defence against one specific, silent, HIGH-severity failure:
a file that feeds a durable output (a model frame, a plot input) is written
to an untracked scratch path (`/tmp/…`), so workspace auto-capture never sees
it, lineage never edges to it, and a kernel restart destroys it. The *outputs*
survive (they were written workspace-relative); the *inputs* vanish, and the
lineage graph reports healthy provenance while the proximal input is one
restart from gone.

Motivating incident: `PROVENANCE_FAILURE_bug_report.md`
(artifact `51e2e35f-36ae-4247-a783-7b56b14d2aab`). A model frame feeding a
published figure was written to `/tmp/guild_additive_modelframe.csv`, never
promoted, and lost on a kernel restart — recoverable only by forensic
re-derivation ~17.5 h later. A second frame feeding another published figure
was in the same state at diagnosis time. This is a recurring workflow shape,
not a one-off.

## Three auto-loaded helpers (kernel.py)

`kernel.py` loads into the python kernel when this skill is loaded — no import
needed.

- `audit_tmp_provenance(execution_log=None, artifact_names=None,
  fit_markers=None, fig_markers=None, read_funcs=None, write_funcs=None,
  scratch_dirs=None, scratch_exts=None, extra_save_scan=True, quiet=False)
  -> list[dict]`
- `checkpoint_frame(df, name, save=True, fmt="parquet", handoff_dir="handoff")
  -> str`
- `dump_execution_log(path=None, scratch_only=True) -> str` (repl-only bridge;
  see "Running the linter" below)
- `verify_before_assert(facts, reads=None) -> dict` (the SEED-01 assert-from-
  recollection gate; see "The assert-from-recollection gate" below)

## Workflow rules this skill encodes

1. **Save every file another cell will READ, before the fit.** The old rule
   ("save every derived file") fired on a fit's *outputs* (figure, results
   table) but never on its *inputs* — the exact blind spot that lost the frame.
   Any file handed to `brm` / `glmer` / `lmer` / `gam` / `stan` / a `savefig` /
   `ggsave` is a first-class input: make it durable **before** the fit runs.
   `checkpoint_frame(df, name)` is that save, in one call.
2. **Never hand off between kernels through /tmp.** The workspace is shared
   across python/bash/R kernels **and** tracked; `/tmp` is shared but invisible
   to auto-capture. Use `./handoff/<name>.parquet` (what `checkpoint_frame`
   writes). Reserve `/tmp` only for throwaway scratch no durable output reads.
3. **Run the linter before a kernel restart or session end.** It is a
   pre-restart / pre-submission audit — the last check that nothing feeding a
   result is scratch-only.

## Save-the-frame-before-you-fit: checkpoint_frame

Instead of `mf.to_csv("/tmp/modelframe.csv")` then fitting in another kernel:

```python
path = checkpoint_frame(mf, "guild_additive_modelframe")
# -> writes ./handoff/guild_additive_modelframe.parquet (tracked + cross-kernel)
# -> prints the exact save_artifacts(...) call to make it a durable checkpoint
# -> returns the path; hand THIS path to the fit worker, not a /tmp path
```

`checkpoint_frame` writes to `./handoff/` (falls back to CSV if no parquet
engine), appends the path to `handoff/_provenance_to_save.txt`, and prints the
`save_artifacts(files=[...], checkpoints=[...])` call for you to run. It does
**not** itself promote to an artifact — `save_artifacts` is an agent tool, not
a host method — so run the printed call to complete the durable save.

## Running the linter: audit_tmp_provenance

THE FINGERPRINT: a cell that READS a scratch path (`/tmp/*.csv|*.rds|…`) AND
contains a fit/figure marker, where that path's basename was NEVER promoted to
a durable artifact. Severity: **CRITICAL** = read by a model-fit cell (a model
frame one restart from oblivion) · **HIGH** = read by a figure cell, or a
fit/fig cell wrote it to scratch · **WARN** = consumed downstream but unsaved,
no fit/fig. Durable files and write-once-never-read scratch are not flagged.
Markers inside string literals (a keyword list like `"brm(","gam("`) are
ignored via a quote-guard, so a linter-like cell does not flag itself.

The linter reads `execution_log`, which is reachable **only** via `host.query`
— and `host.query` lives in the `repl` tool, not the python kernel. So:

**Path A — run it from a `repl` cell (simplest; host.query is live there):**

```python
exec(host.skills.read("provenance-guard", "kernel.py")["content"])
audit_tmp_provenance()          # prints the warning list, returns list[dict]
```

**Path B — run it in the python kernel (where the sidecar already auto-loaded):**
`host.query` is absent there, so first stage the log from a `repl` cell, then
audit in python:

```python
# repl cell:
exec(host.skills.read("provenance-guard", "kernel.py")["content"])
dump_execution_log()            # -> handoff/execution_log_dump.json
```
```python
# python cell (sidecar already loaded):
audit_tmp_provenance()          # reads the staged dump; host.artifacts is live here
```

If neither `host.query` nor a staged dump is reachable, the function raises
with these exact instructions rather than returning a silent empty list.

## Acting on a flag

For each flagged path, either (a) re-run its producer writing to
`./handoff/<name>` instead of `/tmp` (then `save_artifacts`), or (b) if the
producing cell is in the `execution_log`, re-derive and `save_artifacts` the
file now. CRITICAL rows (model frames) are the priority — those are the ones
whose loss forces forensic re-derivation.

## The assert-from-recollection gate: verify_before_assert (SEED-01)

**WHEN about to emit an asserted value / count / ID / status ⇒ each carries its
`source_read_ref` naming the read that grounds it; run the gate, let the marker land.**

`verify_before_assert(facts, reads=None)` is the mechanical form of "never assert from
recollection." It is the **SEED-01** gate the failure catalog prescribes for
provenance-guard: the recorded confession (frame `45171f5d`, msg 514/624) wrote three
artifact version-ids *invented from memory*, none grounded by a read. The gate makes
every asserted datum name its read, and FAILS the batch when one does not.

- `facts`: a list of `{claim, value, source_read_ref}` (a lone dict is one fact).
- Two modes:
  - **presence-only** (`reads=None`): a fact FAILS when its `source_read_ref` is
    missing/blank or a placeholder token —
    `ASSERT_PLACEHOLDER_REFS = {"", "n/a", "memory", "recalled"}`. Match is whole-value
    after casefold + whitespace normalization, **never substring**, so
    `"read of memory_map.json"` (which merely *contains* "memory") PASSES.
  - **strict** (`reads=<this-turn read ids>`): a fact ALSO FAILS when its ref is not
    among the reads you pass — the grounding read did not happen this turn. The natural
    source for `reads` is this turn's `execution_log` rows (the record
    `audit_tmp_provenance` already queries), **but `verify_before_assert` never calls
    `host.*`** — you inject `reads`, exactly as delegation-planning injects `list_models`.
- Returns `{gate, verdict, n, reads_mode, vacuous, failures, marker}`; the marker is
  exactly `[[assert_gate n=N verdict=PASS|FAIL]]`. `n=0` (empty batch) is PASS but flagged
  `vacuous`, so an empty check is visible rather than laundered as green. Library use
  NEVER raises or exits; only the CLI maps verdict → exit code.

```python
# a repl / python cell, sidecar already loaded:
verify_before_assert([
    {"claim": "row count", "value": 4096, "source_read_ref": "read of memory_map.json"},
])  # -> verdict PASS, marker [[assert_gate n=1 verdict=PASS]]
```

**Honest firing scope [DISCRETION].** Claude Science has **no hooks** — nothing forces
this gate to run. It is `[DISCRETION]`-fired by the profile discipline, and the auditable
object is the **marker's ABSENCE on a span that asserts values**: a Reviewer greps an
asserting turn for `[[assert_gate …]]` and flags its absence. The gate does **not** judge
whether a *cited* read actually says what the caller claims (no in-process check can), and
presence-only mode passes a disguised recollection like `"recalled from last session"`
(not the exact token `"recalled"`) — only the strict `reads` mode catches that. What it
removes is the ungrounded assertion and the placeholder/blank ref that SEED-01 consisted
of. Verification status: **fixtures-verified for FORM** (red-before-green + mutation in
`fixtures_assert_gate.py`); its *efficacy* at reducing SEED-01 recurrence is a measurement
question, not asserted here.

**CLI** (additive; this kernel had no CLI before this pass):
`python3 kernel.py assert-gate -i case.json`, where `case.json` is a bare facts list or
`{"facts": […], "reads": […]}`; prints the result JSON then the marker, exit 0 PASS / 2
FAIL. Run the fixtures with `python3 fixtures_assert_gate.py` (exit 0 = all behaved).

## Safety

This guard is additive. It warns and stages; it never deletes a file, never
promotes an artifact on its own, and never weakens any approval or safety
check. `save_artifacts` remains an explicit agent action.
