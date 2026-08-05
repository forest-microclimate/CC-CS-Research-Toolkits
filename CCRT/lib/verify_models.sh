#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# verify_models.sh [PAYLOAD_DIR] — fail-closed gate on the MODEL keys the payload ships.
# EXIT 1 (listing every offender file:line) if a payload/agents frontmatter carries ANY `model:`
# key, or if anything scanned names a BARRED model. WARNINGS (a bare alias outside payload/agents)
# print but NEVER fail.
#
# WHY THIS EXISTS — TWO contracts, inverted 2026-08-04 (F2):
#  (1) ZERO PINS in payload/agents. Model control on the shipped payload is LAUNCHER-ONLY: the
#      launcher names the model on the Task call. A frontmatter pin is RANK 3 of the measured
#      precedence (env var > Task param > frontmatter > inherit the main model), so a shipped pin
#      OVERRIDES the launcher choice for every session that installs it — THE PIN ITSELF IS THE
#      DEFECT here, barred or not. MEASURED CONSTRAINT (2026-08-04, live InputValidationError):
#      the Task `model` param accepts ALIASES ONLY {sonnet|opus|haiku|fable} — no full ids — so
#      the launcher vocabulary is `fable` · `sonnet` · `haiku` (`opus` barred).
#      [SUPERSEDED 2026-08-04, O6 one-sweep — an omitted param is rank 4 and requests the MAIN
#      model, not fable; and "naming fable risks a silent resolve" was a REAL observation with the
#      wrong cause: serving-side SUBSTITUTION of fable requests, not alias resolution]
#      ~~OMIT ⇒ fable · naming `fable` risks the silent resolve to claude-opus-5~~.
#      FULL-ID precision is reachable ONLY through a PROJECT-SCOPED shadow pin
#      (lib/crt-dev-model.sh) — the same rank-3 mechanism, narrowed to one project — which is why
#      payload-project/agents (project scope) may still pin and payload/agents (user scope) may not.
#  (2) THE BARRED-ID BAN, with ONE carve added 2026-08-04 (O-series). claude-opus-5 is barred in
#      any tier, any call (user bar) — EXCEPT in `payload-project/agents/`, where the supervised
#      executor class (opus5-executor) may pin it. WHY the carve is safe exactly there and nowhere
#      else: a payload/agents pin installs into the general ~/.claude and rides into EVERY session,
#      while a payload-project pin shadows exactly ONE project root the operator names at install
#      time — so the model can only run where a Planner has deliberately placed it. The BARE aliases
#      `opus` and `opusplan` stay DENIED everywhere, INCLUDING payload-project: an alias re-resolves
#      silently (that is how `opus` became a barred pin without any file changing), so it can never
#      be the sanctioned route. This gate is the CC counterpart of the model_route_gate named in A2
#      §COMPANION GATES, moved from dispatch time to BUILD time; the DISPATCH-time half of the alias
#      ban now lives in payload/hooks/opus-dispatch-guard.sh (PreToolUse, matcher=Task).
#
# USAGE:
#   bash verify_models.sh [PAYLOAD_DIR]      # gate: exit 1 on any pin or barred id, 0 otherwise
# PAYLOAD_DIR defaults to ../payload resolved from this script's own location (lib/ -> toolkit root),
# matching lib/scrub_verify.sh.
# REGRESSION GUARD: tests/test_verify_models.sh — red-before/green-after fixtures (A2 §FIXTURE
# CONTRACT), run SEPARATELY from any suite. Its RED fixtures reproduce BOTH recorded defects: the
# pre-fix barred state (agents on bare `opus` + a personal fragment on "opus[1m]") and the pre-F2
# PINNED state (agents on claude-opus-4-8 / claude-fable-5, allowed ids that are now themselves the
# defect).
#
# WHAT IT CHECKS
#   agents   payload/agents/*.md   — the `model:` key INSIDE the YAML frontmatter only (a `model:`
#                                    written in the BODY is prose — e.g. a doc quoting this very ban
#                                    — and must not trip the gate). ANY such key FAILS (contract 1);
#                                    a barred VALUE is named as barred too, in the same finding.
#   project  payload-project/agents/*.md — OPTIONAL, project scope: pins are LEGAL here (the
#                                    sanctioned full-id escape hatch), so only contract 2 applies —
#                                    and contract 2 runs here in its CARVED form: claude-opus-5 is
#                                    ALLOWED (reported as a NOTE, never silently), the bare aliases
#                                    `opus`/`opusplan` are still DENIED.
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
# SCOPE ARG (added 2026-08-04): classify <value> [general|project], default general. It changes
#         EXACTLY ONE branch — claude-opus-5 — and nothing else. At `project` scope that id returns
#         SUPERVISED (allowed, reported as a NOTE); at `general` scope it stays DENY. Every alias
#         branch below is scope-INDEPENDENT on purpose: an alias re-resolves silently, so it can
#         never be the sanctioned route, not even at project scope.
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
      if [ "$_scope" = "project" ]; then
        printf 'SUPERVISED\tclaude-opus-5 at PROJECT scope — the supervised-executor carve: legal here because a payload-project pin shadows ONE named project root, never the general ~/.claude\n'
        return
      fi
      printf 'DENY\tclaude-opus-5 is barred in any tier, any call (user bar) outside the project-scoped agent surfaces (payload-project/agents/ + planner-kit/payload/.claude/agents/) — project scope is the ONE carve (the supervised-executor class)\n'; return;;
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

