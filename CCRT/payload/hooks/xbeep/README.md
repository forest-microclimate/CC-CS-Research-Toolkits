<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->
# xbeep - Audible Notification System for Claude Code

## Overview

The **xbeep** system provides audible notifications for Claude Code session events:
- **Beep when you submit a prompt** (UserPromptSubmit hook)
- **Beep when Claude finishes responding** (Stop hook)
- **Beep on permission requests** (Notification hook, excludes idle timeouts)

Additionally, the `/xbeep` slash command allows toggling beep notifications on/off for the current session.

## Architecture

### Key Design Decision: Project Settings Override Global Settings

**CRITICAL UNDERSTANDING:** Claude Code's settings hierarchy replaces rather than merges - project settings completely override global settings.

This means:
- If a project defines hooks, ONLY the project's hooks are used
- When project settings exist, the project's hooks fully replace the global ones
- **Solution:** Store files globally, register hooks per-project

### File Storage vs Hook Registration

**Files stored globally:** `~/.claude/hooks/xbeep/`
- ✅ Single source of truth
- ✅ Accessible to sandboxed hooks
- ✅ No file duplication across projects
- ✅ Updates apply to all projects

**Hooks registered per-project:** `.claude/settings.local.json` in each project
- ✅ Each project controls which hooks to use
- ✅ Points to global file location
- ✅ Allows project-specific customization

### Why This Location Works

The `~/.claude/hooks/` directory is:
- ✅ Accessible to sandboxed hooks (verified by system settings.json using this location)
- ✅ Global across all Claude Code projects
- ✅ Standard location matching Claude Code conventions
- ❌ Directories with spaces (like "command helper files") were blocked by sandbox

## Files

### Core Scripts

**beep-state.sh**
- State management for beep enable/disable
- Uses TERM_SESSION_ID for session isolation (not PPID)
- State file: `${TMPDIR:-/tmp}/claude_beep_enabled_${TERM_SESSION_ID}`
- Operations: `enable`, `disable`, `toggle`, `check`, `status`

**user-prompt-submit-beep.sh**
- UserPromptSubmit hook
- Intercepts `/xbeep` commands before they reach Claude (exit code 2)
- Passes all other prompts through (exit code 0)
- Robust JSON parsing with multiple extraction methods

**stop-beep.sh**
- Stop hook
- Plays beep when Claude finishes responding
- Checks if already in stop hook to prevent infinite loops

**notification-beep.sh**
- Notification hook
- Plays beep on permission requests
- Intelligently filters out idle timeout notifications
- Only beeps for: permission/approval requests, questions/choices

### Sound Configuration

All hooks use: `/System/Library/Sounds/Glass.aiff`

To change the sound, edit the `SOUND_FILE` variable in:
- `stop-beep.sh`
- `notification-beep.sh`

## Installation

### For New Projects

To enable xbeep in a new Claude Code project:

1. **Add hooks to project's `.claude/settings.local.json`:**

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/xbeep/user-prompt-submit-beep.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/xbeep/stop-beep.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/xbeep/notification-beep.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

2. **If project already has other hooks**, add xbeep hooks to the existing arrays:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/xbeep/user-prompt-submit-beep.sh",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "bash '/path/to/existing/hook.sh'",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

3. **Ensure `/xbeep` command is defined** in `~/.claude/commands/xbeep.md`:

The command file should reference the global beep-state.sh script:
```bash
bash ~/.claude/hooks/xbeep/beep-state.sh $ARGUMENTS
```

4. **Restart Claude Code** (hooks load at startup)

## Usage

### Slash Command

Control beep notifications for the current session:

```bash
/xbeep on        # Enable beeping
/xbeep off       # Disable beeping
/xbeep toggle    # Toggle current state
/xbeep status    # Show current state
/xbeep           # Same as toggle (no argument)
```

**Note:** State is session-specific - each Claude Code window has independent beep state.

### Hook Behavior

**When beeping is enabled:**
- ✅ Beep when you submit a prompt
- ✅ Beep when Claude finishes responding
- ✅ Beep on permission requests
- ❌ No beep on idle timeouts

**When beeping is disabled:**
- All hooks exit silently (no sounds)

## Debugging

All hooks write debug logs to `/tmp/claude/`:
- `/tmp/claude/hook-debug.log` - user-prompt-submit-beep.sh
- `/tmp/claude/stop-hook-debug.log` - stop-beep.sh
- `/tmp/claude/notification-hook-debug.log` - notification-beep.sh

To monitor in real-time:
```bash
tail -f /tmp/claude/hook-debug.log
```

