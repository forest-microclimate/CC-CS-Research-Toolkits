#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# verify_models.sh [PAYLOAD_DIR] — fail-closed gate on the MODEL keys the payload ships.
# EXIT 1 (listing every offender file:line) if a payload/agents frontmatter OUTSIDE the named
# ALLOWLIST (fable-executor · fable-subplanner · opus5-executor) carries ANY `model:`
# key, or if anything scanned names a BARRED model. WARNINGS (a bare alias outside payload/agents)
# print but NEVER fail.
#
# WHY THIS EXISTS — TWO contracts + a PARITY arm; contract 1 NARROWED 2026-08-09 (PC1):
#  (1) PINS BY NAME in payload/agents. Model control on the shipped payload is LAUNCHER-ONLY for
#      every agent EXCEPT a NAMED ALLOWLIST of three: fable-executor · fable-subplanner ·
#      opus5-executor. A frontmatter pin is RANK 3 of the measured precedence (env var > Task param
#      > frontmatter > inherit the main model), so a shipped pin OVERRIDES the launcher choice for
#      every session that installs it — THE PIN ITSELF IS THE DEFECT on an ordinary agent, barred
#      value or not. That blast radius is exactly why the exemption is a NAMED SET of three and
#      never a wildcard, never "any file carrying a pin", never a tier test: the reach is real, so
#      the vetting is per-file and the list IS the vetting record.
#      MEASURED CONSTRAINT (2026-08-04, live InputValidationError): the Task `model` param accepts
#      ALIASES ONLY {sonnet|opus|haiku|fable} — no full ids — so the launcher vocabulary is
#      `fable` · `sonnet` · `haiku` (`opus` barred).
#      [SUPERSEDED 2026-08-04, O6 one-sweep — an omitted param is rank 4 and requests the MAIN
#      model, not fable; and "naming fable risks a silent resolve" was a REAL observation with the
#      wrong cause: serving-side SUBSTITUTION of fable requests, not alias resolution]
#      ~~OMIT ⇒ fable · naming `fable` risks the silent resolve to claude-opus-5~~.
#      WHY THE THREE ARE DIFFERENT IN KIND (user decision 2026-08-09): they are not agents that
#      happen to carry a model, they ARE model ROUTES — launching `delegate:fable-executor` IS the
#      tier choice — and the measured serving-substitution bug is why a route must place its request
#      from frontmatter (rank 3) rather than from the launcher. Strip the pin and the route
#      dissolves into whatever the main model happens to be. For exactly these three the pin is the
#      identity; for every other agent it is the defect. Same mechanism, opposite verdict, decided
#      by the one question this gate asks: is the file NAMED on the allowlist?
#  (1b) THE MIRROR (added 2026-08-09, PC1 addendum): for those same three names a MISSING `model:`
#      key is itself a FAIL, on BOTH agent surfaces. MAY-pin and MUST-pin are one contract, because
#      the pin IS the route: strip it and a paramless launch falls from rank 3 to rank 4 and silently
#      inherits the session model — no error, no DENY, just a route that stopped being one. It is
#      ENFORCED rather than warned because the absence is silent, is almost never deliberate, and is
#      INVISIBLE TO PARITY: both homes drop the pin together and stay byte-identical. For every OTHER
#      agent, no pin remains the REQUIRED state (silent in payload/, a non-fatal "(allowed)" note on
#      the kit surface) — that wording is true for an ordinary agent and backwards for a route, so
#      the allowlisted names never reach it.
#      [SUPERSEDED 2026-08-09, PC1 — payload-project/ was DELETED, so a carve naming that directory
#      is a rule that can never fire; full-id precision for the shipped routes now comes from the
#      named allowlist above, while lib/crt-dev-model.sh remains the per-project shadow for anything
#      that is NOT one of the three]
#      ~~FULL-ID precision is reachable ONLY through a PROJECT-SCOPED shadow pin
#      (lib/crt-dev-model.sh) — the same rank-3 mechanism, narrowed to one project — which is why
#      payload-project/agents (project scope) may still pin and payload/agents (user scope) may not.~~
#  (2) THE BARRED-ID BAN, carve NARROWED 2026-08-09 (PC1) from a DIRECTORY to a NAMED FILE.
#      claude-opus-5 is barred in any tier, any call (user bar) — EXCEPT in the file named
#      `opus5-executor.md`, on either allowlisted agent surface (payload/agents/ and
#      planner-kit/payload/.claude/agents/). WHY the carve is safe exactly there and nowhere else:
#      the blast-radius reasoning is UNCHANGED — a payload/agents pin installs into the general
#      ~/.claude and rides into EVERY session — but it is now answered by the NAME instead of by a
#      directory. That one file's body carries the supervision contract (a tightly-scoped child
#      under a Planner's active watch, never a coordinator, spawning nothing), and the model reaches
#      a session only when a Planner deliberately launches `delegate:opus5-executor`. In any OTHER
#      file, on any surface, the id is still DENIED. The BARE aliases `opus` and `opusplan` stay
#      DENIED everywhere, ALLOWLIST INCLUDED: an alias re-resolves silently (that is how `opus`
#      became a barred pin without any file changing), so it can never be the sanctioned route.
#      This gate is the CC counterpart of the model_route_gate named in A2 §COMPANION GATES, moved
#      from dispatch time to BUILD time; the DISPATCH-time half of the alias ban lives in
#      payload/hooks/opus-dispatch-guard.sh (PreToolUse, matcher=Task).
#  (3) PARITY (added 2026-08-09, PC1). Each allowlisted route ships from TWO homes: payload/agents
#      (installed into the general ~/.claude) and planner-kit/payload/.claude/agents (installed into
#      each adopting project root). Two homes for one route is a drift surface, so the copies must be
#      BYTE-IDENTICAL (`cmp`) and any drift FAILS naming the file. This arm is what makes the
#      duplication safe: without it, the two homes are free to disagree about what a route IS.
#
# USAGE:
#   bash verify_models.sh [PAYLOAD_DIR]      # gate: exit 1 on any pin or barred id, 0 otherwise
# PAYLOAD_DIR defaults to ../payload resolved from this script's own location (lib/ -> toolkit root),
# matching lib/scrub_verify.sh.
# REGRESSION GUARD: tests/test_verify_models.sh — red-before/green-after fixtures (A2 §FIXTURE
# CONTRACT), run SEPARATELY from any suite. Its RED fixtures reproduce BOTH recorded defects: the
# pre-fix barred state (agents on bare `opus` + a personal fragment on "opus[1m]") and the pre-F2
# PINNED state (agents on claude-opus-4-8 / claude-fable-5, allowed ids that are now themselves the
# defect) — plus, from PC1, the allowlist arms (§L), the parity arms (§N), the re-scoped carve (§S)
# and a LIVE-SHAPE arm (§O) that runs the gate against the REAL payload and ASSERTS it green. That
# last one closes a measured gap: on 2026-08-09 the suite reported SUITE: PASS while this gate exited
# 1 on the shipped tree, because every fixture was hermetic and none had the live shape.
#
# WHAT IT CHECKS
#   agents   payload/agents/*.md   — the `model:` key INSIDE the YAML frontmatter only (a `model:`
#                                    written in the BODY is prose — e.g. a doc quoting this very ban
#                                    — and must not trip the gate). Such a key FAILS (contract 1)
#                                    UNLESS the file's BASENAME is on the ALLOWLIST below, in which
#                                    case the pin is ALLOWED and reported as a NOTE, never silently;
#                                    a barred VALUE is named as barred too, in the same finding.
#   kit      planner-kit/payload/.claude/agents/*.md — OPTIONAL, scanned when present. Contract 2
#                                    ONLY: the kit installs these into ONE project root per install
#                                    run, never into the general ~/.claude, so a pin is legal here —
#                                    but the claude-opus-5 carve still narrows to the NAMED
#                                    opus5-executor file, and the aliases are still DENIED.
#   parity   payload/agents/<allowlisted>.md vs the kit copy of the same name — byte-identical or
#                                    FAIL (contract 3). A MISSING kit counterpart is drift too. When
#                                    the kit surface is absent entirely there is nothing to compare:
#                                    that WARNS out loud; it never reads as a pass.
#   settings payload/settings/*.json — any "model", "ANTHROPIC_MODEL", or "ANTHROPIC_CUSTOM_MODEL_OPTION" string value, at any nesting (the custom picker-row env is a model surface too; added 2026-07-28). Contract 2 only: `"model": "claude-fable-5[1m]"` is legitimate SESSION-DEFAULT config, not an agent pin.
# ANTI-VACUOUS-PASS: a missing agents/ or settings/ dir, or an agents/ dir with no .md files, is a
# FAIL — a gate that cannot read its subject must not report PASS.
#
# Portable: POSIX + bash 3.2 (macOS default). No mapfile, no associative arrays, no readlink -f,
# no GNU-only grep flags; grep/sed/awk only. Every path quoted (spaces safe).
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PAYLOAD="${1:-$SCRIPT_DIR/../payload}"
# Canonicalize so every reported file:line is a clean absolute path (and so the no-arg default prints
# ".../payload", not ".../lib/../payload"). cd+pwd -P is the portable form — no readlink -f on macOS.
# A non-existent path is left verbatim so the missing-dir FAIL below still names what was asked for.
[ -d "$PAYLOAD" ] && PAYLOAD="$(cd -- "$PAYLOAD" && pwd -P)"
AGENTS="$PAYLOAD/agents"
SETTINGS="$PAYLOAD/settings"
NL='
'

