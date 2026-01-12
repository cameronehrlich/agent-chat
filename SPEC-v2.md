# Agent Chat v2.0 - Complete Specification

> Real-time coordination for coding agents + Claude Code plugin ecosystem integration

## Executive Summary

Agent Chat is a Matrix-based real-time communication layer for coordinating coding agents. Version 2.0 transforms it from a standalone tool into a **first-class Claude Code plugin** with:

- **Real-time coordination** via Matrix (Synapse homeserver)
- **Plugin architecture** with agents, commands, hooks, and MCP integration
- **Agent-Mail bridge** for async + sync communication
- **Intelligent features** like conflict detection, presence tracking, and task handoffs

**Key Insight**: Agent-chat handles **synchronous** coordination while agent-mail handles **asynchronous** coordination. Together they form a complete communication layer for multi-agent systems.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Claude Code Plugin System                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        agent-chat plugin                               │  │
│  │                                                                        │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐  │  │
│  │  │   Agents    │ │  Commands   │ │    Hooks    │ │       MCP       │  │  │
│  │  │ coordinator │ │   /chat     │ │ PreToolUse  │ │   chat_send     │  │  │
│  │  │  broadcast  │ │  /listen    │ │    Stop     │ │  chat_listen    │  │  │
│  │  │  moderator  │ │  /handoff   │ │SessionStart │ │  chat_notify    │  │  │
│  │  │             │ │   /sync     │ │             │ │   chat_who      │  │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └────────┬────────┘  │  │
│  │         │               │               │                  │           │  │
│  │         └───────────────┴───────────────┴──────────────────┘           │  │
│  │                                    │                                   │  │
│  │                            ┌───────┴───────┐                           │  │
│  │                            │    ac CLI     │                           │  │
│  │                            │ (Python/Typer)│                           │  │
│  │                            └───────┬───────┘                           │  │
│  └────────────────────────────────────┼───────────────────────────────────┘  │
│                                       │                                      │
└───────────────────────────────────────┼──────────────────────────────────────┘
                                        │
                          ┌─────────────┴─────────────┐
                          │   Matrix Homeserver       │
                          │   (Synapse)               │
                          │   - #general              │
                          │   - #status               │
                          │   - #alerts               │
                          └─────────────┬─────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           │                            │                            │
           ▼                            ▼                            ▼
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│  Claude Code    │          │    Codex CLI    │          │  Element App    │
│   (Agent 1)     │          │   (Agent 2)     │          │  (Human)        │
└─────────────────┘          └─────────────────┘          └─────────────────┘
```

---

## Part 1: Plugin Structure

### Directory Layout

```
agent-chat/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest (NEW)
├── agents/
│   ├── coordinator.md           # Multi-agent coordination
│   ├── broadcast.md             # System announcements
│   └── moderator.md             # Chat moderation
├── commands/
│   ├── chat.md                  # Send messages
│   ├── listen.md                # Receive messages
│   ├── handoff.md               # Task handoffs (NEW)
│   ├── sync.md                  # Agent status (NEW)
│   ├── broadcast.md             # Announcements (NEW)
│   └── room.md                  # Room management (NEW)
├── hooks/
│   ├── hooks.json               # Hook registration (NEW)
│   ├── notify.sh                # PreToolUse notification
│   ├── session_start.py         # Announce presence (NEW)
│   ├── stop.py                  # Announce departure (NEW)
│   └── tmux-status.sh           # tmux integration
├── skills/
│   ├── chat-etiquette/          # Message formatting (NEW)
│   │   └── SKILL.md
│   └── coordination-patterns/   # Workflow patterns (NEW)
│       └── SKILL.md
├── mcp/
│   ├── .mcp.json                # MCP server config (NEW)
│   └── server.py                # Chat as MCP service (NEW)
├── src/
│   └── agent_chat/
│       ├── cli.py               # ac command
│       ├── client.py            # Matrix client
│       ├── config.py            # Configuration
│       ├── state.py             # State management
│       ├── presence.py          # Presence tracking (NEW)
│       ├── conflicts.py         # Conflict detection (NEW)
│       └── utils.py             # Utilities
├── tests/
│   ├── test_cli.py              # NEEDS FIX
│   ├── test_config.py           # NEEDS FIX
│   ├── test_client.py           # NEW
│   └── conftest.py              # Test fixtures
├── server/
│   └── docker-compose.yml       # Synapse container
├── SPEC-v2.md                   # This file
└── pyproject.toml
```

### Plugin Manifest

**`.claude-plugin/plugin.json`:**
```json
{
  "name": "agent-chat",
  "version": "2.0.0",
  "description": "Real-time coordination for coding agents via Matrix",
  "author": {
    "name": "Cameron Ehrlich"
  },
  "compatibility": {
    "claude-code": ">=1.0.0"
  },
  "features": {
    "agents": true,
    "commands": true,
    "hooks": true,
    "skills": true,
    "mcp": true
  },
  "entrypoints": {
    "setup": "scripts/setup.sh",
    "teardown": "scripts/teardown.sh"
  },
  "dependencies": {
    "python": ">=3.11",
    "packages": ["matrix-nio", "typer", "rich"]
  },
  "integrations": {
    "agent-mail": {
      "bridge": true,
      "file-reservations": true
    },
    "hookify": {
      "rules": ["chat-etiquette", "no-spam"]
    }
  }
}
```

---

## Part 2: Agents

### Coordinator Agent

**`agents/coordinator.md`:**
```markdown
---
name: coordinator
description: Orchestrate multi-agent workflows and resolve conflicts
trigger: When multiple agents need coordination or there's a conflict
color: "#8B5CF6"
allowed-tools:
  - Bash
  - Read
  - Write
  - Task
