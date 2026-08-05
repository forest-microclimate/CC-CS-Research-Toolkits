#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""check_sidecar_contract.py -- recurrence gate for the sidecar-publish invariant.

WHY THIS EXISTS (BUG-0001, the class this closes)
Three skill sidecars (delegation-planning, provenance-guard, verification-loop) shipped
kernel.py files the Science sidecar-publish gate REJECTS: computed top-level constants
(frozenset(...), re.compile(...)), "_"-prefixed top-level names, and a bottom
`if __name__ == "__main__"` guard. The content installed, but the kernel helpers never
registered -- so loading any of the three yielded the SKILL.md guidance with its advertised
functions UNDEFINED. The live gate reports only the FIRST violation, so a fix cycle is blind
to the rest. This checker reports the FULL set, off-line, before any build.

THE GATE INVARIANT (encoded here verbatim, from BUG_INCIDENT_LOG.machine.md)
A skill sidecar kernel.py may contain, AT MODULE TOP LEVEL, ONLY:
  (1) function definitions whose names do NOT start with "_"
  (2) import / from-import statements
  (3) assignments of a LITERAL constant (str/num/bool/None, or list/tuple/set/dict OF
      literals, or unary +/- on a numeric literal) to a PLAIN name -- not "_"-prefixed,
      not a Python builtin.
  plus a leading module docstring.
FORBIDDEN at top level: any computed value (frozenset(...), re.compile(...), a generator,
  any Call), "_"-prefixed names (assignments AND def names -- the loader reserves them),
  and any top-level if / for / with / try / class / bare expression (so a bottom
  `if __name__ == "__main__": ...` guard is rejected). main() itself may be DEFINED.

COUNTING (matches the recorded AST-scan inventory 17/11/2/9)
Per Assign: one violation for EACH bad target name (reserved "_" or builtin) PLUS one
violation if the value is not an allowed literal. So a line like `_X = re.compile(...)`
is TWO violations (reserved name + computed value); `_X = ("a","b")` is ONE (name only);
`X = re.compile(...)` is ONE (value only). Every def/if/... is one violation.

ALSO CHECKS (BUG-0002): each skill's SKILL.md frontmatter `description:` folded length
must be <= 1024 (the registry publish limit). Folding mirrors the house tolerant reader
(strip the >-/|  block-scalar marker, join continuation lines with single spaces).

USAGE
  python3 check_sidecar_contract.py                 # scan the CS bundle (kernels + descriptions)
  python3 check_sidecar_contract.py --file K.py     # scan one file as a kernel
  python3 check_sidecar_contract.py --fixtures DIR  # scan every *.py in DIR as a kernel
  python3 check_sidecar_contract.py --self-test     # red-before-green: reproduce 17/11/2/9

EXIT: 0 = all clean | 1 = a violation or an over-limit description (fail-closed).
argparse usage errors exit 2 (its default); an unreadable target exits 1.
Python 3.9-compatible, stdlib only.
"""
import argparse
import ast
import builtins
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(HERE, "bundle_src", "skills")
FIXTURE_DIR = os.path.join(HERE, "parity_fixtures", "sidecar_prefix_20260728")
DESC_LIMIT = 1024
BUILTIN_NAMES = frozenset(dir(builtins))

# The recorded pre-fix violation inventory the self-test must reproduce EXACTLY.
# A checker that cannot re-derive the recorded defect counts fails its own test.
EXPECTED_FIXTURE_COUNTS = {
    "delegation-planning": 17,
    "directing-execution": 11,
    "provenance-guard": 2,
    "verification-loop": 9,
}


# ─── the AST rule ───────────────────────────────────────────────────────────────
def is_literal(node):
    """True iff `node` is an ALLOWED literal constant: a str/num/bool/None/bytes
    constant, a list/tuple/set/dict whose members are all literals (recursively), or a
    unary +/- on a numeric literal. Everything else -- any Call (frozenset(), re.compile()),
    generator, comprehension, name reference, f-string, BinOp -- is a computed value."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(is_literal(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        # a ** spread gives a None key -> not a literal mapping
        return all(k is not None and is_literal(k) and is_literal(v)
                   for k, v in zip(node.keys, node.values))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return isinstance(node.operand, ast.Constant) and \
            isinstance(node.operand.value, (int, float, complex))
    return False


