<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# FORMAT: machine-methods
# DOC_ID: <project>/<method-topic>-method
# DOC_CURRENCY: CURRENT            | one of DRAFT | CURRENT | SUPERSEDED | RETRACTED
# AUTHORITY_CLASS: A1_CURRENT_OWNER   | CONCEPTUAL owner — the intended science, explicitly NOT the implementation
# VERIFICATION_STATUS: <VERIFIED | PARTIALLY_VERIFIED | UNVERIFIED>
# TASK_STATUS: <DRAFT | ACTIVE | DONE | FROZEN>
# AS_OF: <ISO-8601 + tz>
# TOPIC_ID: <the-ONE-method-topic-this-doc-owns>
# DDC_CATEGORY: DDC-04 (STATE)
# SUPERSEDES: <doc_id or ->   ; SUPERSEDED_BY: <doc_id or ->
#
# PURPOSE (DDC-04): the intended biology / physics / math / statistics — equations, model spec, priors,
#   estimators, assumptions, invariants — as the PROJECT MEANS them, independent of what the code happens
#   to compute. At the moment an agent reasons about what the model SHOULD compute, this doc (the
#   intended-science object) is forced to the front, kept SEPARATE from the live-code object — so "the
#   code does X" is never mistaken for "the science intends X".
# AUTHORITY: A1 CONCEPTUAL owner, one current owner per method-topic. Distinct from IMPLEMENTATION (code).
#   When intent and code differ, RECORD the gap (see IMPL_CORRESPONDENCE) — never silently merge them.
# SCOPE: DDC-04 owns the SETTLED CURRENT method (its content). The adjudication of WHY-this-over-that
#   (e.g. chose Medlyn over Ball-Berry, informative over weak priors) is a DECISION — it belongs in the
#   DDC-11 decisions ledger, not here.
# STATE CONTRACT (STATE = supersede-with-retract): exactly ONE current spec per method. On change,
#   supersede in place and leave a dated retract stub (see below). No accumulation.
#
# CHECKER (check_current_documents.py enforces):
#   - in-band STATUS header present                                          (fail on missing field)
#   - each method states its intended INVARIANTS / CONSERVATION / IDENTIFIABILITY conditions in a form a
#         semantic test can check                                            (fail on method block with no test-checkable INVARIANTS field)
#   - each conceptual claim cites whether implementation evidence exists — no design-as-implemented
#         without A0 evidence                                                (fail on IMPL_CORRESPONDENCE=IMPLEMENTED_AS_DESIGNED with no A0_EVIDENCE pointer)
#   - one current owner per method-topic                                     (fail on duplicate method-topic owner)
#
# ─────────────────────────────────────────────────────────────────────────────
# COPY + EDIT BELOW. One METHOD block per method / model component / estimator this topic owns.
#   RULE 1 — describe the INTENDED science, not the code.
#   RULE 2 — state invariants so a semantic test can bind to them (fill CHECKABLE_AS).
#   RULE 3 — mark the intent↔code relation with IMPL_CORRESPONDENCE. IMPLEMENTED_AS_DESIGNED REQUIRES an
#            A0_EVIDENCE pointer (a run / code object that shows it); the other three record a gap.
#   RULE 4 — put method CHOICES (why this over that) in DDC-11, not here.
# ─────────────────────────────────────────────────────────────────────────────

## METHOD: <name of the method / model component / estimator>
- INTENDED: <the science as the project means it — equation / model spec / estimator; write the equation>
    <equation or formal spec block>
- INVARIANTS / CONSERVATION / IDENTIFIABILITY: <stated so a semantic test can check — e.g. "energy budget closes to |resid| < ε", "mass conserved per timestep", "posterior identifiable given ≥ N obs">
    - CHECKABLE_AS: <the semantic test that binds to this invariant — test id / assertion / "-" if none yet>
- PRIORS / ASSUMPTIONS: <priors, distributional assumptions, boundary conditions the intent requires>
- IMPL_CORRESPONDENCE: <IMPLEMENTED_AS_DESIGNED | DESIGNED_NOT_IMPLEMENTED | IMPLEMENTED_NOT_DOCUMENTED | UNRESOLVED>
    - A0_EVIDENCE: <code/run pointer proving implementation — REQUIRED if IMPLEMENTED_AS_DESIGNED; "-" otherwise>
- AS_OF: <ISO-8601 + tz>

## METHOD: <next method / model component / estimator this topic owns>
- INTENDED: <intended science / equation>
- INVARIANTS / CONSERVATION / IDENTIFIABILITY: <...>
    - CHECKABLE_AS: <test id / assertion / ->
- PRIORS / ASSUMPTIONS: <...>
- IMPL_CORRESPONDENCE: <one of the four values>
    - A0_EVIDENCE: <pointer or ->
- AS_OF: <ISO-8601 + tz>

# ── RETRACT STUB (supersede a method spec IN PLACE) ──
## METHOD: <old method>   [SUPERSEDED <ISO-8601> → <new spec / doc_id>]
- RETRACTED <ISO-8601>: <old spec no longer intended; why>. Current spec: <pointer>.
