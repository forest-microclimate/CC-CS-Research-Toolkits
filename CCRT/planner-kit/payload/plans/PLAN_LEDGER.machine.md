# PLAN_LEDGER.machine.md  (machine-optimized; the plan registry — one row per plan ever run in this project)
# STATUS: CURRENT (2026-08-03). Seeded template — restamp the date when you record your first row. A plan's FOLDER is its status — `plans/current_active/` (last-approved copy of the running plan) · `plans/for_later_resume/` (parked, resumable) · `plans/finished/` (completed); every folder move pairs with a row update here. RULE: the harness plan slot (~/.claude/plans/<session-slug>.md) is ONE mutable file — BEFORE repurposing it ⇒ (1) snapshot the current plan VERBATIM into the status folder that fits, with a provenance header + resume pointer, (2) update this ledger. At plan APPROVAL ⇒ copy the approved plan into current_active/; on PARKING ⇒ move to for_later_resume/; on COMPLETION ⇒ move to finished/. TO RESUME a parked plan: read its snapshot + its row's resume pointer + the ledgers it names; the snapshot body is the plan of record.
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# COLUMNS: plan | status ∈ {active, parked-resumable, completed, superseded} | snapshot | harness slot | resume pointer | dates

| plan | status | snapshot | harness slot | resume pointer | dates |
|---|---|---|---|---|---|
