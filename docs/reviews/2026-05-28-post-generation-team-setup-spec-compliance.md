# Spec Compliance Review — Post-generation team setup

**Date**: 2026-05-28
**Corrections applied**: 2026-05-29
**Branch**: `feat/post-generation-team-setup`
**Reviewer**: spec-reviewer subagent
**Verdict**: ✅ Fully compliant (post-corrections)

---

## Feature Brief — Acceptance criteria

### Mode 1 — Post-generation team setup

| Criterion | Status | Evidence |
| --- | :---: | --- |
| `start_session()` creates one `ValidationSession` + one `AgentValidationRecord` per COO and N-1, all `status="pending"` | ✅ | `team_setup.py:207-254` |
| `start_session()` raises `TeamSetupError` if session already exists | ✅ | `team_setup.py:213-215` |
| `resume_session()` returns existing incomplete session or `None` | ✅ | `team_setup.py:256-263` |
| COO must be validated/skipped before N-1 starts; raises `TeamSetupError` | ✅ | `team_setup.py:296-311` |
| `start_agent_conversation()` makes LLM call, returns opening message | ✅ | `team_setup.py:269-341` |
| In-progress resume: restores conversation, produces "continuation" message | ✅ | `team_setup.py:277-291` |
| COO `navigation_stack=[coo_id]`, `visited_agent_ids=[]` on fresh start | ✅ | `team_setup.py:335-336` |
| N-1 depth-first traversal via `_advance_traversal` | ✅ | `team_setup.py:366-456` |
| `reply()` routes to `active_agent_id` | ✅ | `team_setup.py:343-360` |
| `complete_current_agent()` always returns `str` | ✅ | Both branches return string |
| Caller detects subtree completion by `navigation_stack == []` | ✅ | `team_setup.py:451` |
| `active_agent_id = root_agent_id` when delivering final summary | ✅ | Fixed (V1): `record.active_agent_id = root_agent_id` set before final LLM call |
| Traversal state persisted after every call | ✅ | `_save_record` called after each step |
| `validate_team()`: extraction LLM, atomic DB update, `status="validated"`, state reverts to `PAUSED`, fires `_go_live` if all done | ✅ | `team_setup.py:462-477` |
| `skip_agent()` returns subtree summary + warning, marks `skipped` | ✅ | Fixed (G3): returns `dict[str, Any]` with `"summary"` and `"warning"` keys; warning includes agent name and ID |
| `skip_all()` returns full org summary + warning dict, marks all `skipped`, triggers go-live | ✅ | Fixed (G4): returns `dict[str, Any]` with `"summary"` and `"warning"` keys |
| `get_subtree_summary(Optional[str])` handles `None` for full-org case | ✅ | Fixed (G5): signature is `(self, agent_id: str \| None)`, `None` returns full org |
| `_go_live()` sets all `is_paused=False`, all states `IDLE`, sets `completed_at` atomically | ✅ | `team_setup.py:536-553` — single commit |

### Mode 2 — Direct agent reconfiguration

| Criterion | Status | Evidence |
| --- | :---: | --- |
| `AgentReconfiguration(agent_id, client, prompt_loader, session)` | ✅ | `reconfiguration.py:30-44` |
| `start()` loads `AgentSpec` + direct reports, sets `IN_MEETING_1ON1`, returns opening message | ✅ | `reconfiguration.py:46-77` |
| `reply()` continues conversation | ✅ | `reconfiguration.py:79-88` |
| `apply_changes()` runs extraction, applies to DB, restores prior `AgentState.status` | ✅ | `reconfiguration.py:90-100` |
| No `ValidationSession` or `AgentValidationRecord` created | ✅ | Confirmed absent |
| No go-live logic | ✅ | Confirmed absent |

### Shared — extraction and apply

| Criterion | Status | Evidence |
| --- | :---: | --- |
| Both use `prompts/agent/intro.md` and `prompts/agent/extract_agent_adjustments.md` | ✅ | Both files load by name |
| Agent data injected as first user message, not in system prompt | ✅ | `team_setup.py:324-325`; `reconfiguration.py:69-70` |
| Every injected agent block includes `agent_id` UUID | ✅ | `_build_agent_context_message` first line |
| `prompt.content` used (not `prompt.render()`) | ✅ | Used throughout |
| Frozen fields silently dropped | ✅ | Both `_apply_agent_updates` copies |
| Frozen fields: warning logged | ✅ | Fixed (G1): `_log.warning("Dropping frozen field %r for agent %s", key, agent_id)` in both copies |
| `visual_character` not in valid list: dropped, warning logged | ✅ | Both files |
| `scheduler_interval_seconds` outside [300,3600]: clamped, warning logged | ✅ | Both files |
| Extraction invalid JSON: retry up to `_MAX_RETRIES=3` | ✅ | Both files |
| Extraction exhausted retries: raise `TeamSetupError` | ✅ | Fixed (V3): `AgentReconfiguration` now raises `TeamSetupError` (from `adjents.errors`) |
| Skill name not found: warning logged, skip gracefully | ✅ | Fixed (G2): `_log.warning("Skill %r not found for removal/update on agent %s", ...)` in both files |