# ── CLASSIFIER (contract 2 ONLY — the BARRED-ID ban; shared by every scan) ───────────────────
# Contract 1 (zero pins in payload/agents) is enforced by the PRESENCE of the key, not by its value,
# so it is applied in the payload/agents loop below and never asked of this function. The classifier
# still runs there, so a payload/agents pin whose value is ALSO barred reports both facts at once.
# SCOPE ARG (added 2026-08-04; re-scoped 2026-08-09, PC1): classify <value> [general|supervised],
#         default general. It changes EXACTLY ONE branch — claude-opus-5 — and nothing else. The
#         caller passes `supervised` ONLY for the file literally named `opus5-executor.md` on an
#         allowlisted agent surface; there that id returns SUPERVISED (allowed, reported as a NOTE),
#         and in every other file, on every surface, it stays DENY. Every alias branch below is
#         scope-INDEPENDENT on purpose: an alias re-resolves silently, so it can never be the
#         sanctioned route, not even inside the carved file itself.
# DENY = the barred model in ANY spelling:
#         * any id containing claude-opus-5  (bare, context-suffixed `[1m]`, or vendor-qualified)
#           — at GENERAL scope only; see SUPERVISED below
#         * the bare alias `opus`, alone or context-suffixed (`opus[1m]`) — CC >=2.1.219 maps it to
#           Claude Opus 5. Matching by PREFIX (not equality) is deliberate fail-closed behaviour:
#           an unknown opus-5 variant is treated as barred rather than let through.
#         * the alias `opusplan`, alone or context-suffixed (`opusplan[1m]`) — its planning phase
#           runs on the latest Opus, which resolves to the barred Claude Opus 5 on CC >=2.1.219;
#           same hazard as bare `opus`.
#         NOT denied: claude-opus-4-8 (allowed T1).
# WARN = any other BARE alias (sonnet / haiku / fable / inherit / …). Allowed, but a full
#        id is preferred: an alias re-resolves whenever CC remaps it, which is exactly how `opus`
#        became a barred pin without any file changing.
# OK   = a full model id: claude-* , or a vendor-qualified id (contains "anthropic" or a "/").
# SUPERVISED = claude-opus-5 at PROJECT scope: allowed, and REPORTED (a NOTE line), never silent —
#        a carve nobody can see is a carve nobody can audit.
classify() {  # classify <raw-value> [general|project] -> prints "<DENY|WARN|OK|SUPERVISED>\t<reason>"
  _v="$(printf '%s' "$1" | tr 'A-Z' 'a-z')"
  _scope="${2:-general}"
  if [ -z "$_v" ]; then printf 'WARN\tempty model: value\n'; return; fi
  case "$_v" in
    *claude-opus-5*)
      if [ "$_scope" = "supervised" ]; then
        printf 'SUPERVISED\tclaude-opus-5 in the NAMED opus5-executor file — the supervised-executor carve: legal in this ONE file because its own body carries the supervision contract (a tightly-scoped child under a Planner active watch, never a coordinator, spawning nothing), so the id can only run where a Planner launched that route\n'
        return
      fi
      printf 'DENY\tclaude-opus-5 is barred in any tier, any call (user bar) outside the ONE file named opus5-executor.md on an allowlisted agent surface (payload/agents/ + planner-kit/payload/.claude/agents/) — the supervised-executor class is the ONE carve, and it travels with the NAME, not with a directory\n'; return;;
  esac
  case "$_v" in
    opus)            printf 'DENY\tbare alias `opus` resolves to Claude Opus 5 on Claude Code >=2.1.219\n'; return;;
    opus[!a-z0-9-]*) printf 'DENY\tbare alias `opus` (context-suffixed) resolves to Claude Opus 5 on Claude Code >=2.1.219\n'; return;;
  esac
  case "$_v" in
    opusplan)            printf 'DENY\talias `opusplan` plans on the latest Opus, which resolves to Claude Opus 5 on Claude Code >=2.1.219 (same bar as bare `opus`)\n'; return;;
    opusplan[!a-z0-9-]*) printf 'DENY\talias `opusplan` (context-suffixed) plans on the latest Opus, which resolves to Claude Opus 5 on Claude Code >=2.1.219 (same bar as bare `opus`)\n'; return;;
  esac
  case "$_v" in
    claude-*|*anthropic*|*/*) printf 'OK\t-\n'; return;;
  esac
  printf 'WARN\tbare alias — pin a full model id (an alias silently re-resolves)\n'
}

# ── THE NAMED ALLOWLIST (contract 1's exemption) ─────────────────────────────────────────────
# EXACTLY three basenames, spelled out in full. Never a glob, never a prefix or suffix test, never
# "any file that carries a pin", never a tier test: this list IS the vetting record, so it has to be
# readable AS a list, and adding a name has to be an edit somebody reviews. Membership decides ONE
# thing — whether contract 1 fires on this file. It never relaxes contract 2: a barred value in an
# allowlisted file still DENIES, and the claude-opus-5 carve narrows further still, to the single
# name `opus5-executor`.
ALLOWLIST='fable-executor fable-subplanner opus5-executor'
is_allowlisted() {  # is_allowlisted <basename-without-.md> -> exit 0 when the name is on the list
  # EXACT-NAME match, never a substring: a `case` glob on a space-padded list admits a basename
  # that is a RUN of allowlist names ("fable-executor fable-subplanner"), which the contract
  # above forbids. Iterate the list and compare whole words. (PC8 finding B1, 2026-08-09.)
  for _a in $ALLOWLIST; do [ "$1" = "$_a" ] && return 0; done
  return 1
}
# The one name the claude-opus-5 value carve is scoped to (a subset of ALLOWLIST, deliberately).
SUPERVISED_NAME='opus5-executor'
# scope_for <basename> -> the classify() scope this file earns: `supervised` for the carved name,
# `general` for everything else. Kept as ONE function so both agent surfaces answer it identically.
scope_for() { if [ "$1" = "$SUPERVISED_NAME" ]; then printf 'supervised'; else printf 'general'; fi; }

# expected_id_for <allowlisted-basename> -> the id that route exists to place, named in the FAIL text
# so the fix is legible without opening another file. REPORTED, NOT ENFORCED: the gate does not
# require the value to equal this string, because legitimate spellings vary (a context-suffixed
# `claude-opus-5[1m]` is a valid pin the carve accepts). What IS enforced is that the key EXISTS.
expected_id_for() {
  case "$1" in
    fable-executor|fable-subplanner) printf 'claude-fable-5';;
    opus5-executor)                  printf 'claude-opus-5';;
    *)                               printf 'a full model id';;
  esac
}

unquote() { printf '%s' "$1" | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"; }
count_lines() { if [ -z "$1" ]; then echo 0; else printf '%s' "$1" | grep -c ''; fi; }

# frontmatter_model_lines <file> -> "LINE<TAB>RAWVALUE" for each `model:` key inside the YAML
# frontmatter (the block delimited by the leading `---` and the next `---`). Body lines are ignored.
frontmatter_model_lines() {
  awk '
    NR==1 && /^---[[:space:]]*$/ { fm=1; next }
    fm && /^---[[:space:]]*$/    { exit }
    fm && /^[[:space:]]*model:/ {
      v = $0
      sub(/^[[:space:]]*model:[[:space:]]*/, "", v)
      sub(/[[:space:]]+#.*$/, "", v)
      sub(/[[:space:]]+$/, "", v)
      print NR "\t" v
    }
  ' "$1"
}

