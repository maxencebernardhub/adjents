"""Core data models for deliverables: Deliverable."""

from datetime import datetime

from pydantic import BaseModel


class Deliverable(BaseModel):
    id: str
    agent_id: str
    project_id: str | None  # None if produced during daily operations
    title: str
    file_path: str  # relative path under data/outputs/
    created_at: datetime
