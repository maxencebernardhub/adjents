# Walkthrough — Step 4: foundations

> Branch: `refactor/walkthrough-foundations` · Started: 2026-10-23
> Plan: `PROJECT_STATE.md` → Next steps → Step 4.

Walkthrough notes for the foundation modules: domain models (4.1), database layer
(4.2), prompts / LLM client / router (4.3). For each file: role and place in the flow,
design choices and their trade-offs, library idioms, test coverage. Then the questions
asked during the walkthrough, the answers, the findings and the decisions taken.

Findings feed steps 4.4 (docstrings), 4.5 (spec review), 4.6 (code review) and 4.7
(fixes with TDD). Nothing is fixed during the reading (4.1 → 4.3).

Every library behavior stated here was checked by running code against the installed
versions (Pydantic 2.14.1, SQLAlchemy 2.1.6, SQLModel 0.0.48, aiosqlite 0.22.1,
pytest-asyncio 1.4.0), not from memory.

---

## 4.0 — Setup

- Branch created from `main` at `307795e` (PR #4 merge commit).
- `PROJECT_STATE.md`: step 3 "Stopped at" corrected (PR #4 merged on 2026-10-22, branch
  deleted, CI green on main); header updated. Commit `f29a0ee`.
- `make lint && make typecheck && make test`: green, 282 tests.

---

## 4.1 — Domain models

Files read (tests first): `test_models_agents.py` → `agents/models.py`,
`test_models_messaging.py` → `messaging/models.py`, `test_models_memory.py` →
`memory/models.py`, `test_models_projects.py` → `projects/models.py`,
`test_models_deliverables.py` → `deliverables/models.py`, `test_models_generator.py` →
`generator/models.py`.

### Place in the flow

- These modules are the **domain / API layer** of ADR 0002: plain Pydantic
  `BaseModel` classes, no database import.
- They call nothing. They are imported by `db/convert.py` (all of them),
  `generator/interview.py`, `generator/org_generation.py`, `generator/team_setup.py`,
  `agents/reconfiguration.py` and `utils/agent_context.py`.
- No FastAPI route uses them yet (`api/` is empty): their "API response schema" role
  is still an intention.

### Conformance with ARCHITECTURE §3

The 9 models sketched in §3 (`AgentSpec`, `AgentState`, `AgentStatus`, `Skill`,
`Message`, `Conversation`, `Memory`, `Project`, `Deliverable`, `BlockingQuestion`)
match the code field by field. `BlockingQuestion` matches ADR 0004 exactly.
`BusinessContext` is missing from §3 (F7).

### Shared design choices

| Choice | Benefit | Cost |
| --- | --- | --- |
| **No field has a default**, not even nullable ones (`work_hours: str \| None`) | Explicit construction everywhere; an LLM JSON must be complete; adding a field breaks every call site, so nothing is forgotten | Verbose construction (15 lines per `AgentSpec` in tests) |
| **No constraint, no validator** (`Field(ge=...)`, `Literal`, `@model_validator`) | Pure data containers, trivial to write and test | Invariants live elsewhere, duplicated with diverging policies (F3); a direct table writer bypasses them |
| **Mutable models**, assignment not validated | Simplicity | `spec.level = "N-1"` is accepted (checked) |
| **`extra` left at its default (`"ignore"`)** | Tolerates extra keys | Unknown keys in an LLM JSON are dropped silently (see Q&A B3) |

No written decision explains the absence of constraints (not in ADR 0002, the
2026-05-20 session, or ARCHITECTURE §3): the models were transcribed from the §3
sketches, which only give types. It is an absence of decision rather than a choice.
At the time, the only producer of agents (org generation) validated on its own.

### Pydantic v2 idioms

| Idiom | What to know |
| --- | --- |
| `X \| None` without default | **Required but nullable**: the key must be present, its value may be `null`. A missing key → `ValidationError` (`missing`). Opposite of Pydantic v1, where `Optional` implied `= None`. Matters when parsing LLM output. |
| Lax mode (default) | `"5"` → `5`, `True` → `1`, `5.0` → `5`; `5.5` rejected. For `str`, `123` is rejected (v2 no longer coerces int → str). `ConfigDict(strict=True)` disables coercion. |
| `StrEnum` (Python 3.11+) | Members *are* `str`: `AgentStatus.IDLE == "idle"` is `True` at runtime; JSON holds the value. `model_dump()` keeps the enum member, `model_dump(mode="json")` gives a `str`. |
| `Literal[...]` vs `StrEnum` | Both restrict a field to a finite set. `Literal` is a type annotation (plain `str` values, no class, no names); `StrEnum` is a class with named members, iterable, reusable. `Literal[0, 1, 2]` was rejected for `level` (no depth cap). `visual_character` has neither (free `str`). |
| `Field(...)` | Attaches constraints (`ge`, `le`, `gt`, `lt`, `min_length`, `pattern`) and metadata (`description`) to a field, usually via `Annotated[int, Field(ge=0)]`. Checked at construction; also emitted in `model_json_schema()` (used by FastAPI docs and, from step 4b, structured outputs). Today `level` is only `{'type': 'integer'}`. |
| `@field_validator` / `@model_validator` | Custom validation of one field / of the whole object (cross-field rules, e.g. `answered` ⇔ `answer is not None`). `mode="after"` runs after field validation and returns `self`. None is used here. |
| `model_validate(dict)` / `model_validate_json(str)` | Validate from a dict / from raw JSON. `model_dump()` / `model_dump_json()` go the other way. |
| `model_copy(update=...)` | **Does not validate.** Checked: with `level: Literal[0, 1, 2]`, `model_copy(update={"level": 5})` yields `level=5`. |
| `==` between models | Same class and same field values. |
| Validation points | Pydantic validates only at entry points (constructor, `model_validate*`). Python annotations are not enforced at runtime, so a later assignment is a plain `setattr`. mypy catches `spec.level = "N-1"` written literally, not `setattr(obj, key, value)` with an `Any` value from an LLM JSON. |
| `ConfigDict(validate_assignment=True)` | Every assignment is validated like the constructor. |
| `ConfigDict(frozen=True)` | The instance is immutable (assignment raises) and hashable; "changing" it means `model_copy(update=...)` (which does not validate). |
| `ConfigDict(extra=...)` | Keys matching no field: `"ignore"` (default, dropped silently), `"allow"` (kept), `"forbid"` (`ValidationError`). |
| `datetime` | A **naive** datetime is accepted; a `"...Z"` string is parsed as aware. `AwareDatetime` requires a timezone. |
| SQLModel `table=True` classes | **Do not validate** — even at construction. Checked: `AgentSpecTable(level="N-1", scheduler_interval_seconds=-5, ...)` is accepted. (Detailed in 4.2.) |

### Per file

**`agents/models.py` (60 lines)**

- `AgentSpec` / `AgentState` split by rate of change (§3): the spec is written once,
  the state changes many times per minute and is broadcast over WebSocket.
- `level: int`, not `Literal`: no depth cap (VISION §3.1). "Agents are data"
  (ADR 0010): the COO is `level == 0`, not a subclass.
- `skill_ids`: the link goes from the agent to its skills only; `Skill` has no
  `agent_id`.
- `BlockingQuestion` defined ahead of its first consumer (ADR 0004: schema fully
  determined by the WebSocket protocol).
- `is_paused` sits in the "static" spec although it changes at runtime (pause /
  resume), and duplicates `AgentStatus.PAUSED` in `AgentState` (F6).

**`messaging/models.py` (23 lines)**

- `from_agent` / `to_agent` mix agent IDs and sentinel strings (`"user"`, `"system"`).
- Threading through `parent_message_id`. `Conversation.message_ids` is an ordered
  list and `Message` has no `conversation_id`: the link is one-directional (DB impact
  examined in 4.2).
- The `MessageDispatcher` does not exist yet (§4).

**`memory/models.py` (14 lines)** — `agent_id=None` = global KB entry (§7). The
embedding is managed by Chroma. Why a SQLite `Memory` table also exists is examined
in 4.2.

**`projects/models.py` (24 lines)** — v0.2 feature, defined ahead by precedent
(ADR 0004 §4).

**`deliverables/models.py` (14 lines)** — `file_path` is relative to `data/outputs/`;
nothing prevents `../` (to handle when deliverables are written to disk —
Deliverables feature).

**`generator/models.py` (26 lines)** — `BusinessContext`: structured output of the
interview, input of org generation. Built in `interview.py:220-225` as
`BusinessContext(id=..., conversation_id=..., created_at=..., **data)` where `data`
is the extraction LLM's JSON. Missing from ARCHITECTURE §3 (F7).

### Tests (758 lines)

pytest idioms:

- `with pytest.raises(ValidationError):` — the block must raise that exception. If it
  raises nothing, the test fails (`DID NOT RAISE`); another exception propagates and
  the test errors.
- **Factories** (`make_skill()`, `make_bc(**overrides)`) rather than **fixtures**. A
  fixture is a function decorated with `@pytest.fixture`, injected by pytest from the
  test's parameter name, optionally with setup / teardown around a `yield`. A factory
  is a plain function called explicitly: the construction is visible in the test, and
  one call varies one field (`make_bc(business_name=None)`). Fixtures remain the right
  tool for resources that need setup and teardown (the DB session in `conftest.py`).
- `# type: ignore[call-arg]` on deliberately invalid constructions: Pydantic declares
  models with `@dataclass_transform` (PEP 681), so mypy knows the constructor
  signature and flags a missing argument; the comment silences that error code on
  that line. But mypy only checks `adjents/` (`Makefile:23`, `ci.yml:37`), so these
  comments have no effect today (F2). Run by hand on these tests, the ignores *are*
  used; the 9 errors are `comparison-overlap` on `AgentStatus.IDLE == "idle"` (strict
  mypy treats an enum member and a `str` literal as non-overlapping although a
  `StrEnum` compares equal at runtime — fix: compare `.value`).

What the error tests actually check (from `ValidationError.errors()`):

| Test | Errors raised |
| --- | --- |
| `test_skill_missing_required_field` | 1: `name` missing |
| `test_agent_spec_missing_required_field` | **4**: `name`, `parent_id`, `domain`, `work_hours` missing |
| `test_agent_spec_invalid_level_type` | 1: `level` `int_parsing` (`"5"` would be accepted: lax mode) |
| `test_agent_state_invalid_status` | 1: `status` `enum` |
| `test_blocking_question_missing_required_field` | 1: `question` missing |
| `test_business_context_missing_required_field` | **13** missing fields |

Covered: one valid construction per model; main nullable cases (COO without parent /
domain, global KB entry, deliverable without project); missing field; invalid enum;
invalid `level` type; `model_dump()` → `model_validate()` roundtrip.

Not covered, and why:

- **Tests based on `model_copy` cannot fail** (F1): `model_copy` does not validate, so
  `test_agent_spec_level_no_cap` would pass even if depth were capped.
- **"Required but nullable" contract** (F9): the key contract for parsing LLM JSON (a
  missing `work_hours` key must be rejected, not defaulted to `None`). Only covered by
  accident in the 4-error test above; adding `= None` to a field would break nothing.
- **JSON-mode roundtrip** (F9): `model_dump()` returns Python objects (no text
  conversion), so the tested roundtrip is nearly tautological. The real path (FastAPI,
  WebSocket) goes through JSON text. Checked: a `Message` with
  `metadata={"due": datetime(...)}` survives `model_dump()` but **not**
  `model_dump_json()` — the date comes back as a `str`.
- **No invariant tested** (F3): there is none in the models.
- **Tautological tests** (F10): `*_are_lists`, `*_is_dict`,
  `test_conversation_message_ids_ordered` test Pydantic / Python lists, not our code.
  Order loss is a DB serialization risk (checked in 4.2).

### Corrections to the first presentation

Three statements made when presenting 4.1 were wrong and were corrected in the Q&A:

1. "Business validation can send aggregated feedback to the LLM" — false.
   `_validate_structure` (`org_generation.py:77`) returns at the **first** violated
   rule; the LLM gets one error per attempt. Pydantic, on the contrary, aggregates all
   field errors of an object in one `ValidationError`. The real reasons the 8 rules
   live outside the model: rules 1–6 are cross-agent (several agents involved); they
   run on `RawAgentData` (a plain `@dataclass`, no validation) before any `AgentSpec`
   exists; their messages are written for the LLM.
2. "`BusinessContext` is built from keyword arguments" — misleading: it is
   `**data` from the LLM JSON, so `extra="ignore"` does apply to the LLM output.
3. "The `# type: ignore` comments in the model tests are useless" — false: they are
   used when mypy runs on them; the 40 `unused-ignore` errors are in the org
   generation and team setup tests.

### Q&A

**A1–A5 — What do the `pytest.raises` tests check?** That an invalid object is
refused at construction. Exact errors in the table above. A2 has 4 missing fields
(`parent_id` and `domain` are required-but-nullable), not 2. A3: `"N-1"` cannot be
parsed as an int; a numeric string would be accepted. → F12.

**B1 — Why no constraints / validators? What are "trivial models"? What does
"invariants live elsewhere" mean?**

- No recorded decision (see "Shared design choices").
- "Trivial" = pure data containers: typed fields, no rule beyond the type, no logic.
  Not simplified — complete.
- An *invariant* is a rule that must always hold. `scheduler_interval_seconds` in
  [300, 3600] exists in three copies with three policies:

  | Where | How | On violation |
  | --- | --- | --- |
  | `org_generation.py:175` | literals `300` / `3600` | reject, LLM retry with the error |
  | `team_setup.py:31-32` | `_INTERVAL_MIN/MAX` | clamp + warning |
  | `reconfiguration.py:27-28` | same constants, copied | clamp + warning |

  `visual_character` is checked in the same three places (`VALID_VISUAL_CHARACTERS`,
  imported lazily from `org_generation` by the two others).
- "A direct table writer bypasses them": `reconfiguration.py` updates the table row
  with `setattr(spec_row, key, value)` (`AgentSpecTable`), and SQLModel table classes
  do not validate. Even with constraints in `AgentSpec`, this path ignores them until
  it goes through the domain model — same root cause as B1 in step 8.

**B2 — What is a mutable model? How can `"N-1"` be stored in an `int` field?**
Mutable = attributes can be changed after creation. Pydantic validates only at entry
points; an assignment is a plain `setattr`. No bug today: domain objects modified in
place receive correctly typed values (e.g. `record.validated_at`,
`team_setup.py:415`). Latent risk only.

**B3 — What is `extra`?** See the idioms table. With the LLM JSON unpacked into
`BusinessContext(**data)`:

1. Misspelled required key (`"founder_nmae"`): dropped, but `founder_name` is then
   missing → `ValidationError` → `InterviewError`. Caught, thanks to the absence of
   defaults.
2. Invented key (`"company_size": "1"`): dropped **silently** — information lost.
3. If a field ever gets a default, a typo on its key yields the default silently.

Low impact today (only case 2 is silent) → extraction audit, step 6.3.

**B4 — `validate_assignment` / `frozen`?** See the idioms table. Not proposed in
step 4: a design choice for the agent loop.

**B5 — Fixtures vs factories, `# type: ignore`, coverage gaps?** See "Tests" above.

### Findings — block 4.1

Severity: 🟠 medium · 🟢 low. No runtime bug.

| # | File:line | Category | Sev. | Finding → recommendation | Step |
| --- | --- | --- | :-: | --- | --- |
| F1 | `test_models_agents.py:124`, `test_models_projects.py:51,57`, `test_models_deliverables.py:35` | Missing test (false positive) | 🟠 | `model_copy(update=...)` does not validate → build through `Model.model_validate({**make().model_dump(), ...})` | 4.7 |
| F2 | `Makefile:23`, `.github/workflows/ci.yml:37` | Debt | 🟠 | mypy only checks `adjents/`; on `tests/`: 53 errors in 5 files (40 `unused-ignore`, 13 `comparison-overlap`) → run `mypy --strict adjents/ tests/` in Makefile + CI, fix all 53 | 4.7 |
| F3 | `agents/models.py:30-40`; `org_generation.py:26,175`; `team_setup.py:31-32,562`; `reconfiguration.py:27-28,153` | Debt / deviation from ARCH §3 | 🟠 | `AgentSpec` invariants (`visual_character` set, interval in [300, 3600], `level ≥ 0`, `work_hours` format) not in the model, duplicated in 3 places → constraints in the model + reference constants in `agents/models.py` (4.7); callers rewired in 7.2 / 8.3 | 4.7, 7, 8 |
| F4 | all `datetime` fields | Deviation from ARCH §3 | 🟢 | Naive datetimes accepted → `AwareDatetime` + test | 4.7 |
| F5 | `agents/models.py:57-60` | Debt | 🟢 | `BlockingQuestion(answered=True, answer=None)` accepted → `@model_validator` for consistency, ADR 0004 schema kept | 4.7 |
| F6 | `agents/models.py:14,39`; ARCH §3 l.221-224, §5 l.597 | Deviation / ambiguity | 🟠 | Two representations of pause (`AgentSpec.is_paused`, `AgentStatus.PAUSED`), no documented invariant; `is_paused` changes at runtime but lives in the "write-once" spec → Technical debt, decided with the agent loop design; nothing changed in step 4 | agent loop |
| F7 | ARCHITECTURE §3 | Docs | 🟢 | `BusinessContext` missing from §3 (and from the serialization table — to confirm in 4.2) → add it | 4.7 |
| F8 | the 6 model modules | Missing docstrings | 🟢 | No class docstrings; module docstrings do not follow the convention (place in the flow, entry points, related ADRs) | 4.4 |
| F9 | model tests | Missing tests | 🟢 | No test of the "required but nullable" contract; no JSON-mode roundtrip | 4.7 |
| F10 | `test_models_agents.py:72`, `test_models_messaging.py:64,101`, `test_models_memory.py:37` | Readability | 🟢 | Tautological tests → accepted as is (zero cost) | 4.7 |
| F11 | `test_models_agents.py:1` | Docstring | 🟢 | Module docstring omits `BlockingQuestion` | 4.4 |
| F12 | `test_models_agents.py:135`, `test_models_generator.py:79` | Readability (imprecise test) | 🟢 | `pytest.raises` only checks that *some* error is raised (4 and 13 missing fields) → one missing field per test + assert on `exc_info.value.errors()` locations | 4.7 |

Out of scope, recorded for other steps:

- `ValidationSession`, `AgentValidationRecord`, `AgentValidationStatus` defined in
  `generator/team_setup.py:35-49`, not in a models module → step 8.3 (split).
- `team_setup` / `reconfiguration` write table rows directly (e.g.
  `reconfiguration.py:67`), bypassing domain validation → step 8.2 (same root cause
  as B1).
- `_validate_structure` returns only the first violation → return all of them
  (fewer paid retries) → step 7.2.
- Callers rewired to the `AgentSpec` reference constants → steps 7.2 and 8.3.
- Which JSON Schema keywords of the new `Field` constraints the provider accepts, and
  what the SDK does with unsupported ones → step 4b.1.
- `Message.from_agent` / `to_agent` sentinel strings → Technical debt,
  `MessageDispatcher` design (§4).
- Unknown keys in the extraction JSON dropped silently (`extra="ignore"`) → extraction
  audit, step 6.3.
- `Deliverable.file_path` accepts `..` / absolute paths → Technical debt, Deliverables
  feature.

### Decisions — block 4.1 (2026-10-23)

- **Q1 — `AgentSpec` invariants live in the model**, fixed in **4.7**: `Field`
  constraints / validators + reference constants in `agents/models.py`. Callers
  (`org_generation`, `team_setup`, `reconfiguration`) keep their own policy (reject vs
  clamp) and are rewired to the reference constants in **7.2** and **8.3**. Rationale:
  "what is valid data" is independent of "how the LLM produces JSON" (4b), applies to
  every writer, and gives 4b real constraints to test against the provider's JSON
  Schema support. Cost contained: only 3 test files (all in step 4) use values that
  become invalid.
- **Q2 — mypy covers `tests/`**: Makefile + CI run `mypy --strict adjents/ tests/`;
  all 53 errors fixed in **4.7** (mechanical, no logic change), including the files of
  steps 7 and 8, so CI protects the tests from now on.
- **Q3 — `is_paused` vs `PAUSED`**: added to Technical debt with a pointer to the
  agent loop design; nothing changed in step 4.
- F1–F12 recommendations and target steps validated as listed.
- Walkthrough notes live in `docs/walkthroughs/` (one file per walkthrough step).

---

## 4.2 — Database layer

Files read (tests first): `tests/conftest.py`, `test_db_tables.py`, `test_db_convert.py`
→ `db/tables.py`, `db/convert.py`, `db/engine.py`.

### Place in the flow

```text
domain (Pydantic)  ──to_table()──▶  tables (SQLModel)  ──session.add / commit──▶  SQLite
domain (Pydantic)  ◀─from_table()──  tables (SQLModel)  ◀─session.get / exec─────  SQLite
```

- **`db/tables.py`**: 12 `table=True` classes, one per domain model (10 + the 2 team
  setup models). No logic.
- **`db/convert.py`**: 24 `x_to_table` / `x_from_table` functions; the only place where
  JSON and ISO dates are (de)serialized (ADR 0002).
- **`db/engine.py`**: async engine, `create_db_and_tables()`, `get_session()`
  (ADR 0003). **Nothing imports it yet**: it waits for the FastAPI app (`api/` is
  empty).
- Today's DB writers: `interview.py`, `org_generation.py`, `team_setup.py`,
  `reconfiguration.py`. Each receives an `AsyncSession` and goes through `convert`,
  except the direct `setattr` writes on table rows (step 8.2).

### Design choices

| Choice | Why | Cost |
| --- | --- | --- |
| **Tables separate from domain models** (ADR 0002) | Clean domain (no `primary_key`, no JSON), FastAPI exposes schemas without persistence details, domain testable without a DB | Each field declared 3 times (model, table, `convert`); no test detects drift (F18) |
| **`list` / `dict` → JSON text** | SQLite has no list type; explicit conversion in `convert` | No SQL query inside lists ("agents whose `skill_ids` contain X"); appending a message rewrites the whole `message_ids` array (F30). Alternative not taken: SQLAlchemy's `JSON` type (automatic serialization) |
| **`datetime` → ISO 8601 string** | **Checked:** even `DateTime(timezone=True)` loses the offset on SQLite (`10:00+02:00` reads back as naive `10:00`, i.e. the wrong instant); the ISO string keeps it | SQL ordering is lexicographic: correct only if every date is UTC with the same format (true today; a naive date would break it — ties to F4) |
| **`metadata` → `metadata_json` column** | `metadata` is reserved on SQLAlchemy declarative classes (the table registry) | Name differs between the two layers |
| **Async + aiosqlite** (ADR 0003) | Never block the event loop (agent loops, WebSocket) | aiosqlite runs `sqlite3` in a background thread. **Async does not make the DB faster** (SQLite serializes writes anyway); it only keeps other coroutines running during a query |

### SQLModel / SQLAlchemy async / pytest-asyncio idioms

| Idiom | What to know |
| --- | --- |
| `class X(SQLModel, table=True)` + `__tablename__` | A SQL table. **Checked: no validation**, even at construction. Only SQL constraints apply at `commit` (`NOT NULL`: a row without `name` → `IntegrityError`). |
| `Field(primary_key=True)` / `Field(default=...)` | `str` → `NOT NULL`, `str \| None` → nullable. SQLite indexes the primary key automatically — the only index (F16). |
| `import adjents.db.tables  # noqa: F401` | Defining a `table=True` class registers it in the global `SQLModel.metadata`. The **module must be imported** before `create_all`, otherwise no table is created. `noqa: F401` tells ruff the "unused" import is intended. |
| `create_async_engine("sqlite+aiosqlite:///...")` | `sqlite+aiosqlite` = dialect + driver. For `:memory:`, SQLAlchemy uses a `StaticPool` (checked): one shared connection, otherwise each connection would see an empty database. |
| `async with engine.begin() as conn: await conn.run_sync(SQLModel.metadata.create_all)` | `begin()` opens a transaction committed at block exit. `create_all` is a sync API; `run_sync` runs it through the **greenlet bridge** SQLAlchemy uses to run its sync core inside a coroutine. |
| `AsyncSession` (`sqlmodel.ext.asyncio`) | Subclass of SQLAlchemy's. `session.add(obj)` touches nothing in the DB; `await session.commit()` writes. `await session.get(Table, pk)` checks the *identity map* (the session cache) first, then issues a `SELECT`. |
| `session.exec(select(...))` / `session.execute(...)` | `exec` is SQLModel's API, typed for `select()`, returns model objects. Raw SQL (`text(...)`) goes through `execute` — hence the `# type: ignore[call-overload]` in `test_db_tables.py:364`. |
| `expire_on_commit` (default `True`) | After a commit, objects are "expired": reading an attribute triggers a reload, which is forbidden in async. **Checked:** `row.name` after commit raises `MissingGreenlet`. The SQLAlchemy asyncio docs examples use `expire_on_commit=False` (F15). |
| `AsyncGenerator[AsyncSession]` | Since Python 3.13 the second type parameter (`SendType`) has a default (PEP 696), hence the single argument. |
| `async` fixture with `yield` | `asyncio_mode = "auto"` (`pyproject.toml`): pytest-asyncio 1.4 treats every `async` test and fixture as asyncio. `@pytest.fixture` and `@pytest_asyncio.fixture` are equivalent here; `conftest.py` mixes both (F27). |
| `json.dumps` | `ensure_ascii=True` by default: `€` stored as `€`; the roundtrip is exact (checked). |
| `str(StrEnum)` / `AgentStatus(row.status)` | `str()` of a `StrEnum` gives the value (`"working"`); the enum constructor raises `ValueError` on an unknown value. |

### Per file

**`tests/conftest.py` (210 lines)** — see Q&A C1 for what a `conftest.py` is.

- `async_session`: one in-memory engine **per test** (full isolation), `create_all`, a
  session, then `dispose()`.
- It **does not use `engine.py`**: it rebuilds its own configuration, so the production
  configuration is never tested (F14).
- It also holds three team setup fixtures (`stub_prompt_loader`, `mini_org`,
  `coo_only_org`) — step 8 territory (F27).

**`db/tables.py` (164 lines)**

- Matches the §3 serialization table, except `BusinessContext`, missing from it (F7
  confirmed).
- **Table defaults diverge from the domain**: `is_paused=False` while §5 says agents are
  created paused; `"[]"` for lists. `convert` always passes every field, but a direct
  writer silently gets these defaults (F17).
- **No foreign key, `PRAGMA foreign_keys` = 0.** Checked: an orphan `AgentState` with
  `status="flying"` and `updated_at="not a date"` is accepted. The "no orphan agent"
  invariant of §3 holds only through the code (F16, Q&A C4).
- `MemoryTable` is used by nothing, and neither §3 nor §7 mentions it (§7 puts memory
  in Chroma). Open question: SQLite as source of truth with Chroma as an index, or a
  dead table (F29).

**`db/convert.py` (404 lines)**

- One responsibility (mapping) repeated 12 times, fully mechanical.
- Above the 300-line review trigger; the `Task` entity (step 5) brings it close to the
  500-line hard limit (F19).
- **Inverted coupling**: it imports models from `generator/team_setup.py`, a business
  module; `team_setup` works around the circular import with 9 lazy imports of
  `db.convert` (`team_setup.py:141` to `817`). Same as A3 of the step 8 review; goes
  away when these models move (8.3) (F20).

**`db/engine.py` (35 lines)**

- The engine is created **at module import** (side effect, environment read at load
  time).
- `_async_url` rewrites `sqlite:///` into `sqlite+aiosqlite:///`.
- **Relative path** `./data/adjents.db`: depends on the working directory. `make dev`
  starts uvicorn from `backend/`, so the DB would be `backend/data/adjents.db`; that
  directory does not exist and SQLite does not create parent directories ("unable to
  open database file"). §1 puts `data/` at the repository root (F13).
- `get_session` keeps `expire_on_commit=True` (F15).

### Tests (1,109 lines)

**`test_db_tables.py` (384 lines)**

- Covered: insert then read back for each of the 10 domain tables, nullable cases,
  table existence.
- Mostly tests SQLAlchemy and overlaps the `convert` roundtrips.
- Not covered: `NOT NULL` rejections; columns matching domain fields (F18, F25).
- `test_all_tables_exist` says "10 tables" while 12 exist, and `issubset` would let the
  2 team setup tables go missing; `test_unused_import_unused` (line 381) is dead code
  that checks nothing (F23).

**`test_db_convert.py` (515 lines)**

- One real roundtrip per model (domain → table → SQLite → table → domain), plus
  nullable cases. **`message_ids` order is asserted** (line 250) — answers the open
  point of 4.1 (F10).
- Not covered: a naive date (it comes back naive, checked); corrupt JSON or an unknown
  enum value in a row (the error path a direct writer could trigger); the team setup
  tables, tested elsewhere (F24).
- Table imports are repeated locally inside each test (F26).

### Corrections to the first presentation

1. In Q4 (foreign keys): "no code deletes rows" — false. `reconfiguration.py:216` and
   `team_setup.py:625` call `session.delete(skill)` when a skill is removed from an
   agent (the skill row is deleted and its id removed from `skill_ids` in the same
   transaction). A foreign key would not protect this case anyway: `skill_ids` is a
   JSON list.

### Q&A

**C1 — What is `conftest.py` for? Who uses it? Why no `assert`?**

- A pytest-specific file, not a test file: it has no `assert` because it checks
  nothing; it **prepares** what tests need.
- **Automatic discovery**: pytest loads every `conftest.py` of the test directory;
  nobody imports it.
- **Fixtures**: a function decorated with `@pytest.fixture` becomes a resource available
  to **every** test of the directory, without import.
- **Injection by name**: a test gets a fixture by declaring a parameter with the same
  name; pytest runs the fixture and passes its result.
- **Chaining**: a fixture can depend on another the same way. `mini_org(async_session)`
  receives the session, so a test asking for `mini_org` gets the session **and** the
  org already inserted in it.

| Fixture | Used by |
| --- | --- |
| `async_session` | `test_db_tables`, `test_db_convert`, `test_generator_interview`, `test_generator_org_generation`, `test_team_setup_orchestrator`, `test_agent_reconfiguration` |
| `stub_prompt_loader` | `test_team_setup_orchestrator`, `test_agent_reconfiguration` |
| `mini_org` | `test_team_setup_orchestrator`, `test_agent_reconfiguration` |
| `coo_only_org` | `test_team_setup_orchestrator`, `test_team_setup`, `test_generator_org_generation` |

**C2 — What does each function of `conftest.py` do?**

- `async_session` (l.24-31): a fresh, empty database for each test. `yield` splits the
  fixture in two: setup before, teardown after (runs even if the test fails). A fixture
  is re-run **for every test** by default, so no test sees another's data and test
  order does not matter.
- `stub_prompt_loader` (l.34-40): a fake `PromptLoader`. Team setup and reconfiguration
  need a loader for their system prompts; the fake avoids reading the real `.md` files
  and makes the tests independent of prompt wording. Whatever the key, `loader.get(...)`
  returns an object whose `.content` is `"You are a helpful agent."`.
- `mini_org` (l.43-163): inserts a 3-agent org (COO → N-1 Finance → N-2 Invoicing), one
  skill each, all `PAUSED`, through `convert` (same path as production); returns the 3
  ids.
- `coo_only_org` (l.166-210): edge case of a COO-only org, for the paths without N-1.

**C3 — What is `MagicMock()`?** A standard library object (`unittest.mock`) that
**accepts everything and records everything**: any attribute exists (`m.foo.bar`), any
call succeeds (`m.get("x")`) and returns another `MagicMock`, and calls are recorded
(`m.get.call_args`, `m.get.assert_called_with(...)`).

- `MagicMock(spec=PromptLoader)`: only `PromptLoader` attributes exist; a typo
  (`loader.gett(...)`) raises `AttributeError` instead of passing silently.
- Limit 1: `stub` has no `spec`. If the code called `prompt.render(...)` instead of
  `.content`, it would get a `MagicMock` as system prompt and the test would still pass.
  The code only uses `.content` today (checked) — no effect.
- Limit 2: the loader returns the same prompt for **every** key and no test checks which
  key is requested (`loader.get.call_args` appears nowhere, checked). Swapping the
  intro and extraction prompts would go unnoticed (F31).

**C4 — Which foreign keys? What is `PRAGMA foreign_keys=ON`? Why add them?**

- A **foreign key** is a schema rule: "this column's value must exist as a primary key
  in that table" (e.g. `agent_states.agent_id` → `agent_specs.id`). The database then
  refuses whatever would break the link: a state for a missing agent, deleting an agent
  still referenced.
- `PRAGMA` is SQLite's connection configuration command. **SQLite quirk**: for
  historical compatibility, foreign key enforcement is **off by default**, even when
  foreign keys are declared; `PRAGMA foreign_keys=ON` must run on **every** connection
  (with SQLAlchemy, through a `connect` event listener). Today both are missing: no
  foreign key declared, pragma off.
- Candidates in `db/tables.py`:

  | Column | → references |
  | --- | --- |
  | `agent_states.agent_id` (l.33) | `agent_specs.id` |
  | `agent_specs.parent_id` (l.17) | `agent_specs.id` (**self-reference**) |
  | `messages.parent_message_id` (l.59) | `messages.id` (self-reference) |
  | `blocking_questions.agent_id` (l.111) | `agent_specs.id` |
  | `deliverables.agent_id` / `project_id` (l.86-87) | `agent_specs.id` / `projects.id` |
  | `projects.lead_agent_id` (l.101) | `agent_specs.id` |
  | `memories.agent_id` (l.76) | `agent_specs.id` (`None` = global KB) |
  | `business_contexts.conversation_id` (l.124) | `conversations.id` |
  | `agent_validation_records.session_id`, `root_agent_id`, `active_agent_id`, `active_conversation_id` (l.156-160) | `validation_sessions`, `agent_specs`, `conversations` |

- Not possible as is: **JSON lists** (`skill_ids`, `message_ids`, `meeting_with`,
  `participant_agents`…) — a foreign key applies to a plain column, not to an array
  stored as text; protecting them would need **association tables** (e.g.
  `agent_skills(agent_id, skill_id)`). `messages.from_agent` / `to_agent` also hold
  sentinel strings.
- Benefit: **the database itself guarantees consistency**, whatever code writes —
  today it relies on the discipline of 4 orchestrators plus direct `setattr` writes. A
  bug cannot create orphans; the error surfaces at the faulty write, not three screens
  later; the schema documents the relations.
- Checked by script (FK declared, pragma on vs off):

  | Scenario | Pragma off (today) | Pragma on + FK |
  | --- | --- | --- |
  | Orphan `AgentState` | accepted | **rejected** |
  | Child added before parent, **different tables**, same commit | OK | **OK** (SQLAlchemy orders tables from the foreign keys) |
  | Child added before parent, **same table** (`parent_id`) | OK | **FAIL** (without `relationship()`, rows of one table are inserted in `add()` order) |
  | Deleting a still-referenced agent | accepted | **rejected** |

  Consequence: `org_generation.py:432` inserts agents **in the order the LLM returned
  them**. With the `parent_id` foreign key on, an org where the LLM lists an N-2 before
  its N-1 would fail at commit. Enabling foreign keys therefore also means sorting
  agents by level before inserting (or declaring `relationship()`): a code change, not
  only a schema change.

**C5 — Which "migration" is Q6 about?** A **schema migration**: evolving the
**structure** of a database that **already exists on disk** when the table code
changes (not a data migration from another system, not the Claude 5.5 migration).

1. A user runs Adjents v0.1 and completes onboarding: `data/adjents.db` holds their
   agents.
2. Step 5.4 adds a column to `AgentSpecTable` (the reasoning tier, step 5.1b).
3. They update and restart. `create_all` **only creates missing tables**: `agent_specs`
   exists, so nothing happens and the column is never added.
4. First `SELECT` on agents: crash. Checked by script (v1 table, then the same file read
   with a v2 table that has one more column):
   `OperationalError: no such column: agent.reasoning_tier`.

A new **table** (`Task`) is not a problem — `create_all` creates it. Added, renamed or
dropped **columns** are.

| Option | Principle | Pros | Cons |
| --- | --- | --- | --- |
| (a) Drop and recreate | On a schema change, delete `adjents.db` (documented, possibly detected at startup) | No tooling; acceptable while no real user data exists | The user loses their org and redoes onboarding |
| (b) Alembic | SQLAlchemy's standard migration tool: each schema change is a versioned script (`ALTER TABLE ... ADD COLUMN`), applied at startup | Data kept; standard practice | **New dependency** (explicit request required); on SQLite some changes require recreating the table (Alembic "batch mode") |
| (c) Hand-written migrations | A `schema_version` table and a few `ALTER TABLE` functions | No dependency | Reinventing Alembic, worse |

Why now: no database exists on disk today (`engine.py` unused, tests in memory), step
5.4 is the **first column change**, and ARCH §1 already announces "migrations (via
SQLModel)" — SQLModel has no migration system.

### Findings — block 4.2

Numbering continues from 4.1. Severity: 🟠 medium · 🟢 low. No active bug (`engine.py`
has no caller); F13–F15 become bugs as soon as the FastAPI app uses it.

| # | File:line | Category | Sev. | Finding → recommendation | Step |
| --- | --- | --- | :-: | --- | --- |
| F13 | `db/engine.py:23` | Latent bug / deviation from ARCH §1 | 🟠 | Relative DB path depends on the working directory; from `backend/`, `data/` does not exist → opening fails → anchor the path on the repository root, create the directory in `create_db_and_tables`, test | 4.7 |
| F14 | `db/engine.py:22-35`, `conftest.py:24-31` | Missing test / debt | 🟠 | No `test_db_engine.py`; engine created at import; `conftest` replicates the configuration instead of using production's → engine and session factories used by `conftest`, tests for `_async_url`, `create_db_and_tables`, `get_session` | 4.7 |
| F15 | `db/engine.py:34`, `conftest.py:29` | Latent bug | 🟠 | `expire_on_commit=True` → `MissingGreenlet` when reading an attribute after commit (checked) → `expire_on_commit=False` in the shared factory + test | 4.7 |
| F16 | `db/tables.py` | Debt | 🟢 | No foreign key (pragma off), no secondary index: orphans and invalid values accepted → Technical debt, decided with the API / agent loop (Q4) | tech debt |
| F17 | `db/tables.py:17-25` and others | Debt | 🟢 | Table defaults diverge from the domain and §5 (`is_paused=False`) → remove them: an omission becomes a visible `NOT NULL` error instead of a silent value | 4.7 |
| F18 | `db/` (no test) | Missing test / deviation from ADR 0002 | 🟠 | ADR 0002 says "a test can detect schema drift": none exists → parametrized test "domain fields == table columns" (with the `metadata_json` rename) | 4.7 |
| F19 | `db/convert.py` (404 lines) | Debt (size) | 🟢 | Above the 300-line trigger, `Task` arrives in step 5 → split into a `db/convert/` package per domain (Q5) | 4.7 |
| F20 | `db/convert.py:34-38`, `team_setup.py:141…817` | Debt | 🟠 | `db/` depends on `generator/team_setup.py`, hence 9 lazy imports → resolved by the model move (8.3, already planned), then remove the lazy imports | 8.3 |
| F21 | ARCH §3 l.432-435, §1 l.29 | Docs | 🟢 | "`fromisoformat` … timezone-aware" is inaccurate (a naive string stays naive, checked); §1 announces "migrations (via SQLModel)" that do not exist; `BusinessContext` missing from the serialization table (F7) → fix §1 and §3 | 4.7 |
| F22 | `db/engine.py:29-30` | Debt / decision | 🟠 | `create_all` never alters an existing table; no migration strategy (ADR 0002 mentions one); step 5.4 adds a column to `AgentSpec` → decide in 5.1b with an ADR (Q6) | 5.1b |
| F23 | `test_db_tables.py:359,381` | Readability | 🟢 | Docstring says "10 tables" (12 exist), `issubset` too permissive, dead `test_unused_import_unused` → fix, delete | 4.7 |
| F24 | `test_team_setup_models.py`, `test_team_setup_orchestrator.py` | Convention deviation | 🟢 | Team setup tables and conversions tested outside the `db/` test files ("one test file per source module") → move with the models | 8.3 |
| F25 | `test_db_tables.py` | Missing test | 🟢 | Mostly tests SQLAlchemy; no `NOT NULL` rejection tested → replace with constraint tests, alongside F18 | 4.7 |
| F26 | `test_db_convert.py:66,97,…` | Missing test / readability | 🟢 | Repeated local imports; no test for a naive date, corrupt JSON or unknown enum in a row → add | 4.7 |
| F27 | `conftest.py:24-210` | Readability | 🟢 | Team setup fixtures in the global `conftest`, mixed fixture decorators → harmonize decorators in 4.7, move team setup fixtures in 8.3 | 4.7, 8.3 |
| F28 | ADR 0003 ("repository functions") | Deviation / debt | 🟠 | No repository layer: `session.get` / `exec`, `convert` and direct writes scattered across 4 orchestrators — one cause of B1 and of `team_setup`'s size → decide in 8.3 (ADR candidate) | 8.3 |
| F29 | `db/tables.py:72` | Deviation / ambiguity | 🟢 | `MemoryTable` used by nothing, absent from §7 (memory in Chroma) → Technical debt, Memory feature | tech debt |
| F30 | `interview.py:176-197` | Debt | 🟢 | Appending a message = read then rewrite the `message_ids` JSON array; `Message` has no `conversation_id`. With concurrent writers (dispatcher), messages would be lost → Technical debt, `MessageDispatcher` design (with 6.2) | tech debt |
| F31 | `conftest.py:34-40` | Missing test | 🟢 | Fake loader returns the same prompt for every key and no test checks which key is requested → `stub` with `spec=LoadedPrompt`, per-key return (or assert on `get.call_args`) | 8.3 |

Out of scope, recorded for other steps:

- `make dev` starts `adjents.api.main:app`, which does not exist yet: the backend half of
  `make dev` fails today → FastAPI app feature.

### Decisions — block 4.2 (2026-10-23)

- **Q4 — Foreign keys**: postponed to Technical debt, decided with the API / agent loop
  (when agent deletion and concurrent writers appear). Scope when done: plain foreign
  keys, pragma listener in the engine factory (F14), sort agents by level in
  `org_generation` before insert, tests.
- **Q5 — `convert.py`**: option (b), split into a `db/convert/` package per domain
  (`agents.py`, `messaging.py`, `generator.py`…), mirroring the domain modules, in
  **4.7**. Rejected: (a) accept as a documented exception; (c) a generic converter
  driven by field lists (less code, but magic that is hard to type under
  `mypy --strict`).
- **Q6 — Schema migration strategy**: decided in **5.1b** with an ADR, before the first
  column change (5.4). Initial inclination: (a) drop and recreate for v0.1, (b) Alembic
  before the first release distributed to real users. ARCH §1 "migrations (via
  SQLModel)" corrected in **4.7** (F21).
- F13–F31 routed to the target steps listed above (no objection raised).

---

## 4.3 — Prompts, LLM client, router

*To be written.*
