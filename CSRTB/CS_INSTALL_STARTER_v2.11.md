# CS_INSTALL_STARTER_v2.11.md — paste-ready starter for installing bundle v2.11 into Claude Science
# STATUS: CURRENT (2026-08-03). RE-SITED into the bundle dir (from the mirror root) + counts recounted to 52 skills / 18 profiles. User-run step: the CC session cannot reach the CS runtime; you run this in a Science session.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# PRECONDITION: upload (or sync) these two files — they sit beside this starter in the bundle dir — into the Claude Science project workspace first:
#   crt_science_bundle.json   (v2.11 content: 52 skills / 18 profiles, recounted from the shipped bundle 2026-08-03; the 2026-07-30 J-series rebuild added supervisory-workflow + count-enumeration-contagion)
#   install_crt_science.py
# (Optionally also check_currency.py for the post-install currency manifest.)
# RELATIONSHIP: CS_README is the orientation front door and POINTS here; THIS file is the paste-ready USER-RUN install + its acceptance probes. Day-one usage → CS_QUICKSTART.

── PASTE THE BLOCK BELOW INTO A NEW CLAUDE SCIENCE CONVERSATION ──

Install the Research Toolkit bundle v2.11 (planner upgrade + SOFTWARE_DEVELOPER + verification-integrity gates) and smoke-test the new Planner gates. Run these as separate repl cells, reporting each cell's output before the next:

1) INSTALL (overwrite — differing profiles are silently SKIPPED without it):
   exec(open("install_crt_science.py").read()); install_crt_science(overwrite=True)
   Confirm the installer reports 52 skills / 18 profiles, PLANNER + SOFTWARE_DEVELOPER updated/created, no InstallVerificationError.

2) CURRENCY MANIFEST (so future logins can be checked against these bytes):
   run check_currency.py --write-manifest per its usage (skip if the file wasn't uploaded; say so).

3) SMOKE — kernel gates (host-independent, so this must pass identically to the dev-side fixtures):
   exec(host.skills.read("delegation-planning", "kernel.py")["content"])
   print(model_route_gate({"child_a": "claude-opus-5"})["marker"])          # expect verdict=FAIL (the ban)
   print(model_route_gate({"child_a": resolve_tier("T1"), "child_b": resolve_tier("T4")})["marker"])  # expect PASS
   exec(host.skills.read("directing-execution", "kernel.py")["content"])
   print(confirm_before_stop("probe-child")["marker"])                      # expect FAIL (no receipts)
   exec(host.skills.read("provenance-guard", "kernel.py")["content"])
   print(verify_before_assert([{"claim": "n_files", "value": 3, "source_read_ref": "memory"}])["marker"])  # expect FAIL (SEED-01 gate)
   exec(host.skills.read("verification-loop", "kernel.py")["content"])
   print(require_receipt("byte-identical, shipping", [])["marker"])        # expect FAIL (DISC-07 gate)

4) SMOKE — live per-child model routing (the first host.delegate(model=…) use in this bundle):
   r = host.delegate([{"task": "Reply with exactly: T4-probe-ok", "name": "t4_probe", "model": "claude-haiku-4-5"}])
   Confirm the child ran on the requested model (inspect the result's model field / frames record), then report.
   NEVER dispatch any probe to claude-opus-5 — the ban applies to probes too.

5) SIDECAR ACCEPTANCE (the path-independent test for the 2026-07-28 BUG-0001/0002 fix — REQUIRED this install):
   for each of the FOUR sidecar skills — delegation-planning, directing-execution, provenance-guard,
   verification-loop — re-probe the publish gate:
     host.skills.edit(<skill>, "kernel.py", host.skills.read(<skill>, "kernel.py")["content"])
   and confirm the returned sidecar_gate verdict has ok=True; then confirm the installer report shows
   publish=published for all four (no "Assign at module top level" / "description exceeds" lines).
   If ANY probe returns ok=False, STOP and report the exact gate message verbatim — never retry-edit past the gate.

6) Report: install verdict, gate marker outputs, the delegate-probe model confirmation, and the four
   sidecar_gate verdicts. Tag everything attempted-untested in efficacy terms — this smoke proves the
   MECHANISMS load and fire, not that failure rates drop (that measurement = future FAILURE_CLASS_LOG
   appends vs the 2026-07-27/28 baseline).

── END PASTE BLOCK ──
