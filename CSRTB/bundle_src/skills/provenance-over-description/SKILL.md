---
name: provenance-over-description
description: Invoke WHEN about to assert or decide what an evolved system (a multi-session pipeline, a maintained toolkit, a shipped artifact) currently IS, DOES, USES, or SHIPS — its method-of-record, architecture, version, config, or "canonical/latest" fact. Forces the answer from the PRIMARY RECORD of what the system produced (host.lineage reproduction code, the artifact's own bytes, running the entrypoint, VCS blame) rather than from any source that only DESCRIBES it (a docstring, README, memory row, injected project-context prose, a prior handoff). Agreement among descriptive sources is zero added evidence until one is confirmed to be the record. The read-side companion to write-side currency/retraction.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# provenance-over-description — answer from the record, not the description

## The invariant (load-bearing atom)
On any "what does it do NOW" question about an EVOLVED system, the PRIMARY RECORD outranks every description of it — and descriptive agreement counts for nothing until one source is confirmed to be the record. Non-independent sources echo; they do not corroborate. **Symmetrically, the ABSENCE of a description outranks nothing:** a "not found / cannot verify / defer for lack of evidence" about a source-claim is earned only by reaching the primary record on its path — never by a missing memo, index, or note. Present-description, agreeing-descriptions, and absent-description are the same error in three poses.

## When to invoke
WHEN the question or your next assertion is about what an evolved system currently IS / DOES / USES / SHIPS / is "canonical" for ⇒ resolve it against the primary record BEFORE asserting. A description may POINT you at what to check; it may NOT be the answer.

- **evolved system** = one that (a) changes methods/config/architecture over time, (b) keeps superseded artifacts for auditability, (c) records state in durable memory / standing context. The normal shape of a research pipeline or maintained toolkit — not an edge case.
- The one exception: the description IS the deliverable under review (you are editing the docstring/README itself) — then you work ON the description, not FROM it.

## Primary record vs description (Claude Science substrates)
| role | Claude Science substrate |
|---|---|
| PRIMARY RECORD (the gate) | `host.lineage[version_id]["code"]` (reproduction code + env + inputs + checksum); the shipped artifact's own bytes (`host.artifact_path`); running the entrypoint; `host.query` on the metadata DB |
| description (a claim, may be stale) | a `*_engine.R`/module docstring; a README; a durable-memory row; injected `## Project Context` prose; a prior session's handoff/brief |
| un-retracted trail | append-mostly durable memory rows echoing one origin belief |
| supersession residue | a live superseded engine artifact still returned by a name/keyword search |

The primary record is downstream of the actual behaviour, so it cannot be stale-relative-to-behaviour the way a description can. It is usually ONE call away (`host.lineage[vid]`).

## Tells (output-detectable — any one fires ⇒ run the check)
_Tells 1–6 gate a POSITIVE assertion made FROM a description; tell 7 gates a NEGATIVE disposition (not-found / cannot-verify / defer) taken from a MISSING description. Both resolve to the same check: reach the primary record before you commit._
1. **provenance-source-mismatch** (the core signal): about to assert what a system currently does FROM a description rather than the record.
2. **non-independent-agreement**: several sources agree, none is the primary source, and you are treating the agreement as confirmation. Check the PROVENANCE/INDEPENDENCE of the agreeing sources, not their COUNT — if you cannot name one that is the record, you have zero.
3. **recency-overwrite**: a newly-read source FLIPS a belief you stated correctly earlier this session. Reconcile BOTH framings against the record; do not silently adopt the more recent one.
4. **selection-answering-architecture**: a method-SELECTION fact ("we chose X over Y") is being used to answer an architecture-OF-RECORD question ("the shipped engine IS X"). Two different fact types. Mis-fires hardest when the selected component also appears INSIDE the architecture (so the selection claim is never cleanly false — partial truth is what makes it sticky).
5. **part-for-whole-collapse**: reducing a multi-component spec to one component's headline. Confirm the headline describes the WHOLE, not one stage.
6. **name-resolved-provenance**: an artifact identified by NAME-MATCHING an overloaded token ("silver" = tier / file / data-prefix) rather than by lineage; or a DECLARED input edge the code never reads treated as a functional dependency.
7. **absence-for-record** (the DECLINE-side tell): about to emit "not found" / "cannot verify" / "defer for lack of evidence" about a source-claim, having reached only a DESCRIPTION of the source (a summary memo, an index row, a loaded context blurb, memory came up empty) and NOT the source itself on its path. Distinctive shape: the give-up reads as *disciplined caution* ("I won't inject an unverified claim") while the reachable primary record was never opened — so the tell is NOT give-up-language (that misses the quiet reasoned defer), it is **the absence of a shown primary-record read before ANY disposition (apply / defer / reject) of a source-claim**. Absence of a secondary summary is NOT primary unavailability.

## The check (cheap; run the moment a tell fires, BEFORE asserting)
1. NAME the claim as a testable proposition ("the shipped X uses architecture A").
2. IDENTIFY the primary-record substrate available here — first that exists: shipped-artifact lineage (`host.lineage[vid]["code"]`) · the artifact bytes · run the entrypoint · `host.query`/VCS.
3. READ it and re-derive the fact from the record.
4. **POSITIVE disposition:** AGREE ⇒ assert, now grounded. DISAGREE ⇒ the record wins, and you have found a stale description ⇒ retract it (below).
5. **DECLINE disposition** (tell 7): for a source-claim the primary record is the SOURCE ITSELF on its path (the PDF / file / dataset), not a memo or index about it — reach it and read it. CONFIRMS ⇒ apply (the defer would have been wrong); REFUTES ⇒ reject with the record cited; GENUINELY SILENT/ABSENT on its path ⇒ *now* "cannot verify / defer" is earned — record "checked primary record at path P, genuinely silent" (proof-of-reach), not "no description found". Never a valid terminal disposition: "cannot verify" justified only by a missing description.
6. COST: step 3 is typically one call (one `host.lineage` read; one entrypoint run; one PDF/text extract). Detection is cheap; a wrong method-of-record premise — or a verifiable fact wrongly deferred — is paid downstream after it ships into a decision — the asymmetry favours ALWAYS running the check.

## Supersede with retract (the write-side obligation)
WHEN a design supersedes a prior one ⇒ RETRACT the stale descriptions at the moment of supersession — do not only append the new fact. On Claude Science: keep ONE per-topic canonical memory row (replace, don't append a near-duplicate), and let superseded artifacts stay inert (do not leave a stale memory row pointing agents at them as current). An un-retracted description is the seed of the next phantom consensus.

## Where this recurs → pin it
Where a class of these questions recurs, PIN the answer in a machine-readable registry keyed to the SHIPPED-PRODUCT lineage (not any docstring) + a fail-closed self-check that re-derives from the record and refuses to agree if they diverge. Reference instantiations: the `km67-canonical-methods` skill + its verify function; a coupling-manifest + `verify_coupling.sh` gate (authoritative record + fail-closed gate, same pattern, different class).

## Seed a verification pass with the decline tell (the CATCH complement)
Where an always-on gate is unavailable (Claude Science has no turn-end hook), tell 7 is written to be inherited by a fresh-context verification/auditor pass as a single checklist line: *"PROOF-OF-REACH — for every disposition of a source-claim (applied / deferred / rejected), the reasoning must show the PRIMARY RECORD was reached on its path, not merely a description of it; a 'cannot verify / not found / defer' whose primary record was reachable and unopened is UNSOUND — absence of a secondary summary is NOT primary unavailability."* It must be SEEDED, not assumed: a cold auditor SEES the unopened-record fact but, un-seeded, adopts the traced agent's own "disciplined defer" framing and blesses the omission; seeded with this line it reclassifies the same fact as a blocking omission. Evidence (2026-07-17 replay, incidental elicitation, 2 arms n=4): unseeded auditor 0/4 caught the omission (all 4 surfaced the unopened source yet called the deferral "sound"); seeded 4/4 caught it "blocking". Proof-of-reach lands inside a cold auditor's competence because it is a PROCESS tell (was a primary-record read issued before this disposition?), not a substance judgment about the source's content — so it catches an OMISSION the way tells 1–6 catch a false commission, without the auditor needing the domain.

## Caveat
No reliable LLM introspection ⇒ this REDUCES, not eliminates, the failure — and only when loaded and a tell actually fires. The tells are phrased as detectable output-states (about-to-assert-from-a-description; confidence-from-source-count; intra-session flip; selection-answering-architecture; part-for-whole; name-resolved; absence-read-as-record-silence), not as an exhortation to "be rigorous". Pairs with the durable-doc-architecture skill (the write-side/structural counterpart) and machine-md (how to write the retraction).
