#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>
"""transcript_archive.py — Claude Code SessionStart hook + detached archiver.

PRESERVES the AUTO-PRODUCED Claude Code record — session transcripts, subagent
logs, auto-memory, history, todos — into a vault OUTSIDE ~/.claude, so the
built-in `cleanupPeriodDays` startup purge (default 30d) can never reach it.
This is the belt-and-suspenders companion to the `cleanupPeriodDays: 99999`
retention-max in the same settings fragment: retention keeps the live copy,
the vault keeps an out-of-tree copy the purge/reset/mtime-edge-case cannot
touch. For scientific work the transcript is the lab notebook (the WHY/HOW);
git + the artifact store hold the WHAT. This closes the one un-redundant gap.

SCOPE (the load-bearing distinction): copies only files Claude Code PRODUCES
AUTOMATICALLY. NEVER copies (a) secrets — .credentials* ; (b) re-derivable
customization — skills/ agents/ commands/ hooks/ lib/ rules/ methodology/
docs/ plugins/ backups/ settings*.json CLAUDE*.md (all in git + reproducible
from install.sh) ; (c) the sweep's own state — .last-cleanup. Everything else
copies (fail-safe toward "never lose a record"); anything outside the
documented expected set is COPIED and FLAGGED in the log so the classification
self-audits against future CC versions.

Two modes (self-re-exec):
  hook mode (no args): SessionStart entry. Reads+discards stdin JSON, honors
      the CRT master switch, spawns THIS file --run DETACHED, exits 0 at once
      (a backup must NEVER delay the user's session start).
  --run: acquire a lock, incrementally mirror the copy-eligible tree to the
      vault (copy when dest absent OR src newer/size-differs; mtime-preserving;
      NEVER deletes), append one JSON line to <vault>/archive-log.jsonl.

Contract: SessionStart · python3 pure stdlib · exit 0 ALWAYS (fail-open on the
session; every failure is logged to the vault log, never surfaced as a session
error). Portable macOS+Linux: no rsync, no `timeout` binary, no setsid — detach
via subprocess start_new_session; delta-copy + lock in stdlib.

Env: CLAUDE_HOME (default ~/.claude) · CRT_VAULT_DIR (default ~/.claude-vault)
     · CRT_VAULT_EXCLUDE (":"/"," list of extra top-level names to skip)
     · CRT_MODE / CRT_MODE_FILE (master switch; "off" => fully inert).
"""
import sys, os, json, time, shutil, subprocess

HOME = os.path.expanduser("~")
STALE_LOCK_SEC = 1800          # a lock older than this is presumed dead and stolen
LOG_NAME = "archive-log.jsonl"
LOCK_NAME = ".archive.lock"
MIRROR_SUBDIR = "claude-home"  # the mirror lives under <vault>/claude-home/ so the log sits beside it


def claude_home():
    return os.environ.get("CLAUDE_HOME") or os.path.join(HOME, ".claude")


def vault_dir():
    return os.environ.get("CRT_VAULT_DIR") or os.path.join(HOME, ".claude-vault")


def crt_mode():
    """CRT MASTER SWITCH: on (default) | observe | off. $CRT_MODE wins over the
    ~/.claude/crt_mode file; unknown value => 'on' (fail-safe: stay protective).
    This hook injects NOTHING into the model context — it is an invisible
    side-effect — so 'observe' (the unaided-behaviour shadow arm) does NOT
    suppress it (a silent backup cannot contaminate the measurement). Only a
    deliberate 'off' (toolkit fully inert) skips it; retention-max still guards
    the live copy even then."""
    m = os.environ.get("CRT_MODE", "").strip()
    if not m:
        cmf = os.environ.get("CRT_MODE_FILE") or os.path.join(claude_home(), "crt_mode")
        try:
            with open(cmf) as fh:
                m = fh.read().strip()
        except Exception:
            m = ""
    return m or "on"


# --- classification (grounded in the real ~/.claude tree, CC v2.1.207) -------
SECRET_PREFIXES = (".credentials",)          # auth token — NEVER vault a secret
CUSTOMIZATION = {                            # re-derivable from install.sh + git (class-2)
    "skills", "agents", "commands", "hooks", "lib", "rules", "methodology",
    "docs", "plugins", "backups",
    "settings.json", "settings.local.json", "CLAUDE.md", "CLAUDE.local.md",
    "toolkit_build.json",                    # install.sh write_build_stamp provenance — re-derivable
}
SWEEP_STATE = {".last-cleanup"}              # the purge's own bookkeeping
SETTINGS_BAK_PREFIXES = (                    # install.sh's own snapshots of DENY'd settings*
    "settings.json.bak", "settings.local.json.bak",
)
NOISE = {".DS_Store"}                        # OS filesystem cruft — never CC-produced, never a record
EXPECTED = {                                 # documented auto-produced entries; NOT a copy gate (unknowns still copy)
    # transcripts / activity record
    "projects", "history.jsonl", "todos", "file-history", "shell-snapshots",
    "sessions", "statsig", "cache", "debug", "stats-cache.json", "ide", "logs",
    # observed on real macOS ~/.claude (CC v2.1.207, 2026-07-12): auto-produced work record
    "plans", "tasks", "uploads", "paste-cache", "jobs", "daemon", "daemon.log",
    "session-env", "state",
}


def user_exclude():
    raw = os.environ.get("CRT_VAULT_EXCLUDE", "")
    return {x.strip() for x in raw.replace(",", ":").split(":") if x.strip()}


