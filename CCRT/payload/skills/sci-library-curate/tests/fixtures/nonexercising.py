# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# FIXTURE (known_bad, class: non_exercising_coverage_gap)  -- THE vacuous-pass the review flagged.
# The edited code is correct and runs. The smoke driver exercises only the PRE-EXISTING
# function; the CHANGED function (classify_supp) is never touched. Nothing raises, yet the
# changed lines have zero coverage -> the gate must FAIL on coverage.
def existing_thing(x):
    return x + 1


def classify_supp(row):              # the "newly added" block -- never called by the driver
    t = row.get("record_type", "")
    if t in ("supplement", "dataset"):
        return "companion"
    return "primary"
