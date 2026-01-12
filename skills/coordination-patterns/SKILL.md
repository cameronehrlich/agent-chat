---
name: coordination-patterns
description: Multi-agent coordination workflows and conflict prevention patterns
---

# Coordination Patterns

## File Ownership Check

Before editing shared files:
1. Run `ac listen '#general' --last 10`
2. Check if anyone mentioned the file recently
3. If unclear, post: `ac send '#general' '[COORD] About to edit <file> - conflicts?'`
4. Wait 30-60 seconds for response, then proceed

## Handoff Protocol

When transferring work to another agent:
1. Complete current work to a stable state
2. Commit with descriptive message
3. Send handoff message:
   ```
   ac send '@AgentName' '[HANDOFF] Task: <description>
   Files Modified: <list>
   Current State: <status>
   Next Steps: <what to do>'
   ```

## Conflict Resolution

If two agents are working on the same file:
1. First agent to post in #general has priority
2. Second agent should wait or work on different files
3. Use [COORD] prefix to negotiate

## Status Updates

Post to #status at natural breakpoints:
- `[STATUS] Working on <task>`
- `[DONE] Completed <task>`
- `[BLOCKED] Waiting on <dependency>`
