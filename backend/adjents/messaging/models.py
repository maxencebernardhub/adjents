"""Messaging domain models: Message, Conversation.

`Message` is the unit of agent-to-agent and agent-to-user communication; agents
communicate only by exchanging messages, never by calling each other (ARCHITECTURE
§4). The `MessageDispatcher` that will route them does not exist yet.

Place in the flow: domain / API layer (ADR 0002). Today only the Generator interview
(`generator/interview.py`) builds `Message` and `Conversation` objects; team setup
and reconfiguration write message rows directly through `db/tables.py`. Persistence
goes through `db/convert/messaging.py`.

Entry points: `Message`, `Conversation`.

Related ADRs: 0002 (domain models vs tables).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Message(BaseModel):
    """One message between two participants.

    A message carries no conversation id: the interview groups its messages
    through `Conversation.message_ids`, while team setup and reconfiguration store
    their conversation id under `metadata["conv_id"]`.

    Attributes:
        id: UUID.
        from_agent: Sender: an agent id, or a sentinel — "user", "generator"
            (the Generator Agent, which has no `AgentSpec`) or "system" (planned
            in ARCHITECTURE §3, used by no code yet).
        to_agent: Recipient: an agent id or a sentinel, as for `from_agent`.
        content: Message text.
        metadata: Free-form routing and tracing data.
        parent_message_id: Id of the message this one replies to, for threading;
            None for a thread start.
        created_at: Send time.
    """

    id: str
    from_agent: str
    to_agent: str
    content: str
    metadata: dict[str, Any]
    parent_message_id: str | None
    created_at: datetime


class Conversation(BaseModel):
    """An ordered sequence of messages between participants.

    Attributes:
        id: UUID.
        participant_agents: Participant ids, sentinels included (e.g.
            ["generator", "user"] for the interview).
        message_ids: Ids of the conversation's messages, in send order.
        started_at: Start time.
    """

    id: str
    participant_agents: list[str]
    message_ids: list[str]
    started_at: datetime
