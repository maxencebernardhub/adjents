# Adjents — Vision & MVP v0.1 Specification

> Describe your business. Get your AI workforce.

## 1. Vision

### 1.1 The core promise

A solopreneur starting out should have the firepower of a 10-to-20-person company — without
hiring a single employee. Adjents gives them exactly that: a full team of AI agents working
24/7, each with a defined role, a memory, skills, and the autonomy to act without being told
what to do at every step.

The user never writes prompts, draws graphs, or configures YAML. They just talk.

### 1.2 What makes Adjents different

Most multi-agent platforms (CrewAI, Lindy, Dust, Relevance AI) ask users to **configure**
their agents: pick a template, drag nodes, write a prompt. This creates two problems:

- It requires technical knowledge most solopreneurs don't have.
- It produces a generic setup that doesn't reflect the user's actual business.

**Adjents generates everything from a conversation.** A dedicated meta-agent — the
**Generator Agent** — conducts a deep, funnel-style interview with the solopreneur. It asks
about their current context, the tools they already use, their goals, their identity, their
know-how, their target clients, their prospecting and communication style, and more.

From those answers, Adjents produces:

- The **org structure**: which N-1 domain leads and N-2 specialists make sense for *this
  specific business*, not a generic one.
- The **skills and tools** of each agent: tailored to the user's workflows and needs.
- The **parameters** of each agent: autonomy level, complexity threshold, scheduling
  cadence, memory scope.

This onboarding happens **once**. The resulting organization is persistent: agents are not
recreated on the next run — they exist, remember, and keep working.

### 1.3 Two distinct roles: Generator Agent and COO

The **Generator Agent** is a one-shot meta-agent. Its sole purpose is to interview the
solopreneur and produce the organization. It runs at onboarding with maximum inference
quality (frontier cloud LLM), then becomes dormant. It can be reactivated if the user
wants to restructure their team. When reactivated, the Generator Agent conducts a
focused delta interview with the user, then consults the affected N-1 (and N-2, if
relevant) agents — their operational knowledge may shape the restructuring proposal.
The user validates before any change is applied. This flow is implemented in v0.2
(see ADR 0005).

The **COO (N-0, Chief of Staff)** is the permanent operational super-agent. After
onboarding, the COO is the user's primary point of contact. It coordinates N-1 leads,
delegates work, monitors progress, and escalates blockers to the user.

Think of the Generator Agent as the **recruitment agency** that built the team. The COO
is the **permanent manager** who runs it.

### 1.4 Agents are autonomous, not passive

N-1 leads have a mandate and objectives. They do not wait for instructions. They plan,
act, delegate to their N-2 specialists, and report results. The COO orchestrates across
all domains.

The user has full control at all times: they can pause, slow down, or stop any agent.
When agents have blocking questions — decisions that require human judgement — those
questions surface in a dedicated notification zone in the UI.

### 1.5 Projects, not just daily operations

Beyond the day-to-day "run" (invoicing, marketing, sales, client support...), the user
can create **projects**: temporary, goal-oriented work units with a defined objective,
expected deliverables, a deadline, assigned agents, and a task list.

A project has:

- An objective ("Build the company website")
- One or more deliverables ("Live website", "Copy document")
- A deadline
- Assigned agents (a lead + contributors)
- A task breakdown, tracked and supervised by the project lead agent

Once a project is complete, the assigned agents stop working on it and return to their
regular operations. The user can see the status of any project at any time.

### 1.6 The workspace: a living org chart

The UI is designed as a **2D RPG-style workspace**. Each agent has a name, a visual
character, and a visual state that reflects what they are actually doing in real time:

| State | Visual |
| --- | --- |
| Idle | Agent reading, eating, or resting at their desk |
| 1-on-1 conversation | Two agents sitting across a small table |
| Group discussion (3+) | Agents sitting around a meeting room table |
| Solo task | Agent working alone behind a computer |

The user can:

- **Hover over any agent** to see their current task, pending questions, and memory state.
- **Click any agent** to open a direct conversation with them.
- **Watch live dialogues** between agents in real time.
- **Customize** each agent's name and appearance.

