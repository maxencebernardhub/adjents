"""Tests for db.convert.deliverables: Deliverable ↔ DeliverableTable roundtrips."""

from datetime import UTC, datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.db.convert.deliverables import (
    deliverable_from_table,
    deliverable_to_table,
)
from adjents.db.tables import DeliverableTable
from adjents.deliverables.models import Deliverable


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

    stored = await async_session.get(DeliverableTable, d.id)
    assert stored is not None
    restored = deliverable_from_table(stored)
    assert restored.project_id is None