def _flatten_targets(target):
    """Yield leaf target nodes from a possibly-nested assignment target
    (tuple/list unpacking, starred). Non-Name leaves are yielded as-is so the caller
    can flag a non-plain-name target (obj.attr / d[k])."""
    if isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _flatten_targets(elt)
    elif isinstance(target, ast.Starred):
        yield from _flatten_targets(target.value)
    else:
        yield target


def _target_violations(targets, lineno):
    """One violation per bad target NAME: a "_"-prefixed name (loader-reserved) or a
    Python builtin (shadowing). A non-Name target (attribute/subscript) is not a plain
    name and is itself a violation."""
    out = []
    for target in targets:
        for leaf in _flatten_targets(target):
            if isinstance(leaf, ast.Name):
                name = leaf.id
                if name.startswith("_"):
                    out.append((lineno, "assignment to reserved '_'-prefixed name %r "
                                        "(the sidecar loader reserves '_' names)" % name))
                elif name in BUILTIN_NAMES:
                    out.append((lineno, "assignment to builtin name %r (shadows a "
                                        "Python builtin)" % name))
            else:
                out.append((lineno, "assignment to a non-plain-name target (%s); only a "
                                    "plain name may be assigned" % type(leaf).__name__))
    return out


def _assign_violations(node, targets, value):
    """Target-name violations plus, if the value is not an allowed literal, exactly ONE
    computed-value violation (naming the first plain target for readability)."""
    out = _target_violations(targets, node.lineno)
    if not is_literal(value):
        names = [leaf.id for t in targets for leaf in _flatten_targets(t)
                 if isinstance(leaf, ast.Name)]
        who = (" to %r" % names[0]) if names else ""
        out.append((node.lineno, "computed value assigned%s (top-level value is a %s, not "
                                 "a literal constant) -- move it behind a lazy accessor "
                                 "function" % (who, type(value).__name__)))
    return out


def _kind_label(node):
    labels = {
        ast.If: "top-level `if` statement (e.g. an `if __name__ == \"__main__\"` guard)",
        ast.For: "top-level `for` loop",
        ast.AsyncFor: "top-level `async for` loop",
        ast.While: "top-level `while` loop",
        ast.With: "top-level `with` block",
        ast.AsyncWith: "top-level `async with` block",
        ast.Try: "top-level `try` block",
        ast.ClassDef: "top-level class definition (sidecars may only define functions)",
        ast.AugAssign: "augmented assignment (reads an existing value -- not a literal "
                       "constant assignment)",
        ast.Delete: "top-level `del` statement",
        ast.Assert: "top-level `assert` statement",
        ast.Raise: "top-level `raise` statement",
        ast.Global: "top-level `global` statement",
        ast.Nonlocal: "top-level `nonlocal` statement",
    }
    return labels.get(type(node), "%s at module top level" % type(node).__name__)


def scan_source(src, label="<source>"):
    """Return a sorted list of (lineno, reason) violations of the sidecar contract.
    An unparseable source is itself a single violation (the loader could not exec it)."""
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [(getattr(exc, "lineno", 0) or 0,
                 "kernel does not parse (%s) -- it could never load" % exc)]

    violations = []
    for idx, node in enumerate(tree.body):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                violations.append((node.lineno,
                                   "function def with reserved '_'-prefixed name %r "
                                   "(the sidecar loader reserves '_' names)" % node.name))
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    violations.append((dec.lineno,
                                       "decorator with a call on def %r (a computed value at module "
                                       "top level; the sidecar gate may reject it)" % node.name))
            continue
        if isinstance(node, ast.Expr):
            # a leading string literal is the module docstring; any other bare
            # expression (incl. a non-first string) is a forbidden top-level statement
            if idx == 0 and isinstance(node.value, ast.Constant) and \
                    isinstance(node.value.value, str):
                continue
            violations.append((node.lineno, "bare expression at module top level "
                                            "(only defs, imports, and literal assigns allowed)"))
            continue
        if isinstance(node, ast.Assign):
            violations.extend(_assign_violations(node, node.targets, node.value))
            continue
        if isinstance(node, ast.AnnAssign):
            if node.value is None:
                violations.append((node.lineno, "bare annotation at module top level "
                                                "(not a literal constant assignment)"))
            else:
                violations.extend(_assign_violations(node, [node.target], node.value))
            continue
        violations.append((node.lineno, _kind_label(node)))

    violations.sort(key=lambda v: v[0])
    return violations


