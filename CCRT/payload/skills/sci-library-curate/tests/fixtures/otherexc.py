# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# FIXTURE (known_bad, class: other_runtime_exception)
# Proves the top-level catch is `except Exception`, NOT a NameError/ImportError/AttributeError
# allowlist: this raises ZeroDivisionError, which such an allowlist would let slip through.
def parse_supp(row):
    n = row["count"]
    return 100 / n
