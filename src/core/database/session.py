"""Database session management.

Responsible for connection lifecycle, transaction context, and SQLite initialization.
"""

import logging  # Logging utilities for database initialization and session management
import os  # Operating system interface module providing DDL file path parsing and database file path construction
import sqlite3  # SQLite database module for executing DDL scripts to initialize local database file structure
from contextlib import asynccontextmanager  # Async context manager decorator for transaction context acquisition logic
from typing import AsyncGenerator  # Async generator type hint for get_db_transaction return type annotation

import sqlglot  # SQL parsing and translation library for auto-converting MySQL dialect DDL scripts to SQLite dialect
from tortoise import Tortoise  # Tortoise ORM used for database connections and model-table mappings
from tortoise.transactions import in_transaction  # Transaction context manager for async transaction control

from core.database.connect import get_db_config  # Database config getter returning connection dict for Tortoise ORM
from core.database.connect import get_db_url  # Database URL getter for unified connection and initialization entry
from core.database.connect import parse_sqlite_path  # SQLite path parser extracting database file absolute path

_LOGGER = logging.getLogger(__name__)

DDL_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'deployments',
    'ddl',
    'database.sql',
)


def _convert_mysql_ddl_to_sqlite(mysql_ddl: str) -> str:
    """Convert MySQL dialect DDL script to SQLite dialect DDL script text using sqlglot."""

    try:
        expressions = sqlglot.parse(mysql_ddl, read='mysql')
    except Exception as error:
        _LOGGER.error('Failed to parse MySQL DDL with sqlglot: %s', error)
        raise

    sqlite_statements: list[str] = []
    for expression in expressions:
        try:
            sqlite_sql = expression.to_sql(dialect='sqlite')
            sqlite_statements.append(sqlite_sql)
        except Exception as error:
            _LOGGER.warning('Failed to convert expression to SQLite DDL: %s', error)

    return ';\n'.join(sqlite_statements)


def _init_sqlite_db(db_file: str) -> None:
    """Initialize SQLite database and execute DDL script to create table structure if database file does not exist."""

    if os.path.exists(db_file):
        return

    with open(DDL_FILE, 'r', encoding='utf-8') as f:
        ddl_script = f.read()

    sqlite_script = _convert_mysql_ddl_to_sqlite(ddl_script)

    connect = sqlite3.connect(db_file)

    for statement in sqlite_script.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                connect.cursor().execute(statement)
            except sqlite3.Error as e:
                _LOGGER.warning("SQL execution warning: %s", e)

    connect.commit()
    connect.close()


async def start_db() -> None:
    """Initialize database connection, check and create data directory and table structure."""

    db_url = get_db_url()

    db_file = parse_sqlite_path(db_url)
    if db_file:
        db_dir = os.path.dirname(db_file)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        _init_sqlite_db(db_file)

    config = get_db_config()
    await Tortoise.init(config=config)


async def close_db() -> None:
    """Close all database connections."""

    await Tortoise.close_connections()


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator:
    """Get database transaction context manager."""

    async with in_transaction():
        yield

