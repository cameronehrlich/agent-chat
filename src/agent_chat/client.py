from __future__ import annotations

import asyncio
import ssl
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional

from irc import client_aio, connection as irc_connection

from .config import AgentChatConfig, get_password
from .logging import get_logger

log = get_logger(__name__)


@dataclass
class HistoryMessage:
    channel: str
    nick: str
    text: str
    msgid: Optional[str]
    timestamp: Optional[str]


def _tags_to_dict(tags) -> Dict[str, Optional[str]]:
    data: Dict[str, Optional[str]] = {}
    if not tags:
        return data
    for tag in tags:
        key = tag.get("key") if isinstance(tag, dict) else tag[0]
        value = tag.get("value") if isinstance(tag, dict) else tag[1]
        data[key] = value
    return data


class IRCSession(client_aio.AioSimpleIRCClient):
    def __init__(
        self,
        config: AgentChatConfig,
        password: Optional[str],
        on_ready: Callable[["IRCSession"], Awaitable[None]],
    ) -> None:
        self._config = config
        self._password = password
        self._on_ready = on_ready
        self._loop = asyncio.new_event_loop()
        self.loop = self._loop
        self._completed: asyncio.Future[None] = self._loop.create_future()
        try:
            self._previous_loop = asyncio.get_event_loop()
        except RuntimeError:
            self._previous_loop = None
        asyncio.set_event_loop(self._loop)
        super().__init__()
        if self._previous_loop is not None:
            asyncio.set_event_loop(self._previous_loop)
        self.connection.add_global_handler("disconnect", self._on_disconnect, -10)
        self.connection.add_global_handler("all_events", self._log_events, -50)

    def _log_events(self, connection, event):  # pragma: no cover - verbose tracing
        log.debug("IRC event %s target=%s args=%s", event.type, event.target, event.arguments)

    def _on_disconnect(self, connection, event):
        if not self._completed.done():
            self._completed.set_result(None)

    async def _handle_ready(self):
        self.connection.cap('REQ', 'batch chathistory message-tags')
        self.connection.cap('END')
        await self._on_ready(self)
        self.connection.quit("done")

    def on_welcome(self, connection, event):
        log.debug("welcome: %s", event)
        asyncio.run_coroutine_threadsafe(self._handle_ready(), self._loop)

    def connect_and_run(self) -> None:
        asyncio.set_event_loop(self._loop)
        factory = irc_connection.AioFactory(ssl=self._config.server.tls)
        log.info(
            "Connecting to %s:%s as %s",
            self._config.server.host,
            self._config.server.port,
            self._config.identity.nick,
        )
        coro = self.connection.connect(
            self._config.server.host,
            self._config.server.port,
            self._config.identity.nick,
            password=self._password,
            ircname=self._config.identity.realname,
            connect_factory=factory,
        )
        self._loop.run_until_complete(coro)
        try:
            self._loop.run_until_complete(self._completed)
        finally:
            self._loop.run_until_complete(asyncio.sleep(0.1))
            self._loop.stop()
            self._loop.close()

    async def send_privmsg(self, target: str, message: str) -> None:
        self.connection.privmsg(target, message)

    async def join_channel(self, channel: str) -> None:
        self.connection.join(channel)

    async def fetch_history(
        self,
        channel: str,
        limit: int,
        after_msgid: Optional[str] = None,
    ) -> List[HistoryMessage]:
        future: asyncio.Future[List[HistoryMessage]] = self._loop.create_future()
        pending: Dict[str, List[HistoryMessage]] = {"messages": []}
        target_batch: Dict[str, Optional[str]] = {"id": None}

        def on_batch(connection, event):
            args = event.arguments or []
            token = args[0] if args else ""
            if token.startswith("+"):
                if len(args) >= 3 and args[1] == "chathistory" and args[2] == channel:
                    target_batch["id"] = token[1:]
            elif token.startswith("-"):
                if target_batch.get("id") and token[1:] == target_batch["id"]:
                    self.connection.remove_global_handler("batch", on_batch)
                    self.connection.remove_global_handler("privmsg", on_privmsg)
                    if not future.done():
                        future.set_result(pending["messages"])

        def on_privmsg(connection, event):
            tags = _tags_to_dict(event.tags)
            batch_id = tags.get("batch")
            if not target_batch.get("id") or batch_id != target_batch["id"]:
                return
            pending["messages"].append(
                HistoryMessage(
                    channel=event.target,
                    nick=getattr(event.source, "nick", str(event.source)),
                    text=event.arguments[0] if event.arguments else "",
                    msgid=tags.get("msgid"),
                    timestamp=tags.get("time"),
                )
            )

        self.connection.add_global_handler("batch", on_batch, 10)
        self.connection.add_global_handler("privmsg", on_privmsg, 10)

        if after_msgid:
            command = f"CHATHISTORY AFTER {channel} {after_msgid} {limit}"
        else:
            command = f"CHATHISTORY LATEST {channel} * {limit}"
        log.debug("Issuing %s", command)
        self.connection.send_raw(command)

        return await asyncio.wait_for(future, timeout=10)


def run_with_client(
    config: AgentChatConfig,
    on_ready: Callable[[IRCSession], Awaitable[None]],
) -> None:
    password = get_password(config.identity.nick)
    session = IRCSession(config=config, password=password, on_ready=on_ready)
    session.connect_and_run()
