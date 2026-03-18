"""Unit tests for the instruct parsing module, covering InstructParse and InstructParseError behaviors."""

from __future__ import annotations  # Enable postponed evaluation of annotations to support forward reference typing

import asyncio  # Asynchronous helpers used to run async parse within synchronous test cases
import os  # Operating system helpers used to read environment variables for optional integration tests
from typing import Any  # Generic type hint used by mocked objects and dynamic configurations

import pytest  # Testing framework providing fixtures, monkeypatching utilities and assertions

from apps.instruct.instruct import InstructParse  # Instruction parser converting text into plans or structured steps
from apps.instruct.instruct import InstructParseError  # Custom exception class raised when parsing instructions fails
from apps.instruct.actions import InstructAction  # Instruction action model used to validate parsed structured results
from apps.instruct.actions import InstructActionType  # Instruction action type enumeration used in type assertions
from apps.configuration.configuration import DefaultModelConfig  # Model config dataclass used for deterministic mocks


async def _run_parse(parser: InstructParse, instruction: str) -> str:
    """Execute InstructParse.parse inside the test suite and return the resulting textual plan string."""
    return await parser.parse(instruction)


def test_parse_empty_instruction_raises() -> None:
    """Ensure that an empty or whitespace only instruction string causes InstructParseError to be raised."""
    parser = InstructParse()
    with pytest.raises(InstructParseError):
        asyncio.run(_run_parse(parser, ''))
    with pytest.raises(InstructParseError):
        asyncio.run(_run_parse(parser, '   \n\t '))


def test_parse_llm_success_returns_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure that when the language model returns a textual plan, parse returns the same string content."""

    monkeypatch.setattr('apps.instruct.instruct._chat_open_ai', None)
    fake_prompt = '1、打开浏览器，在地址栏输入 https://www.taobao.com。\n2、在搜索框输入关键词。'

    class FakeMessage:
        content = fake_prompt

    class FakeChatOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def ainvoke(self, messages: Any) -> Any:
            return FakeMessage()

    monkeypatch.setattr(
        'apps.instruct.instruct.get_default_config',
        lambda: type('Config', (), {'model': DefaultModelConfig(
            name='test-model',
            temperature=0.1,
            top_p=0.9,
            api_url='http://fake',
            api_key='fake-key',
            timeout=60,
        )})(),
    )
    monkeypatch.setattr('apps.instruct.instruct.ChatOpenAI', FakeChatOpenAI)

    parser = InstructParse()
    result = asyncio.run(_run_parse(parser, '帮我到淘宝搜 4K 显示器'))

    assert result == fake_prompt


def test_parse_to_actions_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure that when the model returns a valid JSON plan, parse_to_actions yields a structured action list."""
    monkeypatch.setattr('apps.instruct.instruct._chat_open_ai', None)
    fake_plan = """
    [
      {
        "index": 1,
        "type": "navigate",
        "url": "https://www.taobao.com",
        "description": "打开电商网站首页"
      },
      {
        "index": 2,
        "type": "type",
        "selector": "input[name='q']",
        "text": "4K 显示器",
        "description": "在搜索框输入关键词"
      },
      {
        "index": 3,
        "type": "press",
        "key": "Enter",
        "description": "按下回车键发起搜索"
      }
    ]
    """

    class FakeMessage:
        content = fake_plan

    class FakeChatOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def ainvoke(self, messages: Any) -> Any:
            return FakeMessage()

    monkeypatch.setattr(
        'apps.instruct.instruct.get_default_config',
        lambda: type('Config', (), {'model': DefaultModelConfig(
            name='test-model',
            temperature=0.1,
            top_p=0.9,
            api_url='http://fake',
            api_key='fake-key',
            timeout=60,
        )})(),
    )
    monkeypatch.setattr('apps.instruct.instruct.ChatOpenAI', FakeChatOpenAI)

    parser = InstructParse()
    actions = asyncio.run(parser.parse_to_actions('帮我到淘宝搜 4K 显示器'))

    assert isinstance(actions, list)
    assert len(actions) == 3
    assert isinstance(actions[0], InstructAction)
    assert actions[0].type == InstructActionType.NAVIGATE
    assert actions[1].type == InstructActionType.TYPE
    assert actions[2].type == InstructActionType.PRESS


def test_parse_llm_empty_content_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure that when the language model returns empty content, parse raises InstructParseError."""
    monkeypatch.setattr('apps.instruct.instruct._chat_open_ai', None)

    class FakeMessage:
        content = ''

    class FakeChatOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def ainvoke(self, messages: Any) -> Any:
            return FakeMessage()

    monkeypatch.setattr(
        'apps.instruct.instruct.get_default_config',
        lambda: type('Config', (), {'model': DefaultModelConfig(
            name='test-model',
            temperature=0.1,
            top_p=0.9,
            api_url='http://fake',
            api_key='fake-key',
            timeout=60,
        )})(),
    )
    monkeypatch.setattr('apps.instruct.instruct.ChatOpenAI', FakeChatOpenAI)

    parser = InstructParse()
    with pytest.raises(InstructParseError):
        asyncio.run(_run_parse(parser, 'some instruction'))


def test_parse_llm_exception_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure that exceptions raised during model invocation are converted into InstructParseError."""
    monkeypatch.setattr('apps.instruct.instruct._chat_open_ai', None)

    class FakeChatOpenAI:
        async def ainvoke(self, messages: Any) -> Any:
            raise RuntimeError('network error')

    monkeypatch.setattr(
        'apps.instruct.instruct.get_default_config',
        lambda: type('Config', (), {'model': DefaultModelConfig(
            name='m',
            temperature=0.1,
            top_p=0.9,
            api_url='http://x',
            api_key='k',
            timeout=10,
        )})(),
    )
    monkeypatch.setattr('apps.instruct.instruct.ChatOpenAI', FakeChatOpenAI)

    parser = InstructParse()
    with pytest.raises(InstructParseError):
        asyncio.run(_run_parse(parser, 'vague instruction'))


def test_parse_llm_real_call_smoke() -> None:
    """Optionally verify parse can call a real language model once, skipped by default to avoid external coupling."""
    if os.getenv('RUN_LLM_INTEGRATION_TEST') != '1':
        pytest.skip('Set RUN_LLM_INTEGRATION_TEST=1 to enable real LLM integration test.')

    result = asyncio.run(InstructParse().parse('请打开淘宝搜索 4K 显示器'))

    assert isinstance(result, str)
    assert len(result) > 0

