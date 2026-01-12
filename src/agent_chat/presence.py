"""Presence tracking for agent-chat."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from filelock import FileLock

PRESENCE_FILE = Path.home() / ".agent-chat" / "presence.json"
PRESENCE_LOCK = Path.home() / ".agent-chat" / "presence.json.lock"


def load_presence() -> dict:
    """Load presence data from file."""
    if not PRESENCE_FILE.exists():
        return {"agents": {}}
    try:
        return json.loads(PRESENCE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"agents": {}}


def save_presence(data: dict) -> None:
    """Save presence data to file."""
    PRESENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRESENCE_FILE.write_text(json.dumps(data, indent=2))


def update_presence(nick: str, status: str, message: str = "") -> dict:
    """Update presence for an agent (with file locking for multi-agent safety)."""
    with FileLock(PRESENCE_LOCK, timeout=5):
        data = load_presence()
        data["agents"][nick] = {
            "status": status,
            "message": message,
            "last_seen": datetime.now().isoformat(),
            "cwd": os.getcwd()
        }
        save_presence(data)
        return data["agents"][nick]


def get_presence(nick: Optional[str] = None) -> dict:
    """Get presence for one or all agents."""
    data = load_presence()
    if nick:
        return data["agents"].get(nick, {})
    return data["agents"]


def clear_stale(max_age_minutes: int = 15) -> int:
    """Remove agents not seen in max_age_minutes (with file locking)."""
    with FileLock(PRESENCE_LOCK, timeout=5):
        data = load_presence()
        now = datetime.now()
        cutoff = timedelta(minutes=max_age_minutes)

        stale_nicks = [
            nick for nick, info in data["agents"].items()
            if now - datetime.fromisoformat(info["last_seen"]) > cutoff
        ]

        for nick in stale_nicks:
            del data["agents"][nick]

        if stale_nicks:
            save_presence(data)

        return len(stale_nicks)
