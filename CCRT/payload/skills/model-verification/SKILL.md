---
name: model-verification
description: Invoke WHEN a claim about WHICH MODEL ACTUALLY RAN has to be verified rather than assumed — at collect for every subagent launch whose model matters, before attributing any behavior (quality, error rate, timidity, speed, cost) to a named model, when a UI header or a child's self-report or a config disagrees with what you expected, or when a model ban or routing rule must be SHOWN to have held. Runs model_run_audit.py over the harness transcripts to catalog every run's raw arg vs resolved model vs SERVED model, with MATCH/MISMATCH/UNKNOWN verdicts and a gate-able exit code; also ships fable_watchdog.py, the LIVE early-certification instrument that reads a still-running child's first ~5 serving stamps (verified-launch). The serving stamp is the only authoritative layer; headers, configs, resolutions, and the model's own testimony record intent or belief. Fires on "which model actually ran", "verify the model", "did the ban hold", "is this child really on X", "check the model at collect", "prove the routing worked", "certify a fable child live", "watch a launch". NOT which model to ROUTE a task to (-> delegation-planning) and NOT child error-rate telemetry (-> the error-mode log readout).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# STATUS: CURRENT (2026-08-04). Authored from the four-layer forensic anatomy measured in the 2026-08-04 model-resolution incident (MRI-20260804), where a child's self-report, its UI header, and its transcript's API metadata disagreed and only one of the three was downstream of what actually ran. Method source: METHODS_model_verification.md (authoring workspace, dev/reports/) — this skill is its operational half; the reliability gradings below are that incident's measurements, not assumptions. EXTENDED 2026-08-06 (Z1, kit v1.7): fable_watchdog.py joins the skill — LIVE certification of a running fable-tier child (verified-launch), measured against the deterministic call-4 swap.

# model-verification — verify which model RAN, not which model was asked for

## When to invoke
- AT COLLECT, for every subagent launch whose model matters — a tier assignment, a cost claim, a ban, a supervision contract.
- BEFORE attributing any behavior to a named model: quality, error rate, over-caution, speed, cost.
- WHEN a UI header, a child's self-report, a frontmatter pin, or an environment default disagrees with what you expected.
- WHEN a routing rule or model ban must be SHOWN to have held rather than assumed to have held.
- BEFORE writing a durable row (ledger, report, memory, incident record) that NAMES the model which produced something.

## The rule
A model claim is verified by the SERVING STAMP or it is not verified. The serving stamp is the `"model"` field the API writes onto every assistant turn in a transcript, once per call, by the serving side — the only record downstream of what actually ran. Every other signal is a statement of intent or belief: useful for diagnosing WHY a substitution happened, never evidence of WHAT ran.

## Run it
```bash
# Resolve the script: the installed toolkit copy, else the authoring repo's master.
AUDIT="$HOME/.claude/skills/model-verification/model_run_audit.py"
[ -f "$AUDIT" ] || AUDIT="dev/tools/model_run_audit.py"

ls -t "$HOME/.claude/projects/"                    # find the project slug (dir name = the encoded project path)

python3 "$AUDIT" "$HOME/.claude/projects/<slug>/"                  # every session in the project
python3 "$AUDIT" "$HOME/.claude/projects/<slug>/<sessionId>.jsonl" # ONE session + its children  <- the usual collect check
python3 "$AUDIT" "$HOME/.claude/projects/<slug>/<sessionId>/"      # a session dir (subagents/ + its sibling main transcript)

python3 "$AUDIT" <path> --summary-only             # just the pasteable SUMMARY block
python3 "$AUDIT" <path> --json                     # machine output (per-run records + summary)
python3 "$AUDIT" <path> --tsv                      # rows + a comment-prefixed summary
```
EXIT CODES (gate-able): `0` no MISMATCH · `1` at least one MISMATCH · `2` input/parse error. UNKNOWN does NOT gate — a main-loop run carries no intent layer by construction, so every main row is UNKNOWN and a project-wide audit would otherwise never exit 0.

NO SCRIPT AVAILABLE ⇒ the same authoritative layer by hand, one file at a time — but read the caveat, because the quick form silently mixes two layers:
```bash
# QUICK LOOK (fine on a leaf child transcript; MISLEADING on a transcript that LAUNCHES children):
grep -oh '"model":"[^"]*"' <transcript.jsonl> | sort | uniq -c
# ACCURATE (assistant rows only = the serving stamp, "<synthetic>" harness rows dropped):
python3 -c 'import json,sys,collections
c=collections.Counter()
for l in open(sys.argv[1],errors="replace"):
    if "\"model\"" not in l: continue
    try: r=json.loads(l)
    except ValueError: continue
    m=r.get("message")
    if r.get("type")=="assistant" and isinstance(m,dict) and m.get("model","")not in("","<synthetic>"): c[m["model"]]+=1
print(*("%7d %s"%(n,k) for k,n in c.most_common()),sep="\n")' <transcript.jsonl>
```
WHY THE QUICK FORM MISLEADS (measured on a 141-run session): a transcript that launches children also carries each launch's `"model"` ARGUMENT inside its tool-use blocks, so the naive grep returns bare aliases (`"model":"sonnet"`, `"model":"haiku"`, `"model":"fable"`, `"model":"opus"`) and config echoes MIXED INTO what reads as a serving tally — the exact intent-for-serving conflation this skill exists to prevent. On one main transcript it added 23 phantom rows to a true tally of 2283. A bare alias in that output is never a serving stamp: the API stamps full ids.

