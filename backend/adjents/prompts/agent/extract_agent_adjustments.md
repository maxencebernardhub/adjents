---
version: 1
description: "Extract agent configuration changes from conversation transcripts"
model_hint: "claude-sonnet-4-6"
---

# Extract Agent Adjustments

You are given one or more conversation transcripts between a user and AI agents.
Each transcript is delimited by `---AGENT:<agent_id>---` markers where `<agent_id>`
is a UUID. Your task: extract all configuration changes that were explicitly discussed
and agreed upon.

## Output format (mandatory)

Return a single valid JSON object — nothing else. No markdown, no preamble:

```json
{
  "agent_updates": [
    {
      "agent_id": "<uuid>",
      "fields": {
        "name": "Lucas",
        "role_description": "...",
        "work_hours": "09:00-20:00",
        "scheduler_interval_seconds": 600,
        "visual_character": "character_creative",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "escalation_rules": ["Rule 1"]
      },
      "skills_to_add": [
        {
          "name": "Monthly newsletter",
          "description": "Drafts and sends the monthly newsletter.",
          "inputs": ["subscriber list", "content brief"],
          "outputs": ["drafted newsletter"],
          "requires_human_review": true
        }
      ],
      "skills_to_remove": ["Skill name to remove"],
      "skills_to_update": [
        {
          "name": "Existing skill name",
          "fields": {
            "description": "Updated description.",
            "inputs": ["updated input"],
            "outputs": ["updated output"],
            "requires_human_review": false
          }
        }
      ]
    }
  ]
}
```

## Rules

- Include an entry in `agent_updates` only for agents where at least one change was
  explicitly discussed and confirmed by the user.
- All `fields` keys are optional — include only modified fields.
- `skills_to_add`, `skills_to_remove`, `skills_to_update` must be present for every
  entry, even if empty.
- Do NOT include `domain`, `level`, or `parent_id` in `fields`.
- `visual_character` must be one of: `character_suit`, `character_creative`,
  `character_tech`, `character_support`, `character_analyst`, `character_sales`.
- `scheduler_interval_seconds` must be an integer.
- `work_hours` format: `"HH:MM-HH:MM"` or `null` (always active).
- agent_id values come from the `---AGENT:<agent_id>---` markers.
- If no changes were made in any transcript: `{ "agent_updates": [] }`.
