# Supervised Multi-Agent Work System: Operating Logic
# STATUS: CURRENT (2026-08-04). Runtime/model/tool-agnostic operating logic (§0); adds the subordinate-coordinator element (§3, §10) and completes the named-outcome collect contract (§3, six exits). 2026-08-04: §5's version-pinning clause made placement-agnostic (pinned somewhere is the invariant; pinned at the launch is a runtime property to measure); and §5 gained the supervised-lane element for re-admitting an EXCLUDED tier, with its §10 scope limit — the element is stated agnostically (no model ids, no agent or hook names, and our own three watch classes are NOT enumerated as universal: the rule requires that you name yours in advance). 2026-08-04 (second edit): §5's pinning bullet gained the request-versus-serving clause after a measured case in which correctly pinned, correctly resolved requests were answered by a different tier, which falsified "pinning makes the tier reproducible" as stated. Model params and aliases stay OUT per §0's omits-implementation law.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

## 0. What this document is

STATES: the operating logic of a supervised multi-agent work system. For each element: what it is, and the failure it exists to prevent.
OMITS: implementation. Every mechanism is yours to choose.
ASSUMES of your runtime: you can start isolated worker instances, run programs, and write persistent records that outlive the worker that wrote them. Where a rule depends on a further runtime property, the rule names that property and tells you to measure it.
VOCABULARY, one name per concept, used throughout: **requester** (sets the goal and the boundary), **coordinator**, **worker**, **code**, **store**, **cycle**, **brief**, **tier**, **ledger**, **receipt**.
Section 10 separates the load-bearing invariants from the free parameters. Read it before treating any rule below as optional.

## 1. The problem the architecture solves

One agent instance has one bounded working context. A job whose source material, intermediate products, and measurements together exceed that bound cannot be held in one instance.

Attempting it produces two failures with a single cause, which is that no capacity remains for keeping state or checking claims:
1. The instance loses the thread. It re-reads material it has already read and begins to contradict its own earlier statements.
2. The instance asserts without checking. It reports that a fix works, because making the claim is far cheaper than measuring it.

Decomposition into a supervised loop buys four properties:
- **Isolation.** Each worker holds only its own assignment. Its context stays small, and a mistake it makes stays inside its own product instead of contaminating the rest of the job.
- **Parallelism.** Independent pieces run at the same time, so elapsed time tracks the longest piece rather than the sum of all pieces.
- **Verifiability.** A worker's product is a named record that a second party can read and check. A conclusion that exists only inside one context is unavailable for checking.
- **Token economy.** Cost scales with capability and with the volume of context carried. Splitting the job lets each piece run at the cheapest capability that fits it, and keeps the coordinator's context reserved for deciding rather than for raw material.

Decomposition also has a cost, and the rest of these rules exist to pay it: every boundary between participants is a place where information can be lost. Briefs that carry primary sources, named destinations for every product, and bounded reports are what make the boundaries lossless enough to be worth having.

## 2. Three participants and one store

Three participants perform work. They rank equally: each does part of the job that the others do worse.

**Coordinator.** Decomposes the goal, writes briefs, chooses arrangement and tier, launches, collects, verifies, synthesizes, and decides the next cycle. It performs no domain work. Two reasons. Its context is the only one that persists across cycles, so filling it with raw source material destroys the capacity the whole loop depends on. And a coordinator that also produces work becomes the reviewer of its own product, which section 6 rules out.
Carve-out, deliberately narrow: the coordinator reads primary material in exactly two cases. (a) The material is a worker's output or report, which it must read to synthesize. (b) A load-bearing claim is about to decide something consequential, or two reports disagree. Case (b) is accuracy outranking economy at the moment where a wrong premise is most expensive. Keeping the exception to two named cases is what stops it from becoming the default.

**Workers.** Fresh instances, each launched with one written brief and no view of the coordinator's conversation or of each other. They do the substantive reading, writing, building, and measuring. Each returns one bounded report and ends. Isolation is kept rather than repaired: a worker that cannot see the wider conversation also cannot inherit its errors, and spends its entire context on its own assignment.

