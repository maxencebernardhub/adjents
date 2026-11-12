"""Conversion functions between Pydantic domain models and SQLModel tables.

The only bridge between the two layers of ADR 0002: each domain model has an
`<model>_to_table()` function (domain → row) and an `<model>_from_table()` function
(row → domain). Every function maps every field explicitly, by name. The shared
conventions:

- `list[str]` and `dict[str, JsonValue]` fields: `json.dumps()` / `json.loads()`;
  the `metadata` dumps pass `allow_nan=False`, so NaN or infinity added after
  validation raises a `ValueError` instead of writing invalid JSON.
- `datetime` fields: `isoformat()` / `datetime.fromisoformat()`. The roundtrip
  keeps the value and its UTC offset. The domain models accept only
  timezone-aware datetimes, so a naive date stored in a row fails at
  `*_from_table()`.
- `StrEnum` fields: stored as their string value with `str()`, rebuilt with the
  enum constructor.
- `metadata` fields: stored in the `metadata_json` column.

`*_from_table()` functions repair nothing. A malformed row raises a `ValueError`
subclass: `json.JSONDecodeError` for invalid JSON, `ValueError` for an unknown
enum value or an invalid date, `pydantic.ValidationError` for a value of the wrong
type.

One submodule per domain module, re-exported here: `agents`, `messaging`, `memory`,
`projects`, `deliverables`, `generator`. Callers import from this package, not
from the submodules.

Place in the flow: called by the orchestrators (`generator/interview.py`,
`generator/org_generation.py`, `generator/team_setup.py`,
`agents/reconfiguration.py`) before `session.add()` and after reading rows; by
`tests/conftest.py` to insert fixtures. Importing this package imports
`generator/team_setup.py` (through the `generator` submodule), which therefore
imports this package lazily, inside its methods, to avoid a circular import.

Entry points: the 24 `*_to_table()` / `*_from_table()` functions.

Related ADRs: 0002 (domain models vs tables).
"""

from adjents.db.convert.agents import (
    agent_spec_from_table,
    agent_spec_to_table,
    agent_state_from_table,
    agent_state_to_table,
    blocking_question_from_table,
    blocking_question_to_table,
    skill_from_table,
    skill_to_table,
)
from adjents.db.convert.deliverables import (
    deliverable_from_table,
    deliverable_to_table,
)
from adjents.db.convert.generator import (
    agent_validation_record_from_table,
    agent_validation_record_to_table,
    business_context_from_table,
    business_context_to_table,
    validation_session_from_table,
    validation_session_to_table,
)
from adjents.db.convert.memory import memory_from_table, memory_to_table
from adjents.db.convert.messaging import (
    conversation_from_table,
    conversation_to_table,
    message_from_table,
    message_to_table,
)
from adjents.db.convert.projects import project_from_table, project_to_table

__all__ = [
    "agent_spec_from_table",
    "agent_spec_to_table",
    "agent_state_from_table",
    "agent_state_to_table",
    "agent_validation_record_from_table",
    "agent_validation_record_to_table",
    "blocking_question_from_table",
    "blocking_question_to_table",
    "business_context_from_table",
    "business_context_to_table",
    "conversation_from_table",
    "conversation_to_table",
    "deliverable_from_table",
    "deliverable_to_table",
    "memory_from_table",
    "memory_to_table",
    "message_from_table",
    "message_to_table",
    "project_from_table",
    "project_to_table",
    "skill_from_table",
    "skill_to_table",
    "validation_session_from_table",
    "validation_session_to_table",
]