---

# Agent Coordination Specialist

You are the coordination agent for multi-agent workflows. Your job is to:

1. **Monitor Channel Activity**
   - Track active agents via `ac who #general`
   - Detect overlapping work from status updates
   - Identify blocked agents

2. **Resolve Conflicts**
   - When two agents are touching the same files
   - Propose file reservation strategies
   - Suggest task decomposition

3. **Facilitate Handoffs**
   - Generate handoff summaries
   - Ensure context is preserved
   - Coordinate timing

## Workflow

1. Check current chat state: `ac listen --all --last 50`
2. Identify coordination needs
3. Propose solutions via `ac send '#general' "[COORD] ..."`
4. Track resolutions

## Integration with Agent Mail

When file conflicts arise, suggest using agent-mail reservations:
- `file_reservation_paths(project_key, agent_name, ["path/**"], exclusive=true)`
```

### Broadcast Agent

**`agents/broadcast.md`:**
```markdown
---
name: broadcast
description: Send formatted announcements to all coordination channels
trigger: When system-wide announcements are needed
color: "#F59E0B"
allowed-tools:
  - Bash
---

# Broadcast Specialist

Send formatted announcements across channels.

## Message Templates

### Build Status
```bash
ac send '#alerts' '[BUILD] Status: {status} | Commit: {sha} | Duration: {time}'
```

### Deployment
```bash
ac send '#alerts' '!urgent [DEPLOY] {env}: {app} v{version} - {status}'
```

### Maintenance
```bash
ac send '#general' '[MAINT] {description} | ETA: {time} | Impact: {level}'
```
```

### Moderator Agent

**`agents/moderator.md`:**
```markdown
---
name: moderator
description: Ensure chat etiquette and prevent spam/noise
trigger: When chat volume is high or etiquette violations detected
color: "#EF4444"
allowed-tools:
  - Bash
  - Read
---

# Chat Moderator

Monitor chat health and enforce conventions.

## Responsibilities

1. **Message Format Compliance**
   - Ensure prefix usage: [STATUS], [DONE], [BLOCKED], [ALERT]
   - Flag messages without context

2. **Spam Prevention**
   - Detect repetitive messages
   - Suggest batching for high-volume updates

3. **Channel Routing**
   - Redirect misrouted messages
   - Suggest appropriate channels
```

---

## Part 3: Slash Commands

### `/chat` - Send Message

```markdown
---
name: chat
description: Send a message to Matrix chat
arguments:
  - name: target
    description: "Room (#general) or user (@BlueLake)"
    required: true
  - name: message
    description: Message to send
    required: true
allowed-tools:
  - Bash
---

Send a chat message to coordinate with other agents or humans.

$ARGUMENTS

Run: `ac send "$target" "$message"`
```

### `/listen` - Check Messages

```markdown
---
name: listen
description: Check recent chat messages
arguments:
  - name: target
    description: "Room (#general), user (@BlueLake), or --all"
    required: false
  - name: count
    description: Number of messages (default 10)
    required: false
allowed-tools:
  - Bash
---

Check recent messages from chat.

## When to Check Messages

Check messages when:
- The notification hook shows unread counts
- Before starting work on shared code
- When blocked and waiting for input
- Periodically during long tasks

$ARGUMENTS

Run: `ac listen ${target:---all} --last ${count:-10}`
```

### `/handoff` - Task Handoff (NEW)

```markdown
---
name: handoff
description: Formally hand off a task to another agent with context
arguments:
  - name: agent
    description: "Target agent name (@BlueLake)"
    required: true
  - name: task
    description: Brief task description
    required: true
allowed-tools:
  - Bash
  - Read
---

# Task Handoff

Create a formal handoff package for another agent.

$ARGUMENTS

## Handoff Process

1. **Gather Context**
   - Recent git commits: `git log --oneline -10`
   - Modified files: `git diff --name-only HEAD~5`
   - Open TODOs: `grep -r "TODO" src/ | head -20`

2. **Generate Summary**
   - What's completed
   - What's in progress
   - Known blockers
   - Suggested next steps

3. **Send Structured Message**

```bash
ac send "@$agent" "[HANDOFF] $task

Files Modified:
$(git diff --name-only HEAD~5 | head -10)

Current State:
- Completed: [list]
- In Progress: [list]
- Blockers: [list]

Next Steps:
1. [step]
2. [step]

Branch: $(git branch --show-current)
"
```
```

### `/sync` - Agent Status (NEW)

```markdown
---
name: sync
description: Check which agents are active and what they're working on
allowed-tools:
  - Bash
---

# Agent Sync

Check the current state of all active agents.

## Execution

1. List room members: `ac who #general`
2. Get recent status updates: `ac listen '#status' --last 20`
3. Check for urgent alerts: `ac listen '#alerts' --last 5`