# ─── the description-length rule ─────────────────────────────────────────────────
def _tolerant_frontmatter(body):
    """House tolerant reader (mirrors check_bundle_parity._tolerant_frontmatter): a
    top-level `key: value` map, folding >-/| block scalars and wrapped continuation lines
    with single spaces. This is the pinned operand for the folded description length."""
    data, cur, buf = {}, None, []
    for line in body.splitlines():
        if not line.strip():
            continue
        if line[0] not in " \t" and ":" in line:
            if cur is not None:
                data[cur] = " ".join(buf).strip()
            key, val = line.split(":", 1)
            cur, val = key.strip(), val.strip()
            buf = [] if val in (">-", ">", "|", "|-", "") else [val]
        elif cur is not None:
            buf.append(line.strip())
    if cur is not None:
        data[cur] = " ".join(buf).strip()
    return data


def description_length(skill_md_text):
    """Return (folded_len_or_None, error_or_None) for the frontmatter `description:`."""
    if not skill_md_text.startswith("---"):
        return None, "no frontmatter block (does not start with ---)"
    end = skill_md_text.find("\n---", 3)
    if end == -1:
        return None, "unterminated frontmatter block"
    data = _tolerant_frontmatter(skill_md_text[3:end])
    desc = data.get("description")
    if desc is None:
        return None, "no `description:` key in frontmatter"
    return len(desc), None


# ─── runs ───────────────────────────────────────────────────────────────────────
def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def scan_kernels(kernel_paths):
    """-> (per_file list of (relpath, violations), total_violations)."""
    per_file, total = [], 0
    for path in kernel_paths:
        try:
            src = _read(path)
        except OSError as exc:
            viols = [(0, "unreadable: %s" % exc)]
        else:
            viols = scan_source(src, path)
        rel = os.path.relpath(path, HERE)
        per_file.append((rel, viols))
        total += len(viols)
    return per_file, total


def scan_descriptions(skill_md_paths):
    """-> (over list of (relpath, length, over_by), errors list of (relpath, err))."""
    over, errors = [], []
    for path in skill_md_paths:
        try:
            text = _read(path)
        except OSError as exc:
            errors.append((os.path.relpath(path, HERE), "unreadable: %s" % exc))
            continue
        length, err = description_length(text)
        rel = os.path.relpath(path, HERE)
        if err:
            errors.append((rel, err))
        elif length > DESC_LIMIT:
            over.append((rel, length, length - DESC_LIMIT))
    return over, errors


def _print_kernel_fails(per_file):
    for rel, viols in per_file:
        if viols:
            print("  kernel %s: %d violation(s)" % (rel, len(viols)))
            for lineno, reason in viols:
                print("    - L%d: %s" % (lineno, reason))


