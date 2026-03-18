"""Executor factory module supporting single-step and multi-step chain tasks."""

import asyncio  # Async IO module providing event loop and coroutine functionality
import json  # JSON serialization and deserialization module for data conversion
import logging  # Logging module providing application log output functionality
from dataclasses import dataclass  # Data class decorator for creating configuration data classes
from datetime import datetime  # Date time module for recording event timestamps
from uuid import uuid4  # UUID generation module for creating task unique identifiers

from browser_use import Agent  # Browser-use agent abstraction for orchestrating LLM-driven browser automation workflows
from browser_use import Browser  # Browser-use browser wrapper providing controlled navigation operations for tasks
from langchain_openai import ChatOpenAI  # LangChain OpenAI chat model client used as the executor LLM backend interface

from apps.executor.executor_browser import borrow_browser_from_pool  # Borrow browser instance from the shared pool
from apps.executor.executor_browser import BrowserSession  # Browser session type for chained execution steps
from apps.executor.executor_browser import return_browser_to_pool  # Return borrowed browser instance to pool
from apps.executor.executor_browser import SESSION_MANAGER  # Session manager coordinating browser pool leases
from apps.executor.executor_configuration import ExecutorConfiguration  # Executor configuration loaded from environment
from apps.executor.executor_event import ExecutorEventPayload  # Payload model for persisted executor events
from apps.executor.executor_event import ExecutorEventType  # Enum type for executor event lifecycle stages
from apps.executor.executor_event_delivery import ExecutorEventDelivery  # Delivery interface for pushing events
from apps.executor.executor_event_delivery import LocalMemoryExecutorEventDelivery  # In-memory delivery used for local
from apps.executor.executor_event_logger import attach_handler  # Attach logger handler for per-task capture
from apps.executor.executor_event_logger import detach_handler  # Detach logger handler to avoid leaks
from apps.executor.executor_event_playback import DEFAULT_MAX_EVENTS  # Default max buffered playback events count
from apps.executor.executor_event_playback import ExecutorEventPlayback  # Playback interface for reading task events
from apps.executor.executor_event_playback import LocalMemoryExecutorEventPlayback  # In-memory playback used for local
from apps.executor.executor_event_producer import ExecutorEventProducer  # Producer pushing events into delivery
from apps.executor.executor_workspace import ExecutorWorkspace  # Per-task workspace directory helper

_LOGGER = logging.getLogger(__name__)

_CONTEXT_POOL: dict[str, 'ExecutorContext'] = {}
_RUNNING_TASK: dict[str, asyncio.Task] = {}

SESSION_ACQUIRE_POLL_INTERVAL_SECONDS = 0.1  # Poll interval used when waiting to acquire chained session browser access


@dataclass
class ExecutorContext:
    """Executor context where chain tasks share browser but model/agent are independent per step."""
    model: ChatOpenAI
    agent: Agent
    playback: ExecutorEventPlayback
    delivery: ExecutorEventDelivery
    producer: ExecutorEventProducer
    browser: Browser
    workspace: ExecutorWorkspace
    logger_handlers: list[logging.Handler] | None = None
    # Chain call related fields
    session: BrowserSession | None = None
    is_chained: bool = False
    step_index: int = 0
    total_steps: int = 1


async def _event_release_handle(
    task_id: str, playback: ExecutorEventPlayback, producer: ExecutorEventProducer,
    event_type: ExecutorEventType, data: str,
) -> None:
    """Publish events to delivery system and save to playback storage."""
    payload = ExecutorEventPayload(
        task_id=task_id,
        event_type=event_type,
        event_data=data,
        event_time=datetime.now(),
    )
    await playback.save(payload)
    await producer.push(payload)


def _create_task_id() -> str:
    """Create task unique identifier."""
    return str(uuid4())


def _create_event_producer(delivery: ExecutorEventDelivery) -> ExecutorEventProducer:
    """Create event producer object."""
    return ExecutorEventProducer(delivery=delivery)


def _create_event_playback(max_events: int = DEFAULT_MAX_EVENTS) -> ExecutorEventPlayback:
    """Create local event playback storage."""
    return LocalMemoryExecutorEventPlayback(max_events=max_events)


