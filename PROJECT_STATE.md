# Project State

> Updated: 2026-11-12 | Branch: refactor/walkthrough-foundations | Milestone: v0.1 — MVP

---

## Milestone progress — v0.1

Legend: ✅ done · ⏳ in progress · ⚠️ done with open findings · — to do · n/a not applicable.
"TDD" = tests and code written together in red → green cycles. "Step N" refers to
the Next steps plan below.

| Feature | Feature Brief | Implementation Plan | TDD (tests → code) | Smoke Test | Spec Review | Code Review | Merged |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Project scaffold | n/a | n/a | n/a | n/a | n/a | n/a | ✅ |
| Core Pydantic models (`AgentSpec`, `AgentState`, `Message`, etc.) | n/a | n/a | ✅ | n/a | ⚠️ (4.7) | ⚠️ (4.7) | ✅ |
| Database layer (SQLModel + SQLite) | n/a | n/a | ✅ | n/a | ⚠️ (4.7) | ⚠️ (4.7) | ✅ |
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

### Done (2026-10-22, step 3)

- ADR 0012 (provider-neutral LLM call contract) written; ADR 0007 and 0008 amended.
- `AnthropicClient` rewritten (TDD): `Effort` type in `llm/types.py`, required `effort`,
  explicit adaptive thinking with summarized display, `stop_reason` checked before
  the text, typed errors in `llm/errors.py`, DEBUG usage log, opt-in
  `adjents.llm.thinking` logger, `model` property. Callers pass their effort
  constants (done in 3.2: a required `effort` needs them to type-check); org
  generation `max_tokens` 32000 → 64000 at `high` effort.
- `LLMRouter`: Claude 5.5 IDs + `get_team_setup_client()`; no model ID hard-coded
  outside the router. Smoke scripts print the router's model, catch
  `LLMResponseError`, and accept `--llm-debug` (new `scripts/_common.py`).
- Docs: ARCHITECTURE §2 (streaming rationale, call contract), §8 (router status,
  `RouterDecision.temperature` → `effort`, Claude 5.5 IDs), §9 (`model_hint`
  informational); `backend/README.md`; `model_hint` in the 5 prompts.
- 282 tests (244 → 282), ruff + mypy --strict + frontend checks green.

### Smoke tests (2026-10-22, step 3, real API calls, `--llm-debug`)

| Smoke | Model | Result | Calls | Output tokens (max per call) | Duration |
| --- | --- | --- | --- | --- | --- |
| `smoke_team_setup.py --real` | `claude-sonnet-5-5` | ✅ modes 1 and 2, `work_hours` change applied | 13 | 2,157 (383) | 28 s |
| `smoke_generator_interview.py` | `claude-opus-5-5` | ✅ `ready_to_generate` reached, `BusinessContext` complete | 12 | 10,689 (1,863) | 1 min 52 s |
| `smoke_generator_org.py` | `claude-opus-5-5` | ✅ all assertions | 1 | 28,256 | 3 min 53 s |

- Cost: about $0.80 of output tokens (measured) plus an estimated ~$0.30 of input
  (input tokens are not logged) — about $1.1, within the ~$1.5–2 estimate.
- `max_tokens` caps confirmed with margin: 16000 vs 1,863 max; 64000 vs 28,256.
- Sonnet 5.5 at `medium` produced no thinking summaries on team setup conversations
  (12–383 output tokens per call): it barely thinks on these simple turns.
