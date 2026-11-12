"""Tests for projects.models: Project, ProjectStatus."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from adjents.projects.models import Project, ProjectStatus


def make_project() -> Project:
    return Project(
        id="proj-001",
        title="Company website redesign",
        objective="Build a new public website showcasing services.",
        deliverable_descriptions=["Live website", "Copy document"],
        deadline=datetime(2026, 8, 1, tzinfo=UTC),
        lead_agent_id="agent-003",
        contributor_agent_ids=["agent-004", "agent-005"],
        status=ProjectStatus.ACTIVE,
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )


# --- ProjectStatus ---


def test_project_status_all_values() -> None:
    assert ProjectStatus.ACTIVE.value == "active"
    assert ProjectStatus.COMPLETED.value == "completed"
    assert ProjectStatus.CANCELLED.value == "cancelled"


def test_project_status_is_str_enum() -> None:
    assert isinstance(ProjectStatus.ACTIVE, str)


# --- Project ---


def test_project_valid() -> None:
    proj = make_project()
    assert proj.id == "proj-001"
    assert proj.status == ProjectStatus.ACTIVE
    assert len(proj.deliverable_descriptions) == 2


def _validate_project(**overrides: object) -> Project:
    """Build a Project through validation (`model_copy(update=...)` skips it)."""
    return Project.model_validate({**make_project().model_dump(), **overrides})


def test_project_no_deadline() -> None:
    """deadline is optional — daily-ops projects may have no fixed end date."""
    assert _validate_project(deadline=None).deadline is None


def test_project_no_contributors() -> None:
    solo = _validate_project(contributor_agent_ids=[])
    assert solo.contributor_agent_ids == []


def test_project_invalid_status() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate_project(status="running")
    assert [error["loc"] for error in exc_info.value.errors()] == [("status",)]


@pytest.mark.parametrize("field", list(Project.model_fields))
def test_project_every_field_is_required(field: str) -> None:
    """Nullable fields included: a JSON that omits a key fails instead of
    defaulting to None."""
    data = make_project().model_dump()
    del data[field]
    with pytest.raises(ValidationError) as exc_info:
        Project.model_validate(data)
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        ((field,), "missing")
    ]


def test_project_json_mode_roundtrip() -> None:
    proj = make_project()
    assert Project.model_validate_json(proj.model_dump_json()) == proj


@pytest.mark.parametrize("field", ["deadline", "created_at"])
def test_project_rejects_naive_datetime(field: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate_project(**{field: datetime(2026, 5, 20, 10, 0)})
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        ((field,), "timezone_aware")
    ]


def test_project_validation_error_hides_the_input() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate_project(objective=["SECRET-INPUT"])
    assert "objective" in str(exc_info.value)
    assert "SECRET-INPUT" not in str(exc_info.value)


def test_project_serialisation_roundtrip() -> None:
    proj = make_project()
    restored = Project.model_validate(proj.model_dump())
    assert restored == proj
