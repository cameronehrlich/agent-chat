#!/bin/bash
set -euo pipefail

CACHE_FILE="${TMPDIR:-/tmp}/agent-chat-notify"
CACHE_TTL=30

python_age() {
python3 - "$1" <<'PY'
import os, sys, time
path = sys.argv[1]
try:
    mtime = os.path.getmtime(path)
except OSError:
    print(10**9)
    raise SystemExit
print(int(time.time() - mtime))
PY
}

if [[ -f "$CACHE_FILE" ]]; then
    AGE=$(python_age "$CACHE_FILE" 2>/dev/null || echo "$CACHE_TTL")
    if [[ "$AGE" -lt "$CACHE_TTL" ]]; then
        cat "$CACHE_FILE"
        exit 0
    fi
fi

NOTIFY=$(ac notify --json 2>/dev/null || echo "{}")
python3 <<'PY' <<<"$NOTIFY" | tee "$CACHE_FILE" >/dev/null
import json, sys
try:
    data=json.load(sys.stdin)
except Exception:
    print("")
    raise SystemExit
parts=[]
for key, val in data.items():
    count=val.get("count",0)
    if count<=0:
        continue
    suffix="!" if val.get("urgent") else ""
    parts.append(f"{key}({count}{suffix})")
print(f"[chat] {' '.join(parts)}" if parts else "")
PY
