"""Async Anthropic LLM client."""

from typing import Any

import anthropic


class AnthropicClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if system is not None:
            kwargs["system"] = system
        response = await self._client.messages.create(**kwargs)
        block = response.content[0]
        if block.type != "text":
            raise ValueError(f"Unexpected content block type: {block.type!r}")
        return str(block.text)
