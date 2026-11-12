"""Conversions for the agent domain models (`agents/models.py`).

`AgentSpec`, `AgentState`, `Skill` and `BlockingQuestion` ↔ their tables, following
the conventions of the `adjents.db.convert` package docstring.

Place in the flow: org generation builds the spec, state and skill rows of a new
org; team setup and reconfiguration read specs and skills back; `tests/conftest.py`
and `scripts/smoke_team_setup.py` insert orgs. No code converts a `BlockingQuestion`
yet. Callers import these functions from `adjents.db.convert`.

Entry points: `agent_spec_*`, `agent_state_*`, `skill_*`, `blocking_question_*`
(`_to_table()` / `_from_table()`).

Related ADRs: 0002 (domain models vs tables), 0004 (`BlockingQuestion`).
"""

import json
from datetime import datetime

from adjents.agents.models import (
    AgentSpec,
    AgentState,
    AgentStatus,
    BlockingQuestion,
    Skill,
)
from adjents.db.tables import (
    AgentSpecTable,
    AgentStateTable,
    BlockingQuestionTable,
    SkillTable,
)

# --- AgentSpec ---


def agent_spec_to_table(spec: AgentSpec) -> AgentSpecTable:
    return AgentSpecTable(
        id=spec.id,
        name=spec.name,
        level=spec.level,
        parent_id=spec.parent_id,
        domain=spec.domain,
        role_description=spec.role_description,
        responsibilities=json.dumps(spec.responsibilities),
        skill_ids=json.dumps(spec.skill_ids),
        escalation_rules=json.dumps(spec.escalation_rules),
        scheduler_interval_seconds=spec.scheduler_interval_seconds,
        work_hours=spec.work_hours,
        is_paused=spec.is_paused,
        visual_character=spec.visual_character,
        created_at=spec.created_at.isoformat(),
    )


def agent_spec_from_table(row: AgentSpecTable) -> AgentSpec:
    return AgentSpec(
        id=row.id,
        name=row.name,
        level=row.level,
        parent_id=row.parent_id,
        domain=row.domain,
        role_description=row.role_description,
        responsibilities=json.loads(row.responsibilities),
        skill_ids=json.loads(row.skill_ids),
        escalation_rules=json.loads(row.escalation_rules),
        scheduler_interval_seconds=row.scheduler_interval_seconds,
        work_hours=row.work_hours,
        is_paused=row.is_paused,
        visual_character=row.visual_character,
        created_at=datetime.fromisoformat(row.created_at),
    )


# --- AgentState ---


def agent_state_to_table(state: AgentState) -> AgentStateTable:
    return AgentStateTable(
        agent_id=state.agent_id,
        status=str(state.status),
        current_task_summary=state.current_task_summary,
        meeting_with=json.dumps(state.meeting_with),
        updated_at=state.updated_at.isoformat(),
    )


def agent_state_from_table(row: AgentStateTable) -> AgentState:
    return AgentState(
        agent_id=row.agent_id,
        status=AgentStatus(row.status),
        current_task_summary=row.current_task_summary,
        meeting_with=json.loads(row.meeting_with),
        updated_at=datetime.fromisoformat(row.updated_at),
    )


# --- Skill ---


def skill_to_table(skill: Skill) -> SkillTable:
    return SkillTable(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        inputs=json.dumps(skill.inputs),
        outputs=json.dumps(skill.outputs),
        requires_human_review=skill.requires_human_review,
    )


def skill_from_table(row: SkillTable) -> Skill:
    return Skill(
        id=row.id,
        name=row.name,
        description=row.description,
        inputs=json.loads(row.inputs),
        outputs=json.loads(row.outputs),
        requires_human_review=row.requires_human_review,
    )


# --- BlockingQuestion ---


def blocking_question_to_table(bq: BlockingQuestion) -> BlockingQuestionTable:
    return BlockingQuestionTable(
        id=bq.id,
        agent_id=bq.agent_id,
        question=bq.question,
        context=bq.context,
        answered=bq.answered,
        answer=bq.answer,
        created_at=bq.created_at.isoformat(),
        answered_at=bq.answered_at.isoformat() if bq.answered_at is not None else None,
    )


def blocking_question_from_table(row: BlockingQuestionTable) -> BlockingQuestion:
    return BlockingQuestion(
        id=row.id,
        agent_id=row.agent_id,
        question=row.question,
        context=row.context,
        answered=row.answered,
        answer=row.answer,
        created_at=datetime.fromisoformat(row.created_at),
        answered_at=datetime.fromisoformat(row.answered_at)
        if row.answered_at is not None
        else None,
    )
