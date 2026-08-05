#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>

# User Prompt Submit Hook for Claude Code xbeep
# Intercepts /xbeep commands to manage beep state
# Exit 0 = pass through, Exit 2 = block prompt (command handled here)

# --- Configuration ---
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
BEEP_STATE_SCRIPT="${HOOK_DIR}/beep-state.sh"
XBEEP_DEBUG="${XBEEP_DEBUG:-0}"
DEBUG_LOG="/tmp/claude/hook-debug.log"

# --- Debug logging (only when XBEEP_DEBUG=1) ---
log_debug() {
    if [[ "$XBEEP_DEBUG" == "1" ]]; then
        echo "$@" >> "$DEBUG_LOG"
    fi
}

if [[ "$XBEEP_DEBUG" == "1" ]]; then
    mkdir -p -m 700 "$(dirname "$DEBUG_LOG")"
    log_debug "=== $(date '+%Y-%m-%d %H:%M:%S') user-prompt-submit ==="
fi

# --- Read stdin ---
input=$(cat)
log_debug "Input (first 200 chars): ${input:0:200}"

# --- Check for /xbeep command ---
# Use a single reliable extraction path: awk to get the prompt field value
if echo "$input" | grep -q '"prompt":"/xbeep'; then
    # Extract the full prompt value
    prompt=$(echo "$input" | awk -F'"prompt":"' '{print $2}' | awk -F'"' '{print $1}')
    log_debug "Extracted prompt: '$prompt'"

    # Extract argument (on/off/status/etc.) from the prompt
    if [[ "$prompt" =~ ^/xbeep[[:space:]]+(.+)$ ]]; then
        arg="${BASH_REMATCH[1]}"
    else
        arg=""
    fi
    log_debug "Argument: '$arg'"

    # Execute beep-state.sh with the argument
    output=$(bash "$BEEP_STATE_SCRIPT" "${arg:-}" 2>&1)
    log_debug "Output: $output"

    # Send output to stderr so user sees it
    echo "$output" >&2

    # Exit 2 to block the prompt from reaching Claude
    exit 2
else
    log_debug "Not /xbeep, passing through"
    exit 0
fi
