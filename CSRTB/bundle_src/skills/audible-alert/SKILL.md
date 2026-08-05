---
name: audible-alert
description: >-
  Produce an audible + visual alert inside Claude Science when a long task
  finishes — the Science-native analog of the Claude Code toolkit's xbeep
  hook. Invoke WHEN the user asks to "beep when done", "play a sound",
  "audible alert", "notify me when the run finishes", "change the alert
  sound", or wants an xbeep-equivalent. Science kernels run in a remote
  sandbox with no access to the machine's audio device, so the ONLY channel
  that reaches the user is the browser: this skill writes a self-contained
  HTML artifact that, when opened, plays a sound via the Web Audio API and
  flashes a banner + document title. Because the sound is produced in-browser
  it is OS-independent (macOS/Linux/Windows identical); the sole variance is
  the browser autoplay policy, which the page detects and degrades around
  automatically. Ships kernel.py helper emit_alert() with 14 built-in
  synthesized sounds (default "soft"), an optional sound_file= to embed a
  downloaded audio file, and repeat=. No network, no assets, no dependencies.
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# Audible alert (Claude Science)

The Claude Code toolkit fires **xbeep** from a Stop/Notification hook that runs
a local shell player (`afplay` / `paplay` / PowerShell). That model cannot port
verbatim: a Science analysis kernel runs in a **remote sandbox**, not on the
user's machine, and the `host` SDK exposes **no** notification/audio primitive.
The one channel from a session to the user's senses is the **browser**. So this
skill makes sound *in the browser tab* by emitting a self-contained HTML
artifact the user opens — which is why it is **OS-independent by construction**.

## Usage

`kernel.py` auto-loads when this skill is loaded, defining `emit_alert`:

```python
emit_alert("Run finished", "442 candidates scored")        # default: soft ping, once
emit_alert("Done", sound="chime", repeat=2)                # a different built-in
emit_alert("Done", sound_file="notify.mp3")                # your downloaded file
# then: save_artifacts(["alert.html"], language="python") and link it in the reply.
```

Signature:

```python
emit_alert(message="Task complete", detail="", sound="soft", repeat=1,
           sound_file=None, out_path="alert.html") -> out_path
```

- **message / detail** — banner text and subtitle.
- **sound** — a built-in synthesized sound. One of: `ping soft chime bell
  marimba xylophone glass doorbell arpup success twotone swell pop knock`.
  Default is **soft** (a single mellow tone). Audition every option in the
  companion **sound_picker.html** artifact.
- **sound_file** — optional path to a downloaded audio file (`.mp3`/`.wav`/
  `.ogg`). It is base64-embedded as a data URI, so the page stays fully
  self-contained (no network when opened). Overrides `sound`. Use it for a
  sound chosen from the online index in **ONLINE_ALERT_SOUNDS.md**.
- **repeat** — how many times to play, spaced by the sound's own length
  (default 1). Keep this at 1 unless the user wants insistence — the original
  "annoying" default was 12 beeps (3×4), not the tone.
- **out_path** — workspace filename to write.

Always `save_artifacts([...])` the returned file and reference it in your reply
as `![alert]({{artifact:VERSION_ID}})` / `[alert.html]({{artifact:VERSION_ID}})`
so the user can open it — the sound only plays when the page is open.

## Choosing / changing the sound

- **Built-in (recommended, zero deps):** point the user at `sound_picker.html`
  (14 sounds, each with a Play button and its `emit_alert(sound="…")` call),
  then pass their pick as `sound=`.
- **From the web:** `ONLINE_ALERT_SOUNDS.md` lists curated royalty-free
  sources. Download a file into the workspace, pass it as `sound_file=`.

## How it degrades (why it is robust across browsers/OSes)

Four layers run at once, most → least robust:

1. **Visual banner + flashing document title** — works with zero audio.
2. **First-interaction / return-to-tab play** — the instant the user clicks,
   presses a key, or switches back to the tab, it plays. Defeats a browser
   autoplay block automatically, without a dedicated button.
3. **Autoplay attempt on load** — truly hands-free when the browser permits.
4. **Explicit "Play alert" button** — manual guarantee.

