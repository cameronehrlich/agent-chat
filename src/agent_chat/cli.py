"""Agent Chat CLI - Matrix-based coordination for coding agents."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .client import MatrixClient, get_client, run_sync
from .config import AgentChatConfig, set_credentials, get_credentials
from .logging import setup_logging, get_logger
from .presence import update_presence, get_presence, clear_stale
from .state import AgentChatState
from .utils import generate_nick, is_channel, is_direct

app = typer.Typer(help="Agent Chat CLI - Matrix coordination for coding agents")
console = Console()
log = get_logger(__name__)


def _get_client() -> MatrixClient:
    """Get configured Matrix client."""
    config = AgentChatConfig.load()
    return get_client(config)


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging")):
    """Agent Chat - Real-time coordination for coding agents."""
    setup_logging(verbose)


@app.command()
def status():
    """Check connectivity and authentication."""
    client = _get_client()

    async def check():
        try:
            result = await client.check_status()
            return result
        finally:
            await client.close()

    result = run_sync(check())

    if result.get("connected"):
        console.print(":white_check_mark: Connected")
        console.print(f"  User: {result.get('user_id')}")
        console.print(f"  Rooms: {result.get('rooms')}")
    else:
        console.print(":x: Not connected")
        console.print(f"  Error: {result.get('error')}")
        raise typer.Exit(1)


@app.command()
def send(target: str, message: str):
    """Send message to room or user.

    Examples:
        ac send "#general" "Hello everyone!"
        ac send "@BlueLake" "Can you review my PR?"
    """
    client = _get_client()
    state = AgentChatState.load()

    async def do_send():
        try:
            success = await client.send_message(target, message)
            if success:
                if is_channel(target):
                    state.ensure_subscription(target)
                    state.touch_channel(target)
                else:
                    dm_key = target if target.startswith("@") else f"@{target}"
                    state.ensure_direct(dm_key)
                    state.touch_direct(dm_key)
            return success
        finally:
            await client.close()

    success = run_sync(do_send())

    if success:
        console.print(f"Sent to {target}")
    else:
        console.print(f"Failed to send to {target}")
        raise typer.Exit(1)


@app.command()
def listen(
    target: Optional[str] = typer.Argument(None, help="Room (#general) or user (@BlueLake)"),
    last: int = typer.Option(20, "--last", help="Number of messages"),
    all_rooms: bool = typer.Option(False, "--all", help="Listen to all subscribed rooms"),
):
    """Fetch recent messages from a room or user.

    Examples:
        ac listen "#general" --last 10
        ac listen --all
    """
    client = _get_client()
    state = AgentChatState.load()

    targets = []
    if all_rooms:
        targets = state.subscribed_channels
    elif target:
        targets = [target]
    else:
        console.print("Specify a room or use --all")
        raise typer.Exit(1)

    async def do_listen():
        try:
            for t in targets:
                messages = await client.fetch_history(t, last)

                table = Table(title=t)
                table.add_column("Time", style="dim")
                table.add_column("Nick", style="cyan")
                table.add_column("Message")

                for msg in messages:
                    # Format timestamp
                    time_str = ""
                    if msg.timestamp:
                        dt = datetime.fromtimestamp(msg.timestamp / 1000)
                        time_str = dt.strftime("%H:%M")

                    # Extract display name from sender
                    nick = msg.sender.split(":")[0].lstrip("@")

                    table.add_row(time_str, nick, msg.text)

                console.print(table)

                # Update state
                if messages:
                    if is_channel(t):
                        state.touch_channel(t, messages[-1].event_id)
                    else:
                        state.touch_direct(t, messages[-1].event_id)
        finally:
            await client.close()

    run_sync(do_listen())


@app.command()
def channels(
    subscribe: Optional[str] = typer.Option(None, "--subscribe", help="Subscribe to a room"),
):
    """List subscribed rooms."""
    state = AgentChatState.load()

    if subscribe:
        state.ensure_subscription(subscribe)
        console.print(f"Subscribed to {subscribe}")

    table = Table(title="Subscribed Rooms")
    table.add_column("Room")
    for ch in state.subscribed_channels:
        table.add_row(ch)
    console.print(table)


@app.command("config")
def config_cmd(
    set_option: Optional[str] = typer.Option(
        None,
        "--set",
        help="key=value (server.url, identity.username/display_name)",
    ),
):
    """View or update configuration."""
    config = AgentChatConfig.load()

    if set_option:
        if "=" not in set_option:
            console.print("Use key=value with --set")
            raise typer.Exit(1)
        key, value = set_option.split("=", 1)
        if key == "server.url":
            config.server.url = value
        elif key == "identity.username":
            config.identity.username = value
        elif key == "identity.display_name":
            config.identity.display_name = value
        else:
            console.print(f"Unknown key: {key}")
            raise typer.Exit(1)
        config.save()

    console.print(json.dumps({
        "server": {
            "url": config.server.url,
        },
        "identity": {
            "username": config.identity.username,
            "display_name": config.identity.display_name,
        }
    }, indent=2))


@app.command()
def register(
    username: Optional[str] = typer.Argument(None, help="Username"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password"),
):
    """Register a new account on the Matrix homeserver.

    If username is not provided, a random one will be generated.
    """
    config = AgentChatConfig.load()

    if not username:
        username = generate_nick().lower()

    if not password:
        password = typer.prompt("Password", hide_input=True)

    client = _get_client()

    async def do_register():
        try:
            result = await client.register(username, password)
            # Auto-join #general after registration
            try:
                user_id = result.get("user_id", f"@{username}")
                await client.send_message("#general", f"Welcome {user_id} to the chat!")
            except Exception as join_err:
                log.warning("Could not auto-join #general: %s", join_err)
            return result
        finally:
            await client.close()

    try:
        result = run_sync(do_register())
        config.identity.username = username
        config.save()
        console.print(f":white_check_mark: Registered as {result['user_id']}")
    except Exception as e:
        console.print(f":x: Registration failed: {e}")
        raise typer.Exit(1)


@app.command()
def login(
    username: str = typer.Argument(..., help="Username"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password"),
):
    """Login to the Matrix homeserver."""
    config = AgentChatConfig.load()

    if password is None:
        password = typer.prompt("Password", hide_input=True)

    client = _get_client()

    async def do_login():
        try:
            result = await client.login(username, password)
            return result
        finally:
            await client.close()

    try:
        result = run_sync(do_login())
        config.identity.username = username
        config.save()
        console.print(f":white_check_mark: Logged in as {result['user_id']}")
    except Exception as e:
        console.print(f":x: Login failed: {e}")
        raise typer.Exit(1)


@app.command()
def notify(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    oneline: bool = typer.Option(False, "--oneline", help="One-line format for tmux"),
):
    """Check for unread messages (for hooks/status bars)."""
    client = _get_client()
    state = AgentChatState.load()
    results: dict[str, dict[str, object]] = {}

    async def do_notify():
        try:
            for room in state.subscribed_channels:
                messages = await client.fetch_history(room, 20)
                # Filter to messages newer than last seen
                entry = state.channels.get(room)
                if entry and entry.msgid:
                    # Find messages after the last seen one
                    new_msgs = []
                    found_last = False
                    for msg in messages:
                        if found_last:
                            new_msgs.append(msg)
                        elif msg.event_id == entry.msgid:
                            found_last = True
                    messages = new_msgs if found_last else messages

                results[room] = {
                    "count": len(messages),
                    "urgent": any(m.text.lower().startswith("!urgent") for m in messages),
                }

            for dm_key in state.directs:
                messages = await client.fetch_history(dm_key, 20)
                entry = state.directs.get(dm_key)
                if entry and entry.msgid:
                    new_msgs = []
                    found_last = False
                    for msg in messages:
                        if found_last:
                            new_msgs.append(msg)
                        elif msg.event_id == entry.msgid:
                            found_last = True
                    messages = new_msgs if found_last else messages

                results[dm_key] = {
                    "count": len(messages),
                    "urgent": any(m.text.lower().startswith("!urgent") for m in messages),
                }
        finally:
            await client.close()

    try:
        run_sync(do_notify())
    except Exception as e:
        log.warning("Notify check failed: %s", e)
        # Degrade gracefully - return empty results
        pass

    if json_output:
        console.print(json.dumps(results))
    elif oneline:
        parts = [
            f"{key}({data['count']}{'!' if data['urgent'] else ''})"
            for key, data in results.items()
            if data.get("count", 0) > 0
        ]
        if parts:
            console.print("[chat] " + " ".join(parts))
    else:
        for key, data in results.items():
            count = data.get("count", 0)
            if count > 0:
                urgent = " (URGENT)" if data.get("urgent") else ""
                console.print(f"{key}: {count} new messages{urgent}")


@app.command()
def who(room: str = typer.Argument("#general", help="Room to list members of")):
    """List members of a room."""
    client = _get_client()

    async def do_who():
        try:
            members = await client.get_room_members(room)
            return members
        finally:
            await client.close()

    members = run_sync(do_who())

    table = Table(title=f"Users in {room}")
    table.add_column("Nick")
    for member in members:
        nick = member.display_name or member.user_id.split(":")[0].lstrip("@")
        table.add_row(nick)
    console.print(table)


@app.command()
def join(
    room: str = typer.Argument(..., help="Room alias (e.g., #general or #my-project)"),
    topic: str = typer.Option("", "--topic", help="Room topic if creating new"),
):
    """Join a room, creating it if it doesn't exist.

    Examples:
        ac join "#my-project"
        ac join "#new-channel" --topic "Discussion about feature X"
    """
    client = _get_client()
    state = AgentChatState.load()

    async def do_join():
        try:
            room_id = await client.join_or_create_room(room, topic=topic)
            return room_id
        finally:
            await client.close()

    room_id = run_sync(do_join())

    if room_id:
        # Add to subscribed channels
        clean_room = room if room.startswith("#") else f"#{room}"
        state.ensure_subscription(clean_room)
        console.print(f":white_check_mark: Joined {clean_room}")
        console.print(f"  Room ID: {room_id}")
    else:
        console.print(f":x: Failed to join {room}")
        raise typer.Exit(1)


@app.command("create-room")
def create_room(
    alias: str = typer.Argument(..., help="Room alias (e.g., #general)"),
    public: bool = typer.Option(True, "--public/--private", help="Public or private room"),
    topic: str = typer.Option("", "--topic", help="Room topic"),
):
    """Create a new room."""
    client = _get_client()

    async def do_create():
        try:
            room_id = await client.create_room(alias, public=public, topic=topic)
            return room_id
        finally:
            await client.close()

    room_id = run_sync(do_create())

    if room_id:
        console.print(f":white_check_mark: Created room {alias}")
        console.print(f"  Room ID: {room_id}")
    else:
        console.print(f":x: Failed to create room {alias}")
        raise typer.Exit(1)


VALID_STATUSES = {"online", "busy", "away", "offline"}
STATUS_STYLES = {
    "online": "green",
    "busy": "red",
    "away": "yellow",
    "offline": "dim",
}


@app.command()
def presence(
    status: str = typer.Argument(..., help="Status: online, busy, away, offline"),
    message: str = typer.Option("", "--message", "-m", help="Status message"),
):
    """Set your presence status.

    Examples:
        ac presence online --message "Working on auth module"
        ac presence busy --message "Deep focus - do not disturb"
        ac presence away
        ac presence offline
    """
    status_lower = status.lower()
    if status_lower not in VALID_STATUSES:
        console.print(f":x: Invalid status. Use one of: {', '.join(sorted(VALID_STATUSES))}")
        raise typer.Exit(1)

    config = AgentChatConfig.load()
    nick = config.identity.username or "agent"

    update_presence(nick, status_lower, message)

    client = _get_client()

    async def announce():
        try:
            prefix = f"[{status_lower.upper()}]"
            msg = f"{prefix} @{nick}"
            if message:
                msg += f" - {message}"
            await client.send_message("#status", msg)
        except Exception as e:
            log.warning("Could not announce presence: %s", e)
        finally:
            await client.close()

    run_sync(announce())

    console.print(f":white_check_mark: Status set to {status_lower}")
    if message:
        console.print(f"  Message: {message}")


@app.command("presence-list")
def presence_list(
    clear: bool = typer.Option(False, "--clear-stale", help="Remove stale entries"),
):
    """List all agent presence statuses.

    Examples:
        ac presence-list
        ac presence-list --clear-stale
    """
    if clear:
        removed = clear_stale()
        if removed:
            console.print(f"Cleared {removed} stale entries")

    agents = get_presence()

    if not agents:
        console.print("No agents currently tracked")
        return

    table = Table(title="Agent Presence")
    table.add_column("Agent", style="cyan")
    table.add_column("Status")
    table.add_column("Message")
    table.add_column("Last Seen", style="dim")

    for nick, info in agents.items():
        status = info.get("status", "unknown")
        status_style = STATUS_STYLES.get(status, "white")

        last_seen = info.get("last_seen", "")
        if last_seen:
            try:
                dt = datetime.fromisoformat(last_seen)
                last_seen = dt.strftime("%H:%M")
            except ValueError:
                pass

        table.add_row(
            nick,
            f"[{status_style}]{status}[/{status_style}]",
            info.get("message", ""),
            last_seen,
        )

    console.print(table)
