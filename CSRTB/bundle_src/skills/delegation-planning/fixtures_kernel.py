# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""Red-team fixtures for the delegation-planning kernel (A2_ROUTING_SCHEMA v1).

Standalone: `python3 fixtures_kernel.py` (add -v for failure detail). No test
framework -- each fixture is built and run SEPARATELY, because a suite-green with
no shown red run is not evidence (a check never seen failing cannot be trusted).

Every RED fixture reproduces a REAL recorded defect shape:
  a* model_route_gate     the 16-agents-on-bare-opus state (the toolkit's own pre-fix state)
  b* plan_lint            SEED-06 delegation theater, FAILURE_CLASS_LOG arc=55710d86 msg=4022:
                          "I declared a delegation track and then wrote 'main agent
                          does this' inside it" -- 6 tracks, 4 declared delegations, self-run
  c* route_receipt_audit  declared delegate:X with dispatched=[] + an undeclared dispatch

ATTRIBUTION, not just verdict: each red fixture also asserts WHICH check fired on
WHICH track/child. `gate(known_bad) == FAIL` is necessary, not sufficient -- a
banned model id also trips the off-table check, so a verdict-only fixture stayed
green with the ban deleted (caught by mutation testing 2026-07-27).

EXIT 0 only when every fixture behaves: no RED passing, no GREEN failing, and
every attribution assertion holding.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kernel import model_route_gate, plan_lint, route_receipt_audit  # noqa: E402

VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv


# ─── (b) the SEED-06 delegation-theater block ────────────────────────────────
# Field-complete and tier-clean BY DESIGN: the ONLY defect is declared-vs-self,
# so a FAIL here is attributable to L3 and nothing else.
THEATER_TRACKS = [
    {"id": "1", "task": "Draft the phase-A handoff record.", "archetype": "handoff document",
     "owner": "main agent + handoff-brief", "executor": "delegate:MAIN-AGENT",
     "topology": "sequential-build", "model_tier": "T1", "effort": "max", "detached": True,
     "brief_ref": "artifact:brief-A", "record_access": "self-service",
     "recon_done": "ls of development/ (12 files)", "reserved_for_user": False,
     "scope_ref": "plan sectionA", "tradeoff": "clean slate for the render phase",
     "concurrency": "n/a"},
    {"id": "2", "task": "Reconstruct the rationale of the v2.6 gate set; main agent does this inline.",
     "archetype": "design rationale", "owner": "DESIGN_RATIONALE_ANALYST + design-rationale",
     "executor": "delegate:DESIGN_RATIONALE_ANALYST", "topology": "verify-loop",
     "model_tier": "T2", "effort": "high", "detached": True, "brief_ref": "artifact:brief-B",
     "record_access": "self-service", "recon_done": "read of A2_ROUTING_SCHEMA.machine.md",
     "reserved_for_user": False, "scope_ref": "plan sectionB",
     "tradeoff": "adversarial check on a shipped gate", "concurrency": "n/a"},
    {"id": "3", "task": "Tighten the child task briefs.", "archetype": "skill/agent authoring",
     "owner": "PROMPT_ENGINEER + eliciting-llm-behavior", "executor": "delegate:self",
     "topology": "single-thread", "model_tier": "T3", "effort": "medium", "detached": True,
     "brief_ref": "artifact:brief-C", "record_access": "self-service",
     "recon_done": "stated-none:coupled edit", "reserved_for_user": False,
     "scope_ref": "plan sectionC", "tradeoff": "n/a", "concurrency": "n/a"},
    {"id": "4", "task": "Verify the gate fixtures; I'll run this myself rather than spawn a child.",
     "archetype": "code review", "owner": "CODE_REVIEW_DEBUGGER + verification-loop",
     "executor": "delegate:CODE_REVIEW_DEBUGGER", "topology": "verify-loop",
     "model_tier": "T2", "effort": "high", "detached": True, "brief_ref": "artifact:brief-D",
     "record_access": "self-service", "recon_done": "ls of skills/*/kernel.py (17)",
     "reserved_for_user": False, "scope_ref": "plan sectionD",
     "tradeoff": "high-consequence gate, checkable output", "concurrency": "n/a"},
    {"id": "5", "task": "Assemble the plan prose.", "archetype": "planning",
     "owner": "main agent", "executor": "MAIN-AGENT", "topology": "single-thread",
     "model_tier": "n/a", "effort": "n/a", "detached": False, "brief_ref": "n/a",
     "record_access": "n/a", "recon_done": "stated-none:one coupled doc",
     "reserved_for_user": False, "scope_ref": "plan sectionE", "tradeoff": "n/a",
     "concurrency": "n/a"},
    {"id": "6", "task": "Recompute the doc-status header table.", "archetype": "verification",
     "owner": "skill-only", "executor": "CODE:python3 lib/doc_status.py check",
     "topology": "single-thread", "model_tier": "n/a", "effort": "n/a", "detached": False,
     "brief_ref": "n/a", "record_access": "n/a", "recon_done": "ls of payload/ (104 rows)",
     "reserved_for_user": False, "scope_ref": "plan sectionF", "tradeoff": "n/a",
     "concurrency": "n/a"},
]
# Fed as RAW FENCED TEXT (prose + ```routing fence) -- the form a plan actually emits.
THEATER_BLOCK_TEXT = ("## Delegation & Routing (as emitted by the lead)\n\n```routing\n"
                      + json.dumps({"tracks": THEATER_TRACKS}, indent=1) + "\n```\n")

NO_BLOCK_TEXT = ("## Delegation & Routing\n\nWe may delegate some of this to the "
                 "specialists as the work develops.\n")


def _corrected_tracks():
    """The same plan with the four declarations honored: real NON-SELF profiles and
    no self-run tell in the track body."""
    t = json.loads(json.dumps(THEATER_TRACKS))
    t[0]["executor"] = "delegate:RESEARCH_DATA_MANAGER"
    t[0]["owner"] = "RESEARCH_DATA_MANAGER + handoff-brief"
    t[1]["task"] = "Reconstruct the rationale of the v2.6 gate set."
    t[2]["executor"] = "delegate:PROMPT_ENGINEER"
    t[2]["record_access"] = "precis-only:brief quotes the user's private path list"
    t[3]["task"] = "Verify the gate fixtures against the recorded defect shapes."
    return t


CORRECTED_BLOCK = {"tracks": _corrected_tracks()}


def _mutate(index, **fields):
    """Corrected block with one track's fields overridden ('' deletes a key)."""
    t = _corrected_tracks()
    for k, v in fields.items():
        if v is None:
            t[index].pop(k, None)
        else:
            t[index][k] = v
    return {"tracks": t}


NO_RECON_BLOCK = _mutate(1, recon_done="")                       # L6: commit-class track
MISSING_FIELDS_BLOCK = _mutate(1, effort=None, brief_ref="")     # L2: delegate-class fields
BANNED_ID_BLOCK = _mutate(                                       # L4: literal id in the block
    1, owner="DESIGN_RATIONALE_ANALYST + design-rationale (claude-opus-5)")
RESERVED_BLOCK = _mutate(                                        # L5: user-reserved step
    4, reserved_for_user=True, task="Rewrite the installer copy_tree tier.")


# ─── (c) declared blocks for the receipt audit ───────────────────────────────
DECLARED_ONE = {"tracks": [
    {"id": "1", "task": "Adversarially review the routing kernel.", "archetype": "code review",
     "owner": "CODE_REVIEW_DEBUGGER + verification-loop",
     "executor": "delegate:CODE_REVIEW_DEBUGGER", "topology": "verify-loop",
     "model_tier": "T2", "effort": "high", "detached": True, "brief_ref": "artifact:brief-R",
     "record_access": "self-service", "recon_done": "ls of skills/delegation-planning",
     "reserved_for_user": False, "tradeoff": "high-consequence gate", "concurrency": "n/a"}]}

DECLARED_TWO = {"tracks": [
    DECLARED_ONE["tracks"][0],
    {"id": "2", "task": "Author the hook + settings fragment.", "archetype": "skill/agent authoring",
     "owner": "AGENT_TOOLING_ENGINEER + toolkit-extension-authoring",
     "executor": "delegate:AGENT_TOOLING_ENGINEER", "topology": "parallel-wave",
     "model_tier": "T1", "effort": "max", "detached": True, "brief_ref": "artifact:brief-T",
     "record_access": "self-service", "recon_done": "read of A2_ROUTING_SCHEMA.machine.md",
     "reserved_for_user": False, "tradeoff": "independent tracks",
     "concurrency": "2 units, sized via preflight-parallel"},
    {"id": "3", "task": "Assemble the plan prose.", "archetype": "planning", "owner": "main agent",
     "executor": "MAIN-AGENT", "topology": "single-thread", "model_tier": "n/a", "effort": "n/a",
     "recon_done": "stated-none:coupled", "reserved_for_user": False}]}


# ─── attribution assertions (a FAIL for the wrong reason is a wrong fixture) ──
def _expect_check(child, check_id):
    """model_route_gate: the named child must fail for the named REASON."""
    def _fn(result):
        got = [(f.get("child"), f.get("check")) for f in result["failures"]]
        if (child, check_id) not in got:
            return "expected child %s to fail %r; got %s" % (child, check_id, got)
        return ""
    return _fn


def _expect_lint(check_id, tracks=None, field=None, only=False):
    """plan_lint: check_id must fire on exactly `tracks` (and optionally `field`);
    only=True additionally asserts NO other check fired -- that is what makes the
    fixture attributable to one lint rule instead of to generic malformation."""
    def _fn(result):
        hits = [f for f in result["failures"] if f.get("check") == check_id]
        if not hits:
            return "expected a %s failure; got %s" % (
                check_id, sorted({f.get("check") for f in result["failures"]}))
        got_tracks = sorted({str(f.get("track")) for f in hits})
        if tracks is not None and got_tracks != sorted(tracks):
            return "%s should name tracks %s; named %s" % (check_id, sorted(tracks), got_tracks)
        if field is not None and not any(str(f.get("field")).endswith(field) for f in hits):
            return "%s should name field %r; named %s" % (
                check_id, field, [f.get("field") for f in hits])
        if only:
            others = sorted({f.get("check") for f in result["failures"]} - {check_id})
            if others:
                return "only %s should fire; also got %s" % (check_id, others)
        return ""
    return _fn


def _expect_named(check_id, profile):
    """route_receipt_audit: check_id must fire naming that profile."""
    def _fn(result):
        hits = [f for f in result["failures"]
                if f.get("check") == check_id and f.get("profile") == profile]
        if not hits:
            return "expected %s naming %s; got %s" % (check_id, profile, [
                (f.get("check"), f.get("profile")) for f in result["failures"]])
        return ""
    return _fn


# ─── runner ──────────────────────────────────────────────────────────────────
def run(fid, kind, label, result, expect, extra=None):
    """Print one fixture's transcript line. -> True when the fixture behaved."""
    got = result["verdict"]
    ok = (got == expect)
    why = "" if ok else "verdict %s, expected %s" % (got, expect)
    if ok and extra is not None:
        why = extra(result) or ""
        ok = not why
    print("[%-5s] %-3s %-58s expect=%-4s got=%-4s %-5s %s"
          % (kind, fid, label[:58], expect, got, "ok" if ok else "WRONG", result["marker"]))
    if VERBOSE or not ok:
        for f in result["failures"][:4]:
            who = f.get("child") or f.get("profile") or f.get("track") or "-"
            print("          - [%s] %s: %s" % (f.get("check"), who, f.get("detail")))
    if not ok:
        print("          !! %s" % why)
    return ok


VALID_MAP = {"tooling": "claude-opus-4-8", "novel": "claude-fable-5",
             "reviewer": "claude-sonnet-5", "sweep": "claude-haiku-4-5"}


def main():
    print("=== delegation-planning kernel -- red-team fixtures (A2_ROUTING_SCHEMA v1) ===")
    print("    RED = must FAIL (reproduces a recorded defect)   GREEN = must PASS\n")
    r = []

    # (a) model_route_gate -- the 16-agents-on-bare-opus state
    r.append(run("a1", "RED", "route_gate . claude-opus-5 in the route map",
                 model_route_gate({"reviewer": "claude-opus-5", "sweep": "claude-haiku-4-5"}),
                 "FAIL", _expect_check("reviewer", "banned")))
    r.append(run("a2", "RED", "route_gate . bare `opus` alias, live-resolvable",
                 model_route_gate({"planner": "opus", "sweep": "claude-haiku-4-5"},
                                  list_models=["opus", "claude-haiku-4-5"]),
                 "FAIL", _expect_check("planner", "banned")))
    r.append(run("a3", "RED", "route_gate . off-table id, no list_models injected",
                 model_route_gate({"drafter": "claude-sonnet-9"}),
                 "FAIL", _expect_check("drafter", "off-table")))
    r.append(run("a4", "RED", "route_gate . ban NOT rescuable by a live model list",
                 model_route_gate({"reviewer": "claude-opus-5"},
                                  list_models=["claude-opus-5", "claude-sonnet-5"]),
                 "FAIL", _expect_check("reviewer", "banned")))
    r.append(run("a5", "GREEN", "route_gate . the valid tiered map (T1/T1_hardest/T2/T4)",
                 model_route_gate(VALID_MAP), "PASS"))
    r.append(run("a6", "GREEN", "route_gate . off-table id confirmed by list_models",
                 model_route_gate({"drafter": "claude-sonnet-9"},
                                  list_models=lambda: ["claude-sonnet-9"]), "PASS"))

    # (b) plan_lint -- SEED-06 delegation theater (arc=55710d86 msg=4022) + L1..L6
    r.append(run("b1", "RED", "plan_lint L3 . 6 tracks, 4 declared delegations, self-run",
                 plan_lint(THEATER_BLOCK_TEXT), "FAIL",
                 _expect_lint("L3", tracks=["1", "2", "3", "4"], only=True)))
    r.append(run("b2", "GREEN", "plan_lint . the corrected block (real NON-SELF profiles)",
                 plan_lint(CORRECTED_BLOCK), "PASS"))
    r.append(run("b3", "RED", "plan_lint L6 . recon_done blank on a commit-class track",
                 plan_lint(NO_RECON_BLOCK), "FAIL",
                 _expect_lint("L6", tracks=["2"], field="recon_done", only=True)))
    r.append(run("b4", "RED", "plan_lint L2 . delegate track missing effort + brief_ref",
                 plan_lint(MISSING_FIELDS_BLOCK), "FAIL",
                 _expect_lint("L2", tracks=["2"], field="effort", only=True)))
    r.append(run("b5", "RED", "plan_lint L4 . literal claude-opus-5 inside the block",
                 plan_lint(BANNED_ID_BLOCK), "FAIL",
                 _expect_lint("L4", tracks=["2"], field="owner", only=True)))
    r.append(run("b6", "RED", "plan_lint L5 . reserved step, mutating task, solo",
                 plan_lint(RESERVED_BLOCK), "FAIL",
                 _expect_lint("L5", tracks=["5"], only=True)))
    r.append(run("b7", "GREEN", "plan_lint L5 . same block with the user in the loop",
                 plan_lint(RESERVED_BLOCK, solo=False), "PASS"))
    r.append(run("b8", "RED", "plan_lint L1 . prose plan, no routing block at all",
                 plan_lint(NO_BLOCK_TEXT), "FAIL", _expect_lint("L1", only=True)))
    r.append(run("b9", "RED", "plan_lint L1 . routing block present but zero tracks",
                 plan_lint({"tracks": []}), "FAIL", _expect_lint("L1", only=True)))
    r.append(run("b10", "RED", "plan_lint L2 . always-required field missing (archetype)",
                 plan_lint(_mutate(2, archetype=None)), "FAIL",
                 _expect_lint("L2", tracks=["3"], field="archetype", only=True)))

    # (c) route_receipt_audit -- theater + undeclared dispatch
    r.append(run("c1", "RED", "route_audit . declared delegate:X, dispatched=[]",
                 route_receipt_audit(DECLARED_ONE, []), "FAIL",
                 _expect_named("unhonored", "CODE_REVIEW_DEBUGGER")))
    r.append(run("c2", "RED", "route_audit . a dispatched child never declared",
                 route_receipt_audit(DECLARED_ONE, ["CODE_REVIEW_DEBUGGER",
                                                    {"agent_name": "PROMPT_ENGINEER"}]),
                 "FAIL", _expect_named("undeclared", "PROMPT_ENGINEER")))
    r.append(run("c3", "GREEN", "route_audit . declarations honored (mixed row forms)",
                 route_receipt_audit(DECLARED_TWO, [{"agent_name": "code_review_debugger"},
                                                    "delegate:Agent Tooling Engineer"]), "PASS"))

    n, bad = len(r), r.count(False)
    print("\n--- %d fixtures run separately: %d behaved, %d MISBEHAVED" % (n, n - bad, bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
