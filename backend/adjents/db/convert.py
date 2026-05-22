"""Conversion functions between Pydantic domain models and SQLModel tables.

Each model has a to_table() and a from_table() function.
JSON serialization of list[str] and dict[str, Any] fields, and ISO 8601
datetime serialization, are handled exclusively here (ADR 0002).
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
    BusinessContextTable,
    ConversationTable,
    DeliverableTable,
    MemoryTable,
    MessageTable,
    ProjectTable,
    SkillTable,
)
from adjents.deliverables.models import Deliverable
from adjents.generator.models import BusinessContext
from adjents.memory.models import Memory
from adjents.messaging.models import Conversation, Message
from adjents.projects.models import Project, ProjectStatus

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


# --- Message ---


def message_to_table(msg: Message) -> MessageTable:
    return MessageTable(
        id=msg.id,
        from_agent=msg.from_agent,
        to_agent=msg.to_agent,
        content=msg.content,
        metadata_json=json.dumps(msg.metadata),
        parent_message_id=msg.parent_message_id,
        created_at=msg.created_at.isoformat(),
    )


def message_from_table(row: MessageTable) -> Message:
    return Message(
        id=row.id,
        from_agent=row.from_agent,
        to_agent=row.to_agent,
        content=row.content,
        metadata=json.loads(row.metadata_json),
        parent_message_id=row.parent_message_id,
        created_at=datetime.fromisoformat(row.created_at),
    )


# --- Conversation ---


def conversation_to_table(conv: Conversation) -> ConversationTable:
    return ConversationTable(
        id=conv.id,
        participant_agents=json.dumps(conv.participant_agents),
        message_ids=json.dumps(conv.message_ids),
        started_at=conv.started_at.isoformat(),
    )


def conversation_from_table(row: ConversationTable) -> Conversation:
    return Conversation(
        id=row.id,
        participant_agents=json.loads(row.participant_agents),
        message_ids=json.loads(row.message_ids),
        started_at=datetime.fromisoformat(row.started_at),
    )


# --- Memory ---


def memory_to_table(mem: Memory) -> MemoryTable:
    return MemoryTable(
        id=mem.id,
        agent_id=mem.agent_id,
        content=mem.content,
        metadata_json=json.dumps(mem.metadata),
        created_at=mem.created_at.isoformat(),
    )


def memory_from_table(row: MemoryTable) -> Memory:
    return Memory(
        id=row.id,
        agent_id=row.agent_id,
        content=row.content,
        metadata=json.loads(row.metadata_json),
        created_at=datetime.fromisoformat(row.created_at),
    )


# --- Deliverable ---


def deliverable_to_table(d: Deliverable) -> DeliverableTable:
    return DeliverableTable(
        id=d.id,
        agent_id=d.agent_id,
        project_id=d.project_id,
        title=d.title,
        file_path=d.file_path,
        created_at=d.created_at.isoformat(),
    )


def deliverable_from_table(row: DeliverableTable) -> Deliverable:
    return Deliverable(
        id=row.id,
        agent_id=row.agent_id,
        project_id=row.project_id,
        title=row.title,
        file_path=row.file_path,
        created_at=datetime.fromisoformat(row.created_at),
    )


# --- Project ---


def project_to_table(proj: Project) -> ProjectTable:
    return ProjectTable(
        id=proj.id,
        title=proj.title,
        objective=proj.objective,
        deliverable_descriptions=json.dumps(proj.deliverable_descriptions),
        deadline=proj.deadline.isoformat() if proj.deadline is not None else None,
        lead_agent_id=proj.lead_agent_id,
        contributor_agent_ids=json.dumps(proj.contributor_agent_ids),
        status=str(proj.status),
        created_at=proj.created_at.isoformat(),
    )


def project_from_table(row: ProjectTable) -> Project:
    return Project(
        id=row.id,
        title=row.title,
        objective=row.objective,
        deliverable_descriptions=json.loads(row.deliverable_descriptions),
        deadline=datetime.fromisoformat(row.deadline)
        if row.deadline is not None
        else None,
        lead_agent_id=row.lead_agent_id,
        contributor_agent_ids=json.loads(row.contributor_agent_ids),
        status=ProjectStatus(row.status),
        created_at=datetime.fromisoformat(row.created_at),
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


# --- BusinessContext ---


def business_context_to_table(bc: BusinessContext) -> BusinessContextTable:
    return BusinessContextTable(
        id=bc.id,
        conversation_id=bc.conversation_id,
        business_name=bc.business_name,
        founder_name=bc.founder_name,
        language=bc.language,
        core_activity=bc.core_activity,
        legal_status=bc.legal_status,
        target_clients=json.dumps(bc.target_clients),
        domains_with_human_coverage=json.dumps(bc.domains_with_human_coverage),
        domains_to_staff=json.dumps(bc.domains_to_staff),
        tasks_to_delegate=json.dumps(bc.tasks_to_delegate),
        tasks_user_keeps=json.dumps(bc.tasks_user_keeps),
        financial_goals=bc.financial_goals,
        existing_tools=json.dumps(bc.existing_tools),
        autonomy_preference=bc.autonomy_preference,
        work_hours=bc.work_hours,
        additional_context=bc.additional_context,
        created_at=bc.created_at.isoformat(),
    )


def business_context_from_table(row: BusinessContextTable) -> BusinessContext:
    return BusinessContext(
        id=row.id,
        conversation_id=row.conversation_id,
        business_name=row.business_name,
        founder_name=row.founder_name,
        language=row.language,
        core_activity=row.core_activity,
        legal_status=row.legal_status,
        target_clients=json.loads(row.target_clients),
        domains_with_human_coverage=json.loads(row.domains_with_human_coverage),
        domains_to_staff=json.loads(row.domains_to_staff),
        tasks_to_delegate=json.loads(row.tasks_to_delegate),
        tasks_user_keeps=json.loads(row.tasks_user_keeps),
        financial_goals=row.financial_goals,
        existing_tools=json.loads(row.existing_tools),
        autonomy_preference=row.autonomy_preference,
        work_hours=row.work_hours,
        additional_context=row.additional_context,
        created_at=datetime.fromisoformat(row.created_at),
    )
