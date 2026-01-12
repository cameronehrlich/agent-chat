from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from filelock import FileLock

from .config import APP_DIR, DEFAULT_ROOMS

STATE_FILE = APP_DIR / "state.json"
STATE_LOCK = STATE_FILE.with_suffix(".lock")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class LastSeenEntry:
    timestamp: str = field(default_factory=_now_iso)
    msgid: Optional[str] = None

    @classmethod
    def from_raw(cls, raw: object) -> "LastSeenEntry":
        if isinstance(raw, dict):
            return cls(timestamp=str(raw.get("timestamp", _now_iso())), msgid=raw.get("msgid"))
        if isinstance(raw, str):
            return cls(timestamp=raw, msgid=None)
        return cls()

    def to_raw(self) -> Dict[str, str]:
        data = {"timestamp": self.timestamp}
        if self.msgid:
            data["msgid"] = self.msgid
        return data


@dataclass
class AgentChatState:
    channels: Dict[str, LastSeenEntry]
    directs: Dict[str, LastSeenEntry]
    subscribed_channels: list[str]

    @classmethod
    def load(cls) -> "AgentChatState":
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if not STATE_FILE.exists():
            state = cls(
                channels={ch: LastSeenEntry() for ch in DEFAULT_ROOMS},
                directs={},
                subscribed_channels=DEFAULT_ROOMS.copy(),
            )
            state.save()
            return state
        with FileLock(str(STATE_LOCK)):
            data = json.loads(STATE_FILE.read_text())
        last_seen = data.get("last_seen", {})
        channels_raw = last_seen.get("channels", {})
        directs_raw = last_seen.get("direct", {}) or last_seen.get("directs", {})
        channels = {name: LastSeenEntry.from_raw(val) for name, val in channels_raw.items()}
        directs = {name: LastSeenEntry.from_raw(val) for name, val in directs_raw.items()}
        subs = data.get("subscribed_channels", DEFAULT_ROOMS)
        return cls(channels=channels, directs=directs, subscribed_channels=list(subs))

    def save(self) -> None:
        payload = {
            "last_seen": {
                "channels": {name: entry.to_raw() for name, entry in self.channels.items()},
                "direct": {name: entry.to_raw() for name, entry in self.directs.items()},
            },
            "subscribed_channels": self.subscribed_channels,
        }
        with FileLock(str(STATE_LOCK)):
            STATE_FILE.write_text(json.dumps(payload, indent=2))

    def touch_channel(self, name: str, msgid: Optional[str] = None) -> None:
        self.channels[name] = LastSeenEntry(timestamp=_now_iso(), msgid=msgid)
        self.save()

    def touch_direct(self, target: str, msgid: Optional[str] = None) -> None:
        if target not in self.directs:
            self.directs[target] = LastSeenEntry()
        self.directs[target] = LastSeenEntry(timestamp=_now_iso(), msgid=msgid)
        self.save()

    def ensure_subscription(self, channel: str) -> None:
        if channel not in self.subscribed_channels:
            self.subscribed_channels.append(channel)
        if channel not in self.channels:
            self.channels[channel] = LastSeenEntry()
        self.save()

    def remove_subscription(self, channel: str) -> None:
        if channel in self.subscribed_channels:
            self.subscribed_channels.remove(channel)
            self.save()

    def ensure_direct(self, target: str) -> None:
        if not target.startswith("@"):
            target = f"@{target}"
        if target not in self.directs:
            self.directs[target] = LastSeenEntry()
            self.save()
