# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
def draft_handoff_brief(goal="", phase="", next_steps=None, kernel_reload=None, memory_note="", limit=12):
    """Scaffold a Claude Science cold-start brief from the current project's recent artifacts.
    Fill goal / phase / next_steps (list) / kernel_reload (list) / memory_note; the canonical-artifacts
    section is auto-populated from host.artifacts(). Returns markdown to save as handoff_brief.md.
    See SKILL.md ## Procedure step 3."""
    try:
        arts = host.artifacts(limit=limit).get("artifacts", [])
    except Exception as e:
        arts = []
    out = ["# Cold-start brief"]
    if goal:  out.append("\n**GOAL:** " + goal)
    if phase: out.append("**PHASE:** " + phase)
    out.append("\n## Canonical artifacts (load by id)")
    if arts:
        for a in arts:
            vid = a.get("latest_version_id", "")
            marker = host.artifact_marker(vid) if vid else "(no version_id)"
            out.append("- `" + str(a.get("filename", "?")) + "` — " + marker)
    else:
        out.append("- (none found — save_artifacts first, or widen limit)")
    if kernel_reload:
        out.append("\n## Kernel state to reconstruct")
        for k in kernel_reload: out.append("- " + str(k))
    if memory_note:
        out.append("\n## Memory to trust")
        out.append(memory_note)
    if next_steps:
        out.append("\n## Next (priority-ordered; GATE = observable that proves it worked)")
        for i, s in enumerate(next_steps, 1): out.append(str(i) + ". " + str(s))
    return "\n".join(out)
