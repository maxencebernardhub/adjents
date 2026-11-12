"""Tests for db.convert.agents: agent domain models ↔ SQLModel table roundtrips."""

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.agents.models import (
    AgentSpec,
    AgentState,
    AgentStatus,
    BlockingQuestion,
    Skill,
)
from adjents.db.convert.agents import (
    agent_spec_from_table,
    agent_spec_to_table,
    agent_state_from_table,
    agent_state_to_table,
    blocking_question_from_table,
    blocking_question_to_table,
    skill_from_table,
    skill_to_table,
)
from adjents.db.tables import (
    AgentSpecTable,
    AgentStateTable,
    BlockingQuestionTable,
    SkillTable,
)

# --- AgentSpec ---


async def test_agent_spec_roundtrip(async_session: AsyncSession) -> None:
    spec = AgentSpec(
        id="agent-001",
        name="Finance Lead",
        level=1,
        parent_id="agent-000",
        domain="Finance",
        role_description="Manages all financial operations.",
        responsibilities=["Invoicing", "Cash flow monitoring"],
        skill_ids=["skill-001", "skill-002"],
        escalation_rules=["Escalate if overdue > 30 days"],
        scheduler_interval_seconds=900,
        work_hours="09:00-18:00",
        is_paused=False,
        visual_character="character_analyst",
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = agent_spec_to_table(spec)
    async_session.add(row)
    await async_session.commit()

    stored = await async_session.get(AgentSpecTable, spec.id, populate_existing=True)
    assert stored is not None
    restored = agent_spec_from_table(stored)
    assert restored == spec


async def test_agent_spec_nullable_fields_roundtrip(
    async_session: AsyncSession,
) -> None:
    spec = AgentSpec(
        id="agent-000",
        name="COO",
        level=0,
        parent_id=None,
        domain=None,
        role_description="Chief of Staff.",
        responsibilities=[],
        skill_ids=[],
        escalation_rules=[],
        scheduler_interval_seconds=300,
        work_hours=None,
        is_paused=False,
        visual_character="character_suit",
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = agent_spec_to_table(spec)
    async_session.add(row)
    await async_session.commit()

    stored = await async_session.get(AgentSpecTable, spec.id, populate_existing=True)
    assert stored is not None
    restored = agent_spec_from_table(stored)
    assert restored.parent_id is None
    assert restored.domain is None
    assert restored.work_hours is None


# --- AgentState ---


async def test_agent_state_roundtrip(async_session: AsyncSession) -> None:
    state = AgentState(
        agent_id="agent-001",
        status=AgentStatus.WORKING,
        current_task_summary="Drafting Q1 invoices.",
        meeting_with=[],
        updated_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
    )
    row = agent_state_to_table(state)
    async_session.add(row)
    await async_session.commit()

    stored = await async_session.get(
        AgentStateTable, state.agent_id, populate_existing=True
    )
    assert stored is not None
    restored = agent_state_from_table(stored)
    assert restored == state


async def test_agent_state_meeting_with_roundtrip(async_session: AsyncSession) -> None:
    state = AgentState(
        agent_id="agent-002",
        status=AgentStatus.IN_MEETING_1ON1,
        current_task_summary=None,
        meeting_with=["agent-001", "agent-003"],
        updated_at=datetime(2026, 5, 20, 14, 0, tzinfo=UTC),
    )
    row = agent_state_to_table(state)
    async_session.add(row)
    await async_session.commit()

    stored = await async_session.get(
        AgentStateTable, state.agent_id, populate_existing=True
    )
    assert stored is not None
    restored = agent_state_from_table(stored)
    assert restored.meeting_with == ["agent-001", "agent-003"]


# --- Skill ---


async def test_skill_roundtrip(async_session: AsyncSession) -> None:
    skill = Skill(
        id="skill-001",
        name="Draft invoice",
        description="Generates a PDF invoice from template.",
        inputs=["Client name", "Amount"],
        outputs=["Invoice PDF path"],
        requires_human_review=True,
    )
    row = skill_to_table(skill)
    async_session.add(row)
    await async_session.commit()

    stored = await async_session.get(SkillTable, skill.id, populate_existing=True)
    assert stored is not None
    restored = skill_from_table(stored)
    assert restored == skill


# --- Malformed rows: the roundtrip reads must reach SQLite ---


async def _corrupt(session: AsyncSession, statement: str) -> None:
    """Change a committed row behind the ORM's back, as another writer would."""
    conn = await session.connection()
    await conn.execute(text(statement))
    await session.commit()


async def test_skill_from_table_rejects_corrupt_json_stored_in_sqlite(
    async_session: AsyncSession,
) -> None:
    """Guards the roundtrip read pattern: a read served from the session, not from
    SQLite, would return the row as added and this test would not raise."""
    skill = Skill(
        id="skill-001",
        name="Draft invoice",
        description="Generates a PDF invoice from template.",
        inputs=["Client name"],
        outputs=[],
        requires_human_review=False,
    )
    row = skill_to_table(skill)
    async_session.add(row)
    await async_session.commit()
    await _corrupt(async_session, "UPDATE skills SET inputs = 'not json'")

    stored = await async_session.get(SkillTable, skill.id, populate_existing=True)
    assert stored is not None
    with pytest.raises(json.JSONDecodeError):
        skill_from_table(stored)


async def test_agent_state_from_table_rejects_unknown_status_stored_in_sqlite(
    async_session: AsyncSession,
) -> None:
    state = AgentState(
        agent_id="agent-001",
        status=AgentStatus.PAUSED,
        current_task_summary=None,
        meeting_with=[],
        updated_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
    )
    row = agent_state_to_table(state)
    async_session.add(row)
    await async_session.commit()
    await _corrupt(async_session, "UPDATE agent_states SET status = 'flying'")

    stored = await async_session.get(
        AgentStateTable, state.agent_id, populate_existing=True
    )
    assert stored is not None
    with pytest.raises(ValueError, match="flying"):
        agent_state_from_table(stored)


# --- BlockingQuestion ---


async def test_blocking_question_roundtrip(async_session: AsyncSession) -> None:
    bq = BlockingQuestion(
        id="bq-001",
        agent_id="agent-001",
        question="Send overdue reminder to Acme Corp?",
        context="Invoice #42 is 15 days overdue.",
        answered=False,
        answer=None,
        created_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
        answered_at=None,
    )
    row = blocking_question_to_table(bq)
    async_session.add(row)
    await async_session.commit()

    stored = await async_session.get(
        BlockingQuestionTable, bq.id, populate_existing=True
    )
    assert stored is not None
    restored = blocking_question_from_table(stored)
    assert restored == bq


async def test_blocking_question_answered_roundtrip(
    async_session: AsyncSession,
) -> None:
    bq = BlockingQuestion(
        id="bq-002",
        agent_id="agent-001",
        question="Approve Q3 budget?",
        context=None,
        answered=True,
        answer="Yes, approved.",
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=UTC),
        answered_at=datetime(2026, 5, 20, 9, 30, tzinfo=UTC),
    )
    row = blocking_question_to_table(bq)
    async_session.add(row)
    await async_session.commit()

    stored = await async_session.get(
        BlockingQuestionTable, bq.id, populate_existing=True
    )
    assert stored is not None
    restored = blocking_question_from_table(stored)
    assert restored.answered is True
    assert restored.answered_at == bq.answered_at
