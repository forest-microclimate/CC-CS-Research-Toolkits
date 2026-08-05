---
description: Toggle audible beep notifications for this Claude Code session
tags: [notifications, beep, hooks, session]
argument-hint: [on|off|status|toggle]
---
<!-- SPDX-License-Identifier: MIT · Copyright (c) 2026 Neill Prohaska <forest.microclimate@gmail.com> -->

# Beep State Management

Control audible beep notifications for this session.

**Available options:**
- `on` or `enable` - Enable beeping
- `off` or `disable` - Disable beeping
- `status` - Show current state
- No argument - Toggle current state

**Executing beep state script:**

Execute the following command and display the output:
```bash
bash "$HOME/.claude/hooks/xbeep/beep-state.sh" $ARGUMENTS
```

Based on the output, briefly confirm the beep notification state change.
