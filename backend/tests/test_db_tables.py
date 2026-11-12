"""Tests for db.tables: the 12 tables, their schema against the domain, constraints."""

import types
from typing import Any, Union, get_args, get_origin

import pytest
from pydantic import BaseModel
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.agents.models import AgentSpec, AgentState, BlockingQuestion, Skill
from adjents.db.tables import (
    AgentSpecTable,
    AgentStateTable,
    AgentValidationRecordTable,
    BlockingQuestionTable,
    BusinessContextTable,
    ConversationTable,
    DeliverableTable,
    MemoryTable,
    MessageTable,
    ProjectTable,
    SkillTable,
    ValidationSessionTable,
)
from adjents.deliverables.models import Deliverable
from adjents.generator.models import BusinessContext
from adjents.generator.team_setup import AgentValidationRecord, ValidationSession
from adjents.memory.models import Memory
from adjents.messaging.models import Conversation, Message
from adjents.projects.models import Project

_NOW = "2026-05-20T10:00:00+00:00"

# One complete, valid row per table, as `db/convert` would build it.
_VALID_ROWS: dict[type[SQLModel], dict[str, Any]] = {
    AgentSpecTable: {
        "id": "agent-001",
        "name": "Finance Lead",
        "level": 1,
        "parent_id": "agent-000",
        "domain": "Finance",
        "role_description": "Manages all financial operations.",
        "responsibilities": '["Invoicing"]',
        "skill_ids": '["skill-001"]',
        "escalation_rules": "[]",
        "scheduler_interval_seconds": 900,
        "work_hours": "09:00-18:00",
        "is_paused": True,
        "visual_character": "character_analyst",
        "created_at": _NOW,
    },
    AgentStateTable: {
        "agent_id": "agent-001",
        "status": "paused",
        "current_task_summary": None,
        "meeting_with": "[]",
        "updated_at": _NOW,
    },
    SkillTable: {
        "id": "skill-001",
        "name": "Draft invoice",
        "description": "Generates a PDF invoice.",
        "inputs": '["Client name"]',
        "outputs": "[]",
        "requires_human_review": True,
    },
    MessageTable: {
        "id": "msg-001",
        "from_agent": "agent-001",
        "to_agent": "user",
        "content": "Invoice batch ready.",
        "metadata_json": "{}",
        "parent_message_id": None,
        "created_at": _NOW,
    },
    ConversationTable: {
        "id": "conv-001",
        "participant_agents": '["agent-001"]',
        "message_ids": '["msg-001"]',
        "started_at": _NOW,
    },
    MemoryTable: {
        "id": "mem-001",
        "agent_id": None,
        "content": "Company: Acme Corp.",
        "metadata_json": "{}",
        "created_at": _NOW,
    },
    DeliverableTable: {
        "id": "del-001",
        "agent_id": "agent-001",
        "project_id": None,
        "title": "Daily ops note",
        "file_path": "agent-001/2026-05-20_daily-ops.md",
        "created_at": _NOW,
    },
    ProjectTable: {
        "id": "proj-001",
        "title": "Website redesign",
        "objective": "Build a new public website.",
        "deliverable_descriptions": "[]",
        "deadline": None,
        "lead_agent_id": "agent-001",
        "contributor_agent_ids": "[]",
        "status": "active",
        "created_at": _NOW,
    },
    BlockingQuestionTable: {
        "id": "bq-001",
        "agent_id": "agent-001",
        "question": "Approve the Q3 budget?",
        "context": None,
        "answered": False,
        "answer": None,
        "created_at": _NOW,
        "answered_at": None,
    },
    BusinessContextTable: {
        "id": "bc-001",
        "conversation_id": "conv-001",
        "business_name": None,
        "founder_name": "Alex Chen",
        "language": "fr",
        "core_activity": "Freelance UX designer",
        "legal_status": None,
        "target_clients": "[]",
        "domains_with_human_coverage": "[]",
        "domains_to_staff": '["Finance"]',
        "tasks_to_delegate": "[]",
        "tasks_user_keeps": "[]",
        "financial_goals": None,
        "existing_tools": "[]",
        "autonomy_preference": "Validation required for external comms",
        "work_hours": None,
        "additional_context": None,
        "created_at": _NOW,
    },
    ValidationSessionTable: {
        "id": "vs-001",
        "started_at": _NOW,
        "completed_at": None,
        "skipped": False,
    },
    AgentValidationRecordTable: {
        "id": "avr-001",
        "session_id": "vs-001",
        "root_agent_id": "agent-001",
        "status": "pending",
        "active_agent_id": None,
        "active_conversation_id": None,
        "navigation_stack": "[]",
        "conversation_ids": "[]",
        "visited_agent_ids": "[]",
        "validated_at": None,
    },
}

