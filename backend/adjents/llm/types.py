"""Provider-neutral types of the LLM call contract.

Callers (Generator interview, org generation, team setup, reconfiguration) only see
these types, never a provider's own vocabulary; each LLM client maps them to its
provider's request parameters. Today only `AnthropicClient` exists; the OpenAI and
Gemini clients of step 10 implement the same contract.

Entry point: `Effort`, the type of the required `effort` argument of `complete()`.

Related ADRs: 0012 (provider-neutral LLM call contract).
"""

from typing import Literal

Effort = Literal["low", "medium", "high"]
"""How much reasoning a call may spend. Required on every call (no default), so a
change of provider or model default can never alter a call's behavior silently.
`xhigh` / `max` are left out until a measured need."""
