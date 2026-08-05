#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""check_bundle_parity.py -- VLOOP Item 4: bundle build-integrity gate.

Closes failure family F5 (CSRTB slice): a bundled engine silently lagged the live tool by
4 files, and malformed YAML frontmatter reached publish.

------------------------------------------------------------------------------------
THE OPERAND TRAP THIS EXISTS TO AVOID (adversarial-review catch)
------------------------------------------------------------------------------------
The bundle stores each skill file as a JSON *string field*, not as a file. So a naive
`sha256(open(path,'rb').read())` vs `sha256(json_string.encode())` MISMATCHES even with
zero drift, and would produce either false FAILs or -- worse -- false PASSes if you
hash the wrong side. The operands are therefore PINNED, and pinned to what the builder
actually does (verified empirically against v2.4: 77/77 files match with no normalization):

    builder embed transform : _read_text()  = open(path,'rb').read().decode('utf-8')
                              serialize()   = json.dumps(..., indent=2, ensure_ascii=False)

    DISK operand   : sha256( open(path,'rb').read().decode('utf-8').encode('utf-8') )
    BUNDLE operand : sha256( json_decoded_stored_string.encode('utf-8') )

i.e. compare TEXT to TEXT after reversing the embed transform (JSON decode), never
raw file bytes to a JSON string. `--strict-bytes` additionally asserts the disk file is
byte-identical to its own UTF-8 re-encoding, catching non-UTF-8 or BOM-prefixed files
that would decode-compare equal while differing on disk.

------------------------------------------------------------------------------------
THREE DIRECTIONS, KEPT DISTINCT (the canonical-direction catch)
------------------------------------------------------------------------------------
Project convention: the bundle JSON is the SOURCE OF TRUTH. So:

  --mode install   PRIMARY invariant. installed/served on-disk bytes == bundle's stored
                   bytes. Asserts what actually installs matches the canonical artifact.
  --mode build     SECONDARY guard. bundle's stored bytes == the bundle_src tree it was
                   built from ("did the builder embed what I edited"). Kept explicitly
                   distinct from --mode install, not conflated with it.
  --mode manifest  SELF-CONSISTENCY. the bundle's own embedded sha256 manifest matches
                   its own stored file bodies. Catches a manifest written from different
                   bytes than the bodies beside it.

Also gates YAML frontmatter (beyond parse-success, per review): every skill's SKILL.md
must parse AND carry non-empty mandatory keys `name` + `description`, and `name` must
equal the skill's directory name.

EXIT: 0 = PASS, 2 = FAIL (fail-closed), 3 = usage/IO error.
"""
import argparse
import hashlib
import json
import os
import sys


def sha_text(text):
    """The pinned operand: sha256 over UTF-8-encoded TEXT (post-embed-transform-reversal)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_ignorable(rel):
    """Cruft the builder deliberately does NOT embed -- MUST match
    build_crt_science_bundle.is_ignorable byte-for-byte, or this gate's OMITTED check
    and the builder's discovered set disagree (the gate would FAIL on a source tree the
    builder embedded correctly). Covers dotfiles, *.bak / *.bak_<epoch> editor backups,
    OS junk, byte-compiled caches. See that function for the trap this prevents."""
    parts = rel.split("/")
    if any(p == "__pycache__" for p in parts):
        return True
    base = parts[-1]
    if base.startswith("."):
        return True
    if base.endswith(("~", ".pyc", ".pyo", ".swp")):
        return True
    if ".bak" in base:
        return True
    return False


class NotUtf8(Exception):
    """A source file the builder could not have read. Raised so the gate reports a FAIL
    instead of dying with an uncaught UnicodeDecodeError (ADVERSARIAL FIX 2026-07-24)."""


def read_disk_text(path):
    """Mirror the builder's _read_text exactly."""
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        return raw.decode("utf-8"), raw
    except UnicodeDecodeError as exc:
        raise NotUtf8("%s is not valid UTF-8 (%s) -- the builder's _read_text would have "
                      "raised on it too, so this file could never have been bundled"
                      % (path, exc)) from exc