def run_default():
    if not os.path.isdir(SKILLS_DIR):
        print("no skills dir at %s" % SKILLS_DIR)
        return 1
    skills = sorted(d for d in os.listdir(SKILLS_DIR)
                    if os.path.isdir(os.path.join(SKILLS_DIR, d)) and not d.startswith("."))
    kernel_paths = [os.path.join(SKILLS_DIR, s, "kernel.py") for s in skills
                    if os.path.isfile(os.path.join(SKILLS_DIR, s, "kernel.py"))]
    skill_md_paths = [os.path.join(SKILLS_DIR, s, "SKILL.md") for s in skills
                      if os.path.isfile(os.path.join(SKILLS_DIR, s, "SKILL.md"))]

    per_file, kviol = scan_kernels(kernel_paths)
    over, derr = scan_descriptions(skill_md_paths)

    print("[[sidecar_contract kernels=%d kernel_viol=%d descs=%d desc_over=%d]]"
          % (len(kernel_paths), kviol, len(skill_md_paths), len(over)))

    fail = bool(kviol or over)
    if kviol:
        print("\nKERNEL contract violations (%d across %d file(s)):"
              % (kviol, sum(1 for _, v in per_file if v)))
        _print_kernel_fails(per_file)
    if over:
        print("\nDESCRIPTION over the %d-char registry limit (%d):" % (DESC_LIMIT, len(over)))
        for rel, length, ob in over:
            print("  - %s: description folds to %d chars (over by %d)" % (rel, length, ob))
    if derr:
        # frontmatter that cannot be read for a description is advisory, not a gate fail:
        # report it so it is visible, but it does not by itself flip the exit code.
        print("\nDESCRIPTION unreadable (advisory, %d):" % len(derr))
        for rel, err in derr:
            print("  - %s: %s" % (rel, err))

    if fail:
        print("\nSIDECAR CONTRACT GATE: FAIL (%d kernel violation(s), %d over-limit "
              "description(s))" % (kviol, len(over)))
        return 1
    print("\nSIDECAR CONTRACT GATE: PASS -- %d kernel(s) clean, %d description(s) <= %d chars."
          % (len(kernel_paths), len(skill_md_paths), DESC_LIMIT))
    return 0


def run_file(path):
    if not os.path.isfile(path):
        print("no such file: %s" % path)
        return 1
    viols = scan_source(_read(path), path)
    print("[[sidecar_contract file=%s kernel_viol=%d]]"
          % (os.path.basename(path), len(viols)))
    if viols:
        _print_kernel_fails([(os.path.relpath(path, HERE), viols)])
        print("\nSIDECAR CONTRACT GATE: FAIL (%d violation(s))" % len(viols))
        return 1
    print("\nSIDECAR CONTRACT GATE: PASS (%s is contract-clean)" % os.path.basename(path))
    return 0


def run_fixtures(fixture_dir):
    if not os.path.isdir(fixture_dir):
        print("no such dir: %s" % fixture_dir)
        return 1
    py = sorted(f for f in os.listdir(fixture_dir) if f.endswith(".py"))
    if not py:
        print("no *.py fixtures in %s" % fixture_dir)
        return 1
    paths = [os.path.join(fixture_dir, f) for f in py]
    per_file, total = scan_kernels(paths)
    print("[[sidecar_contract fixtures=%d kernel_viol=%d]]" % (len(paths), total))
    for rel, viols in per_file:
        print("  %s: %d violation(s)" % (os.path.basename(rel), len(viols)))
    if total:
        _print_kernel_fails(per_file)
        print("\nSIDECAR CONTRACT GATE: FAIL (%d violation(s) across %d fixture(s))"
              % (total, len(paths)))
        return 1
    print("\nSIDECAR CONTRACT GATE: PASS (all fixtures clean)")
    return 0


# ─── self-test (red-before-green) ────────────────────────────────────────────────
CLEAN_SAMPLE = '''"""A contract-clean sidecar kernel (self-test green fixture)."""
import os
import re
from collections import OrderedDict

MARKERS = ("brm(", "gam(", "stan(")
LIMIT = 1024
NEG = -5
FLAGS = {"strict": True, "modes": ["a", "b"], "n": None}
NESTED = [("x", 1), ("y", 2)]


def helper(value):
    return re.compile(value)


def marker_of(name, n):
    return "[[%s n=%d]]" % (name, n)
'''

