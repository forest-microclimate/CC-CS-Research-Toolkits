#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""
install_crt_science.py — replay the claude-research-toolkit customization layer
onto a Claude Science account.

WHAT THIS DOES
  Recreates, on the account running it, every custom SKILL and every custom
  agent PROFILE captured in crt_science_bundle.json — so a collaborator's
  account behaves as close to identically as the platform allows.

HOW TO RUN  (Claude Science)
  This uses host.skills.* / host.agents.*, which live ONLY in the control-plane
  kernel — i.e. the `repl` tool, NOT the `python` tool. In a `repl` cell:

      exec(open("install_crt_science.py").read())
      report = install_crt_science()                 # non-destructive default
      # to update items that already exist AND differ:
      # report = install_crt_science(overwrite=True)

  `host` is pre-injected in the repl kernel — no import needed. If the bundle
  file is not in the working directory, the installer locates it via
  host.artifacts() automatically (upload crt_science_bundle.json to the project
  first).

SAFETY MODEL  (engineered idempotent + non-destructive)
  - A skill/profile that does NOT exist is created.
  - A skill whose files are byte-identical to the bundle is a NO-OP ("current").
  - A skill/profile that exists but DIFFERS is SKIPPED and reported, UNLESS
    overwrite=True — so a re-run never silently clobbers the account's own
    same-named item.
  - Re-running with the same bundle changes nothing it already applied.
  - publish() runs the platform sidecar gate; a rejection is caught and
    reported per-skill, never swallowed.

POST-INSTALL VERIFICATION  (added v1.8 — the "no silent drift" guard)
  The v1.7 installer's one blind spot: an exists-but-differs skill was SKIPPED
  with only a stdout warning. If the caller (or a daemon login-reseed) didn't
  read that line, a stale skill silently survived a "successful" install — the
  exact failure the cross-org drift postmortem traced (a working org kept the
  pre-mandate plan/SKILL.md through repeated installs).

  The fix: the bundle now ships a content-hash MANIFEST (sha256 of every file
  of every skill + every identity field of every profile). After the install
  pass, `_verify_against_manifest()` RE-READS the account's LIVE skills/profiles,
  hashes them, and compares to the manifest. Any file/profile whose live hash
  != the bundle hash is DRIFT.
    - Drift is always reported prominently (report["verified"], report["drift"]).
    - With strict=True (the default), ANY residual drift RAISES
      InstallVerificationError — so a skipped-exists-differs skill can no longer
      pass as a clean install. The remedy is printed: re-run with overwrite=True.
  `verify_against_manifest(bundle_path)` is also callable standalone at any time
  as a one-command recheck (the recurrence guard against a later reseed).

