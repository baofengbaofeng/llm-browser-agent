"""Database connection configuration module, responsible for building Tortoise ORM
database configuration dict from app config."""

import os  # Operating system interface module, providing file path parsing and combination capabilities

from environment.environment import get_application_config  # Application configuration getter (process singleton)
from environment.environment import get_config_value  # String type configuration getter function


def parse_sqlite_path(db_url: str) -> str | None:
    """Parse SQLite absolute path from database URL, return None for non-SQLite URLs.

    Args:
        db_url: Database connection URL, format like "sqlite://.data/llm_browser_agent.db"

    Returns:
        str | None: Absolute path of the database file, return None for non-SQLite URLs
    """

    if not db_url.startswith('sqlite://'):
        return None
    db_path = db_url[9:]
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), db_path)
    return db_path


def get_db_url() -> str:
    """Read database connection URL string from application configuration, as the unified
    config entry for connection and initialization."""

    return get_config_value(get_application_config(), 'llm_browser_agent.server.database.url')


def get_db_config() -> dict:
    """Get Tortoise ORM database configuration dictionary, including connection pool configuration."""

    db_url = get_db_url()

    if db_url.startswith('mysql://'):
        connection_config = {
            'engine': 'tortoise.backends.mysql',
            'credentials': {
                'uri': db_url
            }
        }
    else:
        file_path = parse_sqlite_path(db_url)
        connection_config = {
            'engine': 'tortoise.backends.sqlite',
            'credentials': {
                'file_path': file_path if file_path else db_url.replace('sqlite://', '')
            }
        }

    return {
        'connections': {
            'default': connection_config
        },
        'apps': {
            'models': {
                'models': [
                    'models.customer_profile',
                    'models.customer_setting',
                    'models.task_project',
                    'models.task_history',
                ],
                'default_connection': 'default',
            }
        }
    }

