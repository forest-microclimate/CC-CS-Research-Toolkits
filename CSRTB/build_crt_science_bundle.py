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
  - profiles[]         : discovered from <src>/profiles/<name>.json, with any
                          `{{FRAGMENT:<id>}}` token in system_prompt EXPANDED against
                          <src>/fragments/<id>.* before the profile entry is built (see
                          FRAGMENT MECHANISM below) -- the manifest hashes the EXPANDED text,
                          i.e. exactly what ships, never the raw un-expanded source.
  - profiles[].skill_names: None if the profile is unrestricted else its skillNames list
  - counts             : {"skills": len(skills), "profiles": len(profiles)}
  - list ordering      : skills + profiles both sorted by name (ascending)

FRAGMENT MECHANISM (source-level single-sourcing; Rc2, 2026-08-05):
  Several profiles' system_prompt fields duplicated the SAME standing-behavior block
  verbatim (audible-alert: 17 of 18 profiles, one canonical body; self-scan: 15 of 18,
  two named variants -- see bundle_src/fragments/*.md for the canonical bodies and
  dev/reports/Rc2_*.md for the measurement). Rather than 32 inline copies, a profile's
  system_prompt now carries an include token, `{{FRAGMENT:<id>}}`, and the builder
  expands it VERBATIM (a straight substring substitution -- not templated/parameterized,
  because the measured variants are byte-exact fixed alternatives, not a single family
  with a plug-in slot) against a same-named file under <src>/fragments/. This is a PURE
  SOURCE refactor: the fragment file's content is byte-identical to what used to be
  inlined, so an unchanged bundle_src tree still rebuilds a byte-identical bundle.
  FAIL-CLOSED: a token whose id has no matching fragment file makes the WHOLE build
  refuse loudly (FragmentResolutionError, naming every offending profile+id) rather than
  ship a live system_prompt that still contains a literal unresolved token.

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
import re
import sys


# Include-token grammar for the fragment mechanism (see module docstring FRAGMENT
# MECHANISM). Deliberately narrow charset (id = letters/digits/_/-) so a token is easy
# to eyeball and a malformed one (stray space, wrong bracket count) simply fails to
# match -- and therefore ships literally into the profile text, which the sanity check
# in expand_fragments below is designed to still catch (it re-scans for the "{{FRAGMENT:"
# lead-in even where the full pattern didn't match, e.g. an unclosed token).
FRAGMENT_TOKEN_RE = re.compile(r"\{\{FRAGMENT:([A-Za-z0-9_-]+)\}\}")


class FragmentResolutionError(RuntimeError):
    """Raised by build_bundle when one or more profiles reference a fragment id with no
    file under <src>/fragments/, or carry a malformed/unclosed token. Fail-closed: the
    caller (main()) must treat this as a hard build refusal, never a partial write."""


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


def discover_fragments(src):
    """Return {fragment_id: text} for every non-cruft file directly under <src>/fragments/
    (non-recursive; is_ignorable applies the same dotfile/.bak/__pycache__ filter as
    skill discovery). fragment_id = filename stem (e.g. "audible_alert.md" -> "audible_alert").

    Each fragment's trailing newline(s) are stripped at READ time (not baked out of the
    file on disk): this lets a fragment file follow the ordinary text-file convention of
    ending in a single newline without that newline leaking into every include site --
    the profile source's OWN text on either side of the token supplies whatever seam
    whitespace belongs there, exactly as it did before the fragment existed (verified:
    see T1 boundary-artifact note in the module docstring / Rc2 report).

    Returns {} if <src>/fragments/ does not exist -- fragments are OPTIONAL; a source
    tree with no fragments dir builds exactly as it did before this mechanism existed.
    """
    frag_root = os.path.join(src, "fragments")
    fragments = {}
    if not os.path.isdir(frag_root):
        return fragments
    for n in sorted(os.listdir(frag_root)):
        full = os.path.join(frag_root, n)
        if not os.path.isfile(full) or is_ignorable(n):
            continue
        fid = os.path.splitext(n)[0]
        fragments[fid] = _read_text(full).rstrip("\n")
    return fragments


def expand_fragments(text, fragments, profile_name, unresolved):
    """Replace every well-formed {{FRAGMENT:id}} token in `text` with fragments[id],
    VERBATIM (a straight substring substitution; see module docstring for why this is
    verbatim-per-named-variant rather than a parameterized template).

    An id with no matching fragment file is NOT substituted -- it is appended to
    `unresolved` as (profile_name, fid) and the literal token text is left in place, so
    the caller (build_bundle) can refuse the WHOLE build with every offending
    profile+id named, rather than silently shipping a live system_prompt that still
    contains an unresolved token.

    Fail-closed on a MALFORMED token too: after substitution, if the literal lead-in
    "{{FRAGMENT:" still appears anywhere in the result, that is an unclosed or otherwise
    malformed token the regex could not parse (e.g. a stray space before the colon, or a
    missing closing "}}") -- it is recorded into `unresolved` under the id "<malformed>"
    so the same fail-closed refusal path catches it too.
    """
    def _sub(m):
        fid = m.group(1)
        if fid not in fragments:
            unresolved.append((profile_name, fid))
            return m.group(0)          # leave the token literally; build_bundle refuses
        return fragments[fid]
    out = FRAGMENT_TOKEN_RE.sub(_sub, text)
    if "{{FRAGMENT:" in out:
        # a malformed token slipped past the regex (e.g. missing "}}") -- still refuse
        unresolved.append((profile_name, "<malformed-token>"))
    return out


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
    fragments = discover_fragments(src)

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
    unresolved = []
    for f in sorted(prof_files):
        rec = json.load(open(os.path.join(profiles_root, f), encoding="utf-8"))
        if only_profiles is not None and rec["name"] not in only_profiles:
            continue
        # Expand any {{FRAGMENT:id}} include token BEFORE the profile entry is built, so
        # the manifest hashes the assembled (shipped) text -- never the raw source. A
        # profile with no tokens is unaffected (expand_fragments is then a no-op).
        rec["system_prompt"] = expand_fragments(
            rec.get("system_prompt", ""), fragments, rec["name"], unresolved)
        profiles.append((rec["name"], rec))
    if unresolved:
        detail = "; ".join("%s -> {{FRAGMENT:%s}}" % (p, i) for p, i in unresolved)
        raise FragmentResolutionError(
            "build REFUSED: %d unresolved fragment include(s): %s -- add the missing "
            "fragment file(s) under %s or fix the profile source."
            % (len(unresolved), detail, os.path.join(src, "fragments")))
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
    try:
        obj = build_bundle(args.src, config,
                           only_skills=_load_manifest(args.only_skills),
                           only_profiles=_load_manifest(args.only_profiles))
    except FragmentResolutionError as exc:
        print("FRAGMENT GATE: FAIL", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 2
    data = serialize(obj).encode("utf-8")
    with open(args.out, "wb") as fh:
        fh.write(data)
    print(f"wrote {args.out}: {len(data)} bytes, "
          f"{obj['counts']['skills']} skills, {obj['counts']['profiles']} profiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
