"""Executor handler module providing HTTP API endpoints for task submission, status query, and stream output."""

import json  # JSON serialization and deserialization module for handling request and response data
import logging  # Logging module for recording task execution and error information

import tornado.web  # Tornado Web framework module providing HTTP request handling base class

from apps.configuration.configuration import get_default_config  # Default configuration getter
from apps.customer.customer_profile import CustomerInterceptor  # Customer interceptor base class
from apps.executor.executor_configuration import ExecutorConfiguration  # Executor configuration class
from apps.executor.executor_factory import task_cancel_handle  # Task cancellation function
from apps.executor.executor_factory import task_status_handle  # Task status query function
from apps.executor.executor_factory import task_submit_handle  # Task submission function
from apps.language.language import LANGUAGE_NAMES  # Supported language name mapping
from apps.language.language import get_all_translations  # Get all translations for specified language
from web.handlers.response import failure_response  # Failure response constructor
from web.handlers.response import success_response  # Success response constructor
from core.security.security import SecurityMixin  # Security response header mixin
from core.validators import CreateTaskRequestModel  # Task submission request validation model
from core.validators import validate_request_body  # Request body validation function

_LOGGER = logging.getLogger(__name__)
_CONFIG = get_default_config()


class ApplicationIndexHandler(SecurityMixin, CustomerInterceptor, tornado.web.RequestHandler):
    """Index page handler rendering main page and injecting configuration and translation data."""

    def get(self) -> None:
        lang = self.get_argument('lang', 'zh-hans')
        if lang not in LANGUAGE_NAMES:
            lang = 'zh-hans'

        self.render('index.html', static_url=self.static_url, json_encode=json.dumps, lang=lang,
            language_dict=get_all_translations(lang),
            language_list=LANGUAGE_NAMES,
            browser_config=_CONFIG.browser,
            model_config=_CONFIG.model,
            agent_config=_CONFIG.agent,
            customer_id=self.customer_id,
        )


class TaskSubmitHandler(SecurityMixin, CustomerInterceptor, tornado.web.RequestHandler):
    """Task submission handler processing task creation requests and returning task ID."""

    async def post(self) -> None:
        try:
            # Validate request data using Pydantic
            validated_data = validate_request_body(self.request.body, CreateTaskRequestModel)

            # Convert to ExecutorConfiguration data class
            request = ExecutorConfiguration(
                task_prompts=validated_data.task_prompts,
                model_name=validated_data.model_name,
                model_temperature=validated_data.model_temperature,
                model_top_p=validated_data.model_top_p,
                model_api_url=validated_data.model_api_url,
                model_api_key=validated_data.model_api_key,
                model_timeout=validated_data.model_timeout,
                agent_use_vision=validated_data.agent_use_vision,
                agent_max_actions_per_step=validated_data.agent_max_actions_per_step,
                agent_max_failures=validated_data.agent_max_failures,
                agent_step_timeout=validated_data.agent_step_timeout,
                agent_use_thinking=validated_data.agent_use_thinking,
                agent_calculate_cost=validated_data.agent_calculate_cost,
                agent_fast_mode=validated_data.agent_fast_mode,
                agent_demo_mode=validated_data.agent_demo_mode,
                browser_headless=validated_data.browser_headless,
                browser_enable_security=validated_data.browser_enable_security,
                browser_use_sandbox=validated_data.browser_use_sandbox,
                base_working_dir=validated_data.base_working_dir,
            )
            result = await task_submit_handle(request, self.customer_id)

            _LOGGER.info('Task submit handler, result: %s', result)
            self.write(success_response(data=result))
        except ValueError as e:
            _LOGGER.warning('Task submit validation error: %s', e)
            self.write(failure_response(code=400, text=str(e)))
        except Exception as e:
            _LOGGER.error('Task submit error: %s', e)
            self.write(failure_response(code=500, text='Internal server error'))


class TaskCancelHandler(SecurityMixin, CustomerInterceptor, tornado.web.RequestHandler):
    """Task cancellation handler returning whether task cancellation operation was successful."""

    def post(self, task_id: str) -> None:
        result = task_cancel_handle(task_id)
        _LOGGER.info('Task cancel handler, task_id: %s, result: %s', task_id, result)
        self.write(success_response(data=result))


class TaskStatusHandler(SecurityMixin, CustomerInterceptor, tornado.web.RequestHandler):
    """Task query handler returning current running status of specified task."""

    def get(self, task_id: str) -> None:
        result = task_status_handle(task_id)
        _LOGGER.info('Task status handler, task_id: %s, status: %s', task_id, result)
        self.write(success_response(data={'task_id': task_id, 'status': result}))


class TaskStreamHandler(SecurityMixin, CustomerInterceptor, tornado.web.RequestHandler):
    """Task stream handler using Server-Sent Events to push task execution events (reserved interface)."""

    pass

