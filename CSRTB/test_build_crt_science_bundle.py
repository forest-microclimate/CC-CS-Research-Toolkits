#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""test_build_crt_science_bundle.py -- red-before-green tests for the fragment/include
mechanism added to build_crt_science_bundle.py (Rc2, 2026-08-05).

Every gate is shown able to FAIL before it is trusted to pass, per this project's house
testing convention (see dev/tools/test_derive_public_release.py):

  T1  expansion        a fixture profile carrying a {{FRAGMENT:id}} token builds with the
                       token replaced VERBATIM by the fragment file's content, and the
                       bundle's own manifest hashes the EXPANDED text (not the raw token)
  T2  red: missing     a token naming a fragment id with NO file under fragments/ ->
                       build_bundle() RAISES FragmentResolutionError naming the profile +
                       the missing id; the CLI (main()) exits 2 with the message on stderr
  T3  red: malformed   an unclosed/malformed token (no closing "}}") is NOT silently left
                       in the shipped prompt -> also raises FragmentResolutionError
  T4  no-fragments     a bundle_src tree with NO fragments/ dir and NO tokens in any
                       profile builds EXACTLY as it did before this mechanism existed
                       (backward-compatibility / regression guard)
  T5  idempotency      two consecutive builds of the SAME source tree are byte-identical
  T6  real-tree accept builds the REAL production bundle_src + build_config.json and
                       asserts (a) it succeeds, (b) no profile's expanded system_prompt
                       still contains a "{{FRAGMENT:" token, (c) the canonical fragment
                       bodies are recoverable verbatim inside every profile that includes
                       them, matching the fragment file's own on-disk content exactly