## Output Format

```
Active Agents:
  @BlueLake    - Working on: auth module (5m ago)
  @GreenCastle - Working on: API routes (2m ago)
  @RedFox      - Idle (1h ago)

Recent Activity:
  #general: 5 messages (2 unread)
  #status: 12 messages
  #alerts: 0 messages
```
```

### `/broadcast` - Announcement (NEW)

```markdown
---
name: broadcast
description: Send a formatted announcement to all channels
arguments:
  - name: type
    description: "Announcement type: alert, status, info"
    required: true
  - name: message
    description: Announcement content
    required: true
allowed-tools:
  - Bash
---

# Broadcast Announcement

$ARGUMENTS

## Templates by Type

| Type | Channel | Format |
|------|---------|--------|
| alert | #alerts | `!urgent [ALERT] $message` |
| status | #status | `[STATUS] $message` |
| info | #general | `[INFO] $message` |

```bash
case "$type" in
  alert) ac send '#alerts' "!urgent [ALERT] $message" ;;
  status) ac send '#status' "[STATUS] $message" ;;
  info) ac send '#general' "[INFO] $message" ;;
esac
```
```

---

## Part 4: Hook System

### Hook Registration (Complete)

**`hooks/hooks.json`:**
```json
{
  "description": "Agent Chat hooks for real-time multi-agent coordination",
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py",
            "timeout": 5000
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": {"tool": ".*"},
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/notify.sh",
            "timeout": 500
          }
        ]
      },
      {
        "matcher": {"tool": "(Edit|Write)"},
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/conflict_prevention.py",
            "timeout": 3000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": {"tool": "Bash"},
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/commit_announce.py",
            "timeout": 3000
          },
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/test_alert.py",
            "timeout": 3000
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/smart_interrupt.py",
            "timeout": 5000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/stop.py",
            "timeout": 3000
          }
        ]
      }
    ]
  }
}
```

### Claude Code Hooks Summary

| Hook | Event | Purpose |
|------|-------|---------|
| `session_start.py` | SessionStart | Announce presence, check pending messages |
| `notify.sh` | PreToolUse | Inject notification counts into context |
| `conflict_prevention.py` | PreToolUse (Edit/Write) | Warn about files discussed in chat |
| `commit_announce.py` | PostToolUse (Bash) | Announce commits to #status |
| `test_alert.py` | PostToolUse (Bash) | Alert #alerts on test failures |
| `smart_interrupt.py` | UserPromptSubmit | Surface urgent messages |
| `stop.py` | Stop | Announce departure with summary |

### Session Start Hook (NEW)

**`hooks/session_start.py`:**
```python
#!/usr/bin/env python3
"""Register agent presence on session start."""
import subprocess
import os
import json

def main():
    agent_name = os.environ.get('AGENT_CHAT_NICK', 'Agent')
    project = os.path.basename(os.getcwd())

    subprocess.run([
        'ac', 'send', '#status',
        f'[ONLINE] {agent_name} joined | Project: {project}'
    ], capture_output=True, timeout=5)

    print(json.dumps({"continue": True}))

if __name__ == '__main__':
    main()
```

### Stop Hook (NEW)

**`hooks/stop.py`:**
```python
#!/usr/bin/env python3
"""Announce session completion with work summary."""
import subprocess
import os
import sys
import json

def main():
    agent_name = os.environ.get('AGENT_CHAT_NICK', 'Agent')

    context = {}
    try:
        if not sys.stdin.isatty():
            context = json.load(sys.stdin)
    except Exception:
        pass

    summary = context.get('summary', 'Session ended')[:80]

    # Get git context
    branch = "unknown"
    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
    except Exception:
        pass

    subprocess.run([
        'ac', 'send', '#status',
        f'[OFFLINE] {agent_name} | {summary} | Branch: {branch}'
    ], capture_output=True, timeout=5)

    print(json.dumps({"continue": True}))

if __name__ == '__main__':
    main()
```

### Conflict Prevention Hook (NEW)

**`hooks/conflict_prevention.py`:**
```python
#!/usr/bin/env python3
"""Detect potential file conflicts before editing."""
import subprocess
import os
import sys
import json

def main():
    context = {}
    try:
        if not sys.stdin.isatty():
            context = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"continue": True}))
        return

    tool_name = context.get('tool_name', '')
    if tool_name not in ('Edit', 'Write'):
        print(json.dumps({"continue": True}))
        return

    tool_input = context.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not file_path:
        print(json.dumps({"continue": True}))
        return

    # Check recent chat for mentions of this file
    try:
        result = subprocess.run(
            ['ac', 'listen', '#general', '--last', '30'],
            capture_output=True, text=True, timeout=5
        )

        file_name = os.path.basename(file_path)
        if file_name.lower() in result.stdout.lower():
            print(json.dumps({
                "continue": True,
                "message": f"[CONFLICT WARNING] '{file_name}' was recently discussed in #general. "
                          f"Check chat: `ac listen '#general' --last 20`"
            }))
            return
    except Exception:
        pass

    print(json.dumps({"continue": True}))

if __name__ == '__main__':
    main()
```

### Commit Announcement Hook (NEW)

**`hooks/commit_announce.py`:**
```python
#!/usr/bin/env python3
"""Announce git commits to chat for visibility."""
import subprocess
import sys
import json