### 1.7 Deliverables

Agents produce outputs: documents, drafted emails, research notes, code, website copy...
These deliverables are stored locally in a structured output directory within the
repository. The UI surfaces recent and historical deliverables in a dedicated view.

### 1.8 Local-first, cloud-optional inference

By default, Adjents runs entirely offline using a local LLM via Ollama. Cloud LLMs
(Claude, OpenAI, Google Gemini) are used for tasks that require higher reasoning
quality — the Generator Agent's interview, complex planning, code generation. Each
agent's model preference can be configured independently.

## 2. Target users

Adjents is designed for **one person who needs a team** — without hiring one. The product
is single-user by design (v0.1 through at least v0.3). Multi-user shared workspaces are
a post-v1.0 consideration.

### 2.1 Primary segment — Solopreneurs and freelancers

A person running a one-person business: a freelancer, consultant, coach, designer,
accountant, e-commerce seller, or service provider. They are often:

- Drowning in admin work that keeps them from their core activity
- Unable to scale because they trade time for money
- Non-technical: they will never write code, prompts, or YAML

Adjents gives them a full AI team tailored to their actual business — generated in a
single onboarding conversation, then running autonomously.

#### Persona — Alex Chen

Freelance UX designer, 3 years independent. Has a steady stream of clients but spends
30–40% of his time on non-design work: drafting proposals, chasing invoices, managing
his LinkedIn presence, tracking project timelines. He wants to focus on design. He has
no interest in learning AI tools — he just wants things done.

#### Persona — Maria Santos

Online English teacher, runs her own micro-school with 15 recurring students. Handles
scheduling, lesson prep, billing, and student follow-ups entirely alone. She wants to
delegate everything except the teaching itself. She is not technical and slightly
intimidated by software.

### 2.2 Secondary segment — Small business owners with a hybrid team

A founder or director of a very small company (fewer than 20 employees) who already has
humans covering some domains, and wants to extend their capacity with AI agents in the
domains that aren't staffed.

During onboarding, the Generator Agent asks which business domains already have human
employees. **Those domains are excluded from agent generation.** The resulting AI team
fills only the gaps.

Example: a 5-person design studio has a real marketing lead and a real office manager.
The Generator Agent creates agents only for Sales, Finance, and Operations — the domains
without coverage.

#### Persona — James Whitfield

Founder of a 6-person consulting firm. Has a project manager and a part-time bookkeeper,
but no one covering sales or business development. He wants AI agents to handle
prospecting, proposal drafting, and competitive research — without replacing his existing
team.

### 2.3 Out of scope (for now)

Private individuals using Adjents for personal life admin (household finances, job
search, etc.) are a plausible future use case but are explicitly out of scope for v0.1.
The product message and onboarding are calibrated for professional contexts.

## 3. Core concepts

### 3.1 Agent hierarchy

The Generator Agent bootstraps the organization once, then becomes dormant. The
operational hierarchy it produces is persistent and runs indefinitely.

```text
  [ Generator Agent ]  ← one-shot bootstrap; dormant after onboarding
          │ generates
          ▼
  [ User / Founder ]
          │
  ┌───────┴───────┐
  │  COO  (N-0)   │   ← permanent coordinator; primary interface for the user
  └───────┬───────┘
          │
  ┌───────┼────────┐
[N-1]  [N-1]  [N-1]   ← domain leads (Sales, Finance, Marketing, Ops...)
  │       │
[N-2]  [N-2]          ← specialists (Invoicing, Cold outreach, Copywriter...)
  │
[N-3]  ...            ← deeper levels for complex businesses, no hard cap
```

There is no hard limit on hierarchy depth. A simple freelance business may need only
N-0 + N-1. A more complex one may have N-0 through N-3 or beyond.

**Reporting and communication rules:**

- Each agent reports to its direct manager (N+1 up to N-0 up to the user).
- Agents can escalate directly to their N+2, or to the user, when needed.
- Agents can collaborate laterally with agents at any level across any branch when a
  task requires it — hierarchy governs accountability, not communication.
