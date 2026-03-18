"""Task project application service module providing query, creation and deletion operations for customer plans."""

from __future__ import annotations  # Enable postponed evaluation of annotations to support forward reference typing

from typing import List  # List type hint used for returned collections of task project entities

from apps.customer.customer_setting import CustomerSettingRequest  # Customer configuration request used for expansion
from models.task_project import TaskProject  # Task project domain model used for persistence operations


async def select_task_project_list(customer_id: str, page: int = 1, size: int = 50) -> List[TaskProject]:
    """Return a paginated list of task projects for the given customer ordered by creation time descending."""

    if not customer_id or not customer_id.strip():
        raise ValueError('customer_id must be a non-empty string')
    if page <= 0:
        raise ValueError('page must be a positive integer')
    if size <= 0:
        raise ValueError('size must be a positive integer')

    return await (TaskProject.filter(customer_id=customer_id)
        .order_by('-created_at').offset((page - 1) * size).limit(size)
    )


async def amount_task_project(customer_id: str) -> int:
    """Return the total number of task projects for the given customer, validating input arguments."""

    if not customer_id or not customer_id.strip():
        raise ValueError('customer_id must be a non-empty string')

    return await TaskProject.filter(customer_id=customer_id).count()


async def delete_task_project(customer_id: str, pk: int) -> bool:
    """Delete a task project belonging to the given customer and return True when at least one row was removed."""

    if not customer_id or not customer_id.strip():
        raise ValueError('customer_id must be a non-empty string')
    if not pk or pk <= 0:
        raise ValueError('id must be a positive integer')

    deleted_row_count = await TaskProject.filter(id=pk, customer_id=customer_id).delete()
    return deleted_row_count > 0


async def create_task_project(customer_id: str, task_digest: str, task_prompt: str,
    setting: CustomerSettingRequest) -> TaskProject:
    """Create and persist a task project record using the provided customer configuration request as field source."""

    if not customer_id or not customer_id.strip():
        raise ValueError('customer_id must be a non-empty string')
    if not task_digest or not task_digest.strip():
        raise ValueError('task_digest must be a non-empty string')
    if not task_prompt or not task_prompt.strip():
        raise ValueError('task_prompt must be a non-empty string')
    if setting is None:
        raise ValueError('setting must not be None')

    return await TaskProject.create(
        customer_id=customer_id,
        task_digest=task_digest,
        task_prompt=task_prompt,
        created_by=customer_id,
        updated_by=customer_id,
        **setting.to_dict(),
    )

