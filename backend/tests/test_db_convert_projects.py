"""Tests for db.convert.projects: Project ↔ ProjectTable roundtrips."""

from datetime import UTC, datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.db.convert.projects import project_from_table, project_to_table
from adjents.db.tables import ProjectTable
from adjents.projects.models import Project, ProjectStatus


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

    stored = await async_session.get(ProjectTable, proj.id)
    assert stored is not None
    restored = project_from_table(stored)
    assert restored.deadline is None
