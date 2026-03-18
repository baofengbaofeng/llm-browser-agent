"""Workspace management module providing task working directory creation and management functionality."""

from __future__ import annotations  # Enable postponed evaluation of annotations for forward reference type hints

import logging  # Logging module used to record workspace operations and error information
import os  # Operating system module providing directory creation and path manipulation functions

from apps.executor.executor_error import ExecutorNotReadyError  # Executor not ready exception type

_LOGGER = logging.getLogger(__name__)


class ExecutorWorkspace:
    """Executor workspace class managing task log, data, and user directories."""

    def __init__(self, task_id: str, base_dir: str) -> None:
        self.task_id = task_id  # Task unique identifier
        self._initialized = False  # Initialization state flag
        self._base_dir = base_dir  # Workspace base directory
        self._task_dir = os.path.join(base_dir, task_id)  # Task specific directory
        self._logs_dir = os.path.join(self._task_dir, 'logs')  # Log files directory
        self._data_dir = os.path.join(self._task_dir, 'data')  # Data files directory
        self._user_dir = os.path.join(self._task_dir, 'user')  # User files directory

    @property
    def task_dir(self) -> str:
        """Return task directory path."""

        return self._task_dir

    @property
    def logs_dir(self) -> str:
        """Return logs directory path."""

        return self._logs_dir

    @property
    def data_dir(self) -> str:
        """Return data directory path."""

        return self._data_dir

    @property
    def user_dir(self) -> str:
        """Return user directory path."""

        return self._user_dir

    def initialize(self) -> None:
        """Initialize workspace directories, creating log, data, and user directories."""

        if self._initialized:
            return

        try:
            os.makedirs(self._logs_dir, exist_ok=True)
        except OSError as e:
            _LOGGER.error('Failed to create logs directory %s: %s', self._logs_dir, e)
            raise ExecutorNotReadyError(f'Failed to create logs directory {self._logs_dir}: {e}') from e

        try:
            os.makedirs(self._data_dir, exist_ok=True)
        except OSError as e:
            _LOGGER.error('Failed to create data directory %s: %s', self._data_dir, e)
            raise ExecutorNotReadyError(f'Failed to create data directory {self._data_dir}: {e}') from e

        try:
            os.makedirs(self._user_dir, exist_ok=True)
        except OSError as e:
            _LOGGER.error('Failed to create user directory %s: %s', self._user_dir, e)
            raise ExecutorNotReadyError(f'Failed to create user directory {self._user_dir}: {e}') from e

        self._initialized = True
        _LOGGER.debug('Workspace directories initialized for task %s', self.task_id)

    def get_conversation_path(self) -> str:
        """Return path for conversation log file."""

        return os.path.join(self._logs_dir, f'conversation_{self.task_id}.txt')

