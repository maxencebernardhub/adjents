# Implementation Plan — Generator Agent Org Generation

> Spec: `docs/specs/2026-05-22-generator-agent-org-generation.md`
> Date: 2026-05-25 | Branch: `feat/generator-org-generation`

## Context

The Generator Agent interview feature (merged) produces a `BusinessContext` persisted
in SQLite. This feature is the second and final step: given that `BusinessContext`, make
a single LLM call to produce a complete org hierarchy (`AgentSpec` + `Skill` +
`AgentState`) and persist everything to SQLite.

All shared infrastructure is already in place: `AnthropicClient`, `LLMRouter`,
`PromptLoader`, `AgentSpec`/`AgentState`/`Skill` models, their SQLModel tables, and
their convert functions. Nothing new needs to be added to the DB or models layers.

---

## Scope

**In scope**: `_validate_structure` (pure function), `RawAgentData` (intermediate
dataclass), `OrgGenerationResult`, `OrgGenerationError`, `GeneratorOrgGeneration`
class with full LLM + retry + persist logic, `prompts/generator/org_generation.md`,
and the Sophie Dubois smoke test.

**Out of scope**: Ollama/OpenAI/Google routing, full routing rules (semaphores,
sensitivity), `prompts/agent/intro.md` (post-gen validation feature), frontend/API
layer.

---

## Tasks (ordered)

### T1 — Types + structural validation (pure functions)

**Files**:

- CREATE `backend/adjents/generator/org_generation.py` (partial: types + validation)
- CREATE `backend/tests/test_generator_org_generation.py` (validation tests only)

**What goes in `org_generation.py` at this stage**:

```python
VALID_VISUAL_CHARACTERS: frozenset[str] = frozenset({
    "character_suit",
    "character_creative",
    "character_tech",
    "character_support",
    "character_analyst",
    "character_sales",
})

@dataclass
class RawAgentData:
    """Intermediate dataclass parsed from the LLM JSON before UUID resolution."""
    temp_id: str
    name: str
    level: int
    parent_temp_id: str | None
    domain: str | None
    role_description: str
    responsibilities: list[str]
    skills: list[dict[str, Any]]  # inline skill dicts from LLM
    escalation_rules: list[str]
    scheduler_interval_seconds: int
    work_hours: str | None
    visual_character: str

@dataclass
class OrgGenerationResult:
    agents: list[AgentSpec]
    skills: list[Skill]

class OrgGenerationError(Exception): ...

def _validate_structure(
    raw_agents: list[RawAgentData],
    domains_with_human_coverage: list[str],
) -> str | None:
    """Return None if the org is structurally valid, or an error message."""
```

**Validation rules (in order)**:

1. Exactly one agent with `level=0` (the COO).
2. The COO (`level=0`) must have `parent_temp_id=None`. No other agent may have
   `parent_temp_id=None`. (Catches the LLM generating a non-COO with no parent, or
   a `level=0` agent that still references a parent.)
3. All `temp_id` values are unique.
4. Every agent with `level > 0` has a `parent_temp_id` that exists in the list.
5. No parent cycle (depth-first walk from every node; detect revisiting a node).
6. No N-1 agent has a `domain` that appears in `domains_with_human_coverage`
   (case-insensitive).
7. Every `visual_character` is in `VALID_VISUAL_CHARACTERS`.
8. Every `scheduler_interval_seconds` is in the range `[300, 3600]` (inclusive).
   This matches the constraint stated in the Feature Brief and the prompt guidance.

Returns `None` if all pass; returns a descriptive error string on first failure.

**Tests** (all pure, no DB, no LLM):

- `test_valid_org_returns_none` — COO + 2 N-1 + 1 N-2, all valid
- `test_coo_only_org_returns_none` — COO alone (all domains covered by humans)
- `test_no_coo_returns_error` — no agent with level=0
- `test_two_coos_returns_error` — two agents with level=0
- `test_level_0_with_parent_returns_error` — agent with level=0 but non-null
  `parent_temp_id`
- `test_non_coo_without_parent_returns_error` — agent with level=1 and
  `parent_temp_id=None`
