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
# Project-specialty bundle routing (PASS 3). The project manifest + the fillable routes MASTER both ship
# under payload-project/; the master is authoritative (CRT_ROUTES_MASTER overrides its path, for testing).
DEFAULT_PROJECT_MANIFEST = os.path.join(
    os.path.dirname(HERE), "payload-project", "project_manifest.tsv"
)
DEFAULT_ROUTES_MASTER = os.environ.get("CRT_ROUTES_MASTER") or os.path.join(
    os.path.dirname(HERE), "payload-project", "project_routes.tsv"
)


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


# ── Phase B3: project-specialty bundle routes (PASS 3) ───────────────────────
# The picker composes `--apply-project-routes` and may APPEND a route row to the routes MASTER (the file
# install reads). Appending a route is user-config editing (the ONE write the picker makes) — it is NOT
# payload copy/coupling/discipline logic, which stays in the engine. Menus -> stderr; input -> stdin; EOF = skip.
def load_bundles(project_manifest):
    """Parse project_manifest.tsv -> ordered [{name, members:[...], dest_hint, note}]. Skips `#` + the
    header (col1=='name'); bundle = col 6 (index 5). [] if the file is absent/has no bundles."""
    bundles, order = {}, []
    try:
        with open(project_manifest, encoding="utf-8") as fh:
            for raw in fh:
                if raw.lstrip().startswith("#"):
                    continue
                parts = raw.rstrip("\n").split("\t")
                if len(parts) < 6:
                    continue
                name, dest_hint, note, bundle = parts[0], parts[3], parts[4], parts[5]
                if name == "name" or not bundle.strip():
                    continue
                b = bundle.strip()
                if b not in bundles:
                    bundles[b] = {"name": b, "members": [], "dest_hint": dest_hint.strip(), "note": note.strip()}
                    order.append(b)
                bundles[b]["members"].append(name.strip())
    except OSError:
        return []
    return [bundles[b] for b in order]


def load_routes(routes_file):
    """Return active (bundle, dest) rows from the live routes file (skip `#` + blank); [] if absent."""
    rows = []
    try:
        with open(routes_file, encoding="utf-8") as fh:
            for raw in fh:
                if raw.lstrip().startswith("#") or not raw.strip():
                    continue
                parts = raw.rstrip("\n").split("\t")
                if len(parts) >= 2 and parts[0].strip():
                    rows.append((parts[0].strip(), parts[1].strip()))
    except OSError:
        pass
    return rows


def append_route(routes_file, bundle, dest):
    """Append one `bundle<TAB>dest` row to the routes MASTER (the file install reads). In real use the
    master already exists in the repo; if it is somehow absent (e.g. a temp path under test), write a
    minimal documented header first. Stores the dest verbatim (a leading `~` is expanded later, at apply)."""
    d = os.path.dirname(os.path.abspath(routes_file))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(routes_file):
        with open(routes_file, "w", encoding="utf-8") as o:
            o.write("# project_routes.tsv — the fillable MASTER: bundle<TAB>dest routes (edit in the repo).\n")
    with open(routes_file, "a", encoding="utf-8") as o:
        o.write("%s\t%s\n" % (bundle, dest))


def bundles_pass(project_manifest, routes_file):
    """PASS 3 — offer to apply/add project-specialty bundle routes (routes_file = the MASTER install reads).
    Returns ['--apply-project-routes'] (chose apply, or added >=1 route) or None (skip). No bundles known
    => None WITHOUT prompting."""
    bundles = load_bundles(project_manifest)
    if not bundles:
        return None  # nothing to offer -> do not prompt / consume input
    err("\n########## PASS 3 of 3 — PROJECT-SPECIALTY BUNDLES ##########")
    err("Route project-specialty bundles to a project's OWN .claude/ (never into ~/.claude).")
    err("Available bundles (from project_manifest.tsv):")
    for i, b in enumerate(bundles, 1):
        err(f"  {i}) {b['name']}  — members: {', '.join(b['members'])}")
        if b["dest_hint"]:
            err(f"       dest hint: {b['dest_hint']}")
        if b["note"]:
            err(f"       note: {b['note'][:100]}")
    rows = load_routes(routes_file)
    err(f"Current routes (from {routes_file}):")
    if rows:
        for rb, rd in rows:
            err(f"  - {rb} -> {rd}")
    else:
        err("  (none yet)")
    has_rows = len(rows) > 0
    err("Options:  a) apply all routes%s   b) add a route   c) skip%s"
        % ("  [default]" if has_rows else "", "  [default]" if not has_rows else ""))
    choice = ask_default("Choice [a/b/c]> ", "c").strip().lower()  # EOF -> 'c' (skip cleanly)
    if choice == "":                                               # bare Enter -> the shown default
        choice = "a" if has_rows else "c"
    if choice in ("a", "apply"):
        return ["--apply-project-routes"]
    if choice in ("b", "add"):
        pick = ask_default(f"  Pick a bundle by number [1-{len(bundles)}] (blank to cancel)> ", "").strip()
        if not pick.isdigit() or not (1 <= int(pick) <= len(bundles)):
            err("  (no valid bundle chosen — skipping route add.)")
            return None
        b = bundles[int(pick) - 1]
        err(f"  adding routes for '{b['name']}'. Enter dest project root(s); blank/done to finish.")
        added = 0
        while True:
            dest = ask_default("  Destination project root> ", "").strip()
            if dest == "" or dest.lower() == "done":
                break
            append_route(routes_file, b["name"], dest)
            err(f"  + route: {b['name']} -> {dest}")
            added += 1
        return ["--apply-project-routes"] if added > 0 else None
    err("  (skipped project bundles.)")
    return None


# ── Phase B: the two-pass driver ─────────────────────────────────────────────
def run(menu, project_manifest, routes_file):
    invocations = []  # list of argv-token lists; one install.sh call each

    # PASS 1 — global set
    err("\n########## PASS 1 of 3 — GLOBAL install (~/.claude) ##########")
    g_names, g_all, g_deferred = select_pass(menu, "GLOBAL components")
    g_args = compose_global(g_names, g_all, g_deferred)
    if g_args is not None:
        invocations.append(g_args)
    else:
        err("(no global components chosen — you must add at least one project root.)")

    # PASS 2 — optional per-root specialist sets
    err("\n########## PASS 2 of 3 — optional PROJECT ROOTS ##########")
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

    # PASS 3 — optional project-specialty bundle routes (composes --apply-project-routes)
    b_args = bundles_pass(project_manifest, routes_file)
    if b_args is not None:
        invocations.append(b_args)

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
    ap.add_argument("--project-manifest", default=DEFAULT_PROJECT_MANIFEST,
                    help="path to payload-project/project_manifest.tsv (PASS 3 bundles; default: ../payload-project/)")
    ap.add_argument("--routes-file", default=DEFAULT_ROUTES_MASTER,
                    help="path to the project-routes MASTER install reads/appends (default: payload-project/project_routes.tsv; CRT_ROUTES_MASTER overrides)")
    a = ap.parse_args(argv)
    menu = load_menu(a.resolver, a.manifest)
    return run(menu, a.project_manifest, a.routes_file)


if __name__ == "__main__":
    sys.exit(main())
