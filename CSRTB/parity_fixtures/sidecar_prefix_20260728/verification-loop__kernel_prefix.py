# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""verification-loop kernel sidecar -- the claim-vs-record check.

Closes failure families F1+F2+F3 (assertion-without-verification, prose/artifact
drift, stale-state) = 53% of 76 mined failures, one meta-pattern: asserting a
state without checking it against the ground-truth record.

MECHANICAL, not exhortation: verify_claims() RAISES on mismatch. A skill that
calls it has a real loop; a SKILL.md paragraph telling the agent to self-check
is model discretion. PASS is the definition of "done".
"""
import hashlib
import json
import os
import re
import sys

VLOOP_TAGS = ("count-over-artifact", "field-value", "state")
VLOOP_MARKER_RE = r"\[\[vloop:([A-Za-z0-9_.\-]+)((?:\s+[a-z_]+=-?\d+)*)\s*\]\]"


def vloop_marker(name, n_claims, n_fail, **extra):
    """Render the machine-detectable tell. Grep target for verify-the-embed."""
    if not re.fullmatch(r"[A-Za-z0-9_.\-]+", str(name) or ""):
        raise ValueError("marker name must match [A-Za-z0-9_.-]+, got %r" % (name,))
    parts = ["n_claims=%d" % int(n_claims), "n_fail=%d" % int(n_fail)]
    for k in sorted(extra):
        parts.append("%s=%d" % (k, int(extra[k])))
    return "[[vloop:%s %s]]" % (name, " ".join(parts))


def vloop_parse_marker(text, name=None):
    """Find markers in text. Returns [{name, n_claims, n_fail, raw}].
    A marker preceded by a quote char is string DATA (a doc mentioning the
    format), not an emission -- so documentation never reads as having fired."""
    out = []
    if not text:
        return out
    for m in re.finditer(VLOOP_MARKER_RE, text):
        i = m.start()
        if i > 0 and text[i - 1] in ("'", '"', "`"):
            continue
        rec = {"name": m.group(1), "raw": m.group(0)}
        for k, v in re.findall(r"([a-z_]+)=(-?\d+)", m.group(2) or ""):
            rec[k] = int(v)
        if name is None or rec["name"] == name:
            out.append(rec)
    return out


def vloop_verdict(text, name=None):
    """Three-way, never a bool: MARKER_ABSENT / CLEAN / DEFECTS.
    MARKER_ABSENT means the check did not demonstrably run -- it is NOT a pass.
    Collapsing it into CLEAN is the false-green this module exists to prevent."""
    ms = vloop_parse_marker(text, name=name)
    if not ms:
        return "MARKER_ABSENT"
    worst = max(ms, key=lambda r: r.get("n_fail", 0))
    if "n_fail" not in worst:
        return "MARKER_ABSENT"
    return "DEFECTS" if worst["n_fail"] >= 1 else "CLEAN"


def vloop_normalize(value, mode=None):
    """The DECLARED normalization. Comparison is only deterministic if the
    normalization is named, so every predicate states its mode explicitly."""
    if mode is None:
        mode = "exact"
    if value is None:
        return None
    s = str(value)
    if mode == "exact":
        return s
    if mode == "strip":
        return s.strip()
    if mode == "casefold":
        return s.strip().casefold()
    if mode == "collapse-space":
        return re.sub(r"\s+", " ", s).strip()
    if mode == "numeric":
        t = s.strip().replace(",", "")
        return repr(float(t))
    if mode == "sha256":
        return hashlib.sha256(s.encode("utf-8")).hexdigest()
    raise ValueError("unknown normalization mode %r (declare one of: exact, strip, "
                     "casefold, collapse-space, numeric, sha256)" % (mode,))


def vloop_count_over_artifact(path, pattern=None, mode=None):
    """count-over-artifact recompute: len(lines) or grep-count over a REAL file."""
    if not os.path.exists(path):
        raise FileNotFoundError("source not resolvable: %s" % path)
    # DIRECTORY sources: count entries (immediate children, or pattern-matching names).
    # ADDED 2026-07-24: this skill's own documented Usage example passes a directory
    # ("count the staged skill dirs"), and the CCRT hook already handled that case, so the
    # kernel raised IsADirectoryError on the very example it ships. A doc example that
    # cannot run is the same assert-without-checking failure this skill exists to close.
    if os.path.isdir(path):
        names = sorted(n for n in os.listdir(path) if not n.startswith("."))
        if pattern is None:
            return len(names)
        flags = re.I if mode == "casefold" else 0
        return len([n for n in names if re.search(pattern, n, flags)])
    if str(path).endswith((".json",)) and pattern is None:
        with open(path, encoding="utf-8") as fh:
            obj = json.load(fh)
        return len(obj)
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    if pattern is None:
        return sum(1 for ln in text.splitlines() if ln.strip())
    flags = re.I if mode == "casefold" else 0
    return len(re.findall(pattern, text, flags))


def vloop_field_value(path, field, mode=None):
    """field-value recompute: parse one field out of a JSON source."""
    if not os.path.exists(path):
        raise FileNotFoundError("source not resolvable: %s" % path)
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    cur = obj
    for part in str(field).split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return vloop_normalize(cur, mode)


def vloop_check_claim(claim):
    """Resolve ONE tagged claim to a verdict row.

    claim = {tag, source, asserted, [pattern], [field], [normalize], [observed], [id]}
    Returns {id, tag, source, recomputed, asserted, normalize, verdict, detail}.
    """
    tag = claim.get("tag")
    out = {"id": claim.get("id"), "tag": tag, "source": claim.get("source"),
           "asserted": claim.get("asserted"), "normalize": claim.get("normalize") or "exact",
           "recomputed": None, "verdict": "FAIL", "detail": ""}
    if tag not in VLOOP_TAGS:
        out["detail"] = ("tag %r is not in the closed taxonomy %s -- free-prose "
                         "assertions with no machine-resolvable source are OUT OF "
                         "SCOPE by design and must not be tagged"
                         % (tag, list(VLOOP_TAGS)))
        return out
    try:
        if tag == "count-over-artifact":
            got = vloop_count_over_artifact(claim["source"], claim.get("pattern"),
                                           claim.get("normalize"))
            exp = int(claim["asserted"])
            out["recomputed"] = got
            out["verdict"] = "PASS" if got == exp else "FAIL"
            if got != exp:
                out["detail"] = "recomputed %d != asserted %d" % (got, exp)
        elif tag == "field-value":
            got = vloop_field_value(claim["source"], claim["field"], claim.get("normalize"))
            exp = vloop_normalize(claim["asserted"], claim.get("normalize"))
            out["recomputed"] = got
            out["verdict"] = "PASS" if got == exp else "FAIL"
            if got != exp:
                out["detail"] = "recomputed %r != asserted %r" % (got, exp)
        else:
            if "observed" not in claim:
                out["detail"] = ("state claim requires an `observed` value from a real "
                                 "rerun of the entrypoint -- an unobserved state claim "
                                 "cannot be verified and must not pass")
                return out
            got = vloop_normalize(claim["observed"], claim.get("normalize"))
            exp = vloop_normalize(claim["asserted"], claim.get("normalize"))
            out["recomputed"] = got
            out["verdict"] = "PASS" if got == exp else "FAIL"
            if got != exp:
                out["detail"] = "observed %r != asserted %r" % (got, exp)
    except Exception as exc:
        out["detail"] = "%s: %s" % (type(exc).__name__, exc)
    return out


def vloop_render_table(rows):
    """The enumerated claims table. Emitting it is what makes an empty
    extraction VISIBLE rather than a silent green."""
    head = "| id | tag | source | recomputed | asserted | norm | verdict |"
    sep = "|---|---|---|---|---|---|---|"
    body = []
    for r in rows:
        body.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            r.get("id") or "-", r.get("tag") or "-", r.get("source") or "-",
            r.get("recomputed"), r.get("asserted"), r.get("normalize"), r.get("verdict")))
    return "\n".join([head, sep] + body)


def verify_claims(claims, name=None, durable_output=None, strict=None,
                  allow_empty=None):
    """THE MECHANICAL ASSERTION. Call it; PASS is the definition of done.

    RAISES AssertionError when any tagged claim mismatches, OR when the claim
    list is empty while `durable_output` is non-empty (the anti-vacuous rule:
    0 claims extracted from a non-empty output is a VISIBLE failure, not a
    silent pass). Returns {marker, table, rows, n_claims, n_fail} on success.
    """
    if name is None:
        name = "claims"
    if strict is None:
        strict = True
    rows = [vloop_check_claim(c) for c in (claims or [])]
    n_fail = sum(1 for r in rows if r["verdict"] != "PASS")
    table = vloop_render_table(rows)
    if allow_empty is None:
        allow_empty = False
    # ADVERSARIAL FIX 2026-07-24 (MAJOR): the vacuous guard used to fire ONLY when
    # the caller passed durable_output, so the natural minimal call verify_claims(x)
    # -- where x came from an extraction that silently returned [] (the F1 pattern
    # itself) -- returned a CLEAN marker. Now ANY empty claim list is vacuous unless
    # the caller explicitly asserts allow_empty=True. Fail-closed by default.
    vacuous = (not rows) and not allow_empty
    marker = vloop_marker(name, len(rows), n_fail + (1 if vacuous else 0))
    result = {"marker": marker, "table": table, "rows": rows,
              "n_claims": len(rows), "n_fail": n_fail, "vacuous": bool(vacuous)}
    if vacuous:
        raise AssertionError(
            "%s\nVACUOUS CHECK: 0 claims enumerated (%s). An empty claims table is a "
            "visible failure, not a pass -- "
            "tag the claims, or pass allow_empty=True to assert on the record that "
            "this output genuinely makes no recomputable claim."
            % (marker, ("%d chars" % len(str(durable_output))) if durable_output
               else "no durable_output supplied"))
    if n_fail and not strict:
        # strict=False is a documented FOOTGUN: it downgrades a real mismatch to a
        # silent return, which is precisely the "wrap it in try/except" move the
        # skill body forbids. It stays available for gate self-testing only, and it
        # complains on stderr so a non-raising run is never silent.
        sys.stderr.write("verify_claims: strict=False suppressed %d real "
                         "mismatch(es) -- %s\n" % (n_fail, marker))
    if n_fail and strict:
        bad = "\n".join("  - [%s] %s: %s" % (r.get("tag"), r.get("id") or "?", r.get("detail"))
                        for r in rows if r["verdict"] != "PASS")
        raise AssertionError("%s\nCLAIM-VS-RECORD MISMATCH (%d of %d):\n%s\n\n%s"
                             % (marker, n_fail, len(rows), bad, table))
    return result


# ═══════════════════════════════════════════════════════════════════════════
# EMIT-TIME ASSERTION GATES (append-only extension; nothing above is modified)
# ───────────────────────────────────────────────────────────────────────────
# Two RETURN-based verdict gates that carry two recorded record-integrity
# classes to the write point:
#   require_receipt(claim_text, receipts)   -> [[receipt_gate ...]]  DISC-07
#   require_verification_status(row)        -> [[vstatus_gate ...]]  DISC-18
# UNLIKE verify_claims (which RAISES), these RETURN {verdict, failures, marker,
# ...} and never raise or exit in library use. On Claude Science there is no
# turn hook, so in library use the firing point is [DISCRETION] and the emitted
# marker is the auditable object a Reviewer checks for (marker-absence == the
# check did not demonstrably run). The main() CLI below is the mechanical
# option: it maps a FAIL verdict to exit 2.
# A THIRD sibling gate -- verify_before_assert (SEED-01, assert-from-
# recollection) -- lives in the provenance-guard skill, not here; see its
# kernel. Do not re-add it to this module.
#
# Guard logic lives in these module-level constants so it is (a) auditable as
# data and (b) patchable by the mutation fixtures (fixtures_new_gates.py) with
# no edit to this shipped file.

# require_receipt -- DISC-07 verification-theater. Word-boundary, case-insensitive.
RECEIPT_TOKEN_RES = {
    "verified":       re.compile(r"\bverified\b", re.I),
    "passed":         re.compile(r"\bpassed\b", re.I),
    "byte-identical": re.compile(r"\bbyte[\s_\u2014\u2013-]?identical\b", re.I),
    "all-green":      re.compile(r"\ball\s+green\b", re.I),
    "all-N-passed":   re.compile(r"\ball[\s_-]+\d+[\s_-]+passed\b", re.I),
    "addressed":      re.compile(r"\baddressed\b", re.I),
    "reproduced":     re.compile(r"\breproduced\b", re.I),
    "confirmed":      re.compile(r"\bconfirmed\b", re.I),
}
VALID_RECEIPT_KINDS = frozenset({"hash", "diff", "exit_code", "read_ref", "test_tally"})

# require_verification_status -- DISC-18 efficacy-from-existence.
VALID_VSTATUS = frozenset({"verified-working", "attempted-untested", "unknown"})
VSTATUS_REQUIRE_CITATION = frozenset({"verified-working"})


def _blank(value):
    """True for None or a whitespace-only string. False/0/'0' are NOT blank."""
    return value is None or (isinstance(value, str) and not value.strip())


def _marker(gate, verdict, **counts):
    """Render the [[gate k=v ... verdict=X]] tell for the return-based gates.
    Counts render in call order (kwargs order, py3.7+), verdict last. Distinct
    from vloop_marker: these markers carry no `vloop:` prefix, so the existing
    vloop_parse_marker / vloop_verdict path never matches them."""
    parts = ["%s=%s" % (k, counts[k]) for k in counts]
    parts.append("verdict=%s" % verdict)
    return "[[%s %s]]" % (gate, " ".join(parts))


def require_receipt(claim_text, receipts):
    """DISC-07 gate: a verification TOKEN in claim_text needs a real RECEIPT.

    Detects verification tokens (verified, passed, byte-identical, all green,
    all-N-passed, addressed, reproduced, confirmed) in claim_text. When >=1 is
    present, at least one VALID receipt must back it. A receipt is valid iff it
    is a dict with kind in VALID_RECEIPT_KINDS and a non-blank value.

      >=1 token and 0 valid receipts -> FAIL (verification theater), naming tokens
      0 tokens                       -> PASS, vacuous=True (nothing was claimed)
      >=1 token and >=1 valid receipt -> PASS

    Returns {gate, verdict, tokens, receipts_supplied, receipts_valid, failures,
    notes, vacuous, marker}. Never raises; never exits.
    """
    if isinstance(claim_text, str):
        text = claim_text
    elif claim_text is None:
        text = ""
    else:
        text = str(claim_text)
    found = [name for name, rx in RECEIPT_TOKEN_RES.items() if rx.search(text)]

    notes = []
    if isinstance(receipts, (list, tuple)):
        supplied = list(receipts)
    else:
        supplied = []
        if receipts is not None:
            notes.append("receipts is %s, expected a list -- treated as empty "
                         "(fail-closed)" % type(receipts).__name__)
    valid = 0
    for i, r in enumerate(supplied):
        if not isinstance(r, dict):
            notes.append("receipt #%d is %s, not a {kind, value} object"
                         % (i, type(r).__name__))
            continue
        kind = str(r.get("kind") or "").strip().lower()
        if kind not in VALID_RECEIPT_KINDS:
            notes.append("receipt #%d kind %r not in %s"
                         % (i, r.get("kind"), sorted(VALID_RECEIPT_KINDS)))
            continue
        if _blank(r.get("value")):
            notes.append("receipt #%d (kind=%s) has a blank value" % (i, kind))
            continue
        valid += 1

    failures = []
    vacuous = not found
    if found and valid == 0:
        failures.append({
            "check": "no-receipt", "tokens": found,
            "detail": "claim asserts verification token(s) %s but no valid receipt "
                      "(kind in %s) backs it -- verification theater (DISC-07)"
                      % (found, sorted(VALID_RECEIPT_KINDS))})
    verdict = "FAIL" if failures else "PASS"
    return {"gate": "require_receipt", "verdict": verdict, "tokens": found,
            "receipts_supplied": len(supplied), "receipts_valid": valid,
            "failures": failures, "notes": notes, "vacuous": bool(vacuous),
            "marker": _marker("receipt_gate", verdict, tokens=len(found), receipts=valid)}


def require_verification_status(row):
    """DISC-18 gate: a durable efficacy/behavior claim must carry an honest
    verification_status, and 'verified-working' must cite a measurement.

    PASS iff row['verification_status'] (strip+casefold) is in VALID_VSTATUS
    AND, when it is in VSTATUS_REQUIRE_CITATION ('verified-working'), row carries
    a non-blank 'citation'. Missing/other status -> FAIL; verified-working with
    no citation -> FAIL (existence is not efficacy). A brand-new fix defaults to
    'attempted-untested'. Returns {gate, verdict, status, failures, marker}.
    Never raises; never exits.
    """
    failures = []
    if not isinstance(row, dict):
        failures.append({"check": "input",
                         "detail": "row is %s, expected a {verification_status, ...} "
                                   "object" % type(row).__name__})
        return {"gate": "require_verification_status", "verdict": "FAIL",
                "status": None, "failures": failures,
                "marker": _marker("vstatus_gate", "FAIL")}
    raw = row.get("verification_status")
    status = str(raw).strip().casefold() if raw is not None else ""
    if status not in VALID_VSTATUS:
        failures.append({"check": "status",
                         "detail": "verification_status %r is missing or not one of %s "
                                   "-- a durable efficacy/behavior claim defaults to "
                                   "'attempted-untested'" % (raw, sorted(VALID_VSTATUS))})
    elif status in VSTATUS_REQUIRE_CITATION and _blank(row.get("citation")):
        failures.append({"check": "citation",
                         "detail": "verification_status 'verified-working' requires a "
                                   "non-empty 'citation' (a measured before/after, "
                                   "ablation, or test) -- existence is not efficacy "
                                   "(DISC-18)"})
    verdict = "FAIL" if failures else "PASS"
    return {"gate": "require_verification_status", "verdict": verdict,
            "status": status or None, "failures": failures,
            "marker": _marker("vstatus_gate", verdict)}


# ─── CLI (the ONLY place that prints or exits) ───────────────────────────────
def _read_input(path):
    """Read the JSON payload text from a file path, or stdin for '-'/''/None."""
    if path in (None, "-", ""):
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main(argv=None):
    """argparse CLI -- one subcommand per gate, JSON in / JSON out, exit 0 PASS /
    2 FAIL. Mirrors the delegation-planning kernel's CLI contract and is the
    mechanical firing point Claude Science lacks a hook for. ADDED ADDITIVELY:
    importing this module never runs main(), so verify_claims and the vloop_*
    API are byte-for-byte unaffected. argparse is imported locally so the
    module's top-of-file import block is unchanged.

      verify-claims  claims JSON (list, or {"claims", "name", ...})  [verify_claims]
      receipt-gate   {"claim_text": str, "receipts": [...]}          [require_receipt]
      vstatus-gate   a claim row object                              [require_verification_status]
    """
    import argparse
    ap = argparse.ArgumentParser(
        prog="kernel.py",
        description="verification-loop gates: claim-vs-record + emit-time assertion gates")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("verify-claims",
                       help="verify_claims over a claim list (raises internally -> exit 2)")
    p.add_argument("-i", "--input", default="-", help="JSON file, or - for stdin")
    p.add_argument("--allow-empty", action="store_true",
                   help="assert on the record that the output makes no recomputable claim")

    p = sub.add_parser("receipt-gate",
                       help='require_receipt over {"claim_text": str, "receipts": [...]}')
    p.add_argument("-i", "--input", default="-", help="JSON file, or - for stdin")

    p = sub.add_parser("vstatus-gate",
                       help="require_verification_status over a claim row object")
    p.add_argument("-i", "--input", default="-", help="JSON file, or - for stdin")

    args = ap.parse_args(argv)
    try:
        raw = _read_input(args.input)
    except Exception as exc:
        print(json.dumps({"verdict": "FAIL", "failures": [
            {"check": "input", "detail": "%s: %s" % (type(exc).__name__, exc)}]}))
        return 2
    try:
        payload = json.loads(raw)
    except Exception as exc:
        print(json.dumps({"verdict": "FAIL", "failures": [
            {"check": "input", "detail": "payload is not JSON (%s: %s)"
             % (type(exc).__name__, exc)}]}))
        return 2

    if args.cmd == "receipt-gate":
        if isinstance(payload, dict):
            result = require_receipt(payload.get("claim_text"), payload.get("receipts"))
        else:
            result = require_receipt(payload, None)
        print(json.dumps(result, indent=2, sort_keys=True))
        print(result["marker"])
        return 0 if result["verdict"] == "PASS" else 2

    if args.cmd == "vstatus-gate":
        result = require_verification_status(payload)
        print(json.dumps(result, indent=2, sort_keys=True))
        print(result["marker"])
        return 0 if result["verdict"] == "PASS" else 2

    # verify-claims: verify_claims RAISES on mismatch/vacuous -> map to exit 2.
    if isinstance(payload, dict) and "claims" in payload:
        claims = payload.get("claims")
        name = payload.get("name")
        durable = payload.get("durable_output")
        allow_empty = bool(payload.get("allow_empty") or args.allow_empty)
    else:
        claims, name, durable, allow_empty = payload, None, None, args.allow_empty
    try:
        result = verify_claims(claims, name=name, durable_output=durable,
                               allow_empty=allow_empty)
    except AssertionError as exc:
        marker = str(exc).split("\n", 1)[0]
        print(json.dumps({"verdict": "FAIL", "marker": marker, "detail": str(exc)},
                         indent=2, sort_keys=True))
        print(marker)
        return 2
    except Exception as exc:
        print(json.dumps({"verdict": "FAIL", "failures": [
            {"check": "input", "detail": "%s: %s" % (type(exc).__name__, exc)}]}))
        return 2
    print(json.dumps({"verdict": "PASS", "marker": result["marker"],
                      "n_claims": result["n_claims"], "n_fail": result["n_fail"],
                      "table": result["table"]}, indent=2, sort_keys=True))
    print(result["marker"])
    return 0


def _vloop_is_script_run():
    """True only for a real CLI run — NOT an exec()-in-repl load (where __name__ is '__main__' but __file__/argv do not point here). Mirrors provenance-guard pg_is_script_run."""
    try:
        return os.path.basename(globals().get("__file__", "")) == os.path.basename(sys.argv[0])
    except Exception:
        return False


if __name__ == "__main__" and _vloop_is_script_run():
    sys.exit(main())
