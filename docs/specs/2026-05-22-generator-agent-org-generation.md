# Feature: Generator Agent — Org Generation

> Spec date: 2026-05-22 | Status: Validated | Next: Implementation Plan

---

## Feature Brief

**Goal**: Given a persisted `BusinessContext`, produce a complete `AgentSpec` + `Skill` +
`AgentState` hierarchy tailored to the user's business and persist it to SQLite. This is
the second and final step of the Generator Agent: the interview produces the
`BusinessContext`; this feature produces the org that will run autonomously.

**Users**: Developer (smoke test), then the API/onboarding layer that calls
`GeneratorOrgGeneration.generate()` once `ready_to_generate=True` is returned by the
interview.

---

**Acceptance criteria**:

- `GeneratorOrgGeneration.generate(context: BusinessContext) -> OrgGenerationResult`
  calls `claude-opus-4-7` with `max_tokens=8192`, parses and structurally validates the
  response, and persists to SQLite in a single commit: all `AgentSpec`, `Skill`, and
  `AgentState` (status=`PAUSED`) records
- Structural validation checks all of the following; any failure triggers a retry with
  specific feedback to the LLM (max 3 attempts), then raises `OrgGenerationError`:
  - Exactly one agent with `level=0` and `parent_temp_id=null` (the COO)
  - Every agent with `level > 0` has a `parent_temp_id` that references another agent
    in the same response
  - No parent cycle (no agent whose parent chain eventually points back to itself)
  - No domain listed in `BusinessContext.domains_with_human_coverage` appears as the
    `domain` field of any N-1 agent
  - Every `visual_character` value is one of the predefined list (see Constraints)
- The LLM uses stable string slugs for agent references (e.g. `"coo"`,
  `"marketing_lead"`); the code generates UUIDs and resolves all
  `parent_temp_id` → UUID before persisting
- Skills are embedded inline in each agent in the LLM JSON; the code assigns UUIDs
  and builds `skill_ids` references
- `AgentState` records are created alongside `AgentSpec` in the same commit, with
  `status=PAUSED`, `current_task_summary=None`, `meeting_with=[]`
- `generate()` uses plain INSERT — no prior DELETE (ADR 0005, upsert-safe)
- A smoke test (`scripts/smoke_generator_org.py`) runs a real Anthropic API call using
  a rich, hand-crafted `BusinessContext` (see smoke test persona below) and prints the
  resulting org tree. The generated org must contain at least 10 N-1 agents, at least
  15 N-2 agents, and at least 40 skills total — validating that the prompt and
  generation handle complex, multi-domain businesses correctly
- `ruff`, `mypy --strict`, all tests pass

---

**LLM output JSON schema** (the exact shape `org_generation.md` must instruct the LLM
to return):

```json
{
  "agents": [
    {
      "temp_id": "coo",
      "name": "Jordan",
      "level": 0,
      "parent_temp_id": null,
      "domain": null,
      "role_description": "Chief of Staff — coordinates all N-1 leads...",
      "responsibilities": ["Coordinate N-1 leads daily", "Escalate blockers to the user"],
      "skills": [
        {
          "name": "Daily standup synthesis",
          "description": "Aggregates N-1 status reports into a daily summary",
          "inputs": ["N-1 status reports"],
          "outputs": ["Daily summary for the user"],
          "requires_human_review": false
        }
      ],
      "escalation_rules": ["Escalate to user if two N-1 leads conflict"],
      "scheduler_interval_seconds": 900,
      "work_hours": "09:00-18:00",
      "visual_character": "character_suit"
    },
    {
      "temp_id": "finance_lead",
      "name": "Alex",
      "level": 1,
      "parent_temp_id": "coo",
      "domain": "Finance",
      "role_description": "...",
      "responsibilities": ["..."],
      "skills": ["..."],
      "escalation_rules": ["..."],
      "scheduler_interval_seconds": 1800,
      "work_hours": "09:00-18:00",
      "visual_character": "character_suit"
    }
  ]
}
```

---

### `OrgGenerationResult` — return type of `generate()`

```python
@dataclass
class OrgGenerationResult:
    agents: list[AgentSpec]
    skills: list[Skill]
```

`OrgGenerationError`: raised after max retries if JSON is invalid or structural
validation fails.

---

### Smoke test persona — Sophie Dubois

A deliberately complex, multi-vertical solopreneur to stress-test the generation. The
`BusinessContext` is hand-crafted (not produced by a real interview) and passed directly
to `generate()`.

