#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# plan-routing-gate.sh — PLAN-TIME routing-block enforcement (PreToolUse, matcher=ExitPlanMode).
# STATUS: CURRENT (2026-08-04). A2_ROUTING_SCHEMA lint checks L1-L4, CC half.
#
# ─── L4 REWORK (2026-08-04, O-series: opus-5 as CONSTRAINED SUPERVISED USE) ────────
#   claude-opus-5 is no longer barred outright on the CC side; it is legal in exactly one
#   shape — a tightly-scoped CHILD under a Planner's active watch, launched through the
#   project-scoped `opus5-executor` agent. Three consequences here:
#   (a) A track whose executor is `delegate:opus5-executor` is LEGAL, but ONLY when the
#       track carries a SUPERVISION MARKER (`"supervised": true` or `"supervision":
#       "planner-watch"`). An UNSUPERVISED opus5-executor track is a new FAIL: the marker
#       is what distinguishes "a planner is watching this run" from "someone routed the
#       model and walked away", and the whole permission rests on the watch.
#   (b) `T1_supervised` joins the tier vocabulary for exactly this class, and it too
#       requires the marker — declaring the tier without the watch is the same defect.
#   (c) The block-wide backstop no longer fires on a BARE `claude-opus-5` SUBSTRING. It
#       now fires on MODEL-FIELD assignments (`model:`/`model_tier:`/`model_id:` = ...
#       claude-opus-5) and on blocks that FAILED TO PARSE. WHY: a plan that legitimately
#       routes to the supervised executor must be able to NAME the model in an executor,
#       owner, task, or tradeoff field ("delegate:opus5-executor (claude-opus-5, watched)")
#       without the gate reading its own documentation as a violation. Raw model FIELDS stay
#       banned — the sanctioned route is the agent's frontmatter pin, never a routing-block
#       model field — and the `opus`/`opusplan` ALIAS regexes are untouched: an alias
#       re-resolves silently, so it is never a sanctioned route at any scope.
#
# WHAT: when the agent is about to present a plan for approval (ExitPlanMode), lint the
#   plan's Delegation & Routing block and DENY the tool call when it is missing or
#   malformed, so the model must fix the plan and retry BEFORE the user ever sees it.
#   Enforces A2_ROUTING_SCHEMA.machine.md lint checks L1-L4.
#   (2026-07-27 reviewer pass, mirroring delegation-planning/kernel.py + lib/verify_models.sh:
#    L3 also catches BODY-TEXT theater — a delegate:<real-agent> track whose task/owner text
#    says the lead runs it; L4 denies opus[1m] and opusplan (not just bare opus) and tier-checks
#    model_tier; and the gate lints ALL routing fences + the markdown table, not just the first,
#    so a compliant first block cannot shadow a violating second one.)
#
# WHY A HOOK AND NOT AN INSTRUCTION: a routing mandate written into the planner prompt
#   fires only if the prompt is loaded AND the model chooses to comply. The recorded
#   defect this closes (SEED-06) is exactly that failure: six declared delegation tracks,
#   four of them actually self-run. A PreToolUse hook fires on the tool call regardless.
#
# ─── PROBE EVIDENCE (2026-07-27, Claude Code 2.1.220, measured — not assumed) ──────
#   Q: does PreToolUse actually fire for ExitPlanMode? A: YES. Captured verbatim from a
#   live interactive session (headless `-p` CANNOT be used to test this: it disables the
#   tool outright — "ExitPlanMode exists but is not enabled in this context"):
#     {"session_id":"f80d8443-...","cwd":"...","permission_mode":"plan",
#      "hook_event_name":"PreToolUse","tool_name":"ExitPlanMode",
#      "tool_input":{"plan":"# Plan: Add a \"Hello\" line to README.md\n\n## Context\n...",
#                    "planFilePath":"$HOME/.claude/plans/plan-a-tiny-change-virtual-wadler.md"},
#      "tool_use_id":"toolu_016qzsPRLivG5Qo9t3WUtJBv"}
#   So tool_input carries BOTH the full plan text AND the plan file path. Per the shipped
#   binary these two are "injected by normalizeToolInput from disk" — they are NOT model
#   arguments. CONSEQUENCE: when no plan exists on disk, tool_input is literally {} (also
#   measured). That is the documented fail-open skip below, not a lint failure.
#
# ─── SUBAGENT DETECTION (measured, same probe) ────────────────────────────────────
#   A subagent's PreToolUse payload carries TWO EXTRA top-level keys the main agent's
#   does not: agent_id (e.g. "afae817c36aa6cd6e") and agent_type (e.g. "general-purpose").
#   Main-agent payload keys: session_id transcript_path cwd prompt_id permission_mode
#   effort hook_event_name tool_name tool_input tool_use_id  (no agent_*).
#   There is NO isSidechain field in the hook payload (that lives only in the transcript),
#   so agent_id/agent_type is the ONLY in-band sidechain signal — and it is sufficient.
#
# CONTRACT (per bash-hook-contract; verified against the doc-currency-guard precedent):
#   IN : one JSON object on STDIN (NOT env vars — the old $CLAUDE_* vars are unset).
#        load-bearing: tool_name, tool_input.{plan,planFilePath}, agent_id, agent_type.
#   OUT: the ONLY model-facing channel is STDOUT, which for a tool-loop event is PARSED
#        AS JSON on exit 0 — so stdout is EITHER empty (silent pass) OR exactly one JSON
#        object carrying hookSpecificOutput.permissionDecision="deny". Any stray echo =>
#        malformed JSON => the decision is silently dropped. Debug text => stderr only.
#   EXIT: 0 ALWAYS. The BLOCK rides in the stdout JSON (permissionDecision), not the exit
#        code. exit 2 would also block, but it denies the model the structured reason it
#        needs to repair the plan and retry — and the whole point is the retry.
#        Any internal error => INDETERMINATE => FAIL-OPEN but LOG. A gate that cannot
#        reach a verdict must never wedge the user's plan on its own bug.
#   BLAST: read-only. Reads stdin plus (only as a fallback) the plan file the payload
#        names; never writes, edits, deletes, or forks a network call.
set -eo pipefail   # NOT set -u — maybe-unset vars are guarded with ${x:-}

