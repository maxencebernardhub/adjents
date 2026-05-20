# ADR 0002 — Separate Pydantic domain models from SQLModel persistence tables

**Date**: 2026-05-20
**Status**: Accepted

---

## Context

The project uses both Pydantic v2 (for data validation, API contracts, and business
logic) and SQLModel (for SQLite persistence). When building the database layer, two
structural approaches were available.

**Option A — Two distinct layers**: Pydantic `BaseModel` classes in each domain module
(`agents/models.py`, `messaging/models.py`, etc.) serve as the domain/API contract.
Separate SQLModel `table=True` classes in `db/` handle persistence. Explicit conversion
functions translate between the two.

**Option B — Single SQLModel layer**: Domain models inherit from `SQLModel` instead
of `BaseModel`, making each class serve both as a Pydantic model and a database table.
No conversion needed; no duplication of field definitions.

---

## Decision

We chose **Option A**: Pydantic domain models and SQLModel persistence tables are
separate classes. Conversion between them is explicit.

---

## Rationale

**Why not Option B (single SQLModel layer)**:

1. **SQLModel `table=True` imposes persistence-specific constraints** on field
   definitions: primary key annotations (`Field(primary_key=True)`), optional fields
   defaulting to `None`, and `__tablename__` declarations. These are persistence
   concerns that do not belong in the domain model layer.

2. **Our models contain non-native SQLite types** — `list[str]`, `dict[str, Any]` —
   that SQLModel cannot store natively. They require JSON serialization. Handling
   this at the SQLModel level forces validators and serialization logic into the domain
   model, mixing layers.

3. **FastAPI uses Pydantic models as response schemas**. If those models inherit from
   `SQLModel(table=True)`, SQLModel internals bleed into the API contract. Keeping
   `BaseModel` as the base preserves a clean API layer.

4. **Testability**: domain logic and agents can be tested without a database. If the
   domain model is also the table model, any unit test that instantiates an agent
   potentially drags in SQLModel's session mechanics.

**Why the duplication in Option A is acceptable**:

Domain models are stable once defined — they change only when the domain changes, not
when persistence details change. The duplication is bounded and mechanical (same field
names, same types). A future migration tool or a test can detect schema drift between
the two layers.

---

## Consequences

- `backend/adjents/db/tables.py` contains all SQLModel table definitions, mirroring
  the Pydantic models in their respective modules.
- `backend/adjents/db/convert.py` (or equivalent) provides `to_table()` / `from_table()`
  helpers for each model pair.
- Fields of type `list[str]` and `dict[str, Any]` are stored as JSON strings in SQLite
  and deserialized on read. This is handled exclusively in the `db/` layer.
- Adding a field to a domain model requires a matching change in the table class and
  a database migration.

---

## Alternatives considered

See Option B above. Rejected primarily because of the mixed-layer concerns and
FastAPI API contract implications.
