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
# TWO ARMS, one per direction of the description<->record relation:
#   ARM 1  MANIFEST -> PAYLOAD (invariants 1-3): every manifest row still describes something real.
#   ARM 2  PAYLOAD -> MANIFEST (invariants 4-6, the COMPLETENESS arm, added 2026-08-09): every
#          payload skill dir and agent file is actually REGISTERED. Arm 1 walks manifest ROWS, so an
#          item with NO row is INVISIBLE to it — which is exactly how `model-verification` and
#          `ssh-compute-provision` shipped unregistered, and an unregistered skill is UNINSTALLABLE
#          by name (lib/select_resolve.py resolves --select THROUGH this manifest). A gate that can
#          only see what it was told about cannot catch an omission; arm 2 is the omission arm.
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
# Proves the gate is genuinely fail-closed on the drift classes it must catch:
#  ARM 1 (manifest -> payload):
#   (A) a NEW operational skill-ref in an agent that the manifest doesn't list as a dependency
#   (B) a manifest dependency whose skill DIR no longer exists in payload/skills
#   (C) a manifest dependency whose agent FILE no longer exists in payload/agents
#  ARM 2 (payload -> manifest, the completeness arm):
#   (D) a payload SKILL DIR with no SECTION-1 row      (the model-verification / ssh-compute-provision class)
#   (E) a payload AGENT FILE with no SECTION-2 row     (the three-executor-routes class)
#   (F) a SECTION-2 agent row whose agent FILE is gone (a departed agent left registered)
if [ "${1:-}" = "--self-test" ]; then
  TD="$(mktemp -d)"; trap 'rm -rf "$TD"' EXIT
  mkdir -p "$TD/payload/agents" "$TD/payload/skills/known-skill" "$TD/payload/skills/orphan-skill"
  # a manifest: known-skill is DEDICATED to agent-x; orphan-skill is STANDALONE. SECTION 2 registers
  # agent-x — arm 2 requires every payload agent to carry one, so the fixture must carry one too.
  cat > "$TD/manifest.tsv" <<'M'
# FORMAT: machine-manifest
name	kind	tier	dep_referrers	nondep_referrers	dep_semantics	science_present	install_rule	note
known-skill	skill	DEDICATED	agent-x	-	agent-x:OPERATIONAL	yes	install IFF agent-x	-
orphan-skill	skill	STANDALONE	-	-	-	yes	installable alone	-

agent	n_skills	dedicated	shared	required_skills
agent-x	1	1	0	known-skill
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
  printf 'You load the known-skill for its workflow.\n' > "$TD/payload/agents/agent-x.md"  # restore
  # ---- ARM 2: the completeness (omission) cases ----
  # (D) a payload skill dir with NO manifest row -> must FAIL  [the unregistered-skill class]
  mkdir -p "$TD/payload/skills/unlisted-skill"
  if bash "$SCRIPT_DIR/verify_coupling.sh" "$TD/payload" "$TD/manifest.tsv" >/dev/null 2>&1; then
    echo "  (D) FAIL: unregistered payload skill NOT caught — completeness arm is not fail-closed"; rc=1
  else echo "  (D) unregistered payload skill CAUGHT ✓"; fi
  rmdir "$TD/payload/skills/unlisted-skill"  # restore
  # (E) a payload agent file with NO SECTION-2 row -> must FAIL  [the unregistered-agent class]
  printf 'A body that references nothing.\n' > "$TD/payload/agents/agent-unlisted.md"
  if bash "$SCRIPT_DIR/verify_coupling.sh" "$TD/payload" "$TD/manifest.tsv" >/dev/null 2>&1; then
    echo "  (E) FAIL: unregistered payload agent NOT caught"; rc=1
  else echo "  (E) unregistered payload agent CAUGHT ✓"; fi
  rm -f "$TD/payload/agents/agent-unlisted.md"  # restore
  # (F) a SECTION-2 row whose agent file is gone -> must FAIL  [the departed-agent class: a
  #     pure-role agent with no dep_referrer skills is invisible to arm 1's invariant 2]
  printf 'agent-departed\t0\t0\t0\t-\n' >> "$TD/manifest.tsv"
  if bash "$SCRIPT_DIR/verify_coupling.sh" "$TD/payload" "$TD/manifest.tsv" >/dev/null 2>&1; then
    echo "  (F) FAIL: dangling SECTION-2 agent row NOT caught"; rc=1
  else echo "  (F) dangling SECTION-2 agent row CAUGHT ✓"; fi
  # (G) restore -> the fixture must be CLEAN again (proves D/E/F failed for their planted reason,
  #     not because an earlier case left the fixture permanently broken)
  grep -v '^agent-departed' "$TD/manifest.tsv" > "$TD/m2.tsv" && mv "$TD/m2.tsv" "$TD/manifest.tsv"
  if bash "$SCRIPT_DIR/verify_coupling.sh" "$TD/payload" "$TD/manifest.tsv" >/dev/null 2>&1; then
    echo "  (G) restored fixture PASSES again ✓"
  else echo "  (G) FAIL: restored fixture still rejected — a planted drift was not undone"; rc=1; fi
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

