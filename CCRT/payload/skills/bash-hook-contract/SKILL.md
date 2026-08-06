---
name: bash-hook-contract
description: Invoke WHEN writing or debugging a Claude Code hook (bash/python) or any script that reads Claude's stdin-JSON, maps hook exit codes (0 pass / 2 block / others fail-open-but-logged), enforces a portable timeout without the `timeout` binary, gates on the CRT master switch, or writes a file atomically. Holds the macOS/Linux portability contract for hooks. Pair with the toolkit-extension-authoring skill for where the hook registers.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# STATUS: CURRENT (2026-07-12).
# bash-hook-contract - the Claude Code hook I/O + portability contract

## When to invoke
WHEN about to author or debug a hook script under `payload/hooks/` (or `~/.claude/hooks/`), OR any script Claude Code invokes as a hook command => apply this contract. The hook's correctness is a CONTRACT with the harness, not free-form scripting: get the I/O shape, exit codes, timeout, and portability right or it silently no-ops.

## 1. Read hook context from STDIN JSON, not env vars
WHEN a hook needs the tool name / file path / prompt => read it from the stdin JSON payload, NOT from `CLAUDE_TOOL` / `CLAUDE_FILE_PATH` env vars. Current Claude Code passes hook data on stdin; the old env vars are no longer set, so an env-var hook silently no-ops (fires, extracts nothing, exits 0 - the worst failure: looks alive, does nothing).
- Canonical read + extract (python3 primary, grep/sed fallback so it still works if python3 is absent):
```bash
input="$(cat 2>/dev/null || true)"
file_path=""
if command -v python3 >/dev/null 2>&1; then
  file_path="$(printf '%s' "$input" | python3 -c '
import sys, json
try: d = json.load(sys.stdin)
except Exception: d = {}
ti = d.get("tool_input", {}) or {}
print(ti.get("file_path") or ti.get("filePath") or ti.get("path") or "")' 2>/dev/null || true)"
fi
if [ -z "${file_path:-}" ]; then   # a file path has no newlines => line-wise grep/sed is safe
  file_path="$(printf '%s' "$input" | grep -oE '"file_?[Pp]ath"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//; s/"$//')"
fi
```
- TELL a hook reads `$CLAUDE_*` env => it is the pre-fix shape; convert to the stdin read above.
- Key payload fields: `tool_name`, `tool_input` (has `file_path`/`filePath`/`path`, `command`, ...), `prompt` (UserPromptSubmit). Accept the camelCase AND snake_case spellings (harness versions differ).

## 2. Exit codes are a documented contract; default to fail-open-but-logged
An LLM-facing gate hook must map exit codes deliberately, because a wrong code either blocks the user or lets a bad completion through.
- `exit 0` => PASS (hook is satisfied; work proceeds). The default for a passive reminder hook.
- `exit 2` => BLOCK (Stop/PreToolUse hook vetoes the action; the message on stderr tells Claude why).
- Any OTHER nonzero (e.g. a forked helper returning `124` timeout / `127` missing-binary) => treat as INDETERMINATE => FAIL-OPEN but LOG it. WHEN a gate cannot reach a verdict => let the work proceed AND write one line to a log, never block on an internal error.
- Concrete: the F1 adversary Stop-gate forks `claude -p` on the final claim; `rc=124`(timeout) or `rc=127`(claude/timeout missing) => fail-open-but-logged, NOT a block. A silent fail-open (no log) is the bug - you cannot tell a clean pass from a broken gate.
- Emit human/agent-facing hook messages on STDERR (`cat >&2 <<EOF ... EOF`); stdout is reserved for structured protocol on hook types that consume it.

## 3. Enforce a timeout ceiling in python3, not the `timeout` binary
WHEN a hook forks a slow subprocess (another `claude`, a network call) and must bound it => enforce the ceiling with python3's `subprocess` timeout, NOT the shell `timeout` binary. macOS without Homebrew coreutils has NO `timeout` => the call returns `rc=127` => error branch => the intended bound never applies (and a naive gate then fail-opens silently). python3 is already a hard dep of the hooks, so a python3 ceiling is identical on macOS + Linux and preserves the 124/127/passthrough rc semantics.
- Example (60s ceiling, portable): `python3 - "$claim" <<'PY'` ... `subprocess.run([...], timeout=60)`; on `TimeoutExpired` `sys.exit(124)`; on `FileNotFoundError` `sys.exit(127)`.
- Do NOT "skip the timeout when the binary is absent" - an unbounded fork can hang the Stop hook and wedge the session.

## 4. Portable by default: macOS AND Linux, with a fallback chain
WHEN a hook shells out to a platform tool (sound, clipboard, `sed -i`, `date`) => provide a fallback chain, not one hard dependency, and assume BOTH OSes.
- Sound: try `afplay` (macOS) -> `paplay` (PulseAudio) -> `aplay` (ALSA) -> terminal bell `\a`. Point at a sound via `$XBEEP_SOUND` override.
- `sed -i` differs (`sed -i ''` macOS vs `sed -i` GNU) => prefer a temp-file rewrite + `mv`, or do the transform in python3.
- Guard every platform binary with `command -v <bin> >/dev/null 2>&1` before calling it; degrade, don't error.

## 5. Write files atomically; one writer per file
WHEN a hook or helper writes a file another process may read (a state file, a merged config, a log another hook appends) => write a temp file then atomically rename (`os.replace(tmp, dst)` in python; `mv` on the same filesystem in bash). A truncate-mode write another reader catches mid-flush yields a corrupt/partial read with no error on either side. Give concurrent writers distinct filenames; never two writers on one path.

## 6. Gate intervention hooks on the CRT master switch
WHEN authoring a hook that INJECTS behavior (a reminder, a block, an extra prompt) => honor the shared on/observe/off switch so the user (and the research shadow arm) can silence it. Resolve mode: `$CRT_MODE` env wins, else read `${CLAUDE_HOME:-$HOME/.claude}/crt_mode`, else default `on`. BOTH `off` and `observe` silence an intervention hook (`observe` = measure unaided behavior); only `on` emits. A pure passive LOGGER (writes a JSONL line, injects nothing) may run in all modes - it is not an intervention.
```bash
_crt_mode="${CRT_MODE:-}"
[ -z "$_crt_mode" ] && { _cmf="${CRT_MODE_FILE:-${CLAUDE_HOME:-$HOME/.claude}/crt_mode}"; [ -r "$_cmf" ] && _crt_mode="$(tr -d '[:space:]' < "$_cmf")"; }
[ "${_crt_mode:-on}" != "on" ] && exit 0
```

## 7. Shell hygiene
`#!/usr/bin/env bash` + `set -eo pipefail` (NOT `set -u` if you read maybe-unset hook vars; guard with `${x:-}`). Keep the hook fast - it runs on every matching event; a slow hook taxes every turn.

## Refs
`toolkit-extension-authoring` (where a hook registers: the `payload/settings/<name>.fragment.json` + `FRAGS+=` recipe, and matcher/exit-code registration) - author the script HERE, wire it THERE.
