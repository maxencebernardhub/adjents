"""Conversions for the Generator domain models.

`BusinessContext` (`generator/models.py`), `ValidationSession` and
`AgentValidationRecord` (defined in `generator/team_setup.py`) ↔ their tables,
following the conventions of the `adjents.db.convert` package docstring.

Place in the flow: the interview persists the extracted `BusinessContext`
(`scripts/smoke_generator_interview.py` reads it back); team setup persists and
reloads its sessions and records. This module imports `generator/team_setup.py`,
so `team_setup` imports `adjents.db.convert` lazily, inside its methods, to avoid a
circular import. Callers import these functions from `adjents.db.convert`.

Entry points: `business_context_*`, `validation_session_*`,
`agent_validation_record_*` (`_to_table()` / `_from_table()`).

Related ADRs: 0002 (domain models vs tables), 0006 (post-generation team setup).
"""

import json
from datetime import datetime

from adjents.db.tables import (
    AgentValidationRecordTable,
    BusinessContextTable,
    ValidationSessionTable,
)
from adjents.generator.models import BusinessContext
from adjents.generator.team_setup import (
    AgentValidationRecord,
    AgentValidationStatus,
    ValidationSession,
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


# --- ValidationSession ---


def validation_session_to_table(session: ValidationSession) -> ValidationSessionTable:
    return ValidationSessionTable(
        id=session.id,
        started_at=session.started_at.isoformat(),
        completed_at=session.completed_at.isoformat()
        if session.completed_at is not None
        else None,
        skipped=session.skipped,
    )


def validation_session_from_table(row: ValidationSessionTable) -> ValidationSession:
    return ValidationSession(
        id=row.id,
        started_at=datetime.fromisoformat(row.started_at),
        completed_at=datetime.fromisoformat(row.completed_at)
        if row.completed_at is not None
        else None,
        skipped=row.skipped,
    )


# --- AgentValidationRecord ---


def agent_validation_record_to_table(
    record: AgentValidationRecord,
) -> AgentValidationRecordTable:
    return AgentValidationRecordTable(
        id=record.id,
        session_id=record.session_id,
        root_agent_id=record.root_agent_id,
        status=str(record.status),
        active_agent_id=record.active_agent_id,
        active_conversation_id=record.active_conversation_id,
        navigation_stack=json.dumps(record.navigation_stack),
        conversation_ids=json.dumps(record.conversation_ids),
        visited_agent_ids=json.dumps(record.visited_agent_ids),
        validated_at=record.validated_at.isoformat()
        if record.validated_at is not None
        else None,
    )


def agent_validation_record_from_table(
    row: AgentValidationRecordTable,
) -> AgentValidationRecord:
    return AgentValidationRecord(
        id=row.id,
        session_id=row.session_id,
        root_agent_id=row.root_agent_id,
        status=AgentValidationStatus(row.status),
        active_agent_id=row.active_agent_id,
        active_conversation_id=row.active_conversation_id,
        navigation_stack=json.loads(row.navigation_stack),
        conversation_ids=json.loads(row.conversation_ids),
        visited_agent_ids=json.loads(row.visited_agent_ids),
        validated_at=datetime.fromisoformat(row.validated_at)
        if row.validated_at is not None
        else None,
    )
