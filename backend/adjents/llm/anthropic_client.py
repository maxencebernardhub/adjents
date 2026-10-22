"""Async Anthropic client implementing the provider-neutral LLM call contract.

Every LLM call of the Generator interview, org generation, team setup and
reconfiguration goes through `AnthropicClient.complete()`. Clients are obtained from
`LLMRouter`, which owns the choice of model (architecture rule 4).

Request side: `complete()` always streams (`messages.stream()`). A non-streaming
`messages.create()` is refused by the SDK when its expected duration
(`3600 × max_tokens / 128000` s) exceeds 10 minutes, i.e. above ~21,333
`max_tokens` — below what org generation needs once thinking shares the output
budget. Every request sends adaptive thinking with summarized display and an
explicit effort, so behavior never depends on per-model API defaults.

Response side: `stop_reason` is checked before any text is read, because the SDK's
`get_final_text()` ignores it and would return truncated or partially refused
output as if complete. Only `text` blocks are returned; thinking summaries go to
the opt-in `adjents.llm.thinking` DEBUG logger.

Related ADRs: 0007 (always stream, amended), 0012 (provider-neutral LLM call
contract).
"""

import logging
from typing import Any

import anthropic
from anthropic.types import Message, TextBlock, ThinkingBlock

from adjents.llm.errors import LLMRefusalError, LLMResponseError, LLMTruncatedError
from adjents.llm.types import Effort

_log = logging.getLogger(__name__)
# Separate logger so reasoning summaries — which contain user business data — are
# enabled on purpose, never as a side effect of turning on DEBUG for the client.
_thinking_log = logging.getLogger("adjents.llm.thinking")

_TRUNCATION_STOP_REASONS = frozenset({"max_tokens", "model_context_window_exceeded"})


class AnthropicClient:
    """Anthropic implementation of the LLM call contract (ADR 0012).

    Args:
        api_key: Anthropic API key.
        model: Model ID, chosen by `LLMRouter`.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def model(self) -> str:
        """The model ID every request is sent to."""
        return self._model

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        effort: Effort,
        system: str | None = None,
        max_tokens: int = 16000,
    ) -> str:
        """Send a conversation and return the model's reply text.

        Args:
            messages: Conversation turns (`role` + `content`), ending with a user
                turn — assistant prefill is rejected by current models.
            effort: Reasoning effort; required so no default applies silently.
            system: Optional system prompt.
            max_tokens: Output cap, thinking included. A guardrail on cost and
                latency, not a cost: billing is on generated tokens.

        Returns:
            The concatenated text blocks of a complete (`end_turn`) response.

        Raises:
            LLMRefusalError: The model or a safety classifier declined.
            LLMTruncatedError: Output hit `max_tokens` or the context window.
            LLMResponseError: Any other unusable response (no text, unexpected
                stop reason).
        """
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": effort},
        }
        if system is not None:
            kwargs["system"] = system
        async with self._client.messages.stream(**kwargs) as stream:
            message = await stream.get_final_message()
        return self._extract_text(message, max_tokens)

    def _extract_text(self, message: Message, max_tokens: int) -> str:
        """Validate the stop reason, then return the reply text."""
        stop_reason = message.stop_reason
        output_tokens = message.usage.output_tokens
        _log.debug(
            "model=%s stop_reason=%s output_tokens=%d",
            message.model,
            stop_reason,
            output_tokens,
        )
        for block in message.content:
            if isinstance(block, ThinkingBlock) and block.thinking:
                _thinking_log.debug(
                    "model=%s thinking summary:\n%s", message.model, block.thinking
                )

        if stop_reason == "refusal":
            details = message.stop_details
            category = details.category if details else None
            _log.warning(
                "LLM refusal: model=%s category=%s output_tokens=%d",
                message.model,
                category,
                output_tokens,
            )
            raise LLMRefusalError(
                model=message.model,
                category=category,
                explanation=details.explanation if details else None,
            )
        if stop_reason in _TRUNCATION_STOP_REASONS:
            _log.warning(
                "LLM output truncated: model=%s stop_reason=%s output_tokens=%d "
                "max_tokens=%d",
                message.model,
                stop_reason,
                output_tokens,
                max_tokens,
            )
            raise LLMTruncatedError(
                stop_reason=str(stop_reason),
                model=message.model,
                max_tokens=max_tokens,
                output_tokens=output_tokens,
            )
        # We send no tools and no stop sequences: any other stop reason means the
        # response cannot be trusted to be complete.
        if stop_reason != "end_turn":
            raise LLMResponseError(
                f"Unexpected stop_reason {stop_reason!r}.",
                stop_reason=stop_reason,
                model=message.model,
            )
        text = "".join(
            block.text for block in message.content if isinstance(block, TextBlock)
        )
        if not text:
            raise LLMResponseError(
                "LLM response contained no text.",
                stop_reason=stop_reason,
                model=message.model,
            )
        return text
