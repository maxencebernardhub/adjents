"""SQLModel persistence tables — one per domain model (ADR 0002).

Fields of type list[str] and dict[str, Any] are stored as JSON text.
datetime fields are stored as ISO 8601 strings to preserve timezone info.
Conversion to/from domain models is handled exclusively in db.convert.
"""

from sqlmodel import Field, SQLModel


class AgentSpecTable(SQLModel, table=True):
    __tablename__ = "agent_specs"

    id: str = Field(primary_key=True)
    name: str
    level: int
    parent_id: str | None = Field(default=None)
    domain: str | None = Field(default=None)
    role_description: str
    responsibilities: str = Field(default="[]")  # JSON: list[str]
    skill_ids: str = Field(default="[]")  # JSON: list[str]
    escalation_rules: str = Field(default="[]")  # JSON: list[str]
    scheduler_interval_seconds: int
    work_hours: str | None = Field(default=None)
    is_paused: bool = Field(default=False)
    visual_character: str
    created_at: str  # ISO 8601


class AgentStateTable(SQLModel, table=True):
    __tablename__ = "agent_states"

    agent_id: str = Field(primary_key=True)
    status: str  # AgentStatus value
    current_task_summary: str | None = Field(default=None)
    meeting_with: str = Field(default="[]")  # JSON: list[str]
    updated_at: str  # ISO 8601


class SkillTable(SQLModel, table=True):
    __tablename__ = "skills"

    id: str = Field(primary_key=True)
    name: str
    description: str
    inputs: str = Field(default="[]")  # JSON: list[str]
    outputs: str = Field(default="[]")  # JSON: list[str]
    requires_human_review: bool = Field(default=False)


class MessageTable(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(primary_key=True)
    from_agent: str
    to_agent: str
    content: str
    metadata_json: str = Field(default="{}")  # JSON: dict[str, Any]
    parent_message_id: str | None = Field(default=None)
    created_at: str  # ISO 8601


class ConversationTable(SQLModel, table=True):
    __tablename__ = "conversations"

    id: str = Field(primary_key=True)
    participant_agents: str = Field(default="[]")  # JSON: list[str]
    message_ids: str = Field(default="[]")  # JSON: list[str]
    started_at: str  # ISO 8601


class MemoryTable(SQLModel, table=True):
    __tablename__ = "memories"

    id: str = Field(primary_key=True)
    agent_id: str | None = Field(default=None)
    content: str
    metadata_json: str = Field(default="{}")  # JSON: dict[str, Any]
    created_at: str  # ISO 8601


class DeliverableTable(SQLModel, table=True):
    __tablename__ = "deliverables"

    id: str = Field(primary_key=True)
    agent_id: str
    project_id: str | None = Field(default=None)
    title: str
    file_path: str
    created_at: str  # ISO 8601


class ProjectTable(SQLModel, table=True):
    __tablename__ = "projects"

    id: str = Field(primary_key=True)
    title: str
    objective: str
    deliverable_descriptions: str = Field(default="[]")  # JSON: list[str]
    deadline: str | None = Field(default=None)  # ISO 8601
    lead_agent_id: str
    contributor_agent_ids: str = Field(default="[]")  # JSON: list[str]
    status: str  # ProjectStatus value
    created_at: str  # ISO 8601


class BlockingQuestionTable(SQLModel, table=True):
    __tablename__ = "blocking_questions"

    id: str = Field(primary_key=True)
    agent_id: str
    question: str
    context: str | None = Field(default=None)
    answered: bool = Field(default=False)
    answer: str | None = Field(default=None)
    created_at: str  # ISO 8601
    answered_at: str | None = Field(default=None)  # ISO 8601
