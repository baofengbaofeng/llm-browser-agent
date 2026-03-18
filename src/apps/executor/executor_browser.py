"""Browser management module providing browser pool operations and browser instance lifecycle management."""

import asyncio  # Async IO support used for coordinating browser pool access and lifecycle operations safely
import logging  # Logging module, recording browser operations and error messages
import os  # Operating system interface module, providing directory creation and path operations functionality
from abc import ABC  # Abstract base class module, used for defining abstract interfaces
from abc import abstractmethod  # Abstract method decorator, marking methods that must be implemented by subclasses
from dataclasses import dataclass  # Dataclass decorator used for defining simple configuration and state containers
from dataclasses import field  # Dataclass field helper used to provide defaults for configuration attributes safely
from typing import Any  # Any type hint, browser-use library lacks type stubs

from browser_use import Browser  # Browser automation library, providing browser instance management functionality

from apps.executor.executor_configuration import ExecutorConfiguration  # Executor configuration dataclass
from apps.executor.executor_error import ExecutorNotReadyError  # Executor not ready exception class
from environment.environment import get_config_int  # Integer config value getter
from environment.environment import get_config_list  # List config value getter
from environment.environment import get_config_value  # Generic config value getter
from environment.environment import get_application_config  # Application config getter (process singleton)

_LOGGER = logging.getLogger(__name__)


class PooledBrowserManager(ABC):
    """Browser pool manager abstract base class, defining browser instance borrow and return interfaces."""

    @abstractmethod
    async def borrow_browser(self, executor_config: ExecutorConfiguration) -> Browser:
        """Borrow browser instance from pool."""

        pass

    @abstractmethod
    async def return_browser(self, browser: Browser) -> None:
        """Return browser instance to pool."""

        pass


class DefaultPooledBrowserManager(PooledBrowserManager):
    """Default browser pool manager implementation, creating and destroying browser instances."""

    async def borrow_browser(self, executor_config: ExecutorConfiguration) -> Browser:
        """Borrow browser instance from pool, create new browser instance."""

        application_config = get_application_config()

        userdata_dir = os.path.join(executor_config.base_working_dir,
                get_config_value(application_config, 'llm_browser_agent.browser.dir.userdata')
        )

        try:
            os.makedirs(userdata_dir, exist_ok=True)
        except OSError as e:
            _LOGGER.error('Failed to create userdata directory %s: %s', userdata_dir, e)
            raise ExecutorNotReadyError(f'Failed to create userdata directory {userdata_dir}: {e}') from e

        download_dir = os.path.join(executor_config.base_working_dir,
                get_config_value(application_config, 'llm_browser_agent.browser.dir.download')
        )

        try:
            os.makedirs(download_dir, exist_ok=True)
        except OSError as e:
            _LOGGER.error('Failed to create download directory %s: %s', download_dir, e)
            raise ExecutorNotReadyError(f'Failed to create download directory {download_dir}: {e}') from e

        args = list(get_config_list(application_config, 'llm_browser_agent.browser.chrome.args'))

        w_size = get_config_int(application_config, 'llm_browser_agent.browser.window.w_size')
        h_size = get_config_int(application_config, 'llm_browser_agent.browser.window.h_size')
        args.append(f'--window-size={w_size},{h_size}')

        if not executor_config.browser_use_sandbox:
            args.extend(['--no-sandbox', '--disable-dev-shm-usage'])

        args.append(f'--download-default-directory={download_dir}')

        browser_kwargs = {
            'headless': executor_config.browser_headless,
            'disable_security': not executor_config.browser_enable_security,
            'enable_default_extensions': False,
            'args': args,
            'user_data_dir': userdata_dir
        }

        try:
            browser = Browser(**browser_kwargs)
        except Exception as e:
            _LOGGER.error('Failed to initialize browser: %s', e)
            raise ExecutorNotReadyError(f'Failed to initialize browser: {e}') from e

        return browser

    async def return_browser(self, browser: Any) -> None:
        """Return browser instance to pool, close browser to release resources."""

        try:
            await browser.close()
        except Exception as e:
            _LOGGER.error('Browser closed failure: %s', e)


# Global browser pool instance
_BROWSER_POOL = DefaultPooledBrowserManager()


