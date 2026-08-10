#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# STATUS: CURRENT (2026-08-04). software-developer agent model selector (user scope + project shadow).
# Header re-scoped to the F2 unpin policy (2026-08-04); the MECHANISM is unchanged.
# ============================================================================
# crt-dev-model.sh - choose which MODEL the software-developer agent runs on.
# ----------------------------------------------------------------------------
# POLICY (F2, 2026-08-04 - what this helper is FOR now). The shipped payload/agents carry NO
# frontmatter model pin: model control on the shipped payload is LAUNCHER-ONLY, and
# lib/verify_models.sh FAILS on any `model:` key in payload/agents OUTSIDE the named allowlist
# (fable-executor · fable-subplanner · opus5-executor, whose pin IS their route). But the Task tool's `model`
# param accepts ALIASES ONLY {sonnet|opus|haiku|fable} - no full ids (MEASURED 2026-08-04, live
# InputValidationError) - so the launcher's whole vocabulary is `fable` · `sonnet` · `haiku`
# [`opus` is barred at every scope].
# [SUPERSEDED 2026-08-04, O6 one-sweep - an omitted param is RANK 4 of the measured precedence
# (env var > Task param > agent frontmatter > inherit) and requests the MAIN model, not fable;
# and "naming fable risks a silent resolve" was a REAL observation with the WRONG cause -
# serving-side SUBSTITUTION of fable requests, an open vendor bug, not alias resolution]
# ~~OMIT the param => fable (the configured subagent default); naming `fable` risks the silent
# resolve to claude-opus-5~~.
# A FULL id is UNREACHABLE from a launch, but it IS legal at RANK 3, in agent frontmatter. This
# helper is the sanctioned route to one: it writes a PROJECT-SCOPED shadow agent, a rank-3 pin
# narrowed to exactly one project, without putting a pin back into the shipped payload. verify_models.sh scopes its zero-pin contract to payload/agents
# (and payload-project/agents, where project-scope pins stay legal); the paths this helper writes -
# $CLAUDE_DIR/agents/ and $PWD/.claude/agents/ - are OUTSIDE both, so its shadows never trip it.
#
# CONTRACT. Claude Code loads an agent's model from the "model:" key of its YAML frontmatter.
# This helper edits that ONE line for the software-developer agent, at either of two scopes, and
# it will ONLY ever write one of two vetted model ids:
#     fable   ->  model: claude-fable-5
#     opus48  ->  model: claude-opus-4-8
# Any other requested value is refused (exit 64). NOT WRITABLE HERE, deliberately - claude-opus-5,
# the bare alias opus, and opusplan (the aliases resolve to Claude Opus 5 on Claude Code >=2.1.219,
# and re-resolve silently whenever CC remaps them) - can NEVER be written: the dispatch accepts only
# the two verbs above, and the writer re-checks the id against a two-value allowlist and refuses
# otherwise (fail-closed, defense in depth).
# [SUPERSEDED 2026-08-04 - constrained supervised use; the ALLOWED list is UNCHANGED, see below]
# ~~claude-opus-5 is barred in any tier, any call~~ - as of 2026-08-04 claude-opus-5 is PERMITTED on
# Claude Code in exactly ONE position: a tightly-scoped supervised CHILD launched as
# `delegate:opus5-executor`, the project-scoped agent whose OWN frontmatter carries the pin, under a
# Planner's active watch. That does NOT make it writable here, and it must NOT be added to ALLOWED:
# this helper writes a GENERAL project shadow for the house executor agents, whereas the opus-5 pin
# is legal only INSIDE the opus5-executor agent file itself (lib/verify_models.sh contract 2 carves
# that one id as legal in payload-project/agents/ and nowhere else). Adding it here would put opus-5
# behind an ordinary executor carrying no supervision contract - the wrong model by the wrong route.
# It stays barred as the session default, as a coordinator or sub-planner, and as a raw model-field
# value in a routing block; the aliases stay barred everywhere, supervised runs included. This is the
# per-agent runtime counterpart of the build-time gate in lib/verify_models.sh.
#
# SCOPES.
#   (default)   edit  $CLAUDE_DIR/agents/software-developer.md  in place. Missing file -> exit 1.
#   --project   edit  ./.claude/agents/software-developer.md  (relative to $PWD). A project-scoped
#               agent SHADOWS the user-scoped one of the same name - a session started in this
#               project loads the project copy's frontmatter. For fable|opus48: if the project copy
#               does not exist yet it is CREATED by copying the user-scoped file, then its model
#               line is set (this is how you pin a per-project model without touching the global
#               default). If the user-scoped SOURCE is also missing -> exit 1.
#
# EDIT DISCIPLINE. Only "model:" line(s) INSIDE the frontmatter (between the leading --- and the
# next ---) are changed; every other byte is preserved verbatim, INCLUDING CRLF vs LF line endings
# (the file is read and written with newline="" so Python performs no line-ending translation). A
# "model:" string in the BODY (e.g. a code example) is never touched. Two structural edge cases:
#   * DUPLICATE keys - if the frontmatter carries MORE THAN ONE "model:" line (malformed YAML, but
#     last-wins parsing would let a stray second line govern), ALL of them are rewritten to the
#     requested id, so no non-vetted model line can survive an edit; the reader/`show` report the
#     LAST frontmatter model line, matching YAML last-wins semantics.
#   * ABSENT key - if the frontmatter has NO "model:" line, one is INSERTED just before the closing
#     --- fence (using the file's leading line ending). Since F2 this is the NORMAL path, not an
#     edge case: every shipped agent is unpinned, so the first `fable`/`opus48` on a fresh install
#     always inserts. (Verified 2026-08-04 against an unpinned source, both scopes, idempotent.)
# The write is atomic: a temp file is written then os.replace()d over the target (POSIX-atomic), so a
# crash mid-write can never leave a truncated agent file. NOTE: if the agent path is a SYMLINK,
# os.replace swaps in a REGULAR FILE at that path (the symlink entry is replaced, not followed).
# Re-running the same verb is idempotent (byte-identical result).
#
# show / show --project.
#   show            prints the user-scope model line, whether a project shadow exists in $PWD (and
#                   its model), and the precedence rule.
#   show --project  reports the project copy's model line, or "no project shadow (user-scope governs)".
#
# PATH RESOLUTION. $CLAUDE_DIR defaults to ${CLAUDE_HOME:-$HOME/.claude} (house convention, cf.
# crt-persona.sh); an explicit $CLAUDE_DIR always wins. Project scope is always relative to $PWD.
#
# USAGE:
#   crt-dev-model.sh fable   [--project]   # set model -> claude-fable-5
#   crt-dev-model.sh opus48  [--project]   # set model -> claude-opus-4-8
#   crt-dev-model.sh show    [--project]   # report the current model + precedence
#   crt-dev-model.sh --help
# EXIT: 0 ok - 1 environment/IO error (missing agent file, missing --project source, write failed)
#       - 64 usage error (bad subcommand, surplus args, unknown option, or a disallowed model id).
# Portable: POSIX + bash 3.2 (macOS default). python3 required (frontmatter edit + atomic write).
# TESTABILITY. Sourcing with CRT_DEV_MODEL_LIB=1 loads the functions WITHOUT running the CLI dispatch,
# so the writer's fail-closed model-id allowlist can be exercised directly by the acceptance suite.
# ============================================================================
set -uo pipefail

