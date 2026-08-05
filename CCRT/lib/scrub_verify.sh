#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# scrub_verify.sh [PAYLOAD_DIR] — fail-closed gate on the scrubbed payload.
# EXIT 1 (printing the offending lines) if any out-of-package "dangling reference" survives.
# INFO patterns (residual domain vocabulary) are printed but NON-fatal — they should be only
# illustrative examples (e.g. "a shaded surface hotter than the sunlit max"), which are kept on purpose.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PAYLOAD="${1:-$SCRIPT_DIR/../payload}"

# --- FAIL pattern (shared by the scan and the self-test) --------------------
# Project pointers / dead paths / engine identifiers that MUST NOT survive anywhere in payload/:
# NOTE: \[\[[A-Za-z] matches an Obsidian wikilink ([[name…, always letter-initial) but NOT bash
# `[[ cond ]]` (space after [[) nor a POSIX class `[[:space:]]` (colon after [[).
FAIL='(\[\[[A-Za-z]|/Users/|projects/CliMA|EmeraldDeveloping|code/diel|clima-[a-z-]+\.machine|@protocols|native_baseline|diel_setup|GF_SWSUNBINS|DIEL_[A-Z]|gfh_|p_fleck|p_sunlit|GF-bins|PCFW_ROOT|CliMA|Emerald|sunfleck|km67|Pará|Manaus)'
# Verification-marker whitelist: `[[vloop:…]]` etc. are LEGITIMATE status tokens the VLOOP
# self-check system emits + greps — NOT wikilinks. Known-family prefixes only (a whitelist of
# status tokens, not a broadening of the wikilink class). EDGE CASE: the post-filter drops the
# whole LINE, so a line carrying BOTH a marker AND a real dangling ref would be missed — none
# exists in payload today; if that becomes possible, move to a PCRE negative-lookahead inside
# FAIL instead of this post-filter.
MARKER_SAFE='\[\[(vloop|claim_check|canon|prior_art|ship_parity|scrub|post_edit_smoke)[: ]'
EXCLUDE_BINARY=(--exclude='*.pdf' --exclude='*.docx' --exclude='*.png' --exclude='*.svg')

# --- REGRESSION GUARD: bash scrub_verify.sh --self-test ----------------------
# Proves the three invariants the 2026-07-12 + 2026-07-27 fixes must uphold, so neither exclusion
# can silently go over-broad: (A) a dangling ref in SOURCE TEXT is still caught THROUGH the marker
# filter (fail-closed); (B) a byte coincidence inside a derived binary (.pdf) is NOT caught (the
# bug the 2026-07-12 exclusion fix closed); (C) a legitimate [[vloop:…]] verification marker is
# NOT flagged (the false-positive the 2026-07-27 MARKER_SAFE fix closed).
if [ "${1:-}" = "--self-test" ]; then
  TD="$(mktemp -d)"; trap 'rm -rf "$TD"' EXIT
  printf 'a dangling ref /Users/x and a [[Wikilink to CliMA\n' > "$TD/planted.machine.md"       # (A) source text
  printf '%%PDF-1.7 binary [[Xcoincidence CliMA stream\n' > "$TD/derived.pdf"                    # (B) fake derived binary
  printf 'legit [[vloop:g n_claims=4]] marker\n' > "$TD/marker_ok.py"                            # (C) verification marker
  a_hits="$(grep -rInE "${EXCLUDE_BINARY[@]}" "$FAIL" "$TD/planted.machine.md" 2>/dev/null | grep -vE "$MARKER_SAFE" || true)"
  b_hits="$(grep -rInE "${EXCLUDE_BINARY[@]}" "$FAIL" "$TD/derived.pdf" 2>/dev/null || true)"
  c_hits="$(grep -rInE "${EXCLUDE_BINARY[@]}" "$FAIL" "$TD/marker_ok.py" 2>/dev/null | grep -vE "$MARKER_SAFE" || true)"
  rc=0
  if [ -n "$a_hits" ]; then echo "  (A) source-text ref CAUGHT ✓"; else echo "  (A) FAIL: source-text ref MISSED — gate no longer fail-closed"; rc=1; fi
  if [ -z "$b_hits" ]; then echo "  (B) derived .pdf coincidence SKIPPED ✓"; else echo "  (B) FAIL: derived .pdf scanned — the excluded-binary fix regressed"; rc=1; fi
  if [ -z "$c_hits" ]; then echo "  (C) legit [[vloop:…]] marker NOT flagged ✓"; else echo "  (C) FAIL: verification marker flagged — MARKER_SAFE whitelist regressed"; rc=1; fi
  [ "$rc" = 0 ] && echo "SELF-TEST: PASS" || echo "SELF-TEST: FAIL"
  exit "$rc"
fi

# Derived binary outputs (rendered PDF/docx twins) are NOT scrubbable source text. Excluded BY PATH
# (EXCLUDE_BINARY above) — not by grep's -I content-sniff, which misclassifies typst-rendered PDFs (the
# folio render backbone) as text and then false-positives on byte coincidences (e.g. the [[ wikilink
# pattern) inside compressed streams. -I is kept too (belt-and-suspenders); the --exclude is what makes a
# re-rendered PDF safe. INVARIANT (proven by --self-test): only *derived* formats are excluded; all source text is scanned.
echo "== scrub_verify: scanning $PAYLOAD =="
hits="$(grep -rInE "${EXCLUDE_BINARY[@]}" "$FAIL" "$PAYLOAD" 2>/dev/null | grep -vE "$MARKER_SAFE" || true)"   # -I + --exclude derived binaries; marker whitelist applied
if [ -n "$hits" ]; then
  echo "FAIL — dangling project reference(s) survive:"
  echo "$hits"
  exit 1
fi
echo "PASS — no dangling project references."

echo "== INFO: residual domain vocabulary (illustrative examples are OK; eyeball) =="
grep -rIniE "${EXCLUDE_BINARY[@]}" 'canopy|leaf.?t|eddy.covariance|tropical forest|shade EB|microsite' "$PAYLOAD" 2>/dev/null \
  | sed "s|$PAYLOAD/||" || echo "(none)"
exit 0