def _create_event_delivery(delivery_id: str) -> ExecutorEventDelivery:
    """Create local memory event delivery."""
    return LocalMemoryExecutorEventDelivery(delivery_id=delivery_id)


async def _create_executor_workspace(
    task_id: str, config: ExecutorConfiguration, playback: ExecutorEventPlayback,
    producer: ExecutorEventProducer,
) -> ExecutorWorkspace:
    """Create task executor workspace."""
    workspace = ExecutorWorkspace(task_id=task_id, base_dir=config.base_working_dir)
    workspace.initialize()

    data = (
        f"Workspace initialized, task_id: {task_id}, "
        f"task_dir:{workspace.task_dir}, "
        f"logs_dir:{workspace.logs_dir}, "
        f"data_dir:{workspace.data_dir}, "
        f"user_dir:{workspace.user_dir}"
    )
    await _event_release_handle(
        task_id=task_id,
        playback=playback,
        producer=producer,
        event_type=ExecutorEventType.WORKSPACE_INITIALIZED,
        data=data,
    )
    return workspace


async def _create_model(
    task_id: str, config: ExecutorConfiguration, playback: ExecutorEventPlayback,
    producer: ExecutorEventProducer,
) -> ChatOpenAI:
    """Create large model instance."""
    model = ChatOpenAI(
        base_url=config.model_api_url,
        model=config.model_name,
        temperature=config.model_temperature,
        top_p=config.model_top_p,
        api_key=config.model_api_key,
        timeout=config.model_timeout,
    )

    data = (
        f"Model initialized, task_id: {task_id}, "
        f"name:{config.model_name}, "
        f"temperature:{config.model_temperature}, "
        f"top_p:{config.model_top_p}, "
        f"timeout:{config.model_timeout}"
    )
    await _event_release_handle(
        task_id=task_id,
        playback=playback,
        producer=producer,
        event_type=ExecutorEventType.MODEL_INITIALIZED,
        data=data,
    )
    return model


async def _create_agent(
    task_id: str, task_prompt: str, config: ExecutorConfiguration, model: ChatOpenAI,
    browser: Browser, playback: ExecutorEventPlayback, producer: ExecutorEventProducer,
) -> Agent:
    """Create agent instance."""
    agent = Agent(
        task=task_prompt,
        llm=model,
        browser=browser,
        max_actions_per_step=config.agent_max_actions_per_step,
        demo_mode=config.agent_demo_mode,
        calculate_cost=config.agent_calculate_cost,
        max_failures=config.agent_max_failures,
        use_thinking=config.agent_use_thinking,
        step_timeout=config.agent_step_timeout,
        use_vision=config.agent_use_vision,
        flash_mode=config.agent_fast_mode,
    )

    data = (
        f"Agent initialized, task_id: {task_id}, "
        f"prompt:{task_prompt[:50]}..."
    )
    await _event_release_handle(
        task_id=task_id,
        playback=playback,
        producer=producer,
        event_type=ExecutorEventType.AGENT_INITIALIZED,
        data=data,
    )
    return agent


async def _destroy_context(task_id: str, return_browser: bool) -> None:
    """
    Destroy context and release resources.

    Args:
        return_browser: True=return browser to pool, False=only release usage right
    """
    if task_id not in _CONTEXT_POOL:
        return

    context = _CONTEXT_POOL[task_id]

    # Clean up log handlers
    if context.logger_handlers:
        detach_handler(context.logger_handlers)
        context.logger_handlers = None

    # Handle browser
    if context.browser:
        if return_browser:
            # Last step: return browser to pool
            await return_browser_to_pool(context.browser)
            await _event_release_handle(
                task_id=task_id,
                playback=context.playback,
                producer=context.producer,
                event_type=ExecutorEventType.BROWSER_DESTROYED,
                data=f"Browser returned to pool, task_id:{task_id}"
            )
        else:
            # Intermediate step: release usage right, browser stays open
            if context.session:
                await context.session.release()
                _LOGGER.info("Task %s released browser for next step", task_id)

    # Clean up session
    if context.session:
        SESSION_MANAGER.remove_task(task_id)

    # Clean up other resources
    await context.delivery.destroy()
    del _CONTEXT_POOL[task_id]

    # Trigger next step (if not last step)
    if not return_browser and context.session:
        next_task_id = context.session.get_next_task(task_id)
        if next_task_id:
            await _trigger_next_step(next_task_id, context.session)

