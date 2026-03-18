"""Unit tests for CustomerProfileModule, verifying create and query behaviors match expectations."""

from __future__ import annotations  # Enable postponed evaluation of annotations to support forward reference typing

import asyncio  # Async execution module, used to run async methods in synchronous tests
from typing import Any  # Generic type hint, used for type annotations and assertion helpers

from apps.customer.customer_profile import CustomerProfileModule  # Module under test, provides customer profile ops
from models.customer_profile import CustomerProfile  # Tortoise ORM customer profile model class


class _FakeQuery:
    """Simplified fake object replacing Tortoise QuerySet, provides async interfaces for first/exists."""

    def __init__(self, profile: Any, exists_flag: bool) -> None:
        self._profile = profile
        self._exists_flag = exists_flag

    async def first(self) -> Any:
        """Return the preset profile object."""

        return self._profile

    async def exists(self) -> bool:
        """Return the preset boolean existence flag."""

        return self._exists_flag


async def _run(coro):
    """Utility function to simplify running a single coroutine in tests."""

    return await coro


def test_create_profile_uses_uuid_and_sets_created_by() -> None:
    """Verify that create_profile calls CustomerProfile.create with UUID as customer_id and syncs audit fields."""

    created_kwargs: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        created_kwargs.update(kwargs)
        return type('ProfileStub', (), kwargs)()

    original_create = CustomerProfile.create
    CustomerProfile.create = staticmethod(fake_create)  # type: ignore[assignment]

    try:
        profile = asyncio.run(_run(CustomerProfileModule.create_profile()))

        assert isinstance(profile, object)
        assert 'customer_id' in created_kwargs
        assert created_kwargs['customer_id']
        assert created_kwargs['created_by'] == created_kwargs['customer_id']
        assert created_kwargs['updated_by'] == created_kwargs['customer_id']
    finally:
        CustomerProfile.create = original_create  # type: ignore[assignment]


def test_select_profile_raises_on_invalid_customer_id() -> None:
    """Verify that select_profile raises ValueError when customer_id is None or empty string."""

    for invalid in (None, '', '   '):
        try:
            asyncio.run(_run(CustomerProfileModule.select_profile(invalid)))  # type: ignore[arg-type]
            assert False, f'select_profile should raise ValueError for invalid customer_id={invalid!r}'
        except ValueError as error:
            assert error is not None


def test_select_profile_returns_profile_or_none() -> None:
    """Verify that select_profile returns Profile instance or None when record exists or not exists."""

    original_filter = CustomerProfile.filter

    class StubProfile:
        def __init__(self, customer_id: str) -> None:
            self.customer_id = customer_id

    try:
        # Scenario 1: return profile when record exists
        profile_obj = StubProfile('customer-1')

        def fake_filter_existing(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(profile_obj, True)

        CustomerProfile.filter = staticmethod(fake_filter_existing)  # type: ignore[assignment]

        result = asyncio.run(_run(CustomerProfileModule.select_profile('customer-1')))
        assert result is profile_obj

        # Scenario 2: return None when record does not exist
        def fake_filter_missing(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(None, False)

        CustomerProfile.filter = staticmethod(fake_filter_missing)  # type: ignore[assignment]

        result_none = asyncio.run(_run(CustomerProfileModule.select_profile('customer-2')))
        assert result_none is None
    finally:
        CustomerProfile.filter = original_filter  # type: ignore[assignment]


def test_exists_profile_raises_on_invalid_customer_id() -> None:
    """Verify that exists_profile raises ValueError when customer_id is None or empty string."""

    for invalid in (None, '', '   '):
        try:
            asyncio.run(_run(CustomerProfileModule.exists_profile(invalid)))  # type: ignore[arg-type]
            assert False, f'exists_profile should raise ValueError for invalid customer_id={invalid!r}'
        except ValueError as error:
            assert error is not None


def test_exists_profile_true_and_false_cases() -> None:
    """Verify that exists_profile returns True or False when record exists or not exists."""

    original_filter = CustomerProfile.filter

    try:
        def fake_filter_true(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(object(), True)

        CustomerProfile.filter = staticmethod(fake_filter_true)  # type: ignore[assignment]
        exists_result = asyncio.run(_run(CustomerProfileModule.exists_profile('customer-1')))
        assert exists_result is True

        def fake_filter_false(*args: Any, **kwargs: Any) -> _FakeQuery:
            return _FakeQuery(None, False)

        CustomerProfile.filter = staticmethod(fake_filter_false)  # type: ignore[assignment]
        not_exists_result = asyncio.run(_run(CustomerProfileModule.exists_profile('customer-2')))
        assert not_exists_result is False
    finally:
        CustomerProfile.filter = original_filter  # type: ignore[assignment]

