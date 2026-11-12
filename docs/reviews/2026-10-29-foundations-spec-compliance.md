# Spec Compliance Review — Foundations (step 4.5)

**Date**: 2026-10-29
**Branch**: `refactor/walkthrough-foundations` (HEAD `7eed65d`)
**Reviewer**: spec-reviewer subagent; findings verified by the main session
**Verdict**: ⚠️ Partially compliant — 12 new low-severity findings (11 confirmed,
1 partly refuted), no runtime bug; 25 checklist items fail on findings already known
from the walkthrough (F1–F47), all routed

---

## Scope and method

There is no Feature Brief or Implementation Plan for the foundations (decision of
2026-10-16). Spec sources used instead:

| Area | Spec sources |
| --- | --- |
| Domain models + DB | ARCHITECTURE §1, §3; ADRs 0002, 0003, 0004, 0010 |
| LLM layer | ADR 0007 (amended), ADR 0012; ARCHITECTURE §2, §8 |
| Prompts | ARCHITECTURE §9 |
| Conventions | `.claude/CLAUDE.md` (architecture rules, "What NOT to do", "Conventions") |

Modules reviewed (full content, not the branch diff, which only holds docstrings and
docs): `agents/models.py`, `messaging/models.py`, `memory/models.py`,
`projects/models.py`, `deliverables/models.py`, `generator/models.py`,
`db/tables.py`, `db/convert.py`, `db/engine.py`, `prompts/loader.py`,
`llm/anthropic_client.py`, `llm/types.py`, `llm/errors.py`, `router/router.py`, and
their tests. Callers of steps 6–8 were read only to check docstring statements.

Focus requested: (1) CLAUDE.md conventions module by module; (2) ADR 0004 and ADR
0010 decision by decision; (3) consistency between the step 4.4 docstrings (commits
`9469392`, `5019475`, `a8f7db0`) and the code.

The subagent was told that F1–F47 (`docs/walkthroughs/step-4-foundations.md`) are
known and routed, and to report only new findings or argued disagreements. It ran
read-only (working tree clean afterwards; `mypy --strict` run with
`--cache-dir=/dev/null`, clean on the 14 modules). The subagent's N1–N12 are
renumbered F48–F59 below.

---

## Subagent report

### ARCHITECTURE

| Item (section) | Status | Evidence |
| --- | :---: | --- |
| §1 Module placement matches the tree | ✅ | `agents/`, `messaging/`, `memory/`, `projects/`, `deliverables/`, `generator/`, `db/`, `prompts/`, `llm/`, `router/` |
| §1 `data/` at the repository root | ⚠️ | `db/engine.py:44`, path relative to the working directory — known, F13 |
| §1 "migrations (via SQLModel)" | ❌ | Do not exist — known, F21, F22 |
| §2 No AI framework | ✅ | Imports of the 14 modules: stdlib, `pydantic`, `sqlmodel`, `sqlalchemy`, `anthropic`, all declared in `pyproject.toml` |
| §2 `AnthropicClient` always streams; `_MAX_TOKENS = 64000` | ✅ | `anthropic_client.py:93-94`, `org_generation.py:324` |
| §2 LLM call contract (required `effort`, `max_tokens` guardrail, `str`, typed errors) | ✅ | `anthropic_client.py:57-64`, `llm/errors.py` |
| §2 Module size 300 / 500 | ⚠️ | `db/convert.py` is 428 lines — known, F19 |
| §3 An agent = records keyed by `id` | ✅ | `AgentSpec.id`, `skill_ids`, `AgentStateTable.agent_id` primary key (`tables.py:58`) |
| §3 No subclass per agent; COO = `level == 0` | ✅ | grep: no subclass; `org_generation.py:94`, `team_setup.py:162,236,819` |
| §3 Prompts "rendered with the agent's fields" | ❌ | Fixed system prompts + context message (`utils/agent_context.py`) — **F49** (related to Q7 / F35) |
| §3 Generator JSON validated by Pydantic, then persisted | ⚠️ | ✅ org generation (`org_generation.py:296,433`), ✅ interview (`interview.py:220`); team setup / reconfiguration write table rows through `setattr` without Pydantic — known, 8.2 / Q1 / F3 |
| §3 Reconfiguration = SQL `UPDATE` | ✅ | `reconfiguration.py:182-183` |
| §3 `AgentSpec` fields, `level` without a cap | ✅ | `agents/models.py:100-113` |
| §3 `visual_character` in a predefined set | ⚠️ | Not in the model — known, F3 / Q1 |
| §3 `AgentState` created `PAUSED` with each spec | ✅ | `org_generation.py:434-441` |
| §3 No orphan agent | ⚠️ | Guaranteed by code only, no foreign key — known, F16 |
| §3 Skill / Message / Memory / Conversation / Project / Deliverable / BlockingQuestion fields | ✅ | Field-by-field match |
| §3 `Message` sentinels (`"user"`, `"system"`) | ⚠️ | The code uses `"generator"` — **F57** |
| §3 `BusinessContext` documented | ❌ | Missing — known, F7 |
| §3 Persistence layer `tables.py` / `convert.py` | ✅ | 12 tables, 24 functions |
| §3 datetime / JSON / `metadata_json` serialization | ⚠️ | ✅ in code; "fromisoformat … timezone-aware" is inaccurate and `BusinessContext` is missing from the table — known, F21 / F7 |
| §3 DB engine setup | ⚠️ | ✅ `engine.py:43-73`; relative path (F13), `expire_on_commit` (F15), tables not imported (F46) — known |
| §3 "no synchronous DB calls anywhere" | ✅ | grep: no sync `Session`, `create_engine` or `sqlite3` |
| §5 Agents created with `is_paused = True` | ⚠️ | ✅ `org_generation.py:296`, but the table default is `False` (`tables.py:48`) — known, F17 |
| §8 Router status note | ✅ | `router.py:18-19,61-67`; grep: no model ID outside `router.py` |
| §8 sensitivity → local, Ollama, semaphores | — | Expected at this stage (status note, step 10) |
| §9 Prompts as `.md`, `<agent_type>/<purpose>.md` naming, informational `model_hint` | ✅ | 8 files; nothing reads `model_hint` in production |
| §9 "reads all `.md` at startup", `loader.render(...)` | ❌ | Known, F35 / F32 |

