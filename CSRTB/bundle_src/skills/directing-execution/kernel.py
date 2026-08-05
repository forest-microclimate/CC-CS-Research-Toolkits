# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""directing-execution kernel sidecar -- the two-receipts stop gate.

Closes SEED-19 (killing running subagents against user intent). The recorded shape:
a lead stopped children the user wanted finished, then mischaracterised the child as
having saved nothing -- BEFORE checking. Recovery found the artifacts existed. Two
distinct receipts were absent at the stop moment, so the gate demands exactly those two:

  1. user_intent_ref  -- the recorded user intent / plan clause AUTHORIZING this stop.
  2. artifacts_read   -- evidence the child's OWN saved artifacts were READ (ids/paths
                         + a one-line summary each), or an explicit, verified
                         "child produced no artifacts: <how verified>" declaration.

FAIL-CLOSED: missing or empty either receipt => FAIL. The standing instruction on every
FAIL is `default = let children finish` -- a stop that discards a finished result is
unrecoverable, so absence of evidence resolves toward NOT stopping.

MECHANICAL, not exhortation: confirm_before_stop() returns a verdict dict and emits
`[[stop_gate child=<name> verdict=...]]`. The marker is the auditable object -- Claude
Science has no hooks, so this is `[DISCRETION]`-fired by the PLANNER profile's stop
mandate and its ABSENCE on a stopping span is Reviewer-flaggable (stop_gate_verdict()
reads a transcript for exactly that).

HONEST SCOPE (verification_status of the gate itself: fixtures-verified for FORM only).
The gate checks that the receipts are PRESENT, REFERENTIAL, and SUBSTANTIVE. It cannot
verify that the named artifacts were truly read or that the cited intent truly says what
the caller claims -- no in-process check can. What it removes is the un-receipted stop
and the bare "it saved nothing" assertion that SEED-19 actually consisted of.

Host-independent, stdlib-only, Python 3.9+. Library use NEVER calls sys.exit; only main()
does (exit 0 PASS / 2 FAIL). The bottom `__main__` guard was removed so the sidecar-publish
gate accepts this file, so exec()/import defines the API without firing the CLI -- call
main() explicitly (e.g. `python3 -c 'import kernel; kernel.main()' < case.json`) to run it.
"""
import argparse
import json
import os
import re
import sys

STANDING_INSTRUCTION = "default = let children finish"

STOP_GATE_MARKER_RE = r"\[\[stop_gate child=(\S+) verdict=(PASS|FAIL)\]\]"

# The "no artifacts" escape hatch. It MUST carry how that was verified: asserting a child
# saved nothing without checking IS the SEED-19 defect, so a bare token is not a receipt.
# Pattern kept as a top-level LITERAL and compiled lazily in no_artifacts_re(): the
# sidecar-publish gate rejects a computed value (re.compile) at module top level.
NO_ARTIFACTS_PATTERN = r"^\s*child\s+produced\s+no\s+artifacts\s*:\s*(.+)$"

# Matched against the WHOLE normalized receipt, never as a substring -- so a real
# reference that merely contains the word "none" is not rejected. A set literal (not
# frozenset(...)) so module top level holds no computed value; membership is identical.
PLACEHOLDER_TOKENS = {
    "", "-", "--", "?", "n/a", "na", "none", "nil", "null", "nothing", "no", "no artifacts",
    "tbd", "todo", "unknown", "unspecified", "assumed", "presumably", "obvious", "self-evident",
}

MIN_REF_CHARS = 3       # a plan-clause reference can be as terse as "4.2"; shorter is noise
MIN_SUMMARY_CHARS = 8   # "ok" / "read" is not evidence that an artifact was read

# Ordered longest-first so " -- " wins over " - " at the same offset.
SPLITTERS_ = (" -- ", "—", "–", " | ", "\t", ": ", " - ")

RECEIPTS_ = ("user_intent_ref", "artifacts_read")

# Lazy-compile cache. Module top level may hold no computed value, so a compiled regex
# lives behind an accessor that compiles on first call and memoizes here (plain-name
# dict literal -- gate-safe). See no_artifacts_re().
de_cache = {}


def no_artifacts_re():
    """Lazily compile + cache NO_ARTIFACTS_PATTERN with the frozen flags re.I | re.S.
    Kept out of module top level because the sidecar-publish gate forbids a computed
    (re.compile) value there; behaviour is identical to the old module-level constant."""
    if "no_artifacts_re" not in de_cache:
        de_cache["no_artifacts_re"] = re.compile(NO_ARTIFACTS_PATTERN, re.I | re.S)
    return de_cache["no_artifacts_re"]


# ------------------------------------------------------------------ text normalization
def flatten_(value):
    """Flatten a receipt value to one string. None / booleans / empties -> ''."""
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts = [str(value[k]).strip() for k in sorted(value) if str(value.get(k) or "").strip()]
        return " ".join(parts).strip()
    if isinstance(value, (list, tuple)):
        return " ".join(p for p in (flatten_(v) for v in value) if p).strip()
    return str(value).strip()


def normalize_(text):
    """Casefold + collapse whitespace + strip edge punctuation. Used ONLY for the
    placeholder comparison -- the value reported back is always the caller's own."""
    s = re.sub(r"\s+", " ", str(text or "")).strip().casefold()
    return s.strip(" .,;:!\"'`()[]")