CLAUDE_DIR="${CLAUDE_DIR:-${CLAUDE_HOME:-$HOME/.claude}}"
SELF="$(basename "${BASH_SOURCE[0]:-$0}")"
AGENT_REL="agents/software-developer.md"

usage(){ sed -n '2,/^[^#]/p' "${BASH_SOURCE[0]:-$0}" | sed -n 's/^# \{0,1\}//p'; exit "${1:-0}"; }
die(){ echo "$SELF: $1" >&2; exit "${2:-1}"; }
usage_err(){ echo "$SELF: $1" >&2; echo >&2; usage 64 >&2; }

need_python(){
  command -v python3 >/dev/null 2>&1 || die "python3 not found on PATH (required to edit agent frontmatter)"
}

# verb -> the ONE allowed model id. User input NEVER becomes a model id directly; only these two
# hardcoded ids can leave this function, and the writer re-validates against the same allowlist.
model_for_verb(){
  case "$1" in
    fable)  printf 'claude-fable-5' ;;
    opus48) printf 'claude-opus-4-8' ;;
    *)      return 1 ;;
  esac
}

# frontmatter_model_value <file>: print the frontmatter "model:" value (no trailing newline).
# exit: 0 printed a value - 3 file present but no frontmatter "model:" line - 4 file missing.
# (heredoc lives in this function body, NOT inside a $(...), so command-substituting the CALL is safe.)
frontmatter_model_value(){
  python3 - "$1" <<'PY'
import sys, os, re
path = sys.argv[1]
if not os.path.exists(path):
    sys.exit(4)
with open(path, newline="") as f:
    lines = f.read().splitlines()
if not lines or lines[0].strip() != "---":
    sys.exit(3)
val = None
for i in range(1, len(lines)):
    if lines[i].strip() == "---":
        break
    m = re.match(r'^\s*model\s*:\s*(.*)$', lines[i])
    if m:
        v = re.sub(r'\s+#.*$', '', m.group(1)).strip()
        if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
            v = v[1:-1]
        val = v          # keep scanning: YAML is last-wins, so the LAST frontmatter model line governs
if val is None:
    sys.exit(3)
sys.stdout.write(val)
sys.exit(0)
PY
}