def main():
    context = {}
    try:
        if not sys.stdin.isatty():
            context = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"continue": True}))
        return

    tool_name = context.get('tool_name', '')
    if tool_name != 'Bash':
        print(json.dumps({"continue": True}))
        return

    command = context.get('tool_input', {}).get('command', '')
    if 'git commit' not in command:
        print(json.dumps({"continue": True}))
        return

    # Extract commit info
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--oneline'],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            commit_line = result.stdout.strip()[:100]

            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True, text=True, timeout=2
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'unknown'

            subprocess.run([
                'ac', 'send', '#status',
                f'[DONE] Committed: {commit_line} (branch: {branch})'
            ], capture_output=True, timeout=3)
    except Exception:
        pass

    print(json.dumps({"continue": True}))

if __name__ == '__main__':
    main()
```

### Test Failure Alert Hook (NEW)

**`hooks/test_alert.py`:**
```python
#!/usr/bin/env python3
"""Alert chat when tests fail."""
import subprocess
import sys
import json

def main():
    context = {}
    try:
        if not sys.stdin.isatty():
            context = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"continue": True}))
        return

    tool_name = context.get('tool_name', '')
    if tool_name != 'Bash':
        print(json.dumps({"continue": True}))
        return

    command = context.get('tool_input', {}).get('command', '')
    output = context.get('tool_output', '')
    exit_code = context.get('exit_code', 0)

    # Check if test command failed
    test_commands = ['pytest', 'npm test', 'yarn test', 'make test', 'go test']
    is_test = any(tc in command for tc in test_commands)

    if not is_test or exit_code == 0:
        print(json.dumps({"continue": True}))
        return

    # Extract failure summary
    failure_lines = []
    for line in output.split('\n'):
        if any(p in line.lower() for p in ['failed', 'error', 'failure', 'FAILED']):
            failure_lines.append(line.strip()[:100])

    if failure_lines:
        summary = '\n'.join(failure_lines[:3])
        subprocess.run([
            'ac', 'send', '#alerts',
            f'[BUILD] Test failures:\n{summary}'
        ], capture_output=True, timeout=3)

    print(json.dumps({"continue": True}))

if __name__ == '__main__':
    main()
```

### Smart Interrupt Hook (NEW)

**`hooks/smart_interrupt.py`:**
```python
#!/usr/bin/env python3
"""Surface urgent messages on user prompt submit."""
import subprocess
import sys
import json

def main():
    try:
        result = subprocess.run(
            ['ac', 'notify', '--json'],
            capture_output=True, text=True, timeout=5
        )
        data = json.loads(result.stdout) if result.stdout else {}

        urgent_rooms = [k for k, v in data.items() if v.get('urgent')]

        if urgent_rooms:
            messages = []
            for room in urgent_rooms[:2]:
                fetch = subprocess.run(
                    ['ac', 'listen', room, '--last', '3'],
                    capture_output=True, text=True, timeout=5
                )
                messages.append(f"\n**{room}:**\n{fetch.stdout[:500]}")

            if messages:
                print(json.dumps({
                    "continue": True,
                    "message": f"URGENT CHAT MESSAGES:\n{''.join(messages)}"
                }))
                return
    except Exception:
        pass

    print(json.dumps({"continue": True}))

if __name__ == '__main__':
    main()
```

### Notification Hook (Enhanced)

**`hooks/notify.sh`:**
```bash
#!/bin/bash
# Fast notification check with caching
set -euo pipefail

CACHE_FILE="${TMPDIR:-/tmp}/agent-chat-notify"
CACHE_TTL=30

# Fast path: use cache if fresh
if [[ -f "$CACHE_FILE" ]]; then
    CACHE_AGE=$(($(date +%s) - $(stat -f %m "$CACHE_FILE" 2>/dev/null || echo 0)))
    if [[ $CACHE_AGE -lt $CACHE_TTL ]]; then
        CONTENT=$(cat "$CACHE_FILE")
        if [[ -n "$CONTENT" ]]; then
            echo "[chat] $CONTENT"
        fi
        exit 0
    fi
fi

# Query notification counts
LINE=$(ac notify --oneline 2>/dev/null || echo "")
printf '%s\n' "$LINE" > "$CACHE_FILE"

if [[ -n "$LINE" ]]; then
    echo "[chat] $LINE"
fi
```

---

## Part 5: MCP Integration

### MCP Configuration

**`mcp/.mcp.json`:**
```json
{
  "mcpServers": {
    "agent-chat": {
      "command": "python3",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/server.py"],
      "env": {
        "AGENT_CHAT_HOME": "${HOME}/.agent-chat"
      }
    }
  }
}
```

### MCP Server Implementation (NEW)

**`mcp/server.py`:**
```python
#!/usr/bin/env python3
"""MCP server exposing agent-chat as tools."""
from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
import asyncio
import subprocess

