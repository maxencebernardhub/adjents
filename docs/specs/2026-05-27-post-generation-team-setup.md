# Feature: Post-Generation Team Setup

> Spec date: 2026-05-27 | Updated: 2026-05-28 | Status: Validated | Next: Implementation Plan

---

## Feature Brief

**Goal**: Two related modes sharing the same core building blocks (conversation,
extraction, DB update):

1. **Post-generation team setup** — after `GeneratorOrgGeneration.generate()`
   completes, guide the user through individual conversations with the COO then
   each N-1 agent (in free order) before the org goes live. Each agent presents
   itself and its full subtree; the user discusses, adjusts, and validates. All
   agents are unpaused atomically on completion or explicit skip. Resumable across
   sessions.

2. **Direct agent reconfiguration** — at any point after go-live, the user can open
   a conversation with any agent to review and adjust its own configuration. Same
   conversation + extraction mechanics, no session tracking.

**Users**: Developer (smoke test), then the API/onboarding layer that calls
`TeamSetupOrchestrator` after generation completes, and any future interface that
surfaces agent reconfiguration.

---

## Acceptance criteria

### Mode 1 — Post-generation team setup

- `TeamSetupOrchestrator.start_session()` creates one `ValidationSession` + one
  `AgentValidationRecord` per COO and N-1 agent, all with `status="pending"`. Raises
  `TeamSetupError` if a session already exists.
- `TeamSetupOrchestrator.resume_session()` loads the existing incomplete
  `ValidationSession` if any; returns `None` if no session exists or the last
  session is already completed.
- The COO record must be `validated` or `skipped` before any N-1 conversation can
  start; `start_agent_conversation()` raises `TeamSetupError` if this ordering
  constraint is violated.
- `start_agent_conversation(session_id, root_agent_id) -> str` starts (or resumes)
  a conversation with a COO or N-1 root agent. Makes a real LLM call and returns
  the agent's opening message. If the record was already `in_progress`, the
  conversation history is restored from `active_conversation_id` and the agent
  produces a "conversation resumed" continuation message.
- **COO specificity**: the COO presents only its own configuration (role,
  responsibilities, skills, work hours, scheduler interval, visual character,
  escalation rules). It does **not** introduce the N-1 agents as its team — each
  N-1 has its own `AgentValidationRecord` and will be met separately. COO record:
  `navigation_stack = [coo_id]`, `visited_agent_ids = []`.
- For N-1 root agents, the orchestrator traverses the subtree depth-first: after
  the root agent's intro, the first unvisited direct report takes over; after each
  sub-agent is done, control returns to its parent; when all descendants are
  visited, the root agent delivers a final team summary.
- `reply(session_id, root_agent_id, message) -> str` appends the user message to
  `active_conversation_id` and returns the active agent's response. `reply()` always
  routes to the **currently active agent** (`active_agent_id`), which may be a N-2
  or N-3 — not necessarily the root agent.
- `complete_current_agent(session_id, root_agent_id) -> str` closes the
  active sub-agent's conversation, advances the traversal (via the depth-first
  algorithm described below), **makes a new LLM call**, and returns either:
  - the next sub-agent's opening message (if unvisited sub-agents remain), or
  - the root agent's final team summary (if the entire subtree has been visited).
  Never returns `None`. The caller detects "subtree complete" by checking
  `AgentValidationRecord.navigation_stack == []` after the call.
  `AgentState.status` of the closing agent reverts to `PAUSED`; the next agent
  (or the root agent for the final summary) moves to `IN_MEETING_1ON1`.
- The traversal state is fully persisted in `AgentValidationRecord` — an
  interruption at any depth (including mid-N-3 or deeper) resumes exactly where it
  stopped on the next `start_agent_conversation()` call.
- `validate_team(session_id, root_agent_id)` triggers: (a) extraction LLM call on
  all transcripts in `conversation_ids` at that point in time (regardless of whether
  all sub-agents were visited), (b) atomic DB update of all modified `AgentSpec`
  and `Skill` records, (c) `AgentValidationRecord.status = "validated"`,
  (d) `AgentState.status` of the root agent and all visited agents reverts to
  `PAUSED`.
- `skip_agent(session_id, root_agent_id)` returns a subtree summary
  (`get_subtree_summary(root_agent_id)`) and a warning, then marks the record
  `"skipped"` without extraction.
