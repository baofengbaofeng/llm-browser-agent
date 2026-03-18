"""Executor log handler module.

Convert LLM/Agent/Browser logs to events by intercepting records via logging.Handler and forwarding via callback.
"""

import logging  # Standard logging library providing logging infrastructure and Handler base class
from typing import Callable  # Callable type hint for defining callback function type signature


class ExecutorEventLogger(logging.Handler):
    """Private log event handler converting log records to event callbacks for external processing via _handler."""

    def __init__(self, task_id: str, handler: Callable[[str, str, str, str], None]) -> None:
        """Initialize log event handler."""

        super().__init__()
        self._task_id = task_id  # Used to identify log source and event association
        self._handler = handler  # Passes log data to external event system

    def emit(self, record: logging.LogRecord) -> None:
        """Handle log record, calling callback function to pass log data."""

        message = self.format(record)  # Use formatter to format log message, extracting plain text content
        # Call callback function passing log data, parameter order: task_id, logger name, log level, message content
        self._handler(self._task_id, record.name, record.levelname, message)


def attach_handler(task_id: str, callback: Callable[[str, str, str, str], None], logger_names: tuple[str, ...] = (
    'browser_use', 'langchain_openai', 'openai')) -> list[logging.Handler]:
    """Attach log handler to specified loggers, starting log collection."""

    handlers: list[logging.Handler] = []  # Store created handler list for return and subsequent cleanup
    for name in logger_names:  # Iterate through all target logger names, attaching handler to each logger
        handler = ExecutorEventLogger(task_id, callback)  # Create log event handler instance
        handler.setLevel(logging.INFO)  # Set handler level to INFO, only collecting INFO and above level logs
        handler.setFormatter(logging.Formatter('%(message)s'))  # Output message only without time prefix
        logger = logging.getLogger(name)  # Get logger instance, automatically created if not existent
        logger.addHandler(handler)  # Add handler to logger handler list, starting log output interception
        handlers.append(handler)  # Add handler to return list for subsequent detach_handler cleanup
    return handlers  # Return handler list, caller needs to save for subsequent detach_handler operations


def detach_handler(handlers: list[logging.Handler], logger_names: tuple[str, ...] = (
    'browser_use', 'langchain_openai', 'openai')) -> None:
    """Remove log handler from specified loggers, stopping log collection."""

    for name in logger_names:  # Iterate through all target logger names for cleanup
        logger = logging.getLogger(name)  # Get logger instance, creating empty logger if not existent
        for handler in handlers:  # Iterate through all handlers that need removal
            if handler in logger.handlers:  # Check if handler exists in current logger's handler list
                logger.removeHandler(handler)  # Remove handler from logger to stop log interception