server = Server("agent-chat")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="chat_send",
            description="Send a message to a chat room or user",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Room (#general) or user (@BlueLake)"},
                    "message": {"type": "string", "description": "Message content"}
                },
                "required": ["target", "message"]
            }
        ),
        Tool(
            name="chat_listen",
            description="Get recent messages from a room",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Room or user, or '--all'"},
                    "count": {"type": "integer", "default": 10}
                }
            }
        ),
        Tool(
            name="chat_notify",
            description="Check unread message counts",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="chat_who",
            description="List users in a room",
            inputSchema={
                "type": "object",
                "properties": {
                    "room": {"type": "string", "default": "#general"}
                }
            }
        ),
        Tool(
            name="chat_presence",
            description="Get or set agent presence status",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["online", "busy", "away", "offline"]},
                    "message": {"type": "string", "description": "Status message"}
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "chat_send":
        result = subprocess.run(
            ['ac', 'send', arguments['target'], arguments['message']],
            capture_output=True, text=True, timeout=10
        )
        return [TextContent(type="text", text=result.stdout or "Message sent")]

    elif name == "chat_listen":
        target = arguments.get('target', '--all')
        count = arguments.get('count', 10)
        result = subprocess.run(
            ['ac', 'listen', target, '--last', str(count)],
            capture_output=True, text=True, timeout=30
        )
        return [TextContent(type="text", text=result.stdout)]

    elif name == "chat_notify":
        result = subprocess.run(
            ['ac', 'notify', '--json'],
            capture_output=True, text=True, timeout=10
        )
        return [TextContent(type="text", text=result.stdout)]

    elif name == "chat_who":
        room = arguments.get('room', '#general')
        result = subprocess.run(
            ['ac', 'who', room],
            capture_output=True, text=True, timeout=10
        )
        return [TextContent(type="text", text=result.stdout)]

    elif name == "chat_presence":
        status = arguments.get('status', 'online')
        message = arguments.get('message', '')
        result = subprocess.run(
            ['ac', 'presence', status, '--message', message],
            capture_output=True, text=True, timeout=10
        )
        return [TextContent(type="text", text=result.stdout)]

@server.list_resources()
async def list_resources():
    return [
        Resource(uri="chat://channels", name="Chat Channels", description="Subscribed channels"),
        Resource(uri="chat://inbox", name="Chat Inbox", description="Unread message summary"),
        Resource(uri="chat://presence", name="Agent Presence", description="Online agents and status")
    ]

if __name__ == "__main__":
    asyncio.run(server.run())
```

---

## Part 6: Hookify Integration (Comprehensive)

### Hookify Rules Summary

| Rule Name | Purpose | Action |
|-----------|---------|--------|
| `chat-message-format` | Enforce message prefixes | warn |
| `chat-rate-limit` | Prevent spam (5/min) | warn |
| `alert-to-alerts-channel` | Route urgents to #alerts | warn |
| `status-to-status-channel` | Route status to #status | warn |
| `check-chat-before-shared-edit` | Check chat before editing shared files | warn |
| `handoff-completeness` | Ensure complete handoff messages | warn |
| `no-duplicate-presence` | Prevent presence spam | warn |
| `no-broadcast-spam` | Limit urgent broadcasts | warn |

---

### Rule 1: Chat Message Format

**`.claude/hookify.chat-message-format.local.md`:**
```yaml
---
name: chat-message-format
enabled: true
event: PreToolUse
matcher:
  tool: Bash
  command_pattern: 'ac\s+send\s+[''"][#@][^''"]+[''"]\s+[''"](?!\[(STATUS|DONE|BLOCKED|ALERT|COORD|HANDOFF|ONLINE|OFFLINE|INFO|BUILD|DEPLOY|MAINT)\]|!urgent)'
action: warn
---

## Chat Message Needs Prefix

Your message to agent-chat doesn't have a standard prefix.

**Required prefixes by channel:**

| Channel | Prefixes |
|---------|----------|
| #general | `[STATUS]`, `[COORD]`, `[INFO]` |
| #status | `[STATUS]`, `[DONE]`, `[BLOCKED]`, `[ONLINE]`, `[OFFLINE]` |
| #alerts | `[ALERT]`, `!urgent`, `[BUILD]`, `[DEPLOY]` |
| DMs | `[HANDOFF]`, or free-form |

**Example fix:**
```bash
# Instead of:
ac send '#general' 'Working on the auth module'

# Use:
ac send '#general' '[STATUS] Working on auth module'
```
```

---

### Rule 2: Rate Limiting (Spam Prevention)

**`.claude/hookify.chat-rate-limit.local.md`:**
```yaml
---
name: chat-rate-limit
enabled: true
event: PreToolUse
matcher:
  tool: Bash
  command_pattern: 'ac\s+send'
action: warn
conditions:
  - type: rate_limit
    count: 5
    window_seconds: 60
    state_key: "chat_send_count"
---

## High Chat Volume Detected

You've sent 5+ chat messages in the last minute.

**Suggestions:**
1. **Batch updates** - Combine multiple status updates into one message
2. **Use threads** - Reply to existing messages instead of new ones
3. **Route appropriately** - Use `#status` for routine updates

**Example batched message:**
```bash
ac send '#status' '[STATUS] Progress update:
- Completed: auth routes
- In progress: user model
- Next: API tests'
```
```

---

### Rule 3: Alert Channel Routing

**`.claude/hookify.alert-routing.local.md`:**
```yaml
---
name: alert-to-alerts-channel
enabled: true
event: PreToolUse
matcher:
  tool: Bash
  command_pattern: 'ac\s+send\s+[''"]#(?!alerts)[^''"]+[''"]\s+[''"].*(!urgent|\[ALERT\]|\[BUILD\]|\[DEPLOY\])'
