# ADR 0012 — Provider-Neutral LLM Call Contract

**Date**: 2026-10-22
**Status**: Accepted

---

## Context

Every LLM call in Adjents goes through `AnthropicClient.complete()`: the Generator
interview (turns + `BusinessContext` extraction), org generation, and post-generation
team setup / reconfiguration (conversations + adjustments extraction). Until step 3
the contract was minimal: `complete(messages, system, max_tokens=8192) -> str`, using
`messages.stream()` + `get_final_text()` (ADR 0007).

Step 3 migrates these calls from Claude Opus 4.7 / Sonnet 4.6 to Claude Opus 5.5 /
Sonnet 5.5. The new models change what a call means:

- **Thinking is always on.** Disabling it returns a 400 on both models. Our calls never
  sent `thinking`, so they used to run without it; thinking now counts toward
  `max_tokens` and is billed as output.
- **Effort is the main control**, and its API default changed silently: `high` on
  Opus 4.7, `medium` on Opus 5.5; Sonnet 5.5 keeps `high` but with recalibrated levels.
- **Safety classifiers can decline** a request with HTTP 200 and
  `stop_reason == "refusal"`, before any output or mid-stream.
- `get_final_text()` ignores `stop_reason`: a truncated or partially refused response
  is returned as if complete, and a response without a text block raises an uncaught
  `RuntimeError`.

At the same time, VISION §3.6 / §4.1 require the Generator and team setup to be
selectable among Anthropic, OpenAI and Google Gemini (implemented in step 10 with the
LLM router). The contract seen by callers must therefore not encode Anthropic
semantics, even though only `AnthropicClient` exists today.

---

## Decision

### 1. `complete()` is the provider-neutral contract

Callers depend only on: `messages`, `system`, `effort`, `max_tokens`, a `str` result,
and the error types below. Anthropic-specific parameters (`thinking`, `output_config`,
`display`, beta headers) stay inside `AnthropicClient`. A formal `LLMClient` protocol
is introduced in step 10, when the OpenAI and Gemini clients exist.

### 2. Effort is required on every call

- `Effort = Literal["low", "medium", "high"]` in `adjents/llm/types.py`. Each client
  maps it to its provider's control (identity mapping for Anthropic's
  `output_config.effort`). `xhigh` / `max` are left out until a measured need.
- `effort` is a **required keyword argument** of `complete()`; the client has no
  default. A forgotten effort fails `mypy --strict` (and raises `TypeError` before any
  API call) instead of silently inheriting a default.
- Values are interim module constants in each caller, next to `_MAX_TOKENS`:

| Call | Model | Effort |
| --- | --- | --- |
| Interview turns | `claude-opus-5-5` | `medium` |
| `BusinessContext` extraction | `claude-opus-5-5` | `medium` |
| Org generation | `claude-opus-5-5` | `high` |
| Team setup / reconfiguration conversations | `claude-sonnet-5-5` | `medium` |
| Team setup / reconfiguration extraction | `claude-sonnet-5-5` | `medium` |

### 3. `max_tokens` is a guardrail sized for thinking + reply

- Default **16000**; org generation **64000**. The cap covers thinking and the reply.
- Raising it costs nothing by itself (billing is on generated tokens; per the rate-limit
  docs, `max_tokens` does not count toward OTPM) and the model does not see it. Its
  only role is to bound the cost and duration of a runaway call.
- A cap that is too low now fails loudly (`LLMTruncatedError`), so, unlike `effort`,
  `max_tokens` keeps a default.
- `stop_reason` and `usage.output_tokens` are logged at DEBUG to calibrate the caps.

### 4. Unusable responses raise typed errors

In `adjents/llm/errors.py`, with provider-neutral names:

- `LLMResponseError(Exception)` — the call succeeded at HTTP level but the response is
  unusable (empty text, unexpected `stop_reason`). Attributes: `stop_reason`, `model`.
- `LLMRefusalError(LLMResponseError)` — the model or a safety classifier declined.
  Attributes: `category: str | None`, `explanation: str | None`.
- `LLMTruncatedError(LLMResponseError)` — output stopped at a limit (`max_tokens` or
  `model_context_window_exceeded`). Attributes: `max_tokens`, `output_tokens`.

`AnthropicClient` reads `get_final_message()`, checks `stop_reason` **before**
extracting text, accepts only `end_turn`, and concatenates `text` blocks only
(thinking blocks are skipped). Partial output of a refused or truncated response is
never returned. Refusals and truncations are logged at WARNING (model, `stop_reason`,
category, output tokens — never content).

