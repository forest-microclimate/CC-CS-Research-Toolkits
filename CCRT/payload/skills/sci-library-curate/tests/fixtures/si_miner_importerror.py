# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# FIXTURE (known_bad, class: import_error_fresh_import)
# A top-level import of a module that was never ported. Compiles clean; the ImportError
# surfaces only on a FRESH import (the exact reason an in-process re-call can mask it).
from _never_ported_si_miner import mine_si_dois


def check_i18(rows):
    return [r for r in rows if mine_si_dois(r)]