# Domain model mirrored by each table, and the field names that differ.
_MIRRORS: list[tuple[type[BaseModel], type[SQLModel], dict[str, str]]] = [
    (AgentSpec, AgentSpecTable, {}),
    (AgentState, AgentStateTable, {}),
    (Skill, SkillTable, {}),
    (Message, MessageTable, {"metadata": "metadata_json"}),
    (Conversation, ConversationTable, {}),
    (Memory, MemoryTable, {"metadata": "metadata_json"}),
    (Deliverable, DeliverableTable, {}),
    (Project, ProjectTable, {}),
    (BlockingQuestion, BlockingQuestionTable, {}),
    (BusinessContext, BusinessContextTable, {}),
    (ValidationSession, ValidationSessionTable, {}),
    (AgentValidationRecord, AgentValidationRecordTable, {}),
]


def _required_columns() -> list[tuple[type[SQLModel], str]]:
    """Every `NOT NULL` column that is not the primary key, per table."""
    return [
        (table, column.name)
        for table in _VALID_ROWS
        for column in table.__table__.columns  # type: ignore[attr-defined]
        if not column.nullable and not column.primary_key
    ]


def _is_nullable(annotation: Any) -> bool:
    # `str | None` is a `types.UnionType`, but `Annotated[str, ...] | None` (e.g.
    # `WorkHours | None`) is a `typing.Union`.
    return get_origin(annotation) in (Union, types.UnionType) and type(
        None
    ) in get_args(annotation)


# --- Tables ---


async def test_all_tables_exist(async_session: AsyncSession) -> None:
    """`create_all` creates exactly the 12 tables, one per domain model."""
    conn = await async_session.connection()
    names = await conn.run_sync(lambda sync: inspect(sync).get_table_names())
    assert set(names) == {
        "agent_specs",
        "agent_states",
        "skills",
        "messages",
        "conversations",
        "memories",
        "deliverables",
        "projects",
        "blocking_questions",
        "business_contexts",
        "validation_sessions",
        "agent_validation_records",
    }


# --- Schema drift (ADR 0002) ---


@pytest.mark.parametrize(
    ("domain", "table", "renames"),
    _MIRRORS,
    ids=[table.__name__ for _, table, _ in _MIRRORS],
)
def test_table_columns_mirror_domain_fields(
    domain: type[BaseModel], table: type[SQLModel], renames: dict[str, str]
) -> None:
    """Same fields, same nullability; a field added on one side only fails here."""
    domain_fields = {
        renames.get(name, name): _is_nullable(field.annotation)
        for name, field in domain.model_fields.items()
    }
    columns = {
        column.name: column.nullable
        for column in table.__table__.columns  # type: ignore[attr-defined]
    }
    assert columns == domain_fields


# --- Constraints ---


@pytest.mark.parametrize(
    "table", list(_VALID_ROWS), ids=[table.__name__ for table in _VALID_ROWS]
)
async def test_complete_row_is_stored(
    async_session: AsyncSession, table: type[SQLModel]
) -> None:
    async_session.add(table(**_VALID_ROWS[table]))
    await async_session.commit()


@pytest.mark.parametrize(
    ("table", "column"),
    _required_columns(),
    ids=[f"{table.__name__}.{column}" for table, column in _required_columns()],
)
async def test_omitted_required_column_fails_at_commit(
    async_session: AsyncSession, table: type[SQLModel], column: str
) -> None:
    """Table classes do not validate: an omitted field must not get a silent value."""
    values = {k: v for k, v in _VALID_ROWS[table].items() if k != column}
    async_session.add(table(**values))
    with pytest.raises(IntegrityError, match="NOT NULL"):
        await async_session.commit()
