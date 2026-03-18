"""Task execution history model mapped to llm_browser_agent_task_history database table."""

from typing import Any  # Generic type hint used for values in serialized dictionary representations
from typing import Dict  # Dictionary type hint used for explicit to_dict return type declarations

from tortoise import fields  # Tortoise ORM field definitions used to describe persistence schema
from tortoise.models import Model  # Tortoise ORM base model used for mapping task history to the database


class TaskHistory(Model):
    """Task execution history entity storing request parameters, configuration snapshots, results and timing data."""

    id = fields.BigIntField(pk=True)  # Primary key, auto-increment identifier for the history record
    customer_id = fields.CharField(max_length=255)  # Customer unique identifier that owns this execution record

    task_id = fields.CharField(max_length=255)  # Logical task identifier such as a UUID used to correlate executions
    task_prompt = fields.TextField()  # Original task prompt string submitted when the execution was created

    model_name = fields.CharField(max_length=100)  # Snapshot of the language model name used for this execution
    model_temperature = fields.DecimalField(max_digits=2, decimal_places=1)  # Snapshot of the sampling temperature
    model_top_p = fields.DecimalField(max_digits=2, decimal_places=1)  # Snapshot of the nucleus sampling top_p value
    model_api_url = fields.CharField(max_length=255)  # Snapshot of the language model endpoint base url
    model_timeout = fields.IntField()  # Snapshot of the timeout in seconds used for language model calls

    agent_use_vision = fields.BooleanField()  # Snapshot flag indicating whether visual capabilities were enabled
    agent_max_actions_per_step = fields.IntField()  # Snapshot of the maximum actions allowed per agent step
    agent_max_failures = fields.IntField()  # Snapshot of the maximum consecutive failures tolerated
    agent_step_timeout = fields.IntField()  # Snapshot of the timeout in seconds for each agent step
    agent_use_thinking = fields.BooleanField()  # Snapshot flag indicating whether deliberate thinking was enabled
    agent_fast_mode = fields.BooleanField()  # Snapshot flag indicating whether fast mode was active

    browser_headless = fields.BooleanField()  # Snapshot flag indicating whether the browser ran without a window
    browser_enable_security = fields.BooleanField()  # Snapshot flag indicating whether extra browser security was on
    browser_use_sandbox = fields.BooleanField()  # Snapshot flag indicating whether browser sandboxing was enabled

    execution_status = fields.CharField(max_length=50)  # Current execution status string such as success or failure
    execution_result = fields.TextField()  # Raw execution result payload produced by the automation engine
    execution_faulty = fields.TextField()  # Error information captured when the execution did not complete successfully

    execution_duration_ms = fields.IntField(default=0)  # Total execution duration in milliseconds
    execution_complete_at = fields.DatetimeField()  # Timestamp marking when the execution finished

    is_chained = fields.BooleanField()  # Flag indicating whether this record belongs to a chained multi-step session
    chain_session_id = fields.CharField(max_length=255)  # Identifier for the chained session grouping related tasks
    chain_step_index = fields.IntField(default=0)  # Zero based index representing the position inside the chain
    chain_step_total = fields.IntField(default=1)  # Total number of steps that belong to the same chain session

    created_at = fields.DatetimeField(auto_now_add=True)  # Creation timestamp for auditing when the record was added
    created_by = fields.CharField(max_length=255)  # Identifier of the principal that originally created the record
    updated_at = fields.DatetimeField(auto_now=True)  # Last modification timestamp reflecting most recent updates
    updated_by = fields.CharField(max_length=255)  # Identifier of the principal that last updated this record

    class Meta:
        """Model level metadata configuration describing the underlying database table mapping."""

        table = 'llm_browser_agent_task_history'

    def __str__(self) -> str:
        """Return a concise string representation for logging and debugging."""

        return f'<TaskHistory(id={self.id}, task_id={self.task_id}, status={self.execution_status})>'

    def to_dict(self) -> Dict[str, Any]:
        """Convert the task history instance into a plain dictionary ready for JSON serialization."""

        result_dict: Dict[str, Any] = {}
        for attribute_name, attribute_value in vars(self).items():
            if attribute_name.startswith('_'):
                continue
            result_dict[attribute_name] = attribute_value
        return result_dict

