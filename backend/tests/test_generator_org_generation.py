"""Tests for Generator Agent org generation — T1: validation + T3: integration."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlmodel import select

from adjents.db.tables import AgentSpecTable, AgentStateTable, SkillTable
from adjents.generator.models import BusinessContext
from adjents.generator.org_generation import (
    VALID_VISUAL_CHARACTERS,
    GeneratorOrgGeneration,
    OrgGenerationError,
    OrgGenerationResult,
    RawAgentData,
    _validate_structure,
)
from adjents.llm.anthropic_client import AnthropicClient
from adjents.llm.errors import LLMRefusalError, LLMTruncatedError
from adjents.prompts.loader import LoadedPrompt, PromptLoader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_raw(
    temp_id: str,
    level: int,
    parent_temp_id: str | None = None,
    domain: str | None = None,
    visual_character: str = "character_suit",
    scheduler_interval_seconds: int = 900,
) -> RawAgentData:
    return RawAgentData(
        temp_id=temp_id,
        name="Test Agent",
        level=level,
        parent_temp_id=parent_temp_id,
        domain=domain,
        role_description="Test role.",
        responsibilities=["Do things"],
        skills=[],
        escalation_rules=["Escalate to user"],
        scheduler_interval_seconds=scheduler_interval_seconds,
        work_hours="09:00-18:00",
        visual_character=visual_character,
    )


# ---------------------------------------------------------------------------
# T1 — Structural validation: happy paths
# ---------------------------------------------------------------------------


def test_valid_org_returns_none() -> None:
    """COO + 2 N-1 + 1 N-2 — all valid, no human coverage."""
    coo = make_raw("coo", level=0)
    n1_a = make_raw("lead_a", level=1, parent_temp_id="coo", domain="Finance")
    n1_b = make_raw("lead_b", level=1, parent_temp_id="coo", domain="Marketing")
    n2 = make_raw("spec_a", level=2, parent_temp_id="lead_a", domain="Finance")
    assert _validate_structure([coo, n1_a, n1_b, n2], []) is None


def test_coo_only_org_returns_none() -> None:
    """COO alone — all domains covered by humans, no AI agents below."""
    coo = make_raw("coo", level=0)
    assert _validate_structure([coo], []) is None


# ---------------------------------------------------------------------------
# T1 — Rule 1 & 2: COO presence and parent_temp_id constraints
# ---------------------------------------------------------------------------


def test_no_coo_returns_error() -> None:
    """No agent with level=0 → error."""
    n1 = make_raw("lead_a", level=1, parent_temp_id="somewhere", domain="Finance")
    result = _validate_structure([n1], [])
    assert result is not None


def test_two_coos_returns_error() -> None:
    """Two agents with level=0 → error."""
    coo1 = make_raw("coo1", level=0)
    coo2 = make_raw("coo2", level=0)
    n1 = make_raw("lead_a", level=1, parent_temp_id="coo1", domain="Finance")
    result = _validate_structure([coo1, coo2, n1], [])
    assert result is not None


def test_level_0_with_parent_returns_error() -> None:
    """Agent with level=0 but non-null parent_temp_id → error."""
    coo = make_raw("coo", level=0, parent_temp_id="someone")
    result = _validate_structure([coo], [])
    assert result is not None


def test_non_coo_without_parent_returns_error() -> None:
    """Agent with level=1 and parent_temp_id=None → error."""
    coo = make_raw("coo", level=0)
    orphan = make_raw("orphan", level=1, parent_temp_id=None, domain="Finance")
    result = _validate_structure([coo, orphan], [])
    assert result is not None


# ---------------------------------------------------------------------------
# T1 — Rule 3: Unique temp_ids
# ---------------------------------------------------------------------------


def test_duplicate_temp_id_returns_error() -> None:
    """Two agents with the same temp_id → error."""
    coo = make_raw("coo", level=0)
    n1_a = make_raw("lead_a", level=1, parent_temp_id="coo", domain="Finance")
    n1_dup = make_raw("lead_a", level=1, parent_temp_id="coo", domain="Marketing")
    result = _validate_structure([coo, n1_a, n1_dup], [])
    assert result is not None


# ---------------------------------------------------------------------------
# T1 — Rule 4: parent_temp_id must exist
# ---------------------------------------------------------------------------


def test_unknown_parent_returns_error() -> None:
    """Agent references a non-existent parent_temp_id → error."""
    coo = make_raw("coo", level=0)
    n1 = make_raw("lead_a", level=1, parent_temp_id="ghost", domain="Finance")
    result = _validate_structure([coo, n1], [])
    assert result is not None


# ---------------------------------------------------------------------------
# T1 — Rule 5: No cycle
# ---------------------------------------------------------------------------


def test_cycle_returns_error() -> None:
    """A is parent of B, B is parent of A → cycle detected."""
    coo = make_raw("coo", level=0)
    a = make_raw("a", level=1, parent_temp_id="b", domain="Sales")
    b = make_raw("b", level=1, parent_temp_id="a", domain="Marketing")
    result = _validate_structure([coo, a, b], [])
    assert result is not None
    assert "cycle" in result.lower()


# ---------------------------------------------------------------------------
# T1 — Rule 6: No N-1 agent in human-covered domain
# ---------------------------------------------------------------------------


def test_human_domain_n1_returns_error() -> None:
    """N-1 agent whose domain is in domains_with_human_coverage → error."""
    coo = make_raw("coo", level=0)
    n1 = make_raw("finance_lead", level=1, parent_temp_id="coo", domain="Finance")
    result = _validate_structure([coo, n1], ["Finance"])
    assert result is not None


def test_human_domain_case_insensitive() -> None:
    """'finance' in human coverage matches N-1 domain 'Finance' (case-insensitive)."""
    coo = make_raw("coo", level=0)
    n1 = make_raw("finance_lead", level=1, parent_temp_id="coo", domain="Finance")
    result = _validate_structure([coo, n1], ["finance"])
    assert result is not None


# ---------------------------------------------------------------------------
# T1 — Rule 7: visual_character must be in VALID_VISUAL_CHARACTERS
# ---------------------------------------------------------------------------


def test_invalid_visual_character_returns_error() -> None:
    """Unknown visual_character value → error."""
    coo = make_raw("coo", level=0, visual_character="character_unicorn")
    result = _validate_structure([coo], [])
    assert result is not None


def test_valid_visual_characters_pass() -> None:
    """Each valid visual_character passes validation on its own."""
    for vc in VALID_VISUAL_CHARACTERS:
        coo = make_raw("coo", level=0, visual_character=vc)
        assert _validate_structure([coo], []) is None, f"Expected None for {vc!r}"


# ---------------------------------------------------------------------------
# T1 — Rule 8: scheduler_interval_seconds in [300, 3600]
# ---------------------------------------------------------------------------


def test_scheduler_interval_too_low_returns_error() -> None:
    """scheduler_interval_seconds=299 → below minimum → error."""
    coo = make_raw("coo", level=0, scheduler_interval_seconds=299)
    result = _validate_structure([coo], [])
    assert result is not None


def test_scheduler_interval_too_high_returns_error() -> None:
    """scheduler_interval_seconds=3601 → above maximum → error."""
    coo = make_raw("coo", level=0, scheduler_interval_seconds=3601)
    result = _validate_structure([coo], [])
    assert result is not None


def test_scheduler_interval_valid_bounds() -> None:
    """scheduler_interval_seconds=300 and 3600 are both inclusive bounds."""
    coo_low = make_raw("coo", level=0, scheduler_interval_seconds=300)
    assert _validate_structure([coo_low], []) is None

    coo_high = make_raw("coo", level=0, scheduler_interval_seconds=3600)
    assert _validate_structure([coo_high], []) is None


# ---------------------------------------------------------------------------
# T3 — Integration tests for GeneratorOrgGeneration
# ---------------------------------------------------------------------------

# Minimal valid LLM response: 1 COO + 1 N-1, each with 1 skill.
_VALID_LLM_RESPONSE = json.dumps(
    {
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
    }
)

# COO-only response (no Finance agent) — used for human-coverage exclusion test.
_VALID_LLM_RESPONSE_NO_FINANCE = json.dumps(
    {
        "agents": [
            {
                "temp_id": "coo",
                "name": "Jordan",
                "level": 0,
                "parent_temp_id": None,
                "domain": None,
                "role_description": "Chief of Staff.",
                "responsibilities": ["Coordinate leads"],
                "skills": [
                    {
                        "name": "Daily synthesis",
                        "description": "Aggregates reports.",
                        "inputs": ["Reports"],
                        "outputs": ["Summary"],
                        "requires_human_review": False,
                    }
                ],
                "escalation_rules": ["Escalate to user"],
                "scheduler_interval_seconds": 900,
                "work_hours": "09:00-18:00",
                "visual_character": "character_suit",
            }
        ]
    }
)


@pytest.fixture
def business_context() -> BusinessContext:
    return BusinessContext(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        business_name="Test Business",
        founder_name="Test Founder",
        language="en",
        core_activity="Test activity",
        legal_status=None,
        target_clients=["Client A"],
        domains_with_human_coverage=[],
        domains_to_staff=["Finance"],
        tasks_to_delegate=["Manage invoicing"],
        tasks_user_keeps=["Make decisions"],
        financial_goals=None,
        existing_tools=["Stripe"],
        autonomy_preference="Medium autonomy",
        work_hours="09:00-18:00",
        additional_context=None,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_prompt_loader() -> MagicMock:
    loader = MagicMock(spec=PromptLoader)
    loader.get.return_value = LoadedPrompt(
        frontmatter={"version": 1},
        content="You are a test system prompt.",
    )
    return loader


def _make_client(response: str) -> MagicMock:
    """Return a mocked AnthropicClient whose complete() returns `response`."""
    client = MagicMock(spec=AnthropicClient)
    client.complete = AsyncMock(return_value=response)
    return client


# ── LLM call parameters ─────────────────────────────────────────────────────


async def test_generate_calls_llm_with_max_tokens(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """complete() must be called with max_tokens == _MAX_TOKENS class constant."""
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, async_session)  # type: ignore[arg-type]
    await gen.generate(business_context)
    assert (
        client.complete.call_args.kwargs["max_tokens"]
        == GeneratorOrgGeneration._MAX_TOKENS
    )


async def test_generate_leaves_room_for_thinking_in_max_tokens(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """Large org JSON + high-effort thinking share one output budget (ADR 0012)."""
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, async_session)  # type: ignore[arg-type]
    await gen.generate(business_context)
    assert client.complete.call_args.kwargs["max_tokens"] == 64000


async def test_generate_uses_high_effort(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, async_session)  # type: ignore[arg-type]
    await gen.generate(business_context)
    assert client.complete.call_args.kwargs["effort"] == "high"


@pytest.mark.parametrize(
    "error",
    [
        LLMRefusalError(model="m", category="cyber", explanation=None),
        LLMTruncatedError(
            stop_reason="max_tokens", model="m", max_tokens=64000, output_tokens=64000
        ),
    ],
)
async def test_generate_propagates_llm_errors_without_retry(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
    error: Exception,
) -> None:
    """Refusal / truncation is not a JSON error: no corrective retry (ADR 0012)."""
    client = MagicMock(spec=AnthropicClient)
    client.complete = AsyncMock(side_effect=error)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, async_session)  # type: ignore[arg-type]
    with pytest.raises(type(error)):
        await gen.generate(business_context)
    assert client.complete.call_count == 1


# ── Persistence: counts ──────────────────────────────────────────────────────


async def test_generate_persists_agent_specs(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """2 AgentSpecTable rows must be inserted for the 2-agent response."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    await gen.generate(business_context)
    rows = (await session.exec(select(AgentSpecTable))).all()
    assert len(rows) == 2