- `skip_all(session_id)` returns a full org summary (`get_subtree_summary(None)`)
  and a warning, marks all remaining records `"skipped"`, and triggers go-live.
- `get_subtree_summary(agent_id: str | None) -> dict` returns a structured dict of
  the agent + its full descendant tree with `AgentSpec` and `Skill` data.
  `agent_id=None` returns the full org.
- `_go_live(session_id)` sets all `AgentSpec.is_paused = False` **and** all
  `AgentState.status = IDLE` in a single DB commit, then sets
  `ValidationSession.completed_at`. Triggered when all `AgentValidationRecord`
  entries for the session are `validated` or `skipped`.
- `ruff`, `mypy --strict`, all tests pass.

### Mode 2 — Direct agent reconfiguration

- `AgentReconfiguration(client, prompt_loader, session)` instantiated with an
  `agent_id`.
- `start() -> str` loads the agent's `AgentSpec` + direct reports from DB,
  sets `AgentState.status = IN_MEETING_1ON1`, and returns the agent's opening
  message (same intro prompt as Mode 1).
- `reply(message) -> str` continues the conversation; returns the agent's response.
- `apply_changes()` triggers the extraction LLM call on the conversation transcript,
  applies all modifications to the DB, and resets `AgentState.status` to its
  previous value (no agent pause in v0.1 — the agent loop is not yet active).
- No `ValidationSession` or `AgentValidationRecord` created; no go-live logic; no
  session resumption.
- **v0.2 note**: once the agent loop is active, `apply_changes()` should briefly set
  `AgentSpec.is_paused = True` around the DB commit to avoid the loop reading a
  partially-updated spec.

### Shared — extraction and apply

- Both modes use `prompts/agent/intro.md` (system prompt) and
  `prompts/agent/extract_agent_adjustments.md` (extraction prompt).
- Agent data (AgentSpec + subtree + explicit UUIDs) is injected as the **first user
  message** — not in the system prompt — to avoid `str.format_map()` breakage on
  user-supplied curly braces (same decision as `org_generation.py`). Every injected
  agent block must include its `agent_id` (UUID) so the extraction LLM can reference
  it correctly.
- `prompt.content` used (not `prompt.render()`) for both new prompts.
- Frozen fields (`domain`, `level`, `parent_id`) are silently dropped if returned
  by extraction; a warning is logged.
- `visual_character` not in `VALID_VISUAL_CHARACTERS`: dropped, warning logged.
- `scheduler_interval_seconds` outside [300, 3600]: clamped to nearest bound,
  warning logged.
- Extraction invalid JSON or schema error: retry up to `_MAX_RETRIES = 3` with
  corrective feedback; after all retries, raise `TeamSetupError`.
- All DB updates applied in a single commit per `validate_team()` /
  `apply_changes()` call.

---

## AgentState.status transitions

| Event | Status change |
| --- | --- |
| `start_agent_conversation()` or `complete_current_agent()` opens a conversation | Active agent: `PAUSED → IN_MEETING_1ON1` |
| `complete_current_agent()` closes current, opens next sub-agent | Closing agent: `IN_MEETING_1ON1 → PAUSED`; next sub-agent: `PAUSED → IN_MEETING_1ON1` |
| `complete_current_agent()` closes last sub-agent (subtree complete) | Closing agent: `IN_MEETING_1ON1 → PAUSED`; root agent: `PAUSED → IN_MEETING_1ON1` (delivers final summary) |
| `validate_team()` or `skip_agent()` completes a root agent | All involved agents: `IN_MEETING_1ON1 → PAUSED` |
| `_go_live()` | All agents: `PAUSED → IDLE`; `AgentSpec.is_paused = False` |
| `AgentReconfiguration.start()` | Target agent: current status → `IN_MEETING_1ON1` |
| `AgentReconfiguration.apply_changes()` | Target agent: `IN_MEETING_1ON1 → prior status` |

---

## Modifiable fields

