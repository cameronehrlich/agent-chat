from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Any, Dict

import tomllib
from filelock import FileLock

APP_DIR = Path(os.environ.get("AGENT_CHAT_HOME", Path.home() / ".agent-chat"))
CONFIG_FILE = APP_DIR / "config.toml"
CREDENTIALS_FILE = APP_DIR / "credentials.json"
LOCK_FILE = CONFIG_FILE.with_suffix(".lock")
SERVICE_NAME = "agent-chat"

try:
    import keyring  # type: ignore
except ImportError:  # pragma: no cover - fallback when keyring unavailable
    class _MemoryKeyring:
        def __init__(self) -> None:
            self._store: Dict[tuple[str, str], str] = {}

        def set_password(self, service: str, user: str, password: str) -> None:
            self._store[(service, user)] = password

        def get_password(self, service: str, user: str) -> str | None:
            return self._store.get((service, user))

    keyring = _MemoryKeyring()
DEFAULT_CHANNELS = ["#general", "#status", "#alerts"]


@dataclasses.dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 6697
    tls: bool = True


@dataclasses.dataclass
class IdentityConfig:
    nick: str = ""
    realname: str = "Agent Chat"


@dataclasses.dataclass
class AgentChatConfig:
    server: ServerConfig
    identity: IdentityConfig

    @classmethod
    def load(cls) -> "AgentChatConfig":
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            data = tomllib.loads(CONFIG_FILE.read_text())
        else:
            data = {}
        server_tbl = data.get("server", {})
        if not server_tbl:
            server_tbl = {"host": "127.0.0.1", "port": 6697, "tls": True}
        identity_tbl = data.get("identity", {})
        if not identity_tbl:
            identity_tbl = {"nick": "", "realname": "Agent Chat"}
        return cls(
            server=ServerConfig(
                host=str(server_tbl.get("host", "127.0.0.1")),
                port=int(server_tbl.get("port", 6697)),
                tls=bool(server_tbl.get("tls", True)),
            ),
            identity=IdentityConfig(
                nick=str(identity_tbl.get("nick", "")),
                realname=str(identity_tbl.get("realname", "Agent Chat")),
            ),
        )

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        lines = [
            "[server]",
            f"host = \"{self.server.host}\"",
            f"port = {self.server.port}",
            f"tls = {str(self.server.tls).lower()}",
            "",
            "[identity]",
            f"nick = \"{self.identity.nick}\"",
            f"realname = \"{self.identity.realname}\"",
            "",
        ]
        doc = "\n".join(lines)
        with FileLock(str(LOCK_FILE)):
            CONFIG_FILE.write_text(doc)


def get_password(nick: str) -> str | None:
    if not nick:
        return None
    return keyring.get_password(SERVICE_NAME, nick)


def set_password(nick: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, nick, password)


def read_credentials_meta() -> Dict[str, Any]:
    if not CREDENTIALS_FILE.exists():
        return {}
    with CREDENTIALS_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_credentials_meta(meta: Dict[str, Any]) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with CREDENTIALS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
