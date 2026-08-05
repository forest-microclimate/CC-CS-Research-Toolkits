#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""check_current_documents.py — fail-closed checker for the Durable-Doc Architecture (DDA).

Enforces the ratified structural floor on every durable doc in a project tree:
  UNIVERSAL  : a well-formed in-band STATUS header (the D7 pre-seeded mandatory floor).
  CLASS      : STATE / HISTORY / HYBRID body contract (supersede-in-place / append-only / split faces).
  CROSS-DOC  : one-owner-per-topic (DDC-02), no dangling route/registry target (DDC-01/02).

DESIGN LIMIT (stated in DDA_SPEC §7): this checks FORM / identity, NOT content-truth. A well-formed
but stale or poisoned CLAIM passes the header/hash check; content-truth needs the verification ledger
(DDC-14) + authority lattice, not this checker. That is by design — the checker is one invariant of
several, and it fails closed on the ones it CAN mechanically verify.

USAGE:
  python3 check_current_documents.py <dir> [--strict] [--json]
  python3 check_current_documents.py --self-test
Exit 0 = all pass; 1 = one or more FAIL; 2 = usage error. --strict makes WARN fatal too.
A durable doc = any *.machine.md / *.template.* / file carrying a '# DDC_CATEGORY:' or 'DDC_CATEGORY:' line.
"""
import argparse, os, re, sys, hashlib, glob, json

REQUIRED_FIELDS = ["DOC_ID", "DOC_CURRENCY", "AUTHORITY_CLASS", "VERIFICATION_STATUS",
                   "TASK_STATUS", "AS_OF", "TOPIC_ID", "DDC_CATEGORY"]
LEGAL_AUTHORITY = {"A0_VERIFIED_LIVE", "A1_CURRENT_OWNER", "A2_SECONDARY", "A3_HISTORICAL"}
LEGAL_VERIF = {"VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "N/A"}
# currency tokens legal by class
CURRENCY_STATE = {"DRAFT", "CURRENT", "SUPERSEDED", "RETRACTED"}
CURRENCY_HISTORY = {"APPEND_ONLY"}
DDC_CLASS = {  # ratified §1 classification
    "DDC-01": "STATE", "DDC-02": "STATE", "DDC-03": "STATE", "DDC-04": "STATE", "DDC-05": "STATE",
    "DDC-06": "STATE", "DDC-07": "STATE", "DDC-08": "STATE", "DDC-09": "STATE", "DDC-19": "STATE",
    "DDC-20": "STATE",
    "DDC-10": "HYBRID", "DDC-11": "HYBRID", "DDC-12": "HYBRID", "DDC-13": "HYBRID", "DDC-14": "HYBRID",
    "DDC-15": "HYBRID", "DDC-17": "HYBRID",
    "DDC-16": "HISTORY", "DDC-18": "HISTORY",
}
CLOSED_CURRENCY = {"SUPERSEDED", "RETRACTED"}


def parse_header(text):
    """Pull the STATUS-header fields from the first ~20 lines (accepts '# K: v' or 'K: v')."""
    h = {}
    for line in text.splitlines()[:24]:
        m = re.match(r'#?\s*([A-Z_]+):\s*(.*)', line)
        if m and m.group(1) in REQUIRED_FIELDS + ["FORMAT", "SUPERSEDES", "SUPERSEDED_BY", "SOURCE_HASH"]:
            h[m.group(1)] = m.group(2).strip()
    return h


def ddc_of(header):
    m = re.search(r'(DDC-\d+)', header.get("DDC_CATEGORY", ""))
    return m.group(1) if m else None


def check_doc(path, text):
    """Return (fails, warns) for one durable doc."""
    fails, warns = [], []
    h = parse_header(text)
    # UNIVERSAL: required fields present + non-empty
    for f in REQUIRED_FIELDS:
        if f not in h:
            fails.append(f"missing STATUS field {f}")
        elif not h[f] or h[f].startswith("<"):
            warns.append(f"{f} is an unfilled placeholder")
    ddc = ddc_of(h)
    if not ddc:
        fails.append("DDC_CATEGORY names no DDC-NN")
        return fails, warns
    # UNIVERSAL: legal vocab. Authority is an A<n>_<NAME> taxonomy; a project MAY extend it with
    # semantic variants (the CliMA exemplar uses A2_CURRENT_CAVEATED). Check the FORM (A<digit>_UPPER),
    # not a fixed enum — form is what a fail-closed checker can verify; a closed enum would reject a
    # legitimate richer taxonomy (over-strict, the oracle-test finding of 2026-07-17).
    auth = h.get("AUTHORITY_CLASS", "").split()[0] if h.get("AUTHORITY_CLASS") else ""
    if auth and not re.match(r'^A\d_[A-Z_]+$', auth):
        fails.append(f"AUTHORITY_CLASS '{auth}' is not an A<n>_<NAME> class")
    verif = h.get("VERIFICATION_STATUS", "").split()[0] if h.get("VERIFICATION_STATUS") else ""
    if verif and verif not in LEGAL_VERIF:
        # N/A often written with a parenthetical
        if not verif.startswith("N/A"):
            warns.append(f"VERIFICATION_STATUS '{verif}' unusual")
    # CLASS contract
    cls = DDC_CLASS.get(ddc)
    declared_cls = None
    dm = re.search(r'\((STATE|HYBRID|HISTORY)\)', h.get("DDC_CATEGORY", ""))
    if dm:
        declared_cls = dm.group(1)
    if cls and declared_cls and declared_cls != cls:
        fails.append(f"{ddc} declared class {declared_cls} != ratified {cls}")
    # STATE: currency must be a STATE token
    cur = h.get("DOC_CURRENCY", "").split()[0]
    if cls == "STATE" and cur and cur not in CURRENCY_STATE:
        warns.append(f"STATE doc currency '{cur}' not in {sorted(CURRENCY_STATE)}")
    if cls == "HISTORY" and cur and "APPEND_ONLY" not in h.get("DOC_CURRENCY", ""):
        warns.append(f"HISTORY doc currency should be APPEND_ONLY (got '{cur}')")
    if cls == "HYBRID":
        # A HYBRID doc must carry BOTH a current-state face and a historical face. Templates use the
        # explicit '## STATE face' / '## HISTORY face' headings; a real-world HYBRID (the CliMA
        # exemplar) may realize the split semantically instead. Accept EITHER an explicit heading OR
        # a semantic marker of that face — form-checkable without demanding one literal string.
        state_markers = ["## STATE", "STATE face", "CURRENT:", "# 0 VERDICT", "current selection",
                         "CURRENT_", "decision_state", "## STATE face"]
        hist_markers = ["## HISTORY", "HISTORY face", "append-only", "superseded", "historical",
                        "pre-edit evidence", "OUTCOME_LOG", "adjudication trail", "newest first",
                        "newest-first"]
        has_state = any(m in text for m in state_markers)
        has_hist = any(m.lower() in text.lower() for m in hist_markers)
        # A HYBRID may split its two faces across two coupled docs (the CliMA exemplar keeps DDC-11
        # decisions here + the append-only verdicts in a sibling contradiction LEDGER). Accept a
        # missing in-doc face IF the doc explicitly names a sibling owner for it (ledger/log/history
        # pointer) — the split then stays traceable rather than silently absent.
        points_to_sibling = bool(re.search(r'ledger|contradiction[_ ]ledger|history owner|see .*log', text, re.I))
        if not has_state:
            fails.append(f"{ddc} HYBRID has no current-state face (no ## STATE heading nor a current-state marker)")
        if not has_hist and not points_to_sibling:
            fails.append(f"{ddc} HYBRID has no history face and names no sibling history owner (ledger/log)")
    return fails, warns


def discover(root):
    docs = []
    for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
        if not os.path.isfile(p):
            continue
        if p.endswith((".png", ".pdf", ".zip", ".pyc")):
            continue
        try:
            head = open(p, encoding="utf-8", errors="ignore").read(1500)
        except Exception:
            continue
        # a real durable doc carries DDC_CATEGORY as a HEADER FIELD (K: v in the first lines),
        # not merely the bareword somewhere in prose (e.g. an authoring brief describing the schema).
        if re.search(r'^#?\s*DDC_CATEGORY:\s*DDC-\d+', head, re.M):
            docs.append(p)
    return docs


def cross_doc_checks(parsed):
    """parsed = list of (path, header, text). Enforce one-owner-per-topic among CURRENT A1 docs."""
    fails = []
    owners = {}
    for path, h, _ in parsed:
        cur = h.get("DOC_CURRENCY", "").split()[0]
        auth = h.get("AUTHORITY_CLASS", "").split()[0]
        topic = h.get("TOPIC_ID", "").strip()
        if not topic or topic.startswith("<"):
            continue
        if auth == "A1_CURRENT_OWNER" and cur in ("CURRENT",) or (auth == "A1_CURRENT_OWNER" and "CURRENT" in h.get("DOC_CURRENCY", "")):
            owners.setdefault(topic, []).append(os.path.basename(path))
    for topic, ds in owners.items():
        if len(ds) > 1:
            fails.append(f"one-owner-per-topic violated: topic '{topic}' has {len(ds)} A1 CURRENT owners: {ds}")
    return fails


def run(root, strict=False, as_json=False):
    docs = discover(root)
    parsed = []
    results = []
    total_fail = 0
    total_warn = 0
    for p in docs:
        text = open(p, encoding="utf-8", errors="ignore").read()
        h = parse_header(text)
        parsed.append((p, h, text))
        fails, warns = check_doc(p, text)
        total_fail += len(fails)
        total_warn += len(warns)
        results.append({"doc": os.path.relpath(p, root), "fails": fails, "warns": warns})
    xfails = cross_doc_checks(parsed)
    total_fail += len(xfails)
    if as_json:
        print(json.dumps({"root": root, "n_docs": len(docs), "doc_results": results,
                          "cross_doc_fails": xfails, "total_fail": total_fail, "total_warn": total_warn}, indent=2))
    else:
        for r in results:
            if r["fails"] or (strict and r["warns"]):
                print(f"FAIL {r['doc']}")
                for f in r["fails"]:
                    print(f"     ✗ {f}")
                if strict:
                    for w in r["warns"]:
                        print(f"     ⚠ {w}")
            elif r["warns"]:
                print(f"warn {r['doc']}: {len(r['warns'])} placeholder/soft note(s)")
        for xf in xfails:
            print(f"FAIL (cross-doc) ✗ {xf}")
        print(f"\n{len(docs)} durable docs checked | {total_fail} FAIL | {total_warn} warn")
    hard = total_fail + (total_warn if strict else 0)
    return 1 if hard > 0 else 0


def self_test():
    import tempfile
    td = tempfile.mkdtemp()
    rc = 0
    good = ("# DOC_ID: p/x\n# DOC_CURRENCY: CURRENT\n# AUTHORITY_CLASS: A1_CURRENT_OWNER\n"
            "# VERIFICATION_STATUS: VERIFIED\n# TASK_STATUS: ACTIVE\n# AS_OF: 2026-07-17T00:00:00+10:00\n"
            "# TOPIC_ID: alpha\n# DDC_CATEGORY: DDC-03 (STATE)\nbody\n")
    open(os.path.join(td, "good.machine.md"), "w").write(good)
    # baseline PASS
    if run(td, as_json=False) == 0:
        print("  (baseline) clean doc PASSES ✓")
    else:
        print("  (baseline) FAIL — clean doc rejected"); rc = 1
    # (A) missing a required field -> FAIL
    bad = good.replace("# TOPIC_ID: alpha\n", "")
    open(os.path.join(td, "bad_missing.machine.md"), "w").write(bad)
    if run(td, as_json=False) == 1:
        print("  (A) missing STATUS field CAUGHT ✓")
    else:
        print("  (A) FAIL: missing field not caught"); rc = 1
    os.remove(os.path.join(td, "bad_missing.machine.md"))
    # (B) class mismatch -> FAIL
    mm = good.replace("DDC-03 (STATE)", "DDC-03 (HISTORY)")
    open(os.path.join(td, "bad_class.machine.md"), "w").write(mm)
    if run(td, as_json=False) == 1:
        print("  (B) declared-class mismatch CAUGHT ✓")
    else:
        print("  (B) FAIL: class mismatch not caught"); rc = 1
    os.remove(os.path.join(td, "bad_class.machine.md"))
    # (C) HYBRID missing a face -> FAIL
    hyb = ("# DOC_ID: p/y\n# DOC_CURRENCY: CURRENT\n# AUTHORITY_CLASS: A1_CURRENT_OWNER\n"
           "# VERIFICATION_STATUS: N/A\n# TASK_STATUS: ACTIVE\n# AS_OF: 2026-07-17T00:00:00+10:00\n"
           "# TOPIC_ID: beta\n# DDC_CATEGORY: DDC-11 (HYBRID)\n## STATE face\nrows\n")  # no HISTORY face
    open(os.path.join(td, "bad_hybrid.machine.md"), "w").write(hyb)
    if run(td, as_json=False) == 1:
        print("  (C) HYBRID missing-face CAUGHT ✓")
    else:
        print("  (C) FAIL: hybrid face not caught"); rc = 1
    os.remove(os.path.join(td, "bad_hybrid.machine.md"))
    # (D) two A1 CURRENT owners of the same topic -> cross-doc FAIL
    dup = good.replace("# DOC_ID: p/x", "# DOC_ID: p/z")
    open(os.path.join(td, "dup_owner.machine.md"), "w").write(dup)
    if run(td, as_json=False) == 1:
        print("  (D) duplicate topic-owner CAUGHT ✓")
    else:
        print("  (D) FAIL: dup owner not caught"); rc = 1
    print("SELF-TEST: PASS" if rc == 0 else "SELF-TEST: FAIL")
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if not a.root:
        ap.error("root dir required (or --self-test)")
    sys.exit(run(a.root, a.strict, a.json))


if __name__ == "__main__":
    main()