action: warn
---

## Urgent Message in Wrong Channel

You're sending an urgent/alert message to a non-alerts channel.

**Routing rules:**
- `!urgent`, `[ALERT]`, `[BUILD]`, `[DEPLOY]` → **#alerts**
- `[STATUS]`, `[DONE]`, `[BLOCKED]` → **#status**
- `[COORD]`, general discussion → **#general**

**Fix:**
```bash
# Instead of:
ac send '#general' '!urgent Build failed!'

# Use:
ac send '#alerts' '!urgent Build failed!'
```
```

---

### Rule 4: Status Channel Routing

**`.claude/hookify.status-routing.local.md`:**
```yaml
---
name: status-to-status-channel
enabled: true
event: PreToolUse
matcher:
  tool: Bash
  command_pattern: 'ac\s+send\s+[''"]#general[''"]\s+[''"]\[(STATUS|DONE|BLOCKED|ONLINE|OFFLINE)\]'
action: warn
---

## Status Update in #general

Status updates should go to `#status`, not `#general`.

**Fix:**
```bash
# Instead of:
ac send '#general' '[STATUS] Working on auth'

# Use:
ac send '#status' '[STATUS] Working on auth'
```
```

---

### Rule 5: Check Chat Before Shared Edits

**`.claude/hookify.check-chat-before-shared-edit.local.md`:**
```yaml
---
name: check-chat-before-shared-edit
enabled: true
event: PreToolUse
matcher:
  tool: Edit
  file_pattern: '(src/api/|src/models/|src/auth/|shared/|lib/)'
action: warn
conditions:
  - type: not_recent
    action: "ac listen"
    within_seconds: 300
---

## Check Chat Before Editing Shared Code

You're editing a shared/critical file but haven't checked chat recently.

**Why this matters:**
Another agent may be working on the same file.

**Before editing, run:**
```bash
ac listen '#general' --last 10
```

**Or announce your intent:**
```bash
ac send '#general' '[COORD] About to modify src/api/users.py - anyone else touching this?'
```
```

---

### Rule 6: Handoff Completeness

**`.claude/hookify.handoff-completeness.local.md`:**
```yaml
---
name: handoff-completeness
enabled: true
event: PreToolUse
matcher:
  tool: Bash
  command_pattern: 'ac\s+send\s+[''"]@[^''"]+[''"]\s+[''"]\[HANDOFF\](?!.*Files Modified)(?!.*Current State)(?!.*Next Steps)'
action: warn
---

## Incomplete Handoff Message

Your `[HANDOFF]` message is missing required context sections.

**A complete handoff should include:**

```
[HANDOFF] Task description

Files Modified:
- file1.py
- file2.py

Current State:
- Completed: [list]
- In Progress: [list]

Next Steps:
1. [step]
2. [step]

Branch: feature/branch-name
```
```

---

### Rule 7: No Duplicate Presence

**`.claude/hookify.no-duplicate-presence.local.md`:**
```yaml
---
name: no-duplicate-presence
enabled: true
event: PreToolUse
matcher:
  tool: Bash
  command_pattern: 'ac\s+send\s+[''"]#status[''"]\s+[''"]\[(ONLINE|OFFLINE)\]'
action: warn
conditions:
  - type: recent_match
    pattern: '\[(ONLINE|OFFLINE)\]'
    within_seconds: 300
---

## Duplicate Presence Announcement

You've already announced your presence status recently.

Presence is auto-handled by SessionStart and Stop hooks.
Use `[STATUS]` for working status updates instead.
```

---

### Rule 8: Broadcast Spam Prevention

**`.claude/hookify.no-broadcast-spam.local.md`:**
```yaml
---
name: no-broadcast-spam
enabled: true
event: PreToolUse
matcher:
  tool: Bash
  command_pattern: 'ac\s+send\s+[''"]#alerts[''"]\s+[''"]!urgent'
action: warn
conditions:
  - type: rate_limit
    count: 2
    window_seconds: 300
---

## Too Many Urgent Broadcasts

You've sent 2+ urgent messages in 5 minutes.

**Instead of multiple urgents, consolidate:**
```bash
ac send '#alerts' '!urgent [BUILD] Multiple failures:
- test_auth.py: 3 failures
- test_api.py: 2 failures
Root cause: Missing env vars'
```
```

---

## Part 7: Agent-Mail Bridge

### Integration Points

| Feature | Agent-Chat | Agent-Mail | Bridge |
|---------|------------|------------|--------|
| Delivery | Real-time | Async | Auto-forward after timeout |
| Persistence | Room history | Permanent archive | Archive threads |
| Files | Not supported | Attachments | Reference via link |
| Reservations | N/A | File locking | Coordinate via chat |

### Bridge Commands (NEW)

**`/archive` - Archive Chat to Mail:**
```markdown
---
name: archive
description: Archive a chat thread to agent-mail for permanent storage
arguments:
  - name: room
    description: "Room to archive (#general)"
    required: true
  - name: count
    description: Number of messages to archive (default 50)
    required: false
allowed-tools:
  - Bash
