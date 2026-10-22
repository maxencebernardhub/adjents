# Project State

> Updated: 2026-10-22 | Branch: chore/claude-5-5-migration | Milestone: v0.1 — MVP

---

## Milestone progress — v0.1

Legend: ✅ done · ⏳ in progress · ⚠️ done with open findings · — to do · n/a not applicable.
"TDD" = tests and code written together in red → green cycles. "Step N" refers to
the Next steps plan below.

| Feature | Feature Brief | Implementation Plan | TDD (tests → code) | Smoke Test | Spec Review | Code Review | Merged |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Project scaffold | n/a | n/a | n/a | n/a | n/a | n/a | ✅ |
| Core Pydantic models (`AgentSpec`, `AgentState`, `Message`, etc.) | n/a | n/a | ✅ | n/a | — (step 4) | — (step 4) | ✅ |
| Database layer (SQLModel + SQLite) | n/a | n/a | ✅ | n/a | — (step 4) | — (step 4) | ✅ |
| Generator Agent — interview | ✅ | ✅ | ✅ | ✅ | — (step 6) | ✅ ¹ | ✅ |
| Generator Agent — org generation | ✅ | ✅ | ✅ | ✅ | — (step 7) | ✅ ¹ | ✅ |
| Post-generation team setup (user ↔ agents) | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ (step 8) | ✅ |
| Task entity (per-agent task queue) | — (step 5) | — | — | n/a | — | — | — |
| LLM router | — (step 10) | — | ⏳ (Anthropic only) | — | — | — | — |
| LLM clients (Ollama, Anthropic, OpenAI, Google) | — (step 10) | — | ⏳ (Anthropic only) | — | — | — | — |
| Async message dispatcher | — | — | — | — | — | — | — |
| Agent loop (asyncio, pause/resume, work hours) | — | — | — | — | — | — | — |
| Memory layer (Chroma — per-agent + global KB) | — | — | — | — | — | — | — |
| Deliverables output (`data/outputs/`) | — | — | — | — | — | — | — |
| FastAPI app + REST routes | — | — | — | — | — | — | — |
| WebSocket handler (real-time agent state) | — | — | — | — | — | — | — |
| Onboarding view (React) | — | — | — | — | — | — | — |
| 2D workspace (PixiJS) | — | — | — | — | — | — | — |
| Org chart view (React) | — | — | — | — | — | — | — |
| Blocking questions UI | — | — | — | — | — | — | — |
| Deliverables view (React) | — | — | — | — | — | — | — |

¹ Informal subagent review in May 2026, no written report. A full written code review
is re-run during the walkthrough step, since the code will change significantly
(SDK upgrade, Claude 5.5 migration, file splits).

---

## Environment

| Step | Status |
| --- | :---: |
| `.env` created from `.env.example` | ✅ |
| `git init` + scaffold commit | ✅ |
| `uv sync` (backend deps) | ✅ |
| `pnpm install` (frontend deps) | ✅ |
| Ollama running + model pulled (`qwen3.5:9b`) | ✅ |
| `backend/.venv` rebuilt after project move out of Dropbox (2026-10-16) | ✅ |
| VS Code workspace settings: interpreter pinned, terminal venv activation off (2026-10-16) | ✅ |
| pnpm 12.15.0 used in `frontend/` via `packageManager` (auto-switch, global pnpm untouched) (2026-10-22) | ✅ |
| Ollama update + local model review | — (step 10) |

---

## Last session — 2026-05-20

- Ollama model pulled (`qwen3.5:9b`) — local inference ready
- Core Pydantic models implemented (TDD, 44 tests, ruff + mypy --strict clean):
  - `agents/models.py` — `AgentSpec`, `AgentState`, `AgentStatus` (`StrEnum`), `Skill`, `BlockingQuestion`
  - `messaging/models.py` — `Message`, `Conversation`
  - `memory/models.py` — `Memory`
  - `projects/models.py` — `Project`, `ProjectStatus` (`StrEnum`)
  - `deliverables/models.py` — `Deliverable`
- Database layer implemented (TDD, 80 tests total, ruff + mypy --strict clean):
  - `db/tables.py` — 9 SQLModel table classes (one per domain model)
  - `db/engine.py` — async engine (`aiosqlite`), `create_db_and_tables`, `get_session`
  - `db/convert.py` — 18 `to_table`/`from_table` functions; JSON + ISO 8601 serialization
  - `tests/conftest.py` — shared async in-memory fixture for DB tests
- ADR 0002 (séparation Pydantic/SQLModel), ADR 0003 (sessions async), ADR 0004 (BlockingQuestion) documentés
- `feat/core-pydantic-models` mergé dans main, branche locale supprimée

**Stopped at:** merge complete — ready for Generator Agent feature spec

---

## Last session — 2026-05-20 (continued)

- Feature spec written and validated: Generator Agent — interview
  - `docs/specs/2026-05-20-generator-agent-interview.md` — full Feature Brief
  - `docs/specs/2026-05-20-generator-agent-interview-roleplay.md` — annotated interview flow example
    (reference for writing the interview prompt)
- Key design decisions:
  - Interview = structured (12 mandatory items) + conversational (adaptive order)
  - End condition: `ready_to_generate: true` flag in the LLM JSON payload
  - Feature 1 output: SQLite transcript + structured `BusinessContext` Pydantic model
  - Skills: intent-level in Feature 1; details co-constructed per agent post-onboarding (dedicated future feature)
  - LLM routing: driven by configured API keys — no forced provider order, Ollama valid for fully local setups

**Stopped at:** Feature Brief validated — ready for implementation plan (Phase 2 of /feature)

---

## Last session — 2026-05-21

- Implementation plan written and saved: `docs/specs/2026-05-20-generator-agent-interview-plan.md`
- Full TDD implementation of Generator Agent — interview (T1–T7):
  - `generator/models.py` — `BusinessContext` Pydantic model
  - `db/tables.py` + `db/convert.py` — `BusinessContextTable` + convert functions
  - `prompts/loader.py` — `PromptLoader` (.md files, YAML frontmatter, `{variable}` rendering)
  - `llm/anthropic_client.py` — async `AnthropicClient` wrapper
  - `router/router.py` — minimal `LLMRouter` (Anthropic-only, reads `ANTHROPIC_API_KEY`)
  - `prompts/generator/interview.md` — real interview prompt (12 mandatory items, closing sequence)
  - `prompts/generator/extract_business_context.md` — extraction prompt (transcript → BusinessContext JSON)
  - `generator/interview.py` — `GeneratorInterview` orchestration (multi-turn, retry, persist, resume)
  - `scripts/smoke_generator_interview.py` — end-to-end smoke test (real API, in-memory SQLite)
- 128 tests passing, ruff + mypy --strict clean
- Smoke test validated: `BusinessContext` correctly produced for Alex Chen / Luminescence scenario
- Code review (subagent) identified 1 blocking + 4 warnings + 1 spec gap → all fixed:
  - `ValidationError` from LLM extraction now wrapped in `InterviewError`
  - `_completed` flag prevents duplicate `BusinessContext` on repeated `reply()` calls
  - `LLMRouter` no longer stores the raw API key in memory
  - Kickoff string moved from Python source to `interview.md` frontmatter
  - `assert` guards replaced with explicit `InterviewError` raises
  - `existing_tools` added as 12th mandatory item
- 130 tests passing after fixes

**Stopped at:** code review fixes committed — ready for merge to main

---

## Last session — 2026-05-22

- `feat/generator-agent-interview` merged into `main`, local branch deleted
- Branch `feat/generator-org-generation` created
- Full brainstorming + design for Generator Agent — org generation:
  - Single LLM call (global coherence over per-domain generation)
  - `visual_character` from predefined list injected into prompt
  - `AgentState` created in `generate()` alongside `AgentSpec` (no orphan invariant)
  - `prompts/agent/intro.md` deferred to post-generation team setup feature
  - Validation: structural invariants extracted as pure function + retry with LLM feedback
- ADR 0005 created: org restructuring deferred to v0.2; Generator Agent orchestrates
  with N-1/N-2 consultation; micro-adjustments via parent agent (v0.2); upsert-safe `generate()`
- ADR 0006 created: post-generation team setup; agents start `is_paused=True`;
  N-1 agents (not Generator Agent) conduct introduction conversations; skippable
- `docs/VISION.md` updated: post-gen validation flow, restructuring flow, micro-adjustments,
  updated roadmap and scope
- `docs/ARCHITECTURE.md` updated: lifecycle diagram, AgentState invariant, visual_character
  constraint, restructuring safety note
- Feature Brief validated: `docs/specs/2026-05-22-generator-agent-org-generation.md`

**Stopped at:** Feature Brief validated — ready for implementation plan (Phase 2 of /feature)

