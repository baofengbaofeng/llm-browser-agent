"""TOML configuration loader and helpers.

This module supports environment-specific config selection based on CLI args and provides typed accessors.
"""

import os  # OS utilities for config file path calculation and assets directory traversal
import sys  # System utilities for CLI args, stderr output, and process exit
from typing import Any  # Any type hint, used for config values and generic function return type annotation declarations
from typing import Dict  # Dictionary type hint used for application config dictionary structure annotations

from utils.load_toml_util import get_toml_bool  # TOML bool accessor converting boolean-like values from config dict
from utils.load_toml_util import get_toml_float  # TOML float accessor converting numeric values from config dict
from utils.load_toml_util import get_toml_int  # TOML int accessor converting numeric values from config dict
from utils.load_toml_util import get_toml_list  # TOML list accessor validating list type values from config dict
from utils.load_toml_util import get_toml_value  # TOML generic accessor retrieving nested values from config dict
from utils.load_toml_util import load_toml_file  # TOML file loader reading and parsing a configuration file path
from utils.load_toml_util import require_toml_bool  # TOML required bool accessor raising exception on missing/invalid
from utils.load_toml_util import require_toml_float  # TOML required float accessor raising exception on missing/invalid
from utils.load_toml_util import require_toml_int  # TOML required int accessor raising exception on missing/invalid
from utils.load_toml_util import require_toml_list  # TOML required list accessor raising exception on missing/invalid
from utils.load_toml_util import require_toml_value  # TOML required generic accessor raising exception on missing key


def _parse_env_from_args() -> str | None:
    """Parse --env environment argument from command line arguments and return environment identifier string.

    Returns:
        str | None: Environment identifier string if ``--env=xxx`` exists, otherwise ``None``.
    """

    for arg in sys.argv:
        if arg.startswith('--env='):
            return arg.split('=', 1)[1]
    return None


def _get_config_file_path(assets_dir: str, env: str | None) -> str:
    """Get configuration file path based on environment name.

    Args:
        assets_dir: Absolute path of config assets directory, usually ``assets`` subdirectory under module directory.
        env: Environment identifier string, e.g. ``test``, ``prod``, use default config file when empty.

    Returns:
        str: Parsed configuration file absolute path, pointing to environment.toml or environment-{env}.toml.
    """

    if env:
        return os.path.join(assets_dir, f'environment-{env}.toml')
    return os.path.join(assets_dir, 'environment.toml')


def load_application_config() -> Dict[str, Any]:
    """Load application configuration from TOML file, supporting environment-specific config selection.

    Returns:
        Dict[str, Any]: Parsed configuration dictionary mapping config path strings to corresponding config data.

    Raises:
        SystemExit: When config file does not exist, writes error message to stderr and terminates process.
    """

    config_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(config_dir, 'assets')
    env = _parse_env_from_args()
    config_file = _get_config_file_path(assets_dir, env)

    if not os.path.exists(config_file):
        sys.stderr.write(f"Configuration file not found: {config_file}\n")
        sys.exit(1)

    return load_toml_file(config_file)


# Process-wide config cache, retrieved by modules via get_application_config(), avoiding repeated loading
_APPLICATION_CONFIG_CACHE: Dict[str, Any] | None = None


def get_application_config() -> Dict[str, Any]:
    """Get application configuration dictionary loaded only once per process and cached for subsequent calls.

    Returns:
        Dict[str, Any]: Application config dictionary containing complete config content loaded from TOML file.
    """

    global _APPLICATION_CONFIG_CACHE
    if _APPLICATION_CONFIG_CACHE is None:
        _APPLICATION_CONFIG_CACHE = load_application_config()
    return _APPLICATION_CONFIG_CACHE


def get_config_value(config: Dict[str, Any], key: str, default=None):
    """Get configuration value with default fallback when key does not exist.

    Args:
        config: Loaded configuration dictionary, usually return value of ``get_application_config()``.
        key: Dot-separated config key path string, e.g. ``llm_browser_agent.server.port``.
        default: Default value returned when key does not exist or type mismatch, default value is ``None``.

    Returns:
        Any: Corresponding key config value or default value, will not throw exception when key does not exist.
    """

    return get_toml_value(config, key, default)