| Field | Modifiable | Notes |
| --- | :---: | --- |
| `name` | ✅ | |
| `role_description` | ✅ | v0.2: recommended via parent for non-COO agents |
| `responsibilities` | ✅ | v0.2: recommended via parent for non-COO agents |
| `work_hours` | ✅ | v0.2: recommended via parent for non-COO agents |
| `scheduler_interval_seconds` | ✅ | Clamped to [300, 3600] |
| `escalation_rules` | ✅ | |
| `visual_character` | ✅ | Must be in `VALID_VISUAL_CHARACTERS`; invalid values dropped |
| Skill: name, description, inputs, outputs, `requires_human_review` | ✅ | |
| Add a skill | ✅ | New UUID assigned; added to `AgentSpec.skill_ids` |
| Remove a skill | ✅ | Deleted from `SkillTable`; removed from `AgentSpec.skill_ids` |
| `domain` | ❌ | Structural identity — restructuring = v0.2 |
| `level` | ❌ | Hierarchy position — restructuring = v0.2 |
| `parent_id` | ❌ | Hierarchical link — restructuring = v0.2 |

---

## New domain models

```python
class AgentValidationStatus(StrEnum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATED   = "validated"
    SKIPPED     = "skipped"

class ValidationSession(BaseModel):
    id: str
    started_at: datetime
    completed_at: datetime | None   # None = in progress
    skipped: bool

class AgentValidationRecord(BaseModel):
    id: str
    session_id: str
    root_agent_id: str              # COO (level=0) or N-1 agent ID
    status: AgentValidationStatus
    active_agent_id: str | None     # currently active agent in subtree traversal
    active_conversation_id: str | None
    navigation_stack: list[str]     # path from root to active agent; enables resume
    conversation_ids: list[str]     # all conversations produced during this validation
    visited_agent_ids: list[str]    # agents whose conversation is finished
    validated_at: datetime | None
```

### Depth-first traversal algorithm

```python
def _get_next_agent(current_id, stack, visited, db):
    children = db.get_direct_reports(current_id)
    unvisited = [c for c in children if c.id not in visited]

    if unvisited:
        # Unvisited children remain — descend to the first one
        next_agent = unvisited[0]
        stack.append(next_agent.id)
        return next_agent
    else:
        # All children visited (or leaf node) — pop stack, return to parent
        visited.append(current_id)
        stack.pop()
        if stack:
            parent_id = stack[-1]
            return db.get_agent(parent_id)
        else:
            return None  # Entire subtree visited — see note below
```

This algorithm is depth-agnostic: it handles N-2, N-3, N-4, and beyond without
modification. `navigation_stack` and `visited_agent_ids` are persisted to
`AgentValidationRecord` after every call, enabling exact-position resume on restart.

**When `_get_next_agent` returns `None`** (stack empty after the final pop),
`complete_current_agent()` does **not** forward `None` to the caller. Instead, it
makes one final LLM call on the **root agent** to generate its team summary, sets
`active_agent_id = root_agent_id`, and returns that string. The caller detects
subtree completion by checking `record.navigation_stack == []` after the call.

---

## Extraction output JSON schema

Output of `prompts/agent/extract_agent_adjustments.md`:

```json
{
  "agent_updates": [
    {
      "agent_id": "<uuid>",
      "fields": {
        "name": "Lucas",
        "role_description": "...",
        "work_hours": "09:00-20:00",
        "scheduler_interval_seconds": 600,
        "visual_character": "character_creative",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "escalation_rules": ["Rule 1"]
      },
      "skills_to_add": [
        {
          "name": "Monthly newsletter",
          "description": "Drafts and sends the monthly newsletter",
          "inputs": ["subscriber list", "content brief"],
          "outputs": ["drafted newsletter"],
          "requires_human_review": true
        }
      ],
      "skills_to_remove": ["PDF invoice generation"],
      "skills_to_update": [
        {
          "name": "Existing skill name",
          "fields": {
            "description": "updated description",
            "inputs": ["updated input"],
            "outputs": ["updated output"],
            "requires_human_review": false
          }
        }
      ]
    }
  ]
}
```

All `fields` keys are optional — only modified fields are included. `skills_to_add`,
`skills_to_remove`, and `skills_to_update` may be empty lists. The extraction LLM
must produce a valid JSON object even when no changes were requested:
`{ "agent_updates": [] }`.

---

## Edge cases

