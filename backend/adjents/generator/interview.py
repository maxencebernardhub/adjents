"""Generator Agent interview orchestration."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.db.convert import (
    business_context_to_table,
    conversation_from_table,
    conversation_to_table,
    message_from_table,
    message_to_table,
)
from adjents.db.tables import ConversationTable, MessageTable
from adjents.generator.models import BusinessContext
from adjents.llm.anthropic_client import AnthropicClient
from adjents.messaging.models import Conversation, Message
from adjents.prompts.loader import PromptLoader

_GENERATOR_ID = "generator"
_MAX_RETRIES = 3
_KICKOFF = "Hello."


@dataclass
class InterviewResponse:
    message: str
    ready_to_generate: bool
    missing_mandatory_info: list[str]


class InterviewError(Exception): ...


class GeneratorInterview:
    def __init__(
        self,
        client: AnthropicClient,
        prompt_loader: PromptLoader,
        session: AsyncSession,
    ) -> None:
        self._client = client
        self._loader = prompt_loader
        self._session = session
        self._conversation: Conversation | None = None
        self._messages: list[Message] = []

    async def start(self) -> str:
        system = self._loader.get("generator/interview").content
        raw = await self._call_llm(system, [{"role": "user", "content": _KICKOFF}])
        response = self._parse_response(raw)

        self._conversation = Conversation(
            id=str(uuid.uuid4()),
            participant_agents=[_GENERATOR_ID, "user"],
            message_ids=[],
            started_at=datetime.now(UTC),
        )
        kickoff = self._make_message("user", _GENERATOR_ID, _KICKOFF)
        agent = self._make_message(_GENERATOR_ID, "user", raw)
        await self._persist_messages([kickoff, agent])
        return response.message

    async def reply(self, user_message: str) -> InterviewResponse:
        if self._conversation is None:
            raise InterviewError("Interview not started. Call start() first.")

        user_msg = self._make_message("user", _GENERATOR_ID, user_message)
        await self._persist_messages([user_msg])

        system = self._loader.get("generator/interview").content
        raw = await self._call_llm(system, self._build_llm_messages())
        response = self._parse_response(raw)

        agent_msg = self._make_message(_GENERATOR_ID, "user", raw)
        await self._persist_messages([agent_msg])

        if response.ready_to_generate:
            bc = await self._build_business_context()
            self._session.add(business_context_to_table(bc))
            await self._session.commit()

        return response

    async def resume(self, conversation_id: str) -> None:
        result = await self._session.exec(
            select(ConversationTable).where(ConversationTable.id == conversation_id)
        )
        row = result.first()
        if row is None:
            raise InterviewError(f"Conversation {conversation_id!r} not found.")
        self._conversation = conversation_from_table(row)
        self._messages = []
        for msg_id in self._conversation.message_ids:
            msg_result = await self._session.exec(
                select(MessageTable).where(MessageTable.id == msg_id)
            )
            msg_row = msg_result.first()
            if msg_row is not None:
                self._messages.append(message_from_table(msg_row))

    async def _call_llm(self, system: str, messages: list[dict[str, str]]) -> str:
        current = list(messages)
        last_raw = ""
        for attempt in range(_MAX_RETRIES):
            last_raw = await self._client.complete(current, system=system)
            try:
                json.loads(last_raw)
                return last_raw
            except json.JSONDecodeError:
                if attempt < _MAX_RETRIES - 1:
                    current = [
                        *current,
                        {"role": "assistant", "content": last_raw},
                        {
                            "role": "user",
                            "content": "Respond with a valid JSON object only.",
                        },
                    ]
        raise InterviewError(
            f"LLM failed to return valid JSON after {_MAX_RETRIES} attempts. "
            f"Last response: {last_raw[:200]!r}"
        )

    def _parse_response(self, raw: str) -> InterviewResponse:
        try:
            data = json.loads(raw)
            return InterviewResponse(
                message=str(data["message"]),
                ready_to_generate=bool(data.get("ready_to_generate", False)),
                missing_mandatory_info=list(data.get("missing_mandatory_info", [])),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise InterviewError(f"Invalid LLM response: {exc}") from exc

    def _build_llm_messages(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for msg in self._messages:
            if msg.from_agent == "user":
                result.append({"role": "user", "content": msg.content})
            elif msg.from_agent == _GENERATOR_ID:
                result.append({"role": "assistant", "content": msg.content})
        return result

    def _make_message(self, from_agent: str, to_agent: str, content: str) -> Message:
        return Message(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            metadata={},
            parent_message_id=None,
            created_at=datetime.now(UTC),
        )

    async def _persist_messages(self, messages: list[Message]) -> None:
        assert self._conversation is not None
        new_ids = list(self._conversation.message_ids)
        for msg in messages:
            self._messages.append(msg)
            new_ids.append(msg.id)
            self._session.add(message_to_table(msg))

        self._conversation = Conversation(
            id=self._conversation.id,
            participant_agents=self._conversation.participant_agents,
            message_ids=new_ids,
            started_at=self._conversation.started_at,
        )
        result = await self._session.exec(
            select(ConversationTable).where(
                ConversationTable.id == self._conversation.id
            )
        )
        row = result.first()
        if row is None:
            self._session.add(conversation_to_table(self._conversation))
        else:
            row.message_ids = json.dumps(new_ids)
        await self._session.commit()

    async def _build_business_context(self) -> BusinessContext:
        assert self._conversation is not None
        system = self._loader.get("generator/extract_business_context").content
        transcript = self._build_transcript()
        raw = await self._client.complete(
            [{"role": "user", "content": transcript}], system=system
        )
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InterviewError(
                "BusinessContext extraction failed: invalid JSON"
            ) from exc
        data.pop("id", None)
        data.pop("conversation_id", None)
        data.pop("created_at", None)
        return BusinessContext(
            id=str(uuid.uuid4()),
            conversation_id=self._conversation.id,
            created_at=datetime.now(UTC),
            **data,
        )

    def _build_transcript(self) -> str:
        parts: list[str] = []
        for msg in self._messages:
            if msg.from_agent == "user":
                parts.append(f"User: {msg.content}")
            elif msg.from_agent == _GENERATOR_ID:
                try:
                    parsed = json.loads(msg.content)
                    text = str(parsed.get("message", msg.content))
                except json.JSONDecodeError:
                    text = msg.content
                parts.append(f"Agent: {text}")
        return "\n\n".join(parts)