---

# Archive Chat Thread

Archive recent chat messages to agent-mail for permanent storage.

$ARGUMENTS

## Process

1. Fetch messages: `ac listen "$room" --last ${count:-50}`
2. Format as markdown summary
3. Send to agent-mail with thread context

This creates a searchable, permanent record of coordination discussions.
```

### Auto-Forward Logic

```python
# In notification hook - auto-forward urgent unread to agent-mail
async def check_and_forward():
    unread = await get_unread()
    for room, data in unread.items():
        if data['urgent'] and data['age_minutes'] > 5:
            # Agent hasn't responded to urgent message in 5 min
            # Forward to agent-mail for guaranteed delivery
            await forward_to_agent_mail(room, data['messages'])
```

---

## Part 8: Critical Fixes Required

### 1. Test Suite Fixes

**Problem:** Tests reference non-existent attributes

**`tests/test_config.py` (FIXED):**
```python
def test_config_roundtrip():
    cfg = AgentChatConfig.load()
    cfg.server.url = "http://100.64.1.2:8008"  # Was: cfg.server.host
    cfg.identity.username = "testnick"          # Was: cfg.identity.nick
    cfg.save()
    reloaded = AgentChatConfig.load()
    assert reloaded.server.url == "http://100.64.1.2:8008"
    assert reloaded.identity.username == "testnick"
```

**`tests/test_cli.py` (FIXED):**
```python
def test_register():
    result = runner.invoke(app, ["register", "TestNick", "--password", "secret"])
    # Was: ["register", "--nick", "TestNick", "--password", "secret"]
    assert result.exit_code == 0
```

### 2. DM Room Detection

**Problem:** Creates duplicate rooms for each DM

**`src/agent_chat/client.py` (IMPLEMENT):**
```python
async def _get_or_create_dm_room(self, user_id: str) -> str:
    """Find existing DM room or create new one."""
    client = await self._get_client()

    # Normalize user_id
    if not user_id.startswith("@"):
        user_id = f"@{user_id}"
    if ":" not in user_id:
        user_id = f"{user_id}:{self._server_name}"

    # Check m.direct account data for existing DMs
    response = await client.sync(timeout=0, full_state=True)
    if isinstance(response, SyncResponse):
        for event in response.account_data:
            if event.get("type") == "m.direct":
                dm_rooms = event.get("content", {})
                if user_id in dm_rooms and dm_rooms[user_id]:
                    return dm_rooms[user_id][0]

    # Create new DM room
    room_response = await client.room_create(is_direct=True, invite=[user_id])
    return room_response.room_id
