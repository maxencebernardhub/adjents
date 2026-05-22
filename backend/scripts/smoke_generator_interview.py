"""Smoke test — Generator Agent interview.

Linked feature : feat/generator-agent-interview
Key files      : adjents/generator/interview.py
                 adjents/prompts/generator/interview.md
                 adjents/prompts/generator/extract_business_context.md

Runs a scripted conversation with the real Anthropic API (claude-opus-4-7)
and verifies that a BusinessContext is produced at the end.
Uses an in-memory SQLite DB — does not touch data/adjents.db.

Usage (from backend/):
    uv run python scripts/smoke_generator_interview.py

Requirements:
    ANTHROPIC_API_KEY set in .env (backend/ or project root) or in environment.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

# Register all SQLModel tables before create_all
import adjents.db.tables  # noqa: F401, E402
from adjents.db.convert import business_context_from_table
from adjents.db.tables import BusinessContextTable
from adjents.generator.interview import GeneratorInterview, InterviewError
from adjents.prompts.loader import PromptLoader
from adjents.router.router import LLMConfigError, LLMRouter

# --- Scripted turns (Alex Chen scenario from the roleplay spec) ---
# Reference: docs/specs/2026-05-20-generator-agent-interview-roleplay.md

_SCRIPTED_TURNS = [
    (
        "Hi, I'm Alex Chen. I'm a salaried UX designer specialised in mobile apps "
        "(iOS / Android) and I want to go freelance."
    ),
    (
        "I've worked on mobile app redesigns for 3 years, about 30 releases. "
        "I use Figma, Miro, Sketch, and Hotjar. "
        "Clients were internal B2C product teams."
    ),
    (
        "I'd like to target startups mainly, but I'm open to SMEs and agencies. "
        "I'm scared of everything non-design: admin, accounting, invoicing, "
        "prospecting, and LinkedIn communication."
        "I live in Paris and would like to work with french companies only."
    ),
    (
        "A friend advised auto-entrepreneur status. "
        "I have about 200 LinkedIn contacts. "
        "I want to start now, working evenings 18:00-23:00 (weekdays only) "
        "while keeping my day job."
    ),
    (
        "For external communications (prospects, clients) I want to validate first. "
        "For everything else agents can go fully autonomous. "
        "My goal is at least 2000€ net per month; fixed costs are about 1000€/month."
    ),
    (
        "No one else covers those domains. "
        "Oh — I'd like to call my company Luminescence. "
        "I think that's everything."
    ),
    (
        "For prospecting: find and qualify startup leads, draft outreach messages "
        "for my review. "
        "For LinkedIn: draft posts about UX twice a week for my approval. "
        "For admin and accounting: issue invoices, chase late payments, "
        "handle URSSAF declarations and track expenses."
    ),
]

# Fallback closing answers used if the interview is not complete after _SCRIPTED_TURNS
_CLOSING_TURNS = [
    "Nothing else to add for now.",
    "No, I think we've covered all the domains I want to delegate.",
    "Yes, I'm ready to build my team!",
]

_WIDTH = 72


def _hr(char: str = "─") -> None:
    print(char * _WIDTH)


def _print_turn(label: str, text: str) -> None:
    print()
    _hr()
    print(f"  {label}")
    _hr()
    print(text)


def _load_env() -> None:
    backend_env = Path(__file__).parent.parent / ".env"
    root_env = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(backend_env)
    load_dotenv(root_env, override=False)


async def run() -> None:
    _load_env()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set. Add it to .env or export it.")
        sys.exit(1)

    total_turns = len(_SCRIPTED_TURNS) + len(_CLOSING_TURNS)
    print()
    _hr("═")
    print("  Smoke test — Generator Agent Interview")
    print(f"  Model: claude-opus-4-7  |  Max turns: {total_turns}")
    _hr("═")

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    prompts_dir = Path(__file__).parent.parent / "adjents" / "prompts"
    loader = PromptLoader(prompts_dir)

    try:
        client = LLMRouter(anthropic_api_key=api_key).get_generator_client()
    except LLMConfigError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    async with AsyncSession(engine) as session:
        interview = GeneratorInterview(client, loader, session)

        try:
            opening = await interview.start()
        except InterviewError as exc:
            print(f"\nERROR during start(): {exc}")
            sys.exit(1)

        _print_turn("Agent  (opening)", opening)
        completed = False

        for i, user_text in enumerate(_SCRIPTED_TURNS, 1):
            _print_turn(f"User   (turn {i})", user_text)
            try:
                response = await interview.reply(user_text)
            except InterviewError as exc:
                print(f"\nERROR on turn {i}: {exc}")
                sys.exit(1)
            _print_turn(f"Agent  (turn {i})", response.message)
            if response.missing_mandatory_info:
                print(f"\n  Still missing: {response.missing_mandatory_info}")
            if response.ready_to_generate:
                print("\n  ✓ ready_to_generate = True")
                completed = True
                break

        if not completed:
            print("\n  — Scripted turns exhausted; running closing sequence —")
            for j, closing_text in enumerate(_CLOSING_TURNS, 1):
                _print_turn(f"User   (closing {j})", closing_text)
                try:
                    response = await interview.reply(closing_text)
                except InterviewError as exc:
                    print(f"\nERROR on closing turn {j}: {exc}")
                    sys.exit(1)
                _print_turn(f"Agent  (closing {j})", response.message)
                if response.ready_to_generate:
                    print("\n  ✓ ready_to_generate = True")
                    completed = True
                    break

        print()
        _hr("═")
        rows = (await session.exec(select(BusinessContextTable))).all()
        if rows:
            bc = business_context_from_table(rows[0])
            print("  ✓ BusinessContext created")
            print(f"  business_name     : {bc.business_name}")
            print(f"  founder_name      : {bc.founder_name}")
            print(f"  language          : {bc.language}")
            print(f"  legal_status      : {bc.legal_status}")
            print(f"  domains_to_staff  : {bc.domains_to_staff}")
            print(f"  work_hours        : {bc.work_hours}")
            print(f"  tasks_to_delegate : {len(bc.tasks_to_delegate)} items")
            print(f"  conversation_id   : {bc.conversation_id}")
        else:
            print("  ✗ No BusinessContext — interview did not reach ready_to_generate.")
            print("    Extend _SCRIPTED_TURNS or _CLOSING_TURNS to cover more ground.")
            sys.exit(1)
        _hr("═")
        print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
