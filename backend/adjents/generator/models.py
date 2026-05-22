"""Domain models for the Generator Agent."""

from datetime import datetime

from pydantic import BaseModel


class BusinessContext(BaseModel):
    id: str
    conversation_id: str
    business_name: str | None
    founder_name: str
    language: str
    core_activity: str
    legal_status: str | None
    target_clients: list[str]
    domains_with_human_coverage: list[str]
    domains_to_staff: list[str]
    tasks_to_delegate: list[str]
    tasks_user_keeps: list[str]
    financial_goals: str | None
    existing_tools: list[str]
    autonomy_preference: str
    work_hours: str | None
    additional_context: str | None
    created_at: datetime
