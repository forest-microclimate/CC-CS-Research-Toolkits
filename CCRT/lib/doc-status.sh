#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# doc-status.sh — check/stamp in-band STATUS headers on durable toolkit docs.
# Convention: payload/rules/doc-currency.machine.md (RULE.status_header_present + RULE.status_form).
# Portable: POSIX + bash 3.2 (macOS default). No GNU sed -i, no readlink -f, no `timeout`, no mapfile.
#
# USAGE:
#   bash lib/doc-status.sh check  [ROOT]          # report unstamped durable docs; ADVISORY (exit 0) — for a live ~/.claude
#   bash lib/doc-status.sh check  [ROOT] --strict # same, but EXIT 1 if any missing (GATE mode — used by install.sh on payload/)
#   bash lib/doc-status.sh stamp  [ROOT]          # add `# STATUS: CURRENT (today).` to unstamped docs (idempotent)
#   bash lib/doc-status.sh list   [ROOT]          # print every durable doc + its current STATUS value
# ROOT defaults to the payload/ dir next to this script's repo. Non-destructive except `stamp`,
# which inserts exactly one line and never touches an already-stamped file.
#
# WHY strict vs advisory: against payload/ the toolkit OWNS every durable doc, so any unstamped
# doc is a real defect => --strict (gate, exit 1). Against a live ~/.claude the tree ALSO holds
# the user's own pre-existing skills/agents and third-party docs the toolkit did NOT author and
# cannot stamp; flagging those as failures would make the check cry wolf. So a bare `check` on a
# live tree is ADVISORY (lists unstamped docs for the user's eye, but exits 0). backups/ + plugins/
# are pruned entirely (installer snapshots + CC marketplace — never toolkit currency surface).
set -u

MODE="${1:-check}"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${2:-$SELF_DIR/../payload}"
# --strict may be arg 2 (ROOT omitted) or arg 3; scan all args for it.
STRICT=0
for a in "$@"; do [ "$a" = "--strict" ] && STRICT=1; done
# if ROOT itself is the --strict flag (check --strict with no ROOT), restore the default ROOT.
[ "$ROOT" = "--strict" ] && ROOT="$SELF_DIR/../payload"
TODAY="$(date +%Y-%m-%d)"

# --- which files are DEF.durable-doc (doc-currency.machine.md) -------------------------------
# rules/*, agents/*, skills/*/SKILL.md, methodology/*, CLAUDE*.md, any *.machine.md.
# EXCLUDE: rendered .pdf (not text), xbeep/ (vendored), *_REPORT* (dated one-shots), human .md twins
# of a *.machine.md (the machine root is the stamped source of truth; the twin is derived).
is_durable() {
  # skip dot-basename files: macOS AppleDouble sidecars (._foo), .DS_Store, any dotfile.
  # a macOS-origin tree tarred+extracted on Linux materializes ._<name>.machine.md files
  # that would otherwise match *.machine.md below — they are binary metadata, not docs.
  b="${1##*/}"
  case "$b" in
    .*) return 1 ;;
  esac
  case "$1" in
    *_REPORT*|*/xbeep/*|*.pdf) return 1 ;;
  esac
  # EXCLUDE non-toolkit trees (keep in sync with the find -prune in collect()):
  #  backups/ = the installer's OWN timestamped pre-install snapshots (date IS its currency,
  #             same principle as the *_REPORT dated-one-shot exclusion — never a live surface);
  #  plugins/ = Claude Code's third-party plugin marketplace (not toolkit-authored, unstampable by us);
  #  .git/    = version control. None are docs the toolkit's currency convention governs.
  #  dda-templates/ = blank DDA category FORMS (placeholders, not live claims); they carry the DDA
  #             header schema and are governed by lib/check_current_documents.py, not this currency gate.
  case "$1" in
    */backups/*|*/plugins/*|*/.git/*|*/dda-templates/*) return 1 ;;
  esac
  case "$1" in
    *.machine.md) return 0 ;;
    */rules/*.md|*/agents/*.md) return 0 ;;
    */skills/*/SKILL.md) return 0 ;;
    */methodology/*.md) return 0 ;;
    *CLAUDE*.md) return 0 ;;
  esac
  return 1
}

# a human .md that has a *.machine.md sibling is DERIVED — skip (root carries the header)
has_machine_sibling() {
  case "$1" in *.machine.md) return 1 ;; esac
  [ -f "${1%.md}.machine.md" ]
}

# does the file open with a YAML frontmatter block (--- … ---)?
has_frontmatter() { [ "$(head -1 "$1")" = "---" ]; }

# line number of the frontmatter CLOSING fence (the 2nd `---`), or empty
frontmatter_end() {
  awk 'NR==1 && $0=="---"{infm=1; next} infm && $0=="---"{print NR; exit}' "$1"
}

# STATUS value carried as a `# STATUS:` comment line. It sits on line 2 for a
# machine doc, or just after the frontmatter close for a YAML doc — which can be
# line 7-8 for agents with tools/model/color keys. Scan a window past the longest
# realistic frontmatter (12 lines) so those are still found. First hit only.
status_of() {
  head -12 "$1" | grep -iE '^(#[[:space:]]*)?STATUS:' | head -1 \
    | sed -E 's/^(#[[:space:]]*)?STATUS:[[:space:]]*//I; s/[[:space:]].*$//'
}

