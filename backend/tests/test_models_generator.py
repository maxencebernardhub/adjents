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


def test_business_context_accepts_overnight_work_hours() -> None:
    """Same `WorkHours` type as `AgentSpec`: an end before the start crosses
    midnight."""
    assert make_bc(work_hours="22:00-02:00").work_hours == "22:00-02:00"


@pytest.mark.parametrize("value", ["evenings", "99:99-25:00", "18:00-18:00"])
def test_business_context_rejects_invalid_work_hours(value: str) -> None:
    """Rejected at the interview, not only later when org generation copies the
    value into every agent."""
    with pytest.raises(ValidationError) as exc_info:
        make_bc(work_hours=value)
    assert {error["loc"][0] for error in exc_info.value.errors()} == {"work_hours"}


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


@pytest.mark.parametrize("field", list(BusinessContext.model_fields))
def test_business_context_every_field_is_required(field: str) -> None:
    """Nullable fields included: an extraction JSON that omits a key fails instead
    of defaulting to None."""
    data = make_bc().model_dump()
    del data[field]
    with pytest.raises(ValidationError) as exc_info:
        BusinessContext.model_validate(data)
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        ((field,), "missing")
    ]


def test_business_context_json_mode_roundtrip() -> None:
    bc = make_bc()
    assert BusinessContext.model_validate_json(bc.model_dump_json()) == bc


def test_business_context_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError) as exc_info:
        make_bc(created_at=datetime(2026, 5, 20, 10, 0))
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        (("created_at",), "timezone_aware")
    ]


def test_business_context_validation_error_hides_the_input() -> None:
    """The interview wraps this error in its own: it must name the field, never
    the extracted business data."""
    with pytest.raises(ValidationError) as exc_info:
        make_bc(target_clients="Patients of Dr X")
    assert "target_clients" in str(exc_info.value)
    assert "Patients of Dr X" not in str(exc_info.value)


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