### ADR compliance

| Decision | ADR | Status | Notes |
| --- | --- | :---: | --- |
| Pydantic models in each domain module, no DB import | 0002 | ✅ | 6 modules |
| Tables in `db/tables.py`, mirroring the models | 0002 | ✅ | 12 `table=True` classes |
| to/from functions per pair in `convert.py` | 0002 | ✅ | 24 functions |
| list/dict JSON handled "exclusively in the `db/` layer" | 0002 | ❌ | team setup / reconfiguration: known, 8.2; `interview.py:197`: **F48** |
| A test detects schema drift | 0002 | ❌ | Known, F18 |
| Adding a field implies a migration | 0002 | ❌ | Known, F22 |
| `create_async_engine("sqlite+aiosqlite:///./data/adjents.db")` | 0003 | ⚠️ | Literal followed, path relative — known, F13 |
| `AsyncSession` from `sqlmodel.ext.asyncio`; `await session.exec` | 0003 | ✅ | `engine.py:30,72` |
| `aiosqlite` as a runtime dependency | 0003 | ✅ | `pyproject.toml` |
| Async repository functions | 0003 | ❌ | No repository layer — known, F28 |
| Async `get_session()` for FastAPI | 0003 | ✅ | `engine.py:61` (no app yet) |
| Tests on an in-memory async engine | 0003 | ✅ | `conftest.py:24-31` |
| `BlockingQuestion` as a `BaseModel` in `agents/models.py` | 0004 | ✅ | `agents/models.py:138-163`, exact field list |
| `BlockingQuestionTable` in `tables.py` | 0004 | ✅ | `tables.py:144-156` |
| Tests: valid construction, invalid case, roundtrip | 0004 | ✅ | `test_models_agents.py:236,283,296`, `test_db_tables.py:277,300`, `test_db_convert.py:395,418` |
| WebSocket handler and agent loop read / write `BlockingQuestion` | 0004 | — | No producer yet (expected) |
| An agent = AgentSpec + Skills + AgentState + Chroma collection | 0010 | ⚠️ | 3 SQLite records ✅; Chroma not implemented, expected with the memory layer (related to F29) |
| No subclass per agent | 0010 | ✅ | grep |
| COO = `level == 0`, branches on that field | 0010 | ✅ | See §3 |
| Prompts "rendered with the agent's fields" | 0010 | ❌ | **F49** |
| JSON validated by Pydantic before persistence | 0010 | ⚠️ | Org generation and interview ✅; team setup / reconfiguration not — known, 8.2 / Q1 |
| Reconfiguring = `UPDATE`, no redeploy | 0010 | ✅ | |
| Agents serializable and restorable from SQLite | 0010 | ✅ | `convert.py` |
| Always `messages.stream()` + `get_final_message()` | 0007 (amended) | ✅ | `anthropic_client.py:93-94` |
| `stop_reason` checked before text; empty response → `LLMResponseError` | 0007 (amended) | ✅ | `:113-158` |
| `_FakeStream` helper in the tests | 0007 | ✅ | `test_llm_anthropic.py:53` |
| Neutral `complete()`; Anthropic parameters internal | 0012 §1 | ✅ | |
| `Effort` in `llm/types.py`, keyword-only, no default; caller constants | 0012 §2 | ✅ | interview / extraction / team setup / reconfiguration `medium`, org generation `high` |
| `max_tokens` 16000 / 64000; DEBUG log of `stop_reason` and tokens | 0012 §3 | ✅ | `:63,101-106`, tested `:294` |
| 3 typed errors and their attributes; only `end_turn` accepted; text blocks only | 0012 §4 | ✅ | |
| Refusals **and truncations** logged at WARNING | 0012 §4 | ⚠️ | Code ✅ `:128`; truncation untested — **F51** |
| Callers do not retry or wrap; "retry loops only catch JSONDecodeError" | 0012 §4 | ⚠️ | Decision respected (`complete()` is outside the `try`), but the statement is inaccurate for org generation — **F56** |
| No `fallbacks` | 0012 §5 | ✅ | grep |
| Adaptive + summarized `thinking`; `adjents.llm.thinking` logger | 0012 §6 | ✅ | |

