"""Executor event consumer module.

Consumers bind to dispatcher to receive events and write to local queue for SSE consumption.
"""

from __future__ import annotations  # Enable postponed annotations for forward references

import asyncio  # Async IO support module, providing async queue and coroutine functionality
import logging  # Logging module, recording consumption operations and error messages
import time  # Time utility module, used for tracking timestamps
from typing import AsyncIterator  # Async iterator type hint
from typing import Awaitable  # Awaitable type hint used for async callbacks that process executor events reliably
from typing import Callable  # Callable type hint used for dependency injection of event handler functions in tests

from apps.executor.executor_event_delivery import ExecutorEventDelivery  # Event delivery interface for attach/detach
from apps.executor.executor_event import ExecutorEventPayload  # Executor event payload dataclass

_LOGGER = logging.getLogger(__name__)

# Consumer default configuration constants
DEFAULT_CONSUMER_TTL = 1800.0  # Default idle timeout (seconds)
DEFAULT_QUEUE_SIZE = 5000  # Default queue size
STREAM_TIMEOUT = 1.0  # Stream consumption timeout (seconds)


class ExecutorEventConsumer:
    """Executor event consumer binding to dispatcher and supporting TTL auto-destruction based on idle time."""

    def __init__(self, consumer_id: str, ttl: float = DEFAULT_CONSUMER_TTL,
        queue_size: int = DEFAULT_QUEUE_SIZE) -> None:
        """Initialize event consumer."""

        self._consumer_id = consumer_id  # Consumer unique identifier (usually corresponding to SSE connection)
        self._local_queue: asyncio.Queue[ExecutorEventPayload] = asyncio.Queue(maxsize=queue_size)  # Local event queue
        self._last_receive_time: float = time.time()  # Last event reception timestamp
        self._active = False  # Consumer active status flag
        self._ttl = ttl  # Idle timeout (seconds), can destroy if no event received beyond this time
        self._on_detach: Callable[[], bool] | None = None  # Callback used to detach handler from delivery safely

    @property
    def consumer_id(self) -> str:
        """Get consumer ID."""

        return self._consumer_id

    def _create_handler(self) -> Callable[[ExecutorEventPayload], Awaitable[None]]:
        """Create event handler callback, used to bind to dispatcher."""

        async def handler(event: ExecutorEventPayload) -> None:
            await self._enqueue(event)
        return handler

    async def attach(self, delivery: ExecutorEventDelivery) -> None:
        """Bind consumer to dispatcher, start receiving events."""

        if self._active:
            raise RuntimeError('Consumer already attached')
        delivery.attach_handler(self._consumer_id, self._create_handler())
        self._on_detach = lambda: delivery.detach_handler(self._consumer_id)
        self._active = True
        _LOGGER.info('Consumer %s attached to delivery', self._consumer_id)

    async def detach(self) -> None:
        """Detach consumer from dispatcher, stop receiving events and cleanup resources."""

        self._active = False
        if self._on_detach:
            self._on_detach()
            self._on_detach = None
        while not self._local_queue.empty():
            try:
                self._local_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        _LOGGER.info('Consumer %s detached from delivery', self._consumer_id)

    def is_idle(self) -> bool:
        """Check if consumer is idle (exceeded TTL without receiving events), can destroy when idle."""

        return time.time() - self._last_receive_time > self._ttl

    async def stream(self) -> AsyncIterator[ExecutorEventPayload]:
        """Stream consume events in local queue, used for SSE."""

        if not self._active:
            raise RuntimeError('Consumer not attached')

        while self._active:
            try:
                event = await asyncio.wait_for(self._local_queue.get(), timeout=STREAM_TIMEOUT)
                yield event
            except asyncio.TimeoutError:
                continue

    async def _enqueue(self, event: ExecutorEventPayload) -> None:
        """Write event to local queue (triggered by dispatcher callback)."""

        if not self._active:
            _LOGGER.debug('Consumer %s is inactive, dropping event', self._consumer_id)
            return
        self._last_receive_time = time.time()
        while self._local_queue.full():
            try:
                self._local_queue.get_nowait()
                _LOGGER.debug('Consumer %s dropped oldest event', self._consumer_id)
            except asyncio.QueueEmpty:
                break
        try:
            self._local_queue.put_nowait(event)
            _LOGGER.debug('Event enqueued to consumer %s', self._consumer_id)
        except asyncio.QueueFull:
            _LOGGER.warning('Consumer %s queue full after dropping', self._consumer_id)