# write_model_line <file> <model_id>: set the frontmatter "model:" line, preserving every other byte.
# Atomic (temp + os.replace). Refuses a non-allowlisted id (exit 64). exit 1 on IO/frontmatter error.
write_model_line(){
  python3 - "$1" "$2" <<'PY'
import sys, os, re
path, new_model = sys.argv[1], sys.argv[2]
ALLOWED = ("claude-fable-5", "claude-opus-4-8")   # MUST stay in lockstep with model_for_verb (bash side)
if new_model not in ALLOWED:
    sys.stderr.write("crt-dev-model: refusing to write disallowed model id: %s\n" % new_model)
    sys.exit(64)
if not os.path.exists(path):
    sys.stderr.write("crt-dev-model: agent file not found: %s\n" % path)
    sys.exit(1)
with open(path, newline="") as f:              # newline="" -> no line-ending translation (CRLF preserved)
    text = f.read()
lines = text.splitlines(keepends=True)
if not lines or lines[0].rstrip("\r\n").strip() != "---":
    sys.stderr.write("crt-dev-model: %s has no YAML frontmatter (first line is not '---')\n" % path)
    sys.exit(1)
close = None
for i in range(1, len(lines)):
    if lines[i].rstrip("\r\n").strip() == "---":
        close = i
        break
if close is None:
    sys.stderr.write("crt-dev-model: %s frontmatter has no closing '---'\n" % path)
    sys.exit(1)

def split_eol(s):
    if s.endswith("\r\n"): return s[:-2], "\r\n"
    if s.endswith("\n"):   return s[:-1], "\n"
    if s.endswith("\r"):   return s[:-1], "\r"
    return s, ""

changed = 0
for i in range(1, close):                      # frontmatter interior ONLY; body is never scanned
    content, eol = split_eol(lines[i])
    if re.match(r'^(\s*)model\s*:', content):
        indent = re.match(r'^(\s*)', content).group(1)
        lines[i] = "%smodel: %s%s" % (indent, new_model, eol)
        changed += 1                           # rewrite ALL model: lines (NO break): a stray/duplicate
                                               # model line (YAML last-wins) must not survive as a barred id
if changed == 0:                               # no model: line in frontmatter -> insert before close
    _, eol0 = split_eol(lines[0])
    if eol0 == "":
        eol0 = "\n"
    lines.insert(close, "model: %s%s" % (new_model, eol0))

new_text = "".join(lines)
tmp = "%s.tmp.%d" % (path, os.getpid())        # pid-suffixed: distinct writers never collide
try:
    with open(tmp, "w", newline="") as f:       # newline="" -> bytes written as-is (no \n -> os.linesep)
        f.write(new_text)
    os.replace(tmp, path)                       # atomic swap; if path is a SYMLINK it is replaced by a regular file
except Exception as e:
    try:
        os.remove(tmp)
    except OSError:
        pass
    sys.stderr.write("crt-dev-model: write failed for %s: %s\n" % (path, e))
    sys.exit(1)
PY
}

user_agent(){ printf '%s' "$CLAUDE_DIR/$AGENT_REL"; }
proj_agent(){ printf '%s' "$PWD/.claude/$AGENT_REL"; }

cmd_set_user(){
  local verb="$1" ua model
  ua="$(user_agent)"
  [ -f "$ua" ] || die "user-scope agent not found: $ua (nothing written)" 1
  model="$(model_for_verb "$verb")" || die "internal: no model mapped for verb '$verb'" 1
  write_model_line "$ua" "$model" || exit $?
  echo "set user-scope software-developer model -> $model"
  echo "  file : $ua"
  echo "  takes effect on the NEXT new session (a project shadow, if any, overrides it there)."
}

