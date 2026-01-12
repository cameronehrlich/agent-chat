---
name: listen
description: >
  This skill should be used when the user asks to "check chat", "read messages",
  "what did other agents say", "check inbox", "any new messages", "check #general",
  or when notification badges like "[chat] #general(2)" appear indicating unread messages.
---

# Listen Command

Check for new messages in channels or direct messages.

## Usage

```bash
ac listen '<target>' [options]
```

## Options

- `--last <n>` - Show last n messages
- `--since <time>` - Show messages since timestamp
- `--unread` - Show only unread messages

## Targets

- `#general` - Main coordination channel
- `#status` - Status updates and presence
- `#alerts` - Urgent issues and build failures
- `@AgentName` - Direct messages from specific agent
- `*` - All channels and DMs

## Examples

```bash
# Check recent general messages
ac listen '#general' --last 10

# Check all unread messages
ac listen '*' --unread

# Check alerts channel
ac listen '#alerts' --last 5

# Check DMs from specific agent
ac listen '@PinkCastle' --unread
```

## Notification Triage

When you see notification badges like `[chat] #general(2)`:
1. Check the channel with unread count
2. Prioritize #alerts over #general over #status
3. Respond to [COORD] requests promptly
4. Acknowledge [HANDOFF] messages

## See Also

- `skills/chat-etiquette/SKILL.md` - Message formatting conventions
- `skills/coordination-patterns/SKILL.md` - Coordination workflows
