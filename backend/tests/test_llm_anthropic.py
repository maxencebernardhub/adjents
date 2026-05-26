"""Tests for llm.anthropic_client: AnthropicClient (streaming implementation)."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from adjents.llm.anthropic_client import AnthropicClient

_MESSAGES = [{"role": "user", "content": "Hello."}]
_MODEL = "claude-opus-4-7"
_REPLY = "I am the Generator Agent."


class _FakeStream:
    """Minimal async context manager that mimics anthropic.AsyncMessageStream."""

    def __init__(self, text: str) -> None:
        self._text = text

    async def __aenter__(self) -> "_FakeStream":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def get_final_text(self) -> str:
        return self._text


@pytest.fixture
def mock_anthropic() -> Generator[MagicMock]:
    with patch("adjents.llm.anthropic_client.anthropic.AsyncAnthropic") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.messages.stream.return_value = _FakeStream(_REPLY)
        mock_cls.return_value = mock_instance
        yield mock_instance


async def test_complete_returns_text(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    result = await client.complete(_MESSAGES)
    assert result == _REPLY


async def test_complete_passes_model(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES)
    kwargs = mock_anthropic.messages.stream.call_args.kwargs
    assert kwargs["model"] == _MODEL


async def test_complete_passes_messages(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES)
    kwargs = mock_anthropic.messages.stream.call_args.kwargs
    assert kwargs["messages"] == _MESSAGES


async def test_complete_passes_max_tokens(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, max_tokens=1024)
    kwargs = mock_anthropic.messages.stream.call_args.kwargs
    assert kwargs["max_tokens"] == 1024


async def test_complete_passes_system_prompt(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, system="You are a helpful assistant.")
    kwargs = mock_anthropic.messages.stream.call_args.kwargs
    assert kwargs["system"] == "You are a helpful assistant."


async def test_complete_without_system_omits_key(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES)
    kwargs = mock_anthropic.messages.stream.call_args.kwargs
    assert "system" not in kwargs


async def test_complete_raises_on_empty_text(mock_anthropic: MagicMock) -> None:
    """ValueError raised when get_final_text() returns an empty string."""
    mock_anthropic.messages.stream.return_value = _FakeStream("")
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(ValueError, match="no text"):
        await client.complete(_MESSAGES)
