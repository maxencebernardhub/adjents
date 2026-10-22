"""Helpers shared by the smoke scripts (not run by pytest).

Imported as `from _common import ...`: scripts are run as
`uv run python scripts/<name>.py`, which puts `scripts/` on `sys.path`.
"""

import logging

LLM_DEBUG_HELP = (
    "print each LLM call's stop_reason, output tokens and thinking summary "
    "(summaries contain business data)"
)


def configure_llm_logging(llm_debug: bool) -> None:
    """Route log records to stderr; with *llm_debug*, show the `adjents.llm` DEBUG logs.

    Warnings (refusals, truncations) are always shown. DEBUG adds, per call, the
    usage line of `adjents.llm.anthropic_client` and the thinking summaries of the
    opt-in `adjents.llm.thinking` logger (ADR 0012) — used to calibrate `max_tokens`
    and to understand the model's choices.
    """
    logging.basicConfig(level=logging.WARNING, format="  [%(name)s] %(message)s")
    if llm_debug:
        logging.getLogger("adjents.llm").setLevel(logging.DEBUG)