- **Business**: sells handmade jewellery (Shopify e-commerce, B2C), runs online
  crafting workshops and video courses (Teachable), has a YouTube channel and Instagram,
  runs B2B corporate team-building workshops
- **Tools**: Shopify, Teachable, Stripe, Mailchimp, Meta Ads, Google Ads, Notion,
  Canva, Later (social scheduling), Google Analytics, Zoom
- **Domains to staff** (~10): E-commerce, Marketing, Content, Education, B2B Sales,
  Finance, Operations, Customer Service, Tech, Social Media
- **Expected N-2 depth**: 2-3 specialists per domain
  (e.g. Marketing → SEO specialist, Paid Ads specialist, Email Marketing specialist)
- **Autonomy**: medium — agents act independently on routine tasks, escalate on
  anything involving money or client communication
- **Work hours**: `"09:00-22:00"` (evening work sessions)
- **Human coverage**: none — Sophie is fully solo

Expected org: 1 COO + ~10 N-1 + ~20 N-2 = ~31 agents, ~60-80 skills.

---

**Edge cases**:

- `domains_with_human_coverage` covers all domains → org = COO only (valid, no N-1
  generated)
- LLM generates an N-1 agent with unknown `parent_temp_id` → structural validation
  fails, LLM receives specific error message, retries
- LLM generates two COOs → caught, retried with feedback
- `BusinessContext.work_hours = None` → all agents generated with `work_hours=None`
  (always active)
- `generate()` called twice on the same `BusinessContext` → two independent INSERTs,
  no error (v0.1 expected behaviour)
- LLM returns invalid JSON → retry with `"Respond with valid JSON only."` (same pattern
  as `GeneratorInterview._call_llm()`)
- All retries exhausted → `OrgGenerationError` raised with last raw response excerpt

---

**Dependencies**:

- `backend/adjents/agents/models.py` — `AgentSpec`, `AgentState`, `AgentStatus`,
  `Skill` ✅
- `backend/adjents/generator/models.py` — `BusinessContext` ✅
- `backend/adjents/db/tables.py` — `AgentSpecTable`, `AgentStateTable`, `SkillTable` ✅
- `backend/adjents/db/convert.py` — `agent_spec_to_table`, `agent_state_to_table`,
  `skill_to_table` ✅
- `backend/adjents/db/engine.py` — `AsyncSession` ✅
- `backend/adjents/llm/anthropic_client.py` — `AnthropicClient` ✅
- `backend/adjents/router/router.py` — `LLMRouter.get_generator_client()` ✅
- `backend/adjents/prompts/loader.py` — `PromptLoader` ✅
- `backend/adjents/prompts/generator/org_generation.md` — stub exists, to implement ✅
- `anthropic>=0.103.1` — already in `pyproject.toml` ✅

**Files to create**:

- `backend/adjents/generator/org_generation.py`
- `backend/scripts/smoke_generator_org.py`

---

**Constraints**:

- Single LLM call — no per-domain generation (global coherence requirement)
- `max_tokens=8192` — covers complex orgs (up to ~30 agents × 5 skills)
- `scheduler_interval_seconds`: LLM chooses within 300–3600s, guided by
  `autonomy_preference` from `BusinessContext`; the prompt provides the valid range
- `visual_character` must be one of: `"character_suit"`, `"character_creative"`,
  `"character_tech"`, `"character_support"`, `"character_analyst"`, `"character_sales"`
  — full list injected into `org_generation.md`; final values will be aligned with
  PixiJS sprite design
- Plain INSERT, no DELETE (ADR 0005)
- `AgentState` created in `generate()` alongside `AgentSpec` — no orphan agents
  (ARCHITECTURE.md §3)
- No prompt strings in Python source — all content in
  `prompts/generator/org_generation.md`
- `mypy --strict` must pass; files ≤ 300 lines
- `prompts/agent/intro.md` out of scope — belongs to the post-generation validation
  feature (ADR 0006)

---

**Scope boundaries**:

| In scope | Out of scope |
| --- | --- |
| `generator/org_generation.py` — `GeneratorOrgGeneration`, `OrgGenerationResult`, `OrgGenerationError` | `prompts/agent/intro.md` (post-gen validation feature) |
| `prompts/generator/org_generation.md` — full prompt with JSON schema + predefined sprite list | Full LLM router (Ollama, complexity/sensitivity rules, semaphores) |
| Structural validation + retry with LLM feedback | Post-generation validation conversations |
| Persist `AgentSpec`, `Skill`, `AgentState` (status=`PAUSED`) | Frontend / API layer |
| `OrgGenerationError` exception | |
| `scripts/smoke_generator_org.py` smoke test | |
