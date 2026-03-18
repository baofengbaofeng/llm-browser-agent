"""Unit tests for task related handlers validating response structures and parameter validation behaviors."""

from __future__ import annotations  # Enable postponed evaluation of annotations for consistent forward reference typing

import json  # JSON utilities used to deserialize handler response bodies into dictionaries for assertions
from typing import Any  # Generic type hint used in type annotations and assertion helper signatures
from unittest.mock import AsyncMock  # Async mock utility used to stub coroutine dependencies in handler unit tests
from unittest.mock import patch  # Patch utility used to replace imports and attributes during isolated unit tests

from tornado.testing import AsyncHTTPTestCase  # Tornado base class used to spin up in memory apps for HTTP testing
from tornado.web import Application  # Tornado application class used to register minimal routes under test

from web.handlers.task import ChainTaskHistoryHandler  # Handler returning all history records for a chained session
from web.handlers.task import CustomerTaskProjectHandler  # Handler for task project list/create/delete APIs
from web.handlers.task import TaskHistoryListHandler  # Handler for paginated and filtered task history lists
from web.handlers.task import TaskHistoryViewHandler  # Handler responsible for returning single history record details
from core.security.security import SecurityHeadersMiddleware  # Middleware patched to no-op to simplify test startup

SecurityHeadersMiddleware.apply_to_handler = classmethod(  # type: ignore[assignment]
    lambda cls, handler: None,
)

_VALID_SETTING = {
    'model_name': 'm',
    'model_temperature': 0.5,
    'model_top_p': 0.9,
    'model_api_url': 'https://api.example.com',
    'model_api_key': 'key',
    'model_timeout': 60,
    'agent_use_vision': False,
    'agent_max_actions_per_step': 10,
    'agent_max_failures': 3,
    'agent_step_timeout': 120,
    'agent_use_thinking': False,
    'agent_calculate_cost': True,
    'agent_fast_mode': False,
    'agent_demo_mode': False,
    'browser_headless': True,
    'browser_enable_security': True,
    'browser_use_sandbox': True,
}


