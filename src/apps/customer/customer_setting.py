"""Customer configuration settings service.

Provides versioned customer setting management and task plan configuration persistence helpers.
"""

from dataclasses import dataclass  # Dataclass decorator used for request DTO definitions with explicit field mapping
from typing import Any  # Generic type hint used for dictionary payload values returned by request serialization

from tortoise.exceptions import IntegrityError  # Unique constraint exception type for concurrent conflict retry control

from models.customer_setting import CustomerSetting  # Customer configuration setting model class


@dataclass(slots=True)
class CustomerSettingRequest:
    """Customer configuration request data mapping one-to-one with CustomerSetting model fields."""

    model_name: str
    model_temperature: float
    model_top_p: float
    model_api_url: str
    model_api_key: str
    model_timeout: int

    agent_use_vision: bool
    agent_max_actions_per_step: int
    agent_max_failures: int
    agent_step_timeout: int
    agent_use_thinking: bool
    agent_calculate_cost: bool
    agent_fast_mode: bool
    agent_demo_mode: bool

    browser_headless: bool
    browser_enable_security: bool
    browser_use_sandbox: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration snapshot data to dictionary for ORM write operations."""

        return {
            'model_name': self.model_name,
            'model_temperature': self.model_temperature,
            'model_top_p': self.model_top_p,
            'model_api_url': self.model_api_url,
            'model_api_key': self.model_api_key,
            'model_timeout': self.model_timeout,
            'agent_use_vision': self.agent_use_vision,
            'agent_max_actions_per_step': self.agent_max_actions_per_step,
            'agent_max_failures': self.agent_max_failures,
            'agent_step_timeout': self.agent_step_timeout,
            'agent_use_thinking': self.agent_use_thinking,
            'agent_calculate_cost': self.agent_calculate_cost,
            'agent_fast_mode': self.agent_fast_mode,
            'agent_demo_mode': self.agent_demo_mode,
            'browser_headless': self.browser_headless,
            'browser_enable_security': self.browser_enable_security,
            'browser_use_sandbox': self.browser_use_sandbox,
        }


class CustomerSettingModule:
    """Customer setting module handling versioned configuration saving, querying, and history operations."""

    @staticmethod
    async def get_next_snapshot_id(customer_id: str) -> int:
        """Get next snapshot_id for specified customer, returning 1 if no history exists."""

        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')

        latest = await CustomerSetting.filter(
            customer_id=customer_id
        ).order_by('-snapshot_id').first()

        if latest is None:
            return 1

        return latest.snapshot_id + 1

    @staticmethod
    async def create_setting(customer_id: str, setting: CustomerSettingRequest) -> CustomerSetting:
        """Create customer configuration setting by inserting a new record with incremented snapshot_id."""

        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')
        if setting is None:
            raise ValueError('setting must not be None')

        max_retries = 3
        latest_error: IntegrityError | None = None

        for attempt in range(1, max_retries + 1):
            snapshot_id = await CustomerSettingModule.get_next_snapshot_id(customer_id)

            try:
                result = await CustomerSetting.create(
                    customer_id=customer_id,
                    snapshot_id=snapshot_id,
                    created_by=customer_id,
                    **setting.to_dict()
                )

                return result
            except IntegrityError as error:
                latest_error = error

        raise latest_error if latest_error is not None else RuntimeError(
            'Failed to create customer setting after retries'
        )

    @staticmethod
    async def select_setting_latest(customer_id: str) -> CustomerSetting | None:
        """Get customer latest configuration setting record, returning None when not existent."""

        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')

        return await CustomerSetting.filter(
            customer_id=customer_id
        ).order_by('-snapshot_id').first()

    @staticmethod
    async def select_setting_by_snapshot_id(customer_id: str, snapshot_id: int) -> CustomerSetting | None:
        """Get specific version configuration record based on snapshot_id, returning None when not existent."""

        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')
        if snapshot_id <= 0:
            raise ValueError('snapshot_id must be a positive integer')

        return await CustomerSetting.filter(
            customer_id=customer_id,
            snapshot_id=snapshot_id
        ).first()

    @staticmethod
    async def select_setting_history(customer_id: str, page: int = 1, size: int = 20) -> list[CustomerSetting]:
        """Paginated retrieval of customer configuration setting history records, not returning total record count."""

        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')
        if page <= 0:
            raise ValueError('page must be a positive integer')
        if size <= 0:
            raise ValueError('size must be a positive integer')

        query = CustomerSetting.filter(customer_id=customer_id).order_by('-snapshot_id')

        return await query.offset((page - 1) * size).limit(size)

    @staticmethod
    async def amount_setting_history(customer_id: str) -> int:
        """Get customer configuration history total count and return integer count value."""

        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')

        return await CustomerSetting.filter(customer_id=customer_id).count()

    @staticmethod
    async def exists_setting(customer_id: str) -> bool:
        """Check if customer has at least one configuration record, returning True if exists otherwise False."""

        if not customer_id or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')

        return await CustomerSetting.filter(customer_id=customer_id).exists()