### CLAUDE.md conventions

| Module | Lines | Size | Module docstring (4 parts) | Google style | Comments = why | No prompt string | Type hints / async I/O | Test file | Notes |
| --- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | --- | --- |
| `agents/models.py` | 163 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `test_models_agents.py` | F53, F54 |
| `messaging/models.py` | 66 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `test_models_messaging.py` | |
| `memory/models.py` | 38 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `test_models_memory.py` | |
| `projects/models.py` | 60 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `test_models_projects.py` | |
| `deliverables/models.py` | 38 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `test_models_deliverables.py` | |
| `generator/models.py` | 74 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `test_models_generator.py` | |
| `db/tables.py` | 209 | ✅ | ✅ | ✅ (one line per class) | ✅ (storage-format notes) | ✅ | ✅ | `test_db_tables.py` | F55 |
| `db/convert.py` | 428 | ⚠️ F19 | ✅ | ✅ (module docstring only, 4.4 decision) | ✅ | ✅ | ✅ | `test_db_convert.py` (team setup elsewhere, F24) | |
| `db/engine.py` | 73 | ✅ | ✅ | ✅ | — | ✅ | ✅ async | ❌ none — known, F14 | F59 |
| `prompts/loader.py` | 146 | ✅ | ✅ | ✅ | — | ✅ | ⚠️ sync file I/O | `test_prompts_loader.py` | F50, F58 |
| `llm/anthropic_client.py` | 159 | ✅ | ✅ (entry point named in the first sentence) | ✅ | ✅ (`:33-34`, `:142-143`) | ✅ | ✅ | `test_llm_anthropic.py` | F51 |
| `llm/types.py` | 16 | ✅ | ⚠️ no entry points | ✅ | — | ✅ | ✅ | none (type alias with no runtime behavior, checked by mypy) | F52 |
| `llm/errors.py` | 75 | ✅ | ⚠️ no entry points | ✅ | — | ✅ | ✅ | `test_llm_errors.py` | F52, F56 |
| `router/router.py` | 67 | ✅ | ⚠️ no entry points, no callers | ✅ | — | ✅ | ✅ | `test_router.py` | F52 |

### Docstrings ↔ code