- `test_unknown_parent_returns_error` — agent references non-existent `parent_temp_id`
- `test_duplicate_temp_id_returns_error` — two agents with the same `temp_id`
- `test_cycle_returns_error` — A is parent of B, B is parent of A
- `test_human_domain_n1_returns_error` — N-1 agent with domain in human coverage
- `test_human_domain_case_insensitive` — "finance" matches "Finance"
- `test_invalid_visual_character_returns_error`
- `test_valid_visual_characters_pass`
- `test_scheduler_interval_too_low_returns_error` — `scheduler_interval_seconds=299`
- `test_scheduler_interval_too_high_returns_error` — `scheduler_interval_seconds=3601`
- `test_scheduler_interval_valid_bounds` — 300 and 3600 both pass

---

### T2 — `prompts/generator/org_generation.md`

**File**:

- MODIFY `backend/adjents/prompts/generator/org_generation.md`

No pytest tests for the prompt file itself. Correctness is validated by the smoke test.

**Full prompt content** (implement verbatim in `org_generation.md`):

````markdown
---
version: 1
description: "Generator Agent org structure generation"
model_hint: "claude-opus-4-7"
---

# Generator Agent — Org Structure Generation

You are the Generator Agent for Adjents, an AI platform that builds a customized
team of autonomous AI agents for solopreneurs. The user message contains the full
business context collected during the onboarding interview. Your task is to design
and return the complete AI agent organization for this specific business.

## Output format (mandatory)

Return a single valid JSON object — nothing else. No markdown, no preamble, no
trailing text. The JSON must match exactly this schema:

```json
{
  "agents": [
    {
      "temp_id": "coo",
      "name": "Jordan",
      "level": 0,
      "parent_temp_id": null,
      "domain": null,
      "role_description": "Chief of Staff — coordinates all N-1 leads and is the
        user's primary point of contact for daily operations.",
      "responsibilities": [
        "Coordinate N-1 leads daily",
        "Escalate blockers to the user"
      ],
      "skills": [
        {
          "name": "Daily standup synthesis",
          "description": "Aggregates N-1 status reports into a concise daily summary.",
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
      "role_description": "Finance Lead — owns invoicing, expense tracking, and
        financial reporting.",
      "responsibilities": ["Manage invoicing", "Track expenses"],
      "skills": [
        {
          "name": "Invoice drafting",
          "description": "Drafts invoices from project data and sends for review.",
          "inputs": ["Project name", "Client name", "Amount"],
          "outputs": ["Draft invoice"],
          "requires_human_review": true
        }
      ],
      "escalation_rules": ["Escalate to COO if payment is more than 30 days late"],
      "scheduler_interval_seconds": 1800,
      "work_hours": "09:00-18:00",
      "visual_character": "character_analyst"
    }
  ]
}
```

## Field rules

- `temp_id`: stable snake_case slug used only within this response for parent
  references (e.g. `"coo"`, `"marketing_lead"`, `"invoicing_specialist"`). Must
  be unique. The system assigns real UUIDs — do not include UUIDs.
- `name`: a human first name. Keep names varied and gender-diverse across the org.
  Do NOT use the domain name as the agent name.
- `level`: 0 = COO, 1 = N-1 domain lead, 2 = N-2 specialist, 3 = N-3 if needed.
  No hard cap; use deeper levels only for genuinely complex domains.
- `parent_temp_id`: `null` for the COO only. Every other agent must reference a
  valid `temp_id` from this response.
- `domain`: `null` for the COO. For all other agents, the domain name
  (e.g. `"Finance"`, `"Marketing"`, `"Customer Service"`).
- `role_description`: one sentence describing the agent's purpose and mandate.
- `responsibilities`: 2–5 concrete responsibilities, each as an actionable string.
- `skills`: 1–5 skills per agent. Each skill should be specific and actionable.
  Set `requires_human_review: true` for anything involving money, external
  communications sent on behalf of the user, or irreversible actions.
- `escalation_rules`: 1–3 rules specifying when this agent escalates to its parent
  or to the user.
