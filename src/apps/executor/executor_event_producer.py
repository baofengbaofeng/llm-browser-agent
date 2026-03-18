"""Executor event producer module, provides event writing and distribution functionality."""

from apps.executor.executor_event import ExecutorEventPayload  # Executor event payload data class
from apps.executor.executor_event_delivery import ExecutorEventDelivery  # Executor event delivery class


class ExecutorEventProducer:
    """Executor event producer, writes events to delivery system for broadcasting."""

    def __init__(self, delivery: ExecutorEventDelivery) -> None:
        """Initialize the event producer."""

        self._delivery = delivery  # Reference to event delivery system

    async def push(self, event: ExecutorEventPayload) -> None:
        """Write event to delivery system for broadcasting."""

        await self._delivery.handle(event)

