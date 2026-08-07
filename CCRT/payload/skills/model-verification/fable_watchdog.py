#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""fable_watchdog.py -- early serving-swap verdict for a claude-fable-5-pinned
subagent transcript, readable while the child is STILL RUNNING.

WHY (dev/reports/BUGREPORT_fable_substitution_v3_20260806.md +
dev/reports/V2_STAMP_TABLES.machine.md): a fable-resolved child is often silently
SERVED claude-opus-5 instead. In the current era the swap point is DETERMINISTIC at
call 4 (the first 3 assistant turns are genuinely fable-5, every turn from the 4th
on is opus-5) -- so a launch's fidelity is decidable from its first ~5 served-model
stamps instead of waiting out a full run (H1: 3 fable then 106 opus-5, over a
109-call run; this tool reaches the same verdict after 4 stamps, not 109).

WHAT: reads a child transcript's assistant turns in ORDER (mirroring, not
replacing, dev/tools/model_run_audit.py's per-line scan -- see CODE REUSE below),
compares the first --verdict-at served-model stamps against --expect, and prints
ONE verdict line + a matching exit code. One-shot by default (reads the file once,
as it stands right now); --watch polls a still-growing file until enough stamps
exist or --timeout elapses, so it can be pointed at a RUNNING child.

VERDICTS (stdout, exactly one line; exit code):
  FAITHFUL       exit 0  -- the first --verdict-at stamps all equal --expect.
  SWAPPED@k      exit 1  -- the first divergent stamp is call k (k <= --verdict-at);
                            prints BOTH the expected and the served id. Decided as
                            soon as a divergence is seen -- does not wait for
                            --verdict-at stamps to accumulate first.
  UNDETERMINED   exit 2  -- fewer than --verdict-at stamps were available when the
                            read stopped (one-shot: right now; --watch: by timeout),
                            OR the transcript has no assistant records at all, OR
                            every line in it failed to parse. Never a crash.

CODE REUSE (dev/briefs/W-W1-watchdog.md; dev/CODE_INVENTORY.machine.md read first):
  USE, verbatim, via import -- dev/tools/model_run_audit.py's normalize_model()
    (strips harness display suffixes like "[1m]" before any id comparison) and its
    SYNTHETIC sentinel (excluded from served stamps, same as the registered tool).
  ADAPT (technique, not code) -- sandbox/V2_scratch/v2_stamp_aggregator.py showed
    that model_run_audit.py's own scan_transcript() returns a Counter, which is
    ORDER-LOSING by construction and cannot say "which call was the divergent one".
    read_ordered_stamps() below re-derives that same ordered-scan technique (same
    per-line predicate: type=="assistant", a non-empty string message.model, not
    SYNTHETIC) directly against this file's own single-transcript/watch-loop needs,
    rather than importing the sandbox/-scratch aggregator (a dev/tools/ deliverable
    should not depend on scratch code, and that script's per-transcript timestamp/
    version/multi-slug machinery is not needed here).
  BUILD-NEW -- the early-decision evaluate() (short-circuits on first divergence
    rather than waiting for N stamps), the --watch poll loop, and the CLI: no
    registered script does early-verdict polling of a single running transcript.

