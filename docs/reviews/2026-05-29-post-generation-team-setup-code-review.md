# Code Review — Post-generation team setup

**Date**: 2026-05-29
**Branch**: `feat/post-generation-team-setup`
**Reviewer**: code-reviewer subagent (claude-sonnet-4-6)
**Scope**: Backend Python — full diff vs `main`
**Static analysis**: `mypy --strict` ✅ | `ruff` ✅ | 244 tests ✅
**Verdict**: ⚠️ Changes requested (2 blockers)

---

## Executive summary

The branch is structurally solid: architecture respected, ADRs well written, static
analysis clean. Two blocking issues must be resolved before merge: a silent data
corruption bug in `_apply_agent_updates`, and a file size violation (839 lines vs the
300-line limit). Five warnings address missing state guards and robustness gaps. Three
notes are informational.

---

## Blockers

### B1 — Silent JSON corruption of `responsibilities` / `escalation_rules`

**Files**: `team_setup.py:581`, `reconfiguration.py:172`

#### B1 — Problem

`AgentSpecTable.responsibilities` and `AgentSpecTable.escalation_rules` are `str`
columns holding serialized JSON (declared explicitly in `tables.py`):

```python
# tables.py:20-22
responsibilities: str = Field(default="[]")   # JSON: list[str]
skill_ids: str = Field(default="[]")          # JSON: list[str]
escalation_rules: str = Field(default="[]")   # JSON: list[str]
```

When the LLM extracts these fields it returns native Python types (as the prompt
instructs):

```json
{
  "agent_id": "abc",
  "fields": {
    "responsibilities": ["Manage operations", "Hire the team"]
  }
}
```

`_apply_agent_updates` then does a generic `setattr` over all keys:

```python
# BEFORE — team_setup.py:565-581
for key, value in fields.items():
    if key in _FROZEN_FIELDS:
        _log.warning("Dropping frozen field %r for agent %s", key, agent_id)
        continue
    if key == "visual_character" and value not in VALID_VISUAL_CHARACTERS:
        _log.warning("Dropping invalid visual_character: %r", value)
        continue
    if key == "scheduler_interval_seconds":
        raw = int(value)
        clamped = max(_INTERVAL_MIN, min(_INTERVAL_MAX, raw))
        if clamped != raw:
            _log.warning("scheduler_interval_seconds clamped to %d", clamped)
        value = clamped
    setattr(spec_row, key, value)   # ← Python list written directly to a str column
```

SQLite/SQLModel silently accepts writing a Python `list` into a `str` column. The
stored value becomes `"['Manage operations', 'Hire the team']"` — Python repr, not
valid JSON. The next read via `agent_spec_from_table` calls
`json.loads(row.responsibilities)` and raises `JSONDecodeError`.

**This bug is silent**: no exception at write time, failure only at next read.
Agent data is permanently corrupted.

#### B1 — After fix

```python
# AFTER
_JSON_LIST_FIELDS = frozenset({"responsibilities", "escalation_rules"})

for key, value in fields.items():
    if key in _FROZEN_FIELDS:
        _log.warning("Dropping frozen field %r for agent %s", key, agent_id)
        continue
    if key == "visual_character" and value not in VALID_VISUAL_CHARACTERS:
        _log.warning("Dropping invalid visual_character: %r", value)
        continue
    if key == "scheduler_interval_seconds":
        raw = int(value)
        clamped = max(_INTERVAL_MIN, min(_INTERVAL_MAX, raw))
        if clamped != raw:
            _log.warning("scheduler_interval_seconds clamped to %d", clamped)
        value = clamped
    if key in _JSON_LIST_FIELDS:
        value = json.dumps(value) if isinstance(value, list) else value
    setattr(spec_row, key, value)
```

The same fix must be applied to **both copies** of `_apply_agent_updates`
(`team_setup.py` and `reconfiguration.py`).

Note: `skill_ids` is not affected here — it is never exposed directly in
`agent_updates.fields` and is managed separately via `skills_to_add/remove/update`.

#### B1 — Missing tests

No current test covers this case. Add to both test files:

```python
async def test_apply_updates_json_list_fields_are_serialized(mini_org, ...):
    # Simulate an LLM extraction returning responsibilities as a Python list
    updates = [{
        "agent_id": coo_id,
        "fields": {"responsibilities": ["R1", "R2"]},
        "skills_to_add": [], "skills_to_remove": [], "skills_to_update": []
    }]
    await orchestrator._apply_agent_updates(updates)
    # Verify that re-reading does not raise JSONDecodeError
    spec_row = await session.get(AgentSpecTable, coo_id)
    parsed = json.loads(spec_row.responsibilities)
    assert parsed == ["R1", "R2"]
```

