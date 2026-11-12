"""Tests for db.convert.messaging: Message / Conversation ↔ table roundtrips."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.db.convert.messaging import (
    conversation_from_table,
    conversation_to_table,
    message_from_table,
    message_to_table,
)
from adjents.db.tables import ConversationTable, MessageTable
from adjents.messaging.models import Conversation, Message

# --- Message ---


async def test_message_roundtrip(async_session: AsyncSession) -> None:
    msg = Message(
        id="msg-001",
        from_agent="agent-001",
        to_agent="user",
        content="Invoice batch ready for review.",
        metadata={"task_id": "task-042"},
        parent_message_id=None,
        created_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
    )
    row = message_to_table(msg)
    async_session.add(row)
    await async_session.commit()

    stored = await async_session.get(MessageTable, msg.id, populate_existing=True)
    assert stored is not None
    restored = message_from_table(stored)
    assert restored == msg


async def test_message_with_parent_roundtrip(async_session: AsyncSession) -> None:
    parent = Message(
        id="msg-001",
        from_agent="user",
        to_agent="agent-001",
        content="Please prioritise the Q2 report.",
        metadata={},
        parent_message_id=None,
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=UTC),
    )
    child = Message(
        id="msg-002",
        from_agent="agent-001",
        to_agent="user",
        content="Understood. Prioritising Q2 report.",
        metadata={},
        parent_message_id="msg-001",
        created_at=datetime(2026, 5, 20, 9, 1, tzinfo=UTC),
    )
    async_session.add(message_to_table(parent))
    async_session.add(message_to_table(child))
    await async_session.commit()

    stored = await async_session.get(MessageTable, "msg-002", populate_existing=True)
    assert stored is not None
    restored = message_from_table(stored)
    assert restored.parent_message_id == "msg-001"


def _message() -> Message:
    return Message(
        id="msg-001",
        from_agent="agent-001",
        to_agent="user",
        content="Invoice batch ready for review.",
        metadata={},
        parent_message_id=None,
        created_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
    )


def test_message_to_table_rejects_nan_added_after_validation() -> None:
    """The model rejects NaN at construction, not on assignment: the dump refuses
    to write `NaN`, which is not JSON."""
    msg = _message()
    msg.metadata["score"] = float("nan")
    with pytest.raises(ValueError, match="not JSON compliant"):
        message_to_table(msg)


def test_message_from_table_rejects_a_naive_date() -> None:
    row = message_to_table(_message())
    row.created_at = "2026-05-20T10:00:00"
    with pytest.raises(ValidationError) as exc_info:
        message_from_table(row)
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        (("created_at",), "timezone_aware")
    ]


# --- Conversation ---


async def test_conversation_roundtrip(async_session: AsyncSession) -> None:
    conv = Conversation(
        id="conv-001",
        participant_agents=["agent-001", "agent-002"],
        message_ids=["msg-001", "msg-002", "msg-003"],
        started_at=datetime(2026, 5, 20, 9, 0, tzinfo=UTC),
    )
    row = conversation_to_table(conv)
    async_session.add(row)
    await async_session.commit()

    stored = await async_session.get(ConversationTable, conv.id, populate_existing=True)
    assert stored is not None
    restored = conversation_from_table(stored)
    assert restored == conv
    assert restored.message_ids == ["msg-001", "msg-002", "msg-003"]