---

## Feature Brief — Edge cases and constraints

| Item | Status | Evidence |
| --- | :---: | --- |
| Org has only COO (no N-1s): go-live triggered after COO validation | ✅ | `test_coo_only_org_validate_team_triggers_go_live` |
| Leaf agent: no subtree traversal | ✅ | `_advance_traversal` returns `(None,[],...)` |
| Interrupted mid-N-3: resume restores exact state | ✅ | `navigation_stack` + `active_conversation_id` persisted |
| `validate_team()` before all sub-agents visited: allowed | ✅ | Extraction runs on `conversation_ids` at that moment |
| All agents skipped individually: go-live triggered | ✅ | `_maybe_go_live` checks all records |
| Extraction returns no changes: handled gracefully | ✅ | Empty `agent_updates` handled |
| Extraction returns frozen field: dropped, warning logged | ✅ | Fixed (G1): `_log.warning` present in both files |
| Extraction returns invalid `visual_character`: dropped, warning logged | ✅ | `_log.warning` present |
| Skill name not found: warning, skip | ✅ | Fixed (G2): `_log.warning` present in both files |
| All extraction retries exhausted: `TeamSetupError` raised | ✅ | Both `team_setup.py` and `reconfiguration.py` |
| `start_session()` when session exists: `TeamSetupError` | ✅ | `team_setup.py:213-215` |
| Mode 2 on leaf agent: no subtree context | ✅ | `_load_direct_reports` returns empty list |

---

## Implementation Plan — Tasks

| Task / File | Status | Notes |
| --- | :---: | --- |
| T1 — `tables.py`: `ValidationSessionTable`, `AgentValidationRecordTable` | ✅ | `tables.py:143-164` |
| T1 — `convert.py`: 4 convert functions | ✅ | `convert.py:344-404` |
| T1 — `team_setup.py` models: enums, Pydantic models | ✅ | `team_setup.py:33-60` |
| T1 — `errors.py`: `TeamSetupError` (shared module) | ✅ | Fixed (V3/D2): `adjents/errors.py` created |
| T1 — `test_team_setup_models.py`: 9 tests | ✅ | All 9 present |
| T2 — `_advance_traversal` pure function | ✅ | `team_setup.py:68-98` |
| T2 — `utils/agent_context.py`: `_build_agent_context_message` (shared module) | ✅ | Fixed (D2): `adjents/utils/agent_context.py` created |
| T2 — `test_team_setup.py`: 9 traversal + 3 context tests | ✅ | All 12 present + 1 bonus; imports updated to `adjents.utils.agent_context` |
| T3 — `prompts/agent/intro.md` | ✅ | Fixed (V2): Feature Brief COO intro rule updated to align with ADR 0006 — agents present direct reports in opening message |
| T3 — `prompts/agent/extract_agent_adjustments.md` | ✅ | Matches spec |
| T4 — `TeamSetupOrchestrator` full implementation | ✅ | All methods present |
| T4 — `test_team_setup_orchestrator.py`: all specified tests | ✅ | 41 tests including new V1/G3/G4/G5 tests |
| T4 — `conftest.py`: `mini_org` and `coo_only_org` fixtures | ✅ | Both present |
| T4 — `_MAX_RETRIES` as class constant | ✅ | Fixed (D1): `_MAX_RETRIES: int = 3` as class attribute in both classes |
| T5 — `agents/reconfiguration.py`: `AgentReconfiguration` | ✅ | All methods present |
| T5 — `test_agent_reconfiguration.py`: 7 tests | ✅ | 8 tests (original 7 + V3 retry test) |
| T5 — `_apply_agent_updates` duplicated; `_build_agent_context_message` shared via `adjents.utils` | ✅ | Fixed (D2): no cross-direction import; both classes import from `adjents.utils.agent_context` |
| T5 — `_call_extraction_llm` signatures harmonized | ✅ | Fixed (D3): both take `conversations: list[str]` |
| T6 — `scripts/smoke_team_setup.py` | ✅ | Mock + real modes; `skip_all` result asserted as dict |
| T7 — ADR 0008 created | ✅ | `docs/decisions/0008-...` |
| T7 — ADR 0009 created | ✅ | `docs/decisions/0009-...` |
| T7 — `ARCHITECTURE.md`, `VISION.md`, ADR 0005, ADR 0006 updated | ✅ | All modified |
| T7 — `PROJECT_STATE.md`, `README.md`, `backend/README.md` updated | ✅ | All modified |

