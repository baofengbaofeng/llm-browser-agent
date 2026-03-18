"""Executor configuration module defining executor runtime configuration parameter data classes."""

from dataclasses import dataclass  # Data class decorator for creating lightweight configuration classes
from dataclasses import field  # Dataclass field helper used to define defaults for configuration attributes safely


@dataclass
class ExecutorConfiguration:
    """Executor configuration data class containing model, agent, and browser runtime configuration parameters."""

    # Task configuration
    task_prompts: list[str]  # Task description prompt list supporting single-step and multi-step chain tasks

    # Model configuration
    model_name: str  # Large language model name
    model_temperature: float  # Model sampling temperature parameter
    model_top_p: float  # Nucleus sampling parameter controlling generated text diversity
    model_api_url: str  # Model API service address
    model_api_key: str  # Model API authentication key
    model_timeout: int  # LLM request timeout in seconds

    # Agent configuration
    agent_use_vision: bool  # Whether to enable vision capability
    agent_max_actions_per_step: int  # Maximum number of actions per step
    agent_max_failures: int  # Maximum consecutive failure count
    agent_step_timeout: int  # Step execution timeout in seconds
    agent_use_thinking: bool  # Whether to enable thinking mode
    agent_calculate_cost: bool  # Whether to enable cost calculation
    agent_fast_mode: bool  # Whether to enable fast mode
    agent_demo_mode: bool  # Whether to enable demo mode

    # Browser configuration
    browser_headless: bool  # Whether to enable headless mode
    browser_enable_security: bool  # Whether to enable security features
    browser_use_sandbox: bool  # Whether to enable sandbox mode

    # Workspace configuration
    base_working_dir: str = field(default='temp')  # Executor workspace base directory

