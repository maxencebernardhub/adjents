# ADR 0007 — AnthropicClient uses streaming unconditionally

**Date**: 2026-05-25
**Status**: Accepted

---

## Context

The Anthropic Python SDK defines a per-model non-streaming token threshold
(`MODEL_NONSTREAMING_TOKENS`). For Opus 4.x models (e.g.
`claude-opus-4-20250514`), this threshold is **8192**: any call to
`messages.create()` with `max_tokens > 8192` raises a `ValueError` at
request time before any network call is made. (Rationale corrected — see
Amendment 2026-10-22.)

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

---

## Amendments

### 2026-10-22 — Rationale correction (Claude 5.5 migration)

The Context section attributes the constraint to `MODEL_NONSTREAMING_TOKENS`
(8192 for "Opus 4.x"). This is inaccurate. In the installed SDK (checked in
`anthropic` 0.103.1 on 2026-10-16 and 2.1.0 on 2026-10-22), that table only
lists Opus 4.0 and 4.1. The check that applies to every model is the SDK's
expected-duration check (`_calculate_nonstreaming_timeout`):
`3600 × max_tokens / 128000` seconds > 600 ⇒ `ValueError`, i.e. a
non-streaming `messages.create()` fails above ~21,333 `max_tokens`. The check
only runs when no explicit timeout is set, so Option B's "no workaround
exists" is also inaccurate: an explicit timeout bypasses it, but the SDK
itself requires streaming for operations that may exceed 10 minutes.

The decision is unchanged and reinforced: with Claude 5.5 models thinking is
always on and counts toward `max_tokens`, and org generation now uses
`max_tokens = 64000`, well above the threshold.

Consequences updated: `complete()` reads `get_final_message()` and checks
`stop_reason` before extracting text (`get_final_text()` ignores it); an empty
response raises `LLMResponseError` instead of `ValueError` (see ADR 0012).
