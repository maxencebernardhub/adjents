"""Generator Agent — org generation: types, validation, and orchestration.

Covers the full lifecycle from raw LLM output to persisted AgentSpec/Skill/AgentState.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.agents.models import AgentSpec, AgentState, AgentStatus, Skill
from adjents.db.convert import agent_spec_to_table, agent_state_to_table, skill_to_table
from adjents.generator.models import BusinessContext
from adjents.llm.anthropic_client import AnthropicClient
from adjents.llm.types import Effort
from adjents.prompts.loader import PromptLoader

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_VISUAL_CHARACTERS: frozenset[str] = frozenset(
    {
        "character_suit",
        "character_creative",
        "character_tech",
        "character_support",
        "character_analyst",
        "character_sales",
    }
)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class RawAgentData:
    """Intermediate dataclass parsed from the LLM JSON before UUID resolution."""

    temp_id: str
    name: str
    level: int
    parent_temp_id: str | None
    domain: str | None
    role_description: str
    responsibilities: list[str]
    skills: list[dict[str, Any]]  # inline skill dicts from LLM
    escalation_rules: list[str]
    scheduler_interval_seconds: int
    work_hours: str | None
    visual_character: str


@dataclass
class OrgGenerationResult:
    """Final output of a successful org generation."""

    agents: list[AgentSpec]
    skills: list[Skill]


class OrgGenerationError(Exception):
    """Raised when org generation fails after all retries."""


# ---------------------------------------------------------------------------
# Structural validation (pure function — no I/O)
# ---------------------------------------------------------------------------


def _validate_structure(
    raw_agents: list[RawAgentData],
    domains_with_human_coverage: list[str],
) -> str | None:
    """Return None if the org is structurally valid, or a descriptive error message.

    Rules checked in order:
    1. Exactly one COO (level=0).
    2. COO has parent_temp_id=None; all others must have a non-None parent_temp_id.
    3. All temp_id values are unique.
    4. Every level>0 agent references an existing parent_temp_id.
    5. No parent cycle.
    6. No N-1 agent has a domain in domains_with_human_coverage (case-insensitive).
    7. Every visual_character is in VALID_VISUAL_CHARACTERS.
    8. Every scheduler_interval_seconds is in [300, 3600].
    """
    # ── Rule 1: exactly one COO ────────────────────────────────────────────
    coos = [r for r in raw_agents if r.level == 0]
    if len(coos) == 0:
        return "No COO found: exactly one agent with level=0 is required."
    if len(coos) > 1:
        ids = ", ".join(r.temp_id for r in coos)
        return (
            f"Multiple COOs found ({ids}): exactly one agent with level=0 is required."
        )

    # ── Rule 2: COO parent=None; all others must have a parent ─────────────
    coo = coos[0]
    if coo.parent_temp_id is not None:
        return (
            f"COO '{coo.temp_id}' has level=0 but references parent "
            f"'{coo.parent_temp_id}'. COO must have parent_temp_id=None."
        )
    for agent in raw_agents:
        if agent.level != 0 and agent.parent_temp_id is None:
            return (
                f"Agent '{agent.temp_id}' (level={agent.level}) has no parent. "
                "Only the COO (level=0) may have parent_temp_id=None."
            )

    # ── Rule 3: unique temp_ids ────────────────────────────────────────────
    seen_ids: set[str] = set()
    for agent in raw_agents:
        if agent.temp_id in seen_ids:
            return (
                f"Duplicate temp_id '{agent.temp_id}': "
                "all temp_id values must be unique."
            )
        seen_ids.add(agent.temp_id)

    # ── Rule 4: parent must exist ──────────────────────────────────────────
    all_ids = {r.temp_id for r in raw_agents}
    for agent in raw_agents:
        if agent.parent_temp_id is not None and agent.parent_temp_id not in all_ids:
            return (
                f"Agent '{agent.temp_id}' references unknown parent "
                f"'{agent.parent_temp_id}'."
            )

    # ── Rule 5: no parent cycle ────────────────────────────────────────────
    parent_map: dict[str, str | None] = {
        r.temp_id: r.parent_temp_id for r in raw_agents
    }
    for start_id in parent_map:
        visited: set[str] = set()
        current: str | None = start_id
        while current is not None:
            if current in visited:
                return (
                    f"Parent cycle detected starting from '{start_id}': "
                    f"'{current}' was visited twice."
                )
            visited.add(current)
            current = parent_map.get(current)

    # ── Rule 6: no N-1 agent in a human-covered domain ────────────────────
    human_lower = {d.lower() for d in domains_with_human_coverage}
    for agent in raw_agents:
        if agent.level == 1 and agent.domain is not None:
            if agent.domain.lower() in human_lower:
                return (
                    f"N-1 agent '{agent.temp_id}' has domain '{agent.domain}', "
                    "which is covered by a human. "
                    "Remove this agent or reassign the domain."
                )

    # ── Rule 7: visual_character must be valid ─────────────────────────────
    for agent in raw_agents:
        if agent.visual_character not in VALID_VISUAL_CHARACTERS:
            valid = ", ".join(sorted(VALID_VISUAL_CHARACTERS))
            return (
                f"Agent '{agent.temp_id}' has invalid visual_character "
                f"'{agent.visual_character}'. Must be one of: {valid}."
            )

    # ── Rule 8: scheduler_interval_seconds in [300, 3600] ──────────────────
    for agent in raw_agents:
        interval = agent.scheduler_interval_seconds
        if interval < 300 or interval > 3600:
            return (
                f"Agent '{agent.temp_id}' has scheduler_interval_seconds={interval}. "
                "Must be in [300, 3600]."
            )

    return None


# ---------------------------------------------------------------------------
# Pure helpers (no I/O)
# ---------------------------------------------------------------------------


def _build_context_message(context: BusinessContext) -> str:
    """Serialize BusinessContext into a human-readable text block for the user message.

    The result is passed as the user message to the LLM — not injected into the
    system prompt — to avoid str.format_map() breakage on user-supplied curly braces.
    """
    lines = [
        f"Business name: {context.business_name or 'N/A'}",
        f"Founder: {context.founder_name}",
        f"Language: {context.language}",
        f"Core activity: {context.core_activity}",
        f"Legal status: {context.legal_status or 'N/A'}",
        f"Target clients: {', '.join(context.target_clients) or 'N/A'}",
        "Domains with human coverage (DO NOT generate agents for these): "
        f"{', '.join(context.domains_with_human_coverage) or 'none'}",
        "Domains to staff with AI agents: "
        f"{', '.join(context.domains_to_staff) or 'infer from tasks below'}",
        "Tasks to delegate:",
        *[f"  - {t}" for t in context.tasks_to_delegate],
        f"Tasks user keeps: {', '.join(context.tasks_user_keeps) or 'N/A'}",
        f"Financial goals: {context.financial_goals or 'N/A'}",
        f"Existing tools: {', '.join(context.existing_tools) or 'none'}",
        f"Autonomy preference: {context.autonomy_preference}",
        f"Work hours: {context.work_hours or 'null — always active'}",
        f"Additional context: {context.additional_context or 'none'}",
    ]
    return "\n".join(lines)


def _parse_raw_agents(data: dict[str, Any]) -> list[RawAgentData]:
    """Parse the 'agents' list from a validated LLM JSON dict.

    Raises ValueError on any shape error (missing key, wrong type, etc.).
    """
    agents_raw = data.get("agents")
    if not isinstance(agents_raw, list):
        raise ValueError("'agents' must be a list.")
    result: list[RawAgentData] = []
    for item in agents_raw:
        if not isinstance(item, dict):
            raise ValueError(f"Each agent must be a dict, got {type(item).__name__}.")
        raw_parent = item.get("parent_temp_id")
        result.append(
            RawAgentData(
                temp_id=str(item["temp_id"]),
                name=str(item["name"]),
                level=int(item["level"]),
                parent_temp_id=str(raw_parent) if raw_parent is not None else None,
                domain=item.get("domain"),
                role_description=str(item["role_description"]),
                responsibilities=list(item["responsibilities"]),
                skills=list(item.get("skills", [])),
                escalation_rules=list(item["escalation_rules"]),
                scheduler_interval_seconds=int(item["scheduler_interval_seconds"]),
                work_hours=item.get("work_hours"),
                visual_character=str(item["visual_character"]),
            )
        )
    return result


def _resolve_and_build(
    raw_agents: list[RawAgentData],
    on_agent_ready: Callable[[str, int], None] | None = None,
) -> tuple[list[AgentSpec], list[Skill]]:
    """Assign UUIDs, resolve parent_temp_id → UUID, build AgentSpec + Skill objects.

    Each AgentSpec is created with is_paused=True (all agents start paused;
    unpausing happens after post-generation user validation — ADR 0006).

    The optional *on_agent_ready* callback is invoked with (name, level) after
    each AgentSpec is built — useful for progress reporting (e.g. smoke tests,
    future WebSocket streaming to the frontend).
    """
    now = datetime.now(UTC)
    # One pass to assign a stable UUID to each temp_id
    temp_to_uuid: dict[str, str] = {r.temp_id: str(uuid4()) for r in raw_agents}
    all_specs: list[AgentSpec] = []
    all_skills: list[Skill] = []
    for raw in raw_agents:
        agent_id = temp_to_uuid[raw.temp_id]
        parent_id = temp_to_uuid[raw.parent_temp_id] if raw.parent_temp_id else None
        skill_ids: list[str] = []
        for s in raw.skills:
            skill = Skill(
                id=str(uuid4()),
                name=str(s["name"]),
                description=str(s["description"]),
                inputs=list(s.get("inputs", [])),
                outputs=list(s.get("outputs", [])),
                requires_human_review=bool(s.get("requires_human_review", False)),
            )
            all_skills.append(skill)
            skill_ids.append(skill.id)
        all_specs.append(
            AgentSpec(
                id=agent_id,
                name=raw.name,
                level=raw.level,
                parent_id=parent_id,
                domain=raw.domain,
                role_description=raw.role_description,
                responsibilities=raw.responsibilities,
                skill_ids=skill_ids,
                escalation_rules=raw.escalation_rules,
                scheduler_interval_seconds=raw.scheduler_interval_seconds,
                work_hours=raw.work_hours,
                is_paused=True,
                visual_character=raw.visual_character,
                created_at=now,
            )
        )
        if on_agent_ready is not None:
            on_agent_ready(raw.name, raw.level)
    return all_specs, all_skills


# ---------------------------------------------------------------------------
# Orchestration class
# ---------------------------------------------------------------------------


class GeneratorOrgGeneration:
    """Orchestrates org generation: single LLM call + retry loop + persist.

    Usage:
        gen = GeneratorOrgGeneration(client, prompt_loader, session)
        result = await gen.generate(business_context)
    """

    _MAX_RETRIES: int = 3
    # Org JSONs for complex businesses (10+ domains) can exceed 10k tokens, and
    # high-effort thinking shares the same output budget. 64k leaves room for both
    # while still bounding a runaway call (ADR 0012). Interim: effort and cap move
    # into the router's per-role table in step 10.
    _MAX_TOKENS: int = 64000
    # Single one-shot call whose coherence drives the whole org: worth more thinking.
    _EFFORT: Effort = "high"

    def __init__(
        self,
        client: AnthropicClient,
        prompt_loader: PromptLoader,
        session: AsyncSession,
    ) -> None:
        self._client = client
        self._prompt_loader = prompt_loader
        self._session = session

    async def generate(
        self,
        context: BusinessContext,
        on_agent_ready: Callable[[str, int], None] | None = None,
    ) -> OrgGenerationResult:
        """Generate and persist the full agent org for a given BusinessContext.

        The optional *on_agent_ready* callback is forwarded to _resolve_and_build
        and invoked with (name, level) as each AgentSpec is constructed.
        """
        system = self._prompt_loader.get("generator/org_generation").content
        context_msg = _build_context_message(context)
        raw_agents = await self._call_llm(
            system, context_msg, context.domains_with_human_coverage
        )
        agents, skills = _resolve_and_build(raw_agents, on_agent_ready)
        await self._persist(agents, skills)
        return OrgGenerationResult(agents=agents, skills=skills)

    async def _call_llm(
        self,
        system: str,
        context_msg: str,
        domains_with_human_coverage: list[str],
    ) -> list[RawAgentData]:
        """Retry loop: call LLM → parse JSON → validate structure → return raw agents.

        On failure, appends the bad response + corrective feedback to the message
        history before retrying (progressive context). After _MAX_RETRIES failures,
        raises OrgGenerationError with the last raw response for diagnostics.
        """
        # The initial user message (business context) is set once and never repeated.
        # Each failed attempt appends 2 messages (assistant + corrective feedback),
        # so the history grows to at most 1 + 2*_MAX_RETRIES = 7 messages.
        # This is intentional: progressive context helps the LLM self-correct.
        messages: list[dict[str, str]] = [{"role": "user", "content": context_msg}]
        last_raw = ""
        for _ in range(self._MAX_RETRIES):
            last_raw = await self._client.complete(
                messages,
                effort=self._EFFORT,
                system=system,
                max_tokens=self._MAX_TOKENS,
            )
            try:
                data: dict[str, Any] = json.loads(last_raw)
            except json.JSONDecodeError:
                messages += [
                    {"role": "assistant", "content": last_raw},
                    {"role": "user", "content": "Respond with valid JSON only."},
                ]
                continue
            try:
                raw_agents = _parse_raw_agents(data)
            except (KeyError, TypeError, ValueError) as exc:
                messages += [
                    {"role": "assistant", "content": last_raw},
                    {
                        "role": "user",
                        "content": (
                            f"JSON parse error: {exc}. Use the exact JSON schema."
                        ),
                    },
                ]
                continue
            error = _validate_structure(raw_agents, domains_with_human_coverage)
            if error:
                messages += [
                    {"role": "assistant", "content": last_raw},
                    {
                        "role": "user",
                        "content": (
                            f"Structural error: {error}. "
                            "Fix this issue and respond with the corrected JSON."
                        ),
                    },
                ]
                continue
            return raw_agents
        raise OrgGenerationError(
            f"Org generation failed after {self._MAX_RETRIES} retries. "
            f"Last response: {last_raw[:300]}"
        )

    async def _persist(self, agents: list[AgentSpec], skills: list[Skill]) -> None:
        """Persist all AgentSpec, Skill, and AgentState records in a single commit.

        Plain INSERT — no DELETE before. Calling generate() twice on the same
        context inserts two independent sets of records (new UUIDs each time).
        This is expected v0.1 behaviour (ADR 0005).
        """
        now = datetime.now(UTC)
        for skill in skills:
            self._session.add(skill_to_table(skill))
        for spec in agents:
            self._session.add(agent_spec_to_table(spec))
            state = AgentState(
                agent_id=spec.id,
                status=AgentStatus.PAUSED,
                current_task_summary=None,
                meeting_with=[],
                updated_at=now,
            )
            self._session.add(agent_state_to_table(state))
        await self._session.commit()
