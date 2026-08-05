# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# FIXTURE (known_bad, class: hidden_dependency_runtime_error)
# SYNTHETIC reproduction of the hidden-dependency SHAPE (not a byte-copy of any real
# revision). VERIFIED 2026-07-24 against the pre-port backup
# sci_library_curate.py.pre_i16i19_20260724T165610Z: that file contains NEITHER
# _cn_stem nor is_cryptic_name (0 and 0), and the CURRENT module contains BOTH, so no
# real revision ever shipped one without the other. What IS real is the defect CLASS --
# a ported function calling a helper that never came with it, which py_compile passes
# and only a fresh-import functional run catches. That class is what this fixture tests. py_compile is green
# (the name resolves lexically); the NameError fires only when is_cryptic_name is actually
# CALLED on a row -- i.e. only when the changed cryptic-name branch is exercised.
import re

_CRYPTIC_LEADDIGIT_RE = re.compile(r"^\d")
_CRYPTIC_PUBCODE_RE = re.compile(r"^[a-z]{2,6}\d{4,6}")
_AUTHOR_YEAR_RE = re.compile(r"^[A-Z][A-Za-z'\-]+_(1[6-9]\d\d|20[0-2]\d)(_|$)")


def is_cryptic_name(cn):
    s = _cn_stem(cn)                     # _cn_stem NEVER PORTED -> NameError at call time
    if _CRYPTIC_LEADDIGIT_RE.match(s):
        return True
    if _CRYPTIC_PUBCODE_RE.match(s):
        return True
    if "_MOESM" in cn or "MOESM" in cn:
        return True
    if "-sup-" in cn.lower():
        return True
    return not bool(_AUTHOR_YEAR_RE.match(s))


def _note_blob(r):
    return ((r.get("notes", "") or "") + " " + (r.get("dedup_note", "") or ""))


def check_i17(idx, name_col="clean_name"):
    """I17: no cryptic clean_name without a 'cryptic_unresolved' flag."""
    i17_bad = []
    for r in idx:
        rt = r.get("record_type", "")
        if rt not in {"article", "supplement"}:
            continue
        cn = r.get(name_col, "")
        if not is_cryptic_name(cn):       # <-- calls the helper with the unported dep
            continue
        blob = _note_blob(r)
        if "cryptic_unresolved" in blob:
            continue
        i17_bad.append(cn)
    return i17_bad