# ── GATE ─────────────────────────────────────────────────────────────────────────────────────
echo "== verify_models: scanning $PAYLOAD =="
[ -d "$AGENTS" ]   || { echo "FAIL — agents dir not found: $AGENTS"; exit 1; }
[ -d "$SETTINGS" ] || { echo "FAIL — settings dir not found: $SETTINGS"; exit 1; }

deny=""; pins=""; warn=""; note=""; drift=""; unpinned=""; n_agents=0; n_keys=0; n_frag=0; n_allow=0; n_sup=0; n_kit_agents=0; n_kit_full=0; n_kit_sup=0; n_parity=0; n_allow_files=0

# unpinned_finding <file> <basename> -> the CONTRACT 1b finding: an allowlisted route with no pin.
# ONE function, called from BOTH agent surfaces, so the two homes can never drift in how they judge
# a missing pin — the same reason scope_for is shared.
unpinned_finding() {
  printf '  UNPINNED: %s: no model: key in frontmatter — this is an allowlisted ROUTE (expected id: %s), and it is launched PARAMLESS so the rank-3 pin governs; with no pin the launch falls to rank 4 and silently inherits the SESSION model%s' \
    "$1" "$(expected_id_for "$2")" "$NL"
}

# --- agents: CONTRACT 1 — NO `model:` key in the YAML frontmatter, EXCEPT the named allowlist ---
# An ordinary agent with no model: line is the REQUIRED state, so it is silent (not a warning — a
# dozen-plus silent agents warning on every run would be noise the operator learns to skip, which is
# how a real warning gets missed). Every key found on a NON-allowlisted file is a PIN offender; if
# its value is also barred, the finding names that too (contract 2 in the same line), so one run
# reports both defects rather than hiding the barred id behind the pin verdict.
# On an ALLOWLISTED file the key is the route's identity, so contract 1 stands down and the pin is
# reported as a NOTE — never silently, because an exemption nobody can see is an exemption nobody
# can audit. Contract 2 still runs there, and it is the ONLY thing standing between the allowlist
# and a barred id, so it is applied to allowlisted files exactly as to any other.
for f in "$AGENTS"/*.md; do
  [ -f "$f" ] || continue
  n_agents=$((n_agents + 1))
  base="$(basename "$f" .md)"
  hits="$(frontmatter_model_lines "$f")"
  if [ -z "$hits" ]; then
    # CONTRACT 1b (added 2026-08-09, PC1 addendum): for an ORDINARY agent no pin is the REQUIRED
    # state and stays silent. For an ALLOWLISTED route it is a FAIL — the pin IS the route, so its
    # absence is the route silently gone, and parity cannot see it when both homes drop it together.
    is_allowlisted "$base" && unpinned="${unpinned}$(unpinned_finding "$f" "$base")"
    continue
  fi
  while IFS=$'\t' read -r ln raw; do
    [ -n "$ln" ] || continue
    n_keys=$((n_keys + 1))
    val="$(unquote "$raw")"
    if is_allowlisted "$base"; then
      verdict="$(classify "$val" "$(scope_for "$base")")"
      kind="${verdict%%$'\t'*}"; reason="${verdict#*$'\t'}"
      case "$kind" in
        DENY)       deny="${deny}  DENY: ${f}:${ln}: model: ${val} — ${reason}${NL}";;
        WARN)       warn="${warn}  WARN: ${f}:${ln}: model: ${val} — ${reason}${NL}";;
        SUPERVISED) n_allow=$((n_allow + 1)); n_sup=$((n_sup + 1))
                    note="${note}  NOTE: ${f}:${ln}: model: ${val} — ${reason}${NL}";;
        OK)         n_allow=$((n_allow + 1))
                    note="${note}  NOTE: ${f}:${ln}: model: ${val} — allowlisted route pin: for these three NAMED agents the pin IS the route (launching the agent IS the tier choice), so it is admitted by name and shown so it stays auditable${NL}";;
      esac
    else
      verdict="$(classify "$val")"
      kind="${verdict%%$'\t'*}"; reason="${verdict#*$'\t'}"
      extra=""
      [ "$kind" = "DENY" ] && extra=" — AND the value is barred: ${reason}"
      pins="${pins}  PIN:  ${f}:${ln}: model: ${val} — agent frontmatter must carry NO model key (model control is launcher-only outside the named allowlist: ${ALLOWLIST})${extra}${NL}"
    fi
  done <<EOF
$hits
EOF
done

if [ "$n_agents" -eq 0 ]; then
  echo "FAIL — no agent .md files found in $AGENTS (nothing to verify; the gate does not pass vacuously)."
  exit 1
fi

# --- payload-project/agents — SURFACE RETIRED 2026-08-09 (PC1) --------------------------------
# [SUPERSEDED 2026-08-09, PC1] ~~a project-scope scan of payload-project/agents/*.md, described here
# as the sanctioned full-id escape hatch and carrying the claude-opus-5 carve~~ — that directory was
# DELETED, so the scan could only ever find nothing while its FAIL text went on teaching a route no
# operator can take. A rule that cannot fire, worded as the way out, is worse than no rule: a blind
# session reads it and re-creates the wrong thing. The exemption it carried now lives as the NAMED
# ALLOWLIST above, checked against files that actually exist, and the carve narrowed with it — from
# "any pin in that directory" to the single name opus5-executor.
# [SUPERSEDED 2026-08-09, PC6a — both halves of this note were made FALSE later the same day, by PC3,
# and a revival note that misdescribes the machinery is the exact hazard the tombstone above exists to
# prevent] ~~FOR WHOEVER REVIVES A PROJECT-SPECIALTY TREE: install.sh still carries --project-items /
# --project-dest and lib/interactive_select.py still reads ../payload-project/project_manifest.tsv~~
# FOR WHOEVER REVIVES A PROJECT-SPECIALTY TREE — the machinery is GONE, not merely unused (verified by
# reading the code this session, not from a changelog):
#   * install.sh dispatches all four flags to retired_project_flag() (install.sh:81), which prints the
#     manual-install recipe and EXITS 2 writing nothing — confirmed live: `install.sh --project-items foo
#     --project-dest /tmp/pc6a_probe` exited 2 and created no such directory. The one-shot copy block and
#     the project preflight blocks are retired in place (install.sh:145, :314, :512).
#   * lib/interactive_select.py:41-42 now resolves DEFAULT_MANIFEST to ../payload/coupling_manifest_v1.tsv;
#     its project-specialty routing pass, which read ../payload-project/project_manifest.tsv, is retired
#     at :44-45.
# So reviving that directory is no longer a one-line change: it means restoring the installer flags AND
# the selector pass AND re-adding a scan HERE, in the same change. Until then a revived payload-project/
# is NOT watched by any gate, and nothing would install from it.
# WHAT REPLACED IT: CCRT_specialists/ — copied in BY HAND from CCRT_specialists/<bucket>/{agents,skills}/,
# variable depth, ships publicly. It is outside this gate's subject (payload/agents + the kit agents) and
# outside lib/scrub_verify.sh's root (which defaults to ../payload), both BY DESIGN.

# --- kit-shipped agents (planner-kit/payload/.claude/agents/*.md) — OPTIONAL; scanned only when present. ----
# CONTRACT 2 ONLY: the kit installs these into ONE project's .claude/agents (per-root install.sh
# run), never into the general ~/.claude — so pins are LEGAL here (this is the executors' second
# home) and only the barred-id ban binds them. Added 2026-08-04 (K11-C step 0.5): the kit began
# shipping pinned executors at v1.4, and a pin the gates do not watch must not ship.
# NARROWED 2026-08-09 (PC1): the claude-opus-5 carve is per-FILE here too — the name earns it, not
# the directory — so a kit agent under any OTHER name is DENIED that id exactly as in payload/.
KIT_AGENTS="$(dirname "$PAYLOAD")/planner-kit/payload/.claude/agents"
if [ -d "$KIT_AGENTS" ]; then
  for f in "$KIT_AGENTS"/*.md; do
    [ -f "$f" ] || continue
    n_kit_agents=$((n_kit_agents + 1))
    kbase="$(basename "$f" .md)"
    hits="$(frontmatter_model_lines "$f")"
    if [ -z "$hits" ]; then
      # Same split as the payload surface: "(allowed)" is TRUE for an ordinary kit agent and exactly
      # BACKWARDS for a route, so an allowlisted name takes the FAIL branch instead of the warning.
      if is_allowlisted "$kbase"; then
        unpinned="${unpinned}$(unpinned_finding "$f" "$kbase")"
      else
        warn="${warn}  WARN: ${f}: no model: line in frontmatter — inherits the session model (allowed)${NL}"
      fi
      continue
    fi
    while IFS=$'\t' read -r ln raw; do
      [ -n "$ln" ] || continue
      val="$(unquote "$raw")"
      verdict="$(classify "$val" "$(scope_for "$kbase")")"
      kind="${verdict%%$'\t'*}"; reason="${verdict#*$'\t'}"
      case "$kind" in
        DENY)       deny="${deny}  DENY: ${f}:${ln}: model: ${val} — ${reason}${NL}";;
        WARN)       warn="${warn}  WARN: ${f}:${ln}: model: ${val} — ${reason}${NL}";;
        SUPERVISED) n_kit_full=$((n_kit_full + 1)); n_kit_sup=$((n_kit_sup + 1))
                    note="${note}  NOTE: ${f}:${ln}: model: ${val} — ${reason}${NL}";;
        OK)         n_kit_full=$((n_kit_full + 1));;
      esac
    done <<EOF2
$hits
EOF2
  done
fi

# --- PARITY: each allowlisted payload agent vs its kit copy (CONTRACT 3) ---------------------
# `cmp -s` per allowlisted NAME. Any difference — content OR a missing counterpart — is drift and
# FAILS naming the file, because the two homes install the same route into different places and a
# session cannot tell which copy it got.
# ANTI-VACUOUS, subject-aware: when payload/agents holds NO allowlisted agent there is nothing to
# compare and silence is honest (nothing was skipped). When it holds one but the kit surface is
# ABSENT, the comparison was SKIPPED — and a skipped check must say so out loud rather than let a
# clean exit read as "the copies agree".
for name in $ALLOWLIST; do
  pf="$AGENTS/$name.md"
  [ -f "$pf" ] || continue
  n_allow_files=$((n_allow_files + 1))
  [ -d "$KIT_AGENTS" ] || continue
  kf="$KIT_AGENTS/$name.md"
  if [ ! -f "$kf" ]; then
    drift="${drift}  DRIFT: ${pf}: kit copy MISSING at ${kf} — an allowlisted route must ship from BOTH homes, byte-identical${NL}"
  elif cmp -s "$pf" "$kf"; then
    n_parity=$((n_parity + 1))
  else
    drift="${drift}  DRIFT: ${pf}: differs from its kit copy ${kf} — two homes for ONE route must be byte-identical${NL}"
  fi
done
if [ "$n_allow_files" -gt 0 ] && [ ! -d "$KIT_AGENTS" ]; then
  warn="${warn}  WARN: parity NOT verified — ${n_allow_files} allowlisted agent(s) in ${AGENTS} but no kit surface at ${KIT_AGENTS}; the two-home drift check could not run${NL}"
fi

# --- settings fragments: any "model" / "ANTHROPIC_MODEL" string value ------------------------
# grep -nEo gives LINE:"key": "value" for each match (works on BSD + GNU grep; multiple matches on
# one line each print with that line number, so a minified fragment reports correctly too).
for g in "$SETTINGS"/*.json; do
  [ -f "$g" ] || continue
  n_frag=$((n_frag + 1))
  ghits="$(grep -nEo '"(model|ANTHROPIC_MODEL|ANTHROPIC_CUSTOM_MODEL_OPTION)"[[:space:]]*:[[:space:]]*"[^"]*"' "$g" 2>/dev/null || true)"
  [ -n "$ghits" ] || continue
  while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    ln="${hit%%:*}"
    rest="${hit#*:}"
    key="$(printf '%s' "$rest" | sed -E 's/^"([^"]+)".*/\1/')"
    val="$(printf '%s' "$rest" | sed -E 's/^"[^"]+"[[:space:]]*:[[:space:]]*"(.*)"$/\1/')"
    verdict="$(classify "$val")"
    kind="${verdict%%$'\t'*}"; reason="${verdict#*$'\t'}"
    case "$kind" in
      DENY) deny="${deny}  DENY: ${g}:${ln}: ${key} = ${val} — ${reason}${NL}";;
      WARN) warn="${warn}  WARN: ${g}:${ln}: ${key} = ${val} — ${reason}${NL}";;
    esac
  done <<EOF
