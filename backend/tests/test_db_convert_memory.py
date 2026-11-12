"""Tests for db.convert.memory: Memory ↔ MemoryTable roundtrips."""

from datetime import UTC, datetime

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.db.convert.memory import memory_from_table, memory_to_table
from adjents.db.tables import MemoryTable
from adjents.memory.models import Memory


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

    stored = await async_session.get(MemoryTable, mem.id, populate_existing=True)
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

    stored = await async_session.get(MemoryTable, mem.id, populate_existing=True)
    assert stored is not None
    restored = memory_from_table(stored)
    assert restored.agent_id is None


def test_memory_to_table_rejects_nan_added_after_validation() -> None:
    """The model rejects NaN at construction, not on assignment: the dump refuses
    to write `NaN`, which is not JSON."""
    mem = Memory(
        id="mem-003",
        agent_id=None,
        content="x",
        metadata={},
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    mem.metadata["score"] = float("inf")
    with pytest.raises(ValueError, match="not JSON compliant"):
        memory_to_table(mem)
