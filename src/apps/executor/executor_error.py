"""Executor exception module defining executor-related custom exception classes."""


class ExecutorError(Exception):
    """Executor exception base class, parent class for all executor-related exceptions."""

    pass


class ExecutorNotReadyError(ExecutorError):
    """Executor not ready exception thrown when attempting to use an unprepared executor."""

    pass


class ExecutorDisposedError(ExecutorError):
    """Executor disposed exception thrown when attempting to use an already disposed executor."""

    pass


class TaskExecutionError(ExecutorError):
    """Task execution exception thrown when task execution fails."""

    pass

