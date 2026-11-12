"""Memory domain model: Memory.

Agent memory lives in Chroma: one namespaced collection per agent plus a shared
global knowledge base (ARCHITECTURE §7). A `Memory` is one entry of either.

Place in the flow: domain / API layer (ADR 0002). No code produces or reads it yet:
it waits for the memory layer. A persistence table and conversion functions exist
in `db/tables.py` and `db/convert/memory.py`.

Entry points: `Memory`.

Related ADRs: 0002 (domain models vs tables).
"""

from pydantic import AwareDatetime, BaseModel, ConfigDict, JsonValue


class Memory(BaseModel):
    """One entry of an agent's memory or of the global knowledge base.

    The embedding is computed and stored by Chroma, not held here. Validation
    errors never include the input value (memories hold business data).

    Attributes:
        id: UUID.
        agent_id: Id of the owning agent; None for a global knowledge base entry.
        content: The remembered text.
        metadata: Free-form data stored alongside the entry, JSON values only: no
            datetime, tuple or set, no NaN or infinity (it is stored as JSON text).
        created_at: Creation time; must carry a timezone.
    """

    model_config = ConfigDict(hide_input_in_errors=True, allow_inf_nan=False)

    id: str
    agent_id: str | None
    content: str
    metadata: dict[str, JsonValue]
    created_at: AwareDatetime