def _schedule_event_publish(
    loop: asyncio.AbstractEventLoop,
    task_id: str,
    context: ExecutorContext,
    event_type: ExecutorEventType,
    data: str,
) -> None:
    """Schedule event publish on loop without blocking logger emit call sites."""

    def _create_event_task() -> None:
        asyncio.create_task(
            _event_release_handle(
                task_id=task_id,
                playback=context.playback,
                producer=context.producer,
                event_type=event_type,
                data=data,
            )
        )

    loop.call_soon_threadsafe(_create_event_task)


async def _async_run_task(task_id: str, context: ExecutorContext) -> None:
    """Run agent task as background coroutine on current event loop."""

    loop = asyncio.get_running_loop()
    context.logger_handlers = attach_handler(
        task_id,
        lambda tid, logger_name, logger_level, logger_message: _schedule_event_publish(
            loop=loop,
            task_id=tid,
            context=context,
            event_type=ExecutorEventType.TASK_RUNNING,
            data=f"{logger_level}: [{logger_name}] {logger_message}",
        ),
    )

    step_info = ""
    if context.is_chained:
        step_info = f" [Step {context.step_index + 1}/{context.total_steps}]"

    await _event_release_handle(
        task_id=task_id,
        playback=context.playback,
        producer=context.producer,
        event_type=ExecutorEventType.TASK_RUNNING,
        data=f"Task running{step_info}, task_id:{task_id}",
    )

    running_task = asyncio.create_task(context.agent.run())
    _RUNNING_TASK[task_id] = running_task

    try:
        result = await running_task
        await _event_release_handle(
            task_id=task_id,
            playback=context.playback,
            producer=context.producer,
            event_type=ExecutorEventType.TASK_SUCCESS,
            data=f"Task success{step_info}, task_id:{task_id}",
        )

        await _event_release_handle(
            task_id=task_id,
            playback=context.playback,
            producer=context.producer,
            event_type=ExecutorEventType.TASK_RESULT,
            data=json.dumps(result, default=str, ensure_ascii=False) if result else '{}',
        )

        if context.is_chained and context.step_index == context.total_steps - 1:
            await _event_release_handle(
                task_id=task_id,
                playback=context.playback,
                producer=context.producer,
                event_type=ExecutorEventType.TASK_CHAIN_COMPLETED,
                data=f"Chain completed, session_id:{context.session.session_id if context.session else 'none'}",
            )

    except asyncio.CancelledError:
        await _event_release_handle(
            task_id=task_id,
            playback=context.playback,
            producer=context.producer,
            event_type=ExecutorEventType.TASK_CANCELLED,
            data=f"Task cancelled{step_info}, task_id:{task_id}",
        )
        raise
    except Exception as error:
        await _event_release_handle(
            task_id=task_id,
            playback=context.playback,
            producer=context.producer,
            event_type=ExecutorEventType.TASK_FAILURE,
            data=f"{step_info} {str(error)}",
        )
    finally:
        _RUNNING_TASK.pop(task_id, None)

        is_last = True
        if context.session:
            is_last = context.session.is_last_task(task_id)

        await _destroy_context(task_id, return_browser=is_last)


async def _trigger_next_step(next_task_id: str, session: BrowserSession) -> None:
    """Trigger next step execution for chain task."""
    if next_task_id not in _CONTEXT_POOL:
        _LOGGER.error("Next task %s not found in context pool", next_task_id)
        return

    context = _CONTEXT_POOL[next_task_id]

    # Wait to acquire browser usage right
    while not await session.acquire():
        await asyncio.sleep(SESSION_ACQUIRE_POLL_INTERVAL_SECONDS)

    _LOGGER.info("Triggering next step: %s", next_task_id)

    # Send step switch event
    step_info = session.get_step_info(next_task_id)
    if step_info:
        await _event_release_handle(
            task_id=next_task_id,
            playback=context.playback,
            producer=context.producer,
            event_type=ExecutorEventType.TASK_CHAIN_STEP,
            data=f"Step {step_info[0]}/{step_info[1]} started"
        )

    asyncio.create_task(_async_run_task(next_task_id, context))