$ghits
EOF
done

n_warn="$(count_lines "$warn")"

if [ -n "$note" ]; then
  echo "== NOTES (allowlisted route pins + the supervised-executor carve — allowed, and shown so they stay auditable) =="
  printf '%s' "$note"
fi

if [ -n "$warn" ]; then
  echo "== WARNINGS (non-fatal — full ids preferred) =="
  printf '%s' "$warn"
fi

if [ -n "$pins" ]; then
  echo "FAIL — model pin(s) in payload/agents frontmatter (outside the named allowlist the pin ITSELF is the defect, barred or not):"
  printf '%s' "$pins"
  echo "       DELETE the model: line. Model control is LAUNCHER-ONLY for every payload agent EXCEPT the"
  echo "       three NAMED model routes, whose pin IS their identity (launching the route IS the tier choice):"
  echo "         fable-executor · fable-subplanner · opus5-executor"
  echo "       Adding a name to that allowlist is a reviewed edit to lib/verify_models.sh, never a workaround:"
  echo "       a payload pin is rank 3 and overrides the launcher in EVERY session that installs the toolkit,"
  echo "       while an unspecified launch is rank 4 and inherits the MAIN model (measured 2026-08-04)."
  echo "       Launcher vocabulary (the Task model param takes ALIASES ONLY — full ids are rejected):"
  echo "         fable · sonnet · haiku    [opus barred at every scope]"
  echo "       Need a FULL id for one project? Write a project-scoped shadow pin (lib/crt-dev-model.sh),"
  echo "       never a pin in the shipped payload."
