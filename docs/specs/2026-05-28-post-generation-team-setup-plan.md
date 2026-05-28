# Implementation Plan — Post-Generation Team Setup

> Spec: `docs/specs/2026-05-27-post-generation-team-setup.md`
> Date: 2026-05-28 | Branch: `feat/post-generation-team-setup`

## Context

`GeneratorOrgGeneration.generate()` (merged) produces a full org of `AgentSpec` records
in SQLite, all with `is_paused=True`. This feature adds two complementary modes built
on top of that org:

1. **Post-generation team setup** (`TeamSetupOrchestrator`) — a guided, resumable
   conversation flow where the user meets each agent before the org goes live. The COO
   presents itself first; then each N-1 root agent initiates a depth-first traversal
   through its subtree, ending with the root's final team summary. All agents unpause
   atomically on completion.

2. **Direct agent reconfiguration** (`AgentReconfiguration`) — at any point after
   go-live, the user opens a conversation with any single agent to review and adjust
   its configuration without a session layer.

Both modes share the same agent intro prompt, extraction prompt, and
`_apply_agent_updates` logic. All dependencies are already in place: `AnthropicClient`,
`PromptLoader`, `AsyncSession`, `AgentSpec`/`AgentState`/`Skill` models,
`ConversationTable`/`MessageTable`.

---

## Scope

**In scope**: `ValidationSession`, `AgentValidationRecord`, `AgentValidationStatus`,
`TeamSetupError`, `TeamSetupOrchestrator` (full), `AgentReconfiguration` (full),
two new DB tables, four new convert functions, `prompts/agent/intro.md`,
`prompts/agent/extract_agent_adjustments.md`, smoke test, ADRs 0008 + 0009,
and documentation updates.

**Out of scope**: FastAPI endpoints, Chroma memory integration, "via parent" mediated
reconfiguration, org restructuring (add/remove/move agents), frontend UI, agent loop
integration.

---

## Tasks (ordered)

### T1 — DB tables, Pydantic domain models, convert functions

**Files**:

- MODIFY `backend/adjents/db/tables.py` — add two SQLModel tables
- MODIFY `backend/adjents/db/convert.py` — add four convert functions
- CREATE `backend/adjents/generator/team_setup.py` (partial: enums + Pydantic models + `TeamSetupError` only)
- CREATE `backend/tests/test_team_setup_models.py`

#### `tables.py` additions

```python
class ValidationSessionTable(SQLModel, table=True):
    __tablename__ = "validation_sessions"
    id: str = Field(primary_key=True)
    started_at: str           # ISO 8601
    completed_at: str | None = Field(default=None)
    skipped: bool = Field(default=False)


class AgentValidationRecordTable(SQLModel, table=True):
    __tablename__ = "agent_validation_records"
    id: str = Field(primary_key=True)
    session_id: str
    root_agent_id: str
    status: str               # AgentValidationStatus value
    active_agent_id: str | None = Field(default=None)
    active_conversation_id: str | None = Field(default=None)
    navigation_stack: str = Field(default="[]")   # JSON: list[str]
    conversation_ids: str = Field(default="[]")   # JSON: list[str]
    visited_agent_ids: str = Field(default="[]")  # JSON: list[str]
    validated_at: str | None = Field(default=None)  # ISO 8601
```

#### `team_setup.py` (partial — models only at T1)

```python
from enum import StrEnum
from datetime import datetime
from pydantic import BaseModel


class AgentValidationStatus(StrEnum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATED   = "validated"
    SKIPPED     = "skipped"


class ValidationSession(BaseModel):
    id: str
    started_at: datetime
    completed_at: datetime | None
    skipped: bool


class AgentValidationRecord(BaseModel):
    id: str
    session_id: str
    root_agent_id: str
    status: AgentValidationStatus
    active_agent_id: str | None
    active_conversation_id: str | None
    navigation_stack: list[str]
    conversation_ids: list[str]
    visited_agent_ids: list[str]
    validated_at: datetime | None


class TeamSetupError(Exception): ...
```

#### `convert.py` additions

```python
def validation_session_to_table(session: ValidationSession) -> ValidationSessionTable:
    """datetime → ISO 8601 string."""
    ...

def validation_session_from_table(row: ValidationSessionTable) -> ValidationSession:
    """ISO 8601 string → datetime."""
    ...

def agent_validation_record_to_table(
    record: AgentValidationRecord,
) -> AgentValidationRecordTable:
    """JSON-serializes list fields (navigation_stack, conversation_ids, visited_agent_ids)."""
    ...

def agent_validation_record_from_table(
    row: AgentValidationRecordTable,
) -> AgentValidationRecord:
    """JSON-deserializes list fields."""
    ...
```

#### Tests (`test_team_setup_models.py` — all pure, no DB, no LLM)

- `test_validation_session_roundtrip` — `to_table` → `from_table` → equal `ValidationSession`
- `test_validation_session_completed_at_none` — `completed_at=None` survives roundtrip as `None`
- `test_agent_validation_record_roundtrip` — full roundtrip with all fields populated
- `test_navigation_stack_serializes_to_json_string` — `["a", "b"]` → `'["a", "b"]'` in table row
- `test_navigation_stack_empty_list_roundtrip` — `[]` → `"[]"` → `[]`
- `test_visited_agent_ids_roundtrip` — non-empty list survives roundtrip unchanged
- `test_conversation_ids_roundtrip` — same
- `test_agent_validation_status_values` — enum values match spec strings exactly
- `test_agent_validation_record_nullable_fields` — `active_agent_id=None`,
  `active_conversation_id=None`, `validated_at=None` all survive roundtrip as `None`

