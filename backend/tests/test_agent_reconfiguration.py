"""T5 tests: AgentReconfiguration — Mode 2 direct reconfiguration."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.agents.models import AgentStatus
from adjents.agents.reconfiguration import AgentReconfiguration
from adjents.db.tables import AgentSpecTable, AgentStateTable, MessageTable
from adjents.errors import TeamSetupError
from adjents.llm.anthropic_client import AnthropicClient
from adjents.llm.errors import LLMRefusalError
from adjents.prompts.loader import PromptLoader


def _make_reconf(
    agent_id: str,
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mock_complete: AsyncMock,
) -> AgentReconfiguration:
    client = MagicMock(spec=AnthropicClient)
    client.complete = mock_complete
    return AgentReconfiguration(agent_id, client, stub_prompt_loader, async_session)


@pytest.mark.asyncio
async def test_start_returns_opening_message(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(return_value="Hi, I'm Jordan the COO!")
    reconf = _make_reconf(coo_id, async_session, stub_prompt_loader, mock_complete)
    response = await reconf.start()
    assert response == "Hi, I'm Jordan the COO!"


@pytest.mark.asyncio
async def test_start_sets_agent_state_in_meeting(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(return_value="Hello.")
    reconf = _make_reconf(coo_id, async_session, stub_prompt_loader, mock_complete)
    await reconf.start()
    state = await async_session.get(AgentStateTable, coo_id)
    assert state is not None
    assert state.status == AgentStatus.IN_MEETING_1ON1


@pytest.mark.asyncio
async def test_reply_continues_conversation(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(side_effect=["Hello.", "Sure, noted!"])
    reconf = _make_reconf(coo_id, async_session, stub_prompt_loader, mock_complete)
    await reconf.start()
    rows_before = (await async_session.exec(select(MessageTable))).all()
    response = await reconf.reply("Rename yourself to Robin.")
    assert response == "Sure, noted!"
    rows_after = (await async_session.exec(select(MessageTable))).all()
    assert len(rows_after) > len(rows_before)


@pytest.mark.asyncio
async def test_apply_changes_calls_extraction_llm(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(side_effect=["Hello.", '{"agent_updates": []}'])
    reconf = _make_reconf(coo_id, async_session, stub_prompt_loader, mock_complete)
    await reconf.start()
    await reconf.apply_changes()
    assert mock_complete.call_count == 2


@pytest.mark.asyncio
async def test_apply_changes_updates_agent_spec(
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
    mock_complete = AsyncMock(side_effect=["Hello.", extraction])
    reconf = _make_reconf(coo_id, async_session, stub_prompt_loader, mock_complete)
    await reconf.start()
    await reconf.apply_changes()
    spec = await async_session.get(AgentSpecTable, coo_id)
    assert spec is not None
    assert spec.name == "Robin"


@pytest.mark.asyncio
async def test_apply_changes_restores_agent_state(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(side_effect=["Hello.", '{"agent_updates": []}'])
    reconf = _make_reconf(coo_id, async_session, stub_prompt_loader, mock_complete)
    await reconf.start()
    await reconf.apply_changes()
    state = await async_session.get(AgentStateTable, coo_id)
    assert state is not None
    assert state.status == AgentStatus.PAUSED


@pytest.mark.asyncio
async def test_leaf_agent_no_subtree_context(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    n2_id = mini_org["n2_id"]
    mock_complete = AsyncMock(return_value="Hi, I'm Sam!")
    reconf = _make_reconf(n2_id, async_session, stub_prompt_loader, mock_complete)
    await reconf.start()
    messages = (await async_session.exec(select(MessageTable))).all()
    user_msgs = [m for m in messages if m.from_agent == "user"]
    assert len(user_msgs) > 0
    assert "direct report" not in user_msgs[0].content.lower()


@pytest.mark.asyncio
async def test_extraction_raises_team_setup_error_after_max_retries(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    """V3: AgentReconfiguration must raise TeamSetupError on retry exhaustion."""
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello.", "bad json 1", "bad json 2", "bad json 3"]
    )
    reconf = _make_reconf(coo_id, async_session, stub_prompt_loader, mock_complete)
    await reconf.start()
    with pytest.raises(TeamSetupError):
        await reconf.apply_changes()


# ---------------------------------------------------------------------------
# LLM call contract (ADR 0012)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_every_llm_call_uses_medium_effort(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    mock_complete = AsyncMock(
        side_effect=["Hello.", "Sure, noted!", '{"agent_updates": []}']
    )
    reconf = _make_reconf(coo_id, async_session, stub_prompt_loader, mock_complete)
    await reconf.start()
    await reconf.reply("Please be more concise.")
    await reconf.apply_changes()
    efforts = [call.kwargs["effort"] for call in mock_complete.call_args_list]
    assert efforts == ["medium"] * 3


@pytest.mark.asyncio
async def test_extraction_refusal_propagates_without_retry(
    async_session: AsyncSession,
    stub_prompt_loader: PromptLoader,
    mini_org: dict[str, str],
) -> None:
    coo_id = mini_org["coo_id"]
    refusal = LLMRefusalError(model="m", category="general_harms", explanation=None)
    mock_complete = AsyncMock(side_effect=["Hello.", refusal])
    reconf = _make_reconf(coo_id, async_session, stub_prompt_loader, mock_complete)
    await reconf.start()
    with pytest.raises(LLMRefusalError):
        await reconf.apply_changes()
    assert mock_complete.call_count == 2