_log() {
  local d="${CLAUDE_HOME:-$HOME/.claude}/logs"
  mkdir -p "$d" 2>/dev/null || return 0
  printf '%s plan-routing-gate: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" \
    >> "$d/plan-routing-gate.log" 2>/dev/null || true
}

# --- CRT MASTER SWITCH: on (default) | observe | off ---------------------------
#   This is an INTERVENTION hook (it can deny), so BOTH "off" and "observe" silence it:
#   "off" = fully inert; "observe" = measure UNAIDED planning behavior. Only "on" enforces.
#   (Exact snippet shared with claim-verify-guard.sh / doc-currency-guard.sh.)
_crt_mode="${CRT_MODE:-}"
if [ -z "$_crt_mode" ]; then
  _cmf="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"
  [ -r "$_cmf" ] && _crt_mode="$(tr -d '[:space:]' < "$_cmf" 2>/dev/null || true)"
fi
_crt_mode="${_crt_mode:-on}"
[ "$_crt_mode" != "on" ] && exit 0

input="$(cat)"
[ -z "${input:-}" ] && exit 0

# --- fast bail: not an ExitPlanMode payload (cheap string test, no parse) -------
case "$input" in
  *ExitPlanMode*) : ;;
  *) exit 0 ;;
esac

command -v python3 >/dev/null 2>&1 || { _log "python3 absent => fail-open"; exit 0; }

_errf="${TMPDIR:-/tmp}/prg_err.$$"
_outf="${TMPDIR:-/tmp}/prg_out.$$"

