"""Tests for db.convert.generator: BusinessContext ↔ table roundtrips.

The `ValidationSession` / `AgentValidationRecord` conversions are still tested in
`test_team_setup_models.py`, next to their models.
"""

from datetime import UTC, datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.db.convert.generator import (
    business_context_from_table,
    business_context_to_table,
)
from adjents.db.tables import BusinessContextTable
from adjents.generator.models import BusinessContext


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

    stored = await async_session.get(
        BusinessContextTable, bc.id, populate_existing=True
    )
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

    stored = await async_session.get(
        BusinessContextTable, bc.id, populate_existing=True
    )
    assert stored is not None
    restored = business_context_from_table(stored)
    assert restored.business_name is None
    assert restored.legal_status is None
    assert restored.work_hours is None
    assert restored.existing_tools == []
