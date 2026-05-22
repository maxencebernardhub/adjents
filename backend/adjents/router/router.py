"""Minimal LLM router — provider selection for the Generator Agent.

Full routing rules (Ollama, complexity/sensitivity, semaphores) are a
separate future feature.
"""

import os

from adjents.llm.anthropic_client import AnthropicClient

_GENERATOR_MODEL = "claude-opus-4-7"


class LLMConfigError(Exception): ...


class LLMRouter:
    def __init__(self, anthropic_api_key: str | None = None) -> None:
        key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise LLMConfigError(
                "No LLM provider configured. "
                "Set ANTHROPIC_API_KEY in .env to use the Generator Agent."
            )
        self._client: AnthropicClient = AnthropicClient(
            api_key=key, model=_GENERATOR_MODEL
        )

    def get_generator_client(self) -> AnthropicClient:
        return self._client
