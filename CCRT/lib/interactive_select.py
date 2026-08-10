#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""interactive_select.py — the CCRT interactive installer FRONT-END (numbered-menu picker).

WHAT IT IS (and is NOT):
  A thin FLAG COMPOSER. It presents the selectable agents/skills as a numbered menu, runs a
  two-pass scope flow (global set, then optional per-root specialist sets), and emits — one per
  line on STDOUT — the exact `install.sh` argument-lines a driver should run. It adds ZERO copy
  logic, resolves NO coupling, and computes NO discipline decision: every one of those stays in
  the already-built engine (install.sh + lib/select_resolve.py). See HANDOFF §4 invariants.

CONTRACT (so it is deterministic + testable):
  - ALL menus/prompts/previews are written to STDERR.
  - ONLY the confirmed install.sh arg-lines are written to STDOUT, one invocation per line,
    WITHOUT the leading `install.sh` (the driver prepends the script path). So:
        STDOUT line:  --core --select planner,solo
        driver runs:  install.sh --core --select planner,solo
  - Input is read with readline(): at EOF (piped/CI stdin exhausted, or no tty) it never hangs —
    it returns "" and the loop treats that as the terminating/abort answer. The tty and non-tty
    paths consume identical bytes and therefore emit identical arg-lines (HANDOFF invariant 8).
  - Exit 0 = arg-lines emitted (user confirmed). Exit 1 = aborted / nothing to install.
    Exit 2 = internal/data error (e.g. the resolver --list feed could not be read).

UI action -> engine flag (the WHOLE mapping; HANDOFF §3.2):
  global, chosen picks     -> --core --select <names>
  global, "all"            -> --core                       (no --select = full trees)
  per root DIR, picks      -> --core --root <DIR> --select <names> --discipline-trees auto
  a DEFERRED skill picked  -> add --allow-deferred (to THAT invocation only)
  root wants portability   -> --discipline-trees copy  (explicit opt-in; else auto)