---

## Last session — 2026-05-25

- Implementation plan written, reviewed, and finalised:
  `docs/specs/2026-05-25-generator-agent-org-generation-plan.md`
- Plan covers 4 tasks (T1 → T4) with full TDD detail:
  - T1 — `RawAgentData`, `OrgGenerationResult`, `OrgGenerationError`, `_validate_structure`
    (8 validation rules, 16 unit tests)
  - T2 — `prompts/generator/org_generation.md` (full prompt: JSON schema, org design
    rules, visual character list, scheduler guidance)
  - T3 — `GeneratorOrgGeneration` class + helpers (`_build_context_message`,
    `_parse_raw_agents`, `_resolve_and_build`, `_persist`) + 15 integration tests
  - T4 — `scripts/smoke_generator_org.py` (Sophie Dubois persona, ≥ 10 N-1,
    ≥ 15 N-2, ≥ 40 skills)
- Key design decisions documented in the plan:
  - `prompt.content` used instead of `prompt.render()` to avoid `str.format_map()`
    breakage on user-supplied curly braces; prompt still lives in the `.md` file
  - `work_hours` current format (`"HH:MM-HH:MM"`) is a known v0.1 simplification:
    per-agent schedules ✅ supported; day-of-week granularity → v0.2
  - Validation rule added for `scheduler_interval_seconds` range (300–3600)
  - Edge case documented: `level=0` with non-null `parent_temp_id` is an explicit
    validation failure (separate from the "exactly one COO" rule)

**Stopped at:** implementation plan finalised — ready for TDD implementation (Phase 4)

---

## Last session — 2026-05-25 (continued)

- Full TDD implementation of Generator Agent — org generation (T1 → T4):
  - T1 — `generator/org_generation.py`: `VALID_VISUAL_CHARACTERS`, `RawAgentData`,
    `OrgGenerationResult`, `OrgGenerationError`, `_validate_structure` (8 rules)
    → 16 unit tests, all pure (no DB, no LLM)
  - T2 — `prompts/generator/org_generation.md`: full prompt written (JSON schema,
    field rules, visual character list, org design rules)
  - T3 — `generator/org_generation.py` extended with `_build_context_message`,
    `_parse_raw_agents`, `_resolve_and_build`, `GeneratorOrgGeneration` class
    (generate + _call_llm retry loop + _persist)
    → 15 integration tests with mocked `AnthropicClient` and in-memory SQLite
  - T4 — `scripts/smoke_generator_org.py`: Sophie Dubois Creations persona,
    verifies ≥ 10 N-1, ≥ 15 N-2, ≥ 40 skills, all states paused
- 161 tests passing (130 existing + 31 new), ruff + mypy --strict clean
- Design decision: file kept at ~350 lines (docstrings + comments preserved);
  the 300-line guideline is a soft constraint — coherence > arbitrary split

**Stopped at:** TDD complete — ready for smoke test (requires real ANTHROPIC_API_KEY),
then code review + merge to main

---

## Last session — 2026-05-25 (session 3)

Smoke test debugging, architecture decisions, and smoke script enrichment for
Generator Agent — org generation.

### `AnthropicClient` rewritten to stream unconditionally (ADR 0007)

The Anthropic SDK raises `ValueError` for `messages.create()` with
`max_tokens > 8192` on Opus 4+ models (`MODEL_NONSTREAMING_TOKENS` threshold).
`GeneratorOrgGeneration` requires `_MAX_TOKENS = 32000` → first smoke run crashed.

Fix: `AnthropicClient.complete()` now always uses `messages.stream()` +
`get_final_text()`. Caller API unchanged. `tests/test_llm_anthropic.py`
rewritten with `_FakeStream` async context manager helper.

### Prompt design decisions (org_generation.md)

After analysis of multiple smoke runs, three prompt rules were revised through
discussion:

- **Rule #2 (domain merging)**: one N-1 per listed domain; if two domains truly
  overlap, the LLM may create one N-1 with a merged scope — not a hard ban.
- **Rule #3 (N-2 agents)**: N-2s created when the context shows ≥ 2 distinct task
  clusters; N-1 leaf nodes are explicitly valid. No fixed min or max. N-1 interviews
  will refine the org post-generation (consistent with ADR 0006).
- **Skills**: removed the arbitrary 1–5 cap. "At least 1 skill per agent, as many
  as needed to cover responsibilities; quality over quantity."

### Smoke script enrichment (smoke_generator_org.py)

- **Domains**: disambiguated overlapping entries — `"Content & Social Media"` +
  `"Social Media"` → `"Content Creation & Publishing"` + `"Social Media Management"`
- **Tasks**: split bundled entries into distinct sub-tasks per domain (B2B Sales,
  Content, Social Media, Customer Service, Finance) to give the LLM clear signals
  for N-2 creation
- **Thresholds revised**:
  - N-1: `≥ len(domains) - 1` (±1 tolerance for legitimate merges)
  - N-2: check removed — N-1 leaf nodes valid; count displayed as informational
  - Skills: proportional `≥ floor(1.5 × total_agents)` (robust to org size variance)

### `on_agent_ready` progress callback added to `generate()`

`GeneratorOrgGeneration.generate()` accepts an optional
`on_agent_ready: Callable[[str, int], None] | None = None` parameter, forwarded
to `_resolve_and_build()`. Called with `(name, level)` after each `AgentSpec` is
built. Used by `smoke_generator_org.py` to print live progress; designed for future
WebSocket streaming of org generation progress to the frontend.

### `_print_agent_details` added to smoke script

After the org tree summary, the smoke script now prints a detailed card per agent:
role, schedule (interval + work hours), responsibilities, skills (inputs/outputs/
review flag), and escalation rules. Sorted by level then name.

### Final state

- 31 tests passing (unchanged), ruff + mypy --strict clean
- Smoke test passes reliably: 10 N-1 agents, proportional skills, all states paused
- ADR 0007 created, ARCHITECTURE.md §2 updated, backend/README.md Scripts updated

**Stopped at:** smoke test validated manually — ready for code review + merge to main

---

## Last session — 2026-05-27

Code review of `feat/generator-org-generation` + two fixes applied:

- **Point 1** (`generator/org_generation.py` — `_parse_raw_agents`): `parent_temp_id`
  now explicitly cast via `str(raw_parent) if raw_parent is not None else None`,
  consistent with the `temp_id` field treatment. Guards against malformed LLM output
  (e.g. integer instead of string).
- **Point 2** (`generator/org_generation.py` — `_call_llm`): comment added above
  `messages` initialisation documenting the progressive-context retry strategy and
  the maximum history size (1 + 2×_MAX_RETRIES = 7 messages).
- 31 tests passing, ruff + mypy --strict clean after fixes.
- `feat/generator-org-generation` merged into `main`, local branch deleted.

**Stopped at:** merge complete — ready for next feature

---

## Last session — 2026-05-27 (continued)

Feature Brief written and validated for Post-generation team setup (user ↔ agents).

### Key design decisions

- **Two modes**: `TeamSetupOrchestrator` (sequential, all N-1s, depth-first) +
  `AgentReconfiguration` (any agent, any time, both in v0.1)
- **Conversation + extraction pattern** (ADR 0008): natural language turns, no per-turn JSON;
  single LLM extraction call at validation time
- **Direct reconfiguration in v0.1** (ADR 0009): all non-structural fields modifiable directly;
  `work_hours`, `responsibilities`, `role_description` get parent-mediated governance in v0.2
- **Depth-first traversal** + `navigation_stack` (`list[str]`): enables resume at any depth
  (N-2, N-3, etc.) after interruption
- **Frozen fields**: `domain`, `level`, `parent_id` (restructuring deferred to v0.2)
- **New models**: `ValidationSession`, `AgentValidationRecord` (Pydantic + SQLModel tables)
- **AgentState.status**: `PAUSED → IN_MEETING_1ON1` during conversation; `→ IDLE` at go-live
- **LLM**: `claude-sonnet-4-6` for conversations and extraction (to revisit after LLM Router feature)

### Artefacts

- `docs/specs/2026-05-27-post-generation-team-setup.md` — Feature Brief

**Stopped at:** Feature Brief validated — ready for implementation plan (Phase 2 of /feature)

---

## Last session — 2026-05-28

Implementation plan written and validated for Post-generation team setup.

### Plan design decisions (2026-05-28)

- **`complete_current_agent()` → always `str` (Option B)**: never returns `None`;
  when the subtree is exhausted, makes one final LLM call on the root agent for its
  team summary; caller detects completion via `record.navigation_stack == []`
