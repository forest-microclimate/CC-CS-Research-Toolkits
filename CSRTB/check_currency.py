#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""check_currency.py -- VLOOP Item 5: post-login / post-install currency check.

WHAT IT CLOSES
The F3 login-reseed slice. A Claude Science login/reseed can silently REVERT served
skill bytes to an older catalog copy, with no error and no notification.

THE REVIEW CATCH THIS EXISTS TO HONOUR (and the whole reason it is not a one-liner)
A blind republish can DESTROY an intentional post-manifest edit, because a reversion
and a legitimate edit BOTH present as `live sha != known-good sha`. Two items can
drift in OPPOSITE directions in one check --
  one item : live OLDER  (reseed reversion)      -> repair FROM the record
  another  : live NEWER  (unpublished real work)  -> record is stale
A single global direction would have destroyed one or the other. So:

  *** THIS TOOL NEVER OFFERS A GLOBAL DIRECTION. It classifies EVERY item ***
  *** independently and refuses to auto-repair anything it cannot direct.  ***

THE MECHANISM THAT MAKES DIRECTION DECIDABLE
A BUILD-time manifest cannot distinguish the two cases: any post-build edit looks
like drift. So the known-good manifest is written by the PUBLISH/INSTALL ACTION
itself (`--write-manifest`, normally called right after a successful publish), and
it is stored OUTSIDE the reseed-mutable catalog. After that, `live != manifest`
means "changed since the last INTENDED publish".

That still leaves the edit-without-publish case, so direction is not assumed from
the timestamp alone -- it is EVIDENCED per item from the text (see classify_drift).

HONEST LIMIT -- READ THIS BEFORE BELIEVING THE GATE PROTECTS YOU
On Claude Science this check is DISCRETION-FIRED. The platform exposes no login or
session-start hook, so nothing can make it run: it fires when an agent or the user
invokes it. It is a callable gate, not an enforced one. (The CCRT side of the
toolkit CAN be hooked mechanically via SessionStart; that half is not built here.)
Calling this "protection" would be the exact efficacy-from-existence failure the
VLOOP work exists to close. It is a fast, reliable check that must be RUN.

MARKER
Emits `[[vloop:currency n_claims=N n_fail=M]]`; MARKER_ABSENT means it did not run,
which is NOT a pass.

USAGE
  # right after a successful publish/install -- records the new known-good state
  check_currency.py --write-manifest --bundle <bundle.json> --live-root <skills/> \
                    --manifest <path> --reason "published v2.5"

  # any time -- compare served bytes to the last intended publish
  check_currency.py --check --bundle <bundle.json> --live-root <skills/> \
                    --manifest <path> [--repair]