def is_denied(name, excl):
    if name in excl or name in CUSTOMIZATION or name in SWEEP_STATE or name in NOISE:
        return True
    if any(name.startswith(p) for p in SETTINGS_BAK_PREFIXES):
        return True                          # install.sh snapshots of DENY'd settings* — same class
    return any(name.startswith(p) for p in SECRET_PREFIXES)


# --- incremental, never-deleting mirror --------------------------------------
def _needs_copy(src, dst):
    """Copy iff dest missing, or src size/mtime indicates a newer/changed file."""
    try:
        ss = os.stat(src)
    except OSError:
        return False
    try:
        ds = os.stat(dst)
    except OSError:
        return True
    return (ss.st_size != ds.st_size) or (ss.st_mtime > ds.st_mtime + 1e-6)


def _copy_file(src, dst, st):
    if not _needs_copy(src, dst):
        st["skipped"] += 1
        return
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)              # copy2 preserves mtime
        st["copied"] += 1
        st["bytes"] += os.path.getsize(dst)
    except Exception as e:                  # one unreadable file must not abort the run
        st["errors"].append("%s: %s" % (src, e))


def _mirror_entry(src_root, name, mirror_root, st):
    src = os.path.join(src_root, name)
    if os.path.islink(src) and os.path.isdir(src):
        return                              # don't follow symlinked dirs (loop-safe)
    if os.path.isfile(src):
        _copy_file(src, os.path.join(mirror_root, name), st)
    elif os.path.isdir(src):
        for dp, _dirs, files in os.walk(src, followlinks=False):
            rel = os.path.relpath(dp, src_root)
            for f in files:
                if f in NOISE:              # OS cruft (.DS_Store) at any depth — not a record
                    continue
                _copy_file(os.path.join(dp, f), os.path.join(mirror_root, rel, f), st)


def _acquire_lock(lockpath):
    """Best-effort single-writer lock. Returns True if held. Steals a stale lock."""
    try:
        fd = os.open(lockpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.write(fd, ("%d %f\n" % (os.getpid(), time.time())).encode())
        os.close(fd)
        return True
    except FileExistsError:
        ts = 0.0
        try:
            ts = float(open(lockpath).read().split()[1])
        except Exception:
            ts = 0.0
        if time.time() - ts < STALE_LOCK_SEC:
            return False                    # a live archiver is running — yield
        try:                                # stale — steal it
            os.unlink(lockpath)
            fd = os.open(lockpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, ("%d %f\n" % (os.getpid(), time.time())).encode())
            os.close(fd)
            return True
        except Exception:
            return False


def _log(vault, record):
    try:
        os.makedirs(vault, exist_ok=True)
        with open(os.path.join(vault, LOG_NAME), "a") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    except Exception:
        pass                                # logging must never raise


def run():
    """--run mode: the actual archive pass. Fail-open, log everything."""
    t0 = time.time()
    ch, vault = claude_home(), vault_dir()
    rec = {"ts": t0, "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "claude_home": ch, "vault": vault, "status": "ok",
           "copied": 0, "skipped": 0, "bytes": 0,
           "excluded": [], "unknown": [], "errors": []}

    # invariant: the vault MUST live outside ~/.claude, or the purge would eat it
    # (and we'd mirror-a-mirror). Refuse if misconfigured.
    rv, rc = os.path.realpath(vault), os.path.realpath(ch)
    if rv == rc or rv.startswith(rc + os.sep):
        rec["status"] = "refused: vault is inside CLAUDE_HOME"
        _log(vault if not rv.startswith(rc + os.sep) else os.path.join(HOME, ".claude-vault"), rec)
        return
    if not os.path.isdir(ch):
        rec["status"] = "skip: no CLAUDE_HOME"
        _log(vault, rec)
        return

    lock = os.path.join(vault, LOCK_NAME)
    try:
        os.makedirs(vault, exist_ok=True)
    except Exception as e:
        rec["status"] = "error: vault unwritable: %s" % e
        _log(os.path.join(HOME, ".claude-vault"), rec)
        return
    if not _acquire_lock(lock):
        return                              # another archiver holds the lock — silent yield

    try:
        mirror_root = os.path.join(vault, MIRROR_SUBDIR)
        excl = user_exclude()
        for name in sorted(os.listdir(ch)):
            if is_denied(name, excl):
                rec["excluded"].append(name)
                continue
            if name not in EXPECTED:        # copied anyway (fail-safe) but flagged for review
                rec["unknown"].append(name)
            _mirror_entry(ch, name, mirror_root, rec)
        if rec["errors"]:
            rec["status"] = "ok-with-errors (%d)" % len(rec["errors"])
        rec["errors"] = rec["errors"][:20]  # cap log-line size
    except Exception as e:
        rec["status"] = "error: %s" % e
    finally:
        rec["duration_s"] = round(time.time() - t0, 3)
        _log(vault, rec)
        try:
            os.unlink(lock)
        except Exception:
            pass


def hook_mode():
    """SessionStart entry: consume stdin, honor the switch, detach --run, exit 0."""
    try:
        sys.stdin.read()                    # drain stdin JSON per hook contract
    except Exception:
        pass
    if crt_mode() == "off":                 # toolkit fully inert
        return
    try:
        devnull = open(os.devnull, "wb")
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--run"],
            stdin=subprocess.DEVNULL, stdout=devnull, stderr=devnull,
            start_new_session=True, close_fds=True,
        )                                   # detached; parent returns immediately
    except Exception:
        pass                                # never let a spawn failure break session start


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        run()
    else:
        hook_mode()
    sys.exit(0)                             # ALWAYS 0 — never block the session
