"""Unit tests for task_project module, verifying query, count, create and delete behaviors."""

from __future__ import annotations  # Enable postponed evaluation of annotations to support forward reference typing

import asyncio  # Async execution module, used to run async methods in synchronous tests
from typing import Any  # Generic type hint, used for type annotations and assertion helpers

from apps.configuration.configuration import (  # type: ignore[import-untyped]
    DefaultAgentConfig,
    DefaultBrowserConfig,
    DefaultConfig,
    DefaultModelConfig,
)
from apps.customer.customer_setting import CustomerSettingRequest  # type: ignore[import-untyped]
from apps.task.task_project import (  # type: ignore[import-untyped]
    amount_task_project,
    create_task_project,
    delete_task_project,
    select_task_project_list,
)
from models.task_project import TaskProject  # type: ignore[import-untyped]


class _FakeQuery:
    """Simplified fake object replacing Tortoise QuerySet, provides paginated query, count and delete interfaces."""

    def __init__(
        self,
        items: list[Any] | None = None,
        total_count: int = 0,
        deleted: int = 0,
    ) -> None:
        self._items = items or []
        self._total_count = total_count
        self._deleted = deleted

    def order_by(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def offset(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    async def limit(self, *args: Any, **kwargs: Any) -> list[Any]:
        return self._items

    async def count(self) -> int:
        return self._total_count

    async def delete(self) -> int:
        return self._deleted


async def _run(coro):
    """Utility function to simplify running a single coroutine in tests."""

    return await coro


def test_select_task_project_list_validation_and_result() -> None:
    """Verify parameter validation and return list behavior of select_task_project_list."""

    # Parameter validation
    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(select_task_project_list(invalid)))  # type: ignore[arg-type]
            assert False, f"select_task_project_list should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None

    for bad_page in (0, -1):
        try:
            asyncio.run(_run(select_task_project_list("customer-1", page=bad_page)))
            assert False, f"select_task_project_list should raise ValueError for page={bad_page}"
        except ValueError as error:
            assert error is not None

    for bad_size in (0, -1):
        try:
            asyncio.run(_run(select_task_project_list("customer-1", size=bad_size)))
            assert False, f"select_task_project_list should raise ValueError for size={bad_size}"
        except ValueError as error:
            assert error is not None

    original_filter = TaskProject.filter

    class StubTask:
        def __init__(self, task_digest: str) -> None:
            self.task_digest = task_digest

    class _FakeListQuery:
        def __init__(self, items: list[Any]) -> None:
            self._items = items

        def order_by(self, *args: Any, **kwargs: Any) -> "_FakeListQuery":
            return self

        def offset(self, *args: Any, **kwargs: Any) -> "_FakeListQuery":
            return self

        async def limit(self, *args: Any, **kwargs: Any) -> list[Any]:
            return self._items

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeListQuery:
            return _FakeListQuery([StubTask("t1"), StubTask("t2")])

        TaskProject.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        tasks = asyncio.run(_run(select_task_project_list("customer-1", page=1, size=2)))
        assert isinstance(tasks, list)
        assert len(tasks) == 2
        assert isinstance(tasks[0], StubTask)
    finally:
        TaskProject.filter = original_filter  # type: ignore[assignment]


def test_amount_task_project_validation_and_result() -> None:
    """Verify parameter validation and count behavior of amount_task_project."""

    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(amount_task_project(invalid)))  # type: ignore[arg-type]
            assert False, f"amount_task_project should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None

    original_filter = TaskProject.filter

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(total_count=7)

        TaskProject.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        count = asyncio.run(_run(amount_task_project("customer-1")))
        assert count == 7
    finally:
        TaskProject.filter = original_filter  # type: ignore[assignment]


def test_delete_task_project_validation_and_result() -> None:
    """Verify parameter validation and delete result behavior of delete_task_project."""

    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(delete_task_project(invalid, "id-1")))  # type: ignore[arg-type]
            assert False, f"delete_task_project should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None

    for invalid_id in (0, -1):
        try:
            asyncio.run(_run(delete_task_project("customer-1", invalid_id)))
            assert False, f"delete_task_project should raise ValueError for invalid id={invalid_id!r}"
        except ValueError as error:
            assert error is not None

    original_filter = TaskProject.filter

    try:
        def fake_filter_zero(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(deleted=0)

        def fake_filter_one(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(deleted=1)

        # Should return False when deleting 0 records
        TaskProject.filter = staticmethod(fake_filter_zero)  # type: ignore[assignment]
        result_false = asyncio.run(_run(delete_task_project("customer-1", 1)))
        assert result_false is False

        # Should return True when deleting 1 record
        TaskProject.filter = staticmethod(fake_filter_one)  # type: ignore[assignment]
        result_true = asyncio.run(_run(delete_task_project("customer-1", 1)))
        assert result_true is True
    finally:
        TaskProject.filter = original_filter  # type: ignore[assignment]


def test_create_task_project_validation_and_create_args() -> None:
    """Verify parameter validation and database field content of create_task_project."""

    setting = CustomerSettingRequest(
        model_name="m",
        model_temperature=0.1,
        model_top_p=0.9,
        model_api_url="u",
        model_api_key="k",
        model_timeout=1,
        agent_use_vision=True,
        agent_max_actions_per_step=1,
        agent_max_failures=1,
        agent_step_timeout=1,
        agent_use_thinking=False,
        agent_calculate_cost=False,
        agent_fast_mode=False,
        agent_demo_mode=False,
        browser_headless=True,
        browser_enable_security=True,
        browser_use_sandbox=True,
    )

    # Parameter validation
    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(create_task_project(invalid, "d", "p", setting)))  # type: ignore[arg-type]
            assert False, f"create_task_project should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None

    for bad_digest in (None, "", "   "):
        try:
            asyncio.run(_run(create_task_project("customer-1", bad_digest, "p", setting)))  # type: ignore[arg-type]
            assert False, f"create_task_project should raise ValueError for task_digest={bad_digest!r}"
        except ValueError as error:
            assert error is not None

    for bad_prompt in (None, "", "   "):
        try:
            asyncio.run(_run(create_task_project("customer-1", "d", bad_prompt, setting)))  # type: ignore[arg-type]
            assert False, f"create_task_project should raise ValueError for task_prompt={bad_prompt!r}"
        except ValueError as error:
            assert error is not None

    try:
        asyncio.run(_run(create_task_project("customer-1", "d", "p", None)))  # type: ignore[arg-type]
        assert False, "create_task_project should raise ValueError when setting is None"
    except ValueError as error:
        assert error is not None

    # Database field assertions
    created_kwargs: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        created_kwargs.update(kwargs)
        return type("TaskProjectStub", (), kwargs)()

    original_create = TaskProject.create

    try:
        TaskProject.create = staticmethod(fake_create)  # type: ignore[assignment]

        result = asyncio.run(_run(create_task_project("customer-1", "digest", "prompt", setting)))

        assert isinstance(result, object)
        assert created_kwargs["customer_id"] == "customer-1"
        assert created_kwargs["task_digest"] == "digest"
        assert created_kwargs["task_prompt"] == "prompt"
        assert created_kwargs["created_by"] == "customer-1"
        assert created_kwargs["updated_by"] == "customer-1"
        for key, value in setting.to_dict().items():
            assert created_kwargs[key] == value
    finally:
        TaskProject.create = original_create  # type: ignore[assignment]

