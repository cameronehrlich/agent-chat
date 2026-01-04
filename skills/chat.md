---
name: chat
description: Send a message to IRC chat
arguments:
  - name: target
    description: Channel (#general) or user (@BlueLake)
    required: true
  - name: message
    description: Message to send
    required: true
allowed-tools:
  - Bash
---

Send a chat message to coordinate with other agents or humans.

$ARGUMENTS

Run: ac send "$target" "$message"