- `scheduler_interval_seconds`: integer between 300 and 3600 (inclusive).
  Calibrate from the `autonomy_preference` in the business context:
  - High autonomy → 300–900 (agents wake up frequently and act independently)
  - Medium autonomy → 900–1800
  - Low autonomy / validation-heavy → 1800–3600
- `work_hours`: use the `work_hours` value from the business context as the
  default for all agents. Use `null` if the business context `work_hours` is null
  (always active). You may deviate for a specific agent only if semantically
  justified (e.g. a customer service agent may need wider hours than the user's
  personal schedule).
- `visual_character`: MUST be one of the exact strings listed below.

## Visual characters

`visual_character` must be one of the following exact strings — no other value
is valid:

- `"character_suit"` — executive, COO, management, finance, legal, HR
- `"character_creative"` — marketing, design, content, branding, social media
- `"character_tech"` — tech, IT, product, data, automation, web
- `"character_support"` — customer service, support, admin, operations, logistics
- `"character_analyst"` — research, analytics, strategy, reporting, planning
- `"character_sales"` — sales, business development, partnerships, prospecting

## Org design rules

1. Always generate exactly one COO (level=0). The COO coordinates all N-1 leads
   and is the user's primary operational contact.
2. Generate one N-1 domain lead (level=1) for each domain listed in
   `Domains to staff with AI agents`. Do NOT generate a lead for any domain listed
   in `Domains with human coverage` — those are explicitly excluded.
3. Under each N-1 lead, generate 1–3 N-2 specialists (level=2) based on task
   complexity. Do not generate N-2 agents with generic roles that duplicate their
   N-1 parent's scope — each specialist must own a distinct sub-domain.
4. Use N-3 agents (level=3) only for businesses with genuinely complex domains
   that warrant a third tier (e.g. a large e-commerce operation with separate
   SEO, paid acquisition, and retention specialists all under a Marketing Lead,
   who in turn has a Content Lead with copywriters underneath).
5. Infer the domains and specialist breakdown from the `Tasks to delegate` list
   if `Domains to staff` is empty or underspecified.
6. Agent names must be human first names. Use the language from the business
   context to choose culturally appropriate names.
7. The entire org must be self-consistent: every `parent_temp_id` must reference
   a `temp_id` that appears elsewhere in the response.
````

**Key design decisions for the prompt**:

- The business context is passed as the **user message** (not injected into the
  system prompt via `render()`). This avoids escaping issues with `str.format_map`
  when the context contains curly braces. The system prompt instructs: "The user
  message contains the business context."
- `scheduler_interval_seconds` range: 300–3600. Prompt guides the LLM:
  low autonomy → long interval (1800–3600); high autonomy → short interval (300–900).
- `work_hours` format: `"HH:MM-HH:MM"` or `null` for always active. Prompt says:
  "Use the work_hours from the business context unless a specific agent should run on
  a different schedule."
- The prompt instructs the LLM to **exclude** any domain from `domains_with_human_coverage`
  when placing N-1 agents.
- `is_paused` is **not** in the JSON schema — the prompt explicitly notes that it is
  managed by the system, not the LLM.
- Skills are inline per agent (list of objects, not references). UUIDs are assigned
  by the code.

---

### T3 — `GeneratorOrgGeneration` class (full implementation)

**Files**:

- MODIFY `backend/adjents/generator/org_generation.py` — add the class + helpers
- MODIFY `backend/tests/test_generator_org_generation.py` — add integration tests

**Full interface** of the completed `org_generation.py`:

```python
def _build_context_message(context: BusinessContext) -> str:
    """Serialize BusinessContext into a human-readable text for the user message."""
    ...

def _parse_raw_agents(data: dict[str, Any]) -> list[RawAgentData]:
    """Parse the 'agents' list from validated LLM JSON. Raises ValueError on shape error."""
    ...

def _resolve_and_build(
    raw_agents: list[RawAgentData],
) -> tuple[list[AgentSpec], list[Skill]]:
    """Assign UUIDs, resolve parent_temp_id → UUID, build AgentSpec + Skill objects."""
    ...

class GeneratorOrgGeneration:
    _MAX_RETRIES: int = 3

    def __init__(
        self,
        client: AnthropicClient,
        prompt_loader: PromptLoader,
        session: AsyncSession,
    ) -> None: ...

    async def generate(self, context: BusinessContext) -> OrgGenerationResult: ...

    async def _call_llm(
        self,
        system: str,
        context_msg: str,
        domains_with_human_coverage: list[str],
    ) -> list[RawAgentData]:
        """Retry loop: call LLM → parse JSON → validate structure → return raw agents."""
        ...

    async def _persist(
        self, agents: list[AgentSpec], skills: list[Skill]
    ) -> None:
        """Persist all AgentSpec, Skill, and AgentState records in a single commit."""
        ...
```

