"""Task project domain model mapped to llm_browser_agent_task_project database table."""

from decimal import Decimal  # Decimal type used when converting persisted numeric config values for JSON encoding
from typing import Any  # Generic type hint used for dictionary values in serialization helpers
from typing import Dict  # Dictionary type hint used for explicit to_dict return type declarations

from tortoise import fields  # Tortoise ORM field definitions used to describe persistence schema
from tortoise.models import Model  # Tortoise ORM base model used for task project persistence mapping


class TaskProject(Model):
    """Task project entity representing persisted execution configuration for a reusable customer task definition."""

    id = fields.BigIntField(pk=True)  # Primary key, auto-increment identifier for the task project record
    customer_id = fields.CharField(max_length=255)  # Customer unique identifier that owns this task project
    task_prompt = fields.TextField()  # Full task description prompt provided by the customer
    task_digest = fields.CharField(max_length=100)  # Short human readable digest used as a task project summary

    model_name = fields.CharField(max_length=100)  # Language model name associated with this task configuration
    model_temperature = fields.DecimalField(max_digits=2, decimal_places=1)  # Model sampling temperature factor
    model_top_p = fields.DecimalField(max_digits=2, decimal_places=1)  # Model nucleus sampling top_p parameter
    model_api_url = fields.CharField(max_length=255)  # Endpoint base url for calling the configured language model
    model_api_key = fields.CharField(max_length=255)  # Secret api key for authenticating with the language model
    model_timeout = fields.IntField()  # Timeout in seconds for remote model invocations associated with this project

    agent_use_vision = fields.BooleanField()  # Flag indicating whether visual capabilities should be enabled
    agent_max_actions_per_step = fields.IntField()  # Maximum number of actions allowed within a single agent step
    agent_max_failures = fields.IntField()  # Maximum number of consecutive failures tolerated before aborting
    agent_step_timeout = fields.IntField()  # Timeout in seconds for a single agent step execution
    agent_use_thinking = fields.BooleanField()  # Flag indicating whether deliberate thinking mode should be enabled
    agent_calculate_cost = fields.BooleanField()  # Flag indicating whether to calculate and persist execution cost
    agent_fast_mode = fields.BooleanField()  # Flag indicating whether the agent should prefer fast execution behavior
    agent_demo_mode = fields.BooleanField()  # Flag indicating whether the agent should operate in demonstration mode

    browser_headless = fields.BooleanField()  # Flag indicating whether the browser runs without a visible window
    browser_enable_security = fields.BooleanField()  # Flag for enabling additional browser level security measures
    browser_use_sandbox = fields.BooleanField()  # Flag indicating whether browser sandbox mode should be enabled

    created_at = fields.DatetimeField(auto_now_add=True)  # Creation timestamp for auditing when the project was added
    created_by = fields.CharField(max_length=255)  # Identifier of the principal that originally created the project
    updated_at = fields.DatetimeField(auto_now=True)  # Last modification timestamp reflecting most recent changes
    updated_by = fields.CharField(max_length=255)  # Identifier of the principal that last updated the project record

    class Meta:
        """Model level metadata configuration describing the underlying database table mapping."""

        table = 'llm_browser_agent_task_project'

    def __str__(self) -> str:
        """Return a concise string representation for logging and debugging."""

        return f'<TaskProject(id={self.id}, digest={self.task_digest})>'

    def to_dict(self) -> Dict[str, Any]:
        """Convert the task project instance into a plain dictionary suitable for JSON serialization."""

        result_dict: Dict[str, Any] = {}
        for attribute_name, attribute_value in vars(self).items():
            if attribute_name.startswith('_'):
                continue
            if isinstance(attribute_value, Decimal):
                result_dict[attribute_name] = float(attribute_value)
            else:
                result_dict[attribute_name] = attribute_value
        return result_dict

