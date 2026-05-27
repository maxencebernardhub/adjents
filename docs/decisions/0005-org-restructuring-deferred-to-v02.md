# ADR 0005 — Org Restructuring: Deferred to v0.2, Generator Agent + N-1 Consultation

**Date**: 2026-05-22
**Status**: Accepted

---

## Context

After onboarding, users will want to modify their AI organization: add missing agents,
remove agents that are no longer useful, or update the scope of existing ones. This is
a predictable need — no org design survives first contact with reality unchanged.

Two design questions arise:

1. **Who orchestrates restructuring?** The Generator Agent (meta-level) or the COO
   (operational level)?
2. **How does `generate()` handle agents that already exist?** Destroy and recreate,
   or update in place?

This feature is not in scope for v0.1, but the v0.1 implementation of `generate()`
must not close the door on it.

---

## Decision

### Deferred to v0.2

Org restructuring is explicitly out of scope for v0.1. The v0.1 `generate()` is
designed for initial onboarding only (no existing org).

### Generator Agent orchestrates restructuring — not the COO

The Generator Agent will be reactivated for restructuring interviews. The COO is
rejected as orchestrator because:

- The COO is an **operational** agent: it coordinates work, delegates tasks, and
  escalates blockers. Restructuring the org is a **meta-level** concern — it changes
  the structure the COO operates within.
- Mixing these responsibilities would blur the COO's identity and create an agent
  with conflicting mandates.
- The Generator Agent already has the right prompt design and LLM routing (frontier
  cloud) for high-quality structural decisions.

### Generator Agent consults affected N-1 (and N-2) agents

During restructuring, the Generator Agent does not only interview the user. Before
proposing structural changes, it also consults the N-1 agents (and potentially N-2
agents) whose domains are affected, via the existing message bus.

**Why:** Operational agents accumulate domain knowledge the user no longer holds in
detail. An N-1 Marketing agent may know that its N-2 Webmarketing specialist has
enough capacity to absorb paid social ads — saving the user from creating a redundant
agent. This is consistent with the "agents are autonomous, not passive" principle.

The restructuring flow (v0.2):

1. User triggers restructuring (natural language or UI button)
2. Generator Agent conducts a focused delta interview with the user
3. Generator Agent sends targeted consultation messages to affected N-1/N-2 agents
4. Generator Agent synthesizes user input + agent feedback, proposes a delta (add /
   remove / update)
5. User validates the proposal
6. Generator Agent applies the changes

### Micro-adjustments: parent agent owns team configuration (v0.2)

For small changes that do not affect the org structure (adding a skill, updating
responsibilities, changing escalation rules or work hours), the user talks to the
agent's direct parent:

- To modify an N-2 agent → conversation with its N-1 parent
- To modify an N-1 agent → conversation with the COO

The parent agent validates the change within its domain context (e.g. an N-1 Marketing
agent knows whether "paid social ads" is already covered by an existing N-2 specialist),
then applies it.

This keeps structural decisions (Generator Agent) separate from operational
configuration decisions (parent agent), and is consistent with the principle that each
agent is responsible for its own team.

This flow requires agents to have executable actions (write to SQLite) — a v0.2
capability dependent on the Python sandbox feature.

### generate() uses upsert-safe INSERT from v0.1

Even in v0.1, `generate()` must not DELETE existing agents before inserting new ones.
Agents removed from a restructured org must be **marked inactive**, not deleted —
their memory (Chroma collections, SQLite records) must survive the change.

In v0.1: no restructuring, so no conflict. But the INSERT call must not assume a
clean slate (no `DELETE FROM agent_specs` before inserting).

In v0.2: an `is_active: bool` field will be added to `AgentSpec`. Agents absent from
the new generated org are set `is_active = False`. Their loop stops, but their data
remains queryable.

---

## Alternatives Considered

| Alternative | Reason rejected |
| --- | --- |
| **COO orchestrates restructuring** | COO is operational, not meta. Mixing concerns. |
| **Full regeneration (DELETE + INSERT)** | Destroys agent memory — irreversible loss of accumulated value. |
| **User-only restructuring (no agent consultation)** | Agents have valuable domain knowledge the user may no longer track. Ignoring it produces worse structural decisions. |
| **Restructuring in v0.1** | Scope creep. The onboarding flow must be solid first. Restructuring can reuse the same Generator Agent infrastructure once it exists. |
| **Micro-adjustments via Generator Agent** | Overkill for a skill addition. The Generator Agent is a meta-level agent for structural changes; a parent agent has the right domain context for small adjustments. |

---

## Consequences

**v0.1 code constraints:**

- `generate()` in `GeneratorOrgGeneration` persists with plain INSERT (no DELETE)
- No `is_active` field yet — not needed since there are no existing agents at first run

**v0.2 additions (restructuring):**

- `is_active: bool` added to `AgentSpec` (default `True`)
- New prompt: `prompts/generator/restructuring_interview.md`
- Generator Agent sends `ConsultationRequest` messages to N-1/N-2 agents and awaits
  responses before proposing the delta
- Upsert logic in the persistence layer: new agents → INSERT; updated agents → UPDATE;
  removed agents → set `is_active = False`

**v0.2 additions (micro-adjustments):**

- Parent agent receives a `spec_update` tool call from the user conversation layer
- Tool writes the updated field to SQLite and triggers a confirmation message to the user
- New prompt section in `agent/think_and_act.md` for handling spec update requests
