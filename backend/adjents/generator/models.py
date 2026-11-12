"""Generator Agent domain model: BusinessContext.

`BusinessContext` is the structured summary of the onboarding interview: the bridge
between the two halves of the Generator Agent.

Place in the flow: domain / API layer (ADR 0002). `GeneratorInterview`
(`generator/interview.py`) builds it once the interview is complete, from the JSON
returned by the `generator/extract_business_context` prompt, and persists it;
`GeneratorOrgGeneration` (`generator/org_generation.py`) reads it to generate the
org. Persistence goes through `db/convert/generator.py`.

Entry points: `BusinessContext`.

Related ADRs: 0002 (domain models vs tables).
"""

from datetime import datetime

from pydantic import BaseModel


class BusinessContext(BaseModel):
    """What the Generator Agent learned about the user's business.

    Every field is required, including the nullable ones: an extraction JSON that
    omits a key fails validation instead of defaulting to None. Unknown keys are
    ignored (Pydantic's default). Field meanings follow the extraction prompt
    (`prompts/generator/extract_business_context.md`).

    Attributes:
        id: UUID.
        conversation_id: Id of the interview `Conversation`.
        business_name: Business or commercial name; None if the user works under
            their own name or gave none.
        founder_name: The user's full name.
        language: ISO 639-1 code of the interview language, e.g. "fr".
        core_activity: The user's main professional activity.
        legal_status: Legal / financial status; None if not mentioned.
        target_clients: Client types or segments, one per item.
        domains_with_human_coverage: Domains already covered by humans, excluded
            from agent generation.
        domains_to_staff: Domains where agents are to be created.
        tasks_to_delegate: Tasks the user wants to delegate, one per item.
        tasks_user_keeps: Tasks the user explicitly keeps.
        financial_goals: Financial objectives and constraints; None if not
            discussed.
        existing_tools: Tools, software or platforms the user mentioned.
        autonomy_preference: What requires human validation vs what agents may
            handle alone.
        work_hours: The user's available hours, e.g. "18:00-23:00"; None if always
            available or not discussed.
        additional_context: Anything relevant that fits no other field; None if
            nothing remains.
        created_at: Creation time.
    """

    id: str
    conversation_id: str
    business_name: str | None
    founder_name: str
    language: str
    core_activity: str
    legal_status: str | None
    target_clients: list[str]
    domains_with_human_coverage: list[str]
    domains_to_staff: list[str]
    tasks_to_delegate: list[str]
    tasks_user_keeps: list[str]
    financial_goals: str | None
    existing_tools: list[str]
    autonomy_preference: str
    work_hours: str | None
    additional_context: str | None
    created_at: datetime