---

### T2 — Pure helpers: `_advance_traversal` + `_build_agent_context_message`

**Files**:

- MODIFY `backend/adjents/generator/team_setup.py` — add two module-level functions
- MODIFY `backend/tests/test_team_setup.py` — add helper tests (CREATE file if not yet present)

#### `_advance_traversal`

```python
def _advance_traversal(
    current_id: str,
    navigation_stack: list[str],
    visited_agent_ids: list[str],
    children_by_parent: dict[str, list[AgentSpec]],
) -> tuple[AgentSpec | None, list[str], list[str]]:
    """Advance depth-first traversal.

    Returns (next_agent, updated_stack, updated_visited).
    Returns (None, [], updated_visited) when entire subtree is exhausted.

    children_by_parent is pre-loaded by the caller (pure — no DB access).
    Handles backtracking internally via while loop.
    """
    stack = list(navigation_stack)
    visited = list(visited_agent_ids)
    node_id = current_id
    while True:
        children = children_by_parent.get(node_id, [])
        unvisited = [c for c in children if c.id not in visited]
        if unvisited:
            next_agent = unvisited[0]
            stack.append(next_agent.id)
            return next_agent, stack, visited
        else:
            visited.append(node_id)
            stack.pop()
            if stack:
                node_id = stack[-1]
            else:
                return None, [], visited
```

`children_by_parent` is pre-loaded by the orchestrator before each call (full subtree in
one DB query). This keeps `_advance_traversal` pure and testable without a DB session.

#### `_build_agent_context_message`

```python
def _build_agent_context_message(
    agent: AgentSpec,
    skills: list[Skill],
    direct_reports: list[AgentSpec],
    reports_skills: dict[str, list[Skill]],
) -> str:
    """Build the first user message injecting agent data for intro/extraction prompts.

    Every agent block includes the agent_id (UUID) so the extraction LLM can
    reference it. direct_reports is empty for leaf agents or the COO self-intro.
    """
    ...
```

#### Tests (`test_team_setup.py` — pure, no DB, no LLM)

Traversal:

- `test_advance_traversal_descends_to_first_child` — root with 2 children: first child
  returned, its ID appended to stack
- `test_advance_traversal_visits_all_depth_first` — root → child A (leaf) → child B
  (leaf): full sequence matches depth-first order
- `test_advance_traversal_backtracks_from_leaf` — leaf node with a sibling: returns the
  next sibling of the leaf's parent after backtracking
- `test_advance_traversal_returns_none_when_exhausted` — entire subtree visited →
  returns `(None, [], visited)`
- `test_advance_traversal_stack_empty_when_exhausted` — returned stack is exactly `[]`
- `test_advance_traversal_visited_includes_all_nodes` — returned `visited` contains all
  node IDs in the subtree
- `test_advance_traversal_leaf_n1_no_children` — N-1 with no direct reports:
  `_advance_traversal` returns `(None, [], ...)` on the first call
- `test_advance_traversal_coo_only_org` — root with no children at all:
  `(None, [], ...)` immediately
- `test_advance_traversal_navigation_stack_empty_after_final_call` — after exhaustion,
  returned stack is exactly `[]` (not just empty — explicitly `[]`)

Context message:

- `test_build_agent_context_message_includes_agent_uuid` — agent_id UUID present in
  the returned string
- `test_build_agent_context_message_includes_skill_names` — all skill names present
- `test_build_agent_context_message_no_reports_section_for_leaf` — when
  `direct_reports=[]`, no "direct reports" section in the output

---

### T3 — Prompts: `agent/intro.md` + `agent/extract_agent_adjustments.md`

**Files**:

- CREATE `backend/adjents/prompts/agent/intro.md`
- CREATE `backend/adjents/prompts/agent/extract_agent_adjustments.md`

No pytest tests. Correctness validated by the smoke test (T6).

#### `prompts/agent/intro.md`

````markdown
---
version: 1
description: "Agent self-introduction and configuration discussion"
model_hint: "claude-sonnet-4-6"
---

# Agent — Introduction and Conversation

You are an AI agent within Adjents, an autonomous agent platform for solopreneurs.
The first message in this conversation contains your complete configuration: your
agent_id (UUID), name, role description, responsibilities, skills, work hours,
scheduler interval, visual character, and escalation rules. If you have direct
reports, they are listed after your own configuration block.

## Your task

Present yourself naturally and specifically to the user. This is their first time
meeting you. They can adjust your configuration before you start working.

In your opening message:
- Use your actual name and role — be concrete, not generic.
- Briefly describe what you do and what you own.
- Invite the user to ask questions or request changes.
- One or two short paragraphs. Plain text, no markdown headers.

During the conversation:
- Answer questions about your configuration honestly.
- If the user requests a change to your name, role description, responsibilities,
  skills, work hours, scheduler interval, visual character, or escalation rules —
  acknowledge it clearly so it can be recorded.
- If the user asks to move you in the hierarchy, change your domain, or reassign
  your parent agent — explain politely that structural changes (domain, level, parent)
  are planned for a future version. Suggest continuing with the current structure.
- Be concise and conversational. You are meeting your operator for the first time.
````

#### `prompts/agent/extract_agent_adjustments.md`

````markdown
---
version: 1
description: "Extract agent configuration changes from conversation transcripts"
model_hint: "claude-sonnet-4-6"
---

# Extract Agent Adjustments

You are given one or more conversation transcripts between a user and AI agents.
Each transcript is delimited by `---AGENT:<agent_id>---` markers where `<agent_id>`
is a UUID. Your task: extract all configuration changes that were explicitly discussed
and agreed upon.