#### B1 — Pros

- Fixes a real, silent data corruption bug
- Aligns behavior with the already-correct handling of `skill.inputs/outputs`
  (line 648: `setattr(s_row, k, json.dumps(v))`)

#### B1 — Cons

- None. The fix is trivial and carries zero regression risk.

#### B1 — Recommendation

Fix before merge, no discussion needed.

---

### B2 — `team_setup.py` is 839 lines (project limit: 300)

**File**: `team_setup.py`

#### B2 — Problem

`CLAUDE.md` and `ARCHITECTURE.md` enforce `no >300-line files` with no documented
exception. `team_setup.py` is 839 lines — nearly 3× the limit.

The file currently holds two distinct responsibilities:

1. **Domain models**: `AgentValidationStatus`, `ValidationSession`,
   `AgentValidationRecord`, `_advance_traversal` (pure, no I/O) — ~80 lines
2. **Orchestrator**: `TeamSetupOrchestrator` with all its methods — ~760 lines

#### B2 — Natural split

```text
# BEFORE
backend/adjents/generator/
  team_setup.py              # 839 lines — everything mixed

# AFTER (first pass)
backend/adjents/generator/
  team_setup_models.py       # ~100 lines — enums, Pydantic models, _advance_traversal
  team_setup.py              # ~760 lines — TeamSetupOrchestrator only
```

This first pass brings `team_setup.py` to ~760 lines. If the 300-line rule must be
strictly enforced, a second pass could extract DB helpers (`_load_*`, `_save_*`,
`_set_*`, `_append_message`) into `team_setup_db.py` (~200 lines) and LLM helpers
(`_build_transcript`, `_call_extraction_llm`, `_apply_agent_updates`) into
`team_setup_llm.py` (~150 lines), leaving `team_setup.py` with only the public
API (~250 lines).

#### B2 — Pros

- Respects the explicit project convention
- Improves navigability: finding `_advance_traversal` no longer requires scrolling
  800 lines
- Eases future reviews

#### B2 — Cons

- Mechanical but non-trivial refactor: ~15 imports to update across tests and
  consuming modules
- Risk of circular import regressions if not planned carefully (see Warning A3)
- Zero functional value

#### B2 — Recommendation

Fix before merge if the rule is non-negotiable. If the project accepts a documented
exception for orchestrators (a common pattern in strict TDD projects), document it in
`CLAUDE.md` with an alternative cap (e.g. 500 lines for orchestrators).
**The current rule has no exception.**

---

## Warnings

### A1 — `assert` used as flow control (5 occurrences)

**File**: `team_setup.py:207, 276, 299, 303, 319`

#### A1 — Problem

```python
# BEFORE — team_setup.py:207, 276, 299, 303, 319
assert record.active_conversation_id is not None
assert record.active_agent_id is not None
assert root_spec_row is not None
assert next_spec_row is not None
```

Python assertions can be disabled with the `-O` flag. More importantly, they raise
`AssertionError` with no useful message, whereas business errors should raise
`TeamSetupError` with an actionable message.

#### A1 — After fix

```python
# AFTER
if record.active_conversation_id is None:
    raise TeamSetupError(
        f"Record for {root_agent_id} is IN_PROGRESS but has no active conversation."
    )
if record.active_agent_id is None:
    raise TeamSetupError(
        f"Record for {root_agent_id} is IN_PROGRESS but has no active agent."
    )
```

#### A1 — Pros

- Actionable error messages in production
- Consistent with the rest of the codebase, which already raises `TeamSetupError`
- Resilient to `python -O`

#### A1 — Cons

- Slightly more verbose (~3 lines per replaced assert)

#### A1 — Recommendation

Fix (trivial, consistency with existing code).

---

### A2 — `validate_team` does not guard against an incomplete traversal

**File**: `team_setup.py:393`

#### A2 — Problem

```python
# BEFORE — team_setup.py:393-408
async def validate_team(self, session_id: str, root_agent_id: str) -> None:
    record = await self._load_record(session_id, root_agent_id)
    transcript = self._build_transcript(record)    # uses conversation_ids
    updates = await self._call_extraction_llm([transcript])
    await self._apply_agent_updates(updates.get("agent_updates", []))
    ...
```

