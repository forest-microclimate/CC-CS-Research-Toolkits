#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# verify_coupling.sh [PAYLOAD_DIR] — fail-closed gate that the FROZEN coupling manifest still
# matches the LIVE payload. Run as a pre-copy gate by install.sh (so --select can never install a
# skill/agent set the manifest doesn't actually describe) and standalone in CI.
#
# WHY THIS EXISTS (provenance-over-description): the manifest is a DESCRIPTION of the agent<->skill
# coupling; the payload agent bodies are the RECORD. A description that has drifted from the record
# is worse than none — it makes install.sh --select silently wrong. This gate re-derives the
# coupling from the record and fails closed on ANY divergence from the frozen manifest.
#
# USAGE:
#   bash verify_coupling.sh [PAYLOAD_DIR] [MANIFEST]   # gate: exit 1 on any drift
#   bash verify_coupling.sh --self-test                # regression guard (plants a drift, proves caught)
# PAYLOAD_DIR defaults to ./payload next to this script; MANIFEST to ./coupling_manifest_v1.tsv.
# Portable: POSIX + bash 3.2 (macOS default). No mapfile, no readlink -f, no GNU-only grep flags.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

# ── SEMANTIC ASSERTION ENGINE ────────────────────────────────────────────────
# A skill S is a DEPENDENCY of agent A iff A's body references S with an OPERATIONAL or DEFER-TO
# intent — NOT merely a word-token match, and NOT a BOUNDARY ("you do NOT do X — that's `S`") or
# an EXAMPLE mention. We approximate the semantic class the frozen manifest encoded by hand with
# two robust, record-grounded rules that need no LLM at gate time:
#   DEP   cue: a load/use/apply/invoke/defer/hand off/companion/→ cue whose VERB OPERATES ON the skill,
#             i.e. the skill name FOLLOWS the cue within a short window (article/quote/"skill"/"to" allowed)
#   NODEP cue: the mention sits in a sentence with "do NOT"/"don't"/"not your"/"belongs to ... instead"
# The gate does not RE-CLASSIFY from scratch (that needs judgment); it ASSERTS three invariants that
# a drifted payload would violate, which is what a fail-closed gate needs.
#
# word-boundary skill-token match: skill name not flanked by [a-z0-9-] (so sci-file-index does not
# match sci-file-indexer, and `plan` inside "rename plan" is handled by requiring backtick for dial skills).
wb_ref() { # wb_ref <skill> <file>  -> prints matching lines (word-boundary)
  grep -nE "(^|[^a-z0-9-])$1([^a-z0-9-]|\$)" "$2" 2>/dev/null || true
}

# ── SELF-TEST (regression guard) ─────────────────────────────────────────────
# Proves the gate is genuinely fail-closed on the three drift classes it must catch:
#  (A) a NEW operational skill-ref in an agent that the manifest doesn't list as a dependency
#  (B) a manifest dependency whose skill DIR no longer exists in payload/skills
#  (C) a manifest dependency whose agent FILE no longer exists in payload/agents
if [ "${1:-}" = "--self-test" ]; then
  TD="$(mktemp -d)"; trap 'rm -rf "$TD"' EXIT
  mkdir -p "$TD/payload/agents" "$TD/payload/skills/known-skill" "$TD/payload/skills/orphan-skill"
  # a manifest: known-skill is DEDICATED to agent-x; orphan-skill is STANDALONE
  cat > "$TD/manifest.tsv" <<'M'
# FORMAT: machine-manifest
name	kind	tier	dep_referrers	nondep_referrers	dep_semantics	science_present	install_rule	note
known-skill	skill	DEDICATED	agent-x	-	agent-x:OPERATIONAL	yes	install IFF agent-x	-
orphan-skill	skill	STANDALONE	-	-	-	yes	installable alone	-
M
  # agent-x body: operationally loads known-skill (matches manifest). GOOD baseline.
  printf 'You load the known-skill for its workflow.\n' > "$TD/payload/agents/agent-x.md"
  rc=0
  # baseline must PASS
  if bash "$SCRIPT_DIR/verify_coupling.sh" "$TD/payload" "$TD/manifest.tsv" >/dev/null 2>&1; then
    echo "  (baseline) clean manifest PASSES ✓"
  else echo "  (baseline) FAIL: clean manifest rejected — gate over-strict"; rc=1; fi
  # (A) inject a new operational ref to orphan-skill in agent-x (manifest says STANDALONE) -> must FAIL
  printf 'You load the known-skill and also use the orphan-skill directly.\n' > "$TD/payload/agents/agent-x.md"
  if bash "$SCRIPT_DIR/verify_coupling.sh" "$TD/payload" "$TD/manifest.tsv" >/dev/null 2>&1; then
    echo "  (A) FAIL: new operational coupling NOT caught — gate not fail-closed"; rc=1
  else echo "  (A) new operational coupling CAUGHT ✓"; fi
  printf 'You load the known-skill for its workflow.\n' > "$TD/payload/agents/agent-x.md"  # restore
  # (B) remove known-skill's dir -> manifest dep points at a missing skill -> must FAIL
  rm -rf "$TD/payload/skills/known-skill"
  if bash "$SCRIPT_DIR/verify_coupling.sh" "$TD/payload" "$TD/manifest.tsv" >/dev/null 2>&1; then
    echo "  (B) FAIL: missing skill dir NOT caught"; rc=1
  else echo "  (B) missing skill dir CAUGHT ✓"; fi
  mkdir -p "$TD/payload/skills/known-skill"  # restore
  # (C) remove agent-x file -> manifest dep names a missing agent -> must FAIL
  rm -f "$TD/payload/agents/agent-x.md"
  if bash "$SCRIPT_DIR/verify_coupling.sh" "$TD/payload" "$TD/manifest.tsv" >/dev/null 2>&1; then
    echo "  (C) FAIL: missing agent file NOT caught"; rc=1
  else echo "  (C) missing agent file CAUGHT ✓"; fi
  [ "$rc" = 0 ] && echo "SELF-TEST: PASS" || echo "SELF-TEST: FAIL"
  exit "$rc"