async def borrow_browser_from_pool(config: ExecutorConfiguration) -> Browser:
    """Borrow browser from pool."""
    return await _BROWSER_POOL.borrow_browser(config)


async def return_browser_to_pool(browser: Browser) -> None:
    """Return browser to pool."""
    await _BROWSER_POOL.return_browser(browser)


# ==================== Browser session management ====================

@dataclass
class BrowserSession:
    """Browser session, chained tasks share browser instance."""

    session_id: str  # Session ID (reusing first task ID)
    browser: Browser  # Shared browser instance
    owner_customer_id: str  # Owner customer ID
    task_ids: list[str] = field(default_factory=list)  # Task ID list (in order)
    current_index: int = -1  # Current execution task index
    is_busy: bool = False  # Whether executing task
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # Concurrency lock

    def add_task(self, task_id: str) -> int:
        """Add task to session, return step index."""
        self.task_ids.append(task_id)
        return len(self.task_ids) - 1

    def is_last_task(self, task_id: str) -> bool:
        """Check if it is the last task."""
        if not self.task_ids:
            return True
        return task_id == self.task_ids[-1]

    def get_step_info(self, task_id: str) -> tuple[int, int] | None:
        """Get task step info (current_step, total_steps)."""
        try:
            idx = self.task_ids.index(task_id)
            return (idx + 1, len(self.task_ids))
        except ValueError:
            return None

    def get_next_task(self, current_task_id: str) -> str | None:
        """Get next task ID."""
        try:
            idx = self.task_ids.index(current_task_id)
            if idx + 1 < len(self.task_ids):
                return self.task_ids[idx + 1]
        except ValueError:
            pass
        return None

    def get_current_task(self) -> str | None:
        """Get currently executing task ID, return None if none."""
        if 0 <= self.current_index < len(self.task_ids):
            return self.task_ids[self.current_index]
        return None

    async def acquire(self) -> bool:
        """Acquire browser usage right."""
        async with self._lock:
            if not self.is_busy:
                self.is_busy = True
                self.current_index += 1
                return True
            return False

    async def release(self) -> None:
        """Release browser usage right."""
        async with self._lock:
            self.is_busy = False


class SessionManager:
    """Browser session manager, managing all active browser sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, BrowserSession] = {}  # session_id -> session
        self._task_to_session: dict[str, str] = {}  # task_id -> session_id

    def create_session(
        self,
        session_id: str,
        browser: Browser,
        owner_customer_id: str,
        task_ids: list[str]
    ) -> BrowserSession:
        """Create new session."""
        session = BrowserSession(
            session_id=session_id,
            browser=browser,
            owner_customer_id=owner_customer_id,
            task_ids=task_ids
        )

        self._sessions[session_id] = session
        for task_id in task_ids:
            self._task_to_session[task_id] = session_id

        _LOGGER.info(
            "Session created: %s, tasks: %d, owner: %s",
            session_id, len(task_ids), owner_customer_id
        )
        return session

    def get_session(self, session_id: str) -> BrowserSession | None:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def get_session_by_task(self, task_id: str) -> BrowserSession | None:
        """Get session by task ID."""
        session_id = self._task_to_session.get(task_id)
        if session_id:
            return self._sessions.get(session_id)
        return None

    def remove_task(self, task_id: str) -> tuple[BrowserSession | None, bool]:
        """
        Remove task.
        Returns: (session, is_last_task)
        """
        session_id = self._task_to_session.pop(task_id, None)
        if not session_id:
            return None, True

        session = self._sessions.get(session_id)
        if not session:
            return None, True

        is_last = session.is_last_task(task_id)

        if is_last:
            self._sessions.pop(session_id, None)
            _LOGGER.info("Session %s completed and removed", session_id)

        return session, is_last

    def cancel_session(self, session_id: str) -> list[str]:
        """
        Cancel entire session.
        Returns: List of all cancelled task IDs
        """
        session = self._sessions.pop(session_id, None)
        if not session:
            return []

        all_tasks = list(session.task_ids)

        for task_id in all_tasks:
            self._task_to_session.pop(task_id, None)

        _LOGGER.info("Session %s cancelled, tasks: %s", session_id, all_tasks)
        return all_tasks


# Global session manager
SESSION_MANAGER = SessionManager()

