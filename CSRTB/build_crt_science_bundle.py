#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""
build_crt_science_bundle.py — reconstruct crt_science_bundle.json from a content source tree.

Reverse-engineered from crt_science_bundle.json v1.2 (md5 e09be0c25223e183a0572f1ee194c823).
This is the missing builder: the original bundle was assembled programmatically in the source
project and only its output was saved. This script re-derives that output from file content on
disk, applying the exact assembly + serialization rules recovered by forensic analysis.

WHAT IS DERIVED FROM CONTENT (computed here, never copied from a reference bundle):
  - skills[]           : discovered from <src>/skills/<name>/**, one entry per skill dir
  - skills[].files     : {relpath: text}, keys in sorted() order
  - skills[].bytes     : sum(len(text) for text in files.values())   # CHARACTER count (str len), not UTF-8 bytes
  - skills[].has_sidecar: ("kernel.py" in files) or ("kernel.R" in files)
  - profiles[]         : discovered from <src>/profiles/<name>.json
  - profiles[].skill_names: None if the profile is unrestricted else its skillNames list
  - counts             : {"skills": len(skills), "profiles": len(profiles)}
  - list ordering      : skills + profiles both sorted by name (ascending)

WHAT IS BUILD CONFIG (frozen inputs a builder is given, not derivable from content):
  - bundle_name, bundle_version, created_utc, source_project, note, dropped
  These come from --config JSON (or CLI flags). For a bit-for-bit RECREATE of an existing
  bundle, pass that bundle's own values (that is the only surviving record of the build inputs).

SERIALIZATION (exact):
  json.dumps(obj, indent=2, ensure_ascii=False) encoded UTF-8, with NO trailing newline.

SOURCE TREE LAYOUT:
  <src>/skills/<skill-name>/SKILL.md                 (+ kernel.py / kernel.R / scripts/*.py ...)
  <src>/profiles/<PROFILE_NAME>.json                 ({name, display_name, description,
                                                       system_prompt, icon_key, color_key,
                                                       unrestricted, skillNames})

USAGE:
  # recreate test — source tree holds exactly the bundled items:
  python3 build_crt_science_bundle.py --src bundle_src --config build_config.json --out rebuilt.json

  # future real rebuild from a larger export, restricted to a manifest:
  python3 build_crt_science_bundle.py --src live_export --config cfg.json \
      --only-skills manifest_skills.txt --only-profiles manifest_profiles.txt --out new.json

TOKENS: this file contains no project-specific data; all specifics arrive via --src and --config.
"""
import argparse
import hashlib
import json
import os
import sys


# `manifest` is placed LAST so the skills/profiles bodies serialize first and the
# manifest reads as a trailing content-hash appendix. It ships INSIDE the bundle
# so install_crt_science.py can verify the account's live state against it.
TOP_KEY_ORDER = ["bundle_name", "bundle_version", "created_utc", "source_project",
                 "note", "counts", "dropped", "skills", "profiles", "manifest"]

# Profile identity fields that get hashed into the manifest — MUST match the set
# install_crt_science.py verifies (_PROFILE_FIELDS there).
MANIFEST_PROFILE_FIELDS = ["display_name", "description", "system_prompt",
                           "icon_key", "color_key", "unrestricted"]
SKILL_KEY_ORDER = ["name", "files", "has_sidecar", "bytes"]
PROFILE_KEY_ORDER = ["name", "display_name", "description", "system_prompt",
                     "icon_key", "color_key", "unrestricted", "skill_names"]


def _read_text(path):
    """Read a file as UTF-8 text. len() of the result is the CHARACTER count used by `bytes`."""
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")


def is_ignorable(rel):
    """True for cruft that must NEVER be embedded in the bundle: dotfiles, editor
    backups, tool-written *.bak_<epoch> snapshots, OS junk, and byte-compiled caches.

    WHY THIS EXISTS (a real trap this build hit, 2026-07-26): edit_file and similar
    tools drop `SKILL.md.bak_<epoch>` beside the file they edit. os.walk() embeds
    EVERYTHING, so without this filter a rebuild would silently fold those backups
    into the shipped JSON as if they were skill content -- and, symmetrically, the
    parity gate's OMITTED-from-bundle check would FAIL on a clean source tree. This
    predicate is MIRRORED byte-for-byte in check_bundle_parity.is_ignorable so the
    builder's discovered set and the gate's expected set can never disagree.
    """
    parts = rel.split("/")
    if any(p == "__pycache__" for p in parts):
        return True
    base = parts[-1]
    if base.startswith("."):                       # .DS_Store, .gitkeep, any dotfile
        return True
    if base.endswith(("~", ".pyc", ".pyo", ".swp")):
        return True
    if ".bak" in base:                             # foo.bak, SKILL.md.bak_1784955921
        return True
    return False


def discover_skill(skill_dir):
    """Return {relpath: text} for every NON-cruft file under a skill dir (keys later
    sorted at assembly). Cruft (see is_ignorable) is skipped so a stray editor backup
    or OS junk file can never leak into the bundle."""
    files = {}
    for root, _dirs, names in os.walk(skill_dir):
        for n in names:
            full = os.path.join(root, n)
            rel = os.path.relpath(full, skill_dir).replace(os.sep, "/")
            if is_ignorable(rel):
                continue
            files[rel] = _read_text(full)
    return files


def build_skill_entry(name, files):
    ordered_files = {k: files[k] for k in sorted(files)}          # file keys sorted
    entry = {
        "name": name,
        "files": ordered_files,
        "has_sidecar": ("kernel.py" in ordered_files) or ("kernel.R" in ordered_files),
        "bytes": sum(len(text) for text in ordered_files.values()),   # str len == char count
    }
    return {k: entry[k] for k in SKILL_KEY_ORDER}


def build_profile_entry(rec):
    unrestricted = bool(rec.get("unrestricted"))
    skill_names = None if unrestricted else (rec.get("skillNames") or rec.get("skill_names") or [])
    entry = {
        "name": rec["name"],
        "display_name": rec["display_name"],
        "description": rec["description"],
        "system_prompt": rec["system_prompt"],
        "icon_key": rec["icon_key"],
        "color_key": rec["color_key"],
        "unrestricted": unrestricted,
        "skill_names": skill_names,
    }
    return {k: entry[k] for k in PROFILE_KEY_ORDER}


def _load_manifest(path):
    if not path:
        return None
    with open(path, encoding="utf-8") as fh:
        return {ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")}


def _sha256_text(s):
    """sha256 of a text value; None -> empty string. Matches install_crt_science._sha256_text."""
    if s is None:
        s = ""
    return hashlib.sha256(str(s).encode("utf-8")).hexdigest()


def build_manifest(skills, profiles):
    """Content-hash manifest over the ASSEMBLED bundle entries (post-sort, post-serialize
    content). Hashes exactly the strings the installer will read back from the account, so
    install-time verification is a true byte-for-byte check. Structure mirrors
    install_crt_science.compute_manifest():
        skills:   name -> {relpath -> sha256(file content)}
        profiles: name -> {field  -> sha256(canonical field value)}
    """
    man = {"algo": "sha256", "skills": {}, "profiles": {}}
    for sk in skills:
        man["skills"][sk["name"]] = {p: _sha256_text(c) for p, c in sk["files"].items()}
    for pr in profiles:
        fh = {}
        for f in MANIFEST_PROFILE_FIELDS:
            v = pr.get(f)
            canon = str(bool(v)) if f == "unrestricted" else ("" if v is None else str(v))
            fh[f] = _sha256_text(canon)
        man["profiles"][pr["name"]] = fh
    return man


def build_bundle(src, config, only_skills=None, only_profiles=None):
    skills_root = os.path.join(src, "skills")
    profiles_root = os.path.join(src, "profiles")

    # --- skills ---
    skill_names = [d for d in os.listdir(skills_root)
                   if os.path.isdir(os.path.join(skills_root, d))]
    if only_skills is not None:
        skill_names = [n for n in skill_names if n in only_skills]
    skills = [build_skill_entry(n, discover_skill(os.path.join(skills_root, n)))
              for n in sorted(skill_names)]                        # skills sorted by name

    # --- profiles ---
    prof_files = [f for f in os.listdir(profiles_root) if f.endswith(".json")]
    profiles = []
    for f in sorted(prof_files):
        rec = json.load(open(os.path.join(profiles_root, f), encoding="utf-8"))
        if only_profiles is not None and rec["name"] not in only_profiles:
            continue
        profiles.append((rec["name"], rec))
    profiles = [build_profile_entry(rec) for _n, rec in sorted(profiles, key=lambda x: x[0])]

    # --- assemble top-level in exact key order ---
    obj = {
        "bundle_name": config["bundle_name"],
        "bundle_version": config["bundle_version"],
        "created_utc": config["created_utc"],
        "source_project": config["source_project"],
        "note": config["note"],
        "counts": {"skills": len(skills), "profiles": len(profiles)},
        "dropped": config["dropped"],
        "skills": skills,
        "profiles": profiles,
        # content-hash manifest of exactly these assembled entries (the install-time
        # verification substrate). Built LAST so it hashes the final sorted content.
        "manifest": build_manifest(skills, profiles),
    }
    return {k: obj[k] for k in TOP_KEY_ORDER}


def serialize(obj):
    """Exact bundle serialization: 2-space indent, non-ASCII kept raw, NO trailing newline."""
    return json.dumps(obj, indent=2, ensure_ascii=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build crt_science_bundle.json from a source tree.")
    ap.add_argument("--src", required=True, help="source tree with skills/ and profiles/")
    ap.add_argument("--config", required=True, help="build-config JSON (frozen metadata + dropped)")
    ap.add_argument("--out", required=True, help="output bundle JSON path")
    ap.add_argument("--only-skills", help="optional file: newline-list of skill names to include")
    ap.add_argument("--only-profiles", help="optional file: newline-list of profile names to include")
    args = ap.parse_args(argv)

    config = json.load(open(args.config, encoding="utf-8"))
    obj = build_bundle(args.src, config,
                       only_skills=_load_manifest(args.only_skills),
                       only_profiles=_load_manifest(args.only_profiles))
    data = serialize(obj).encode("utf-8")
    with open(args.out, "wb") as fh:
        fh.write(data)
    print(f"wrote {args.out}: {len(data)} bytes, "
          f"{obj['counts']['skills']} skills, {obj['counts']['profiles']} profiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
