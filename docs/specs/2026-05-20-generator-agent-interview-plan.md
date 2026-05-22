# Implementation Plan — Generator Agent Interview

> Spec: `docs/specs/2026-05-20-generator-agent-interview.md`
> Date: 2026-05-21 | Branch: `feat/generator-agent-interview`

## Context

The Generator Agent is the entry point for every new Adjents user. It conducts a
multi-turn onboarding interview to collect the 11 mandatory items needed to generate a
full AI team (`BusinessContext`). This feature also builds all shared infrastructure
(PromptLoader, AnthropicClient, LLMRouter) that the rest of v0.1 depends on.
Nothing else in v0.1 can start until this feature is complete.

---

## Scope

**In scope**: PromptLoader, Anthropic client, minimal router (cloud provider selection),
`BusinessContext` model + DB, interview conversation loop, transcript persistence,
interrupt + resume, real interview prompt, extraction prompt.

**Out of scope**: Ollama client, Google/OpenAI clients, full routing rules,
org generation, any frontend/WebSocket integration.

---

## Tasks (ordered)

### T1 — `BusinessContext` model

**Files**:

- CREATE `backend/adjents/generator/models.py`
- CREATE `backend/tests/test_models_generator.py`

**Interface**:

```python
class BusinessContext(BaseModel):
    id: str
    conversation_id: str
    business_name: str | None
    founder_name: str
    language: str                            # e.g. "fr", "en"
    core_activity: str
    legal_status: str | None
    target_clients: list[str]
    domains_with_human_coverage: list[str]
    domains_to_staff: list[str]
    tasks_to_delegate: list[str]
    tasks_user_keeps: list[str]
    financial_goals: str | None
    existing_tools: list[str]
    autonomy_preference: str
    work_hours: str | None                   # "HH:MM-HH:MM" or None = always available
    additional_context: str | None
    created_at: datetime
```

**Tests**: valid instance, optional fields as None, empty lists, missing required field
raises `ValidationError`, serialisation roundtrip.

---

### T2 — `BusinessContextTable` + convert functions

**Files**:

- MODIFY `backend/adjents/db/tables.py` — add `BusinessContextTable`
- MODIFY `backend/adjents/db/convert.py` — add `business_context_to_table` / `business_context_from_table`
- MODIFY `backend/tests/test_db_convert.py` — add `test_business_context_roundtrip`
- MODIFY `backend/tests/test_db_tables.py` — add persistence test

**Pattern**: identical to existing tables — `list[str]` → `json.dumps`, `datetime` → ISO 8601.

**Table schema**:

```python
class BusinessContextTable(SQLModel, table=True):
    __tablename__ = "business_contexts"
    id: str = Field(primary_key=True)
    conversation_id: str
    business_name: str | None = Field(default=None)
    founder_name: str
    language: str
    core_activity: str
    legal_status: str | None = Field(default=None)
    target_clients: str = Field(default="[]")           # JSON list[str]
    domains_with_human_coverage: str = Field(default="[]")
    domains_to_staff: str = Field(default="[]")
    tasks_to_delegate: str = Field(default="[]")
    tasks_user_keeps: str = Field(default="[]")
    financial_goals: str | None = Field(default=None)
    existing_tools: str = Field(default="[]")
    autonomy_preference: str
    work_hours: str | None = Field(default=None)
    additional_context: str | None = Field(default=None)
    created_at: str                                     # ISO 8601
```

**Note**: `conftest.py` already imports `adjents.db.tables` — the new table is auto-registered.

---

### T3 — `PromptLoader`

**Files**:

- CREATE `backend/adjents/prompts/loader.py`
- CREATE `backend/tests/test_prompts_loader.py`

**Interface**:

```python
@dataclass
class LoadedPrompt:
    frontmatter: dict[str, Any]
    content: str

    def render(self, **kwargs: str) -> str:
        """Substitute {variable} placeholders in content via str.format_map."""
        ...

class PromptLoader:
    def __init__(self, prompts_dir: Path) -> None: ...

    def load_all(self) -> None:
        """Load and cache all .md files at startup."""
        ...

    def get(self, key: str) -> LoadedPrompt:
        """Get prompt by relative path without extension, e.g. 'generator/interview'."""
        ...
```

**Frontmatter parsing**: no external dependency. Format is `---\nkey: value\n---\n`.
Rules: value in double quotes → `str`; purely numeric value → `int`; otherwise `str`.

**Template substitution**: `content.format_map(kwargs)` — `{variable}` syntax.

**Tests**: load a real file, frontmatter parsed correctly (types), render with variables,
get non-existent file raises `FileNotFoundError`, `load_all` caches all files.

---

### T4 — `AnthropicClient`

**Files**:

- CREATE `backend/adjents/llm/anthropic_client.py`
- CREATE `backend/tests/test_llm_anthropic.py`

**Interface**:

```python
class AnthropicClient:
    def __init__(self, api_key: str, model: str) -> None: ...

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Send multi-turn messages and return the text response."""
        ...
```

**Implementation details**:

- Uses `anthropic.AsyncAnthropic`
- Extracts `response.content[0].text` (checks `block.type == "text"`)
- Raises `ValueError` if block is not of type "text"

**Tests**: mock `anthropic.AsyncAnthropic`, verify API call arguments, verify text
extraction, verify system prompt is passed, `ValueError` on non-text block.

---

### T5 — Minimal `LLMRouter`

**Files**:

- CREATE `backend/adjents/router/router.py`
- CREATE `backend/tests/test_router.py`

**Interface**:

```python
class LLMConfigError(Exception): ...

class LLMRouter:
    def __init__(self, anthropic_api_key: str | None = None) -> None:
        """Reads ANTHROPIC_API_KEY from env if not passed directly.
        Raises LLMConfigError at construction if no provider is configured."""
        ...

    def get_generator_client(self) -> AnthropicClient:
        """Return the LLM client to use for the Generator Agent."""
        ...
```

**Provider logic**:

- Only Anthropic is supported (Google/OpenAI/Ollama: future feature)
- Missing `ANTHROPIC_API_KEY` → `LLMConfigError` with a clear message
- `get_generator_client()` returns `AnthropicClient(key, "claude-opus-4-7")`

**Default model**: `"claude-opus-4-7"` (matches `model_hint` in `interview.md` frontmatter)

**Tests**: construction succeeds with mocked env key, `LLMConfigError` without key,
`get_generator_client()` returns an `AnthropicClient` with the expected model.

---

### T6 — Real prompts

**Files**:

- MODIFY `backend/adjents/prompts/generator/interview.md` — replace placeholder
- CREATE `backend/adjents/prompts/generator/extract_business_context.md` — new

**`interview.md`** — system prompt for the interview:

- Response format for every turn:
  `{"message": "...", "ready_to_generate": false, "missing_mandatory_info": [...]}`
- Lists the 11 mandatory items to collect
- Conversational rules: adaptive order, no re-asking, capture volunteered info
- Language detection from the first user message (default English on ambiguous input)
- 3-question closing sequence before setting `ready_to_generate: true`
- Frontmatter: `version: 1`, `description`, `model_hint: "claude-opus-4-7"`

**`extract_business_context.md`** — system prompt for extraction:

- Instructs the LLM to extract a `BusinessContext` JSON from a full transcript
- Full JSON schema in the prompt (without `id`, `conversation_id`, `created_at` — added by Python)
- Default to empty lists for fields not mentioned in the conversation
- Return only the JSON object, no surrounding text

---

### T7 — `GeneratorInterview` (orchestration)

**Files**:

- CREATE `backend/adjents/generator/interview.py`
- CREATE `backend/tests/test_generator_interview.py`

**Interface**:

```python
@dataclass
class InterviewResponse:
    message: str
    ready_to_generate: bool
    missing_mandatory_info: list[str]

class InterviewError(Exception): ...

class GeneratorInterview:
    def __init__(
        self,
        client: AnthropicClient,
        prompt_loader: PromptLoader,
        session: AsyncSession,
    ) -> None: ...

    async def start(self) -> str:
        """Create a new Conversation + call LLM. Returns the first agent message."""
        ...

    async def reply(self, user_message: str) -> InterviewResponse:
        """Append user turn, call LLM, persist. Persists BusinessContext when done."""
        ...

    async def resume(self, conversation_id: str) -> None:
        """Reload a paused interview from DB."""
        ...
```

**Design decisions**:

1. **`start()` kickoff**: Anthropic requires the first message to have role "user".
   `start()` sends `[{"role": "user", "content": "Hello."}]` as a hidden kickoff.
   The system prompt instructs the LLM to ignore it and open with its greeting.
   Both the kickoff message and the agent response are persisted to DB.

2. **Stored message format**: the `content` of "generator" messages stores the raw JSON
   string (`{"message": "...", "ready_to_generate": ..., ...}`).
   `_build_llm_messages()` reconstructs the Anthropic-format history from `self._messages`.

3. **Retry on invalid JSON**: `_call_llm()` retries up to `_MAX_RETRIES = 3` times.
   On JSON parse failure, appends `{"role": "assistant", "content": raw}` +
   a correction instruction before retrying. Retry messages are NOT persisted to DB.

4. **`BusinessContext` extraction**: when `ready_to_generate: true`, a separate LLM call
   uses `prompts/generator/extract_business_context.md` + the full conversation transcript
   → parses JSON → creates `BusinessContext` → persists to DB.
   `id` and `created_at` are generated in Python (`uuid4()` / `datetime.now(UTC)`).

5. **Conversation persistence**: `await session.merge(conversation_to_table(...))` for
   upsert after each turn (SQLAlchemy `merge` handles create-or-update by PK).

6. **`resume()`**: loads `ConversationTable` + all `MessageTable` in `message_ids` order.
   No new LLM call — the next `reply()` picks up from the reloaded state.

**Tests** (all with mocked `AnthropicClient.complete`):

- `start()` → Conversation + 2 messages persisted, returns the agent message text
- `reply()` → user message persisted, LLM called with full history, `InterviewResponse` returned
- `reply()` with `ready_to_generate: true` → `BusinessContext` persisted to DB
- Interrupted interview (no `ready_to_generate`) → partial transcript persisted, no `BusinessContext`
- `resume()` → reloads state from DB; subsequent `reply()` works correctly
- Retry on invalid JSON → 2 failures + 1 success: OK; 3 failures → `InterviewError`

---

## TDD execution order

```text
T1 → T2 → T3 → T4 → T5 → T6 → T7
```

Each task: tests RED → implementation → tests GREEN → ruff + mypy.

---

## Critical file reference

| Role | Path |
| --- | --- |
| Existing messaging models | `backend/adjents/messaging/models.py` |
| Existing DB tables | `backend/adjents/db/tables.py` |
| Existing convert functions | `backend/adjents/db/convert.py` |
| DB engine | `backend/adjents/db/engine.py` |
| Test conftest | `backend/tests/conftest.py` |
| Interview prompt placeholder | `backend/adjents/prompts/generator/interview.md` |
| Roleplay reference example | `docs/specs/2026-05-20-generator-agent-interview-roleplay.md` |

---

## Verification

```bash
cd backend
uv run pytest tests/ -v              # all tests pass (existing + new)
uv run ruff check adjents/ tests/    # 0 errors
uv run mypy adjents/                 # mypy --strict clean
```
