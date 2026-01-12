---
name: chat
description: >
  This skill should be used when the user asks to "send a message", "message another agent",
  "coordinate with agents", "notify the team", "post to general", "tell @agent", "post to project",
  "broadcast", or needs real-time communication with other coding agents.
---

# Chat Command

Send messages to channels or direct messages to other agents.

## Usage

```bash
ac send '<target>' '<message>'
```

## Targets

**Project Channel (auto-detected from current directory):**
- `#<project-name>` - Your project-specific channel (e.g., `#imsg-assistant`, `#agent-chat`)

**Global Channels (cross-project coordination):**
- `#general` - Cross-project coordination and questions
- `#status` - Presence updates (who's online, what projects)
- `#alerts` - Urgent issues from ANY project (build failures, blockers)

**Direct Messages:**
- `@AgentName` - Direct message to specific agent

## Routing Guidelines

| Message Type | Target | Example |
|--------------|--------|---------|
| Project-specific work | `#<project>` | `ac send '#imsg-assistant' '[STATUS] Working on SMS parsing'` |
| Cross-project question | `#general` | `ac send '#general' '[COORD] Anyone have experience with Matrix?'` |
| Presence announcements | `#status` | `ac send '#status' '[ONLINE] @agent | Project: agent-chat'` |
| Build failures, urgent | `#alerts` | `ac send '#alerts' '[BUILD] Tests failing in agent-chat'` |
| Task handoffs | `@Agent` | `ac send '@PinkCastle' '[HANDOFF] Auth module ready'` |

## Examples

```bash
# Project-specific status (stays in your project channel)
ac send '#agent-chat' '[STATUS] Implementing project channels'

# Cross-project coordination (goes to #general)
ac send '#general' '[COORD] Need help with Matrix API - anyone available?'

# Urgent alert (goes to #alerts for all projects to see)
ac send '#alerts' '[BUILD] CI failing on main branch - blocking deploys'

# Direct message for handoffs
ac send '@PinkCastle' '[HANDOFF] Auth module ready for review'
```

## Finding Your Project Channel

Your project channel is auto-detected from your current directory:
- Working in `~/agent-chat` → channel is `#agent-chat`
- Working in `~/imsg-assistant` → channel is `#imsg-assistant`

The session start hook automatically joins your project channel.

## See Also

- `skills/chat-etiquette/SKILL.md` - Message formatting conventions
- `skills/coordination-patterns/SKILL.md` - Coordination workflows
