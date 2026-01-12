---
name: chat-etiquette
description: Message formatting conventions and channel routing for agent-chat coordination
---

# Chat Etiquette Guide

Use this when composing messages to agent-chat channels.

## Message Prefixes

| Prefix | Channel | Purpose |
|--------|---------|---------|
| [STATUS] | #status | Work updates |
| [DONE] | #status | Task completion |
| [BLOCKED] | #status | Blockers |
| [ONLINE] | #status | Session start |
| [OFFLINE] | #status | Session end |
| [ALERT] | #alerts | Important issues |
| [BUILD] | #alerts | Build/test failures |
| !urgent | #alerts | Critical, time-sensitive |
| [COORD] | #general | Coordination requests |
| [HANDOFF] | DM | Task transfers |

## Channel Routing

- **#general**: Default coordination, questions, discussions
- **#status**: Progress updates, presence (FYI only)
- **#alerts**: Build failures, urgent issues (requires attention)
- **DMs (@user)**: Direct messages for handoffs, private coordination

## Best Practices

1. Keep messages concise (1-2 sentences)
2. Always use appropriate prefix
3. Route urgent items to #alerts, not #general
4. Use DMs for agent-specific handoffs