# ── ARM 2 — COMPLETENESS (payload -> manifest). The arm above walks manifest ROWS, so an item with
# NO row is invisible to it. Here we walk the PAYLOAD and require a row for each thing found.
#   INVARIANT 4: every dir in payload/skills has a SECTION-1 skill row.
#   INVARIANT 5: every file in payload/agents has a SECTION-2 row (SECTION 2 is what makes an agent
#                selectable — select_resolve.py reads its closure from there).
#   INVARIANT 6: every SECTION-2 agent row still has its payload/agents file (the dangling half;
#                a pure-role agent with no dependent skills is invisible to invariant 2).
# Parsing is field-exact, not positional: SECTION-1 skill rows are `$2 == "skill"`, SECTION-2 rows
# are the >=5-field rows AFTER the `agent<TAB>n_skills` header. bash 3.2: no assoc arrays, no
# mapfile — membership is grep -qxF over a newline list.
S1_SKILL_ROWS="$(awk -F'\t' '/^[[:space:]]*#/ { next } $2 == "skill" { print $1 }' "$MANIFEST")"
S2_AGENT_ROWS="$(awk -F'\t' '
  /^[[:space:]]*#/ { next }
  $1 == "agent" && $2 == "n_skills" { s = 1; next }
  s == 1 && NF >= 5 && $1 != "" { print $1 }
' "$MANIFEST")"

# fail-closed on an unparseable manifest: a gate that silently reads ZERO rows would pass everything.
if [ -z "$S1_SKILL_ROWS" ]; then
  note "DRIFT: manifest has NO SECTION-1 skill rows (empty or unparseable: $MANIFEST)"; fail=1
fi
if [ -z "$S2_AGENT_ROWS" ]; then
  note "DRIFT: manifest has NO SECTION-2 agent rows (missing the 'agent<TAB>n_skills' header?)"; fail=1
fi

# INVARIANT 4 — payload skill dir => SECTION-1 row
for sd in "$SKILLS"/*/; do
  [ -d "$sd" ] || continue                       # unmatched glob: no skill dirs at all
  sn="$(basename "$sd")"
  if ! printf '%s\n' "$S1_SKILL_ROWS" | grep -qxF "$sn"; then
    note "DRIFT: payload skill '$sn' has NO row in the manifest — it is UNINSTALLABLE by name (--select cannot resolve it)"
    fail=1
  fi
done

# INVARIANT 5 — payload agent file => SECTION-2 row
for af in "$AGENTS"/*.md; do
  [ -f "$af" ] || continue
  an="$(basename "$af" .md)"
  if ! printf '%s\n' "$S2_AGENT_ROWS" | grep -qxF "$an"; then
    note "DRIFT: payload agent '$an' has NO SECTION-2 row — it is UNSELECTABLE and its skill closure is undeclared"
    fail=1
  fi
done

# INVARIANT 6 — SECTION-2 row => payload agent file
OLDIFS="$IFS"; IFS='
'
for an in $S2_AGENT_ROWS; do
  [ -z "$an" ] && continue
  if [ ! -f "$AGENTS/$an.md" ]; then
    note "DRIFT: SECTION-2 lists agent '$an' but payload/agents/$an.md is missing"
    fail=1
  fi
done
IFS="$OLDIFS"

if [ "$fail" = 0 ]; then
  echo "PASS — frozen coupling manifest matches the live payload (both arms: no drifted rows, no unregistered payload items)."
  exit 0
else
  echo "FAIL — coupling manifest has drifted from the payload record (see DRIFT lines above)."
  echo "       Re-derive + re-freeze the manifest before shipping; do NOT edit the payload to match a stale manifest."
  echo "       An 'has NO row' line means the OMISSION direction: register the payload item, do not delete it."
  exit 1
fi
