"""Customer base information model corresponding to llm_browser_agent_customer_profile database table."""

from typing import Any  # Arbitrary type hint for to_dict method value type annotation
from typing import Dict  # Dictionary type hint for to_dict method return type annotation

from tortoise import fields  # Tortoise ORM field definitions used for declaring database column types and constraints
from tortoise.models import Model  # Tortoise ORM model base class


class CustomerProfile(Model):
    """Customer base information entity class storing customer identifiers and audit information."""

    id = fields.BigIntField(pk=True)  # Primary key, auto-increment ID
    customer_id = fields.CharField(max_length=255, unique=True)  # Customer unique identifier

    # Audit fields
    created_at = fields.DatetimeField(auto_now_add=True)  # Record creation time
    created_by = fields.CharField(max_length=255)  # Creator identifier
    updated_at = fields.DatetimeField(auto_now=True)  # Last update time
    updated_by = fields.CharField(max_length=255)  # Last updater identifier

    class Meta:
        """Model metadata configuration."""

        table = 'llm_browser_agent_customer_profile'

    def __str__(self) -> str:
        """Return model string representation."""

        return f'<CustomerProfile(id={self.id}, customer_id={self.customer_id})>'

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in vars(self).items():
            if key.startswith('_'):
                continue
            result[key] = value
        return result

