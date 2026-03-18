"""Language handler module providing HTTP API endpoints for multi-language translation configuration."""

from typing import Dict  # Dictionary type hint for function return value type annotation declarations

from apps.customer.customer_profile import CustomerInterceptor  # Customer interceptor injecting customer_id
from apps.language.language import LANGUAGE_NAMES  # Language code-to-name mapping for validation and iteration
from apps.language.language import get_all_translations  # Translation loader returning all translations for a language
from web.handlers.base_handler import BaseHandler  # Base Handler with unified exception handling and JSON errors
from web.handlers.response import success_response  # Success response constructor returning unified JSON structure
from core.security.security import SecurityMixin  # Security mixin attaching generic security-related HTTP headers


class LanguageHandler(SecurityMixin, CustomerInterceptor, BaseHandler):
    """Language configuration handler returning single language or all language translations based on lang parameter."""

    def get(self) -> None:
        """Handle GET request returning language translation configuration."""

        lang = self.get_argument('lang', '')

        if not lang:
            all_configs: Dict[str, Dict[str, str]] = {}
            for lang_code in LANGUAGE_NAMES.keys():
                all_configs[lang_code] = get_all_translations(lang_code)
            self.write(success_response(data=all_configs))
            return

        if lang not in LANGUAGE_NAMES:
            self.write(success_response(data={}))
            return

        self.write(success_response(data=get_all_translations(lang)))

