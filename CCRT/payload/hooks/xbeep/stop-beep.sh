#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>

# Stop Beep Hook for Claude Code
# Beeps when Claude finishes responding and is waiting for next input

# --- Configuration ---
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
BEEP_STATE_SCRIPT="${HOOK_DIR}/beep-state.sh"
XBEEP_DEBUG="${XBEEP_DEBUG:-0}"
DEBUG_LOG="/tmp/claude/stop-hook-debug.log"

# Sound: XBEEP_SOUND env var > OS-appropriate default > terminal bell fallback
if [ -n "${XBEEP_SOUND:-}" ]; then
    SOUND_FILE="$XBEEP_SOUND"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    SOUND_FILE="/System/Library/Sounds/Glass.aiff"
else
    SOUND_FILE=""  # Linux/WSL: play_sound() will use terminal bell
fi

# --- Debug logging (only when XBEEP_DEBUG=1) ---
log_debug() {
    if [[ "$XBEEP_DEBUG" == "1" ]]; then
        echo "$@" >> "$DEBUG_LOG"
    fi
}

if [[ "$XBEEP_DEBUG" == "1" ]]; then
    mkdir -p -m 700 "$(dirname "$DEBUG_LOG")"
    log_debug "=== $(date '+%Y-%m-%d %H:%M:%S') stop-hook ==="
fi

# --- Cross-platform sound playback ---
play_sound() {
    local sound_file="$1"
    if [ -f "$sound_file" ] && command -v afplay &>/dev/null; then
        afplay "$sound_file" &          # macOS
    elif [ -f "$sound_file" ] && command -v paplay &>/dev/null; then
        paplay "$sound_file" &          # Linux (PulseAudio)
    elif [ -f "$sound_file" ] && command -v aplay &>/dev/null; then
        aplay -q "$sound_file" &        # Linux (ALSA)
    else
        printf '\a'                     # Terminal bell fallback
    fi
}

# --- Read stdin FIRST (before any subprocess calls) ---
input=$(cat)
log_debug "Input (first 300 chars): ${input:0:300}"

# --- Check if beeping is enabled ---
if ! bash "$BEEP_STATE_SCRIPT" check 2>/dev/null; then
    log_debug "Beeping DISABLED, exiting"
    exit 0
fi
log_debug "Beeping ENABLED"

# --- Loop prevention: extract the specific field value ---
# Fix: previously grepped the entire JSON body including Claude's response text.
# If Claude discussed xbeep code (mentioning "stop_hook_active" and "true"),
# the grep matched and silently suppressed the beep.
# Now: extract only the stop_hook_active field value.
stop_active=$(echo "$input" | grep -o '"stop_hook_active":[a-z]*' | head -1 | sed 's/.*://')
if [ "$stop_active" = "true" ]; then
    log_debug "stop_hook_active=true, preventing loop"
    exit 0
fi

# --- Play the beep ---
log_debug "Playing beep sound"
play_sound "$SOUND_FILE"
log_debug "Stop hook completed (sound PID: $!)"

exit 0
