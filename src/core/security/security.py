"""Security middleware module providing CSP, security headers and basic input sanitization using secure and bleach."""

import logging  # Logging module for recording security events
from typing import List  # List type hint for sanitize_request_data return type annotation

import bleach  # HTML cleaning library for removing potential XSS-related tags and attributes
from secure import Secure  # Security headers tool providing various security-related HTTP headers
from tornado.web import RequestHandler  # Tornado request handler base class

_LOGGER = logging.getLogger(__name__)

_SECURE = Secure()


class SecurityHeadersMiddleware:
    """Security header middleware injecting CSP and other security related HTTP headers."""

    # CSP directive set for resource loading and embedding policies, tweak sources as needed.
    CSP_DIRECTIVES = {
        'default-src': ["'self'"],  # Default resource sources allowed by CSP.
        'object-src': ["'none'"],  # Plugin resources such as object/embed.
        'script-src': ["'self'", "'unsafe-inline'"],  # Script sources (consider tightening in production).
        'frame-src': ["'none'"],  # Embedded frame sources.
        'media-src': ["'self'"],  # Media sources such as audio/video.
        'style-src': ["'self'", "'unsafe-inline'"],  # Stylesheet sources (consider tightening in production).
        'img-src': ["'self'", 'data:', 'blob:'],  # Image sources.
        'font-src': ["'self'"],  # Font sources.
        'connect-src': ["'self'"],  # Network connection targets for XHR/fetch/WebSocket.
        'base-uri': ["'self'"],  # Base URL sources for <base> tag.
        'form-action': ["'self'"],  # Form submission targets.
    }

    # Other security headers, may override secure defaults for embedding/redirect/permissions policies.
    SECURITY_HEADERS = {
        'Permissions-Policy': 'geolocation=(self), microphone=(self), camera=(self)',  # Feature policy defaults.
        'X-Content-Type-Options': 'nosniff',  # Prevent MIME type sniffing.
        'X-XSS-Protection': '1; mode=block',  # Legacy XSS protection header for older browsers.
        'Referrer-Policy': 'strict-origin-when-cross-origin',  # Referrer header policy.
        'X-Frame-Options': 'DENY',  # Prevent clickjacking via framing.
    }

    @classmethod
    def apply_to_handler(cls, handler: RequestHandler) -> None:
        """Apply security response headers to handler, injecting CSP and other security related header fields."""

        # secure.Secure.framework is a dynamic property, type checker cannot recognize it,
        # but at runtime it correctly injects various security response headers
        _SECURE.framework.tornado(handler)  # type: ignore[attr-defined]

        handler.set_header('Content-Security-Policy', cls._build_csp_header())

        # Override or supplement other security headers
        for header, value in cls.SECURITY_HEADERS.items():
            handler.set_header(header, value)

    @classmethod
    def _build_csp_header(cls) -> str:
        """Build Content-Security-Policy response header value string from CSP directives."""

        return '; '.join(
            f"{directive} {' '.join(sources)}"
            for directive, sources in cls.CSP_DIRECTIVES.items()
        )


class SecurityMixin:
    """Security mixin providing default security headers for Tornado handlers."""

    def set_default_headers(self) -> None:
        """Set default response headers, adding project security headers and CSP policies on top of Tornado defaults."""

        # Explicitly call RequestHandler.set_default_headers, convention is that mixin classes
        # only combine with RequestHandler and its subclasses
        RequestHandler.set_default_headers(self)  # type: ignore[misc]
        SecurityHeadersMiddleware.apply_to_handler(self)


def sanitize_request_data(data: dict | str | None | List[dict | str | None]) -> (
        dict | List[dict | str | None] | str | None):
    """Sanitize request data recursively to reduce XSS and injection risks while preserving overall structure."""

    if data is None:
        return None

    if isinstance(data, str):
        return _sanitize_string(data)

    if isinstance(data, dict):
        return {key: sanitize_request_data(value) for key, value in data.items()}

    if isinstance(data, list):
        return [sanitize_request_data(item) for item in data]

    return data


def _sanitize_string(value: str) -> str:
    """Sanitize string by removing HTML tags and attributes to reduce basic XSS risks before rendering."""

    if not isinstance(value, str):
        return str(value)

    return bleach.clean(value, tags=[], attributes={}, protocols=[], strip=True)

