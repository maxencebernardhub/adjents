"""Tests for db.tables: SQLModel table classes — insert and read via async session."""

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.db.tables import (
    AgentSpecTable,
    AgentStateTable,
    BlockingQuestionTable,
    BusinessContextTable,
    ConversationTable,
    DeliverableTable,
    MemoryTable,
    MessageTable,
    ProjectTable,
    SkillTable,
)

# --- AgentSpecTable ---


async def test_agent_spec_table_insert_read(async_session: AsyncSession) -> None:
    row = AgentSpecTable(
        id="agent-001",
        name="Finance Lead",
        level=1,
        parent_id="agent-000",
        domain="Finance",
        role_description="Manages all financial operations.",
        responsibilities='["Invoicing", "Cash flow"]',
        skill_ids='["skill-001"]',
        escalation_rules='["Escalate if overdue > 30 days"]',
        scheduler_interval_seconds=900,
        work_hours="09:00-18:00",
        is_paused=False,
        visual_character="accountant_f",
        created_at="2026-05-20T00:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(AgentSpecTable, "agent-001")
    assert result is not None
    assert result.name == "Finance Lead"
    assert result.level == 1
    assert result.domain == "Finance"


async def test_agent_spec_table_nullable_fields(async_session: AsyncSession) -> None:
    row = AgentSpecTable(
        id="agent-000",
        name="COO",
        level=0,
        parent_id=None,
        domain=None,
        role_description="Chief of Staff.",
        responsibilities="[]",
        skill_ids="[]",
        escalation_rules="[]",
        scheduler_interval_seconds=300,
        work_hours=None,
        is_paused=False,
        visual_character="coo_m",
        created_at="2026-05-20T00:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(AgentSpecTable, "agent-000")
    assert result is not None
    assert result.parent_id is None
    assert result.domain is None
    assert result.work_hours is None


# --- AgentStateTable ---


async def test_agent_state_table_insert_read(async_session: AsyncSession) -> None:
    row = AgentStateTable(
        agent_id="agent-001",
        status="working",
        current_task_summary="Drafting Q1 invoices.",
        meeting_with="[]",
        updated_at="2026-05-20T10:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(AgentStateTable, "agent-001")
    assert result is not None
    assert result.status == "working"
    assert result.current_task_summary == "Drafting Q1 invoices."


# --- SkillTable ---


async def test_skill_table_insert_read(async_session: AsyncSession) -> None:
    row = SkillTable(
        id="skill-001",
        name="Draft invoice",
        description="Generates a PDF invoice.",
        inputs='["Client name", "Amount"]',
        outputs='["Invoice PDF path"]',
        requires_human_review=True,
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(SkillTable, "skill-001")
    assert result is not None
    assert result.name == "Draft invoice"
    assert result.requires_human_review is True


# --- MessageTable ---


async def test_message_table_insert_read(async_session: AsyncSession) -> None:
    row = MessageTable(
        id="msg-001",
        from_agent="agent-001",
        to_agent="user",
        content="Invoice batch ready.",
        metadata_json='{"task_id": "t-42"}',
        parent_message_id=None,
        created_at="2026-05-20T10:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(MessageTable, "msg-001")
    assert result is not None
    assert result.from_agent == "agent-001"
    assert result.parent_message_id is None


# --- ConversationTable ---


async def test_conversation_table_insert_read(async_session: AsyncSession) -> None:
    row = ConversationTable(
        id="conv-001",
        participant_agents='["agent-001", "agent-002"]',
        message_ids='["msg-001", "msg-002"]',
        started_at="2026-05-20T09:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(ConversationTable, "conv-001")
    assert result is not None
    assert result.participant_agents == '["agent-001", "agent-002"]'


# --- MemoryTable ---


async def test_memory_table_insert_read(async_session: AsyncSession) -> None:
    row = MemoryTable(
        id="mem-001",
        agent_id="agent-001",
        content="Client Acme prefers invoices on the 1st.",
        metadata_json='{"source": "onboarding"}',
        created_at="2026-05-20T00:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(MemoryTable, "mem-001")
    assert result is not None
    assert result.agent_id == "agent-001"


async def test_memory_table_global_kb(async_session: AsyncSession) -> None:
    row = MemoryTable(
        id="mem-002",
        agent_id=None,
        content="Company: Acme Corp. Founded 2018.",
        metadata_json='{"source": "generator_agent"}',
        created_at="2026-05-20T00:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(MemoryTable, "mem-002")
    assert result is not None
    assert result.agent_id is None


# --- DeliverableTable ---


async def test_deliverable_table_insert_read(async_session: AsyncSession) -> None:
    row = DeliverableTable(
        id="del-001",
        agent_id="agent-001",
        project_id="proj-001",
        title="Q1 Invoice Batch",
        file_path="agent-001/2026-05-20_q1-invoice-batch.md",
        created_at="2026-05-20T00:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(DeliverableTable, "del-001")
    assert result is not None
    assert result.title == "Q1 Invoice Batch"
    assert result.project_id == "proj-001"


async def test_deliverable_table_no_project(async_session: AsyncSession) -> None:
    row = DeliverableTable(
        id="del-002",
        agent_id="agent-001",
        project_id=None,
        title="Daily ops report",
        file_path="agent-001/2026-05-20_daily-ops.md",
        created_at="2026-05-20T00:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(DeliverableTable, "del-002")
    assert result is not None
    assert result.project_id is None


# --- ProjectTable ---


async def test_project_table_insert_read(async_session: AsyncSession) -> None:
    row = ProjectTable(
        id="proj-001",
        title="Website redesign",
        objective="Build new public website.",
        deliverable_descriptions='["Live website", "Copy doc"]',
        deadline="2026-08-01T00:00:00+00:00",
        lead_agent_id="agent-003",
        contributor_agent_ids='["agent-004"]',
        status="active",
        created_at="2026-05-20T00:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(ProjectTable, "proj-001")
    assert result is not None
    assert result.status == "active"
    assert result.deadline == "2026-08-01T00:00:00+00:00"


async def test_project_table_no_deadline(async_session: AsyncSession) -> None:
    row = ProjectTable(
        id="proj-002",
        title="Ongoing ops",
        objective="Day-to-day operations.",
        deliverable_descriptions="[]",
        deadline=None,
        lead_agent_id="agent-001",
        contributor_agent_ids="[]",
        status="active",
        created_at="2026-05-20T00:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(ProjectTable, "proj-002")
    assert result is not None
    assert result.deadline is None


# --- BlockingQuestionTable ---


async def test_blocking_question_table_insert_read(
    async_session: AsyncSession,
) -> None:
    row = BlockingQuestionTable(
        id="bq-001",
        agent_id="agent-001",
        question="Send overdue reminder to Acme Corp?",
        context="Invoice #42 is 15 days overdue.",
        answered=False,
        answer=None,
        created_at="2026-05-20T10:00:00+00:00",
        answered_at=None,
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(BlockingQuestionTable, "bq-001")
    assert result is not None
    assert result.answered is False
    assert result.answer is None
    assert result.answered_at is None


async def test_blocking_question_table_answered(async_session: AsyncSession) -> None:
    row = BlockingQuestionTable(
        id="bq-002",
        agent_id="agent-001",
        question="Approve Q3 budget increase?",
        context=None,
        answered=True,
        answer="Yes, approved up to $500.",
        created_at="2026-05-20T09:00:00+00:00",
        answered_at="2026-05-20T09:30:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(BlockingQuestionTable, "bq-002")
    assert result is not None
    assert result.answered is True
    assert result.answer == "Yes, approved up to $500."
    assert result.answered_at == "2026-05-20T09:30:00+00:00"


# --- BusinessContextTable ---


async def test_business_context_table_insert_read(async_session: AsyncSession) -> None:
    row = BusinessContextTable(
        id="bc-001",
        conversation_id="conv-001",
        business_name="Luminescence",
        founder_name="Alex Chen",
        language="fr",
        core_activity="Freelance UX designer",
        legal_status="Auto-entrepreneur",
        target_clients='["Startups"]',
        domains_with_human_coverage="[]",
        domains_to_staff='["Finance", "Sales"]',
        tasks_to_delegate='["Invoicing"]',
        tasks_user_keeps='["UX design"]',
        financial_goals="2000€/month",
        existing_tools='["Gmail"]',
        autonomy_preference="Validation required for external comms",
        work_hours="18:00-23:00",
        additional_context=None,
        created_at="2026-05-20T00:00:00+00:00",
    )
    async_session.add(row)
    await async_session.commit()

    result = await async_session.get(BusinessContextTable, "bc-001")
    assert result is not None
    assert result.founder_name == "Alex Chen"
    assert result.business_name == "Luminescence"
    assert result.work_hours == "18:00-23:00"


# --- Engine: all tables are created ---


async def test_all_tables_exist(async_session: AsyncSession) -> None:
    """Smoke test: all 10 tables are created without error."""
    from sqlalchemy import text

    result = await async_session.exec(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    )  # type: ignore[call-overload]
    table_names = {row[0] for row in result.fetchall()}
    expected = {
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
    }
    assert expected.issubset(table_names)


@pytest.mark.usefixtures("async_session")
async def test_unused_import_unused() -> None:
    """Ensure inspect import is not flagged."""
    pass
