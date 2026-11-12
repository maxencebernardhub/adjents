"""Minimal LLM router — the only place where a model is chosen (architecture rule 4).

Serves the two system roles that exist today: the Generator Agent (interview,
`BusinessContext` extraction, org generation) and post-generation team setup /
reconfiguration. Callers ask for a client per role and never name a model.

Interim design: one `get_*_client()` method per role, Anthropic only. Step 10
replaces it with request-based routing across Anthropic / OpenAI / Gemini / Ollama
(complexity, sensitivity, agent reasoning tier, concurrency).

Place in the flow: today only the smoke scripts build a router; the orchestrators
(interview, org generation, team setup, reconfiguration) receive the client it hands
out, injected by their caller.

Entry points: `LLMRouter` (`get_generator_client()`, `get_team_setup_client()`),
`LLMConfigError`.

Related ADRs: 0008 (team setup routing, amended), 0012 (LLM call contract).
"""

import os
import string

from adjents.llm.anthropic_client import AnthropicClient

_GENERATOR_MODEL = "claude-opus-5-5"
_TEAM_SETUP_MODEL = "claude-sonnet-5-5"

# Printable ASCII without space. A key holding anything else is rejected before it
# reaches the SDK: the HTTP layer refuses a header holding a newline and quotes the
# whole header value, key included, in the exception chain it raises.
_KEY_CHARACTERS = frozenset(string.printable) - frozenset(string.whitespace)


class LLMConfigError(Exception):
    """No LLM provider can be configured from the API key that was found.

    Raised by `LLMRouter` at construction, before any request is sent, when no
    Anthropic API key is found or when the key holds characters an API key never
    contains. The message names no key value.
    """


class LLMRouter:
    """Hands out one LLM client per system role; the only place a model is chosen.

    Both clients are built at construction and share the same API key; each
    `get_*_client()` call returns the same instance. Only the key's characters are
    checked here: a well-formed but invalid key fails at the first request, with
    the SDK's own error.

    The API key is resolved in this order:

    1. `anthropic_api_key`, when it is a non-empty string;
    2. otherwise the `ANTHROPIC_API_KEY` variable of the process environment. The
       router does not read `.env` files: loading one is the caller's job (today
       the smoke scripts do it).

    Whitespace around the resolved key is stripped (a quoted dotenv value or a
    shell export can carry a trailing space or newline). A whitespace-only direct
    key does not fall back to the environment: it is rejected.

    Args:
        anthropic_api_key: Anthropic API key. None or "" falls back to the
            environment.

    Raises:
        LLMConfigError: Neither source gives a key, the key is blank once
            stripped, or it holds a space, a control or a non-ASCII character.
    """

    def __init__(self, anthropic_api_key: str | None = None) -> None:
        key = (anthropic_api_key or os.getenv("ANTHROPIC_API_KEY") or "").strip()
        if not key:
            raise LLMConfigError(
                "No LLM provider configured. Set ANTHROPIC_API_KEY in .env."
            )
        if not set(key) <= _KEY_CHARACTERS:
            raise LLMConfigError(
                "The Anthropic API key contains whitespace, control or non-ASCII "
                "characters."
            )
        self._generator_client = AnthropicClient(api_key=key, model=_GENERATOR_MODEL)
        self._team_setup_client = AnthropicClient(api_key=key, model=_TEAM_SETUP_MODEL)

    def get_generator_client(self) -> AnthropicClient:
        """Client for the Generator Agent: frontier quality for one-shot work."""
        return self._generator_client

    def get_team_setup_client(self) -> AnthropicClient:
        """Client for team setup and reconfiguration conversations + extraction."""
        return self._team_setup_client
