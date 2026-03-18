"""Executor event delivery module providing callback-based event subscription and real-time delivery functionality."""

from __future__ import annotations  # Enable forward reference type annotations

import asyncio  # Async IO support module providing async locks and coroutines
import logging  # Logging module for recording delivery operations and errors
from abc import ABC  # Abstract base class module for defining abstract interfaces
from abc import abstractmethod  # Abstract method decorator marking methods that must be implemented by subclasses
import threading  # Thread lock used to protect handler registry updates across async and sync call sites safely
from typing import Awaitable  # Awaitable type hint used for async delivery calls that may run in an event loop
from typing import Callable  # Callable type hint used for registering async listeners for event notifications safely
from typing import Dict  # Dict type hint used for storing payload fields and metadata for event delivery
from typing import List  # List type hint used for maintaining an ordered in-memory event buffer for playback

from apps.executor.executor_event import ExecutorEventPayload  # Executor event payload data class

_LOGGER = logging.getLogger(__name__)

ExecutorEventHandler = Callable[[ExecutorEventPayload], Awaitable[None]]  # Event handler callback type alias


class ExecutorEventDelivery(ABC):
    """Executor event delivery abstract base class defining callback-based event subscription interfaces."""

    @property
    @abstractmethod
    def delivery_id(self) -> str:
        """Get delivery ID."""

        pass

    @abstractmethod
    async def handle(self, event: ExecutorEventPayload) -> None:
        """Dispatch event to all registered handlers."""

        pass

    @abstractmethod
    def attach_handler(self, handler_id: str, handler: ExecutorEventHandler) -> None:
        """Attach event handler."""

        pass

    @abstractmethod
    def detach_handler(self, handler_id: str) -> bool:
        """Detach event handler."""

        pass

    @abstractmethod
    async def destroy(self) -> None:
        """Destroy delivery and clean up all resources."""

        pass


class LocalMemoryExecutorEventDelivery(ExecutorEventDelivery):
    """Local memory event delivery implementation supporting single-producer multi-consumer event broadcasting."""

    def __init__(self, delivery_id: str) -> None:
        """Initialize local memory event delivery."""

        self._delivery_id = delivery_id  # Delivery unique identifier
        self._handlers: Dict[str, ExecutorEventHandler] = {}  # Registered event handlers dictionary
        self._handlers_lock = threading.Lock()  # Thread-safe lock protecting handler registry and snapshots

    @property
    def delivery_id(self) -> str:
        """Get delivery ID."""

        return self._delivery_id

    async def handle(self, event: ExecutorEventPayload) -> None:
        """Dispatch event to all registered handlers."""

        _LOGGER.info(
            'Dispatching event type %s to %s handlers in delivery %s',
            event.event_type.name,
            len(self._handlers),
            self._delivery_id
        )
        with self._handlers_lock:
            handlers: List[ExecutorEventHandler] = list(self._handlers.values())
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                _LOGGER.error('Failed to dispatch event to handler: %s', e)

    def attach_handler(self, handler_id: str, handler: ExecutorEventHandler) -> None:
        """Attach event handler."""

        with self._handlers_lock:
            self._handlers[handler_id] = handler
        _LOGGER.info('Attached handler %s to delivery %s', handler_id, self._delivery_id)

    def detach_handler(self, handler_id: str) -> bool:
        """Detach event handler."""

        with self._handlers_lock:
            if handler_id in self._handlers:
                del self._handlers[handler_id]
                _LOGGER.info('Detached handler %s from delivery %s', handler_id, self._delivery_id)
                return True
            return False

    async def destroy(self) -> None:
        """Destroy delivery and clean up all resources."""

        with self._handlers_lock:
            self._handlers.clear()
            _LOGGER.info('ExecutorEventDelivery %s destroyed', self._delivery_id)

