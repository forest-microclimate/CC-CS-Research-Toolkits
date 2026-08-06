---
name: julia-performance-correctness
description: Diagnose and fix Julia performance (allocations, type instability, dispatch) and correctness gotchas (column-major, aliasing, @inbounds, float equality). Use when writing, reviewing, or debugging Julia — especially numerical hot loops — or when hitting slow code, unexpected allocations, type-instability, method-ambiguity, or a silently-wrong numerical result.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-11).

# julia-performance-correctness — type stability, allocations, dispatch, correctness

## When to invoke
Writing/reviewing/debugging Julia (esp. numerical inner loops); code slower than expected; unexpected allocations; a `@code_warntype` shows `Any`/`Union`; method ambiguities; or a numerically-wrong-but-runs result.

## Type stability — the #1 perf lever
- `@code_warntype f(args)` (or `Test.@inferred`): any red / `Any` / non-small `Union` return or variable = instability → fix before optimizing anything else.
- Struct fields must be CONCRETE or parametric (`struct S{T}; x::T; end`), NEVER abstract (`Real`, `AbstractArray`) or untyped — abstract fields kill inference at every access.
- In hot code, pass globals as args or make them `const` — a non-`const` global's type can change ⇒ unstable.
- Function barriers: split an unstable outer (setup) from a stable inner kernel typed on its args — the kernel compiles specialized.
- Containers concrete-eltype: `Vector{Float64}`, not `Vector{Any}`; `zeros(FT, n)` not `[]`.

## Allocations
- Measure: `BenchmarkTools.@btime f($x)` (interpolate globals with `$`), `@allocated`. `@time` includes first-call COMPILE — run twice.
- In-place: `.=`, `@.` (fuse a whole expression), `mul!`, `sum!`; pre-allocate buffers and reuse across iterations.
- Slices COPY: use `@views`/`view()` for read-only slicing; fuse loop expressions with `@.` to skip temporaries.
- Pre-size arrays (or `sizehint!`) rather than growing them in hot loops (`push!` reallocates).

## Multiple dispatch
- `@which f(x)` = the method chosen; `methods(f)` / `Test.detect_ambiguities` for ambiguities.
- Abstract-typed ARGUMENTS are fine (dispatch specializes per concrete call); the danger is abstract FIELDS / containers.
- Extend only a function or type you own — type piracy is adding methods when you own neither.

## Correctness gotchas (runs ≠ correct)
- COLUMN-MAJOR: innermost loop over the FIRST index (columns contiguous); row-major loop order thrashes cache and can be 10× slower.
- 1-based indexing; prefer `eachindex(a)` / `axes(a,d)` over `1:length(a)`; `2:1` is empty, `2:-1:1` counts down.
- `==` (value) vs `===` (identity); floats: `isapprox`/`≈`, and `NaN != NaN` ⇒ use `isnan`.
- Integer overflow is SILENT (`Int` wraps) — use `Float`/`widen`/checked arithmetic where products can exceed `typemax`.
- `@inbounds` ONLY when the index is provably in bounds — otherwise an off-by-one becomes silent memory corruption, not an error.
- Aliasing: `b = a` shares memory (mutating `b` mutates `a`); `copy`/`deepcopy` to detach; `.=` mutates the LHS in place.

## Workflow
- `Revise.jl` for iterative edits — BUT it does NOT reload `include`d files or redefine structs; for struct changes OR any determinism/before-after verdict, use a FRESH process.
- Warm the first call (compile) before timing; profile with `@profview` / `Profile.@profile`, inspect hot kernels with `@code_llvm`.

## Success check
`@code_warntype` clean on hot functions; `@btime` shows ~0 allocations in the inner loop; no method ambiguities; the correctness-gotcha list checked against the changed code.

## Threading / parallel launches (hard-won)
- A SCALAR-bound Julia run ≈ 1 core, but a MATRIX-heavy run silently spawns OpenBLAS threads and grabs ALL cores — two can saturate 16 while the process count still reads "2". Measure load by summed per-process CPU%, NOT process count. For parallel launches pin `OPENBLAS_NUM_THREADS=1` (+ `OMP_NUM_THREADS=1`) per run. `BLAS.get_num_threads` is a CEILING for matrix-call bursts, not steady load.
- Before launching N parallel processes, do ONE warm-up load to populate the shared precompile cache — else the N race and contend on the precompile lock (an edit/revert invalidates the cache ⇒ silent multi-minute recompile).
- juliaup shim: many quick `julia` invocations each check for a self-update and contend on `.juliaup-lock` ⇒ can deadlock and block all subsequent calls. Call the julia BINARY directly (bypass the shim), or invoke sequentially.

## More correctness gotchas (hard-won)
- `clamp(NaN, lo, hi)` returns `NaN` — it does NOT sanitize NaN; a NaN flux propagates silently into state. Guard inputs for NaN BEFORE clamping.
- `@inbounds` over an index past the real length (e.g. `x[i+1]` on a 1-elem array) reads garbage ⇒ NON-DETERMINISTIC flickering results (step-to-step change, or "healthy"↔"collapsed" oscillation). Remove `@inbounds` first to let bounds-checking expose it — but a bit-identical A/B proves a suspected UB behaviorally irrelevant, so verify it's load-bearing before blaming it.
- Revise reloads FUNCTION-BODY edits in seconds but NOT module-level changes (new file / `include` / `import` / `const`, or struct redefinition) — those need a fresh process. A "fix" tested only under Revise may be running OLD code.
- Symptom triage: a run at 100% CPU producing NO output far longer than a comparable run ⇒ suspect an inner iterative solver hitting max-iter every step (non-convergence), not "just slow" — add per-step timing to confirm.
- Fixed-size per-element buffers are often allocated to a compile-time dimension in constructors, NOT length-adaptive; growing a working dimension requires resizing EVERY allocator, not just the loops (loops may adapt via `length()` while allocations silently don't).

## Package / environment setup (hard-won)
- `]instantiate` resolving deps ≠ a working env — PRECOMPILATION fails independently AFTER. Diagnose by whether `using <Pkg>` precompiles, not whether instantiate returned (tell: the Manifest "in-use" timestamp lags the artifact-download timestamp).
- A package that downloads ARTIFACTS at PRECOMPILE time (e.g. a package pulling a large artifact from a remote archive) leaves the cache broken on a transient network hiccup — which then also breaks `using` of shared-dep packages. Fix = re-run `]instantiate` / `using <Pkg>`, NOT a code change.
- `Project.toml` `[sources]` requires Julia ≥1.11 — silently unusable on older toolchains; flag toolchain assumptions (e.g. `+1.12.6`) when a manifest uses newer features.
- Fork-and-modify a dependency: `Pkg.develop(path=<local clone>)` repoints the project at a working copy (edits picked up after re-precompile; a normal git repo to branch/rebase vs upstream).

## More type / correctness gotchas (hard-won)
- Type-parametric numeric code (`@kwdef mutable struct X{FT<:AbstractFloat}`): set `FT` once and wrap EVERY float literal `FT(1.35)` — bare literals silently break parametric type stability across Float32/Float64.
- Struct default field values are runtime PLACEHOLDERS, not behavioral defaults (overwritten each step) — read the runtime assignment site; take a model's effective default from that runtime assignment, not the struct definition.
- Unicode identifiers (`g_CO₂_b`, `ψ`, `∂e∂t`, subscripts) are pervasive in scientific Julia — grep with the EXACT glyphs; ASCII patterns miss them.

## Related
`preflight-parallel` (independent runs, OpenBLAS pinning); verify-or-hedge (state the numbers on any perf claim).