RED_SAMPLE = '''"""A deliberately-dirty kernel (self-test red fixture)."""
import re

TABLE = re.compile("x")          # computed value -> 1
_CACHE = {"a": 1}                # reserved name  -> 1


def _hidden():                   # reserved def   -> 1
    return 1


if __name__ == "__main__":       # top-level if   -> 1
    _hidden()
'''


def run_self_test():
    ok = True

    # (1) reproduce the recorded pre-fix inventory EXACTLY
    print("SELF-TEST -- reproducing the recorded pre-fix violation inventory")
    if not os.path.isdir(FIXTURE_DIR):
        print("  FAIL: fixture dir missing: %s" % FIXTURE_DIR)
        return 1
    for skill, expected in sorted(EXPECTED_FIXTURE_COUNTS.items()):
        path = os.path.join(FIXTURE_DIR, "%s__kernel_prefix.py" % skill)
        if not os.path.isfile(path):
            print("  FAIL: missing fixture %s" % os.path.basename(path))
            ok = False
            continue
        got = len(scan_source(_read(path), path))
        verdict = "ok" if got == expected else "MISMATCH"
        if got != expected:
            ok = False
        print("  %-22s expected=%-3d got=%-3d [%s]" % (skill, expected, got, verdict))

    # (2) a clean sample must pass
    n_clean = len(scan_source(CLEAN_SAMPLE, "<clean-sample>"))
    print("  %-22s expected=%-3d got=%-3d [%s]"
          % ("clean-sample", 0, n_clean, "ok" if n_clean == 0 else "MISMATCH"))
    if n_clean != 0:
        ok = False

    # (2b) description folding: one over-limit RED + one folded GREEN (red-before-green
    #      for the length check itself -- previously untested; verify-loop gap 1, 2026-07-28)
    red_desc = "---\nname: x\ndescription: >-\n  " + "a" * 600 + "\n  " + "b" * 600 + "\n---\nbody\n"
    green_desc = "---\nname: x\ndescription: >-\n  alpha line one\n  beta line two\n  gamma line three\n---\nbody\n"
    rl, rerr = description_length(red_desc)
    gl, gerr = description_length(green_desc)
    red_ok = (rerr is None and rl is not None and rl > 1024)
    green_expected = len("alpha line one beta line two gamma line three")
    green_ok = (gerr is None and gl == green_expected)
    print("  %-22s expected>%-3d got=%s [%s]" % ("desc-red-sample", 1024, rl, "ok" if red_ok else "MISMATCH"))
    print("  %-22s expected=%-3d got=%s [%s]" % ("desc-green-fold", green_expected, gl, "ok" if green_ok else "MISMATCH"))
    if not (red_ok and green_ok):
        ok = False

    # (3) verify-the-verifier: the red sample must trip exactly its 4 planted defects
    n_red = len(scan_source(RED_SAMPLE, "<red-sample>"))
    print("  %-22s expected>=%-2d got=%-3d [%s]"
          % ("red-sample", 4, n_red, "ok" if n_red == 4 else "MISMATCH"))
    if n_red != 4:
        ok = False

    if ok:
        print("\nSELF-TEST: PASS -- inventory reproduced (delegation-planning=17, "
              "directing-execution=11, provenance-guard=2, verification-loop=9); "
              "clean sample clean; red sample caught.")
        return 0
    print("\nSELF-TEST: FAIL -- the checker cannot reproduce the recorded defect counts; "
          "it does not encode the invariant it claims to.")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="check_sidecar_contract.py",
        description=__doc__.split("\n")[0])
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--file", help="scan one file as a sidecar kernel")
    group.add_argument("--fixtures", metavar="DIR",
                       help="scan every *.py in DIR as a kernel (red-fixture self-scan)")
    group.add_argument("--self-test", action="store_true",
                       help="reproduce the recorded 17/11/2/9 inventory then a clean sample")
    a = ap.parse_args(argv)

    if a.self_test:
        return run_self_test()
    if a.file:
        return run_file(a.file)
    if a.fixtures:
        return run_fixtures(a.fixtures)
    return run_default()


if __name__ == "__main__":
    sys.exit(main())