# The linter runs in python3 (the routing block needs real JSON + markdown-table
# parsing, and bash-hook-contract makes python3 a hard dep of the hooks). It prints
# the deny JSON — and ONLY the deny JSON — to stdout, or nothing at all on a pass.
#
# NOTE (bash gotcha, do NOT "simplify" this into verdict="$(python3 - ... <<'PYEOF')"):
#   a heredoc nested inside a $( ) command substitution is STILL scanned for backtick
#   balance while bash hunts for the closing paren, and the linter below contains
#   ```routing fences. Capturing that way is a hard syntax error on bash 3.2/5.x alike.
#   Redirect to a temp file and read it back — the same shape claim-verify-guard.sh uses.
set +e
python3 - "$input" <<'PYEOF' >"$_outf" 2>"$_errf"
import json, re, sys

# ---------- fail-open guards: anything unexpected => silent pass ----------------
try:
    obj = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
if not isinstance(obj, dict):
    sys.exit(0)

# Defensive: the matcher should guarantee this, but a mis-registered fragment must
# not let this gate lint (and deny) unrelated tool calls.
if obj.get("tool_name") != "ExitPlanMode":
    sys.exit(0)

# SUBAGENT / SIDECHAIN SKIP (probe-measured signal — see header). A subagent that
# somehow reaches ExitPlanMode is not the orchestrator whose routing we govern.
if obj.get("agent_id") or obj.get("agent_type"):
    sys.exit(0)

ti = obj.get("tool_input")
if not isinstance(ti, dict):
    sys.exit(0)

# ---------- get the plan text: tool_input.plan, else the plan FILE --------------
plan = ti.get("plan")
if not isinstance(plan, str) or not plan.strip():
    plan = ""
    p = ti.get("planFilePath") or ti.get("plan_file_path")
    if isinstance(p, str) and p:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                plan = fh.read()
        except Exception:
            plan = ""
# Plan text absent ENTIRELY => fail-open by contract. This is the real, measured
# no-plan-on-disk case (tool_input == {}), not a lint violation to punish.
if not plan.strip():
    sys.exit(0)

# ---------- locate the routing block (fenced JSON is canonical) -----------------
FENCE = re.compile(r"```+[ \t]*routing[ \t]*\r?\n(.*?)```", re.S | re.I)
SEP   = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


