"""Unit tests for environment.py configuration module.

Validate configuration loading and typed accessor behavior.
"""

from __future__ import annotations  # Enable delayed annotation evaluation to support forward reference type annotations

from typing import Dict  # Dictionary type hint for constructing test configuration dictionaries and type assertions

from environment import environment as env_module  # Tested environment config module providing config helpers
from utils.load_toml_util import (  # TOML configuration exception types for require_* series function assertions
    TomlConfigKeyNotFoundError,
    TomlConfigValueFormatError,
)


def test_load_application_config_returns_dict() -> None:
    """Validate load_application_config loads TOML and returns dict containing llm_browser_agent node."""

    config = env_module.load_application_config()

    assert isinstance(config, dict), 'load_application_config must return a dict'
    assert 'llm_browser_agent' in config, 'top-level key "llm_browser_agent" should exist in config'


def test_get_application_config_uses_process_cache() -> None:
    """Validate get_application_config caches config object and returns same instance on multiple calls."""

    # Reset module-level cache for testing singleton behavior
    env_module._APPLICATION_CONFIG_CACHE = None  # type: ignore[attr-defined]

    config_first = env_module.get_application_config()
    config_second = env_module.get_application_config()

    assert config_first is config_second, 'get_application_config should return same cached instance'


def test_get_config_helpers_return_typed_values() -> None:
    """Validate get_config_* helpers return typed values for int/float/bool/list as expected."""

    config = env_module.get_application_config()

    port = env_module.get_config_int(config, 'llm_browser_agent.server.port')
    debug_flag = env_module.get_config_bool(config, 'llm_browser_agent.server.debug')
    timeout = env_module.get_config_float(config, 'llm_browser_agent.model.timeout')
    chrome_args = env_module.get_config_list(config, 'llm_browser_agent.browser.chrome.args')

    assert isinstance(port, int), 'server.port must be returned as int'
    assert isinstance(debug_flag, bool), 'server.debug must be returned as bool'
    assert isinstance(timeout, float), 'model.timeout must be coerced to float'
    assert isinstance(chrome_args, list), 'browser.chrome.args must be returned as list'


def test_get_config_value_with_default_fallback() -> None:
    """Validate get_config_value returns default value when key does not exist instead of throwing exception."""

    config = env_module.get_application_config()
    fallback = 'fallback-value'

    value = env_module.get_config_value(config, 'non.existent.key.path', default=fallback)

    assert value == fallback, 'get_config_value must return provided default when key is missing'


def test_require_config_value_raises_on_missing_key() -> None:
    """Validate require_config_value throws TomlConfigKeyNotFoundError exception when key does not exist."""

    empty_config: Dict[str, object] = {}

    try:
        env_module.require_config_value(empty_config, 'missing.key')
        assert False, 'require_config_value should raise TomlConfigKeyNotFoundError for missing key'
    except TomlConfigKeyNotFoundError as error:
        assert error is not None


def test_require_config_int_and_float_type_errors() -> None:
    """Validate require_config_int and require_config_float throw TomlConfigValueFormatError on bad value formats."""

    bad_config: Dict[str, object] = {'int_key': 'not-an-int', 'float_key': 'not-a-float'}

    try:
        env_module.require_config_int(bad_config, 'int_key')
        assert False, 'require_config_int should raise TomlConfigValueFormatError when value is not int-like'
    except TomlConfigValueFormatError as error:
        assert error is not None

    try:
        env_module.require_config_float(bad_config, 'float_key')
        assert False, 'require_config_float should raise TomlConfigValueFormatError when value is not float-like'
    except TomlConfigValueFormatError as error:
        assert error is not None


def test_require_config_bool_and_list_type_errors() -> None:
    """Validate require_config_bool and require_config_list throw TomlConfigValueFormatError on bad value formats."""

    bad_config: Dict[str, object] = {'bool_key': 'not-bool', 'list_key': 'not-a-list'}

    try:
        env_module.require_config_bool(bad_config, 'bool_key')
        assert False, 'require_config_bool should raise TomlConfigValueFormatError when value is not bool-like'
    except TomlConfigValueFormatError as error:
        assert error is not None

    try:
        env_module.require_config_list(bad_config, 'list_key')
        assert False, 'require_config_list should raise TomlConfigValueFormatError when value is not list-like'
    except TomlConfigValueFormatError as error:
        assert error is not None

