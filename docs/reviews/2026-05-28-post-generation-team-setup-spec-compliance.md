# Spec Compliance Review — Post-generation team setup

**Date**: 2026-05-28
**Branch**: `feat/post-generation-team-setup`
**Reviewer**: spec-reviewer subagent
**Verdict**: ⚠️ Partially compliant

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
| `active_agent_id = root_agent_id` when delivering final summary | ❌ | `team_setup.py:451` sets `None` instead of `root_agent_id` — see V1 |
| Traversal state persisted after every call | ✅ | `_save_record` called after each step |
| `validate_team()`: extraction LLM, atomic DB update, `status="validated"`, state reverts to `PAUSED`, fires `_go_live` if all done | ✅ | `team_setup.py:462-477` |
| `skip_agent()` returns subtree summary + warning, marks `skipped` | ⚠️ | Returns `str`, not `dict`. No "warning" included — see G3 |
| `skip_all()` returns full org summary + warning dict, marks all `skipped`, triggers go-live | ⚠️ | Returns `None` instead of `dict` — see G4 |
| `get_subtree_summary(Optional[str])` handles `None` for full-org case | ⚠️ | Accepts `str` only; `None` not handled — see G5 |
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
| Frozen fields: warning logged | ❌ | No `_log.warning()` for frozen field drops — see G1 |
| `visual_character` not in valid list: dropped, warning logged | ✅ | Both files |
| `scheduler_interval_seconds` outside [300,3600]: clamped, warning logged | ✅ | Both files |
| Extraction invalid JSON: retry up to `_MAX_RETRIES=3` | ✅ | Both files |
| Extraction exhausted retries: raise `TeamSetupError` | ⚠️ | `TeamSetupOrchestrator` ✅; `AgentReconfiguration` raises `ValueError` — see V3 |
| Skill name not found: warning logged, skip gracefully | ⚠️ | Skips gracefully but no `_log.warning()` — see G2 |

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
| Extraction returns frozen field: dropped | ✅ | No warning however — see G1 |
| Extraction returns invalid `visual_character`: dropped, warning logged | ✅ | `_log.warning` present |
| Skill name not found: warning, skip | ⚠️ | Skips; no warning — see G2 |
| All extraction retries exhausted: `TeamSetupError` raised | ✅ | `team_setup.py:699-701` |
| `start_session()` when session exists: `TeamSetupError` | ✅ | `team_setup.py:213-215` |
| Mode 2 on leaf agent: no subtree context | ✅ | `_load_direct_reports` returns empty list |

---

## Implementation Plan — Tasks

| Task / File | Status | Notes |
| --- | :---: | --- |
| T1 — `tables.py`: `ValidationSessionTable`, `AgentValidationRecordTable` | ✅ | `tables.py:143-164` |
| T1 — `convert.py`: 4 convert functions | ✅ | `convert.py:344-404` |
| T1 — `team_setup.py` models: enums, Pydantic models, `TeamSetupError` | ✅ | `team_setup.py:33-60` |
| T1 — `test_team_setup_models.py`: 9 tests | ✅ | All 9 present |
| T2 — `_advance_traversal` pure function | ✅ | `team_setup.py:68-98` |
| T2 — `_build_agent_context_message` | ✅ | `team_setup.py:101-181` |
| T2 — `test_team_setup.py`: 9 traversal + 3 context tests | ✅ | All 12 present + 1 bonus |
| T3 — `prompts/agent/intro.md` | ⚠️ | File correct. Prompt instructs agents to introduce direct reports — contradicts original Feature Brief COO rule but aligns with ADR 0006 update. Feature Brief needs updating — see V2 |
| T3 — `prompts/agent/extract_agent_adjustments.md` | ✅ | Matches spec |
| T4 — `TeamSetupOrchestrator` full implementation | ✅ | All methods present |
| T4 — `test_team_setup_orchestrator.py`: all specified tests | ✅ | All ~37 tests present |
| T4 — `conftest.py`: `mini_org` and `coo_only_org` fixtures | ✅ | Both present |
| T4 — `_MAX_RETRIES` as class constant | ⚠️ | Implemented as module-level constant — see D1 |
| T5 — `agents/reconfiguration.py`: `AgentReconfiguration` | ✅ | All methods present |
| T5 — `test_agent_reconfiguration.py`: 7 tests | ✅ | All 7 present |
| T5 — `_apply_agent_updates` and `_call_extraction_llm` duplicated | ⚠️ | `_apply_agent_updates` duplicated ✅; `_build_agent_context_message` shared via import — see D2 |
| T6 — `scripts/smoke_team_setup.py` | ✅ | Mock + real modes, all scenarios |
| T7 — ADR 0008 created | ✅ | `docs/decisions/0008-...` |
| T7 — ADR 0009 created | ✅ | `docs/decisions/0009-...` |
| T7 — `ARCHITECTURE.md`, `VISION.md`, ADR 0005, ADR 0006 updated | ✅ | All modified |
| T7 — `PROJECT_STATE.md`, `README.md`, `backend/README.md` updated | ✅ | All modified |

---

## ADR compliance

