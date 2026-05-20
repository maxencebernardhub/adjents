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
    assert ProjectStatus.ACTIVE == "active"
    assert ProjectStatus.COMPLETED == "completed"
    assert ProjectStatus.CANCELLED == "cancelled"


def test_project_status_is_str_enum() -> None:
    assert isinstance(ProjectStatus.ACTIVE, str)


# --- Project ---


def test_project_valid() -> None:
    proj = make_project()
    assert proj.id == "proj-001"
    assert proj.status == ProjectStatus.ACTIVE
    assert len(proj.deliverable_descriptions) == 2


def test_project_no_deadline() -> None:
    """deadline is optional — daily-ops projects may have no fixed end date."""
    proj = make_project()
    proj_no_deadline = proj.model_copy(update={"deadline": None})
    assert proj_no_deadline.deadline is None


def test_project_no_contributors() -> None:
    proj = make_project()
    solo = proj.model_copy(update={"contributor_agent_ids": []})
    assert solo.contributor_agent_ids == []


def test_project_invalid_status() -> None:
    with pytest.raises(ValidationError):
        Project(
            id="x",
            title="x",
            objective="x",
            deliverable_descriptions=[],
            deadline=None,
            lead_agent_id="agent-001",
            contributor_agent_ids=[],
            status="running",  # type: ignore[arg-type]
            created_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


def test_project_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        Project(  # type: ignore[call-arg]
            id="x",
            title="x",
            deliverable_descriptions=[],
            deadline=None,
            lead_agent_id="agent-001",
            contributor_agent_ids=[],
            status=ProjectStatus.ACTIVE,
            created_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


def test_project_serialisation_roundtrip() -> None:
    proj = make_project()
    restored = Project.model_validate(proj.model_dump())
    assert restored == proj
