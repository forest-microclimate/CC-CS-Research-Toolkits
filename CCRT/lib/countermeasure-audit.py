#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""countermeasure-audit.py — the MECHANICAL efficacy-measurement substrate for
COUNTERMEASURES_LEDGER.machine.md.

Every countermeasure in that ledger ships efficacy_status = attempted-untested;
upgrading it to verified-working requires a MEASUREMENT — an interrupted time-series
of the per-class instance rate, pre vs post ship. This script computes the MECHANICAL
INPUTS of that measurement. It ENUMERATES and COUNTS; it never GRADES. The JUDGEMENT
half (deciding whether a candidate transcript excerpt IS a failure-class instance, and
whether a countermeasure's efficacy actually improved) stays with the skill/LLM
reviewer. This script only produces, under --out:

  (1) rates.tsv        — gate/marker event counts from the three structured logs
                         (timeline · adversary-gate · claim-verify-guard), partitioned
                         pre/post by build_id (default) or a --since boundary; each row
                         notes the timeline/adversary `mode` (on|observe|...).
  (2) marker_usage.tsv — per-session counts of the wikilink-shaped audit markers the
                         gates emit (route_gate, plan_lint, stop_gate, receipt_gate,
                         assert_gate, vloop) plus plan_lint verdict/deny-reasons, swept
                         from the vault project transcripts.
  (3) candidates.jsonl — transcript excerpts that MATCH a built-in failure-class TELL
                         regex table. EVERY row is labeled a CANDIDATE, never an
                         instance: the table UNDER-APPROXIMATES by construction (a miss
                         is not evidence of absence) and exists only to feed the
                         JUDGEMENT half.
  (4) proposed_history_rows.md — a human-reviewed SKELETON of ledger-HISTORY append
                         lines carrying the counts above. The script NEVER writes the
                         ledger or FAILURE_CLASS_LOG itself (see the file's own header).

Read-only w.r.t. every input; it writes only its own reports under --out.

Sources (all OPTIONAL — a missing one is skipped with a note and the run still exits 0
with partial outputs):
  vault transcripts   <vault>/projects/*/*.jsonl     (default ~/.claude-vault/claude-home)
                      the purge-surviving mirror of the session records.
  structured logs     <logs>/timeline.jsonl, adversary-gate.jsonl, claim-verify-guard.log
                                                      (default ~/.claude/logs)
  ledger (class list) $CRT_REPO/analysis of failure modes and logical errors/
                      COUNTERMEASURES_LEDGER.machine.md, or an explicit --ledger.
                      NOT hardcoded to any absolute dev-mirror path — resolved from the
                      CRT_REPO environment variable, or passed explicitly.

--since <ISO date | build_id> is a PARTITION BOUNDARY, not a filter: rows are labeled
  pre/post relative to it and BOTH arms are retained (an interrupted time-series needs
  both). A YYYY-MM-DD boundary compares against each log row's epoch; a build_id
  boundary uses the build_id's embedded -YYYYMMDD-HHMMSS timestamp. With no --since the
  partition column is the row's build_id itself.

Exit: 0 = ran (possibly with skipped sources and partial outputs).
      2 = an input the run cannot proceed without is unusable: an explicitly-passed
          --ledger that is not a readable file, or an --out dir that cannot be
          created/written.

Usage:
  python3 countermeasure-audit.py [--since ISO|build_id] [--vault DIR] [--logs DIR]
                                  [--ledger PATH] [--out DIR]
"""
import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import sys

# ─── DATA: the wikilink-shaped audit markers the CRT gates emit ─────────────────────
# The bracket-open is built from an ESCAPED half (_OB) so this source file never carries
# a literal letter-initial double-open-bracket — the dangling-wikilink shape the payload
# scrub gate (lib/scrub_verify.sh) forbids. These are the gates' own status tokens, not
# Obsidian links. Families listed by exact name, so unrelated tokens do NOT match.
_OB = r"\[\["                                   # a marker's opening bracket, escaped
MARKER_FAMILIES = ["route_gate", "plan_lint", "stop_gate",
                   "receipt_gate", "assert_gate", "vloop"]
# a family name is followed by a space / colon / pipe / slash / closing-bracket
MARKER_RE = re.compile(_OB + r"(" + "|".join(MARKER_FAMILIES) + r")[\s:|/\]]")
# plan_lint carries a verdict / deny-reason token, e.g. verdict=FAIL or verdict=FAIL(4)
PLAN_LINT_VERDICT_RE = re.compile(_OB + r"plan_lint[^\]]*verdict=([A-Za-z]+(?:\(\d+\))?)")

# ─── DATA: failure-class TELL regexes ───────────────────────────────────────────────
# UNDER-APPROXIMATES BY CONSTRUCTION. A match is a CANDIDATE for the JUDGEMENT half to
# grade, NEVER a confirmed instance; a miss is NOT evidence of absence. The `family`
# names the loose ledger failure-family the candidate would route to. Extend the table
# as new tells are learned — it is deliberately a small, legible data table, not a model.
TELLS = [
    # (family, class_hint, regex)  — matched case-insensitively
    ("refusal-handling", "content-safety-refusal",
     r"stop_reason\W{0,4}refusal|content[ -]safety[ -]filter|"
     r"potential prompt injection|model refused the request"),
    ("assert-from-memory", "from-recollection-confession",
     r"from memory|from recollection|answer(?:ed|ing) from memory|"
     r"I (?:invented|made up|fabricated|guessed)|"
     r"without (?:reading|checking|running) the|"
     r"I did(?:n't| not) (?:run|read|check|verify)"),
    ("fixture-theater", "verified-without-receipt",
     r"byte[- ]identical|bytewise identical|"
     r"verified.{0,24}(?:works|passing|green|clean)|"
     r"(?:passes|passed).{0,16}so it works"),
    ("reflexive-delegation", "delegate-then-self-ran",
     r"I(?:'ll| will| just)?\s+(?:do|run|handle|write) (?:it|this) myself|"
     r"instead of delegating|hand[- ]fl(?:y|ew|own|ies)|"
     r"ran it myself|re-?implement(?:ed)? by hand"),
]
TELL_RES = [(fam, hint, re.compile(rx, re.I)) for fam, hint, rx in TELLS]

LEDGER_REL = os.path.join("analysis of failure modes and logical errors",
                          "COUNTERMEASURES_LEDGER.machine.md")


# ─── helpers ────────────────────────────────────────────────────────────────────────
def die2(msg):
    sys.stderr.write("countermeasure-audit: ERROR: %s\n" % msg)
    sys.exit(2)


def _build_id_epoch_ms(bid):
    """A build_id's embedded -YYYYMMDD-HHMMSS as a local-time epoch (ms), or None."""
    m = re.search(r"-(\d{8})-(\d{6})$", bid or "")
    if not m:
        return None
    try:
        d = dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
        return d.timestamp() * 1000.0
    except Exception:
        return None


def _iso_z_epoch_ms(s):
    """An ISO-8601 UTC 'Z' timestamp (claim-verify-guard.log) as epoch ms, or None."""
    try:
        d = dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        return d.timestamp() * 1000.0
    except Exception:
        return None


def parse_since(s):
    """Return (since_epoch_ms|None, since_date_str|None, mode_label).

    mode_label ∈ {build_id (no boundary — partition by build_id),
                  date (YYYY-MM-DD boundary), build_id-boundary}."""
    if not s:
        return (None, None, "build_id")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        try:
            e = dt.datetime.strptime(s, "%Y-%m-%d").timestamp() * 1000.0
            return (e, s, "date")
        except Exception:
            return (None, None, "build_id")
    be = _build_id_epoch_ms(s)
    if be is not None:
        return (be, None, "build_id-boundary")
    sys.stderr.write("countermeasure-audit: WARNING: --since %r is neither a "
                     "YYYY-MM-DD date nor a build_id with a -YYYYMMDD-HHMMSS suffix; "
                     "falling back to build_id partition.\n" % s)
    return (None, None, "build_id")


def message_text(obj):
    """Extract readable text from a transcript row (message.content str-or-list)."""
    msg = obj.get("message")
    if isinstance(msg, dict):
        c = msg.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            parts = []
            for it in c:
                if isinstance(it, dict):
                    t = it.get("text")
                    if isinstance(t, str):
                        parts.append(t)
                    elif isinstance(it.get("content"), str):
                        parts.append(it["content"])
                elif isinstance(it, str):
                    parts.append(it)
            return "\n".join(parts)
    c = obj.get("content")
    return c if isinstance(c, str) else ""


def excerpt_of(text, m, width=300):
    """<=`width`-char whitespace-collapsed snippet centered on a TELL match."""
    start = max(0, m.start() - 80)
    seg = re.sub(r"\s+", " ", text[start:start + width]).strip()
    return seg[:width]


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def parse_ledger_classes(path):
    """Class ids from the ledger STATE face — the leading token of each ` | ` row."""
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#") or " | " not in line:
                continue
            head = line.split(" | ", 1)[0].strip()
            m = re.match(r"^([A-Z][A-Z0-9-]+)", head)
            if m:
                out.append(m.group(1))
    seen = set()
    return [c for c in out if not (c in seen or seen.add(c))]


# ─── rates: the three structured logs ───────────────────────────────────────────────
def collect_rates(logs_dir, since_epoch, skip):
    """Counter keyed (log, event, partition, mode) -> count, plus per-log row totals."""
    rates = collections.Counter()
    totals = {}

    def partition(epoch, build):
        if since_epoch is not None:
            if epoch is not None and epoch >= since_epoch:
                return "post"
            return "pre"
        return build or "(unstamped)"

    def add(log, event, epoch, build, mode):
        rates[(log, event or "?", partition(epoch, build), mode or "(unstamped)")] += 1

    # timeline.jsonl + adversary-gate.jsonl: JSONL with epoch_ms / event / build_id / mode
    for name, tag in (("timeline.jsonl", "timeline"),
                      ("adversary-gate.jsonl", "adversary")):
        p = os.path.join(logs_dir, name)
        if not os.path.isfile(p):
            skip.append("log %s absent (%s) — not counted" % (name, p))
            totals[tag] = 0
            continue
        rows = read_jsonl(p)
        totals[tag] = len(rows)
        for r in rows:
            add(tag, r.get("event"),
                r.get("epoch_ms") if isinstance(r.get("epoch_ms"), (int, float)) else None,
                r.get("build_id"), r.get("mode"))

    # claim-verify-guard.log: PLAIN TEXT — `<ISO-Z> claim-verify-guard: <TOKEN> ...`
    # (no build_id/mode fields; TOKEN ∈ BLOCK|PASS|INDETERMINATE). Currently often absent.
    cvg = os.path.join(logs_dir, "claim-verify-guard.log")
    if not os.path.isfile(cvg):
        skip.append("log claim-verify-guard.log absent (%s) — not counted" % cvg)
        totals["claim-verify-guard"] = 0
    else:
        n = 0
        cvg_re = re.compile(r"^(\S+)\s+claim-verify-guard:\s+([A-Za-z]+)")
        with open(cvg, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = cvg_re.match(line.strip())
                if not m:
                    continue
                n += 1
                add("claim-verify-guard", m.group(2).upper(),
                    _iso_z_epoch_ms(m.group(1)), None, None)
        totals["claim-verify-guard"] = n
    return rates, totals


# ─── markers + candidates: the vault transcripts ────────────────────────────────────
def sweep_vault(vault_dir, since_date_str, skip):
    """Return (marker Counter keyed (marker, session), candidate rows, sweep stats)."""
    markers = collections.Counter()
    candidates = []
    stats = {"projects": 0, "transcripts": 0}
    proj_root = os.path.join(vault_dir, "projects")
    if not os.path.isdir(proj_root):
        skip.append("vault absent (%s) — marker_usage + candidates empty" % proj_root)
        return markers, candidates, stats

    jfiles = sorted(glob.glob(os.path.join(proj_root, "*", "*.jsonl")))
    stats["transcripts"] = len(jfiles)
    stats["projects"] = len({os.path.dirname(j) for j in jfiles})
    if not jfiles:
        skip.append("vault has no project transcripts under %s — marker_usage + "
                    "candidates empty" % proj_root)
        return markers, candidates, stats

    for jf in jfiles:
        session = os.path.splitext(os.path.basename(jf))[0]
        with open(jf, encoding="utf-8", errors="replace") as fh:
            for i, raw in enumerate(fh, start=1):
                if not raw.strip():
                    continue
                obj = None
                try:
                    obj = json.loads(raw)
                except Exception:
                    obj = None
                # optional date window (transcripts carry no build_id): a YYYY-MM-DD
                # --since drops lines dated before it; parse-failed lines are kept.
                if since_date_str and obj is not None:
                    ts = obj.get("timestamp")
                    if isinstance(ts, str) and ts[:10] and ts[:10] < since_date_str:
                        continue
                # marker sweep on the raw line (robust to JSON-parse failure)
                for m in MARKER_RE.finditer(raw):
                    markers[(m.group(1), session)] += 1
                for vm in PLAN_LINT_VERDICT_RE.finditer(raw):
                    markers[("plan_lint:verdict=" + vm.group(1), session)] += 1
                # candidate mining needs clean text -> requires a parsed row
                if obj is None:
                    continue
                text = message_text(obj)
                if not text:
                    continue
                # mechanical structural fields (NOT a grade) so the JUDGEMENT half can
                # discount e.g. an adversary/guard sidechain PROMPT that merely quotes a
                # tell, vs the agent's own assistant-role confession of it.
                msg = obj.get("message")
                role = (msg.get("role") if isinstance(msg, dict) else None) or obj.get("type")
                is_side = bool(obj.get("isSidechain"))
                for fam, hint, rx in TELL_RES:
                    mm = rx.search(text)
                    if mm:
                        candidates.append({
                            "label": "candidate",          # NEVER an instance
                            "family": fam,
                            "class_hint": hint,
                            "session": session,
                            "line_no": i,
                            "role": role,
                            "is_sidechain": is_side,
                            "excerpt": excerpt_of(text, mm),
                        })
    return markers, candidates, stats


# ─── output writers ─────────────────────────────────────────────────────────────────
def write_rates(path, rates):
    with open(path, "w", encoding="utf-8") as f:
        f.write("log\tevent\tpartition\tmode\tcount\n")
        for (log, ev, part, mode), c in sorted(rates.items()):
            f.write("%s\t%s\t%s\t%s\t%d\n" % (log, ev, part, mode, c))


def write_markers(path, markers):
    with open(path, "w", encoding="utf-8") as f:
        f.write("marker\tsession\tcount\n")
        for (mk, sess), c in sorted(markers.items()):
            f.write("%s\t%s\t%d\n" % (mk, sess, c))


def write_candidates(path, candidates):
    rows = sorted(candidates, key=lambda r: (r["session"], r["line_no"], r["family"]))
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_proposed(path, classes, rates, markers, candidates, window_desc):
    adv = collections.Counter()
    for (log, ev, _p, _m), c in rates.items():
        if log == "adversary":
            adv[ev] += c
    marker_tot = collections.Counter()
    for (mk, _s), c in markers.items():
        marker_tot[mk] += c
    L = []
    L.append("# PROPOSED ledger-HISTORY append lines — REVIEW BEFORE PASTE")
    L.append("#")
    L.append("# SKELETON of MECHANICAL INPUTS for the countermeasure efficacy measurement.")
    L.append("# This script NEVER writes COUNTERMEASURES_LEDGER.machine.md or")
    L.append("# FAILURE_CLASS_LOG.machine.md. Those are THREE writes across TWO disciplines")
    L.append("#   (ledger STATE supersede-in-place · ledger HISTORY append · class-log append)")
    L.append("# and are not safely scriptable. A human/lead reviews these counts, GRADES the")
    L.append("# candidates (the JUDGEMENT half this script does not do), then pastes the")
    L.append("# finished HISTORY line by hand. Efficacy stays attempted-untested until a")
    L.append("# NAMED measurement (pre-vs-post instance rate) is filled in and cited.")
    L.append("")
    L.append("## Mechanical inputs (window: %s)" % window_desc)
    L.append("- adversary-gate events: "
             + (", ".join("%s=%d" % (k, adv[k]) for k in sorted(adv)) or "(none)"))
    L.append("- marker totals: "
             + (", ".join("%s=%d" % (k, marker_tot[k]) for k in sorted(marker_tot))
                or "(none)"))
    L.append("- transcript CANDIDATES (UNGRADED — for the JUDGEMENT half): %d"
             % len(candidates))
    L.append("")
    L.append("## Proposed per-class HISTORY rows")
    L.append("## (PROPOSED — fill the graded pre/post instance counts, then paste by hand)")
    for cid in (classes or ["<CLASS-ID>"]):
        L.append("PROPOSED %s: <YYYY-MM-DD> MEASURED %s instance rate pre=<n> post=<n> "
                 "(window %s); mechanical counts attached above; "
                 "efficacy attempted-untested -> <verdict>." % (cid, cid, window_desc))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


# ─── main ───────────────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="countermeasure-audit.py",
        description="Compute the mechanical inputs of the countermeasure efficacy "
                    "measurement (counts only; never grades).")
    ap.add_argument("--since", default=None,
                    help="pre/post partition boundary: a YYYY-MM-DD date or a build_id "
                         "(NOT a filter — both arms are kept). Default: partition by build_id.")
    ap.add_argument("--vault", default=os.path.expanduser("~/.claude-vault/claude-home"),
                    help="vault dir holding projects/*/*.jsonl (default ~/.claude-vault/claude-home)")
    ap.add_argument("--logs", default=os.path.expanduser("~/.claude/logs"),
                    help="dir with timeline.jsonl / adversary-gate.jsonl / claim-verify-guard.log "
                         "(default ~/.claude/logs)")
    ap.add_argument("--ledger", default=None,
                    help="COUNTERMEASURES_LEDGER.machine.md path (for the class list). "
                         "Default: resolved from $CRT_REPO; never a hardcoded absolute path.")
    ap.add_argument("--out", default="./countermeasure_audit_out",
                    help="output dir for the report files (default ./countermeasure_audit_out)")
    args = ap.parse_args(argv)

    skip = []

    # --out: create + probe writability, else exit 2.
    out = args.out
    try:
        os.makedirs(out, exist_ok=True)
        probe = os.path.join(out, ".write_probe")
        with open(probe, "w"):
            pass
        os.remove(probe)
    except Exception as e:
        die2("--out %r is not creatable/writable: %s" % (out, e))

    # --ledger: explicit+unreadable => exit 2; env/absent => graceful generic class list.
    classes = []
    if args.ledger is not None:
        if os.path.isfile(args.ledger) and os.access(args.ledger, os.R_OK):
            classes = parse_ledger_classes(args.ledger)
            ledger_note = "%s (%d classes)" % (args.ledger, len(classes))
        else:
            die2("--ledger %r is not a readable file" % args.ledger)
    else:
        repo = os.environ.get("CRT_REPO")
        cand = os.path.join(repo, LEDGER_REL) if repo else None
        if cand and os.path.isfile(cand) and os.access(cand, os.R_OK):
            classes = parse_ledger_classes(cand)
            ledger_note = "%s (%d classes, via $CRT_REPO)" % (cand, len(classes))
        else:
            ledger_note = "unresolved (no --ledger; $CRT_REPO %s) — class list generic" % (
                "unset" if not repo else "set but ledger not found")
            skip.append("ledger " + ledger_note)

    since_epoch, since_date_str, since_mode = parse_since(args.since)
    if since_mode == "date":
        window_desc = "pre/post @ %s (date)" % args.since
    elif since_mode == "build_id-boundary":
        window_desc = "pre/post @ build %s" % args.since
    else:
        window_desc = "partition=build_id (no --since)"

    rates, log_totals = collect_rates(args.logs, since_epoch, skip)
    markers, candidates, vstats = sweep_vault(args.vault, since_date_str, skip)

    p_rates = os.path.join(out, "rates.tsv")
    p_marks = os.path.join(out, "marker_usage.tsv")
    p_cands = os.path.join(out, "candidates.jsonl")
    p_prop = os.path.join(out, "proposed_history_rows.md")
    write_rates(p_rates, rates)
    write_markers(p_marks, markers)
    write_candidates(p_cands, candidates)
    write_proposed(p_prop, classes, rates, markers, candidates, window_desc)

    # ── stdout summary (also the skip report) ───────────────────────────────────────
    print("=== countermeasure-audit ===")
    print("window: %s" % window_desc)
    print("sources:")
    print("  logs:   timeline=%d  adversary=%d  claim-verify-guard=%d rows (%s)"
          % (log_totals.get("timeline", 0), log_totals.get("adversary", 0),
             log_totals.get("claim-verify-guard", 0), args.logs))
    print("  vault:  %d project(s), %d transcript(s) swept (%s)"
          % (vstats["projects"], vstats["transcripts"], args.vault))
    print("  ledger: %s" % ledger_note)
    print("outputs (under %s):" % out)
    print("  rates.tsv            %d event-rows" % len(rates))
    print("  marker_usage.tsv     %d marker-rows" % len(markers))
    print("  candidates.jsonl     %d CANDIDATE excerpt(s) — ungraded, for the JUDGEMENT half"
          % len(candidates))
    print("  proposed_history_rows.md   PROPOSED skeleton (script never writes the ledger)")
    if skip:
        print("skipped:")
        for s in skip:
            print("  - " + s)
    else:
        print("skipped: none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
