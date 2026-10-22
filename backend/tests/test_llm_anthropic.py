"""Tests for llm.anthropic_client: AnthropicClient (streaming implementation)."""

import logging
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from anthropic.types import (
    ContentBlock,
    Message,
    RefusalStopDetails,
    StopReason,
    TextBlock,
    ThinkingBlock,
    Usage,
)

from adjents.llm.anthropic_client import AnthropicClient
from adjents.llm.errors import LLMRefusalError, LLMResponseError, LLMTruncatedError

_MESSAGES = [{"role": "user", "content": "Hello."}]
_MODEL = "claude-opus-5-5"
_REPLY = "I am the Generator Agent."


def _text(text: str) -> TextBlock:
    return TextBlock(type="text", text=text)


def _thinking(summary: str = "") -> ThinkingBlock:
    return ThinkingBlock(type="thinking", thinking=summary, signature="sig")


def _message(
    *blocks: ContentBlock,
    stop_reason: StopReason = "end_turn",
    stop_details: RefusalStopDetails | None = None,
    output_tokens: int = 42,
) -> Message:
    return Message(
        id="msg_test",
        type="message",
        role="assistant",
        model=_MODEL,
        content=list(blocks),
        stop_reason=stop_reason,
        stop_details=stop_details,
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=output_tokens),
    )


class _FakeStream:
    """Minimal async context manager that mimics anthropic.AsyncMessageStream."""

    def __init__(self, message: Message) -> None:
        self._message = message

    async def __aenter__(self) -> "_FakeStream":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def get_final_message(self) -> Message:
        return self._message


@pytest.fixture
def mock_anthropic() -> Generator[MagicMock]:
    with patch("adjents.llm.anthropic_client.anthropic.AsyncAnthropic") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.messages.stream.return_value = _FakeStream(
            _message(_thinking(), _text(_REPLY))
        )
        mock_cls.return_value = mock_instance
        yield mock_instance


def _respond_with(mock_anthropic: MagicMock, message: Message) -> None:
    mock_anthropic.messages.stream.return_value = _FakeStream(message)


def _sent_kwargs(mock_anthropic: MagicMock) -> dict[str, object]:
    kwargs: dict[str, object] = mock_anthropic.messages.stream.call_args.kwargs
    return kwargs


# --- Model ---


def test_model_property_exposes_configured_model(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    assert client.model == _MODEL


# --- Request parameters ---


async def test_complete_passes_model(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, effort="medium")
    assert _sent_kwargs(mock_anthropic)["model"] == _MODEL


async def test_complete_passes_messages(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, effort="medium")
    assert _sent_kwargs(mock_anthropic)["messages"] == _MESSAGES


async def test_complete_passes_max_tokens(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, effort="medium", max_tokens=1024)
    assert _sent_kwargs(mock_anthropic)["max_tokens"] == 1024


async def test_complete_default_max_tokens_leaves_room_for_thinking(
    mock_anthropic: MagicMock,
) -> None:
    """Thinking counts toward max_tokens on Claude 5.5 models (ADR 0012)."""
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, effort="medium")
    assert _sent_kwargs(mock_anthropic)["max_tokens"] == 16000


async def test_complete_passes_system_prompt(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(
        _MESSAGES, effort="medium", system="You are a helpful assistant."
    )
    assert _sent_kwargs(mock_anthropic)["system"] == "You are a helpful assistant."


async def test_complete_without_system_omits_key(mock_anthropic: MagicMock) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, effort="medium")
    assert "system" not in _sent_kwargs(mock_anthropic)


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
async def test_complete_passes_effort_in_output_config(
    mock_anthropic: MagicMock, effort: str
) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, effort=effort)  # type: ignore[arg-type]
    assert _sent_kwargs(mock_anthropic)["output_config"] == {"effort": effort}


async def test_complete_sends_adaptive_thinking_with_summarized_display(
    mock_anthropic: MagicMock,
) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, effort="medium")
    assert _sent_kwargs(mock_anthropic)["thinking"] == {
        "type": "adaptive",
        "display": "summarized",
    }


async def test_complete_sends_no_sampling_prefill_or_tool_parameters(
    mock_anthropic: MagicMock,
) -> None:
    """temperature / top_p / top_k / tool_choice return a 400 on Claude 5.5 models."""
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, effort="medium")
    sent = _sent_kwargs(mock_anthropic)
    for forbidden in ("temperature", "top_p", "top_k", "tool_choice", "tools"):
        assert forbidden not in sent


# --- Successful responses ---


async def test_complete_returns_text_and_skips_thinking_blocks(
    mock_anthropic: MagicMock,
) -> None:
    _respond_with(mock_anthropic, _message(_thinking("I should greet."), _text(_REPLY)))
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    assert await client.complete(_MESSAGES, effort="medium") == _REPLY


async def test_complete_concatenates_text_blocks(mock_anthropic: MagicMock) -> None:
    _respond_with(mock_anthropic, _message(_text('{"a": '), _text("1}")))
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    assert await client.complete(_MESSAGES, effort="medium") == '{"a": 1}'


# --- Refusals ---


