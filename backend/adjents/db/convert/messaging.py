"""Conversions for the messaging domain models (`messaging/models.py`).

`Message` and `Conversation` ↔ their tables, following the conventions of the
`adjents.db.convert` package docstring. `Message.metadata` is stored in the
`metadata_json` column.

Place in the flow: the Generator interview persists and reloads its conversation
through these functions. Team setup and reconfiguration build `MessageTable` rows
directly, without them. Callers import these functions from `adjents.db.convert`.

Entry points: `message_*`, `conversation_*` (`_to_table()` / `_from_table()`).

Related ADRs: 0002 (domain models vs tables).
"""

import json
from datetime import datetime

from adjents.db.tables import ConversationTable, MessageTable
from adjents.messaging.models import Conversation, Message

# --- Message ---


def message_to_table(msg: Message) -> MessageTable:
    return MessageTable(
        id=msg.id,
        from_agent=msg.from_agent,
        to_agent=msg.to_agent,
        content=msg.content,
        # The model rejects NaN / infinity at validation, not on assignment.
        metadata_json=json.dumps(msg.metadata, allow_nan=False),
        parent_message_id=msg.parent_message_id,
        created_at=msg.created_at.isoformat(),
    )


def message_from_table(row: MessageTable) -> Message:
    return Message(
        id=row.id,
        from_agent=row.from_agent,
        to_agent=row.to_agent,
        content=row.content,
        metadata=json.loads(row.metadata_json),
        parent_message_id=row.parent_message_id,
        created_at=datetime.fromisoformat(row.created_at),
    )


# --- Conversation ---


def conversation_to_table(conv: Conversation) -> ConversationTable:
    return ConversationTable(
        id=conv.id,
        participant_agents=json.dumps(conv.participant_agents),
        message_ids=json.dumps(conv.message_ids),
        started_at=conv.started_at.isoformat(),
    )


def conversation_from_table(row: ConversationTable) -> Conversation:
    return Conversation(
        id=row.id,
        participant_agents=json.loads(row.participant_agents),
        message_ids=json.loads(row.message_ids),
        started_at=datetime.fromisoformat(row.started_at),
    )
