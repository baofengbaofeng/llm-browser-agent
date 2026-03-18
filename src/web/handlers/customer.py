"""Customer handler module.

Provides HTTP endpoints for browser requests including task parameter retrieval.
"""

import logging  # Logging module for recording task parameter related operation logs

from apps.configuration.configuration import get_default_config  # Default configuration singleton getter function
from apps.customer.customer_profile import CustomerInterceptor  # Customer interceptor injecting customer_id
from apps.customer.customer_setting import CustomerSettingModule  # Customer setting module providing task config query
from web.handlers.base_handler import BaseHandler  # Base Handler base class providing unified write_error capabilities
from web.handlers.response import success_response  # Success response constructor function
from core.security.security import SecurityMixin  # Security response header mixin class

_LOGGER = logging.getLogger(__name__)


class CustomerTaskArgsHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Customer task args handler returning latest customer configuration or system default configuration."""

    async def get(self) -> None:
        """Handle GET request returning customer task config with fallback to defaults and unified error output."""

        custom_setting = await CustomerSettingModule.select_setting_latest(self.customer_id)

        if custom_setting:
            self.write(success_response(data=custom_setting.to_dict()))
            return

        config = get_default_config()

        default_setting = {
            'model_name': config.model.name,
            'model_temperature': config.model.temperature,
            'model_top_p': config.model.top_p,
            'model_api_url': config.model.api_url,
            'model_api_key': config.model.api_key,
            'model_timeout': config.model.timeout,
            'agent_use_vision': config.agent.use_vision,
            'agent_max_actions_per_step': config.agent.max_actions_per_step,
            'agent_max_failures': config.agent.max_failures,
            'agent_step_timeout': config.agent.step_timeout,
            'agent_use_thinking': config.agent.use_thinking,
            'agent_calculate_cost': config.agent.calculate_cost,
            'agent_fast_mode': config.agent.fast_mode,
            'agent_demo_mode': config.agent.demo_mode,
            'browser_headless': config.browser.headless,
            'browser_enable_security': config.browser.enable_security,
            'browser_use_sandbox': config.browser.use_sandbox,
        }

        self.write(success_response(data=default_setting))