- The user can talk directly to any agent at any level at any time.

### 3.2 Generator Agent and onboarding

The Generator Agent is a one-shot meta-agent. It does not belong to the operational
org — it bootstraps it. Once onboarding is complete, it becomes dormant and can be
reactivated only if the user explicitly wants to restructure the organization. When
reactivated for restructuring, the Generator Agent conducts a focused delta interview
with the user, then consults the N-1 (and N-2, if relevant) agents whose domains are
affected. Agent-side input helps produce a better restructuring proposal. The user
validates before any change is applied. See ADR 0005 and v0.2 roadmap.

The onboarding is a **deep funnel-style interview**: the Generator Agent asks a
progressive sequence of questions to understand:

- The user's business context and activity
- The external tools and services they already use
- Their goals, their identity, their know-how
- Their target clients and personas
- How they prospect, communicate, and deliver their work
- Which business domains already have human coverage (TPE case → those domains are
  excluded from agent generation)

From those answers, it produces:

- The full org structure: which domain leads and specialists make sense for *this*
  specific business
- Each agent's role, responsibilities, skills, and escalation rules
- Each agent's parameters: autonomy level, scheduling interval, memory scope
- Each agent's name, persona, and visual character for the UI

Skills are **descriptive in v0.1** (a name + a description of what the skill does).
They become **executable Python functions in a sandbox starting from v0.2**.

After org generation, the user is invited to meet each N-1 agent one-on-one before the
org goes live. Each agent presents itself and its team (role, responsibilities, skills,
schedule). The user validates, renames, or requests adjustments. Agents are created with
`is_paused = True` and become active only after the user completes this step (or
explicitly skips it). Micro-adjustments to a single agent's config (skills, escalation
rules, work hours) go through the agent's parent, not the Generator Agent — see ADR 0005.
The post-generation validation flow is documented in ADR 0006.

### 3.3 Agent autonomy model

Each agent runs an **agent loop** — a continuous cycle of perception, reasoning, and
action. An agent can be activated by three triggers:

**1 — Scheduled wake-up**
Each agent has a configurable wake-up interval (e.g. every 15 minutes). When the
interval fires and the agent is idle, it reviews its objectives, its task queue, and
its context, then decides what to do next.

**2 — Message or task trigger**
Any agent or the user can send a message to another agent or assign it a task. The
receiving agent wakes up immediately, even if idle, and processes the request.