## Output format (mandatory)

Return a single valid JSON object — nothing else. No markdown, no preamble:

```json
{
  "agent_updates": [
    {
      "agent_id": "<uuid>",
      "fields": {
        "name": "Lucas",
        "role_description": "...",
        "work_hours": "09:00-20:00",
        "scheduler_interval_seconds": 600,
        "visual_character": "character_creative",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "escalation_rules": ["Rule 1"]
      },
      "skills_to_add": [
        {
          "name": "Monthly newsletter",
          "description": "Drafts and sends the monthly newsletter.",
          "inputs": ["subscriber list", "content brief"],
          "outputs": ["drafted newsletter"],
          "requires_human_review": true
        }
      ],
      "skills_to_remove": ["Skill name to remove"],
      "skills_to_update": [
        {
          "name": "Existing skill name",
          "fields": {
            "description": "Updated description.",
            "inputs": ["updated input"],
            "outputs": ["updated output"],
            "requires_human_review": false
          }
        }
      ]
    }
  ]
}
```

## Rules

- Include an entry in `agent_updates` only for agents where at least one change was
  explicitly discussed and confirmed by the user.
- All `fields` keys are optional — include only modified fields.
- `skills_to_add`, `skills_to_remove`, `skills_to_update` must be present for every
  entry, even if empty.
- Do NOT include `domain`, `level`, or `parent_id` in `fields`.
- `visual_character` must be one of: `character_suit`, `character_creative`,
  `character_tech`, `character_support`, `character_analyst`, `character_sales`.
- `scheduler_interval_seconds` must be an integer.
- `work_hours` format: `"HH:MM-HH:MM"` or `null` (always active).
- agent_id values come from the `---AGENT:<agent_id>---` markers.
- If no changes were made in any transcript: `{ "agent_updates": [] }`.
````

---

### T4 — `TeamSetupOrchestrator` (Mode 1)

**Files**:

- MODIFY `backend/adjents/generator/team_setup.py` — add `TeamSetupOrchestrator`
- MODIFY `backend/tests/test_team_setup.py` — add orchestrator tests
- MODIFY `backend/tests/conftest.py` — add `mini_org` and `coo_only_org` fixtures

**Note on file size**: `team_setup.py` will exceed the 300-line soft limit. This is
deliberate — splitting the file artificially (e.g. `team_setup_helpers.py`,
`team_setup_session.py`) would harm cohesion without real benefit. All Mode 1 types
and logic belong together.

**Note on LLM client**: `LLMRouter.get_generator_client()` returns `claude-opus-4-7`
and must NOT be used here. The caller constructs `AnthropicClient` directly:

```python
client = AnthropicClient(api_key=os.environ["ANTHROPIC_API_KEY"], model="claude-sonnet-4-6")
```

This is consistent with the prompt frontmatter (`model_hint: "claude-sonnet-4-6"`).

#### Full interface

```python
class TeamSetupOrchestrator:
    _MAX_RETRIES: int = 3

    def __init__(
        self,
        client: AnthropicClient,
        prompt_loader: PromptLoader,
        session: AsyncSession,
    ) -> None: ...

    async def start_session(self) -> ValidationSession:
        """Create one ValidationSession + one AgentValidationRecord per COO and N-1.
        Raises TeamSetupError if a session already exists."""
        ...

    async def resume_session(self) -> ValidationSession | None:
        """Return the existing incomplete session, or None if none exists or last is completed."""
        ...

    async def start_agent_conversation(
        self, session_id: str, root_agent_id: str
    ) -> str:
        """Start (or resume) a conversation with a COO or N-1 root agent.
        For the COO: navigation_stack = [coo_id], visited_agent_ids = [].
        For N-1: navigation_stack = [n1_id], visited_agent_ids = [].
        Raises TeamSetupError if COO record is not validated/skipped when starting N-1."""
        ...

    async def reply(
        self, session_id: str, root_agent_id: str, message: str
    ) -> str:
        """Append user message to active_conversation_id; return active agent's response.
        Routes to active_agent_id (may be N-2 or deeper, not necessarily root)."""
        ...

    async def complete_current_agent(
        self, session_id: str, root_agent_id: str
    ) -> str:
        """Close active agent's conversation; advance traversal; return next opening message
        or root agent's final team summary. Never returns None.
        Caller detects subtree completion by checking record.navigation_stack == [] after call."""
        ...

    async def validate_team(
        self, session_id: str, root_agent_id: str
    ) -> None:
        """Run extraction on all conversation_ids; apply updates; mark record validated.
        Triggers _go_live if all records are validated or skipped."""
        ...

    async def skip_agent(
        self, session_id: str, root_agent_id: str
    ) -> dict[str, Any]:
        """Mark record skipped; return subtree summary + warning dict."""
        ...

    async def skip_all(self, session_id: str) -> dict[str, Any]:
        """Mark all pending/in-progress records skipped; trigger _go_live.
        Return full org summary + warning dict."""
        ...

    async def get_subtree_summary(
        self, agent_id: str | None
    ) -> dict[str, Any]:
        """Return structured dict: agent + full descendant tree with AgentSpec/Skill data.
        agent_id=None returns the full org."""
        ...

    async def _go_live(self, session_id: str) -> None:
        """Atomic: set all AgentSpec.is_paused=False + all AgentState.status=IDLE +
        ValidationSession.completed_at=now in one DB commit."""
        ...

    async def _call_llm(
        self, system: str, messages: list[dict[str, str]]
    ) -> str: ...

    async def _call_extraction_llm(
        self, conversations: list[str]
    ) -> dict[str, Any]:
        """Retry up to _MAX_RETRIES with corrective feedback.
        Raises TeamSetupError after all retries exhausted."""
        ...

    async def _apply_agent_updates(
        self, agent_updates: list[dict[str, Any]]
    ) -> None:
        """Apply all updates in a single DB commit.
        - Silently drops frozen fields (domain, level, parent_id); logs warning.
        - Drops invalid visual_character; logs warning.
        - Clamps scheduler_interval_seconds to [300, 3600]; logs warning.
        - Skill CRUD: ADD=INSERT new row + extend skill_ids;
          UPDATE=modify existing row; REMOVE=DELETE row + remove from skill_ids.
        - Skill name not found (update/remove): log warning, skip gracefully."""
        ...
```

