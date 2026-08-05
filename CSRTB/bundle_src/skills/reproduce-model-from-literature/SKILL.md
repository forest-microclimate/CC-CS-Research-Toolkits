---
name: reproduce-model-from-literature
description: Invoke WHEN re-implementing a published model from its equations — reproducing a paper's figure or reported result before extending it, or building a mechanistic / optimality / dynamical model from a methods section. Reconstruct the parameter+unit table FIRST, reproduce the published baseline to its own numbers, THEN extend. Covers the gotchas papers omit — missing units, initial conditions, integrator settings — plus digitizing the target curve and stating a match tolerance before you look.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# reproduce-model-from-literature — recover the baseline before you extend it

## When to invoke
WHEN re-implementing any published model from its equations — photosynthesis, stomatal/optimality, energy-balance, population, community, or biogeochemical — and you intend to reproduce a figure or result, or extend it. The deliverable of THIS skill is a baseline that recovers the paper's own numbers; the extension comes after.

## The load-bearing rule
A model that cannot reproduce the paper's published baseline is not a basis for new work. Reproduce first, extend second — always in that order.

## 1. Reconstruct the parameter + unit table BEFORE writing model code
Papers scatter parameters across text, captions, and tables, and silently omit some.
- WHEN about to code an equation ⇒ first build a table: symbol · value · UNIT · source (eqn / table / caption / "not stated").
- A "not stated" row is a decision point, not a blank — record the assumed value and why, and tag it `(guessed)`.
- Unit mismatch is the modal reproduction bug — carry units in the table and check both sides of every equation dimensionally before running.

## 2. Pin what the paper under-specifies
Recurring omissions, each an output-detectable trigger:
- WHEN the model integrates over time ⇒ the paper rarely states the integrator / timestep / tolerance. Pick one, RECORD it, and confirm the result is invariant to halving the step — if it moves, you are reading a numerical artifact, not the model.
- WHEN a state model needs initial conditions ⇒ they are often unstated. Record the assumption and report sensitivity to it.
- WHEN an optimality model reports an optimum ⇒ name the objective, the constraint, and the currency being maximized. A reproduced optimum with an unnamed objective is not reproduced.

## 3. Reproduce the TARGET quantitatively, not by eye
- WHEN the target is a published figure ⇒ digitize its curve/points (a plot digitizer), overlay your output on the SAME axes, and compare numerically — never "looks close".
- State the match tolerance BEFORE you look (within digitization error, or X% of the reported value).
- WHEN your baseline misses ⇒ the parameter/unit table (§1) is the first suspect, then the under-specified settings (§2), before you doubt the equations.

## 4. Only then extend
- Keep the reproduced baseline as a regression fixture: with the new terms switched off, the extension must still recover it bit-identically (the null control).
- Report the extension against the baseline — direction and magnitude of change — never in isolation.

## Hand-offs
- The objective / constraint / currency discipline for optimality claims, and the pool-conservation / transient-vs-equilibrium discipline for dynamical models, live in the modeler specialist that called this skill.
- Rendering the reproduction as a human write-up ⇒ a teaching / science-writing skill, not this one.