If `validate_team` is called while `navigation_stack != []` (traversal still in
progress), the extraction LLM works on an incomplete transcript: conversations from
unvisited N-2 agents are missing. The extraction can silently miss entire sub-agents.

The spec (Feature Brief, acceptance criterion line 72) states this case is "allowed"
(extract on what has been done), but without a warning the caller has no visibility
that they are validating a partial traversal.

#### A2 — After fix

```python
# AFTER — option 1: strict refusal
async def validate_team(self, session_id: str, root_agent_id: str) -> None:
    record = await self._load_record(session_id, root_agent_id)
    if record.navigation_stack:
        raise TeamSetupError(
            "Cannot validate: traversal is not complete "
            f"(remaining stack: {record.navigation_stack})."
        )
    ...

# AFTER — option 2: warning + continue
async def validate_team(self, session_id: str, root_agent_id: str) -> None:
    record = await self._load_record(session_id, root_agent_id)
    if record.navigation_stack:
        _log.warning(
            "validate_team called with incomplete traversal for %s "
            "(stack: %s) — extraction will only cover visited agents.",
            root_agent_id, record.navigation_stack
        )
    ...
```

#### A2 — Pros

- Option 1 protects against silent misuse
- Option 2 preserves spec flexibility while making the state visible

#### A2 — Cons

- Option 1 breaks the flexibility documented in the spec (line 72) and requires
  updating the spec

#### A2 — Recommendation

Option 2 (warning log) — preserves spec flexibility while making the
partial-traversal case observable.

---

### A3 — Top-level import in `convert.py` creates a latent circular dependency

**File**: `backend/adjents/db/convert.py`

#### A3 — Problem

`convert.py` imports at module level:

```python
# convert.py (top-level import)
from adjents.generator.team_setup import (
    AgentValidationRecord,
    AgentValidationStatus,
    ValidationSession,
)
```

`team_setup.py` in turn imports `convert.py` via **local imports** (inside methods,
not at module level):

```python
# team_setup.py — local imports inside methods
async def start_session(self) -> ValidationSession:
    from adjents.db.convert import (
        agent_validation_record_to_table,
        validation_session_to_table,
    )
```

This works today because of the local imports. But if a future developer moves those
imports to module level in `team_setup.py` (a natural "cleanup" reflex), it creates a
fatal import cycle.

#### A3 — Recommended fix

Extract domain models into a dependency-free module (`team_setup_models.py` as
described in B2), and have `convert.py` import from there instead of `team_setup.py`.
The cycle risk is eliminated entirely.

#### A3 — Pros

- Permanently eliminates the cycle risk
- Clarifies dependency direction: `convert` ← `models` (unidirectional)

#### A3 — Cons

- Requires the B2 split first, or a dedicated intermediate module

#### A3 — Recommendation

Address together with B2.

---

### A4 — Session resumability is misleading after a server restart

**File**: `team_setup.py:128-130, 206-221`

#### A4 — Problem

`_conv_messages: dict[str, list[dict[str, str]]]` is an in-memory instance attribute.
**Messages are written to SQLite** (`MessageTable` via `_append_message`), but when
resuming, the LLM context is rebuilt from the in-memory dict, not from the database:

```python
# BEFORE — team_setup.py:212
msgs = list(self._conv_messages.get(conv_id, []))  # in-memory dict, empty after restart
nudge = "Please continue our conversation."
msgs.append({"role": "user", "content": nudge})
response = await self._client.complete(msgs, ...)
```

If the server restarts between two turns of a conversation:

1. `self._conv_messages` is empty
2. `msgs = []`
3. The LLM receives only `"Please continue our conversation."` with no agent context
4. Its response is generic or incoherent

The messages are in the database — they are simply never read back.

#### A4 — After fix

```python
# AFTER — utility method to add
async def _load_conv_messages(self, conv_id: str) -> list[dict[str, str]]:
    """Reconstruct messages from MessageTable if not cached in-memory."""
    if conv_id in self._conv_messages:
        return list(self._conv_messages[conv_id])
    rows = (
        await self._session.exec(
            select(MessageTable).where(
                MessageTable.metadata_json.contains(conv_id)  # type: ignore
            ).order_by(MessageTable.created_at)
        )
    ).all()
    msgs = []
    for row in rows:
        role = "user" if row.from_agent == "user" else "assistant"
        msgs.append({"role": role, "content": row.content})
    self._conv_messages[conv_id] = msgs
    return list(msgs)

# In start_agent_conversation (resume branch)
msgs = await self._load_conv_messages(conv_id)
```