cmd_set_project(){
  local verb="$1" pa ua model
  pa="$(proj_agent)"; ua="$(user_agent)"
  model="$(model_for_verb "$verb")" || die "internal: no model mapped for verb '$verb'" 1
  if [ ! -f "$pa" ]; then
    [ -f "$ua" ] || die "cannot create project shadow: user-scope source not found: $ua (nothing written)" 1
    mkdir -p "$PWD/.claude/agents" || die "could not create $PWD/.claude/agents" 1
    cp "$ua" "$pa" || die "failed to copy user-scope agent -> $pa" 1
    echo "created project shadow from user scope: $pa"
  fi
  write_model_line "$pa" "$model" || exit $?
  echo "set project-shadow software-developer model -> $model"
  echo "  file : $pa"
  echo "  this project copy SHADOWS the user-scope agent for sessions started here."
}

cmd_show_user(){
  local ua pa um urc pm prc
  ua="$(user_agent)"; pa="$(proj_agent)"
  um="$(frontmatter_model_value "$ua")"; urc=$?
  case "$urc" in
    0) echo "user scope     : model: $um" ;;
    3) echo "user scope     : agent present, no model: line in frontmatter" ;;
    *) echo "user scope     : agent file NOT FOUND" ;;
  esac
  echo "                 $ua"
  if [ -f "$pa" ]; then
    pm="$(frontmatter_model_value "$pa")"; prc=$?
    case "$prc" in
      0) echo "project shadow : PRESENT - model: $pm" ;;
      3) echo "project shadow : PRESENT - no model: line" ;;
      *) echo "project shadow : PRESENT" ;;
    esac
    echo "                 $pa"
  else
    echo "project shadow : none (user-scope governs)"
    echo "                 $pa"
  fi
  cat <<'NOTE'
  precedence: project shadow > user agent; a per-launch Agent-tool model override > both.
  Shipped agents are UNPINNED (F2): with no shadow and no launch override, a child runs on the
  configured subagent default (claude-fable-5), which the launcher selects by naming NO model.
  The Task model param takes ALIASES ONLY (sonnet | haiku; opus is barred, fable risks a silent
  resolve), so a FULL id is reachable only through a shadow written here -- which is what opus48
  is for: there is NO non-banned alias for Opus 4.8.
NOTE
}

cmd_show_project(){
  local pa pm prc
  pa="$(proj_agent)"
  if [ -f "$pa" ]; then
    pm="$(frontmatter_model_value "$pa")"; prc=$?
    case "$prc" in
      0) echo "project shadow : model: $pm" ;;
      3) echo "project shadow : present, no model: line in frontmatter" ;;
      *) echo "project shadow : present" ;;
    esac
    echo "                 $pa"
  else
    echo "no project shadow (user-scope governs)"
    echo "                 $pa"
  fi
}

# Sourced as a library (CRT_DEV_MODEL_LIB=1)? Load the functions above, then skip the CLI below - lets
# the acceptance suite call write_model_line directly to exercise its fail-closed model-id allowlist.
if [ "${CRT_DEV_MODEL_LIB:-0}" = "1" ]; then return 0 2>/dev/null || exit 0; fi

# ---- parse: exactly one verb + optional --project (flag may appear in any position) ------------
PROJECT=0
VERB=""
seen_verb=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --project)  PROJECT=1 ;;
    -h|--help)  usage 0 ;;
    -*)         usage_err "unknown option '$1'" ;;
    *)
      if [ "$seen_verb" -eq 1 ]; then
        usage_err "too many arguments (expected: fable | opus48 | show [--project])"
      fi
      VERB="$1"; seen_verb=1 ;;
  esac
  shift
done

case "$VERB" in
  fable|opus48)
    need_python
    if [ "$PROJECT" -eq 1 ]; then cmd_set_project "$VERB"; else cmd_set_user "$VERB"; fi ;;
  show)
    need_python
    if [ "$PROJECT" -eq 1 ]; then cmd_show_project; else cmd_show_user; fi ;;
  "")
    usage_err "missing subcommand (expected: fable | opus48 | show [--project])" ;;
  *)
    usage_err "unknown subcommand '$VERB' (expected: fable | opus48 | show [--project])" ;;
esac
