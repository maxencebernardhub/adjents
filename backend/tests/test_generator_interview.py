"""Tests for generator.interview: GeneratorInterview."""

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.db.tables import BusinessContextTable, ConversationTable, MessageTable
from adjents.generator.interview import GeneratorInterview, InterviewError
from adjents.llm.anthropic_client import AnthropicClient
from adjents.prompts.loader import PromptLoader

# --- Test constants ---

_AGENT_RESPONSE = json.dumps(
    {
        "message": "Hello! I am the Generator Agent. Tell me about your business.",
        "ready_to_generate": False,
        "missing_mandatory_info": [
            "identity",
            "core_activity",
            "delegation",
            "legal_status",
        ],
    }
)

_DONE_RESPONSE = json.dumps(
    {
        "message": "Your team is ready to be generated!",
        "ready_to_generate": True,
        "missing_mandatory_info": [],
    }
)

_EXTRACT_RESPONSE = json.dumps(
    {
        "business_name": "Acme",
        "founder_name": "Alex Chen",
        "language": "en",
        "core_activity": "UX designer",
        "legal_status": "LLC",
        "target_clients": ["Startups"],
        "domains_with_human_coverage": [],
        "domains_to_staff": ["Finance", "Sales"],
        "tasks_to_delegate": ["Invoicing", "Prospecting"],
        "tasks_user_keeps": ["UX design"],
        "financial_goals": "100k/year",
        "existing_tools": ["Gmail"],
        "autonomy_preference": "High autonomy except external comms",
        "work_hours": "09:00-18:00",
        "additional_context": None,
    }
)

# --- Fixtures ---


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock(spec=AnthropicClient)
    client.complete = AsyncMock(return_value=_AGENT_RESPONSE)
    return client


@pytest.fixture
def loader(tmp_path: Path) -> PromptLoader:
    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "generator").mkdir(parents=True)
    (prompts_dir / "generator" / "interview.md").write_text(
        "---\nversion: 1\n---\n# Interview\nConduct the interview."
    )
    (prompts_dir / "generator" / "extract_business_context.md").write_text(
        "---\nversion: 1\n---\n# Extract\nExtract the JSON."
    )
    return PromptLoader(prompts_dir)


@pytest.fixture
def interview(
    mock_client: MagicMock,
    loader: PromptLoader,
    async_session: AsyncSession,
) -> Generator[GeneratorInterview]:
    yield GeneratorInterview(mock_client, loader, async_session)


# --- start() ---


async def test_start_returns_agent_message_text(
    interview: GeneratorInterview,
) -> None:
    result = await interview.start()
    assert result == "Hello! I am the Generator Agent. Tell me about your business."


async def test_start_creates_conversation_in_db(
    interview: GeneratorInterview,
    async_session: AsyncSession,
) -> None:
    await interview.start()
    rows = (await async_session.exec(select(ConversationTable))).all()
    assert len(rows) == 1
    assert rows[0].participant_agents == '["generator", "user"]'


async def test_start_persists_two_messages(
    interview: GeneratorInterview,
    async_session: AsyncSession,
) -> None:
    await interview.start()
    rows = (await async_session.exec(select(MessageTable))).all()
    assert len(rows) == 2
    roles = {r.from_agent for r in rows}
    assert roles == {"user", "generator"}


# --- reply() ---


async def test_reply_returns_interview_response(
    interview: GeneratorInterview,
) -> None:
    await interview.start()
    response = await interview.reply("Hi, I am Alex.")
    assert (
        response.message
        == "Hello! I am the Generator Agent. Tell me about your business."
    )
    assert response.ready_to_generate is False
    assert isinstance(response.missing_mandatory_info, list)


async def test_reply_persists_user_and_agent_messages(
    interview: GeneratorInterview,
    async_session: AsyncSession,
) -> None:
    await interview.start()
    await interview.reply("Hi, I am Alex.")
    rows = (await async_session.exec(select(MessageTable))).all()
    # start: 2 messages, reply: 2 more (user + agent)
    assert len(rows) == 4


async def test_reply_updates_conversation_message_ids(
    interview: GeneratorInterview,
    async_session: AsyncSession,
) -> None:
    await interview.start()
    await interview.reply("Hi, I am Alex.")
    rows = (await async_session.exec(select(ConversationTable))).all()
    assert len(rows) == 1
    ids = json.loads(rows[0].message_ids)
    assert len(ids) == 4


# --- BusinessContext persistence ---


async def test_reply_ready_to_generate_persists_business_context(
    mock_client: MagicMock,
    loader: PromptLoader,
    async_session: AsyncSession,
) -> None:
    mock_client.complete = AsyncMock(
        side_effect=[_AGENT_RESPONSE, _DONE_RESPONSE, _EXTRACT_RESPONSE]
    )
    iv = GeneratorInterview(mock_client, loader, async_session)
    await iv.start()
    response = await iv.reply("I am ready to build my team.")

    assert response.ready_to_generate is True
    rows = (await async_session.exec(select(BusinessContextTable))).all()
    assert len(rows) == 1
    assert rows[0].founder_name == "Alex Chen"


async def test_interrupted_interview_no_business_context(
    interview: GeneratorInterview,
    async_session: AsyncSession,
) -> None:
    await interview.start()
    await interview.reply("Hi, I am Alex.")
    rows = (await async_session.exec(select(BusinessContextTable))).all()
    assert len(rows) == 0


# --- resume() ---


async def test_resume_reloads_conversation_and_messages(
    mock_client: MagicMock,
    loader: PromptLoader,
    async_session: AsyncSession,
) -> None:
    mock_client.complete = AsyncMock(return_value=_AGENT_RESPONSE)
    iv1 = GeneratorInterview(mock_client, loader, async_session)
    await iv1.start()
    await iv1.reply("Hi, I am Alex.")
    conv_id = iv1._conversation.id  # type: ignore[union-attr]

    iv2 = GeneratorInterview(mock_client, loader, async_session)
    await iv2.resume(conv_id)

    assert iv2._conversation is not None
    assert iv2._conversation.id == conv_id
    assert len(iv2._messages) == 4


async def test_resume_unknown_conversation_raises(
    interview: GeneratorInterview,
) -> None:
    with pytest.raises(InterviewError, match="not found"):
        await interview.resume("nonexistent-id")


# --- Retry logic ---


async def test_retry_invalid_json_succeeds_on_third_attempt(
    mock_client: MagicMock,
    loader: PromptLoader,
    async_session: AsyncSession,
) -> None:
    mock_client.complete = AsyncMock(
        side_effect=["not json", "still not json", _AGENT_RESPONSE]
    )
    iv = GeneratorInterview(mock_client, loader, async_session)
    result = await iv.start()
    assert result == "Hello! I am the Generator Agent. Tell me about your business."


async def test_retry_all_failed_raises_interview_error(
    mock_client: MagicMock,
    loader: PromptLoader,
    async_session: AsyncSession,
) -> None:
    mock_client.complete = AsyncMock(return_value="not valid json at all")
    iv = GeneratorInterview(mock_client, loader, async_session)
    with pytest.raises(InterviewError, match="valid JSON"):
        await iv.start()
