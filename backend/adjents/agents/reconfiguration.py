"""Direct agent reconfiguration (Mode 2) — post-generation."""

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.agents.models import AgentSpec, AgentStatus, Skill
from adjents.db.tables import (
    AgentSpecTable,
    AgentStateTable,
    MessageTable,
    SkillTable,
)
from adjents.errors import TeamSetupError
from adjents.llm.anthropic_client import AnthropicClient
from adjents.llm.types import Effort
from adjents.prompts.loader import PromptLoader
from adjents.utils.agent_context import _build_agent_context_message

_log = logging.getLogger(__name__)
_FROZEN_FIELDS = frozenset({"domain", "level", "parent_id"})
_INTERVAL_MIN = 300
_INTERVAL_MAX = 3600


class AgentReconfiguration:
    _MAX_RETRIES: int = 3
    # Interim: moves into the router's per-role table in step 10 (ADR 0012).
    _CONVERSATION_EFFORT: Effort = "medium"
    _EXTRACTION_EFFORT: Effort = "medium"

    def __init__(
        self,
        agent_id: str,
        client: AnthropicClient,
        prompt_loader: PromptLoader,
        session: AsyncSession,
    ) -> None:
        self._agent_id = agent_id
        self._client = client
        self._prompts = prompt_loader
        self._session = session
        self._messages: list[dict[str, str]] = []
        self._conv_id: str = str(uuid4())
        self._prior_status: AgentStatus = AgentStatus.PAUSED

    async def start(self) -> str:
        from adjents.db.convert import agent_spec_from_table

        spec_row = await self._session.get(AgentSpecTable, self._agent_id)
        if spec_row is None:
            raise ValueError(f"Agent {self._agent_id} not found.")
        agent = agent_spec_from_table(spec_row)

        skills = await self._load_skills(agent.skill_ids)
        direct_reports, reports_skills = await self._load_direct_reports(agent)

        state_row = await self._session.get(AgentStateTable, self._agent_id)
        if state_row is not None:
            self._prior_status = AgentStatus(state_row.status)
            state_row.status = str(AgentStatus.IN_MEETING_1ON1)
            state_row.updated_at = datetime.now(UTC).isoformat()
            self._session.add(state_row)
            await self._session.commit()

        context_msg = _build_agent_context_message(
            agent, skills, direct_reports, reports_skills
        )
        intro_prompt = self._prompts.get("agent/intro")
        messages: list[dict[str, str]] = [{"role": "user", "content": context_msg}]
        response = await self._client.complete(
            messages, effort=self._CONVERSATION_EFFORT, system=intro_prompt.content
        )
        messages.append({"role": "assistant", "content": response})
        self._messages = messages

        await self._append_message("user", context_msg)
        await self._append_message("assistant", response)

        return response

    async def reply(self, message: str) -> str:
        self._messages.append({"role": "user", "content": message})
        intro_prompt = self._prompts.get("agent/intro")
        response = await self._client.complete(
            self._messages,
            effort=self._CONVERSATION_EFFORT,
            system=intro_prompt.content,
        )
        self._messages.append({"role": "assistant", "content": response})
        await self._append_message("user", message)
        await self._append_message("assistant", response)
        return response

    async def apply_changes(self) -> None:
        transcript = self._build_transcript()
        updates = await self._call_extraction_llm([transcript])
        await self._apply_agent_updates(updates.get("agent_updates", []))

        state_row = await self._session.get(AgentStateTable, self._agent_id)
        if state_row is not None:
            state_row.status = str(self._prior_status)
            state_row.updated_at = datetime.now(UTC).isoformat()
            self._session.add(state_row)
            await self._session.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_transcript(self) -> str:
        lines: list[str] = [f"---AGENT:{self._agent_id}---"]
        for msg in self._messages:
            role = "User" if msg["role"] == "user" else "Agent"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    async def _call_extraction_llm(self, conversations: list[str]) -> dict[str, Any]:
        extract_prompt = self._prompts.get("agent/extract_agent_adjustments")
        transcript = "\n\n".join(conversations)
        messages: list[dict[str, str]] = [{"role": "user", "content": transcript}]
        last_error = ""
        for attempt in range(self._MAX_RETRIES):
            if attempt > 0:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your response was not valid JSON (error: {last_error}). "
                            "Return only a valid JSON object, nothing else."
                        ),
                    }
                )
            raw = await self._client.complete(
                messages, effort=self._EXTRACTION_EFFORT, system=extract_prompt.content
            )
            try:
                return json.loads(raw)  # type: ignore[no-any-return]
            except json.JSONDecodeError as exc:
                last_error = str(exc)
                messages.append({"role": "assistant", "content": raw})
        # V3: raise TeamSetupError (not ValueError) on retry exhaustion
        raise TeamSetupError(
            f"Extraction LLM failed after {self._MAX_RETRIES} attempts: {last_error}"
        )

    async def _apply_agent_updates(self, updates: list[dict[str, Any]]) -> None:
        from adjents.generator.org_generation import VALID_VISUAL_CHARACTERS

        for update in updates:
            agent_id: str = update.get("agent_id", "")
            fields: dict[str, Any] = update.get("fields", {})
            skills_to_add: list[dict[str, Any]] = update.get("skills_to_add", [])
            skills_to_remove: list[str] = update.get("skills_to_remove", [])
            skills_to_update: list[dict[str, Any]] = update.get("skills_to_update", [])

            spec_row = await self._session.get(AgentSpecTable, agent_id)
            if spec_row is None:
                continue

            for key, value in fields.items():
                if key in _FROZEN_FIELDS:
                    # G1: warn when frozen fields are dropped
                    _log.warning("Dropping frozen field %r for agent %s", key, agent_id)
                    continue
                if key == "visual_character" and value not in VALID_VISUAL_CHARACTERS:
                    _log.warning("Dropping invalid visual_character: %r", value)
                    continue
                if key == "scheduler_interval_seconds":
                    raw_val = int(value)
                    clamped = max(_INTERVAL_MIN, min(_INTERVAL_MAX, raw_val))
                    if clamped != raw_val:
                        _log.warning(
                            "scheduler_interval_seconds clamped to %d", clamped
                        )
                    value = clamped
                setattr(spec_row, key, value)
            self._session.add(spec_row)

            current_skill_ids: list[str] = json.loads(spec_row.skill_ids)

            for skill_data in skills_to_add:
                new_id = str(uuid4())
                skill_row = SkillTable(
                    id=new_id,
                    name=skill_data["name"],
                    description=skill_data.get("description", ""),
                    inputs=json.dumps(skill_data.get("inputs", [])),
                    outputs=json.dumps(skill_data.get("outputs", [])),
                    requires_human_review=bool(
                        skill_data.get("requires_human_review", False)
                    ),
                )
                self._session.add(skill_row)
                current_skill_ids.append(new_id)

            if skills_to_remove and current_skill_ids:
                existing_skills = (
                    await self._session.exec(
                        select(SkillTable).where(
                            SkillTable.id.in_(current_skill_ids)  # type: ignore[attr-defined]
                        )
                    )
                ).all()
                remove_ids: list[str] = []
                found_remove_names: set[str] = set()
                for s in existing_skills:
                    if s.name in skills_to_remove:
                        remove_ids.append(s.id)
                        found_remove_names.add(s.name)
                        await self._session.delete(s)
                # G2: warn for skill names not found during removal
                for name in skills_to_remove:
                    if name not in found_remove_names:
                        _log.warning(
                            "Skill %r not found for removal on agent %s", name, agent_id
                        )
                current_skill_ids = [
                    i for i in current_skill_ids if i not in remove_ids
                ]

            for su in skills_to_update:
                skill_name: str = su["name"]
                skill_fields: dict[str, Any] = su.get("fields", {})
                if not current_skill_ids:
                    # G2: warn when no skills exist to update
                    _log.warning(
                        "Skill %r not found for update on agent %s (no skills)",
                        skill_name,
                        agent_id,
                    )
                    continue
                s_row = (
                    await self._session.exec(
                        select(SkillTable).where(
                            SkillTable.id.in_(current_skill_ids),  # type: ignore[attr-defined]
                            SkillTable.name == skill_name,
                        )
                    )
                ).first()
                if s_row is not None:
                    for k, v in skill_fields.items():
                        if k in ("inputs", "outputs"):
                            setattr(s_row, k, json.dumps(v))
                        else:
                            setattr(s_row, k, v)
                    self._session.add(s_row)
                else:
                    # G2: warn when skill name not found for update
                    _log.warning(
                        "Skill %r not found for update on agent %s",
                        skill_name,
                        agent_id,
                    )

            spec_row.skill_ids = json.dumps(current_skill_ids)
            self._session.add(spec_row)

        await self._session.commit()

    async def _load_skills(self, skill_ids: list[str]) -> list[Skill]:
        from adjents.db.convert import skill_from_table

        if not skill_ids:
            return []
        rows = (
            await self._session.exec(
                select(SkillTable).where(
                    SkillTable.id.in_(skill_ids)  # type: ignore[attr-defined]
                )
            )
        ).all()
        return [skill_from_table(r) for r in rows]

    async def _load_direct_reports(
        self, agent: AgentSpec
    ) -> tuple[list[AgentSpec], dict[str, list[Skill]]]:
        from adjents.db.convert import agent_spec_from_table

        report_rows = (
            await self._session.exec(
                select(AgentSpecTable).where(AgentSpecTable.parent_id == agent.id)
            )
        ).all()
        reports: list[AgentSpec] = [agent_spec_from_table(r) for r in report_rows]
        reports_skills: dict[str, list[Skill]] = {}
        for report in reports:
            reports_skills[report.id] = await self._load_skills(report.skill_ids)
        return reports, reports_skills

    async def _append_message(self, role: str, content: str) -> None:
        from_agent = "user" if role == "user" else self._agent_id
        to_agent = self._agent_id if role == "user" else "user"
        self._session.add(
            MessageTable(
                id=str(uuid4()),
                from_agent=from_agent,
                to_agent=to_agent,
                content=content,
                metadata_json=json.dumps({"conv_id": self._conv_id}),
                parent_message_id=None,
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        await self._session.commit()
