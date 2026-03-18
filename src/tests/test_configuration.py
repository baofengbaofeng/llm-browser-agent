"""Unit tests for application configuration module, verifying default config structure and field validity."""

from __future__ import annotations  # Enable postponed evaluation of annotations to support forward reference typing

from apps.configuration.configuration import DefaultAgentConfig  # Default agent config data class for field validation
from apps.configuration.configuration import DefaultBrowserConfig  # Default browser config data class for validation
from apps.configuration.configuration import DefaultConfig  # Full config data class for overall structure validation
from apps.configuration.configuration import DefaultModelConfig  # Default model config data class for field validation
from apps.configuration.configuration import get_default_config  # Default config getter used to generate test objects


def _assert_positive_int(value: int, field_name: str) -> None:
    """Assert that the given field is a positive integer, and print field name and value on failure for debugging."""

    assert isinstance(value, int), f'Field {field_name} must be int, got {type(value)!r}'
    assert value > 0, f'Field {field_name} must be positive, got {value!r}'


def test_get_default_config_returns_singleton() -> None:
    """Verify that get_default_config returns a DefaultConfig object with singleton semantics."""

    st1 = get_default_config()
    nd2 = get_default_config()

    assert isinstance(st1, DefaultConfig), 'get_default_config should return DefaultConfig instance'
    assert st1 is nd2, 'get_default_config must return the same singleton instance'


def test_default_model_config_fields() -> None:
    """Verify that DefaultModelConfig field types and key value ranges meet basic constraint requirements."""

    config = get_default_config()
    model: DefaultModelConfig = config.model

    assert isinstance(model.name, str) and model.name, 'model.name must be non-empty string'
    assert isinstance(model.api_url, str) and model.api_url, 'model.api_url must be non-empty string'
    assert isinstance(model.api_key, str) and model.api_key, 'model.api_key must be non-empty string'

    assert 0.0 <= model.temperature <= 1.0, 'model.temperature must be between 0.0 and 1.0'
    assert 0.0 <= model.top_p <= 1.0, 'model.top_p must be between 0.0 and 1.0'

    _assert_positive_int(model.timeout, 'model.timeout')


def test_default_agent_config_fields() -> None:
    """Verify that DefaultAgentConfig field types and boundary values meet expected runtime constraints."""

    config = get_default_config()
    agent: DefaultAgentConfig = config.agent

    _assert_positive_int(agent.max_actions_per_step, 'agent.max_actions_per_step')
    _assert_positive_int(agent.max_failures, 'agent.max_failures')
    _assert_positive_int(agent.step_timeout, 'agent.step_timeout')

    assert isinstance(agent.calculate_cost, bool), 'agent.calculate_cost must be bool'
    assert isinstance(agent.use_vision, bool), 'agent.use_vision must be bool'
    assert isinstance(agent.use_thinking, bool), 'agent.use_thinking must be bool'
    assert isinstance(agent.fast_mode, bool), 'agent.fast_mode must be bool'
    assert isinstance(agent.demo_mode, bool), 'agent.demo_mode must be bool'


def test_default_browser_config_fields() -> None:
    """Verify that DefaultBrowserConfig boolean switch field types and default config can be read correctly."""

    config = get_default_config()
    browser: DefaultBrowserConfig = config.browser

    assert isinstance(browser.headless, bool), 'browser.headless must be bool'
    assert isinstance(browser.enable_security, bool), 'browser.enable_security must be bool'
    assert isinstance(browser.use_sandbox, bool), 'browser.use_sandbox must be bool'