- **`_advance_traversal` pure helper**: replaces the `_get_next_agent` pseudocode from
  the spec; handles backtracking internally via `while True` loop; takes
  `children_by_parent: dict[str, list[AgentSpec]]` (pre-loaded) — fully testable without DB
- **LLM client**: `AnthropicClient(api_key, model="claude-sonnet-4-6")` constructed
  directly by the caller — NOT via `LLMRouter.get_generator_client()` which returns
  `claude-opus-4-7`
- **`team_setup.py` line count exception**: file will exceed 300-line soft limit;
  splitting artificially would harm cohesion — documented as deliberate exception
- **`_call_extraction_llm` + `_apply_agent_updates` duplication**: ~70 lines duplicated
  between `TeamSetupOrchestrator` and `AgentReconfiguration`; accepted for v0.1

### Plan coverage

- 7 tasks (T1–T7), TDD order T1 → T2 → T3 → T4 → T5 → T6 → T7
- ~52 tests: T1 (9) + T2 (12) + T4 (49, including COO-only + resume + state revert) +
  T5 (7)
- `mini_org` + `coo_only_org` fixtures defined; mock LLM call ordering documented
- `stub_prompt_loader` fixture defined for T4 tests (T3 prompts not required for pytest)
- T7 (documentation updates) runs last, as part of phase 4

### Artefacts (2026-05-28)

- `docs/specs/2026-05-28-post-generation-team-setup-plan.md` — Implementation Plan
- `docs/specs/2026-05-27-post-generation-team-setup.md` — updated (Option B spec)

**Stopped at:** Implementation plan finalised — ready for TDD implementation (Phase 4 of /feature)

---

## Last session — 2026-05-28 (session 2)

Full TDD implementation of Post-generation team setup (T1 → T7, all complete).

### Files created

- `backend/adjents/db/tables.py` — `ValidationSessionTable`, `AgentValidationRecordTable`
- `backend/adjents/db/convert.py` — 4 new convert functions (session + record roundtrip)
- `backend/adjents/generator/team_setup.py` — `AgentValidationStatus`, `ValidationSession`,
  `AgentValidationRecord`, `TeamSetupError`, `_advance_traversal`, `_build_agent_context_message`,
  `TeamSetupOrchestrator` (full Mode 1 orchestration)
- `backend/adjents/agents/reconfiguration.py` — `AgentReconfiguration` (Mode 2 direct reconfiguration)
- `backend/adjents/prompts/agent/intro.md` — agent introduction + adjustment conversation
- `backend/adjents/prompts/agent/extract_agent_adjustments.md` — extraction prompt (JSON output)
- `backend/scripts/smoke_team_setup.py` — mock mode (automated assertions) + real mode
- `backend/tests/test_team_setup_models.py` — 9 pure roundtrip tests
- `backend/tests/test_team_setup.py` — 49 orchestrator tests (traversal, conversation, go-live, skip)
- `backend/tests/test_agent_reconfiguration.py` — 7 reconfiguration tests
- `docs/decisions/0008-team-setup-natural-conversation-extraction.md` — ADR
- `docs/decisions/0009-direct-agent-reconfiguration-v01.md` — ADR

### Test counts

- 238 tests passing (161 existing + 77 new), ruff + mypy --strict clean
- Smoke test: mock mode fully automated and passing

### Key decisions made during implementation

- `_advance_traversal` pure function handles backtracking via `while True` loop; takes
  `children_by_parent: dict` pre-loaded by caller — fully testable without DB
- `complete_current_agent()` always returns `str` (Option B); caller detects subtree
  completion via `record.navigation_stack == []`
- `sqlmodel.select` required (not `sqlalchemy.select`) for SQLModel's `exec()` to
  return typed model instances rather than `Row` tuples
- `_call_extraction_llm` + `_apply_agent_updates` (~70 lines) intentionally duplicated
  between `TeamSetupOrchestrator` and `AgentReconfiguration` — avoids cross-direction
  dependency between `generator/` and `agents/` for v0.1
- `team_setup.py` exceeds 300-line soft limit deliberately — splitting would harm
  cohesion; documented exception

**Stopped at:** T7 complete — feature ready for code review (Phase 5 of /feature)

---

## Last session — 2026-05-28 (session 3)

Bugfix: agent context injection for team setup was incomplete.

### Problem

`_build_agent_context_message` accepted a `direct_reports` parameter and built a
"Direct reports" block, but both call sites in `TeamSetupOrchestrator` passed empty
lists (`[], {}`), so agents never received information about their sub-agents. Additionally,
the direct reports block itself only projected name + role + skill names — omitting
responsibilities, work_hours, scheduler_interval_seconds, and escalation_rules.

Discovered via real-mode smoke test: Jordan (COO) never mentioned Alex, Maya, Felix;
Alex said "no direct reports" despite having Sam.

### Changes

- `backend/adjents/generator/team_setup.py`:
  - `_build_agent_context_message`: extended direct reports block to include
    responsibilities, work_hours, scheduler_interval_seconds, escalation_rules,
    and skill `requires_human_review` flag
  - `TeamSetupOrchestrator._load_direct_reports()`: new helper (SELECT by `parent_id`)
  - `start_agent_conversation()`: calls `_load_direct_reports` and passes result to context builder
  - `complete_current_agent()`: same fix for sub-agents opened during DFS traversal
  - Summary request message: reworded to explicitly ask the agent to present its team
- `backend/adjents/prompts/agent/intro.md`: added instruction to present direct reports
  in the opening message
- `backend/tests/test_team_setup.py`: added `test_build_agent_context_message_direct_reports_full_config`
  covering responsibilities, work_hours, scheduler_interval, escalation_rules, requires_human_review

`AgentReconfiguration` was already correct — it called its own `_load_direct_reports` and
passed the result to `_build_agent_context_message` (imported from `team_setup.py`).

**Tests:** 20/20 passing, ruff + mypy --strict clean.

**Stopped at:** bugfix complete — feature ready for code review (Phase 5 of /feature)

---

## Last session — 2026-05-28 (session 4)

Spec compliance review (Phase 5 of /feature) completed by spec-reviewer subagent.

### Process additions

- Created `~/.claude/agents/spec-reviewer.md` — new specialized subagent for spec
  compliance review (distinct from code-reviewer: checks "was the right thing built?"
  vs "was it built right?")
- Updated `~/.claude/skills/feature/SKILL.md` — inserted Phase 5 (Spec Compliance
  Review) between TDD and Code Review; renumbered Code Review → Phase 6, Commit/PR → Phase 7
- Created `docs/reviews/` directory for storing spec-reviewer and code-reviewer reports

### Spec compliance review results

Full report: `docs/reviews/2026-05-28-post-generation-team-setup-spec-compliance.md`

**Verdict: ⚠️ Partially compliant.** 3 violations, 5 gaps, 3 deviations identified.

Items to address before code review:

| # | Type | Description |
| --- | --- | --- |
| V1 | Violation | `active_agent_id = None` instead of `root_agent_id` after subtree exhaustion (`team_setup.py:451`) |
| V2 | Violation | Feature Brief text outdated vs ADR 0006 — fix by updating Feature Brief, not reverting `intro.md` |
| V3 | Violation | `AgentReconfiguration` raises `ValueError` instead of `TeamSetupError` on retry exhaustion |
| G1 | Gap | No `_log.warning()` when frozen fields are dropped in `_apply_agent_updates` |
| G2 | Gap | No `_log.warning()` when skill name not found (remove/update) |
| G3 | Gap | `skip_agent()` returns `str` instead of `dict[str, Any]` per spec |
| G4 | Gap | `skip_all()` returns `None` instead of `dict[str, Any]` per spec |
| G5 | Gap | `get_subtree_summary()` doesn't handle `agent_id=None` (full-org case) |

Deviations (non-blocking, noted as tech debt):

- D1: `_MAX_RETRIES` module-level vs class attribute
- D2: `_build_agent_context_message` imported from `generator/` into `agents/` (cross-direction dep)
- D3: `_call_extraction_llm` signatures diverge between the two classes

**Stopped at:** spec compliance review complete — next: address V1/V2/V3/G1-G5, then Phase 6 (code review)

---

## Last session — 2026-05-29

Spec compliance corrections applied to `feat/post-generation-team-setup`.

### All 11 findings resolved (3 violations, 5 gaps, 3 deviations)

**New shared modules created:**

- `backend/adjents/errors.py` — `TeamSetupError` moved here from `team_setup.py`
  (breaks the `generator/ → agents/` import direction V3+D2 required)
- `backend/adjents/utils/__init__.py` + `backend/adjents/utils/agent_context.py` —
  `_build_agent_context_message` moved here from `team_setup.py` (D2: no more
  cross-direction import)

**Code changes:**

- V1: `complete_current_agent()` now sets `record.active_agent_id = root_agent_id`
  (not `None`) before delivering the final team summary
