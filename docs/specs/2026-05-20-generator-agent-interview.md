# Feature: Generator Agent — Interview

> Spec date: 2026-05-20 | Status: Validated | Next: Implementation Plan

---

## Feature Brief

**Goal**: Implement the Generator Agent onboarding interview. The Generator Agent conducts
a multi-turn conversation with the user to collect all information needed to generate their
agent organisation. It produces two persisted outputs: the full conversation transcript
(SQLite via existing `Message`/`Conversation` models) and a structured `BusinessContext`
summary that Feature 2 (org generation) will consume.

**Users**: The end user (solopreneur or small business owner) on first launch of Adjents.

**Acceptance criteria**:

- `PromptLoader` (`adjents/prompts/loader.py`) loads `.md` files with YAML frontmatter
  from `backend/adjents/prompts/`, supports template variable substitution, and caches
  all prompts in memory at startup
- Anthropic LLM client (`adjents/llm/anthropic_client.py`) sends multi-turn messages to
  the Anthropic API and returns the text response — async, no framework
- `LLMRouter` (minimal, `adjents/router/router.py`) routes Generator Agent requests to
  the configured LLM provider. Provider selection is driven by which API keys are present
  in `.env` — no hardcoded preference order. If no provider is configured → raises a
  clear error at startup. A local Ollama model is a valid choice for fully offline setups
  (quality trade-off accepted by the user); a cloud LLM is recommended for best results.
  The full routing logic (complexity rules, sensitivity rules, concurrency semaphores) is
  a separate future feature — only provider selection for the Generator Agent is in scope
- The Generator Agent detects the language from the user's first message and responds
  in that language throughout the interview. Default: English if the first message is
  ambiguous (e.g. "Hi", a single name)
- Each Generator Agent response includes a structured payload:
  `{"message": "...", "ready_to_generate": false, "missing_mandatory_info": [...]}`
- The Generator Agent collects the 12 mandatory items conversationally (not as a linear
  questionnaire). The LLM adapts question order and follow-ups based on prior answers;
  information volunteered spontaneously is captured without re-asking
- The 12 mandatory items are:
  1. Identity / commercial name (may be `None` for sole proprietors using their personal name)
  2. Core activity and context
  3. What the user wants to delegate vs. keep for themselves (determines agent domains)
  4. Legal / financial status (e.g. auto-entrepreneur, SASU, LLC)
  5. Target clients
  6. Business domains already covered by humans (excluded from agent generation)
  7. Financial goals (revenue target, fixed costs)
  8. High-level task intentions per emerging domain (skill-level intent, not implementation)
  9. Autonomy / validation preferences (what requires human review before acting)
  10. Availability / work hours
  11. Existing tools, apps, and services the user already uses
  12. Open-ended closing sequence (3 successive questions before confirming readiness):
      "Anything else you'd like to mention?",
      "Any domains or tasks we haven't covered that you'd like to delegate?",
      "Ready to build your team?"
- When `ready_to_generate: true`, the Generator Agent produces a `BusinessContext` object
  (Pydantic) and persists it to SQLite
- All `Message` and `Conversation` records for the interview are persisted to SQLite using
  the existing `db/convert.py` functions
- If the interview is interrupted before `ready_to_generate: true`: the partial transcript
  is persisted; `BusinessContext` is not created; the interview can be resumed by reloading
  the existing `Conversation` and continuing from the last `Message`
- `ruff`, `mypy --strict`, and all tests pass

**`BusinessContext` model** (output of this feature, input to Feature 2):

```python
class BusinessContext(BaseModel):
    id: str
    conversation_id: str            # link to the interview transcript
    business_name: str | None       # None if sole proprietor using personal name
    founder_name: str
    language: str                   # detected language code, e.g. "fr", "en"
    core_activity: str
    legal_status: str | None
    target_clients: list[str]
    domains_with_human_coverage: list[str]   # excluded from agent generation
    domains_to_staff: list[str]              # will become agent domains
    tasks_to_delegate: list[str]             # high-level intent per domain
    tasks_user_keeps: list[str]              # user does these themselves
    financial_goals: str | None
    existing_tools: list[str]
    autonomy_preference: str                 # narrative description
    work_hours: str | None                   # e.g. "18:00-23:00"; None = always
    additional_context: str | None
    created_at: datetime
```

**Edge cases**:

- User launches without a company name → `business_name` is `None`
- User interrupts the interview before completion → partial transcript persisted,
  `BusinessContext` not created, resumable
- Ambiguous first message for language detection → default to English, adapt next turn
- Anthropic API key absent or invalid → clear startup error, not a runtime crash
- LLM response missing the expected JSON payload → retry with explicit instruction,
  no crash
- User spontaneously covers a mandatory item before it's asked → captured, not re-asked
- User explicitly says they want to handle a domain themselves → that domain excluded
  from `domains_to_staff`

**Dependencies**:

- `backend/adjents/db/` (tables, convert, engine) — already implemented
- `backend/adjents/messaging/models.py` (`Message`, `Conversation`) — already implemented
- `backend/adjents/prompts/generator/interview.md` — existing placeholder, to implement
- At least one cloud API key in `.env` (`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`,
  or `OPENAI_API_KEY`)
- `anthropic>=0.103.1` — already in `pyproject.toml`

**Constraints**:

- No AI framework (LangChain, etc.) — official `anthropic` SDK only
- `mypy --strict` must pass at all times
- No prompt strings in Python source — everything in `prompts/generator/interview.md`
- Files max 300 lines
- `PromptLoader` and Anthropic client are shared components (not Generator Agent-specific):
  `adjents/prompts/loader.py` and `adjents/llm/anthropic_client.py`
- In v0.1: no real external actions (no emails sent, no external API calls)
- Full LLM router (Ollama routing, complexity/sensitivity rules, concurrency semaphores)
  is a separate future feature; only provider selection for the Generator Agent is in scope
- See `docs/specs/2026-05-20-generator-agent-interview-roleplay.md` for a full annotated
  example of the interview flow (used as reference for writing the interview prompt)

---

## Scope boundaries

| In scope (this feature) | Out of scope |
| --- | --- |
| `PromptLoader` + `generator/interview.md` prompt | Full `LLMRouter` with Ollama + rules |
| Anthropic LLM client | Google / OpenAI LLM clients |
| Minimal router (cloud provider selection) | Agent-specific skill/tool interviews (post-onboarding) |
| Multi-turn interview conversation state | Org generation from `BusinessContext` (Feature 2) |
| `BusinessContext` Pydantic model + DB persistence | Any frontend / WebSocket integration |
| Transcript persistence (`Message` + `Conversation`) | |
| Interview resume after interruption | |
