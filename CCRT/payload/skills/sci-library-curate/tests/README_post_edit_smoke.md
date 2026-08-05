<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# `post_edit_smoke.py` — VLOOP Item 3: the post-edit functional smoke test

Closes failure family **F5: "compiles" is not "runs".** `py_compile` / an import-lint prove
the bytes parse — not that the changed entrypoint *executes*. The motivating defect: a port
of curator invariants **I16–I19** (`sci-library-curate`, 2026-07-24) compiled clean but was
runtime-broken on two hidden dependencies (`is_cryptic_name`, `_cn_stem`) that were never
ported; the break surfaced only under a manual smoke test.

## What it checks — three non-vacuous claim families

1. **Functional, fresh-import.** The changed module is imported *by path in a brand-new
   subprocess interpreter* (`coverage run` spawns it; the driver `importlib`-loads the
   target inside that process). Hidden-dependency `ImportError`/`NameError` surface there —
   an in-process re-call against an already-populated namespace can hide them. A top-level
   `except Exception` fails the check; it is **not** a `NameError`/`ImportError`/
   `AttributeError` allowlist (that would miss `ZeroDivisionError`, `KeyError`, `TypeError`, …).
2. **Diff-scoped line coverage** (the anti-vacuous half). Every changed *executable* line
   must be executed by the smoke test. The changed-line set comes from `git diff` in a git
   work tree, and from an **explicit `changed_lines` argument** otherwise. The CCRT payload
   is **not** a git repo, so that fallback is load-bearing. An unknown changed-set (neither
   source) or an empty diff is a hard **FAIL**, never a silent pass over nothing.
3. **Diff-scoped branch coverage.** For a covered changed line that branches, every arc must
   be taken ("each new branch is hit"). Requires `coverage run --branch`.

Emits a `[[vloop:post_edit_smoke n_claims=N n_fail=M]]` marker and registers a gate in the
`vloop_harness` `GATES` registry.

## Dependencies & layout

- **`coverage`** (tested with 7.15.2). Install into a dedicated env: `pip install coverage`.
- **`vloop_harness.py`** — the provided substrate (marker emission, three-way verdict,
  fixture-pair contract). `post_edit_smoke.py` imports it; it must sit alongside
  `post_edit_smoke.py` (or one directory up, for the `tests/` layout — a copy is kept in
  `tests/` for import resolution). This bundle does not vendor its own copy; use the
  canonical `vloop_harness.py` artifact.

```
post_edit_smoke.py            # the reusable checker
README_post_edit_smoke.md
REGISTRY_VERDICT.txt          # verbatim registry report
tests/
  test_post_edit_smoke.py     # fixture-pair driver + intended-reason asserts
  vloop_harness.py            # copy, for import resolution when run from tests/
  fixtures/
    i17_port_broken.py        # (a) hidden-dependency NameError — the real I16-I19 shape
    si_miner_importerror.py   # (b) ImportError on fresh import
    nonexercising.py          # (c) THE vacuous pass: runs clean, changed lines untouched
    otherexc.py               #     non-allowlist exception (ZeroDivisionError)
    branch_miss.py            #     branch-independence proof: lines 100%, one arc untaken
    i17_port_fixed.py         # known_clean: correctly-ported counterpart
```

## Run

```bash
python3 vloop_harness.py            # confirm the substrate self-tests PASS (21/21) first
python3 post_edit_smoke.py          # built-in self-demo (inline temp fixtures, no git)
cd tests && python3 test_post_edit_smoke.py   # full fixture-pair suite (exit 0 = PASS)
```

## Using it on a real edit

```python
from post_edit_smoke import run_smoke, register_smoke_gate
spec = {
    "name": "my_edit",
    "target_path": "skills/<skill>/<module>.py",
    # git target -> pass repo_root (+ optional git_ref); non-git -> pass changed_lines=[...]
    "repo_root": "/path/to/repo",          # OR:
    "changed_lines": [2009, 2010, 2011],   # load-bearing for the non-git CCRT payload
    "driver_body": 'mod.check_i17(rows)',  # statements exercising the changed entrypoint via `mod`
}
result = run_smoke(spec)   # result["n_fail"] == 0 and result["func_ok"] is the pass condition
```

## Verified behaviour (see `REGISTRY_VERDICT.txt` and the test output)

- Each planted defect fails **for its intended reason** — not merely "fails".
- The **non-exercising** fixture (nothing raises, `func_ok=True`) still **FAILs on coverage** —
  the vacuous pass a functional-only gate would wave through.
- **Branch** coverage bites **independently**: `branch_miss` runs fine with 100% changed-line
  coverage yet fails on an untaken arc.
- **Both-ways proof:** a deliberately crippled functional-only version of the gate is caught
  by the harness as a `FALSE GREEN` on the non-exercising known-bad, while the real gate PASSes.