The page prints a **self-check panel** on open (chosen sound, Web Audio
availability, autoplay ALLOWED/BLOCKED, in-iframe, notification permission).

## Limits (on-demand emit_alert)

- **Not hook-fired.** Nothing auto-opens the emitted page; the user opens the
  artifact. For a genuinely hands-free turn-end beep (no click), use the
  **hands-free standing protocol** below — a running MCP server the agent beeps,
  not this HTML emitter.
- **Sound needs the tab open.** If autoplay is blocked and the tab never gets
  focus/interaction, only the visual flash shows until the user returns to it.

## Hands-free standing protocol (agent-fired turn-end beep)

This is the SHIPPED hands-free variant — the true xbeep analog. It does NOT use
`emit_alert`/HTML artifacts; it is a persistent MCP server the agent beeps
directly, so the sound fires with NO click. Verified working 2026-07-15.

WHY IT EXISTS: Claude Science has NO turn-end hook, so a turn-end beep is
AGENT-INITIATED — the agent calls it as its last action; nothing auto-fires it.
An earlier design pushed beeps into an inline `ui://` app-tile via
`host.app("<server>").beep()`; that FAILED because the platform would not mount
an off-host custom server's inline tile. The working design INVERTS to POLLING.

ARCHITECTURE (poll, not push):
- A FastMCP server runs on the USER'S MAC behind a cloudflared quick tunnel.
- Three surfaces on one port: the MCP endpoint at **/mcp** (the connector
  target), **GET /tile** (a plain audio page the user opens in a browser tab),
  and **GET /beep-next** (a poll endpoint).
- The `beep` MCP tool ENQUEUES `{sound,message,repeat}` into an in-process deque
  and returns `{queued,...,queue_len}`. The open tab polls /beep-next every
  ~2.5s and plays queued beeps via a 14-sound Web-Audio synth. INSTANCE-
  INDEPENDENT: uses only Web Audio in a tab + an HTTP GET — never the tile-mount
  hop that failed.

FIRING POLICY (what every agent should do, if this behavior is in its profile):
- PAUSE-FOR-INPUT (before any `ask_user`, or any turn ending awaiting the user):
  `host.mcp("hands-free-alert","beep",sound="twotone")`. Always.
- FULL-STOP (substantive work done, nothing pending): as the genuine last
  action, `host.mcp("hands-free-alert","beep",sound="soft")`. NEVER on quick
  one-line replies/acknowledgements — beep-spam on trivial turns is the exact
  annoyance to avoid.
- FIRE-AND-FORGET: wrap in `try/except Exception: pass`. The tunnel/server is
  often down (quick-tunnel URLs churn); a failed beep must never delay the turn,
  retry, or be narrated. Do not verify reachability first.
- MCP calls run ONLY in the `repl` tool. The connector name `hands-free-alert`
  is load-bearing (the literal string in the call). Sounds swappable (14
  synthesized; soft = stop, twotone = input).

DEPLOY / REDEPLOY (all steps are the USER's; needed each time the tunnel churns):
1. On the Mac: `cd "…/Claude R code dev/audible-alert-server" && ./run_alert_server.sh`
   (reclaims a stale :8000 port, serves the poll server, prints a NEW <tunnel>
   URL; leave the terminal open).
2. Customize -> Connectors: add a Remote-URL connector `hands-free-alert` at
   `<tunnel>/mcp` (the **/mcp** suffix is REQUIRED — bare URL => 404 Not Found).
   Delete the old connector first (Claude has no edit-connector).
3. Open `<tunnel>/tile` in a browser tab, click "Enable sound" once (goes green).
4. AGENT (repl): `host.mcp("hands-free-alert","beep",sound="soft")` => the armed
   tab plays within ~3s. To stop per-run re-registration, use a NAMED cloudflared
   tunnel or an ngrok reserved domain.

FILES (deployed on the Mac at .../Claude R code dev/audible-alert-server/):
audible_alert_server.py (poll server), audible_alert_poll_tile.html (the /tile
page), run_alert_server.sh (launcher). Full detail + resume state = the
audible-alert-handoff bundle under .../projects/Claude Science/.