- V3: `AgentReconfiguration._call_extraction_llm` now raises `TeamSetupError` instead
  of `ValueError` on retry exhaustion
- G1: `_log.warning("Dropping frozen field %r for agent %s", ...)` added to both
  `_apply_agent_updates` copies
- G2: `_log.warning(...)` added for skill-not-found (remove and update paths) in both files
- G3: `skip_agent()` returns `dict[str, Any]` with `"summary"` and `"warning"` keys;
  warning includes agent name and ID
- G4: `skip_all()` returns `dict[str, Any]` with `"summary"` and `"warning"` keys
- G5: `get_subtree_summary(agent_id: str | None)` — `None` now returns full org
- D1: `_MAX_RETRIES: int = 3` as class attribute in both `TeamSetupOrchestrator` and
  `AgentReconfiguration` (was module-level)
- D3: `_call_extraction_llm(conversations: list[str])` signature harmonized

**Documentation updated:**

- `docs/specs/2026-05-27-post-generation-team-setup.md` — V2: COO intro rule corrected
  to reflect ADR 0006 (agents present direct reports); new shared modules added
- `docs/reviews/2026-05-28-post-generation-team-setup-spec-compliance.md` — all findings
  updated to ✅, verdict changed to "Fully compliant (post-corrections)"

**Test count:** 244 tests passing (238 → +6 new), ruff + mypy --strict clean.

**Stopped at:** all spec compliance corrections done — ready for Phase 6 (code review)

---

## Last session — 2026-06-02 (logged retroactively)

- Phase 6 code review run by the `code-reviewer` subagent:
  `docs/reviews/2026-05-29-post-generation-team-setup-code-review.md`
  — verdict **changes requested**: 2 blockers (B1 silent JSON corruption of
  `responsibilities` / `escalation_rules` in `_apply_agent_updates`; B2
  `team_setup.py` at 839 lines), 5 warnings (A1–A5), 3 notes (N1–N3). Not addressed yet.
- `fc90cb3`: frontend lint fix (non-null assertion removed, `vite.config.ts` excluded
  from ESLint).

**Stopped at:** code review written, findings not addressed, branch not merged.

---

## Last session — 2026-10-16

Re-entry session after a ~4.5-month break. Goal: restore context, audit the repo state,
and agree on a detailed, step-by-step action plan.

### Findings

- `PROJECT_STATE.md` was stale: the 2026-06-02 code review and its open findings were
  not recorded (now logged above).
- **Broken local environment**: the project was moved from Dropbox to `~/dev/adjents`.
  Python venvs are not relocatable — entry-point scripts in `backend/.venv/bin/` kept
  absolute shebangs to the old path → `uv run pytest` failed and mypy reported 57
  import errors. In addition, the VS Code Python extension and the Claude Code
  extension injected a stale `VIRTUAL_ENV` into integrated terminals.
- **Pre-existing frontend check failures** (present on main since scaffold `af912bc`):
  Prettier flags `pnpm-lock.yaml` / `pnpm-workspace.yaml` (no `.prettierignore`);
  `vitest run` fails with "No test files found"; `tsc --noEmit` fails on the
  `./index.css` side-effect import (missing Vite client types under TypeScript 6).
- **Architecture gap**: VISION §3.3 and ARCHITECTURE §5 (agent loop step 4) rely on a
  per-agent task queue, but no `Task` entity exists in the models, tables or
  ARCHITECTURE §3.
