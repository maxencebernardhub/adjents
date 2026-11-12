"""Tests for agents domain models: AgentSpec, AgentState, AgentStatus, Skill,
BlockingQuestion."""

from datetime import UTC, datetime

import pytest
from pydantic import TypeAdapter, ValidationError

from adjents.agents.models import (
    VISUAL_CHARACTERS,
    AgentSpec,
    AgentState,
    AgentStatus,
    BlockingQuestion,
    Skill,
    WorkHours,
)
from adjents.generator.org_generation import VALID_VISUAL_CHARACTERS


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
        visual_character="character_analyst",
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )


# --- AgentStatus ---


def test_agent_status_all_values() -> None:
    assert AgentStatus.IDLE.value == "idle"
    assert AgentStatus.WORKING.value == "working"
    assert AgentStatus.IN_MEETING_1ON1.value == "meeting_1on1"
    assert AgentStatus.IN_MEETING_GROUP.value == "meeting_group"
    assert AgentStatus.PAUSED.value == "paused"
    assert AgentStatus.WAITING_FOR_HUMAN.value == "waiting_for_human"


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
        visual_character="character_suit",
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
            scheduler_interval_seconds=300,
            is_paused=False,
            visual_character="character_suit",
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
            scheduler_interval_seconds=300,
            work_hours=None,
            is_paused=False,
            visual_character="character_suit",
            created_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


# --- AgentSpec constraints ---


def _validate_spec(**overrides: object) -> AgentSpec:
    """Build an AgentSpec through validation (`model_copy(update=...)` skips it)."""
    return AgentSpec.model_validate({**make_agent_spec().model_dump(), **overrides})


def _error_fields(exc_info: pytest.ExceptionInfo[ValidationError]) -> set[object]:
    return {error["loc"][0] for error in exc_info.value.errors()}


@pytest.mark.parametrize("level", [0, 1, 7])
def test_agent_spec_accepts_any_non_negative_level(level: int) -> None:
    """Depth has no upper bound (VISION.md §3.1)."""
    assert _validate_spec(level=level).level == level


def test_agent_spec_rejects_negative_level() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate_spec(level=-1)
    assert _error_fields(exc_info) == {"level"}


@pytest.mark.parametrize("interval", [300, 3600])
def test_agent_spec_accepts_interval_bounds(interval: int) -> None:
    spec = _validate_spec(scheduler_interval_seconds=interval)
    assert spec.scheduler_interval_seconds == interval


@pytest.mark.parametrize("interval", [0, 299, 3601])
def test_agent_spec_rejects_interval_out_of_bounds(interval: int) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate_spec(scheduler_interval_seconds=interval)
    assert _error_fields(exc_info) == {"scheduler_interval_seconds"}


def test_visual_characters_reference_set() -> None:
    """The sprite identifiers the workspace can render."""
    assert VISUAL_CHARACTERS == {
        "character_suit",
        "character_creative",
        "character_tech",
        "character_support",
        "character_analyst",
        "character_sales",
    }


def test_visual_characters_match_org_generation_copy() -> None:
    """Org generation keeps its own copy until it is rewired to the reference set;
    remove this test then."""
    assert VISUAL_CHARACTERS == VALID_VISUAL_CHARACTERS


@pytest.mark.parametrize("character", sorted(VISUAL_CHARACTERS))
def test_agent_spec_accepts_every_reference_visual_character(character: str) -> None:
    assert _validate_spec(visual_character=character).visual_character == character


@pytest.mark.parametrize(
    "character", ["accountant_f", "", "Character_suit", " character_suit"]
)
def test_agent_spec_rejects_unknown_visual_character(character: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate_spec(visual_character=character)
    assert _error_fields(exc_info) == {"visual_character"}


def test_agent_spec_accepts_overnight_work_hours() -> None:
    assert _validate_spec(work_hours="22:00-02:00").work_hours == "22:00-02:00"


def test_agent_spec_rejects_invalid_work_hours() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _validate_spec(work_hours="99:99-25:00")
    assert _error_fields(exc_info) == {"work_hours"}


# --- WorkHours ---

_work_hours: TypeAdapter[str] = TypeAdapter(WorkHours)


@pytest.mark.parametrize(
    "value", ["09:00-18:00", "00:00-23:59", "18:00-23:00", "08:30-12:45"]
)
def test_work_hours_accepts_a_same_day_window(value: str) -> None:
    assert _work_hours.validate_python(value) == value


@pytest.mark.parametrize("value", ["22:00-02:00", "23:59-00:00", "18:00-09:00"])
def test_work_hours_accepts_an_end_before_the_start(value: str) -> None:
    """An end before the start is a window crossing midnight."""
    assert _work_hours.validate_python(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "09:00-09:00",  # start == end: empty or full day, ambiguous
        "24:00-02:00",
        "09:00-24:00",
        "99:99-25:00",
        "09:60-18:00",
        "9:00-18:00",
        "09:00 - 18:00",
        "09:00-18:00\n",
        "09h00-18h00",
        "٠٩:٠٠-١٨:٠٠",  # Arabic-Indic digits
        "evenings",
        "",
    ],
)
def test_work_hours_rejects(value: str) -> None:
    with pytest.raises(ValidationError):
        _work_hours.validate_python(value)


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
