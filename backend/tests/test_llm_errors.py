"""Tests for llm.errors: provider-neutral LLM response errors (ADR 0012)."""

from adjents.llm.errors import LLMRefusalError, LLMResponseError, LLMTruncatedError

_MODEL = "claude-opus-5-5"


def test_response_error_keeps_stop_reason_and_model() -> None:
    err = LLMResponseError("no text", stop_reason="end_turn", model=_MODEL)
    assert str(err) == "no text"
    assert err.stop_reason == "end_turn"
    assert err.model == _MODEL


def test_response_error_is_not_a_value_error() -> None:
    """An unrelated `except ValueError` must not swallow an unusable response."""
    assert not issubclass(LLMResponseError, ValueError)


def test_refusal_error_is_a_response_error() -> None:
    err = LLMRefusalError(model=_MODEL, category="cyber", explanation="Declined.")
    assert isinstance(err, LLMResponseError)
    assert err.stop_reason == "refusal"
    assert err.category == "cyber"
    assert err.explanation == "Declined."


def test_refusal_error_accepts_unknown_category() -> None:
    err = LLMRefusalError(model=_MODEL, category=None, explanation=None)
    assert err.category is None
    assert "unspecified" in str(err)


def test_truncated_error_keeps_limits() -> None:
    err = LLMTruncatedError(
        stop_reason="max_tokens", model=_MODEL, max_tokens=16000, output_tokens=16000
    )
    assert isinstance(err, LLMResponseError)
    assert err.stop_reason == "max_tokens"
    assert err.max_tokens == 16000
    assert err.output_tokens == 16000
    assert "max_tokens" in str(err)
