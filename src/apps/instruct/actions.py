"""Instruction action model module: define engine-agnostic step types and structures for parsed execution plans."""

from __future__ import annotations  # Enable postponed evaluation of annotations for forward reference support

from enum import Enum  # Enumeration support, used to define constrained sets of allowed instruction action types
from typing import Any  # Generic type support, used for representing extension fields interoperating with external data

from pydantic import BaseModel  # Data validation base model, used to guarantee field level type safety and completeness


class InstructActionType(str, Enum):
    """Instruction action type enumeration describing executable step kinds independent from concrete engine choices."""

    NAVIGATE = 'navigate'
    CLICK = 'click'
    TYPE = 'type'
    SCROLL = 'scroll'
    WAIT = 'wait'
    SCREENSHOT = 'screenshot'
    EXTRACT = 'extract'
    HOVER = 'hover'
    PRESS = 'press'


class InstructAction(BaseModel):
    """Instruction action data model describing all required fields for mapping a single step to execution engines."""

    index: int  # Sequential step index starting from one to keep execution order semantics and user facing clarity
    type: InstructActionType  # Instruction action type limited to the enumeration to avoid ambiguous action semantics
    page: str | None = None  # Optional logical page identifier supporting multi page scenarios and later extensions
    selector: str | None = None  # Optional element selector whose necessity depends on the concrete action type usage
    url: str | None = None  # Optional location field used by navigation oriented actions to specify the destination
    text: str | None = None  # Optional text field for actions that need textual content such as search or form input
    key: str | None = None  # Optional key name for keyboard driven actions such as confirmations or shortcuts
    direction: str | None = None  # Optional scroll direction such as up or down used for semantic scrolling intents
    distance: int | None = None  # Optional scroll distance in pixels enabling fine grained control over movement length
    wait_for: str | None = None  # Optional waiting condition which can be a selector or a human readable state hint
    screenshot_path: str | None = None  # Optional screenshot output path when the step requires persisted visual output
    description: str | None = None  # Optional human readable description written in the user language for plan review
    extra: dict[str, Any] | None = None  # Optional extension payload for engine or business specific additional fields

