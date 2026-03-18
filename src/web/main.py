#!/usr/bin/env python
"""Tornado Web application entry module, providing HTTP service startup and routing configuration functionality."""

import asyncio  # Async IO support module, providing event loop and coroutine functionality
import logging  # Logging module, providing application log output functionality
import os  # Operating system interface module, providing file path operations
import signal  # Signal handling module, used for capturing system signals for graceful shutdown
from logging.handlers import TimedRotatingFileHandler  # Time-based rotating file log handler
from types import FrameType  # Call stack frame type, used for signal handler callback parameter annotation

import nest_asyncio  # Nested event loop support library, solving asyncio and Tornado compatibility issues
import tornado.ioloop  # Tornado event loop module, handling async IO events
import tornado.web  # Tornado Web framework module, providing HTTP request handling functionality

from apps.executor.executor_factory import cancel_all_running_tasks  # Cancel all running executor tasks on shutdown
from apps.executor.executor_factory import get_running_task_ids  # Get running executor tasks for graceful shutdown wait
from web.handlers.executor import TaskCancelHandler  # Task cancel API handler for HTTP cancel endpoint behavior
from web.handlers.configuration import AgentConfigHandler  # Agent config API handler returning agent runtime settings
from web.handlers.configuration import AllConfigHandler  # All config API handler returning merged config payload
from web.handlers.configuration import BrowserConfigHandler  # Browser config API handler returning browser settings
from web.handlers.configuration import ModelConfigHandler  # Model config API handler returning LLM runtime settings
from web.handlers.customer import CustomerTaskArgsHandler  # Customer task args handler returning per-customer defaults
from web.handlers.task import CustomerTaskProjectHandler  # Task project handler providing create/list/delete APIs
from web.handlers.executor import ApplicationIndexHandler  # Index handler rendering UI entry page and injecting config
from web.handlers.executor import TaskStatusHandler  # Task status handler returning current execution status
from web.handlers.executor import TaskStreamHandler  # Task stream handler pushing execution events to frontend
from web.handlers.executor import TaskSubmitHandler  # Task submit handler creating and starting new task execution
from web.handlers.instruct import InstructTaskSubmitHandler  # Instruction submit handler parsing natural language text
from web.handlers.language import LanguageHandler  # Language handler returning translation mappings for UI display
from web.handlers.task import ChainTaskHistoryHandler  # Chain history handler returning per-session step histories
from web.handlers.task import TaskHistoryViewHandler  # Task history detail handler returning a single record payload
from web.handlers.task import TaskHistoryListHandler  # Task history list handler returning paginated record lists
from environment.environment import get_application_config  # Application config getter using in-process caching
from environment.environment import get_config_bool  # Bool config accessor converting values for runtime settings
from environment.environment import get_config_int  # Int config accessor converting values for runtime settings
from environment.environment import get_config_value  # Generic config accessor supporting default fallback values
from core.database.session import close_db  # Database close function used for graceful shutdown resource cleanup
from core.database.session import start_db  # Database start function used for startup initialization and migrations

# Module-level config cache, avoiding repeated loading of config files
_CONFIG = get_application_config()

# Application base directory path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_LOG_ROTATION_BACKUP_COUNT = 168  # Default hourly backups count keeping 7 days of logs for operational debugging
DEFAULT_SHUTDOWN_TIMEOUT_SECONDS = 30  # Default graceful shutdown timeout in seconds before force stopping service
MAX_GRACEFUL_SHUTDOWN_WAIT_SECONDS = 5  # Maximum wait seconds for in-flight requests before closing dependencies
SHUTDOWN_POLL_INTERVAL_SECONDS = 0.2  # Polling interval for checking in-process task completion during shutdown
SHUTDOWN_CANCEL_GRACE_SECONDS = 2.0  # Grace seconds to wait after cancellation requests before closing dependencies

_LOGGING_INITIALIZED = False  # Process-wide logging init guard preventing duplicate handler setup on repeated imports


def _get_logs_dir() -> str:
    """Get log directory path from application config and convert to absolute path for unified output location.

    Returns:
        str: Absolute path of log directory, if config is relative path then expand based on project root directory.
    """

    log_dir = get_config_value(_CONFIG, 'llm_browser_agent.server.logging.dir', 'logs')

    # If relative path, convert to absolute path
    if not os.path.isabs(log_dir):
        log_dir = os.path.join(BASE_DIR, log_dir)

    return log_dir


