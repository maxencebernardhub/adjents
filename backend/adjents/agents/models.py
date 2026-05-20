"""Core data models for agents: AgentSpec, AgentState, AgentStatus, Skill."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class AgentStatus(StrEnum):
    IDLE = "idle"
    WORKING = "working"
    IN_MEETING_1ON1 = "meeting_1on1"
    IN_MEETING_GROUP = "meeting_group"
    PAUSED = "paused"
    WAITING_FOR_HUMAN = "waiting_for_human"


class Skill(BaseModel):
    id: str
    name: str
    description: str
    inputs: list[str]
    outputs: list[str]
    requires_human_review: bool


class AgentSpec(BaseModel):
    id: str
    name: str
    level: int  # 0 = COO, 1 = N-1, 2 = N-2 — no upper bound
    parent_id: str | None  # None for the COO
    domain: str | None  # None for the COO
    role_description: str
    responsibilities: list[str]
    skill_ids: list[str]  # v0.1: descriptive; v0.2: executable
    escalation_rules: list[str]
    scheduler_interval_seconds: int
    work_hours: str | None  # e.g. "09:00-18:00"; None = always active
    is_paused: bool
    visual_character: str
    created_at: datetime


class AgentState(BaseModel):
    agent_id: str
    status: AgentStatus
    current_task_summary: str | None
    meeting_with: list[str]  # agent IDs when in a meeting
    updated_at: datetime
