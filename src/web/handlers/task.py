"""Task related handler module providing API endpoints for task projects and task execution histories."""

from __future__ import annotations  # Enable postponed evaluation of annotations to support forward reference typing

import logging  # Logging utilities used to record operations around task projects and task histories
from typing import List  # List type hint used for handler return value annotations

from apps.customer.customer_profile import CustomerInterceptor  # Customer interceptor injecting customer_id
from apps.customer.customer_setting import CustomerSettingRequest  # Customer configuration request used to build plans
from apps.task.task_history import EXECUTION_STATUS_ALL  # Allowed execution status values used for input validation
from apps.task.task_history import TaskHistoryModule  # Task history application service used by handlers
from apps.task.task_project import create_task_project  # Application service to create task projects
from apps.task.task_project import delete_task_project  # Application service to delete task projects
from apps.task.task_project import select_task_project_list  # Application service to query paginated task projects
from web.handlers.base_handler import BaseHandler  # Base handler providing unified error writing behavior
from web.handlers.base_handler import BaseHandlerError  # Domain specific handler error type with codes and http status
from web.handlers.base_handler import ERROR_INTERNAL_ERROR  # Generic internal error code for unexpected exceptions
from web.handlers.base_handler import ERROR_PARAM_STATUS_INVALID_VALUE  # Error code for invalid execution status
from web.handlers.base_handler import ERROR_TASK_HISTORY_INVALID_ID  # Error code for invalid task history identifier
from web.handlers.base_handler import ERROR_TASK_PROJECT_INVALID_DIGEST  # Error code for invalid task project digest
from web.handlers.base_handler import ERROR_TASK_PROJECT_INVALID_ID  # Error code for invalid task project identifier
from web.handlers.base_handler import ERROR_TASK_PROJECT_INVALID_PROMPT  # Error code for invalid task project prompt
from web.handlers.base_handler import ERROR_TASK_PROJECT_MISSING_DIGEST  # Error code when digest field is missing
from web.handlers.base_handler import ERROR_TASK_PROJECT_MISSING_PROMPT  # Error code when prompt field is missing
from web.handlers.base_handler import ERROR_TASK_PROJECT_MISSING_SETTING  # Error code when setting field is missing
from web.handlers.base_handler import parse_json_body  # Helper for safely parsing JSON request bodies
from web.handlers.base_handler import parse_pagination_params  # Helper for parsing and validating pagination params
from web.handlers.base_handler import validate_setting_dict  # Helper validating and normalizing incoming setting dicts
from web.handlers.response import success_response  # Helper for constructing unified successful response envelopes
from core.security.security import SecurityMixin  # Mixin providing cross cutting security related response headers
from models.task_project import TaskProject  # Task project domain model mapped to llm_browser_agent_task_project

_LOGGER = logging.getLogger(__name__)


class CustomerTaskProjectHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Customer task project handler for paginated listing, creation and deletion of task plans."""

    async def get(self) -> None:
        """Handle GET /api/customer/task/plan/ returning a paginated list of task projects for the current customer."""

        page, size = parse_pagination_params(self)

        result: List[TaskProject] = await select_task_project_list(
            customer_id=self.customer_id,
            page=page,
            size=size,
        )

        self.write(success_response(data=[task.to_dict() for task in result]))

    async def post(self) -> None:
        """Handle POST /api/customer/task/plan/ creating a new task project using digest, prompt and setting payload."""

        payload = parse_json_body(self)

        task_digest = str(payload.get('task_digest') or '').strip()
        task_prompt = str(payload.get('task_prompt') or '').strip()

        if not task_digest:
            raise BaseHandlerError(ERROR_TASK_PROJECT_MISSING_DIGEST)
        if not task_prompt:
            raise BaseHandlerError(ERROR_TASK_PROJECT_MISSING_PROMPT)

        if len(task_digest) > 100:
            raise BaseHandlerError(ERROR_TASK_PROJECT_INVALID_DIGEST)
        if len(task_prompt) > 50_000:
            raise BaseHandlerError(ERROR_TASK_PROJECT_INVALID_PROMPT)

        if 'setting' not in payload:
            raise BaseHandlerError(ERROR_TASK_PROJECT_MISSING_SETTING)

        try:
            result = await create_task_project(
                task_digest=task_digest,
                task_prompt=task_prompt,
                customer_id=self.customer_id,
                setting=CustomerSettingRequest(**validate_setting_dict(payload.get('setting'))),
            )
        except Exception as error:
            _LOGGER.error('Create task project error: %s', error)
            raise BaseHandlerError(ERROR_INTERNAL_ERROR) from error

        self.write(success_response(data=result.to_dict()))

    async def delete(self) -> None:
        """Handle DELETE /api/customer/task/plan/ deleting a specific task project when the id argument is valid."""

        try:
            pk = int(self.get_argument('id'))
        except ValueError as error:
            raise BaseHandlerError(ERROR_TASK_PROJECT_INVALID_ID) from error

        if pk < 1:
            raise BaseHandlerError(ERROR_TASK_PROJECT_INVALID_ID)

        try:
            success = await delete_task_project(self.customer_id, pk)
        except Exception as error:
            _LOGGER.error('Delete task project error: %s', error)
            raise BaseHandlerError(ERROR_INTERNAL_ERROR) from error

        self.write(success_response(data=success))


class TaskHistoryListHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Task history list handler supporting pagination, status filtering and session based filtering."""

    async def get(self) -> None:
        """Handle GET /api/task/history/ returning a paginated list of history records based on query parameters."""

        session_id = self.get_argument('session_id', None)
        sub_status = self.get_argument('status', None)

        page, size = parse_pagination_params(self)

        execution_status = None
        if sub_status:
            if sub_status not in EXECUTION_STATUS_ALL:
                raise BaseHandlerError(ERROR_PARAM_STATUS_INVALID_VALUE)
            execution_status = sub_status

        try:
            items = await TaskHistoryModule.select_task_history_list(
                customer_id=self.customer_id,
                execution_status=execution_status,
                chain_session_id=session_id,
                page=page,
                size=size,
            )
        except Exception as error:
            _LOGGER.error('select task history error: %s', error)
            raise BaseHandlerError(ERROR_INTERNAL_ERROR) from error

        try:
            total = await TaskHistoryModule.amount_task_history_list(
                customer_id=self.customer_id,
                execution_status=execution_status,
                chain_session_id=session_id,
            )
        except Exception as error:
            _LOGGER.error('amount task history error: %s', error)
            raise BaseHandlerError(ERROR_INTERNAL_ERROR) from error

        data = {
            'total': total,
            'items': [item.to_dict() for item in items],
            'page': page,
            'size': size,
        }

        self.write(success_response(data=data))


class TaskHistoryViewHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Task history detail handler returning a single history record when the identifier is valid."""

    async def get(self, pk: str) -> None:
        """Handle GET /api/task/history/{history_id}/ validating path parameters and returning record details."""

        pk_str = (pk or '').strip()
        if not pk_str:
            raise BaseHandlerError(ERROR_TASK_HISTORY_INVALID_ID)

        try:
            pk_int = int(pk_str)
        except ValueError as error:
            raise BaseHandlerError(ERROR_TASK_HISTORY_INVALID_ID) from error

        if pk_int < 1:
            raise BaseHandlerError(ERROR_TASK_HISTORY_INVALID_ID)

        try:
            result = await TaskHistoryModule.select_task_history_by_id(self.customer_id, pk_int)
        except Exception as error:
            _LOGGER.error('select task history error: %s', error)
            raise BaseHandlerError(ERROR_INTERNAL_ERROR) from error

        if not result:
            self.write(success_response(data={}))
        else:
            self.write(success_response(data=result.to_dict()))


class ChainTaskHistoryHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Chained task history handler returning all history records that belong to a single chained session."""

    async def get(self, session_id: str) -> None:
        """Handle GET returning all history records for given chained session identifier with unified error output."""

        try:
            items = await TaskHistoryModule.select_task_history_by_session_id(
                self.customer_id, session_id)
        except Exception as error:
            _LOGGER.error('select task history by session_id error: %s', error)
            raise BaseHandlerError(ERROR_INTERNAL_ERROR) from error

        if not items:
            self.write(success_response(data=[]))
        else:
            self.write(success_response(data=[item.to_dict() for item in items]))