**Code.** Deterministic programs. Apply the **determinism test** to every piece of work: if it can be expressed as a fixed sequence of operations over code that exists or can be written, run it as code. An instance asked to imitate a program returns a slower, costlier, non-reproducible approximation of it. The consequence is that code ranks as a product of the system alongside the other two participants, planned for and stored on the same terms as their output. Where code runs is a separate question from whether it should be code: inside a worker by default, directly under the coordinator only for a one-command check.

**The store.** Everything exchanged between participants persists as a named record: briefs, outputs, reports, ledgers, measurements, and the code itself. Isolated workers have no other channel, so an unwritten result dies with the worker that held it. The store is simultaneously the communication channel and the project's history.

Boundary rule in one line: judgment is delegated, determinism is run, synthesis and decision stay with the coordinator, and anything that crosses a boundary is written down.

## 3. The cycle

One cycle is the unit of work: **decompose, brief, launch, collect, verify, synthesize, decide**. Everything the loop does happens inside some cycle.

The decision is the point of the cycle. It asks one question, explicitly rather than by implication: given what just came back, does the plan still fit the evidence? A plan executed to its end without re-fitting is a plan that ignores everything it learned on the way.

Six exits, exactly one per cycle, and the one taken is named in the record alongside the receipts it rests on. The naming is the operative act: an unnamed outcome defaults silently to continue, which is how a plan outlives the evidence that justified it.
- **Continue** to the next pieces, when the plan fits and work remains.
- **Re-route**, when the evidence touches only part of the remaining work. Re-brief those pieces and no others.
- **Fix first**, when a returned result exposes a defect that blocks the next pieces. Repair it before anything else proceeds.
- **Adapt**, when the evidence shows the decomposition itself is wrong. Return to decompose.
- **Abort**, when the work is blocked or unrecoverable. Stop and report the blockage to the requester.
- **Close**, when the goal is met. Update the ledgers and take a backup.

**Arrangement** is chosen per cycle by how the pieces depend on each other, not by habit: one worker alone; a chain where each piece consumes the last; a fan-out of independent pieces; a fan-out giving several workers the same material and a different question each; or a build-then-review pair with a separate reviewer. The last two fan-outs are identical at launch and differ at collect: independent pieces need only collection, while several answers to different questions about one body of material need a merge, and that merge is coordinator work that must be budgeted before launching.

**A chunk can earn its own coordinator.** Weigh this at every decompose. When a chunk passes three tests at once — it is internally multi-step and delegable, so it would need a plan of its own; it is separable behind a narrow interface of named inputs and outputs; and it is heavy enough that supervising its internals would consume the coordinator's attention at collect — route it whole to one worker running the coordinator role at the highest-capability tier, and let that subordinate run the full cycle inside the chunk. A chunk that needs its own plan either gets one from a party that owns it, or it fragments across the coordinator's collect.

A subordinate coordinator is sealed, and each clause of the seal closes its own failure:
- **Narrowed access.** Its read paths are the named inputs; its write path is the subtree it owns. Without the narrowing it reaches material its interface never promised, and the separability that justified routing the chunk whole stops being true.
- **A private record area for its own workers' briefs and returns.** The shared records have exactly one writer, the coordinator. Two writers appending to one running record lose or interleave each other's rows.
- **Non-overlapping scopes where several run at once**, assigned by the coordinator. A shared store has no lock, so overlapping writers are resolved by whichever lands last.
- **A compressed roll-up rather than a transcript.** Within its report cap the subordinate returns the outcomes it named and the receipts it checked, not its workers' reports; the coordinator spot-checks those receipts and writes the shared row itself. A transcript moves the subordinate's whole collect problem onto the coordinator, which is the cost the routing existed to avoid.

Depth is one measured level rather than open recursion. The property this rests on — a worker able to launch a worker and receive its reply — was measured to one level, so a subordinate coordinator's own children are workers and not a third tier. Measure your own runtime before nesting deeper.