fi

if [ -n "$deny" ]; then
  echo "FAIL — barred model id(s) in the payload:"
  printf '%s' "$deny"
  echo "       Allowed FULL ids (A2_ROUTING_SCHEMA §MODEL TIERS):"
  echo "         T1 claude-opus-4-8 · T1_hardest claude-fable-5 · T2/T3 claude-sonnet-5 · T4 claude-haiku-4-5"
  echo "       claude-opus-5 is barred in any tier, any call EXCEPT in the ONE file named opus5-executor.md, on an"
  echo "       allowlisted agent surface (payload/agents/ + planner-kit/payload/.claude/agents/) — the supervised-"
  echo "       executor carve, which travels with that NAME and with the supervision contract in that file's body."
  echo "       On Claude Code the alias 'opus' IS that model and 'opusplan' plans on it: both stay barred"
  echo "       EVERYWHERE, allowlist and carve INCLUDED — an alias re-resolves silently, so it is never a route."
fi

if [ -n "$unpinned" ]; then
  echo "FAIL — allowlisted route(s) missing the model: pin that IS the route:"
  printf '%s' "$unpinned"
  echo "       These three are launched PARAMLESS so the rank-3 frontmatter pin governs. Strip the pin"
  echo "       and the launch falls to rank 4 and silently inherits the SESSION model — no error, no"
  echo "       DENY, just a route that quietly stopped being one, which is the exact failure the"
  echo "       verified-launch convention exists to prevent. PARITY CANNOT CATCH THIS: both homes drop"
  echo "       the pin together and stay byte-identical, so this check is the only thing that sees it."
  echo "       Restore the model: key in the frontmatter of the named file(s), in BOTH homes."
