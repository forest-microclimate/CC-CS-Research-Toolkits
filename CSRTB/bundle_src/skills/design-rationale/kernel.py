# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
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
