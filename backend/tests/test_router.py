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


def test_get_generator_client_uses_opus_model() -> None:
    router = LLMRouter(anthropic_api_key="sk-test-key")
    client = router.get_generator_client()
    assert client._model == "claude-opus-4-7"
