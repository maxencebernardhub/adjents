"""Core data models for memory: Memory."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Memory(BaseModel):
    id: str
    agent_id: str | None  # None = global knowledge base entry
    content: str
    metadata: dict[str, Any]
    created_at: datetime
