"""SQLModel persistence tables — one per domain model (ADR 0002).

The domain models stay plain Pydantic classes; these `table=True` classes carry the
persistence details instead: primary keys, table names, and column types SQLite
can store. `list[str]` and `dict[str, Any]` fields are stored as JSON text, and
`datetime` fields as ISO 8601 strings, which keep the UTC offset that SQLite's
`DATETIME` columns would drop. `metadata` is a reserved attribute name on
SQLAlchemy declarative classes, hence the `metadata_json` columns.

Table classes do not validate, not even at construction: only SQL constraints
(`NOT NULL`, primary key) apply, at commit. Validation happens in the domain
models. No column has a default value: a field left out of a constructor is
reported by mypy, and fails at commit with `NOT NULL` unless its column is
nullable. Columns are nullable exactly where the domain field accepts `None`.

Place in the flow: the `db/convert/` package builds rows from domain models and
turns rows back into domain models. The orchestrators add rows to their
`AsyncSession` (`generator/interview.py`, `generator/org_generation.py`,
`generator/team_setup.py`, `agents/reconfiguration.py`); all but org generation
also query these classes with `select(...)` and update loaded rows in place, and
team setup and reconfiguration build some rows directly. Importing this module
registers every table in `SQLModel.metadata`, which `create_all` needs; `db/engine.py`
imports it.

Entry points: the 12 `*Table` classes.

Related ADRs: 0002 (domain models vs tables), 0003 (async SQLite sessions), 0004
(BlockingQuestion).
"""

from sqlmodel import Field, SQLModel


class AgentSpecTable(SQLModel, table=True):
    """Row of `agent_specs`, mirroring `AgentSpec` (`agents/models.py`)."""

    __tablename__ = "agent_specs"

    id: str = Field(primary_key=True)
    name: str
    level: int
    parent_id: str | None
    domain: str | None
    role_description: str
    responsibilities: str  # JSON: list[str]
    skill_ids: str  # JSON: list[str]
    escalation_rules: str  # JSON: list[str]
    scheduler_interval_seconds: int
    work_hours: str | None
    is_paused: bool
    visual_character: str
    created_at: str  # ISO 8601


class AgentStateTable(SQLModel, table=True):
    """Row of `agent_states`, mirroring `AgentState`; keyed by the agent's id."""

    __tablename__ = "agent_states"

    agent_id: str = Field(primary_key=True)
    status: str  # AgentStatus value
    current_task_summary: str | None
    meeting_with: str  # JSON: list[str]
    updated_at: str  # ISO 8601


class SkillTable(SQLModel, table=True):
    """Row of `skills`, mirroring `Skill` (`agents/models.py`)."""

    __tablename__ = "skills"

    id: str = Field(primary_key=True)
    name: str
    description: str
    inputs: str  # JSON: list[str]
    outputs: str  # JSON: list[str]
    requires_human_review: bool


class MessageTable(SQLModel, table=True):
    """Row of `messages`, mirroring `Message`; `metadata` is `metadata_json`."""

    __tablename__ = "messages"

    id: str = Field(primary_key=True)
    from_agent: str
    to_agent: str
    content: str
    metadata_json: str  # JSON: dict[str, Any]
    parent_message_id: str | None
    created_at: str  # ISO 8601


class ConversationTable(SQLModel, table=True):
    """Row of `conversations`, mirroring `Conversation` (`messaging/models.py`)."""

    __tablename__ = "conversations"

    id: str = Field(primary_key=True)
    participant_agents: str  # JSON: list[str]
    message_ids: str  # JSON: list[str]
    started_at: str  # ISO 8601


class MemoryTable(SQLModel, table=True):
    """Row of `memories`, mirroring `Memory`; `metadata` is `metadata_json`."""

    __tablename__ = "memories"

    id: str = Field(primary_key=True)
    agent_id: str | None
    content: str
    metadata_json: str  # JSON: dict[str, Any]
    created_at: str  # ISO 8601


class DeliverableTable(SQLModel, table=True):
    """Row of `deliverables`, mirroring `Deliverable` (`deliverables/models.py`)."""

    __tablename__ = "deliverables"

    id: str = Field(primary_key=True)
    agent_id: str
    project_id: str | None
    title: str
    file_path: str
    created_at: str  # ISO 8601


class ProjectTable(SQLModel, table=True):
    """Row of `projects`, mirroring `Project` (`projects/models.py`)."""

    __tablename__ = "projects"

    id: str = Field(primary_key=True)
    title: str
    objective: str
    deliverable_descriptions: str  # JSON: list[str]
    deadline: str | None  # ISO 8601
    lead_agent_id: str
    contributor_agent_ids: str  # JSON: list[str]
    status: str  # ProjectStatus value
    created_at: str  # ISO 8601


class BlockingQuestionTable(SQLModel, table=True):
    """Row of `blocking_questions`, mirroring `BlockingQuestion` (ADR 0004)."""

    __tablename__ = "blocking_questions"

    id: str = Field(primary_key=True)
    agent_id: str
    question: str
    context: str | None
    answered: bool
    answer: str | None
    created_at: str  # ISO 8601
    answered_at: str | None  # ISO 8601


class BusinessContextTable(SQLModel, table=True):
    """Row of `business_contexts`, mirroring `BusinessContext`."""

    __tablename__ = "business_contexts"

    id: str = Field(primary_key=True)
    conversation_id: str
    business_name: str | None
    founder_name: str
    language: str
    core_activity: str
    legal_status: str | None
    target_clients: str  # JSON: list[str]
    domains_with_human_coverage: str  # JSON: list[str]
    domains_to_staff: str  # JSON: list[str]
    tasks_to_delegate: str  # JSON: list[str]
    tasks_user_keeps: str  # JSON: list[str]
    financial_goals: str | None
    existing_tools: str  # JSON: list[str]
    autonomy_preference: str
    work_hours: str | None
    additional_context: str | None
    created_at: str  # ISO 8601


class ValidationSessionTable(SQLModel, table=True):
    """Row of `validation_sessions`, mirroring `ValidationSession` (team setup)."""

    __tablename__ = "validation_sessions"

    id: str = Field(primary_key=True)
    started_at: str  # ISO 8601
    completed_at: str | None  # ISO 8601
    skipped: bool


class AgentValidationRecordTable(SQLModel, table=True):
    """Row of `agent_validation_records`, mirroring `AgentValidationRecord`."""

    __tablename__ = "agent_validation_records"

    id: str = Field(primary_key=True)
    session_id: str
    root_agent_id: str
    status: str  # AgentValidationStatus value
    active_agent_id: str | None
    active_conversation_id: str | None
    navigation_stack: str  # JSON: list[str]
    conversation_ids: str  # JSON: list[str]
    visited_agent_ids: str  # JSON: list[str]
    validated_at: str | None  # ISO 8601