def _setup_logging() -> None:
    """Initialize logging system and output to files as access/error/general categories.

    Returns:
        None: This function only has side effects, used to configure root logger handlers and levels.
    """
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return

    # Get log directory
    logs_dir = _get_logs_dir()

    # Ensure log directory exists
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Read log configuration
    log_format = get_config_value(_CONFIG, 'llm_browser_agent.server.logging.format')
    rotation_when = get_config_value(_CONFIG, 'llm_browser_agent.server.logging.rotation.when', 'H')
    rotation_interval = get_config_int(_CONFIG, 'llm_browser_agent.server.logging.rotation.interval', 1)
    rotation_backup = get_config_int(
        _CONFIG,
        'llm_browser_agent.server.logging.rotation.backup_count',
        DEFAULT_LOG_ROTATION_BACKUP_COUNT,
    )

    formatter = logging.Formatter(log_format)

    # 1. Access log handler - records all HTTP requests
    access_handler = TimedRotatingFileHandler(
        filename=os.path.join(logs_dir, 'llm_browser_agent-access.log'),
        when=rotation_when,
        interval=rotation_interval,
        backupCount=rotation_backup,
        encoding='utf-8'
    )
    access_handler.setFormatter(formatter)
    access_handler.setLevel(logging.INFO)
    access_handler.addFilter(lambda record: getattr(record, 'log_type', None) == 'access')

    # 2. Error log handler - records WARNING and above levels
    error_handler = TimedRotatingFileHandler(
        filename=os.path.join(logs_dir, 'llm_browser_agent-errors.log'),
        when=rotation_when,
        interval=rotation_interval,
        backupCount=rotation_backup,
        encoding='utf-8'
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.WARNING)

    # 3. Common log handler - records INFO and DEBUG levels
    common_handler = TimedRotatingFileHandler(
        filename=os.path.join(logs_dir, 'llm_browser_agent-common.log'),
        when=rotation_when,
        interval=rotation_interval,
        backupCount=rotation_backup,
        encoding='utf-8'
    )
    common_handler.setFormatter(formatter)
    common_handler.setLevel(logging.DEBUG)
    common_handler.addFilter(lambda record: record.levelno < logging.WARNING)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, get_config_value(_CONFIG, 'llm_browser_agent.server.logging.level')))

    # Clear default handlers and add custom handlers
    root_logger.handlers = []
    root_logger.addHandler(access_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(common_handler)

    _LOGGING_INITIALIZED = True


_LOGGER = logging.getLogger(__name__)


class Application(tornado.web.Application):
    """Tornado Web application class, configuring routes and application settings."""

    def __init__(self) -> None:
        """Initialize Tornado application and register URL routes with core runtime settings.

        Returns:
            None: Constructor initializes Tornado Application and registers routes and template/static resource configs.
        """

        handlers = [
            (r'/api/task/', TaskSubmitHandler),
            (r'/api/task/([a-f0-9\-]+)/status/', TaskStatusHandler),
            (r'/api/task/([a-f0-9\-]+)/cancel/', TaskCancelHandler),
            (r'/api/task/([a-f0-9\-]+)/stream/', TaskStreamHandler),
            (r'/api/language/', LanguageHandler),
            (r'/api/configuration/model/', ModelConfigHandler),
            (r'/api/configuration/agent/', AgentConfigHandler),
            (r'/api/configuration/browser/', BrowserConfigHandler),
            (r'/api/configuration/', AllConfigHandler),
            (r'/api/customer/task/args/', CustomerTaskArgsHandler),
            (r'/api/customer/task/plan/', CustomerTaskProjectHandler),
            (r'/api/task/history/', TaskHistoryListHandler),
            (r'/api/task/history/([0-9]+)/', TaskHistoryViewHandler),
            (r'/api/task/history/task/([a-f0-9\-]+)/', TaskHistoryByTaskIdHandler),
            (r'/api/task/history/chain/([a-f0-9\-]+)/', ChainTaskHistoryHandler),
            (r'/api/task/instruct/', InstructTaskSubmitHandler),
            (r'/', ApplicationIndexHandler),
        ]

        settings = {
            'template_path': os.path.join(BASE_DIR, 'templates'),
            'static_path': os.path.join(BASE_DIR, 'static'),
            'static_url_prefix': '/static/',
            'cookie_secret': get_config_value(_CONFIG, 'llm_browser_agent.server.security.cookie_secret'),
            'xsrf_cookies': False,
            'debug': get_config_bool(_CONFIG, 'llm_browser_agent.server.debug'),
        }

        super().__init__(handlers, **settings)
        _LOGGER.info('Tornado application initialized')


async def graceful_shutdown() -> None:
    """Gracefully shutdown service and release critical resources like DB connections to avoid data corruption.

    Returns:
        None: This function completes service graceful exit by closing DB connections and stopping event loop.
    """

    _LOGGER.info('Starting graceful shutdown...')

    # Stop accepting new requests (stop listening for new connections)
    # Tornado's HTTPServer needs to keep reference in Application to stop
    # Here we implement this by closing IOLoop

    # Wait for existing requests to complete (currently fixed wait, not polling by running task count)
    shutdown_timeout = get_config_int(
        _CONFIG,
        'llm_browser_agent.server.shutdown_timeout',
        DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
    )
    _LOGGER.info('Waiting up to %ds for requests to complete...', shutdown_timeout)
    await asyncio.sleep(min(shutdown_timeout, MAX_GRACEFUL_SHUTDOWN_WAIT_SECONDS))

    # Wait for in-process executor tasks to complete before closing dependencies like DB connections.
    deadline = asyncio.get_running_loop().time() + float(shutdown_timeout)
    while True:
        running_task_ids = get_running_task_ids()
        if not running_task_ids:
            break

        remaining_seconds = deadline - asyncio.get_running_loop().time()
        if remaining_seconds <= 0:
            _LOGGER.warning(
                'Graceful shutdown timed out with %s running tasks, cancelling them now',
                len(running_task_ids),
            )
            cancelled_task_ids = cancel_all_running_tasks()
            _LOGGER.warning('Cancelled tasks: %s', cancelled_task_ids)
            break

        _LOGGER.info(
            'Waiting for %s running tasks to finish, remaining timeout: %.1fs',
            len(running_task_ids),
            remaining_seconds,
        )
        await asyncio.sleep(min(SHUTDOWN_POLL_INTERVAL_SECONDS, remaining_seconds))

    # If we cancelled tasks, wait a short grace period for cleanup paths to run.
    cancelled_running_task_ids = get_running_task_ids()
    if cancelled_running_task_ids:
        _LOGGER.warning(
            'Waiting %.1fs for %s cancelled tasks cleanup',
            SHUTDOWN_CANCEL_GRACE_SECONDS,
            len(cancelled_running_task_ids),
        )
        await asyncio.sleep(SHUTDOWN_CANCEL_GRACE_SECONDS)

    # Close database connections
    _LOGGER.info('Closing database connections...')
    await close_db()

    _LOGGER.info('Graceful shutdown completed')


def setup_signal_handlers() -> None:
    """Setup signal handlers, capture SIGTERM and SIGINT signals for graceful shutdown process.

    Returns:
        None: This function registers signal handler callbacks and dispatches shutdown to Tornado IOLoop.
    """

    def signal_handler(sig: int, frame: FrameType | None) -> None:
        """Handle system signals and trigger async shutdown logic to ensure orderly resource release.

        Args:
            sig: Received signal number, usually SIGTERM or SIGINT.
            frame: Call stack frame info when signal triggered, may be None in some runtime environments.

        Returns:
            None: This function only dispatches shutdown process to IOLoop for async execution.
        """

        _LOGGER.info('Received signal %s, initiating graceful shutdown...', sig)
        io_loop = tornado.ioloop.IOLoop.current()
        io_loop.add_callback_from_signal(shutdown_server)

    async def shutdown_server() -> None:
        """Execute async shutdown logic and stop Tornado IOLoop to end event loop.

        Returns:
            None: This coroutine executes graceful_shutdown and stops IOLoop to end service.
        """

        await graceful_shutdown()
        io_loop = tornado.ioloop.IOLoop.current()
        io_loop.stop()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def main() -> None:
    """Application main entry function, initialize database and start HTTP service main loop.

    Returns:
        None: This coroutine completes database initialization, signal registration and Tornado IOLoop startup.
    """

    _setup_logging()

    await start_db()

    # Setup signal handlers
    setup_signal_handlers()

    Application().listen(get_config_int(_CONFIG, 'llm_browser_agent.server.port'))

    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        _LOGGER.info('Received KeyboardInterrupt')
    finally:
        # Ensure database connections are closed
        await close_db()


if __name__ == '__main__':
    nest_asyncio.apply()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Already handled in main

