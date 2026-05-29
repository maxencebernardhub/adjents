# ADR 0006 — Post-Generation Team Validation Before Go-Live

**Date**: 2026-05-22
**Status**: Accepted — Full design added 2026-05-28

---

## Context

After the Generator Agent produces an `AgentSpec` hierarchy, the org could technically
start running immediately. However, no LLM-generated org is perfect on the first pass:
responsibilities may be slightly off, skills may miss something obvious, work hours may
not reflect the user's real schedule. If agents act autonomously before the user has
reviewed their configuration, the first actions may be wrong — and trust in the product
is hard to rebuild once lost.

A decision is needed on: when do agents transition from "just created" to "active", and
who is responsible for that transition?

---

## Decision

### Agents are created with `is_paused = True`

All agents produced by `GeneratorOrgGeneration.generate()` are persisted with
`is_paused = True`. Their autonomous loop does not start until explicitly unpaused.
No separate `is_validated` field is introduced — `is_paused` serves as the guard in
v0.1, keeping the model unchanged.

### The user meets each N-1 agent one-on-one before go-live

After org generation, the user is invited (not forced) to have a short introduction
conversation with each N-1 agent. In each conversation:

- The N-1 agent presents itself: role, responsibilities, skills, work hours
- The N-1 agent presents its direct reports (N-2 and below): same summary per agent
- The user can ask questions, request renames, or flag adjustments
- The user says "ready" (or an equivalent) to validate

Once all N-1 agents have been validated (or the user skips), all agents transition to
`is_paused = False` and their loops start.

### N-1 agents conduct these conversations — not the Generator Agent

The Generator Agent is dormant after producing the org. Introduction conversations are
conducted by the N-1 agents themselves, using a dedicated prompt
(`prompts/agent/intro.md`). This is deliberate:

- It is the first real interaction between the user and their team — the right moment
  to establish the agent's voice and domain authority
- The Generator Agent has no operational knowledge of the org it created; it cannot
  answer "what will you actually do on Monday morning?"
- N-1 agents will be the user's primary contacts during daily use; starting that
  relationship here is natural

### The validation step is skippable

If the user skips, all agents go live immediately with their generated configuration.
This accommodates power users who trust the generation output and want to start
quickly. The validation step can also be resumed later by talking to any agent
directly.

---

## Alternatives Considered

| Alternative | Reason rejected |
| --- | --- |
| **Agents start IDLE immediately** | First autonomous actions may be wrong; trust is hard to rebuild once lost |
| **Generator Agent conducts introductions** | Generator Agent is dormant post-generation; N-1 agents have the right domain context; introduction is the first step of the operational relationship |
| **Mandatory validation (cannot skip)** | Blocks power users and re-onboarding flows; adds friction without adding safety — the user can always pause agents later |
| **Dedicated `is_validated` flag on AgentSpec** | Adds schema complexity for a boolean already covered by `is_paused`; a second flag with identical semantics at creation time creates confusion |

---

## Full design (2026-05-28)

The initial sketch above described the intent. The implementation settled on the
following concrete design.

### Two modes

**Mode 1 — Post-generation team setup (`TeamSetupOrchestrator`)**:
A guided, resumable flow where the user meets each agent before go-live.

- A `ValidationSession` is created with one `AgentValidationRecord` per COO and
  N-1 root agent (level ≤ 1).
- The COO is always the first conversation. N-1 conversations may only start after
  the COO record is validated or skipped.
- Each N-1 record uses **depth-first traversal** through its subtree. A
  `navigation_stack` (list of agent IDs, JSON-serialized) tracks the current path.
  An empty stack signals subtree completion.
- `complete_current_agent()` closes the current agent's conversation, advances the
  traversal (or returns the root's team summary if exhausted), and returns the next
  agent's opening message. It always returns a `str` — the caller detects completion
  via `record.navigation_stack == []`.
- `validate_team()` runs the extraction LLM on all conversations in the record's
  `conversation_ids`, applies updates, marks the record `VALIDATED`, and fires
  `_go_live()` if all records are done.
- `skip_agent()` / `skip_all()` mark records `SKIPPED` and fire `_go_live()`.
- `_go_live()` is atomic: sets all `AgentSpec.is_paused = False`, all
  `AgentState.status = IDLE`, and `ValidationSession.completed_at = now` in one
  DB commit.

**Mode 2 — Direct agent reconfiguration (`AgentReconfiguration`)**:
Available at any time after go-live. See ADR 0009.

### Prompts

Two new prompts in `prompts/agent/`:

- `intro.md` — system prompt for the introduction / adjustment conversation. Used
  by both modes. Model hint: `claude-sonnet-4-6`.
- `extract_agent_adjustments.md` — extraction prompt. Reads the full conversation
  transcript (delimited by `---AGENT:<uuid>---` markers) and returns a single JSON
  object with `agent_updates`. Used by both modes. Model hint: `claude-sonnet-4-6`.

The extraction pattern is documented in ADR 0008.

### Agent context injection

Agent data (`AgentSpec` + skills + direct reports with their skills) is injected as
the **first user message**, not in the system prompt. This avoids `str.format_map()`
`KeyError` on user-supplied text that may contain curly braces. Consistent with the
same decision in `generator/org_generation.py`.

### AgentState transitions during team setup

```text
[ is_paused = True ] ──► start_agent_conversation ──► IN_MEETING_1ON1
        │                                                      │
        │                                   complete_current_agent → PAUSED (current)
        │                                   next sub-agent → IN_MEETING_1ON1
        │
        │                       validate_team / skip_all
        └───────────────────────────────────────────────────► IDLE (go_live)
```

---

## Consequences

**v0.1 code:**

- `generate()` persists all agents with `is_paused = True` (unchanged)
- New prompts: `prompts/agent/intro.md` + `prompts/agent/extract_agent_adjustments.md`
- New models: `ValidationSession`, `AgentValidationRecord` (Pydantic + SQLModel tables
  and convert functions)
- `TeamSetupOrchestrator` in `generator/team_setup.py` implements Mode 1
- `AgentReconfiguration` in `agents/reconfiguration.py` implements Mode 2
- Smoke test: `scripts/smoke_team_setup.py` (mock mode + real mode)

**Future versions:**

- In v0.2, when parent-mediated governance is supported, `AgentReconfiguration` gains
  a validation layer for non-COO agents (see ADR 0005 amendment and ADR 0009)
- The `is_active` flag planned for v0.2 (ADR 0005) is distinct: it marks agents
  deactivated by restructuring, not agents awaiting initial validation