#### `complete_current_agent` internal logic (Option B)

```python
async def complete_current_agent(self, session_id: str, root_agent_id: str) -> str:
    record = await self._load_record(session_id, root_agent_id)
    current_id = record.active_agent_id

    # 1. Close current agent's conversation
    await self._set_agent_state(current_id, AgentStatus.PAUSED)

    # 2. Advance traversal
    children_by_parent = await self._load_subtree_children(root_agent_id)
    next_agent, new_stack, new_visited = _advance_traversal(
        current_id,
        record.navigation_stack,
        record.visited_agent_ids,
        children_by_parent,
    )

    if next_agent is not None:
        # Open new sub-agent conversation
        record.navigation_stack = new_stack
        record.visited_agent_ids = new_visited
        record.active_agent_id = next_agent.id
        # ... open new conversation, call LLM for opening message
        await self._set_agent_state(next_agent.id, AgentStatus.IN_MEETING_1ON1)
        opening = await self._call_llm(system, messages=[context_msg])
        await self._save_record(record)
        return opening
    else:
        # Subtree complete — final LLM call on root agent
        record.navigation_stack = []          # signal for caller
        record.visited_agent_ids = new_visited
        record.active_agent_id = root_agent_id
        root_spec = await self._get_agent_spec(root_agent_id)
        await self._set_agent_state(root_agent_id, AgentStatus.IN_MEETING_1ON1)
        summary = await self._call_llm(system, messages=[root_context_msg])
        await self._save_record(record)
        return summary
```

#### Fixtures (add to `backend/tests/conftest.py`)

```python
@pytest_asyncio.fixture
async def mini_org(db_session: AsyncSession) -> dict[str, str]:
    """Three-agent org: COO → N-1 Finance Lead → N-2 Invoicing Specialist.
    Each has one skill. All AgentState.status = PAUSED.
    Returns dict: {"coo_id": ..., "n1_id": ..., "n2_id": ...}.
    """
    coo_id, n1_id, n2_id = str(uuid4()), str(uuid4()), str(uuid4())
    coo_skill_id, n1_skill_id, n2_skill_id = str(uuid4()), str(uuid4()), str(uuid4())

    specs = [
        AgentSpec(id=coo_id, name="Jordan", level=0, parent_id=None,
                  domain=None, role_description="COO — coordinates all N-1 leads.",
                  responsibilities=["Coordinate N-1 leads"],
                  skill_ids=[coo_skill_id], escalation_rules=[],
                  scheduler_interval_seconds=900, work_hours="09:00-18:00",
                  visual_character="character_suit", is_paused=True),
        AgentSpec(id=n1_id, name="Alex", level=1, parent_id=coo_id,
                  domain="Finance", role_description="Finance Lead.",
                  responsibilities=["Manage invoicing"],
                  skill_ids=[n1_skill_id], escalation_rules=[],
                  scheduler_interval_seconds=1800, work_hours="09:00-18:00",
                  visual_character="character_analyst", is_paused=True),
        AgentSpec(id=n2_id, name="Sam", level=2, parent_id=n1_id,
                  domain="Finance", role_description="Invoicing Specialist.",
                  responsibilities=["Track invoices"],
                  skill_ids=[n2_skill_id], escalation_rules=[],
                  scheduler_interval_seconds=1800, work_hours="09:00-18:00",
                  visual_character="character_analyst", is_paused=True),
    ]
    skills = [
        Skill(id=coo_skill_id, name="Synthesis", description="Aggregates reports.",
              inputs=[], outputs=[], requires_human_review=False),
        Skill(id=n1_skill_id, name="Invoicing", description="Tracks invoices.",
              inputs=[], outputs=[], requires_human_review=True),
        Skill(id=n2_skill_id, name="Tracking", description="Tracks payment status.",
              inputs=[], outputs=[], requires_human_review=False),
    ]
    states = [
        AgentState(agent_id=coo_id, status=AgentStatus.PAUSED,
                   meeting_with=[], updated_at=datetime.now(UTC)),
        AgentState(agent_id=n1_id, status=AgentStatus.PAUSED,
                   meeting_with=[], updated_at=datetime.now(UTC)),
        AgentState(agent_id=n2_id, status=AgentStatus.PAUSED,
                   meeting_with=[], updated_at=datetime.now(UTC)),
    ]
    for skill in skills:
        db_session.add(skill_to_table(skill))
    for spec in specs:
        db_session.add(agent_spec_to_table(spec))
    for state in states:
        db_session.add(agent_state_to_table(state))
    await db_session.commit()
    return {"coo_id": coo_id, "n1_id": n1_id, "n2_id": n2_id}


@pytest_asyncio.fixture
async def coo_only_org(db_session: AsyncSession) -> dict[str, str]:
    """Single-agent org: COO only (no N-1 agents).
    Returns dict: {"coo_id": ...}.
    """
    coo_id = str(uuid4())
    coo_skill_id = str(uuid4())
    # ... same pattern, only COO
    return {"coo_id": coo_id}
```