def is_placeholder_(text):
    return normalize_(text) in PLACEHOLDER_TOKENS


def split_ref_summary_(text):
    """Split 'art_123 -- what it contains' into (ref, summary) at the EARLIEST splitter."""
    s = str(text or "").strip()
    best = None
    for sp in SPLITTERS_:
        i = s.find(sp)
        if i > 0 and (best is None or i < best[0]):
            best = (i, sp)
    if best is None:
        return s, ""
    i, sp = best
    return s[:i].strip(), s[i + len(sp):].strip()


# ------------------------------------------------------------------ the marker
def stop_gate_marker(child, verdict):
    """Render the machine-detectable tell, exactly `[[stop_gate child=X verdict=Y]]`.

    The child token is squeezed to whitespace-free so the marker stays greppable as one
    line; the unsquashed name is carried in the result dict."""
    if verdict not in ("PASS", "FAIL"):
        raise ValueError("verdict must be PASS or FAIL, got %r" % (verdict,))
    tok = re.sub(r"[\s\[\]]+", "_", str(child or "").strip()) or "<unnamed>"
    return "[[stop_gate child=%s verdict=%s]]" % (tok, verdict)


def stop_gate_parse_marker(text, child=None):
    """Find emitted markers in a transcript. Returns [{child, verdict, raw}].
    A marker preceded by a quote char is string DATA (a doc showing the format), not an
    emission -- so documentation never reads as having fired."""
    out = []
    if not text:
        return out
    for m in re.finditer(STOP_GATE_MARKER_RE, text):
        i = m.start()
        if i > 0 and text[i - 1] in ("'", '"', "`"):
            continue
        rec = {"child": m.group(1), "verdict": m.group(2), "raw": m.group(0)}
        if child is None or rec["child"] == child:
            out.append(rec)
    return out


def stop_gate_verdict(text, child=None):
    """Three-way, never a bool: MARKER_ABSENT / PASS / FAIL.

    MARKER_ABSENT means the gate did not demonstrably run -- it is NOT a pass. That is the
    Reviewer-flaggable state on a span where a stop happened. A FAIL anywhere dominates."""
    ms = stop_gate_parse_marker(text, child=child)
    if not ms:
        return "MARKER_ABSENT"
    return "FAIL" if any(r["verdict"] == "FAIL" for r in ms) else "PASS"


# ------------------------------------------------------------------ receipt 1: user intent
def check_user_intent_ref(value):
    """Receipt 1 -- a reference to the recorded user intent / plan clause authorizing
    the stop. Returns {ok, value, detail}."""
    text = flatten_(value)
    out = {"ok": False, "value": text, "detail": ""}
    if not text:
        out["detail"] = ("no reference to recorded user intent or a plan clause authorizing "
                         "this stop was supplied (cite the message/clause that says stop)")
        return out
    if is_placeholder_(text):
        out["detail"] = "%r is a placeholder, not a reference to recorded intent" % (text,)
        return out
    if len(text) < MIN_REF_CHARS:
        out["detail"] = "%r is too short to be a reference (< %d chars)" % (text, MIN_REF_CHARS)
        return out
    out["ok"] = True
    return out


# ------------------------------------------------------------------ receipt 2: artifacts read
def entry_ref_summary_(entry):
    """Resolve one artifacts_read entry to (ref, summary)."""
    if isinstance(entry, dict):
        ref = ""
        for k in ("id", "artifact_id", "version_id", "path", "ref", "name"):
            if str(entry.get(k) or "").strip():
                ref = str(entry[k]).strip()
                break
        summary = ""
        for k in ("summary", "note", "read", "detail", "description", "contents"):
            if str(entry.get(k) or "").strip():
                summary = str(entry[k]).strip()
                break
        return ref, summary
    return split_ref_summary_(flatten_(entry))


