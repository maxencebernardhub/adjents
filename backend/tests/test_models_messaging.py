"""Tests for messaging.models: Message, Conversation."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from adjents.messaging.models import Conversation, Message


def make_message(msg_id: str = "msg-001", parent: str | None = None) -> Message:
    return Message(
        id=msg_id,
        from_agent="agent-001",
        to_agent="user",
        content="Invoice batch ready for review.",
        metadata={"task_id": "task-042"},
        parent_message_id=parent,
        created_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
    )


# --- Message ---


def test_message_valid() -> None:
    msg = make_message()
    assert msg.from_agent == "agent-001"
    assert msg.to_agent == "user"
    assert msg.parent_message_id is None


def test_message_with_parent() -> None:
    msg = make_message(msg_id="msg-002", parent="msg-001")
    assert msg.parent_message_id == "msg-001"


def test_message_from_user() -> None:
    msg = Message(
        id="msg-003",
        from_agent="user",
        to_agent="agent-001",
        content="Please prioritise the Q2 report.",
        metadata={},
        parent_message_id=None,
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    assert msg.from_agent == "user"


def test_message_from_system() -> None:
    msg = Message(
        id="msg-004",
        from_agent="system",
        to_agent="agent-001",
        content="Agent loop started.",
        metadata={},
        parent_message_id=None,
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    assert msg.from_agent == "system"


def test_message_metadata_is_dict() -> None:
    msg = make_message()
    assert isinstance(msg.metadata, dict)


def test_message_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        Message(  # type: ignore[call-arg]
            id="x",
            from_agent="agent-001",
            content="hello",
            metadata={},
            parent_message_id=None,
            created_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


def test_message_serialisation_roundtrip() -> None:
    msg = make_message()
    restored = Message.model_validate(msg.model_dump())
    assert restored == msg


# --- Conversation ---


def test_conversation_valid() -> None:
    conv = Conversation(
        id="conv-001",
        participant_agents=["agent-001", "agent-002"],
        message_ids=["msg-001", "msg-002"],
        started_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    assert len(conv.participant_agents) == 2
    assert conv.message_ids[0] == "msg-001"


def test_conversation_message_ids_ordered() -> None:
    """Message IDs must preserve insertion order."""
    ids = ["msg-001", "msg-002", "msg-003"]
    conv = Conversation(
        id="conv-002",
        participant_agents=["agent-001"],
        message_ids=ids,
        started_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    assert conv.message_ids == ids


def test_conversation_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        Conversation(  # type: ignore[call-arg]
            id="x",
            message_ids=[],
            started_at=datetime(2026, 5, 20, tzinfo=UTC),
        )


def test_conversation_serialisation_roundtrip() -> None:
    conv = Conversation(
        id="conv-001",
        participant_agents=["agent-001"],
        message_ids=["msg-001"],
        started_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    restored = Conversation.model_validate(conv.model_dump())
    assert restored == conv