| Statement (short quote) | File:line | Status | Evidence |
| --- | --- | :---: | --- |
| "`GeneratorOrgGeneration` creates every `AgentSpec`, `Skill` and `AgentState`" | `agents/models.py:8-9` | ⚠️ | `team_setup.py:598` and `reconfiguration.py:189` also build `SkillTable(...)` rows (`skills_to_add`) — F53 |
| "Today only team setup and reconfiguration set a status" | `agents/models.py:31-32` | ⚠️ | `org_generation.py:436`: `status=AgentStatus.PAUSED` — F54 |
| "team setup and reconfiguration build some rows directly and update loaded rows in place" | `db/tables.py:18-19` | ⚠️ | `interview.py:197`: `row.message_ids = json.dumps(new_ids)` — F55 |
| "their retry loops only cover invalid JSON" | `llm/errors.py:5` | ⚠️ | `org_generation.py:390-415` also retries on `(KeyError, TypeError, ValueError)` and on structure errors — F56 |
| Frontmatter recognised "when the text starts with `---\n` and contains a later `\n---\n` line" | `prompts/loader.py:34-36` | ⚠️ | Probe: `_parse_frontmatter('---\n---\nbody')` → `({}, '---\n---\nbody')` — F58 |
| `get()` Raises: only `FileNotFoundError` | `prompts/loader.py:132-133` | ⚠️ | Also propagates the parser's `ValueError` (F44) — F58 |
| "URLs that already name aiosqlite … are returned unchanged" | `db/engine.py:36` | ⚠️ | Probe: `_async_url('sqlite:///./aiosqlite-data/a.db')` is returned unchanged; the check is a substring anywhere in the URL — F59 |

Statements verified accurate (about 175): `agents/models.py` ≈ 30,
`messaging/models.py` 12, `memory/models.py` 7, `projects/models.py` 8,
`deliverables/models.py` 7, `generator/models.py` 22, `db/tables.py` 11,
`db/convert.py` 10, `db/engine.py` 13, `prompts/loader.py` 23, `router/router.py` 12,
`llm/anthropic_client.py` 15, `llm/types.py` 4, `llm/errors.py` 9. Among those
checked explicitly: `"system"` is used by no code (grep); nothing imports
`engine.py`; the 5 prompt keys and `kickoff_message` are the ones read by callers;
`load_all()` and `render()` have no production caller; `pydantic.ValidationError` and
`JSONDecodeError` are `ValueError` subclasses (probe); the "12 tables" and "24
functions" counts are right; only `router.py` names a model.

### Gaps, violations, deviations (new only)

**F48 (N1) — [VIOLATION]** `generator/interview.py:197`
- **Spec**: ADR 0002, Consequences — "Fields of type `list[str]` and `dict[str, Any]`
  are stored as JSON strings… This is handled exclusively in the `db/` layer."
- **Finding**: the interview serializes `message_ids` itself on a loaded row:
  `row.message_ids = json.dumps(new_ids)`. The team setup / reconfiguration
  equivalents (`team_setup.py:594,670,765-767`; `reconfiguration.py:185,261`) fall
  under the known "direct writes → 8.2" note; the interview case (step 6) is covered
  neither by 8.2 nor by F30, which is about concurrency only.

**F49 (N2) — [DEVIATION, docs]** ARCHITECTURE §3 l.157-158 and ADR 0010, Decision
- **Spec**: "Prompts are shared templates per agent type … rendered with the agent's
  fields."
- **Finding**: no prompt is rendered. System prompts are fixed (`.content`) and agent
  fields reach the LLM in a message (`utils/agent_context.py:6`,
  `team_setup.py:254`). Q7 only plans to rewrite §9 (F35), so §3 and ADR 0010 would
  contradict the corrected §9.

**F50 (N3) — [DEVIATION]** `prompts/loader.py:113-146`
- **Spec**: CLAUDE.md — "`async def` by default for I/O. Sync only for pure CPU work."
- **Finding**: `get()`, `load_all()` and `_load()` read files synchronously
  (`path.read_text`). `get()` is called from async methods (`interview.py:60,85,203`,
  `org_generation.py:348`, `team_setup.py:219,257,…`, `reconfiguration.py:74,89,124`).
  Since `load_all()` is never called (F35), the first `get()` of each key reads the
  disk inside the event loop. Negligible real impact (small files), but the
  convention is not followed and the exception is recorded nowhere.

**F51 (N4) — [GAP, test]** `tests/test_llm_anthropic.py:304-317`
- **Spec**: ADR 0012 §4 — "Refusals and truncations are logged at WARNING … never
  content"; CLAUDE.md — "No feature without a test".
- **Finding**: only the refusal WARNING is tested; the truncation WARNING
  (`anthropic_client.py:128-135`) has no assertion. Evidence: the only `caplog`
  uses in the file are at lines 295, 305, 321, 333.

