"""Conversions for the memory domain model (`memory/models.py`).

`Memory` ↔ `MemoryTable`, following the conventions of the `adjents.db.convert`
package docstring. `Memory.metadata` is stored in the `metadata_json` column.

Place in the flow: no production code calls these functions yet. Callers import
them from `adjents.db.convert`.

Entry points: `memory_to_table()`, `memory_from_table()`.

Related ADRs: 0002 (domain models vs tables).
"""

import json
from datetime import datetime

from adjents.db.tables import MemoryTable
from adjents.memory.models import Memory


def memory_to_table(mem: Memory) -> MemoryTable:
    return MemoryTable(
        id=mem.id,
        agent_id=mem.agent_id,
        content=mem.content,
        # The model rejects NaN / infinity at validation, not on assignment.
        metadata_json=json.dumps(mem.metadata, allow_nan=False),
        created_at=mem.created_at.isoformat(),
    )


def memory_from_table(row: MemoryTable) -> Memory:
    return Memory(
        id=row.id,
        agent_id=row.agent_id,
        content=row.content,
        metadata=json.loads(row.metadata_json),
        created_at=datetime.fromisoformat(row.created_at),
    )
