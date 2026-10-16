"""Shared async session fixture for database tests."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import adjents.db.tables  # noqa: F401  # registers tables in SQLModel.metadata
from adjents.agents.models import AgentSpec, AgentState, AgentStatus, Skill
from adjents.db.convert import (
    agent_spec_to_table,
    agent_state_to_table,
    skill_to_table,
)
from adjents.prompts.loader import PromptLoader


@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
    await engine.dispose()


@pytest.fixture
def stub_prompt_loader() -> PromptLoader:
    loader = MagicMock(spec=PromptLoader)
    stub = MagicMock()
    stub.content = "You are a helpful agent."
    loader.get.return_value = stub
    return loader


@pytest_asyncio.fixture
async def mini_org(async_session: AsyncSession) -> dict[str, str]:
    """Three-agent org: COO → N-1 Finance Lead → N-2 Invoicing Specialist.

    Each has one skill. All AgentState.status = PAUSED.
    Returns {"coo_id": ..., "n1_id": ..., "n2_id": ...}.
    """
    coo_id = str(uuid4())
    n1_id = str(uuid4())
    n2_id = str(uuid4())
    coo_skill_id = str(uuid4())
    n1_skill_id = str(uuid4())
    n2_skill_id = str(uuid4())

    specs = [
        AgentSpec(
            id=coo_id,
            name="Jordan",
            level=0,
            parent_id=None,
            domain=None,
            role_description="COO — coordinates all N-1 leads.",
            responsibilities=["Coordinate N-1 leads"],
            skill_ids=[coo_skill_id],
            escalation_rules=[],
            scheduler_interval_seconds=900,
            work_hours="09:00-18:00",
            visual_character="character_suit",
            is_paused=True,
            created_at=datetime.now(UTC),
        ),
        AgentSpec(
            id=n1_id,
            name="Alex",
            level=1,
            parent_id=coo_id,
            domain="Finance",
            role_description="Finance Lead.",
            responsibilities=["Manage invoicing"],
            skill_ids=[n1_skill_id],
            escalation_rules=[],
            scheduler_interval_seconds=1800,
            work_hours="09:00-18:00",
            visual_character="character_analyst",
            is_paused=True,
            created_at=datetime.now(UTC),
        ),
        AgentSpec(
            id=n2_id,
            name="Sam",
            level=2,
            parent_id=n1_id,
            domain="Finance",
            role_description="Invoicing Specialist.",
            responsibilities=["Track invoices"],
            skill_ids=[n2_skill_id],
            escalation_rules=[],
            scheduler_interval_seconds=1800,
            work_hours="09:00-18:00",
            visual_character="character_analyst",
            is_paused=True,
            created_at=datetime.now(UTC),
        ),
    ]
    skills = [
        Skill(
            id=coo_skill_id,
            name="Synthesis",
            description="Aggregates reports.",
            inputs=[],
            outputs=[],
            requires_human_review=False,
        ),
        Skill(
            id=n1_skill_id,
            name="Invoicing",
            description="Tracks invoices.",
            inputs=[],
            outputs=[],
            requires_human_review=True,
        ),
        Skill(
            id=n2_skill_id,
            name="Tracking",
            description="Tracks payment status.",
            inputs=[],
            outputs=[],
            requires_human_review=False,
        ),
    ]
    states = [
        AgentState(
            agent_id=coo_id,
            status=AgentStatus.PAUSED,
            current_task_summary=None,
            meeting_with=[],
            updated_at=datetime.now(UTC),
        ),
        AgentState(
            agent_id=n1_id,
            status=AgentStatus.PAUSED,
            current_task_summary=None,
            meeting_with=[],
            updated_at=datetime.now(UTC),
        ),
        AgentState(
            agent_id=n2_id,
            status=AgentStatus.PAUSED,
            current_task_summary=None,
            meeting_with=[],
            updated_at=datetime.now(UTC),
        ),
    ]
    for skill in skills:
        async_session.add(skill_to_table(skill))
    for spec in specs:
        async_session.add(agent_spec_to_table(spec))
    for state in states:
        async_session.add(agent_state_to_table(state))
    await async_session.commit()
    return {"coo_id": coo_id, "n1_id": n1_id, "n2_id": n2_id}


@pytest_asyncio.fixture
async def coo_only_org(async_session: AsyncSession) -> dict[str, str]:
    """Single-agent org: COO only (no N-1 agents).

    Returns {"coo_id": ...}.
    """
    coo_id = str(uuid4())
    coo_skill_id = str(uuid4())

    spec = AgentSpec(
        id=coo_id,
        name="Jordan",
        level=0,
        parent_id=None,
        domain=None,
        role_description="COO — coordinates all operations.",
        responsibilities=["Run the company"],
        skill_ids=[coo_skill_id],
        escalation_rules=[],
        scheduler_interval_seconds=900,
        work_hours="09:00-18:00",
        visual_character="character_suit",
        is_paused=True,
        created_at=datetime.now(UTC),
    )
    skill = Skill(
        id=coo_skill_id,
        name="Synthesis",
        description="Aggregates reports.",
        inputs=[],
        outputs=[],
        requires_human_review=False,
    )
    state = AgentState(
        agent_id=coo_id,
        status=AgentStatus.PAUSED,
        current_task_summary=None,
        meeting_with=[],
        updated_at=datetime.now(UTC),
    )
    async_session.add(skill_to_table(skill))
    async_session.add(agent_spec_to_table(spec))
    async_session.add(agent_state_to_table(state))
    await async_session.commit()
    return {"coo_id": coo_id}