| Case | Behaviour |
| --- | --- |
| Org has only COO (no N-1s) | Session completes after COO validation; go-live triggered immediately |
| Leaf agent (no direct reports) | No subtree traversal; agent presents only itself |
| Interrupted mid-N-3 | `navigation_stack = [root, N-2, N-3]`; `active_conversation_id` → N-3 conversation; resume restores exact state |
| `validate_team()` before all sub-agents visited | Allowed — extraction runs on `conversation_ids` that exist at that point |
| All agents skipped individually | Equivalent to global skip; go-live triggered |
| Extraction returns no changes | Empty `agent_updates`; record marked `validated`, no DB writes |
| Extraction returns frozen field (`domain`, `level`, `parent_id`) | Field silently dropped; rest applied |
| Extraction returns invalid `visual_character` | Field dropped; warning logged |
| Skill name not found (remove/update) | Warning logged; skip gracefully |
| All extraction retries exhausted | `TeamSetupError` raised with last raw response excerpt |
| User requests frozen field change in conversation | Agent politely declines; explains restructuring is a v0.2 capability |
| `start_session()` called when session already exists | `TeamSetupError` raised |
| Mode 2 on leaf agent | Agent presents only itself; no subtree context injected |
| `work_hours = None` | Valid value ("always active"); extraction may set it back to `None` |
| Mode 2 `apply_changes()` in v0.1 | Agent NOT paused during apply; v0.2 will add brief pause around the commit |

---

## Dependencies

**Existing (all ✅):**

- `agents/models.py` — `AgentSpec`, `AgentState`, `AgentStatus`, `Skill`
- `generator/models.py` — `BusinessContext`
- `generator/org_generation.py` — `VALID_VISUAL_CHARACTERS`
- `db/tables.py` — `AgentSpecTable`, `AgentStateTable`, `SkillTable`,
  `ConversationTable`, `MessageTable`
- `db/convert.py` — all existing conversion functions
- `db/engine.py` — `AsyncSession`
- `llm/anthropic_client.py` — `AnthropicClient`
- `router/router.py` — `LLMRouter.get_generator_client()`
- `prompts/loader.py` — `PromptLoader`
- `messaging/models.py` — `Conversation`, `Message`

---

## Files to create

| File | Description |
| --- | --- |
| `backend/adjents/generator/team_setup.py` | `ValidationSession`, `AgentValidationRecord`, `AgentValidationStatus`, `TeamSetupError`, `TeamSetupOrchestrator` (Mode 1) |
| `backend/adjents/agents/reconfiguration.py` | `AgentReconfiguration` (Mode 2) |
| `backend/adjents/prompts/agent/intro.md` | Agent intro + discussion system prompt (both modes) |
| `backend/adjents/prompts/agent/extract_agent_adjustments.md` | Extraction prompt; outputs the schema above |
| `backend/scripts/smoke_team_setup.py` | Smoke test: mock LLM for automated tests; real API for manual end-to-end |
| `docs/decisions/0008-team-setup-natural-conversation-extraction.md` | ADR: natural language conversations + LLM extraction at validation time |
| `docs/decisions/0009-direct-agent-reconfiguration-v01.md` | ADR: direct reconfiguration in v0.1; via-parent mediated changes in v0.2 |

## Files to modify

| File | Change |
| --- | --- |
| `backend/adjents/db/tables.py` | Add `ValidationSessionTable`, `AgentValidationRecordTable` |
| `backend/adjents/db/convert.py` | Add `validation_session_to/from_table`, `agent_validation_record_to/from_table` |
| `docs/ARCHITECTURE.md` | §3: add `ValidationSession` + `AgentValidationRecord` models + serialization table rows; §5: update lifecycle diagram with `IN_MEETING_1ON1` transitions; §9: add `agent/intro` and `agent/extract_agent_adjustments` to prompt loading table |
| `docs/VISION.md` | §4.1: add direct agent reconfiguration to v0.1 scope; §4.2: rephrase micro-adjustments item |
| `docs/decisions/0005-org-restructuring.md` | Add note: direct reconfiguration (all fields) in v0.1; via-parent mediated changes in v0.2 |
| `docs/decisions/0006-post-generation-validation.md` | Update with full design — supersedes initial sketch |
| `PROJECT_STATE.md` | Add session entry; update milestone table; update decisions log |
| `README.md` | §"What v0.1 includes": add direct agent reconfiguration |
| `backend/README.md` | Scripts section: add `smoke_team_setup.py` entry |

