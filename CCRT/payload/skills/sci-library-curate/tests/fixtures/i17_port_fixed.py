# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# FIXTURE (known_clean) -- the correctly-ported counterpart of i17_port_broken.py.
# _cn_stem IS present, and the driver exercises BOTH branches of is_cryptic_name (cryptic / non-cryptic) -- the
# record_type gate named by the broken twin's check_i17 is NOT defined in this file -- so
# all changed lines and all branch arcs over changed lines are covered with nothing raised.
import re

_CRYPTIC_LEADDIGIT_RE = re.compile(r"^\d")
_CRYPTIC_PUBCODE_RE = re.compile(r"^[a-z]{2,6}\d{4,6}")
_AUTHOR_YEAR_RE = re.compile(r"^[A-Z][A-Za-z'\-]+_(1[6-9]\d\d|20[0-2]\d)(_|$)")


def _cn_stem(cn):
    return re.sub(r"\.[A-Za-z0-9]+$", "", str(cn or ""))


def is_cryptic_name(cn):
    s = _cn_stem(cn)
    if _CRYPTIC_LEADDIGIT_RE.match(s):
        return True
    if _CRYPTIC_PUBCODE_RE.match(s):
        return True
    if "_MOESM" in cn or "MOESM" in cn:
        return True
    return not bool(_AUTHOR_YEAR_RE.match(s))
