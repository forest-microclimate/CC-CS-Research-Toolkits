#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""rationale_ledger.py -- traceability-ledger validator for the design-rationale skill.

Forces the design-rationale rigor spine STRUCTURALLY: a principle row missing an
instance, a grade, a scope, a friction (or, if schema-scoped, a falsification
result) is a HARD failure. Re-shipped from the Claude Science design-rationale
kernel as a standalone CLI (Claude Code has no auto-loaded kernel). The validator
functions are VERBATIM; only the argparse CLI is added.

Bundled in this skill's directory. Invoke it directly -- there is no auto-load:
    python3 "$HOME/.claude/skills/design-rationale/rationale_ledger.py" validate <ledger.json>
    python3 "$HOME/.claude/skills/design-rationale/rationale_ledger.py" render   <ledger.json>
Read the ledger from stdin by passing "-" as <ledger.json>.

  validate : check every row against the Tier-1 gates. Prints PASS/FAIL + each
             failing row and its violated disciplines. Exit 0 = all rows clean,
             exit 1 = one or more violations (usable as a build gate:
             `... validate led.json && <ship>`).
  render   : print the ledger as the markdown audit table (the grounded content
             to hand to teaching-narrative, or ship as an appendix).

<ledger.json> is a JSON list of principle rows, or an object carrying that list
under "ledger" / "principles" / "rows". Each row is an object with the fields the
rigor spine maps 1:1 to (see add_principle below):
    {"principle","instances","grade","scope","friction","friction_grade","falsification"}

