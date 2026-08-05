#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
r"""post_edit_smoke.py -- VLOOP Item 3: the post-edit functional smoke test.

Closes failure family F5: "compiles" is not "runs". `py_compile` / an import-lint give a
VACUOUS pass -- they prove the bytes parse, not that the changed entrypoint EXECUTES.

MOTIVATING DEFECT (cite: sci-library-curate I16-I19 port, 2026-07-24)
A port of curator invariants I16-I19 compiled clean but was runtime-broken on TWO hidden
dependencies (`is_cryptic_name`, `_cn_stem`) that were never ported. `py_compile` was
green; the break surfaced only under a manual smoke test. Two lessons drive this checker:
  * A NameError from an unported helper is invisible until the code actually RUNS under a
    fresh import -- an in-process re-call against an already-populated namespace can hide it.
  * "It ran" is not "the CHANGED code ran". A test that exercises a pre-existing function
    while the new block sits untouched is a vacuous pass no functional check alone detects.

WHAT THIS CHECKS -- three claim families, none vacuous:
  (1) FUNCTIONAL, fresh-import.  The changed entrypoint is exercised in a brand-new
      subprocess interpreter (`coverage run` spawns it; the target is imported by path via
      importlib inside that process). Hidden-dependency ImportError/NameError -- and ANY
      other Exception -- surface there. A top-level `except Exception` fails the check; it
      is deliberately NOT a NameError/ImportError/AttributeError allowlist (the adversarial
      review's catch: a 3-name allowlist misses ZeroDivisionError, KeyError, TypeError, ...).
  (2) DIFF-SCOPED LINE COVERAGE (the anti-vacuous half).  Every CHANGED *executable* line
      must be executed by the smoke test. The changed-line set comes from `git diff` when
      the target lives in a git work tree, and from an EXPLICIT changed-lines argument
      otherwise. The CCRT payload is NOT a git repo, so that fallback is load-bearing, not
      optional -- and an UNKNOWN changed-set (neither source available, or an empty diff)
      is a hard FAIL, never a silent pass over nothing.
  (3) DIFF-SCOPED BRANCH COVERAGE.  For a changed line that is executed AND branches, every
      arc must be taken ("each new branch is hit"). Requires `coverage run --branch`.

Emits a `[[vloop:...]]` marker (via vloop_harness.emit_marker) and registers a gate in the
vloop_harness GATES registry. Run as a script for a built-in self-demo:  python3 post_edit_smoke.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

# The harness is the substrate: marker emission + the three-way verdict + fixture-pair
# contract all live there. We import it rather than reinventing the marker format.
try:
    from vloop_harness import emit_marker, classify, register_gate, MARKER_ABSENT, CLEAN, DEFECTS
except ImportError:
    # Some launchers (isolated-mode python) do not prepend the script's own directory to
    # sys.path. Add this file's dir AND its parent (the tests/ layout keeps a copy one up).
    _here = os.path.dirname(os.path.abspath(__file__))
    for _d in (_here, os.path.dirname(_here)):
        if _d not in sys.path:
            sys.path.insert(0, _d)
    from vloop_harness import emit_marker, classify, register_gate, MARKER_ABSENT, CLEAN, DEFECTS

GATE_NAME = "post_edit_smoke"
_SENTINEL_NAME = "__smoke_sentinel__.json"
_FUNC_FAIL_EXIT = 97

# `git diff --unified=0` hunk header: @@ -old[,oldn] +new[,newn] @@
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.M)


class CannotScopeDiff(Exception):
    """Raised when neither a git work tree nor an explicit changed-lines set is available.
    Refusing to proceed here is the point: certifying coverage over an unknown changed-set
    would be a vacuous pass."""


# --------------------------------------------------------------------------
# Changed-line derivation:  git diff  ->  explicit fallback  ->  refuse.
# --------------------------------------------------------------------------
def _is_git_worktree(root):
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True, timeout=30)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except (OSError, subprocess.SubprocessError):
        return False


def _git_changed_lines(target_path, repo_root, git_ref=None):
    """New-side line numbers touched by the diff of `target_path`. `git_ref` picks the base
    (e.g. a commit / 'HEAD'); with no ref this is the unstaged working-tree diff."""
    cmd = ["git", "-C", str(repo_root), "diff", "--unified=0", "--no-color"]
    if git_ref:
        cmd.append(git_ref)
    cmd += ["--", str(target_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode not in (0, 1):  # 0 = ok; 1 only appears with --exit-code, which we don't pass
        raise RuntimeError("git diff failed (rc=%d): %s" % (r.returncode, r.stderr.strip()))
    out = set()
    for m in _HUNK_RE.finditer(r.stdout):
        start = int(m.group(1))
        count = 1 if m.group(2) is None else int(m.group(2))
        for ln in range(start, start + count):  # count==0 (pure deletion) contributes nothing
            out.add(ln)
    return sorted(out)


def derive_changed_lines(target_path, repo_root=None, git_ref=None, explicit=None):
    """Return a sorted list of 'changed' new-side line numbers for `target_path`.

    Precedence (each was an explicit design requirement):
      explicit is not None  -> use it verbatim. The load-bearing fallback for non-git
                               targets (the CCRT payload is not a git repo).
      repo_root is a git work tree -> parse `git diff --unified=0` hunk headers.
      neither                -> raise CannotScopeDiff. We do NOT default to an empty set:
                               an empty changed-set would make coverage vacuously pass.
    """
    if explicit is not None:
        return sorted({int(x) for x in explicit})
    if repo_root and _is_git_worktree(repo_root):
        return _git_changed_lines(target_path, repo_root, git_ref)
    raise CannotScopeDiff(
        "no changed-line source for %r: not in a git work tree and no explicit "
        "changed_lines given" % (str(target_path),))


# --------------------------------------------------------------------------
# The fresh-import driver.  Runs in a subprocess under `coverage run --branch`.
# --------------------------------------------------------------------------
def _build_driver(target_path, sentinel_path, driver_body):
    """Generate the driver script. The user supplies `driver_body` (statements that use
    `mod`, the freshly imported target module, to exercise the entrypoint). The framework --
    not the fixture author -- owns the fresh-import-by-path, the top-level `except Exception`,
    and the sentinel, so requirements (1) and (2) cannot be forgotten per-fixture."""
    body = textwrap.indent(textwrap.dedent(driver_body).strip("\n") + "\n", "    ")
    return (
        "import importlib.util, json, sys, traceback\n"
        "_TARGET = " + json.dumps(str(target_path)) + "\n"
        "_SENTINEL = " + json.dumps(str(sentinel_path)) + "\n"
        "def _fresh_import(path):\n"
        "    spec = importlib.util.spec_from_file_location('__smoke_target__', path)\n"
        "    m = importlib.util.module_from_spec(spec)\n"
        "    sys.modules['__smoke_target__'] = m\n"
        "    spec.loader.exec_module(m)   # fresh import: hidden-dep ImportError/NameError raise HERE\n"
        "    return m\n"
        "_res = {'ok': False, 'exc_type': None, 'exc_msg': None}\n"
        "try:\n"
        "    mod = _fresh_import(_TARGET)\n"
        + body +
        "    _res['ok'] = True\n"
        "except Exception as _e:                    # ANY Exception, not a 3-name allowlist\n"
        "    _res['exc_type'] = type(_e).__name__\n"
        "    _res['exc_msg'] = str(_e)[:500]\n"
        "    traceback.print_exc()\n"
        "finally:\n"
        "    open(_SENTINEL, 'w').write(json.dumps(_res))\n"
        "sys.exit(0 if _res['ok'] else %d)\n" % _FUNC_FAIL_EXIT
    )


def _match_file(files_dict, target_path):
    """coverage json keys are whatever path coverage recorded; match by realpath."""
    tp = os.path.realpath(str(target_path))
    for k in files_dict:
        if os.path.realpath(k) == tp:
            return k
    return None


# --------------------------------------------------------------------------
# Core: run the smoke test + coverage, compute the three claim families.
# --------------------------------------------------------------------------
def run_smoke(spec, python_exe=None, keep_tmp=False):
    """Execute one SmokeSpec and return a structured result dict.

    spec keys:
      name         : label
      target_path  : path to the edited .py module (imported by path in a fresh subprocess)
      driver_body  : statements using `mod` (the imported module) to exercise the entrypoint
      changed_lines / repo_root / git_ref : forwarded to derive_changed_lines
    """
    python_exe = python_exe or sys.executable
    name = spec.get("name", "?")
    target_path = os.path.abspath(spec["target_path"])

    # (2)/(3) changed-line set FIRST -- if we cannot scope the diff we fail loudly.
    scope_error = None
    try:
        changed = derive_changed_lines(
            target_path, repo_root=spec.get("repo_root"),
            git_ref=spec.get("git_ref"), explicit=spec.get("changed_lines"))
    except CannotScopeDiff as e:
        changed, scope_error = [], str(e)

    tmp = tempfile.mkdtemp(prefix="smoke_")
    result = {"name": name, "target_path": target_path, "changed_lines": changed}
    try:
        sentinel = os.path.join(tmp, _SENTINEL_NAME)
        driver_path = os.path.join(tmp, "driver.py")
        with open(driver_path, "w") as f:
            f.write(_build_driver(target_path, sentinel, spec["driver_body"]))
        cov_data = os.path.join(tmp, ".coverage")
        cov_json = os.path.join(tmp, "cov.json")

        # (1) FRESH-IMPORT functional run, traced with branch coverage.
        run = subprocess.run(
            [python_exe, "-m", "coverage", "run", "--branch",
             "--data-file=" + cov_data, "--include=" + target_path, driver_path],
            capture_output=True, text=True, timeout=120, cwd=tmp)
        result["run_exit"] = run.returncode
        result["run_stderr_tail"] = run.stderr[-800:]

        sent = None
        if os.path.exists(sentinel):
            try:
                sent = json.load(open(sentinel))
            except Exception:  # noqa: BLE001
                sent = None
        result["sentinel"] = sent
        func_ok = bool(sent and sent.get("ok"))
        result["func_ok"] = func_ok
        result["exc_type"] = None if func_ok else (sent or {}).get("exc_type") \
            or ("<no sentinel: process died before finally>" if sent is None else None)
        result["exc_msg"] = None if func_ok else (sent or {}).get("exc_msg")

        # Coverage JSON (line + branch).
        cov = {"files": {}}
        cj = subprocess.run(
            [python_exe, "-m", "coverage", "json", "--data-file=" + cov_data, "-o", cov_json],
            capture_output=True, text=True, timeout=120, cwd=tmp)
        if os.path.exists(cov_json):
            cov = json.load(open(cov_json))
        result["cov_json_exit"] = cj.returncode

        key = _match_file(cov.get("files", {}), target_path)
        if key is not None:
            fe = cov["files"][key]
            executed = set(fe.get("executed_lines", []))
            missing = set(fe.get("missing_lines", []))
            missing_branches = [tuple(b) for b in fe.get("missing_branches", [])]
            executed_branches = [tuple(b) for b in fe.get("executed_branches", [])]
            measured = True
        else:  # module never measured (typically: import failed -> functional already FAILs)
            executed, missing, missing_branches, executed_branches = set(), set(), [], []
            measured = False
        result["measured"] = measured

        statements = executed | missing
        relevant = sorted(set(changed) & statements) if measured else sorted(changed)
        covered_changed = set(relevant) & executed
        uncovered_lines = sorted((set(relevant) & missing) if measured else set(relevant))
        # A branch arc counts only when its SOURCE line is a covered changed line -- a fully
        # uncovered changed line is already counted once as a missing LINE (no double count).
        changed_missing_branches = [b for b in missing_branches if b[0] in covered_changed]
        changed_branch_arcs = [b for b in (missing_branches + executed_branches)
                               if b[0] in covered_changed]

        result.update(
            statements=sorted(statements), relevant_changed=relevant,
            covered_changed=sorted(covered_changed), uncovered_changed=uncovered_lines,
            changed_missing_branches=changed_missing_branches,
            n_changed_branch_arcs=len(changed_branch_arcs))

        # ----- assemble claims / fails -----
        problems = []
        n_claims = 1                          # the functional claim
        n_fail = 0
        if not func_ok:
            n_fail += 1
            problems.append("FUNCTIONAL: entrypoint raised %s under fresh import%s"
                            % (result["exc_type"],
                               (": " + result["exc_msg"]) if result["exc_msg"] else ""))

        if scope_error is not None:
            n_fail += 1
            problems.append("SCOPE: %s" % scope_error)
        elif not changed:
            n_fail += 1
            problems.append("SCOPE: empty changed-line set -- refusing to certify coverage "
                            "over nothing (vacuous-pass guard)")

        n_claims += len(relevant)
        if uncovered_lines:
            n_fail += len(uncovered_lines)
            problems.append("COVERAGE: %d changed line(s) never executed by the smoke test: %s"
                            % (len(uncovered_lines), uncovered_lines))

        n_claims += len(changed_branch_arcs)
        if changed_missing_branches:
            n_fail += len(changed_missing_branches)
            problems.append("BRANCH: %d arc(s) from changed lines not taken: %s"
                            % (len(changed_missing_branches),
                               [list(b) for b in changed_missing_branches]))

        # Honest boundary note (not a failure): changed but no executable statements.
        if changed and measured and not relevant:
            problems.append("NOTE: changed lines contain no executable statements "
                            "(comment/blank-only edit); functional claim still applies")

        result.update(n_claims=n_claims, n_fail=n_fail, problems=problems)
        return result
    finally:
        if not keep_tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def smoke_gate_runner(spec):
    """The vloop_harness runner: run the smoke test and RETURN report text containing a
    marker. The harness greps this text for `[[vloop:...]]`; text without one is treated as
    'the check did not demonstrably run'."""
    r = run_smoke(spec)
    marker = emit_marker(GATE_NAME, r["n_claims"], r["n_fail"])
    lines = ["%s  [%s]" % (marker, r.get("name", "?")),
             "  target=%s  changed=%s  func_ok=%s  covered_changed=%s  uncovered=%s"
             % (os.path.basename(r["target_path"]), r["changed_lines"], r["func_ok"],
                r.get("covered_changed"), r.get("uncovered_changed"))]
    for p in r["problems"]:
        lines.append("  - " + p)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Registration helper (fixtures live with the caller; see tests/).
# --------------------------------------------------------------------------
_MOTIVATION = ("sci-library-curate I16-I19 port (2026-07-24): is_cryptic_name/_cn_stem were "
               "hidden deps never ported; py_compile gave a vacuous pass, caught only by a "
               "manual smoke test")

_DEFECT_CLASSES = [
    "hidden_dependency_runtime_error",   # (a) NameError from an unported helper
    "import_error_fresh_import",         # (b) ImportError surfacing only on a fresh import
    "non_exercising_coverage_gap",       # (c) code runs, but the CHANGED lines are untouched
    "other_runtime_exception",           # proves the top-level catch is not a 3-name allowlist
]


def register_smoke_gate(specs, target=None):
    """Register the post_edit_smoke gate given a dict of specs keyed by intent:
    {'nameerror','importerror','nonexercising','otherexc','clean'}."""
    return register_gate(
        name=GATE_NAME, runner=smoke_gate_runner,
        known_bad={
            "hidden_dependency_runtime_error": specs["nameerror"],
            "import_error_fresh_import": specs["importerror"],
            "non_exercising_coverage_gap": specs["nonexercising"],
            "other_runtime_exception": specs["otherexc"],
        },
        known_clean=specs["clean"],
        defect_classes=_DEFECT_CLASSES,
        motivating_evidence=_MOTIVATION, target=target)


# --------------------------------------------------------------------------
# Self-demo: inline temp fixtures so `python3 post_edit_smoke.py` proves itself
# WITHOUT the tests/ tree. Uses the explicit changed_lines fallback (no git).
# --------------------------------------------------------------------------
def _self_demo():
    from vloop_harness import run_fixture_pair, GATES
    demo = tempfile.mkdtemp(prefix="smoke_demo_")

    def w(fn, src):
        p = os.path.join(demo, fn)
        open(p, "w").write(textwrap.dedent(src).lstrip("\n"))
        return p

    # (a) hidden-dependency NameError: check_i17 calls is_cryptic_name, never defined.
    a = w("curator_nameerror.py", """
        def check_i17(rows):
            fails = []
            for r in rows:
                cn = r.get("clean_name", "")
                if is_cryptic_name(cn):     # never ported -> NameError at call time
                    fails.append(cn)
            return fails
    """)
    # (b) ImportError on fresh import.
    b = w("curator_importerror.py", """
        from _never_ported_si_miner import mine_si_dois
        def check_i18(rows):
            return [r for r in rows if mine_si_dois(r)]
    """)
    # (c) NON-EXERCISING: existing_thing runs; classify_supp (changed) is never called.
    c = w("curator_nonexercising.py", """
        def existing_thing(x):
            return x + 1
        def classify_supp(row):
            t = row.get("type", "")
            if t in ("supplement", "dataset"):
                return "companion"
            return "primary"
    """)
    # extra: a non-named-three exception (ZeroDivisionError).
    d = w("curator_otherexc.py", """
        def parse_supp(row):
            n = row["count"]
            return 100 / n
    """)
    # clean: classify_supp exercised on BOTH branches.
    cl = w("curator_clean.py", """
        def classify_supp(row):
            t = row.get("type", "")
            if t in ("supplement", "dataset"):
                return "companion"
            return "primary"
    """)
    specs = {
        "nameerror": {"name": "nameerror", "target_path": a, "changed_lines": [1, 2, 3, 4, 5, 6, 7],
                      "driver_body": 'mod.check_i17([{"clean_name": "1234_MOESM1.pdf"}])'},
        "importerror": {"name": "importerror", "target_path": b, "changed_lines": [1, 2, 3],
                        "driver_body": 'mod.check_i18([{"x": 1}])'},
        "nonexercising": {"name": "nonexercising", "target_path": c, "changed_lines": [3, 4, 5, 6, 7],
                          "driver_body": 'mod.existing_thing(1)'},
        "otherexc": {"name": "otherexc", "target_path": d, "changed_lines": [1, 2, 3],
                     "driver_body": 'mod.parse_supp({"count": 0})'},
        "clean": {"name": "clean", "target_path": cl, "changed_lines": [1, 2, 3, 4, 5],
                  "driver_body": ('assert mod.classify_supp({"type": "dataset"}) == "companion"\n'
                                  'assert mod.classify_supp({"type": "article"}) == "primary"')},
    }
    try:
        register_smoke_gate(specs)
        rep = run_fixture_pair(GATE_NAME)
        print("self-demo gate verdict:", rep["verdict"])
        for p in rep.get("problems", []):
            print("  -", p)
        # Show each fixture's own marker + verdict for transparency.
        for kind, s in specs.items():
            out = smoke_gate_runner(s)
            v, _ = classify(out)
            print("  fixture %-13s -> %s" % (kind, v))
        return rep
    finally:
        GATES.pop(GATE_NAME, None)
        shutil.rmtree(demo, ignore_errors=True)


if __name__ == "__main__":
    rep = _self_demo()
    sys.exit(0 if rep and rep["verdict"] == "PASS" else 2)
