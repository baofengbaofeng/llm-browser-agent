"""Executor event module providing event type definitions and event payload structures."""

from __future__ import annotations  # Enable postponed evaluation of annotations to support forward reference typing

import logging  # Logging module for recording event operations and error information
from dataclasses import dataclass  # Dataclass decorator for creating lightweight data structures
from datetime import datetime  # Datetime class for event timestamps
from typing import Any  # Generic type hint used for flexible event payload structures and optional fields in events
from typing import ClassVar  # ClassVar type hint used for constants on dataclasses without turning into fields
from typing import Dict  # Dict type hint used for mapping event payload key-values for JSON serialization

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutorEventType:
    """Executor event type class defining all supported event types."""

    name: str  # Event type name

    HEARTBEAT: ClassVar[ExecutorEventType]  # Heartbeat event
    WORKSPACE_INITIALIZED: ClassVar[ExecutorEventType]  # Workspace initialization complete event
    BROWSER_INITIALIZED: ClassVar[ExecutorEventType]  # Browser initialization complete event
    BROWSER_DESTROYED: ClassVar[ExecutorEventType]  # Browser destruction event
    MODEL_INITIALIZED: ClassVar[ExecutorEventType]  # Large model initialization complete event
    AGENT_INITIALIZED: ClassVar[ExecutorEventType]  # Agent initialization complete event
    TASK_STARTUP: ClassVar[ExecutorEventType]  # Task startup event
    TASK_RUNNING: ClassVar[ExecutorEventType]  # Task running event
    TASK_SUCCESS: ClassVar[ExecutorEventType]  # Task success event
    TASK_FAILURE: ClassVar[ExecutorEventType]  # Task failure event
    TASK_CANCELLED: ClassVar[ExecutorEventType]  # Task cancellation event
    TASK_RESULT: ClassVar[ExecutorEventType]  # Task result event
    # Chain invocation events
    TASK_CHAIN_STARTED: ClassVar[ExecutorEventType]  # Chain task started event
    TASK_CHAIN_STEP: ClassVar[ExecutorEventType]  # Chain task step change event
    TASK_CHAIN_COMPLETED: ClassVar[ExecutorEventType]  # Chain task completed event
    TASK_CHAIN_CANCELLED: ClassVar[ExecutorEventType]  # Chain task cancelled event

    def __str__(self) -> str:
        return self.name

    _EVENT_TYPES: ClassVar[list[tuple[str, str, str]]] = [
        ('HEARTBEAT', 'heartbeat', 'Heartbeat event'),
        ('WORKSPACE_INITIALIZED', 'workspace_initialized', 'Workspace initialization complete event'),
        ('BROWSER_INITIALIZED', 'browser_initialized', 'Browser initialization complete event'),
        ('BROWSER_DESTROYED', 'browser_destroyed', 'Browser destruction event'),
        ('MODEL_INITIALIZED', 'model_initialized', 'Large model initialization complete event'),
        ('AGENT_INITIALIZED', 'agent_initialized', 'Agent initialization complete event'),
        ('TASK_STARTUP', 'task_startup', 'Task startup event'),
        ('TASK_RUNNING', 'task_running', 'Task running event'),
        ('TASK_SUCCESS', 'task_success', 'Task success event'),
        ('TASK_FAILURE', 'task_failure', 'Task failure event'),
        ('TASK_CANCELLED', 'task_cancelled', 'Task cancellation event'),
        ('TASK_RESULT', 'task_result', 'Task result event'),
        # Chain invocation events
        ('TASK_CHAIN_STARTED', 'task_chain_started', 'Chain task started event'),
        ('TASK_CHAIN_STEP', 'task_chain_step', 'Chain task step change event'),
        ('TASK_CHAIN_COMPLETED', 'task_chain_completed', 'Chain task completed event'),
        ('TASK_CHAIN_CANCELLED', 'task_chain_cancelled', 'Chain task cancelled event'),
    ]

    @classmethod
    def initialize_instances(cls) -> None:
        """Initialize class-level event type instances and mappings."""

        cls._EVENT_TYPE_MAP = {}
        for attr_name, event_name, _ in cls._EVENT_TYPES:
            instance = cls(event_name)
            setattr(cls, attr_name, instance)
            cls._EVENT_TYPE_MAP[event_name] = instance


ExecutorEventType.initialize_instances()  # Initialize event type instances


@dataclass
class ExecutorEventPayload:
    """Executor event payload data class containing complete event information."""

    task_id: str  # Task unique identifier
    event_type: ExecutorEventType  # Event type
    event_data: str  # Event data string
    event_time: datetime  # Event timestamp

    _EVENT_TYPE_MAP: ClassVar[Dict[str, ExecutorEventType]] = {}  # Event type mapping for deserialization

    def serialize(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""

        return {
            'task_id': self.task_id,
            'event_type': self.event_type.name,
            'event_data': self.event_data,
            'event_time': self.event_time.isoformat()
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ExecutorEventPayload:
        """Deserialize event from dictionary."""

        return cls(
            task_id=data['task_id'],
            event_type=cls._EVENT_TYPE_MAP.get(data['event_type'], ExecutorEventType(data['event_type'])),
            event_data=data['event_data'],
            event_time=datetime.fromisoformat(data['event_time'])
        )