def get_config_int(config: Dict[str, Any], key: str, default: int = 0) -> int:
    """Get integer configuration value, returns specified default integer value when key does not exist or type invalid.

    Args:
        config: Loaded configuration dictionary.
        key: Config key path string.
        default: Default value returned when key missing or cannot convert to integer, default value is ``0``.

    Returns:
        int: Parsed integer config value or provided default value.
    """

    return get_toml_int(config, key, default)


def get_config_float(config: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """Get float configuration value, returns specified default float value when key does not exist or type invalid.

    Args:
        config: Loaded configuration dictionary.
        key: Config key path string.
        default: Default value returned when key missing or cannot convert to float, default value is ``0.0``.

    Returns:
        float: Parsed float config value or provided default value.
    """

    return get_toml_float(config, key, default)


def get_config_bool(config: Dict[str, Any], key: str, default: bool = False) -> bool:
    """Get boolean configuration value, returns specified default boolean value when key does not exist or type unclear.

    Args:
        config: Loaded configuration dictionary.
        key: Config key path string.
        default: Default boolean value returned when key missing, default value is ``False``.

    Returns:
        bool: Parsed boolean config value or provided default value.
    """

    return get_toml_bool(config, key, default)


def get_config_list(config: Dict[str, Any], key: str, default=None):
    """Get list configuration value, returns specified default list when key does not exist or type invalid.

    Args:
        config: Loaded configuration dictionary.
        key: Config key path string.
        default: Default value returned when key missing or type not list, default ``None`` means return empty list.

    Returns:
        list: Parsed list config value or provided default list copy.
    """

    return get_toml_list(config, key, default)


def require_config_value(config: Dict[str, Any], key: str) -> Any:
    """Get required configuration value, throws TomlConfigKeyNotFoundError exception when key does not exist.

    Args:
        config: Loaded configuration dictionary.
        key: Required config key path string.

    Returns:
        Any: Corresponding key config value, guaranteed key exists and available.

    Raises:
        TomlConfigKeyNotFoundError: Thrown when specified key does not exist in configuration dictionary.
    """

    return require_toml_value(config, key)


def require_config_int(config: Dict[str, Any], key: str) -> int:
    """Get required integer configuration value, raising value format error when key is missing or type is invalid.

    Args:
        config: Loaded configuration dictionary.
        key: Required integer config key path string.

    Returns:
        int: Parsed integer config value.

    Raises:
        TomlConfigKeyNotFoundError: Thrown when key does not exist.
        TomlConfigValueFormatError: Thrown when value cannot convert to integer type.
    """

    return require_toml_int(config, key)


def require_config_float(config: Dict[str, Any], key: str) -> float:
    """Get required float configuration value, raising value format error when key is missing or type is invalid.

    Args:
        config: Loaded configuration dictionary.
        key: Required float config key path string.

    Returns:
        float: Parsed float config value.

    Raises:
        TomlConfigKeyNotFoundError: Thrown when key does not exist.
        TomlConfigValueFormatError: Thrown when value cannot convert to float type.
    """

    return require_toml_float(config, key)


def require_config_bool(config: Dict[str, Any], key: str) -> bool:
    """Get required boolean configuration value, raising value format error when key is missing or type is invalid.

    Args:
        config: Loaded configuration dictionary.
        key: Required boolean config key path string.

    Returns:
        bool: Parsed boolean config value.

    Raises:
        TomlConfigKeyNotFoundError: Thrown when key does not exist.
        TomlConfigValueFormatError: Thrown when value cannot parse to boolean type.
    """

    return require_toml_bool(config, key)


def require_config_list(config: Dict[str, Any], key: str) -> list:
    """Get required list configuration value, raising value format error when key is missing or type is invalid.

    Args:
        config: Loaded configuration dictionary.
        key: Required list config key path string.

    Returns:
        list: Parsed list config value.

    Raises:
        TomlConfigKeyNotFoundError: Thrown when key does not exist.
        TomlConfigValueFormatError: Thrown when value is not list type.
    """

    return require_toml_list(config, key)

