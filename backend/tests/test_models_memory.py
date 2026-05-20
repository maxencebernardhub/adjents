"""Tests for memory.models: Memory."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from adjents.memory.models import Memory

# --- Memory ---


def test_memory_valid() -> None:
    mem = Memory(
        id="mem-001",
        agent_id="agent-001",
        content="Client Acme Corp prefers invoices on the 1st of each month.",
        metadata={"source": "onboarding"},
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
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


def test_memory_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        Memory(  # type: ignore[call-arg]
            id="x",
            agent_id="agent-001",
            metadata={},
            created_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


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