deny=""; pins=""; warn=""; note=""; n_agents=0; n_keys=0; n_frag=0; n_proj_agents=0; n_proj_full=0; n_proj_sup=0; n_kit_agents=0; n_kit_full=0; n_kit_sup=0

# --- agents: CONTRACT 1 — ZERO `model:` keys in the YAML frontmatter -------------------------
# An agent with no model: line is the REQUIRED state, so it is silent (not a warning — 18 silent
# agents warning on every run would be noise the operator learns to skip). Every key found is a
# PIN offender; if its value is also barred, the finding names that too (contract 2 in the same
# line), so one run reports both defects rather than hiding the barred id behind the pin verdict.
for f in "$AGENTS"/*.md; do
  [ -f "$f" ] || continue
  n_agents=$((n_agents + 1))
  hits="$(frontmatter_model_lines "$f")"
  [ -n "$hits" ] || continue
  while IFS=$'\t' read -r ln raw; do
    [ -n "$ln" ] || continue
    n_keys=$((n_keys + 1))
    val="$(unquote "$raw")"
    verdict="$(classify "$val")"
    kind="${verdict%%$'\t'*}"; reason="${verdict#*$'\t'}"
    extra=""
    [ "$kind" = "DENY" ] && extra=" — AND the value is barred: ${reason}"
    pins="${pins}  PIN:  ${f}:${ln}: model: ${val} — agent frontmatter must carry NO model key (model control is launcher-only)${extra}${NL}"
  done <<EOF
$hits
EOF
done

if [ "$n_agents" -eq 0 ]; then
  echo "FAIL — no agent .md files found in $AGENTS (nothing to verify; the gate does not pass vacuously)."
  exit 1
fi

# --- project-specialty agents (payload-project/agents/*.md) — OPTIONAL; scanned only when present. ----
# CONTRACT 2 ONLY. These are PROJECT-scoped agents (installed via --project-items/--project-dest into
# one project's .claude/agents, never into the general ~/.claude), so a pin here shadows exactly one
# project — the same mechanism lib/crt-dev-model.sh writes, and the ONLY route to full-id precision
# now that the Task model param takes aliases only. A pin is therefore LEGAL here and contract 1 does
# NOT apply; the barred-id ban still does, and fails the gate exactly as in payload/. Counted
# SEPARATELY and reported as "(+N project agents)": they are NOT part of the payload/ agents the
# vacuous-pass guard above requires. payload-project/ is a SIBLING of payload/ (its project-specific
# TOKENS are out of the scrub gate's scope by design — scrub_verify.sh roots at payload/).
PROJECT_AGENTS="$(dirname "$PAYLOAD")/payload-project/agents"
if [ -d "$PROJECT_AGENTS" ]; then
  for f in "$PROJECT_AGENTS"/*.md; do
    [ -f "$f" ] || continue
    n_proj_agents=$((n_proj_agents + 1))
    hits="$(frontmatter_model_lines "$f")"
    if [ -z "$hits" ]; then
      warn="${warn}  WARN: ${f}: no model: line in frontmatter — inherits the session model (allowed)${NL}"
      continue
    fi
    while IFS=$'\t' read -r ln raw; do
      [ -n "$ln" ] || continue
      val="$(unquote "$raw")"
      verdict="$(classify "$val" project)"
      kind="${verdict%%$'\t'*}"; reason="${verdict#*$'\t'}"
      case "$kind" in
        DENY)       deny="${deny}  DENY: ${f}:${ln}: model: ${val} — ${reason}${NL}";;
        WARN)       warn="${warn}  WARN: ${f}:${ln}: model: ${val} — ${reason}${NL}";;
        SUPERVISED) n_proj_full=$((n_proj_full + 1)); n_proj_sup=$((n_proj_sup + 1))
                    note="${note}  NOTE: ${f}:${ln}: model: ${val} — ${reason}${NL}";;
        OK)         n_proj_full=$((n_proj_full + 1));;
      esac
    done <<EOF
$hits
EOF
  done
fi

# --- kit-shipped agents (planner-kit/payload/.claude/agents/*.md) — OPTIONAL; scanned only when present. ----
# CONTRACT 2 ONLY, same class as payload-project: the kit installs these into ONE project's
# .claude/agents (per-root install.sh run), never into the general ~/.claude — so pins are LEGAL
# here (the executor route) and the barred-id ban + supervised carve apply exactly as at project
# scope. Added 2026-08-04 (K11-C step 0.5): the kit began shipping pinned executors at v1.4, and a
# pin the gates do not watch must not ship.
KIT_AGENTS="$(dirname "$PAYLOAD")/planner-kit/payload/.claude/agents"
if [ -d "$KIT_AGENTS" ]; then
  for f in "$KIT_AGENTS"/*.md; do
    [ -f "$f" ] || continue
    n_kit_agents=$((n_kit_agents + 1))
    hits="$(frontmatter_model_lines "$f")"
    if [ -z "$hits" ]; then
      warn="${warn}  WARN: ${f}: no model: line in frontmatter — inherits the session model (allowed)${NL}"
      continue
    fi
    while IFS=$'\t' read -r ln raw; do
      [ -n "$ln" ] || continue
      val="$(unquote "$raw")"
      verdict="$(classify "$val" project)"
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
  echo "== NOTES (the supervised-executor carve — allowed, and shown so it stays auditable) =="
  printf '%s' "$note"
fi

if [ -n "$warn" ]; then
  echo "== WARNINGS (non-fatal — full ids preferred) =="
  printf '%s' "$warn"
fi

if [ -n "$pins" ]; then
  echo "FAIL — model pin(s) in payload/agents frontmatter (the pin ITSELF is the defect, barred or not):"
  printf '%s' "$pins"
  echo "       DELETE the model: line. Model control is LAUNCHER-ONLY: the launch names the model, and"
  echo "       an unspecified launch is rank 4 of the precedence and inherits the MAIN model (measured 2026-08-04)."
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
  echo "       claude-opus-5 is barred in any tier, any call EXCEPT payload-project/agents (the supervised-executor"
  echo "       carve — a project pin shadows one named project root, never the general ~/.claude). On Claude Code the"
  echo "       alias 'opus' IS that model and 'opusplan' plans on it: both stay barred EVERYWHERE, carve included."
fi

if [ -n "$pins" ] || [ -n "$deny" ]; then exit 1; fi

proj_note=""; kit_note=""
if [ "$n_proj_agents" -gt 0 ]; then
  sup_note=""
  # Appended ONLY when the carve is actually exercised, so a project tree with no supervised
  # executor keeps the exact pre-carve summary string.
  [ "$n_proj_sup" -gt 0 ] && sup_note=", $n_proj_sup on the supervised claude-opus-5 carve"
  proj_note=" (+$n_proj_agents project agent(s), $n_proj_full pinned to a full id — project scope MAY pin${sup_note})"
fi
if [ "$n_kit_agents" -gt 0 ]; then
  kit_sup_note=""
  [ "$n_kit_sup" -gt 0 ] && kit_sup_note=", $n_kit_sup on the supervised claude-opus-5 carve"
  kit_note=" (+$n_kit_agents kit-shipped agent(s), $n_kit_full pinned — project scope via the kit installer${kit_sup_note})"
fi
warn_note=""
[ "$n_warn" -gt 0 ] && warn_note=" ${n_warn} warning(s)."
echo "PASS — $n_agents agents, $n_keys model keys, $n_frag settings fragment(s) scanned, 0 banned.${proj_note}${kit_note}${warn_note}"
exit 0