Callers **do not retry and do not wrap** these errors: their retry loops only catch
`JSONDecodeError`, so the errors propagate unchanged. Smoke scripts catch
`LLMResponseError` to print a clean diagnostic.

### 5. Server-side fallbacks are not enabled

Refusals surface as `LLMRefusalError`. Anthropic's server-side `fallbacks` are not used
in v0.1 step 3; the fallback policy is decided with the router in step 10.

### 6. Thinking is explicit and summarized, inside `AnthropicClient`

- Every request sends `thinking: {"type": "adaptive", "display": "summarized"}`, so
  behavior does not depend on per-model defaults (omitting `thinking` means adaptive on
  Opus 5.5 / Sonnet 5.5 but *no thinking* on Opus 4.7 / 4.8).
- Thinking summaries are exposed only through a dedicated DEBUG logger,
  `adjents.llm.thinking`, disabled by default. This is a deliberate exception to "log
  counters, never content": the logger is opt-in, local to the process, and its output
  contains user business data.
- The `complete()` contract is unchanged; per-call tracing (storage, retention,
  sensitivity rules, evals, agent-reasoning UI) is designed in step 10.

---

## Alternatives Considered

| Option | Reason rejected |
| --- | --- |
| **Rely on the API's default effort** | The default changed silently between model generations (`high` → `medium` on Opus); org generation would have dropped a level unnoticed. |
| **Default effort on the client, overridable per call** | Recreates the same trap at our scale: changing the default silently changes every call that omitted it. |
| **Effort in prompt frontmatter** | Effort belongs to the (model, task) pair, not to the prompt text, and loses meaning when the provider changes; scatters routing data outside the router (rule 4); frontmatter is untyped (a typo only fails at the API); `model_hint` shows that unread frontmatter drifts. |
| **Per-role settings table in the router now** | Would design the step 10 router before studying the OpenAI and Gemini APIs. |
| **`max_tokens` at the model maximum (128k) everywhere** | No cost or rate-limit downside, but removes the only hard bound on a runaway call (Opus 5.5: $2.56 per attempt, ×3 retries for org generation, plus minutes of latency). |
| **Errors in `adjents/errors.py`** | That module holds domain errors and exists to break a `generator/` → `agents/` dependency; LLM errors belong with the LLM contract in `adjents/llm/`. |
| **Subclass `ValueError`** (previous empty-response error) | No caller relies on it; an unrelated `except ValueError` could swallow a refusal. |
| **Retry refusals and truncations in callers** | A refusal on the same input is likely to repeat; a truncation with the same cap and effort too. Both are paid calls; the fix is a fallback policy or a configuration change, not a blind retry. |
| **Wrap into `InterviewError` / `OrgGenerationError` / `TeamSetupError`** | Loses the refusal / truncation distinction the future API layer needs (user-facing message vs internal error); four modules to change for no gain. |
| **Enable server-side fallbacks now** (`fallbacks: "default"`) | Beta, Claude API only, refusals only (not outages); the fallback model is chosen by Anthropic, not by our router (rule 4); sticky routing for ~1 hour; on Sonnet 5.5 only `cyber` / `frontier_llm` declines are retried. Deferred to step 10, against the SDK guide's "opt in from day one" advice. |
| **Omit `thinking`** | Equivalent on the two current models, but behavior would then depend on each model's default. |
| **`display: "omitted"`** | No visibility on the model's reasoning while debugging; billing is identical under every display mode. |
| **Return thinking in a structured result now** | Changes the contract for every call site and designs tracing before the router exists. |

---

## Consequences

**Positive:**

- Callers are already written against the contract that the OpenAI and Gemini clients
  will implement in step 10.
- Every call states its effort; no model default can change behavior silently.
- Truncated or refused output can no longer be mistaken for a valid answer, and the
  JSON retry loops no longer resend broken output to the model.
- Reasoning summaries are available for debugging and the smoke tests.

**Negative:**

- Effort and `max_tokens` are scattered as constants across four caller modules until
  step 10 moves them into the router's per-role table.
- A refusal is a hard failure in v0.1 (no fallback), and SDK HTTP errors
  (`anthropic.*`) still reach callers unmapped (step 10).
- The DEBUG thinking logger can write user business data to logs when enabled.
- Every call now carries thinking tokens; cost per call can rise despite the lower
  per-token prices of the 5.5 models.

**Related:** ADR 0007 (always stream — amended in step 3), ADR 0008 (team setup
routing — amended in step 3), ARCHITECTURE §8 (LLM router).
