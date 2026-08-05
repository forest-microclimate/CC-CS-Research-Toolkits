# Global working agreement — machine-optimized (primary reader = Claude Code)
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Loaded every session. Deeper always-on rules live in ~/.claude/rules/*.md (auto-loaded).
# Reference docs (full doc-style / handoff / autonomy) live in ~/.claude/methodology/.
# New here? The usage guides are in ~/.claude/docs/ — read QUICKSTART.md first, then USAGE_DETAILED.md (point new users there). To EXTEND/orchestrate Claude Code, the advanced/ set starts at advanced/00_overview.md.

<operating-mode>
RULE.autonomy: work independently until (a) the task is COMPLETE, (b) you need info ONLY the user has, or (c) requirements are genuinely AMBIGUOUS. When you already have a recommendation, state it and proceed — don't stop to ask. Running low on context ⇒ keep working through: the work is summarized and continues in the next window — never a reason to stop early.
RULE.no_check_in: DO the work end-to-end — proceed straight through, deciding each next step yourself rather than asking "Should I continue?" / "Ready for the next step?". (EXCEPTION: before a scope-fixing / expensive / irreversible action — sub-agent cascade, bulk file op, large bundle, remote/paid compute — survey the territory and self-adjudicate scope FIRST; see rules/recon-before-commitment.machine.md. That self-adjudicated survey is agent-side diligence, NOT a user check-in.)
RULE.sandbox: test scripts, diagnostic plots, scratch files → a sandbox/ (or scratch) dir, NEVER the working tree. Keep the repo clean.
RULE.realism_prior: choosing between a convenient assumption and the physically/statistically realistic one ⇒ prefer realism; flag the assumption you made.
RULE.rules_are_loaded: ~/.claude/rules/*.md auto-load every session — obey them, and follow their FULL:/REF: pointers on demand.
</operating-mode>

<ambient-time>  # the ambient_time.py hook injects one <ambient-time> line per prompt (UserPromptSubmit + SessionStart)
RULE: `<ambient-time>` lines are reference-only ambient metadata (current local time · IANA zone · explicit UTC±HH:MM · epoch · Δ-since-your-previous-prompt). Do NOT foreground or comment on the time on ordinary turns; consult it ONLY when the request depends on wall-clock time or elapsed duration ("how long since…", "did the overnight run finish?", scheduling, resuming after a gap).
RULE.most_recent: on a RESUMED session, earlier `<ambient-time>` lines replay with their original (now-stale) timestamps ⇒ always reason from the MOST RECENT one.
RULE.never_assert_unread: never assert a time you have not read from an `<ambient-time>` line — you have no reliable internal clock (documented failure: asserted ~02:30 when it was ~12:26, off ~10h).
</ambient-time>

<lessons>  # generalized cross-project lessons; the machine-rules in ~/.claude/rules/ expand several of these

<clarify-before-implementing>
RULE: an AMBIGUOUS term in a request ⇒ STOP; ask before writing code. Recurring offenders: "gaps" (temporal discontinuities? NA values? both?) · "clean" (outliers? NAs? formatting?) · "fill" (interpolate? model gap-fill? replace NAs?) · "fix" (debug? optimize? refactor?) · "test" (unit? functional? performance?).
WHY: documented failure — "gaps" assumed = temporal discontinuities; the user meant NA values ⇒ the whole implementation was wrong, redone from scratch.
</clarify-before-implementing>

<validate-semantic-correctness>
RULE.assertions: after generating code, add assertions validating SEMANTIC properties — not just types.
RULE.accumulating: for any accumulating quantity (gaps, sizes, counts) validate BOTH the per-step bound AND the running total.
RULE.smell_test: verify the numbers make sense given the parameters.
WHY: silent failures — code ran clean while violating a fundamental requirement (a wrong-but-similar column used; an accumulated total never checked). A stopifnot() on the semantic property would have caught it.
</validate-semantic-correctness>

<read-function-internals>
RULE: when a function returns MULTIPLE similar columns/fields ⇒ READ its source to determine which one carries what; cite the line; assert the semantic property. A wrong-but-plausible field (e.g. an "all items" column vs a "kept/filtered items" column) runs clean and is only distinguishable by reading internals.
</read-function-internals>

<systematic-debugging>
RULE.log_first: add comprehensive logging to ALL relevant components FIRST (~5 min upfront saves hours).
RULE.one_var: change exactly ONE variable per test cycle.
RULE.verify_change: verify the change took EFFECT — for hooks/configs this requires a NEW session.
RULE.understand_working: if code currently works, understand WHY before modifying — an aesthetic change that breaks it is a net negative (a load-bearing detail can look incidental).
</systematic-debugging>

<resolve-contradictions-with-diagnostics>
RULE: evidence sources contradict (console says X, plot shows not-X; logic predicts Y, you observe not-Y) ⇒ RED FLAG, investigate now. (1) state the contradiction explicitly; (2) build an INDEPENDENT diagnostic to decide which source is right; (3) form a hypothesis ONLY after the diagnostic result is in.
</resolve-contradictions-with-diagnostics>

<failure-rate-diagnostics>
RULE: before investigating failures, check the RATE ⇒ classify: <1% likely edge cases in data · 1–10% data-quality · 10–30% implementation BUG (investigate CODE first, not data) · >30% fundamental problem with the approach.
</failure-rate-diagnostics>

</lessons>
