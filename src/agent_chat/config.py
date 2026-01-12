"""Configuration management for agent-chat."""
from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import tomllib
from filelock import FileLock

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    keyring = None  # type: ignore
    KEYRING_AVAILABLE = False

APP_DIR = Path(os.environ.get("AGENT_CHAT_HOME", Path.home() / ".agent-chat"))
CONFIG_FILE = APP_DIR / "config.toml"
CREDENTIALS_FILE = APP_DIR / "credentials.json"
LOCK_FILE = CONFIG_FILE.with_suffix(".lock")
SERVICE_NAME = "agent-chat"
DEFAULT_ROOMS = ["#general", "#status", "#alerts"]


@dataclasses.dataclass
class ServerConfig:
    """Matrix homeserver configuration."""
    url: str = "http://localhost:8008"


@dataclasses.dataclass
class IdentityConfig:
    """User identity configuration."""
    username: str = ""
    display_name: str = "Agent Chat"


@dataclasses.dataclass
class AgentChatConfig:
    """Main configuration container."""
    server: ServerConfig
    identity: IdentityConfig

    @classmethod
    def load(cls) -> "AgentChatConfig":
        """Load configuration from file or create defaults."""
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            data = tomllib.loads(CONFIG_FILE.read_text())
        else:
            data = {}

        server_tbl = data.get("server", {})
        if not server_tbl:
            server_tbl = {"url": "http://localhost:8008"}

        identity_tbl = data.get("identity", {})
        if not identity_tbl:
            identity_tbl = {"username": "", "display_name": "Agent Chat"}

        config = cls(
            server=ServerConfig(
                url=str(server_tbl.get("url", "http://localhost:8008")),
            ),
            identity=IdentityConfig(
                username=str(identity_tbl.get("username", "")),
                display_name=str(identity_tbl.get("display_name", "Agent Chat")),
            ),
        )

        if not CONFIG_FILE.exists():
            config.save()

        return config

    def save(self) -> None:
        """Save configuration to file."""
        APP_DIR.mkdir(parents=True, exist_ok=True)
        lines = [
            "[server]",
            f'url = "{self.server.url}"',
            "",
            "[identity]",
            f'username = "{self.identity.username}"',
            f'display_name = "{self.identity.display_name}"',
            "",
        ]
        doc = "\n".join(lines)
        with FileLock(str(LOCK_FILE)):
            CONFIG_FILE.write_text(doc)


def get_credentials() -> Optional[Dict[str, Any]]:
    """Get stored Matrix credentials (access_token, user_id, device_id)."""
    if not CREDENTIALS_FILE.exists():
        return None

    with CREDENTIALS_FILE.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if "access_token" not in data:
        return None

    return data


def set_credentials(
    user_id: str,
    access_token: str,
    device_id: str = "",
) -> None:
    """Store Matrix credentials."""
    APP_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "user_id": user_id,
        "access_token": access_token,
        "device_id": device_id,
    }

    # Also try to store in keyring for extra security
    if KEYRING_AVAILABLE and keyring is not None:
        try:
            keyring.set_password(SERVICE_NAME, user_id, access_token)
        except Exception:
            pass  # Fall through to JSON storage

    with FileLock(str(LOCK_FILE)):
        with CREDENTIALS_FILE.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)


def clear_credentials() -> None:
    """Clear stored credentials."""
    if CREDENTIALS_FILE.exists():
        with FileLock(str(LOCK_FILE)):
            CREDENTIALS_FILE.unlink()


# Legacy compatibility
def read_credentials_meta() -> Dict[str, Any]:
    """Read credentials metadata (legacy compatibility)."""
    creds = get_credentials()
    if creds:
        return creds
    return {}


def get_password(nick: str) -> Optional[str]:
    """Get password (legacy compatibility - returns access token)."""
    creds = get_credentials()
    if creds:
        return creds.get("access_token")
    return None


def set_password(nick: str, password: str) -> None:
    """Set password (legacy compatibility)."""
    # This is a no-op for Matrix - use set_credentials instead
    pass