async def test_generate_persists_skills(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """2 SkillTable rows (one per agent) must be inserted."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    await gen.generate(business_context)
    rows = (await session.exec(select(SkillTable))).all()
    assert len(rows) == 2


async def test_generate_persists_agent_states(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """2 AgentStateTable rows must be inserted."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    await gen.generate(business_context)
    rows = (await session.exec(select(AgentStateTable))).all()
    assert len(rows) == 2


# ── Persistence: invariants ───────────────────────────────────────────────────


async def test_generate_all_states_are_paused(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """All AgentStateTable rows must have status='paused'."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    await gen.generate(business_context)
    rows = (await session.exec(select(AgentStateTable))).all()
    assert all(r.status == "paused" for r in rows)


async def test_generate_all_specs_are_paused(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """All AgentSpecTable rows must have is_paused=True."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    await gen.generate(business_context)
    rows = (await session.exec(select(AgentSpecTable))).all()
    assert all(r.is_paused for r in rows)


async def test_generate_coo_has_no_parent_id(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """COO's parent_id must be None in the DB."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    await gen.generate(business_context)
    rows = (await session.exec(select(AgentSpecTable))).all()
    coo = next(r for r in rows if r.level == 0)
    assert coo.parent_id is None


async def test_generate_n1_parent_id_is_coo_uuid(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """N-1 agent's parent_id must match the COO's id."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    await gen.generate(business_context)
    rows = (await session.exec(select(AgentSpecTable))).all()
    coo = next(r for r in rows if r.level == 0)
    n1 = next(r for r in rows if r.level == 1)
    assert n1.parent_id == coo.id


async def test_generate_skill_ids_reference_persisted_skills(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """Each skill_id in AgentSpec.skill_ids must correspond to a SkillTable row."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    await gen.generate(business_context)
    spec_rows = (await session.exec(select(AgentSpecTable))).all()
    skill_rows = (await session.exec(select(SkillTable))).all()
    skill_ids_in_db = {r.id for r in skill_rows}
    for spec_row in spec_rows:
        for skill_id in json.loads(spec_row.skill_ids):
            assert skill_id in skill_ids_in_db


# ── Return value ──────────────────────────────────────────────────────────────


async def test_generate_returns_org_result(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """generate() must return an OrgGenerationResult with 2 agents and 2 skills."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    result = await gen.generate(business_context)
    assert isinstance(result, OrgGenerationResult)
    assert len(result.agents) == 2
    assert len(result.skills) == 2


# ── Retry behaviour ───────────────────────────────────────────────────────────


async def test_generate_retry_invalid_json_succeeds(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """2 non-JSON responses then 1 valid → success, DB has 2 AgentSpec rows."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = MagicMock(spec=AnthropicClient)
    client.complete = AsyncMock(
        side_effect=["not json", "still not json", _VALID_LLM_RESPONSE]
    )
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    result = await gen.generate(business_context)
    assert isinstance(result, OrgGenerationResult)
    rows = (await session.exec(select(AgentSpecTable))).all()
    assert len(rows) == 2


async def test_generate_retry_invalid_structure_with_feedback(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """1 structurally invalid response (two COOs) then 1 valid → success."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    two_coos = json.dumps(
        {
            "agents": [
                {
                    "temp_id": "coo1",
                    "name": "Jordan",
                    "level": 0,
                    "parent_temp_id": None,
                    "domain": None,
                    "role_description": "COO 1.",
                    "responsibilities": ["Coordinate"],
                    "skills": [
                        {
                            "name": "Synthesis",
                            "description": "Aggregates.",
                            "inputs": ["Reports"],
                            "outputs": ["Summary"],
                            "requires_human_review": False,
                        }
                    ],
                    "escalation_rules": ["Escalate"],
                    "scheduler_interval_seconds": 900,
                    "work_hours": "09:00-18:00",
                    "visual_character": "character_suit",
                },
                {
                    "temp_id": "coo2",
                    "name": "Morgan",
                    "level": 0,
                    "parent_temp_id": None,
                    "domain": None,
                    "role_description": "COO 2.",
                    "responsibilities": ["Coordinate"],
                    "skills": [
                        {
                            "name": "Synthesis",
                            "description": "Aggregates.",
                            "inputs": ["Reports"],
                            "outputs": ["Summary"],
                            "requires_human_review": False,
                        }
                    ],
                    "escalation_rules": ["Escalate"],
                    "scheduler_interval_seconds": 900,
                    "work_hours": "09:00-18:00",
                    "visual_character": "character_suit",
                },
            ]
        }
    )
    client = MagicMock(spec=AnthropicClient)
    client.complete = AsyncMock(side_effect=[two_coos, _VALID_LLM_RESPONSE])
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    result = await gen.generate(business_context)
    assert isinstance(result, OrgGenerationResult)
    assert client.complete.call_count == 2


async def test_generate_all_retries_exhausted_raises_error(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """3 non-JSON responses → OrgGenerationError raised."""
    client = MagicMock(spec=AnthropicClient)
    client.complete = AsyncMock(side_effect=["bad", "bad", "bad"])
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, async_session)  # type: ignore[arg-type]
    with pytest.raises(OrgGenerationError):
        await gen.generate(business_context)


async def test_generate_twice_inserts_two_independent_sets(
    async_session: object,
    business_context: BusinessContext,
    mock_prompt_loader: MagicMock,
) -> None:
    """Calling generate() twice inserts 4 AgentSpec rows (new UUIDs, no conflict)."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    client = _make_client(_VALID_LLM_RESPONSE)
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    await gen.generate(business_context)
    await gen.generate(business_context)
    rows = (await session.exec(select(AgentSpecTable))).all()
    assert len(rows) == 4


async def test_generate_excludes_human_covered_domain(
    async_session: object,
    mock_prompt_loader: MagicMock,
) -> None:
    """Finance in human coverage → first call rejected, second (COO-only) accepted."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    session = async_session  # type: ignore[assignment]
    assert isinstance(session, AsyncSession)
    context = BusinessContext(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        business_name="Test",
        founder_name="Founder",
        language="en",
        core_activity="Testing",
        legal_status=None,
        target_clients=[],
        domains_with_human_coverage=["Finance"],
        domains_to_staff=[],
        tasks_to_delegate=[],
        tasks_user_keeps=[],
        financial_goals=None,
        existing_tools=[],
        autonomy_preference="Medium",
        work_hours=None,
        additional_context=None,
        created_at=datetime.now(UTC),
    )
    client = MagicMock(spec=AnthropicClient)
    # First response has a Finance N-1 → validation fails (human coverage)
    # Second response is COO-only → passes
    client.complete = AsyncMock(
        side_effect=[_VALID_LLM_RESPONSE, _VALID_LLM_RESPONSE_NO_FINANCE]
    )
    gen = GeneratorOrgGeneration(client, mock_prompt_loader, session)
    await gen.generate(context)
    assert client.complete.call_count == 2
    rows = (await session.exec(select(AgentSpecTable))).all()
    assert all(r.domain != "Finance" for r in rows)