USAGE:  python3 test_build_crt_science_bundle.py
EXIT:   0 = every check passes; 1 = at least one failed.
"""
import io
import json
import os
import shutil
import sys
import time
import contextlib

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))  # workspace root
sys.path.insert(0, HERE)
import build_crt_science_bundle as B          # noqa: E402

RUN_ID = os.environ.get("RC2_RUN_ID") or time.strftime("%Y%m%d_%H%M%S")
FX_ROOT = os.environ.get("RC2_FIXTURE_ROOT") or os.path.join(WS, "sandbox", "Rc2_scratch", "T4_fixtures")
FX = os.path.join(FX_ROOT, RUN_ID)            # run-scoped: nothing is ever deleted

REAL_SRC = os.path.join(HERE, "bundle_src")
REAL_CONFIG = os.path.join(HERE, "build_config.json")


# ------------------------------------------------------------------ fixture helpers --

def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _profile_json(name, system_prompt):
    return json.dumps({
        "name": name,
        "display_name": name.title(),
        "description": "fixture profile for Rc2 tests",
        "system_prompt": system_prompt,
        "icon_key": "lightning",
        "color_key": "accent-main",
        "unrestricted": True,
        "skillNames": None,
    }, indent=2, ensure_ascii=False)


def _config():
    return json.dumps({
        "bundle_name": "fixture-bundle",
        "bundle_version": "0.0-test",
        "created_utc": "2026-08-05T00:00:00Z",
        "source_project": "test_build_crt_science_bundle.py",
        "note": "fixture; not a real bundle",
        "dropped": {"skills": [], "profiles": [], "note": "n/a"},
    }, indent=2)


def make_base_tree(tag):
    """A minimal 2-profile, 1-skill, 1-fragment tree. Returns (src_dir, config_path)."""
    root = os.path.join(FX, tag)
    if os.path.isdir(root):
        shutil.rmtree(root)
    src = os.path.join(root, "src")
    _write(os.path.join(src, "skills", "dummy_skill", "SKILL.md"),
           "---\nname: dummy_skill\ndescription: a fixture skill\n---\nbody text.")
    _write(os.path.join(src, "fragments", "greeting.md"),
           "## Greeting\nHello from the shared fragment.\n")   # note trailing \n on purpose
    _write(os.path.join(src, "profiles", "ALPHA.json"),
           _profile_json("ALPHA", "Alpha intro.\n\n{{FRAGMENT:greeting}}\n\nAlpha outro."))
    _write(os.path.join(src, "profiles", "OMEGA.json"),
           _profile_json("OMEGA", "Omega intro.\n\n{{FRAGMENT:greeting}}"))
    cfg = os.path.join(root, "build_config.json")
    _write(cfg, _config())
    return src, cfg


# ------------------------------------------------------------------------- T1, T2, T3 --

def test_expansion_verbatim_and_manifest():
    src, cfg = make_base_tree("t1")
    config = json.load(open(cfg, encoding="utf-8"))
    obj = B.build_bundle(src, config)
    profs = {p["name"]: p for p in obj["profiles"]}
    expected_frag = "## Greeting\nHello from the shared fragment."   # rstripped at read time
    assert "{{FRAGMENT:" not in profs["ALPHA"]["system_prompt"], "token leaked unexpanded (ALPHA)"
    assert "{{FRAGMENT:" not in profs["OMEGA"]["system_prompt"], "token leaked unexpanded (OMEGA)"
    assert profs["ALPHA"]["system_prompt"] == "Alpha intro.\n\n%s\n\nAlpha outro." % expected_frag, \
        "ALPHA expansion did not reproduce the exact surrounding text"
    assert profs["OMEGA"]["system_prompt"] == "Omega intro.\n\n%s" % expected_frag, \
        "OMEGA expansion did not reproduce the exact surrounding text"
    # manifest must hash the EXPANDED text, not the raw token
    want = B._sha256_text(profs["ALPHA"]["system_prompt"])
    got = obj["manifest"]["profiles"]["ALPHA"]["system_prompt"]
    assert got == want, "manifest hashed something other than the expanded system_prompt"


def test_red_missing_fragment_refuses():
    src, cfg = make_base_tree("t2")
    _write(os.path.join(src, "profiles", "GAMMA.json"),
           _profile_json("GAMMA", "Gamma intro.\n\n{{FRAGMENT:does_not_exist}}"))
    config = json.load(open(cfg, encoding="utf-8"))
    try:
        B.build_bundle(src, config)
        raise AssertionError("expected FragmentResolutionError, build succeeded instead")
    except B.FragmentResolutionError as exc:
        msg = str(exc)
        assert "GAMMA" in msg, "refusal message did not name the offending profile"
        assert "does_not_exist" in msg, "refusal message did not name the missing fragment id"

    # also drive it through the CLI entrypoint and check the exit code + stderr
    out_path = os.path.join(FX, "t2", "out.json")
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        rc = B.main(["--src", src, "--config", cfg, "--out", out_path])
    assert rc == 2, "CLI did not exit 2 on an unresolved fragment"
    assert "does_not_exist" in buf.getvalue(), "CLI stderr did not name the missing fragment id"
    assert not os.path.exists(out_path), "a partial/incorrect bundle was written despite the refusal"


def test_red_malformed_token_refuses():
    src, cfg = make_base_tree("t3")
    _write(os.path.join(src, "profiles", "DELTA.json"),
           _profile_json("DELTA", "Delta intro.\n\n{{FRAGMENT:greeting"))   # missing closing }}
    config = json.load(open(cfg, encoding="utf-8"))
    try:
        B.build_bundle(src, config)
        raise AssertionError("expected FragmentResolutionError for a malformed token")
    except B.FragmentResolutionError as exc:
        assert "DELTA" in str(exc), "refusal message did not name the offending profile"


# ------------------------------------------------------------------------------- T4 --

def test_no_fragments_dir_is_backward_compatible():
    root = os.path.join(FX, "t4")
    if os.path.isdir(root):
        shutil.rmtree(root)
    src = os.path.join(root, "src")
    _write(os.path.join(src, "skills", "dummy_skill", "SKILL.md"),
           "---\nname: dummy_skill\ndescription: a fixture skill\n---\nbody text.")
    _write(os.path.join(src, "profiles", "PLAIN.json"),
           _profile_json("PLAIN", "No fragments here, just plain text."))
    cfg = os.path.join(root, "build_config.json")
    _write(cfg, _config())
    assert not os.path.isdir(os.path.join(src, "fragments")), "fixture setup error"
    config = json.load(open(cfg, encoding="utf-8"))
    obj = B.build_bundle(src, config)          # must NOT raise
    prof = obj["profiles"][0]
    assert prof["system_prompt"] == "No fragments here, just plain text.", \
        "a token-free profile's text changed even though no fragments dir exists"


# ------------------------------------------------------------------------------- T5 --

def test_idempotent_on_same_tree():
    src, cfg = make_base_tree("t5")
    config = json.load(open(cfg, encoding="utf-8"))
    obj1 = B.build_bundle(src, config)
    obj2 = B.build_bundle(src, config)
    assert B.serialize(obj1) == B.serialize(obj2), "two builds of the identical tree produced different bytes"


# ------------------------------------------------------------------------------- T6 --

def test_real_tree_accepts_and_expands():
    if not (os.path.isdir(REAL_SRC) and os.path.isfile(REAL_CONFIG)):
        print("  SKIP (real bundle_src/build_config.json not found at expected path)")
        return
    config = json.load(open(REAL_CONFIG, encoding="utf-8"))
    obj = B.build_bundle(REAL_SRC, config)      # must not raise on the real production tree
    frag_dir = os.path.join(REAL_SRC, "fragments")
    fragments_on_disk = {}
    for n in os.listdir(frag_dir):
        if n.endswith(".md"):
            fragments_on_disk[n[:-3]] = open(os.path.join(frag_dir, n), encoding="utf-8").read().rstrip("\n")
    assert fragments_on_disk, "expected at least one real fragment file (audible_alert/self_scan/self_scan_alt)"
    found_any = {fid: False for fid in fragments_on_disk}
    for prof in obj["profiles"]:
        sp = prof["system_prompt"]
        assert "{{FRAGMENT:" not in sp, "real profile %s still carries an unexpanded token" % prof["name"]
        for fid, body in fragments_on_disk.items():
            if body in sp:
                found_any[fid] = True
    for fid, seen in found_any.items():
        assert seen, "fragment %r never appears (verbatim) in any real profile's expanded prompt" % fid


# ------------------------------------------------------------------------------ runner --

TESTS = [
    ("T1 expansion + manifest hashes expanded text", test_expansion_verbatim_and_manifest),
    ("T2 RED: missing fragment refuses (build_bundle + CLI)", test_red_missing_fragment_refuses),
    ("T3 RED: malformed token refuses", test_red_malformed_token_refuses),
    ("T4 no fragments/ dir is backward compatible", test_no_fragments_dir_is_backward_compatible),
    ("T5 idempotent on the same source tree", test_idempotent_on_same_tree),
    ("T6 real production tree builds + expands cleanly", test_real_tree_accepts_and_expands),
]


def main():
    os.makedirs(FX, exist_ok=True)
    passed, failed = 0, 0
    for name, fn in TESTS:
        try:
            fn()
            print("PASS -- %s" % name)
            passed += 1
        except AssertionError as exc:
            print("FAIL -- %s: %s" % (name, exc))
            failed += 1
        except Exception as exc:                 # noqa: BLE001 -- a test crashing is also a FAIL
            print("FAIL -- %s: unexpected %s: %s" % (name, type(exc).__name__, exc))
            failed += 1
    print("\n%d passed, %d failed (fixtures under %s)" % (passed, failed, FX))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
