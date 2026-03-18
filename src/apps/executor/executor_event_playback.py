"""Executor event playback module.

Provide event saving and timestamp-based loading functions for historical event replay.
"""

from __future__ import annotations  # Enable postponed annotations for forward reference typing

import asyncio  # Async IO support module providing async locks and coroutines
import logging  # Logging module for recording storage operations and error messages
from abc import ABC  # Abstract base class module for defining abstract interfaces
from abc import abstractmethod  # Abstract method decorator marking methods that must be implemented by subclasses
from typing import List  # List type hint used for storing ordered playback events when replaying executor history
from typing import Optional  # Optional type hint representing values that may be None

from apps.executor.executor_event import ExecutorEventPayload  # Executor event payload data class

_LOGGER = logging.getLogger(__name__)

# Default maximum event count limit
DEFAULT_MAX_EVENTS = 10000


class ExecutorEventPlayback(ABC):
    """Executor event playback abstract base class defining event saving and timestamp-based loading interfaces."""

    @abstractmethod
    async def save(self, event: ExecutorEventPayload) -> None:
        """Save event for replay."""

        pass

    @abstractmethod
    async def load(self, after_timestamp: Optional[float] = None) -> List[ExecutorEventPayload]:
        """Load events after specified timestamp for replay."""

        pass


class LocalMemoryExecutorEventPlayback(ExecutorEventPlayback):
    """Local memory event playback implementation for single task isolated event storage and replay."""

    def __init__(self, max_events: int = DEFAULT_MAX_EVENTS) -> None:
        """Initialize local memory event playback storage."""

        self._events: List[ExecutorEventPayload] = []  # Event list
        self._max_events = max_events  # Maximum event count limit
        self._lock = asyncio.Lock()  # Async lock ensuring thread safety

    async def save(self, event: ExecutorEventPayload) -> None:
        """Save event to local memory for replay."""

        async with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

    async def load(self, after_timestamp: Optional[float] = None) -> List[ExecutorEventPayload]:
        """Load events after specified timestamp from local memory for replay."""

        async with self._lock:
            if after_timestamp:
                return [e for e in self._events if e.timestamp.timestamp() > after_timestamp]
            return self._events.copy()

