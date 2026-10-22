# ADR 0010 — Agents Are Data, Not Code

**Date**: 2026-10-22 (decision in force since project inception, 2026-05-18;
recorded retroactively)
**Status**: Accepted

---

## Context

Adjents generates a team of AI agents from a single onboarding interview. The
Generator Agent (an LLM) decides at runtime which agents exist, what they are called,
what they are responsible for and how they relate to each other. Two users never get
the same org: one may get a "Wedding Planning Lead", another a "Grant Applications
Specialist".

Hand-built multi-agent systems usually define one class per agent, because the
developer knows the team in advance. In Adjents, no agent is known before onboarding,
and the user must be able to reconfigure any agent after go-live (ADR 0009) without
a redeploy.

The principle was stated from day one in `.claude/CLAUDE.md` ("Agents are data, not
code") and is embodied in the existing code (`AgentSpec`, `GeneratorOrgGeneration`,
`AgentReconfiguration`), but its rationale and rejected alternatives were never
recorded.

---

## Decision

An agent is **data**, never a Python class. It is the set of records keyed by its
`id`:

- one `AgentSpec` row (identity, role, responsibilities, hierarchy position,
  schedule);
- its `Skill` rows;
- one `AgentState` row (runtime status);
- one namespaced Chroma collection (memory).

Prompts are shared templates per agent type (`prompts/agent/`, `prompts/coo/`),
rendered with the agent's fields. All agents run the same generic agent loop.

Special cases are expressed as data, never as a subclass: the COO is an `AgentSpec`
with `level == 0`; code that must treat it differently branches on that field.

---

## Alternatives Considered

| Option | Reason rejected |
| --- | --- |
| **One hand-written subclass per agent** (`class FinanceAgent(BaseAgent)` with its own `think()`) | Impossible: agents do not exist until the LLM invents them at onboarding. No class can be written for an agent nobody knows yet. |
| **LLM-generated Python code per agent, executed at runtime** | Arbitrary code execution on the user's machine (major security risk); generated code is untested, untyped and unreviewed; contradicts the v0.1 "no real-world execution" scope. |
| **Hybrid: generic agent + a fixed library of hand-written behavior classes** (e.g. `InvoicingBehavior`, selected by the Generator) | The library cannot anticipate open-ended business domains; it reintroduces "agents as code" for the domains it covers and creates two competing ways to express behavior. |

---

## Consequences

**Positive:**

- Creating an agent = inserting rows: the Generator outputs JSON, validated by
  Pydantic, then persisted. No code is generated or executed.
- Reconfiguring an agent = a SQL `UPDATE` (ADR 0009). No redeploy, no restart.
- One agent loop to write, type-check and test, whatever the size of the org.
- Agents are fully serializable: inspectable in the UI, auditable, restorable from
  SQLite after a restart.

**Negative:**

- Every behavioral difference between agents must be expressible through fields,
  prompts and skills; there is no escape hatch for bespoke per-agent logic.
- Agent quality rests on prompt engineering and on the quality of generated specs,
  which are harder to test than code.
- Field-based branching (e.g. `level == 0`) must stay rare and explicit, or it will
  grow into an implicit type system.

**v0.2 boundary:** skills become executable in v0.2 (Python sandbox, VISION §3.2).
This ADR holds as long as those functions are generic tools invoked by the generic
loop, with each agent's access defined by data (its skill list). Whether they are
hand-written, LLM-generated or MCP tools is a v0.2 decision, to be recorded in a new
ADR that refines or supersedes this one.
