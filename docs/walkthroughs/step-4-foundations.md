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
versions (Pydantic 2.14.1), not from memory.

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

*To be written.*

---

## 4.3 — Prompts, LLM client, router

*To be written.*
