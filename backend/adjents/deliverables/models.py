"""Deliverable domain model: Deliverable.

A deliverable is a file an agent produces, written under `data/outputs/`
(ARCHITECTURE §10). v0.1 writes no file outside `./data/`.

Place in the flow: domain / API layer (ADR 0002). No code produces or reads it yet:
it waits for the agent loop and the Deliverables feature. A persistence table and
conversion functions exist in `db/tables.py` and `db/convert/deliverables.py`.

Entry points: `Deliverable`.

Related ADRs: 0002 (domain models vs tables).
"""

from pydantic import AwareDatetime, BaseModel, ConfigDict


class Deliverable(BaseModel):
    """A file produced by an agent, during daily work or for a project.

    `created_at` must carry a timezone; validation errors never include the input
    value.

    Attributes:
        id: UUID.
        agent_id: Id of the producing agent.
        project_id: Id of the related `Project`; None if produced during daily
            operations.
        title: Display title.
        file_path: Path of the file, relative to `data/outputs/`.
        created_at: Creation time.
    """

    model_config = ConfigDict(hide_input_in_errors=True)

    id: str
    agent_id: str
    project_id: str | None
    title: str
    file_path: str
    created_at: AwareDatetime
