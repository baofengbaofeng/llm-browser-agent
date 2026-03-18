"""Natural language instruction parsing handler receiving browser submitted text and returning structured plans."""

from __future__ import annotations  # Enable postponed evaluation of annotations

import logging  # Logging module for recording instruction parsing related operation logs

from apps.customer.customer_profile import CustomerInterceptor  # Customer context interceptor for request customer_id
from apps.instruct.instruct import InstructParse  # Instruction parser converting natural language text into plan string
from apps.instruct.instruct import InstructParseError  # Custom exception thrown on parse failures, converted to errors
from web.handlers.base_handler import BaseHandler  # Base handler providing unified write_error and error translation
from web.handlers.base_handler import BaseHandlerError  # Custom business error type with error code and HTTP status
from web.handlers.base_handler import ERROR_INSTRUCT_EMPTY  # Error code when instruction is empty or missing
from web.handlers.base_handler import ERROR_INTERNAL_ERROR  # General error code for internal unknown exceptions
from web.handlers.base_handler import parse_json_body  # JSON request body parsing helper raising BaseHandlerError
from web.handlers.response import success_response  # Success response constructor building unified successful JSON
from core.security.security import SecurityMixin  # Security response header mixin adding generic security headers

_LOGGER = logging.getLogger(__name__)


class InstructTaskSubmitHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Instruction parsing handler parsing browser submitted text into structured instructions without task creation."""

    async def post(self) -> None:
        """Handle POST request by reading instruction text from body, parsing it, and returning success and payload."""

        payload = parse_json_body(self)
        instruction = (payload.get('instruction') if isinstance(payload, dict) else None) or ''
        instruction = instruction.strip() if isinstance(instruction, str) else ''
        if not instruction:
            raise BaseHandlerError(ERROR_INSTRUCT_EMPTY)

        try:
            payload_str = await InstructParse().parse(instruction)
        except InstructParseError as error:
            _LOGGER.warning('Instruct parse failed: %s', error)
            raise BaseHandlerError(
                ERROR_INSTRUCT_EMPTY if 'empty' in str(error).lower() else ERROR_INTERNAL_ERROR
            ) from error
        except Exception as error:
            _LOGGER.error('Instruct parse error: %s', error)
            raise BaseHandlerError(ERROR_INTERNAL_ERROR) from error

        self.write(success_response(data={'success': True, 'payload': payload_str}))