def check_artifacts_read(value):
    """Receipt 2 -- evidence the child's OWN saved artifacts were read.

    Accepts a list of "id/path -- one-line summary" strings or {id, summary} dicts, or the
    explicit "child produced no artifacts: <how verified>" declaration. Returns
    {ok, mode, entries, defects, detail}; mode in absent|none-declared|read."""
    out = {"ok": False, "mode": "absent", "entries": [], "defects": [], "detail": ""}
    raw = value if isinstance(value, (list, tuple)) else ([] if value is None else [value])
    raw = [e for e in raw if flatten_(e)]

    if not raw:
        out["detail"] = ("no read-receipt supplied -- list the child's saved artifacts "
                         "(id/path + a one-line summary of what each holds), or state "
                         "'child produced no artifacts: <how verified>'. Concluding a child "
                         "saved nothing WITHOUT reading is the recorded SEED-19 defect")
        return out

    declared_none = [e for e in raw if isinstance(e, str) and no_artifacts_re().match(e)]
    if declared_none and len(raw) > 1:
        out["mode"] = "none-declared"
        out["detail"] = ("contradictory receipt: a 'child produced no artifacts' declaration "
                         "was supplied alongside %d listed artifact(s)" % (len(raw) - 1))
        return out
    if declared_none:
        out["mode"] = "none-declared"
        how = no_artifacts_re().match(declared_none[0]).group(1).strip()
        if is_placeholder_(how) or len(how) < MIN_SUMMARY_CHARS:
            out["detail"] = ("the 'no artifacts' declaration must state HOW that was verified "
                             "(e.g. 'host.frames(fid) shows artifacts_created == []'); %r is a "
                             "bare assertion, which is exactly the SEED-19 defect" % (how,))
            return out
        out["entries"] = [{"ref": "<none>", "summary": how}]
        out["detail"] = ("no-artifacts declared, verified by: %s (HOT PATH -- the recorded "
                         "defect lives here; a Reviewer should re-read it)" % how)
        out["ok"] = True
        return out

    out["mode"] = "read"
    for i, entry in enumerate(raw):
        ref, summary = entry_ref_summary_(entry)
        if not ref:
            out["defects"].append("entry %d: no artifact id/path" % i)
            continue
        if not summary:
            out["defects"].append("entry %d (%s): no one-line summary -- a bare id is a "
                                  "pointer, not evidence it was read" % (i, ref))
            continue
        if len(summary) < MIN_SUMMARY_CHARS or is_placeholder_(summary):
            out["defects"].append("entry %d (%s): summary %r is too thin to be a read-receipt"
                                  % (i, ref, summary))
            continue
        if normalize_(summary) == normalize_(ref):
            out["defects"].append("entry %d (%s): summary merely repeats the reference" % (i, ref))
            continue
        out["entries"].append({"ref": ref, "summary": summary})

    if out["defects"]:
        out["detail"] = "%d of %d entries are not read-receipts: %s" % (
            len(out["defects"]), len(raw), "; ".join(out["defects"]))
        return out
    out["detail"] = "%d artifact(s) read: %s" % (
        len(out["entries"]), ", ".join(e["ref"] for e in out["entries"]))
    out["ok"] = True
    return out


# ------------------------------------------------------------------ the gate
def render_stop_report(result):
    """Human/machine-readable block: marker first, then the operative reason(s)."""
    lines = [result["marker"]]
    if result["verdict"] == "PASS":
        lines.append("STOP AUTHORIZED -- both receipts present for child %r."
                     % (result["child"],))
        lines.append("  user_intent_ref: %s" % result["receipts"]["user_intent_ref"]["value"])
        lines.append("  artifacts_read : %s" % result["receipts"]["artifacts_read"]["detail"])
    else:
        lines.append("STOP BLOCKED -- missing receipt(s): %s" % ", ".join(result["missing"]))
        for r in result["reasons"]:
            lines.append("  - %s" % r)
    lines.append("STANDING INSTRUCTION: %s." % STANDING_INSTRUCTION)
    return "\n".join(lines)


