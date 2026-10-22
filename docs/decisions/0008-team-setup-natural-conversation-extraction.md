# ADR 0008 — Team Setup: Natural Conversation + Single LLM Extraction

**Date**: 2026-05-27
**Status**: Accepted

---

## Context

After org generation, the user needs to review and adjust agent configurations before
agents go live. Each agent presents itself, the user may request changes, and the
resulting conversation must be translated into concrete DB updates (rename, skill
addition, work hours change, etc.).

Two approaches were considered for capturing user-requested changes:

**Option A — Per-turn intent classification**: after each user message, a second LLM
call classifies whether the message contains a configuration change and emits a
structured diff. Changes are applied incrementally, turn by turn.

**Option B — Natural conversation + single extraction**: the conversation proceeds
freely in natural language. When the user is satisfied (explicit "validate" action),
a single extraction LLM call reads the full conversation transcript and produces all
changes at once.

---

## Decision

**Option B** — natural conversation for N turns, single extraction LLM call at
validation time.

The extraction call receives the full conversation transcript, delimited by
`---AGENT:<agent_id>---` markers (with the agent's UUID). It returns a single JSON
object with `agent_updates`: a list of per-agent diffs (field updates, skills to add,
skills to update, skills to remove).

This same pattern is used for both:

1. **`TeamSetupOrchestrator.validate_team()`** — validates one root agent (COO or N-1)
   and applies changes from all conversations in that record's subtree
2. **`AgentReconfiguration.apply_changes()`** — applies changes from the single agent
   conversation

Both use the same prompt (`prompts/agent/extract_agent_adjustments.md`) and the same
`_apply_agent_updates()` helper. The helper (~70 lines) is intentionally duplicated
between `generator/team_setup.py` and `agents/reconfiguration.py` rather than sharing
a utilities module — this avoids cross-direction dependencies between `generator/` and
`agents/` for v0.1. Shared utilities will be introduced in v0.2 when the scope
justifies the dependency.

---

## Alternatives Considered

| Alternative | Reason rejected |
| --- | --- |
| **Per-turn intent classification** | Interrupts conversation flow — every user message triggers a second LLM call; adds latency, increases cost, and introduces parsing errors in the middle of the conversation |
| **Agent-emits-diff format** | Requires the intro prompt to produce structured output, which conflicts with the goal of natural self-introduction; a separate extraction model is cleaner |
| **Shared `_apply_agent_updates` utility module** | Introduced a cross-direction import (`generator/` → `agents/`) that was not justified by the v0.1 codebase size; duplication is explicit and accepted |

---

## Consequences

- **Extraction model**: `claude-sonnet-4-6` (matching the prompt frontmatter
  `model_hint`). NOT routed via `LLMRouter.get_generator_client()` (which returns
  `claude-opus-4-7`). The caller constructs `AnthropicClient` directly. LLMRouter
  integration will be revisited in v0.2. (Model and routing changed — see
  Amendment 2026-10-22.)
- **Retry logic**: the extraction call retries up to `_MAX_RETRIES = 3` times on
  invalid JSON, with corrective feedback appended to the conversation. After all
  retries, `TeamSetupError` is raised (from `adjents/errors.py`).
- **Frozen fields**: `domain`, `level`, and `parent_id` are silently dropped from
  any `fields` dict in `agent_updates`. These are structural fields whose mutation
  is deferred to v0.2 (org restructuring via Generator Agent — see ADR 0005). A
  warning is logged.
- **Guardrails**: `visual_character` is validated against `VALID_VISUAL_CHARACTERS`;
  `scheduler_interval_seconds` is clamped to `[300, 3600]`. Invalid values are
  logged as warnings and silently skipped.

---

## Amendment — 2026-05-29 (spec compliance corrections)

Two helpers originally described as duplicated have been moved to neutral shared
modules, resolving the cross-direction import issue more cleanly than planned:

- **`TeamSetupError`** moved to `adjents/errors.py`. Both `TeamSetupOrchestrator`
  and `AgentReconfiguration` import it from there. This avoids a `generator/ →
  agents/` import that would have been needed if `AgentReconfiguration` imported
  it from `generator/team_setup.py`.

- **`_build_agent_context_message`** moved to `adjents/utils/agent_context.py`.
  Both classes import it from there. The function has no dependency on either
  `generator/` or `agents/` internals — a shared `utils/` module is the correct
  home.

- **`_apply_agent_updates`** remains duplicated (~70 lines) in both
  `generator/team_setup.py` and `agents/reconfiguration.py`. The rationale in
  the original decision still holds for this helper.

The Alternatives Considered table entry "Shared `_apply_agent_updates` utility
module" therefore applies narrowly to `_apply_agent_updates` only. The broader
pattern (share genuinely neutral helpers in `utils/`; duplicate direction-specific
logic) supersedes the blanket "no shared utilities" stance.

---

## Amendment — 2026-10-22 (Claude 5.5 migration: model and routing)

Two consequences listed above change in step 3; the decision itself
(natural conversation, then a single extraction call at validation time)
is unchanged.

- **Model**: team setup conversations and extraction now use
  `claude-sonnet-5-5`, both at effort `medium` (see ADR 0012).
- **Routing**: the client is no longer built by the caller. It comes from
  `LLMRouter.get_team_setup_client()`, so no caller hard-codes a model ID
  (architecture rule 4). This brings forward, in a minimal form, the
  `LLMRouter` integration announced for v0.2. The per-role method is
  interim: step 10 replaces it with request-based routing.

The `model_hint` field in prompt frontmatter is informational only: no code
reads it. Whether the router consumes or drops it is decided in step 10.
