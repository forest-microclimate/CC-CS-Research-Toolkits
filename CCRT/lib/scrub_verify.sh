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
# NOTE: one project-root token is written with a single-character class (`P[C]FW_ROOT`) so this
# gate's own source does not carry the very literal it screens for — a scanner that spells out its
# denylist becomes a hit in any tree-wide scan of the same vocabulary. ERE matches the same string
# either way; --self-test case (D) proves it, so the masking cannot silently break the pattern.
FAIL='(\[\[[A-Za-z]|/Users/|projects/CliMA|EmeraldDeveloping|code/diel|clima-[a-z-]+\.machine|@protocols|native_baseline|diel_setup|GF_SWSUNBINS|DIEL_[A-Z]|gfh_|p_fleck|p_sunlit|GF-bins|P[C]FW_ROOT|CliMA|Emerald|sunfleck|km67|Pará|Manaus)'
# Verification-marker whitelist: `[[vloop:…]]` etc. are LEGITIMATE status tokens the VLOOP
# self-check system emits + greps — NOT wikilinks. Known-family prefixes only (a whitelist of
# status tokens, not a broadening of the wikilink class). EDGE CASE: the post-filter drops the
# whole LINE, so a line carrying BOTH a marker AND a real dangling ref would be missed — none
# exists in payload today; if that becomes possible, move to a PCRE negative-lookahead inside
# FAIL instead of this post-filter.
MARKER_SAFE='\[\[(vloop|claim_check|canon|prior_art|ship_parity|scrub|post_edit_smoke)[: ]'

# --- HOST-ENVIRONMENT residue (2026-08-09) ----------------------------------
# Added after a shipped skill was found carrying the author's LAN IP and box name in 4 places:
# FAIL above screens project/engine vocabulary, and matched none of it. A shipped payload must
# name no real machine. Scanned as a SECOND pass with its OWN whitelist, deliberately NOT folded
# into FAIL — one whitelist per pattern, so an exclusion tuned for an IP can never widen the
# project-token gate. Three classes:
#   (1) IPv4 literal — any dotted quad. Measured against the whole payload before choosing this
#       breadth: 0 hits other than the real residue, so no version string pays for it. A 4-part
#       version ("1.2.3.4") WOULD be a false positive; none exists, and the whitelist below is
#       where one would go.
#   (2) mDNS host name — `<name>.local` NOT followed by `.`, an alphanumeric, or `/`. That one
#       trailing condition is what keeps `settings.local.json`, `CLAUDE.local.md`, `~/.local/bin`
#       and `_time_shim.localtime()` out of the gate; they are the dominant `.local` uses here.
#   (3) Linux home path — the sibling of FAIL's `/Users/`, on a toolkit whose skills provision
#       Linux boxes. Placeholder users are whitelisted below.
HOSTNET='(([0-9]{1,3}\.){3}[0-9]{1,3}|[A-Za-z0-9][A-Za-z0-9_-]*\.local([^.A-Za-z0-9/]|$)|/home/[a-z_][a-z0-9_-]*/)'
# STATED EXCLUSIONS (each is content that is legitimately generic, not a hole being papered over):
#   0.0.0.0 / 127.0.0.1 / 255.255.255.255 — bind-all, loopback, broadcast: they name no machine.
#   192.0.2.x / 198.51.100.x / 203.0.113.x — the RFC 5737 ranges RESERVED for documentation.
#   a dotted quad followed by /<digit> — CIDR notation in prose (e.g. a subnet example).
#   /home/{me,user,username,you}/ — the placeholder users our docs already use in examples.
HOSTNET_SAFE='(0\.0\.0\.0|127\.0\.0\.1|255\.255\.255\.255|192\.0\.2\.[0-9]|198\.51\.100\.[0-9]|203\.0\.113\.[0-9]|([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]|/home/(me|user|username|you)/)'
# OPERATOR HOOK: a BARE machine name ("the box in the corner") matches no generic pattern — the
# only way to screen one is to name it, and this gate SHIPS, so it must not carry anybody's
# identity. Supply your own alternation at run time instead; empty by default:
#   SCRUB_HOST_TOKENS='mybox|myname' bash scrub_verify.sh
if [ -n "${SCRUB_HOST_TOKENS:-}" ]; then HOSTNET="($HOSTNET|$SCRUB_HOST_TOKENS)"; fi