def confirm_before_stop(child, user_intent_ref=None, artifacts_read=None):
    """THE GATE. Run it BEFORE any host.stop_child; no receipts => no stop.

    PASS only when BOTH (1) user_intent_ref is a non-empty reference to recorded user
    intent or a plan clause authorizing the stop, AND (2) artifacts_read is non-empty
    evidence the child's saved artifacts were READ. Missing/empty either => FAIL carrying
    the reason and the standing instruction `default = let children finish`.

    Returns {verdict, missing, marker, child, reasons, standing_instruction, receipts,
    report}. Never raises on a bad case and never calls sys.exit -- a FAIL is data, so the
    caller can print it and keep directing (require_confirm_before_stop raises instead)."""
    missing = []
    reasons = []

    child_txt = flatten_(child)
    if not child_txt or is_placeholder_(child_txt):
        # Fail-closed extension: a stop whose target is unnamed cannot have had its
        # artifacts read, and its marker would be unattributable in the trail.
        missing.append("child")
        reasons.append("child: the frame/child being stopped is not named")

    intent = check_user_intent_ref(user_intent_ref)
    if not intent["ok"]:
        missing.append("user_intent_ref")
        reasons.append("user_intent_ref: %s" % intent["detail"])

    arts = check_artifacts_read(artifacts_read)
    if not arts["ok"]:
        missing.append("artifacts_read")
        reasons.append("artifacts_read: %s" % arts["detail"])

    verdict = "FAIL" if missing else "PASS"
    result = {
        "verdict": verdict,
        "missing": missing,
        "marker": stop_gate_marker(child_txt, verdict),
        "child": child_txt or None,
        "reasons": reasons,
        "standing_instruction": STANDING_INSTRUCTION,
        "receipts": {"user_intent_ref": intent, "artifacts_read": arts},
    }
    result["report"] = render_stop_report(result)
    return result


def require_confirm_before_stop(child, user_intent_ref=None, artifacts_read=None):
    """Strict wrapper: RAISES AssertionError on FAIL, returns the result on PASS.
    Use where the stop is scripted and a returned FAIL could be ignored."""
    result = confirm_before_stop(child, user_intent_ref, artifacts_read)
    if result["verdict"] != "PASS":
        raise AssertionError(result["report"])
    return result


# ------------------------------------------------------------------ CLI (exit 0 PASS / 2 FAIL)
def main(argv=None):
    """JSON in, JSON out. Malformed input is FAIL (exit 2), never a pass."""
    ap = argparse.ArgumentParser(
        prog="kernel.py",
        description="two-receipts stop gate (SEED-19): confirm user intent + artifacts read "
                    "before stopping a child. Exit 0 = PASS, 2 = FAIL.")
    ap.add_argument("-i", "--input", default="-",
                    help="JSON object {child, user_intent_ref, artifacts_read}; '-' = stdin")
    ap.add_argument("-q", "--quiet", action="store_true", help="print only the marker line")
    args = ap.parse_args(argv)
    try:
        if args.input == "-":
            raw = sys.stdin.read()
        else:
            with open(args.input, encoding="utf-8") as fh:
                raw = fh.read()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("input JSON must be an object")
    except Exception as exc:
        err = {"verdict": "FAIL", "missing": ["input"],
               "marker": stop_gate_marker("<unparsed>", "FAIL"),
               "child": None, "reasons": ["input: %s: %s" % (type(exc).__name__, exc)],
               "standing_instruction": STANDING_INSTRUCTION}
        err["report"] = render_stop_report(err)
        sys.stdout.write((err["marker"] if args.quiet
                          else json.dumps(err, indent=2, sort_keys=True)) + "\n")
        return 2
    result = confirm_before_stop(payload.get("child"), payload.get("user_intent_ref"),
                                 payload.get("artifacts_read"))
    sys.stdout.write((result["marker"] if args.quiet
                      else json.dumps(result, indent=2, sort_keys=True)) + "\n")
    return 0 if result["verdict"] == "PASS" else 2


def is_script_run_():
    """True ONLY when this file was executed as a script.

    RETAINED but currently UNUSED: the bottom `if __name__ == "__main__"` guard that used
    to call this was removed because the sidecar-publish gate forbids a top-level `if`. Kept
    (renamed, underscore-free) so a guarded entry point can be reintroduced without rewriting
    it. The documented load path is exec(host.skills.read("directing-execution",
    "kernel.py")["content"]) inside a repl cell, where __name__ is ALSO "__main__" -- a bare
    __name__ guard would fire main() and block on stdin every time the skill loads. Compare
    the running script to this file instead; under exec() there is no __file__."""
    try:
        this = os.path.realpath(__file__)
    except NameError:
        return False
    argv0 = sys.argv[0] if sys.argv else ""
    return bool(argv0) and os.path.realpath(argv0) == this