| Decision | ADR | Status | Notes |
| --- | --- | :---: | --- |
| Frozen fields (`domain`, `level`, `parent_id`) silently dropped | 0005, 0008 | ✅ | Both `_apply_agent_updates` copies |
| Plain UPDATE for AgentSpec/Skill — no DELETE+re-INSERT | 0005 | ✅ | `setattr` on existing row |
| `AgentReconfiguration` allows all non-structural fields in v0.1 | 0009 | ✅ | All modifiable fields handled |
| No FastAPI endpoint in this feature | 0009 | ✅ | Confirmed absent |
| Single extraction LLM call at validation time (Option B) | 0008 | ✅ | Called in `validate_team` and `apply_changes` |
| `_apply_agent_updates` duplicated — no cross-direction import | 0008 | ⚠️ | `_apply_agent_updates` duplicated ✅; `_build_agent_context_message` imported from `generator/` — see D2 |
| `AnthropicClient` constructed with `claude-sonnet-4-6`, NOT via `LLMRouter` | 0008 | ✅ | Smoke test and orchestrator confirm |
| Retry up to `_MAX_RETRIES=3`, raise `TeamSetupError` on exhaustion | 0008 | ⚠️ | `AgentReconfiguration` raises `ValueError` instead — see V3 |
| `visual_character` validated; `scheduler_interval_seconds` clamped | 0008 | ✅ | Both enforced |
| `AgentState.status = IN_MEETING_1ON1` on start, restored after | 0009 | ✅ | Both modes |

---

## Gaps, violations, deviations

### Violations (must fix)

- **[V1 — VIOLATION]** `active_agent_id` after subtree exhaustion: `team_setup.py:451` sets
  `record.active_agent_id = None`. Spec (Feature Brief + Implementation Plan §complete_current_agent
  Option B) explicitly says `record.active_agent_id = root_agent_id` when the final summary LLM
  call is made. Caller cannot determine the speaking agent from the record alone after this call.

- **[V2 — VIOLATION / Feature Brief outdated]** `intro.md` instructs agents to present their
  direct reports in the opening message. Original Feature Brief says "COO presents only its own
  configuration — it does not introduce the N-1 agents as its team." However, ADR 0006 (updated
  2026-05-28) states "Agent data + direct reports injected as first user message" and the real-mode
  smoke test confirmed this behavior is correct and desirable. **Resolution: update the Feature
  Brief to reflect the ADR 0006 update — do NOT revert `intro.md`.**

- **[V3 — VIOLATION]** `AgentReconfiguration._call_extraction_llm` raises `ValueError` on retry
  exhaustion (`reconfiguration.py:135`) instead of `TeamSetupError` as specified in ADR 0008 and
  Feature Brief.

### Gaps (should fix)

- **[G1 — GAP]** Frozen field drops produce no warning log. Spec states "a warning is logged."
  Code uses silent `continue` with no `_log.warning()` in both `_apply_agent_updates`
  copies (`team_setup.py:586-587`, `reconfiguration.py:153-154`).

- **[G2 — GAP]** Skill name not found (remove/update) produces no warning log. Spec specifies
  "Warning logged; skip gracefully." Code skips gracefully but no `_log.warning()` in either file.

- **[G3 — GAP]** `skip_agent()` return type: spec defines `-> dict[str, Any]` with subtree
  summary + warning dict. Code returns `str`. Warning content absent.

- **[G4 — GAP]** `skip_all()` return type: spec defines `-> dict[str, Any]` with full org
  summary + warning dict. Code returns `None`.

- **[G5 — GAP]** `get_subtree_summary(Optional[str])`: spec says `agent_id=None` returns
  the full org summary. Implemented signature is `(self, root_agent_id: str)` — `None` not accepted.

### Deviations (noted, not blocking)

- **[D1 — DEVIATION]** `_MAX_RETRIES` is a module-level constant (`_MAX_RETRIES = 3`) in both
  files rather than a class attribute (`_MAX_RETRIES: int = 3` on the class). Spec explicitly
  calls it a class attribute. No behavioral impact.

- **[D2 — DEVIATION]** `reconfiguration.py:19` imports `_build_agent_context_message` from
  `generator/team_setup`. ADR 0008 justifies duplication of helpers to avoid cross-direction
  imports between `generator/` and `agents/`. This creates exactly the dependency the ADR
  intended to avoid. Clean fix: move `_build_agent_context_message` to `adjents/utils/` —
  noted as technical debt for v0.2.

- **[D3 — DEVIATION]** `_call_extraction_llm` signatures diverge: `TeamSetupOrchestrator`
  takes `transcript: str`; `AgentReconfiguration` takes `conversations: list[str]`. Spec plan
  defines both as `list[str]`. No behavioral impact but reduces internal consistency.

---

## Verdict

**⚠️ Partially compliant.**

Core functionality (session lifecycle, depth-first traversal, extraction/apply loop, DB
persistence, both modes, all required tests, all required files) is correctly implemented.

- 3 violations: V1 (active_agent_id = None vs root_agent_id), V2 (Feature Brief text outdated
  vs ADR 0006, resolved by updating the Brief), V3 (ValueError vs TeamSetupError)
- 5 gaps: missing warning logs (G1, G2), skip return types (G3, G4, G5)
- 3 deviations: all non-blocking (D1, D2, D3)
