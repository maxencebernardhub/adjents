"""Tests for agents domain models: AgentSpec, AgentState, AgentStatus, Skill,
BlockingQuestion."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from adjents.agents.models import (
    AgentSpec,
    AgentState,
    AgentStatus,
    BlockingQuestion,
    Skill,
)


def make_skill() -> Skill:
    return Skill(
        id="skill-001",
        name="Draft invoice",
        description="Generates a PDF invoice for a client.",
        inputs=["Client name", "Amount", "Due date"],
        outputs=["Invoice PDF path"],
        requires_human_review=True,
    )


def make_agent_spec() -> AgentSpec:
    return AgentSpec(
        id="agent-001",
        name="Finance Lead",
        level=1,
        parent_id="agent-000",
        domain="Finance",
        role_description="Manages all financial operations.",
        responsibilities=["Invoicing", "Cash flow monitoring"],
        skill_ids=["skill-001"],
        escalation_rules=["Escalate if invoice overdue > 30 days"],
        scheduler_interval_seconds=900,
        work_hours="09:00-18:00",
        is_paused=False,
        visual_character="accountant_f",
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )


# --- AgentStatus ---


def test_agent_status_all_values() -> None:
    assert AgentStatus.IDLE == "idle"
    assert AgentStatus.WORKING == "working"
    assert AgentStatus.IN_MEETING_1ON1 == "meeting_1on1"
    assert AgentStatus.IN_MEETING_GROUP == "meeting_group"
    assert AgentStatus.PAUSED == "paused"
    assert AgentStatus.WAITING_FOR_HUMAN == "waiting_for_human"


def test_agent_status_is_str_enum() -> None:
    assert isinstance(AgentStatus.IDLE, str)


# --- Skill ---


def test_skill_valid() -> None:
    skill = make_skill()
    assert skill.id == "skill-001"
    assert skill.requires_human_review is True


def test_skill_inputs_outputs_are_lists() -> None:
    skill = make_skill()
    assert isinstance(skill.inputs, list)
    assert isinstance(skill.outputs, list)


def test_skill_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        Skill(  # type: ignore[call-arg]
            id="s",
            description="x",
            inputs=[],
            outputs=[],
            requires_human_review=False,
        )


# --- AgentSpec ---


def test_agent_spec_valid() -> None:
    spec = make_agent_spec()
    assert spec.id == "agent-001"
    assert spec.level == 1
    assert spec.domain == "Finance"


def test_agent_spec_coo_no_parent_no_domain() -> None:
    spec = AgentSpec(
        id="agent-000",
        name="COO",
        level=0,
        parent_id=None,
        domain=None,
        role_description="Chief of Staff.",
        responsibilities=["Coordinate all N-1 leads"],
        skill_ids=[],
        escalation_rules=[],
        scheduler_interval_seconds=300,
        work_hours=None,
        is_paused=False,
        visual_character="coo_m",
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    assert spec.parent_id is None
    assert spec.domain is None
    assert spec.level == 0


def test_agent_spec_level_no_cap() -> None:
    """Hierarchy depth has no hard limit per VISION.md §3.1."""
    spec = make_agent_spec()
    spec_deep = spec.model_copy(update={"id": "deep", "level": 5})
    assert spec_deep.level == 5


def test_agent_spec_serialisation_roundtrip() -> None:
    spec = make_agent_spec()
    data = spec.model_dump()
    restored = AgentSpec.model_validate(data)
    assert restored == spec


def test_agent_spec_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        AgentSpec(  # type: ignore[call-arg]
            id="x",
            level=1,
            role_description="x",
            responsibilities=[],
            skill_ids=[],
            escalation_rules=[],
            scheduler_interval_seconds=60,
            is_paused=False,
            visual_character="x",
            created_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


def test_agent_spec_invalid_level_type() -> None:
    with pytest.raises(ValidationError):
        AgentSpec(
            id="x",
            name="x",
            level="N-1",  # type: ignore[arg-type]
            parent_id=None,
            domain=None,
            role_description="x",
            responsibilities=[],
            skill_ids=[],
            escalation_rules=[],
            scheduler_interval_seconds=60,
            work_hours=None,
            is_paused=False,
            visual_character="x",
            created_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


# --- AgentState ---


def test_agent_state_valid() -> None:
    state = AgentState(
        agent_id="agent-001",
        status=AgentStatus.WORKING,
        current_task_summary="Drafting Q1 invoice batch.",
        meeting_with=[],
        updated_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    assert state.status == AgentStatus.WORKING
    assert state.current_task_summary is not None


def test_agent_state_no_task_summary() -> None:
    state = AgentState(
        agent_id="agent-001",
        status=AgentStatus.IDLE,
        current_task_summary=None,
        meeting_with=[],
        updated_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    assert state.current_task_summary is None


def test_agent_state_in_meeting() -> None:
    state = AgentState(
        agent_id="agent-001",
        status=AgentStatus.IN_MEETING_1ON1,
        current_task_summary=None,
        meeting_with=["agent-002"],
        updated_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    assert "agent-002" in state.meeting_with


def test_agent_state_invalid_status() -> None:
    with pytest.raises(ValidationError):
        AgentState(
            agent_id="agent-001",
            status="flying",  # type: ignore[arg-type]
            current_task_summary=None,
            meeting_with=[],
            updated_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


def test_agent_state_serialisation_roundtrip() -> None:
    state = AgentState(
        agent_id="agent-001",
        status=AgentStatus.PAUSED,
        current_task_summary=None,
        meeting_with=[],
        updated_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    data = state.model_dump()
    restored = AgentState.model_validate(data)
    assert restored == state


# --- BlockingQuestion ---


def test_blocking_question_valid() -> None:
    bq = BlockingQuestion(
        id="bq-001",
        agent_id="agent-001",
        question="Should I send the overdue invoice reminder to Acme Corp?",
        context="Invoice #42 is 15 days overdue. Escalation threshold is 14 days.",
        answered=False,
        answer=None,
        created_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
        answered_at=None,
    )
    assert bq.id == "bq-001"
    assert bq.answered is False
    assert bq.answer is None
    assert bq.answered_at is None


def test_blocking_question_answered_state() -> None:
    bq = BlockingQuestion(
        id="bq-002",
        agent_id="agent-001",
        question="Confirm budget increase for Q3 campaign?",
        context=None,
        answered=True,
        answer="Yes, approved up to $500.",
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=UTC),
        answered_at=datetime(2026, 5, 20, 9, 30, tzinfo=UTC),
    )
    assert bq.answered is True
    assert bq.answer == "Yes, approved up to $500."
    assert bq.answered_at is not None


def test_blocking_question_no_context() -> None:
    bq = BlockingQuestion(
        id="bq-003",
        agent_id="agent-002",
        question="Proceed with vendor switch?",
        context=None,
        answered=False,
        answer=None,
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
        answered_at=None,
    )
    assert bq.context is None


def test_blocking_question_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        BlockingQuestion(  # type: ignore[call-arg]
            id="bq-x",
            agent_id="agent-001",
            context=None,
            answered=False,
            answer=None,
            created_at=datetime(2026, 5, 20, tzinfo=UTC),
            answered_at=None,
        )


def test_blocking_question_serialisation_roundtrip() -> None:
    bq = BlockingQuestion(
        id="bq-001",
        agent_id="agent-001",
        question="Approve the new pricing tier?",
        context="Current tier expires end of month.",
        answered=False,
        answer=None,
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
        answered_at=None,
    )
    restored = BlockingQuestion.model_validate(bq.model_dump())
    assert restored == bq