#### Mock LLM call ordering for `test_team_setup.py`

Tests that exercise `TeamSetupOrchestrator` mock `AnthropicClient.complete` with
`AsyncMock(side_effect=[...])`. The expected call sequence in a full Mode 1 run on
`mini_org` (COO + N-1 Finance + N-2 Invoicing):

```text
Call 1 — start_agent_conversation(coo_id)
         system=intro_prompt, messages=[coo_context_msg]
         → mock returns: "Hello, I'm Jordan, your COO..."

Call 2 — reply(coo_id, "Can you rename yourself to Claude?")
         → mock returns: "Of course! I'll go by Claude from now on."

Call 3 — complete_current_agent(coo_id)
         COO has no children → _advance_traversal returns (None, [], ...)
         final summary LLM call on COO
         → mock returns: "Here is my full configuration summary..."
         → record.navigation_stack == [] after this call

Call 4 — start_agent_conversation(n1_id)
         system=intro_prompt, messages=[n1_context_msg]
         → mock returns: "Hello, I'm Alex, Finance Lead..."

Call 5 — complete_current_agent(n1_id)
         N-2 Invoicing is unvisited → _advance_traversal returns (N-2, [n1_id, n2_id], [])
         opening LLM call on N-2
         → mock returns: "Hello, I'm Sam, Invoicing Specialist..."
         → record.navigation_stack == [n1_id, n2_id]

Call 6 — complete_current_agent(n1_id) [N-2 is now active]
         N-2 is a leaf → _advance_traversal returns (None, [], [n2_id])
         final summary LLM call on N-1 root
         → mock returns: "Here is the Finance team summary..."
         → record.navigation_stack == [] after this call

Call 7 — validate_team(n1_id): extraction LLM call
         → mock returns: '{"agent_updates": [{"agent_id": "<n1_id>",
            "fields": {"name": "Lucas"}, "skills_to_add": [],
            "skills_to_remove": [], "skills_to_update": []}]}'
```

Individual tests use `side_effect` slices of the above sequence.

#### Tests for T4 (`test_team_setup.py`)

Session management:

- `test_start_session_creates_validation_session` — `ValidationSessionTable` row in DB
- `test_start_session_creates_one_record_per_coo_and_n1` — 2 `AgentValidationRecordTable`
  rows (COO + N-1 Finance; N-2 Invoicing is not a root so not a record)
- `test_start_session_all_records_pending` — all records have `status="pending"`
- `test_start_session_raises_if_session_exists` — second call raises `TeamSetupError`
- `test_resume_session_returns_existing_incomplete_session` — returns the session
- `test_resume_session_returns_none_if_no_session` — `None` when DB is empty
- `test_resume_session_returns_none_if_session_completed` — `None` when
  `completed_at` is set

Conversation:

- `test_start_agent_conversation_sets_record_in_progress` — `status="in_progress"`
- `test_start_agent_conversation_sets_agent_state_in_meeting` — `AgentState.status=IN_MEETING_1ON1`
- `test_start_agent_conversation_raises_if_coo_not_validated` — `TeamSetupError` when
  starting N-1 while COO record is `status="pending"`
- `test_start_agent_conversation_coo_stack_is_coo_id` — `navigation_stack=[coo_id]`
- `test_start_agent_conversation_n1_stack_is_n1_id` — `navigation_stack=[n1_id]`
- `test_reply_returns_active_agent_response` — non-empty string returned
- `test_reply_appends_to_conversation_history` — `MessageTable` has 2 rows after one
  `start_agent_conversation` + one `reply`
- `test_start_agent_conversation_resumes_in_progress_record` — record already
  `in_progress` with an existing `active_conversation_id`: LLM called once (resume
  message), returned string is non-empty, `MessageTable` row count increases by 1
  (not reset), `active_conversation_id` unchanged

Traversal:

- `test_complete_current_agent_opens_next_subagent` — N-1 has N-2 → LLM called for
  N-2 opening; returned string matches mock N-2 response
- `test_complete_current_agent_updates_navigation_stack` — after call 5, `navigation_stack=[n1_id, n2_id]`
- `test_complete_current_agent_closes_current_agent_state` — closing agent:
  `AgentState.status` reverts to `PAUSED`
- `test_complete_current_agent_opens_next_agent_state` — next sub-agent:
  `AgentStatus.IN_MEETING_1ON1`
- `test_complete_current_agent_returns_root_summary_when_subtree_done` — N-2 (leaf):
  mock final LLM call on N-1 root; returned string matches mock summary
- `test_complete_current_agent_navigation_stack_empty_when_subtree_done` — after call 6
  (N-2 leaf exhausted), `record.navigation_stack == []`
- `test_complete_current_agent_leaf_n1_returns_summary_immediately` — N-1 with no
  direct reports: first `complete_current_agent` call returns summary + `navigation_stack == []`
- `test_complete_current_agent_coo_returns_summary` — COO has no children:
  `complete_current_agent` returns summary + `navigation_stack == []`

Validation:

- `test_validate_team_calls_extraction_llm` — extraction mock called once
- `test_validate_team_applies_name_update` — `AgentSpec.name` updated in DB
- `test_validate_team_marks_record_validated` — `status="validated"`
- `test_validate_team_reverts_visited_agents_to_paused` — after `validate_team`,
  all agents whose conversation was opened (root + all visited sub-agents) have
  `AgentState.status=PAUSED`; agents that were never visited are unaffected
