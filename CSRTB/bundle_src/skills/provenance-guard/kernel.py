# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""provenance-guard kernel sidecar.

Two helpers, auto-loaded into the python kernel when the `provenance-guard`
skill is loaded:

  audit_tmp_provenance(...)  -> list[dict]   the /tmp-fit provenance linter
  checkpoint_frame(df, name) -> str          save-the-frame-before-you-fit helper

Motivating incident: PROVENANCE_FAILURE_bug_report.md (artifact
51e2e35f-36ae-4247-a783-7b56b14d2aab). A model frame feeding a published
figure was written to /tmp (untracked by workspace auto-capture) and lost on
a kernel restart. This module hardens the bug's fingerprint into a reusable
scan and makes "save the frame before you fit it" one call.

Design note — module scope is STDLIB ONLY (re, os, json) so this file can also
be exec()'d in the stdlib-only repl kernel, which is the ONLY kernel where
host.query (and thus execution_log) is reachable. All third-party imports
(pandas, pyarrow) are deferred into function bodies.
"""

import re
import os
import json

# ---- default marker vocabularies (literal tuples -> kernel.py gate-safe) ----
# A MODEL-fit cell: fits a statistical model. Kept specific to avoid matching
# English words (no bare "stan"/"gam"). Extend via fit_markers=.
DEFAULT_FIT_MARKERS = (
    "brm(", "brms::", "stan(", "stan_model", "cmdstan", "cmdstanr",
    "glmer(", "glmer.nb(", "lmer(", "lme(", "gam(", "gamm(", "gamm4(",
    "gls(", "glmmTMB(", "stan_glm", "MCMCglmm(",
)
# A FIGURE cell: renders a plot to disk. Separated so a lost figure-input CSV
# (figure itself is usually durable) grades below a lost model frame.
DEFAULT_FIG_MARKERS = ("savefig", "ggsave(")
# Functions that READ a path (the token that precedes the quoted /tmp path).
DEFAULT_READ_FUNCS = (
    "read.csv", "read_csv", "read.delim", "read_tsv", "read.table",
    "readRDS", "read_rds", "fread", "read_parquet", "read_feather",
    "read_pickle", "np.load", "load", "arrow::read", "loadRDS",
)
# Functions that WRITE a path.
DEFAULT_WRITE_FUNCS = (
    "to_csv", "write.csv", "write_csv", "write.table", "saveRDS", "save_rds",
    "fwrite", "write_parquet", "to_parquet", "write_feather", "to_pickle",
    "savefig", "ggsave", "saveRDS", "np.save", "writeLines",
)
DEFAULT_SCRATCH_DIRS = ("/tmp/", "/var/tmp/", "/dev/shm/")
DEFAULT_SCRATCH_EXTS = (
    "csv", "rds", "tsv", "parquet", "feather", "txt", "rdata", "rda",
    "pkl", "pickle", "npy", "npz", "json", "feather",
)


def pg_compile(scratch_dirs, scratch_exts):
    """Build the (path, read, write) regexes. Internal; named without a
    leading underscore-only-arg so the kernel.py gate accepts the def."""
    dir_alt = "|".join(re.escape(d) for d in scratch_dirs)
    ext_alt = "|".join(re.escape(e) for e in scratch_exts)
    path_re = re.compile(
        r"(?P<full>(?:%s)[A-Za-z0-9_.\-/]+?\.(?:%s))\b" % (dir_alt, ext_alt),
        re.I,
    )
    return path_re, dir_alt, ext_alt


def pg_marker_hit(src, markers):
    """True if any marker occurs in src as a genuine token, not inside a string
    literal. A call-shaped marker (ends in '(') immediately preceded by a quote
    is string DATA (e.g. a keyword list "brm(", "gam(") -> not a call, skipped.
    This kills the linter-scans-its-own-marker-list false positive."""
    for mk in markers:
        for m in re.finditer(re.escape(mk), src, re.I):
            i = m.start()
            prev = src[i - 1] if i > 0 else ""
            if prev in ("'", '"', "`"):
                continue  # quoted -> string data, not a call
            return True
    return False


def pg_fetch_artifact_basenames(host_obj):
    """Every durable artifact filename in the project (ground truth for
    'was this basename ever saved?'). Paged. Works in python AND repl."""
    names = set()
    if host_obj is None or not hasattr(host_obj, "artifacts"):
        return names
    offset = 0
    while True:
        page = host_obj.artifacts(limit=500, offset=offset)
        arts = page.get("artifacts", [])
        for a in arts:
            fn = a.get("filename")
            if fn:
                names.add(os.path.basename(fn))
        if len(arts) < 500:
            break
        offset += 500
    return names


def pg_fetch_execution_log(host_obj, scratch_dirs):
    """Return list of {id, source, ...} for cells whose source mentions any
    scratch dir. Self-adapting source:
      1. host.query present (repl tool) -> query execution_log directly, paged.
      2. else handoff/execution_log_dump.json present -> load it.
      3. else raise with actionable guidance.
    """
    # Path 1: host.query (repl only)
    if host_obj is not None and hasattr(host_obj, "query"):
        like = scratch_dirs[0]  # primary scratch dir for the SQL prefilter
        rows = []
        offset = 0
        page_n = 500
        while True:
            q = host_obj.query(
                "SELECT id, frame_id, cell_index, language, source, "
                "files_written, files_read, created_at "
                "FROM execution_log WHERE source LIKE ? "
                "ORDER BY created_at LIMIT ? OFFSET ?",
                ["%" + like + "%", page_n, offset],
            )
            cols = q["columns"]
            batch = [dict(zip(cols, r)) for r in q["rows"]]
            rows.extend(batch)
            if len(batch) < page_n:
                break
            offset += page_n
        # also sweep the other scratch dirs (rare) with one extra pass each
        for d in scratch_dirs[1:]:
            q = host_obj.query(
                "SELECT id, frame_id, cell_index, language, source, "
                "files_written, files_read, created_at "
                "FROM execution_log WHERE source LIKE ? ORDER BY created_at",
                ["%" + d + "%"],
            )
            cols = q["columns"]
            seen = {r["id"] for r in rows}
            for r in q["rows"]:
                row = dict(zip(cols, r))
                if row["id"] not in seen:
                    rows.append(row)
        return rows
    # Path 2: staged dump
    dump = os.path.join("handoff", "execution_log_dump.json")
    if os.path.exists(dump):
        with open(dump) as fh:
            return json.load(fh)
    # Path 3: no source
    raise RuntimeError(
        "audit_tmp_provenance: execution_log is unreachable from this kernel. "
        "It is only queryable via host.query, which lives in the `repl` tool. "
        "Either (a) run this audit from a `repl` cell:\n"
        "    exec(host.skills.read('provenance-guard','kernel.py')['content'])\n"
        "    audit_tmp_provenance()\n"
        "or (b) stage the log first from `repl` via dump_execution_log(), then "
        "re-call here (it will read handoff/execution_log_dump.json)."
    )


def dump_execution_log(path=None, scratch_only=True):
    """repl-only convenience: dump execution_log to a workspace JSON so the
    python-kernel copy of audit_tmp_provenance() can read it. Needs host.query.
    """
    if path is None:
        path = os.path.join("handoff", "execution_log_dump.json")
    if "host" not in globals() or not hasattr(globals()["host"], "query"):
        raise RuntimeError(
            "dump_execution_log needs host.query (run it from the `repl` tool)."
        )
    hq = globals()["host"]
    where = "WHERE source LIKE '%/tmp/%'" if scratch_only else ""
    rows = []
    offset = 0
    while True:
        q = hq.query(
            "SELECT id, frame_id, cell_index, language, source, files_written, "
            "files_read, created_at FROM execution_log %s "
            "ORDER BY created_at LIMIT 500 OFFSET %d" % (where, offset)
        )
        cols = q["columns"]
        batch = [dict(zip(cols, r)) for r in q["rows"]]
        rows.extend(batch)
        if len(batch) < 500:
            break
        offset += 500
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(rows, fh)
    return path


def audit_tmp_provenance(execution_log=None, artifact_names=None,
                         fit_markers=None, fig_markers=None,
                         read_funcs=None, write_funcs=None,
                         scratch_dirs=None, scratch_exts=None,
                         extra_save_scan=True, quiet=False):
    """Scan execution_log for the /tmp-fit provenance bug fingerprint.

    THE FINGERPRINT (from PROVENANCE_FAILURE_bug_report.md §e.5): a cell that
    READS a scratch path (/tmp/*.csv|*.rds|...) AND contains a fit/figure
    marker, where that path's basename was NEVER promoted to a durable
    artifact. Such a file is one kernel restart from oblivion.

    Returns a list[dict] of at-risk scratch files, most severe first. Each row:
      path, basename, durable(bool), severity, reason,
      read_by[cells], written_by[cells], fit_read_by[cells], fit_write_by[cells]
    Severity: CRITICAL (read by a MODEL-fit cell, unsaved -> the canonical bug:
                        a model frame one restart from oblivion) >
              HIGH (read by a FIGURE cell, or a fit/fig cell wrote it to
                    scratch; unsaved) >
              WARN (consumed downstream but unsaved, no fit/fig).
    Durable files and pure write-once-never-read scratch are NOT flagged.
    Markers in string literals (e.g. a keyword list "brm(","gam(") are ignored.

    Data sources self-adapt: host.query if present (repl), else a staged
    handoff/execution_log_dump.json, else a clear error. artifact_names default
    to every durable artifact filename (host.artifacts).
    """
    host_obj = globals().get("host")
    fit_markers = tuple(fit_markers) if fit_markers else DEFAULT_FIT_MARKERS
    fig_markers = tuple(fig_markers) if fig_markers else DEFAULT_FIG_MARKERS
    read_funcs = tuple(read_funcs) if read_funcs else DEFAULT_READ_FUNCS
    write_funcs = tuple(write_funcs) if write_funcs else DEFAULT_WRITE_FUNCS
    scratch_dirs = tuple(scratch_dirs) if scratch_dirs else DEFAULT_SCRATCH_DIRS
    scratch_exts = tuple(scratch_exts) if scratch_exts else DEFAULT_SCRATCH_EXTS

    if execution_log is None:
        execution_log = pg_fetch_execution_log(host_obj, scratch_dirs)
    if artifact_names is None:
        artifact_names = pg_fetch_artifact_basenames(host_obj)
    artifact_names = set(artifact_names)

    path_re, _, _ = pg_compile(scratch_dirs, scratch_exts)
    # save_artifacts basenames mentioned anywhere (intent-to-save safety net)
    saved_in_source = set()

    agg = {}  # basename -> role sets
    for row in execution_log:
        src = row.get("source") or ""
        cid = (row.get("id") or "")[:8]
        # quote-guarded so a marker list like "brm(","gam(" is NOT read as a fit
        has_fit = pg_marker_hit(src, fit_markers)
        has_fig = pg_marker_hit(src, fig_markers)
        if extra_save_scan and "save_artifacts" in src:
            for m in re.finditer(r"[\"']([A-Za-z0-9_.\-/]+\.[A-Za-z0-9]+)[\"']", src):
                # only count basenames that appear inside a save_artifacts(...) span
                pass
            for m in re.finditer(r"save_artifacts\s*\((.*?)\)", src, re.S):
                span = m.group(1)
                for fm in re.finditer(r"[\"']([^\"']+?\.[A-Za-z0-9]+)[\"']", span):
                    saved_in_source.add(os.path.basename(fm.group(1)))
        for m in path_re.finditer(src):
            full = m.group("full")
            base = os.path.basename(full)
            rec = agg.setdefault(base, {
                "path": full, "read_by": set(), "written_by": set(),
                "fit_read_by": set(), "fit_write_by": set(),
                "fig_read_by": set(), "fig_write_by": set(),
            })
            rec["path"] = full
            start = m.start()
            prefix = src[max(0, start - 40):start]
            is_read = any(fn in prefix for fn in read_funcs)
            is_write = any(fn in prefix for fn in write_funcs)
            if is_read:
                rec["read_by"].add(cid)
                if has_fit:
                    rec["fit_read_by"].add(cid)
                if has_fig:
                    rec["fig_read_by"].add(cid)
            if is_write:
                rec["written_by"].add(cid)
                if has_fit:
                    rec["fit_write_by"].add(cid)
                if has_fig:
                    rec["fig_write_by"].add(cid)

    durable_names = artifact_names | (saved_in_source if extra_save_scan else set())

    out = []
    for base, rec in agg.items():
        durable = base in durable_names
        if durable:
            continue
        read_by = sorted(rec["read_by"])
        written_by = sorted(rec["written_by"])
        fit_read_by = sorted(rec["fit_read_by"])
        fit_write_by = sorted(rec["fit_write_by"])
        fig_read_by = sorted(rec["fig_read_by"])
        fig_write_by = sorted(rec["fig_write_by"])
        if fit_read_by:
            sev, reason = ("CRITICAL",
                           "read by a MODEL-fit cell but never saved durably "
                           "(model frame one restart from oblivion)")
        elif fig_read_by:
            sev, reason = ("HIGH",
                           "read by a figure cell but never saved durably")
        elif fit_write_by or fig_write_by:
            sev, reason = ("HIGH",
                           "a fit/figure cell wrote it to scratch; "
                           "never saved durably")
        elif read_by:
            sev, reason = ("WARN",
                           "consumed by a later cell but never saved durably")
        else:
            # written once, never read, never durable -> throwaway scratch, skip
            continue
        out.append({
            "path": rec["path"], "basename": base, "durable": durable,
            "severity": sev, "reason": reason, "read_by": read_by,
            "written_by": written_by, "fit_read_by": fit_read_by,
            "fit_write_by": fit_write_by, "fig_read_by": fig_read_by,
            "fig_write_by": fig_write_by,
        })

    order = {"CRITICAL": 0, "HIGH": 1, "WARN": 2}
    out.sort(key=lambda r: (order[r["severity"]], r["basename"]))

    if not quiet:
        if not out:
            print("provenance-guard: no at-risk /tmp files. "
                  "Every scratch file read/written in the log is durable. \u2713")
        else:
            print("provenance-guard \u2014 %d at-risk scratch file(s):" % len(out))
            for r in out:
                where = []
                if r["fit_read_by"]:
                    where.append("fit-read@" + ",".join(r["fit_read_by"]))
                elif r["fig_read_by"]:
                    where.append("fig-read@" + ",".join(r["fig_read_by"]))
                elif r["read_by"]:
                    where.append("read@" + ",".join(r["read_by"]))
                if r["fit_write_by"]:
                    where.append("fit-write@" + ",".join(r["fit_write_by"]))
                elif r["fig_write_by"]:
                    where.append("fig-write@" + ",".join(r["fig_write_by"]))
                print("  \u26a0 [%-8s] %s \u2014 %s (%s)"
                      % (r["severity"], r["path"], r["reason"], "; ".join(where)))
            print("\nPromote each with a workspace copy + save_artifacts, or "
                  "re-run its producer writing to ./handoff/ instead of /tmp.")
    return out


def checkpoint_frame(df, name, save=True, fmt="parquet", handoff_dir="handoff"):
    """Save a dataframe you are about to FIT or PLOT, before the fit runs.

    Writes df to ./<handoff_dir>/<name>.<ext> (workspace-relative = shared
    across python/bash/R kernels AND tracked by workspace auto-capture, unlike
    /tmp). Returns the path. When save=True, records the path in
    handoff/_provenance_to_save.txt and prints the exact save_artifacts(...)
    call to run so the frame becomes a durable, versioned checkpoint.

    Encodes the rule: save every file another cell will READ, before the fit.
    Use this instead of writing a model frame / plot input to /tmp.
    """
    base = os.path.basename(str(name))
    for ext in (".parquet", ".csv", ".rds", ".feather", ".tsv"):
        if base.lower().endswith(ext):
            base = base[: -len(ext)]
            break
    os.makedirs(handoff_dir, exist_ok=True)

    used_fmt = fmt
    if fmt == "parquet":
        try:
            import importlib
            if (importlib.util.find_spec("pyarrow") is None
                    and importlib.util.find_spec("fastparquet") is None):
                used_fmt = "csv"
        except Exception:
            used_fmt = "csv"

    if used_fmt == "parquet":
        path = os.path.join(handoff_dir, base + ".parquet")
        df.to_parquet(path, index=False)
    else:
        path = os.path.join(handoff_dir, base + ".csv")
        df.to_csv(path, index=False)
        if fmt == "parquet":
            print("checkpoint_frame: no parquet engine; wrote CSV instead -> %s" % path)

    if save:
        manifest = os.path.join(handoff_dir, "_provenance_to_save.txt")
        existing = set()
        if os.path.exists(manifest):
            with open(manifest) as fh:
                existing = {ln.strip() for ln in fh if ln.strip()}
        if path not in existing:
            with open(manifest, "a") as fh:
                fh.write(path + "\n")
        print("checkpoint_frame: staged %s (%d rows). Now make it durable:"
              % (path, len(df)))
        print('    save_artifacts(files=["%s"], language="python", '
              'checkpoints=["%s"])' % (path, os.path.basename(path)))
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# verify_before_assert — the SEED-01 assert-from-recollection gate
# ═══════════════════════════════════════════════════════════════════════════════
# APPENDED 2026-07-28 (verification-integrity pass; plan i-am-trying-to-ethereal-bear,
# W1 CS split). ADDITIVE ONLY: every line above this banner is byte-for-byte unchanged;
# audit_tmp_provenance / checkpoint_frame / dump_execution_log are untouched.
#
# The failure catalog prescribes THIS gate for provenance-guard. SEED-01
# (assert-from-recollection): the recorded confession wrote three artifact version-ids
# INVENTED FROM MEMORY (frame 45171f5d, msg 514/624), no read grounding any of them.
# The gate makes "every asserted value/count/ID/status names the read that grounds it"
# a mechanical check whose ABSENCE on an asserting span is the auditable object.
#
# argparse + sys are stdlib, so the module-scope STDLIB-ONLY contract still holds (they
# are reachable in the stdlib-only repl kernel too). No host.* here: verify_before_assert
# is a PURE function of (facts, reads) — the record source for `reads` is INJECTED by the
# caller, exactly as delegation-planning injects list_models.
import argparse
import sys

# The EXACT placeholder set. A source_read_ref that normalizes (casefold + collapse
# whitespace) to one of these is NOT a real read — it is blank, an "n/a" stub, or a
# bare recollection. Module-level and read at CALL time so a mutation test can neuter it
# (fixtures_assert_gate.py sets this to frozenset() and proves the red fixtures flip
# green, the shipped file untouched). Whole-value match, NEVER substring: "" is a member
# so blank/missing refs fail via this ONE guard, while "read of memory_map.json" — which
# merely CONTAINS "memory" — is not a member and passes.
ASSERT_PLACEHOLDER_REFS = {"", "n/a", "memory", "recalled"}


def pg_norm_ref(value):
    """Normalize a ref for whole-value comparison: None -> '', casefold, collapse
    internal whitespace, strip edges. Used for BOTH the placeholder test and the reads
    membership test so the two stay consistent. Deliberately does NOT strip punctuation —
    the match must stay tight enough that a real path/id ref is never coerced into a
    placeholder."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def pg_assert_marker(n, verdict):
    """The machine-detectable tell, exactly [[assert_gate n=N verdict=PASS|FAIL]]. Its
    ABSENCE on a span that asserts values is the Reviewer-flaggable object: CS has no
    hooks, so the marker is DISCRETION-emitted and non-emission is what an auditor greps
    for."""
    return "[[assert_gate n=%d verdict=%s]]" % (n, verdict)


def verify_before_assert(facts, reads=None):
    """Fail-closed check that every asserted value/count/ID/status names the read that
    grounds it (SEED-01 assert-from-recollection).

    facts: a list of {claim, value, source_read_ref} objects (a lone dict is accepted as
        one fact). Each fact's source_read_ref must name the read that produced its
        value/count/ID/status.
    reads: OPTIONAL list of THIS-TURN read identifiers.
        - None (default, the WEAKER mode): only ref presence is checked — a fact FAILS
          when its source_read_ref is missing/blank or a placeholder token.
        - a list (the STRONGER mode): a fact ALSO FAILS when its ref is not among these
          reads (the grounding read did not happen this turn). The natural source is this
          turn's execution_log rows (what audit_tmp_provenance queries) — but this
          function NEVER calls host.*; the caller INJECTS `reads`.

    A fact FAILS when its source_read_ref (normalized: casefold + whitespace) is:
      * in ASSERT_PLACEHOLDER_REFS -> blank / 'n/a' / 'memory' / 'recalled' (whole-value,
                                      never substring — 'read of memory_map.json' passes),
      * (strong mode only) absent from `reads`.

    Returns {gate, verdict PASS|FAIL, n, reads_mode, vacuous, failures, marker}. n =
    len(facts); n=0 is PASS but flagged vacuous so an empty batch is visible, not laundered
    as green. NEVER raises and NEVER exits — a FAIL is data (only main() maps it to an exit
    code). The guard set is a module constant so a mutation test can neuter it.
    """
    reads_mode = "strict" if reads is not None else "presence-only"

    # Normalize `facts` to a list without ever raising.
    if facts is None:
        facts = []
    elif isinstance(facts, dict):
        facts = [facts]
    elif isinstance(facts, (list, tuple)):
        facts = list(facts)
    else:
        return {"gate": "verify_before_assert", "verdict": "FAIL", "n": 0,
                "reads_mode": reads_mode, "vacuous": False,
                "failures": [{"index": None, "claim": None, "value": None,
                              "source_read_ref": None, "check": "input",
                              "detail": "facts must be a list of "
                                        "{claim, value, source_read_ref} objects, got %s"
                                        % type(facts).__name__}],
                "marker": pg_assert_marker(0, "FAIL")}

    # Normalize `reads` (strong mode) without ever raising.
    norm_reads = None
    if reads is not None:
        if isinstance(reads, str):
            reads = [reads]
        try:
            norm_reads = set(pg_norm_ref(r) for r in reads)
        except TypeError:
            norm_reads = set()   # unusable reads -> fail closed on the stronger check

    failures = []
    for i, fact in enumerate(facts):
        if not isinstance(fact, dict):
            failures.append({"index": i, "claim": None, "value": None,
                             "source_read_ref": None, "check": "malformed",
                             "detail": "fact is %s, expected an object carrying a "
                                       "source_read_ref" % type(fact).__name__})
            continue
        claim = fact.get("claim")
        value = fact.get("value")
        ref = fact.get("source_read_ref")
        ref_norm = pg_norm_ref(ref)

        # Guard 1 — placeholder / blank (the mutable module-constant guard).
        if ref_norm in ASSERT_PLACEHOLDER_REFS:
            if ref_norm == "":
                check = "blank"
                detail = ("source_read_ref is missing or blank — this asserted "
                          "value/count/ID names no read that grounds it")
            else:
                check = "placeholder"
                detail = ("source_read_ref %r is a placeholder (a recollection / stub, "
                          "not a read of a real source)" % (ref,))
            failures.append({"index": i, "claim": claim, "value": value,
                             "source_read_ref": ref, "check": check, "detail": detail})
            continue

        # Guard 2 — the stronger this-turn-reads membership (only when reads injected).
        if norm_reads is not None and ref_norm not in norm_reads:
            failures.append({"index": i, "claim": claim, "value": value,
                             "source_read_ref": ref, "check": "not-in-reads",
                             "detail": "source_read_ref %r is not among this turn's reads "
                                       "— the grounding read did not happen this turn"
                                       % (ref,)})
            continue

    verdict = "FAIL" if failures else "PASS"
    return {"gate": "verify_before_assert", "verdict": verdict, "n": len(facts),
            "reads_mode": reads_mode, "vacuous": (len(facts) == 0),
            "failures": failures, "marker": pg_assert_marker(len(facts), verdict)}


# ─── CLI (the ONLY place that prints or exits) ──────────────────────────────────
def pg_is_script_run():
    """True ONLY when this file was executed as a script.

    The documented load path is exec(host.skills.read("provenance-guard",
    "kernel.py")["content"]) inside a repl cell, where __name__ is ALSO "__main__" — a
    bare __name__ guard would fire main() and BLOCK on stdin every time the skill loads.
    Compare the running script to this file instead; under exec() there is no __file__
    (mirrors directing-execution's guard)."""
    try:
        this = os.path.realpath(__file__)
    except NameError:
        return False
    argv0 = sys.argv[0] if sys.argv else ""
    return bool(argv0) and os.path.realpath(argv0) == this


def main(argv=None):
    """Additive argparse CLI (this kernel had NO __main__/CLI before this pass). One
    subcommand per gate, JSON in / JSON out, exit 0 PASS / 2 FAIL — the delegation-planning
    sibling contract. assert-gate input is a bare JSON facts list, or an object
    {"facts": [...], "reads": [...]} to exercise the stronger reads mode."""
    ap = argparse.ArgumentParser(
        prog="kernel.py",
        description="provenance-guard gates. assert-gate = verify_before_assert "
                    "(SEED-01 assert-from-recollection).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("assert-gate",
                       help='verify_before_assert over a facts list or {"facts","reads"}')
    p.add_argument("-i", "--input", default="-", help="JSON file, or - for stdin")

    args = ap.parse_args(argv)
    try:
        if args.input in (None, "-", ""):
            raw = sys.stdin.read()
        else:
            with open(args.input, encoding="utf-8") as fh:
                raw = fh.read()
    except Exception as exc:
        print(json.dumps({"verdict": "FAIL", "failures": [
            {"check": "input", "detail": "%s: %s" % (type(exc).__name__, exc)}]}))
        return 2

    try:
        payload = json.loads(raw)
        if isinstance(payload, list):
            facts, reads = payload, None
        elif isinstance(payload, dict):
            facts, reads = payload.get("facts"), payload.get("reads")
        else:
            raise ValueError("input must be a JSON facts list or an object {facts, reads}")
        result = verify_before_assert(facts, reads=reads)
    except Exception as exc:
        print(json.dumps({"verdict": "FAIL", "failures": [
            {"check": "input", "detail": "%s: %s" % (type(exc).__name__, exc)}]}))
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    print(result["marker"])
    return 0 if result["verdict"] == "PASS" else 2
