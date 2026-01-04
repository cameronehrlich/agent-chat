---
name: listen
description: Check recent chat messages
arguments:
  - name: target
    description: Channel (#general) or --all
    required: false
  - name: count
    description: Number of messages (default 10)
    required: false
allowed-tools:
  - Bash
---

Check recent messages from chat.

$ARGUMENTS

Run: ac listen ${target:---all} --last ${count:-10}
