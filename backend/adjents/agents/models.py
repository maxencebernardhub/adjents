"""Agent domain models: AgentSpec, AgentState, AgentStatus, Skill, BlockingQuestion.

An agent is data, not code: one `AgentSpec`, its `Skill` records and one
`AgentState`, all keyed by the agent's id. There is no class per agent; the COO is
the `AgentSpec` with `level == 0`.

Place in the flow: domain / API layer (ADR 0002) — Pydantic models with no
database import. `GeneratorOrgGeneration` creates every `AgentSpec` and
`AgentState` (agents start paused) and the initial `Skill` records; team setup and
reconfiguration read and update them, and add skills; `utils/agent_context.py`
renders them into the agent context message. Persistence goes through
`db/convert/agents.py` and `db/tables.py`. `BlockingQuestion` has no producer yet:
it is defined ahead of the agent loop.

Valid-data rules live here as field constraints and reference constants
(`VISUAL_CHARACTERS`, `SCHEDULER_INTERVAL_MIN` / `_MAX`, the `WorkHours` type, also
used by `generator/models.py`), so every writer shares one definition.

As in every domain model, datetimes must carry a timezone (`AwareDatetime`), and
validation errors name the field and the error type, never the input value
(`hide_input_in_errors`): the models carry user and LLM content, and their errors
reach exception messages and logs.

Entry points: `AgentSpec`, `AgentState`, `AgentStatus`, `Skill`,
`BlockingQuestion`, `WorkHours`, `VISUAL_CHARACTERS`, `SCHEDULER_INTERVAL_MIN`,
`SCHEDULER_INTERVAL_MAX`.

Related ADRs: 0002 (domain models vs tables), 0004 (BlockingQuestion), 0006 (agents
start paused), 0009 (direct reconfiguration), 0010 (agents are data, not code).
"""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

# Sprite identifiers the PixiJS workspace can render.
VISUAL_CHARACTERS: frozenset[str] = frozenset(
    {
        "character_suit",
        "character_creative",
        "character_tech",
        "character_support",
        "character_analyst",
        "character_sales",
    }
)

# Bounds of `AgentSpec.scheduler_interval_seconds`, inclusive: 5 minutes to 1 hour.
SCHEDULER_INTERVAL_MIN = 300
SCHEDULER_INTERVAL_MAX = 3600

# `[0-9]`, not `\d`: pydantic-core's regex engine matches any Unicode digit with
# `\d` (e.g. Arabic-Indic digits). Its `$` matches only at the very end, so a
# trailing newline is rejected.
_HH_MM = r"([01][0-9]|2[0-3]):[0-5][0-9]"
_WORK_HOURS_PATTERN = rf"^{_HH_MM}-{_HH_MM}$"


def _check_distinct_bounds(value: str) -> str:
    start, end = value.split("-")
    if start == end:
        raise ValueError("start and end times must differ")
    return value


def _check_visual_character(value: str) -> str:
    if value not in VISUAL_CHARACTERS:
        raise ValueError(f"must be one of {sorted(VISUAL_CHARACTERS)}")
    return value


# A daily active window "HH:MM-HH:MM", times from 00:00 to 23:59. An end before the
# start crosses midnight: "22:00-02:00" runs from 22:00 to 02:00 the next day. Equal
# start and end are rejected: they could mean an empty window or the whole day, and
# "always active" is spelled None. Shared by `AgentSpec` and `BusinessContext`,
# whose value org generation copies into every agent. The pattern also appears in
# the JSON Schema; the distinct-bounds rule does not.
WorkHours = Annotated[
    str,
    StringConstraints(pattern=_WORK_HOURS_PATTERN),
    AfterValidator(_check_distinct_bounds),
]


class AgentStatus(StrEnum):
    """Runtime status of an agent (lifecycle in ARCHITECTURE §5).

    A `StrEnum`: each member compares equal to its string value, which is what is
    stored in SQLite. Today org generation creates every agent `PAUSED`, then team
    setup and reconfiguration change the status (`PAUSED`, `IN_MEETING_1ON1`,
    `IDLE`); the other members wait for the agent loop.

    Attributes:
        IDLE: Live and waiting for its next scheduler tick or message.
        WORKING: Processing a task.
        IN_MEETING_1ON1: In a one-on-one conversation (with the user during team
            setup or reconfiguration).
        IN_MEETING_GROUP: In a meeting with several participants.
        PAUSED: Not running. Every agent starts in this status.
        WAITING_FOR_HUMAN: Blocked on a `BlockingQuestion`.
    """

    IDLE = "idle"
    WORKING = "working"
    IN_MEETING_1ON1 = "meeting_1on1"
    IN_MEETING_GROUP = "meeting_group"
    PAUSED = "paused"
    WAITING_FOR_HUMAN = "waiting_for_human"


