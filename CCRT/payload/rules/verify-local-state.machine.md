# verify-local-state.machine.md  (machine-optimized; style policy: doc-style.machine.md)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# RULE: a locally + CHEAPLY verifiable fact (file · data · process-status · count · timestamp) => state it / act on it from the FRESH source reading — never an assumption, a stale earlier reading, or an inference from an indirect proxy. Verify before asserting; RE-verify (≥2 agreeing sources) before an irreversible act. CRITICAL recurring instance (minimize): on RESUME, confirm a process's running-status from a BROAD ps/pgrep + its OWN growing output files before ever concluding "not running".
# ORIGIN: user, 2026-07-04 — after a Claude Code resume, a healthy ~6 h Stan fit's progress was discarded: a STALE log + a single `pgrep`=0 + a file-SIZE guess were each trusted as fact instead of cross-checked against the process table + the run's actual CSV outputs. Cross-project => lives at the global rules level.

RULE.verify_from_source: WHEN about to STATE or ACT on a specific CURRENT local fact — a file's existence / contents / size / row-count, a data value, a process's running-status, a run's iteration, a timestamp — that a shell command confirms in seconds ⇒ run that command and speak from the FRESH output. Cheaper-to-check ⇒ LESS excuse to assume.
  - EX: "does `M_stan_*.rds` exist?" ⇒ `ls` it, don't recall. · "how many draws?" ⇒ COUNT the rows, don't eyeball the MB.

RULE.direct_not_proxy: WHEN about to CONCLUDE a fact from an INDIRECT proxy ⇒ read the DIRECT / authoritative source instead — a proxy is stale-able and mis-scaled; the source is the truth.
  - file SIZE ⇏ record-count → COUNT the records. · a LOG's last line ⇏ the process's true progress → the log can FREEZE while the process runs on, so read the process's OWN OUTPUT files. · ONE tool's empty output ⇏ "nothing there" → see RULE.confirm_running_before_negative.
  - EX (the 2026-07-04 miss): a 400 MB CSV called "~thousands of draws" was ~470 (each draw ~800 KB); a log frozen at iter 3500 taken as "the run's state" while its chains had already run past it.

RULE.reverify_before_irreversible: WHEN about to do something IRREVERSIBLE (kill · pkill · rm · delete · overwrite · restart) premised on a local-state fact ⇒ re-verify that fact from ≥2 INDEPENDENT authoritative sources in the same breath, and proceed ONLY if they AGREE; on disagreement STOP and resolve first. A long-running result is PRECIOUS — an unrecoverable action earns exhaustive checking, not a glance.
  - EX: before `pkill -f model_` (the 2026-07-04 act) ⇒ FIRST confirm `ps aux | grep model_` + the output CSVs' mtime AGREE the run is truly gone — not a live run a narrow check missed.

RULE.confirm_running_before_negative (CRITICAL — the recurring instance to minimize): WHEN on RESUME / reconnect / post-restart you are about to conclude "process X is NOT running" | "nothing is running" | "the run died" ⇒ assert it ONLY after ≥2 authoritative sources AGREE it is absent:
  1. BROAD process table — `ps aux | grep -i <name>` + a BROAD `pgrep` (NOT one narrow pattern; a mismatched pattern / different name / parent / cwd is the usual reason a LIVE process reads as "missing").
  2. the process's OWN OUTPUT ARTIFACTS — is its `.csv` / `.log` / output still GROWING (recent mtime)? a live process leaves FRESH writes even when your name-match fails.
  one empty NARROW check ⇏ "nothing running"; require ≥2 agreeing readings before any destructive re-run — never off a single empty reading.
  - EX: `pgrep -f './model_x'`=0 ⇒ ALSO `ps aux | grep model` AND `ls -la <tmpdir>/*.csv` (check mtime) BEFORE saying "not running".

WHY: these facts are the CHEAPEST to verify and among the COSTLIEST to get wrong — a false "not running / dead" invites a destructive re-run that discards good work; a false count / progress mis-reports the state to the user. Root failure = trusting ONE indirect or stale signal as ground truth; fix = read the DIRECT source, and require AGREEMENT across INDEPENDENT sources before any irreversible act.

CAVEAT (LLM limits): no reliable introspection ⇒ this REDUCES (not eliminates) the failure, and only when LOADED + a trigger fires — hence the triggers are phrased as detectable moments (about-to-state-a-local-fact · about-to-infer-from-a-proxy · about-to-do-something-irreversible · about-to-say-"not-running"), not "be more careful".

REF: verification-principles.md (verify-don't-assume · say-unchecked · cite-or-hedge — THIS is its local-state / process-status specialization) · reproduce-before-fixing.machine.md (falsifier-first: reproduce at baseline before building) · doc-style.machine.md (style).