**3 — Event trigger**
An agent can be configured to react to specific event types (e.g. "a new prospect
replies", "an invoice is overdue"). When a matching event occurs, the agent activates.

#### Task queue and priorities

Each agent maintains an ordered task queue. When a new task arrives while the agent
is already working, the agent asks the requester for the priority level and may
reorder its queue accordingly. Tasks are processed one at a time, in priority order.

#### Blocking questions

When an agent needs a human decision before it can proceed, it escalates a blocking
question. These surface in a dedicated notification zone in the UI. The agent pauses
the affected task until the user responds.

#### User control

The user can pause, slow down, or stop any agent at any time. Agents never take
irreversible actions without at least a configurable confirmation step.

### 3.4 Projects

Beyond day-to-day operations (invoicing, marketing, sales, support...), the user can
create **projects**: temporary, goal-oriented work units with a defined start and end.

A project is defined by:

- An **objective** — what the project is trying to achieve
- One or more **deliverables** — the expected outputs
- A **deadline**
- A **project lead agent** — responsible for breaking down the work and supervising it
- **Contributing agents** — assigned to specific tasks within the project
- A **task list** — created and tracked by the project lead

Once all deliverables are produced and the project is closed, the assigned agents
return to their regular operational duties. The user can see the status of any project
at any time from the workspace.

### 3.5 Deliverables

Agents produce outputs: documents, drafted emails, research notes, website copy,
code, reports... These deliverables are stored locally in a structured output
directory. The workspace surfaces recent and historical deliverables in a dedicated
view, organized by agent and by project.

### 3.6 LLM routing

No agent picks its own model. A central **router** decides which LLM handles each
task based on three inputs: task type, sensitivity level, and complexity.

Default rules:

- **Generator Agent** → always a frontier cloud LLM (high complexity, one-shot quality
  requirement)
- **Routine agent tasks** → local LLM via Ollama (fast, private, offline)
- **High-complexity reasoning** (planning, code generation, multi-step analysis) →
  cloud LLM
- **Sensitive content** (personal data, financial details) → local-only, never cloud

Supported cloud providers: Anthropic (Claude), OpenAI (GPT), Google (Gemini).
Each agent can have a preferred model configured independently.

### 3.7 Conversational interface and workspace

The user never sees a graph builder, a YAML editor, or a prompt template. Every
interaction is a conversation.

**Onboarding** = a conversation with the Generator Agent.
**Daily use** = a conversation with any agent.
**Configuration** = natural language ("Tell my Finance agent to send invoices on the
5th, not the 1st.").

The workspace is a **2D RPG-style interface** where each agent is a named character
with a visual state reflecting what they are doing in real time. The user can hover
over any agent to see their status, open a direct conversation, or watch live
dialogues between agents. See section 1.6 for the full workspace description.

## 4. MVP v0.1 — Scope

**Goal**: a demoable artifact — solo dev + Claude Code. The v0.1 demo must show a
complete onboarding flow, a live org running autonomously, and the 2D workspace
with agents in visible states.

### 4.1 In scope

1. **Conversational onboarding** — Generator Agent conducts a deep funnel-style
   interview; produces the full persistent org structure (agents, roles, skills,
   parameters)

2. **Organization generator** — outputs a complete, serialized agent hierarchy
   tailored to the user's specific business; excluded domains (TPE case) are skipped

3. **Post-generation team validation** — after org generation, the user is invited to
   meet each N-1 agent one-on-one; each agent presents itself and its team (role,
   responsibilities, skills, schedule); the user validates or adjusts before agents go
   live; skippable; agents are created with `is_paused = True` and go live only after
   validation (see ADR 0006)

4. **Direct agent reconfiguration** — after agents go live, the user can open a
   conversation with any agent to review and adjust its configuration (name, role
   description, responsibilities, skills, work hours, scheduler interval, visual
   character); changes are extracted by a second LLM call at the end of the
   conversation and applied directly to the DB; structural fields (domain, level,
   parent) are frozen (see ADR 0009)

5. **2D RPG workspace** — a house layout with one room per business domain;
   agents appear as 2D sprites (static, Option A) with visible states:
   idle / working alone / 1-on-1 meeting / group meeting; agents can move to shared
   spaces (meeting room, break room) for cross-domain collaboration

6. **Org chart view** — a separate, always-accessible view of the full hierarchy;
   each agent displays their 2D sprite, name, role, and current status

7. **Agent interaction** — hover over any agent to see current task, pending
   questions, and memory state; click to open a direct conversation; watch live
   dialogues between agents in real time

8. **Blocking questions zone** — a dedicated UI area where agents surface questions
   that require a human decision before they can proceed

9. **Multi-agent chat** — the user talks to any agent at any level; agents call
   other agents to get help or delegate subtasks

10. **Internal agent scheduler** — each agent runs an autonomous loop with a
    configurable wake-up interval; agents can also be triggered by messages from
    other agents or the user

11. **Individual memory** per agent + **global knowledge base** shared across the org
    (SQLite + Chroma, local-first, no cloud dependency required)

12. **Deliverables output** — agents write their outputs (documents, notes, drafts)
    to a local structured directory (`./data/outputs/`); the UI surfaces recent and
    historical deliverables

13. **LLM routing** — local inference via Ollama (default) + frontier cloud models
    (Anthropic Claude, OpenAI, Google Gemini) for high-complexity tasks; routing is
    centralized, no agent picks its own model

### 4.2 Out of scope for v0.1

- ❌ **No real-world execution** — no emails sent, no external API calls (v0.2)
- ❌ **No web search** — agents cannot browse the web (v0.2)
- ❌ **No Python sandbox** — skills are descriptive only, not executable (v0.2)
- ❌ **No external event triggers** — no webhooks, no calendar events, no inbox
  monitoring; the internal scheduler IS in scope, external triggers are not (v0.2)
- ❌ **No external integrations** — Gmail, Calendar, CRM, Stripe, Notion... (v0.2+)
- ❌ **No projects feature** — project management with deliverables and deadlines
  (v0.2)
- ❌ **No parent-mediated governance for reconfiguration** — in v0.1, all non-structural
  fields are modifiable directly via `AgentReconfiguration`; in v0.2, parent agents
  will validate changes to `work_hours`, `responsibilities`, and `role_description`
  for non-COO agents before applying them (requires Python sandbox — see ADR 0005 and
  ADR 0009)
- ❌ **No UI animations** — sprites are static; animated transitions come later (v0.3)
- ❌ **No multi-user workspace** — single-user, local only (post-v1.0)
- ❌ **No mobile app**
- ❌ **No commercial billing**

### 4.3 Roadmap after v0.1

> This roadmap is indicative. It will be updated continuously based on user feedback,
> usage patterns, and development priorities. Some items may be dropped, reordered,
> or replaced entirely. Multi-user support in particular is listed for completeness
> but may never be a priority given the solopreneur-first target.

- **v0.2**: Python sandbox for skills execution, web search, external event triggers,
  projects feature, first external integrations — see integration philosophy below;
  **org restructuring** — Generator Agent re-interview (with consultation of affected
  N-1/N-2 agents) to add, remove, or update agents without destroying existing memory;
  **micro-adjustments** — user talks to parent agent to update a single agent's skills,
  responsibilities, or escalation rules (see ADR 0005)
- **v0.3**: Broader MCP server support and validation (Calendar, Stripe, Notion...),
  animated UI sprites and transitions, richer agent memory visualization
- **v0.4**: Multi-user shared workspace (client-server mode, shared org access) —
  *low priority; may be deferred or dropped depending on user demand*
- **v1.0**: Production-ready, one-click deploy for non-technical users; packaging
  for macOS / Windows / Linux
- **post-v1.0**: Mobile companion app, managed cloud hosting option

### 4.4 Integration philosophy

Building every external integration from scratch (Gmail, Calendar, Notion, Stripe...)
would require months of development and permanent maintenance overhead. Adjents will
not go down that path.

**Principle**: integrations will reuse open, existing ecosystems rather than being
built custom. Agents will call external services through a standardized tool-calling
layer — not through hand-coded connectors.

#### Leading candidate: MCP (Model Context Protocol)

MCP is an open protocol, developed by Anthropic, for connecting LLMs to external
tools and data sources. A growing ecosystem of community-maintained MCP servers
already covers Gmail, Google Calendar, GitHub, Notion, Slack, Stripe, web search,
and more. If an agent can call MCP servers, every new publicly available MCP server
becomes immediately usable — with no additional development on Adjents' side.

This decision will be **validated at the start of v0.2** work, when the practical
implications (context window usage, reliability, available server quality) can be
assessed concretely. The approach may be adjusted if a better option emerges.

## 5. What Adjents is NOT

- Not a prompt-engineering tool (no prompt editor for users)
- Not a no-code workflow builder (no nodes, no edges, no flows to draw)
- Not a template or agent marketplace (agents are generated for your business,
  not picked from a catalog)
- Not a single personal assistant — it is a whole team of specialized agents
- Not a chatbot framework (agents act, they don't just respond)
- Not a competitor to Claude/ChatGPT (we use them; we don't replace them)
- Not enterprise-first (solopreneur-first; enterprise may come later, if ever)

## 6. License & philosophy

- **MIT License** — confirmed for the public release in ADR 0013, with guardrails
  (no external code contributions without a CLA; the Adjents name and domain are not
  licensed) and a review trigger for the license of future versions
- Open source for the core; versions already published under MIT stay MIT, while the
  license of future versions may change under the conditions set in ADR 0013
- Future commercial version possible (managed hosting, premium support)
- Built in public — every meaningful decision documented in `docs/decisions/`

## 7. Author

Maxence Bernard — Toronto, ON, Canada
Solo founder, building Adjents as an open-source portfolio.