VERIFIED-LAUNCH PATTERN (coordinator usage; <=15 lines):
  1. Brief the fable child with a WARMUP PREAMBLE -- "Before the task: read these 4
     tiny files, one per tool call" -- to burn past the call-4 swap boundary before
     real work starts (does not prevent a swap; makes an early swap easier to see).
  2. Launch the child (Task tool, no model param -- the frontmatter pin governs).
  3. Point this tool at its transcript: <session>/subagents/agent-<id>.jsonl, or a
     task-output path that symlinks to it -- resolved transparently either way.
  4. Run:  python3 dev/tools/fable_watchdog.py <path> --watch
           (defaults: --expect claude-fable-5 --verdict-at 5 --interval 5 --timeout 300)
  5. exit 0 FAITHFUL     -> proceed trusting the run.
     exit 1 SWAPPED@k    -> stop/relaunch, or proceed KNOWINGLY (log the substitution).
     exit 2 UNDETERMINED -> child stalled or transcript still short; re-poll, or fall
                            back to a full post-hoc model_run_audit.py pass.
  6. At COLLECT, re-verify with model_run_audit.py regardless -- this tool is an
     EARLY signal for a running child, not a replacement for the full-transcript audit.
  NOT WIRED: no hook/template integration exists yet -- a registered CANDIDATE only
  (see this brief's drafted REGISTER_DELTA row); today it is a command the
  coordinator runs by hand after launch.

USAGE:
  python3 dev/tools/fable_watchdog.py <transcript.jsonl>
  python3 dev/tools/fable_watchdog.py <transcript.jsonl> --watch --interval 5 --timeout 300
  python3 dev/tools/fable_watchdog.py <transcript.jsonl> --expect claude-opus-5 --verdict-at 3
Self-test: bash sandbox/W_scratch/test_fable_watchdog.sh
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import model_run_audit as mra  # noqa: E402  -- USE: normalize_model() + SYNTHETIC, verbatim

FAITHFUL, SWAPPED, PENDING = "FAITHFUL", "SWAPPED", "PENDING"
EXIT_CODE = {FAITHFUL: 0, SWAPPED: 1, "UNDETERMINED": 2}


# ---------------------------------------------------------------- path resolution
def resolve_transcript_path(p):
    """Transparently follow the /private/tmp task-output symlink form (SPEC item 3)
    -- or any other symlink -- to the real transcript file. realpath resolves every
    level regardless of the specific directory convention on the other end."""
    return os.path.realpath(os.path.expanduser(p))


# ---------------------------------------------------------------- ordered scan
def read_ordered_stamps(path):
    """One pass over the transcript. Returns (stamps, diag).

    stamps: ordered [(call_idx 1-based, model_id_raw), ...] for every non-synthetic
    served-model stamp, in file order -- the SAME per-line predicate as
    model_run_audit.scan_transcript (type=="assistant", a non-empty string
    message.model, excluding SYNTHETIC), kept ordered instead of counted.

    diag: {"opened_ok", "error", "total_lines", "valid_json_lines", "malformed"} --
    enough to tell "no assistant records" apart from "parse failure" in an
    UNDETERMINED message. Fail-soft throughout: an unreadable file or a malformed
    line is recorded here, never raised.
    """
    diag = {"opened_ok": True, "error": None, "total_lines": 0,
             "valid_json_lines": 0, "malformed": 0}
    stamps = []
    try:
        fh = open(path, "r", errors="replace")
    except OSError as exc:
        diag["opened_ok"] = False
        diag["error"] = str(exc)
        return stamps, diag

    with fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            diag["total_lines"] += 1
            try:
                row = json.loads(line)
            except ValueError:
                diag["malformed"] += 1
                continue
            if not isinstance(row, dict):
                diag["malformed"] += 1
                continue
            diag["valid_json_lines"] += 1

            if row.get("type") != "assistant":
                continue
            msg = row.get("message")
            if not isinstance(msg, dict):
                continue
            model = msg.get("model")
            if isinstance(model, str) and model and model != mra.SYNTHETIC:
                stamps.append((len(stamps) + 1, model))
    return stamps, diag


# ---------------------------------------------------------------- verdict
def evaluate(stamps, expect_norm, n):
    """Pure decision function -- no I/O, so it is independently testable.

    Returns (verdict, detail): verdict in {FAITHFUL, SWAPPED, PENDING}. PENDING
    means "not decidable yet" -- the caller maps a still-PENDING verdict to
    UNDETERMINED once it stops reading (one-shot mode, or a --watch timeout).

    SHORT-CIRCUITS on the first divergence found among the stamps seen so far, even
    if fewer than n total stamps exist yet: a swap at call 4 is decisive whether or
    not calls 5..n ever arrive, which is the whole point of an EARLY verdict.
    """
    limit = min(n, len(stamps))
    for call_idx, model_raw in stamps[:limit]:
        if mra.normalize_model(model_raw) != expect_norm:
            return SWAPPED, {"swap_at": call_idx, "got": model_raw}
    if len(stamps) >= n:
        return FAITHFUL, {}
    return PENDING, {}


def _undetermined_reason(stamps, diag, n):
    if not diag["opened_ok"]:
        return "parse failure: cannot open transcript (%s)" % diag["error"]
    if diag["total_lines"] > 0 and diag["valid_json_lines"] == 0:
        return "parse failure: 0 of %d lines were valid JSON" % diag["total_lines"]
    if len(stamps) == 0:
        return "no assistant records"
    return "%d of %d stamps observed" % (len(stamps), n)


def render_verdict(verdict, detail, stamps, diag, expect_norm, n):
    """Returns (one_line_str, exit_code). Exactly one stdout line per the SPEC."""
    if verdict == FAITHFUL:
        return "FAITHFUL calls=1-%d model=%s" % (n, expect_norm), EXIT_CODE[FAITHFUL]
    if verdict == SWAPPED:
        got_norm = mra.normalize_model(detail["got"])
        return ("SWAPPED@%d expect=%s got=%s" % (detail["swap_at"], expect_norm, got_norm),
                EXIT_CODE[SWAPPED])
    reason = _undetermined_reason(stamps, diag, n)
    return ('UNDETERMINED reason="%s" stamps_seen=%d' % (reason, len(stamps)),
            EXIT_CODE["UNDETERMINED"])


# ---------------------------------------------------------------- cli
def _positive_int(s):
    v = int(s)
    if v < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return v


def _positive_float(s):
    v = float(s)
    if v <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return v


def build_argparser():
    ap = argparse.ArgumentParser(
        prog="fable_watchdog.py",
        description="Early serving-swap verdict for a claude-fable-5-pinned subagent "
                     "transcript. Compares the first --verdict-at served-model stamps "
                     "against --expect. Exit 0 FAITHFUL / 1 SWAPPED@k / 2 UNDETERMINED. "
                     "See dev/reports/BUGREPORT_fable_substitution_v3_20260806.md.",
    )
    ap.add_argument("transcript_path",
                     help="child transcript .jsonl, or a task-output path that symlinks "
                          "to one (any symlink is resolved transparently)")
    ap.add_argument("--expect", default="claude-fable-5", metavar="MODEL_ID",
                     help="the model id the launch requested (default: claude-fable-5)")
    ap.add_argument("--verdict-at", dest="verdict_at", type=_positive_int, default=5,
                     metavar="N",
                     help="check the first N served-call stamps (default: 5 -- the "
                          "measured swap boundary is call 4, so 5 catches it with a "
                          "call to spare)")
    ap.add_argument("--watch", action="store_true",
                     help="poll the transcript until N stamps are seen or --timeout "
                          "elapses, instead of a single one-shot read -- use this for "
                          "a still-running child")
    ap.add_argument("--interval", type=_positive_float, default=5.0, metavar="SEC",
                     help="seconds between polls in --watch mode (default: 5.0)")
    ap.add_argument("--timeout", type=_positive_float, default=300.0, metavar="SEC",
                     help="give up and report UNDETERMINED after this many seconds "
                          "in --watch mode (default: 300.0)")
    return ap


def main(argv=None):
    args = build_argparser().parse_args(argv)
    path = resolve_transcript_path(args.transcript_path)
    expect_norm = mra.normalize_model(args.expect)

    deadline = (time.monotonic() + args.timeout) if args.watch else None
    stamps, diag = [], {"opened_ok": True, "error": None, "total_lines": 0,
                          "valid_json_lines": 0, "malformed": 0}
    verdict, detail = PENDING, {}

    while True:
        stamps, diag = read_ordered_stamps(path)
        verdict, detail = evaluate(stamps, expect_norm, args.verdict_at)
        if verdict != PENDING:
            break
        if not args.watch:
            break
        if time.monotonic() >= deadline:
            break
        sys.stderr.write(
            "fable_watchdog: watching -- %d/%d stamps so far, retrying in %.1fs\n"
            % (len(stamps), args.verdict_at, args.interval)
        )
        time.sleep(args.interval)

    line, code = render_verdict(verdict, detail, stamps, diag, expect_norm, args.verdict_at)
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
