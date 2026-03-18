"""Unit tests for customer task arguments handler.

These tests validate JSON structure and data source logic for customer custom settings and default fallback.
"""

from __future__ import annotations  # Enable delayed annotations for forward references and consistent type checking

import json  # JSON parsing utilities for decoding handler response bodies for structure assertions
from typing import Any  # Arbitrary type hint for type annotations and assertion auxiliary explanations
from unittest.mock import patch  # Patch helper for replacing external dependencies in tests

from tornado.testing import AsyncHTTPTestCase  # Tornado HTTP test base class for in-memory app HTTP requests
from tornado.web import Application  # Tornado application class for registering minimal routes under test

from web.handlers.customer import CustomerTaskArgsHandler  # Customer task arguments handler returning task args
from core.security.security import SecurityHeadersMiddleware  # Security middleware stubbed as no-op in tests


# Disable actual security header injection logic in test environment to avoid Handler initialization
# failure due to secure.Secure.framework.tornado runtime behavior dependency.
SecurityHeadersMiddleware.apply_to_handler = classmethod(  # type: ignore[assignment]
    lambda cls, handler: None,
)


class _CustomerTaskArgsHandlerTestCase(AsyncHTTPTestCase):
    """Customer task args handler test case validating responses under different configuration sources."""

    def get_app(self) -> Application:
        """Build minimal Tornado app with customer task args route and cookie_secret for secure cookies."""

        return Application(
            [
                (r'/api/customer/task/args/', CustomerTaskArgsHandler),
            ],
            cookie_secret='test-cookie-secret',
            xsrf_cookies=False,
            debug=False,
        )

    def _assert_success_response(self, body: bytes) -> dict[str, Any]:
        """Assert unified success structure and return data field for subsequent assertions."""

        payload = json.loads(body.decode('utf-8'))

        assert isinstance(payload, dict), f'Response payload must be dict, got {type(payload)!r}'
        assert 'meta' in payload and 'data' in payload, \
            f'Response must contain meta and data, got keys={list(payload.keys())!r}'

        meta = payload['meta']
        assert isinstance(meta, dict), f'meta field must be dict, got {type(meta)!r}'
        assert meta.get('code') == 0, f'meta.code must be 0 for success, got {meta.get("code")!r}'
        assert isinstance(meta.get('text'), str) and meta.get('text'), \
            f'meta.text must be non-empty string, got {meta.get("text")!r}'

        return payload['data']

    def test_customer_task_args_returns_custom_setting_when_exists(self) -> None:
        """When custom configuration exists, should return it with priority and unified response structure."""

        fake_setting_dict: dict[str, Any] = {
            'model_name': 'm',
            'model_temperature': 0.3,
            'model_top_p': 0.8,
            'model_api_url': 'u',
            'model_api_key': 'k',
            'model_timeout': 10,
            'agent_use_vision': True,
            'agent_max_actions_per_step': 5,
            'agent_max_failures': 3,
            'agent_step_timeout': 20,
            'agent_use_thinking': False,
            'agent_calculate_cost': True,
            'agent_fast_mode': False,
            'agent_demo_mode': False,
            'browser_headless': True,
            'browser_enable_security': True,
            'browser_use_sandbox': True,
        }

        class _FakeSetting:
            def to_dict(self) -> dict[str, Any]:
                return fake_setting_dict

        with patch(
            'web.handlers.customer.CustomerSettingModule.select_setting_latest',
            return_value=_FakeSetting(),
        ):
            response = self.fetch('/api/customer/task/args/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)

        assert isinstance(data, dict), f'CustomerTaskArgsHandler data must be dict, got {type(data)!r}'
        assert data == fake_setting_dict, f'Handler should return custom setting dict when exists, got {data!r}'

    def test_customer_task_args_falls_back_to_default_config_when_no_custom(self) -> None:
        """When custom config does not exist, should return DefaultConfig mapped task args in unified structure."""

        class _ModelCfg:
            def __init__(self) -> None:
                self.name = 'def-model'
                self.temperature = 0.5
                self.top_p = 0.9
                self.api_url = 'http://model'
                self.api_key = 'secret'
                self.timeout = 30

        class _AgentCfg:
            def __init__(self) -> None:
                self.use_vision = False
                self.max_actions_per_step = 10
                self.max_failures = 2
                self.step_timeout = 60
                self.use_thinking = True
                self.calculate_cost = False
                self.fast_mode = True
                self.demo_mode = False

        class _BrowserCfg:
            def __init__(self) -> None:
                self.headless = True
                self.enable_security = True
                self.use_sandbox = False

        class _DefaultCfg:
            def __init__(self) -> None:
                self.model = _ModelCfg()
                self.agent = _AgentCfg()
                self.browser = _BrowserCfg()

        expected_default: dict[str, Any] = {
            'model_name': 'def-model',
            'model_temperature': 0.5,
            'model_top_p': 0.9,
            'model_api_url': 'http://model',
            'model_api_key': 'secret',
            'model_timeout': 30,
            'agent_use_vision': False,
            'agent_max_actions_per_step': 10,
            'agent_max_failures': 2,
            'agent_step_timeout': 60,
            'agent_use_thinking': True,
            'agent_calculate_cost': False,
            'agent_fast_mode': True,
            'agent_demo_mode': False,
            'browser_headless': True,
            'browser_enable_security': True,
            'browser_use_sandbox': False,
        }

        with patch(
            'web.handlers.customer.CustomerSettingModule.select_setting_latest',
            return_value=None,
        ), patch(
            'web.handlers.customer.get_default_config',
            return_value=_DefaultCfg(),
        ):
            response = self.fetch('/api/customer/task/args/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)

        assert isinstance(data, dict), f'CustomerTaskArgsHandler data must be dict, got {type(data)!r}'
        assert data == expected_default, \
            f'Handler should return default config mapping when no custom setting, got {data!r}'