def parse_md_table(text):
    """A2 allows the equivalent as a markdown table. Find one with an `executor` column."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if "|" not in ln:
            continue
        hdr = [c.strip().lower().strip("*` ") for c in ln.strip().strip("|").split("|")]
        if "executor" not in hdr:
            continue
        if i + 1 >= len(lines) or not SEP.match(lines[i + 1]):
            continue
        rows = []
        for row in lines[i + 2:]:
            if not row.strip() or "|" not in row:
                break
            vals = [c.strip().strip("`") for c in row.strip().strip("|").split("|")]
            vals += [""] * (len(hdr) - len(vals))
            rows.append(dict(zip(hdr, vals[:len(hdr)])))
        if rows:
            return rows, "\n".join(lines[i:i + 2 + len(rows)])
    return None, ""


# ---------- L3/L4 shared machinery (ported from delegation-planning/kernel.py) --
# L3b SELF_RUN_TELLS: the recorded msg-4022 shape — a delegate:<real-agent> track whose
# OWN body text says the LEAD runs it ("main agent does this inline"). Mirrors
# kernel.SELF_RUN_TELLS + SELF_RUN_SCAN_FIELDS; scans the descriptive body, not the tag.
SELF_RUN_TELLS = (
    re.compile(r"main[\s_-]*agent\s+(?:does|do|runs?|will|executes?|handles?|writes?|authors?)", re.I),
    re.compile(r"(?:executed|run|written|authored|handled|done)\s+by\s+(?:the\s+)?main[\s_-]*agent", re.I),
    re.compile(r"\bself[\s_-]?run\b", re.I),
    re.compile(r"\bexecution\s*:\s*main[\s_-]*agent\b", re.I),
    re.compile(r"\b(?:i(?:'ll)?|lead|planner)\s+(?:will\s+)?(?:do|run|write|author|handle|execut\w*)\s+(?:this|it)\b", re.I),
)
SELF_RUN_FIELDS = ("owner", "task", "tradeoff", "brief_ref")

# L4 valid model_tier tokens: kernel TIER_TABLE keys (+ the non-delegate sentinel n/a).
# T1_supervised (2026-08-04) = the constrained supervised-executor class: the model comes from the
# project-scoped agent's frontmatter, not from a tier lookup, so the token names the SUPERVISION
# ARRANGEMENT rather than a model. It is valid ONLY on a track that also carries the marker below.
VALID_TIERS = ("T1", "T1_hardest", "T1_supervised", "T2", "T3", "T4")

# Executors that may run a barred-outside-this-shape model, and therefore require the watch.
SUPERVISED_EXECUTORS = ("opus5-executor",)


def supervision_marker(t):
    """True when a track DECLARES planner supervision. Accepts `"supervised": true` (real bool,
    or the STRING a markdown-table row necessarily produces) or a non-empty `"supervision"` value
    such as "planner-watch". Deliberately generous about spelling and strict about emptiness: the
    point is a positive, visible declaration that a planner is watching this run, and a blank or
    negated field is the absence of one."""
    v = t.get("supervised")
    if v is True:
        return True
    if isinstance(v, str) and v.strip().strip("`").lower() in ("true", "yes", "planner-watch"):
        return True
    s = t.get("supervision")
    if isinstance(s, str):
        low = s.strip().strip("`").lower()
        if low and low not in ("false", "no", "none", "n/a", "-"):
            return True
    return False


def norm_name(s):
    """Profile-name normalization for the self-match: case/space/underscore-insensitive
    (kernel _norm_name). delegate:Main_Agent and delegate:"the main agent" both fold in."""
    return re.sub(r"[\s_]+", "-", str(s or "").strip().lower())


def norm_text(s):
    """Collapse whitespace for tell-matching (kernel _norm); None -> ''."""
    return re.sub(r"\s+", " ", str(s or "")).strip()


def banned_model(value):
    """Mirror lib/verify_models.sh classify() DENY branch -> reason str, or None if OK.
    DENY: any id containing 'claude-opus-5' (substring — catches [1m]/vendor-qualified);
    the bare alias 'opus' alone or context-suffixed ('opus[1m]') via a non-[a-z0-9-]
    boundary (fail-closed on unknown opus-N variants); and 'opusplan' likewise. NOT
    denied: claude-opus-4-8 (allowed T1). Applied ONLY to model-type fields — never to
    prose — so a task that merely NAMES the ban is not itself flagged."""
    low = str(value or "").strip().strip("`").lower()
    if not low:
        return None
    if "claude-opus-5" in low:
        return ("claude-opus-5 is BANNED as a raw model FIELD value, any tier, any call. Its one "
                "legal shape is executor delegate:opus5-executor + a supervision marker, with the "
                "model coming from that project-scoped agent's own frontmatter")
    if re.match(r"^opus([^a-z0-9-].*)?$", low):
        return ("the bare alias `opus` resolves to Opus 5 on Claude Code >=2.1.219 and is "
                "BANNED. Name a tier (T1|T1_hardest|T2|T3|T4) or an allowed model id")
    if re.match(r"^opusplan([^a-z0-9-].*)?$", low):
        return ("the alias `opusplan` plans on the latest Opus (Opus 5 on Claude Code "
                ">=2.1.219) and is BANNED — name a tier or an allowed model id")
    return None


# ---------- collect EVERY routing surface (findall + the table), then L1 --------
fails = []
all_tracks = []          # tracks accumulated across every routing surface
block_texts = []         # each surface's raw text, for the block-wide L4 backstop
unparsed_texts = []      # surfaces NO per-track scan ever saw (bad JSON / no tracks array)
forms = []               # human labels of the forms found
found_surface = False    # a routing surface exists (>=1 fence, or a table)

# ALL fenced ```routing blocks — findall, NOT first-match: a compliant first block must
# not shadow a violating second one (the exact gap this closes).
for _i, _body in enumerate(FENCE.findall(plan)):
    found_surface = True
    block_texts.append(_body)
    forms.append("fenced ```routing JSON block")
    try:
        got = json.loads(_body)
    except Exception as exc:
        fails.append("L1 block-present: ```routing block #%d IS present but does not parse "
                     "as JSON (%s). A malformed block must not pass as 'no block'."
                     % (_i + 1, exc))
        unparsed_texts.append(_body)
        continue
    if isinstance(got, dict):
        bt = got.get("tracks")
    elif isinstance(got, list):
        bt = got
    else:
        bt = None
    if not isinstance(bt, list):
        fails.append("L1 block-present: ```routing block #%d parsed but carries no `tracks` "
                     "array (expected {\"tracks\":[ ... ]})." % (_i + 1))
        unparsed_texts.append(_body)
        continue
    all_tracks.extend(bt)

# The markdown-table equivalent is ALSO linted (not only as a fallback when no fence).
rows, raw = parse_md_table(plan)
if rows:
    found_surface = True
    forms.append("Delegation & Routing markdown table")
    block_texts.append(raw)
    all_tracks.extend(rows)

block_text = "\n".join(block_texts)
form = "; ".join([f for j, f in enumerate(forms) if f not in forms[:j]]) if forms else None

if not found_surface:
    fails.append(
        "L1 block-present: this plan carries NO Delegation & Routing block. Every plan "
        "must emit either a fenced ```routing JSON block ({\"tracks\":[...]}) or the "
        "equivalent markdown table with an `executor` column.")
elif len(all_tracks) == 0 and not fails:
    fails.append("L1 block-present: the routing block declares ZERO tracks. An empty "
                 "tracks array is a visible failure, not a pass.")

# ---------- L2 / L3 / L4 over the declared tracks -------------------------------
EXEC_OK = re.compile(r"^(MAIN-AGENT|CODE:.+|delegate:.+)$", re.I)
# Self-aliases, compared AFTER norm_name (so main_agent / "main agent" fold to main-agent).
# Mirrors kernel.SELF_TOKENS {main-agent, mainagent, main, self, myself, me, lead,
# lead-agent, the-main-agent} PLUS the CC-hook extras kept from the prior set
# (orchestrator, main-claude). `planner` is deliberately NOT a self-name: it is a real
# roster profile a non-planner may legitimately route to. delegate:planner is self ONLY
# under the planner persona, which a PreToolUse hook cannot observe — so, like the kernel,
# this gate treats planner as a valid non-self target rather than false-block it.
SELF_NAMES = {"main-agent", "mainagent", "main", "self", "myself", "me",
              "lead", "lead-agent", "the-main-agent", "orchestrator", "main-claude"}

for i, t in enumerate(all_tracks):
    if not isinstance(t, dict):
        fails.append("L2 fields: track #%d is not an object." % (i + 1))
        continue
    tid = str(t.get("id") or t.get("track") or t.get("task") or ("#%d" % (i + 1)))[:60]

    ex = t.get("executor")
    if not isinstance(ex, str) or not ex.strip():
        fails.append("L2 fields: track %s names NO `executor`. Required, one of "
                     "MAIN-AGENT | CODE:<cmd> | delegate:<NAME>." % tid)
        continue
    ex = ex.strip().strip("`").strip()
    if not EXEC_OK.match(ex):
        fails.append("L2 fields: track %s has executor %r, which is not one of "
                     "MAIN-AGENT | CODE:<cmd> | delegate:<NAME>." % (tid, ex))
        continue

    if ex.lower().startswith("delegate:"):
        name = norm_name(ex.split(":", 1)[1].strip().strip("`<>[]\"'"))
        if not name or name in SELF_NAMES:
            fails.append(
                "L3 anti-theater: track %s declares executor %r. A `delegate:` executor "
                "must name a REAL, NON-SELF agent — declaring delegation and then running "
                "it yourself is the exact defect this gate exists to catch. Either name "
                "the actual specialist agent, or be honest and use MAIN-AGENT."
                % (tid, ex))
        else:
            # L3b body-theater: a real, non-self delegate whose OWN body says the LEAD
            # runs it (the msg-4022 shape). Scan the descriptive fields, never the tag.
            for fld in SELF_RUN_FIELDS:
                txt = norm_text(t.get(fld))
                if txt and any(rx.search(txt) for rx in SELF_RUN_TELLS):
                    fails.append(
                        "L3 anti-theater: track %s declares executor %r but its `%s` says "
                        "the LEAD runs it (%r) — declared delegation, self-run. Name the "
                        "real specialist that does the work, or be honest and use MAIN-AGENT."
                        % (tid, ex, fld, txt[:120]))
                    break
            # L4 supervision: a supervised-executor track must DECLARE the watch it depends on.
            if name in SUPERVISED_EXECUTORS and not supervision_marker(t):
                fails.append(
                    "L4 supervision: track %s routes to the supervised executor %r but declares "
                    "no supervision marker. That executor runs a model whose only sanctioned "
                    "shape is a tightly-scoped child under a Planner's ACTIVE watch, so the "
                    "watch has to be on the record: add \"supervised\": true (or "
                    "\"supervision\": \"planner-watch\") to this track, or route the work to an "
                    "unsupervised agent." % (tid, ex))

    # L4, per-track: a banned model id / alias in a model or tier field (verify_models.sh
    # classify() semantics), AND model_tier must be a known tier token when present.
    for k in ("model", "model_tier", "tier", "model_id"):
        v = t.get(k)
        if not isinstance(v, str):
            continue
        why = banned_model(v)
        if why:
            fails.append("L4 tier-ban: track %s sets %s=%r — %s." % (tid, k, v.strip(), why))
    mt = t.get("model_tier")
    if isinstance(mt, str) and mt.strip():
        mtv = mt.strip().strip("`")
        if banned_model(mtv) is None and mtv.lower() != "n/a" and mtv not in VALID_TIERS:
            fails.append("L4 tier-ban: track %s sets model_tier=%r — not a known tier. Use one "
                         "of T1|T1_hardest|T1_supervised|T2|T3|T4 (or 'n/a' when nothing is "
                         "delegated)." % (tid, mtv))
        elif mtv == "T1_supervised" and not supervision_marker(t):
            fails.append("L4 supervision: track %s sets model_tier=T1_supervised but declares "
                         "no supervision marker. That tier NAMES the supervision arrangement, "
                         "so claiming it without the watch is the defect it exists to prevent: "
                         "add \"supervised\": true (or \"supervision\": \"planner-watch\")."
                         % tid)

# L4, block-wide backstop — REWORKED 2026-08-04 (O-series). Two surfaces, deliberately
# NARROWER than the old bare-substring scan, which could not tell a raw model assignment
# from a plan legitimately naming the model of the supervised executor it routes to:
#   (1) UNPARSEABLE surfaces — a block no per-track scan ever saw. There, and only there,
#       a bare substring is still the right instrument: nothing else can read it.
#   (2) MODEL-FIELD assignments anywhere in the raw text — `model:`/`model_tier:`/
#       `model_id:` set to claude-opus-5. A raw model field is never the sanctioned route:
#       supervised use goes through the project-scoped agent's own frontmatter pin, named
#       in the track as executor + the supervision marker.
# Everything else — an executor name, an owner, a task or tradeoff sentence that mentions
# the model — is now free to say so. The `opus`/`opusplan` ALIAS regex is unchanged: it was
# already model-field-anchored, and no alias is sanctioned at any scope.
_l4ban = [f for f in fails if f.startswith("L4 tier-ban")]
_unparsed_low = "\n".join(unparsed_texts).lower()
if "claude-opus-5" in _unparsed_low and not _l4ban:
    fails.append("L4 tier-ban: a routing block that does NOT parse names claude-opus-5. An "
                 "unreadable block cannot be checked track-by-track, so its contents are "
                 "read literally: fix the block's JSON, and route supervised opus-5 work "
                 "through executor delegate:opus5-executor with a supervision marker rather "
                 "than a raw model id.")
    _l4ban = [f for f in fails if f.startswith("L4 tier-ban")]
if re.search(r"\bmodel(?:_tier|_id)?\b\s*[:=]\s*[\"'`]?[^\"'`,}\n]*claude-opus-5",
             block_text, re.I) and not _l4ban:
    fails.append("L4 tier-ban: the routing block sets a model/tier FIELD to claude-opus-5. "
                 "A raw model field is never the sanctioned route — supervised use is "
                 "declared as executor delegate:opus5-executor plus \"supervised\": true, "
                 "and the model itself comes from that project-scoped agent's frontmatter.")
if re.search(r"\bmodel(?:_tier|_id)?\b\s*[:=]\s*[\"'`]?(?:opus(?:plan)?)(?![a-z0-9-])",
             block_text, re.I) and not any("alias" in f for f in fails):
    fails.append("L4 tier-ban: the routing block sets a model/tier to the bare alias "
                 "`opus`/`opusplan`, which resolves to Opus 5 on Claude Code >=2.1.219 "
                 "and is BANNED — at every scope, supervised or not, because an alias "
                 "re-resolves silently.")

# ---------- verdict -------------------------------------------------------------
n = len(all_tracks)
if not fails:
    sys.exit(0)                      # PASS: stdout stays EMPTY

# MARKER FORM: A2 assigns the double-square-bracketed plan_lint marker to the CS carrier
# (the plan_lint kernel) and assigns "deny-with-reason" to this CC hook, so the CC marker
# is deliberately NOT wikilink-shaped: lib/scrub_verify.sh treats a letter-initial double
# square bracket as a dangling Obsidian wikilink, and its MARKER_SAFE whitelist does not
# cover plan_lint. Kept greppable ("plan_lint") for auditors without tripping that
# fail-closed scrub gate. To adopt the CS-parity bracketed form, whoever owns
# lib/scrub_verify.sh must first add plan_lint to MARKER_SAFE.
marker = "plan_lint tracks=%d verdict=FAIL(%d)" % (n, len(fails))
reason = ["BLOCKED by plan-routing-gate %s" % marker, ""]
if form:
    reason.append("Found: %s." % form)
reason.append("This plan does not satisfy A2_ROUTING_SCHEMA lint checks L1-L4:")
reason += ["  - %s" % f for f in fails]
reason += [
    "",
    "Fix the routing block in the plan, then call ExitPlanMode again. Required per-track "
    "shape (fenced ```routing block, the canonical form):",
    '  {"tracks":[{"id":"t1","task":"...","archetype":"...","owner":"...",',
    '              "executor":"MAIN-AGENT | CODE:<cmd> | delegate:<real-agent-name>",',
    '              "topology":"single-thread","model_tier":"T2","effort":"high",',
    '              "detached":false,"brief_ref":"...","record_access":"self-service",',
    '              "recon_done":"...","reserved_for_user":false}]}',
    "A supervised opus-5 track adds the watch to that shape and names NO model field:",
    '  {"id":"t2","task":"...","executor":"delegate:opus5-executor","supervised":true,',
    '   "model_tier":"T1_supervised","effort":"high", ...}',
    "Do not delete the block or rename the fence to dodge this check.",
]
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "\n".join(reason)}}))
sys.exit(0)
PYEOF
rc=$?
set -e

verdict="$(cat "$_outf" 2>/dev/null || true)"
err="$(cat "$_errf" 2>/dev/null || true)"
rm -f "$_errf" "$_outf" 2>/dev/null || true

if [ "$rc" -ne 0 ]; then
  # INDETERMINATE (the linter itself crashed) => fail-open BUT log it. A silent
  # fail-open is the bug: you cannot tell a clean pass from a broken gate.
  _log "INDETERMINATE rc=$rc => fail-open: $(printf '%s' "$err" | head -1)"
  exit 0
fi

if [ -n "${verdict:-}" ]; then
  # Emit the deny decision. Guard the shape: a partial/garbled payload on stdout would
  # be parsed as malformed JSON and silently dropped, turning a BLOCK into a phantom pass.
  case "$verdict" in
    \{*\}) printf '%s\n' "$verdict"
           _log "DENY: $(printf '%s' "$verdict" | head -c 200)" ;;
    *)     _log "INDETERMINATE: linter stdout was not a JSON object => fail-open" ;;
  esac
fi
exit 0
