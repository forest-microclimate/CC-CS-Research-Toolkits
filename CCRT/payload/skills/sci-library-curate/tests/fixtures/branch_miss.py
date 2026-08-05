# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# FIXTURE (branch-independence proof for requirement 3: "each new branch is hit").
# Runs fine; EVERY changed line is executed; but one branch ARC is not taken. Line coverage
# alone would pass -- only branch coverage catches the unexercised arc.
def flag_row(r):
    y = 0
    if r.get("orphan"):        # driver passes only orphan=True -> the (if-False) arc is never taken
        y = 1
    return y                   # reachable on both arcs, so line coverage of every line is 100%
