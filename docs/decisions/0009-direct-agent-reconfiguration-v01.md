# ADR 0009 — Direct Agent Reconfiguration in v0.1

**Date**: 2026-05-27
**Status**: Accepted

---

## Context

After the org goes live, users need a way to adjust individual agent configurations:
rename an agent, update its work hours, change its responsibilities, add or remove
skills. ADR 0005 deferred "micro-adjustments" to v0.2, describing a parent-mediated
path where the user talks to an agent's parent to update its configuration.

Two questions arose:

1. **When can micro-adjustments land?** Parent-mediated reconfiguration requires agents
   to have executable actions (write to SQLite) — a v0.2 capability dependent on the
   Python sandbox. But the extraction + apply pattern from `TeamSetupOrchestrator` is
   already implemented in v0.1.

2. **What scope?** Should v0.1 allow modifying all non-structural fields, or only a
   "safe" subset?

---

## Decision

### Direct reconfiguration of all non-structural fields in v0.1

`AgentReconfiguration` (in `adjents/agents/reconfiguration.py`) allows the user to
open a conversation with any agent and adjust:

- `name`
- `role_description`
- `responsibilities`
- `work_hours`
- `scheduler_interval_seconds`
- `visual_character`
- `escalation_rules`
- Skills (add, update, remove)

The following fields are **frozen** (silently dropped from any extraction output):

- `domain` — structural, changing it changes the agent's org position
- `level` — structural, part of the hierarchy
- `parent_id` — structural, defines the reporting line

Structural changes (domain, level, parent assignment) remain deferred to v0.2 via
the Generator Agent restructuring flow (ADR 0005).

### COO exception

The COO (level=0) has no parent, so all reconfiguration goes directly against it in
both v0.1 and v0.2. The parent-mediated path introduced in v0.2 applies only to
N-1 and deeper agents.

### Parent-mediated governance deferred to v0.2

In v0.2, fields like `work_hours`, `responsibilities`, and `role_description` for
non-COO agents will gain parent-mediated governance: the N+1 agent validates whether
the requested change is coherent with the team's structure and mandate. This requires
agents to have executable tool calls (Python sandbox, v0.2).

In v0.1, there is no execution barrier, so governance is the user's own responsibility.
Direct reconfiguration is an acceptable risk at v0.1 scale (single user, no delegation).

---

## Alternatives Considered

| Alternative | Reason rejected |
| --- | --- |
| **Defer all reconfiguration to v0.2** | The extraction + apply infrastructure is already in place (ADR 0008); deferring would leave users with no way to correct generation errors after go-live |
| **Allow only name + visual_character changes** | Arbitrary subset; the extraction prompt already handles all non-structural fields; adding a whitelist adds complexity without real safety benefit at v0.1 |
| **Implement parent-mediated path in v0.1** | Requires agents to have executable tool calls — a v0.2 sandbox dependency; bypassing it with a direct write would be inconsistent with the parent-agent principle |

---

## Consequences

- `AgentReconfiguration` is the only entry point for direct reconfiguration in v0.1.
- `AgentReconfiguration` sets `AgentState.status = IN_MEETING_1ON1` at the start of
  `start()` and restores the prior status at the end of `apply_changes()`. In v0.1,
  the prior status is always `PAUSED` or `IDLE` (no active loop).
- In v0.2, once the parent-mediated path exists, `AgentReconfiguration` will be
  restricted (or supplemented) with parent validation for non-COO agents. The interface
  remains compatible — it is the governance layer that changes, not the reconfiguration
  mechanism itself.
- No FastAPI endpoint wraps `AgentReconfiguration` in v0.1 (frontend integration is
  out of scope). The class is designed for direct use from the backend API layer or
  CLI tooling.
