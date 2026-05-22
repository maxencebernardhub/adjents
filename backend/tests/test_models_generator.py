"""Tests for generator.models: BusinessContext."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from adjents.generator.models import BusinessContext


def make_bc(**overrides: object) -> BusinessContext:
    defaults: dict[str, object] = {
        "id": "bc-001",
        "conversation_id": "conv-001",
        "business_name": "Luminescence",
        "founder_name": "Alex Chen",
        "language": "fr",
        "core_activity": "Freelance UX designer — mobile apps",
        "legal_status": "Auto-entrepreneur",
        "target_clients": ["Startups", "PMEs"],
        "domains_with_human_coverage": [],
        "domains_to_staff": ["Finance", "Sales", "Marketing"],
        "tasks_to_delegate": ["Invoicing", "Prospecting"],
        "tasks_user_keeps": ["UX design work"],
        "financial_goals": "2000€ net/month",
        "existing_tools": ["Gmail", "LinkedIn"],
        "autonomy_preference": "Validation required for external communications",
        "work_hours": "18:00-23:00",
        "additional_context": None,
        "created_at": datetime(2026, 5, 20, tzinfo=UTC),
    }
    defaults.update(overrides)
    return BusinessContext(**defaults)  # type: ignore[arg-type]


def test_business_context_valid() -> None:
    bc = make_bc()
    assert bc.founder_name == "Alex Chen"
    assert bc.language == "fr"
    assert bc.conversation_id == "conv-001"


def test_business_context_no_company_name() -> None:
    bc = make_bc(business_name=None)
    assert bc.business_name is None


def test_business_context_no_legal_status() -> None:
    bc = make_bc(legal_status=None)
    assert bc.legal_status is None


def test_business_context_no_work_hours() -> None:
    bc = make_bc(work_hours=None)
    assert bc.work_hours is None


def test_business_context_no_financial_goals() -> None:
    bc = make_bc(financial_goals=None)
    assert bc.financial_goals is None


def test_business_context_no_additional_context() -> None:
    bc = make_bc(additional_context=None)
    assert bc.additional_context is None


def test_business_context_empty_lists() -> None:
    bc = make_bc(
        domains_with_human_coverage=[],
        tasks_user_keeps=[],
        existing_tools=[],
    )
    assert bc.domains_with_human_coverage == []
    assert bc.tasks_user_keeps == []
    assert bc.existing_tools == []


def test_business_context_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        BusinessContext(  # type: ignore[call-arg]
            id="bc-001",
            founder_name="Alex",
            language="fr",
            core_activity="UX design",
            created_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


def test_business_context_serialisation_roundtrip() -> None:
    bc = make_bc()
    restored = BusinessContext.model_validate(bc.model_dump())
    assert restored == bc


def test_business_context_full_example() -> None:
    bc = make_bc(
        domains_to_staff=["Finance", "Sales", "Marketing", "Operations"],
        tasks_to_delegate=[
            "Invoicing and payment tracking",
            "URSSAF declarations",
            "LinkedIn prospecting (draft for validation)",
        ],
        additional_context="Currently employed full-time. Freelance evenings.",
    )
    assert len(bc.domains_to_staff) == 4
    assert bc.additional_context is not None
