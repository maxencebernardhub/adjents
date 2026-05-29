# Project State

> Updated: 2026-05-29 | Branch: feat/post-generation-team-setup | Milestone: v0.1 — MVP

---

## Milestone progress — v0.1

| Feature | Spec | Impl | Tests |
| --- | :---: | :---: | :---: |
| Project scaffold | ✅ | ✅ | — |
| Core Pydantic models (`AgentSpec`, `AgentState`, `Message`, etc.) | — | ✅ | ✅ |
| Database layer (SQLModel + SQLite) | — | ✅ | ✅ |
| Generator Agent — interview | ✅ | ✅ | ✅ |
| Generator Agent — org generation | ✅ | ✅ | ✅ |
| Post-generation team setup (user ↔ agents) | ✅ | ✅ | ✅ |
| LLM router | — | ✅ (Anthropic only) | ✅ |
| LLM clients (Ollama, Anthropic, OpenAI, Google) | — | ✅ (Anthropic only) | ✅ |
| Async message dispatcher | — | — | — |
| Agent loop (asyncio, pause/resume, work hours) | — | — | — |
| Memory layer (Chroma — per-agent + global KB) | — | — | — |
| Deliverables output (`data/outputs/`) | — | — | — |
| FastAPI app + REST routes | — | — | — |
| WebSocket handler (real-time agent state) | — | — | — |
| Onboarding view (React) | — | — | — |
| 2D workspace (PixiJS) | — | — | — |
| Org chart view (React) | — | — | — |
| Blocking questions UI | — | — | — |
| Deliverables view (React) | — | — | — |

---

## Environment

| Step | Status |
| --- | :---: |
| `.env` created from `.env.example` | ✅ |
| `git init` + scaffold commit | ✅ |
| `uv sync` (backend deps) | ✅ |
| `pnpm install` (frontend deps) | ✅ |
| Ollama running + model pulled (`qwen3.5:9b`) | ✅ |

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

## Next steps

1. Phase 6: code review (`code-reviewer` subagent)
2. Commit + merge `feat/post-generation-team-setup` into main
3. Next feature: LLM Router

---

## Technical debt

- `eslint.config.js`: written against ESLint 9 API — may need adjustments for ESLint 10 after `pnpm install`
- `vite.config.ts`: written against Vite 6 API — to validate against installed Vite 8
- `resume()` in `GeneratorInterview`: N sequential SELECTs (one per message) — acceptable
  for v0.1 short conversations, replace with `WHERE id IN (...)` if conversations grow
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
| 2026-05-25 | `AnthropicClient` streams unconditionally via `messages.stream()` (ADR 0007) | SDK raises `ValueError` for `messages.create()` with `max_tokens > 8192` on Opus 4+ |
| 2026-05-25 | N-1 leaf nodes valid; N-2 count driven by context, not enforced; skills no upper cap | Initial org is a first draft — N-1 setup conversations refine scope and spawn specialists (ADR 0006) |
| 2026-05-25 | `generate()` accepts optional `on_agent_ready` callback for progress reporting | Pattern for future WebSocket streaming of org generation progress to the frontend |
| 2026-05-27 | Natural conversation + single extraction call at validation time (ADR 0008) | Avoids per-turn JSON fragility; one clean extraction when the user is satisfied |
| 2026-05-27 | Direct reconfiguration v0.1; parent-mediated governance for `work_hours`/`responsibilities`/`role_description` in v0.2 (ADR 0009) | Skills are descriptive only in v0.1 (no execution barrier); governance deferred until agents are autonomous |
| 2026-05-28 | `_apply_agent_updates` + `_call_extraction_llm` duplicated between `TeamSetupOrchestrator` and `AgentReconfiguration` | Avoids cross-direction `generator/ → agents/` dependency at v0.1 scale; accepted per ADR 0008 |
| 2026-05-28 | `sqlmodel.select` required (not `sqlalchemy.select`) for typed SQLModel `exec()` results | `sqlalchemy.select` returns `Row` tuples; `sqlmodel.select` returns scalar model instances |