class Skill(BaseModel):
    """A capability of an agent, generated with it.

    Descriptive only in v0.1 (nothing executes it); `AgentSpec.skill_ids` links an
    agent to its skills, the skill does not point back to its agent.

    Attributes:
        id: UUID.
        name: Short name, e.g. "Draft invoice".
        description: What the skill does.
        inputs: Natural-language descriptions of the inputs ("Client name").
        outputs: Natural-language descriptions of the outputs.
        requires_human_review: Whether the user must review the skill's output.
    """

    model_config = ConfigDict(hide_input_in_errors=True)

    id: str
    name: str
    description: str
    inputs: list[str]
    outputs: list[str]
    requires_human_review: bool


class AgentSpec(BaseModel):
    """The definition of an agent: identity, role, hierarchy position, schedule.

    Generated by the Generator Agent and changed only by team setup or
    reconfiguration, unlike `AgentState`, which changes constantly. Every field is
    required, including the nullable ones: a missing key is a validation error, not
    a silent `None`.

    The field constraints define what a valid agent is, for every writer. How to
    react to invalid LLM output (reject and retry, clamp, drop the value) stays the
    writer's policy. Constraints apply when the model is built or validated:
    assignment is not validated, and code that writes table rows directly bypasses
    them.

    Attributes:
        id: UUID.
        name: Display name, e.g. "Finance Lead".
        level: Hierarchy depth, at least 0: 0 = COO, 1 = N-1, 2 = N-2. No upper
            bound.
        parent_id: Id of the parent agent; None for the COO.
        domain: Business domain, e.g. "Finance"; None for the COO.
        role_description: What the agent is for.
        responsibilities: One responsibility per item.
        skill_ids: Ids of the agent's `Skill` records.
        escalation_rules: When the agent must escalate, one rule per item.
        scheduler_interval_seconds: Interval between autonomous wake-ups, from
            `SCHEDULER_INTERVAL_MIN` to `SCHEDULER_INTERVAL_MAX` inclusive.
        work_hours: Daily active window (`WorkHours`), e.g. "09:00-18:00"; None =
            always active.
        is_paused: User-controlled pause flag.
        visual_character: Sprite identifier for the PixiJS workspace, one of
            `VISUAL_CHARACTERS`.
        created_at: Creation time.
    """

    model_config = ConfigDict(hide_input_in_errors=True)

    id: str
    name: str
    level: Annotated[int, Field(ge=0)]
    parent_id: str | None
    domain: str | None
    role_description: str
    responsibilities: list[str]
    skill_ids: list[str]
    escalation_rules: list[str]
    scheduler_interval_seconds: Annotated[
        int, Field(ge=SCHEDULER_INTERVAL_MIN, le=SCHEDULER_INTERVAL_MAX)
    ]
    work_hours: WorkHours | None
    is_paused: bool
    visual_character: Annotated[str, AfterValidator(_check_visual_character)]
    created_at: AwareDatetime


class AgentState(BaseModel):
    """The runtime state of an agent, one per `AgentSpec`.

    Kept apart from `AgentSpec` because the two change at very different rates: the
    state is meant to change many times per minute and be broadcast to the frontend
    on every change, while the spec rarely changes.

    Attributes:
        agent_id: Id of the agent; also the table's primary key.
        status: Current `AgentStatus`.
        current_task_summary: Short description of the current task, if any.
        meeting_with: Agent ids of the other participants when in a meeting.
        updated_at: Time of the last change.
    """

    model_config = ConfigDict(hide_input_in_errors=True)

    agent_id: str
    status: AgentStatus
    current_task_summary: str | None
    meeting_with: list[str]
    updated_at: AwareDatetime


class BlockingQuestion(BaseModel):
    """A decision an agent cannot make without the user.

    A persisted entity, so that a pending question survives a restart and the
    `question_id` of a `blocking_answer` WebSocket message can be matched to it
    (ADR 0004).

    The answer fields are consistent: an answered question has an `answer` and an
    `answered_at`, an unanswered one has neither (checked at validation, like the
    field types; `answered` stays a field, as in ADR 0004).

    Attributes:
        id: UUID; the `question_id` of the WebSocket protocol.
        agent_id: Id of the agent that asked.
        question: The question shown to the user.
        context: Why the agent needs this decision, if given.
        answered: Whether the user has answered.
        answer: The user's answer; None while unanswered.
        created_at: Time the question was raised.
        answered_at: Time of the answer; None while unanswered.
    """

    model_config = ConfigDict(hide_input_in_errors=True)

    id: str
    agent_id: str
    question: str
    context: str | None
    answered: bool
    answer: str | None
    created_at: AwareDatetime
    answered_at: AwareDatetime | None

    @model_validator(mode="after")
    def _check_answer_state(self) -> Self:
        has_answer = (self.answer is not None, self.answered_at is not None)
        if has_answer != (self.answered, self.answered):
            raise ValueError(
                "answered=True requires answer and answered_at; "
                "answered=False requires both to be None"
            )
        return self
