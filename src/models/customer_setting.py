"""Customer setting model mapping to llm_browser_agent_customer_setting database table."""

from decimal import Decimal  # Decimal type used to convert Decimal to float when serializing config objects
from typing import Any  # Generic type hint used for value type annotation in to_dict method
from typing import Dict  # Dictionary type hint used for return value annotation in to_dict method

from tortoise import fields  # Tortoise ORM field definitions used for declaring database column types and constraints
from tortoise.models import Model  # Tortoise ORM base model


class CustomerSetting(Model):
    """Customer setting entity storing versioned history records of customer configurations."""

    id = fields.BigIntField(pk=True)  # Primary key, auto-increment ID
    customer_id = fields.CharField(max_length=255)  # Customer unique identifier
    snapshot_id = fields.IntField()  # Configuration snapshot ID, starts from 1 and increments

    # Large model configuration
    model_name = fields.CharField(max_length=100)  # Large language model name
    model_temperature = fields.DecimalField(max_digits=2, decimal_places=1)  # Random factor
    model_top_p = fields.DecimalField(max_digits=2, decimal_places=1)  # Sampling parameter
    model_api_url = fields.CharField(max_length=255)  # API service URL
    model_api_key = fields.CharField(max_length=255)  # API authentication key
    model_timeout = fields.IntField()  # LLM request timeout duration

    # Agent configuration
    agent_use_vision = fields.BooleanField()  # Whether to enable vision capability
    agent_max_actions_per_step = fields.IntField()  # Maximum actions per step
    agent_max_failures = fields.IntField()  # Maximum consecutive failure count
    agent_step_timeout = fields.IntField()  # Single step execution timeout duration
    agent_use_thinking = fields.BooleanField()  # Whether to enable thinking mode
    agent_calculate_cost = fields.BooleanField()  # Whether to enable cost calculation
    agent_fast_mode = fields.BooleanField()  # Whether to enable fast mode
    agent_demo_mode = fields.BooleanField()  # Whether to enable demo mode

    # Browser configuration
    browser_headless = fields.BooleanField()  # Whether to enable headless mode
    browser_enable_security = fields.BooleanField()  # Whether to enable security features
    browser_use_sandbox = fields.BooleanField()  # Whether to enable sandbox mode

    # Audit fields (creation time only, no updates)
    created_at = fields.DatetimeField(auto_now_add=True)  # Record creation timestamp
    created_by = fields.CharField(max_length=255)  # Creator identifier

    class Meta:
        """Model metadata configuration."""

        table = 'llm_browser_agent_customer_setting'
        unique_together = (('customer_id', 'snapshot_id'),)

    def __str__(self) -> str:
        """Return model string representation."""

        return f'<CustomerSetting(id={self.id}, customer_id={self.customer_id}, snapshot_id={self.snapshot_id})>'

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in vars(self).items():
            if key.startswith('_'):
                continue
            if isinstance(value, Decimal):
                result[key] = float(value)
            else:
                result[key] = value
        return result