**`_build_context_message` format** (Python code, not in the prompt):

```python
def _build_context_message(context: BusinessContext) -> str:
    lines = [
        f"Business name: {context.business_name or 'N/A'}",
        f"Founder: {context.founder_name}",
        f"Language: {context.language}",
        f"Core activity: {context.core_activity}",
        f"Legal status: {context.legal_status or 'N/A'}",
        f"Target clients: {', '.join(context.target_clients) or 'N/A'}",
        f"Domains with human coverage (DO NOT generate agents for these): "
        f"{', '.join(context.domains_with_human_coverage) or 'none'}",
        f"Domains to staff with AI agents: "
        f"{', '.join(context.domains_to_staff) or 'infer from tasks below'}",
        "Tasks to delegate:",
        *[f"  - {t}" for t in context.tasks_to_delegate],
        f"Tasks user keeps: {', '.join(context.tasks_user_keeps) or 'N/A'}",
        f"Financial goals: {context.financial_goals or 'N/A'}",
        f"Existing tools: {', '.join(context.existing_tools) or 'none'}",
        f"Autonomy preference: {context.autonomy_preference}",
        f"Work hours: {context.work_hours or 'null — always active'}",
        f"Additional context: {context.additional_context or 'none'}",
    ]
    return "\n".join(lines)
```

**`_call_llm` retry logic** (3 passes max, with progressive feedback):

```text
Attempt N:
  1. Call client.complete(messages, system=system, max_tokens=8192)
  2. If JSON invalid:
       append {"role": "assistant", last_raw} + {"role": "user", "Respond with valid JSON only."}
       continue
  3. If JSON valid but _parse_raw_agents fails (KeyError/TypeError/ValueError):
       append error + "Use the exact JSON schema."
       continue
  4. If JSON valid, parsed, but _validate_structure returns an error message:
       append error + "Fix this issue and respond with the corrected JSON."
       continue
  5. Valid → return raw_agents

After 3 failed attempts: raise OrgGenerationError with last_raw[:300]
```

**`_resolve_and_build` logic**:

```text
1. Build temp_id → uuid4() mapping for all agents (one pass)
2. For each raw agent:
   a. agent_id = temp_id_to_uuid[raw.temp_id]
   b. parent_id = temp_id_to_uuid[raw.parent_temp_id] if parent_temp_id else None
   c. For each inline skill dict → build Skill(id=uuid4(), ...)
   d. Build AgentSpec(id=agent_id, parent_id=parent_id, skill_ids=[...], is_paused=True, ...)
3. Return (all_specs, all_skills)
```

**`_persist` logic**:

```text
For each Skill → session.add(skill_to_table(skill))
For each AgentSpec:
  → session.add(agent_spec_to_table(spec))
  → build AgentState(agent_id=spec.id, status=PAUSED, meeting_with=[], updated_at=now)
  → session.add(agent_state_to_table(state))
await session.commit()   ← single commit for the entire org
```

Plain INSERT — no DELETE before. If called twice on the same context, two independent
sets of records are inserted (new UUIDs each time). This is expected v0.1 behaviour
(ADR 0005).

**Fixture used across all T3 tests** — minimal valid LLM response (1 COO + 1 N-1):