Note: the `contains(conv_id)` query on `metadata_json` is fragile (text search, no
index, possible collision if one conv_id is a prefix of another). A clean fix
requires adding a dedicated indexed `conv_id` column to `MessageTable`, which is a
schema migration.

#### A4 — Pros

- Resume actually works after a server restart
- Reuses data that is already persisted — no new storage required

#### A4 — Cons

- The `contains(conv_id)` query is fragile without a schema migration
- Proper fix requires a schema migration (indexed `conv_id` column)
- Likely v0.2 scope

#### A4 — Recommendation

Document the limitation in the `resume_session()` docstring for v0.1. Implement
proper reconstruction in v0.2 with a schema migration.

---

### A5 — No guard against `reply()` called before `start()`

**Files**: `reconfiguration.py:81`, `team_setup.py:272`

#### A5 — Problem

```python
# BEFORE — reconfiguration.py:81
async def reply(self, message: str) -> str:
    self._messages.append({"role": "user", "content": message})
    intro_prompt = self._prompts.get("agent/intro")
    response = await self._client.complete(self._messages, system=intro_prompt.content)
    # If start() was never called: self._messages = [], LLM called without agent context
```

If `reply()` is called without a prior `start()`:

- `self._messages` is empty
- The LLM receives only the user message with no agent context
- The resulting transcript for extraction contains no agent data
- `apply_changes()` extracts updates without a baseline, potentially producing
  empty or incorrect results

#### A5 — After fix

```python
# AFTER — reconfiguration.py
async def reply(self, message: str) -> str:
    if not self._messages:
        raise TeamSetupError(
            "reply() called before start() — no conversation context available."
        )
    ...
```

#### A5 — Pros

- Fast, explicit failure instead of silently incorrect behavior
- The error is immediately traceable

#### A5 — Cons

- None

#### A5 — Recommendation

Fix (one line, zero risk).

---

## Notes

### N1 — `__all__` re-exports symbols defined elsewhere

**File**: `team_setup.py:62-70`

```python
# team_setup.py:62-70
__all__ = [
    ...
    "TeamSetupError",                # defined in adjents.errors
    "_build_agent_context_message",  # defined in adjents.utils.agent_context
]
```

Both symbols are imported into `team_setup.py` but not defined there. Re-exporting
them in `__all__` falsely implies they belong to this module. No known consumer
imports them from `team_setup.py`. Remove both entries.

---

### N2 — `_build_agent_context_message`: private name for a shared utility

**File**: `adjents/utils/agent_context.py`

The `_` prefix implies internal use (Python convention). But the function is used
across two distinct modules (`team_setup.py` and `reconfiguration.py`) and re-exported
in `team_setup.py`'s `__all__`. If it is intended as a shared utility,
`build_agent_context_message` would be more consistent.

ADR 0008 documents this decision — it is intentional. Style note only.

---

### N3 — 1 SQLite commit per `_append_message`

**Files**: `team_setup.py:839`, `reconfiguration.py:300`

A 5-turn exchange triggers ~10 sequential commits. In SQLite local/v0.1, this has no
measurable impact. Batch into one commit per business operation in v0.2.

---

## Decision matrix

| ID | Severity | Effort | Priority |
| --- | --- | --- | --- |
| B1 — JSON corruption in `_apply_agent_updates` | Blocker | Low (5 lines × 2) | Immediate |
| B2 — `team_setup.py` size (839 lines) | Blocker | Medium (refactor) | Before merge |
| A1 — `assert` as flow control | Warning | Low | Recommended |
| A2 — `validate_team` missing traversal guard | Warning | Low (warning log) | Recommended |
| A3 — Latent circular dependency in `convert` | Warning | Medium (with B2) | Handle with B2 |
| A4 — In-memory resume not reconstructed | Warning | Medium (+ migration) | Document v0.1, fix v0.2 |
| A5 — `reply()` missing `start()` guard | Warning | Trivial (1 line × 2) | Recommended |
| N1 — Inconsistent `__all__` | Note | Trivial | Optional |
| N2 — `_build_agent_context_message` name | Note | Trivial | Optional |
| N3 — Commits per message | Note | — | v0.2 |

---

## Verdict

```text
[ ] Approved
[ ] Approved with minor fixes
[x] Changes requested
```

**Blockers to resolve before merge**:

1. **B1**: Add conditional JSON serialization in `_apply_agent_updates` (both copies)
   and tests covering `responsibilities` and `escalation_rules`.
2. **B2**: Split `team_setup.py` or document an explicit exception to the 300-line
   rule in `CLAUDE.md`.