# enumerate durable docs (find is POSIX; -print0 avoided for bash-3.2 read compat)
collect() {
  # prune non-toolkit trees (keep in sync with the is_durable exclusion above): don't even
  # walk the installer's own backups, the CC plugin marketplace, or VCS — big + irrelevant.
  find "$ROOT" \( -name backups -o -name plugins -o -name .git -o -name dda-templates \) -prune -o -type f -name '*.md' -print 2>/dev/null | sort | while IFS= read -r f; do
    is_durable "$f" || continue
    has_machine_sibling "$f" && continue
    printf '%s\n' "$f"
  done
}

n_total=0; n_stamped=0; n_missing=0; missing_list=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  n_total=$((n_total+1))
  sv="$(status_of "$f")"
  if [ -n "$sv" ]; then
    n_stamped=$((n_stamped+1))
    [ "$MODE" = list ] && printf '%-64s %s\n' "${f#$ROOT/}" "$sv"
  else
    n_missing=$((n_missing+1))
    missing_list="$missing_list$f
"
    [ "$MODE" = list ] && printf '%-64s %s\n' "${f#$ROOT/}" "(none)"
  fi
done <<EOF
$(collect)
EOF

case "$MODE" in
  list)
    printf '\n%s durable docs · %s stamped · %s missing\n' "$n_total" "$n_stamped" "$n_missing" ;;
  check)
    if [ "$n_missing" -gt 0 ]; then
      if [ "$STRICT" = 1 ]; then
        printf 'STATUS-header CHECK: %s/%s durable docs MISSING a header:\n' "$n_missing" "$n_total"
        printf '%s' "$missing_list" | sed "s#^$ROOT/#  - #"
        exit 1
      fi
      # advisory (live-tree) mode: list for the user's eye, but do NOT fail — unstamped docs
      # here may be user-owned or third-party, which the toolkit neither authored nor can stamp.
      printf 'STATUS-header CHECK (advisory): %s/%s durable docs have no header (may be user-owned/third-party):\n' "$n_missing" "$n_total"
      printf '%s' "$missing_list" | sed "s#^$ROOT/#  - #"
      printf 'OK — %s toolkit-convention docs stamped. (advisory: use --strict to fail on any miss, as the install gate does.)\n' "$n_stamped"
      exit 0
    fi
    printf 'STATUS-header CHECK: OK — all %s durable docs stamped.\n' "$n_total" ;;
  stamp)
    stamped=0
    printf '%s' "$missing_list" | while IFS= read -r f; do
      [ -n "$f" ] || continue
      tmp="$f.crttmp.$$"
      note="STATUS: CURRENT (${TODAY}). Auto-stamped by doc-status.sh; refine the note on next edit."
      if has_frontmatter "$f"; then
        # YAML frontmatter: insert a `# STATUS:` comment line AFTER the closing --- fence,
        # so the skill/agent loader's frontmatter parse is untouched.
        fe="$(frontmatter_end "$f")"
        if [ -n "$fe" ]; then
          awk -v fe="$fe" -v note="$note" 'NR==fe{print; print "# " note; next} {print}' "$f" > "$tmp" && mv "$tmp" "$f"
        else
          # malformed frontmatter (no close) — skip rather than corrupt
          printf '  SKIP (open frontmatter): %s\n' "${f#$ROOT/}"; rm -f "$tmp"; continue
        fi
      else
        # machine doc: insert after line 1 (the `# <name> …` title line)
        awk -v note="$note" 'NR==1{print; print "# " note; next} {print}' "$f" > "$tmp" && mv "$tmp" "$f"
      fi
      printf '  stamped: %s\n' "${f#$ROOT/}"
    done
    # recount after stamping
    left=0
    while IFS= read -r f; do [ -n "$f" ] || continue; [ -z "$(status_of "$f")" ] && left=$((left+1)); done <<EOF2
$(collect)
EOF2
    printf 'stamp done — %s docs now missing a header.\n' "$left" ;;
  *)
    printf 'usage: doc-status.sh {check|stamp|list} [ROOT]\n'; exit 2 ;;
esac
