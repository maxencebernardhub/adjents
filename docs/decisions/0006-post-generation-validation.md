# ADR 0006 — Post-Generation Team Validation Before Go-Live

**Date**: 2026-05-22
**Status**: Accepted

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

## Consequences

**v0.1 code:**

- `generate()` persists all agents with `is_paused = True`
- New prompt: `prompts/agent/intro.md` — N-1 agent introduction script (presents self
  and direct reports; handles user questions and adjustment requests)
- The onboarding flow (frontend or API) sequences the introduction conversations after
  generation completes, then unpauses all agents on user confirmation

**Future versions:**

- In v0.2, when micro-adjustments via parent agent are supported, the intro conversation
  can already apply small spec changes (rename, skill addition) before go-live — the
  infrastructure will be the same
- The `is_active` flag planned for v0.2 (ADR 0005) is distinct: it marks agents
  deactivated by restructuring, not agents awaiting initial validation