```python
_VALID_LLM_RESPONSE = json.dumps({
    "agents": [
        {
            "temp_id": "coo",
            "name": "Jordan",
            "level": 0,
            "parent_temp_id": None,
            "domain": None,
            "role_description": "Chief of Staff — coordinates all N-1 leads.",
            "responsibilities": ["Coordinate N-1 leads daily"],
            "skills": [
                {
                    "name": "Daily synthesis",
                    "description": "Aggregates status reports into a summary.",
                    "inputs": ["N-1 status reports"],
                    "outputs": ["Daily summary"],
                    "requires_human_review": False,
                }
            ],
            "escalation_rules": ["Escalate conflicts to user"],
            "scheduler_interval_seconds": 900,
            "work_hours": "09:00-18:00",
            "visual_character": "character_suit",
        },
        {
            "temp_id": "finance_lead",
            "name": "Alex",
            "level": 1,
            "parent_temp_id": "coo",
            "domain": "Finance",
            "role_description": "Finance Lead.",
            "responsibilities": ["Manage invoicing"],
            "skills": [
                {
                    "name": "Invoice tracking",
                    "description": "Tracks invoice payment status.",
                    "inputs": ["Invoice list"],
                    "outputs": ["Status report"],
                    "requires_human_review": True,
                }
            ],
            "escalation_rules": ["Escalate to COO if blocked"],
            "scheduler_interval_seconds": 1800,
            "work_hours": "09:00-18:00",
            "visual_character": "character_analyst",
        },
    ]
})
```

**Tests for T3** (all with mocked `AnthropicClient.complete`):

- `test_generate_calls_llm_with_max_tokens_8192`
  — verify `complete(..., max_tokens=8192)` is called
- `test_generate_persists_agent_specs`
  — 2 `AgentSpecTable` rows in DB
- `test_generate_persists_skills`
  — 2 `SkillTable` rows in DB
- `test_generate_persists_agent_states`
  — 2 `AgentStateTable` rows in DB
- `test_generate_all_states_are_paused`
  — all `AgentStateTable.status == "paused"`
- `test_generate_all_specs_are_paused`
  — all `AgentSpecTable.is_paused == True`
- `test_generate_coo_has_no_parent_id`
  — COO's `AgentSpec.parent_id` is `None`
- `test_generate_n1_parent_id_is_coo_uuid`
  — N-1's `parent_id` matches the COO's `id` (both in DB, joined by `parent_id`)
- `test_generate_skill_ids_reference_persisted_skills`
  — `AgentSpec.skill_ids` are UUIDs of persisted `Skill` records
- `test_generate_returns_org_result`
  — returns `OrgGenerationResult` with `len(agents)==2`, `len(skills)==2`
- `test_generate_retry_invalid_json_succeeds`
  — 2 non-JSON responses then 1 valid → success, DB has records
- `test_generate_retry_invalid_structure_with_feedback`
  — 1 structurally invalid (two COOs) then 1 valid → success
- `test_generate_all_retries_exhausted_raises_error`
  — 3 non-JSON responses → `OrgGenerationError`
- `test_generate_twice_inserts_two_independent_sets`
  — call `generate()` twice → 4 `AgentSpecTable` rows (no PK conflict)
- `test_generate_excludes_human_covered_domain`
  — `BusinessContext` has `domains_with_human_coverage=["Finance"]`; mock returns
    `_VALID_LLM_RESPONSE` (which contains a Finance N-1) on the first call, then
    `_VALID_LLM_RESPONSE_NO_FINANCE` (COO only, no Finance agent) on the second;
    assert `complete` was called twice and that no `AgentSpecTable` row has
    `domain="Finance"` in the DB. `_VALID_LLM_RESPONSE_NO_FINANCE` must be defined
    as a second fixture constant (COO-only org, all valid)

---

### T4 — Smoke test `scripts/smoke_generator_org.py`

**File**:

- CREATE `backend/scripts/smoke_generator_org.py`

Not a pytest test — requires a real `ANTHROPIC_API_KEY`. Not run by CI.

**Sophie Dubois `BusinessContext`** (hand-crafted, not from an interview):

