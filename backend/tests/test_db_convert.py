"""Tests for db.convert: Pydantic ↔ SQLModel table roundtrips."""

from datetime import UTC, datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.agents.models import (
    AgentSpec,
    AgentState,
    AgentStatus,
    BlockingQuestion,
    Skill,
)
from adjents.db.convert import (
    agent_spec_from_table,
    agent_spec_to_table,
    agent_state_from_table,
    agent_state_to_table,
    blocking_question_from_table,
    blocking_question_to_table,
    business_context_from_table,
    business_context_to_table,
    conversation_from_table,
    conversation_to_table,
    deliverable_from_table,
    deliverable_to_table,
    memory_from_table,
    memory_to_table,
    message_from_table,
    message_to_table,
    project_from_table,
    project_to_table,
    skill_from_table,
    skill_to_table,
)
from adjents.deliverables.models import Deliverable
from adjents.generator.models import BusinessContext
from adjents.memory.models import Memory
from adjents.messaging.models import Conversation, Message
from adjents.projects.models import Project, ProjectStatus

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
        visual_character="accountant_f",
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = agent_spec_to_table(spec)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import AgentSpecTable

    stored = await async_session.get(AgentSpecTable, spec.id)
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
        visual_character="coo_m",
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = agent_spec_to_table(spec)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import AgentSpecTable

    stored = await async_session.get(AgentSpecTable, spec.id)
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

    from adjents.db.tables import AgentStateTable

    stored = await async_session.get(AgentStateTable, state.agent_id)
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

    from adjents.db.tables import AgentStateTable

    stored = await async_session.get(AgentStateTable, state.agent_id)
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

    from adjents.db.tables import SkillTable

    stored = await async_session.get(SkillTable, skill.id)
    assert stored is not None
    restored = skill_from_table(stored)
    assert restored == skill


# --- Message ---


async def test_message_roundtrip(async_session: AsyncSession) -> None:
    msg = Message(
        id="msg-001",
        from_agent="agent-001",
        to_agent="user",
        content="Invoice batch ready for review.",
        metadata={"task_id": "task-042"},
        parent_message_id=None,
        created_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
    )
    row = message_to_table(msg)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import MessageTable

    stored = await async_session.get(MessageTable, msg.id)
    assert stored is not None
    restored = message_from_table(stored)
    assert restored == msg


async def test_message_with_parent_roundtrip(async_session: AsyncSession) -> None:
    parent = Message(
        id="msg-001",
        from_agent="user",
        to_agent="agent-001",
        content="Please prioritise the Q2 report.",
        metadata={},
        parent_message_id=None,
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=UTC),
    )
    child = Message(
        id="msg-002",
        from_agent="agent-001",
        to_agent="user",
        content="Understood. Prioritising Q2 report.",
        metadata={},
        parent_message_id="msg-001",
        created_at=datetime(2026, 5, 20, 9, 1, tzinfo=UTC),
    )
    async_session.add(message_to_table(parent))
    async_session.add(message_to_table(child))
    await async_session.commit()

    from adjents.db.tables import MessageTable

    stored = await async_session.get(MessageTable, "msg-002")
    assert stored is not None
    restored = message_from_table(stored)
    assert restored.parent_message_id == "msg-001"


# --- Conversation ---


async def test_conversation_roundtrip(async_session: AsyncSession) -> None:
    conv = Conversation(
        id="conv-001",
        participant_agents=["agent-001", "agent-002"],
        message_ids=["msg-001", "msg-002", "msg-003"],
        started_at=datetime(2026, 5, 20, 9, 0, tzinfo=UTC),
    )
    row = conversation_to_table(conv)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import ConversationTable

    stored = await async_session.get(ConversationTable, conv.id)
    assert stored is not None
    restored = conversation_from_table(stored)
    assert restored == conv
    assert restored.message_ids == ["msg-001", "msg-002", "msg-003"]


# --- Memory ---


