"""T2 tests: _advance_traversal and _build_agent_context_message pure helpers."""

from datetime import UTC, datetime

from adjents.agents.models import AgentSpec, Skill
from adjents.generator.team_setup import (
    _advance_traversal,
    _build_agent_context_message,
)


def _make_spec(agent_id: str, name: str = "Agent") -> AgentSpec:
    return AgentSpec(
        id=agent_id,
        name=name,
        level=1,
        parent_id=None,
        domain=None,
        role_description=f"Role of {name}",
        responsibilities=[],
        skill_ids=[],
        escalation_rules=[],
        scheduler_interval_seconds=900,
        work_hours="09:00-18:00",
        is_paused=True,
        visual_character="character_suit",
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
    )


def _make_skill(skill_id: str, name: str) -> Skill:
    return Skill(
        id=skill_id,
        name=name,
        description=f"Desc of {name}",
        inputs=[],
        outputs=[],
        requires_human_review=False,
    )


# ---------------------------------------------------------------------------
# _advance_traversal
# ---------------------------------------------------------------------------


def test_advance_traversal_descends_to_first_child() -> None:
    child_a = _make_spec("a")
    child_b = _make_spec("b")
    children_by_parent = {"root": [child_a, child_b]}

    next_agent, stack, visited = _advance_traversal(
        "root", ["root"], [], children_by_parent
    )

    assert next_agent is not None
    assert next_agent.id == "a"
    assert stack == ["root", "a"]
    assert visited == []


def test_advance_traversal_visits_all_depth_first() -> None:
    child_a = _make_spec("a")
    child_b = _make_spec("b")
    children_by_parent: dict[str, list[AgentSpec]] = {
        "root": [child_a, child_b],
        "a": [],
        "b": [],
    }

    # Step 1: root → a
    next1, stack1, visited1 = _advance_traversal(
        "root", ["root"], [], children_by_parent
    )
    assert next1 is not None and next1.id == "a"

    # Step 2: a (leaf) → b
    next2, stack2, visited2 = _advance_traversal(
        "a", stack1, visited1, children_by_parent
    )
    assert next2 is not None and next2.id == "b"
    assert "a" in visited2

    # Step 3: b (leaf) → exhausted
    next3, stack3, visited3 = _advance_traversal(
        "b", stack2, visited2, children_by_parent
    )
    assert next3 is None
    assert stack3 == []
    assert "b" in visited3
    assert "root" in visited3


def test_advance_traversal_backtracks_from_leaf() -> None:
    child_a = _make_spec("a")
    child_b = _make_spec("b")
    children_by_parent: dict[str, list[AgentSpec]] = {
        "root": [child_a, child_b],
        "a": [],
        "b": [],
    }

    # a (leaf) completes; should backtrack to root and visit b
    next_agent, stack, visited = _advance_traversal(
        "a", ["root", "a"], [], children_by_parent
    )
    assert next_agent is not None
    assert next_agent.id == "b"
    assert "a" in visited


def test_advance_traversal_returns_none_when_exhausted() -> None:
    children_by_parent: dict[str, list[AgentSpec]] = {"leaf": []}

    next_agent, _, _ = _advance_traversal("leaf", ["leaf"], [], children_by_parent)
    assert next_agent is None


def test_advance_traversal_stack_empty_when_exhausted() -> None:
    children_by_parent: dict[str, list[AgentSpec]] = {"leaf": []}

    _, stack, _ = _advance_traversal("leaf", ["leaf"], [], children_by_parent)
    assert stack == []


def test_advance_traversal_visited_includes_all_nodes() -> None:
    a = _make_spec("a")
    b = _make_spec("b")
    children_by_parent: dict[str, list[AgentSpec]] = {
        "root": [a, b],
        "a": [],
        "b": [],
    }

    _, stack1, visited1 = _advance_traversal("root", ["root"], [], children_by_parent)
    _, stack2, visited2 = _advance_traversal("a", stack1, visited1, children_by_parent)
    _, _, visited3 = _advance_traversal("b", stack2, visited2, children_by_parent)

    assert set(visited3) == {"a", "b", "root"}


def test_advance_traversal_leaf_n1_no_children() -> None:
    children_by_parent: dict[str, list[AgentSpec]] = {}

    next_agent, stack, _ = _advance_traversal("n1", ["n1"], [], children_by_parent)
    assert next_agent is None
    assert stack == []


def test_advance_traversal_coo_only_org() -> None:
    children_by_parent: dict[str, list[AgentSpec]] = {}

    next_agent, stack, _ = _advance_traversal("coo", ["coo"], [], children_by_parent)
    assert next_agent is None
    assert stack == []


def test_advance_traversal_navigation_stack_empty_after_final_call() -> None:
    a = _make_spec("a")
    children_by_parent: dict[str, list[AgentSpec]] = {"root": [a], "a": []}

    _, s1, v1 = _advance_traversal("root", ["root"], [], children_by_parent)
    _, stack, _ = _advance_traversal("a", s1, v1, children_by_parent)
    assert stack == []


# ---------------------------------------------------------------------------
# _build_agent_context_message
# ---------------------------------------------------------------------------


def test_build_agent_context_message_includes_agent_uuid() -> None:
    agent = _make_spec("uuid-1234-5678")
    skill = _make_skill("sk1", "Analysis")
    msg = _build_agent_context_message(agent, [skill], [], {})
    assert "uuid-1234-5678" in msg


def test_build_agent_context_message_includes_skill_names() -> None:
    agent = _make_spec("agent-id")
    skills = [_make_skill("sk1", "Analysis"), _make_skill("sk2", "Reporting")]
    msg = _build_agent_context_message(agent, skills, [], {})
    assert "Analysis" in msg
    assert "Reporting" in msg


def test_build_agent_context_message_no_reports_section_for_leaf() -> None:
    agent = _make_spec("agent-id")
    msg = _build_agent_context_message(agent, [], [], {})
    assert "direct report" not in msg.lower()


def test_build_agent_context_message_direct_reports_full_config() -> None:
    agent = _make_spec("root-id")
    report = AgentSpec(
        id="report-id",
        name="Sam",
        level=2,
        parent_id="root-id",
        domain="Finance",
        role_description="Invoicing Specialist",
        responsibilities=["Track invoices", "Flag overdue payments"],
        skill_ids=["sk1"],
        escalation_rules=["Escalate if overdue > 30d"],
        scheduler_interval_seconds=1800,
        work_hours="08:00-20:00",
        is_paused=True,
        visual_character="character_analyst",
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
    )
    report_skill = Skill(
        id="sk1",
        name="Tracking",
        description="Tracks payment status.",
        inputs=[],
        outputs=[],
        requires_human_review=True,
    )
    msg = _build_agent_context_message(
        agent, [], [report], {"report-id": [report_skill]}
    )
    assert "Sam" in msg
    assert "Invoicing Specialist" in msg
    assert "Track invoices" in msg
    assert "Flag overdue payments" in msg
    assert "Tracking" in msg
    assert "requires review" in msg
    assert "08:00-20:00" in msg
    assert "1800" in msg
    assert "Escalate if overdue > 30d" in msg