---

## ADR compliance

| Decision | ADR | Status | Notes |
| --- | --- | :---: | --- |
| Frozen fields (`domain`, `level`, `parent_id`) silently dropped + warning logged | 0005, 0008 | ✅ | Fixed (G1): warning logged in both `_apply_agent_updates` copies |
| Plain UPDATE for AgentSpec/Skill — no DELETE+re-INSERT | 0005 | ✅ | `setattr` on existing row |
| `AgentReconfiguration` allows all non-structural fields in v0.1 | 0009 | ✅ | All modifiable fields handled |
| No FastAPI endpoint in this feature | 0009 | ✅ | Confirmed absent |
| Single extraction LLM call at validation time (Option B) | 0008 | ✅ | Called in `validate_team` and `apply_changes` |
| No cross-direction import between `generator/` and `agents/` | 0008 | ✅ | Fixed (D2): `_build_agent_context_message` moved to `adjents/utils/agent_context.py` |
| `AnthropicClient` constructed with `claude-sonnet-4-6`, NOT via `LLMRouter` | 0008 | ✅ | Smoke test and orchestrator confirm |
| Retry up to `_MAX_RETRIES=3`, raise `TeamSetupError` on exhaustion | 0008 | ✅ | Fixed (V3): `AgentReconfiguration` now raises `TeamSetupError` from `adjents.errors` |
| `visual_character` validated; `scheduler_interval_seconds` clamped | 0008 | ✅ | Both enforced |
| `AgentState.status = IN_MEETING_1ON1` on start, restored after | 0009 | ✅ | Both modes |

---

## Corrections applied (2026-05-29)

All findings from the initial review have been resolved. Summary of changes made:

| # | Type | Finding | Resolution |
| --- | --- | --- | --- |
| V1 | Violation | `active_agent_id = None` instead of `root_agent_id` after subtree exhaustion | `team_setup.py`: `record.active_agent_id = root_agent_id` set before final LLM call |
| V2 | Violation | Feature Brief COO intro rule contradicted ADR 0006 and `intro.md` | Feature Brief updated: COO **does** present direct reports in opening message |
| V3 | Violation | `AgentReconfiguration` raised `ValueError` instead of `TeamSetupError` | `TeamSetupError` moved to `adjents/errors.py`; both classes import and raise it |
| G1 | Gap | No `_log.warning()` for frozen field drops | `_log.warning("Dropping frozen field %r for agent %s", key, agent_id)` added to both `_apply_agent_updates` copies |
| G2 | Gap | No `_log.warning()` for skill name not found (remove/update) | `_log.warning(...)` added for both removal and update paths in both files |
| G3 | Gap | `skip_agent()` returned `str` instead of `dict[str, Any]` | Now returns `{"summary": ..., "warning": "Agent 'name' (id) and their subtree were skipped..."}` |
| G4 | Gap | `skip_all()` returned `None` instead of `dict[str, Any]` | Now returns `{"summary": ..., "warning": "All agents were skipped..."}` |
| G5 | Gap | `get_subtree_summary()` didn't accept `None` for full-org case | Signature updated to `(self, agent_id: str \| None)`; `None` returns all agents |
| D1 | Deviation | `_MAX_RETRIES` was module-level constant | Changed to class attribute `_MAX_RETRIES: int = 3` in both `TeamSetupOrchestrator` and `AgentReconfiguration` |
| D2 | Deviation | `_build_agent_context_message` imported from `generator/` into `agents/` | Moved to `adjents/utils/agent_context.py`; both classes import from there |
| D3 | Deviation | `_call_extraction_llm` signature diverged | Both classes now take `conversations: list[str]` and join internally |

**Test count after corrections**: 244 tests passing (238 before + 6 new: V1×1, G3×1, G4×1, G5×2, V3×1).

---

## Verdict

**✅ Fully compliant (post-corrections 2026-05-29).**

Core functionality (session lifecycle, depth-first traversal, extraction/apply loop, DB
persistence, both modes, all required tests, all required files) is correctly implemented.
All 11 findings (3 violations, 5 gaps, 3 deviations) resolved. 244 tests passing,
`ruff` and `mypy --strict` clean.
