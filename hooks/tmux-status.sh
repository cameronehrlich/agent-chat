#!/bin/bash
NOTIFY=$(ac notify --oneline 2>/dev/null)
if [[ -n "$NOTIFY" ]]; then
    echo "[chat: $NOTIFY]"
fi