Exit: 0 = no drift (served bytes already match the record) | 2 = drift found (this
INCLUDES a --repair run that restored files: repair reports exit 2 and prints "re-run
--check to confirm", so a fresh --check afterwards is what returns 0) | 3 = usage error.
"""
import argparse
import contextlib
import datetime
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

MARKER_NAME = "currency"

# Direction verdicts. The point of the tool is that these are NOT one bucket.
LIVE_OLDER = "LIVE_OLDER"        # reseed reversion -> repair from the record
LIVE_NEWER = "LIVE_NEWER"        # unpublished real work -> the RECORD is stale
LIVE_MISSING = "LIVE_MISSING"    # file vanished from live -> reversion-like
LIVE_EXTRA = "LIVE_EXTRA"        # file only live -> unpublished addition, NEVER delete
AMBIGUOUS = "AMBIGUOUS"          # genuinely both-ways -> human decides

REPAIRABLE = (LIVE_OLDER, LIVE_MISSING)


def sha_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def emit_marker(n_claims, n_fail):
    return "[[vloop:%s n_claims=%d n_fail=%d]]" % (MARKER_NAME, n_claims, n_fail)


def read_text(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    return raw.decode("utf-8")


def bundle_items(bundle):
    """{(skill, relpath): text} for every file the bundle carries."""
    out = {}
    for sk in bundle.get("skills", []):
        for rel, text in sk["files"].items():
            out[(sk["name"], rel)] = text
    return out


def live_items(live_root, names):
    """{(skill, relpath): text} for the served copies of `names`, skipping dotfiles."""
    out = {}
    for name in names:
        d = os.path.join(live_root, name)
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for f in files:
                if f.startswith("."):
                    continue
                p = os.path.join(root, f)
                rel = os.path.relpath(p, d)
                try:
                    out[(name, rel)] = read_text(p)
                except UnicodeDecodeError:
                    out[(name, rel)] = None      # unreadable -> surfaced as a fail
    return out


def classify_drift(record_text, live_text):
    """Decide DIRECTION for one drifting file, from the text -- not from a timestamp.

    Returns (verdict, evidence). The line-overlap accounting is deliberately reported
    even when the verdict is decisive, because a bare verdict is unauditable.

    WHY LINE SETS AND NOT `startswith`: on 2026-07-24 the audible-alert drift was first
    recorded as a "strict superset, bundle text is a literal prefix of live". Measured,
    that was FALSE -- the texts diverge mid-file (a heading was rewritten) while 74 of 77
    non-empty lines still appear verbatim. A prefix test would have called that
    AMBIGUOUS-with-no-detail; line sets produce the 74/77 accounting that actually
    tells a human what happened.
    """
    if live_text is None:
        return AMBIGUOUS, "live copy is not valid UTF-8 and cannot be compared"
    rec = [l for l in record_text.splitlines() if l.strip()]
    liv = [l for l in live_text.splitlines() if l.strip()]
    rec_s, liv_s = set(rec), set(liv)
    rec_only = rec_s - liv_s
    liv_only = liv_s - rec_s
    shared = len(rec_s & liv_s)
    acct = ("%d/%d record lines present live; %d record-only, %d live-only; "
            "chars %d -> %d" % (shared, len(rec_s), len(rec_only), len(liv_only),
                                len(record_text), len(live_text)))
    if not rec_only and liv_only:
        return LIVE_NEWER, "live is a strict line-superset of the record. " + acct
    if not liv_only and rec_only:
        return LIVE_OLDER, "live is a strict line-SUBSET of the record. " + acct
    if not rec_only and not liv_only:
        # same line SET, different text: reordering or whitespace-only change
        return AMBIGUOUS, "identical line set, different text (reorder/whitespace). " + acct
    # HONEST LIMITATION, verified on the real 2026-07-24 drift rather than assumed:
    # audible-alert -- unambiguously newer work to a human -- lands HERE, not in LIVE_NEWER,
    # because 4 record lines were REWRITTEN rather than merely appended (70/74 shared,
    # 4 record-only, 52 live-only). That is the correct call on the available evidence: a
    # rewrite is textually indistinguishable from a partial revert, and guessing NEWER
    # because "live is bigger" is exactly the size heuristic that would have destroyed a
    # legitimately hardened item. So the common real case of "edited an existing section
    # while adding new ones" needs a human. --repair never touches it; that is the design,
    # not a gap to close by loosening the predicate.
    return AMBIGUOUS, ("both sides carry lines the other lacks -- neither a clean revert "
                       "nor a clean extension. " + acct)


def write_manifest(bundle_path, live_root, manifest_path, reason):
    """Record the CURRENT served state as known-good. Called by the publish/install action.

    Records the LIVE bytes, not the bundle's: the manifest's job is to answer "what did we
    last intend to serve", and the publish action's own output is what was served.
    """
    with open(bundle_path, encoding="utf-8") as fh:
        bundle = json.load(fh)
    names = [sk["name"] for sk in bundle.get("skills", [])]
    live = live_items(live_root, names)
    if not live:
        print("REFUSING to write an empty manifest: no live files found under %s.\n"
              "An empty known-good record would make every future check pass vacuously."
              % live_root)
        return 3
    items = {}
    for (name, rel), text in sorted(live.items()):
        if text is None:
            print("REFUSING to write manifest: %s/%s is not valid UTF-8." % (name, rel))
            return 3
        items.setdefault(name, {})[rel] = {"sha": sha_text(text), "chars": len(text)}
    man = {
        "schema": "crt-known-good-manifest/1",
        "written_at": datetime.datetime.now(datetime.timezone.utc)
                      .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason": reason or "(unspecified)",
        "bundle_path": os.path.abspath(bundle_path),
        "bundle_version": bundle.get("bundle_version"),
        "live_root": os.path.abspath(live_root),
        "n_skills": len(items),
        "n_files": sum(len(v) for v in items.values()),
        "items": items,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1, sort_keys=True)
    print("wrote known-good manifest: %s\n  %d skills / %d files at %s\n  reason: %s"
          % (manifest_path, man["n_skills"], man["n_files"], man["written_at"],
             man["reason"]))
    return 0


def load_manifest(path):
    """Load + VACUITY-GATE the manifest. An empty or hollow record must never pass."""
    if not os.path.exists(path):
        return None, ("no known-good manifest at %s. This check cannot run without one; "
                      "write it with --write-manifest immediately after a publish. "
                      "Absence is NOT currency." % path)
    with open(path, encoding="utf-8") as fh:
        man = json.load(fh)
    items = man.get("items") or {}
    if not items:
        return None, "manifest has ZERO skills -- an empty record passes every check vacuously"
    n_files = sum(len(v or {}) for v in items.values())
    if n_files == 0:
        return None, "manifest has skills but ZERO files -- hollow record, would pass vacuously"
    hollow = [("%s/%s" % (n, r)) for n, fs in items.items() for r, meta in (fs or {}).items()
              if not (meta or {}).get("sha")]
    if hollow:
        return None, "manifest entries with no sha (hollow): %s" % ", ".join(sorted(hollow)[:5])
    return man, None


def check(bundle_path, live_root, manifest_path, repair=False, json_out=None):
    man, err = load_manifest(manifest_path)
    if err:
        print(emit_marker(0, 1))
        print("\nCURRENCY GATE: FAIL (manifest unusable)\n  - %s" % err)
        return 2

    with open(bundle_path, encoding="utf-8") as fh:
        bundle = json.load(fh)
    btexts = bundle_items(bundle)
    names = sorted(man["items"])
    live = live_items(live_root, names)

    rows, n_checked = [], 0
    for name in names:
        for rel, meta in sorted(man["items"][name].items()):
            n_checked += 1
            key = (name, rel)
            lt = live.get(key)
            if key not in live:
                rows.append({"item": "%s/%s" % (name, rel), "verdict": LIVE_MISSING,
                             "evidence": "present in the known-good record, ABSENT live",
                             "record_sha": meta["sha"][:12], "live_sha": "-"})
                continue
            if lt is None:
                rows.append({"item": "%s/%s" % (name, rel), "verdict": AMBIGUOUS,
                             "evidence": "live copy is not valid UTF-8",
                             "record_sha": meta["sha"][:12], "live_sha": "?"})
                continue
            ls = sha_text(lt)
            if ls == meta["sha"]:
                continue
            # drifted -- direction needs the RECORD's text. The manifest stores hashes
            # only, so the bundle supplies the text; if the bundle no longer carries this
            # file we say so rather than guessing a direction.
            rec_text = btexts.get(key)
            if rec_text is None or sha_text(rec_text) != meta["sha"]:
                rows.append({"item": "%s/%s" % (name, rel), "verdict": AMBIGUOUS,
                             "evidence": ("drifted, but the bundle's copy does not match the "
                                          "manifest sha either, so no trustworthy record text "
                                          "exists to diff against"),
                             "record_sha": meta["sha"][:12], "live_sha": ls[:12]})
                continue
            verdict, ev = classify_drift(rec_text, lt)
            rows.append({"item": "%s/%s" % (name, rel), "verdict": verdict, "evidence": ev,
                         "record_sha": meta["sha"][:12], "live_sha": ls[:12],
                         "record_text": rec_text})

    # live files with no manifest entry: unpublished ADDITIONS. Reported, never deleted.
    for (name, rel) in sorted(live):
        if rel not in (man["items"].get(name) or {}):
            rows.append({"item": "%s/%s" % (name, rel), "verdict": LIVE_EXTRA,
                         "evidence": "served live but absent from the known-good record "
                                     "(an unpublished addition -- do NOT delete it)",
                         "record_sha": "-", "live_sha": sha_text(live[(name, rel)] or "")[:12]
                         if live[(name, rel)] is not None else "?"})

    n_fail = len(rows)
    print(emit_marker(n_checked, n_fail))
    if json_out:
        _by = {}
        for _r in rows:
            _by[_r["verdict"]] = _by.get(_r["verdict"], 0) + 1
        try:
            with open(json_out, "w", encoding="utf-8") as _fh:
                json.dump({"n_checked": n_checked, "n_fail": n_fail, "by_verdict": _by,
                           "rows": [{"item": _r["item"], "verdict": _r["verdict"]} for _r in rows]},
                          _fh)
        except Exception:
            pass
    print("\nmanifest written %s (%s)\n  covering %d skills / %d files; %d files compared"
          % (man.get("written_at"), man.get("reason"), man.get("n_skills"),
             man.get("n_files"), n_checked))

    if not rows:
        print("\nCURRENCY GATE: PASS -- every served file matches the last intended publish.")
        return 0

    by = {}
    for r in rows:
        by.setdefault(r["verdict"], []).append(r)
    print("\nCURRENCY GATE: DRIFT (%d)" % n_fail)
    for verdict in (LIVE_MISSING, LIVE_OLDER, LIVE_NEWER, LIVE_EXTRA, AMBIGUOUS):
        for r in by.get(verdict, []):
            print("  [%s] %s\n      record %s vs live %s\n      %s"
                  % (verdict, r["item"], r["record_sha"], r["live_sha"], r["evidence"]))

    print("\nPER-ITEM DIRECTION (this tool deliberately offers no global overwrite):")
    print("  %-14s %d -> repair FROM the record (reseed reversion)" % (LIVE_MISSING + ":", len(by.get(LIVE_MISSING, []))))
    print("  %-14s %d -> repair FROM the record (reseed reversion)" % (LIVE_OLDER + ":", len(by.get(LIVE_OLDER, []))))
    print("  %-14s %d -> the RECORD is stale; re-publish, do NOT overwrite live" % (LIVE_NEWER + ":", len(by.get(LIVE_NEWER, []))))
    print("  %-14s %d -> unpublished addition; leave alone, publish if wanted" % (LIVE_EXTRA + ":", len(by.get(LIVE_EXTRA, []))))
    print("  %-14s %d -> HUMAN DECIDES; no automatic action is safe" % (AMBIGUOUS + ":", len(by.get(AMBIGUOUS, []))))

    repairable = [r for r in rows if r["verdict"] in REPAIRABLE]
    if repair and repairable:
        print("\n--repair: restoring %d file(s) whose direction is unambiguous." % len(repairable))
        print("  NOT touching %d non-repairable item(s) -- that restraint is the point."
              % (len(rows) - len(repairable)))
        for r in repairable:
            name, rel = r["item"].split("/", 1)
            text = r.get("record_text")
            if text is None:
                text = btexts.get((name, rel))
            if text is None:
                print("  SKIP %s: no record text available" % r["item"])
                continue
            dst = os.path.join(live_root, name, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(text)
            back = sha_text(read_text(dst))
            print("  %s %s (read-back sha %s)"
                  % ("RESTORED" if back == sha_text(text) else "WROTE-BUT-MISMATCH",
                     r["item"], back[:12]))
        print("\nNOTE: on Claude Science a plain disk write can lose to the cloud catalog "
              "copy. Prefer host.skills.publish(name, overwrite=True) from a repl cell; "
              "re-run --check afterwards to confirm.")
    elif repairable:
        print("\n%d item(s) are safely repairable. Re-run with --repair to restore them "
              "(nothing was modified now)." % len(repairable))

    return 2


# --------------------------------------------------------------------------- #
# Fixtures (contract clause 5) -- build REAL bundle + live trees, drive REAL
# main(). PLANTED-BAD must FAIL, PLANTED-CLEAN must PASS, and NEGATIVE CONTROLS
# prove each rule fires independently rather than passing vacuously. Assert,
# never print. Run:  check_currency.py --self-test
#
# The load-bearing control here is repair-selectivity: the whole reason this
# tool is not a one-liner is that it must NEVER apply a global direction. The
# combined fixture plants all five direction classes at once and proves --repair
# restores ONLY the two reversions (LIVE_OLDER + LIVE_MISSING) while leaving the
# other three byte-identical -- verified by READ-BACK of the saved bytes.
# --------------------------------------------------------------------------- #
def _fm(name, desc):
    """Minimal valid SKILL.md frontmatter (check_currency ignores it, but real
    inputs carry one, so the fixtures look like real inputs)."""
    return "---\nname: %s\ndescription: %s\n---\n" % (name, desc)


def _write_tree(root, content):
    """content: {skill: {relpath: text}} -> write root/<skill>/<relpath>."""
    for skill, files in content.items():
        for rel, text in files.items():
            p = os.path.join(root, skill, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)


def _bundle_obj(content):
    return {"skills": [{"name": s, "files": dict(files)}
                       for s, files in content.items()]}


def _read_file(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _fresh_lab(root, content):
    """Build a bundle JSON + a live tree with IDENTICAL content, then record the
    known-good manifest exactly as the publish/install action would (via REAL
    main() --write-manifest). Identical content is required so the manifest sha
    (recorded from live) also matches the bundle's record text -- the substrate
    classify_drift() diffs against. Returns (bundle_path, live_root, manifest_path);
    the manifest is written OUTSIDE live_root, as the tool demands."""
    os.makedirs(root, exist_ok=True)
    bundle_path = os.path.join(root, "bundle.json")
    with open(bundle_path, "w", encoding="utf-8") as fh:
        json.dump(_bundle_obj(content), fh)
    live_root = os.path.join(root, "live")
    _write_tree(live_root, content)
    manifest_path = os.path.join(root, "known_good.json")          # outside live_root
    with contextlib.redirect_stdout(io.StringIO()):                # keep self-test stdout small
        rc = main(["--write-manifest", "--bundle", bundle_path, "--live-root", live_root,
                   "--manifest", manifest_path, "--reason", "selftest publish"])
    if rc != 0 or not os.path.exists(manifest_path):
        raise RuntimeError("fixture setup: write-manifest returned rc=%s" % rc)
    return bundle_path, live_root, manifest_path


def _run(argv):
    """Drive REAL main(), capturing its stdout so assertions read the true verdict.

    A crash in the code-under-test is converted to a sentinel rc + the traceback in
    the captured output, so a fixture never aborts the harness with a bare exit 1 --
    the assertions (which look for a specific exit code and verdict string) then fail
    cleanly as `result=FAIL`, which is what a negative control must do. Setup errors
    stay OUTSIDE this wrapper (in _fresh_lab), so they still surface loudly."""
    import traceback
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = main(argv)
    except Exception:                       # noqa: BLE001 -- deliberate: see docstring
        return 99, buf.getvalue() + "\nEXCEPTION:\n" + traceback.format_exc()
    return rc, buf.getvalue()


def run_fixtures():
    lab = tempfile.mkdtemp(prefix="currency_selftest_")
    failures = []

    def check_(name, cond):
        if not cond:
            failures.append(name)

    def base():
        # DISTINCT content lines so line-set direction is never ambiguous by accident.
        return {
            "skill-one": {
                "SKILL.md": _fm("skill-one", "first") + "A1\nA2\nA3\nA4\n",
                "scripts/a.py": "AA-original-1\nAA-original-2\n",
                "notes.md": "N1\nN2\nN3\n",
            },
            "skill-two": {
                "SKILL.md": _fm("skill-two", "second") + "B1\nB2\nB3\n",
            },
        }

    try:
        # ---- PLANTED-CLEAN (negative control): no drift -> exit 0, PASS, marker ----
        bp, lr, mp = _fresh_lab(os.path.join(lab, "clean"), base())
        rc, out = _run(["--check", "--bundle", bp, "--live-root", lr, "--manifest", mp])
        check_("clean_exit0", rc == 0)
        check_("clean_says_pass", "CURRENCY GATE: PASS" in out)
        check_("clean_marker_present", "[[vloop:currency" in out)   # MARKER_ABSENT != pass
        check_("clean_marker_zero_fail", "n_fail=0" in out)

        # ---- LIVE_OLDER (reseed reversion): live is a strict line-SUBSET ----------
        bp, lr, mp = _fresh_lab(os.path.join(lab, "older"), base())
        _write_tree(lr, {"skill-one": {"SKILL.md": _fm("skill-one", "first") + "A1\nA2\n"}})
        rc, out = _run(["--check", "--bundle", bp, "--live-root", lr, "--manifest", mp])
        check_("older_exit2", rc == 2)
        check_("older_verdict", "[LIVE_OLDER] skill-one/SKILL.md" in out)

        # ---- LIVE_NEWER (unpublished work): live is a strict line-SUPERSET --------
        bp, lr, mp = _fresh_lab(os.path.join(lab, "newer"), base())
        _write_tree(lr, {"skill-two": {"SKILL.md":
                     _fm("skill-two", "second") + "B1\nB2\nB3\nB4\nB5\n"}})
        rc, out = _run(["--check", "--bundle", bp, "--live-root", lr, "--manifest", mp])
        check_("newer_exit2", rc == 2)
        check_("newer_verdict", "[LIVE_NEWER] skill-two/SKILL.md" in out)

        # ---- LIVE_MISSING: a recorded file vanished from live --------------------
        bp, lr, mp = _fresh_lab(os.path.join(lab, "missing"), base())
        os.remove(os.path.join(lr, "skill-one", "scripts", "a.py"))
        rc, out = _run(["--check", "--bundle", bp, "--live-root", lr, "--manifest", mp])
        check_("missing_exit2", rc == 2)
        check_("missing_verdict", "[LIVE_MISSING] skill-one/scripts/a.py" in out)

        # ---- LIVE_EXTRA: a file only live (unpublished addition) -----------------
        bp, lr, mp = _fresh_lab(os.path.join(lab, "extra"), base())
        _write_tree(lr, {"skill-two": {"scripts/new.py": "brand new\n"}})
        rc, out = _run(["--check", "--bundle", bp, "--live-root", lr, "--manifest", mp])
        check_("extra_exit2", rc == 2)
        check_("extra_verdict", "[LIVE_EXTRA] skill-two/scripts/new.py" in out)

        # ---- AMBIGUOUS: both sides carry unique lines (a rewrite, not a revert) ---
        bp, lr, mp = _fresh_lab(os.path.join(lab, "ambig"), base())
        _write_tree(lr, {"skill-one": {"notes.md": "N1\nN2\nX4\nX5\n"}})  # drop N3, add X4,X5
        rc, out = _run(["--check", "--bundle", bp, "--live-root", lr, "--manifest", mp])
        check_("ambig_exit2", rc == 2)
        check_("ambig_verdict", "[AMBIGUOUS] skill-one/notes.md" in out)

        # ---- THE CORE NEGATIVE CONTROL: --repair is PER-ITEM, never global -------
        # All five classes at once; --repair must restore ONLY the 2 reversions and
        # leave the 3 non-repairable items byte-identical (proven by READ-BACK).
        bp, lr, mp = _fresh_lab(os.path.join(lab, "repair"), base())
        rec = base()
        _write_tree(lr, {
            "skill-one": {"SKILL.md": _fm("skill-one", "first") + "A1\nA2\n",   # LIVE_OLDER
                          "notes.md": "N1\nN2\nX4\nX5\n"},                       # AMBIGUOUS
            "skill-two": {"SKILL.md": _fm("skill-two", "second") + "B1\nB2\nB3\nB4\nB5\n",  # LIVE_NEWER
                          "scripts/new.py": "brand new\n"},                      # LIVE_EXTRA
        })
        os.remove(os.path.join(lr, "skill-one", "scripts", "a.py"))             # LIVE_MISSING
        notes_before = _read_file(os.path.join(lr, "skill-one", "notes.md"))
        two_before = _read_file(os.path.join(lr, "skill-two", "SKILL.md"))
        extra_before = _read_file(os.path.join(lr, "skill-two", "scripts", "new.py"))
        rc, out = _run(["--check", "--repair", "--bundle", bp, "--live-root", lr,
                        "--manifest", mp])
        check_("repair_exit2", rc == 2)                 # non-repairable drift remains -> 2
        check_("repair_reported_all_five",
               all(v in out for v in ("LIVE_OLDER", "LIVE_MISSING", "LIVE_NEWER",
                                      "LIVE_EXTRA", "AMBIGUOUS")))
        # READ-BACK the two that MUST be restored (contract clause 7)
        check_("repair_restored_older",
               _read_file(os.path.join(lr, "skill-one", "SKILL.md"))
               == rec["skill-one"]["SKILL.md"])
        miss_p = os.path.join(lr, "skill-one", "scripts", "a.py")
        check_("repair_restored_missing",
               os.path.exists(miss_p) and _read_file(miss_p) == rec["skill-one"]["scripts/a.py"])
        # the three non-repairable items MUST be byte-unchanged -- the restraint IS the point
        check_("repair_left_newer",
               _read_file(os.path.join(lr, "skill-two", "SKILL.md")) == two_before)
        check_("repair_left_ambiguous",
               _read_file(os.path.join(lr, "skill-one", "notes.md")) == notes_before)
        check_("repair_left_extra",
               _read_file(os.path.join(lr, "skill-two", "scripts", "new.py")) == extra_before)

        # ---- --json-out: machine-readable report is written and well-formed ------
        bp, lr, mp = _fresh_lab(os.path.join(lab, "jsonout"), base())
        _write_tree(lr, {"skill-one": {"SKILL.md": _fm("skill-one", "first") + "A1\nA2\n"}})
        jo = os.path.join(lab, "jsonout", "report.json")
        rc, _ = _run(["--check", "--bundle", bp, "--live-root", lr, "--manifest", mp,
                      "--json-out", jo])
        check_("jsonout_exit2", rc == 2)
        check_("jsonout_written", os.path.exists(jo))
        if os.path.exists(jo):
            rep = json.load(open(jo))
            check_("jsonout_shape",
                   set(rep) >= {"n_checked", "n_fail", "by_verdict", "rows"})
            check_("jsonout_counts_older",
                   rep.get("by_verdict", {}).get("LIVE_OLDER") == 1 and rep.get("n_fail") == 1)

        # ---- VACUITY GUARD A: absent manifest -> FAIL, never a vacuous pass -------
        bp, lr, mp = _fresh_lab(os.path.join(lab, "vac_absent"), base())
        rc, out = _run(["--check", "--bundle", bp, "--live-root", lr,
                        "--manifest", os.path.join(lab, "vac_absent", "nope.json")])
        check_("absent_manifest_exit2", rc == 2)
        check_("absent_manifest_msg", "manifest unusable" in out or "NOT currency" in out)

        # ---- VACUITY GUARD B: empty manifest (0 items) -> FAIL, not 0-of-0 pass ---
        empty_mp = os.path.join(lab, "empty_manifest.json")
        with open(empty_mp, "w", encoding="utf-8") as fh:
            json.dump({"schema": "crt-known-good-manifest/1", "items": {}}, fh)
        rc, out = _run(["--check", "--bundle", bp, "--live-root", lr, "--manifest", empty_mp])
        check_("empty_manifest_exit2", rc == 2)
        check_("empty_manifest_vacuous_msg", "vacuous" in out or "ZERO" in out)

        # ---- VACUITY GUARD C: --write-manifest REFUSES an empty live tree --------
        empty_live = os.path.join(lab, "empty_live")
        os.makedirs(empty_live, exist_ok=True)
        rc, out = _run(["--write-manifest", "--bundle", bp, "--live-root", empty_live,
                        "--manifest", os.path.join(lab, "would_be_empty.json")])
        check_("write_empty_refused_exit3", rc == 3)

        # ---- USAGE GUARD D: a manifest INSIDE live-root is refused (reseed trap) --
        bp, lr, mp = _fresh_lab(os.path.join(lab, "inside"), base())
        rc, out = _run(["--check", "--bundle", bp, "--live-root", lr,
                        "--manifest", os.path.join(lr, "inside_manifest.json")])
        check_("manifest_inside_liveroot_exit3", rc == 3)

        # ---- USAGE GUARD E: neither / both of --write-manifest/--check -> exit 3 --
        rc, _ = _run(["--bundle", bp, "--live-root", lr, "--manifest", mp])
        check_("neither_mode_exit3", rc == 3)
        rc, _ = _run(["--write-manifest", "--check", "--bundle", bp,
                      "--live-root", lr, "--manifest", mp])
        check_("both_modes_exit3", rc == 3)

    finally:
        shutil.rmtree(lab, ignore_errors=True)

    if failures:
        print("[[vloop:currency-selftest result=FAIL failed=%d checks=%s]]"
              % (len(failures), ",".join(failures)))
        return 2
    print("[[vloop:currency-selftest result=PASS]]")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write-manifest", action="store_true",
                    help="record the current served state as known-good (post-publish)")
    ap.add_argument("--check", action="store_true", help="compare served bytes to the record")
    ap.add_argument("--self-test", action="store_true",
                    help="build fixtures, drive REAL main() across all 5 direction classes "
                         "+ vacuity guards, assert; ignores --bundle/--live-root/--manifest")
    # These three are logically required for --write-manifest/--check, but NOT for
    # --self-test (which supplies its own fixture paths). So they are validated
    # MANUALLY below rather than by argparse required=True -- exactly the pattern
    # residue_table.py uses for --src/--dest. A missing arg now returns 3 (usage
    # error, the documented code) instead of argparse's exit 2, which would collide
    # with this tool's "2 = drift" meaning.
    ap.add_argument("--bundle")
    ap.add_argument("--live-root", help="the served skills/ directory")
    ap.add_argument("--manifest",
                    help="known-good manifest path -- MUST be outside the reseed-mutable "
                         "catalog, or a reseed can revert the record along with the skills")
    ap.add_argument("--reason", default=None, help="why the manifest is being written")
    ap.add_argument("--json-out", default=None,
                    help="machine-readable report path: {n_checked,n_fail,by_verdict,rows}")
    ap.add_argument("--repair", action="store_true",
                    help="restore ONLY items whose direction is unambiguously LIVE_OLDER "
                         "or LIVE_MISSING; never touches LIVE_NEWER/EXTRA/AMBIGUOUS")
    a = ap.parse_args(argv)
    if a.self_test:
        return run_fixtures()
    if a.write_manifest == a.check:
        print("choose exactly one of --write-manifest / --check")
        return 3
    missing = [n for n, v in (("--bundle", a.bundle), ("--live-root", a.live_root),
                              ("--manifest", a.manifest)) if not v]
    if missing:
        print("missing required argument(s): %s" % ", ".join(missing))
        return 3
    live_inside = os.path.abspath(a.manifest).startswith(os.path.abspath(a.live_root) + os.sep)
    if live_inside:
        print("REFUSING: the manifest (%s) is INSIDE the reseed-mutable live root (%s). "
              "A reseed could revert the record together with the skills it guards."
              % (a.manifest, a.live_root))
        return 3
    if a.write_manifest:
        return write_manifest(a.bundle, a.live_root, a.manifest, a.reason)
    return check(a.bundle, a.live_root, a.manifest, repair=a.repair, json_out=a.json_out)


if __name__ == "__main__":
    sys.exit(main())