# scan_hostnet <root> — emits `path:lineno:line` for every line holding a NON-whitelisted hit.
# Two things this does that the `| grep -v` post-filter above cannot, both found by self-test (I):
#   (1) PER-MATCH, not per-line: whitelisted tokens are blanked out of a COPY of the line and the
#       pattern re-applied, so `/home/me/x and /home/jdoe/y` still reports — a line-based `grep -v`
#       drops the whole line for the placeholder and takes the real leak down with it. The ORIGINAL
#       line is what gets printed; only the decision is made on the scrubbed copy.
#   (2) NO PATH PREFIX in the filtered text: it greps each file separately and prepends the path
#       afterwards. `grep -rn` prints `path:line:…`, and on a checkout living under /home/<user>/
#       that prefix matches HOSTNET on EVERY line, which would silently disable the whitelist for
#       exactly the users whose home paths this pattern screens. (The FAIL pass above is unaffected:
#       it filters with grep -v on a pattern no payload path can plausibly contain.)
scan_hostnet() {
  find "$1" -type f ! -name '*.pdf' ! -name '*.docx' ! -name '*.png' ! -name '*.svg' -print 2>/dev/null |
  while IFS= read -r f; do
    grep -nIE "$HOSTNET" "$f" 2>/dev/null | while IFS= read -r ln; do
      printf '%s\n' "$ln" | sed -E "s@$HOSTNET_SAFE@<generic>@g" | grep -qE "$HOSTNET" &&
        printf '%s:%s\n' "$f" "$ln"
    done
  done
}

EXCLUDE_BINARY=(--exclude='*.pdf' --exclude='*.docx' --exclude='*.png' --exclude='*.svg')