**Correction semantics depend on your runtime, so measure yours rather than assume it.** Measure two properties: (i) whether a message can reach a worker while it runs, and at what granularity it arrives; (ii) whether a running worker's assignment can be replaced. Then apply the invariant: a correction that fits inside the existing assignment travels on whatever mid-run channel exists, and a change of assignment is a new brief and therefore a new launch. A worker acts from its brief, so changing the goal without changing the brief leaves it working from a stale specification. Where a runtime offers no mid-run channel at all, every correction waits for collect, which costs at most one cycle. That cost is the reason to size cycles so that losing one is affordable.

## 4. Brief anatomy

A brief is a complete, self-contained assignment. Each element and the failure it prevents:

- **The assignment and the standard of done.** The worker has no other source of intent.
- **Read paths that point at the primary sources.** A coordinator's summary is a proxy. A worker acting on the proxy inherits the coordinator's errors and has no way to detect them, while a worker reading the source can catch what the summary lost. This single rule is what makes worker isolation an error filter instead of an error amplifier.
- **A named destination for every work product.** An unwritten product evaporates when the worker ends. Treat any product whose destination the brief does not name as a product that will not exist.
- **A report cap.** Reports land in the coordinator's context, the scarcest resource in the system. An uncapped report moves the worker's context problem onto the coordinator.
- **A stop-when-stuck rule, verbatim in every brief:** if errors recur, the approach stops converging, or you are about to change approach, stop and report what you found; do not thrash. It bounds the cost of a wrong assignment, and it converts a blocked worker into evidence. A worker that halts and reports that its task premise conflicts with what it found is more useful than one that forces a result.
- **The scope rule, verbatim** (section 9).
- **Persistence.** Write the brief to the store before launching. A brief held only in the coordinator's conversation dies with that conversation; a persisted brief lets a crashed or replaced coordinator relaunch from the record.
- **Proportionality.** The full anatomy is sized for non-trivial assignments. A one-line mechanical fan-out does not repay a persisted brief and a stop rule. Keep the apparatus cheaper than the piece it governs.

## 5. Capability tiering

Match worker capability to the reasoning difficulty of the piece. Hard reading, design, code, and judgment go to the top tier; synthesis, review, and sweeps to a middle tier; mechanical fan-out to the cheapest. Capability costs money per unit of work, so overspending on mechanical work is waste and underspending on judgment work buys errors that cost more cycles than the saving.

Rules that make tiering hold:
- **Tier empirically.** Rank capabilities by measured performance on your own work, not by release order or vendor ordering.
- **Pin the tier to an exact version. Never let an unversioned alias select it silently.** An alias resolves at launch to whatever is current, which can silently be a capability you excluded or one you never measured. Pinning makes the REQUEST reproducible, which is a weaker guarantee than it sounds: configuration selects what you ask for, and only a record written by the SERVING side establishes what answered. Where your runtime writes such a record per call, treat it as the only evidence of which tier actually ran, and treat the configuration, the launch-time resolution, and the worker's own account of itself as statements of intent or belief. Measure where your runtime lets that pin live: some launch interfaces accept short names only and reject exact version identifiers, and where that holds the pin belongs in project-scoped configuration rather than at the launch. Pinned somewhere is the invariant; pinned at the launch is not.
- **Exclude tiers with measured failure modes, and record the measurement.** Generic illustration: a project that measured a newer model making more reasoning errors and jumping ahead of its evidence more often than its predecessor excluded the newer one and locked its top tier to the predecessor at maximum reasoning effort. That exclusion rests on a measurement. A project that measures differently tiers differently.
- **An excluded tier may be re-admitted inside a supervised lane, never at large.** Exclusion forfeits capability, so a project that later wants an excluded tier's strength has one sound route: admit it only as a bounded worker, on a named tightly-scoped assignment, under a coordinator actively watching that run — never as the default tier, and never as a coordinator itself. Name the failure classes the watch is for before the first such run, and include over-caution among them: a worker that declines authorized work or hedges past its evidence is failing, not being safe, and a watch that looks only for overreach will not see it. The watch is the permission, so routing an excluded tier and then not watching it is the same as not having excluded it. Where the excess caution traces to the brief's own hedging language, fix the brief before correcting the worker, or the cause keeps re-emitting the symptom. Treat the whole arrangement as a hypothesis under test rather than a settled result, and let these runs produce the measurement that the original exclusion never had. Prevents two opposite failures: a permanent forfeit of capability on one side, and a quiet relaxation of a measured exclusion on the other.
- **Coordinator authority is positional, not capability-ranked.** The coordinator briefs, collects, and decides; the top tier is always available to a worker for the hardest piece regardless of the coordinator's own level, and the coordinator adjudicates what comes back by receipts — a fresh read or measurement made for the claim — rather than by out-ranking the worker in capability.
- **Escalate the hardest judgment and writing to the top tier deliberately.** Difficulty tracks the reasoning a piece demands, not its length. Short pieces of high-stakes judgment are the ones most often mis-tiered downward.