async def _create_task_context(
    task_id: str, prompt: str, config: ExecutorConfiguration, is_chained: bool = False,
    step_index: int = 0, total_steps: int = 1, session: BrowserSession | None = None,
) -> ExecutorContext:
    """Create task context."""
    # Event components
    delivery = _create_event_delivery(task_id)
    producer = _create_event_producer(delivery)
    playback = _create_event_playback()

    # Workspace
    workspace = await _create_executor_workspace(task_id, config, playback, producer)

    # Get browser
    if session and is_chained:
        # Chain task: reuse session's browser
        browser = session.browser
        _LOGGER.info("Task %s using shared browser from session %s", task_id, session.session_id)
    else:
        # Single task: borrow from pool
        browser = await borrow_browser_from_pool(config)
        await _event_release_handle(
            task_id=task_id, playback=playback, producer=producer,
            event_type=ExecutorEventType.BROWSER_INITIALIZED,
            data=f"Browser borrowed from pool, task_id:{task_id}"
        )

    # Create model and agent (independent per step)
    model = await _create_model(task_id, config, playback, producer)
    agent = await _create_agent(task_id, prompt, config, model, browser, playback, producer)

    return ExecutorContext(
        model=model,
        agent=agent,
        playback=playback,
        delivery=delivery,
        producer=producer,
        browser=browser,
        workspace=workspace,
        session=session,
        is_chained=is_chained,
        step_index=step_index,
        total_steps=total_steps
    )


async def task_submit_handle(request: ExecutorConfiguration, customer_id: str) -> dict:
    """
    Submit task, supporting single-step and multi-step chain calls.

    Returns:
        {
            "task_id": str,
            "session_id": str | None,
            "sub_tasks": list[str],
            "total_steps": int
        }
    """
    prompts = request.task_prompts
    total_steps = len(prompts)

    if total_steps == 1:
        # Single step task
        task_id = _create_task_id()
        context = await _create_task_context(
            task_id=task_id,
            prompt=prompts[0],
            config=request
        )
        _CONTEXT_POOL[task_id] = context

        # Send startup event
        await _event_release_handle(
            task_id=task_id,
            playback=context.playback,
            producer=context.producer,
            event_type=ExecutorEventType.TASK_STARTUP,
            data=f"Task startup, task_id:{task_id}",
        )

        # Start execution
        asyncio.create_task(_async_run_task(task_id, context))

        return {
            "task_id": task_id,
            "session_id": None,
            "sub_tasks": [task_id],
            "total_steps": 1
        }

    # Multi-step chain task
    sub_tasks = []
    session_id = None
    session = None

    # Create all task_id in batch
    for _ in range(total_steps):
        sub_tasks.append(_create_task_id())

    session_id = sub_tasks[0]  # Reuse first task id as session id

    # Borrow browser (first step)
    browser = await borrow_browser_from_pool(request)

    # Create contexts for all steps (first step starts immediately, remaining steps wait for trigger)
    for i, (task_id, prompt) in enumerate(zip(sub_tasks, prompts)):
        is_first = (i == 0)

        if is_first:
            # First step: create session
            context = await _create_task_context(
                task_id=task_id,
                prompt=prompt,
                config=request,
                is_chained=True,
                step_index=i,
                total_steps=total_steps
            )
            context.browser = browser  # Ensure using borrowed browser

            # Create session
            session = SESSION_MANAGER.create_session(
                session_id=session_id,
                browser=browser,
                owner_customer_id=customer_id,
                task_ids=sub_tasks
            )
            context.session = session

            # Acquire usage right
            await session.acquire()

            _CONTEXT_POOL[task_id] = context

            # Send chain start event
            await _event_release_handle(
                task_id=task_id, playback=context.playback, producer=context.producer,
                event_type=ExecutorEventType.TASK_CHAIN_STARTED,
                data=f"Chain started, session_id:{session_id}, total_steps:{total_steps}"
            )

            # Send task startup event
            await _event_release_handle(
                task_id=task_id, playback=context.playback, producer=context.producer,
                event_type=ExecutorEventType.TASK_STARTUP,
                data=f"Task startup [Step 1/{total_steps}], task_id:{task_id}"
            )

            # Start execution
            asyncio.create_task(_async_run_task(task_id, context))

        else:
            # Remaining steps: pre-create context and wait for trigger
            context = await _create_task_context(
                task_id=task_id,
                prompt=prompt,
                config=request,
                is_chained=True,
                step_index=i,
                total_steps=total_steps,
                session=session
            )
            _CONTEXT_POOL[task_id] = context

    return {
        "task_id": sub_tasks[0],
        "session_id": session_id,
        "sub_tasks": sub_tasks,
        "total_steps": total_steps
    }


