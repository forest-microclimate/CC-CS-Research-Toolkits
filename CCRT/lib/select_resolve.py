#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""select_resolve.py — resolve an install-time selection against the FROZEN coupling manifest.

install.sh calls this to turn `--select <names>` or `--manifest-subset <file>` into the exact set of
skills + agents to copy. It reads ONE source (coupling_manifest_v1.tsv) so the selection can never
disagree with the coupling gate. Output is two newline-lists on stdout, section-delimited:

  ==AGENTS==
  <agent>...
  ==SKILLS==
  <skill>...

RESOLUTION RULES (grounded in the manifest tiers):
  - Selecting an AGENT pulls the agent + its required-skill closure (DEDICATED + SHARED deps).
  - Selecting a SKILL pulls that skill; if it is DEDICATED/SHARED, it does NOT drag its agent in
    (a skill is usable without its agent), but a shared skill's OTHER agents are NOT pulled either.
  - A DEFERRED-tier skill is refused unless explicitly named AND --allow-deferred is passed.
  - Unknown names are a hard error (fail-closed: never silently install nothing).

USAGE:
  python3 select_resolve.py --manifest M --select a,b,c [--allow-deferred]
  python3 select_resolve.py --manifest M --manifest-subset FILE   # FILE lists one name per line
  python3 select_resolve.py --manifest M --list                   # print selectable names + tiers
  python3 select_resolve.py --self-test
"""
import argparse, sys


def parse_manifest(path):
    skills, agents_closure, all_agents = {}, {}, set()
    section = 1
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            c = line.rstrip("\n").split("\t")
            if c[0] == "name" and c[1] == "kind":
                section = 1; continue
            if c[0] == "agent" and c[1] == "n_skills":
                section = 2; continue
            if section == 1 and len(c) >= 4 and c[1] == "skill":
                deps = [] if c[3] in ("-", "") else c[3].split(";")
                skills[c[0]] = {"tier": c[2], "deps": deps}
                all_agents.update(deps)
            elif section == 2 and len(c) >= 5:
                closure = [] if c[4] in ("-", "") else c[4].split(";")
                agents_closure[c[0]] = closure
                all_agents.add(c[0])
    return skills, agents_closure, all_agents


def resolve(names, skills, agents_closure, all_agents, allow_deferred=False):
    sel_agents, sel_skills, errors = set(), set(), []
    for n in names:
        n = n.strip()
        if not n:
            continue
        if n in agents_closure or n in all_agents:      # it's an agent
            sel_agents.add(n)
            for s in agents_closure.get(n, []):
                sel_skills.add(s)
        elif n in skills:                                # it's a skill
            if skills[n]["tier"] == "DEFERRED" and not allow_deferred:
                errors.append(f"'{n}' is DEFERRED-tier; pass --allow-deferred to force it")
            else:
                sel_skills.add(n)
        else:
            errors.append(f"unknown selectable name: '{n}'")
    return sel_agents, sel_skills, errors


def self_test():
    import tempfile, os
    man = (
        "# FORMAT: machine-manifest\n"
        "name\tkind\ttier\tdep_referrers\tnondep_referrers\tdep_semantics\tscience_present\tinstall_rule\tnote\n"
        "skill-a\tskill\tDEDICATED\tagent-x\t-\t-\tyes\t-\t-\n"
        "skill-b\tskill\tSHARED\tagent-x;agent-y\t-\t-\tyes\t-\t-\n"
        "skill-c\tskill\tSTANDALONE\t-\t-\t-\tyes\t-\t-\n"
        "skill-d\tskill\tDEFERRED\t-\t-\t-\tyes\t-\t-\n"
        "\n"
        "agent\tn_skills\tdedicated\tshared\trequired_skills\n"
        "agent-x\t2\t1\t1\tskill-a;skill-b\n"
        "agent-y\t1\t0\t1\tskill-b\n"
    )
    td = tempfile.mkdtemp(); mp = os.path.join(td, "m.tsv"); open(mp, "w").write(man)
    sk, ac, aa = parse_manifest(mp)
    rc = 0
    # (1) agent -> closure
    a, s, e = resolve(["agent-x"], sk, ac, aa)
    if a == {"agent-x"} and s == {"skill-a", "skill-b"} and not e:
        print("  (1) agent pulls its closure ✓")
    else:
        print(f"  (1) FAIL a={a} s={s} e={e}"); rc = 1
    # (2) standalone skill alone, no agent
    a, s, e = resolve(["skill-c"], sk, ac, aa)
    if a == set() and s == {"skill-c"} and not e:
        print("  (2) standalone skill pulls no agent ✓")
    else:
        print(f"  (2) FAIL a={a} s={s} e={e}"); rc = 1
    # (3) DEFERRED refused without flag, allowed with
    _, _, e1 = resolve(["skill-d"], sk, ac, aa)
    _, s2, e2 = resolve(["skill-d"], sk, ac, aa, allow_deferred=True)
    if e1 and not e2 and s2 == {"skill-d"}:
        print("  (3) DEFERRED refused w/o flag, allowed with ✓")
    else:
        print(f"  (3) FAIL e1={e1} e2={e2} s2={s2}"); rc = 1
    # (4) unknown name is a hard error
    _, _, e = resolve(["nope"], sk, ac, aa)
    if e and "unknown" in e[0]:
        print("  (4) unknown name errors ✓")
    else:
        print(f"  (4) FAIL e={e}"); rc = 1
    # (5) selecting a SHARED skill's one agent pulls that agent's full closure incl the shared skill
    a, s, e = resolve(["agent-y"], sk, ac, aa)
    if a == {"agent-y"} and s == {"skill-b"} and not e:
        print("  (5) shared-skill agent closure correct ✓")
    else:
        print(f"  (5) FAIL a={a} s={s} e={e}"); rc = 1
    print("SELF-TEST: PASS" if rc == 0 else "SELF-TEST: FAIL")
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest")
    ap.add_argument("--select")
    ap.add_argument("--manifest-subset")
    ap.add_argument("--allow-deferred", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if not a.manifest:
        ap.error("--manifest required")
    skills, closure, all_agents = parse_manifest(a.manifest)
    if a.list:
        print("== AGENTS ==")
        for ag in sorted(all_agents):
            print(f"  {ag}  ({len(closure.get(ag, []))} skills)")
        print("== SKILLS ==")
        for s in sorted(skills):
            print(f"  {s}  [{skills[s]['tier']}]")
        return
    if a.select:
        names = a.select.split(",")
    elif a.manifest_subset:
        names = [l.strip() for l in open(a.manifest_subset) if l.strip() and not l.startswith("#")]
    else:
        ap.error("one of --select / --manifest-subset / --list / --self-test required")
    sel_agents, sel_skills, errors = resolve(names, skills, closure, all_agents, a.allow_deferred)
    if errors:
        sys.stderr.write("SELECTION ERROR:\n" + "\n".join("  " + e for e in errors) + "\n")
        sys.exit(2)
    sys.stdout.write("==AGENTS==\n" + "\n".join(sorted(sel_agents)) + "\n")
    sys.stdout.write("==SKILLS==\n" + "\n".join(sorted(sel_skills)) + "\n")


if __name__ == "__main__":
    main()
