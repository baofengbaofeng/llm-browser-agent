"""Error handling and multi-language message utility module providing unified error codes, language
parsing, and response construction capabilities for all HTTP handlers."""

from __future__ import annotations  # Postpone annotation evaluation to avoid runtime import cycles and typing overhead

import json  # Standard JSON module for parsing and serializing structured data in error response body
import os  # Standard path module for locating error message config directory and constructing paths
from typing import Any  # Generic type hint used for decoded JSON payload values in request bodies and responses
from typing import Dict  # Dict type hint used for mapping string keys to typed values in handler helper utilities

from tornado.web import RequestHandler  # Tornado Web base class providing request context and response writing

from web.handlers.response import failure_response  # Unified response constructor for wrapping failure results
from utils.load_toml_util import load_toml_file  # TOML loader for reading multi-language error messages from assets

# Mapping from error codes to translation keys, registered together via factory function at constant definition
_ERROR_TRANSLATION_KEYS: dict[int, str] = {}


def _define_error(code: int, key: str) -> int:
    """Register error code and translation key, return the code to maintain relationship during constant definition."""

    _ERROR_TRANSLATION_KEYS[code] = key
    return code


ERROR_INTERNAL_ERROR = _define_error(50001, 'error_internal_error')  # Server internal error
ERROR_BODY_INVALID_JSON = _define_error(40001, 'error_body_invalid_json')  # Request body JSON parsing failed

ERROR_PARAM_PAGE_INVALID_VALUE = _define_error(40010, 'error_param_page_invalid_value')
ERROR_PARAM_SIZE_INVALID_VALUE = _define_error(40011, 'error_param_size_invalid_value')
ERROR_PARAM_STATUS_INVALID_VALUE = _define_error(40012, 'error_param_status_invalid_value')

# Task project related error codes
ERROR_TASK_PROJECT_INVALID_JSON = _define_error(41000, 'error_task_project_invalid_json')

ERROR_TASK_PROJECT_MISSING_DIGEST = _define_error(41001, 'error_task_project_missing_digest')
ERROR_TASK_PROJECT_INVALID_DIGEST = _define_error(41002, 'error_task_project_invalid_digest')

ERROR_TASK_PROJECT_MISSING_PROMPT = _define_error(41003, 'error_task_project_missing_prompt')
ERROR_TASK_PROJECT_INVALID_PROMPT = _define_error(41004, 'error_task_project_invalid_prompt')

ERROR_TASK_PROJECT_MISSING_SETTING = _define_error(41005, 'error_task_project_missing_setting')
ERROR_TASK_PROJECT_INVALID_SETTING = _define_error(41006, 'error_task_project_invalid_setting')
ERROR_TASK_PROJECT_MISSING_ID = _define_error(41007, 'error_task_project_missing_id')
ERROR_TASK_PROJECT_INVALID_ID = _define_error(41008, 'error_task_project_invalid_id')

# Task history related error codes
ERROR_TASK_HISTORY_INVALID_ID = _define_error(42001, 'error_task_history_invalid_id')

# Natural language instruction parsing related error codes
ERROR_INSTRUCT_EMPTY = _define_error(43001, 'error_instruct_empty')  # Instruction field in request is empty or missing

# Large model setting field error codes
ERROR_SETTING_MODEL_NAME = _define_error(41101, 'error_setting_model_name')
ERROR_SETTING_MODEL_TEMPERATURE = _define_error(41102, 'error_setting_model_temperature')
ERROR_SETTING_MODEL_TOP_P = _define_error(41103, 'error_setting_model_top_p')
ERROR_SETTING_MODEL_API_URL = _define_error(41104, 'error_setting_model_api_url')
ERROR_SETTING_MODEL_API_KEY = _define_error(41105, 'error_setting_model_api_key')
ERROR_SETTING_MODEL_TIMEOUT = _define_error(41106, 'error_setting_model_timeout')

# Agent setting field error codes
ERROR_SETTING_AGENT_USE_VISION = _define_error(41201, 'error_setting_agent_use_vision')
ERROR_SETTING_AGENT_MAX_ACTIONS_PER_STEP = _define_error(41202, 'error_setting_agent_max_actions_per_step')
ERROR_SETTING_AGENT_MAX_FAILURES = _define_error(41203, 'error_setting_agent_max_failures')
ERROR_SETTING_AGENT_STEP_TIMEOUT = _define_error(41204, 'error_setting_agent_step_timeout')
ERROR_SETTING_AGENT_USE_THINKING = _define_error(41205, 'error_setting_agent_use_thinking')
ERROR_SETTING_AGENT_CALCULATE_COST = _define_error(41206, 'error_setting_agent_calculate_cost')
ERROR_SETTING_AGENT_FAST_MODE = _define_error(41207, 'error_setting_agent_fast_mode')
ERROR_SETTING_AGENT_DEMO_MODE = _define_error(41208, 'error_setting_agent_demo_mode')

