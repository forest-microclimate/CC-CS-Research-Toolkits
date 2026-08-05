#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
# merge_settings.py TARGET FRAG1 [FRAG2 ...]
# Deep-merge each FRAG (a settings.json fragment) into TARGET, in place, WITHOUT clobbering.
# Semantics:
#   - objects merge recursively;
#   - hook-event arrays (lists whose items are {matcher, hooks:[...]}) merge BY matcher, and the
#     hooks within a matcher dedup BY command (so re-running the installer never duplicates a hook,
#     and two fragments that both add a UserPromptSubmit hook end up in ONE matcher group);
#   - other string arrays (deny / allow / ask) union, order-preserving;
#   - scalars / type-clash: the fragment wins.
# Atomic write via os.replace. TARGET is pre-validated as JSON by install.sh (json.load raises here otherwise).
import json, os, sys


def dedup(seq):
    out, seen = [], set()
    for x in seq:
        k = x if isinstance(x, str) else json.dumps(x, sort_keys=True)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def dedup_hooks(hs):
    out, seen = [], set()
    for h in hs:
        k = h.get("command", json.dumps(h, sort_keys=True)) if isinstance(h, dict) else json.dumps(h, sort_keys=True)
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out


def is_hook_group(x):
    return isinstance(x, dict) and "hooks" in x


def is_hook_array(x):
    # a hook-event array = a NON-EMPTY list whose items are all {matcher?, hooks:[...]} groups.
    return isinstance(x, list) and bool(x) and all(is_hook_group(i) for i in x)


def coalesce_by_matcher(groups):
    # Merge hook groups that share a matcher (incl. "") into ONE group, order-preserving,
    # deduping hooks within each matcher BY command. Idempotent: coalescing an already-
    # coalesced list is a no-op. This is what makes run1 == run2 (T-27) — a fragment that
    # ships two same-matcher blocks is collapsed on the FIRST write, not only on re-merge.
    by, order = {}, []
    for x in groups:
        m = x.get("matcher", "")
        if m not in by:
            by[m] = {"matcher": m, "hooks": []}
            order.append(m)
        by[m]["hooks"].extend(x.get("hooks", []))
    for m in order:
        by[m]["hooks"] = dedup_hooks(by[m]["hooks"])
    return [by[m] for m in order]


def merge_lists(a, b):
    if (a or b) and all(is_hook_group(x) for x in a + b):  # hook-event arrays: merge by matcher
        return coalesce_by_matcher(a + b)
    return dedup(a + b)  # deny / allow / ask etc.: union


def normalize(x):
    # Recursively coalesce every hook-event array so the merged result is a fixpoint on
    # the FIRST write, regardless of how a fragment authored its blocks. Mirrors merge_lists'
    # own hook-array detection exactly; a no-op on already-normalized structures.
    if isinstance(x, dict):
        return {k: normalize(v) for k, v in x.items()}
    if is_hook_array(x):
        return [normalize(g) for g in coalesce_by_matcher(x)]
    if isinstance(x, list):
        return [normalize(i) for i in x]
    return x


def merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        for k, v in b.items():
            a[k] = merge(a[k], v) if k in a else v
        return a
    if isinstance(a, list) and isinstance(b, list):
        return merge_lists(a, b)
    return b  # scalar / type-clash: fragment wins


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: merge_settings.py TARGET FRAG1 [FRAG2 ...]")
    target = sys.argv[1]
    data = {}
    if os.path.exists(target) and os.path.getsize(target) > 0:
        with open(target) as f:
            data = json.load(f)
    for frag in sys.argv[2:]:
        with open(frag) as f:
            data = merge(data, json.load(f))
    data = normalize(data)  # coalesce hook blocks so a first install already == a re-install (T-27)
    tmp = target + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, target)
    print("merged %d fragment(s) -> %s" % (len(sys.argv) - 2, target))


if __name__ == "__main__":
    main()
