"""Tests for deliverables.models: Deliverable."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from adjents.deliverables.models import Deliverable


def make_deliverable() -> Deliverable:
    return Deliverable(
        id="del-001",
        agent_id="agent-001",
        project_id="proj-001",
        title="Q1 Invoice Batch",
        file_path="agent-001/2026-05-20_q1-invoice-batch.md",
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )


def _validate_deliverable(**overrides: object) -> Deliverable:
    """Build a Deliverable through validation (`model_copy(update=...)` skips it)."""
    return Deliverable.model_validate({**make_deliverable().model_dump(), **overrides})


# --- Deliverable ---


def test_deliverable_valid() -> None:
    d = make_deliverable()
    assert d.id == "del-001"
    assert d.project_id == "proj-001"
    assert d.file_path.startswith("agent-001/")


def test_deliverable_no_project() -> None:
    """project_id=None for deliverables produced outside a project."""
    daily = _validate_deliverable(id="del-002", project_id=None)
    assert daily.project_id is None


@pytest.mark.parametrize("field", list(Deliverable.model_fields))
def test_deliverable_every_field_is_required(field: str) -> None:
    """Nullable fields included: a JSON that omits a key fails instead of
    defaulting to None."""
    data = make_deliverable().model_dump()
    del data[field]
    with pytest.raises(ValidationError) as exc_info:
        Deliverable.model_validate(data)
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        ((field,), "missing")
    ]


def test_deliverable_json_mode_roundtrip() -> None:
    d = make_deliverable()
    assert Deliverable.model_validate_json(d.model_dump_json()) == d


def test_deliverable_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate_deliverable(created_at=datetime(2026, 5, 20, 10, 0))
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        (("created_at",), "timezone_aware")
    ]


def test_deliverable_validation_error_hides_the_input() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate_deliverable(title=["SECRET-INPUT"])
    assert "title" in str(exc_info.value)
    assert "SECRET-INPUT" not in str(exc_info.value)


def test_deliverable_serialisation_roundtrip() -> None:
    d = make_deliverable()
    restored = Deliverable.model_validate(d.model_dump())
    assert restored == d
