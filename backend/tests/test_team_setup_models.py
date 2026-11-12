"""T1 tests: ValidationSession and AgentValidationRecord models + convert roundtrips.

All tests are pure (no DB, no LLM).
"""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

from adjents.db.convert import (
    agent_validation_record_from_table,
    agent_validation_record_to_table,
    validation_session_from_table,
    validation_session_to_table,
)
from adjents.generator.team_setup import (
    AgentValidationRecord,
    AgentValidationStatus,
    ValidationSession,
)


def test_agent_validation_status_values() -> None:
    assert AgentValidationStatus.PENDING.value == "pending"
    assert AgentValidationStatus.IN_PROGRESS.value == "in_progress"
    assert AgentValidationStatus.VALIDATED.value == "validated"
    assert AgentValidationStatus.SKIPPED.value == "skipped"


def test_validation_session_roundtrip() -> None:
    session = ValidationSession(
        id="sess-1",
        started_at=datetime(2026, 5, 28, 10, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 5, 28, 11, 0, 0, tzinfo=UTC),
        skipped=False,
    )
    row = validation_session_to_table(session)
    restored = validation_session_from_table(row)
    assert restored == session


def test_validation_session_completed_at_none() -> None:
    session = ValidationSession(
        id="sess-2",
        started_at=datetime(2026, 5, 28, 10, 0, 0, tzinfo=UTC),
        completed_at=None,
        skipped=False,
    )
    row = validation_session_to_table(session)
    assert row.completed_at is None
    restored = validation_session_from_table(row)
    assert restored.completed_at is None


def test_agent_validation_record_roundtrip() -> None:
    record = AgentValidationRecord(
        id="rec-1",
        session_id="sess-1",
        root_agent_id="agent-1",
        status=AgentValidationStatus.IN_PROGRESS,
        active_agent_id="agent-2",
        active_conversation_id="conv-1",
        navigation_stack=["agent-1", "agent-2"],
        conversation_ids=["conv-1", "conv-2"],
        visited_agent_ids=["agent-3"],
        validated_at=datetime(2026, 5, 28, 12, 0, 0, tzinfo=UTC),
    )
    row = agent_validation_record_to_table(record)
    restored = agent_validation_record_from_table(row)
    assert restored == record


def test_navigation_stack_serializes_to_json_string() -> None:
    record = AgentValidationRecord(
        id="rec-2",
        session_id="sess-1",
        root_agent_id="agent-1",
        status=AgentValidationStatus.PENDING,
        active_agent_id=None,
        active_conversation_id=None,
        navigation_stack=["a", "b"],
        conversation_ids=[],
        visited_agent_ids=[],
        validated_at=None,
    )
    row = agent_validation_record_to_table(record)
    assert row.navigation_stack == '["a", "b"]'


def test_navigation_stack_empty_list_roundtrip() -> None:
    record = AgentValidationRecord(
        id="rec-3",
        session_id="sess-1",
        root_agent_id="agent-1",
        status=AgentValidationStatus.PENDING,
        active_agent_id=None,
        active_conversation_id=None,
        navigation_stack=[],
        conversation_ids=[],
        visited_agent_ids=[],
        validated_at=None,
    )
    row = agent_validation_record_to_table(record)
    assert row.navigation_stack == "[]"
    restored = agent_validation_record_from_table(row)
    assert restored.navigation_stack == []


def test_visited_agent_ids_roundtrip() -> None:
    record = AgentValidationRecord(
        id="rec-4",
        session_id="sess-1",
        root_agent_id="agent-1",
        status=AgentValidationStatus.VALIDATED,
        active_agent_id=None,
        active_conversation_id=None,
        navigation_stack=[],
        conversation_ids=["conv-1"],
        visited_agent_ids=["agent-2", "agent-3"],
        validated_at=None,
    )
    row = agent_validation_record_to_table(record)
    restored = agent_validation_record_from_table(row)
    assert restored.visited_agent_ids == ["agent-2", "agent-3"]


def test_conversation_ids_roundtrip() -> None:
    record = AgentValidationRecord(
        id="rec-5",
        session_id="sess-1",
        root_agent_id="agent-1",
        status=AgentValidationStatus.VALIDATED,
        active_agent_id=None,
        active_conversation_id=None,
        navigation_stack=[],
        conversation_ids=["conv-a", "conv-b", "conv-c"],
        visited_agent_ids=[],
        validated_at=None,
    )
    row = agent_validation_record_to_table(record)
    restored = agent_validation_record_from_table(row)
    assert restored.conversation_ids == ["conv-a", "conv-b", "conv-c"]


def test_agent_validation_record_nullable_fields() -> None:
    record = AgentValidationRecord(
        id="rec-6",
        session_id="sess-1",
        root_agent_id="agent-1",
        status=AgentValidationStatus.PENDING,
        active_agent_id=None,
        active_conversation_id=None,
        navigation_stack=[],
        conversation_ids=[],
        visited_agent_ids=[],
        validated_at=None,
    )
    row = agent_validation_record_to_table(record)
    assert row.active_agent_id is None
    assert row.active_conversation_id is None
    assert row.validated_at is None
    restored = agent_validation_record_from_table(row)
    assert restored.active_agent_id is None
    assert restored.active_conversation_id is None
    assert restored.validated_at is None


# --- Contracts shared by every model of the module ---


def make_validation_session() -> ValidationSession:
    return ValidationSession(
        id="sess-1",
        started_at=datetime(2026, 5, 28, 10, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 5, 28, 11, 0, 0, tzinfo=UTC),
        skipped=False,
    )


def make_agent_validation_record() -> AgentValidationRecord:
    return AgentValidationRecord(
        id="rec-1",
        session_id="sess-1",
        root_agent_id="agent-1",
        status=AgentValidationStatus.VALIDATED,
        active_agent_id="agent-2",
        active_conversation_id="conv-1",
        navigation_stack=["agent-1"],
        conversation_ids=["conv-1"],
        visited_agent_ids=["agent-2"],
        validated_at=datetime(2026, 5, 28, 12, 0, 0, tzinfo=UTC),
    )


_FACTORIES: list[Callable[[], BaseModel]] = [
    make_validation_session,
    make_agent_validation_record,
]
_DATETIME_FIELDS = [
    (make_validation_session, "started_at"),
    (make_validation_session, "completed_at"),
    (make_agent_validation_record, "validated_at"),
]


def _id(value: object) -> str:
    return getattr(value, "__name__", str(value)).removeprefix("make_")


@pytest.mark.parametrize("factory", _FACTORIES, ids=_id)
def test_json_mode_roundtrip(factory: Callable[[], BaseModel]) -> None:
    model = factory()
    assert type(model).model_validate_json(model.model_dump_json()) == model


@pytest.mark.parametrize(("factory", "field"), _DATETIME_FIELDS, ids=_id)
def test_naive_datetime_is_rejected(
    factory: Callable[[], BaseModel], field: str
) -> None:
    data = {**factory().model_dump(), field: datetime(2026, 5, 28, 10, 0)}
    with pytest.raises(ValidationError) as exc_info:
        type(factory()).model_validate(data)
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        ((field,), "timezone_aware")
    ]


@pytest.mark.parametrize("factory", _FACTORIES, ids=_id)
def test_validation_error_hides_the_input(factory: Callable[[], BaseModel]) -> None:
    data = {**factory().model_dump(), "id": ["SECRET-INPUT"]}
    with pytest.raises(ValidationError) as exc_info:
        type(factory()).model_validate(data)
    assert "id" in str(exc_info.value)
    assert "SECRET-INPUT" not in str(exc_info.value)
