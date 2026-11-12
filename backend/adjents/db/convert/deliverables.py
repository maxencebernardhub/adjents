"""Conversions for the deliverable domain model (`deliverables/models.py`).

`Deliverable` ↔ `DeliverableTable`, following the conventions of the
`adjents.db.convert` package docstring.

Place in the flow: no production code calls these functions yet. Callers import
them from `adjents.db.convert`.

Entry points: `deliverable_to_table()`, `deliverable_from_table()`.

Related ADRs: 0002 (domain models vs tables).
"""

from datetime import datetime

from adjents.db.tables import DeliverableTable
from adjents.deliverables.models import Deliverable


def deliverable_to_table(d: Deliverable) -> DeliverableTable:
    return DeliverableTable(
        id=d.id,
        agent_id=d.agent_id,
        project_id=d.project_id,
        title=d.title,
        file_path=d.file_path,
        created_at=d.created_at.isoformat(),
    )


def deliverable_from_table(row: DeliverableTable) -> Deliverable:
    return Deliverable(
        id=row.id,
        agent_id=row.agent_id,
        project_id=row.project_id,
        title=row.title,
        file_path=row.file_path,
        created_at=datetime.fromisoformat(row.created_at),
    )
