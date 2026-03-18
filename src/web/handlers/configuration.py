"""Configuration handler module providing Tornado HTTP API endpoints for configuration queries."""

from dataclasses import asdict  # Dataclass to dict converter for serializing configuration objects to JSON

from apps.configuration.configuration import get_default_config  # Default configuration singleton provider
from apps.customer.customer_profile import CustomerInterceptor  # Customer interceptor injecting customer_id
from web.handlers.base_handler import BaseHandler  # Base Handler with unified exception handling and JSON errors
from web.handlers.response import success_response  # Success response constructor returning unified JSON response
from core.security.security import SecurityMixin  # Security response header mixin adding generic security headers

# Module-level configuration instance initialized on module import
_CONFIG = get_default_config()


class AllConfigHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Global configuration API handler returning full configuration payload."""

    def get(self) -> None:
        """Handle GET request returning all configuration data."""

        self.write(success_response(data=asdict(_CONFIG)))


class BrowserConfigHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Browser configuration API handler returning browser related configuration."""

    def get(self) -> None:
        """Handle GET request returning browser configuration data."""

        self.write(success_response(data=asdict(_CONFIG.browser)))


class AgentConfigHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Agent configuration API handler returning agent related configuration."""

    def get(self) -> None:
        """Handle GET request returning agent configuration data."""

        self.write(success_response(data=asdict(_CONFIG.agent)))


class ModelConfigHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Model configuration API handler returning large language model related configuration."""

    def get(self) -> None:
        """Handle GET request returning model configuration data."""

        self.write(success_response(data=asdict(_CONFIG.model)))

