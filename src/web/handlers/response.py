"""Unified JSON response helpers.

This module provides standard meta+data response shapes shared by all HTTP handlers.
"""

from dataclasses import asdict  # Dataclass conversion helper for serializing response objects to dictionaries
from dataclasses import dataclass  # Dataclass decorator for concise response schema definitions
from typing import Any  # Generic type hint for business payload values in response bodies
from typing import ClassVar  # Class variable type hint for defining response schema metadata constants


@dataclass
class ResponseMeta:
    """Response metadata providing business code and prompt text in meta field."""

    SUCCESS_CODE: ClassVar[int] = 0  # Success status code constant

    code: int
    text: str


@dataclass
class ResponseData:
    """Unified response body combining meta information and business data payload."""

    meta: ResponseMeta
    data: Any


def success_response(data: Any = None, text: str = 'success') -> dict:
    """Create unified success response dictionary with meta.code fixed to 0.

    Args:
        data: Arbitrary business payload returned in data field, default None indicates no business data.
        text: Success prompt text used by frontend, default is 'success' to avoid hardcoding.

    Returns:
        dict: JSON-serializable dict that can be passed to Tornado RequestHandler.write with meta and data fields.

    Raises:
        None: This function constructs ordinary dicts; encoding errors may still occur during caller serialization.
    """

    return asdict(ResponseData(meta=ResponseMeta(code=ResponseMeta.SUCCESS_CODE, text=text), data=data))


def failure_response(code: int, text: str, data: Any = None) -> dict:
    """Create unified failure response dictionary using business error code and prompt text in meta field.

    Args:
        code: Business error code integer value used by frontend to branch error handling.
        text: Error prompt text string used for user display or logging.
        data: Optional supplementary business payload such as form error details, default None returns only error meta.

    Returns:
        dict: JSON-serializable dict that can be passed to Tornado RequestHandler.write with meta and data fields.

    Raises:
        None: This function constructs ordinary dicts; exception handling should be managed by caller or upper layers.
    """

    return asdict(ResponseData(meta=ResponseMeta(code=code, text=text), data=data))

