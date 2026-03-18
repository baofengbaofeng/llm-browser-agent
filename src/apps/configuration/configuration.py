"""Application configuration module providing config loading, parsing, and in-process singleton caching."""

from __future__ import annotations  # Enable postponed annotations for forward references and cleaner typing

from dataclasses import dataclass  # Dataclass decorator for immutable config objects with generated boilerplate
from typing import Any  # Generic type hint used for config dictionary values and broad return type placeholders

from environment.environment import get_application_config  # App config loader using process cache to avoid repeats
from environment.environment import require_config_bool  # Required bool accessor raising config error on invalid values
from environment.environment import require_config_float  # Required float accessor raising config error on invalid
from environment.environment import require_config_int  # Required int accessor raising config error on missing/invalid
from environment.environment import require_config_value  # Required string accessor raising TomlConfigKeyNotFoundError


@dataclass(frozen=True)
class DefaultModelConfig:
    """Default model configuration including LLM connection, authentication, and sampling parameters."""

    name: str  # Large language model name identifier used for selecting the actual model version and routing
    temperature: float  # Sampling temperature controlling randomness and creativity, typically within 0.0 to 1.0
    top_p: float  # Nucleus sampling parameter limiting cumulative probability mass, typically within 0.0 to 1.0
    api_url: str  # LLM API base URL used to send inference requests and receive model responses
    api_key: str  # API authentication key used for request authorization and quota enforcement
    timeout: int  # LLM request timeout in seconds; requests exceeding this are treated as failures upstream


@dataclass(frozen=True)
class DefaultAgentConfig:
    """Default agent configuration including execution behavior, failure controls, and timeouts."""

    max_actions_per_step: int  # Max actions per step, limiting actions per iteration to avoid runaway loops
    max_failures: int  # Max consecutive failures threshold; exceeding it stops task execution for safety and debugging
    step_timeout: int  # Step execution timeout in seconds; a step exceeding this is treated as timeout and failed
    calculate_cost: bool  # Whether to enable API cost calculation for monitoring and display
    use_vision: bool  # Whether to enable vision capability to interpret screenshots and other image inputs
    use_thinking: bool  # Whether to enable thinking mode where the model may return more verbose reasoning output
    fast_mode: bool  # Whether to enable fast mode, potentially trading accuracy for lower latency
    demo_mode: bool  # Whether to enable demo mode, potentially emitting more process information for demos


@dataclass(frozen=True)
class DefaultBrowserConfig:
    """Default browser automation configuration including headless mode, security policies, and sandbox settings."""

    headless: bool  # Whether to enable headless mode so browser runs in background without UI to save resources
    enable_security: bool  # Whether to enable browser security features such as CSP and XSS protections
    use_sandbox: bool  # Whether to enable browser sandbox mode to isolate browser processes for improved safety


@dataclass(frozen=True)
class DefaultConfig:
    """Full application configuration including model, agent, and browser configuration sections."""

    model: DefaultModelConfig  # LLM configuration including model name, API URL, key, and timeout parameters
    agent: DefaultAgentConfig  # Agent behavior configuration including timeouts, feature switches, and failure policy
    browser: DefaultBrowserConfig  # Browser automation configuration including headless mode and security toggles


_DEFAULT_CONFIG_CACHE: DefaultConfig | None = None  # Default config singleton cache avoiding repeated work


class ConfigurationParseError(Exception):
    """Configuration parse error for missing files, invalid formats, or required keys missing during startup."""

    pass


def _load_raw_config() -> dict[str, Any]:
    """Load raw configuration dictionary from TOML and wrap lower-level exceptions for faster debugging.

    This calls environment.get_application_config to read application configuration from TOML,
    and returns a Python dictionary for subsequent processing.

    Returns:
        dict[str, Any]: Dictionary containing all configuration items.

    Raises:
        ConfigurationParseError: Raised when configuration file does not exist, has invalid format, or read fails.
    """
    try:
        return get_application_config()
    except Exception as error:
        raise ConfigurationParseError(f'Failed to load application configuration: {error}') from error


