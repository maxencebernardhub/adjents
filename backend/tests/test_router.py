"""Tests for router.router: LLMRouter."""

from unittest.mock import MagicMock, patch

import pytest

from adjents.llm.anthropic_client import AnthropicClient
from adjents.router.router import LLMConfigError, LLMRouter


def _keys_passed(mock_client_cls: MagicMock) -> list[str]:
    """API keys received by every `AnthropicClient` the router built."""
    return [call.kwargs["api_key"] for call in mock_client_cls.call_args_list]


def test_router_passes_env_key_to_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
    with patch("adjents.router.router.AnthropicClient") as mock_cls:
        LLMRouter()
    assert _keys_passed(mock_cls) == ["sk-env-key", "sk-env-key"]


def test_router_direct_key_takes_priority_over_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
    with patch("adjents.router.router.AnthropicClient") as mock_cls:
        LLMRouter(anthropic_api_key="sk-direct-key")
    assert _keys_passed(mock_cls) == ["sk-direct-key", "sk-direct-key"]


def test_router_empty_direct_key_falls_back_to_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
    with patch("adjents.router.router.AnthropicClient") as mock_cls:
        LLMRouter(anthropic_api_key="")
    assert _keys_passed(mock_cls) == ["sk-env-key", "sk-env-key"]


@pytest.mark.parametrize("raw", ["sk-x\n", " sk-x ", "\tsk-x\r\n"])
def test_router_strips_whitespace_around_direct_key(raw: str) -> None:
    with patch("adjents.router.router.AnthropicClient") as mock_cls:
        LLMRouter(anthropic_api_key=raw)
    assert _keys_passed(mock_cls) == ["sk-x", "sk-x"]


def test_router_strips_whitespace_around_env_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x \n")
    with patch("adjents.router.router.AnthropicClient") as mock_cls:
        LLMRouter()
    assert _keys_passed(mock_cls) == ["sk-x", "sk-x"]


def test_router_rejects_blank_direct_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A whitespace-only direct key is an error, not a silent fallback to the env."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
    with pytest.raises(LLMConfigError):
        LLMRouter(anthropic_api_key="  ")


def test_router_rejects_blank_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", " \n")
    with pytest.raises(LLMConfigError):
        LLMRouter()


@pytest.mark.parametrize(
    "bad_key",
    ["sk-ant-SECRET x", "sk-ant-SECRET\nx", "sk-ant-SECRET\x00x", "sk-ant-SECRETé"],
)
def test_router_rejects_key_with_invalid_characters_without_naming_it(
    bad_key: str,
) -> None:
    """The HTTP layer would reject the header and echo the key in its error chain."""
    with pytest.raises(LLMConfigError) as exc_info:
        LLMRouter(anthropic_api_key=bad_key)
    assert "SECRET" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_router_raises_without_any_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMConfigError, match="ANTHROPIC_API_KEY"):
        LLMRouter()


def test_router_error_message_is_not_generator_specific(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The router now serves the team setup too, not only the Generator Agent."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMConfigError) as exc_info:
        LLMRouter()
    assert "Generator" not in str(exc_info.value)


def test_get_generator_client_returns_anthropic_client() -> None:
    router = LLMRouter(anthropic_api_key="sk-test-key")
    client = router.get_generator_client()
    assert isinstance(client, AnthropicClient)


def test_get_generator_client_uses_opus_5_5() -> None:
    router = LLMRouter(anthropic_api_key="sk-test-key")
    assert router.get_generator_client().model == "claude-opus-5-5"


def test_get_team_setup_client_returns_anthropic_client() -> None:
    router = LLMRouter(anthropic_api_key="sk-test-key")
    assert isinstance(router.get_team_setup_client(), AnthropicClient)


def test_get_team_setup_client_uses_sonnet_5_5() -> None:
    """Team setup is routed too: no caller hard-codes a model (ADR 0008)."""
    router = LLMRouter(anthropic_api_key="sk-test-key")
    assert router.get_team_setup_client().model == "claude-sonnet-5-5"
