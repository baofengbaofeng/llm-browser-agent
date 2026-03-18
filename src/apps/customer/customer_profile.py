"""Customer basic information and identity module, providing customer profile service and
cookie-based customer identity interception."""

import uuid  # UUID generation module, used to generate unique customer identifiers

import tornado.web  # Tornado Web framework, providing web request handling base class and cookie operation methods

from environment.environment import get_application_config  # Application configuration getter (process singleton)
from environment.environment import get_config_int  # Integer type configuration getter function
from environment.environment import get_config_value  # String type configuration getter function
from models.customer_profile import CustomerProfile  # Customer basic information model class

_CONFIG = get_application_config()  # Module-level configuration cache, avoiding repeated loading
_CUSTOMER_ID_COOKIE_KEY = get_config_value(_CONFIG, 'llm_browser_agent.customer.cookie_key')  # Cookie key


def get_customer_id(handler: tornado.web.RequestHandler) -> str:
    """Get customer ID from cookie or create one, generate UUID if not exists and write back to secure cookie."""

    customer_id_bytes = handler.get_secure_cookie(_CUSTOMER_ID_COOKIE_KEY)
    if customer_id_bytes:
        return customer_id_bytes.decode('utf-8')

    customer_id = str(uuid.uuid4())

    handler.set_secure_cookie(
        _CUSTOMER_ID_COOKIE_KEY,
        customer_id,
        expires_days=get_config_int(_CONFIG, 'llm_browser_agent.customer.cookie_max_age_days'),
    )
    return customer_id


class CustomerInterceptor(tornado.web.RequestHandler):
    """Customer identity request interceptor, automatically injects customer_id attribute
    before each request processing."""

    customer_id: str  # Customer identifier attribute injected by interceptor

    def prepare(self) -> None:
        """Intercept request and inject customer identity before processing, then continue
        parent class prepare logic."""

        self.customer_id = get_customer_id(self)
        super().prepare()


class CustomerProfileModule:
    """Customer basic information module class, handles customer profile creation, query and existence check logic."""

    @staticmethod
    async def create_profile() -> CustomerProfile:
        """Create new customer basic information record, using random UUID as customer_id and return that profile."""

        customer_id = str(uuid.uuid4())
        profile = await CustomerProfile.create(customer_id=customer_id,
            created_by=customer_id,
            updated_by=customer_id,
        )

        return profile

    @staticmethod
    async def select_profile(customer_id: str) -> CustomerProfile | None:
        """Get basic information record by customer ID, return None if not exists,
        raise exception for invalid parameter."""

        if not isinstance(customer_id, str) or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')

        return await CustomerProfile.filter(customer_id=customer_id).first()

    @staticmethod
    async def exists_profile(customer_id: str) -> bool:
        """Check if customer basic information exists, return True if exists, False otherwise,
        raise exception for invalid parameter."""

        if not isinstance(customer_id, str) or not customer_id.strip():
            raise ValueError('customer_id must be a non-empty string')

        return await CustomerProfile.filter(customer_id=customer_id).exists()