# Browser setting field error codes
ERROR_SETTING_BROWSER_HEADLESS = _define_error(41301, 'error_setting_browser_headless')
ERROR_SETTING_BROWSER_ENABLE_SECURITY = _define_error(41302, 'error_setting_browser_enable_security')
ERROR_SETTING_BROWSER_USE_SANDBOX = _define_error(41303, 'error_setting_browser_use_sandbox')


def _load_error_messages() -> Dict[str, Dict[str, str]]:
    """Load multi-language error messages from core/handlers/assets directory grouped by language code."""

    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, 'assets')

    if not os.path.isdir(assets_dir):
        return {}

    messages: Dict[str, Dict[str, str]] = {}

    for filename in os.listdir(assets_dir):
        if not (filename.endswith('.toml') and filename.startswith('errors_')):
            continue
        lang_code = filename[7:-5]
        file_path = os.path.join(assets_dir, filename)
        data = load_toml_file(file_path)
        if not isinstance(data, dict):
            continue
        messages[lang_code] = {str(k).lower(): str(v) for k, v in data.items()}

    return messages


_ERROR_MESSAGES: Dict[str, Dict[str, str]] = _load_error_messages()


def _resolve_lang_from_handler(handler: RequestHandler) -> str:
    """Infer request language from querystring and Accept-Language header with region prefix fallback."""

    lang = (handler.get_argument('lang', '') or '').strip().lower()
    if not lang:
        header = handler.request.headers.get('Accept-Language', '')
        if header:
            lang = header.split(',')[0].split('-')[0].strip().lower()
    return lang or 'default'


def _get_error_message(code: int, lang: str) -> str:
    """Get error message by code and language, fallback to key name or code info if translation not configured."""

    key = _ERROR_TRANSLATION_KEYS.get(code, f'error_unknown_{code}').lower()

    lang_messages = _ERROR_MESSAGES.get(lang) or {}
    if key in lang_messages:
        return lang_messages[key]

    default_messages = _ERROR_MESSAGES.get('default') or {}
    if key in default_messages:
        return default_messages[key]

    return f'{key} (code={code})'


def write_error_response(handler: RequestHandler, code: int, http_status: int = 200) -> None:
    """Write unified JSON error response, set HTTP status and use failure_response to wrap error code and message."""

    lang = _resolve_lang_from_handler(handler)
    message = _get_error_message(code, lang)
    handler.set_status(http_status)
    handler.write(failure_response(code=code, text=message))


class BaseHandlerError(Exception):
    """Custom business exception carrying error code and HTTP status, converted to JSON by BaseHandler."""

    def __init__(self, code: int, http_status: int = 200) -> None:
        self.code = code
        self.http_status = http_status
        super().__init__(code)


def parse_json_body(handler: RequestHandler) -> Any:
    """Parse JSON from HTTP request body, raise BaseHandlerError with ERROR_BODY_INVALID_JSON on failure."""

    try:
        return json.loads(handler.request.body or b'{}')
    except json.JSONDecodeError as error:
        raise BaseHandlerError(ERROR_BODY_INVALID_JSON) from error