# --- REGRESSION GUARD: bash scrub_verify.sh --self-test ----------------------
# Proves the three invariants the 2026-07-12 + 2026-07-27 fixes must uphold, so neither exclusion
# can silently go over-broad: (A) a dangling ref in SOURCE TEXT is still caught THROUGH the marker
# filter (fail-closed); (B) a byte coincidence inside a derived binary (.pdf) is NOT caught (the
# bug the 2026-07-12 exclusion fix closed); (C) a legitimate [[vloop:…]] verification marker is
# NOT flagged (the false-positive the 2026-07-27 MARKER_SAFE fix closed); (D) the project-root
# token written as a character class still matches its LITERAL (the 2026-08-06 masking fix — the
# planted string is assembled at runtime, so proving the match costs this file no literal).
if [ "${1:-}" = "--self-test" ]; then
  TD="$(mktemp -d)"; trap 'rm -rf "$TD"' EXIT
  printf 'a dangling ref /Users/x and a [[Wikilink to CliMA\n' > "$TD/planted.machine.md"       # (A) source text
  printf '%%PDF-1.7 binary [[Xcoincidence CliMA stream\n' > "$TD/derived.pdf"                    # (B) fake derived binary
  printf 'legit [[vloop:g n_claims=4]] marker\n' > "$TD/marker_ok.py"                            # (C) verification marker
  printf 'a project-root ref P%sFW_ROOT/docs survives\n' C > "$TD/masked_token.machine.md"       # (D) literal, assembled here
  a_hits="$(grep -rInE "${EXCLUDE_BINARY[@]}" "$FAIL" "$TD/planted.machine.md" 2>/dev/null | grep -vE "$MARKER_SAFE" || true)"
  b_hits="$(grep -rInE "${EXCLUDE_BINARY[@]}" "$FAIL" "$TD/derived.pdf" 2>/dev/null || true)"
  c_hits="$(grep -rInE "${EXCLUDE_BINARY[@]}" "$FAIL" "$TD/marker_ok.py" 2>/dev/null | grep -vE "$MARKER_SAFE" || true)"
  d_hits="$(grep -rInE "${EXCLUDE_BINARY[@]}" "$FAIL" "$TD/masked_token.machine.md" 2>/dev/null | grep -vE "$MARKER_SAFE" || true)"
  rc=0
  if [ -n "$a_hits" ]; then echo "  (A) source-text ref CAUGHT ✓"; else echo "  (A) FAIL: source-text ref MISSED — gate no longer fail-closed"; rc=1; fi
  if [ -z "$b_hits" ]; then echo "  (B) derived .pdf coincidence SKIPPED ✓"; else echo "  (B) FAIL: derived .pdf scanned — the excluded-binary fix regressed"; rc=1; fi
  if [ -z "$c_hits" ]; then echo "  (C) legit [[vloop:…]] marker NOT flagged ✓"; else echo "  (C) FAIL: verification marker flagged — MARKER_SAFE whitelist regressed"; rc=1; fi
  if [ -n "$d_hits" ]; then echo "  (D) masked project-root token CAUGHT ✓"; else echo "  (D) FAIL: masked token MISSED — the character-class masking broke the pattern"; rc=1; fi

  # (E)-(J) HOST-ENVIRONMENT residue, 2026-08-09. Each case is one of the two things that can go
  # wrong with this pattern class: a real leak MISSED, or legitimate content wrongly FLAGGED.
  hscan(){ scan_hostnet "$1" || true; }   # the SHIPPED scanner, so the self-test exercises it
  printf 'HOST=10.0.0.42 ADMIN_USER=you ./provision_host.sh\n' > "$TD/ip_leak.md"                 # (E) real leak
  printf 'bind 0.0.0.0, loopback 127.0.0.1, doc range 203.0.113.7, subnet 10.0.0.0/24\n' > "$TD/ip_generic.md"  # (F) generic
  printf 'edit .claude/settings.local.json and CLAUDE.local.md; _time_shim.localtime(); ~/.local/bin\n' > "$TD/local_words.md"  # (G) not hostnames
  printf 'ssh admin@workbox.local  # the box\n' > "$TD/mdns_leak.md"                              # (H) real leak
  printf 'e.g. cwd `/home/me/proj A` -> a slug\n'      > "$TD/home_ok.md"      # (I1) placeholder only
  printf 'job workdirs land in /home/jdoe/scratch\n'   > "$TD/home_leak.md"    # (I2) real account
  printf 'cwd `/home/me/x` -> slug; also /home/jdoe/y\n' > "$TD/home_mixed.md" # (I3) both on ONE line
  e_hits="$(hscan "$TD/ip_leak.md")";     f_hits="$(hscan "$TD/ip_generic.md")"
  g_hits="$(hscan "$TD/local_words.md")"; h_hits="$(hscan "$TD/mdns_leak.md")"
  i1_hits="$(hscan "$TD/home_ok.md")"; i2_hits="$(hscan "$TD/home_leak.md")"; i3_hits="$(hscan "$TD/home_mixed.md")"
  if [ -n "$e_hits" ]; then echo "  (E) IPv4 literal CAUGHT ✓"; else echo "  (E) FAIL: IPv4 literal MISSED — the residue class that shipped is unscreened again"; rc=1; fi
  if [ -z "$f_hits" ]; then echo "  (F) generic/doc/CIDR addresses NOT flagged ✓"; else echo "  (F) FAIL: a genuinely generic address was flagged: $f_hits"; rc=1; fi
  if [ -z "$g_hits" ]; then echo "  (G) settings.local.json / .localtime() / ~/.local NOT flagged ✓"; else echo "  (G) FAIL: a '.local' word was read as a hostname: $g_hits"; rc=1; fi
  if [ -n "$h_hits" ]; then echo "  (H) mDNS <name>.local hostname CAUGHT ✓"; else echo "  (H) FAIL: mDNS hostname MISSED"; rc=1; fi
  if [ -z "$i1_hits" ]; then echo "  (I1) /home/me placeholder NOT flagged ✓"; else echo "  (I1) FAIL: the documented placeholder user was flagged: $i1_hits"; rc=1; fi
  if [ -n "$i2_hits" ]; then echo "  (I2) real /home/<user> path CAUGHT ✓"; else echo "  (I2) FAIL: a real Linux home path was MISSED"; rc=1; fi
  if [ -n "$i3_hits" ]; then echo "  (I3) leak sharing a line with a whitelisted token still CAUGHT ✓ (per-match, not per-line)"; else echo "  (I3) FAIL: a whitelisted token on the same line masked a real leak"; rc=1; fi
  # (J) the operator hook, BOTH states. $HOSTNET was already composed by the hook above, so this
  # scans through the real armed pattern rather than a re-implementation of it. Run both arms:
  #   bash scrub_verify.sh --self-test                          -> unscreened by default
  #   SCRUB_HOST_TOKENS='darkstar' bash scrub_verify.sh --self-test  -> caught
  printf 'OBSERVED on the reference run on darkstar.\n' > "$TD/bare_name.md"
  j_hits="$(hscan "$TD/bare_name.md")"
  case "${SCRUB_HOST_TOKENS:-}" in
    '')        if [ -z "$j_hits" ]; then echo "  (J) bare machine name unscreened by default ✓ (arm it: SCRUB_HOST_TOKENS='darkstar' … --self-test)"; else echo "  (J) FAIL: a bare name matched with no operator tokens set — the generic patterns are over-broad"; rc=1; fi ;;
    *darkstar*) if [ -n "$j_hits" ]; then echo "  (J) bare machine name CAUGHT once SCRUB_HOST_TOKENS names it ✓"; else echo "  (J) FAIL: SCRUB_HOST_TOKENS did not arm the pattern"; rc=1; fi ;;
    *)         echo "  (J) skipped — SCRUB_HOST_TOKENS is armed with other tokens; re-run with 'darkstar' to exercise this case" ;;
  esac

  [ "$rc" = 0 ] && echo "SELF-TEST: PASS" || echo "SELF-TEST: FAIL"
  exit "$rc"
