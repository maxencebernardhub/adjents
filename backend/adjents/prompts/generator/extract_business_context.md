---
version: 1
description: "Extract BusinessContext JSON from a completed interview transcript"
model_hint: "claude-opus-5-5"
---

# Extract BusinessContext from Interview Transcript

You will receive the full transcript of a completed onboarding interview between a user
and the Generator Agent. Your task is to extract the collected information into a single
structured JSON object.

## Output format

Return only a single valid JSON object. No markdown, no explanations, no surrounding
text of any kind.

## JSON schema

```json
{
  "business_name": "string or null",
  "founder_name": "string",
  "language": "string",
  "core_activity": "string",
  "legal_status": "string or null",
  "target_clients": ["string", "..."],
  "domains_with_human_coverage": ["string", "..."],
  "domains_to_staff": ["string", "..."],
  "tasks_to_delegate": ["string", "..."],
  "tasks_user_keeps": ["string", "..."],
  "financial_goals": "string or null",
  "existing_tools": ["string", "..."],
  "autonomy_preference": "string",
  "work_hours": "string or null",
  "additional_context": "string or null"
}
```

## Field instructions

- `business_name`: the business or commercial name mentioned; `null` if the user
  operates under their personal name or did not provide one
- `founder_name`: the user's full name as stated in the conversation
- `language`: ISO 639-1 code of the language used in the interview (e.g. `"fr"`, `"en"`)
- `core_activity`: concise description of the user's main professional activity
- `legal_status`: the user's legal/financial status; `null` if not mentioned
- `target_clients`: each distinct client type or segment as a separate string
- `domains_with_human_coverage`: domains already covered by humans, excluded from
  agent generation; `[]` if none mentioned
- `domains_to_staff`: domains where AI agents will be created; infer from the
  delegation discussion (what the user wants to delegate)
- `tasks_to_delegate`: specific tasks the user wants to delegate; one task per string
- `tasks_user_keeps`: tasks the user explicitly stated they want to keep for themselves
- `financial_goals`: narrative summary of financial objectives and constraints;
  `null` if not discussed
- `existing_tools`: tools, software, or platforms the user mentioned using; `[]` if none
- `autonomy_preference`: narrative description of what requires human validation vs.
  what agents can handle autonomously
- `work_hours`: user's available hours in `"HH:MM-HH:MM"` format (e.g. `"18:00-23:00"`);
  `null` if always available or not discussed
- `additional_context`: any other relevant information from the transcript that does not
  fit the fields above; `null` if nothing significant remains

## Default values

- Nullable string fields not mentioned in the transcript: `null`
- List fields not mentioned in the transcript: `[]`

Do not invent or infer information that is not explicitly present in the transcript.
