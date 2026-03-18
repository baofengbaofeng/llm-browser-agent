"""Task execution history application service module for creating, updating and querying history records."""

from __future__ import annotations  # Enable postponed evaluation of annotations to support forward reference typing

from datetime import datetime  # Datetime utilities used for recording execution completion timestamps

from apps.customer.customer_setting import CustomerSettingRequest  # Customer setting snapshot used for history records
from models.task_history import TaskHistory  # Task execution history domain model

EXECUTION_STATUS_PENDING = 'pending'  # Initial status for a submitted task waiting to be processed
EXECUTION_STATUS_SUCCESS = 'success'  # Status used when a task has completed successfully
EXECUTION_STATUS_CANCELLED = 'cancelled'  # Status used when a task has been cancelled by user or system
EXECUTION_STATUS_FAILURE = 'failure'  # Status used when a task has failed due to an error
EXECUTION_STATUS_TIMEOUT = 'timeout'  # Status used when a task has not completed within the allowed time window

EXECUTION_STATUS_ALL = (
    EXECUTION_STATUS_SUCCESS,
    EXECUTION_STATUS_FAILURE,
    EXECUTION_STATUS_CANCELLED,
    EXECUTION_STATUS_TIMEOUT,
    EXECUTION_STATUS_PENDING,
)  # Tuple containing all allowed execution status values for input validation

_TASK_HISTORY_SKIP_KEYS = frozenset({'model_api_key'})


class TaskHistoryModule:
    """Task history application service providing creation, update and query capabilities for history records."""

    @staticmethod
    async def create_task_history(task_id: str, customer_id: str, task_prompt: str, setting: CustomerSettingRequest,
        is_chained: bool = False, chain_session_id: str | None = None,
        chain_step_index: int = 0, chain_step_total: int = 1) -> TaskHistory:
        """Create a new task history record at submission time with configuration snapshot taken from the setting."""

        if not task_id or not task_id.strip():
            raise ValueError('task_id must be a non-empty string')
        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')
        if not task_prompt or not task_prompt.strip():
            raise ValueError('task_prompt must be a non-empty string')
        if setting is None:
            raise ValueError('setting must not be None')
        if is_chained and (not chain_session_id or not chain_session_id.strip()):
            raise ValueError('chain_session_id must be a non-empty string')
        if chain_step_index < 0:
            raise ValueError('chain_step_index must be a positive integer')
        if chain_step_total <= 0:
            raise ValueError('chain_step_total must be a positive integer')

        skipped_keys_setting = {
            setting_key: setting_value
            for setting_key, setting_value in setting.to_dict().items()
            if setting_key not in _TASK_HISTORY_SKIP_KEYS
        }

        result = await TaskHistory.create(
            task_id=task_id,
            customer_id=customer_id,
            task_prompt=task_prompt,
            execution_status=EXECUTION_STATUS_PENDING,
            is_chained=is_chained,
            chain_session_id=chain_session_id or '',
            chain_step_index=chain_step_index,
            chain_step_total=chain_step_total,
            created_by=customer_id,
            updated_by=customer_id,
            **skipped_keys_setting,
        )

        return result

    @staticmethod
    async def update_task_history(task_id: str, customer_id: str, execution_status: str,
        execution_result: str | None = None,
        execution_faulty: str | None = None, execution_duration_ms: int = 0) -> bool:
        """Update an existing task history record when a task has finished execution."""

        history_record = await TaskHistory.filter(task_id=task_id).first()
        if not history_record:
            return False
        history_record.execution_status = execution_status
        history_record.execution_result = execution_result
        history_record.execution_faulty = execution_faulty
        history_record.execution_duration_ms = execution_duration_ms
        history_record.execution_complete_at = datetime.now()
        history_record.updated_by = customer_id
        await history_record.save()

        return True

    @staticmethod
    async def select_task_history_by_id(customer_id: str, pk: int) -> TaskHistory | None:
        """Get task history record by primary key ID."""

        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')
        if not pk or pk <= 0:
            raise ValueError('id must be a positive integer')

        return await TaskHistory.filter(customer_id=customer_id, id=pk).first()

    @staticmethod
    async def select_task_history_by_session_id(customer_id: str, session_id: str) -> list[TaskHistory]:
        """Get all history records for chained tasks."""

        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')
        if not session_id or not session_id.strip():
            raise ValueError('session_id must be a non-empty string')

        query = (TaskHistory.filter(customer_id=customer_id, chain_session_id=session_id)
                 .order_by('chain_step_index'))

        return await query.all()

    @staticmethod
    async def select_task_history_by_task_id(customer_id: str, task_id: str) -> TaskHistory | None:
        """Get task history record by task ID."""

        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')
        if not task_id or not task_id.strip():
            raise ValueError('task_id must be a non-empty string')

        return await TaskHistory.filter(customer_id=customer_id, task_id=task_id).first()

    @staticmethod
    async def select_task_history_list(customer_id: str, execution_status: str | None = None,
        chain_session_id: str | None = None,
        page: int = 1, size: int = 20) -> list[TaskHistory]:
        """Paginated query for task history record list."""

        if page <= 0:
            raise ValueError('page must be a positive integer')
        if size <= 0:
            raise ValueError('size must be a positive integer')

        query = TaskHistory.filter(customer_id=customer_id)

        if execution_status:
            query = query.filter(execution_status=execution_status)

        if chain_session_id:
            query = query.filter(chain_session_id=chain_session_id)

        return await query.offset((page - 1) * size).limit(size).all()

    @staticmethod
    async def amount_task_history_list(customer_id: str, execution_status: str | None = None,
        chain_session_id: str | None = None) -> int:
        """Count total number of task history records matching the conditions."""

        query = TaskHistory.filter(customer_id=customer_id)

        if execution_status:
            query = query.filter(execution_status=execution_status)

        if chain_session_id:
            query = query.filter(chain_session_id=chain_session_id)

        return await query.count()

