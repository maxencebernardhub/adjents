"""Provider-neutral errors for LLM responses that cannot be used.

Raised by LLM clients when the call succeeded at the HTTP level but the response is
unusable: declined, cut off at a limit, empty or stopped for an unexpected reason.
Callers neither retry nor wrap them (their retry loops only cover invalid JSON); they
propagate to the caller's caller — today the smoke scripts, later the API layer,
which maps refusals and truncations to distinct outcomes. Transport errors (rate
limits, 5xx, network) are not covered here: they are still raised by the provider
SDK (mapping planned in step 10).

Related ADRs: 0012 (provider-neutral LLM call contract).
"""


class LLMResponseError(Exception):
    """The LLM call succeeded but its response is unusable.

    Deliberately not a `ValueError`: an unrelated `except ValueError` must not
    swallow it.

    Attributes:
        stop_reason: Why generation stopped, as reported by the provider.
        model: The model that produced the response.
    """

    def __init__(self, message: str, *, stop_reason: str | None, model: str) -> None:
        super().__init__(message)
        self.stop_reason = stop_reason
        self.model = model


class LLMRefusalError(LLMResponseError):
    """The model or a provider safety classifier declined the request.

    Any partial output is discarded, never returned.

    Attributes:
        category: Provider policy category (e.g. "cyber"), or None when unknown.
        explanation: Provider explanation, or None. Not guaranteed to be stable.
    """

    def __init__(
        self, *, model: str, category: str | None, explanation: str | None
    ) -> None:
        super().__init__(
            f"LLM request declined (category: {category or 'unspecified'}).",
            stop_reason="refusal",
            model=model,
        )
        self.category = category
        self.explanation = explanation


class LLMTruncatedError(LLMResponseError):
    """Output stopped at a limit (output token cap or context window).

    Usually a configuration issue (`max_tokens` too low for the effort level), not a
    transient one.

    Attributes:
        max_tokens: The output token cap sent with the request.
        output_tokens: Output tokens actually generated, thinking included.
    """

    def __init__(
        self, *, stop_reason: str, model: str, max_tokens: int, output_tokens: int
    ) -> None:
        super().__init__(
            f"LLM output truncated ({stop_reason}) after {output_tokens} output "
            f"tokens (max_tokens={max_tokens}).",
            stop_reason=stop_reason,
            model=model,
        )
        self.max_tokens = max_tokens
        self.output_tokens = output_tokens