def _build_default_model_config(config: dict[str, Any]) -> DefaultModelConfig:
    """Build default model configuration and validate required fields exist with correct types.

    Args:
        config: Raw configuration dictionary loaded from TOML.

    Returns:
        DefaultModelConfig: Model configuration object.

    Raises:
        TomlConfigKeyNotFoundError: Raised when required model configuration keys are missing.
    """
    return DefaultModelConfig(
        name=require_config_value(config, 'llm_browser_agent.model.name'),
        temperature=require_config_float(config, 'llm_browser_agent.model.temperature'),
        top_p=require_config_float(config, 'llm_browser_agent.model.top_p'),
        api_url=require_config_value(config, 'llm_browser_agent.model.api_url'),
        api_key=require_config_value(config, 'llm_browser_agent.model.api_key'),
        timeout=require_config_int(config, 'llm_browser_agent.model.timeout'),
    )


def _build_default_agent_config(config: dict[str, Any]) -> DefaultAgentConfig:
    """Build default agent configuration and validate required fields exist with correct types.

    Args:
        config: Raw configuration dictionary loaded from TOML.

    Returns:
        DefaultAgentConfig: Agent configuration object.

    Raises:
        TomlConfigKeyNotFoundError: Raised when required agent configuration keys are missing.
    """
    return DefaultAgentConfig(
        max_actions_per_step=require_config_int(config, 'llm_browser_agent.agent.max_actions_per_step'),
        max_failures=require_config_int(config, 'llm_browser_agent.agent.max_failures'),
        step_timeout=require_config_int(config, 'llm_browser_agent.agent.step_timeout'),
        calculate_cost=require_config_bool(config, 'llm_browser_agent.agent.calculate_cost'),
        use_vision=require_config_bool(config, 'llm_browser_agent.agent.use_vision'),
        use_thinking=require_config_bool(config, 'llm_browser_agent.agent.use_thinking'),
        fast_mode=require_config_bool(config, 'llm_browser_agent.agent.fast_mode'),
        demo_mode=require_config_bool(config, 'llm_browser_agent.agent.demo_mode'),
    )


def _build_default_browser_config(config: dict[str, Any]) -> DefaultBrowserConfig:
    """Build default browser configuration and validate required fields exist with correct types.

    Args:
        config: Raw configuration dictionary loaded from TOML.

    Returns:
        DefaultBrowserConfig: Browser configuration object.

    Raises:
        TomlConfigKeyNotFoundError: Raised when required browser configuration keys are missing.
    """
    return DefaultBrowserConfig(
        headless=require_config_bool(config, 'llm_browser_agent.browser.headless'),
        enable_security=require_config_bool(config, 'llm_browser_agent.browser.enable_security'),
        use_sandbox=require_config_bool(config, 'llm_browser_agent.browser.use_sandbox'),
    )


def get_default_config() -> DefaultConfig:
    """Get default configuration singleton and cache it in-process to avoid repeated parsing and construction.

    Returns:
        DefaultConfig: Full configuration object including model, agent, and browser sub-configs.

    Raises:
        ConfigurationParseError: Raised when configuration file loading fails.
        TomlConfigKeyNotFoundError: Raised when required configuration keys are missing.
    """
    global _DEFAULT_CONFIG_CACHE
    if _DEFAULT_CONFIG_CACHE is not None:
        return _DEFAULT_CONFIG_CACHE

    raw_config = _load_raw_config()
    _DEFAULT_CONFIG_CACHE = DefaultConfig(
        browser=_build_default_browser_config(raw_config),
        model=_build_default_model_config(raw_config),
        agent=_build_default_agent_config(raw_config),
    )
    return _DEFAULT_CONFIG_CACHE