def validate_setting_dict(setting: Any) -> Dict[str, Any]:
    """Validate and normalize setting dictionary, raise BaseHandlerError for invalid fields, return dict for reuse."""

    if not isinstance(setting, dict):
        raise BaseHandlerError(ERROR_TASK_PROJECT_INVALID_SETTING)

    model_name = setting.get('model_name')
    if not isinstance(model_name, str) or not model_name.strip():
        raise BaseHandlerError(ERROR_SETTING_MODEL_NAME)

    model_temperature = setting.get('model_temperature')
    if not isinstance(model_temperature, (int, float)) or not (0.0 <= float(model_temperature) <= 1.0):
        raise BaseHandlerError(ERROR_SETTING_MODEL_TEMPERATURE)

    model_top_p = setting.get('model_top_p')
    if not isinstance(model_top_p, (int, float)) or not (0.0 <= float(model_top_p) <= 1.0):
        raise BaseHandlerError(ERROR_SETTING_MODEL_TOP_P)

    model_api_url = setting.get('model_api_url')
    if not isinstance(model_api_url, str) or not model_api_url.strip():
        raise BaseHandlerError(ERROR_SETTING_MODEL_API_URL)

    model_api_key = setting.get('model_api_key')
    if not isinstance(model_api_key, str) or not model_api_key.strip():
        raise BaseHandlerError(ERROR_SETTING_MODEL_API_KEY)

    model_timeout = setting.get('model_timeout')
    if not isinstance(model_timeout, int) or model_timeout < 1:
        raise BaseHandlerError(ERROR_SETTING_MODEL_TIMEOUT)

    agent_use_vision = setting.get('agent_use_vision', False)
    if not isinstance(agent_use_vision, bool):
        raise BaseHandlerError(ERROR_SETTING_AGENT_USE_VISION)

    agent_max_actions_per_step = setting.get('agent_max_actions_per_step')
    if not isinstance(agent_max_actions_per_step, int) or agent_max_actions_per_step < 1:
        raise BaseHandlerError(ERROR_SETTING_AGENT_MAX_ACTIONS_PER_STEP)

    agent_max_failures = setting.get('agent_max_failures')
    if not isinstance(agent_max_failures, int) or agent_max_failures < 1:
        raise BaseHandlerError(ERROR_SETTING_AGENT_MAX_FAILURES)

    agent_step_timeout = setting.get('agent_step_timeout')
    if not isinstance(agent_step_timeout, int) or agent_step_timeout < 1:
        raise BaseHandlerError(ERROR_SETTING_AGENT_STEP_TIMEOUT)

    agent_use_thinking = setting.get('agent_use_thinking', False)
    if not isinstance(agent_use_thinking, bool):
        raise BaseHandlerError(ERROR_SETTING_AGENT_USE_THINKING)

    agent_calculate_cost = setting.get('agent_calculate_cost', True)
    if not isinstance(agent_calculate_cost, bool):
        raise BaseHandlerError(ERROR_SETTING_AGENT_CALCULATE_COST)

    agent_fast_mode = setting.get('agent_fast_mode', False)
    if not isinstance(agent_fast_mode, bool):
        raise BaseHandlerError(ERROR_SETTING_AGENT_FAST_MODE)

    agent_demo_mode = setting.get('agent_demo_mode', False)
    if not isinstance(agent_demo_mode, bool):
        raise BaseHandlerError(ERROR_SETTING_AGENT_DEMO_MODE)

    browser_headless = setting.get('browser_headless', True)
    if not isinstance(browser_headless, bool):
        raise BaseHandlerError(ERROR_SETTING_BROWSER_HEADLESS)

    browser_enable_security = setting.get('browser_enable_security', True)
    if not isinstance(browser_enable_security, bool):
        raise BaseHandlerError(ERROR_SETTING_BROWSER_ENABLE_SECURITY)

    browser_use_sandbox = setting.get('browser_use_sandbox', True)
    if not isinstance(browser_use_sandbox, bool):
        raise BaseHandlerError(ERROR_SETTING_BROWSER_USE_SANDBOX)

    return {
        'model_name': model_name.strip(),
        'model_temperature': float(model_temperature),
        'model_top_p': float(model_top_p),
        'model_api_url': model_api_url.strip(),
        'model_api_key': model_api_key.strip(),
        'model_timeout': int(model_timeout),
        'agent_use_vision': agent_use_vision,
        'agent_max_actions_per_step': int(agent_max_actions_per_step),
        'agent_max_failures': int(agent_max_failures),
        'agent_step_timeout': int(agent_step_timeout),
        'agent_use_thinking': agent_use_thinking,
        'agent_calculate_cost': agent_calculate_cost,
        'agent_fast_mode': agent_fast_mode,
        'agent_demo_mode': agent_demo_mode,
        'browser_headless': browser_headless,
        'browser_enable_security': browser_enable_security,
        'browser_use_sandbox': browser_use_sandbox,
    }


def parse_pagination_params(handler: RequestHandler, default_page: str = '1',
    default_size: str = '50') -> tuple[int, int]:
    """Parse pagination params page and size with minimum validation, raise BaseHandlerError for invalid values."""

    try:
        page = int(handler.get_argument('page', default_page))
    except ValueError as error:
        raise BaseHandlerError(ERROR_PARAM_PAGE_INVALID_VALUE) from error

    try:
        size = int(handler.get_argument('size', default_size))
    except ValueError as error:
        raise BaseHandlerError(ERROR_PARAM_SIZE_INVALID_VALUE) from error

    if page < 1:
        raise BaseHandlerError(ERROR_PARAM_PAGE_INVALID_VALUE)
    if size < 1:
        raise BaseHandlerError(ERROR_PARAM_SIZE_INVALID_VALUE)

    return page, size


class BaseHandler(RequestHandler):
    """Base handler providing unified exception handling and converting exceptions to JSON."""

    def write_error(self, status_code: int, **kwargs: Any) -> None:  # type: ignore[override]
        """Handle handler exceptions and map them to unified JSON error response payloads."""

        exc = None
        if 'exc_info' in kwargs and kwargs['exc_info']:
            _, exc, _ = kwargs['exc_info']

        if isinstance(exc, BaseHandlerError):
            write_error_response(self, exc.code, http_status=exc.http_status or status_code)
        else:
            write_error_response(self, ERROR_INTERNAL_ERROR, http_status=status_code)