## Live certification (verified-launch) — certify a fable-tier child DURING the run
DIVISION OF LABOR: `fable_watchdog.py` (same dir) = DURING-run EARLY certification of ONE child by its first serving stamps; `model_run_audit.py` = the post-hoc audit of every run. Both read the same authoritative layer (the serving stamp); the watchdog reaches a verdict by ~call 5 instead of after the whole run.
```bash
python3 .claude/skills/model-verification/fable_watchdog.py <child-transcript> [--expect claude-fable-5] [--verdict-at 5] [--watch]
```
EXIT CODES (one verdict line on stdout): `0` FAITHFUL — the first `--verdict-at` stamps all equal `--expect` · `1` SWAPPED@k — the first divergent stamp is call k, decided the moment a divergence is seen · `2` UNDETERMINED — too few stamps yet / no assistant records / unparseable (never a crash). One-shot by default; `--watch` polls a still-growing transcript, so it can be pointed at a RUNNING child.
THE VERIFIED-LAUNCH PATTERN (measured 2026-08-06): the measured swap is DETERMINISTIC at call 4, so a warmup of >=4 reads opening the child's task makes serving certifiable by ~call 5. POINTER-READS-AS-WARMUP: the brief's persona/`SKILL.md` Read-pointers ARE the warmup — useful work crossing the call-4 boundary, zero throwaway calls. On SWAPPED ⇒ relaunch, or proceed KNOWINGLY and log the substitution; on UNDETERMINED ⇒ re-poll or fall back to the post-hoc audit. REGIME CAVEAT: substitution rates drift within hours and are never a property of a configuration alone — certification-at-launch, not configuration, carries the guarantee; at collect re-verify with `model_run_audit.py` regardless.

## Read the verdicts (the four record layers, in descending authority)
| layer | where it lives | what it actually records | standing |
|---|---|---|---|
| SERVED stamp | assistant rows' `message.model`, in each run's own transcript | the API response's own model field, written per call by the serving side | AUTHORITATIVE — the only serving-side record |
| RESOLVED | `toolUseResult.resolvedModel` on the launch row — which may sit in ANY transcript, including a sub-planner child's, not only the main one | the harness's launch-time resolution after precedence; the only field carrying a `[1m]` display suffix, and evidently the UI header's source | INTENT — measured diverging from the served stamp in ~94% of one model's resolutions during the origin incident |
| RAW ARG | `agent-<id>.meta.json` `.model`, absent when the launch omitted it | the literal launch argument | INPUT ONLY — correct configuration proves nothing about serving |
| SELF-REPORT | the run's own answer to "what model are you?" | a guess assembled from its loaded context | DISQUALIFIED — measured wrong 3 of 5 times; it echoes whatever its docs name as the default |

- MATCH — every served call in that run carries the resolved id (display suffixes normalized before comparing).
- MISMATCH — the request chain resolved one id and the API served another. This is the finding; do not explain it away.
- UNKNOWN — a layer is missing (no launch row found, or the run made no API calls). Not a pass and not a failure; say which layer was absent.

## Disqualified witnesses (never accept these as a receipt)
- The child's SELF-REPORT — it reports what its context says the default is, not what served it.
- The UI HEADER and `resolvedModel` — both read the RESOLUTION. They tell you what was requested after precedence, which is exactly the thing a substitution happens downstream of.
- A correct `model:` pin, launch param, or environment default — all upstream of serving.
- The ONE external witness worth adding when it matters: the account's usage/billing page, which is serving-side and aggregated by model, though it cannot be attributed to a single run in-app. If a model shows tokens nobody intended, something served it.

## Escalation
A MISMATCH is report-worthy. File it via `/feedback` with the receipts the audit already prints: the resolved id, the served tally, the run ids, and the mismatch signature (`resolved -> served`, runs and calls). Then: record the SERVED model — never the resolved one — in any ledger, report, or memory row; re-check cost, because mismatched calls bill as the model that served them; and treat every affected downstream claim about that run's model as unsupported until re-verified.

REF: METHODS_model_verification.md (the session-agnostic method + where transcripts live + the per-child sweep one-liner) · the model-resolution incident record it was measured from (four-layer anatomy, the evidence table, the disqualification of self-report) · `delegation-planning` (choosing which model a task should get — the decision this skill audits after the fact) · `testing-discipline` (the red-before-green epistemics the audit script's own fixture battery is built to).
