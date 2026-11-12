"""Conversions for the project domain model (`projects/models.py`, v0.2).

`Project` ↔ `ProjectTable`, following the conventions of the `adjents.db.convert`
package docstring.

Place in the flow: no production code calls these functions yet. Callers import
them from `adjents.db.convert`.

Entry points: `project_to_table()`, `project_from_table()`.

Related ADRs: 0002 (domain models vs tables), 0004 (models defined ahead of their
feature).
"""

import json
from datetime import datetime

from adjents.db.tables import ProjectTable
from adjents.projects.models import Project, ProjectStatus


def project_to_table(proj: Project) -> ProjectTable:
    return ProjectTable(
        id=proj.id,
        title=proj.title,
        objective=proj.objective,
        deliverable_descriptions=json.dumps(proj.deliverable_descriptions),
        deadline=proj.deadline.isoformat() if proj.deadline is not None else None,
        lead_agent_id=proj.lead_agent_id,
        contributor_agent_ids=json.dumps(proj.contributor_agent_ids),
        status=str(proj.status),
        created_at=proj.created_at.isoformat(),
    )


def project_from_table(row: ProjectTable) -> Project:
    return Project(
        id=row.id,
        title=row.title,
        objective=row.objective,
        deliverable_descriptions=json.loads(row.deliverable_descriptions),
        deadline=datetime.fromisoformat(row.deadline)
        if row.deadline is not None
        else None,
        lead_agent_id=row.lead_agent_id,
        contributor_agent_ids=json.loads(row.contributor_agent_ids),
        status=ProjectStatus(row.status),
        created_at=datetime.fromisoformat(row.created_at),
    )
