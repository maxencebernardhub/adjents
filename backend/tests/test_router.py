"""Tests for router.router: LLMRouter."""

import pytest

from adjents.llm.anthropic_client import AnthropicClient
from adjents.router.router import LLMConfigError, LLMRouter


def test_router_accepts_direct_key() -> None:
    router = LLMRouter(anthropic_api_key="sk-test-key")
    assert router is not None


def test_router_reads_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
    router = LLMRouter()
    assert router is not None


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


def test_router_direct_key_takes_priority_over_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
    router = LLMRouter(anthropic_api_key="sk-direct-key")
    client = router.get_generator_client()
    assert isinstance(client, AnthropicClient)


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
