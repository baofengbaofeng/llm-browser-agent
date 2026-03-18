"""Unit tests for configuration HTTP handlers validating JSON response structure and field completeness."""

from __future__ import annotations  # Enable delayed annotation evaluation for forward reference typing consistency

import json  # JSON parsing module used to deserialize handler response bytes to Python dict for assertions

from tornado.testing import AsyncHTTPTestCase  # Tornado HTTP test base class for in-memory app HTTP requests
from tornado.web import Application  # Tornado application class for registering minimal routes under test

from core.security.security import SecurityHeadersMiddleware  # Security middleware stubbed as no-op in tests
from web.handlers.configuration import AgentConfigHandler  # Agent config handler expected to return agent config dict
from web.handlers.configuration import AllConfigHandler  # All config handler expected to return full config dict
from web.handlers.configuration import BrowserConfigHandler  # Browser config handler expected to return browser config
from web.handlers.configuration import ModelConfigHandler  # Model config handler expected to return model config dict

# Disable actual security header injection logic in test environment to avoid Handler initialization failure
# due to secure.Secure.framework.tornado runtime behavior dependency.
SecurityHeadersMiddleware.apply_to_handler = classmethod(  # type: ignore[assignment]
    lambda cls, handler: None,
)


class _ConfigurationHandlerTestCase(AsyncHTTPTestCase):
    """Configuration handler test base case using AsyncHTTPTestCase validating endpoint response structures."""

    def get_app(self) -> Application:
        """Build minimal Tornado app containing configuration routes for HTTP requests and response validation."""

        return Application(
            [
                (r'/api/configuration/', AllConfigHandler),
                (r'/api/configuration/browser/', BrowserConfigHandler),
                (r'/api/configuration/agent/', AgentConfigHandler),
                (r'/api/configuration/model/', ModelConfigHandler),
            ],
            cookie_secret='test-cookie-secret',
            xsrf_cookies=False,
            debug=False,
        )

    def _assert_success_response(self, body: bytes) -> dict:
        """Assert unified success response and return data field content for field-level assertions."""

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

    def test_all_config_handler_response_structure(self) -> None:
        """Validate AllConfigHandler returns unified structure and required top-level keys."""

        response = self.fetch('/api/configuration/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)

        assert isinstance(data, dict), f'AllConfigHandler data must be dict, got {type(data)!r}'
        # DefaultConfig should contain at least model, agent, and browser configuration sections
        for key in ('model', 'agent', 'browser'):
            assert key in data, f'AllConfigHandler data must contain key {key!r}, got keys={list(data.keys())!r}'

    def test_browser_config_handler_response_structure(self) -> None:
        """Validate BrowserConfigHandler returns a flat dict and expected fields."""

        response = self.fetch('/api/configuration/browser/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)

        assert isinstance(data, dict), f'BrowserConfigHandler data must be dict, got {type(data)!r}'
        # Browser config typically contains headless, enable_security, and use_sandbox boolean switches
        for key in ('headless', 'enable_security', 'use_sandbox'):
            assert key in data, f'BrowserConfigHandler data must contain key {key!r}, got keys={list(data.keys())!r}'

    def test_agent_config_handler_response_structure(self) -> None:
        """Validate AgentConfigHandler returns expected numeric and boolean fields in unified structure."""

        response = self.fetch('/api/configuration/agent/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)

        assert isinstance(data, dict), f'AgentConfigHandler data must be dict, got {type(data)!r}'
        for key in (
            'max_actions_per_step',
            'max_failures',
            'step_timeout',
            'use_vision',
            'use_thinking',
            'calculate_cost',
        ):
            assert key in data, f'AgentConfigHandler data must contain key {key!r}, got keys={list(data.keys())!r}'

    def test_model_config_handler_response_structure(self) -> None:
        """Validate ModelConfigHandler returns core fields such as name/api_url/temperature in unified structure."""

        response = self.fetch('/api/configuration/model/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)

        assert isinstance(data, dict), f'ModelConfigHandler data must be dict, got {type(data)!r}'
        for key in ('name', 'api_url', 'api_key', 'temperature', 'top_p', 'timeout'):
            assert key in data, f'ModelConfigHandler data must contain key {key!r}, got keys={list(data.keys())!r}'

