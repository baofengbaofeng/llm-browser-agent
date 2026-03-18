"""Unit tests for CustomerSettingModule and CustomerSettingRequest classes."""

from __future__ import annotations  # Enable postponed evaluation of annotations to support forward reference typing

import asyncio  # Async execution module, used to run async methods in synchronous tests
from typing import Any  # Generic type hint, used for type annotations and assertion helpers

from tortoise.exceptions import IntegrityError  # Unique constraint violation exception, used for concurrent retry tests

from apps.customer.customer_setting import CustomerSettingModule  # Module under test, provides customer settings ops
from apps.customer.customer_setting import CustomerSettingRequest  # Customer setting request data class
from models.customer_setting import CustomerSetting  # Tortoise ORM customer setting model class


class _FakeQuery:
    """Simplified fake object replacing Tortoise QuerySet with first/exists/count/offset/limit async interfaces."""

    def __init__(
        self,
        first_result: Any = None,
        exists_flag: bool = False,
        total_count: int = 0,
        items: list[Any] | None = None,
    ) -> None:
        self._first_result = first_result
        self._exists_flag = exists_flag
        self._total_count = total_count
        self._items = items or []

    # Chained call support: order_by / offset / limit return self
    def order_by(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def offset(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    def limit(self, *args: Any, **kwargs: Any) -> "_FakeQuery":
        return self

    async def first(self) -> Any:
        """Return the preset first record result."""

        return self._first_result

    async def exists(self) -> bool:
        """Return the preset boolean existence flag."""

        return self._exists_flag

    async def count(self) -> int:
        """Return the preset total record count."""

        return self._total_count

    # Used for select_setting_history to return list of records
    def __aiter__(self):
        async def _iter():
            for item in self._items:
                yield item

        return _iter()


async def _run(coro):
    """Utility function to simplify running a single coroutine in tests."""

    return await coro


def test_customer_setting_request_to_dict_contains_all_fields() -> None:
    """Verify that CustomerSettingRequest.to_dict includes and correctly maps all fields."""

    request = CustomerSettingRequest(
        model_name="gpt-test",
        model_temperature=0.5,
        model_top_p=0.9,
        model_api_url="http://example.com",
        model_api_key="secret",
        model_timeout=30,
        agent_use_vision=True,
        agent_max_actions_per_step=10,
        agent_max_failures=3,
        agent_step_timeout=60,
        agent_use_thinking=False,
        agent_calculate_cost=True,
        agent_fast_mode=False,
        agent_demo_mode=False,
        browser_headless=True,
        browser_enable_security=True,
        browser_use_sandbox=True,
    )

    as_dict = request.to_dict()

    assert as_dict["model_name"] == "gpt-test"
    assert as_dict["model_temperature"] == 0.5
    assert as_dict["model_top_p"] == 0.9
    assert as_dict["model_api_url"] == "http://example.com"
    assert as_dict["model_api_key"] == "secret"
    assert as_dict["model_timeout"] == 30
    assert as_dict["agent_use_vision"] is True
    assert as_dict["agent_max_actions_per_step"] == 10
    assert as_dict["agent_max_failures"] == 3
    assert as_dict["agent_step_timeout"] == 60
    assert as_dict["agent_use_thinking"] is False
    assert as_dict["agent_calculate_cost"] is True
    assert as_dict["agent_fast_mode"] is False
    assert as_dict["agent_demo_mode"] is False
    assert as_dict["browser_headless"] is True
    assert as_dict["browser_enable_security"] is True
    assert as_dict["browser_use_sandbox"] is True


def test_get_next_snapshot_id_raises_on_invalid_customer_id() -> None:
    """Verify that get_next_snapshot_id raises ValueError when customer_id is invalid."""

    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(CustomerSettingModule.get_next_snapshot_id(invalid)))  # type: ignore[arg-type]
            assert False, f"get_next_snapshot_id should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None


def test_get_next_snapshot_id_returns_1_when_no_history() -> None:
    """Verify that get_next_snapshot_id returns 1 when no history exists."""

    original_filter = CustomerSetting.filter

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(first_result=None)

        CustomerSetting.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        result = asyncio.run(_run(CustomerSettingModule.get_next_snapshot_id("customer-1")))
        assert result == 1
    finally:
        CustomerSetting.filter = original_filter  # type: ignore[assignment]


def test_get_next_snapshot_id_returns_latest_plus_one() -> None:
    """Verify that get_next_snapshot_id returns max snapshot_id + 1 when history exists."""

    original_filter = CustomerSetting.filter

    class StubSetting:
        def __init__(self, snapshot_id: int) -> None:
            self.snapshot_id = snapshot_id

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(first_result=StubSetting(3))

        CustomerSetting.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        result = asyncio.run(_run(CustomerSettingModule.get_next_snapshot_id("customer-1")))
        assert result == 4
    finally:
        CustomerSetting.filter = original_filter  # type: ignore[assignment]


def test_create_setting_raises_on_invalid_args() -> None:
    """Verify that create_setting raises ValueError for invalid customer_id and empty setting."""

    request = CustomerSettingRequest(
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

    # Invalid customer_id
    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(CustomerSettingModule.create_setting(invalid, request)))  # type: ignore[arg-type]
            assert False, f"create_setting should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None

    # setting is None
    try:
        asyncio.run(_run(CustomerSettingModule.create_setting("customer-1", None)))  # type: ignore[arg-type]
        assert False, "create_setting should raise ValueError when setting is None"
    except ValueError as error:
        assert error is not None


def test_create_setting_succeeds_without_conflict() -> None:
    """Verify that create_setting calls create once and returns result when no unique constraint conflict."""

    created_kwargs: dict[str, Any] = {}

    async def fake_get_next_snapshot_id(customer_id: str) -> int:
        return 10

    async def fake_create(**kwargs: Any) -> Any:
        created_kwargs.update(kwargs)
        return type("SettingStub", (), kwargs)()

    original_get_next_snapshot_id = CustomerSettingModule.get_next_snapshot_id
    original_create = CustomerSetting.create

    request = CustomerSettingRequest(
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

    try:
        CustomerSettingModule.get_next_snapshot_id = staticmethod(fake_get_next_snapshot_id)  # type: ignore[assignment]
        CustomerSetting.create = staticmethod(fake_create)  # type: ignore[assignment]

        result = asyncio.run(_run(CustomerSettingModule.create_setting("customer-1", request)))

        assert isinstance(result, object)
        assert created_kwargs["customer_id"] == "customer-1"
        assert created_kwargs["snapshot_id"] == 10
        assert created_kwargs["created_by"] == "customer-1"
        for key, value in request.to_dict().items():
            assert created_kwargs[key] == value
    finally:
        CustomerSettingModule.get_next_snapshot_id = staticmethod(
            original_get_next_snapshot_id)  # type: ignore[assignment]
        CustomerSetting.create = original_create  # type: ignore[assignment]


def test_create_setting_retries_on_integrity_error_then_succeeds() -> None:
    """Verify that create_setting retries when IntegrityError is triggered and eventually succeeds."""

    calls: list[dict[str, Any]] = []

    async def fake_get_next_snapshot_id(customer_id: str) -> int:
        return 1 + len(calls)

    async def fake_create(**kwargs: Any) -> Any:
        calls.append(kwargs)
        if len(calls) == 1:
            raise IntegrityError("duplicate key")
        return type("SettingStub", (), kwargs)()

    original_get_next_snapshot_id = CustomerSettingModule.get_next_snapshot_id
    original_create = CustomerSetting.create

    request = CustomerSettingRequest(
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

    try:
        CustomerSettingModule.get_next_snapshot_id = staticmethod(fake_get_next_snapshot_id)  # type: ignore[assignment]
        CustomerSetting.create = staticmethod(fake_create)  # type: ignore[assignment]

        result = asyncio.run(_run(CustomerSettingModule.create_setting("customer-1", request)))

        assert len(calls) == 2
        assert result.snapshot_id == 2
    finally:
        CustomerSettingModule.get_next_snapshot_id = staticmethod(
            original_get_next_snapshot_id)  # type: ignore[assignment]
        CustomerSetting.create = original_create  # type: ignore[assignment]


def test_select_setting_latest_validation_and_result() -> None:
    """Verify parameter validation and return result behavior of select_setting_latest."""

    # Parameter validation
    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(CustomerSettingModule.select_setting_latest(invalid)))  # type: ignore[arg-type]
            assert False, f"select_setting_latest should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None

    original_filter = CustomerSetting.filter

    class StubSetting:
        def __init__(self, customer_id: str) -> None:
            self.customer_id = customer_id

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(first_result=StubSetting("customer-1"))

        CustomerSetting.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        result = asyncio.run(_run(CustomerSettingModule.select_setting_latest("customer-1")))
        assert isinstance(result, StubSetting)
        assert result.customer_id == "customer-1"
    finally:
        CustomerSetting.filter = original_filter  # type: ignore[assignment]


def test_select_setting_by_snapshot_id_validation_and_result() -> None:
    """Verify that select_setting_by_snapshot_id validates parameters and returns expected result."""

    # Parameter validation
    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(CustomerSettingModule.select_setting_by_snapshot_id(invalid, 1)))  # type: ignore[arg-type]
            assert False, f"select_setting_by_snapshot_id should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None

    for bad_snapshot in (0, -1):
        try:
            asyncio.run(_run(CustomerSettingModule.select_setting_by_snapshot_id("customer-1", bad_snapshot)))
            assert False, f"select_setting_by_snapshot_id should raise ValueError for snapshot_id={bad_snapshot}"
        except ValueError as error:
            assert error is not None

    original_filter = CustomerSetting.filter

    class StubSetting:
        def __init__(self, snapshot_id: int) -> None:
            self.snapshot_id = snapshot_id

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(first_result=StubSetting(5))

        CustomerSetting.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        result = asyncio.run(_run(CustomerSettingModule.select_setting_by_snapshot_id("customer-1", 5)))
        assert isinstance(result, StubSetting)
        assert result.snapshot_id == 5
    finally:
        CustomerSetting.filter = original_filter  # type: ignore[assignment]


def test_select_setting_history_validation_and_result() -> None:
    """Verify that select_setting_history validates parameters and returns list of records."""

    # Parameter validation
    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(CustomerSettingModule.select_setting_history(invalid)))  # type: ignore[arg-type]
            assert False, f"select_setting_history should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None

    for bad_page in (0, -1):
        try:
            asyncio.run(_run(CustomerSettingModule.select_setting_history("customer-1", page=bad_page)))
            assert False, f"select_setting_history should raise ValueError for page={bad_page}"
        except ValueError as error:
            assert error is not None

    for bad_size in (0, -1):
        try:
            asyncio.run(_run(CustomerSettingModule.select_setting_history("customer-1", size=bad_size)))
            assert False, f"select_setting_history should raise ValueError for size={bad_size}"
        except ValueError as error:
            assert error is not None

    original_filter = CustomerSetting.filter

    class StubSetting:
        def __init__(self, snapshot_id: int) -> None:
            self.snapshot_id = snapshot_id

    class _FakeHistoryQuery:
        """Used to simulate paginated query behavior in select_setting_history."""

        def __init__(self, items: list[Any]) -> None:
            self._items = items

        def order_by(self, *args: Any, **kwargs: Any) -> "_FakeHistoryQuery":
            return self

        def offset(self, *args: Any, **kwargs: Any) -> "_FakeHistoryQuery":
            return self

        async def limit(self, *args: Any, **kwargs: Any) -> list[Any]:
            return self._items

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeHistoryQuery:
            return _FakeHistoryQuery([StubSetting(1), StubSetting(2)])

        CustomerSetting.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        result_list = asyncio.run(_run(CustomerSettingModule.select_setting_history("customer-1", page=1, size=2)))
        assert isinstance(result_list, list)
        assert len(result_list) == 2
        assert isinstance(result_list[0], StubSetting)
    finally:
        CustomerSetting.filter = original_filter  # type: ignore[assignment]


