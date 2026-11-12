"""Tests for memory.models: Memory."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from adjents.memory.models import Memory


def make_memory() -> Memory:
    return Memory(
        id="mem-001",
        agent_id="agent-001",
        content="Client Acme Corp prefers invoices on the 1st of each month.",
        metadata={"source": "onboarding"},
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )


# --- Memory ---


def test_memory_valid() -> None:
    mem = make_memory()
    assert mem.agent_id == "agent-001"
    assert "Acme" in mem.content


def test_memory_global_kb_no_agent() -> None:
    """agent_id=None marks a global knowledge base entry."""
    mem = Memory(
        id="mem-002",
        agent_id=None,
        content="Company name: Acme Corp. Founded 2018.",
        metadata={"source": "generator_agent"},
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    assert mem.agent_id is None


def test_memory_metadata_is_dict() -> None:
    mem = Memory(
        id="mem-003",
        agent_id="agent-001",
        content="x",
        metadata={"key": "value", "count": 42},
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    assert isinstance(mem.metadata, dict)
    assert mem.metadata["count"] == 42


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 5, 20, tzinfo=UTC),  # not JSON: crashes `json.dumps`
        (1, 2),  # would come back as a list
        float("nan"),  # `json.dumps` writes NaN, which is not JSON
        {"nested": float("inf")},
    ],
    ids=["datetime", "tuple", "nan", "nested-inf"],
)
def test_memory_metadata_rejects_non_json_values(value: object) -> None:
    data = {**make_memory().model_dump(), "metadata": {"key": value}}
    with pytest.raises(ValidationError) as exc_info:
        Memory.model_validate(data)
    assert {error["loc"][0] for error in exc_info.value.errors()} == {"metadata"}


@pytest.mark.parametrize("field", list(Memory.model_fields))
def test_memory_every_field_is_required(field: str) -> None:
    """Nullable fields included: a JSON that omits a key fails instead of
    defaulting to None."""
    data = make_memory().model_dump()
    del data[field]
    with pytest.raises(ValidationError) as exc_info:
        Memory.model_validate(data)
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        ((field,), "missing")
    ]


def test_memory_json_mode_roundtrip() -> None:
    mem = make_memory()
    assert Memory.model_validate_json(mem.model_dump_json()) == mem


def test_memory_rejects_naive_datetime() -> None:
    data = {**make_memory().model_dump(), "created_at": datetime(2026, 5, 20, 10, 0)}
    with pytest.raises(ValidationError) as exc_info:
        Memory.model_validate(data)
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        (("created_at",), "timezone_aware")
    ]


def test_memory_validation_error_hides_the_input() -> None:
    data = {**make_memory().model_dump(), "content": ["SECRET-INPUT"]}
    with pytest.raises(ValidationError) as exc_info:
        Memory.model_validate(data)
    assert "content" in str(exc_info.value)
    assert "SECRET-INPUT" not in str(exc_info.value)


def test_memory_serialisation_roundtrip() -> None:
    mem = Memory(
        id="mem-001",
        agent_id="agent-001",
        content="Some learned fact.",
        metadata={},
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    restored = Memory.model_validate(mem.model_dump())
    assert restored == mem
