"""Core data models for messaging: Message, Conversation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Message(BaseModel):
    id: str
    from_agent: str  # agent_id, "user", or "system"
    to_agent: str  # agent_id or "user"
    content: str
    metadata: dict[str, Any]
    parent_message_id: str | None  # for threading
    created_at: datetime


class Conversation(BaseModel):
    id: str
    participant_agents: list[str]
    message_ids: list[str]  # ordered
    started_at: datetime
