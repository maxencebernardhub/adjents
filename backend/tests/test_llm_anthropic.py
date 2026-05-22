"""Tests for llm.anthropic_client: AnthropicClient."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adjents.llm.anthropic_client import AnthropicClient

_MESSAGES = [{"role": "user", "content": "Hello."}]
_MODEL = "claude-opus-4-7"


def _make_text_response(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


@pytest.fixture
def mock_anthropic() -> Generator[MagicMock]:
    with patch("adjents.llm.anthropic_client.anthropic.AsyncAnthropic") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.messages.create = AsyncMock(
            return_value=_make_text_response("I am the Generator Agent.")
        )
        mock_cls.return_value = mock_instance
        yield mock_instance


async def test_complete_returns_text(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    result = await client.complete(_MESSAGES)
    assert result == "I am the Generator Agent."


async def test_complete_passes_model(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES)
    kwargs = mock_anthropic.messages.create.call_args.kwargs
    assert kwargs["model"] == _MODEL


async def test_complete_passes_messages(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES)
    kwargs = mock_anthropic.messages.create.call_args.kwargs
    assert kwargs["messages"] == _MESSAGES


async def test_complete_passes_max_tokens(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, max_tokens=1024)
    kwargs = mock_anthropic.messages.create.call_args.kwargs
    assert kwargs["max_tokens"] == 1024


async def test_complete_passes_system_prompt(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, system="You are a helpful assistant.")
    kwargs = mock_anthropic.messages.create.call_args.kwargs
    assert kwargs["system"] == "You are a helpful assistant."


async def test_complete_without_system_omits_key(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES)
    kwargs = mock_anthropic.messages.create.call_args.kwargs
    assert "system" not in kwargs


async def test_complete_raises_on_non_text_block(mock_anthropic: MagicMock) -> None:
    block = MagicMock()
    block.type = "tool_use"
    response = MagicMock()
    response.content = [block]
    mock_anthropic.messages.create = AsyncMock(return_value=response)

    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(ValueError, match="Unexpected content block type"):
        await client.complete(_MESSAGES)
