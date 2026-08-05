---
name: tz-safe-timestamps
description: Build timezone-safe timestamps and join/resample data from multiple sources with alignment kept explicit and verified, not silently misaligned. Use whenever parsing or constructing datetimes, joining/merging/resampling across sources that may differ in timezone (e.g. UTC satellite data vs local gauge data), computing diel/seasonal indices, or when a time-based join returns suspiciously few or many rows.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-11). Auto-stamped by doc-status.sh; refine the note on next edit.

# tz-safe-timestamps — no silent timezone misalignment

Timestamps can PRINT identical while differing internally; a mixed-tz join then silently drops/duplicates rows. This makes tz explicit and verified.

## When to invoke
Any datetime parse/construct, any cross-source time join/resample, any diel/seasonal binning, or a join with an unexpected row count.

## Procedure
1. **Define the tz ONCE** at the top of the script as a single canonical constant; use it everywhere — pass it explicitly rather than letting functions default to the session/system tz.
2. **Rebuild timestamps from components (distrust on-disk tz labels).** Rebuild timestamps from y/m/d/h(/min) components with an EXPLICIT `tz=` (e.g. `ISOdate`, `make_datetime(..., tz=TZ)`, `lubridate::force_tz`).
3. **Know the sign convention.** POSIX `Etc/GMT+X` is INVERTED: `Etc/GMT+3` = UTC−3. (Documented failure: Etc/GMT+3 vs UTC mismatch produced 1 block instead of 3.)
4. **Convert all sources to ONE canonical tz before joining** (e.g. UTC satellite product ⇄ local gauge: pick one, convert both explicitly).
5. **Verify empirically against an independent anchor** BEFORE trusting the join: align a known diel signal to solar noon, or a known event to its recorded time; confirm the offset is what you expect.
6. **Sanity-check the join row count** (not silently collapsed or exploded).

## Success check
A single tz constant governs the script; every source's timestamps verified against a physical/known anchor; join row-count sane; alignment rests on rebuilt/verified components, not printed strings.

## Site-tz specifics (hard-won)
- Look up the site's actual UTC offset from an authoritative source; never trust an on-disk tz label. A single wrong offset can silently propagate across many scripts — the step-5 empirical time-of-peak-vs-solar-noon check catches exactly this class, so run it BEFORE building anything downstream.

## Join integrity (hard-won)
- Text-key joins from hand-entered labels (+ hardcoded prefixes) feeding a date-window filter SILENTLY drop non-matching rows — reconcile expected-vs-realized row counts with `stopifnot`/anti-join at EVERY merge; anchor a raw-files-vs-logs-vs-master audit on the actual raw files (a master built from an incomplete file list silently omits subsets).
- Solar-geometry (`suncalc::getSunlightPosition`) must be computed at the LOCAL clock tz THEN converted to UTC; verify it reproduces the pipeline's sun elevation to ~0°.
- Date-parse: `as.Date(x,"%d-%b-%y")` misreads 4-digit years → silent NA → dropped downstream; use `lubridate::dmy()` for day-first dates and verify the parsed range.

## Related
Foundational for temporal-block-cv (block boundaries must be tz-correct) and any diel/seasonal aggregation; gap-fill-imputation (round off-grid timestamps before joining).
