"""Minimal LLM router — the only place where a model is chosen (architecture rule 4).

Serves the two system roles that exist today: the Generator Agent (interview,
`BusinessContext` extraction, org generation) and post-generation team setup /
reconfiguration. Callers ask for a client per role and never name a model.

Interim design: one `get_*_client()` method per role, Anthropic only. Step 10
replaces it with request-based routing across Anthropic / OpenAI / Gemini / Ollama
(complexity, sensitivity, agent reasoning tier, concurrency).

Related ADRs: 0008 (team setup routing, amended), 0012 (LLM call contract).
"""

import os

from adjents.llm.anthropic_client import AnthropicClient

_GENERATOR_MODEL = "claude-opus-5-5"
_TEAM_SETUP_MODEL = "claude-sonnet-5-5"


class LLMConfigError(Exception): ...


class LLMRouter:
    def __init__(self, anthropic_api_key: str | None = None) -> None:
        key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise LLMConfigError(
                "No LLM provider configured. Set ANTHROPIC_API_KEY in .env."
            )
        self._generator_client = AnthropicClient(api_key=key, model=_GENERATOR_MODEL)
        self._team_setup_client = AnthropicClient(api_key=key, model=_TEAM_SETUP_MODEL)

    def get_generator_client(self) -> AnthropicClient:
        """Client for the Generator Agent: frontier quality for one-shot work."""
        return self._generator_client

    def get_team_setup_client(self) -> AnthropicClient:
        """Client for team setup and reconfiguration conversations + extraction."""
        return self._team_setup_client
