<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# Planner memory index

Project-scoped agent memory for the planner: auto-loads for sessions running that agent; other agents reach it via this index.

- [Supervisory workflow (STANDING)](feedback_supervisory-workflow.md) — the cycle PLAN → BRIEF (six elements) → LAUNCH → COLLECT (name one of six outcomes) → DECIDE; planner coordinates only; subagents (≤ `claude-opus-4-8`; `claude-fable-5` ALWAYS available as the ceiling for the hardest pieces, independent of the planner's level) do all file/code work; exchange only via durable files at briefed paths.
- [Two-stage detection protocol (STANDING)](feedback_two-stage-detection.md) — rounds that output a partly-automatable product: the in-development tools detect first, then the standard-owner sweeps the residual; misses become fixtures + efficacy evidence.