def load_bundle(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def parse_frontmatter(text):
    """Return (dict_or_None, error_str_or_None). Minimal YAML: top-level `key: value`
    plus `key: >-` / `|` block scalars -- enough for name/description, and it refuses
    anything it cannot parse rather than guessing."""
    if not text.startswith("---"):
        return None, "no frontmatter block (does not start with ---)"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "unterminated frontmatter block"
    body = text[3:end]
    try:
        import yaml  # noqa
    except ImportError:
        yaml = None
    # WHY A TOLERANT FALLBACK IS CORRECT HERE, with evidence (2026-07-24). The plan's PASS
    # criterion was "yaml.safe_load succeeds AND mandatory keys present". Requiring strict
    # YAML would REJECT WORKING SKILLS: of the SKILL.md files installed and loadable on
    # this platform, several fail yaml.safe_load with ScannerError -- e.g.
    # collab, durable-doc-architecture, folio-science, multi-source-fusion-bias-correction,
    # scanned-pdf-ocr, solo -- and two of those (collab, solo) are PLATFORM-SHIPPED. The
    # cause is unquoted ': ' inside description prose. So a strict gate would fail the
    # platform's own skills; the tolerant reader matches what the loader actually accepts.
    # What is NOT relaxed: mandatory keys must still be present and non-empty (null included),
    # and an unterminated frontmatter block is still a hard FAIL.
    if yaml is not None:
        try:
            data = yaml.safe_load(body)
            if not isinstance(data, dict):
                return None, "frontmatter did not parse to a mapping"
            return data, None
        except Exception as exc:
            # A strict-YAML scanner error is NOT automatically a defect: real shipped
            # frontmatter carries unquoted ':' inside description prose, which the live
            # platform accepts. Fall through to the tolerant reader, which mirrors the
            # platform's own lenient key extraction, rather than failing the build on a
            # parser stricter than the consumer.
            first = str(exc).splitlines()[0][:120]
            data, err = _tolerant_frontmatter(body)
            if data:
                return data, None
            return None, "yaml parse failed (%s) and tolerant read also failed: %s" % (
                first, err)
    return _tolerant_frontmatter(body)


def _tolerant_frontmatter(body):
    """Lenient top-level `key: value` reader, incl. >- / | block scalars."""
    data, cur, buf = {}, None, []
    for line in body.splitlines():
        if not line.strip():
            continue
        if line[0] not in " \t" and ":" in line:
            if cur is not None:
                data[cur] = " ".join(buf).strip()
            k, v = line.split(":", 1)
            cur, v = k.strip(), v.strip()
            buf = [] if v in (">-", ">", "|", "|-", "") else [v]
        elif cur is not None:
            buf.append(line.strip())
    if cur is not None:
        data[cur] = " ".join(buf).strip()
    return (data, None) if data else (None, "frontmatter parsed to nothing")


def cmp_trees(bundle, get_disk_text, label_disk, strict_bytes=False):
    """Compare every bundle-stored file against a disk-resolved counterpart."""
    fails, checked, missing = [], 0, 0
    for sk in bundle.get("skills", []):
        name = sk["name"]
        for rel, stored in sk["files"].items():
            try:
                got = get_disk_text(name, rel)
            except NotUtf8 as exc:
                fails.append("NOT UTF-8 %s/%s: %s" % (name, rel, exc))
                checked += 1
                continue
            if got is None:
                missing += 1
                fails.append("MISSING on %s: %s/%s (in bundle, absent on disk)"
                             % (label_disk, name, rel))
                continue
            disk_text, disk_raw = got
            checked += 1
            if sha_text(disk_text) != sha_text(stored):
                fails.append("DRIFT %s/%s: %s sha %s != bundle sha %s (%d vs %d chars)"
                             % (name, rel, label_disk, sha_text(disk_text)[:12],
                                sha_text(stored)[:12], len(disk_text), len(stored)))
            elif strict_bytes:
                # ADVERSARIAL FIX 2026-07-24 (MAJOR): the old predicate
                # `disk_raw != disk_text.encode("utf-8")` was a DEAD CHECK for both cases
                # its docstring named. A UTF-8 BOM round-trips through decode/encode
                # byte-identically (b"\xef\xbb\xbf...".decode().encode() == original), so it
                # never fired; and a genuinely non-UTF-8 file raises UnicodeDecodeError up
                # in read_disk_text before this line is ever reached, producing a traceback
                # instead of the documented FAIL. Test the byte prefix directly instead.
                if disk_raw.startswith(b"\xef\xbb\xbf"):
                    fails.append("BOM %s/%s: file begins with a UTF-8 BOM. It decode-compares "
                                 "equal to the bundle, but the leading U+FEFF is real content "
                                 "on disk and breaks tools that expect a bare '---' or shebang "
                                 "on byte 0." % (name, rel))
                # NO UTF-16 branch here, deliberately: a UTF-16 BOM (b"\xff\xfe" /
                # b"\xfe\xff") is not valid UTF-8, so read_disk_text raises NotUtf8 and
                # cmp_trees reports "NOT UTF-8 ..." before this block runs. Verified:
                # (b"\xff\xfe" + text.encode("utf-16-le")).decode("utf-8") -> UnicodeDecodeError.
                # A branch that can never fire is the same dead check this section just fixed.
                elif disk_raw != disk_text.encode("utf-8"):
                    fails.append("NON-CANONICAL BYTES %s/%s: decodes equal but on-disk bytes "
                                 "differ from their UTF-8 re-encoding." % (name, rel))
    return fails, checked, missing


def extra_on_disk(bundle, skills_root):
    """Files present in a skill dir but NOT in the bundle -- the reverse of MISSING.
    Without this, a bundle that silently omitted a file would still pass."""
    fails = []
    if not (skills_root and os.path.isdir(skills_root)):
        return fails
    in_bundle = {(sk["name"], rel) for sk in bundle.get("skills", []) for rel in sk["files"]}
    bundled_skills = {sk["name"] for sk in bundle.get("skills", [])}
    # ADVERSARIAL FIX 2026-07-24 (CRITICAL, confirmed by reproduction): the old loop did
    # `if ... or sk not in bundled_skills: continue`, so a skill dir present on disk whose
    # NAME was absent from the bundle was SKIPPED -- omitting a WHOLE skill passed the gate.
    # cmp_trees only walks bundle->disk, so nothing else caught it. A per-file guard cannot
    # see a missing name; the set difference can.
    disk_skills = {d for d in os.listdir(skills_root)
                   if os.path.isdir(os.path.join(skills_root, d)) and not d.startswith(".")}
    for sk in sorted(disk_skills - bundled_skills):
        fails.append("SKILL OMITTED FROM BUNDLE: %s is a skill dir on disk but its name is "
                     "absent from bundle['skills']" % sk)
    for sk in sorted(os.listdir(skills_root)):
        d = os.path.join(skills_root, sk)
        if not os.path.isdir(d) or sk not in bundled_skills:
            continue
        for root, _dirs, names in os.walk(d):
            for n in names:
                rel = os.path.relpath(os.path.join(root, n), d).replace(os.sep, "/")
                if is_ignorable(rel):        # mirrors the builder's skip set
                    continue
                if (sk, rel) not in in_bundle:
                    fails.append("OMITTED FROM BUNDLE: %s/%s exists on disk but is not "
                                 "in the bundle" % (sk, rel))
    return fails


def check_frontmatter(bundle):
    fails = 0
    out = []
    for sk in bundle.get("skills", []):
        name = sk["name"]
        body = sk["files"].get("SKILL.md")
        if body is None:
            out.append("FRONTMATTER %s: no SKILL.md in bundle" % name)
            fails += 1
            continue
        data, err = parse_frontmatter(body)
        if err:
            out.append("FRONTMATTER %s: %s" % (name, err))
            fails += 1
            continue
        for key in ("name", "description"):
            v = data.get(key)
            # NOTE: do NOT write str(v).strip() here -- yaml maps an empty value
            # (`description:`) to None, and str(None) == "None" is NON-empty, so that
            # form silently PASSES an empty mandatory key. This exact false-green was
            # caught by the planted empty-description fixture; the None check is the fix.
            if v is None or not str(v).strip():
                out.append("FRONTMATTER %s: mandatory key %r missing or empty (value=%r)"
                           % (name, key, v))
                fails += 1
        nm = data.get("name")
        if nm is not None and str(nm).strip() and str(nm).strip() != name:
            out.append("FRONTMATTER %s: frontmatter name %r != skill dir name"
                       % (name, str(nm).strip()))
            fails += 1
    return out, fails


def check_manifest(bundle):
    man = bundle.get("manifest") or {}
    if man.get("algo") != "sha256":
        return ["MANIFEST: algo is %r, expected sha256" % man.get("algo")], 1
    fails = []
    mskills = man.get("skills") or {}
    for sk in bundle.get("skills", []):
        name = sk["name"]
        entry = mskills.get(name)
        if entry is None:
            fails.append("MANIFEST: no entry for skill %s" % name)
            continue
        for rel, stored in sk["files"].items():
            want = entry.get(rel)
            if want is None:
                fails.append("MANIFEST: %s/%s absent from manifest" % (name, rel))
            elif want != sha_text(stored):
                fails.append("MANIFEST: %s/%s sha mismatch (manifest %s vs body %s)"
                             % (name, rel, str(want)[:12], sha_text(stored)[:12]))
        for rel in entry:
            if rel not in sk["files"]:
                fails.append("MANIFEST: %s/%s in manifest but not in stored files"
                             % (name, rel))
    for name in mskills:
        if name not in {sk["name"] for sk in bundle.get("skills", [])}:
            fails.append("MANIFEST: skill %s in manifest but not in bundle" % name)
    return fails, len(fails)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True, help="crt_science_bundle.json (canonical)")
    ap.add_argument("--mode", required=True,
                    choices=["install", "build", "manifest", "all"])
    ap.add_argument("--src", help="bundle_src dir (--mode build)")
    ap.add_argument("--installed-root", help="served skills dir (--mode install)")
    ap.add_argument("--strict-bytes", action="store_true",
                    help="also require on-disk bytes == UTF-8 re-encoding")
    ap.add_argument("--skip-frontmatter", action="store_true")
    a = ap.parse_args(argv)

    try:
        bundle = load_bundle(a.bundle)
    except Exception as exc:
        print("cannot load bundle: %s" % exc)
        return 3

    modes = ["install", "build", "manifest"] if a.mode == "all" else [a.mode]
    all_fails, ran = [], []

    if "install" in modes:
        if not a.installed_root:
            print("--mode install requires --installed-root")
            return 3
        def get(name, rel, root=a.installed_root):
            p = os.path.join(root, name, rel)
            return read_disk_text(p) if os.path.exists(p) else None
        f, n, miss = cmp_trees(bundle, get, "installed", a.strict_bytes)
        all_fails += f
        ran.append("install (PRIMARY: served bytes == bundle bytes): %d files, %d missing"
                   % (n, miss))

    if "build" in modes:
        if not a.src:
            print("--mode build requires --src")
            return 3
        skills_root = os.path.join(a.src, "skills")
        def get(name, rel, root=skills_root):
            p = os.path.join(root, name, rel)
            return read_disk_text(p) if os.path.exists(p) else None
        f, n, miss = cmp_trees(bundle, get, "bundle_src", a.strict_bytes)
        f += extra_on_disk(bundle, skills_root)
        all_fails += f
        ran.append("build (SECONDARY: bundle bytes == bundle_src): %d files, %d missing"
                   % (n, miss))

    if "manifest" in modes:
        f, _ = check_manifest(bundle)
        all_fails += f
        nman = sum(len(v) for v in (bundle.get("manifest", {}).get("skills") or {}).values())
        ran.append("manifest (SELF: embedded sha manifest == stored bodies): %d entries" % nman)

    if not a.skip_frontmatter:
        f, _ = check_frontmatter(bundle)
        all_fails += f
        ran.append("frontmatter (parse + non-empty name/description + name==dir): %d skills"
                   % len(bundle.get("skills", [])))

    print("bundle   : %s (v%s, %d skills, %d profiles)"
          % (os.path.basename(a.bundle), bundle.get("bundle_version"),
             len(bundle.get("skills", [])), len(bundle.get("profiles", []))))
    for r in ran:
        print("  ran    : %s" % r)

    if all_fails:
        print("\nPARITY GATE: FAIL (%d)" % len(all_fails))
        for x in all_fails[:60]:
            print("  - %s" % x)
        if len(all_fails) > 60:
            print("  ... +%d more" % (len(all_fails) - 60))
        return 2
    print("\nPARITY GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
