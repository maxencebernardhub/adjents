"""Async Anthropic LLM client — always uses streaming to support large outputs.

Streaming is required by the Anthropic SDK for Opus 4+ models when
max_tokens > 8192 (their MODEL_NONSTREAMING_TOKENS threshold). Using streaming
unconditionally removes the constraint and keeps the API surface identical.
"""

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
        max_tokens: int = 8192,
    ) -> str:
        """Send a chat request and return the response text.

        Uses the streaming API internally so callers are not limited to
        max_tokens ≤ 8192 (the Opus 4 non-streaming threshold).
        Raises ValueError if the response contains no text.
        """
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if system is not None:
            kwargs["system"] = system
        async with self._client.messages.stream(**kwargs) as stream:
            text = await stream.get_final_text()
        if not text:
            raise ValueError("LLM response contained no text.")
        return text
