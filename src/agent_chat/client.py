"""Matrix client wrapper for agent-chat."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Coroutine, Dict, List, Optional

from nio import (
    AsyncClient,
    AsyncClientConfig,
    LoginResponse,
    RoomMessagesResponse,
    RoomSendResponse,
    SyncResponse,
    RoomVisibility,
)

from .config import AgentChatConfig, get_credentials, set_credentials
from .logging import get_logger

log = get_logger(__name__)


@dataclass
class HistoryMessage:
    """A message from room history."""
    room_id: str
    sender: str
    text: str
    event_id: Optional[str]
    timestamp: Optional[int]


@dataclass
class RoomMember:
    """A member of a room."""
    user_id: str
    display_name: Optional[str]


class MatrixClient:
    """Stateless Matrix client for agent-chat operations."""

    def __init__(self, config: AgentChatConfig) -> None:
        self._config = config
        self._client: Optional[AsyncClient] = None

    async def _get_client(self) -> AsyncClient:
        """Get or create authenticated client."""
        if self._client is not None:
            return self._client

        client_config = AsyncClientConfig(
            max_limit_exceeded=0,
            max_timeouts=0,
        )

        self._client = AsyncClient(
            homeserver=self._config.server.url,
            user=f"@{self._config.identity.username}:{self._server_name}",
            config=client_config,
        )

        # Load stored credentials
        creds = get_credentials()
        if creds and creds.get("access_token"):
            self._client.access_token = creds["access_token"]
            self._client.user_id = creds["user_id"]
            self._client.device_id = creds.get("device_id", "")
            log.debug("Using stored credentials for %s", self._client.user_id)

        return self._client

    @property
    def _server_name(self) -> str:
        """Extract server name from URL."""
        # For http://localhost:8008, we want agent-chat.local
        # This should match what Synapse is configured with
        return "agent-chat.local"

    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def register(self, username: str, password: str) -> Dict[str, Any]:
        """Register a new user account."""
        client = AsyncClient(
            homeserver=self._config.server.url,
            user="",
        )

        try:
            # Use the register endpoint directly
            response = await client.register(
                username=username,
                password=password,
            )

            if hasattr(response, "access_token"):
                set_credentials(
                    user_id=response.user_id,
                    access_token=response.access_token,
                    device_id=response.device_id,
                )
                return {
                    "user_id": response.user_id,
                    "access_token": response.access_token,
                    "device_id": response.device_id,
                }
            else:
                raise RuntimeError(f"Registration failed: {response}")
        finally:
            await client.close()

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login with username and password."""
        client = AsyncClient(
            homeserver=self._config.server.url,
            user=f"@{username}:{self._server_name}",
        )

        try:
            response = await client.login(password=password)

            if isinstance(response, LoginResponse):
                set_credentials(
                    user_id=response.user_id,
                    access_token=response.access_token,
                    device_id=response.device_id,
                )
                return {
                    "user_id": response.user_id,
                    "access_token": response.access_token,
                    "device_id": response.device_id,
                }
            else:
                raise RuntimeError(f"Login failed: {response}")
        finally:
            await client.close()

    async def check_status(self) -> Dict[str, Any]:
        """Check connection status with a quick sync."""
        client = await self._get_client()

        try:
            response = await client.sync(timeout=0, full_state=False)
            if isinstance(response, SyncResponse):
                return {
                    "connected": True,
                    "user_id": client.user_id,
                    "rooms": len(response.rooms.join),
                }
            else:
                return {"connected": False, "error": str(response)}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    async def resolve_room_alias(self, alias: str) -> Optional[str]:
        """Resolve a room alias (#general) to room ID (!abc:server)."""
        client = await self._get_client()

        # Ensure proper format
        if not alias.startswith("#"):
            alias = f"#{alias}"
        if ":" not in alias:
            alias = f"{alias}:{self._server_name}"

        try:
            response = await client.room_resolve_alias(alias)
            if hasattr(response, "room_id"):
                return response.room_id
            return None
        except Exception as e:
            log.warning("Failed to resolve alias %s: %s", alias, e)
            return None

    async def send_message(self, target: str, message: str) -> bool:
        """Send a message to a room or user."""
        client = await self._get_client()

        # Resolve target to room ID
        room_id = target
        if target.startswith("#"):
            resolved = await self.resolve_room_alias(target)
            if resolved:
                room_id = resolved
            else:
                raise ValueError(f"Could not resolve room alias: {target}")
        elif target.startswith("@"):
            # Direct message - need to find or create DM room
            room_id = await self._get_or_create_dm_room(target)

        # Ensure we're in the room
        await client.join(room_id)

        response = await client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": message,
            },
        )

        if isinstance(response, RoomSendResponse):
            log.debug("Sent message to %s: %s", room_id, response.event_id)
            return True
        else:
            log.error("Failed to send message: %s", response)
            return False

    async def _get_or_create_dm_room(self, user_id: str) -> str:
        """Get or create a DM room with a user."""
        client = await self._get_client()

        # Ensure proper format
        if not user_id.startswith("@"):
            user_id = f"@{user_id}"
        if ":" not in user_id:
            user_id = f"{user_id}:{self._server_name}"

        # Check existing rooms for DM with this user
        response = await client.sync(timeout=0, full_state=True)
        if isinstance(response, SyncResponse):
            for room_id, room in response.rooms.join.items():
                # Check room state for direct message with target user
                try:
                    state_response = await client.room_get_state(room_id)
                    if hasattr(state_response, "events"):
                        for event in state_response.events:
                            # Look for m.room.member event for target user with is_direct
                            if (event.get("type") == "m.room.member" and
                                event.get("state_key") == user_id and
                                event.get("content", {}).get("is_direct")):
                                log.debug("Found existing DM room %s with %s", room_id, user_id)
                                return room_id
                except Exception as e:
                    log.debug("Could not check state for %s: %s", room_id, e)

        # Create new DM room
        log.debug("Creating new DM room with %s", user_id)
        room_response = await client.room_create(
            is_direct=True,
            invite=[user_id],
        )

        if hasattr(room_response, "room_id"):
            return room_response.room_id
        else:
            raise RuntimeError(f"Failed to create DM room: {room_response}")

    async def fetch_history(
        self,
        target: str,
        limit: int = 20,
    ) -> List[HistoryMessage]:
        """Fetch message history from a room or DM."""
        client = await self._get_client()

        # Resolve target to room ID
        room_id = target
        if target.startswith("#"):
            resolved = await self.resolve_room_alias(target)
            if resolved:
                room_id = resolved
            else:
                return []
        elif target.startswith("@"):
            # DM target - find the DM room
            try:
                room_id = await self._get_or_create_dm_room(target)
            except Exception as e:
                log.warning("Could not get DM room for %s: %s", target, e)
                return []

        # Ensure we're in the room
        try:
            await client.join(room_id)
        except Exception as e:
            log.warning("Failed to join room %s: %s", room_id, e)

        response = await client.room_messages(
            room_id=room_id,
            start="",  # Start from latest
            limit=limit,
        )

        messages: List[HistoryMessage] = []
        if isinstance(response, RoomMessagesResponse):
            for event in response.chunk:
                if hasattr(event, "body"):
                    messages.append(
                        HistoryMessage(
                            room_id=room_id,
                            sender=event.sender,
                            text=event.body,
                            event_id=event.event_id,
                            timestamp=event.server_timestamp,
                        )
                    )

        # Return in chronological order (oldest first)
        messages.reverse()
        return messages

    async def get_joined_rooms(self) -> List[Dict[str, Any]]:
        """Get list of joined rooms with metadata."""
        client = await self._get_client()

        response = await client.sync(timeout=0, full_state=False)
        rooms = []

        if isinstance(response, SyncResponse):
            for room_id in response.rooms.join:
                rooms.append({
                    "room_id": room_id,
                    "name": room_id,  # Could fetch room state for name
                })

        return rooms

    async def get_room_members(self, target: str) -> List[RoomMember]:
        """Get members of a room."""
        client = await self._get_client()

        # Resolve target to room ID
        room_id = target
        if target.startswith("#"):
            resolved = await self.resolve_room_alias(target)
            if resolved:
                room_id = resolved
            else:
                return []

        response = await client.joined_members(room_id)
        members = []

        if hasattr(response, "members"):
            for member in response.members:
                members.append(
                    RoomMember(
                        user_id=member.user_id,
                        display_name=member.display_name,
                    )
                )

        return members

    async def create_room(
        self,
        alias: str,
        public: bool = True,
        topic: str = "",
    ) -> Optional[str]:
        """Create a new room with an alias."""
        client = await self._get_client()

        # Clean up alias
        local_alias = alias.lstrip("#").split(":")[0]

        response = await client.room_create(
            alias=local_alias,
            visibility=RoomVisibility.public if public else RoomVisibility.private,
            topic=topic,
        )

        if hasattr(response, "room_id"):
            log.info("Created room %s with alias #%s", response.room_id, local_alias)
            return response.room_id
        else:
            log.error("Failed to create room: %s", response)
            return None

    async def join_or_create_room(
        self,
        alias: str,
        topic: str = "",
    ) -> Optional[str]:
        """Join a room by alias, creating it if it doesn't exist."""
        client = await self._get_client()

        # Clean up alias
        if not alias.startswith("#"):
            alias = f"#{alias}"

        # Try to resolve existing room
        room_id = await self.resolve_room_alias(alias)
        if room_id:
            # Room exists, join it
            await client.join(room_id)
            log.info("Joined existing room %s (%s)", alias, room_id)
            return room_id

        # Room doesn't exist, create it
        log.info("Room %s doesn't exist, creating...", alias)
        room_id = await self.create_room(alias, public=True, topic=topic)
        if room_id:
            await client.join(room_id)
            return room_id

        return None


def run_sync(coro: Coroutine) -> Any:
    """Run an async coroutine synchronously."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


def get_client(config: AgentChatConfig) -> MatrixClient:
    """Create a new Matrix client instance."""
    return MatrixClient(config)