```python
context = BusinessContext(
    id=str(uuid4()),
    conversation_id=str(uuid4()),
    business_name="Sophie Dubois Creations",
    founder_name="Sophie Dubois",
    language="en",
    core_activity=(
        "Independent artist and maker specializing in handcrafted jewelry. "
        "Sells online (Shopify, B2C), runs live crafting workshops and video courses "
        "(Teachable), and organizes B2B corporate team-building workshops. "
        "Active presence on YouTube and Instagram."
    ),
    legal_status="Sole proprietorship (DBA)",
    target_clients=[
        "B2C buyers of handcrafted jewelry (US market)",
        "Creative learners enrolled in online courses",
        "US companies seeking unique corporate team-building experiences (B2B)",
    ],
    domains_with_human_coverage=[],
    domains_to_staff=[
        "E-commerce",
        "Digital Marketing",
        "Content & Social Media",
        "Online Education",
        "B2B Sales",
        "Finance & Accounting",
        "Operations & Logistics",
        "Customer Service",
        "Tech & Automation",
        "Social Media",
    ],
    tasks_to_delegate=[
        "Shopify store management (product listings, inventory, order fulfillment)",
        "Sales tracking and analytics reporting",
        "Meta Ads and Google Ads campaign management",
        "Email marketing via Mailchimp (newsletters, automated sequences)",
        "Instagram and YouTube content scheduling and publication",
        "Teachable course management (enrollments, follow-ups, student support)",
        "B2B workshop prospecting and quote generation",
        "Invoicing, Stripe payment tracking, quarterly estimated tax reminders",
        "Expense tracking and per-channel profitability analysis",
        "Customer support (emails, comments, refund requests)",
        "Website maintenance, Zapier integrations, tool stack management",
    ],
    tasks_user_keeps=[
        "Making the jewelry",
        "Live facilitation of workshops and courses",
        "Designing new product lines and collections",
    ],
    financial_goals=(
        "Revenue target: $100,000/year. "
        "Net margin > 50% on jewelry, > 70% on courses and workshops. "
        "Fixed costs: ~$1,000/month (materials, tools, software subscriptions)."
    ),
    existing_tools=[
        "Shopify", "Teachable", "Stripe", "Mailchimp", "Meta Ads", "Google Ads",
        "Notion", "Canva", "Later", "Google Analytics", "Zoom",
    ],
    autonomy_preference=(
        "Maximum autonomy on routine tasks. "
        "Human approval required for anything involving money (>$100), "
        "personalized client communications, or pricing changes."
    ),
    work_hours="09:00-22:00",
    additional_context=(
        "Sophie operates fully solo with no employees. "
        "Immediate priority: automate marketing and order management "
        "to free up creative time."
    ),
    created_at=datetime.now(UTC),
)
```

**Verification assertions** (printed, not pytest assertions):

- Total N-1 agents ≥ 10
- Total N-2 agents ≥ 15
- Total skills ≥ 40
- Each N-1 has at least 1 N-2 direct report
- No agent has an invalid `visual_character`
- All `AgentState` have `status = PAUSED`
- Prints an indented org tree (COO → N-1s → N-2s)

**Usage**:

```bash
# From backend/
uv run python scripts/smoke_generator_org.py
```

---

## TDD execution order

```text
T1 → T2 → T3 → T4
```

Each task:

1. Write failing tests (RED) — `uv run pytest tests/test_generator_org_generation.py -v`
2. Write implementation (GREEN) — make tests pass
3. `uv run ruff check adjents/ tests/ && uv run mypy adjents/`
4. Move to next task

T2 has no pytest tests but must be committed before T3 so the smoke test can
use the real prompt. T3 tests use a minimal in-memory prompt fixture (not the
real `org_generation.md`) — so T2 and T3 are independent and T2 can be done
in either order relative to T3.

---

## Critical file reference

| Role | Path |
| --- | --- |
| Agent models | `backend/adjents/agents/models.py` |
| BusinessContext model | `backend/adjents/generator/models.py` |
| DB tables | `backend/adjents/db/tables.py` |
| Convert functions | `backend/adjents/db/convert.py` |
| AnthropicClient | `backend/adjents/llm/anthropic_client.py` |
| LLMRouter | `backend/adjents/router/router.py` |
| PromptLoader | `backend/adjents/prompts/loader.py` |
| Org generation prompt (stub) | `backend/adjents/prompts/generator/org_generation.md` |
| Existing interview class (reference) | `backend/adjents/generator/interview.py` |
| Existing interview tests (reference) | `backend/tests/test_generator_interview.py` |
| Test conftest | `backend/tests/conftest.py` |
| Smoke test reference | `backend/scripts/smoke_generator_interview.py` |
| Feature Brief | `docs/specs/2026-05-22-generator-agent-org-generation.md` |

