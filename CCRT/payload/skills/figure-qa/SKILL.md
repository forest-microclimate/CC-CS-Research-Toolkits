---
name: figure-qa
description: The render-and-LOOK checklist for scientific figures — invoke WHEN a figure/plot/panel is about to be reported, saved as a deliverable, or embedded in a doc, and WHEN diagnosing "the figure looks wrong". Owns the discipline that a CLEAN SAVE IS NOT A CHECK — render the actual image, open it, and inspect against the checklist (panels present, axes+units, legend-series match, expected ranges, gaps not bridged, legibility, colorblind-safe). A checklist for the domain-CAPABLE author — deliberately NOT a mechanical gate (the corpus judged this family uncatchable by domain-blind checks). Fires on "make/save/report this figure", "regenerate the plots", "why does this panel look off". NOT statistical method choice (-> research-stats-advisor) and NOT prose/caption craft (-> writing-science).
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-28). Authored in the verification-integrity pass. Carries SEED-12 (figure self-containment defects, expert-caught) + DISC-05 (lines drawn across data gaps) as a CHECKLIST for the capable author — explicitly not a gate pretense: the ledger routes this family "no domain-blind gate" and this skill honors that. Formalizes the standing produce-diagnostic-plots-and-VISUALLY-INSPECT preference.

# figure-qa — a figure is checked by LOOKING at it, not by the code exiting 0

## When to invoke
WHEN about to report, save-as-deliverable, or embed any figure; WHEN a batch of plots was regenerated; WHEN a reader says a figure looks wrong.

## The one load-bearing move
RENDER THE REAL ARTIFACT AND OPEN IT. The saved file, at final size, actually looked at — not the plotting code, not a thumbnail, not the object printing without error. Numeric summaries and clean exits miss broken panels, empty facets, and visual pattern errors by construction (the recorded failures were all expert-caught BY EYE). Read the rendered image back into the session (view the PNG / rasterize the PDF page) — a save you never re-opened is unverified.

## The checklist (each item inverts a recorded defect)
- PANELS: every expected facet/panel present and NON-EMPTY; facet labels match the data levels (an empty facet = a silent filter/join defect upstream — pull that thread, don't crop it out).
- AXES + UNITS: both axes labeled WITH units; scales sane (no log axis labeled linearly, no percent axis silently 0–1); limits not clipping data unannounced.
- LEGEND ↔ SERIES: every plotted series in the legend and every legend entry plotted; series distinguishable at final size; colorblind-safe palette (never a red-green-only distinction).
- RANGES: values within physical/expected bounds — an impossible value in a plot is a defect POINTER, not a plotting nuisance (root-before-bandaid applies to figures too).
- GAPS: lines NOT drawn across data gaps as if continuous (DISC-05) — break the line or mark the gap; a bridged gap asserts data that does not exist.
- SELF-CONTAINMENT (SEED-12): title/caption + labels let the figure stand alone; paired ratios labeled conceptually separate ("iWUE and WUE", never a slashed compound).
- LEGIBILITY: text readable at the size it will be consumed (test at target dimensions, not the interactive canvas); overplotting handled (alpha/jitter/2D-density), not ignored.

## After the look
Save the INSPECTED render beside the figure object (the object alone cannot prove what the reader will see), note "visually inspected at <size>" in the report, and fix upstream defects at their root — never by cropping, filtering, or smoothing the symptom out of the picture.

REF: `research-stats-advisor` (method-of-display choice: smoother type, interval construction) · `writing-science` (caption/story craft) · root-before-bandaid + the plot-inspection standing preference (the disciplines this checklist operationalizes) · `testing-discipline` (the same a-check-must-be-able-to-fail epistemics — here the check is your eyes on the render).