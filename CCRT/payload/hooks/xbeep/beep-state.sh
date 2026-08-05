#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com>

# Beep State Management for Claude Code Hooks
# Manages session-specific beep notification state

# State file for beep notifications
# Use TERM_SESSION_ID for session isolation, fallback to fixed name
if [ -n "$TERM_SESSION_ID" ]; then
    STATE_FILE="${TMPDIR:-/tmp}/claude_beep_enabled_${TERM_SESSION_ID}"
else
    STATE_FILE="${TMPDIR:-/tmp}/claude_beep_enabled_session"
fi

check_enabled() {
    # Returns 0 if beeping is enabled, 1 if disabled
    # DEFAULT: enabled (beeping on unless explicitly disabled)
    if [ -f "$STATE_FILE" ]; then
        if grep -q "disabled" "$STATE_FILE" 2>/dev/null; then
            return 1
        else
            return 0
        fi
    else
        return 0
    fi
}

enable() {
    echo "enabled" > "$STATE_FILE"
    echo "✅ Beep notifications enabled for this session."
}

disable() {
    echo "disabled" > "$STATE_FILE"
    echo "❌ Beep notifications disabled for this session."
}

status() {
    if check_enabled; then
        echo "🔔 Beep notifications: ENABLED (default: on)"
    else
        echo "🔕 Beep notifications: DISABLED (default: on)"
    fi
}

toggle() {
    if check_enabled; then
        disable
    else
        enable
    fi
}

# Main execution
case "${1:-}" in
    enable|on)
        enable
        ;;
    disable|off)
        disable
        ;;
    status)
        status
        ;;
    toggle|"")
        toggle
        ;;
    check)
        # Silent check for use by hooks
        check_enabled
        exit $?
        ;;
    *)
        echo "Usage: $0 {enable|on|disable|off|status|toggle|check}"
        echo ""
        echo "Commands:"
        echo "  enable/on    - Enable beep notifications for this session"
        echo "  disable/off  - Disable beep notifications for this session"
        echo "  status       - Show current beep state (default: enabled)"
        echo "  toggle       - Toggle current state (default if no args)"
        echo "  check        - Silent check (for hooks), returns 0 if enabled"
        echo ""
        echo "Default behavior: Beeping is ENABLED unless explicitly disabled"
        exit 1
        ;;
esac
