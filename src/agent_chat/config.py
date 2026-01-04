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
        config = cls(
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
        if not CONFIG_FILE.exists():
            config.save()
        return config

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


def read_credentials_meta() -> Dict[str, Any]:
    if not CREDENTIALS_FILE.exists():
        return {"passwords": {}}
    with CREDENTIALS_FILE.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if "passwords" not in data:
        data["passwords"] = {}
    return data


def _write_credentials(meta: Dict[str, Any]) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with CREDENTIALS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)


def get_password(nick: str) -> str | None:
    if not nick:
        return None
    meta = read_credentials_meta()
    return meta.get("passwords", {}).get(nick)


def set_password(nick: str, password: str) -> None:
    meta = read_credentials_meta()
    meta.setdefault("passwords", {})[nick] = password
    _write_credentials(meta)


def write_credentials_meta(update: Dict[str, Any]) -> None:
    meta = read_credentials_meta()
    meta.update({k: v for k, v in update.items() if k != "password"})
    _write_credentials(meta)