def test_amount_setting_history_validation_and_result() -> None:
    """Verify that amount_setting_history validates customer_id and returns count."""

    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(CustomerSettingModule.amount_setting_history(invalid)))  # type: ignore[arg-type]
            assert False, f"amount_setting_history should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None

    original_filter = CustomerSetting.filter

    try:
        def fake_filter(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(total_count=5)

        CustomerSetting.filter = staticmethod(fake_filter)  # type: ignore[assignment]

        count = asyncio.run(_run(CustomerSettingModule.amount_setting_history("customer-1")))
        assert count == 5
    finally:
        CustomerSetting.filter = original_filter  # type: ignore[assignment]


def test_exists_setting_validation_and_result() -> None:
    """Verify that exists_setting validates customer_id and returns existence flag."""

    for invalid in (None, "", "   "):
        try:
            asyncio.run(_run(CustomerSettingModule.exists_setting(invalid)))  # type: ignore[arg-type]
            assert False, f"exists_setting should raise ValueError for invalid customer_id={invalid!r}"
        except ValueError as error:
            assert error is not None

    original_filter = CustomerSetting.filter

    try:
        def fake_filter_true(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(exists_flag=True)

        CustomerSetting.filter = staticmethod(fake_filter_true)  # type: ignore[assignment]
        exists_result = asyncio.run(_run(CustomerSettingModule.exists_setting("customer-1")))
        assert exists_result is True

        def fake_filter_false(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(exists_flag=False)

        CustomerSetting.filter = staticmethod(fake_filter_false)  # type: ignore[assignment]
        not_exists_result = asyncio.run(_run(CustomerSettingModule.exists_setting("customer-2")))
        assert not_exists_result is False
    finally:
        CustomerSetting.filter = original_filter  # type: ignore[assignment]