Pure python3 stdlib; portable macOS (3.9 floor) + Linux.
"""
import argparse, json, sys

# design-rationale — traceability-ledger validator
# Forces the rigor spine STRUCTURALLY. A principle with no instance, no grade,
# no scope, no friction (or, if schema-scoped, no falsification result) is a HARD
# validation failure. This kills the OMISSION half of confabulation — skipping a
# discipline becomes a build error. It does NOT and CANNOT check CONTENT: a
# fabricated-but-present instance or friction passes. Green check proves FORM;
# the falsification/grading REVIEW proves TRUTH. Never let the check stand in for
# the review. See SKILL.md ## The ledger.

VALID_GRADES = ("stated", "inferred")
VALID_SCOPES = ("instance", "schema")

def new_ledger():
    """Return an empty principle ledger (a list of principle rows)."""
    return []

def add_principle(ledger, principle, instances=None, grade=None, scope=None,
                  friction=None, friction_grade=None, falsification=None):
    """Append one principle row. Fields map 1:1 to the rigor spine:
      principle      - the governing principle, stated as a claim (str)
      instances      - list of >=1 NAMED corpus instance grounding it  [traceability]
      grade          - 'stated' | 'inferred'  (grade of the PRINCIPLE) [evidence-grading]
      scope          - 'instance' | 'schema'                           [scope-of-validity]
      friction       - the problem/friction it resolves; OR a string starting
                       'value-driven:' declaring it genuinely frictionless + why
                                                                        [friction-grounding]
      friction_grade - 'stated' | 'inferred'  (grade of the FRICTION itself)
      falsification  - result of applying a SCHEMA claim to a NAMED out-of-corpus
                       case (required when scope=='schema')             [falsification]
    No validation here - fill freely, then call validate_ledger(ledger)."""
    if instances is None:
        instances = []
    row = {"principle": principle, "instances": list(instances), "grade": grade,
           "scope": scope, "friction": friction, "friction_grade": friction_grade,
           "falsification": falsification}
    ledger.append(row)
    return row

def validate_row(row):
    """Return a list of gate-violation strings for one row (empty list = clean)."""
    v = []
    if not (row.get("principle") or "").strip():
        v.append("no principle text")
    if len(row.get("instances") or []) < 1:
        v.append("traceability: no named instance")
    if row.get("grade") not in VALID_GRADES:
        v.append("grading: grade not in {stated, inferred}")
    if row.get("scope") not in VALID_SCOPES:
        v.append("scope-of-validity: scope not in {instance, schema}")
    fr = row.get("friction")
    if fr is None or not str(fr).strip():
        v.append("friction-grounding: no friction named and no 'value-driven:' note "
                 "(set friction='value-driven: <reason>' if genuinely frictionless)")
    elif not str(fr).startswith("value-driven:") and row.get("friction_grade") not in VALID_GRADES:
        v.append("friction-grounding: friction present but friction_grade not in {stated, inferred}")
    if row.get("scope") == "schema" and not (row.get("falsification") or "").strip():
        v.append("falsification: schema-scoped claim has no out-of-corpus test result")
    return v

def validate_ledger(ledger):
    """Check every row against the cheap gates. Returns
    {ok, n, clean, violations:[{index, principle, issues}]}. ok is True only when
    EVERY row is clean - a build gate you can assert on."""
    violations = []
    for i, row in enumerate(ledger):
        issues = validate_row(row)
        if issues:
            violations.append({"index": i,
                               "principle": (row.get("principle") or "")[:80],
                               "issues": issues})
    return {"ok": len(violations) == 0, "n": len(ledger),
            "clean": len(ledger) - len(violations), "violations": violations}

def ledger_to_markdown(ledger):
    """Render the ledger as a markdown table - the grounded CONTENT to hand to
    teaching-narrative for rendering, or to ship as an audit appendix."""
    if not ledger:
        return "_(empty ledger)_"
    out = ["| # | Principle | Grounded in (instances) | Grade | Scope | Friction | Falsification |",
           "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(ledger):
        inst = "; ".join(r.get("instances") or []) or "**MISSING**"
        fr = r.get("friction") or "**MISSING**"
        fg = r.get("friction_grade")
        if fr not in ("**MISSING**",) and fg and not str(fr).startswith("value-driven:"):
            fr = "{0} ({1})".format(fr, fg)
        if r.get("scope") == "schema":
            fal = r.get("falsification") or "**MISSING**"
        else:
            fal = r.get("falsification") or "n/a (instance-scoped)"
        out.append("| {0} | {1} | {2} | {3} | {4} | {5} | {6} |".format(
            i, r.get("principle", ""), inst, r.get("grade", "?"),
            r.get("scope", "?"), fr, fal))
    return "\n".join(out)


# ==========================================================================
# CLI -- wires the verbatim validator functions to subcommands (Claude Code
# has no persistent kernel; this replaces the Science-side auto-load).
# ==========================================================================
def _load_ledger(path):
    """Load a ledger from a JSON file (or stdin when path == '-'). Accepts a
    bare list of principle rows, or an object carrying the list under
    'ledger' / 'principles' / 'rows'. Returns the list."""
    try:
        data = json.load(sys.stdin) if path == "-" else json.load(open(path))
    except FileNotFoundError:
        sys.exit("FATAL: ledger file not found: " + path)
    except json.JSONDecodeError as e:
        sys.exit("FATAL: %s is not valid JSON (%s)" % (path, e))
    if isinstance(data, dict):
        for k in ("ledger", "principles", "rows"):
            if isinstance(data.get(k), list):
                return data[k]
        sys.exit("FATAL: JSON object has no 'ledger' / 'principles' / 'rows' list")
    if not isinstance(data, list):
        sys.exit("FATAL: ledger JSON must be a list of principle rows (or an object carrying one)")
    return data


def cmd_validate(args):
    """Validate the ledger; print PASS/FAIL + failing rows. Return an exit code."""
    report = validate_ledger(_load_ledger(args.ledger))
    if report["ok"]:
        print("PASS: %d/%d principle row(s) clean -- every Tier-1 discipline present on every row."
              % (report["clean"], report["n"]))
        print("  NOTE: FORM only. This proves no discipline was SKIPPED; it does NOT prove the "
              "instances/frictions are correct. The falsification pass + human review prove TRUTH.")
        return 0
    print("FAIL: %d/%d row(s) clean; %d row(s) violate the rigor spine:"
          % (report["clean"], report["n"], len(report["violations"])))
    for v in report["violations"]:
        print("  row %d -- %s" % (v["index"], v["principle"] or "(no principle text)"))
        for issue in v["issues"]:
            print("      * " + issue)
    return 1


def cmd_render(args):
    """Print the ledger as the markdown audit table. Return an exit code."""
    print(ledger_to_markdown(_load_ledger(args.ledger)))
    return 0


def main():
    ap = argparse.ArgumentParser(
        prog="rationale_ledger.py",
        description="Traceability-ledger validator for the design-rationale skill.")
    ap.add_argument("cmd", choices=["validate", "render"],
                    help="validate: gate-check every row; render: markdown audit table")
    ap.add_argument("ledger",
                    help="path to the ledger JSON (list of principle rows), or '-' for stdin")
    args = ap.parse_args()
    sys.exit({"validate": cmd_validate, "render": cmd_render}[args.cmd](args))


if __name__ == "__main__":
    main()