---

## Constraints

- **LLM**: `claude-sonnet-4-6` via `AnthropicClient` for all conversations and
  extraction calls. To revisit after LLM Router + LLM Clients features are built.
  Prompt frontmatter: `model_hint: "claude-sonnet-4-6"`.
- **Prompt injection**: agent data (AgentSpec + subtree + explicit UUIDs) injected
  as the first user message to avoid `str.format_map()` breakage on user-supplied
  curly braces. Same decision as `org_generation.py`.
- **`prompt.content`** used (not `prompt.render()`) for both new prompts.
- **Plain UPDATE** for `AgentSpec` and `Skill` modifications — no DELETE + re-INSERT
  (consistent with ADR 0005 insert-only restructuring constraint).
- **Skills**: ADD = INSERT new `SkillTable` row + update `AgentSpec.skill_ids`;
  UPDATE = modify existing `SkillTable` row; REMOVE = DELETE from `SkillTable` +
  remove from `AgentSpec.skill_ids`.
- No FastAPI endpoints in this feature; API layer is a separate future feature.
- No Chroma memory layer in this feature.
- `mypy --strict` must pass. Individual files ≤ 300 lines (soft limit).

---

## Smoke test validation criteria

Using a pre-generated org (Sophie Dubois persona from `smoke_generator_org.py`, or
equivalent with at least 1 COO + 3 N-1 agents, at least 1 N-1 with N-2 sub-agents):

**Mode 1 — scripted user, mock LLM:**

- `start_session()` creates correct records (1 per COO + N-1)
- COO conversation → scripted: rename, add 1 skill
- 1 N-1 full subtree (1 N-2 minimum) → scripted: rename N-2, update 1 skill
- Interruption simulation: reload orchestrator mid-subtree → verify resume from
  correct `active_agent_id` / `active_conversation_id`
- `skip_all()` for remaining N-1s
- `_go_live()`: assert all `AgentSpec.is_paused = False` + all
  `AgentState.status = IDLE`
- DB assertions: modified names + new/updated skills persisted; frozen fields
  (`domain`, `level`) unchanged

**Mode 2 — scripted user, mock LLM:**

- `AgentReconfiguration.start()` for 1 agent → `AgentState.status = IN_MEETING_1ON1`
- `reply()` with a modification request
- `apply_changes()` → DB update verified; `AgentState.status` restored

**Real-API end-to-end** (run manually with `! uv run scripts/smoke_team_setup.py`):

- Same flow as Mode 1 above with a real Anthropic API
- Verifies the intro prompt generates a coherent, relevant presentation
- Verifies the extraction prompt correctly identifies modifications

---

## v0.2 — "Via parent agent" reconfiguration spec

> *(For ADR 0005 update)*

For `work_hours`, `responsibilities`, and `role_description` of non-COO agents,
v0.2 introduces a parent-mediated path alongside direct reconfiguration:

- **Trigger**: user wants to change structural parameters of a non-COO agent
- **Flow**: user opens a conversation with the agent's direct parent → parent
  discusses with full team context (workload, domain overlaps, sibling scopes) →
  extraction may update the target agent and potentially siblings → apply
- **COO exception**: COO (level=0) has no parent → these fields remain directly
  modifiable by the user
- **v0.2 enforcement**: UI/API recommends the parent path for structural fields but
  does not block direct modification for power users

---

## Scope boundaries

| In scope | Out of scope |
| --- | --- |
| Mode 1: COO + N-1 validation, depth-first traversal, resume at any depth, go-live | FastAPI endpoints for the validation flow |
| Mode 2: direct reconfiguration of any agent, any time | Chroma memory layer integration |
| Extraction + apply all modifiable fields including full skill CRUD | "Via parent" mediated reconfiguration (v0.2) |
| Skip with subtree/org summary + warning | Org restructuring (add/remove/move agents) |
| `ValidationSession` + `AgentValidationRecord` persistence + `AgentState` transitions | Agent loop integration |
| `prompts/agent/intro.md` + `prompts/agent/extract_agent_adjustments.md` | Frontend UI for the validation flow |
| Updates to `VISION.md`, `ARCHITECTURE.md`, ADR 0005, ADR 0006 | |
| New ADRs 0008 and 0009 | |
