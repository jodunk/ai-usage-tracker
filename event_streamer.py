"""
SSE Event Broadcaster for Scudd Oracle

Manages Server-Sent Events (SSE) connections and broadcasts events
to all connected clients in real-time.
"""

import asyncio
import logging
from datetime import datetime
from typing import Set, Optional
from collections import deque

from event_types import Event, EventType, heartbeat_event


logger = logging.getLogger(__name__)


class SSEClient:
    """
    Represents a single SSE client connection

    Each client has its own queue for receiving events.
    """

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.queue: asyncio.Queue = asyncio.Queue()
        self.connected_at = datetime.now()
        self.last_event_at = None

    async def send(self, event: Event):
        """Send event to this client"""
        await self.queue.put(event)
        self.last_event_at = datetime.now()

    async def events(self):
        """Generator that yields events as they arrive"""
        try:
            while True:
                event = await self.queue.get()
                yield event
        except asyncio.CancelledError:
            logger.debug(f"Client {self.client_id} disconnected")
            raise


class EventBroadcaster:
    """
    Broadcasts events to all connected SSE clients

    Features:
    - Manages multiple concurrent client connections
    - Broadcasts events to all connected clients
    - Automatic client cleanup on disconnect
    - Periodic heartbeat (every 30s)
    - Event history buffer (last 100 events)
    """

    def __init__(self, heartbeat_interval: int = 30, history_size: int = 100):
        """
        Initialize broadcaster

        Args:
            heartbeat_interval: Seconds between heartbeat events
            history_size: Number of events to keep in history buffer
        """
        self.clients: Set[SSEClient] = set()
        self.heartbeat_interval = heartbeat_interval
        self.history_size = history_size

        # Event history (circular buffer)
        self.event_history: deque = deque(maxlen=history_size)

        # Stats
        self.total_events_broadcast = 0
        self.total_clients_served = 0
        self.started_at = datetime.now()

        # Background tasks
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the broadcaster (background heartbeat task)"""
        if self.heartbeat_task is None or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info(f"EventBroadcaster started (heartbeat: {self.heartbeat_interval}s)")

    async def stop(self):
        """Stop the broadcaster"""
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("EventBroadcaster stopped")

    async def _heartbeat_loop(self):
        """Background task that sends heartbeat events"""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                await self.broadcast(
                    heartbeat_event(
                        uptime_seconds=int((datetime.now() - self.started_at).total_seconds()),
                        total_tasks=0,  # Will be updated by tracker
                        total_cost_usd=0.0,  # Will be updated by tracker
                    )
                )
        except asyncio.CancelledError:
            logger.debug("Heartbeat loop cancelled")
            raise

    async def broadcast(self, event: Event):
        """
        Broadcast event to all connected clients

        Args:
            event: Event to broadcast
        """
        # Add to history
        self.event_history.append(event)
        self.total_events_broadcast += 1

        # Broadcast to all clients (non-blocking)
        if self.clients:
            tasks = [client.send(event) for client in self.clients]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Remove disconnected clients
            to_remove = set()
            for client, result in zip(self.clients, results):
                if isinstance(result, Exception):
                    logger.warning(f"Client {client.client_id} error: {result}")
                    to_remove.add(client)
                elif isinstance(result, asyncio.CancelledError):
                    to_remove.add(client)

            for client in to_remove:
                await self.remove_client(client)

        logger.debug(
            f"Broadcast {event.type.value} to {len(self.clients)} clients "
            f"(total: {self.total_events_broadcast} events)"
        )

    async def add_client(self, client: SSEClient):
        """
        Add a new client connection

        Args:
            client: SSE client to add
        """
        self.clients.add(client)
        self.total_clients_served += 1
        logger.info(
            f"Client {client.client_id} connected "
            f"(active: {len(self.clients)}, total: {self.total_clients_served})"
        )

        # Send recent history to new client
        for event in self.event_history:
            await client.send(event)

        logger.debug(f"Sent {len(self.event_history)} historical events to {client.client_id}")

    async def remove_client(self, client: SSEClient):
        """
        Remove a client connection

        Args:
            client: SSE client to remove
        """
        if client in self.clients:
            self.clients.discard(client)
            logger.info(
                f"Client {client.client_id} removed "
                f"(active: {len(self.clients)})"
            )

    def get_stats(self) -> dict:
        """
        Get broadcaster statistics

        Returns:
            Dict with current stats
        """
        uptime = datetime.now() - self.started_at

        return {
            "active_clients": len(self.clients),
            "total_clients_served": self.total_clients_served,
            "total_events_broadcast": self.total_events_broadcast,
            "history_size": len(self.event_history),
            "uptime_seconds": int(uptime.total_seconds()),
            "heartbeat_interval": self.heartbeat_interval,
        }

    def get_client_info(self, client_id: str) -> Optional[dict]:
        """
        Get information about a specific client

        Args:
            client_id: Client ID to look up

        Returns:
            Dict with client info or None if not found
        """
        for client in self.clients:
            if client.client_id == client_id:
                uptime = datetime.now() - client.connected_at
                return {
                    "client_id": client.client_id,
                    "connected_at": client.connected_at.isoformat(),
                    "uptime_seconds": int(uptime.total_seconds()),
                    "last_event_at": client.last_event_at.isoformat() if client.last_event_at else None,
                    "queue_size": client.queue.qsize(),
                }
        return None

    def list_clients(self) -> list:
        """
        List all connected clients

        Returns:
            List of client info dicts
        """
        return [self.get_client_info(client.client_id) for client in self.clients]

    async def clear_history(self):
        """Clear event history buffer"""
        self.event_history.clear()
        logger.info("Event history cleared")


# ============================================================================
# Global broadcaster instance
# ============================================================================

# Global broadcaster instance (will be initialized in prometheus_exporter.py)
broadcaster: Optional[EventBroadcaster] = None


def get_broadcaster() -> EventBroadcaster:
    """
    Get global broadcaster instance

    Returns:
        EventBroadcaster instance

    Raises:
        RuntimeError: If broadcaster not initialized
    """
    global broadcaster
    if broadcaster is None:
        raise RuntimeError("EventBroadcaster not initialized. Call init_broadcaster() first.")
    return broadcaster


def init_broadcaster(heartbeat_interval: int = 30, history_size: int = 100) -> EventBroadcaster:
    """
    Initialize global broadcaster instance

    Args:
        heartbeat_interval: Seconds between heartbeats
        history_size: Number of events to keep in history

    Returns:
        Initialized EventBroadcaster instance
    """
    global broadcaster
    broadcaster = EventBroadcaster(
        heartbeat_interval=heartbeat_interval,
        history_size=history_size,
    )
    return broadcaster
