"""Unit tests for TaskHistoryModule."""

from __future__ import annotations  # Postpone annotation evaluation to simplify typing and avoid runtime import cycles

import asyncio  # Async IO support used for running coroutine-based test helpers and executor module interactions
from datetime import datetime  # Datetime helper used to create stable event timestamps for task history assertions
from typing import Any  # Generic type hint used in fake query objects and helper signatures within unit tests

from apps.customer.customer_setting import CustomerSettingRequest  # type: ignore[import-untyped]
from apps.task.task_history import EXECUTION_STATUS_FAILURE  # type: ignore[import-untyped]
from apps.task.task_history import EXECUTION_STATUS_PENDING  # type: ignore[import-untyped]
from apps.task.task_history import EXECUTION_STATUS_SUCCESS  # type: ignore[import-untyped]
from apps.task.task_history import TaskHistoryModule  # type: ignore[import-untyped]
from models.task_history import TaskHistory  # type: ignore[import-untyped]


class _FakeQuery:
    """Simplified Query object, supports filter/offset/limit/count/all interfaces."""

    def __init__(self, items: list[Any] | None = None, total: int = 0) -> None:
        self._items = items or []
        self._total = total

    def filter(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def order_by(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def offset(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def limit(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    async def all(self) -> list[Any]:
        return self._items

    async def first(self) -> Any | None:
        return self._items[0] if self._items else None

    async def count(self) -> int:
        return self._total


async def _run(coro):
    """Helper to run coroutines in synchronous tests."""

    return await coro


def _build_setting() -> CustomerSettingRequest:
    return CustomerSettingRequest(
        model_name="m",
        model_temperature=0.5,
        model_top_p=0.9,
        model_api_url="u",
        model_api_key="k",
        model_timeout=10,
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


def test_create_task_history_validation_errors() -> None:
    """Verify parameter validation logic of create_task_history."""

    setting = _build_setting()

    # task_id
    for bad in (None, "", "   "):
        try:
            asyncio.run(_run(TaskHistoryModule.create_task_history(bad, "c", "p", setting)))  # type: ignore[arg-type]
            assert False, "expected ValueError for invalid task_id"
        except ValueError:
            pass

    # customer_id
    for bad in (None, "", "   "):
        try:
            asyncio.run(_run(TaskHistoryModule.create_task_history("t", bad, "p", setting)))  # type: ignore[arg-type]
            assert False, "expected ValueError for invalid customer_id"
        except ValueError:
            pass

    # task_prompt
    for bad in (None, "", "   "):
        try:
            asyncio.run(_run(TaskHistoryModule.create_task_history("t", "c", bad, setting)))  # type: ignore[arg-type]
            assert False, "expected ValueError for invalid task_prompt"
        except ValueError:
            pass

    # setting None
    try:
        asyncio.run(_run(TaskHistoryModule.create_task_history("t", "c", "p", None)))  # type: ignore[arg-type]
        assert False, "expected ValueError for setting None"
    except ValueError:
        pass

    # Chained parameters
    try:
        asyncio.run(
            _run(
                TaskHistoryModule.create_task_history(
                    "t",
                    "c",
                    "p",
                    setting,
                    is_chained=True,
                    chain_session_id="",
                )
            )
        )
        assert False, "expected ValueError for empty chain_session_id when is_chained=True"
    except ValueError:
        pass


def test_create_task_history_persists_expected_fields() -> None:
    """Verify field content written by create_task_history."""

    setting = _build_setting()
    created_kwargs: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        created_kwargs.update(kwargs)
        return type("TaskHistoryStub", (), kwargs)()

    original_create = TaskHistory.create

    try:
        TaskHistory.create = staticmethod(fake_create)  # type: ignore[assignment]

        result = asyncio.run(
            _run(
                TaskHistoryModule.create_task_history(
                    "task-1",
                    "customer-1",
                    "prompt text",
                    setting,
                    is_chained=True,
                    chain_session_id="sess-1",
                    chain_step_index=2,
                    chain_step_total=3,
                )
            )
        )

        assert isinstance(result, object)
        assert created_kwargs["task_id"] == "task-1"
        assert created_kwargs["customer_id"] == "customer-1"
        assert created_kwargs["task_prompt"] == "prompt text"
        assert created_kwargs["execution_status"] == EXECUTION_STATUS_PENDING
        assert created_kwargs["is_chained"] is True
        assert created_kwargs["chain_session_id"] == "sess-1"
        assert created_kwargs["chain_step_index"] == 2
        assert created_kwargs["chain_step_total"] == 3
        assert created_kwargs["created_by"] == "customer-1"
        assert created_kwargs["updated_by"] == "customer-1"
        # model_api_key is filtered out
        assert "model_api_key" not in created_kwargs
        for key, value in setting.to_dict().items():
            if key == "model_api_key":
                continue
            assert created_kwargs[key] == value
    finally:
        TaskHistory.create = original_create  # type: ignore[assignment]


def test_update_task_history_returns_false_when_not_found() -> None:
    """Verify that update_task_history returns False when record does not exist."""

    original_filter = TaskHistory.filter

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(items=[])

        TaskHistory.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        ok = asyncio.run(
            _run(
                TaskHistoryModule.update_task_history(
                    task_id="no-such",
                    customer_id="c",
                    execution_status=EXECUTION_STATUS_FAILURE,
                )
            )
        )
        assert ok is False
    finally:
        TaskHistory.filter = original_filter  # type: ignore[assignment]


def test_update_task_history_updates_fields_and_returns_true() -> None:
    """Verify that update_task_history correctly updates fields and returns True."""

    class StubHistory:
        def __init__(self) -> None:
            self.execution_status = ""
            self.execution_result = None
            self.execution_faulty = None
            self.execution_duration_ms = 0
            self.execution_complete_at: datetime | None = None
            self.updated_by = ""

        async def save(self) -> None:  # noqa: D401
            """Mock save, no actual operation."""
            return None

    stub = StubHistory()
    original_filter = TaskHistory.filter

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(items=[stub])

        TaskHistory.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        ok = asyncio.run(
            _run(
                TaskHistoryModule.update_task_history(
                    task_id="t1",
                    customer_id="c1",
                    execution_status=EXECUTION_STATUS_SUCCESS,
                    execution_result="result",
                    execution_faulty="err",
                    execution_duration_ms=123,
                )
            )
        )
        assert ok is True
        assert stub.execution_status == EXECUTION_STATUS_SUCCESS
        assert stub.execution_result == "result"
        assert stub.execution_faulty == "err"
        assert stub.execution_duration_ms == 123
        assert stub.updated_by == "c1"
        assert isinstance(stub.execution_complete_at, datetime)
    finally:
        TaskHistory.filter = original_filter  # type: ignore[assignment]


def test_select_task_history_by_id_validation_and_result() -> None:
    """Verify parameter validation and query result of select_task_history_by_id."""

    # Parameter validation
    for bad_customer in (None, "", "   "):
        try:
            asyncio.run(_run(TaskHistoryModule.select_task_history_by_id(bad_customer, 1)))  # type: ignore[arg-type]
            assert False, "expected ValueError for bad customer_id"
        except ValueError:
            pass

    for bad_id in (0, -1):
        try:
            asyncio.run(_run(TaskHistoryModule.select_task_history_by_id("c1", bad_id)))
            assert False, "expected ValueError for bad id"
        except ValueError:
            pass

    original_filter = TaskHistory.filter
    stub = object()

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(items=[stub])

        TaskHistory.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        result = asyncio.run(_run(TaskHistoryModule.select_task_history_by_id("c1", 1)))
        assert result is stub
    finally:
        TaskHistory.filter = original_filter  # type: ignore[assignment]


def test_select_task_history_by_task_id_validation_and_result() -> None:
    """Verify parameter validation and query result of select_task_history_by_task_id."""

    for bad_customer in (None, "", "   "):
        try:
            asyncio.run(
                _run(TaskHistoryModule.select_task_history_by_task_id(bad_customer, "t1"))  # type: ignore[arg-type]
            )
            assert False, "expected ValueError for bad customer_id"
        except ValueError:
            pass

    for bad in (None, "", "   "):
        try:
            asyncio.run(_run(TaskHistoryModule.select_task_history_by_task_id("c1", bad)))  # type: ignore[arg-type]
            assert False, "expected ValueError for bad task_id"
        except ValueError:
            pass

    original_filter = TaskHistory.filter
    stub = object()

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(items=[stub])

        TaskHistory.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        result = asyncio.run(_run(TaskHistoryModule.select_task_history_by_task_id("c1", "t1")))
        assert result is stub
    finally:
        TaskHistory.filter = original_filter  # type: ignore[assignment]


def test_select_task_history_list_and_amount_task_history_list() -> None:
    """Verify behavior of list query and count interfaces."""

    original_filter = TaskHistory.filter

    class StubHistory:
        def __init__(self, task_id: str) -> None:
            self.task_id = task_id

    items = [StubHistory("t1"), StubHistory("t2")]

    try:
        def fake_filter_for_list(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(items=items, total=len(items))

        TaskHistory.filter = staticmethod(fake_filter_for_list)  # type: ignore[assignment]

        histories = asyncio.run(
            _run(
                TaskHistoryModule.select_task_history_list(
                    customer_id="c1",
                    execution_status=None,
                    chain_session_id=None,
                    page=1,
                    size=2,
                )
            )
        )
        assert len(histories) == 2

        total = asyncio.run(
            _run(
                TaskHistoryModule.amount_task_history_list(
                    customer_id="c1",
                    execution_status=None,
                    chain_session_id=None,
                )
            )
        )
        assert total == len(items)
    finally:
        TaskHistory.filter = original_filter  # type: ignore[assignment]


def test_select_task_history_by_session_id_validation_and_result() -> None:
    """Verify parameter validation and query result of select_task_history_by_session_id."""

    for bad_customer in (None, "", "   "):
        try:
            asyncio.run(
                _run(TaskHistoryModule.select_task_history_by_session_id(
                    bad_customer, "sess-1"))  # type: ignore[arg-type]
            )
            assert False, "expected ValueError for bad customer_id"
        except ValueError:
            pass

    for bad in (None, "", "   "):
        try:
            asyncio.run(_run(TaskHistoryModule.select_task_history_by_session_id("c1", bad)))  # type: ignore[arg-type]
            assert False, "expected ValueError for bad session_id"
        except ValueError:
            pass

    original_filter = TaskHistory.filter
    items = [object(), object()]

    class _FakeOrderQuery(_FakeQuery):
        def order_by(self, *args: Any, **kwargs: Any) -> "_FakeOrderQuery":
            return self

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeOrderQuery:
            return _FakeOrderQuery(items=items)

        TaskHistory.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        histories = asyncio.run(_run(TaskHistoryModule.select_task_history_by_session_id("c1", "sess-1")))
        assert len(histories) == 2
    finally:
        TaskHistory.filter = original_filter  # type: ignore[assignment]