Returns a structured report dict (also pretty-printed) so the run is auditable.
"""

import hashlib
import json
import os


BUNDLE_FILENAME = "crt_science_bundle.json"

# Profile identity fields the installer sets (and therefore verifies).
_PROFILE_FIELDS = ["display_name", "description", "system_prompt",
                   "icon_key", "color_key", "unrestricted"]


class InstallVerificationError(RuntimeError):
    """Raised when post-install content-hash verification finds residual drift."""


def _find_bundle(path=None):
    """Locate the bundle JSON: explicit path -> cwd -> host.artifacts fallback."""
    candidates = []
    if path:
        candidates.append(path)
    candidates.append(BUNDLE_FILENAME)
    candidates.append(os.path.join(os.getcwd(), BUNDLE_FILENAME))
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    # Fallback: resolve via the artifact store (repl kernel has `host`).
    try:
        hits = host.artifacts(filename=BUNDLE_FILENAME, exact=True, limit=5)  # noqa: F821
        arts = hits.get("artifacts") or []
        if arts:
            vid = arts[0]["latest_version_id"]
            return host.artifact_path(vid)  # noqa: F821
    except Exception:
        pass
    raise FileNotFoundError(
        f"Could not find {BUNDLE_FILENAME}. Put it in the working directory or "
        f"upload it to the project so host.artifacts() can resolve it."
    )


def _load_bundle(path=None):
    p = _find_bundle(path)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f), p


# ----------------------------------------------------------------------------
# Content-hash manifest (the verification substrate)
# ----------------------------------------------------------------------------
def _sha256_text(s):
    """sha256 of a text value; None normalizes to empty string."""
    if s is None:
        s = ""
    return hashlib.sha256(str(s).encode("utf-8")).hexdigest()


def _profile_field_value(pr_or_snapshot, field):
    """Canonical string form of a profile field for hashing (bundle- or live-shaped)."""
    v = pr_or_snapshot.get(field)
    if field == "unrestricted":
        return str(bool(v))
    return "" if v is None else str(v)


def compute_manifest(bundle):
    """Build the content-hash manifest from the bundle's own contents.
    skills:   name -> {relpath -> sha256(content)}
    profiles: name -> {field  -> sha256(canonical value)}
    This is authoritative: it hashes exactly what the bundle would install.
    """
    man = {"algo": "sha256", "skills": {}, "profiles": {}}
    for sk in bundle.get("skills", []):
        man["skills"][sk["name"]] = {
            p: _sha256_text(c) for p, c in sk["files"].items()
        }
    for pr in bundle.get("profiles", []):
        man["profiles"][pr["name"]] = {
            f: _sha256_text(_profile_field_value(pr, f)) for f in _PROFILE_FIELDS
        }
    return man


def _manifest_for(bundle):
    """Prefer a manifest SHIPPED in the bundle; else compute it. If both exist,
    assert they agree (a shipped manifest that disagrees with the bundle body is
    itself a defect and must fail loudly)."""
    computed = compute_manifest(bundle)
    shipped = bundle.get("manifest")
    if shipped:
        # Structural agreement check on the skills/profiles hash maps.
        if shipped.get("skills") != computed["skills"] or \
           shipped.get("profiles") != computed["profiles"]:
            mism = _manifest_mismatch_detail(shipped, computed)
            raise InstallVerificationError(
                "Shipped manifest disagrees with bundle contents — the bundle is "
                "internally inconsistent (rebuild it). Details: " + mism)
        return shipped
    return computed


def _manifest_mismatch_detail(a, b, limit=6):
    diffs = []
    for kind in ("skills", "profiles"):
        am, bm = a.get(kind, {}), b.get(kind, {})
        for name in sorted(set(am) | set(bm)):
            af, bf = am.get(name, {}), bm.get(name, {})
            for key in sorted(set(af) | set(bf)):
                if af.get(key) != bf.get(key):
                    diffs.append(f"{kind}:{name}:{key}")
    extra = "" if len(diffs) <= limit else f" (+{len(diffs) - limit} more)"
    return ", ".join(diffs[:limit]) + extra


# ----------------------------------------------------------------------------
# Skills
# ----------------------------------------------------------------------------
def _install_skill(sk, overwrite):
    """Create-or-update one skill from its bundle entry. Returns a status dict."""
    name = sk["name"]
    files = sk["files"]  # ordered dict path -> content (SKILL.md first)

    existing = {s["name"] for s in host.skills.list()}  # noqa: F821
    is_new = name not in existing

    # Determine current on-disk state for a differ/no-op decision.
    differs = True
    if not is_new:
        try:
            cur_listing = host.skills.read(name).get("files", [])  # noqa: F821
            cur = {}
            for pth in cur_listing:
                cur[pth] = host.skills.read(name, pth)["content"]  # noqa: F821
            differs = (cur != dict(files))
        except Exception:
            differs = True

    if not is_new and not differs:
        return {"name": name, "action": "current", "published": None,
                "detail": "byte-identical; no change"}

    if not is_new and differs and not overwrite:
        return {"name": name, "action": "skipped-exists-differs", "published": None,
                "detail": "exists and differs; re-run with overwrite=True to update"}

    # Create (new) or overwrite (existing+differs+overwrite) — file by file.
    for pth, content in files.items():
        try:
            # Try create first (works for a genuinely new file).
            host.skills.edit(name, pth, content, old_string=None)  # noqa: F821
        except Exception:
            # File already exists -> full-content overwrite via old_string=current.
            try:
                cur_content = host.skills.read(name, pth)["content"]  # noqa: F821
            except Exception:
                cur_content = None
            if cur_content is None:
                raise
            if cur_content == content:
                continue  # already current
            host.skills.edit(name, pth, content, old_string=cur_content)  # noqa: F821

    # Publish (runs the sidecar gate). Surface any rejection.
    try:
        pub = host.skills.publish(name, overwrite=True)  # noqa: F821
        pub_status = pub.get("status")
        gate = None
    except Exception as e:
        pub_status = "PUBLISH-FAILED"
        gate = str(e)[:300]

    return {"name": name,
            "action": ("created" if is_new else "overwritten"),
            "published": pub_status,
            "detail": gate}


# ----------------------------------------------------------------------------
# Profiles
# ----------------------------------------------------------------------------
def _profile_snapshot(rec):
    """Comparable field subset of a live profile record (camelCase wire keys)."""
    return {
        "display_name": rec.get("displayName"),
        "description": rec.get("description"),
        "system_prompt": rec.get("systemPrompt"),
        "icon_key": rec.get("iconKey"),
        "color_key": rec.get("colorKey"),
        "unrestricted": bool(rec.get("unrestricted")),
    }


def _install_profile(pr, overwrite):
    """Create-or-update one agent profile. Returns a status dict."""
    name = pr["name"]
    want = {
        "display_name": pr["display_name"],
        "description": pr["description"],
        "system_prompt": pr["system_prompt"],
        "icon_key": pr.get("icon_key"),
        "color_key": pr.get("color_key"),
        "unrestricted": bool(pr.get("unrestricted", True)),
    }

    live = {a["name"]: a for a in host.agents.list()}  # noqa: F821
    is_new = name not in live

    if not is_new:
        cur = _profile_snapshot(live[name])
        # Compare only the fields we set.
        differs = any(cur.get(k) != want.get(k) for k in want)
        if not differs:
            return {"name": name, "action": "current", "detail": "fields match; no change"}
        if not overwrite:
            return {"name": name, "action": "skipped-exists-differs",
                    "detail": "exists and differs; re-run with overwrite=True to update"}

    # CREATE if new. create() does NOT accept icon/color — set them via update().
    if is_new:
        # Leave skill_names unset for an unrestricted profile (full catalog +
        # all connectors). Pass the explicit list only for a curated profile.
        if want["unrestricted"]:
            host.agents.create(name, want["display_name"], want["description"],  # noqa: F821
                               system_prompt=want["system_prompt"])
        else:
            host.agents.create(name, want["display_name"], want["description"],  # noqa: F821
                               system_prompt=want["system_prompt"],
                               skill_names=pr.get("skill_names") or [])

    # UPDATE the full field set (idempotent patch; also sets icon/color, and
    # re-asserts identity on an overwrite of an existing profile).
    patch = {
        "display_name": want["display_name"],
        "description": want["description"],
        "system_prompt": want["system_prompt"],
    }
    if want["icon_key"] is not None:
        patch["icon_key"] = want["icon_key"]
    if want["color_key"] is not None:
        patch["color_key"] = want["color_key"]
    if want["unrestricted"]:
        patch["unrestricted"] = True  # keep full catalog + connectors
    host.agents.update(name, patch)  # noqa: F821

    return {"name": name, "action": ("created" if is_new else "overwritten"),
            "detail": None}


# ----------------------------------------------------------------------------
# Post-install verification (the "no silent drift" guard)
# ----------------------------------------------------------------------------
def _live_skill_hashes(name):
    """Re-read a live skill's files and return {relpath -> sha256(content)}.
    Returns None if the skill is absent."""
    existing = {s["name"] for s in host.skills.list()}  # noqa: F821
    if name not in existing:
        return None
    listing = host.skills.read(name).get("files", [])  # noqa: F821
    out = {}
    for pth in listing:
        out[pth] = _sha256_text(host.skills.read(name, pth)["content"])  # noqa: F821
    return out


def _live_profile_hashes(name):
    """Re-read a live profile and return {field -> sha256(canonical value)}.
    Returns None if the profile is absent."""
    live = {a["name"]: a for a in host.agents.list()}  # noqa: F821
    if name not in live:
        return None
    snap = _profile_snapshot(live[name])
    return {f: _sha256_text(_profile_field_value(snap, f)) for f in _PROFILE_FIELDS}


def _verify_against_manifest(bundle, manifest):
    """Compare the account's LIVE state to the manifest. Returns a per-item verdict
    list; any entry with status != 'verified' is drift."""
    results = []
    # Skills
    for name, want in manifest.get("skills", {}).items():
        live = _live_skill_hashes(name)
        if live is None:
            results.append({"kind": "skill", "name": name, "status": "MISSING",
                            "detail": "skill absent from account after install"})
            continue
        bad = []
        for pth, wh in want.items():
            lh = live.get(pth)
            if lh is None:
                bad.append(f"{pth}:absent")
            elif lh != wh:
                bad.append(f"{pth}:hash-mismatch")
        # extra live files are NOT drift (account may carry additions); only
        # missing-or-changed manifest files are.
        if bad:
            results.append({"kind": "skill", "name": name, "status": "DRIFT",
                            "detail": "; ".join(bad)})
        else:
            results.append({"kind": "skill", "name": name, "status": "verified",
                            "detail": None})
    # Profiles
    for name, want in manifest.get("profiles", {}).items():
        live = _live_profile_hashes(name)
        if live is None:
            results.append({"kind": "profile", "name": name, "status": "MISSING",
                            "detail": "profile absent from account after install"})
            continue
        bad = [f for f, wh in want.items() if live.get(f) != wh]
        if bad:
            results.append({"kind": "profile", "name": name, "status": "DRIFT",
                            "detail": "fields differ: " + ", ".join(sorted(bad))})
        else:
            results.append({"kind": "profile", "name": name, "status": "verified",
                            "detail": None})
    return results


def verify_against_manifest(bundle_path=None, verbose=True):
    """Standalone recheck: does the account's LIVE state match the bundle manifest?
    Callable any time (e.g. after a suspected login-reseed) — the recurrence guard.
    Returns {verified: bool, drift: [...], results: [...]}. Does not modify anything."""
    bundle, resolved = _load_bundle(bundle_path)
    manifest = _manifest_for(bundle)
    results = _verify_against_manifest(bundle, manifest)
    drift = [r for r in results if r["status"] != "verified"]
    out = {"bundle_version": bundle.get("bundle_version"), "bundle_path": resolved,
           "verified": not drift, "drift": drift, "results": results}
    if verbose:
        _print_verification(out)
    return out


def _print_verification(v):
    n = len(v["results"])
    ndrift = len(v["drift"])
    print(f"\nCONTENT-HASH VERIFICATION — {n} items checked against bundle "
          f"v{v.get('bundle_version')} manifest")
    if not ndrift:
        print("  \u2713 VERIFIED — every live skill/profile matches the bundle hash.")
        return
    print(f"  \u2717 DRIFT — {ndrift} item(s) do NOT match the bundle:")
    for r in v["drift"]:
        print(f"    [{r['status']:8s}] {r['kind']}:{r['name']}  — {r.get('detail')}")
    print("  Remedy: re-run install_crt_science(overwrite=True) to force these to "
          "the bundle version, then re-verify.")


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
def install_crt_science(bundle_path=None, overwrite=False, verbose=True, strict=True):
    """Replay the bundle, then VERIFY the account matches its content-hash manifest.

    strict=True (default): any residual drift after install RAISES
        InstallVerificationError — a skipped-exists-differs skill can no longer
        masquerade as a clean install. Set strict=False to get the drift report
        without raising (report["verified"] / report["drift"] still populated).

    Returns a structured, auditable report dict.
    """
    bundle, resolved = _load_bundle(bundle_path)
    manifest = _manifest_for(bundle)
    report = {
        "bundle": bundle.get("bundle_name"),
        "bundle_version": bundle.get("bundle_version"),
        "bundle_path": resolved,
        "overwrite": overwrite,
        "skills": [],
        "profiles": [],
        "verified": None,
        "drift": [],
    }

    for sk in bundle.get("skills", []):
        try:
            report["skills"].append(_install_skill(sk, overwrite))
        except Exception as e:
            report["skills"].append({"name": sk.get("name"), "action": "ERROR",
                                     "published": None, "detail": str(e)[:300]})

    for pr in bundle.get("profiles", []):
        try:
            report["profiles"].append(_install_profile(pr, overwrite))
        except Exception as e:
            report["profiles"].append({"name": pr.get("name"), "action": "ERROR",
                                       "detail": str(e)[:300]})

    # ---- POST-INSTALL VERIFICATION (content-hash, not action-log) ----
    verification = _verify_against_manifest(bundle, manifest)
    drift = [r for r in verification if r["status"] != "verified"]
    report["verified"] = not drift
    report["drift"] = drift
    report["verification"] = verification

    if verbose:
        def _tally(rows):
            t = {}
            for r in rows:
                t[r["action"]] = t.get(r["action"], 0) + 1
            return t
        print(f"CRT Science install — bundle: {report['bundle']} v{report['bundle_version']}")
        print(f"  source: {resolved}")
        print(f"  overwrite={overwrite}  strict={strict}\n")
        print(f"SKILLS ({len(report['skills'])}): {_tally(report['skills'])}")
        for r in report["skills"]:
            extra = f"  publish={r.get('published')}" if r.get("published") else ""
            det = f"  — {r['detail']}" if r.get("detail") else ""
            print(f"  [{r['action']:22s}] {r['name']}{extra}{det}")
        print(f"\nPROFILES ({len(report['profiles'])}): {_tally(report['profiles'])}")
        for r in report["profiles"]:
            det = f"  — {r['detail']}" if r.get("detail") else ""
            print(f"  [{r['action']:22s}] {r['name']}{det}")
        # Action-log problems (install-time).
        problems = [r for r in report["skills"] + report["profiles"]
                    if r["action"] in ("ERROR", "skipped-exists-differs")
                    or r.get("published") == "PUBLISH-FAILED"]
        if problems:
            print(f"\n\u26a0 {len(problems)} item(s) flagged during install "
                  f"(errors, publish-failures, or exists-differs skips).")
        # Content-hash verification (post-install truth — catches silent skips).
        _print_verification({"results": verification, "drift": drift,
                             "bundle_version": report["bundle_version"]})

    if strict and drift:
        raise InstallVerificationError(
            f"{len(drift)} item(s) drifted from bundle v{report['bundle_version']} "
            f"after install (overwrite={overwrite}). "
            f"First: {drift[0]['kind']}:{drift[0]['name']} ({drift[0]['status']}). "
            f"Re-run install_crt_science(overwrite=True) to force the bundle version. "
            f"Full drift list in report['drift'].")

    return report


if __name__ == "__main__":
    # Only meaningful inside a Claude Science repl kernel (needs `host`).
    install_crt_science()
