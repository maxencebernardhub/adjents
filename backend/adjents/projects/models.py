"""Core data models for projects: Project, ProjectStatus (v0.2 feature)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Project(BaseModel):
    id: str
    title: str
    objective: str
    deliverable_descriptions: list[str]
    deadline: datetime | None
    lead_agent_id: str
    contributor_agent_ids: list[str]
    status: ProjectStatus
    created_at: datetime
