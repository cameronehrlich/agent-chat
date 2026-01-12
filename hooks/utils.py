"""Shared utilities for agent-chat hooks."""
import json
import os
import re
import subprocess


def get_nick() -> str:
    """Load the agent's nick from config, falling back to 'agent'."""
    try:
        import tomllib
        config_path = os.path.expanduser("~/.agent-chat/config.toml")
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        return config.get("identity", {}).get("username", "agent")
    except Exception:
        return "agent"


def get_project() -> str:
    """Detect project name from current working directory.

    Uses the directory name, sanitized for use as a channel name.
    """
    cwd = os.getcwd()
    project = os.path.basename(cwd)

    # Sanitize for channel name (lowercase, alphanumeric and hyphens only)
    project = project.lower()
    project = re.sub(r'[^a-z0-9-]', '-', project)
    project = re.sub(r'-+', '-', project)  # collapse multiple hyphens
    project = project.strip('-')

    return project or "default"


def join_project_channel(project: str = None) -> bool:
    """Join (or create) the project-specific channel.

    Returns True if successful.
    """
    if project is None:
        project = get_project()

    result = subprocess.run(
        ["ac", "join", f"#{project}"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def send_to_project(message: str, project: str = None) -> bool:
    """Send a message to the project-specific channel.

    Returns True if successful.
    """
    if project is None:
        project = get_project()

    result = subprocess.run(
        ["ac", "send", f"#{project}", message],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def get_alert_count() -> int:
    """Get the count of unread messages in #alerts channel."""
    result = subprocess.run(
        ["ac", "notify", "--json"],
        capture_output=True,
        text=True
    )
    try:
        data = json.loads(result.stdout or "{}")
        return data.get("#alerts", {}).get("count", 0)
    except (json.JSONDecodeError, TypeError):
        return 0


def fetch_alerts(limit: int = 10) -> str:
    """Fetch recent alert messages."""
    result = subprocess.run(
        ["ac", "listen", "#alerts", "--last", str(limit)],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def send_status(message: str) -> None:
    """Send a message to the #status channel."""
    subprocess.run(
        ["ac", "send", "#status", message],
        capture_output=True
    )
