"""Tests for messaging.models: Message, Conversation."""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

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


def make_conversation() -> Conversation:
    return Conversation(
        id="conv-001",
        participant_agents=["agent-001"],
        message_ids=["msg-001"],
        started_at=datetime(2026, 5, 20, tzinfo=UTC),
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


def test_message_metadata_accepts_nested_json() -> None:
    metadata = {"conv_id": "c-1", "tags": ["a", 1, 2.5, None], "trace": {"ok": True}}
    msg = Message.model_validate({**make_message().model_dump(), "metadata": metadata})
    assert msg.metadata == metadata


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 5, 20, tzinfo=UTC),  # not JSON: crashes `json.dumps`
        (1, 2),  # would come back as a list
        {"a", "b"},
        float("nan"),  # `json.dumps` writes NaN, which is not JSON
        float("inf"),
        [1.0, float("-inf")],
        {"nested": float("nan")},
    ],
    ids=["datetime", "tuple", "set", "nan", "inf", "nested-inf", "nested-nan"],
)
def test_message_metadata_rejects_non_json_values(value: object) -> None:
    data = {**make_message().model_dump(), "metadata": {"key": value}}
    with pytest.raises(ValidationError) as exc_info:
        Message.model_validate(data)
    assert {error["loc"][0] for error in exc_info.value.errors()} == {"metadata"}


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


def test_conversation_serialisation_roundtrip() -> None:
    conv = make_conversation()
    restored = Conversation.model_validate(conv.model_dump())
    assert restored == conv


# --- Contracts shared by every model of the module ---

_FACTORIES: list[Callable[[], BaseModel]] = [make_message, make_conversation]
_FIELDS = [
    (factory, field) for factory in _FACTORIES for field in type(factory()).model_fields
]
_DATETIME_FIELDS = [(make_message, "created_at"), (make_conversation, "started_at")]
# A string field per model: free text where there is one (`Conversation` has none).
_CONTENT_FIELDS = [(make_message, "content"), (make_conversation, "id")]


def _id(value: object) -> str:
    return getattr(value, "__name__", str(value)).removeprefix("make_")


@pytest.mark.parametrize(("factory", "field"), _FIELDS, ids=_id)
def test_every_field_is_required(factory: Callable[[], BaseModel], field: str) -> None:
    """Nullable fields included: a JSON that omits a key fails instead of
    defaulting to None."""
    data = factory().model_dump()
    del data[field]
    with pytest.raises(ValidationError) as exc_info:
        type(factory()).model_validate(data)
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        ((field,), "missing")
    ]


@pytest.mark.parametrize("factory", _FACTORIES, ids=_id)
def test_json_mode_roundtrip(factory: Callable[[], BaseModel]) -> None:
    """The path of the API and the WebSocket: through JSON text, not Python
    objects."""
    model = factory()
    assert type(model).model_validate_json(model.model_dump_json()) == model


@pytest.mark.parametrize(("factory", "field"), _DATETIME_FIELDS, ids=_id)
def test_naive_datetime_is_rejected(
    factory: Callable[[], BaseModel], field: str
) -> None:
    data = {**factory().model_dump(), field: datetime(2026, 5, 20, 10, 0)}
    with pytest.raises(ValidationError) as exc_info:
        type(factory()).model_validate(data)
    errors = exc_info.value.errors()
    assert [(error["loc"], error["type"]) for error in errors] == [
        ((field,), "timezone_aware")
    ]


@pytest.mark.parametrize(("factory", "field"), _CONTENT_FIELDS, ids=_id)
def test_validation_error_hides_the_input(
    factory: Callable[[], BaseModel], field: str
) -> None:
    """Error messages reach exceptions and logs: they name the field, never the
    value."""
    data = {**factory().model_dump(), field: ["SECRET-INPUT"]}
    with pytest.raises(ValidationError) as exc_info:
        type(factory()).model_validate(data)
    assert field in str(exc_info.value)
    assert "SECRET-INPUT" not in str(exc_info.value)
