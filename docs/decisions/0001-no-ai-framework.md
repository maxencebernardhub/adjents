# ADR 0001 — No AI Framework: Build Agent Logic from Scratch

**Date**: 2026-05-18
**Status**: Accepted

---

## Context

Adjents requires a multi-agent system with: an autonomous agent loop (asyncio tasks),
a typed async message bus, an N-level agent hierarchy, LLM routing across multiple
providers, and a 2D RPG workspace. Several AI frameworks exist that target multi-agent
use cases and could potentially accelerate development.

Frameworks evaluated: LangChain, LangGraph, LlamaIndex, CrewAI, AutoGen.

---

## Decision

We will **not use any AI agent framework**. The agent loop, message bus, LLM router,
and scheduler are written from scratch. We use only:

- Official LLM provider SDKs (`anthropic`, `openai`, `google-generativeai`) (see Amendment 2026-10-22)
- `httpx` for Ollama (simple REST API, no SDK needed)
- `chromadb` for vector storage
- `sqlmodel` for SQLite ORM

---

## Alternatives Considered

| Framework | Reason rejected |
| --- | --- |
| **LangChain** | Leaky abstractions, high friction, actively being abandoned by teams at scale. Coupling our architecture to LangChain would make future changes harder. |
| **LangGraph** | Built on LangChain. Models workflows as explicit graphs — the exact mental model we want to hide from users. Conflicts with our asyncio task loop. |
| **LlamaIndex** | Focused on RAG pipelines. Useful for memory but Chroma's Python client achieves the same in ~20 lines without the dependency. |
| **CrewAI** | High-level abstractions (crew, task, role) that conflict directly with our AgentSpec + message bus + N-level hierarchy design. Fitting our architecture into CrewAI's model would cost more than building our own. |
| **AutoGen** | Similar problem to CrewAI. Opinionated conversation patterns that don't match our async message bus or autonomous loop model. |

---

## Consequences

**Positive:**

- Full control over the agent loop, routing rules, and message bus
- No dependency lock-in: can adopt any new LLM SDK or library without framework migration
- Each module (loop, bus, router) is 100–300 lines — easy to understand, test, and change
- No abstraction impedance between our Pydantic models and the execution layer

**Negative:**

- More initial code to write (agent loop, dispatcher, router)
- No out-of-the-box tooling for agent observability (must build our own logging/tracing)
- Team must maintain these components; no upstream framework fixes

The tradeoff is acceptable. The components involved are small and well-understood.
The risk of framework lock-in outweighs the short-term productivity gain.

---

## Amendments

### 2026-10-22 — Google SDK package name

The Decision section names `google-generativeai`, which Google has since marked
as deprecated/legacy. The dependency actually declared in `backend/pyproject.toml`
is its successor, `google-genai` (official Google Gen AI SDK). The decision itself
(official provider SDKs only, no AI framework) is unchanged.
