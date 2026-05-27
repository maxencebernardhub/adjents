# ADR 0007 — AnthropicClient uses streaming unconditionally

**Date**: 2026-05-25
**Status**: Accepted
**Deciders**: Maxence Bernard

---

## Context

The Anthropic Python SDK defines a per-model non-streaming token threshold
(`MODEL_NONSTREAMING_TOKENS`). For Opus 4.x models (e.g.
`claude-opus-4-20250514`), this threshold is **8192**: any call to
`messages.create()` with `max_tokens > 8192` raises a `ValueError` at
request time before any network call is made.

`GeneratorOrgGeneration` requires `_MAX_TOKENS = 32000` because org JSONs
for businesses with 10+ domains and rich skill sets routinely exceed 8192
output tokens. Opus 4.7 supports up to 128k output tokens, so the ceiling
is an SDK enforcement constraint, not a model limitation.

---

## Options considered

### Option A — Stream only when `max_tokens > 8192`

Add a conditional branch inside `AnthropicClient.complete()`: use
`messages.create()` for small requests and `messages.stream()` for large
ones.

**Rejected.** The threshold value (`MODEL_NONSTREAMING_TOKENS`) can change
across SDK versions without a major bump. Conditional branching makes the
client harder to test (two code paths, two mock strategies) and provides no
benefit — the streaming path is not meaningfully slower for single-shot
requests where the caller does not process intermediate tokens.

### Option B — Always use `messages.create()` with a workaround

Not possible. The SDK enforces the limit at the client level and raises
before the request is sent. No workaround exists short of monkey-patching
the SDK.

### Option C — Always stream (chosen)

`AnthropicClient.complete()` uses the streaming API unconditionally:

```python
async with self._client.messages.stream(**kwargs) as stream:
    text = await stream.get_final_text()
```

`get_final_text()` waits for the full response before returning, so the
caller API is identical to the non-streaming path. The `max_tokens`
constraint is lifted entirely.

---

## Decision

**`AnthropicClient.complete()` always uses `messages.stream()`**, regardless
of the `max_tokens` value. This removes the 8192 non-streaming ceiling for
Opus 4+ models, keeps the method signature and return type unchanged, and
future-proofs the client against SDK threshold changes.

---

## Consequences

- **Callers**: unaffected. `complete()` still returns `str` and raises
  `ValueError` on empty response. No caller changes required.
- **Tests**: must mock `messages.stream()` (an async context manager)
  instead of `messages.create()`. A `_FakeStream` helper class in
  `tests/test_llm_anthropic.py` provides the minimal async context manager
  contract needed.
- **`GeneratorOrgGeneration._MAX_TOKENS = 32000`**: now works without
  raising. Complex orgs (10+ domains) can be generated in a single LLM
  call without truncation.
- **Other LLM clients** (Ollama, OpenAI, Google): unaffected — each has
  its own client class. This decision applies to `AnthropicClient` only.