The front-end passes selection NAMES straight through to --select and lets the ENGINE resolve the
coupling closure + gate + discipline decision. The skill-count shown for an agent is DISPLAY ONLY.
"""
import argparse
import os
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESOLVER = os.path.join(HERE, "select_resolve.py")
DEFAULT_MANIFEST = os.path.join(
    os.path.dirname(HERE), "payload", "coupling_manifest_v1.tsv"
)
# [RETIRED 2026-08-09, PC3] PASS 3 (project-specialty bundle routing) lived here: DEFAULT_PROJECT_MANIFEST
# and DEFAULT_ROUTES_MASTER pointed at ../payload-project/{project_manifest,project_routes}.tsv — a
# directory that has been DELETED, so both reads dangled. The flags they composed (--apply-project-routes)
# are retired from install.sh too. REPLACEMENT: specialists install MANUALLY from CCRT_specialists/ into a
# project's own .claude/, so there is nothing for a picker to compose and the flow is two passes, not three.


# ── stderr I/O helpers (menus/prompts NEVER touch stdout) ────────────────────
def err(*a):
    sys.stderr.write(" ".join(str(x) for x in a) + "\n")
    sys.stderr.flush()


def ask(prompt):
    """Write a prompt to stderr, read one line from stdin. EOF -> EOFError (never hangs)."""
    sys.stderr.write(prompt)
    sys.stderr.flush()
    line = sys.stdin.readline()
    if line == "":  # EOF: piped stdin exhausted / no tty -> deterministic terminate
        raise EOFError
    return line.rstrip("\n").strip()


def ask_default(prompt, default=""):
    """ask() but an EOF returns `default` instead of raising (for terminal prompts)."""
    try:
        return ask(prompt)
    except EOFError:
        return default


# ── Phase A1: parse the `select_resolve.py --list` data feed ─────────────────
def load_menu(resolver, manifest):
    """Run the resolver's --list and parse it into an ordered menu.

    Returns a list of dicts (1-based menu order = list order): AGENTS first, then SKILLS.
      {"kind": "agent", "name": str, "nskills": int}
      {"kind": "skill", "name": str, "tier": str, "deferred": bool}
    """
    try:
        out = subprocess.run(
            [sys.executable, resolver, "--manifest", manifest, "--list"],
            check=True, capture_output=True, text=True,
        ).stdout
    except FileNotFoundError as e:
        err(f"FATAL: cannot run resolver '{resolver}': {e}")
        sys.exit(2)
    except subprocess.CalledProcessError as e:
        err(f"FATAL: resolver --list failed (exit {e.returncode}):")
        err(e.stderr.rstrip())
        sys.exit(2)

    agents, skills, section = [], [], None
    for raw in out.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == "== AGENTS ==":
            section = "agents"; continue
        if line == "== SKILLS ==":
            section = "skills"; continue
        if section == "agents":
            # "<name>  (<n> skills)"
            name = line.split("(")[0].strip()
            nskills = 0
            if "(" in line:
                num = line.split("(")[1].split()[0]
                nskills = int(num) if num.isdigit() else 0
            agents.append({"kind": "agent", "name": name, "nskills": nskills})
        elif section == "skills":
            # "<name>  [<TIER>]"
            name = line.split("[")[0].strip()
            tier = line.split("[")[1].rstrip("]").strip() if "[" in line else ""
            skills.append({"kind": "skill", "name": name, "tier": tier,
                           "deferred": tier == "DEFERRED"})
    menu = agents + skills
    if not menu:
        err("FATAL: resolver --list returned no selectable names.")
        sys.exit(2)
    return menu


# ── Phase A2: render the numbered menu (to stderr) ───────────────────────────
def render_menu(menu, selected, title):
    err("")
    err(f"=== {title} ===")
    err("  (# = agents and skills; type numbers/ranges to toggle, e.g. 1,4,7-9)")
    last_kind = None
    for i, e in enumerate(menu, 1):
        if e["kind"] != last_kind:
            err(f"  -- {'AGENTS' if e['kind'] == 'agent' else 'SKILLS'} --")
            last_kind = e["kind"]
        mark = "x" if i in selected else " "
        if e["kind"] == "agent":
            meta = f"({e['nskills']} skills)"
        else:
            meta = f"[{e['tier']}]" + ("  (DEFERRED — needs confirm)" if e["deferred"] else "")
        err(f"  [{mark}] {i:>3}  {e['name']:<34} {meta}")
    err("  commands: <numbers> toggle · all · none · done · help")


# ── Phase A3: parse a comma-list / range toggle expression ───────────────────
def parse_toggle(expr, maxidx):
    """'1,4,7-9' -> [1,4,7,8,9]. Raises ValueError on any bad/out-of-range token (fail-closed:
    the WHOLE expression is rejected so a typo never silently toggles a partial set)."""
    idxs = []
    for tok in expr.replace(" ", "").split(","):
        if not tok:
            continue
        if "-" in tok:
            lo, hi = tok.split("-", 1)
            if not (lo.isdigit() and hi.isdigit()):
                raise ValueError(f"bad range: '{tok}'")
            lo, hi = int(lo), int(hi)
            if lo > hi:
                raise ValueError(f"reversed range: '{tok}'")
            rng = range(lo, hi + 1)
        else:
            if not tok.isdigit():
                raise ValueError(f"not a number: '{tok}'")
            rng = [int(tok)]
        for n in rng:
            if not (1 <= n <= maxidx):
                raise ValueError(f"out of range (1-{maxidx}): {n}")
            idxs.append(n)
    # dedupe within a single expression so '1,1' toggles ONCE (net ON) rather than self-cancelling
    return sorted(set(idxs))


# ── Phase A: one selection pass (menu -> confirmed set of names) ─────────────
def select_pass(menu, title):
    """Run the toggle/confirm loop for one scope pass.

    Returns (names, is_all, allow_deferred):
      names          ordered list of selected menu names ([] if none / aborted-empty)
      is_all         True if the user chose "all" (=> --core with no --select)
      allow_deferred True if any selected entry is a DEFERRED skill
    Never hangs: an EOF at the toggle prompt ends the loop with the current selection.
    """
    selected = set()  # 1-based indices
    maxidx = len(menu)
    render_menu(menu, selected, title)
    while True:
        try:
            expr = ask("\nToggle/command> ")
        except EOFError:
            break  # non-tty / stdin exhausted: finalize with current selection
        low = expr.lower()
        if low == "":
            continue  # bare Enter: no-op, re-prompt
        if low == "help":
            err("  Type numbers or ranges to toggle selection, e.g.  1,4,7-9")
            err("  all  = install everything (full trees)   none = clear selection")
            err("  done = finish this pass                   help = this text")
            continue
        if low == "all":
            # Transparency only (NOT set-computation — the install still goes through bare --core,
            # whose full-tree copy is the engine's own decision): note that 'all' pulls DEFERRED skills.
            _def = [e["name"] for e in menu if e.get("deferred")]
            if _def:
                err(f"  note: 'all' installs everything, INCLUDING DEFERRED-tier: {', '.join(_def)}")
            return ([], True, False)
        if low == "none":
            selected.clear()
            render_menu(menu, selected, title)
            continue
        if low == "done":
            break
        try:
            idxs = parse_toggle(expr, maxidx)
        except ValueError as ve:
            err(f"  ! {ve} — nothing changed; try again (or 'help').")
            continue
        for n in idxs:
            if n in selected:
                selected.discard(n)  # toggle OFF: no confirm
            else:
                e = menu[n - 1]
                if e.get("deferred"):
                    ans = ask_default(
                        f"  {n}) '{e['name']}' is DEFERRED-tier — include it? [y/N] ", "n"
                    ).lower()
                    if ans not in ("y", "yes"):
                        err(f"  (skipped DEFERRED '{e['name']}')")
                        continue
                selected.add(n)
        render_menu(menu, selected, title)

    names = [menu[i - 1]["name"] for i in sorted(selected)]
    allow_deferred = any(menu[i - 1].get("deferred") for i in selected)
    return (names, False, allow_deferred)


# ── Phase B: compose the install.sh arg TOKENS for one scope ─────────────────
# Each composer returns a LIST of argv tokens (not a joined string) so a root DIR containing
# spaces survives round-trip: run() shlex.quote()s each token at emit, and the bash driver
# re-splits with `eval set --`, reconstructing the exact argv (invariant 10, dry-run parity).
def compose_global(names, is_all, allow_deferred):
    """Pass 1 (global ~/.claude). Omit --discipline-trees (baseline always copies)."""
    if is_all:
        return ["--core"]
    if not names:
        return None  # nothing chosen globally -> no global invocation
    args = ["--core", "--select", ",".join(names)]
    if allow_deferred:
        args.append("--allow-deferred")
    return args


def compose_root(root, names, is_all, allow_deferred, discipline):
    """Pass 2 (per project root). discipline is 'auto' (default) or 'copy' (portable opt-in).
    One install.sh call per root (invariant 7)."""
    args = ["--core", "--root", root]
    if not is_all:
        if not names:
            return None  # no specialists chosen for this root -> skip it
        args += ["--select", ",".join(names)]
        if allow_deferred:
            args.append("--allow-deferred")
    args += ["--discipline-trees", discipline]
    return args


# ── Phase B: the two-pass driver ─────────────────────────────────────────────
def run(menu):
    invocations = []  # list of argv-token lists; one install.sh call each

    # PASS 1 — global set
    err("\n########## PASS 1 of 2 — GLOBAL install (~/.claude) ##########")
    g_names, g_all, g_deferred = select_pass(menu, "GLOBAL components")
    g_args = compose_global(g_names, g_all, g_deferred)
    if g_args is not None:
        invocations.append(g_args)
    else:
        err("(no global components chosen — you must add at least one project root.)")

    # PASS 2 — optional per-root specialist sets
    err("\n########## PASS 2 of 2 — optional PROJECT ROOTS ##########")
    err("Add project-local (--root DIR) installs that STACK on the global set. Blank/done = skip.")
    while True:
        try:
            root = ask("\nProject root DIR (blank or 'done' to finish roots)> ")
        except EOFError:
            break
        if root == "" or root.lower() == "done":
            break
        root = os.path.expanduser(root)
        r_names, r_all, r_deferred = select_pass(menu, f"specialists for root: {root}")
        if not r_all and not r_names:
            err(f"  (no specialists chosen for {root} — root skipped.)")
            continue
        port = ask_default(
            f"  Make '{root}' self-contained/portable (copy discipline trees)? [y/N] ", "n"
        ).lower()
        discipline = "copy" if port in ("y", "yes") else "auto"
        r_args = compose_root(root, r_names, r_all, r_deferred, discipline)
        if r_args is not None:
            invocations.append(r_args)

    # nothing at all selected -> abort (never emit an empty plan)
    if not invocations:
        err("\nNothing selected to install. Aborting (no install.sh call composed).")
        return 1

    # shlex.quote each token so the emitted line round-trips through the bash driver's
    # `eval set --` exactly (a --root DIR with spaces stays one argv token).
    emit_lines = [" ".join(shlex.quote(t) for t in argv) for argv in invocations]

    # PASS review — always preview before executing (invariant 10; §6 T dry-run parity)
    err("\n========== REVIEW — install.sh invocations to run ==========")
    for n, line in enumerate(emit_lines, 1):
        err(f"  {n})  install.sh {line}")
    err("Each line is ONE install.sh call. Add --dry-run yourself, or the driver runs them in order.")
    proceed = ask_default("\nProceed and emit these invocations? [y/N] ", "n").lower()
    err("")  # close the prompt line so captured/piped output separates cleanly from any driver logs
    if proceed not in ("y", "yes"):
        err("Aborted by user — nothing emitted.")
        return 1

    # emit the confirmed arg-lines on STDOUT (the driver's input); nothing else goes to stdout
    for line in emit_lines:
        sys.stdout.write(line + "\n")
    sys.stdout.flush()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="CCRT interactive installer front-end (numbered-menu flag composer)."
    )
    ap.add_argument("--resolver", default=DEFAULT_RESOLVER,
                    help="path to select_resolve.py (default: alongside this script)")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST,
                    help="path to coupling_manifest_v1.tsv (default: ../payload/)")
    a = ap.parse_args(argv)
    menu = load_menu(a.resolver, a.manifest)
    return run(menu)


if __name__ == "__main__":
    sys.exit(main())
