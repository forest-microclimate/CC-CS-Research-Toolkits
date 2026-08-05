#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""ambient_time.py — Claude Code UserPromptSubmit + SessionStart hook.

Emits ONE ambient local-time line so the assistant knows the current local
time + elapsed-since-last-prompt. Pure stdlib, no network (F3: 30s cap,
output discarded on timeout — keep <1s). PLAIN TEXT to stdout + exit 0
(G7/#17550: NOT hookSpecificOutput JSON, which errors on a session's first
message; G5: never exit 2 — that erases the prompt).

Design-of-record: HANDOFF_BUILD_AMBIENT_TIME_INJECTION.machine.md (§6 FORMAT_SPEC, §7 F7).
"""
import sys, os, json, time, datetime, pathlib

def resolve_iana():
    """Best-effort IANA zone from /etc/localtime symlink; fall back to abbrev."""
    try:
        p = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in p:
            return p.split("zoneinfo/", 1)[1]
    except Exception:
        pass
    return None

def crt_mode():
    """CRT MASTER SWITCH: on (default) | observe | off.
    Shared toolkit on/off control (see methodology/CRT_MASTER_SWITCH.machine.md).
    This hook INJECTS a time line into the model's context, so it is an INTERVENTION:
    BOTH "off" and "observe" suppress it — "off" = fully inert; "observe" = research
    shadow arm where the agent runs without toolkit prompting so its unaided behaviour
    is measurable. Only "on" emits. $CRT_MODE env wins over ~/.claude/crt_mode; an
    unrecognized value falls through to "on" (fail-safe: stay protective)."""
    m = os.environ.get("CRT_MODE", "").strip()
    if not m:
        cmf = os.environ.get("CRT_MODE_FILE") or os.path.join(
            os.environ.get("CLAUDE_HOME") or os.path.join(os.path.expanduser("~"), ".claude"),
            "crt_mode")
        try:
            with open(cmf) as fh:
                m = fh.read().strip()
        except Exception:
            m = ""
    return m or "on"

def fmt_delta(sec):
    if sec is None:
        return "session start"
    sec = int(round(sec)); sign = "+" if sec >= 0 else "-"; sec = abs(sec)
    d, r = divmod(sec, 86400); h, r = divmod(r, 3600); m, s = divmod(r, 60)
    if d: return f"{sign}{d}d{h}h{m}m"
    if h: return f"{sign}{h}h{m}m"
    if m: return f"{sign}{m}m"
    return f"{sign}{s}s"

def main():
    # 0. CRT master switch: only "on" injects the ambient-time line. "off"/"observe"
    #    emit nothing and exit 0 (never exit 2 — G5: that would erase the prompt).
    if crt_mode() != "on":
        sys.exit(0)
    # 1. read stdin JSON (F1: session_id/prompt/cwd; SessionStart carries `source`, F4)
    raw = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
    except Exception:
        raw = ""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}
    sid = data.get("session_id", "default")
    # SessionStart is emit-only: it must NOT overwrite the last-prompt epoch, or the
    # first prompt after a resume would measure vs session-start (few sec) and HIDE the
    # overnight gap — the exact signal we want. UserPromptSubmit is the sole writer.
    is_session_start = ("source" in data) and ("prompt" not in data)

    # 2. state file keyed by session_id (survives --resume: same session_id).
    # CLAUDE_AMBIENT_STATE overrides the path (testability; unset in normal use).
    override = os.environ.get("CLAUDE_AMBIENT_STATE")
    if override:
        state_path = pathlib.Path(override)
    else:
        proj = os.environ.get("CLAUDE_PROJECT_DIR", ".")
        state_path = pathlib.Path(proj) / ".claude" / "state" / "ambient_time_last.json"
    try:
        state = json.loads(state_path.read_text())
    except Exception:
        state = {}

    now = time.time()
    last = state.get(sid)
    delta = (now - last) if isinstance(last, (int, float)) else None

    # 3. write now back — ONLY on UserPromptSubmit (never fail the prompt over I/O)
    if not is_session_start:
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state[sid] = now
            state_path.write_text(json.dumps(state))
        except Exception:
            pass

    # 4. format the line (F7: 24h, explicit UTC+-HH:MM, epoch, decomposed)
    local = datetime.datetime.now().astimezone()
    stamp = local.strftime("%Y-%m-%d %H:%M:%S")
    off = local.strftime("%z")                       # e.g. +1000
    off_fmt = f"UTC{off[:3]}:{off[3:]}" if len(off) == 5 else "UTC?"
    iana = resolve_iana() or local.tzname() or "local"
    line = (f"<ambient-time> {stamp} | {iana} {off_fmt} | "
            f"epoch={int(now)} | \u0394_since_last={fmt_delta(delta)} </ambient-time>")
    sys.stdout.write(line + "\n")
    sys.exit(0)

if __name__ == "__main__":
    main()
