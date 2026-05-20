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


# --- Deliverable ---


def test_deliverable_valid() -> None:
    d = make_deliverable()
    assert d.id == "del-001"
    assert d.project_id == "proj-001"
    assert d.file_path.startswith("agent-001/")


def test_deliverable_no_project() -> None:
    """project_id=None for deliverables produced outside a project."""
    d = make_deliverable()
    daily = d.model_copy(update={"id": "del-002", "project_id": None})
    assert daily.project_id is None


def test_deliverable_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        Deliverable(  # type: ignore[call-arg]
            id="x",
            agent_id="agent-001",
            project_id=None,
            file_path="agent-001/x.md",
            created_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


def test_deliverable_serialisation_roundtrip() -> None:
    d = make_deliverable()
    restored = Deliverable.model_validate(d.model_dump())
    assert restored == d
