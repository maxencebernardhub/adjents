"""Smoke test — Post-generation team setup (Mode 1 + Mode 2).

Linked features: feat/post-generation-team-setup
Key files:        adjents/generator/team_setup.py
                  adjents/agents/reconfiguration.py
                  adjents/prompts/agent/intro.md
                  adjents/prompts/agent/extract_agent_adjustments.md

Mock mode (default): AsyncMock LLM, fully automated, assertions on DB state.
Real mode (--real):  requires ANTHROPIC_API_KEY; prints conversation to stdout.

Usage (from backend/):
    uv run python scripts/smoke_team_setup.py
    uv run python scripts/smoke_team_setup.py --real
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

import adjents.db.tables  # noqa: F401  # registers tables in SQLModel.metadata
from adjents.agents.models import AgentSpec, AgentState, AgentStatus, Skill
from adjents.agents.reconfiguration import AgentReconfiguration
from adjents.db.convert import (
    agent_spec_to_table,
    agent_state_to_table,
    skill_to_table,
)
from adjents.db.tables import (
    AgentSpecTable,
    AgentStateTable,
    AgentValidationRecordTable,
    ValidationSessionTable,
)
from adjents.generator.team_setup import TeamSetupOrchestrator
from adjents.llm.anthropic_client import AnthropicClient
from adjents.prompts.loader import PromptLoader

_WIDTH = 72


def _hr(char: str = "─") -> None:
    print(char * _WIDTH)


def _ok(msg: str) -> None:
    print(f"  OK  {msg}")


def _step(msg: str) -> None:
    print(f"\n>>> {msg}")


def _load_env() -> None:
    backend_env = Path(__file__).parent.parent / ".env"
    root_env = Path(__file__).parent.parent.parent / ".env"
    try:
        from dotenv import load_dotenv

        load_dotenv(backend_env)
        load_dotenv(root_env, override=False)
    except ImportError:
        pass


async def _setup_db() -> tuple[AsyncEngine, AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    return engine, AsyncSession(engine)


async def _seed_org(session: AsyncSession) -> dict[str, str]:
    """Create COO + 3 N-1 agents + 1 N-2 under N-1a."""
    coo_id = str(uuid4())
    n1a_id = str(uuid4())
    n1b_id = str(uuid4())
    n1c_id = str(uuid4())
    n2_id = str(uuid4())
    coo_skill_id = str(uuid4())
    n1a_skill_id = str(uuid4())
    n1b_skill_id = str(uuid4())
    n1c_skill_id = str(uuid4())
    n2_skill_id = str(uuid4())

    now = datetime.now(UTC)

    specs = [
        AgentSpec(
            id=coo_id,
            name="Jordan",
            level=0,
            parent_id=None,
            domain=None,
            role_description="COO — coordinates all N-1 leads.",
            responsibilities=["Coordinate all operations"],
            skill_ids=[coo_skill_id],
            escalation_rules=[],
            scheduler_interval_seconds=900,
            work_hours="09:00-18:00",
            visual_character="character_suit",
            is_paused=True,
            created_at=now,
        ),
        AgentSpec(
            id=n1a_id,
            name="Alex",
            level=1,
            parent_id=coo_id,
            domain="Finance",
            role_description="Finance Lead.",
            responsibilities=["Manage invoicing"],
            skill_ids=[n1a_skill_id],
            escalation_rules=[],
            scheduler_interval_seconds=1800,
            work_hours="09:00-18:00",
            visual_character="character_analyst",
            is_paused=True,
            created_at=now,
        ),
        AgentSpec(
            id=n1b_id,
            name="Maya",
            level=1,
            parent_id=coo_id,
            domain="Marketing",
            role_description="Marketing Lead.",
            responsibilities=["Manage marketing"],
            skill_ids=[n1b_skill_id],
            escalation_rules=[],
            scheduler_interval_seconds=1800,
            work_hours="09:00-18:00",
            visual_character="character_creative",
            is_paused=True,
            created_at=now,
        ),
        AgentSpec(
            id=n1c_id,
            name="Felix",
            level=1,
            parent_id=coo_id,
            domain="Ops",
            role_description="Operations Lead.",
            responsibilities=["Manage operations"],
            skill_ids=[n1c_skill_id],
            escalation_rules=[],
            scheduler_interval_seconds=1800,
            work_hours="09:00-18:00",
            visual_character="character_tech",
            is_paused=True,
            created_at=now,
        ),
        AgentSpec(
            id=n2_id,
            name="Sam",
            level=2,
            parent_id=n1a_id,
            domain="Finance",
            role_description="Invoicing Specialist.",
            responsibilities=["Track invoices"],
            skill_ids=[n2_skill_id],
            escalation_rules=[],
            scheduler_interval_seconds=1800,
            work_hours="09:00-18:00",
            visual_character="character_analyst",
            is_paused=True,
            created_at=now,
        ),
    ]
    skills = [
        Skill(
            id=coo_skill_id,
            name="Synthesis",
            description="Aggregates reports.",
            inputs=[],
            outputs=[],
            requires_human_review=False,
        ),
        Skill(
            id=n1a_skill_id,
            name="Invoicing",
            description="Tracks invoices.",
            inputs=[],
            outputs=[],
            requires_human_review=True,
        ),
        Skill(
            id=n1b_skill_id,
            name="Campaigns",
            description="Runs marketing campaigns.",
            inputs=[],
            outputs=[],
            requires_human_review=False,
        ),
        Skill(
            id=n1c_skill_id,
            name="Logistics",
            description="Manages logistics.",
            inputs=[],
            outputs=[],
            requires_human_review=False,
        ),
        Skill(
            id=n2_skill_id,
            name="Tracking",
            description="Tracks payment status.",
            inputs=[],
            outputs=[],
            requires_human_review=False,
        ),
    ]
    states = [
        AgentState(
            agent_id=coo_id,
            status=AgentStatus.PAUSED,
            current_task_summary=None,
            meeting_with=[],
            updated_at=now,
        ),
        AgentState(
            agent_id=n1a_id,
            status=AgentStatus.PAUSED,
            current_task_summary=None,
            meeting_with=[],
            updated_at=now,
        ),
        AgentState(
            agent_id=n1b_id,
            status=AgentStatus.PAUSED,
            current_task_summary=None,
            meeting_with=[],
            updated_at=now,
        ),
        AgentState(
            agent_id=n1c_id,
            status=AgentStatus.PAUSED,
            current_task_summary=None,
            meeting_with=[],
            updated_at=now,
        ),
        AgentState(
            agent_id=n2_id,
            status=AgentStatus.PAUSED,
            current_task_summary=None,
            meeting_with=[],
            updated_at=now,
        ),
    ]

    for skill in skills:
        session.add(skill_to_table(skill))
    for spec in specs:
        session.add(agent_spec_to_table(spec))
    for state in states:
        session.add(agent_state_to_table(state))
    await session.commit()

    return {
        "coo_id": coo_id,
        "n1a_id": n1a_id,
        "n1b_id": n1b_id,
        "n1c_id": n1c_id,
        "n2_id": n2_id,
    }


def _make_stub_loader() -> PromptLoader:
    loader = MagicMock(spec=PromptLoader)
    stub = MagicMock()
    stub.content = "You are a helpful agent."
    loader.get.return_value = stub
    return cast(PromptLoader, loader)


def _make_mock_client(*responses: str) -> AnthropicClient:
    client = MagicMock(spec=AnthropicClient)
    client.complete = AsyncMock(side_effect=list(responses))
    return cast(AnthropicClient, client)


async def _assert_go_live(session: AsyncSession, session_id: str) -> None:
    spec_rows = (await session.exec(select(AgentSpecTable))).all()
    paused = [s.name for s in spec_rows if s.is_paused]
    assert not paused, f"Expected all is_paused=False, still paused: {paused}"
    _ok(f"go_live: all {len(spec_rows)} AgentSpec.is_paused = False")

    state_rows = (await session.exec(select(AgentStateTable))).all()
    not_idle = [s.agent_id for s in state_rows if s.status != str(AgentStatus.IDLE)]
    assert not not_idle, f"Expected all status=IDLE, not idle: {not_idle}"
    _ok(f"go_live: all {len(state_rows)} AgentState.status = IDLE")

    vs_row = await session.get(ValidationSessionTable, session_id)
    assert vs_row is not None and vs_row.completed_at is not None
    _ok(f"go_live: ValidationSession.completed_at = {vs_row.completed_at}")


async def _run_mode1_mock(
    session: AsyncSession, ids: dict[str, str]
) -> tuple[str, str]:
    """Run Mode 1 mock scenario. Returns (session_id, n2_id)."""
    coo_id = ids["coo_id"]
    n1a_id = ids["n1a_id"]
    n2_id = ids["n2_id"]

    coo_extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": coo_id,
                    "fields": {"name": "Robin"},
                    "skills_to_add": [],
                    "skills_to_remove": [],
                    "skills_to_update": [],
                }
            ]
        }
    )
    n1a_extraction = json.dumps({"agent_updates": []})

    mode1_client = _make_mock_client(
        "Hi, I'm Jordan, your COO.",
        "Sure, I'll rename myself to Robin.",
        coo_extraction,
        "Hi, I'm Alex, Finance Lead.",
        "Hi, I'm Sam, Invoicing Specialist.",
        "Finance team is ready. Summary complete.",
        n1a_extraction,
    )
    loader = _make_stub_loader()

    _step("MODE 1 — Team setup orchestration (mock)")
    orchestrator = TeamSetupOrchestrator(mode1_client, loader, session)

    # start_session
    vs = await orchestrator.start_session()
    session_id = vs.id
    rows = (await session.exec(select(AgentValidationRecordTable))).all()
    assert len(rows) == 4, f"Expected 4 records, got {len(rows)}"
    short_id = session_id[:8]
    _ok(f"start_session: 4 validation records (1 COO + 3 N-1) | session={short_id}...")

    # COO conversation
    msg = await orchestrator.start_agent_conversation(session_id, coo_id)
    assert msg, "Expected non-empty opening message"
    _ok(f"start_agent_conversation(COO): {msg[:70]!r}")

    coo_state = await session.get(AgentStateTable, coo_id)
    assert coo_state is not None
    assert coo_state.status == str(AgentStatus.IN_MEETING_1ON1)
    _ok("COO AgentState: IN_MEETING_1ON1")

    reply_msg = await orchestrator.reply(session_id, coo_id, "Rename yourself to Robin")
    assert reply_msg, "Expected non-empty reply"
    _ok(f"reply: {reply_msg[:70]!r}")

    await orchestrator.validate_team(session_id, coo_id)
    coo_spec = await session.get(AgentSpecTable, coo_id)
    assert coo_spec is not None and coo_spec.name == "Robin"
    _ok("validate_team(COO): name updated to 'Robin'")

    coo_state_after = await session.get(AgentStateTable, coo_id)
    assert coo_state_after is not None
    assert coo_state_after.status == str(AgentStatus.PAUSED)
    _ok("COO AgentState after validation: PAUSED")

    # N-1a with N-2 traversal
    msg = await orchestrator.start_agent_conversation(session_id, n1a_id)
    assert msg, "Expected non-empty N-1a opening"
    _ok(f"start_agent_conversation(N-1a): {msg[:70]!r}")

    n2_intro = await orchestrator.complete_current_agent(session_id, n1a_id)
    assert n2_intro, "Expected N-2 opening message"
    _ok(f"complete_current_agent → N-2 opened: {n2_intro[:70]!r}")

    n1a_rec = (
        await session.exec(
            select(AgentValidationRecordTable).where(
                AgentValidationRecordTable.root_agent_id == n1a_id
            )
        )
    ).first()
    assert n1a_rec is not None
    n1a_stack: list[Any] = json.loads(n1a_rec.navigation_stack)
    assert len(n1a_stack) == 2
    _ok(f"navigation_stack after N-2 opened: {n1a_stack}")

    n2_state = await session.get(AgentStateTable, n2_id)
    assert n2_state is not None
    assert n2_state.status == str(AgentStatus.IN_MEETING_1ON1)
    _ok("N-2 AgentState: IN_MEETING_1ON1")

    summary = await orchestrator.complete_current_agent(session_id, n1a_id)
    assert summary, "Expected summary message"
    _ok(f"complete_current_agent → N-2 leaf, root summary: {summary[:70]!r}")

    n1a_rec2 = (
        await session.exec(
            select(AgentValidationRecordTable).where(
                AgentValidationRecordTable.root_agent_id == n1a_id
            )
        )
    ).first()
    assert n1a_rec2 is not None
    assert json.loads(n1a_rec2.navigation_stack) == []
    _ok("navigation_stack == [] (subtree exhausted)")

    await orchestrator.validate_team(session_id, n1a_id)
    _ok("validate_team(N-1a): completed")

    # Interruption simulation: destroy and recreate orchestrator
    _step("Interruption simulation")
    del orchestrator
    fresh_loader = _make_stub_loader()
    orchestrator2 = TeamSetupOrchestrator(mode1_client, fresh_loader, session)
    resumed = await orchestrator2.resume_session()
    assert resumed is not None and resumed.id == session_id
    _ok(f"resume_session: session {session_id[:8]}... recovered (2 records pending)")

    # skip_all remaining N-1 records (N-1b + N-1c)
    _step("skip_all (N-1b + N-1c pending)")
    await orchestrator2.skip_all(session_id)
    _ok("skip_all: N-1b + N-1c skipped, go_live triggered")

    await _assert_go_live(session, session_id)

    return session_id, n2_id


async def _run_mode2_mock(session: AsyncSession, n2_id: str) -> None:
    """Run Mode 2 mock scenario using n2 from the post-go_live org."""
    _step("MODE 2 — Direct agent reconfiguration (mock)")

    n2_extraction = json.dumps(
        {
            "agent_updates": [
                {
                    "agent_id": n2_id,
                    "fields": {"work_hours": "08:00-20:00"},
                    "skills_to_add": [],
                    "skills_to_remove": [],
                    "skills_to_update": [],
                }
            ]
        }
    )
    mode2_client = _make_mock_client(
        "Hi, I'm Sam, Invoicing Specialist.",
        "Noted, work hours updated.",
        n2_extraction,
    )
    loader = _make_stub_loader()

    reconf = AgentReconfiguration(n2_id, mode2_client, loader, session)

    greeting = await reconf.start()
    assert greeting, "Expected non-empty greeting"
    _ok(f"start: {greeting[:70]!r}")

    n2_state = await session.get(AgentStateTable, n2_id)
    assert n2_state is not None
    assert n2_state.status == str(AgentStatus.IN_MEETING_1ON1)
    _ok("N-2 AgentState: IN_MEETING_1ON1")

    reply = await reconf.reply("Update work_hours to 08:00-20:00")
    assert reply, "Expected non-empty reply"
    _ok(f"reply: {reply[:70]!r}")

    await reconf.apply_changes()

    n2_spec = await session.get(AgentSpecTable, n2_id)
    assert n2_spec is not None and n2_spec.work_hours == "08:00-20:00"
    _ok("apply_changes: work_hours updated to '08:00-20:00'")

    n2_state_after = await session.get(AgentStateTable, n2_id)
    assert n2_state_after is not None
    # Prior status was IDLE (go_live set it); expect restored to IDLE
    assert n2_state_after.status == str(AgentStatus.IDLE)
    _ok("N-2 AgentState restored to IDLE (prior value)")


async def _run_real(session: AsyncSession, ids: dict[str, str]) -> None:
    """Real mode: live LLM calls, prints conversation to stdout."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    backend_dir = Path(__file__).parent.parent
    prompts_dir = backend_dir / "adjents" / "prompts"
    loader = PromptLoader(prompts_dir)
    client = AnthropicClient(api_key=api_key, model="claude-sonnet-4-6")

    coo_id = ids["coo_id"]
    n1a_id = ids["n1a_id"]
    n2_id = ids["n2_id"]

    # MODE 1
    _step("MODE 1 — Team setup orchestration (real LLM)")
    orchestrator = TeamSetupOrchestrator(client, loader, session)
    vs = await orchestrator.start_session()
    session_id = vs.id
    print(f"  Session: {session_id}")

    _hr()
    print("[COO]")
    opening = await orchestrator.start_agent_conversation(session_id, coo_id)
    print(f"COO: {opening}")

    _hr()
    print("User: What are your main responsibilities?")
    reply = await orchestrator.reply(
        session_id, coo_id, "What are your main responsibilities?"
    )
    print(f"COO: {reply}")

    _hr()
    print("[Validating COO — no changes requested]")
    await orchestrator.validate_team(session_id, coo_id)
    print("COO validated.")

    _hr()
    print("[N-1a Finance Lead + N-2 Invoicing]")
    opening = await orchestrator.start_agent_conversation(session_id, n1a_id)
    print(f"N-1a: {opening}")

    _hr()
    print("User: [completing — advance to next agent]")
    next_msg = await orchestrator.complete_current_agent(session_id, n1a_id)
    print(f"Next: {next_msg}")

    _hr()
    print("User: [completing — finish subtree]")
    summary = await orchestrator.complete_current_agent(session_id, n1a_id)
    print(f"Summary: {summary}")

    _hr()
    print("[Validating N-1a team — no changes requested]")
    await orchestrator.validate_team(session_id, n1a_id)
    print("N-1a validated.")

    _hr()
    print("[skip_all remaining records — go live]")
    await orchestrator.skip_all(session_id)
    print("All remaining records skipped. Org is now live.")

    # MODE 2
    _step("MODE 2 — Direct agent reconfiguration on N-2 (real LLM)")
    reconf = AgentReconfiguration(n2_id, client, loader, session)
    greeting = await reconf.start()
    print(f"N-2: {greeting}")

    _hr()
    user_msg = "What are your current work hours? Can you extend them to 08:00-20:00?"
    print(f"User: {user_msg}")
    response = await reconf.reply(user_msg)
    print(f"N-2: {response}")

    _hr()
    print("[Applying changes]")
    await reconf.apply_changes()
    n2_spec = await session.get(AgentSpecTable, n2_id)
    if n2_spec is not None:
        print(f"N-2 work_hours in DB: {n2_spec.work_hours}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test — team setup.")
    parser.add_argument("--real", action="store_true", help="Use real Anthropic API")
    args = parser.parse_args()

    if args.real:
        _load_env()

    engine, session = await _setup_db()

    try:
        _hr("=")
        print("Smoke test — Post-generation team setup")
        _hr("=")

        ids = await _seed_org(session)
        print(
            f"Org seeded: COO={ids['coo_id'][:8]}... "
            f"| N-1a={ids['n1a_id'][:8]}... "
            f"| N-1b={ids['n1b_id'][:8]}... "
            f"| N-1c={ids['n1c_id'][:8]}..."
        )

        if args.real:
            await _run_real(session, ids)
        else:
            _, n2_id = await _run_mode1_mock(session, ids)
            await _run_mode2_mock(session, n2_id)

        _hr("=")
        print("All checks passed.")
        _hr("=")

    finally:
        await session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
