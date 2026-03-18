"""Instruction parsing module: transform natural language into engine-agnostic execution plans and structured steps."""

import logging  # Logging module, used to record instruction parsing flow and unexpected failures
import os  # Operating system utilities, used to locate assets directory that contains Instruct configuration
import json  # JSON utilities, used to convert language model output into structured action lists

from apps.configuration.configuration import get_default_config  # Default configuration provider for model settings
from langchain_openai import ChatOpenAI  # Compatible large language model client used to generate planning responses
from pydantic import SecretStr  # Secret string type hint, used for safely passing model api keys
from utils.load_toml_util import load_toml_file  # TOML loader, used to read Instruct system prompt configuration
from utils.load_toml_util import require_toml_value  # Required value accessor retrieving mandatory configuration keys

from apps.instruct.actions import InstructAction  # Instruction action data model describing validated execution steps
from apps.instruct.actions import InstructActionType  # Instruction action type enum constraining allowed step kinds

_LOGGER = logging.getLogger(__name__)

_LLM_SYSTEM_PROMPT = str(require_toml_value(load_toml_file(os.path.join(os.path.dirname(__file__),
    'assets', 'instruct.toml')), 'system_prompt') or '').strip()

_chat_open_ai: ChatOpenAI | None = None


class InstructParseError(Exception):
    """Instruction parsing failure: raised for empty input, empty model output, invalid plans or invocation failures."""

    pass


def _get_chat_llm() -> ChatOpenAI:
    """Create or return cached ChatOpenAI instance based on current default configuration for process wide reuse."""
    global _chat_open_ai

    if _chat_open_ai is None:
        model = get_default_config().model
        _chat_open_ai = ChatOpenAI(model=model.name, base_url=model.api_url, api_key=SecretStr(model.api_key),
            timeout=model.timeout, temperature=min(0.3, model.temperature), top_p=model.top_p)
    return _chat_open_ai


class InstructParse:
    """Instruction parser: accepts natural language input and produces textual plans or structured execution steps."""

    @staticmethod
    async def parse(input: str) -> str:
        """Generate a textual execution plan for given instruction string or raise InstructParseError on failures."""
        if not (input or '').strip():
            raise InstructParseError('empty instruction')
        try:
            content = getattr(
                await _get_chat_llm().ainvoke([
                    {'role': 'system', 'content': _LLM_SYSTEM_PROMPT},
                    {'role': 'user', 'content': (input or '').strip()},
                ]),
                'content',
                '',
            ) or ''
            if not isinstance(content, str) or not content.strip():
                _LOGGER.warning('LLM returned empty content for instruction: %s', (input or '')[:50])
                raise InstructParseError('llm returned empty content')
            return content.strip()
        except InstructParseError:
            raise
        except Exception as error:
            _LOGGER.error('LLM failed for instruction %s: %s', (input or '')[:50], error)
            raise InstructParseError(f'llm invoke failed: {error}') from error

    @staticmethod
    async def parse_to_actions(input: str) -> list[InstructAction]:
        """Generate validated structured instruction actions from natural language or raise InstructParseError."""
        raw_plan = await InstructParse.parse(input)

        try:
            data = json.loads(raw_plan)
        except json.JSONDecodeError as error:
            _LOGGER.error('Failed to decode instruction plan JSON: %s', error)
            raise InstructParseError('invalid instruction plan json') from error

        if not isinstance(data, list):
            _LOGGER.error('Instruction plan JSON is not a list: %s', type(data))
            raise InstructParseError('instruction plan should be a list')

        actions: list[InstructAction] = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                _LOGGER.warning('Skip non-dict instruction step at index %s: %s', index, type(item))
                continue
            try:
                actions.append(InstructAction.model_validate(item))
            except Exception as error:
                _LOGGER.error('Invalid instruction step at index %s: %s', index, error)
                raise InstructParseError('invalid instruction step in plan') from error

        if not actions:
            _LOGGER.error('Instruction plan produced empty actions after validation')
            raise InstructParseError('instruction plan produced no valid actions')

        return actions