## 6. Verification

- **Claims require receipts.** State a current fact only from a fresh read or measurement made for that claim. Recollection cannot be audited, and a description of a system drifts from the system as the system changes.
- **The author never certifies their own gate-critical product.** A separate party with fresh context reviews it. The author's context holds the intent and reads that intent into the product; a reviewer holding only the product and the standard sees what is actually there.
- **Efficacy language has three levels, and each has a price of admission.** *Built* means the thing exists, and earns only the status "attempted, untested". *Exercised against test cases* earns "behaves as specified on these cases", one level below working. *Measured before and after on real outcomes* earns "improved", stated with the numbers. Without this discipline every capability's status collapses into one undifferentiated label, and the system loses the ability to tell what has been checked from what has been assumed. Existence is the cheapest evidence available and the most convincing-feeling, which is exactly why it needs an explicit rule against it.
- **Spend verification where a wrong claim changes a decision.** The coordinator checks a load-bearing claim at its source before a consequential decision and re-does none of the rest. Verification is not free, and verifying uniformly costs as much as the work.

## 7. The ledger system

Three durable records, each closing a specific failure. Each is written so a worker with no prior context can read and act on it, which is what gives the system continuity across cycles without a shared conversation.

- **Change ledger.** Append-only, one row per change, dated. Past rows are never edited. It closes the absence of a decision history, which is acute where there is no version control. Append-only is the operative property: a history that can be edited is indistinguishable from an accurate one.
- **Status ledger.** One row per capability or check, with a status drawn from a fixed vocabulary, and every status past "attempted, untested" carrying a citation to the measurement that justifies it. It closes unfounded efficacy claims. The citation is required rather than encouraged because an uncited status looks exactly like a cited one at the point of reading.
- **Code inventory.** One row per program: what it does, how it is invoked, where it came from, how it was verified. Every brief points its worker here before any code is written, with a fixed order: use an existing entry where it fits, adapt one in place where it is close, build new only where neither works, and report which of the three was done. It closes reinvention. The cost of reinvention is not only wasted time and capability budget; a second implementation of the same thing produces a second answer, and two answers that disagree cost more to resolve than either cost to build.

## 8. The two-stage quality protocol

Applies to any product judged against a standard that automation covers only partly.

**Stage 1** runs the automated checks and the specialist review passes. It catches the mechanizable defects.
**Stage 2** has the requester, or whoever owns the standard, mark up the stage-1 output. What they mark is the **residual**: what stage 1 could not catch.