async def test_memory_agent_roundtrip(async_session: AsyncSession) -> None:
    mem = Memory(
        id="mem-001",
        agent_id="agent-001",
        content="Client Acme prefers invoices on the 1st.",
        metadata={"source": "onboarding"},
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = memory_to_table(mem)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import MemoryTable

    stored = await async_session.get(MemoryTable, mem.id)
    assert stored is not None
    restored = memory_from_table(stored)
    assert restored == mem


async def test_memory_global_kb_roundtrip(async_session: AsyncSession) -> None:
    mem = Memory(
        id="mem-002",
        agent_id=None,
        content="Company: Acme Corp. Founded 2018.",
        metadata={"source": "generator_agent"},
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = memory_to_table(mem)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import MemoryTable

    stored = await async_session.get(MemoryTable, mem.id)
    assert stored is not None
    restored = memory_from_table(stored)
    assert restored.agent_id is None


# --- Deliverable ---


async def test_deliverable_roundtrip(async_session: AsyncSession) -> None:
    d = Deliverable(
        id="del-001",
        agent_id="agent-001",
        project_id="proj-001",
        title="Q1 Invoice Batch",
        file_path="agent-001/2026-05-20_q1-invoice-batch.md",
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = deliverable_to_table(d)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import DeliverableTable

    stored = await async_session.get(DeliverableTable, d.id)
    assert stored is not None
    restored = deliverable_from_table(stored)
    assert restored == d


async def test_deliverable_no_project_roundtrip(async_session: AsyncSession) -> None:
    d = Deliverable(
        id="del-002",
        agent_id="agent-001",
        project_id=None,
        title="Daily ops note",
        file_path="agent-001/2026-05-20_daily-ops.md",
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = deliverable_to_table(d)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import DeliverableTable

    stored = await async_session.get(DeliverableTable, d.id)
    assert stored is not None
    restored = deliverable_from_table(stored)
    assert restored.project_id is None


# --- Project ---


async def test_project_roundtrip(async_session: AsyncSession) -> None:
    proj = Project(
        id="proj-001",
        title="Website redesign",
        objective="Build new public website.",
        deliverable_descriptions=["Live website", "Copy doc"],
        deadline=datetime(2026, 8, 1, tzinfo=UTC),
        lead_agent_id="agent-003",
        contributor_agent_ids=["agent-004", "agent-005"],
        status=ProjectStatus.ACTIVE,
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = project_to_table(proj)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import ProjectTable

    stored = await async_session.get(ProjectTable, proj.id)
    assert stored is not None
    restored = project_from_table(stored)
    assert restored == proj


async def test_project_no_deadline_roundtrip(async_session: AsyncSession) -> None:
    proj = Project(
        id="proj-002",
        title="Ongoing ops",
        objective="Continuous operations.",
        deliverable_descriptions=[],
        deadline=None,
        lead_agent_id="agent-001",
        contributor_agent_ids=[],
        status=ProjectStatus.ACTIVE,
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = project_to_table(proj)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import ProjectTable

    stored = await async_session.get(ProjectTable, proj.id)
    assert stored is not None
    restored = project_from_table(stored)
    assert restored.deadline is None


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

    from adjents.db.tables import BlockingQuestionTable

    stored = await async_session.get(BlockingQuestionTable, bq.id)
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

    from adjents.db.tables import BlockingQuestionTable

    stored = await async_session.get(BlockingQuestionTable, bq.id)
    assert stored is not None
    restored = blocking_question_from_table(stored)
    assert restored.answered is True
    assert restored.answered_at == bq.answered_at


# --- BusinessContext ---


async def test_business_context_roundtrip(async_session: AsyncSession) -> None:
    bc = BusinessContext(
        id="bc-001",
        conversation_id="conv-001",
        business_name="Luminescence",
        founder_name="Alex Chen",
        language="fr",
        core_activity="Freelance UX designer — mobile apps",
        legal_status="Auto-entrepreneur",
        target_clients=["Startups", "PMEs"],
        domains_with_human_coverage=[],
        domains_to_staff=["Finance", "Sales"],
        tasks_to_delegate=["Invoicing", "Prospecting"],
        tasks_user_keeps=["UX design"],
        financial_goals="2000€ net/month",
        existing_tools=["Gmail", "LinkedIn"],
        autonomy_preference="Validation required for external communications",
        work_hours="18:00-23:00",
        additional_context=None,
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    row = business_context_to_table(bc)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import BusinessContextTable

    stored = await async_session.get(BusinessContextTable, bc.id)
    assert stored is not None
    restored = business_context_from_table(stored)
    assert restored == bc


async def test_business_context_nullable_fields_roundtrip(
    async_session: AsyncSession,
) -> None:
    bc = BusinessContext(
        id="bc-002",
        conversation_id="conv-002",
        business_name=None,
        founder_name="Jordan Lee",
        language="en",
        core_activity="Freelance copywriter",
        legal_status=None,
        target_clients=[],
        domains_with_human_coverage=[],
        domains_to_staff=["Marketing"],
        tasks_to_delegate=[],
        tasks_user_keeps=[],
        financial_goals=None,
        existing_tools=[],
        autonomy_preference="Full autonomy",
        work_hours=None,
        additional_context=None,
        created_at=datetime(2026, 5, 21, tzinfo=UTC),
    )
    row = business_context_to_table(bc)
    async_session.add(row)
    await async_session.commit()

    from adjents.db.tables import BusinessContextTable

    stored = await async_session.get(BusinessContextTable, bc.id)
    assert stored is not None
    restored = business_context_from_table(stored)
    assert restored.business_name is None
    assert restored.legal_status is None
    assert restored.work_hours is None
    assert restored.existing_tools == []