class _TaskHandlersTestCase(AsyncHTTPTestCase):
    """Task handler tests validating response structures and error codes via in-memory AsyncHTTPTestCase."""

    def get_app(self) -> Application:
        """Build a minimal Tornado app with task routes and cookie_secret for secure cookies."""

        return Application(
            [
                (r'/api/customer/task/plan/', CustomerTaskProjectHandler),
                (r'/api/task/history/', TaskHistoryListHandler),
                (r'/api/task/history/([0-9]+)/', TaskHistoryViewHandler),
                (r'/api/task/history/chain/([a-f0-9\-]+)/', ChainTaskHistoryHandler),
            ],
            cookie_secret='test-cookie-secret',
            xsrf_cookies=False,
            debug=False,
        )

    def _assert_success_response(self, body: bytes) -> Any:
        """Assert unified success response (meta.code==0) and return data field content."""

        payload = json.loads(body.decode('utf-8'))
        assert isinstance(payload, dict), f'Response payload must be dict, got {type(payload)!r}'
        assert 'meta' in payload and 'data' in payload, \
            f'Response must contain meta and data, got keys={list(payload.keys())!r}'
        meta = payload['meta']
        assert isinstance(meta, dict), f'meta field must be dict, got {type(meta)!r}'
        assert meta.get('code') == 0, f'meta.code must be 0 for success, got {meta.get("code")!r}'
        return payload['data']

    def _assert_error_response(self, body: bytes) -> int:
        """Assert business error response (meta.code!=0) and return meta.code."""

        payload = json.loads(body.decode('utf-8'))
        assert isinstance(payload, dict) and 'meta' in payload
        code = payload['meta'].get('code')
        assert code != 0, f'Expected error response with meta.code != 0, got code={code!r}'
        return code

    def test_customer_task_project_get_returns_list_structure(self) -> None:
        """GET /api/customer/task/plan/ should return 200 with data as list when stub returns empty list."""

        with patch('web.handlers.task.select_task_project_list', new_callable=AsyncMock, return_value=[]):
            response = self.fetch('/api/customer/task/plan/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)
        assert isinstance(data, list), f'data must be list, got {type(data)!r}'
        assert data == []

    def test_customer_task_project_get_returns_task_list_when_non_empty(self) -> None:
        """GET /api/customer/task/plan/ should return 200 with data as to_dict list when stub returns tasks."""

        class _StubTask:
            def to_dict(self) -> dict[str, Any]:
                return {'id': 1, 'task_digest': 'd1'}

        with patch(
            'web.handlers.task.select_task_project_list',
            new_callable=AsyncMock,
            return_value=[_StubTask(), _StubTask()],
        ):
            response = self.fetch('/api/customer/task/plan/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)
        assert isinstance(data, list) and len(data) == 2
        assert data[0]['task_digest'] == 'd1'

    def test_customer_task_project_post_success_returns_created_data(self) -> None:
        """POST /api/customer/task/plan/ should return 200 with created result when body is valid."""

        class _StubProject:
            def to_dict(self) -> dict[str, Any]:
                return {'id': 1, 'task_digest': 'd', 'task_prompt': 'p'}

        with patch(
            'web.handlers.task.create_task_project',
            new_callable=AsyncMock,
            return_value=_StubProject(),
        ):
            response = self.fetch(
                '/api/customer/task/plan/',
                method='POST',
                body=json.dumps({
                    'task_digest': 'digest',
                    'task_prompt': 'prompt',
                    'setting': _VALID_SETTING,
                }),
                headers={'Content-Type': 'application/json'},
            )

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)
        assert data.get('task_digest') == 'd' and data.get('task_prompt') == 'p'

    def test_customer_task_project_post_missing_digest_returns_error(self) -> None:
        """POST /api/customer/task/plan/ should return business error response when task_digest is missing."""

        response = self.fetch(
            '/api/customer/task/plan/',
            method='POST',
            body=json.dumps({
                'task_prompt': 'p',
                'setting': _VALID_SETTING,
            }),
            headers={'Content-Type': 'application/json'},
        )

        assert response.code == 200, 'BaseHandler returns business errors via HTTP 200 with non-zero meta.code'
        self._assert_error_response(response.body)

    def test_customer_task_project_delete_success_returns_boolean(self) -> None:
        """DELETE /api/customer/task/plan/?id=1 should return 200 with data True when stubbed delete succeeds."""

        with patch(
            'web.handlers.task.delete_task_project',
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = self.fetch('/api/customer/task/plan/?id=1', method='DELETE')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)
        assert data is True

    def test_customer_task_project_delete_invalid_id_returns_error(self) -> None:
        """DELETE /api/customer/task/plan/?id=0 should return business error response when id is invalid."""

        response = self.fetch('/api/customer/task/plan/?id=0', method='DELETE')

        assert response.code == 200, 'BaseHandler returns business errors via HTTP 200 with non-zero meta.code'
        self._assert_error_response(response.body)

    def test_task_history_list_get_returns_paginated_structure(self) -> None:
        """GET /api/task/history/ should return paginated structure fields total/items/page/size when stubbed."""

        class _StubHistory:
            def to_dict(self) -> dict[str, Any]:
                return {'id': 1, 'status': 'success'}

        with patch(
            'web.handlers.task.TaskHistoryModule.select_task_history_list',
            new_callable=AsyncMock,
            return_value=[_StubHistory()],
        ), patch(
            'web.handlers.task.TaskHistoryModule.amount_task_history_list',
            new_callable=AsyncMock,
            return_value=1,
        ):
            response = self.fetch('/api/task/history/?page=1&size=10')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)
        assert 'total' in data and 'items' in data and 'page' in data and 'size' in data
        assert data['total'] == 1 and data['page'] == 1 and data['size'] == 10
        assert len(data['items']) == 1 and data['items'][0]['status'] == 'success'

    def test_task_history_view_get_valid_pk_returns_detail(self) -> None:
        """GET /api/task/history/1/ should return 200 with record dict when stub returns one history record."""

        class _StubHistory:
            def to_dict(self) -> dict[str, Any]:
                return {'id': 1, 'pk': 1, 'status': 'success'}

        with patch(
            'web.handlers.task.TaskHistoryModule.select_task_history_by_id',
            new_callable=AsyncMock,
            return_value=_StubHistory(),
        ):
            response = self.fetch('/api/task/history/1/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)
        assert data.get('pk') == 1 and data.get('status') == 'success'

    def test_task_history_view_get_valid_pk_no_result_returns_empty_data(self) -> None:
        """GET /api/task/history/999/ should return 200 with empty dict when stub returns None."""

        with patch(
            'web.handlers.task.TaskHistoryModule.select_task_history_by_id',
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = self.fetch('/api/task/history/999/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)
        assert data == {}

    def test_task_history_view_get_invalid_pk_returns_error(self) -> None:
        """GET /api/task/history/0/ should return business error response when pk is invalid."""

        response = self.fetch('/api/task/history/0/')

        assert response.code == 200, 'BaseHandler returns business errors via HTTP 200 with non-zero meta.code'
        self._assert_error_response(response.body)

    def test_chain_task_history_get_returns_list_structure(self) -> None:
        """GET /api/task/history/chain/{session_id}/ should return 200 with empty list when stub returns empty list."""

        with patch(
            'web.handlers.task.TaskHistoryModule.select_task_history_by_session_id',
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = self.fetch('/api/task/history/chain/a1b2c3d4-e5f6-7890-abcd-ef1234567890/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)
        assert data == []

    def test_chain_task_history_get_returns_items_when_non_empty(self) -> None:
        """GET /api/task/history/chain/{session_id}/ should return 200 with to_dict list when stub returns records."""

        session_id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'

        class _StubHistory:
            def to_dict(self) -> dict[str, Any]:
                return {'step': 1, 'session_id': session_id}

        with patch(
            'web.handlers.task.TaskHistoryModule.select_task_history_by_session_id',
            new_callable=AsyncMock,
            return_value=[_StubHistory(), _StubHistory()],
        ):
            response = self.fetch(f'/api/task/history/chain/{session_id}/')

        assert response.code == 200, f'HTTP status must be 200, got {response.code!r}'
        data = self._assert_success_response(response.body)
        assert isinstance(data, list) and len(data) == 2
        assert data[0]['session_id'] == session_id