- `test_validate_team_triggers_go_live_when_all_records_done` — all records
  validated/skipped → `AgentSpec.is_paused=False` in DB
- `test_validate_team_no_go_live_when_records_pending` — one record still pending →
  `is_paused` unchanged

Skip:

- `test_skip_agent_marks_record_skipped` — `status="skipped"`
- `test_skip_agent_returns_subtree_summary` — return value contains agent name
- `test_skip_agent_reverts_active_agent_state_to_paused` — if a conversation was
  open when `skip_agent` is called, the active agent's `AgentState.status` reverts
  to `PAUSED`
- `test_skip_all_marks_all_records_skipped` — all records skipped
- `test_skip_all_triggers_go_live` — `AgentSpec.is_paused=False`

Go-live:

- `test_go_live_sets_all_is_paused_false` — all `AgentSpecTable.is_paused=False`
- `test_go_live_sets_all_states_idle` — all `AgentStateTable.status="idle"`
- `test_go_live_sets_session_completed_at` — `ValidationSessionTable.completed_at`
  is a non-null ISO 8601 string

Apply updates:

- `test_apply_agent_updates_modifies_name` — `AgentSpec.name` updated in DB
- `test_apply_agent_updates_adds_skill` — new `SkillTable` row + `AgentSpec.skill_ids` extended
- `test_apply_agent_updates_removes_skill` — `SkillTable` row deleted + removed from `skill_ids`
- `test_apply_agent_updates_updates_skill_description` — `SkillTable.description` updated
- `test_apply_agent_updates_drops_frozen_fields_silently` — `domain`/`level`/`parent_id`
  in update dict → no error, DB field unchanged
- `test_apply_agent_updates_drops_invalid_visual_character` — unknown value → field
  unchanged in DB
- `test_apply_agent_updates_clamps_scheduler_interval_low` — `299` → `300` in DB
- `test_apply_agent_updates_clamps_scheduler_interval_high` — `9999` → `3600` in DB

Extraction retries:

- `test_extraction_retry_on_invalid_json_succeeds` — 2 bad JSON responses then 1 valid
  → success, return value is a dict
- `test_extraction_raises_after_max_retries` — 3 invalid responses → `TeamSetupError`

COO-only org (uses `coo_only_org` fixture):

- `test_coo_only_org_start_session_creates_one_record` — only 1 `AgentValidationRecordTable`
  row (COO only, no N-1 records)
- `test_coo_only_org_validate_team_triggers_go_live` — validating COO (only record)
  triggers immediate `_go_live`

---

### T5 — `AgentReconfiguration` (Mode 2)

**Files**:

- CREATE `backend/adjents/agents/reconfiguration.py`
- CREATE `backend/tests/test_agent_reconfiguration.py`

#### AgentReconfiguration interface

```python
class AgentReconfiguration:
    _MAX_RETRIES: int = 3

    def __init__(
        self,
        agent_id: str,
        client: AnthropicClient,
        prompt_loader: PromptLoader,
        session: AsyncSession,
    ) -> None: ...

    async def start(self) -> str:
        """Load AgentSpec + direct reports from DB; set AgentState.status=IN_MEETING_1ON1;
        create a new Conversation + inject agent context as first message;
        call LLM for opening message; return it."""
        ...

    async def reply(self, message: str) -> str:
        """Append user message to conversation; call LLM; return response."""
        ...

    async def apply_changes(self) -> None:
        """Call extraction LLM on conversation transcript; apply updates to DB;
        restore AgentState.status to prior value (PAUSED in v0.1 — agent loop not active)."""
        ...

    async def _call_llm(self, system: str, messages: list[dict[str, str]]) -> str: ...
    async def _call_extraction_llm(self, conversations: list[str]) -> dict[str, Any]: ...
    async def _apply_agent_updates(self, agent_updates: list[dict[str, Any]]) -> None: ...
```

**Note on duplication**: `_call_extraction_llm` and `_apply_agent_updates` are duplicated
from `TeamSetupOrchestrator` (~70 lines). This is deliberate for v0.1: a shared utilities
module would require careful dependency management between `generator/` and `agents/`.
Accepted per the feature spec.

#### Tests (`test_agent_reconfiguration.py` — uses `mini_org` fixture)

- `test_start_returns_opening_message` — returns non-empty string
- `test_start_sets_agent_state_in_meeting` — `AgentState.status=IN_MEETING_1ON1`
- `test_reply_continues_conversation` — returns non-empty string; `MessageTable` has
  more rows after the call
- `test_apply_changes_calls_extraction_llm` — extraction mock called once
- `test_apply_changes_updates_agent_spec` — name change extracted → `AgentSpec.name` in DB
- `test_apply_changes_restores_agent_state` — `AgentState.status=PAUSED` after apply
- `test_leaf_agent_no_subtree_context` — N-2 agent (leaf): `_build_agent_context_message`
  called with `direct_reports=[]`; no reports section in the injected message

---

### T6 — Smoke test `scripts/smoke_team_setup.py`

**File**:

- CREATE `backend/scripts/smoke_team_setup.py`

Not a pytest test. Not run by CI.

#### Script structure

```text
smoke_team_setup.py
  Runs in two modes:
    - mock (default):  AsyncMock LLM, fully automated, assertions on DB state
    - real (--real):   requires ANTHROPIC_API_KEY; prints conversation to stdout

Usage:
    uv run python scripts/smoke_team_setup.py
    uv run python scripts/smoke_team_setup.py --real
```