- **ADR 0007 rationale inaccurate**: in the installed SDK (`anthropic` 0.103.1),
  `MODEL_NONSTREAMING_TOKENS` only lists Opus 4.0 / 4.1. The constraint that actually
  applies to every model is the SDK's expected-duration check (`3600 × max_tokens /
  128000` s > 600 s ⇒ `ValueError`, i.e. non-streaming fails above ~21,333
  `max_tokens`). The decision (always stream) stays valid; the rationale must be fixed.
- Hard-coded model IDs (`claude-opus-4-7`, `claude-sonnet-4-6`) are a generation behind
  (current: Opus 5.5 / Sonnet 5.5). Dependencies are ~5 months old.

### Done

- `backend/.venv` deleted and rebuilt from `uv.lock` (`uv sync --all-groups`).
- VS Code workspace settings (`.vscode/settings.json`, git-ignored):
  `python.defaultInterpreterPath` pinned to `backend/.venv`,
  `python.terminal.activateEnvironment: false`, `claudeCode.usePythonEnvironment: false`
  — `uv run` is the single way to run Python tools.
- Backend checks green on `feat/post-generation-team-setup`: ruff ✅, mypy --strict ✅,
  244 tests ✅.
- Milestone table restructured (Feature Brief / Implementation Plan / TDD / Smoke Test /
  Spec Review / Code Review / Merged).
- Detailed action plan agreed (see Next steps).

### Decisions

- **One branch open at a time**: each step = branch from up-to-date main → work → PR →
  merge → delete branch. No parallel branches ⇒ no merge conflicts by construction.
- **Merges via GitHub PRs** ("Create a merge commit", consistent with earlier merges).
- `feat/post-generation-team-setup` is merged with its known review findings documented
  in the PR (no runtime caller exists yet — only the smoke script); fixes in step 8.
- **File size rule** (to be written into CLAUDE.md in step 1): source modules — 300
  lines = review trigger ("more than one responsibility?"), 500 lines = hard limit,
  docstrings included; tests — one test file per source module; smoke scripts — no cap,
  but shared helpers extracted to `scripts/_common.py` beyond 400 lines; docs — no limit.
- **No retroactive Feature Brief / Implementation Plan** for core models + DB layer —
  their decisions already live in ARCHITECTURE §3 and ADRs 0002–0004.
- **Retroactive spec + code reviews** for core models, DB layer, interview and org
  generation (steps 4, 6, 7).
- **Docstrings**: Google style; module docstring = purpose + place in the flow + entry
  points + related ADRs; comments explain *why*, not *what*. Written by Claude,
  explained to and validated by the user.
- Technical explanations (agents as data, message passing, scheduler choice, frontend
  tooling) are documented in ARCHITECTURE.md / READMEs / config comments — CLAUDE.md
  only gets one-line pointers to keep the context window small.
- Local model choice (Ollama) is revisited in step 10, with fresh research and a mini
  benchmark on the target machine (Apple M4 Pro, 24 GB RAM).

- PR #1 opened; its frontend CI job failed on the pre-existing Prettier issue. The
  GitHub Actions CI (`.github/workflows/ci.yml`, from the scaffold) had in fact been
  red on main since 2026-06-02 (ESLint, fixed by `fc90cb3`). Step 2.4 was moved to
  step 0.5b so that main is green before the step-by-step workflow starts: the 4 CI
  frontend commands (`pnpm lint`, `format:check`, `typecheck`, `test --run`) now
  pass locally.

**Stopped at:** step 0 complete — PR #1 merged on 2026-10-16 (merge commit `897b6fe`),
branch deleted, CI green on main. Next: step 1.

---

## Last session — 2026-10-22

Step 1 — architecture rationale documented (branch `docs/architecture-rationale`).
Documentation only, no code change.

### Done (2026-10-22)

- Step 0.6 confirmed: PR #1 merged (`897b6fe`), CI green on main.
- ARCHITECTURE §3: new subsection "Agents are data, not code" (what agents-as-code
  would mean, why it is impossible, what an agent is instead, impact, trade-offs).
  Placed inside §3 rather than as a new top-level section, so that the §-numbers
  referenced by ADRs and specs stay valid.
- **ADR 0010** — Agents are data, not code (recorded retroactively: the decision is
  structural, hard to reverse, had real alternatives, and will be challenged by
  executable skills in v0.2). The planned `Task` ADR becomes **ADR 0011**.
- ARCHITECTURE §4 rewritten: "Status: not implemented yet" for the
  `MessageDispatcher`; typed message passing explained (mailbox / email analogy,
  Pydantic `Message`); why not direct calls (blocking, deadlocks, no trace);
  trade-offs (indirection, manual correlation via `parent_message_id`, async
  debugging, persist messages before enqueuing); Redis path for a hosted version.
- ARCHITECTURE §5: "Status: not implemented yet" for the agent loop; open-question
  pointer for the missing `Task` entity (ADR 0011); "Why asyncio tasks and not
  APScheduler or Celery" rewritten (definitions, impact, trade-offs including the
  shared event loop, multi-tenant outlook).
- ARCHITECTURE §2: "Each module is 100–300 lines" aligned with the new file size rule.
- `.claude/CLAUDE.md`: one-line "Why:" pointer per architecture rule; "prompt file"
  → "shared prompt templates" (matches the code); file size rule + docstring
  convention (replace "No >300-line files"); `@` imports of VISION / ARCHITECTURE /
  PROJECT_STATE replaced by plain paths (an `@path` import loads the whole file into
  the context — ~2,400 lines); pre-commit command aligned to
  `make lint && make typecheck && make test`.

### Decisions (2026-10-22)

- Placement of "Agents are data, not code" inside §3 (no renumbering).
- "SQLite is the source of truth" to be promoted to a cross-cutting principle →
  step 9 (see Technical debt).
- Outdated `google-generativeai` name → fixed in step 2.1.

**Stopped at:** step 1 complete — PR #2 merged on 2026-10-22 (merge commit `84dbdbd`),
branch deleted. Next: step 2.

---

## Last session — 2026-10-22 (step 2)

Step 2 — dependency update (branch `chore/deps-update`). Versions checked on PyPI / npm /
GitHub, not from memory; every major bump reviewed against its changelog or migration
guide before upgrading.

### Backend (2026-10-22)

- `pyproject.toml` lower bounds raised to the latest stable releases, then
  `uv lock --upgrade` and `uv sync --all-groups` (72 locked packages updated, 14
  transitive added, none removed).
- Major bumps: `anthropic` 0.103.1 → 2.1.0, `openai` 2.37.0 → 3.36.1 (not imported yet).
  Notable minors: `sqlalchemy` 2.0 → 2.1, `fastapi` 0.136 → 0.159, `ruff` 0.15 → 0.17,
  `mypy` 2.1 → 2.4.
- `anthropic` 1.x: transport moved from `httpx` to `httpx2` (Pydantic-maintained fork;
  `httpx` described upstream as no longer actively maintained); sampling parameters,
  Text Completions and legacy aliases removed. 2.x: API version `2026-10-21`, API key
  sent as `Authorization: Bearer`, one credential per client. **No code change needed**
  — `AnthropicClient` only uses `AsyncAnthropic(api_key=...)`, `messages.stream()` and
  `get_final_text()`.
- ruff, mypy --strict, 244 tests green with no code change; `smoke_team_setup.py` mock
  mode green.
- `google-generativeai` → `google-genai` in `.claude/CLAUDE.md` rule 6 and ARCHITECTURE
  §2; ADR 0001 amended (dated "Amendments" section, original text kept). ARCHITECTURE
  §12: mypy command aligned with the Makefile, `tsc` row added.

### Frontend and CI (2026-10-22)

- All dependencies bumped with pnpm (zustand held at 5.0.15 by pnpm's default
  `minimumReleaseAge`). Major bump: vitest 4 → 5 (no frontend tests yet,
  `--passWithNoTests` kept). TypeScript kept at 6.0.3 (see Technical debt).
- pnpm pinned to 12.15.0 via `packageManager` in `frontend/package.json`: pnpm switches
  to it automatically inside the project, the global pnpm (11.1.3) is untouched; CI
  reads the same field. Stale `minimumReleaseAgeExclude` entry removed.
- ESLint 10 debt resolved: `tseslint.config()` (deprecated) → `defineConfig()` from
  `eslint/config`; `parserOptions.project` → `projectService` (now also lints
  `vite.config.ts` instead of ignoring it); react-hooks flat preset; `ecmaVersion` 2022.
  Resolved rule set unchanged (164 rules, identical before/after).
- Vite 8 debt resolved: `vite.config.ts` type-checks against Vite 8.3.5, `pnpm build` OK,
  no change needed.
- `dist` added to `frontend/.prettierignore` (`pnpm build` then `make lint` failed).
- CI: `actions/checkout` v4 → v7, `astral-sh/setup-uv` v4 → v10.3.2 (full version: no
  floating major tags since v8), `pnpm/action-setup` v4 → v6, `actions/setup-node`
  v4 → v7, frontend job on Node 24.

### Smoke tests (2026-10-22, real API calls)

- `smoke_generator_org.py` (Opus 4.7) ✅ — 13 agents (10 N-1, 2 N-2), 36 skills.
- `smoke_team_setup.py --real` (Sonnet 4.6) ✅ — modes 1 and 2.
- `smoke_generator_interview.py` (Opus 4.7) ❌ — all 11 API calls succeeded, but the
  interview never reached `ready_to_generate`: the agent keeps asking for the daily
  rate (`financial_goals`) and the email / banking tools (`existing_tools`), which the
  scripted Alex Chen scenario never provides. Model behavior against an incomplete
  scenario, not an SDK regression → fixed in step 3 (3.4b).
- Confirms that `anthropic` 2.x (API version `2026-10-21`) works with the current
  `claude-opus-4-7` / `claude-sonnet-4-6` IDs.

### Open points

- pnpm 12 reports "Agent skills awaiting approval: pixi.js" — not approved; install works
  without it. Decision left to the user.
- Vite's type declarations reference `Buffer` (needs `@types/node`); hidden by
  `skipLibCheck: true`, so no package added.

**Stopped at:** step 2 complete — PR #3 merged on 2026-10-22 (merge commit `53d4bd5`),
branch deleted, CI green on main. Next: step 3.

---

## Last session — 2026-10-22 (step 3)

Step 3 — migration to the Claude 5.5 generation (branch `chore/claude-5-5-migration`).
Design session first: every LLM call, breaking change and SDK behavior reviewed against
the `claude-api` skill and the installed SDK sources (`anthropic` 2.1.0), then each
decision agreed one by one (see Decisions log, 2026-10-22, step 3).

### Findings (2026-10-22, step 3)

- Our calls never sent `thinking`, so Opus 4.7 / Sonnet 4.6 ran **without** thinking.
  On Opus 5.5 / Sonnet 5.5 thinking is always on and counts toward `max_tokens`.
- `get_final_text()` ignores `stop_reason`: a truncated or mid-stream-refused response
  is returned as if complete (the JSON retry loops then feed it back to the model), and
  a response with no text block (pre-output refusal, truncation during thinking)
  raises an uncaught `RuntimeError`.
- No assistant prefill, no `temperature` / `top_p` / `top_k`, no `tool_choice` are sent
  (all would return 400). ARCHITECTURE §8 still sketches `RouterDecision.temperature`.
- SDK non-streaming threshold re-verified in 2.1.0: `MODEL_NONSTREAMING_TOKENS` only
  lists Opus 4.0 / 4.1; the expected-duration check (`3600 × max_tokens / 128000` s >
  600 s ⇒ `ValueError`, i.e. > ~21,333) applies to every model, only for non-streaming
  `create()` without an explicit timeout — so ADR 0007's "no workaround exists" is
  also inaccurate (an explicit timeout bypasses the check).
- Server-side `fallbacks` only exist on `client.beta.messages`, and only trigger on
  refusals (not on overload / 5xx / rate limits).
- `model_hint` in prompt frontmatter is read by no code; model IDs were duplicated in
  the router, a smoke script literal, smoke docstrings / prints, prompts and docs.
- VISION §1.2 lists a per-agent *complexity threshold* produced by the Generator; it
  is missing from `AgentSpec`.

**Stopped at:** decisions agreed and recorded, ADR 0012 written — next: 3.2 (TDD).

---

## Next steps

Each step follows the same cycle unless stated otherwise: create the branch from an
up-to-date main → work → `make lint && make typecheck && make test` → update
PROJECT_STATE (Last session + this checklist) → commit → GitHub PR → merge commit →
delete the branch (local + remote) → `git checkout main && git pull`.

Walkthrough steps (4, 6, 7, 8) follow this sub-sequence: (a) read the **tests first**
(they are the executable spec), then the source, then the prompts, then run the smoke
script; (b) add docstrings and comments; (c) spec review (`spec-reviewer` subagent,
report in `docs/reviews/`); (d) code review (`code-reviewer` subagent, report in
`docs/reviews/`); (e) review findings together and fix them with TDD.

### Step 0 — Repair the environment and merge feature 3

Branch: `feat/post-generation-team-setup`

- [x] 0.1 Delete and rebuild `backend/.venv` (`uv sync --all-groups`)
- [x] 0.2 VS Code workspace settings fixed; terminals and Claude Code restarted
- [x] 0.3 Backend checks green (ruff, mypy --strict, 244 tests); frontend failures
  confirmed as pre-existing on main (fixed in step 2)
- [x] 0.4 Update PROJECT_STATE (milestone table, Last session, this plan)
- [x] 0.5 Commit `docs(state)`, push, open PR #1 with a "Known issues" section (B1, B2,
  A1–A5 → step 8)
- [x] 0.5b Fix the pre-existing frontend CI failures (moved here from step 2.4 so that
  main is green before the step-by-step workflow starts — the GitHub Actions CI on
  main had been red since 2026-06-02): `.prettierignore` (pnpm-owned files),
  `src/vite-env.d.ts` (Vite client types), vitest `--passWithNoTests` until real
  frontend tests exist
- [x] 0.6 PR #1 CI green → merge (merge commit), delete the branch, pull main

### Step 1 — Document architecture rationale

Branch: `docs/architecture-rationale`

- [x] 1.1 ARCHITECTURE: new section "Agents are data, not code" — what agent-as-code
  would mean, why it is impossible here (agents are generated at runtime), impact
  (one generic loop, reconfiguration = DB update), trade-offs (behavior must be
  expressible through fields + prompts + skills)
- [x] 1.2 ARCHITECTURE §4 Messaging: typed message passing explained (`Message`
  Pydantic model, mailbox analogy), `MessageDispatcher` role (not implemented yet),
  why (concurrent asyncio tasks, deadlocks, logging/replay, isolated tests), trade-offs
  (indirection, request/response correlation via `parent_message_id`, async debugging,
  in-memory queue ⇒ persist messages), Redis path for a hosted version
- [x] 1.3 ARCHITECTURE §5: what APScheduler and Celery are, impact of the asyncio
  choice, trade-offs (single process, no multi-machine scaling, hand-written calendar
  rules), what would change for a hosted multi-tenant version
- [x] 1.4 CLAUDE.md: one-line pointer to ARCHITECTURE for each architecture rule;
  file size rule; docstring convention

### Step 2 — Update dependencies

Branch: `chore/deps-update`

- [x] 2.1 Backend: bump every dependency in `pyproject.toml` to the latest stable
  version (`anthropic`, `openai`, `google-genai`, `pydantic`, `sqlmodel`, `chromadb`,
  `fastapi`, dev tools…); `uv lock --upgrade` + `uv sync --all-groups`; fix the
  outdated `google-generativeai` name (actual dependency: `google-genai`) in
  `.claude/CLAUDE.md` rule 6, ARCHITECTURE §2 and ADR 0001 (amend, never delete)
- [x] 2.2 Check PyPI for a 1.x major release of the `anthropic` Python SDK; if
  released, follow its migration guide (breaking changes) — 1.x and 2.x both
  released; upgraded to 2.1.0, no code change needed
- [x] 2.3 Frontend: bump dependencies; resolve tech debt ESLint 10 (`eslint.config.js`)
  and Vite 8 (`vite.config.ts`); CI actions bumped, Node 24, pnpm pinned
- [x] 2.4 ~~Fix pre-existing frontend check failures~~ — done in step 0.5b
- [x] 2.5 Full checks green + run the 3 smoke scripts (real API calls — paid) — org
  generation and team setup ✅; interview ❌ on its scenario (not the SDK) → 3.4b

### Step 3 — Migrate to the Claude 5.5 generation

Branch: `chore/claude-5-5-migration`

- [x] 3.1 Choose models per role: Generator (interview, extraction, org generation) →
  `claude-opus-5-5`; team setup (conversations + extraction) → `claude-sonnet-5-5`.
  These are the Anthropic defaults — selection among Anthropic / OpenAI / Gemini comes
  in step 10, so `complete()` stays provider-neutral
- [x] 3.1b ADR 0012 — provider-neutral LLM call contract (written before 3.2)
- [x] 3.2 `AnthropicClient` (TDD — 35 new tests, 279 total; caller effort constants
  done here, since a required `effort` needs them to type-check): `Effort` type (`low` / `medium` / `high`, in
  `adjents/llm/types.py`), `effort` required on every call (no client default); explicit
  `thinking: {type: "adaptive", display: "summarized"}` + DEBUG logger
  `adjents.llm.thinking`; `max_tokens` default 16000 (org generation 64000); read
  `get_final_message()` and check `stop_reason` before the text → `LLMRefusalError` /
  `LLMTruncatedError` / `LLMResponseError` (`adjents/llm/errors.py`), no retry and no
  wrapping in callers; DEBUG log of `stop_reason` + `usage.output_tokens`, WARNING on
  refusal / truncation (no content); read-only `model` property; confirmed: no prefill,
  `temperature` or `tool_choice` sent; server-side fallbacks deferred to step 10
- [x] 3.3 Re-verify the non-streaming threshold in the upgraded SDK (done in the design
  session); fix the `anthropic_client.py` docstring (rewritten in 3.2) and
  ARCHITECTURE §2; **amend** ADR 0007 (rationale correction + Option B "no
  workaround" correction — never delete); **amend** ADR 0008 (model + routing via
  `LLMRouter`)
- [x] 3.4 Model IDs: private constants in `router/router.py` + new
  `LLMRouter.get_team_setup_client()` (no hard-coded model ID outside the router);
  effort constants in each caller; smoke scripts get their clients from the router and
  print `client.model`; `model_hint` updated and documented as informational;
  `backend/README.md`; ARCHITECTURE §8 (IDs, `RouterDecision`: `temperature` →
  `effort`, status note) and §9
- [ ] 3.4b Fix `smoke_generator_interview.py`: the scripted Alex Chen scenario never
  gives the daily rate (`financial_goals`) nor the email / banking tools
  (`existing_tools`), so the interview never reaches `ready_to_generate` (seen in step
  2.5). Complete the scenario only (prompt audit = step 6.3): daily rate €450 (turn 5);
  Google Workspace `alex@luminescence.com` + Qonto business account (turn 6). If the
  scenario is not enough, stop and ask — scenario completed, verified by the smoke
  run in 3.5
- [ ] 3.5 Re-run the smoke tests (paid — cost estimate approved first)

### Step 4 — Walkthrough: foundations

Branch: `refactor/walkthrough-foundations`

- [ ] 4.1 Walkthrough: models (`agents/`, `messaging/`, `memory/`, `projects/`,
  `deliverables/`, `generator/models.py`) + their tests
- [ ] 4.2 Walkthrough: `db/` (`tables.py`, `convert.py`, `engine.py`) + tests
- [ ] 4.3 Walkthrough: `prompts/loader.py`, `llm/anthropic_client.py`,
  `router/router.py` + tests
- [ ] 4.3b Structured outputs: design a provider-neutral method (Pydantic model in →
  validated instance out) and implement it for Anthropic (`output_config.format` /
  `messages.parse()`); check in their docs only that OpenAI and Gemini offer an
  equivalent; check compatibility with adaptive thinking. Adopted by callers in steps
  6, 7, 8
- [ ] 4.4 Docstrings + comments
- [ ] 4.5 Spec review against ARCHITECTURE §3 + ADRs 0002–0004
- [ ] 4.6 Code review
- [ ] 4.7 Review findings together, fix with TDD

### Step 5 — Task entity (per-agent task queue) + routing inputs

Branch: `feat/task-entity` — full `/feature` workflow

- [ ] 5.1 Brainstorming: lifecycle and statuses, priority and reordering (VISION §3.3),
  requester, links to `AgentState` (`current_task_summary` → `current_task_id`?),
  `BlockingQuestion`, `Deliverable`, `Project` (v0.2), retrieval queries
- [ ] 5.1b Routing inputs (consumed by the router in step 10):
  - task complexity as a routing input (`RouterRequest.complexity`), carried by `Task`
  - per-agent reasoning tier in `AgentSpec` (VISION §1.2 "complexity threshold"):
    abstract and provider-neutral (never a model ID), set by the Generator from the
    agent's role and responsibilities — not from its hierarchy level — and adjustable
    in team setup (non-structural field, ADR 0009). Produced in step 7, adjustable in
    step 8. ADR to decide (model selection by agent tier and task complexity)
- [ ] 5.2 ADR 0011
- [ ] 5.3 Feature Brief + Implementation Plan
- [ ] 5.4 TDD: Pydantic model + SQLModel table + convert functions + tests
- [ ] 5.5 Update ARCHITECTURE §3 and §5 (agent loop step 4)
- [ ] 5.6 Spec review + code review, fixes

### Step 6 — Walkthrough: Generator Agent interview

Branch: `refactor/walkthrough-interview`

- [ ] 6.1 Walkthrough: `test_generator_interview.py` → `generator/interview.py` →
  `prompts/generator/interview.md` + `extract_business_context.md` → run
  `smoke_generator_interview.py`
- [ ] 6.2 Tech debt: `resume()` N sequential SELECTs → single `WHERE id IN (...)`
  query (TDD, test asserting the query count)
- [ ] 6.2b Partial state: `reply()` persists the user message before the LLM call, so a
  failed call (network, refusal, truncation) leaves the stored conversation ending with
  an unanswered user message — decide the fix (TDD)
- [ ] 6.3 Prompt audit for Claude 5.5 (patterns written for 4.x models); adopt
  structured outputs (step 4.3b) for interview turns and `BusinessContext` extraction
- [ ] 6.4 Docstrings + comments
- [ ] 6.5 Spec review (against the 2026-05-20 Feature Brief) + code review, fixes

### Step 7 — Walkthrough: Generator Agent org generation

Branch: `refactor/walkthrough-org-generation`

- [ ] 7.1 Walkthrough: `test_generator_org_generation.py` →
  `generator/org_generation.py` → `prompts/generator/org_generation.md` → run
  `smoke_generator_org.py`
- [ ] 7.2 Split `org_generation.py` (435 lines) into a package by responsibility
  (draft: `models.py`, `validation.py`, `parsing.py`, `generator.py`); split the test
  file accordingly (one test file per module)
- [ ] 7.3 Prompt audit for Claude 5.5; adopt structured outputs (step 4.3b); the
  Generator assigns each agent's reasoning tier (step 5.1b) — prompt + validation
- [ ] 7.4 Docstrings + comments
- [ ] 7.5 Spec review (against the 2026-05-22 Feature Brief) + code review, fixes

### Step 8 — Walkthrough: post-generation team setup + code review fixes

Branch: `refactor/walkthrough-team-setup`

- [ ] 8.1 Walkthrough: team setup tests → `generator/team_setup.py`,
  `agents/reconfiguration.py`, `utils/agent_context.py` → prompts `agent/intro.md` +
  `extract_agent_adjustments.md` → run `smoke_team_setup.py`
- [ ] 8.2 B1 (TDD — failing test first): JSON-serialize `responsibilities` /
  `escalation_rules` in `_apply_agent_updates`
- [ ] 8.3 B2: split `team_setup.py` (839 lines) into a package; extract the logic
  shared with `reconfiguration.py` (extraction LLM call + `_apply_agent_updates` +
  persistence helpers) into one module — removes the ~70 duplicated lines; split
  `test_team_setup_orchestrator.py` (1,297 lines) accordingly
- [ ] 8.4 Warnings A1–A5 (asserts as flow control, `validate_team` guard, circular
  import risk, misleading resumability, `reply()` before `start()` guard)
- [ ] 8.5 Notes N1–N3: decide together (fix or accept)
- [ ] 8.5b Adopt structured outputs (step 4.3b) for the adjustments extraction; team
  setup / reconfiguration can adjust the agent's reasoning tier (step 5.1b)
- [ ] 8.6 Smoke scripts: extract shared helpers to `scripts/_common.py` if > 400 lines
- [ ] 8.7 Docstrings + comments
- [ ] 8.8 New code review on the result, fixes

### Step 9 — Document frontend and tooling

Branch: `docs/frontend-and-tooling`

- [ ] 9.1 Comment config files: `tsconfig.json` (JSONC — every compiler option,
  e.g. `isolatedModules`), `vite.config.ts`, `eslint.config.js`,
  `pnpm-workspace.yaml`, `backend/pyproject.toml`
- [ ] 9.2 `frontend/README.md`: dependency table (`package.json` accepts no comments),
  Python ↔ JS tooling equivalences, directory layout rationale
- [ ] 9.3 ARCHITECTURE §11: data flow `api/ → state/ → views/ + components/ |
  workspace/`, layer-based vs feature-based layout trade-off

### Step 10 — LLM Router

Branch: `feat/llm-router` — full `/feature` workflow

- [ ] 10.1 Brainstorming: routing rules (complexity, `sensitivity=high` → local),
  concurrency, startup staggering (ARCHITECTURE §8). Inputs agreed in step 3:
  - **Per-role provider + model selection** for the Generator and team setup among
    Anthropic / OpenAI / Gemini: where the user chooses (`.env` or settings UI),
    defaults from the configured API keys; run the 3 smoke scripts per provider
    before making a model a default; provider-specific prompt variants only if
    measurements justify them; verify OpenAI / Gemini model IDs and prices then
  - Contradiction to settle: "Ollama valid for fully local setups" (2026-05-20) vs
    "Generator Agent → always cloud" (rule 4)
  - Agent reasoning tier (step 5.1b) + task complexity + sensitivity + local-first →
    model and/or effort; route team setup conversations by the agent's tier
  - Move `effort` + `max_tokens` from caller constants into the router's per-role
    table; the per-role `get_*_client()` methods become request-based routing
  - Map each provider's effort control, refusal / truncation signals and HTTP errors
    to the neutral contract (`Effort`, `LLMResponseError` family, ADR 0012);
    sampling parameters (e.g. temperature) for non-Anthropic providers
  - Fallback policy, two distinct cases: refusal fallback (Anthropic server-side
    `fallbacks`, beta `server-side-fallback-2026-07-01`, `"default"` mode, Claude API
    only, refusals only — vs cross-provider fallback via the router) and availability
    fallback (overload, 5xx, rate limits after SDK retries — not covered by
    Anthropic's feature)
  - LLM observability: per-call trace (model, effort, usage, `stop_reason`, thinking
    summary) captured at the router; storage and retention; sensitivity rules; reuse
    for evals and for an agent-reasoning UI
  - Prompt caching (measure `usage.cache_read_input_tokens` with the traces)
  - `model_hint` in prompt frontmatter: consumed by the router, or removed
- [ ] 10.2 OpenAI, Google and Ollama clients; model choice for each provider
- [ ] 10.3 Local models: update Ollama; research recent models suited to 24 GB RAM;
  mini benchmark on Adjents tasks (JSON validity, instruction following, tokens/s);
  choose the embedding model for Chroma; remove unused local models
- [ ] 10.4 Feature Brief → Plan → TDD → smoke → spec review → code review → PR

---

## Technical debt

- TypeScript held at 6.0.3: TS 7 (native Go compiler) is blocked by `typescript-eslint`
  (peer range `typescript <6.1.0`; typed linting on TS 7 tracked in
  typescript-eslint#10940). Bump in a dedicated PR once supported → **when available**
- `smoke_generator_interview.py` fails on an incomplete scenario (see Last session
  2026-10-22, step 2) → **step 3.4b**
- Ollama client planned on `httpx` (ADR 0001), while `anthropic` / `openai` moved to
  `httpx2` because `httpx` is described upstream as no longer actively maintained —
  decide `httpx` vs `httpx2` (ADR candidate) → **step 10**
- No `Task` entity despite the per-agent task queue in VISION §3.3 / ARCHITECTURE §5
  → **step 5**
- ARCHITECTURE: "SQLite is the source of truth" is only stated in §11 (Frontend →
  State principle) although it is cross-cutting (§4 message persistence, §5 loop
  restart, ADR 0004) — promote it to a cross-cutting principle (e.g. §3 Persistence
  layer) → **step 9**
- `resume()` in `GeneratorInterview`: N sequential SELECTs (one per message) — acceptable
  for v0.1 short conversations, replace with `WHERE id IN (...)` → **step 6.2**
- Code review findings on team setup (B1, B2, A1–A5, N1–N3) → **step 8**
- VISION §1.2 lists a per-agent *complexity threshold* produced by the Generator; it is
  missing from `AgentSpec` → designed in **step 5.1b**, produced by the Generator in
  **step 7**, adjustable in **step 8**, consumed by the router in **step 10**
- `effort` and `max_tokens` live as constants in each caller (interim, step 3) → move
  into the router's per-role table in **step 10**
- `model_hint` in prompt frontmatter is informational only (no code reads it) → the
  router consumes it or it is removed in **step 10**
- SDK HTTP errors (`anthropic.RateLimitError`, `APIStatusError`, …) reach callers
  unchanged — map them to provider-neutral errors (retryable or not) → **step 10**
- JSON outputs rely on prompt instructions + retry loops on invalid JSON → structured
  outputs: provider-neutral method in **step 4.3b**, adopted in **steps 6, 7, 8**
- No prompt caching: multi-turn conversations resend the system prompt + history at
  full input price on every turn → **step 10** (measured with the per-call traces)
- Multi-turn conversations replay only the text of earlier replies, not their thinking
  blocks (preserved-thinking rules: append-only history, model-bound blocks, billed as
  input) → decided with the **agent loop** design (v0.1, after step 10), together with
  its action mechanism (parsed JSON actions, ARCHITECTURE §5 step 5d, vs internal
  tools — thinking-block replay is mandatory inside a tool-use loop)
- `work_hours` in `AgentSpec`: single daily window (`"HH:MM-HH:MM"`) applied uniformly
  every day — no day-of-week granularity, no multi-window support; per-agent independent
  schedules ARE supported (each `AgentSpec` has its own field); day-of-week variation
  (e.g. "Tue nights OK, Thu nights not") is a v0.2 enhancement

---

## Decisions log

Full ADRs in `docs/decisions/`. Summary:

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-05-18 | No AI framework (LangChain, LangGraph, etc.) | Custom loop + message bus; official SDKs only |
| 2026-05-18 | PixiJS from v0.1 | Avoids full rewrite when adding animations in v0.3 |
| 2026-05-18 | WebSockets for real-time | Bidirectional needed; SSE is unidirectional |
| 2026-05-18 | asyncio tasks for scheduler | APScheduler/Celery overkill for local single-user app |
| 2026-05-18 | Generator Agent ≠ COO | Different lifecycle and LLM quality requirements |
| 2026-05-18 | Hierarchy depth = `int`, no cap | Complex businesses may need N-3 or deeper |
| 2026-05-18 | MCP for integrations (to validate at v0.2 start) | Reuse open ecosystem rather than custom connectors |
| 2026-05-18 | Projects feature deferred to v0.2 | v0.1 focuses on core autonomous loop |
| 2026-05-20 | Pydantic domain models ≠ SQLModel tables (ADR 0002) | Persistence concerns isolated in `db/`; FastAPI contract stays clean |
| 2026-05-20 | Async SQLite sessions via aiosqlite (ADR 0003) | asyncio-first app; sync sessions would block the event loop |
| 2026-05-20 | BlockingQuestion as first-class persisted entity (ADR 0004) | Schema complet dès le début; shape connue via le protocole WebSocket |
| 2026-05-22 | Post-gen team setup: agents start `is_paused=True`; N-1 agents (not Generator Agent) introduce themselves (ADR 0006) | Builds trust; N-1 has domain context; establishes operational relationship |
| 2026-05-22 | Org restructuring deferred to v0.2 — Generator Agent orchestrates, consults N-1/N-2 (ADR 0005) | Memory preservation; agent domain knowledge improves proposals |
| 2026-05-22 | Micro-adjustments via parent agent (v0.2) — N+1 owns team config for small changes (ADR 0005) | Distinct from restructuring; avoids Generator Agent overkill |
| 2026-05-22 | Org generation: single LLM call (global coherence); `AgentState` created in `generate()`; `visual_character` from predefined list | Coherence over speed; no orphan invariant; PixiJS sprite safety |
| 2026-05-25 | `AnthropicClient` streams unconditionally via `messages.stream()` (ADR 0007) | SDK raises `ValueError` for `messages.create()` with `max_tokens > 8192` on Opus 4+ (rationale corrected 2026-10-22: the SDK's expected-duration check, > ~21,333 `max_tokens` on every model — ADR 0007 amendment) |
| 2026-05-25 | N-1 leaf nodes valid; N-2 count driven by context, not enforced; skills no upper cap | Initial org is a first draft — N-1 setup conversations refine scope and spawn specialists (ADR 0006) |
| 2026-05-25 | `generate()` accepts optional `on_agent_ready` callback for progress reporting | Pattern for future WebSocket streaming of org generation progress to the frontend |
| 2026-05-27 | Natural conversation + single extraction call at validation time (ADR 0008) | Avoids per-turn JSON fragility; one clean extraction when the user is satisfied |
| 2026-05-27 | Direct reconfiguration v0.1; parent-mediated governance for `work_hours`/`responsibilities`/`role_description` in v0.2 (ADR 0009) | Skills are descriptive only in v0.1 (no execution barrier); governance deferred until agents are autonomous |
| 2026-05-28 | `_apply_agent_updates` + `_call_extraction_llm` duplicated between `TeamSetupOrchestrator` and `AgentReconfiguration` | Avoids cross-direction `generator/ → agents/` dependency at v0.1 scale; accepted per ADR 0008 |
| 2026-05-28 | `sqlmodel.select` required (not `sqlalchemy.select`) for typed SQLModel `exec()` results | `sqlalchemy.select` returns `Row` tuples; `sqlmodel.select` returns scalar model instances |
| 2026-10-16 | One branch open at a time; every merge through a GitHub PR (merge commit) | No parallel branches ⇒ no merge conflicts; PR history doubles as portfolio evidence |
| 2026-10-16 | File size rule: source 300 lines = review trigger, 500 = hard limit (docstrings included); one test file per source module | Line count is a proxy for single responsibility; must not push towards stripping documentation |
| 2026-10-16 | `Task` becomes a first-class persisted entity (ADR 0011 in step 5) | Task lifecycle (status, priority, requester, links) does not belong in the hot, frequently broadcast `AgentState` record |
| 2026-10-16 | `uv run` is the only way to run Python tools; IDE venv auto-activation disabled | A stale activated venv broke the environment after the project move |
| 2026-10-22 | Agents are data, not code — recorded retroactively (ADR 0010) | Agents are invented by an LLM at runtime: no class can pre-exist them, and executing generated code is a major security risk |
| 2026-10-22 | `pyproject.toml`: `>=` lower bounds only, no upper bounds | Adjents is an application: `uv.lock` pins exact versions; majors only arrive through a deliberate `uv lock --upgrade` checked by CI |
| 2026-10-22 | `anthropic` 2.1.0 adopted in step 2 (not 1.17) | No code change needed; avoids a second SDK migration in step 3; validated by smoke tests on Opus 4.7 / Sonnet 4.6 |
| 2026-10-22 | pnpm pinned via `packageManager` (12.15.0); pnpm's default `minimumReleaseAge` (1 day) kept; no `exclude-newer` cooldown on uv for now | Same pnpm locally and in CI; supply-chain delay on npm without extra config |
| 2026-10-22 | Python stays 3.13; CI frontend job moves to Node 24 (active LTS) | 3.13 supported until 2029, 3.14+ to be checked against chromadb/onnxruntime wheels when Chroma is used; Node 24 matches local and vitest 5 |
| 2026-10-22 | TypeScript stays 6.0.3 | TS 7 blocked by typescript-eslint; same language semantics, speed gain negligible at this size |
| 2026-10-22 | Generator (interview, extraction, org) → `claude-opus-5-5`; team setup → `claude-sonnet-5-5`, as the Anthropic defaults; both roles become selectable among Anthropic / OpenAI / Gemini in step 10 | Frontier quality for the one-shot Generator, lower cost for multi-turn team setup; VISION §3.6 / §4.1 already require the three cloud providers |
| 2026-10-22 | `complete()` stays provider-neutral; `LLMClient` protocol deferred to step 10 (ADR 0012) | No Anthropic-specific semantics in the caller contract; an interface with a single implementation would be designed blind |
| 2026-10-22 | `Effort` type (`low` / `medium` / `high`), required on every call, no client default; Opus: interview + extraction `medium`, org generation `high`; Sonnet: conversations + extraction `medium` (no `low`) (ADR 0012) | The API default silently changed (`high` on Opus 4.7 → `medium` on Opus 5.5); a client default would recreate the same trap |
| 2026-10-22 | `max_tokens`: default 16000, org generation 64000 (ADR 0012) | Thinking now counts toward the cap; the cap is a cost / latency guardrail, not a cost (billed on actual tokens, no OTPM impact) |
| 2026-10-22 | `LLMResponseError` / `LLMRefusalError` / `LLMTruncatedError` in `adjents/llm/errors.py`; `stop_reason` checked before reading text; no retry and no wrapping in callers (ADR 0012) | A refusal or truncation is not transient; one mapping point in the future API layer; truncated / partial output is never returned |
| 2026-10-22 | Anthropic server-side fallbacks not enabled; refusals surface as `LLMRefusalError`; fallback policy decided in step 10 (ADR 0012) | Fallback is a model choice (rule 4); beta, refusal-only, Claude API only; deliberate deviation from the SDK guide's "opt in from day one" |
| 2026-10-22 | Model IDs only in `router/router.py`; team setup client from `LLMRouter.get_team_setup_client()` (ADR 0008 amendment) | Callers and scripts ask the router instead of choosing a model (rule 4); same shape step 10 generalizes |
| 2026-10-22 | Explicit `thinking: {type: "adaptive", display: "summarized"}` inside `AnthropicClient`; summaries only in a DEBUG logger `adjents.llm.thinking` (ADR 0012) | Behavior independent of per-model defaults; reasoning visible for debugging without changing the `complete()` contract; tracing designed in step 10 |
| 2026-10-22 | Per-agent reasoning tier set by role, not hierarchy level; designed in step 5 (extended), not step 4 | A specialized N-2 may need more reasoning than its parent; step 4 is a walkthrough, and the field needs its producer (step 7) and consumer (step 10) in view |
| 2026-10-22 | Structured outputs: neutral method in step 4.3b, adopted in steps 6, 7, 8 | Removes JSON retry loops without reopening callers after their walkthroughs |
| 2026-10-22 | LLM call contract = ADR 0012 (0011 stays reserved for `Task`) | ADR numbers are stable identifiers; a temporary gap is harmless |