**F52 (N5) — [DEVIATION, convention]** `llm/types.py:1-9`, `llm/errors.py:1-12`,
`router/router.py:1-12`
- **Spec**: CLAUDE.md — "Module docstring = purpose + place in the flow + entry points
  + related ADRs".
- **Finding**: none of the three module docstrings names its entry points (`Effort`;
  the 3 error classes; `LLMRouter` / `LLMConfigError`). `router.py` also does not say
  who builds the router (today the 3 smoke scripts; orchestrators receive an
  injected client). New because F41 only covered the router's class docstrings, and
  the 4.4 review of `llm/` checked accuracy, not the four parts.

**F53 (N6) — [DEVIATION, docstring]** `agents/models.py:8-9` — skills are also
created by team setup and reconfiguration (evidence in the table above).

**F54 (N7) — [DEVIATION, docstring]** `agents/models.py:31-32` — org generation also
sets a status (`PAUSED` at creation, `org_generation.py:436`); the sentence is only
true if "set" is read as "change".

**F55 (N8) — [DEVIATION, docstring]** `db/tables.py:17-19` — the interview also
updates a loaded row in place (`interview.py:197`); the list of modules doing so is
incomplete.

**F56 (N9) — [DEVIATION, docstring + ADR]** `llm/errors.py:5` and ADR 0012 §4
("their retry loops only catch `JSONDecodeError`")
- **Finding**: the org generation retry loop also catches `KeyError` / `TypeError` /
  `ValueError` (`org_generation.py:392`) and retries on structure errors
  (`:403-414`). The core claim holds — LLM errors are neither retried nor wrapped,
  since `complete()` is outside the `try` (`:376-381`) and `LLMResponseError` is not
  a `ValueError`. Only the parenthesis is inaccurate.

**F57 (N10) — [DEVIATION, docs]** ARCHITECTURE §3 l.278-279
- **Spec**: the `Message` sketch says "`from_agent`: agent_id, "user", or "system"" and
  "`to_agent`: agent_id or "user"".
- **Finding**: the code uses `"generator"` in both directions (`interview.py:28,73-74`)
  and `"system"` is used by no code. The model docstring was corrected in 4.4,
  ARCHITECTURE was not. Covered neither by F7 / F21 nor by the sentinels Technical
  debt entry (about design, not docs).

**F58 (N11) — [DEVIATION, docstring]** `prompts/loader.py:34-36` and `:132-133`
- **Finding 1**: an empty frontmatter block (`---\n---\n`) is not recognised (the
  closing delimiter is searched only after the opening `---\n`), which the docstring
  does not say; the delimiters then end up in the system prompt.
- **Finding 2**: `get()`'s `Raises:` section omits the propagated `ValueError` (F44).

**F59 (N12) — [DEVIATION, docstring, minor]** `db/engine.py:36-38`
- **Finding**: "already name aiosqlite" is implemented as `"aiosqlite" not in raw`,
  which tests the whole URL, path included; a `sqlite:///` URL whose path contains
  "aiosqlite" is not rewritten.

### Disagreements with existing findings or decisions

No substantive disagreement. Three nuances:
- Walkthrough 4.3, "ADR 0012: all 6 points conform": §4 is only partly conformant
  (F51, F56) — the code follows the decision, but the ADR's descriptive statement
  about retry loops is inaccurate and the truncation WARNING is untested.
- 4.4, "`llm/` reviewed: accurate": the parenthesis in `llm/errors.py:5` is
  inaccurate (F56) and three module docstrings do not follow the four-part
  convention (F52).
- Q7: agreed on the substance, but the documentation fix should also cover
  ARCHITECTURE §3 l.157-158 and ADR 0010 (F49), otherwise the same inaccurate
  statement survives in two places after §9 is rewritten.

### Verdict (subagent)

⚠️ Partially compliant — 12 new findings (1 violation, 1 gap, 10 deviations), all low
severity, none breaking runtime behavior; 25 table rows fail because of known
findings (F3, F7, F13, F14, F15, F16, F17, F18, F19, F21, F22, F24, F27, F28, F29,
F32, F35, F46 and the "direct writes → 8.2" note).

---

## Verification (main session)

Every finding was checked before routing: code read at the cited lines, grep, and
probes against the installed code (`uv run python`). For `llm/`, the `claude-api`
skill was loaded; no finding depended on SDK behavior. Working tree confirmed clean
after the subagent run.

