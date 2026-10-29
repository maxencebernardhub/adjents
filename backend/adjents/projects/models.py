"""Project domain models: Project, ProjectStatus (v0.2 feature).

A project is a time-bound objective led by one agent with contributors, producing
deliverables. The feature lands in v0.2; the models are defined ahead because their
shape is known and the database schema stays complete (same reasoning as ADR 0004).

Place in the flow: domain / API layer (ADR 0002). No code produces or reads them yet.
A persistence table and conversion functions exist in `db/tables.py` and
`db/convert.py`.

Entry points: `Project`, `ProjectStatus`.

Related ADRs: 0002 (domain models vs tables), 0004 (precedent for defining an
entity ahead of its feature).
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ProjectStatus(StrEnum):
    """Lifecycle status of a project, stored as its string value.

    Attributes:
        ACTIVE: In progress.
        COMPLETED: Objective reached.
        CANCELLED: Stopped before completion.
    """

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Project(BaseModel):
    """A time-bound objective with a lead agent and contributors.

    Attributes:
        id: UUID.
        title: Short name.
        objective: What the project must achieve.
        deliverable_descriptions: Expected deliverables, one per item.
        deadline: Due date; None if open-ended.
        lead_agent_id: Id of the agent leading the project.
        contributor_agent_ids: Ids of the contributing agents.
        status: Current `ProjectStatus`.
        created_at: Creation time.
    """

    id: str
    title: str
    objective: str
    deliverable_descriptions: list[str]
    deadline: datetime | None
    lead_agent_id: str
    contributor_agent_ids: list[str]
    status: ProjectStatus
    created_at: datetime