**Debug log includes:**
- Timestamp of hook execution
- PPID, TERM_SESSION_ID, TMPDIR
- Raw JSON input received
- Parsing decisions
- Whether beep was played

## Troubleshooting

### "/xbeep command not working"

**Check 1:** Hooks defined in project settings?
```bash
grep -A 5 "xbeep" /path/to/project/.claude/settings.local.json
```

**Check 2:** Restart Claude Code after settings changes
- Settings and hooks load at startup only
- Changes take effect in the next new session

**Check 3:** Check debug logs
```bash
cat /tmp/claude/hook-debug.log
```

Look for:
- Is hook being triggered? (check timestamps)
- Is `/xbeep` being detected? (check parsing output)
- What exit code? (2 = blocked, 0 = passed through)

### "Beeps not playing"

**Check 1:** Is beeping enabled for this session?
```bash
/xbeep status
```

**Check 2:** Sound file exists?
```bash
ls -la /System/Library/Sounds/Glass.aiff
```

**Check 3:** Check hook logs for errors
```bash
cat /tmp/claude/stop-hook-debug.log
cat /tmp/claude/notification-hook-debug.log
```

### "Hooks not running"

**Problem:** Hooks may fail if files aren't executable or paths are wrong

**Solution:**
```bash
# Make scripts executable
chmod +x ~/.claude/hooks/xbeep/*.sh

# Verify paths in project settings match actual file locations
ls -la ~/.claude/hooks/xbeep/
```

## Technical Details

### Session Isolation Strategy

**Problem:** Different hook types run in different process contexts
- UserPromptSubmit: PPID = X
- Stop: PPID = Y
- Notification: PPID = Z

**Solution:** Use TERM_SESSION_ID instead of PPID
- Consistent across all hooks in same terminal session
- Fallback to "session" if TERM_SESSION_ID unavailable

**State file pattern:**
```bash
${TMPDIR:-/tmp}/claude_beep_enabled_${TERM_SESSION_ID}
```

### Exit Codes

**UserPromptSubmit hook:**
- `exit 2` - Block prompt from reaching Claude (used for `/xbeep` commands)
- `exit 0` - Pass prompt through to Claude (all other prompts)

**Stop and Notification hooks:**
- Always `exit 0` (passive, never block)

### JSON Parsing Robustness

The user-prompt-submit-beep.sh uses multiple parsing methods for reliability:

```bash
# Method 1: grep + sed
prompt1=$(echo "$input" | grep -o '"prompt":"[^"]*"' | sed 's/"prompt":"\(.*\)"/\1/')

# Method 2: awk
prompt2=$(echo "$input" | awk -F'"prompt":"' '{print $2}' | awk -F'"' '{print $1}')

# Check both results
if [[ "$prompt1" =~ ^/xbeep ]] || [[ "$prompt2" =~ ^/xbeep ]]; then
    # Process /xbeep command
fi
```

This handles various JSON formatting edge cases.

## Development History

### 2025-11-03: Initial Development
- Created beep notification system with session-based state management
- Discovered PPID varies between hook types
- Implemented TERM_SESSION_ID approach for cross-hook state

### 2025-11-05: Migration to Global Location
- **Problem:** Files in project's sandbox broke when moved
- **Attempt 1:** Centralize to `~/.claude/command helper files/xbeep/` (FAILED - sandbox restrictions)
- **Discovery:** Project settings override global settings completely (no merging)
- **Solution:** Files in `~/.claude/hooks/xbeep/`, hooks registered per-project
- **Result:** Successfully working with proper architecture

### Key Lessons Learned

1. **Settings hierarchy is override, not merge**
   - Each project supplies its own hooks rather than inheriting global ones
   - Must register hooks in each project's settings.local.json
   - Files can be global, registration must be per-project

2. **Sandbox-accessible locations**
   - `~/.claude/hooks/` is accessible (proven by system settings.json)
   - Directories with spaces may cause issues
   - Match system patterns for reliability

3. **Hook reload requirements**
   - Hooks load ONCE at Claude Code startup
   - Settings changes require NEW session to take effect
   - Always restart after modifying settings or scripts

4. **Debug logging is essential**
   - Hooks run invisibly - logging is only visibility
   - Log timestamps prove execution
   - Log parsing decisions for troubleshooting

## Version History

### v1.0.0 (2025-11-03)
- Initial implementation with TERM_SESSION_ID approach
- UserPromptSubmit, Stop, and Notification hooks
- Session-based beep state management

### v1.1.0 (2025-11-05)
- Migrated to global location (`~/.claude/hooks/xbeep/`)
- Documented proper architecture (global files + per-project registration)
- Comprehensive README with installation instructions

## License

Provided as-is, no warranty. Free to use, modify, and share.