fi

# ── GATE ─────────────────────────────────────────────────────────────────────
PAYLOAD="${1:-$SCRIPT_DIR/payload}"
MANIFEST="${2:-$SCRIPT_DIR/coupling_manifest_v1.tsv}"
AGENTS="$PAYLOAD/agents"
SKILLS="$PAYLOAD/skills"
fail=0
note() { echo "  $*"; }
echo "== verify_coupling: manifest=$MANIFEST payload=$PAYLOAD =="

[ -f "$MANIFEST" ] || { echo "FAIL — manifest not found: $MANIFEST"; exit 1; }
[ -d "$AGENTS" ]   || { echo "FAIL — agents dir not found: $AGENTS"; exit 1; }
[ -d "$SKILLS" ]   || { echo "FAIL — skills dir not found: $SKILLS"; exit 1; }

# Parse the manifest's SECTION 1 (skill rows). Columns: name kind tier dep_referrers ...
# We read: name, kind, tier, dep_referrers (semicolon list or '-').
while IFS=$'\t' read -r name kind tier deps rest; do
  case "$name" in \#*|""|name) continue;; esac      # skip header/comment/blank
  case "$name" in agent|"") continue;; esac
  # SECTION 2 has a different header (agent...) — stop when we hit it
  [ "$kind" = "n_skills" ] && break

  if [ "$kind" = "skill" ]; then
    # INVARIANT 1: the skill dir must exist in payload/skills
    if [ ! -d "$SKILLS/$name" ]; then
      note "DRIFT: manifest skill '$name' has no dir in payload/skills"; fail=1
    fi
    # INVARIANT 2: every dep_referrer agent must exist AND word-boundary-reference this skill
    if [ "$deps" != "-" ] && [ -n "$deps" ]; then
      OLDIFS="$IFS"; IFS=';'
      for a in $deps; do
        IFS="$OLDIFS"
        af="$AGENTS/$a.md"
        if [ ! -f "$af" ]; then
          note "DRIFT: '$name' lists dep agent '$a' but $a.md is missing"; fail=1
        elif [ -z "$(wb_ref "$name" "$af")" ]; then
          note "DRIFT: '$name' lists dep agent '$a' but $a.md no longer references it"; fail=1
        fi
        IFS=';'
      done
      IFS="$OLDIFS"
    fi
    # INVARIANT 3 (the fail-closed core): a STANDALONE skill must NOT be operationally referenced by
    # any agent (else it is actually coupled and the manifest under-describes it). We flag a
    # word-boundary ref that co-occurs with a DEP cue and NOT a NODEP cue.
    if [ "$tier" = "STANDALONE" ]; then
      for af in "$AGENTS"/*.md; do
        refs="$(wb_ref "$name" "$af")"
        [ -z "$refs" ] && continue
        # DIAL-SKILL RULE (matches how the manifest was derived): plan/solo/collab are common English
        # words, so a bare token match is a false positive ("surface the plan", "rename_plan.tsv").
        # For these, a coupling counts ONLY if the skill name is BACKTICKED. Drop non-backtick refs.
        case "$name" in
          plan|solo|collab)
            refs="$(printf '%s\n' "$refs" | grep -F "\`$name\`" || true)"
            [ -z "$refs" ] && continue ;;
        esac
        # DEP cue present and NODEP cue absent => an undeclared operational coupling. Per the design
        # ruling, a cue counts ONLY when its verb OPERATES ON the skill: the skill name (optionally
        # backticked/quoted, optionally preceded by an article or "to"/"skill") must FOLLOW the cue
        # within a short window. So "apply the writing-science checklist" counts, but "apply the
        # <other-object> ... writing-science" (name NOT adjacent to the cue) does not. The standalone
        # generic cues (companion skill, →) likewise count only with the name adjacent.
        _art='((the|a|an|your|its|to|skill)[[:space:]]+)*'    # short window: optional article / to / skill
        _nm="[\`\"']?$name"                                   # skill name, optional leading backtick/quote
        _cue='(load|use|apply|invoke|defer|hand[[:space:]]+off|companion[[:space:]]+skill)'
        dep_cue="$(printf '%s\n' "$refs" | grep -iE "(^|[^a-z0-9])${_cue}[[:space:]]+${_art}${_nm}|→[[:space:]]*${_art}${_nm}" || true)"
        nodep_cue="$(printf '%s\n' "$refs" | grep -iE "do not|don't|not your|isn't your|belongs to|instead" || true)"
        if [ -n "$dep_cue" ] && [ -z "$nodep_cue" ]; then
          note "DRIFT: STANDALONE '$name' is operationally referenced by $(basename "$af" .md) — should be coupled"
          fail=1
        fi
      done
    fi
  fi
done < "$MANIFEST"

if [ "$fail" = 0 ]; then
  echo "PASS — frozen coupling manifest matches the live payload."
  exit 0
else
  echo "FAIL — coupling manifest has drifted from the payload record (see DRIFT lines above)."
  echo "       Re-derive + re-freeze the manifest before shipping; do NOT edit the payload to match a stale manifest."
  exit 1
fi