- **Behavior shift on org generation**: Opus 5.5 at `high` generated a much larger org
  for the same Sophie Dubois scenario — 29 agents (10 N-1, 18 N-2), 88 skills — vs
  13 agents (10 N-1, 2 N-2), 36 skills with Opus 4.7 in step 2. Its thinking summary
  shows deliberate choices (two specialists per lead, one leaf N-1). Not a failure
  (prompt rule #3: N-2 when ≥ 2 task clusters); whether this size is desirable is
  decided in the prompt audit (step 7.3).

**Stopped at:** step 3 complete — PR #4 merged on 2026-10-22 (merge commit `307795e`),
branch deleted, CI green on main. Next: step 4.

---

## Last session — 2026-10-23 (step 4, part 1 — complete)

Step 4 — walkthrough of the foundations (branch `refactor/walkthrough-foundations`).
Part 1 = setup + commented reading 4.1 → 4.3 (no code change); part 2 = 4.4 → 4.7.
Full notes (explanations, Q&A, findings, decisions) in
`docs/walkthroughs/step-4-foundations.md`. Every library / SDK behavior stated was
checked by running code against the installed versions (Pydantic, SQLAlchemy,
SQLModel, aiosqlite, pytest-asyncio, `anthropic` 2.1.0 sources), not from memory.

### Done (2026-10-23)

- 4.0: branch created from `main` (`307795e`); step 3 "Stopped at" corrected; base
  green (282 tests).
- 4.1: domain models walked through (6 modules + tests). 12 findings (F1–F12), no
  runtime bug; decisions Q1–Q3 (see Decisions log, 2026-10-23).
- `docs/walkthroughs/` created; `docs/reviews/` and `docs/walkthroughs/` added to the
  repository trees of `README.md` and ARCHITECTURE §1.
- 4.2: database layer walked through (`tables.py`, `convert.py`, `engine.py` +
  `conftest.py` and the 2 DB test files). 19 findings (F13–F31), no active bug —
  `engine.py` has no caller yet, but its relative DB path (F13), the missing engine
  tests (F14) and `expire_on_commit=True` (F15) break as soon as the FastAPI app uses
  it; decisions Q4–Q6 (see Decisions log, 2026-10-23).
- 4.3: prompts, LLM client and router walked through (`claude-api` skill loaded, SDK
  sources read). 11 findings (F32–F42), no active bug; the client conforms to ADR 0012
  and ADR 0007 (amended). Notable: `PromptLoader.render()` fails on 3 of the 5
  production prompts (F32); the client tests mock the whole SDK (F37); a mid-stream
  overload surfaces as `APIStatusError(status_code=200)` without retry (F38, input
  for step 10); decisions Q7–Q8 (see Decisions log, 2026-10-23).

### Findings consolidated (part 1)

42 findings, no active bug; F13–F15 become bugs as soon as the FastAPI app uses
`db/engine.py`. Routing (details and severities in the walkthrough file):

| Target | Findings |
| --- | --- |
| 4.4 (docstrings) | F8, F11, F41 |
| 4.7 (fixes, TDD) | F1, F2, F3, F4, F5, F7, F9, F12, F13, F14, F15, F17, F18, F19, F21, F23, F25, F26, F27 (decorators), F32, F33, F34, F35, F36, F37, F40; F10 accepted as is |
| 5.1b | F22 (schema migration strategy, ADR) |
| 6.2 | note on F30 (same code, out of scope) |
| 7.2 / 8.3 | F3 (callers rewired) |
| 8.2 | direct `setattr` writes routed through `AgentSpec` (4.1 out of scope) |
| 8.3 | F20, F24, F27 (fixtures move), F28, F31 |
| 10.1 | F38 |
| Technical debt | F6, F16, F29, F30, F39, F42; `Message` sentinels; `Deliverable.file_path`; templating (Q7); `make dev` / `api.main` |

**Stopped at:** 4.3 complete — step 4 part 1 done. Next: 4.4 (docstrings + comments).

---

## Last session — 2026-10-29 (step 4, part 2 — 4.4)

Step 4.4 — docstrings and comments for every module read in 4.1 → 4.3 (branch
`refactor/walkthrough-foundations`). No behavior change. Details (files, decisions,
corrections, `llm/` review, findings) in `docs/walkthroughs/step-4-foundations.md`,
section "4.4 — Docstrings".

### Done (2026-10-29)

- 4.1 block (`9469392`): module docstrings per the convention and class docstrings
  with `Attributes:` sections for the 6 domain model modules (F8); the
  `Message.from_agent` comment corrected (`"generator"` sentinel, `"system"` unused);
  `test_models_agents.py` module docstring lists `BlockingQuestion` (F11).
- 4.2 block (`5019475`): module docstrings for `db/tables.py`, `db/convert.py` (shared
  contract of the 24 functions, errors on a malformed row), `db/engine.py`; one-line
  docstring per table class; docstrings for `_async_url`, `create_db_and_tables`,
  `get_session`.
- 4.3 block (`a8f7db0`): `LLMRouter` (API key resolution order) and `LLMConfigError`;
  `prompts/loader.py` module docstring + `PromptLoader`, `LoadedPrompt`,
  `_parse_frontmatter` (F41). `llm/anthropic_client.py`, `types.py`, `errors.py`
  reviewed against the `claude-api` skill and the `anthropic` 2.1.0 sources: accurate,
  unchanged.
- Every statement checked against the code (grep, probes); three first-draft
  statements corrected before review (async expiry raises `MissingGreenlet`,
  `get()` cache replaced by `load_all()`, WebSocket behavior described as implemented).
- No module crossed 300 lines; `db/convert.py` (428) was already above it (F19, 4.7).
- `make lint && make typecheck && make test` green after each block (282 tests).

### New findings (4.4) and routing

| # | Finding | Target |
| --- | --- | --- |
| F43 | `LLMConfigError` points to `.env`, but the router only reads the process environment; only the smoke scripts load the dotenv file (same for `DATABASE_URL`) | Technical debt — FastAPI app |
| F44 | `_parse_frontmatter` raises `ValueError` on a value like `²` (`isdigit()` true, `int()` fails) | 4.7, with F33 |
| F45 | Two ways to group messages: interview → `Conversation` row; team setup / reconfiguration → no `Conversation` row, `metadata["conv_id"]` | 8.1 (observe) + Technical debt — MessageDispatcher |
| F46 | `create_db_and_tables()` creates no table unless `adjents.db.tables` was imported first; `engine.py` does not import it | 4.7, with F14 |
| F47 | `load_all()` keys use the OS path separator (`str(Path)`): cache miss on Windows | 4.7, with F33 / F34 |

**Stopped at:** 4.4 complete. Next: 4.5 (spec review, `spec-reviewer` subagent).

---

## Last session — 2026-10-29 (step 4, part 2 — 4.5)

Step 4.5 — spec review of the foundations (branch `refactor/walkthrough-foundations`).
No code change. Report: `docs/reviews/2026-10-29-foundations-spec-compliance.md`;
method, findings and decisions in `docs/walkthroughs/step-4-foundations.md`, section
"4.5 — Spec review".

### Done (2026-10-29, 4.5)

- `spec-reviewer` subagent run once, read-only, against ARCHITECTURE §1 / §2 / §3 /
  §8 / §9, ADRs 0002, 0003, 0004, 0007 (amended), 0010, 0012 and the CLAUDE.md
  conventions (no Feature Brief / Implementation Plan for the foundations); full
  module content, not the branch diff; F1–F47 given as known.
- Verdict ⚠️ partially compliant: ADR 0004 fully conformant, ADR 0010 in substance;
  12 new findings (F48–F59), all 🟢, no runtime bug; 25 checklist items fail on
  known findings. About 175 docstring statements of 4.4 checked accurate.
- Every finding verified in the main session (code read, grep, probes; `claude-api`
  skill loaded for `llm/`): 11 confirmed, 1 partly refuted (F58 part 2).
- Milestone table: "Spec Review" ⚠️ (4.7) for the models and database rows.

### New findings (4.5) and routing

| # | Finding | Target |
| --- | --- | --- |
| F48 | `interview.py:197` serializes `message_ids` with `json.dumps` outside `db/` (ADR 0002) | 6.2 |
| F49 | ARCHITECTURE §3 and ADR 0010 say prompts are "rendered with the agent's fields" (fixed system prompts + context message in fact) | 4.7, with F35 (Q7 scope extended: ADR 0010 amendment) |
| F50 | `PromptLoader` reads files synchronously from async callers (`load_all()` never called) | Technical debt — FastAPI app |
| F51 | Truncation WARNING untested (ADR 0012 §4) | 4.7 |
| F52 | `llm/types.py`, `llm/errors.py`, `router/router.py` module docstrings without entry points | 4.7 |
| F53–F55 | Inaccurate 4.4 docstrings: skill creators (`agents/models.py:8`), status setters (`:31`), in-place row writers (`db/tables.py:18`) | 4.7 |
| F56 | "retry loops only cover invalid JSON" (`llm/errors.py:5`, ADR 0012 §4): org generation also retries on schema / structure errors | 4.7 (docstring), 4b.2 (ADR 0012 amendment) |
| F57 | ARCHITECTURE §3 `Message` sketch lists `"system"`; code uses `"generator"` | 4.7, with F21 / F7 |
| F58 | `_parse_frontmatter` docstring vs empty frontmatter (part 2 refuted) | 4.7, with F33 / F44 |
| F59 | `_async_url`: substring test on the whole URL, redundant clause | 4.7, with F14 |

**Stopped at:** 4.5 complete. Next: 4.6 (code review, `code-reviewer` subagent).

---

## Last session — 2026-10-29 (step 4, part 2 — 4.6)

Step 4.6 — code review of the foundations (branch `refactor/walkthrough-foundations`).
No code change. Report: `docs/reviews/2026-10-29-foundations-code-review.md`; method,
findings and decisions in `docs/walkthroughs/step-4-foundations.md`, section
"4.6 — Code review".

### Done (2026-10-29, 4.6)

- `code-reviewer` subagent run once, read-only, report in English: full content of the
  14 foundation modules and their tests (not the branch diff); F1–F59 and decisions
  Q1–Q8 / 4.4 / 4.5 given as known; findings on code that 4.7 rewrites reported
  separately, tied to the planned fix.
- Verdict ✅ approved with minor fixes: 13 new findings (3 🟠, 10 🟢), no 🔴, no
  active bug. Every finding verified in the main session (code read, grep, probes;
  `claude-api` skill loaded and `anthropic` 2.1.0 sources read for `llm/`): 13
  confirmed; the one disagreement (4.3 note on `MagicMock` and `async with`) partly
  confirmed and corrected in the walkthrough.
- Milestone table: "Code Review" ⚠️ (4.7) for the models and database rows.

### New findings (4.6) and routing

| # | Finding | Target |
| --- | --- | --- |
| F60 | API key with surrounding whitespace accepted; leaks in clear text through the exception chain (🟠) | 4.7, with F40 |
| F61 | `metadata: dict[str, Any]`: `datetime` / `UUID` / `set` crash `to_table`, tuples become lists, `NaN` stored as invalid JSON | 4.7, with F9 |
| F62 | `ValidationError` text holds user business data (input values) | 4.7; `InterviewError` message: 6.3 |
| F63 | `PromptLoader.get()` resolves `..` and absolute keys outside the prompts directory | 4.7, with F33 / F34 |
| F64 | The 3 LLM errors cannot be pickled / deep-copied | Technical debt |
| F65 | Effort tests parametrized as `str` + ignore; a test name promises a prefill check | 4.7, with F2 |
| F66 | `expire_on_commit=False` turns the DB roundtrip reads into identity-map reads (🟠) | 4.7, with F15 / F14 / F26 |
| F67 | `DATABASE_URL=` and `sqlite://` fail at import | 4.7, with F14 / F59 |
| F68 | DB directory creation must skip in-memory URLs | 4.7, with F13 |
| F69 | File engine: second writer fails after 5 s (`journal_mode=delete`, `busy_timeout=5000`) (🟠) | Technical debt, merged with Q4 / F16 |
| F70 | Parser: UTF-8 BOM, unterminated block closed by a `---` rule, lone `"` | 4.7, with F33 / F44 / F58 |
| F71 | Key passed to the SDK never asserted; SDK reads `ANTHROPIC_BASE_URL` / `ANTHROPIC_CUSTOM_HEADERS` | 4.7, with F37 |
| F72 | `work_hours`: ranges unchecked, overnight undefined, `BusinessContext` unconstrained | 4.7, with Q1 / F3 (Q1 scope extended) |

Out of scope: `interview.py` (`InterviewError` embeds `str(ValidationError)`;
non-object extraction JSON raises `TypeError` / `AttributeError`) → 6.3; smoke scripts
without a transport-error handler → 8.6.

**Stopped at:** 4.6 complete. Next: 4.7 (review findings together, fix with TDD —
F60 and F66 first).

---

## Last session — 2026-11-10 (interlude — public release)

Interlude between 4.6 and 4.7: license decision, repository made public, GitHub
settings hardened. Two short branches from main, merged through PRs #5 and #6; main
then merged into `refactor/walkthrough-foundations` (no conflict; lint, typecheck,
282 tests green).

### Done (2026-11-10)

- **Secret scan of the full history** (60 commits, all refs) before going public: no
  real key or password; only fake test keys in `tests/test_router.py`; the
  environment template holds placeholders only. Confirmed after going public by
  GitHub secret scanning (0 alert).
- **ADR 0013** — MIT kept for the public release, with three guardrails: no external
  code contributions without a CLA, the Adjents name / logo / `adjents.com` not
  licensed, review trigger for the license of future versions (FSL-1.1-ALv2 as the
  default candidate). VISION §6 amended ("open-source forever" contradicted the
  review trigger).
- **README aligned with the actual state** (PR #5): v0.1 scope split into "working
  today" / "in progress", smoke scripts instead of `make dev` (no FastAPI app yet),
  Anthropic key required today, Node.js 24, Ollama model aligned with the environment
  template (`qwen3.5:4b`), new "Engineering practices" section, roadmap aligned with
  VISION §4.3, contribution policy and trademark notice.
- **CI token read-only** (PR #6): `permissions: contents: read` at the workflow level
  in `ci.yml`; closed the two CodeQL `actions/missing-workflow-permissions` alerts.
- **Repository made public** and configured on GitHub (by the user, checked through
  the API):
  - General: merge commits only, head branches auto-deleted, Wiki / Discussions /
    Projects off, pull request creation restricted to collaborators, commit comments
    off, release immutability on; description and 15 topics set
  - Security: private vulnerability reporting, Dependabot alerts + grouped security
    updates (version updates off), CodeQL default setup (Python, JS/TS, Actions),
    secret scanning + push protection
  - Ruleset `protect-main` (default branch): pull request required (0 approvals,
    merge method `merge` only), required checks "Backend — Lint, Typecheck & Test" +
    "Frontend — Lint, Typecheck & Test", signed commits, no force push, no deletion;
    bypass: repository admin, pull requests only
  - Actions: default workflow token read-only, Actions cannot create or approve pull
    requests, approval required for all external contributors' fork workflows
- **Commit attribution**: merge commits of PRs #1–#4 carried the Gmail address
  because a server-side merge (`gh pr merge` or the web button) uses the GitHub
  primary email, not the local git config. The primary email is now
  `maxence@maxencebernardhub.com`; history not rewritten (checked on PRs #5 and #6).

### Findings (2026-11-10)

- A **classic branch protection rule** on `main` (created by mistake while exploring
  Settings → Branches) required 1 approval with "enforce admins": PR #6 stayed
  `BLOCKED` / `REVIEW_REQUIRED` although the ruleset asks for 0 approvals — the two
  systems stack and a solo maintainer cannot approve their own PR. Deleted; the
  ruleset is the only protection. The ruleset option "Require an additional approval
  for unattributed Copilot pull requests" (`require_extra_approval_for_unattributed_changes`)
  was not the cause and stays at its default.
- Every commit since 2026-10-16 is SSH-signed and "Verified" on GitHub; the 22
  commits of May–June 2026 are unsigned (the ruleset only checks new commits).

**Stopped at:** interlude complete. Next: 4.7 (review findings together, fix with
TDD — F60 and F66 first).

---

## Last session — 2026-11-12 (step 4, part 2 — 4.7)

Step 4.7 — fix the walkthrough, 4.5 and 4.6 findings with TDD (branch
`refactor/walkthrough-foundations`), one block at a time, one commit (or more) per
block, then a `docs(state)` commit so a `/clear` is possible between blocks. Item
list: Next steps → Step 4 → 4.7.

### Plan (validated 2026-11-12)

| # | Block | Items | Status |
| --- | --- | --- | --- |
| 1 | Router: API key | F60, F40, F52 (router) | ✅ `2928e43` |
| 2 | mypy on `tests/` | F2, F65 | — |
| 3 | `db/convert.py` → `db/convert/` package | F19, F26 (imports) | — |
| 4 | Engine factories | F14, F15, F46, F59, F67, F13, F68 | — |
| 5 | `conftest` on the factory + F66 guard | F66, F27, F26 (corrupt JSON, unknown enum) | — |
| 6 | Tables | F17, F18, F23, F25, F55 | — |
| 7 | `AgentSpec` constraints | F3, F72, F53, F54 | — |
| 8 | Other model contracts | F4, F5, F61, F62, F1, F9, F12, F26 (naive date) | — |
| 9 | `PromptLoader` | F32, F33, F44, F47, F34, F63, F70, F58 | — |
| 10 | LLM client | F37 + F71, then F36; F51, F52, F56 | — |
| 11 | Docs | F7, F21, F35, F49 (ADR 0010 amendment), F57; walkthrough "4.7 — Fixes" | — |

Order: F60 first (🟠, isolated); F2 next so mypy checks every test written
afterwards; the `convert` split and the engine factories before F66, whose tests
depend on them; F25 (block 6) removes the `test_db_tables` roundtrips, so F66 only
concerns the `convert` tests. Docstring findings (F52–F56, F58) go with their
module's block.

Decisions taken with the plan (to copy into the Decisions log at the end of 4.7):

- A — `httpx2` declared as a dev dependency (block 10): `MockTransport` is imported
  from it; already in the lock as a transitive dependency of `anthropic`.
- B — `convert` tests split flat, one file per module: `test_db_convert_<domain>.py`.
- C — `visual_character` stays `str`, checked by an `AfterValidator` against a
  `frozenset` reference constant (no type change for callers; JSON Schema exposure
  decided in 4b). `Literal` rejected: it would force a change in
  `org_generation.py:284` (step 7 module).
- D — `WorkHours`: start == end rejected (ambiguous), `24:00` rejected; type defined
  in `agents/models.py`, imported by `generator/models.py`.
- E — explicit engine factories: `make_engine(url)`, `make_session_factory(engine)`
  (`expire_on_commit=False`), `create_db_and_tables(engine)`, `get_session(factory)`
  (signatures change; no caller). The FastAPI app wires them.
- F — `hide_input_in_errors=True` on every domain model, not only the 5 listed.
- G — `BlockingQuestion`: `answered=True` ⇔ `answer` and `answered_at` not None;
  `answered=False` ⇔ both None.
- H — the environment template sets `DATABASE_URL=sqlite:///./data/adjents.db`
  (relative to the working directory), which would override the anchored default
  of F13 → handled in block 4. Also: `.gitignore` gets `data/*.db` (only
  `data/chroma/` and `data/outputs/` are ignored today).
- I — F2 as block 2, before F66.

Checked while planning: `mypy --strict adjents/ tests/` → 53 errors in 5 files (40
`unused-ignore`, 13 `comparison-overlap`); no naive `datetime(` in `adjents/`,
`tests/`, `scripts/`; the direct table writers of steps 6–8 (`SkillTable`,
`MessageTable`) pass every field, so removing table defaults (F17) breaks none;
removing `default=None` on nullable columns probably changes nothing in SQL (to
check in block 6).

### Block 1 — router (`2928e43`)

- F60: the key is stripped whatever its source; blank once stripped, or holding a
  space, control or non-ASCII character → `LLMConfigError` naming no value, no
  `__cause__`. A whitespace-only direct key is rejected, not a fallback to the
  environment (`None` / `""` still fall back). Stricter than the 4.6
  recommendation (non-ASCII rejected too): probe against a local HTTP server — only
  a newline in the key makes the HTTP layer quote it in the exception chain; `é`,
  `\x7f`, `\xa0`, `\x01` are sent to the server as is (an auth failure, no leak).
- F40: tests patch `AnthropicClient` and assert the `api_key` each client receives
  (environment key, direct over environment, `""` falls back); tautological
  assertions removed. These 3 tests passed at once (characterization); the 10 F60
  tests were red first.
- F52 (router part): module docstring names its entry points and its builders (the
  smoke scripts; orchestrators get the client injected).
- `router.py` 67 → 92 lines; 292 tests; lint, typecheck green.

**Stopped at:** block 1 done. Next: block 2 (F2 — `mypy --strict adjents/ tests/`
in Makefile + CI, the 53 test errors; F65).

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
- [x] 3.4b Fix `smoke_generator_interview.py`: the scripted Alex Chen scenario never
  gives the daily rate (`financial_goals`) nor the email / banking tools
  (`existing_tools`), so the interview never reaches `ready_to_generate` (seen in step
  2.5). Complete the scenario only (prompt audit = step 6.3): daily rate €450 (turn 5);
  Google Workspace `alex@luminescence.com` + Qonto business account (turn 6). If the
  scenario is not enough, stop and ask — scenario completed; the smoke run of 3.5
  reaches `ready_to_generate` (scenario change only, prompt untouched)
- [x] 3.5 Re-run the smoke tests (paid — cost estimate approved first) — 3/3 ✅,
  about $1.1 (see Last session 2026-10-22, step 3)

### Step 4 — Walkthrough: foundations

Branch: `refactor/walkthrough-foundations`

Walkthrough notes and findings: `docs/walkthroughs/step-4-foundations.md`.

- [x] 4.1 Walkthrough: models (`agents/`, `messaging/`, `memory/`, `projects/`,
  `deliverables/`, `generator/models.py`) + their tests — findings F1–F12
- [x] 4.2 Walkthrough: `db/` (`tables.py`, `convert.py`, `engine.py`) + tests —
  findings F13–F31
- [x] 4.3 Walkthrough: `prompts/loader.py`, `llm/anthropic_client.py`,
  `llm/types.py`, `llm/errors.py`, `router/router.py` + tests (incl.
  `test_llm_errors.py`) — findings F32–F42
- [x] 4.4 Docstrings + comments — done 2026-10-29, findings F43–F47
  (`anthropic_client.py`, `types.py` and `errors.py`
  already have full docstrings from step 3: review only). From the walkthrough: class
  docstrings for the 6 model modules and module docstrings per the convention —
  purpose, place in the flow, entry points, related ADRs (F8);
  `test_models_agents.py` module docstring lists `BlockingQuestion` (F11);
  `router.py` — docstrings for `LLMRouter` and `LLMConfigError` (API key resolution
  order: direct argument, then `ANTHROPIC_API_KEY`); `prompts/loader.py` — module
  docstring per the convention, docstrings for `PromptLoader`, `LoadedPrompt`,
  `_parse_frontmatter` (F41)
- [x] 4.5 Spec review against ARCHITECTURE §3 + ADRs 0002–0004, and for the LLM layer
  against ADR 0007 (amended), ADR 0012 and ARCHITECTURE §2 / §8 — done 2026-10-29,
  findings F48–F59 (`docs/reviews/2026-10-29-foundations-spec-compliance.md`)
- [x] 4.6 Code review — done 2026-10-29, findings F60–F72
  (`docs/reviews/2026-10-29-foundations-code-review.md`)
- For 4.5 and 4.6, the subagent prompt points to
  `docs/walkthroughs/step-4-foundations.md` and states: findings F1–F59 (F48–F59 from
  the 4.5 spec review, also in its report) are already known and routed — do not
  report them again; report only new findings, or an argued disagreement with an
  existing finding or decision. 4.5 focused on what the walkthrough did not check
  systematically: CLAUDE.md conventions (file size, docstrings, no prompt strings in
  Python source), ADR 0004 and ADR 0010, consistency between the 4.4 docstrings and
  the code. Rationale: avoid re-deriving known findings and de-duplicating them in
  4.7, while keeping an independent review
- [ ] 4.7 Review findings together (walkthrough + 4.5 + 4.6), fix with TDD. Walkthrough
  findings (details in `docs/walkthroughs/step-4-foundations.md`):
  - F1: tests based on `model_copy(update=...)` (no validation) rebuilt through
    `model_validate`
  - F2 (Q2): `mypy --strict adjents/ tests/` in Makefile + CI; all 53 test errors
    fixed, including the tests of steps 7 and 8
  - F3 (Q1): `AgentSpec` invariants in the model (`Field` constraints / validators)
    and reference constants in `agents/models.py`; callers rewired in 7.2 / 8.3.
    F72 (Q1 scope extended): one shared `WorkHours` type with range checks (not a
    format-only pattern), used by `AgentSpec` and `BusinessContext`; an end before
    the start is accepted and documented as a window crossing midnight; boundary
    tests
  - F4: `AwareDatetime` for every `datetime` field
  - F5: `BlockingQuestion` consistency `@model_validator` (ADR 0004 schema kept)
  - F7: `BusinessContext` added to ARCHITECTURE §3 and to its serialization table
    (6 list fields — confirmed in 4.2)
  - F9: tests for the "required but nullable" contract and a JSON-mode roundtrip.
    F61: `Message.metadata` / `Memory.metadata` typed `dict[str, JsonValue]`, and
    `allow_nan=False` in the two `json.dumps` calls (`JsonValue` accepts NaN); tests
    (datetime / tuple → `ValidationError`, NaN rejected)
  - F12: error tests with one missing field each + assertion on `errors()` locations
  - F10: tautological tests accepted as is (no action)
  - F13: DB path anchored on the repository root (`data/adjents.db`, ARCHITECTURE
    §1) instead of the working directory; `create_db_and_tables` creates the
    directory; test. F68: directory creation skips in-memory URLs
    (`make_url().database` is `None`, `":memory:"` or a `file:` URI); tests with
    `:memory:` and `tmp_path / "sub" / "a.db"`
  - F14: engine and session factories in `db/engine.py` (no engine created at
    import), used by `conftest.py`; new `test_db_engine.py` (`_async_url`,
    `create_db_and_tables`, `get_session`). F67: `os.getenv(...) or default` (an
    empty `DATABASE_URL` fails at import today) and a rewrite based on
    `make_url().drivername` (handles `sqlite://`); tests for `""`, `sqlite://`
  - F46 (with F14): `engine.py` imports `adjents.db.tables` (`# noqa: F401`) so
    `create_db_and_tables` always registers the 12 tables; test in a fresh process
  - F15: `expire_on_commit=False` in the shared session factory + test (attribute
    read after commit raises `MissingGreenlet` today). **F66 (🟠, first)**: once
    `conftest` uses that factory, `session.get()` after commit returns the
    identity-map object without any `SELECT`, so the 33 DB roundtrip reads would no
    longer read SQLite — read back in a fresh session (or `expunge_all()`) and add a
    guard test (row corrupted in raw SQL → `*_from_table` raises; also F26's
    corrupt-JSON case)
  - F17: remove the table defaults that diverge from the domain (`is_paused=False`,
    `"[]"`…) so an omission fails with `NOT NULL` instead of a silent value
  - F18: schema drift test (ADR 0002): domain fields == table columns, parametrized,
    with the `metadata` → `metadata_json` rename
  - F19 (Q5): split `db/convert.py` (404 lines) into a `db/convert/` package per
    domain, mirroring the domain modules
  - F21 (Q6): ARCHITECTURE §1 — remove "migrations (via SQLModel)"; §3 — fix
    "`fromisoformat` … timezone-aware" (a naive string stays naive)
  - F23: `test_all_tables_exist` (12 tables, exact set instead of `issubset`,
    docstring); delete the dead `test_unused_import_unused`
  - F25: replace the SQLAlchemy-only table tests with constraint tests (`NOT NULL`
    rejections), alongside F18
  - F26: `test_db_convert.py` — module-level imports; tests for a naive date, corrupt
    JSON and an unknown enum value in a row
  - F27: one fixture decorator style in `conftest.py` (team setup fixtures move in
    8.3)
  - F32 (Q7): remove `LoadedPrompt.render()` and its 2 tests (fails on the prompts'
    own JSON braces; unused in production)
  - F33: frontmatter parser — normalize line endings, raise on an unterminated
    frontmatter block, tests. F70: strip a UTF-8 BOM (`utf-8-sig`); reject any
    non-blank line inside the block that is not `key: value` (an unterminated block
    closed by a `---` rule in the body is not caught otherwise); a quoted value
    needs at least 2 characters; one `tmp_path` test per case
  - F44 (with F33): a value accepted by `isdigit()` but rejected by `int()` (`²`) no
    longer raises an uncaught `ValueError`; test
  - F47 (with F33 / F34): `load_all()` keys built with `as_posix()` (OS-independent
    separator); test
  - F34: loader tests on `tmp_path` files (parser cases from F33); `load_all` tests
    read the cache; no assertion on a real prompt's `model_hint`. F63: `get()`
    rejects keys resolving outside the prompts directory (`..`, absolute) with an
    `is_relative_to` check; `tmp_path` test
  - F35 (Q7): ARCHITECTURE §9 "How prompts are loaded" rewritten — fixed system
    prompts + agent context in a message, no templating today, `PromptLoader(Path)`,
    `load_all()` not called at startup yet
  - F37: 2-3 `AnthropicClient` tests through `httpx2.MockTransport` with the real SDK
    (success with the JSON body actually sent, refusal, mid-stream error event) —
    **before F36**. F71: assert the `Authorization: Bearer` header carries the key,
    and `monkeypatch.delenv` `ANTHROPIC_BASE_URL` / `ANTHROPIC_CUSTOM_HEADERS` (read
    by the SDK even with an explicit key)
  - F36 (Q8): typed `messages.stream(...)` call (no `dict[str, Any]`), `omit` for
    `system`, `_to_message_params()` converting the neutral messages to
    `MessageParam` and rejecting unknown roles, tests
  - ✅ (block 1, `2928e43`) F40: router tests check the `api_key` passed to `AnthropicClient` (direct key
    over environment, environment key used). **F60 (🟠, first)**: the router
    `strip()`s the key and raises `LLMConfigError` (naming no value) when it is
    empty or contains whitespace / control characters — today such a key leaks in
    clear text through the exception chain; tests (`"sk-x\n"` → stripped,
    `"  "` direct or from the environment → `LLMConfigError`)

  From the 4.5 spec review (`docs/reviews/2026-10-29-foundations-spec-compliance.md`):
  - F49 (with F35, Q7 scope extended): ARCHITECTURE §3 "rendered with the agent's
    fields" fixed (fixed system prompts + agent context in a message); **amend** ADR
    0010 accordingly
  - F57 (with F21 / F7): ARCHITECTURE §3 `Message` sketch — `"generator"` sentinel,
    no `"system"`
  - F51: test asserting the truncation WARNING (model, `stop_reason`, tokens, no
    content)
  - F52: `llm/types.py`, `llm/errors.py`, `router/router.py` module docstrings name
    their entry points; `router.py` says who builds the router — `router.py` ✅
    (block 1, `2928e43`); `llm/` in block 10
  - F53, F54, F55: docstrings fixed — skills also created by team setup /
    reconfiguration (`agents/models.py`); org generation sets `PAUSED` at creation
    (`AgentStatus`); the interview also updates a loaded row in place
    (`db/tables.py`)
  - F56: `llm/errors.py` docstring — retry loops cover invalid output (JSON, schema,
    structure), never LLM errors (ADR 0012 sentence: step 4b.2)
  - F58 (with F33 / F44): `_parse_frontmatter` docstring matches the rewritten parser
    (empty frontmatter block)
  - F59 (with F14): `_async_url` — remove the redundant `"aiosqlite" not in raw`
    clause; test with a path containing "aiosqlite"

  From the 4.6 code review (`docs/reviews/2026-10-29-foundations-code-review.md`);
  F60, F61, F63, F66, F67, F68, F70, F71, F72 are folded into the items above:
  - F62: `hide_input_in_errors=True` on the models carrying user content
    (`BusinessContext`, `Message`, `Memory`, `AgentSpec`, `BlockingQuestion`); test
    that `str(exc)` holds no input value (the `InterviewError` message: step 6.3)
  - F65 (with F2): effort tests parametrized with `get_args(Effort)` and typed
    `Effort` (the `# type: ignore` goes); rename
    `test_complete_sends_no_sampling_prefill_or_tool_parameters` (no prefill check)

### Step 4b — Structured outputs

Branch: `feat/structured-outputs` — before steps 6, 7, 8, which adopt it

- [ ] 4b.1 Design a provider-neutral method (Pydantic model in → validated instance
  out); check in their docs only that OpenAI and Gemini offer an equivalent; check
  compatibility with adaptive thinking and the JSON Schema features supported —
  including the `Field` constraints added to `AgentSpec` in step 4.7 (`ge` / `le`,
  `pattern`): which keywords the provider accepts, and what the SDK does with
  unsupported ones (checked in its sources)
- [ ] 4b.2 **Amend** ADR 0012 (the neutral contract gains a method); the same
  amendment corrects §4 "their retry loops only catch `JSONDecodeError`" — org
  generation also retries on schema / structure errors, LLM errors are still never
  retried (step 4.5, F56)
- [ ] 4b.3 TDD: Anthropic implementation (`output_config.format` /
  `messages.parse()`), same `stop_reason` handling and typed errors as `complete()`;
  same typed SDK call (no `dict[str, Any]`) and transport-level tests as `complete()`
  after step 4.7 (F36, F37)
- [ ] 4b.4 Docs (ARCHITECTURE §2) + code review, fixes. Callers adopt it in 6.3, 7.3
  and 8.5b

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
  - schema migration strategy, decided before 5.4 (the first column change on an
    existing table — `create_all` never alters a table, so an existing
    `adjents.db` would fail with "no such column"): (a) drop and recreate,
    documented; (b) Alembic (new dependency); (c) hand-written migrations. Initial
    inclination: (a) for v0.1, (b) before the first release to real users. ADR to
    write (step 4.2 walkthrough, F22 / Q6)
- [ ] 5.2 ADR 0011
- [ ] 5.3 Feature Brief + Implementation Plan
- [ ] 5.4 TDD: `Task` Pydantic model + SQLModel table + convert functions + tests;
  `AgentSpec` reasoning-tier field (step 5.1b) + table column + convert functions +
  tests
- [ ] 5.5 Update ARCHITECTURE §3, §5 (agent loop step 4) and §8 (router inputs)
- [ ] 5.6 Spec review + code review, fixes

### Step 6 — Walkthrough: Generator Agent interview

Branch: `refactor/walkthrough-interview`

- [ ] 6.1 Walkthrough: `test_generator_interview.py` → `generator/interview.py` →
  `prompts/generator/interview.md` + `extract_business_context.md` → run
  `smoke_generator_interview.py --llm-debug`
- [ ] 6.2 Tech debt: `resume()` N sequential SELECTs → single `WHERE id IN (...)`
  query (TDD, test asserting the query count). The `message_ids` read-modify-write
  in the same code stays out of scope (Technical debt, MessageDispatcher — F30), but
  `_persist_messages` stops serializing `message_ids` itself
  (`row.message_ids = json.dumps(...)`, `interview.py:197`) and goes through
  `db/convert` (ADR 0002: JSON only in `db/` — step 4.5, F48)
- [ ] 6.2b Partial state: `reply()` persists the user message before the LLM call, so a
  failed call (network, refusal, truncation) leaves the stored conversation ending with
  an unanswered user message — decide the fix (TDD)
- [ ] 6.3 Prompt audit for Claude 5.5 (patterns written for 4.x models — e.g.
  `/claude-api prompt-audit`); adopt structured outputs (step 4b) for interview turns
  and `BusinessContext` extraction; unknown keys in the extraction JSON are dropped
  silently (`BusinessContext(**data)` with Pydantic's default `extra="ignore"`) —
  decide: forbid, log, or accept (step 4.1 walkthrough). From the step 4.6 code
  review: the `InterviewError` raised on a `ValidationError` embeds `str(exc)`, i.e.
  LLM-extracted business data (`interview.py:226-229`, F62 — counters, never content);
  a non-object extraction JSON (`[]`, `"text"`) raises `TypeError` / `AttributeError`
  on `data.pop` instead of `InterviewError` (`interview.py:211-218`, checked;
  probably moot with structured outputs)
- [ ] 6.4 Docstrings + comments
- [ ] 6.5 Spec review (against the 2026-05-20 Feature Brief; LLM calls against ADR
  0012) + code review, fixes

### Step 7 — Walkthrough: Generator Agent org generation

Branch: `refactor/walkthrough-org-generation`

- [ ] 7.1 Walkthrough: `test_generator_org_generation.py` →
  `generator/org_generation.py` → `prompts/generator/org_generation.md` → run
  `smoke_generator_org.py --llm-debug`
- [ ] 7.2 Split `org_generation.py` (442 lines) into a package by responsibility
  (draft: `models.py`, `validation.py`, `parsing.py`, `generator.py`); split the test
  file accordingly (one test file per module); `_validate_structure` returns all
  violations, not only the first (fewer paid retries); use the `AgentSpec` reference
  constants from `agents/models.py` (step 4.7, Q1) instead of local literals
- [ ] 7.3 Prompt audit for Claude 5.5 (e.g. `/claude-api prompt-audit`); adopt
  structured outputs (step 4b); the
  Generator assigns each agent's reasoning tier (step 5.1b) — prompt + validation.
  Decide whether the larger orgs generated by Opus 5.5 are desirable (Sophie: 29
  agents / 18 N-2 / 88 skills vs 13 / 2 / 36 on Opus 4.7 — see step 3 smoke tests)
- [ ] 7.4 Docstrings + comments
- [ ] 7.5 Spec review (against the 2026-05-22 Feature Brief; LLM calls against ADR
  0012) + code review, fixes

### Step 8 — Walkthrough: post-generation team setup + code review fixes

Branch: `refactor/walkthrough-team-setup`

- [ ] 8.1 Walkthrough: team setup tests → `generator/team_setup.py`,
  `agents/reconfiguration.py`, `utils/agent_context.py` → prompts `agent/intro.md` +
  `extract_agent_adjustments.md` → run `smoke_team_setup.py --real --llm-debug`.
  Observe how team setup / reconfiguration group messages (no `Conversation` row,
  `metadata["conv_id"]`, step 4.4 walkthrough F45)
- [ ] 8.2 B1 (TDD — failing test first): JSON-serialize `responsibilities` /
  `escalation_rules` in `_apply_agent_updates`. Same root cause: `_apply_agent_updates`
  (both copies) and the state updates `setattr` on SQLModel table rows, which never
  validate — route updates through the `AgentSpec` domain model (constraints from
  step 4.7) before writing the row (step 4.1 walkthrough)
- [ ] 8.3 B2: split `team_setup.py` (851 lines) into a package; extract the logic
  shared with `reconfiguration.py` (310 lines, past the 300-line review trigger) —
  extraction LLM call + `_apply_agent_updates` + persistence helpers + the duplicated
  effort constants — into one module, removing the ~70 duplicated lines; use the
  `AgentSpec` reference constants from `agents/models.py` (step 4.7, Q1) instead of
  `_INTERVAL_MIN/MAX` and the lazy `VALID_VISUAL_CHARACTERS` import; move the domain
  models `ValidationSession`, `AgentValidationRecord`, `AgentValidationStatus` (now in
  `team_setup.py`) into a models module; split
  `test_team_setup_orchestrator.py` (1,358 lines) accordingly. From the step 4.2
  walkthrough: once the models have moved, `db/convert` no longer imports
  `generator/team_setup.py` → remove the 9 lazy `db.convert` imports (F20); move the
  validation table / conversion tests into the `db/` test files (F24) and the team
  setup fixtures (`stub_prompt_loader`, `mini_org`, `coo_only_org`) out of the global
  `conftest.py` (F27); `stub_prompt_loader` returns a prompt per key (`spec=LoadedPrompt`)
  or the tests assert the requested keys (F31); decide whether to introduce a
  repository layer (ADR 0003 mentions "repository functions"; DB access is scattered
  across 4 orchestrators — ADR candidate, F28)
- [ ] 8.4 Warnings A1–A5 (asserts as flow control, `validate_team` guard, circular
  import risk, misleading resumability, `reply()` before `start()` guard)
- [ ] 8.5 Notes N1–N3: decide together (fix or accept)
- [ ] 8.5b Adopt structured outputs (step 4b) for the adjustments extraction; team
  setup / reconfiguration can adjust the agent's reasoning tier (step 5.1b)
- [ ] 8.5c Prompt audit for Claude 5.5 of `agent/intro.md` and
  `extract_agent_adjustments.md` (written for Sonnet 4.6 — e.g.
  `/claude-api prompt-audit`)
- [ ] 8.6 Smoke scripts: move the duplicated helpers (`_hr`, `_load_env`, DB setup…)
  into `scripts/_common.py` (created in step 3); `smoke_team_setup.py` is 635 lines.
  Add a shared handler for SDK transport errors (`anthropic.APIConnectionError`,
  `APIStatusError`) printing a short diagnostic instead of the full traceback, which
  can hold the API key (step 4.6 code review, F60)
- [ ] 8.7 Docstrings + comments
- [ ] 8.8 New code review on the result (LLM calls against ADR 0012), fixes

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
    sampling parameters (e.g. temperature) for non-Anthropic providers. Anthropic:
    an error event in the middle of a stream (e.g. `overloaded_error` after a 200)
    surfaces as a generic `APIStatusError` with `status_code == 200` and is not
    retried by the SDK, while the same error on the initial response is an
    `OverloadedError` retried twice — classify on `body["error"]["type"]`, not on the
    HTTP status (step 4.3 walkthrough, F38, checked against `anthropic` 2.1.0)
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
- [ ] 10.2 OpenAI, Google and Ollama clients implementing the ADR 0012 contract;
  introduce the `LLMClient` protocol (callers stop depending on `AnthropicClient`);
  model choice for each provider
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
  outputs: provider-neutral method in **step 4b**, adopted in **steps 6, 7, 8**
- No prompt caching: multi-turn conversations resend the system prompt + history at
  full input price on every turn → **step 10** (measured with the per-call traces)
- Multi-turn conversations replay only the text of earlier replies, not their thinking
  blocks (preserved-thinking rules: append-only history, model-bound blocks, billed as
  input) → decided with the **agent loop** design (v0.1, after step 10), together with
  its action mechanism (parsed JSON actions, ARCHITECTURE §5 step 5d, vs internal
  tools — thinking-block replay is mandatory inside a tool-use loop)
- Root `README.md` gives `ollama pull qwen2.5:7b` as the example model while
  `qwen3.5:9b` is installed → **step 10.3** (local model choice)
- The DEBUG usage line logs output tokens only; input / cache tokens are not logged,
  so smoke-test cost is partly estimated → per-call tracing in **step 10**
- `work_hours` in `AgentSpec`: single daily window (`"HH:MM-HH:MM"`) applied uniformly
  every day — no day-of-week granularity, no multi-window support; per-agent independent
  schedules ARE supported (each `AgentSpec` has its own field); day-of-week variation
  (e.g. "Tue nights OK, Thu nights not") is a v0.2 enhancement
- Pause has two representations — `AgentSpec.is_paused` (user-controlled, rule 7) and
  `AgentStatus.PAUSED` in `AgentState` — with no documented invariant; `is_paused`
  changes at runtime but lives in the "write-once" spec (ARCHITECTURE §3) → decided
  with the **agent loop** design (walkthrough finding F6, step 4.1)
- `Message.from_agent` / `to_agent` mix agent IDs and sentinel strings (`"user"`,
  `"system"`) → decided with the **MessageDispatcher** design (ARCHITECTURE §4)
- `Deliverable.file_path` is meant to be relative to `data/outputs/`, but nothing
  rejects `..` or absolute paths (path traversal once deliverables are written to
  disk) → **Deliverables feature**
- No foreign key in `db/tables.py` and SQLite's `PRAGMA foreign_keys` is off by
  default: orphans and dangling references are accepted (checked). Scope when done:
  plain foreign keys (`agent_states.agent_id`, `parent_id`, `blocking_questions`,
  `deliverables`, `projects`, validation records…), a `connect` listener enabling the
  pragma in the engine factory, sorting agents by level before insert in
  `org_generation` (rows of one table are inserted in `add()` order, so the
  self-referencing `parent_id` fails otherwise — checked), tests. JSON-list references
  (`skill_ids`, `message_ids`…) would need association tables → decided with the
  **FastAPI app / agent loop** (agent deletion, concurrent writers) (walkthrough F16,
  step 4.2 Q4). The same `connect` listener also sets the journal mode (WAL) and an
  explicit `busy_timeout`: with today's file-engine defaults (`journal_mode=delete`,
  `busy_timeout=5000`) a second writer fails with "database is locked" after 5 s
  (checked); test with two sessions on a `tmp_path` file DB. Also decide whether
  orchestrators may hold a write transaction across an LLM `await` (step 4.6 code
  review, F69)
- `MemoryTable` (`memories`) is used by nothing and appears in neither ARCHITECTURE §3
  nor §7 (memory lives in Chroma): SQLite source of truth with Chroma as an index, or a
  dead table → **Memory feature** (walkthrough F29)
- Appending a message rewrites the whole `Conversation.message_ids` JSON array
  (read-modify-write, `interview.py:176-197`), and `Message` has no
  `conversation_id`: with concurrent writers, messages would be lost →
  **MessageDispatcher** design (walkthrough F30; same code as step 6.2)
- No schema migration strategy (`create_all` never alters an existing table) →
  **step 5.1b** (ADR, before the first column change in 5.4)
- No repository layer despite ADR 0003's "repository functions" → **step 8.3**
  (walkthrough F28)
- `make dev` starts `adjents.api.main:app`, which does not exist yet: the backend half
  of `make dev` fails today → **FastAPI app** feature
- `LLMRouter` builds 2 `AsyncAnthropic` clients (2 connection pools) and nothing ever
  closes them → the app builds one router and closes its clients on shutdown
  (lifespan) → **FastAPI app** feature (walkthrough F39)
- Thinking summaries (user business data) are logged as soon as the `adjents` or root
  logger is at DEBUG, not only when `adjents.llm.thinking` is enabled on purpose
  (checked) → the app's logging configuration sets `adjents.llm.thinking` explicitly
  → **FastAPI app** feature (walkthrough F42, ADR 0012 §6)
- No prompt templating once `render()` is removed (step 4.7, Q7): agent context
  reaches the LLM in a message (`_build_agent_context_message`), system prompts are
  fixed. If a prompt ever needs variables, decide the mechanism (`string.Template`
  as candidate — works on every current prompt, checked) → **agent loop** design
- Nothing in the application loads the dotenv file: `LLMRouter` and `db/engine.py`
  read the process environment only, and `LLMConfigError` tells the user to set the
  key "in .env" — only the smoke scripts load it (`_load_env`) → the app loads it at
  startup → **FastAPI app** feature (walkthrough F43)
- Two ways to group messages into a conversation: the interview writes a
  `Conversation` row with ordered `message_ids`; team setup and reconfiguration write
  no `Conversation` row and store the conversation id in `metadata["conv_id"]`
  (`AgentValidationRecord.conversation_ids` references no `conversations` row) →
  observed in **step 8.1**, one conversation model decided with the
  **MessageDispatcher** design, together with F30 (walkthrough F45)
- `PromptLoader` reads prompt files synchronously (`read_text`) on the first `get()`
  of each key, from async callers, because nothing calls `load_all()` — contrary to
  "`async def` for I/O" (CLAUDE.md) and to ARCHITECTURE §9 "loaded at startup" →
  the app calls `load_all()` once at startup (lifespan), so runtime `get()` only hits
  the cache; no async conversion → **FastAPI app** feature (step 4.5 spec review,
  F50)
- `LLMResponseError`, `LLMRefusalError`, `LLMTruncatedError` cannot be pickled or
  deep-copied (keyword-only constructors; `BaseException.__reduce__` rebuilds from
  `args` → `TypeError`, checked): a process boundary would turn a refusal into
  another error. No such boundary today → add `__reduce__` + a pickle roundtrip test
  per class at the first one (e.g. eval runs, **step 10**) (step 4.6 code review,
  F64)

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
| 2026-10-22 | Structured outputs: neutral method in a dedicated step 4b (`feat/structured-outputs`, ADR 0012 amendment), adopted in steps 6, 7, 8 | Removes JSON retry loops without reopening callers after their walkthroughs; a new capability does not belong in a walkthrough (`refactor/`) branch |
| 2026-10-22 | Plan amended after step 3: step 4 walkthrough covers `llm/types.py` / `llm/errors.py` and reviews the LLM layer against ADRs 0007 / 0012; step 5 also adds the `AgentSpec` reasoning tier; prompt audit added for team setup (8.5c); `LLMClient` protocol in 10.2 | Keep the plan consistent with the step 3 changes; the team setup prompts were written for Sonnet 4.6 like the Generator ones |
| 2026-10-22 | LLM call contract = ADR 0012 (0011 stays reserved for `Task`) | ADR numbers are stable identifiers; a temporary gap is harmless |
| 2026-10-22 | Smoke scripts get `--llm-debug`; `scripts/_common.py` created in step 3 (ahead of step 8.6) | One shared logging setup instead of three copies; real usage figures to calibrate `max_tokens` |
| 2026-10-23 | `AgentSpec` invariants (`visual_character` set, interval range, `level ≥ 0`, `work_hours` format) move into the model with reference constants in `agents/models.py` (step 4.7); callers rewired in steps 7.2 and 8.3, keeping their own policy (reject vs clamp) | "What is valid data" is independent of how the LLM produces JSON (step 4b) and applies to every writer; today the rules are duplicated in 3 places with diverging policies |
| 2026-10-23 | mypy `--strict` also checks `tests/` (Makefile + CI); the 53 existing errors are fixed in step 4.7, including the tests of steps 7 and 8 | The tests' `# type: ignore` comments showed the intent, but nothing checked them; mechanical fixes, no logic change |
| 2026-10-23 | Walkthrough notes (explanations, Q&A, findings, decisions) in `docs/walkthroughs/`, one file per walkthrough step | Survives `/clear`; keeps PROJECT_STATE short; separate from the subagent reports in `docs/reviews/` |
| 2026-10-23 | Foreign keys + `PRAGMA foreign_keys=ON` postponed to Technical debt, decided with the FastAPI app / agent loop | No orphan is possible today outside a bug (sequential writers, only skills are deleted); enabling them also requires sorting agents by level before insert in org generation — a behavior change that does not belong in a walkthrough |
| 2026-10-23 | `db/convert.py` split into a `db/convert/` package per domain in step 4.7 (option b) | Explicit, `mypy --strict`-friendly mapping kept; files well under 300 lines; `Task` (step 5) gets its own module. Rejected: documented exception (a), generic field-list-driven converter (c: less code, but hard to type) |
| 2026-10-23 | Schema migration strategy decided in step 5.1b with an ADR, before the first column change (5.4); ARCHITECTURE §1 "migrations (via SQLModel)" removed in step 4.7 | `create_all` only creates missing tables, so an existing `adjents.db` fails with "no such column" after a column is added (checked); no database exists on disk yet, so nothing breaks before step 5 |
| 2026-10-23 | `LoadedPrompt.render()` removed in step 4.7; system prompts stay fixed and agent context goes in a message; templating, if ever needed, decided with the agent loop | `render()` fails on the prompts' own JSON braces (3 of 5 production prompts) and has no caller; the context-message pattern already exists and keeps one shared system-prompt prefix for prompt caching. Rejected: `string.Template` now (API without consumer), escaping braces (fragile hand-edited prompts), documented status quo (keeps a trap) |
| 2026-10-23 | `AnthropicClient` calls the SDK with typed arguments (no `dict[str, Any]`) and converts the neutral messages to `MessageParam`, in step 4.7 after transport-level tests (not deferred to step 10.2) | mypy then rejects a misspelled parameter value before a paid call; protects steps 4b, 6, 7, 8, which touch these calls; step 10.2 only changes the conversion's input type |
| 2026-10-29 | 4.4 docstrings for code that 4.7 removes or restructures: `render()` one factual line; `db/convert.py` module docstring only; `db/engine.py` documented as is, factually; untyped SDK call left uncommented | Describe what exists at the level a reader needs today; 24 full docstrings would push `convert.py` past the 500-line hard limit before its split; omitting load-bearing facts would make docstrings incomplete for 4.5 |
| 2026-10-29 | Model fields documented in a Google `Attributes:` section, inline field comments moved into it (also for steps 6.4, 7.4, 8.7) | IDE hover shows docstrings, not comments; one source avoids drift; same style as `llm/errors.py` |
| 2026-10-29 | Q7 scope extended (step 4.5, F49): step 4.7 also fixes ARCHITECTURE §3 and amends ADR 0010 ("prompts rendered with the agent's fields" → fixed system prompts + agent context in a message) | Otherwise the same inaccurate statement survives in two places once §9 is rewritten; ADRs are amended, never rewritten |
| 2026-10-29 | Milestone "Spec Review" set to ⚠️ (4.7) for the models and database rows; the "LLM router" and "LLM clients" rows stay unchanged until those features formally start (step 10), although 4.5 reviewed `router.py` and `anthropic_client.py` | ⚠️ = done with open findings (legend); the LLM rows track features not started yet |
| 2026-10-29 | Q1 scope extended (step 4.6, F72): one shared `WorkHours` type with range checks for `AgentSpec` and `BusinessContext`; an end before the start = a window crossing midnight, accepted and documented | A format-only pattern accepts `99:99-25:00`; constraining only `AgentSpec` moves an invalid extraction value into paid org generation retries; a solopreneur working late is a legitimate case |
| 2026-10-29 | WAL + explicit `busy_timeout` merged into the foreign-keys Technical debt entry (Q4), not into the 4.7 engine factory (step 4.6, F69) | One `connect` listener for every SQLite pragma; no file database and no concurrent writer exist before the FastAPI app / agent loop |
| 2026-10-29 | Pickling the LLM errors left to Technical debt (step 4.6, F64); milestone "Code Review" set to ⚠️ (4.7) for the models and database rows | No process boundary consumes them today (same reasoning as Q7); ⚠️ = done with open findings |
| 2026-11-10 | MIT kept for the public release; no external code contributions without a CLA; brand not licensed; license of future versions reviewed if a paid hosted version is prepared or traction makes a commercial clone plausible (ADR 0013) | Primary purpose is a public portfolio; in this market the code is not the moat (funded SaaS and MIT clones exist); sole copyright keeps relicensing open. Rejected: FSL, AGPL, Apache-2.0, BSL, custom licenses, no license |
| 2026-11-10 | Repository public; `main` protected by a single ruleset (`protect-main`), never by a classic branch protection rule | Rulesets are GitHub's current mechanism; a classic rule stacks with the ruleset and its approval count blocks a solo maintainer |
| 2026-11-10 | CI `GITHUB_TOKEN` declared read-only in `ci.yml`, on top of the repository default | Defense in depth against a compromised third-party action; independent of the repository setting |