**Precondition**: the script generates a minimal inline org (COO + 3 N-1 agents +
1 N-2 under the first N-1) using `GeneratorOrgGeneration.generate()` with a mock LLM,
or directly via `_resolve_and_build` + `_persist` if simpler. Avoids depending on a
pre-existing DB state.

**Mock mode scenario — Mode 1**:

1. Generate minimal org + `start_session()` → assert correct number of records
2. COO conversation:
   - `start_agent_conversation(coo_id)` → mock "I'm the COO"
   - `reply("Rename yourself to Robin")` → mock ack
   - `validate_team(coo_id)` → mock extraction returns
     `{"agent_updates": [{"agent_id": coo_id, "fields": {"name": "Robin"}, ...}]}`
   - Assert: `AgentSpec.name == "Robin"` in DB
3. N-1 #0 with N-2:
   - `start_agent_conversation(n1_id)` → mock "I'm the Finance Lead"
   - `complete_current_agent(n1_id)` → mock "I'm N-2..." ; assert `navigation_stack` updated
   - `complete_current_agent(n1_id)` (N-2 is leaf) → mock final summary ; assert `navigation_stack == []`
   - `validate_team(n1_id)` → mock extraction → assert applied
4. **Interruption simulation**: destroy orchestrator instance, recreate with same DB session,
   call `resume_session()` → assert `session_id` matches, `active_agent_id` is correct
5. `skip_all(session_id)` → assert all remaining records skipped
6. Assert: all `AgentSpec.is_paused=False`, all `AgentState.status=IDLE`,
   `ValidationSession.completed_at` is set

**Mock mode scenario — Mode 2**:

- `AgentReconfiguration(n2_id, ...).start()` → mock "I'm Sam..."
- `reply("Update work_hours to 08:00-20:00")` → mock ack
- `apply_changes()` → mock extraction → assert `AgentSpec.work_hours == "08:00-20:00"` in DB
- Assert: `AgentState.status` restored to previous value

**Real mode**: same flow, real LLM, human-readable output printed.

---

### T7 — Documentation updates

**Files** (no pytest tests for this task):

- CREATE `docs/decisions/0008-team-setup-natural-conversation-extraction.md`
  — ADR: natural language conversations + single LLM extraction call at validation time;
  rationale vs. intent-classification approach; duplication accepted for v0.1
- CREATE `docs/decisions/0009-direct-agent-reconfiguration-v01.md`
  — ADR: direct reconfiguration in v0.1 (all modifiable fields, no parent mediation);
  v0.2 introduces parent-mediated path for structural fields; COO exception
- MODIFY `docs/ARCHITECTURE.md`
  — §3: add `ValidationSession` + `AgentValidationRecord` model rows + JSON-serialized
  list fields note; §5: update lifecycle diagram with `IN_MEETING_1ON1` transitions;
  §9: add `agent/intro` + `agent/extract_agent_adjustments` to prompt loading table
- MODIFY `docs/VISION.md`
  — §4.1: add direct agent reconfiguration to v0.1 scope; §4.2: rephrase
  "micro-adjustments" item to reflect the full conversation-based approach
- MODIFY `docs/decisions/0005-org-restructuring.md`
  — Add note: direct reconfiguration (all modifiable fields) in v0.1; via-parent
  mediated changes (work_hours, responsibilities, role_description for non-COO agents)
  in v0.2
- MODIFY `docs/decisions/0006-post-generation-validation.md`
  — Update with full design: depth-first traversal, extraction schema, go-live flow;
  mark initial sketch as superseded
- MODIFY `PROJECT_STATE.md`
  — Add session entry; update milestone table; update decisions log with ADR 0008 + 0009
- MODIFY `README.md`
  — §"What v0.1 includes": add direct agent reconfiguration
- MODIFY `backend/README.md`
  — Scripts section: add `smoke_team_setup.py` entry

---

## TDD execution order

```text
T1 → T2 → T3 → T4 → T5 → T6 → T7
```

Each task (T1–T5):

1. Write failing tests (RED) — `uv run pytest tests/<test_file> -v`
2. Write implementation (GREEN) — make tests pass
3. `uv run ruff check adjents/ tests/ && uv run mypy adjents/`
4. Move to the next task

T3 has no pytest tests but must be committed before T4: T4 integration tests mock
`PromptLoader` in conftest to return a stub prompt object:

```python
@pytest.fixture
def stub_prompt_loader(monkeypatch: pytest.MonkeyPatch) -> PromptLoader:
    loader = MagicMock(spec=PromptLoader)
    stub = MagicMock()
    stub.content = "You are a helpful agent."
    loader.get.return_value = stub
    return loader
```

The smoke test (T6) uses the real `PromptLoader` pointed at the actual prompt files.

T6 can only run after T4 and T5 are complete. Run mock mode first to validate DB
state, then real mode manually:

```bash
cd backend
uv run python scripts/smoke_team_setup.py
uv run python scripts/smoke_team_setup.py --real
```

T7 can proceed in parallel with T6 or after it.

---

## Critical file reference

| Role | Path |
| --- | --- |
| Agent models (AgentSpec, AgentState, Skill) | `backend/adjents/agents/models.py` |
| DB tables | `backend/adjents/db/tables.py` |
| Convert functions | `backend/adjents/db/convert.py` |
| AnthropicClient | `backend/adjents/llm/anthropic_client.py` |
| LLMRouter (reference — do not use for team setup) | `backend/adjents/router/router.py` |
| PromptLoader | `backend/adjents/prompts/loader.py` |
| VALID_VISUAL_CHARACTERS | `backend/adjents/generator/org_generation.py` |
| Org generation (reference pattern) | `backend/adjents/generator/org_generation.py` |
| Existing interview class (reference pattern) | `backend/adjents/generator/interview.py` |
| Test conftest | `backend/tests/conftest.py` |
| Smoke test reference | `backend/scripts/smoke_generator_org.py` |
| Feature Spec | `docs/specs/2026-05-27-post-generation-team-setup.md` |