fi

if [ -n "$drift" ]; then
  echo "FAIL — allowlisted route(s) out of parity between their two homes:"
  printf '%s' "$drift"
  echo "       An allowlisted route ships TWICE: payload/agents (installed into the general ~/.claude) and"
  echo "       planner-kit/payload/.claude/agents (installed into each adopting project root). Two homes for"
  echo "       ONE route is a drift surface, and byte-identity is what makes the duplication safe — otherwise"
  echo "       a session's behaviour depends on which copy its install happened to take."
  echo "       Diff the pair, decide which side is intended, copy it over the other, and re-run this gate."
fi

if [ -n "$pins" ] || [ -n "$deny" ] || [ -n "$drift" ] || [ -n "$unpinned" ]; then exit 1; fi

allow_note=""; kit_note=""; parity_note=""
# Every clause below is appended ONLY when its subject is actually exercised, so a payload with no
# allowlisted route, no kit surface and no warnings prints the exact bare summary string it always
# did — the fixtures that assert that string are asserting a real invariant, not a formatting quirk.
if [ "$n_allow" -gt 0 ]; then
  sup_note=""
  [ "$n_sup" -gt 0 ] && sup_note=", $n_sup on the supervised claude-opus-5 carve"
  allow_note=" (+$n_allow allowlisted route pin(s) — admitted BY NAME${sup_note})"
fi
if [ "$n_kit_agents" -gt 0 ]; then
  kit_sup_note=""
  [ "$n_kit_sup" -gt 0 ] && kit_sup_note=", $n_kit_sup on the supervised claude-opus-5 carve"
  kit_note=" (+$n_kit_agents kit-shipped agent(s), $n_kit_full pinned — project scope via the kit installer${kit_sup_note})"
fi
[ "$n_parity" -gt 0 ] && parity_note=" ${n_parity} parity pair(s) byte-identical."
warn_note=""
[ "$n_warn" -gt 0 ] && warn_note=" ${n_warn} warning(s)."
echo "PASS — $n_agents agents, $n_keys model keys, $n_frag settings fragment(s) scanned, 0 banned.${allow_note}${kit_note}${parity_note}${warn_note}"
exit 0