---

## Files created / modified

| Action | Path |
| --- | --- |
| CREATE | `backend/adjents/generator/org_generation.py` |
| CREATE | `backend/tests/test_generator_org_generation.py` |
| MODIFY | `backend/adjents/prompts/generator/org_generation.md` |
| CREATE | `backend/scripts/smoke_generator_org.py` |

No changes to `db/tables.py`, `db/convert.py`, `agents/models.py`, or
`generator/models.py` — all dependencies are already in place.

---

## Coherence notes

### Divergence from ARCHITECTURE.md §9 (prompt rendering)

`ARCHITECTURE.md` §9 shows `loader.render("agent/think_and_act", agent_name=...)` as
the standard pattern for injecting variables into prompts. This feature does **not**
use `render()` for `org_generation.md`. Instead, the business context is passed as
the user message, and the system prompt is loaded as a static string (`prompt.content`
with no substitution).

The system prompt still lives in `prompts/generator/org_generation.md` and is loaded
at runtime via `PromptLoader.get()`. The only difference is the call site:

```python
# Standard pattern — template variables substituted via str.format_map()
system = loader.get("agent/think_and_act").render(agent_name="Alex", ...)

# Org generation — content loaded from .md as-is, no substitution
system = loader.get("generator/org_generation").content
```

**Why skip `render()`**: `render()` calls `str.format_map()` on the prompt content.
The business context is user-supplied free text that may contain literal curly braces
(tool names, code snippets, markup). Passing it through `format_map()` would raise
`KeyError`. Passing the context as the user message sidesteps this entirely, and is
semantically equivalent — the LLM reads the system prompt and the user message in the
same context window regardless.

The `render()` pattern remains appropriate for prompts whose template variables are
always developer-controlled (agent name, responsibilities list, etc.) and guaranteed
to be brace-free.

This divergence is intentional and does not require an ADR — it is an implementation
detail of this specific prompt call, not an architectural change.

### `work_hours` design — known limitation

`AgentSpec.work_hours` is currently `str | None` with format `"HH:MM-HH:MM"`,
representing a single daily time window applied uniformly on all days.

**What is already covered**: each `AgentSpec` has its own independent `work_hours`
field. The LLM can assign different schedules to different agents — e.g. a Social
Media agent with `work_hours=null` (always active) alongside a B2B Sales agent with
`work_hours="09:00-17:00"`. This is fully supported in v0.1.

**What is not covered** (known limitations, not in scope for this feature):

| Use case | Example | Status |
| --- | --- | --- |
| Per-agent independent schedules | LinkedIn agent 24/7, prospecting agent 9-17 | ✅ Already handled |
| Day-of-week variation | Tuesday nights OK, Thursday nights not | ❌ Not supported |
| Multiple windows per day | 9-12 and 14-18 (lunch break) | ❌ Not supported |
| Weekday-only or weekend-only | Agent active Mon–Fri only | ❌ Not supported |

The day-of-week and multi-window cases are a **v0.2 enhancement**. The format could
evolve to something like `"Mon-Fri:09:00-17:00"` or a list of `{day, start, end}`
objects. This would require:

- A schema change to `AgentSpec.work_hours` and `AgentSpecTable`
- Updated parsing in the agent loop
- Updated prompt instructions and validation

No action required in this feature. The current `"HH:MM-HH:MM"` format is a
documented simplification that covers the large majority of v0.1 use cases.

---

## Verification

```bash
cd backend
uv run pytest tests/ -v              # all tests pass (130 existing + new)
uv run ruff check adjents/ tests/    # 0 errors
uv run mypy adjents/                 # mypy --strict clean
```

After verifying all tests pass, run the smoke test (requires `ANTHROPIC_API_KEY`):

```bash
cd backend
uv run python scripts/smoke_generator_org.py
```

Expected output: org tree with ≥ 10 N-1 agents, ≥ 15 N-2 agents, ≥ 40 skills.
