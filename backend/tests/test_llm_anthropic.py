"""Tests for llm.anthropic_client: AnthropicClient (streaming implementation).

Two levels: above the SDK (mocked SDK client: parameters, stop reasons, logs) and
at the transport level (real SDK over a mocked HTTP transport: JSON body and
headers actually sent, stream parsing, SDK errors).
"""

import json
import logging
from collections.abc import Generator
from typing import get_args
from unittest.mock import MagicMock, patch

import anthropic
import httpx2
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
from adjents.llm.types import Effort

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


@pytest.mark.parametrize("effort", get_args(Effort))
async def test_complete_passes_effort_in_output_config(
    mock_anthropic: MagicMock, effort: Effort
) -> None:
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(_MESSAGES, effort=effort)
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


async def test_complete_sends_no_sampling_or_tool_parameters(
    mock_anthropic: MagicMock,
) -> None:
    """Sampling parameters and a forced tool_choice return a 400 on Claude 5.5."""
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


# --- Transport level: real SDK, mocked HTTP ---


def _sse(*events: dict[str, object]) -> bytes:
    """Encode events as the Server-Sent Events body of a streamed Messages call."""
    return b"".join(
        f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode()
        for event in events
    )


def _opening_events(text: str) -> list[dict[str, object]]:
    """`message_start`, then one complete text block."""
    return [
        {
            "type": "message_start",
            "message": {
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": _MODEL,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 1},
            },
        },
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": text},
        },
        {"type": "content_block_stop", "index": 0},
    ]


def _closing_events(
    stop_reason: str, stop_details: dict[str, object] | None = None
) -> list[dict[str, object]]:
    """`message_delta` carrying the stop reason, then `message_stop`."""
    return [
        {
            "type": "message_delta",
            "delta": {
                "stop_reason": stop_reason,
                "stop_sequence": None,
                "stop_details": stop_details,
            },
            "usage": {"output_tokens": 42},
        },
        {"type": "message_stop"},
    ]


class _Transport:
    """Mocked HTTP layer: records every request, answers 200 with an SSE body."""

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []
        self.body = _sse(*_opening_events(_REPLY), *_closing_events("end_turn"))

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return httpx2.Response(
            200, headers={"content-type": "text/event-stream"}, content=self.body
        )


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> _Transport:
    """`AnthropicClient` builds the real SDK client, over a mocked transport.

    The SDK reads `ANTHROPIC_BASE_URL` and `ANTHROPIC_CUSTOM_HEADERS` even when a key
    is passed, and a custom `Authorization` header replaces the key: both are
    removed so a developer's shell cannot change the request under test.
    """
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_CUSTOM_HEADERS", raising=False)
    recorder = _Transport()
    real_sdk_client = anthropic.AsyncAnthropic

    def build_sdk_client(*, api_key: str) -> anthropic.AsyncAnthropic:
        http_client = httpx2.AsyncClient(
            transport=httpx2.MockTransport(recorder.handle)
        )
        return real_sdk_client(api_key=api_key, http_client=http_client)

    monkeypatch.setattr(
        "adjents.llm.anthropic_client.anthropic.AsyncAnthropic", build_sdk_client
    )
    return recorder


@pytest.mark.parametrize("system", [None, "Be brief."])
async def test_transport_sends_expected_body_and_auth_header(
    transport: _Transport, system: str | None
) -> None:
    """The JSON body actually sent; the key travels as a Bearer token."""
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    reply = await client.complete(_MESSAGES, effort="medium", system=system)
    assert reply == _REPLY
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    assert request.headers["authorization"] == "Bearer test-key"
    assert "x-api-key" not in request.headers
    expected: dict[str, object] = {
        "model": _MODEL,
        "messages": _MESSAGES,
        "max_tokens": 16000,
        "thinking": {"type": "adaptive", "display": "summarized"},
        "output_config": {"effort": "medium"},
        "stream": True,
    }
    if system is not None:
        expected["system"] = system
    assert json.loads(request.content) == expected


async def test_transport_sends_user_and_assistant_turns_in_order(
    transport: _Transport,
) -> None:
    messages = [
        {"role": "user", "content": "Hello."},
        {"role": "assistant", "content": "Hi."},
        {"role": "user", "content": "Plan my week."},
    ]
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    await client.complete(messages, effort="medium")
    sent = json.loads(transport.requests[0].content)
    assert sent["messages"] == messages


@pytest.mark.parametrize("role", ["system", "tool", "User", ""])
async def test_complete_rejects_unknown_role_before_any_request(
    transport: _Transport, role: str
) -> None:
    """The neutral contract has two roles; the system prompt goes through `system`.
    The error names the role, never the content (user data)."""
    messages = [
        {"role": "user", "content": "Hello."},
        {"role": role, "content": "private business detail"},
    ]
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(ValueError, match="role") as exc_info:
        await client.complete(messages, effort="medium")
    assert repr(role) in str(exc_info.value)
    assert "private business detail" not in str(exc_info.value)
    assert transport.requests == []


async def test_transport_refusal_is_read_from_the_stream(
    transport: _Transport,
) -> None:
    transport.body = _sse(
        *_opening_events("Sure, here"),
        *_closing_events(
            "refusal", {"type": "refusal", "category": "cyber", "explanation": "No."}
        ),
    )
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(LLMRefusalError) as exc_info:
        await client.complete(_MESSAGES, effort="medium")
    assert exc_info.value.category == "cyber"
    assert exc_info.value.explanation == "No."


async def test_transport_mid_stream_error_event_raises_sdk_error_without_retry(
    transport: _Transport,
) -> None:
    """An error event after a 200 surfaces as the SDK's generic `APIStatusError`
    with the initial status (200), not as `OverloadedError`, and is not retried.
    SDK errors reach callers unchanged: no provider-neutral mapping yet."""
    error_event: dict[str, object] = {
        "type": "error",
        "error": {"type": "overloaded_error", "message": "Overloaded"},
    }
    transport.body = _sse(*_opening_events("partial"), error_event)
    client = AnthropicClient(api_key="test-key", model=_MODEL)
    with pytest.raises(anthropic.APIStatusError) as exc_info:
        await client.complete(_MESSAGES, effort="medium")
    assert type(exc_info.value) is anthropic.APIStatusError
    assert exc_info.value.status_code == 200
    assert exc_info.value.body == error_event
    assert len(transport.requests) == 1
