"""Unit tests for language configuration handler.

These tests validate unified response structure and translation payload behavior across lang parameter scenarios.
"""

from __future__ import annotations  # Enable delayed annotations for forward references and consistent type checking

import json  # JSON parsing utilities for decoding handler response bodies for structure assertions
from typing import Any  # Arbitrary type hint for type annotations and assertion auxiliary explanations
from unittest.mock import MagicMock  # Mock helper for controlled dependencies in tests
from unittest.mock import patch  # Patch helper for replacing language configuration dependencies in tests

from tornado.testing import AsyncHTTPTestCase  # Tornado HTTP test base class for in-memory app HTTP requests
from tornado.web import Application  # Tornado application class for registering minimal routes under test

from web.handlers.language import LanguageHandler  # Language handler returning translation configuration dictionary
from core.security.security import SecurityHeadersMiddleware  # Security middleware stubbed as no-op in tests


# Disable actual security header injection logic in test environment to avoid Handler initialization
# failure due to secure.Secure.framework.tornado runtime behavior dependency.
SecurityHeadersMiddleware.apply_to_handler = classmethod(  # type: ignore[assignment]
    lambda cls, handler: None,
)


class _LanguageHandlerTestCase(AsyncHTTPTestCase):
    """Language handler test case validating endpoint response structure and data content via in-memory web app."""

    def get_app(self) -> Application:
        """Build minimal Tornado app with language routes and cookie_secret for secure cookies."""

        return Application(
            [
                (r'/api/language/', LanguageHandler),
            ],
            cookie_secret='test-cookie-secret',
            xsrf_cookies=False,
            debug=False,
        )

    def _assert_success_response(self, body: bytes) -> Any:
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

    def test_language_handler_returns_all_languages_when_lang_missing(self) -> None:
        """When lang is missing, should return translation mapping for each language."""

        fake_languages = {'en': 'English', 'fr': 'Français'}

        def _fake_get_all_translations(code: str) -> dict[str, str]:
            return {'HELLO': f'hello-{code}', 'BYE': f'bye-{code}'}

        with patch('web.handlers.language.LANGUAGE_NAMES', fake_languages), patch(
            'web.handlers.language.get_all_translations',
            side_effect=_fake_get_all_translations,
        ):
            response = self.fetch('/api/language/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)

        assert isinstance(data, dict), f'LanguageHandler data must be dict, got {type(data)!r}'
        assert set(data.keys()) == {'en', 'fr'}, f'Expected language keys en, fr, got {set(data.keys())!r}'
        assert data['en'] == {'HELLO': 'hello-en', 'BYE': 'bye-en'}
        assert data['fr'] == {'HELLO': 'hello-fr', 'BYE': 'bye-fr'}

    def test_language_handler_returns_single_language_when_valid_lang(self) -> None:
        """When valid lang is provided, should return only that language translation dictionary."""

        fake_languages = {'en': 'English', 'fr': 'Français'}

        with patch('web.handlers.language.LANGUAGE_NAMES', fake_languages), patch(
            'web.handlers.language.get_all_translations',
            return_value={'HELLO': 'hello-en', 'BYE': 'bye-en'},
        ) as mock_get_all:
            response = self.fetch('/api/language/?lang=en')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)

        assert isinstance(data, dict), f'LanguageHandler data must be dict, got {type(data)!r}'
        assert data == {'HELLO': 'hello-en', 'BYE': 'bye-en'}
        mock_get_all.assert_called_once_with('en')

    def test_language_handler_returns_empty_dict_for_invalid_lang(self) -> None:
        """When lang is invalid, should return empty dict without calling get_all_translations."""

        fake_languages = {'en': 'English'}

        with patch('web.handlers.language.LANGUAGE_NAMES', fake_languages), patch(
            'web.handlers.language.get_all_translations',
        ) as mock_get_all:
            response = self.fetch('/api/language/?lang=unknown')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)

        assert data == {}, f'Expected empty dict for invalid lang, got {data!r}'
        mock_get_all.assert_not_called()