def task_cancel_handle(task_id: str) -> dict:
    """
    Cancel task, supporting single task and chained tasks.

    Returns:
        {
            "cancelled": bool,
            "cancelled_tasks": list[str],
            "session_id": str | None
        }
    """
    # Check whether it is a chained task
    session = SESSION_MANAGER.get_session_by_task(task_id)

    if session:
        # Chained task cancel
        return _cancel_chained_task(task_id, session)

    # Single task cancel
    return _cancel_single_task(task_id)


def _cancel_single_task(task_id: str) -> dict:
    """Cancel single task."""
    if task_id not in _RUNNING_TASK:
        return {"cancelled": False, "cancelled_tasks": [], "session_id": None}

    task = _RUNNING_TASK[task_id]

    if task.done():
        return {"cancelled": False, "cancelled_tasks": [], "session_id": None}

    success = task.cancel()

    return {
        "cancelled": success,
        "cancelled_tasks": [task_id] if success else [],
        "session_id": None
    }


def _cancel_chained_task(task_id: str, session: BrowserSession) -> dict:
    """Cancel chained task."""
    cancelled_tasks = []
    session_id = session.session_id

    # 1. Cancel current running task
    current_task_id = session.get_current_task()
    if current_task_id and current_task_id in _RUNNING_TASK:
        task = _RUNNING_TASK[current_task_id]
        if not task.done():
            if task.cancel():
                cancelled_tasks.append(current_task_id)

    # 2. Cancel entire session
    all_tasks = SESSION_MANAGER.cancel_session(session_id)

    # 3. Force clean up all contexts (return browser)
    for tid in all_tasks:
        if tid in _CONTEXT_POOL:
            context = _CONTEXT_POOL[tid]
            # Force returning browser
            asyncio.create_task(_force_cleanup_context(tid, context))

    return {
        "cancelled": True,
        "cancelled_tasks": list(set(all_tasks + cancelled_tasks)),
        "session_id": session_id
    }


async def _force_cleanup_context(task_id: str, context: ExecutorContext) -> None:
    """Force clean up context."""
    # Clean up logs
    if context.logger_handlers:
        detach_handler(context.logger_handlers)

    # Force returning browser
    if context.browser:
        await return_browser_to_pool(context.browser)

    # Clean up other resources
    await context.delivery.destroy()

    if task_id in _CONTEXT_POOL:
        del _CONTEXT_POOL[task_id]


def task_status_handle(task_id: str) -> str:
    """Get task status: running / pending / completed / cancelled / failed / not_found."""

    if task_id in _RUNNING_TASK:
        task = _RUNNING_TASK[task_id]
        if task.done():
            if task.cancelled():
                return 'cancelled'
            exc = task.exception()
            if exc is not None:
                return 'failed'
            return 'completed'
        return 'running'

    session = SESSION_MANAGER.get_session_by_task(task_id)
    if session and task_id in _CONTEXT_POOL:
        return 'pending'
    if session:
        return 'cancelled'
    return 'not_found'


def get_running_task_ids() -> list[str]:
    """Get a snapshot list of running task ids for shutdown orchestration and observability.

    Returns:
        list[str]: Task id list for tasks that are currently running inside the process event loop.
    """

    return list(_RUNNING_TASK.keys())


def cancel_all_running_tasks() -> list[str]:
    """Cancel all running tasks best-effort, used during graceful shutdown timeout.

    Returns:
        list[str]: Task id list that were requested to cancel.
    """

    task_ids = list(_RUNNING_TASK.keys())
    for task_id in task_ids:
        task = _RUNNING_TASK.get(task_id)
        if task is not None and not task.done():
            task.cancel()
    return task_ids

