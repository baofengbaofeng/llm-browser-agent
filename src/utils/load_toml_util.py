"""TOML configuration loading utilities.

Provide TOML parsing and value accessor helpers.
"""

from typing import Any  # Arbitrary type hint for function parameters and return value generic annotations
from typing import Dict  # Dictionary type hint for configuration dictionary type annotation declarations

import toml  # TOML format parsing library providing TOML file loading and parsing functionality


class TomlConfigKeyNotFoundError(Exception):
    """TOML configuration key not found exception thrown when required configuration key is not found."""

    pass


class TomlConfigValueFormatError(Exception):
    """TOML configuration value format error exception thrown when configuration value type or format is invalid."""

    pass


def load_toml_file(filepath: str) -> Dict[str, Any]:
    """Load configuration from TOML file, throwing exception when file does not exist or parsing fails."""

    with open(filepath, 'r', encoding='utf-8') as f:
        return toml.load(f)


def get_toml_value(config: Dict[str, Any], key_path: str, default=None):
    """Get value from nested TOML configuration using dot-separated key path."""

    keys = key_path.split('.')
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def get_toml_int(config: Dict[str, Any], key_path: str, default: int = 0) -> int:
    """Get integer value from TOML configuration, returning default value when key does not exist or type is invalid."""

    value = get_toml_value(config, key_path)
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_toml_float(config: Dict[str, Any], key_path: str, default: float = 0.0) -> float:
    """Get float value from TOML configuration, returning default value when key does not exist or type is invalid."""

    value = get_toml_value(config, key_path)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_toml_bool(config: Dict[str, Any], key_path: str, default: bool = False) -> bool:
    """Get boolean value from TOML configuration, returning default value when key does not exist."""

    value = get_toml_value(config, key_path)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'on')
    return bool(value)


def get_toml_list(config: Dict[str, Any], key_path: str, default=None):
    """Get list value from TOML configuration, returning default value when key does not exist or type is invalid."""

    if default is None:
        default = []
    value = get_toml_value(config, key_path)
    if value is None:
        return default
    if isinstance(value, list):
        return value
    return default


def require_toml_value(config: Dict[str, Any], key_path: str) -> Any:
    """Get required value from TOML configuration, raising TomlConfigKeyNotFoundError when key does not exist."""

    value = get_toml_value(config, key_path)
    if value is None:
        raise TomlConfigKeyNotFoundError(f'Required TOML configuration key not found: {key_path}')
    return value


def require_toml_int(config: Dict[str, Any], key_path: str) -> int:
    """Get required integer value from TOML configuration, raising on missing key or invalid type."""

    value = require_toml_value(config, key_path)
    try:
        return int(value)
    except (ValueError, TypeError) as e:
        raise TomlConfigValueFormatError(f'Invalid integer value for {key_path}: {value}') from e


def require_toml_float(config: Dict[str, Any], key_path: str) -> float:
    """Get required float value from TOML configuration, raising on missing key or invalid type."""

    value = require_toml_value(config, key_path)
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        raise TomlConfigValueFormatError(f'Invalid float value for {key_path}: {value}') from e


def require_toml_bool(config: Dict[str, Any], key_path: str) -> bool:
    """Get required boolean value from TOML configuration, raising on missing key or invalid type."""

    value = require_toml_value(config, key_path)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        if value.lower() in ('false', 'no', '0', 'off'):
            return False
    raise TomlConfigValueFormatError(f'Invalid boolean value for {key_path}: {value}')


def require_toml_list(config: Dict[str, Any], key_path: str) -> list:
    """Get required list value from TOML configuration, raising on missing key or invalid type."""

    value = require_toml_value(config, key_path)
    if isinstance(value, list):
        return value
    raise TomlConfigValueFormatError(f'Invalid list value for {key_path}: {value}')

