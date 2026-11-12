"""Post-generation team setup: domain models and orchestration (Mode 1)."""

import json
import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.agents.models import AgentSpec, AgentStatus, Skill
from adjents.db.tables import (
    AgentSpecTable,
    AgentStateTable,
    AgentValidationRecordTable,
    MessageTable,
    SkillTable,
    ValidationSessionTable,
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


class AgentValidationStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATED = "validated"
    SKIPPED = "skipped"


class ValidationSession(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    id: str
    started_at: AwareDatetime
    completed_at: AwareDatetime | None
    skipped: bool


class AgentValidationRecord(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    id: str
    session_id: str
    root_agent_id: str
    status: AgentValidationStatus
    active_agent_id: str | None
    active_conversation_id: str | None
    navigation_stack: list[str]
    conversation_ids: list[str]
    visited_agent_ids: list[str]
    validated_at: AwareDatetime | None


# Re-export for backward compatibility with external importers.
__all__ = [
    "AgentValidationRecord",
    "AgentValidationStatus",
    "TeamSetupError",
    "TeamSetupOrchestrator",
    "ValidationSession",
    "_advance_traversal",
    "_build_agent_context_message",
]


# ---------------------------------------------------------------------------
# Pure helpers (no I/O)
# ---------------------------------------------------------------------------


def _advance_traversal(
    current_id: str,
    navigation_stack: list[str],
    visited_agent_ids: list[str],
    children_by_parent: dict[str, list[AgentSpec]],
) -> tuple[AgentSpec | None, list[str], list[str]]:
    """Advance depth-first traversal one step.

    Returns (next_agent, updated_stack, updated_visited).
    Returns (None, [], updated_visited) when the entire subtree is exhausted.

    children_by_parent is pre-loaded by the caller — pure, no DB access.
    Handles backtracking internally via while loop.
    """
    stack = list(navigation_stack)
    visited = list(visited_agent_ids)
    node_id = current_id
    while True:
        children = children_by_parent.get(node_id, [])
        unvisited = [c for c in children if c.id not in visited]
        if unvisited:
            next_agent = unvisited[0]
            stack.append(next_agent.id)
            return next_agent, stack, visited
        else:
            visited.append(node_id)
            stack.pop()
            if stack:
                node_id = stack[-1]
            else:
                return None, [], visited


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class TeamSetupOrchestrator:
    _MAX_RETRIES: int = 3
    # Interim: moves into the router's per-role table in step 10 (ADR 0012).
    _CONVERSATION_EFFORT: Effort = "medium"
    _EXTRACTION_EFFORT: Effort = "medium"

    def __init__(
        self,
        client: AnthropicClient,
        prompt_loader: PromptLoader,
        session: AsyncSession,
    ) -> None:
        self._client = client
        self._prompts = prompt_loader
        self._session = session
        # In-memory conversation state (same orchestrator instance across a session)
        self._conv_messages: dict[str, list[dict[str, str]]] = {}
        self._conv_agent: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def start_session(self) -> ValidationSession:
        from adjents.db.convert import (
            agent_validation_record_to_table,
            validation_session_to_table,
        )

        existing = await self.resume_session()
        if existing is not None:
            raise TeamSetupError("A validation session is already in progress.")

        session_id = str(uuid4())
        now = datetime.now(UTC)
        vs = ValidationSession(
            id=session_id,
            started_at=now,
            completed_at=None,
            skipped=False,
        )
        self._session.add(validation_session_to_table(vs))

        coo_rows = (
            await self._session.exec(
                select(AgentSpecTable).where(AgentSpecTable.level == 0)
            )
        ).all()
        n1_rows = (
            await self._session.exec(
                select(AgentSpecTable).where(AgentSpecTable.level == 1)
            )
        ).all()

        for row in list(coo_rows) + list(n1_rows):
            rec = AgentValidationRecord(
                id=str(uuid4()),
                session_id=session_id,
                root_agent_id=row.id,
                status=AgentValidationStatus.PENDING,
                active_agent_id=None,
                active_conversation_id=None,
                navigation_stack=[],
                conversation_ids=[],
                visited_agent_ids=[],
                validated_at=None,
            )
            self._session.add(agent_validation_record_to_table(rec))

        await self._session.commit()
        return vs

    async def resume_session(self) -> ValidationSession | None:
        from adjents.db.convert import validation_session_from_table

        rows = (await self._session.exec(select(ValidationSessionTable))).all()
        for row in rows:
            if row.completed_at is None:
                return validation_session_from_table(row)
        return None

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    async def start_agent_conversation(
        self, session_id: str, root_agent_id: str
    ) -> str:
        from adjents.db.convert import agent_spec_from_table

        record = await self._load_record(session_id, root_agent_id)

        # Resume in-progress conversation
        if record.status == AgentValidationStatus.IN_PROGRESS:
            assert record.active_conversation_id is not None
            conv_id = record.active_conversation_id
            agent_id = self._conv_agent.get(
                conv_id, record.active_agent_id or root_agent_id
            )
            msgs = list(self._conv_messages.get(conv_id, []))
            nudge = "Please continue our conversation."
            msgs.append({"role": "user", "content": nudge})
            intro_prompt = self._prompts.get("agent/intro")
            response = await self._client.complete(
                msgs, effort=self._CONVERSATION_EFFORT, system=intro_prompt.content
            )
            msgs.append({"role": "assistant", "content": response})
            self._conv_messages[conv_id] = msgs
            await self._append_message(conv_id, agent_id, "user", nudge)
            await self._append_message(conv_id, agent_id, "assistant", response)
            return response

        # Enforce: N-1 cannot start before COO is validated/skipped
        root_spec_row = await self._session.get(AgentSpecTable, root_agent_id)
        if root_spec_row is None:
            raise TeamSetupError(f"Agent {root_agent_id} not found.")
        if root_spec_row.level > 0:
            coo_rows = (
                await self._session.exec(
                    select(AgentSpecTable).where(AgentSpecTable.level == 0)
                )
            ).all()
            for coo_row in coo_rows:
                coo_rec = await self._load_record_or_none(session_id, coo_row.id)
                if coo_rec is None or coo_rec.status not in (
                    AgentValidationStatus.VALIDATED,
                    AgentValidationStatus.SKIPPED,
                ):
                    raise TeamSetupError(
                        "COO must be validated or skipped before N-1 agents."
                    )

        # Fresh conversation
        conv_id = str(uuid4())
        root_agent = agent_spec_from_table(root_spec_row)
        skills = await self._load_agent_skills(root_agent.skill_ids)
        direct_reports, reports_skills = await self._load_direct_reports(root_agent_id)
        context_msg = _build_agent_context_message(
            root_agent, skills, direct_reports, reports_skills
        )
        intro_prompt = self._prompts.get("agent/intro")

        messages: list[dict[str, str]] = [{"role": "user", "content": context_msg}]
        response = await self._client.complete(
            messages, effort=self._CONVERSATION_EFFORT, system=intro_prompt.content
        )
        messages.append({"role": "assistant", "content": response})

        await self._append_message(conv_id, root_agent_id, "user", context_msg)
        await self._append_message(conv_id, root_agent_id, "assistant", response)
        self._conv_messages[conv_id] = messages
        self._conv_agent[conv_id] = root_agent_id

        record.status = AgentValidationStatus.IN_PROGRESS
        record.active_agent_id = root_agent_id
        record.active_conversation_id = conv_id
        record.navigation_stack = [root_agent_id]
        record.conversation_ids = [conv_id]
        await self._save_record(record)
        await self._set_agent_state(root_agent_id, AgentStatus.IN_MEETING_1ON1)

        return response

    async def reply(
        self, session_id: str, root_agent_id: str, user_message: str
    ) -> str:
        record = await self._load_record(session_id, root_agent_id)
        assert record.active_conversation_id is not None
        conv_id = record.active_conversation_id
        agent_id = record.active_agent_id or root_agent_id

        msgs = list(self._conv_messages.get(conv_id, []))
        msgs.append({"role": "user", "content": user_message})
        intro_prompt = self._prompts.get("agent/intro")
        response = await self._client.complete(
            msgs, effort=self._CONVERSATION_EFFORT, system=intro_prompt.content
        )
        msgs.append({"role": "assistant", "content": response})
        self._conv_messages[conv_id] = msgs

        await self._append_message(conv_id, agent_id, "user", user_message)
        await self._append_message(conv_id, agent_id, "assistant", response)
        return response

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    async def complete_current_agent(self, session_id: str, root_agent_id: str) -> str:
        from adjents.db.convert import agent_spec_from_table

        record = await self._load_record(session_id, root_agent_id)
        assert record.active_agent_id is not None
        current_agent_id = record.active_agent_id

        root_spec_row = await self._session.get(AgentSpecTable, root_agent_id)
        assert root_spec_row is not None
        children_by_parent = await self._load_subtree_children(root_spec_row)

        next_agent, new_stack, new_visited = _advance_traversal(
            current_agent_id,
            record.navigation_stack,
            record.visited_agent_ids,
            children_by_parent,
        )

        if next_agent is not None:
            # Move to next agent in subtree
            await self._set_agent_state(current_agent_id, AgentStatus.PAUSED)

            next_conv_id = str(uuid4())
            next_spec_row = await self._session.get(AgentSpecTable, next_agent.id)
            assert next_spec_row is not None
            next_spec = agent_spec_from_table(next_spec_row)
            next_skills = await self._load_agent_skills(next_spec.skill_ids)
            next_reports, next_reports_skills = await self._load_direct_reports(
                next_agent.id
            )
            context_msg = _build_agent_context_message(
                next_spec, next_skills, next_reports, next_reports_skills
            )
            intro_prompt = self._prompts.get("agent/intro")
            messages: list[dict[str, str]] = [{"role": "user", "content": context_msg}]
            intro_response = await self._client.complete(
                messages, effort=self._CONVERSATION_EFFORT, system=intro_prompt.content
            )
            messages.append({"role": "assistant", "content": intro_response})

            await self._append_message(next_conv_id, next_agent.id, "user", context_msg)
            await self._append_message(
                next_conv_id, next_agent.id, "assistant", intro_response
            )
            self._conv_messages[next_conv_id] = messages
            self._conv_agent[next_conv_id] = next_agent.id

            await self._set_agent_state(next_agent.id, AgentStatus.IN_MEETING_1ON1)

            record.active_agent_id = next_agent.id
            record.active_conversation_id = next_conv_id
            record.navigation_stack = new_stack
            record.visited_agent_ids = new_visited
            record.conversation_ids = record.conversation_ids + [next_conv_id]
            await self._save_record(record)

            return intro_response

        else:
            # Subtree exhausted — request final summary from root agent (V1 fix)
            await self._set_agent_state(current_agent_id, AgentStatus.PAUSED)

            root_conv_id = record.conversation_ids[0]
            root_msgs = list(self._conv_messages.get(root_conv_id, []))
            summary_req = (
                "The team setup for your subtree is complete. "
                "Please provide a brief summary of yourself and each member of your "
                "team (name, role, key responsibilities)."
            )
            root_msgs.append({"role": "user", "content": summary_req})
            intro_prompt = self._prompts.get("agent/intro")
            summary = await self._client.complete(
                root_msgs, effort=self._CONVERSATION_EFFORT, system=intro_prompt.content
            )
            root_msgs.append({"role": "assistant", "content": summary})
            self._conv_messages[root_conv_id] = root_msgs

            root_msg_agent = self._conv_agent.get(root_conv_id, root_agent_id)
            await self._append_message(
                root_conv_id, root_msg_agent, "user", summary_req
            )
            await self._append_message(
                root_conv_id, root_msg_agent, "assistant", summary
            )

            # V1: active_agent_id = root_agent_id (not None) when delivering final
            # summary
            record.active_agent_id = root_agent_id
            record.navigation_stack = []
            record.visited_agent_ids = new_visited
            await self._save_record(record)

            return summary

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_team(self, session_id: str, root_agent_id: str) -> None:
        record = await self._load_record(session_id, root_agent_id)
        transcript = self._build_transcript(record)
        updates = await self._call_extraction_llm([transcript])

        await self._apply_agent_updates(updates.get("agent_updates", []))

        for agent_id in record.visited_agent_ids:
            await self._set_agent_state(agent_id, AgentStatus.PAUSED)
        await self._set_agent_state(root_agent_id, AgentStatus.PAUSED)

        record.status = AgentValidationStatus.VALIDATED
        record.validated_at = datetime.now(UTC)
        await self._save_record(record)

        await self._maybe_go_live(session_id)

    # ------------------------------------------------------------------
    # Skip
    # ------------------------------------------------------------------

    async def skip_agent(self, session_id: str, root_agent_id: str) -> dict[str, Any]:
        record = await self._load_record(session_id, root_agent_id)

        if record.active_agent_id is not None:
            await self._set_agent_state(record.active_agent_id, AgentStatus.PAUSED)

        record.status = AgentValidationStatus.SKIPPED
        record.active_agent_id = None
        record.navigation_stack = []
        await self._save_record(record)

        summary = await self.get_subtree_summary(root_agent_id)
        await self._maybe_go_live(session_id)

        agent_name = (
            summary["agents"][0]["name"] if summary["agents"] else root_agent_id
        )
        return {
            "summary": summary,
            "warning": (
                f"Agent '{agent_name}' ({root_agent_id}) and their subtree were"
                " skipped. No configuration changes will be applied."
            ),
        }

    async def skip_all(self, session_id: str) -> dict[str, Any]:
        rows = (
            await self._session.exec(
                select(AgentValidationRecordTable).where(
                    AgentValidationRecordTable.session_id == session_id
                )
            )
        ).all()
        for row in rows:
            row.status = str(AgentValidationStatus.SKIPPED)
            row.active_agent_id = None
            row.navigation_stack = "[]"
            self._session.add(row)
        await self._session.commit()
        await self._go_live(session_id)

        full_summary = await self.get_subtree_summary(None)
        return {
            "summary": full_summary,
            "warning": (
                "All agents were skipped. The org went live with the generated"
                " configuration."
            ),
        }

    async def get_subtree_summary(self, agent_id: str | None) -> dict[str, Any]:
        if agent_id is None:
            all_rows = (await self._session.exec(select(AgentSpecTable))).all()
            return {
                "root_agent_id": None,
                "agents": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "level": r.level,
                        "role_description": r.role_description,
                    }
                    for r in all_rows
                ],
            }

        root_row = await self._session.get(AgentSpecTable, agent_id)
        if root_row is None:
            return {"root_agent_id": agent_id, "agents": []}

        agents: list[dict[str, Any]] = [
            {
                "id": root_row.id,
                "name": root_row.name,
                "level": root_row.level,
                "role_description": root_row.role_description,
            }
        ]
        queue = [agent_id]
        while queue:
            parent_id = queue.pop(0)
            children = (
                await self._session.exec(
                    select(AgentSpecTable).where(AgentSpecTable.parent_id == parent_id)
                )
            ).all()
            for child in children:
                agents.append(
                    {
                        "id": child.id,
                        "name": child.name,
                        "level": child.level,
                        "role_description": child.role_description,
                    }
                )
                queue.append(child.id)
        return {"root_agent_id": agent_id, "agents": agents}

    # ------------------------------------------------------------------
    # Go-live
    # ------------------------------------------------------------------

    async def _go_live(self, session_id: str) -> None:
        now = datetime.now(UTC)
        spec_rows = (await self._session.exec(select(AgentSpecTable))).all()
        for spec_row in spec_rows:
            spec_row.is_paused = False
            self._session.add(spec_row)

        state_rows = (await self._session.exec(select(AgentStateTable))).all()
        for state_row in state_rows:
            state_row.status = str(AgentStatus.IDLE)
            self._session.add(state_row)

        sess_row = await self._session.get(ValidationSessionTable, session_id)
        if sess_row is not None:
            sess_row.completed_at = now.isoformat()
            self._session.add(sess_row)

        await self._session.commit()

    async def _maybe_go_live(self, session_id: str) -> None:
        rows = (
            await self._session.exec(
                select(AgentValidationRecordTable).where(
                    AgentValidationRecordTable.session_id == session_id
                )
            )
        ).all()
        done = {AgentValidationStatus.VALIDATED, AgentValidationStatus.SKIPPED}
        if all(AgentValidationStatus(r.status) in done for r in rows):
            await self._go_live(session_id)

    # ------------------------------------------------------------------
    # Apply updates
    # ------------------------------------------------------------------

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
                    raw = int(value)
                    clamped = max(_INTERVAL_MIN, min(_INTERVAL_MAX, raw))
                    if clamped != raw:
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

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    def _build_transcript(self, record: AgentValidationRecord) -> str:
        parts: list[str] = []
        for conv_id in record.conversation_ids:
            agent_id = self._conv_agent.get(conv_id, "unknown")
            msgs = self._conv_messages.get(conv_id, [])
            lines: list[str] = [f"---AGENT:{agent_id}---"]
            for msg in msgs:
                role = "User" if msg["role"] == "user" else "Agent"
                lines.append(f"{role}: {msg['content']}")
            parts.append("\n".join(lines))
        return "\n\n".join(parts)

    async def _call_extraction_llm(self, conversations: list[str]) -> dict[str, Any]:
        # D3: harmonised signature — takes list[str] like AgentReconfiguration
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
        raise TeamSetupError(
            f"Extraction LLM failed after {self._MAX_RETRIES} attempts: {last_error}"
        )

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _load_record(
        self, session_id: str, root_agent_id: str
    ) -> AgentValidationRecord:
        from adjents.db.convert import agent_validation_record_from_table

        row = (
            await self._session.exec(
                select(AgentValidationRecordTable).where(
                    AgentValidationRecordTable.session_id == session_id,
                    AgentValidationRecordTable.root_agent_id == root_agent_id,
                )
            )
        ).first()
        if row is None:
            raise TeamSetupError(
                f"No record for agent {root_agent_id} in session {session_id}."
            )
        return agent_validation_record_from_table(row)

    async def _load_record_or_none(
        self, session_id: str, root_agent_id: str
    ) -> AgentValidationRecord | None:
        try:
            return await self._load_record(session_id, root_agent_id)
        except TeamSetupError:
            return None

    async def _save_record(self, record: AgentValidationRecord) -> None:
        from adjents.db.convert import agent_validation_record_to_table

        row = (
            await self._session.exec(
                select(AgentValidationRecordTable).where(
                    AgentValidationRecordTable.id == record.id
                )
            )
        ).first()
        if row is not None:
            row.status = str(record.status)
            row.active_agent_id = record.active_agent_id
            row.active_conversation_id = record.active_conversation_id
            row.navigation_stack = json.dumps(record.navigation_stack)
            row.conversation_ids = json.dumps(record.conversation_ids)
            row.visited_agent_ids = json.dumps(record.visited_agent_ids)
            row.validated_at = (
                record.validated_at.isoformat() if record.validated_at else None
            )
            self._session.add(row)
        else:
            self._session.add(agent_validation_record_to_table(record))
        await self._session.commit()

    async def _set_agent_state(self, agent_id: str, status: AgentStatus) -> None:
        row = await self._session.get(AgentStateTable, agent_id)
        if row is not None:
            row.status = str(status)
            row.updated_at = datetime.now(UTC).isoformat()
            self._session.add(row)
            await self._session.commit()

    async def _load_direct_reports(
        self, agent_id: str
    ) -> tuple[list[AgentSpec], dict[str, list[Skill]]]:
        from adjents.db.convert import agent_spec_from_table

        report_rows = (
            await self._session.exec(
                select(AgentSpecTable).where(AgentSpecTable.parent_id == agent_id)
            )
        ).all()
        reports = [agent_spec_from_table(r) for r in report_rows]
        reports_skills: dict[str, list[Skill]] = {}
        for report in reports:
            reports_skills[report.id] = await self._load_agent_skills(report.skill_ids)
        return reports, reports_skills

    async def _load_agent_skills(self, skill_ids: list[str]) -> list[Skill]:
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

    async def _load_subtree_children(
        self, root_spec: AgentSpecTable
    ) -> dict[str, list[AgentSpec]]:
        from adjents.db.convert import agent_spec_from_table

        if root_spec.level == 0:
            return {}
        result: dict[str, list[AgentSpec]] = {}
        queue = [root_spec.id]
        while queue:
            parent_id = queue.pop(0)
            children = (
                await self._session.exec(
                    select(AgentSpecTable).where(AgentSpecTable.parent_id == parent_id)
                )
            ).all()
            child_specs = [agent_spec_from_table(c) for c in children]
            result[parent_id] = child_specs
            queue.extend(c.id for c in child_specs)
        return result

    async def _append_message(
        self, conv_id: str, agent_id: str, role: str, content: str
    ) -> None:
        from_agent = "user" if role == "user" else agent_id
        to_agent = agent_id if role == "user" else "user"
        self._session.add(
            MessageTable(
                id=str(uuid4()),
                from_agent=from_agent,
                to_agent=to_agent,
                content=content,
                metadata_json=json.dumps({"conv_id": conv_id}),
                parent_message_id=None,
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        await self._session.commit()
