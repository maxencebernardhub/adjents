"""Smoke test — Generator Agent org generation.

Linked feature : feat/generator-org-generation
Key files      : adjents/generator/org_generation.py
                 adjents/prompts/generator/org_generation.md

Generates a complete agent org for Sophie Dubois Creations using the real
Anthropic API (model chosen by LLMRouter.get_generator_client()) and verifies
the result against minimum size thresholds. Uses an in-memory SQLite DB — does
not touch data/adjents.db. Makes paid API calls.

Usage (from backend/):
    uv run python scripts/smoke_generator_org.py [--llm-debug]

Requirements:
    ANTHROPIC_API_KEY set in .env (backend/ or project root) or in environment.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from _common import LLM_DEBUG_HELP, configure_llm_logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

# Register all SQLModel tables before create_all
import adjents.db.tables  # noqa: F401, E402
from adjents.db.tables import AgentSpecTable, AgentStateTable
from adjents.generator.models import BusinessContext
from adjents.generator.org_generation import (
    VALID_VISUAL_CHARACTERS,
    GeneratorOrgGeneration,
)
from adjents.llm.errors import LLMResponseError
from adjents.prompts.loader import PromptLoader
from adjents.router.router import LLMConfigError, LLMRouter

_WIDTH = 72


def _hr(char: str = "─") -> None:
    print(char * _WIDTH)


def _load_env() -> None:
    backend_env = Path(__file__).parent.parent / ".env"
    root_env = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(backend_env)
    load_dotenv(root_env, override=False)


def _make_sophie_context() -> BusinessContext:
    return BusinessContext(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        business_name="Sophie Dubois Creations",
        founder_name="Sophie Dubois",
        language="en",
        core_activity=(
            "Independent artist and maker specializing in handcrafted jewelry. "
            "Sells online (Shopify, B2C), runs live crafting workshops "
            "and video courses (Teachable), and organizes B2B corporate "
            "team-building workshops. "
            "Active presence on YouTube and Instagram."
        ),
        legal_status="Sole proprietorship (DBA)",
        target_clients=[
            "B2C buyers of handcrafted jewelry (US market)",
            "Creative learners enrolled in online courses",
            "US companies seeking unique corporate team-building experiences (B2B)",
        ],
        domains_with_human_coverage=[],
        domains_to_staff=[
            "E-commerce",
            "Digital Marketing",
            "Content Creation & Publishing",
            "Social Media Management",
            "Online Education",
            "B2B Sales",
            "Finance & Accounting",
            "Operations & Logistics",
            "Customer Service",
            "Tech & Automation",
        ],
        tasks_to_delegate=[
            # E-commerce
            "Shopify product listings management (inventory, pricing, descriptions)",
            "Order fulfillment tracking and carrier coordination",
            "E-commerce sales analytics and conversion reporting",
            # Digital Marketing
            "Meta Ads and Google Ads campaign management (budgets, targeting)",
            "Email marketing via Mailchimp (newsletters, automated sequences)",
            # Content Creation & Publishing
            "YouTube video publishing and SEO optimization (titles, thumbnails)",
            "Blog posts, newsletters, and long-form written content creation",
            # Social Media Management
            "Instagram feed and Stories scheduling and caption writing",
            "Community management (comments and DMs across platforms)",
            # Online Education
            "Teachable course management (enrollments, updates, promotions)",
            "Student support (progress tracking, Q&A, satisfaction surveys)",
            # B2B Sales
            "Corporate workshop prospecting (outreach, LinkedIn, first contact)",
            "Quote drafting, proposal preparation, and B2B contract follow-up",
            # Finance & Accounting
            "Monthly invoicing and Stripe payment reconciliation",
            "Quarterly expense tracking and per-channel profitability analysis",
            "Quarterly estimated tax computation and payment reminders",
            # Operations & Logistics
            "Shipping carrier management and delivery tracking for jewelry orders",
            "Raw materials and supplies procurement (beads, wire, packaging)",
            # Customer Service
            "Customer email support and refund request processing",
            "Review management and post-purchase follow-up sequences",
            # Tech & Automation
            "Zapier/Make integrations maintenance (Shopify, Mailchimp workflows)",
            "Website maintenance, performance monitoring, and tool management",
        ],
        tasks_user_keeps=[
            "Making the jewelry",
            "Live facilitation of workshops and courses",
            "Designing new product lines and collections",
        ],
        financial_goals=(
            "Revenue target: $100,000/year. "
            "Net margin > 50% on jewelry, > 70% on courses and workshops. "
            "Fixed costs: ~$1,000/month (materials, tools, software subscriptions)."
        ),
        existing_tools=[
            "Shopify",
            "Teachable",
            "Stripe",
            "Mailchimp",
            "Meta Ads",
            "Google Ads",
            "Notion",
            "Canva",
            "Later",
            "Google Analytics",
            "Zoom",
        ],
        autonomy_preference=(
            "Maximum autonomy on routine tasks. "
            "Human approval required for anything involving money (>$100), "
            "personalized client communications, or pricing changes."
        ),
        work_hours="09:00-22:00",
        additional_context=(
            "Sophie operates fully solo with no employees. "
            "Immediate priority: automate marketing and order management "
            "to free up creative time."
        ),
        created_at=datetime.now(UTC),
    )


def _print_org_tree(rows: list[AgentSpecTable]) -> None:
    """Print a text org-chart: COO → N-1s → N-2s."""
    by_parent: dict[str | None, list[AgentSpecTable]] = {}
    for row in rows:
        by_parent.setdefault(row.parent_id, []).append(row)

    def _print_node(node: AgentSpecTable, indent: int) -> None:
        prefix = "  " * indent + ("└─ " if indent > 0 else "")
        domain = f" [{node.domain}]" if node.domain else ""
        print(f"{prefix}{node.name}{domain}  (L{node.level}, {node.visual_character})")
        for child in sorted(by_parent.get(node.id, []), key=lambda r: r.name):
            _print_node(child, indent + 1)

    coos = [r for r in rows if r.level == 0]
    for coo in coos:
        _print_node(coo, 0)


def _print_agent_details(
    rows: list[AgentSpecTable],
    skill_lookup: dict[str, Any],
) -> None:
    """Print a detailed card for each agent, sorted by level then name."""
    for row in sorted(rows, key=lambda r: (r.level, r.name)):
        domain = f" [{row.domain}]" if row.domain else ""
        _hr()
        print(f"[L{row.level}] {row.name}{domain}")
        print(f"  role     : {row.role_description}")
        hours = row.work_hours or "always active"
        print(f"  schedule : every {row.scheduler_interval_seconds}s | {hours}")

        responsibilities: list[str] = json.loads(row.responsibilities)
        if responsibilities:
            print("  responsibilities:")
            for resp in responsibilities:
                print(f"    • {resp}")

        skill_ids: list[str] = json.loads(row.skill_ids)
        if skill_ids:
            print("  skills:")
            for i, sid in enumerate(skill_ids, 1):
                sk = skill_lookup.get(sid)
                if sk is None:
                    continue
                review = "yes ⚠" if sk.requires_human_review else "no"
                print(f"    [{i}] {sk.name}  [review: {review}]")
                print(f"        {sk.description}")
                ins = ", ".join(sk.inputs) if sk.inputs else "—"
                outs = ", ".join(sk.outputs) if sk.outputs else "—"
                print(f"        in  : {ins}")
                print(f"        out : {outs}")

        escalation_rules: list[str] = json.loads(row.escalation_rules)
        if escalation_rules:
            print("  escalation:")
            for rule in escalation_rules:
                print(f"    • {rule}")


async def run() -> None:
    parser = argparse.ArgumentParser(description="Generator Agent org smoke")
    parser.add_argument("--llm-debug", action="store_true", help=LLM_DEBUG_HELP)
    configure_llm_logging(parser.parse_args().llm_debug)
    _load_env()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set. Add it to .env or export it.")
        sys.exit(1)

    try:
        client = LLMRouter(anthropic_api_key=api_key).get_generator_client()
    except LLMConfigError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    print()
    _hr("═")
    print("  Smoke test — Generator Agent Org Generation")
    print(f"  Model: {client.model}  |  Persona: Sophie Dubois Creations")
    _hr("═")
    print()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    prompts_dir = Path(__file__).parent.parent / "adjents" / "prompts"
    loader = PromptLoader(prompts_dir)

    context = _make_sophie_context()
    print("  Calling LLM… (high effort: this may take a few minutes)")
    print()

    agent_count = 0

    def _on_agent_ready(name: str, level: int) -> None:
        nonlocal agent_count
        agent_count += 1
        label = "COO" if level == 0 else f"L{level}"
        print(f"  {agent_count:>2}. {name}  ({label})", flush=True)

    async with AsyncSession(engine) as session:
        gen = GeneratorOrgGeneration(client, loader, session)
        try:
            result = await gen.generate(context, on_agent_ready=_on_agent_ready)
        except LLMResponseError as exc:
            print(f"\nERROR during generate(): {type(exc).__name__}: {exc}")
            sys.exit(1)

        # ── Fetch DB rows for verification ────────────────────────────────
        spec_rows = (await session.exec(select(AgentSpecTable))).all()
        state_rows = (await session.exec(select(AgentStateTable))).all()

    await engine.dispose()

    # ── Verification assertions (print, not pytest) ────────────────────────
    failures: list[str] = []

    n1_agents = [s for s in spec_rows if s.level == 1]
    n2_agents = [s for s in spec_rows if s.level == 2]
    total_skills = len(result.skills)
    expected_n1 = len(context.domains_to_staff)

    # N-1 count must match the number of domains to staff (±1 tolerance for
    # legitimate merges when two listed domains significantly overlap).
    if len(n1_agents) < expected_n1 - 1:
        failures.append(
            f"N-1 agents: {len(n1_agents)} (expected ≥ {expected_n1 - 1}"
            f" for {expected_n1} domains)"
        )
    # N-2 count is informational only — N-1 leaf nodes are valid by design.
    # The N-1 interviews will refine the org and spawn additional specialists.
    # Skills: proportional threshold — 1.5 × total agents, so the check stays
    # meaningful regardless of org size (leaf N-1s, varying N-2 counts, etc.).
    min_skills = int(1.5 * len(spec_rows))
    if total_skills < min_skills:
        failures.append(f"Skills: {total_skills} (expected ≥ {min_skills})")

    # All visual_characters must be valid
    invalid_vc = [
        r for r in spec_rows if r.visual_character not in VALID_VISUAL_CHARACTERS
    ]
    if invalid_vc:
        failures.append(f"Invalid visual_character on: {[r.name for r in invalid_vc]}")

    # All AgentState rows must be paused
    non_paused = [r for r in state_rows if r.status != "paused"]
    if non_paused:
        failures.append(f"Non-paused states: {[r.agent_id for r in non_paused]}")

    skill_lookup: dict[str, Any] = {s.id: s for s in result.skills}

    # ── Results ────────────────────────────────────────────────────────────
    print()
    _hr("═")
    print("  Org tree")
    _hr()
    _print_org_tree(list(spec_rows))

    print()
    _hr()
    print(f"  Total agents  : {len(spec_rows)}")
    print(f"  N-1 agents    : {len(n1_agents)}")
    print(f"  N-2 agents    : {len(n2_agents)}")
    print(f"  Total skills  : {total_skills}")
    print(f"  Agent states  : {len(state_rows)} (all paused: {not non_paused})")

    print()
    if failures:
        _hr("═")
        print("  ✗ VERIFICATION FAILURES:")
        for f in failures:
            print(f"    • {f}")
        _hr("═")
        sys.exit(1)
    else:
        _hr("═")
        print("  ✓ All assertions passed")
        _hr("═")

    print()
    _hr("═")
    print("  Agent details")
    _hr("═")
    _print_agent_details(list(spec_rows), skill_lookup)
    _hr()
    print()


if __name__ == "__main__":
    asyncio.run(run())