fi

# Derived binary outputs (rendered PDF/docx twins) are NOT scrubbable source text. Excluded BY PATH
# (EXCLUDE_BINARY above) — not by grep's -I content-sniff, which misclassifies typst-rendered PDFs (the
# folio render backbone) as text and then false-positives on byte coincidences (e.g. the [[ wikilink
# pattern) inside compressed streams. -I is kept too (belt-and-suspenders); the --exclude is what makes a
# re-rendered PDF safe. INVARIANT (proven by --self-test): only *derived* formats are excluded; all source text is scanned.
echo "== scrub_verify: scanning $PAYLOAD =="
[ -n "${SCRUB_HOST_TOKENS:-}" ] && echo "   (operator host tokens armed: $SCRUB_HOST_TOKENS)"
gate_rc=0

hits="$(grep -rInE "${EXCLUDE_BINARY[@]}" "$FAIL" "$PAYLOAD" 2>/dev/null | grep -vE "$MARKER_SAFE" || true)"   # -I + --exclude derived binaries; marker whitelist applied
if [ -n "$hits" ]; then
  echo "FAIL — dangling project reference(s) survive:"
  echo "$hits"
  gate_rc=1
else
  echo "PASS — no dangling project references."
fi

# SECOND PASS, own pattern + own whitelist (see the HOSTNET block). Reported alongside the first
# rather than short-circuiting, so one run names every class of residue instead of only the first.
host_hits="$(scan_hostnet "$PAYLOAD" || true)"
if [ -n "$host_hits" ]; then
  echo "FAIL — host-environment residue (IP / hostname / home path) survives:"
  echo "$host_hits"
  gate_rc=1
else
  echo "PASS — no host-environment residue."
fi

[ "$gate_rc" = 0 ] || exit 1

echo "== INFO: residual domain vocabulary (illustrative examples are OK; eyeball) =="
grep -rIniE "${EXCLUDE_BINARY[@]}" 'canopy|leaf.?t|eddy.covariance|tropical forest|shade EB|microsite' "$PAYLOAD" 2>/dev/null \
  | sed "s|$PAYLOAD/||" || echo "(none)"
exit 0
