# ADR 0004 — BlockingQuestion as a first-class persisted entity

**Date**: 2026-05-20
**Status**: Accepted

---

## Context

The agent lifecycle (ARCHITECTURE.md §5) includes a `WAITING_FOR_HUMAN` state: an
agent that needs a human decision before it can proceed raises a blocking question,
pauses the affected task, and waits for a response.

The WebSocket protocol (ARCHITECTURE.md §6) already defines two message types that
reference a `question_id`:

```python
# server → client
{"type": "blocking_question", "agent_id": "...", "question": "...", "id": "..."}

# client → server
{"type": "blocking_answer", "question_id": "...", "answer": "..."}
```

The existence of a stable `question_id` implies that blocking questions are persisted
entities, not transient in-memory objects. Without persistence, the system cannot:

- Survive a server restart while a question is pending
- Match an incoming `blocking_answer` to the correct question and agent
- Surface all pending questions at once in the notification UI
- Audit which questions were asked and how they were answered

When building the database layer, a decision was needed: define `BlockingQuestion`
as a domain model and persistence table now, or defer it to the agent loop PR.

---

## Decision

`BlockingQuestion` is defined as a **first-class entity** in this database layer PR:

- A Pydantic `BaseModel` in `backend/adjents/agents/models.py`
- A SQLModel `table=True` class in `backend/adjents/db/tables.py`
- Covered by the standard test suite (valid construction, invalid case, roundtrip)

```python
class BlockingQuestion(BaseModel):
    id: str
    agent_id: str
    question: str
    context: str | None    # why the agent needs this decision
    answered: bool
    answer: str | None
    created_at: datetime
    answered_at: datetime | None
```

---

## Rationale

**Why now and not in the agent loop PR**:

1. **The schema is fully determined**: the WebSocket protocol defines the exact fields
   needed (`id`, `agent_id`, `question`, `answer`). The `context`, `answered`,
   `created_at`, and `answered_at` fields are mechanically derived from the
   lifecycle description. There is no uncertainty to resolve by waiting.

2. **Database schema coherence**: the DB layer should be a complete, self-consistent
   schema. A table that is logically required by the system but missing from the
   initial schema creates a gap that manifests as a migration obligation the moment
   the agent loop PR is written. Building schema piecemeal across feature PRs makes
   the overall data model harder to reason about.

3. **Separation of concerns in the agent loop PR**: the agent loop PR is already
   responsible for the most complex logic in the system (asyncio task management,
   LLM calls, pause/resume, work hours). Adding model and table definitions to that
   PR increases its scope and cognitive load without justification, since those
   definitions belong to the data layer, not the business logic layer.

4. **Precedent from `Project`**: the `Project` model was defined in the Pydantic
   models PR even though the feature lands in v0.2, for the same reason — the shape
   was known, the definition was cheap, and deferral would create an artificial gap.

---

## Consequences

- `BlockingQuestion` is added to `backend/adjents/agents/models.py` alongside
  `AgentSpec`, `AgentState`, and `Skill` — it is part of the agent state domain.
- A corresponding `BlockingQuestionTable` is created in `backend/adjents/db/tables.py`.
- The `blocking_question` WebSocket message handler (built in the API PR) will read
  and write `BlockingQuestion` records via the DB session.
- The agent loop (built in the scheduler PR) will create `BlockingQuestion` records
  when raising human-decision points and check `answered` to resume.

---

## Alternatives considered

**Defer to agent loop PR**: the agent loop is the first consumer of this entity.
Defining the model there keeps all related code in one PR. Rejected because it
conflates data model ownership (DB layer) with business logic (agent loop), and
because the schema is already fully determined by the WebSocket protocol.

**In-memory only (no persistence)**: store pending questions in a dict in the
`MessageDispatcher`. Rejected: does not survive server restarts, cannot handle
concurrent questions from multiple agents, and breaks the "SQLite is source of truth"
principle established in ARCHITECTURE.md §11.