async def test_complete_raises_refusal_before_any_output(
    mock_anthropic: MagicMock,
) -> None:
    details = RefusalStopDetails(type="refusal", category="cyber", explanation="No.")
    _respond_with(mock_anthropic, _message(stop_reason="refusal", stop_details=details))
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(LLMRefusalError) as exc_info:
        await client.complete(_MESSAGES, effort="medium")
    assert exc_info.value.category == "cyber"
    assert exc_info.value.explanation == "No."
    assert exc_info.value.model == _MODEL


async def test_complete_raises_refusal_without_stop_details(
    mock_anthropic: MagicMock,
) -> None:
    _respond_with(mock_anthropic, _message(stop_reason="refusal"))
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(LLMRefusalError) as exc_info:
        await client.complete(_MESSAGES, effort="medium")
    assert exc_info.value.category is None
    assert exc_info.value.explanation is None


async def test_complete_discards_partial_text_on_mid_stream_refusal(
    mock_anthropic: MagicMock,
) -> None:
    """A partial answer must never be returned as if it were complete."""
    _respond_with(
        mock_anthropic,
        _message(_text('{"message": "Sure, here'), stop_reason="refusal"),
    )
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(LLMRefusalError):
        await client.complete(_MESSAGES, effort="medium")


# --- Truncation ---


async def test_complete_raises_truncation_on_max_tokens(
    mock_anthropic: MagicMock,
) -> None:
    _respond_with(
        mock_anthropic,
        _message(_text('{"agents": ['), stop_reason="max_tokens", output_tokens=1024),
    )
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(LLMTruncatedError) as exc_info:
        await client.complete(_MESSAGES, effort="medium", max_tokens=1024)
    assert exc_info.value.stop_reason == "max_tokens"
    assert exc_info.value.max_tokens == 1024
    assert exc_info.value.output_tokens == 1024


async def test_complete_raises_truncation_when_cut_during_thinking(
    mock_anthropic: MagicMock,
) -> None:
    """No text block at all: the budget was spent on thinking."""
    _respond_with(mock_anthropic, _message(_thinking(), stop_reason="max_tokens"))
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(LLMTruncatedError):
        await client.complete(_MESSAGES, effort="medium")


async def test_complete_raises_truncation_on_context_window_exceeded(
    mock_anthropic: MagicMock,
) -> None:
    _respond_with(
        mock_anthropic,
        _message(_text("partial"), stop_reason="model_context_window_exceeded"),
    )
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(LLMTruncatedError) as exc_info:
        await client.complete(_MESSAGES, effort="medium")
    assert exc_info.value.stop_reason == "model_context_window_exceeded"


# --- Other unusable responses ---


async def test_complete_raises_on_empty_text(mock_anthropic: MagicMock) -> None:
    _respond_with(mock_anthropic, _message(_thinking()))
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(LLMResponseError, match="no text"):
        await client.complete(_MESSAGES, effort="medium")


async def test_complete_raises_on_unexpected_stop_reason(
    mock_anthropic: MagicMock,
) -> None:
    """We send no tools and no stop sequences: anything but end_turn is unusable."""
    _respond_with(mock_anthropic, _message(_text("..."), stop_reason="tool_use"))
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(LLMResponseError) as exc_info:
        await client.complete(_MESSAGES, effort="medium")
    assert exc_info.value.stop_reason == "tool_use"


# --- Logging ---


async def test_complete_logs_usage_at_debug(
    mock_anthropic: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with caplog.at_level(logging.DEBUG, logger="adjents.llm.anthropic_client"):
        await client.complete(_MESSAGES, effort="medium")
    assert "stop_reason=end_turn" in caplog.text
    assert "output_tokens=42" in caplog.text


async def test_complete_logs_refusal_at_warning_without_content(
    mock_anthropic: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    details = RefusalStopDetails(type="refusal", category="bio", explanation=None)
    _respond_with(
        mock_anthropic,
        _message(_text("secret partial"), stop_reason="refusal", stop_details=details),
    )
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with caplog.at_level(logging.WARNING, logger="adjents.llm.anthropic_client"):
        with pytest.raises(LLMRefusalError):
            await client.complete(_MESSAGES, effort="medium")
    assert "bio" in caplog.text
    assert "secret partial" not in caplog.text


async def test_complete_logs_thinking_summary_on_dedicated_logger(
    mock_anthropic: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    _respond_with(mock_anthropic, _message(_thinking("Plan the org."), _text(_REPLY)))
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with caplog.at_level(logging.DEBUG, logger="adjents.llm.thinking"):
        await client.complete(_MESSAGES, effort="medium")
    records = [r for r in caplog.records if r.name == "adjents.llm.thinking"]
    assert len(records) == 1
    assert "Plan the org." in records[0].getMessage()


async def test_complete_thinking_logger_is_silent_by_default(
    mock_anthropic: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Summaries contain user business data: off unless explicitly enabled."""
    _respond_with(mock_anthropic, _message(_thinking("Plan the org."), _text(_REPLY)))
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with caplog.at_level(logging.INFO):
        await client.complete(_MESSAGES, effort="medium")
    assert "Plan the org." not in caplog.text
