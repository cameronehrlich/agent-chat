from __future__ import annotations

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .client import run_with_client
from .config import AgentChatConfig, set_password, write_credentials_meta
from .logging import setup_logging, get_logger
from .state import AgentChatState
from .utils import generate_nick, is_channel

app = typer.Typer(help="Agent Chat CLI")
console = Console()
log = get_logger(__name__)


def _run_action(action):
    config = AgentChatConfig.load()
    run_with_client(config, action)


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging")):
    setup_logging(verbose)


@app.command()
def status():
    """Check connectivity/auth."""

    async def action(session):
        log.info("Connected to IRC server")

    _run_action(action)
    console.print(":white_check_mark: Connected")


@app.command()
def send(target: str, message: str):
    """Send message to channel or user."""
    config = AgentChatConfig.load()
    state = AgentChatState.load()

    async def action(session):
        if is_channel(target):
            await session.join_channel(target)
            await session.send_privmsg(target, message)
            state.ensure_subscription(target)
            state.touch_channel(target)
        else:
            pure = target[1:] if target.startswith("@") else target
            await session.send_privmsg(pure, message)
            state.touch_direct(f"@{pure}")

    run_with_client(config, action)
    console.print(f"Sent to {target}")


@app.command()
def listen(
    target: Optional[str] = typer.Argument(None),
    last: int = typer.Option(20, "--last", help="Number of messages"),
    all: bool = typer.Option(False, "--all", help="Listen to all subscribed channels"),
):
    config = AgentChatConfig.load()
    state = AgentChatState.load()
    channels = state.subscribed_channels if all else ([target] if target else [])
    if not channels:
        console.print("No channel specified")
        raise typer.Exit(1)

    async def action(session):
        for ch in channels:
            entry = state.channels.get(ch)
            after = entry.msgid if entry else None
            messages = await session.fetch_history(ch, last, after)
            table = Table(title=ch)
            table.add_column("Time")
            table.add_column("Nick")
            table.add_column("Message")
            for msg in messages:
                table.add_row(msg.timestamp or "", msg.nick, msg.text)
            console.print(table)
            if messages:
                state.touch_channel(ch, messages[-1].msgid)

    run_with_client(config, action)


@app.command()
def channels(subscribe: Optional[str] = typer.Option(None, "--subscribe")):
    state = AgentChatState.load()
    if subscribe:
        state.ensure_subscription(subscribe)
        console.print(f"Subscribed to {subscribe}")
    table = Table(title="Subscribed Channels")
    table.add_column("Channel")
    for ch in state.subscribed_channels:
        table.add_row(ch)
    console.print(table)


@app.command("config")
def config_cmd(
    set_option: Optional[str] = typer.Option(None, "--set", help="key=value (server.host/port/identity.nick)"),
):
    config = AgentChatConfig.load()
    if set_option:
        if "=" not in set_option:
            console.print("Use key=value with --set")
            raise typer.Exit(1)
        key, value = set_option.split("=", 1)
        if key == "server.host":
            config.server.host = value
        elif key == "server.port":
            config.server.port = int(value)
        elif key == "identity.nick":
            config.identity.nick = value
        else:
            console.print(f"Unknown key: {key}")
            raise typer.Exit(1)
        config.save()
    console.print(json.dumps({
        "server": {
            "host": config.server.host,
            "port": config.server.port,
            "tls": config.server.tls,
        },
        "identity": {
            "nick": config.identity.nick,
            "realname": config.identity.realname,
        }
    }, indent=2))


@app.command()
def register(nick: Optional[str] = typer.Option(None, help="Nickname"), password: Optional[str] = typer.Option(None, help="Password")):
    config = AgentChatConfig.load()
    if not nick:
        nick = generate_nick()
    if not password:
        password = typer.prompt("Password", hide_input=True)
    config.identity.nick = nick
    config.save()
    set_password(nick, password)
    write_credentials_meta({"nick": nick, "registered": True})
    console.print(f"Registered as {nick}")


@app.command()
def login(nick: str, password: Optional[str] = typer.Option(None, help="Password")):
    config = AgentChatConfig.load()
    config.identity.nick = nick
    config.save()
    if password is None:
        password = typer.prompt("Password", hide_input=True)
    set_password(nick, password)
    console.print(f"Updated credentials for {nick}")


@app.command()
def notify(json_output: bool = typer.Option(False, "--json")):
    config = AgentChatConfig.load()
    state = AgentChatState.load()
    results = {}

    async def action(session):
        for ch in state.subscribed_channels:
            entry = state.channels.get(ch)
            after = entry.msgid if entry else None
            msgs = await session.fetch_history(ch, 20, after)
            if msgs:
                state.touch_channel(ch, msgs[-1].msgid)
            results[ch] = {
                "count": len(msgs),
                "urgent": any(m.text.lower().startswith("!urgent") for m in msgs),
            }

    run_with_client(config, action)
    if json_output:
        console.print(json.dumps(results))
    else:
        parts = [f"{ch}({data['count']}{'!' if data['urgent'] else ''})" for ch, data in results.items() if data["count"] > 0]
        console.print("[chat] " + " ".join(parts) if parts else "")

@app.command()
def who(channel: str = typer.Argument("#general")):
    """List users in a channel."""
    config = AgentChatConfig.load()

    async def action(session):
        names = []
        future = session.loop.create_future()

        def on_namreply(connection, event):
            args = event.arguments or []
            text = args[-1] if args else ""
            if channel in args:
                names.extend(text.split())

        def on_end(connection, event):
            args = event.arguments or []
            ch = args[0] if args else ""
            if ch == channel:
                connection.remove_global_handler("namreply", on_namreply)
                connection.remove_global_handler("endofnames", on_end)
                if not future.done():
                    future.set_result(None)

        session.connection.add_global_handler("namreply", on_namreply, 10)
        session.connection.add_global_handler("endofnames", on_end, 10)
        session.connection.join(channel)
        session.connection.send_raw(f"NAMES {channel}")
        await asyncio.wait_for(future, timeout=10)
        table = Table(title=f"Users in {channel}")
        table.add_column("Nick")
        for nick in names:
            table.add_row(nick)
        console.print(table)

    run_with_client(config, action)