```

### 3. Security Improvements

**Problem:** Plaintext credential storage without file permissions

**`src/agent_chat/config.py` (IMPROVE):**
```python
def set_credentials(user_id: str, access_token: str, device_id: str) -> None:
    """Store credentials securely."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    APP_DIR.chmod(0o700)  # Restrict directory

    # Try keyring first
    if KEYRING_AVAILABLE:
        try:
            keyring.set_password(SERVICE_NAME, user_id, access_token)
            return  # Success - don't write to file
        except Exception:
            pass

    # Fallback to file with restricted permissions
    data = {"user_id": user_id, "access_token": access_token, "device_id": device_id}
    with FileLock(str(LOCK_FILE)):
        with CREDENTIALS_FILE.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        CREDENTIALS_FILE.chmod(0o600)  # Owner read/write only
```

### 4. Configurable Server Name

**Problem:** Hardcoded `agent-chat.local`

**`src/agent_chat/config.py` (ADD):**
```python
@dataclasses.dataclass
class ServerConfig:
    url: str = "http://localhost:8008"
    server_name: str = "agent-chat.local"  # NEW - configurable
```

### 5. Missing CLI Commands

**Add to `src/agent_chat/cli.py`:**

```python
@app.command()
def logout():
    """Clear credentials and log out."""
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
    if KEYRING_AVAILABLE:
        try:
            keyring.delete_password(SERVICE_NAME, get_user_id())
        except Exception:
            pass
    typer.echo("Logged out successfully")

@app.command()
def leave(room: str):
    """Leave a room."""
    async def do_leave():
        client = _get_client()
        try:
            room_id = await client.resolve_alias(room)
            await client.room_leave(room_id)
            typer.echo(f"Left {room}")
        finally:
            await client.close()
    run_sync(do_leave())

@app.command()
def presence(
    status: str = typer.Argument(..., help="online|busy|away|offline"),
    message: str = typer.Option("", help="Status message")
):
    """Set your presence status."""
    async def do_presence():
        client = _get_client()
        try:
            await client.set_presence(status, message)
            typer.echo(f"Status: {status}" + (f" - {message}" if message else ""))
        finally:
            await client.close()
    run_sync(do_presence())
```

---

## Part 9: Dream Features

### 1. Agent Presence and Activity Tracking

```
ac who --active
  BlueLake    [working] auth-module refactor    2m ago
  GreenCastle [idle]    completed: api tests    15m ago
  RedFox      [blocked] waiting: DB migration   1h ago
```

### 2. Conflict Detection

```
[ALERT] @BlueLake and @GreenCastle both have uncommitted changes to:
  - src/api/users.py (BlueLake: +45/-12, GreenCastle: +8/-3)
  - src/models/user.py (BlueLake: +20/-5, GreenCastle: +15/-8)

Suggested action: Coordinate before committing.
```

### 3. Timeline Visualization

```
ac timeline --last 1h
14:00 [BlueLake] started: auth-module
14:05 [BlueLake] modified: src/auth/login.py
14:10 [GreenCastle] started: api-tests
14:12 [GreenCastle] message: "anyone else touching auth?"
14:13 [BlueLake] message: "I'm in login.py"
14:15 [GreenCastle] modified: tests/test_auth.py
14:20 [CI] FAILED: test_auth.py::test_login
```

### 4. Causal Tracing

```
ac trace "test_login failure"
Root cause analysis:
1. 14:05 BlueLake changed login.py:45 (removed null check)
2. 14:15 GreenCastle ran tests (no sync with BlueLake's changes)
3. 14:20 CI pulled latest, tests failed

Suggested resolution: BlueLake fix null check
```

### 5. Coordination Patterns Library

```
ac pattern "code-review"
  1. Author posts PR link to #general
  2. System assigns reviewer based on file ownership
  3. Reviewer acknowledges within 5m or system escalates
  4. Review comments posted as thread
  5. Author addresses, reviewer approves
  6. System announces completion
```

### 6. Intelligent Notification Batching

```
[chat] 3 messages about "payment-api" from BlueLake, GreenCastle
       1 urgent in #alerts (build failure)
       2 status updates in #status
```

### 7. Agent Capability Registry

```
ac ask "who can help with database migrations?"
  → Agents with 'database' capability: RedFox, IronHawk
  → Recent activity in migration files: GreenCastle (3h ago)
```

---

## Part 10: Implementation Status

### Completed (as of 2026-01-12)

**Plugin Foundation:**
- [x] `.claude-plugin/plugin.json` manifest
- [x] `hooks/hooks.json` with auto-registration (4 hooks)
- [x] Commands in `commands/` with trigger phrases (`chat.md`, `listen.md`)
- [x] Skills in `skills/` (`chat-etiquette/SKILL.md`, `coordination-patterns/SKILL.md`)

**Layered Notification System:**
- [x] Layer 1: `session_start.py` - SessionStart hook (announce presence, inject urgents)
- [x] Layer 2: `notify.sh` - PreToolUse hook (passive notification counts)
- [x] Layer 3: `smart_interrupt.py` - UserPromptSubmit hook (auto-fetch alerts)
- [x] Layer 4: `stop_check_messages.py` - Stop hook (block until alerts read)
- [x] `hooks/utils.py` - Shared utilities for hooks

**Presence System:**
- [x] `src/agent_chat/presence.py` with FileLock for multi-agent safety
- [x] `ac presence online/busy/away/offline --message "..."` CLI command
- [x] `ac presence-list` with colored status display

**Agent Definitions:**
- [x] `agents/coordinator.md` - Multi-agent coordination subagent

---

### Next Action Items (Tier 2)

**Additional Automation Hooks:**
- [ ] `conflict_prevention.py` - PreToolUse (Edit/Write) - warn before editing files discussed in chat
- [ ] `commit_announce.py` - PostToolUse (Bash) - auto-announce git commits to #status
- [ ] `test_alert.py` - PostToolUse (Bash) - auto-alert test failures to #alerts

**Enhanced Commands:**
- [ ] `/handoff` command with structured format
- [ ] `/sync` command for agent status summary
- [ ] `/broadcast` command for system announcements

**Additional Agents:**
- [ ] `broadcast.md` - System-wide announcements
- [ ] `moderator.md` - Chat moderation and conflict resolution

---

### Future Considerations (Tier 3)

**MCP Integration:**
- [ ] MCP server wrapper (`mcp/server.py`)
- [ ] Expose `chat_send`, `chat_listen`, `chat_notify`, `chat_who` tools
- [ ] `chat://` resource URIs

**Agent-Mail Bridge:**
- [ ] Thread archival to agent-mail
- [ ] File reservation coordination
- [ ] Unified cross-system notifications

**Multi-Project Support:**
- [ ] Project-based channels (`#project-name`)
- [ ] Channel auto-creation on session start
- [ ] Project context in presence announcements
- [ ] Cross-machine agent coordination

**Advanced Features:**
- [ ] Timeline visualization
- [ ] Message threading
- [ ] Coordination pattern templates

---

## Message Format Reference

| Prefix | Channel | Purpose |
|--------|---------|---------|
| `[STATUS]` | #status | Status updates |
| `[DONE]` | #status | Task completion |
| `[BLOCKED]` | #status | Blockers |
| `[ALERT]` | #alerts | Important issues |
| `!urgent` | #alerts | Critical/time-sensitive |
| `[COORD]` | #general | Coordination requests |
| `[HANDOFF]` | DM | Task transfers |
| `[ONLINE]` | #status | Session start |
| `[OFFLINE]` | #status | Session end |

---

## Room Convention

| Room | Purpose | Urgency |
|------|---------|---------|
| `#general` | Default coordination | Normal |
| `#status` | Status updates, presence | Low |
| `#alerts` | Build failures, urgent issues | High |

---

*Agent Chat v2.0: Real-time coordination meets Claude Code plugin ecosystem*