- **Every residual item becomes a labeled test case**, carrying the flagged text and the corrected text. This converts a one-time human judgment into a repeatable check and is the only ground truth available for what the automation misses.
- **The efficacy measure is the residual trend across rounds, not the count in any one round.** A single round's count moves with how much material there was and how much attention the reviewer spent. Hold the counting rule fixed across rounds and record two figures alongside the count: the total volume flagged, and the share of it that the standard covers. A residual that shrinks while its covered share rises means the material improved, not that the reviewer's attention lapsed.
- **Read the trend's shape, not only its size.** When the residual falls, check whether what remains has moved to a level the automation cannot reach. Measured in one project: a residual fell 61% in one round while the share of it visible to any automated check fell from 28% to zero, and the round produced the first defect whose extent was a whole section rather than a sentence. That shape says to build fewer new checks and to plan for a heavier reading pass, which is the opposite of what the falling count alone suggests.
- **Remediation text is itself a defect source.** This is measured, not cautionary: in one round, four of the nine flagged sites were text written in the previous round specifically to satisfy a previous instruction. Three rules follow.
  1. **Close a fix against the exact object the instruction named.** Measured instance: an instruction naming one specific figure was satisfied in a different figure and in prose, the named figure was left untouched, and the instruction returned verbatim in the next round.
  2. **Sweep the class, not the instance.** Measured in the same round as a natural experiment: every defect class fixed everywhere it occurred fell to zero, while a class fixed only at its flagged instance came back, with ≥8 untouched instances still standing.
  3. **Re-audit newly written text as a fresh draft.** Text written to answer an instruction arrives after the checks have run and is therefore exempt by default. Two measured consequences of that exemption: compressing an abstraction into a short sentence produced an unhedged absolute claim, because the abstraction had been carrying the hedge; and cutting a self-important phrase left a sentence that announced a reason without giving one. A related effect: removing a defect that was doing structural work leaves a structural hole, so re-express what it was carrying rather than only deleting it.

## 9. Scope and safety

- **One explicit boundary, stated as a path or region, containing all work by every participant.** Nothing outside it is read or written without an explicit grant from the requester for that specific excursion.
- **The boundary rule is repeated verbatim in every brief.** A fresh worker inherits nothing, so a rule held only in the coordinator's context never reaches the party that would violate it. The rule exists because unbounded workers sweeping parent and system locations is observed behavior, and containment is the reason for having a bounded work area at all.
- **Read-only default outside the granted scope.** Anything beyond the boundary is never written and is read only under a grant.
- **Backup before bulk edits where no version control exists.** A dated archive taken at a known-good point is the only undo available. A bulk edit is the action class with the widest blast radius and the highest cost to reverse, which is what earns it a mandatory precondition.
- **General form of these three rules:** where the costs of being wrong are asymmetric, default to the cheap-to-reverse side and require an explicit token for the expensive side.

## 10. What generalizes and what is a local choice

**Load-bearing invariants.** These hold on any runtime with isolated workers, and removing one removes a property section 1 paid for:
coordinator that only decomposes, routes, synthesizes, verifies, and decides; workers doing all domain work; code as a co-equal participant selected by the determinism test; everything exchanged persisted as a named record; complete self-contained briefs with primary-source reads, named destinations, a report cap, and a stop rule; capability tiered by difficulty with versions pinned; the cycle ending in a re-fit decision with a fixed exit set; claims requiring receipts; no self-certification of gate-critical products; efficacy language gated on measurement; append-only provenance plus a status ledger and a code inventory; an explicit boundary repeated in every brief.

**Invariants with a stated scope limit.** Each depends on a runtime property. Measure the property before you carry the rule:
- *The store is the only channel between participants* depends on workers being context-isolated. On a runtime with shared live memory between workers, persistence keeps its provenance value and stops being the only channel.
- *A change of assignment waits for the next launch* depends on workers not being re-assignable mid-run. Where a worker can accept a new assignment while running, redirect it and drop the wait.
- *A chunk can be routed whole to a subordinate coordinator* depends on a worker being able to launch a worker and receive its reply. That property was measured here to one level; measure yours before nesting deeper.
- *An excluded capability tier can be re-admitted inside a supervised lane* depends on your runtime letting you bind a worker to a named configuration the coordinator did not type at the launch, and letting the coordinator observe or interrupt that run while it is happening. Where neither property holds there is no lane to re-admit into, and the exclusion stands flat.
- *The full brief anatomy* is sized for non-trivial work. Trivial mechanical pieces do not repay it.

**Free parameters. Choose these for your context and do not import them:** the specific capability tiers and their version identifiers; the boundary location; the store's layout and record naming; the names you give the arrangements; which checks are automated and which stay a reading pass; the report cap size; backup cadence; ledger formats and status vocabularies; the reviewer's identity in a build-then-review pair.

**Closing rule for the implementer.** Implement each invariant with whatever primitive your runtime provides. Where a rule above names a runtime property, measure that property rather than assume it: these rules were derived on one runtime, and the scope-limited four are exactly the places where a different runtime changes the answer.