| # | Subagent | Status | Verification | Sev. | Routing (decided 2026-10-29) |
| --- | --- | --- | --- | :-: | --- |
| F48 | N1 | ✅ Confirmed | `interview.py:197` read: `row.message_ids = json.dumps(new_ids)` in `_persist_messages`; same lines as F30, different concern (layering, not concurrency) | 🟢 | Step 6.2 (same function) |
| F49 | N2 | ✅ Confirmed | ARCHITECTURE §3 l.157-158 and ADR 0010 "Decision" both say "rendered with the agent's fields"; no caller renders a prompt (`render()` unused, Q7) | 🟢 | 4.7, with F35: fix ARCHITECTURE §3 + **amend ADR 0010** (Q7 scope extended) |
| F50 | N3 | ✅ Confirmed | `loader.py:144` `read_text`; `get()` called from async methods (e.g. `interview.py:60` in `start()`); `load_all()` has no caller | 🟢 | Technical debt — FastAPI app: call `load_all()` at startup (lifespan) so runtime `get()` never reads the disk; no async conversion (would need `to_thread` or a new dependency) |
| F51 | N4 | ✅ Confirmed | Truncation tests (`test_llm_anthropic.py:232-257`) assert the exception only; `caplog` used at 295, 305, 321, 333 only — none on truncation | 🟢 | 4.7 (characterization test) |
| F52 | N5 | ✅ Confirmed | The three module docstrings read: no entry points; `router.py` does not name its builders (smoke scripts) | 🟢 | 4.7 (docstrings) |
| F53 | N6 | ✅ Confirmed | `SkillTable(` built at `team_setup.py:598`, `reconfiguration.py:189` | 🟢 | 4.7 |
| F54 | N7 | ✅ Confirmed | `org_generation.py:436` `status=AgentStatus.PAUSED` | 🟢 | 4.7 |
| F55 | N8 | ✅ Confirmed | `tables.py:18-19` omits `interview.py:197` | 🟢 | 4.7 |
| F56 | N9 | ✅ Confirmed | `org_generation.py:390-414` retries on `(KeyError, TypeError, ValueError)` and on `_validate_structure` errors; LLM errors still propagate (`complete()` outside the `try`) | 🟢 | Docstring: 4.7; ADR 0012 §4 sentence: amendment in step 4b.2 (ADR 0012 already amended there) |
| F57 | N10 | ✅ Confirmed | ARCHITECTURE §3 l.278-279; `interview.py:28` `_GENERATOR_ID = "generator"`; grep: no `"system"` sentinel | 🟢 | 4.7, with F21 / F7 (ARCHITECTURE §3 fixes) |
| F58 | N11 | ⚠️ Partly confirmed | (1) ✅ probe: `_parse_frontmatter('---\n---\nbody')` → `({}, '---\n---\nbody')`, while a literal reading of the docstring says it is recognised. (2) ❌ **Refuted**: the `ValueError` is the F44 bug, removed in 4.7; listing it under `Raises:` would document a bug as contract | 🟢 | (1) 4.7, with F33 / F44 (docstring rewritten with the parser); (2) no action |
| F59 | N12 | ✅ Confirmed | Probe: `_async_url('sqlite:///./aiosqlite-data/a.db')` unchanged. The clause is also redundant: `startswith("sqlite:///")` already excludes `sqlite+aiosqlite:///` | 🟢 | 4.7, with F14 (remove the clause, test in `test_db_engine.py`) |

Disagreements: none contradicts a decision Q1–Q8 or 4.4. The two nuances on earlier
statements (4.3 "all 6 points conform", 4.4 "`llm/` accurate") are recorded in the
walkthrough; the Q7 scope extension (F49) was approved.

Milestone table: "Spec Review" set to ⚠️ (4.7) for "Core Pydantic models" and
"Database layer". The "LLM router" and "LLM clients" rows stay unchanged until those
features formally start (step 10), although 4.5 covered `router.py` and
`anthropic_client.py`.

---

## Verdict

**⚠️ Partially compliant.** The foundations follow ADR 0002 (except F48 and known
findings), ADR 0003 (except known findings), ADR 0004 fully, ADR 0010 in substance
(F49 is a documentation mismatch), ADR 0007 (amended) fully, and ADR 0012 in
decision (F51, F56). The 12 new findings are documentation, docstring and test gaps;
all are routed (4.7, 4b.2, 6.2, Technical debt).
