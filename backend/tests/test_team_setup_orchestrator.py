"""T4 tests: TeamSetupOrchestrator — session, conversation, traversal, validation."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.agents.models import AgentStatus
from adjents.db.tables import (
    AgentSpecTable,
    AgentStateTable,
    AgentValidationRecordTable,
    MessageTable,
    SkillTable,
    ValidationSessionTable,
)
from adjents.generator.team_setup import TeamSetupError, TeamSetupOrchestrator
from adjents.llm.anthropic_client import AnthropicClient
from adjents.prompts.loader import PromptLoader


def _make_orchestrator(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mock_complete: AsyncMock,
) -> TeamSetupOrchestrator:
    client = MagicMock(spec=AnthropicClient)
    client.complete = mock_complete
    return TeamSetupOrchestrator(client, stub_prompt_loader, async_session)


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_session_creates_validation_session(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    mock_complete = AsyncMock(return_value="Hello, I'm Jordan.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    rows = (await async_session.exec(select(ValidationSessionTable))).all()  # type: ignore[call-overload]
    assert len(rows) == 1
    assert rows[0].id == session.id


@pytest.mark.asyncio
async def test_start_session_creates_one_record_per_coo_and_n1(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    await orch.start_session()
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    # COO (level=0) + N-1 Finance Lead (level=1); N-2 Invoicing is NOT a root
    assert len(rows) == 2
    root_ids = {r.root_agent_id for r in rows}
    assert mini_org["coo_id"] in root_ids
    assert mini_org["n1_id"] in root_ids
    assert mini_org["n2_id"] not in root_ids


@pytest.mark.asyncio
async def test_start_session_all_records_pending(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    await orch.start_session()
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    assert all(r.status == "pending" for r in rows)


@pytest.mark.asyncio
async def test_start_session_raises_if_session_exists(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    await orch.start_session()
    with pytest.raises(TeamSetupError):
        await orch.start_session()


@pytest.mark.asyncio
async def test_resume_session_returns_existing_incomplete_session(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    resumed = await orch.resume_session()
    assert resumed is not None
    assert resumed.id == session.id


@pytest.mark.asyncio
async def test_resume_session_returns_none_if_no_session(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    result = await orch.resume_session()
    assert result is None


@pytest.mark.asyncio
async def test_resume_session_returns_none_if_session_completed(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    coo_only_org: dict[str, str],
) -> None:
    coo_id = coo_only_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello, I'm Jordan.",
            "Here is my summary.",
            '{"agent_updates": []}',
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    result = await orch.resume_session()
    assert result is None


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_agent_conversation_sets_record_in_progress(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(return_value="Hello, I'm Jordan.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    coo_rec = next(r for r in rows if r.root_agent_id == coo_id)
    assert coo_rec.status == "in_progress"


@pytest.mark.asyncio
async def test_start_agent_conversation_sets_agent_state_in_meeting(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(return_value="Hello, I'm Jordan.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    state_row = await async_session.get(AgentStateTable, coo_id)
    assert state_row is not None
    assert state_row.status == AgentStatus.IN_MEETING_1ON1


@pytest.mark.asyncio
async def test_start_agent_conversation_raises_if_coo_not_validated(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    n1_id = mini_org["n1_id"]
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    with pytest.raises(TeamSetupError):
        await orch.start_agent_conversation(session.id, n1_id)


@pytest.mark.asyncio
async def test_start_agent_conversation_coo_stack_is_coo_id(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(return_value="Hello, I'm Jordan.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    coo_rec = next(r for r in rows if r.root_agent_id == coo_id)
    assert json.loads(coo_rec.navigation_stack) == [coo_id]


@pytest.mark.asyncio
async def test_start_agent_conversation_n1_stack_is_n1_id(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    n1_id = mini_org["n1_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello, I'm Jordan.",
            "Here is my summary.",
            '{"agent_updates": []}',
            "Hello, I'm Alex.",
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    await orch.start_agent_conversation(session.id, n1_id)
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    n1_rec = next(r for r in rows if r.root_agent_id == n1_id)
    assert json.loads(n1_rec.navigation_stack) == [n1_id]


@pytest.mark.asyncio
async def test_reply_returns_active_agent_response(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello, I'm Jordan.", "Sure, call me Claude!"]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    response = await orch.reply(session.id, coo_id, "Rename yourself to Claude.")
    assert response == "Sure, call me Claude!"


@pytest.mark.asyncio
async def test_reply_appends_to_conversation_history(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(side_effect=["Hello, I'm Jordan.", "Sure, noted!"])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.reply(session.id, coo_id, "Change my name.")
    rows = (await async_session.exec(select(MessageTable))).all()  # type: ignore[call-overload]
    # context inject + LLM response + user message + LLM response = 4
    assert len(rows) >= 2


@pytest.mark.asyncio
async def test_start_agent_conversation_resumes_in_progress_record(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello, I'm Jordan.", "Resuming our conversation."]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)

    # Get conversation ID and message count
    rows_before = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    coo_rec_before = next(r for r in rows_before if r.root_agent_id == coo_id)
    conv_id_before = coo_rec_before.active_conversation_id
    msg_count_before = len(
        (await async_session.exec(select(MessageTable))).all()  # type: ignore[call-overload]
    )

    # Call start_agent_conversation again (in_progress resume)
    response = await orch.start_agent_conversation(session.id, coo_id)

    assert response == "Resuming our conversation."
    assert response != ""

    # conversation_id must not have changed
    rows_after = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    coo_rec_after = next(r for r in rows_after if r.root_agent_id == coo_id)
    assert coo_rec_after.active_conversation_id == conv_id_before

    # At least one new message added
    msg_count_after = len(
        (await async_session.exec(select(MessageTable))).all()  # type: ignore[call-overload]
    )
    assert msg_count_after > msg_count_before


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_current_agent_opens_next_subagent(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    n1_id = mini_org["n1_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello, I'm Jordan.",
            "Here is my summary.",
            '{"agent_updates": []}',
            "Hello, I'm Alex.",
            "Hello, I'm Sam.",
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    await orch.start_agent_conversation(session.id, n1_id)
    response = await orch.complete_current_agent(session.id, n1_id)
    assert response == "Hello, I'm Sam."


@pytest.mark.asyncio
async def test_complete_current_agent_updates_navigation_stack(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    n1_id = mini_org["n1_id"]
    n2_id = mini_org["n2_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello, I'm Jordan.",
            "Here is my summary.",
            '{"agent_updates": []}',
            "Hello, I'm Alex.",
            "Hello, I'm Sam.",
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    await orch.start_agent_conversation(session.id, n1_id)
    await orch.complete_current_agent(session.id, n1_id)
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    n1_rec = next(r for r in rows if r.root_agent_id == n1_id)
    assert json.loads(n1_rec.navigation_stack) == [n1_id, n2_id]


@pytest.mark.asyncio
async def test_complete_current_agent_closes_current_agent_state(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    n1_id = mini_org["n1_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello, I'm Jordan.",
            "Here is my summary.",
            '{"agent_updates": []}',
            "Hello, I'm Alex.",
            "Hello, I'm Sam.",
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    await orch.start_agent_conversation(session.id, n1_id)
    await orch.complete_current_agent(session.id, n1_id)
    # After opening N-2, N-1 reverts to PAUSED
    n1_state = await async_session.get(AgentStateTable, n1_id)
    assert n1_state is not None
    assert n1_state.status == AgentStatus.PAUSED


@pytest.mark.asyncio
async def test_complete_current_agent_opens_next_agent_state(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    n1_id = mini_org["n1_id"]
    n2_id = mini_org["n2_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello, I'm Jordan.",
            "Here is my summary.",
            '{"agent_updates": []}',
            "Hello, I'm Alex.",
            "Hello, I'm Sam.",
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    await orch.start_agent_conversation(session.id, n1_id)
    await orch.complete_current_agent(session.id, n1_id)
    n2_state = await async_session.get(AgentStateTable, n2_id)
    assert n2_state is not None
    assert n2_state.status == AgentStatus.IN_MEETING_1ON1


@pytest.mark.asyncio
async def test_complete_current_agent_returns_root_summary_when_subtree_done(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    n1_id = mini_org["n1_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello, I'm Jordan.",
            "Here is my summary.",
            '{"agent_updates": []}',
            "Hello, I'm Alex.",
            "Hello, I'm Sam.",
            "Here is the Finance team summary.",
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    await orch.start_agent_conversation(session.id, n1_id)
    await orch.complete_current_agent(session.id, n1_id)  # opens N-2
    response = await orch.complete_current_agent(session.id, n1_id)  # N-2 is leaf
    assert response == "Here is the Finance team summary."


@pytest.mark.asyncio
async def test_complete_current_agent_navigation_stack_empty_when_subtree_done(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    n1_id = mini_org["n1_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello, I'm Jordan.",
            "Here is my summary.",
            '{"agent_updates": []}',
            "Hello, I'm Alex.",
            "Hello, I'm Sam.",
            "Finance team summary.",
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    await orch.start_agent_conversation(session.id, n1_id)
    await orch.complete_current_agent(session.id, n1_id)
    await orch.complete_current_agent(session.id, n1_id)
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    n1_rec = next(r for r in rows if r.root_agent_id == n1_id)
    assert json.loads(n1_rec.navigation_stack) == []


@pytest.mark.asyncio
async def test_complete_current_agent_leaf_n1_returns_summary_immediately(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    coo_only_org: dict[str, str],
) -> None:
    """COO-only org re-used: leaf N-1 pattern — first complete returns summary."""
    coo_id = coo_only_org["coo_id"]
    mock_complete = AsyncMock(side_effect=["Hello, I'm Jordan.", "Here is my summary."])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    response = await orch.complete_current_agent(session.id, coo_id)
    assert response == "Here is my summary."
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    coo_rec = next(r for r in rows if r.root_agent_id == coo_id)
    assert json.loads(coo_rec.navigation_stack) == []


@pytest.mark.asyncio
async def test_complete_current_agent_coo_returns_summary(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello, I'm Jordan.", "Here is my COO summary."]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    response = await orch.complete_current_agent(session.id, coo_id)
    assert response == "Here is my COO summary."
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    coo_rec = next(r for r in rows if r.root_agent_id == coo_id)
    assert json.loads(coo_rec.navigation_stack) == []


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_team_calls_extraction_llm(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello, I'm Jordan.",
            "Here is my summary.",
            '{"agent_updates": []}',
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    assert mock_complete.call_count == 3


@pytest.mark.asyncio
async def test_validate_team_applies_name_update(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": coo_id,
                    "fields": {"name": "Robin"},
                    "skills_to_add": [],
                    "skills_to_remove": [],
                    "skills_to_update": [],
                }
            ]
        }
    )
    mock_complete = AsyncMock(side_effect=["Hello.", "Summary.", extraction])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    spec_row = await async_session.get(AgentSpecTable, coo_id)
    assert spec_row is not None
    assert spec_row.name == "Robin"


@pytest.mark.asyncio
async def test_validate_team_marks_record_validated(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello.", "Summary.", '{"agent_updates": []}']
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    coo_rec = next(r for r in rows if r.root_agent_id == coo_id)
    assert coo_rec.status == "validated"


@pytest.mark.asyncio
async def test_validate_team_reverts_visited_agents_to_paused(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    n1_id = mini_org["n1_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello, I'm Jordan.",
            "Here is my summary.",
            '{"agent_updates": []}',
            "Hello, I'm Alex.",
            "Hello, I'm Sam.",
            "Finance team summary.",
            '{"agent_updates": []}',
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    await orch.start_agent_conversation(session.id, n1_id)
    await orch.complete_current_agent(session.id, n1_id)
    await orch.complete_current_agent(session.id, n1_id)
    await orch.validate_team(session.id, n1_id)
    n1_state = await async_session.get(AgentStateTable, n1_id)
    assert n1_state is not None
    # Both COO and N-1 are now VALIDATED → go_live fires → agents become IDLE
    assert n1_state.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_validate_team_triggers_go_live_when_all_records_done(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    coo_only_org: dict[str, str],
) -> None:
    coo_id = coo_only_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello.", "Summary.", '{"agent_updates": []}']
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    spec_row = await async_session.get(AgentSpecTable, coo_id)
    assert spec_row is not None
    assert spec_row.is_paused is False


@pytest.mark.asyncio
async def test_validate_team_no_go_live_when_records_pending(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello.", "Summary.", '{"agent_updates": []}']
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    # N-1 record is still pending
    n1_spec = await async_session.get(AgentSpecTable, mini_org["n1_id"])
    assert n1_spec is not None
    assert n1_spec.is_paused is True


# ---------------------------------------------------------------------------
# Skip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skip_agent_marks_record_skipped(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.skip_agent(session.id, coo_id)
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    coo_rec = next(r for r in rows if r.root_agent_id == coo_id)
    assert coo_rec.status == "skipped"


@pytest.mark.asyncio
async def test_skip_agent_returns_subtree_summary(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    result = await orch.skip_agent(session.id, coo_id)
    assert "Jordan" in str(result)


@pytest.mark.asyncio
async def test_skip_agent_reverts_active_agent_state_to_paused(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(return_value="Hello, I'm Jordan.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.skip_agent(session.id, coo_id)
    state = await async_session.get(AgentStateTable, coo_id)
    assert state is not None
    assert state.status == AgentStatus.PAUSED


@pytest.mark.asyncio
async def test_skip_all_marks_all_records_skipped(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.skip_all(session.id)
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    assert all(r.status == "skipped" for r in rows)


@pytest.mark.asyncio
async def test_skip_all_triggers_go_live(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.skip_all(session.id)
    spec_rows = (await async_session.exec(select(AgentSpecTable))).all()  # type: ignore[call-overload]
    assert all(r.is_paused is False for r in spec_rows)


# ---------------------------------------------------------------------------
# Go-live
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_go_live_sets_all_is_paused_false(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    coo_only_org: dict[str, str],
) -> None:
    coo_id = coo_only_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello.", "Summary.", '{"agent_updates": []}']
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    rows = (await async_session.exec(select(AgentSpecTable))).all()  # type: ignore[call-overload]
    assert all(r.is_paused is False for r in rows)


@pytest.mark.asyncio
async def test_go_live_sets_all_states_idle(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    coo_only_org: dict[str, str],
) -> None:
    coo_id = coo_only_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello.", "Summary.", '{"agent_updates": []}']
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    rows = (await async_session.exec(select(AgentStateTable))).all()  # type: ignore[call-overload]
    assert all(r.status == AgentStatus.IDLE for r in rows)


@pytest.mark.asyncio
async def test_go_live_sets_session_completed_at(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    coo_only_org: dict[str, str],
) -> None:
    coo_id = coo_only_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello.", "Summary.", '{"agent_updates": []}']
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    sess_row = await async_session.get(ValidationSessionTable, session.id)
    assert sess_row is not None
    assert sess_row.completed_at is not None


# ---------------------------------------------------------------------------
# Apply updates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_agent_updates_modifies_name(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": coo_id,
                    "fields": {"name": "Robin"},
                    "skills_to_add": [],
                    "skills_to_remove": [],
                    "skills_to_update": [],
                }
            ]
        }
    )
    mock_complete = AsyncMock(side_effect=["Hello.", "Summary.", extraction])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    spec_row = await async_session.get(AgentSpecTable, coo_id)
    assert spec_row is not None
    assert spec_row.name == "Robin"


@pytest.mark.asyncio
async def test_apply_agent_updates_adds_skill(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": coo_id,
                    "fields": {},
                    "skills_to_add": [
                        {
                            "name": "New Skill",
                            "description": "A brand new skill.",
                            "inputs": [],
                            "outputs": [],
                            "requires_human_review": False,
                        }
                    ],
                    "skills_to_remove": [],
                    "skills_to_update": [],
                }
            ]
        }
    )
    mock_complete = AsyncMock(side_effect=["Hello.", "Summary.", extraction])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    skill_rows = (await async_session.exec(select(SkillTable))).all()  # type: ignore[call-overload]
    skill_names = [s.name for s in skill_rows]
    assert "New Skill" in skill_names
    spec_row = await async_session.get(AgentSpecTable, coo_id)
    assert spec_row is not None
    skill_ids = json.loads(spec_row.skill_ids)
    new_skill = next(s for s in skill_rows if s.name == "New Skill")
    assert new_skill.id in skill_ids


@pytest.mark.asyncio
async def test_apply_agent_updates_removes_skill(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": coo_id,
                    "fields": {},
                    "skills_to_add": [],
                    "skills_to_remove": ["Synthesis"],
                    "skills_to_update": [],
                }
            ]
        }
    )
    mock_complete = AsyncMock(side_effect=["Hello.", "Summary.", extraction])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    skill_rows = (await async_session.exec(select(SkillTable))).all()  # type: ignore[call-overload]
    skill_names = [s.name for s in skill_rows]
    assert "Synthesis" not in skill_names
    spec_row = await async_session.get(AgentSpecTable, coo_id)
    assert spec_row is not None
    skill_ids = json.loads(spec_row.skill_ids)
    assert not any(s.id in skill_ids for s in skill_rows if s.name == "Synthesis")


@pytest.mark.asyncio
async def test_apply_agent_updates_updates_skill_description(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": coo_id,
                    "fields": {},
                    "skills_to_add": [],
                    "skills_to_remove": [],
                    "skills_to_update": [
                        {
                            "name": "Synthesis",
                            "fields": {"description": "Updated description."},
                        }
                    ],
                }
            ]
        }
    )
    mock_complete = AsyncMock(side_effect=["Hello.", "Summary.", extraction])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    skill_rows = (await async_session.exec(select(SkillTable))).all()  # type: ignore[call-overload]
    synthesis = next(s for s in skill_rows if s.name == "Synthesis")
    assert synthesis.description == "Updated description."


@pytest.mark.asyncio
async def test_apply_agent_updates_drops_frozen_fields_silently(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": coo_id,
                    "fields": {"domain": "Forbidden", "level": 99, "parent_id": "x"},
                    "skills_to_add": [],
                    "skills_to_remove": [],
                    "skills_to_update": [],
                }
            ]
        }
    )
    mock_complete = AsyncMock(side_effect=["Hello.", "Summary.", extraction])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    spec_row = await async_session.get(AgentSpecTable, coo_id)
    assert spec_row is not None
    assert spec_row.domain is None
    assert spec_row.level == 0
    assert spec_row.parent_id is None


@pytest.mark.asyncio
async def test_apply_agent_updates_drops_invalid_visual_character(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": coo_id,
                    "fields": {"visual_character": "invalid_character"},
                    "skills_to_add": [],
                    "skills_to_remove": [],
                    "skills_to_update": [],
                }
            ]
        }
    )
    mock_complete = AsyncMock(side_effect=["Hello.", "Summary.", extraction])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    spec_row = await async_session.get(AgentSpecTable, coo_id)
    assert spec_row is not None
    assert spec_row.visual_character == "character_suit"


@pytest.mark.asyncio
async def test_apply_agent_updates_clamps_scheduler_interval_low(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": coo_id,
                    "fields": {"scheduler_interval_seconds": 299},
                    "skills_to_add": [],
                    "skills_to_remove": [],
                    "skills_to_update": [],
                }
            ]
        }
    )
    mock_complete = AsyncMock(side_effect=["Hello.", "Summary.", extraction])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    spec_row = await async_session.get(AgentSpecTable, coo_id)
    assert spec_row is not None
    assert spec_row.scheduler_interval_seconds == 300


@pytest.mark.asyncio
async def test_apply_agent_updates_clamps_scheduler_interval_high(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": coo_id,
                    "fields": {"scheduler_interval_seconds": 9999},
                    "skills_to_add": [],
                    "skills_to_remove": [],
                    "skills_to_update": [],
                }
            ]
        }
    )
    mock_complete = AsyncMock(side_effect=["Hello.", "Summary.", extraction])
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    spec_row = await async_session.get(AgentSpecTable, coo_id)
    assert spec_row is not None
    assert spec_row.scheduler_interval_seconds == 3600


# ---------------------------------------------------------------------------
# Extraction retries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extraction_retry_on_invalid_json_succeeds(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello.",
            "Summary.",
            "not json",
            "still not json",
            '{"agent_updates": []}',
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    coo_rec = next(r for r in rows if r.root_agent_id == coo_id)
    assert coo_rec.status == "validated"


@pytest.mark.asyncio
async def test_extraction_raises_after_max_retries(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=[
            "Hello.",
            "Summary.",
            "bad json 1",
            "bad json 2",
            "bad json 3",
        ]
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    with pytest.raises(TeamSetupError):
        await orch.validate_team(session.id, coo_id)


# ---------------------------------------------------------------------------
# COO-only org
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coo_only_org_start_session_creates_one_record(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    coo_only_org: dict[str, str],
) -> None:
    mock_complete = AsyncMock(return_value="Hello.")
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    await orch.start_session()
    rows = (await async_session.exec(select(AgentValidationRecordTable))).all()  # type: ignore[call-overload]
    assert len(rows) == 1
    assert rows[0].root_agent_id == coo_only_org["coo_id"]


@pytest.mark.asyncio
async def test_coo_only_org_validate_team_triggers_go_live(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    coo_only_org: dict[str, str],
) -> None:
    coo_id = coo_only_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello.", "Summary.", '{"agent_updates": []}']
    )
    orch = _make_orchestrator(async_session, stub_prompt_loader, mock_complete)
    session = await orch.start_session()
    await orch.start_agent_conversation(session.id, coo_id)
    await orch.complete_current_agent(session.id, coo_id)
    await orch.validate_team(session.id, coo_id)
    spec_row = await async_session.get(AgentSpecTable, coo_id)
    assert spec_row is not None
    assert spec_row.is_paused is False