---

## Files created / modified

| Action | Path |
| --- | --- |
| CREATE | `backend/adjents/generator/team_setup.py` |
| CREATE | `backend/adjents/agents/reconfiguration.py` |
| CREATE | `backend/adjents/prompts/agent/intro.md` |
| CREATE | `backend/adjents/prompts/agent/extract_agent_adjustments.md` |
| CREATE | `backend/scripts/smoke_team_setup.py` |
| CREATE | `backend/tests/test_team_setup_models.py` |
| CREATE | `backend/tests/test_team_setup.py` |
| CREATE | `backend/tests/test_agent_reconfiguration.py` |
| CREATE | `docs/decisions/0008-team-setup-natural-conversation-extraction.md` |
| CREATE | `docs/decisions/0009-direct-agent-reconfiguration-v01.md` |
| MODIFY | `backend/adjents/db/tables.py` |
| MODIFY | `backend/adjents/db/convert.py` |
| MODIFY | `backend/tests/conftest.py` |
| MODIFY | `docs/ARCHITECTURE.md` |
| MODIFY | `docs/VISION.md` |
| MODIFY | `docs/decisions/0005-org-restructuring.md` |
| MODIFY | `docs/decisions/0006-post-generation-validation.md` |
| MODIFY | `PROJECT_STATE.md` |
| MODIFY | `README.md` |
| MODIFY | `backend/README.md` |

---

## Coherence notes

### LLM client: `AnthropicClient` directly, not via `LLMRouter`

`LLMRouter.get_generator_client()` returns `claude-opus-4-7`. Team setup and
reconfiguration use `claude-sonnet-4-6` for cost/speed. The caller constructs:

```python
client = AnthropicClient(api_key=os.environ["ANTHROPIC_API_KEY"], model="claude-sonnet-4-6")
```

and injects it. This matches both prompt frontmatters (`model_hint: "claude-sonnet-4-6"`).
LLMRouter routing for team setup will be revisited once the full router feature is built.

### `complete_current_agent()` always returns `str` (Option B)

`complete_current_agent()` never returns `None`. When `_advance_traversal` signals
subtree exhaustion (`(None, [], visited)`), the orchestrator:

1. Sets `record.navigation_stack = []` — the caller's signal
2. Sets `record.active_agent_id = root_agent_id`
3. Makes one final LLM call on the root agent (team summary)
4. Returns that string — always a displayable message

The caller detects subtree completion by checking `record.navigation_stack == []` AFTER
the call. The last string returned is always meaningful content.

### `_advance_traversal` as a pure function

The spec's `_get_next_agent` pseudocode was replaced by `_advance_traversal`, which:

- Takes `children_by_parent: dict[str, list[AgentSpec]]` pre-loaded by the caller
- Handles backtracking internally via `while True` — no recursive calls
- Returns `(next_agent | None, updated_stack, updated_visited)` — pure, no DB access
- Is fully testable without a DB session (T2 tests cover all traversal paths)

The orchestrator pre-loads the entire subtree before calling `_advance_traversal`,
then writes the returned stack and visited list back to `AgentValidationRecord`.

### COO specificity

The COO does not traverse a subtree. Its `navigation_stack` is always `[coo_id]` at
start. `children_by_parent` for the COO will have no entry (N-1 agents are root_agent_ids
in their own records, not children in the COO record's traversal). When
`complete_current_agent` is called on the COO, `_advance_traversal` returns
`(None, [], ...)` immediately, triggering the COO's own final summary LLM call.

### Agent context as first user message

Same decision as `org_generation.py`: agent data (AgentSpec + subtree + explicit UUIDs)
is injected as the first user message, not in the system prompt. This avoids
`str.format_map()` KeyError on user-supplied text that may contain curly braces.
`prompt.content` is used (not `prompt.render()`) for both prompts.

### `team_setup.py` line count exception

`team_setup.py` will exceed the 300-line soft limit. Splitting it artificially (e.g.
`team_setup_helpers.py`, `team_setup_session.py`) would harm cohesion without real
benefit. All Mode 1 types and logic belong in one file. This exception is deliberate.

### Skill CRUD semantics in `_apply_agent_updates`

- **ADD**: `INSERT` new `SkillTable` row; append new `skill.id` to `AgentSpec.skill_ids`
- **UPDATE**: `UPDATE` existing `SkillTable` row matched by skill name within the agent's
  current `skill_ids`; no change to `skill_ids`
- **REMOVE**: `DELETE` `SkillTable` row; remove its id from `AgentSpec.skill_ids`

When the skill name is not found (for UPDATE or REMOVE): log a warning, skip gracefully.
All three operations are applied in a single `await session.commit()`.

### Import direction preserved

`generator/team_setup.py` imports from `agents/models.py` (existing direction:
`generator/` → `agents/`). `agents/reconfiguration.py` imports only from
`agents/models.py`. No new cross-direction dependencies introduced.

---

## Verification

```bash
cd backend
uv run pytest tests/ -v              # all tests pass (existing + new)
uv run ruff check adjents/ tests/    # 0 errors
uv run mypy adjents/                 # mypy --strict clean
```

Then run the smoke test:

```bash
cd backend
uv run python scripts/smoke_team_setup.py          # mock mode
uv run python scripts/smoke_team_setup.py --real   # requires ANTHROPIC_API_KEY
```
