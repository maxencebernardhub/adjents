"""Shared helper for building agent context messages injected into LLM conversations."""

from adjents.agents.models import AgentSpec, Skill


def _build_agent_context_message(
    agent: AgentSpec,
    skills: list[Skill],
    direct_reports: list[AgentSpec],
    reports_skills: dict[str, list[Skill]],
) -> str:
    """Build the first user message injecting agent data for intro/extraction prompts.

    Every agent block includes the agent_id (UUID) so the extraction LLM can
    reference it. direct_reports is empty for leaf agents.
    """
    lines: list[str] = [
        f"Agent ID: {agent.id}",
        f"Name: {agent.name}",
        f"Role: {agent.role_description}",
        "",
        "Responsibilities:",
    ]
    if agent.responsibilities:
        lines += [f"- {r}" for r in agent.responsibilities]
    else:
        lines.append("(none)")

    lines += ["", "Skills:"]
    if skills:
        for skill in skills:
            lines.append(f"- {skill.name}: {skill.description}")
            if skill.inputs:
                lines.append(f"  Inputs: {', '.join(skill.inputs)}")
            if skill.outputs:
                lines.append(f"  Outputs: {', '.join(skill.outputs)}")
            review = "Yes" if skill.requires_human_review else "No"
            lines.append(f"  Requires human review: {review}")
    else:
        lines.append("(none)")

    lines += [
        "",
        f"Work hours: {agent.work_hours or 'always active'}",
        f"Scheduler interval: {agent.scheduler_interval_seconds} seconds",
        f"Visual character: {agent.visual_character}",
        "Escalation rules:",
    ]
    if agent.escalation_rules:
        lines += [f"- {r}" for r in agent.escalation_rules]
    else:
        lines.append("(none)")

    if direct_reports:
        lines += ["", "Direct reports:"]
        for report in direct_reports:
            report_skills_list = reports_skills.get(report.id, [])
            lines.append(
                f"- Agent ID: {report.id} | {report.name} — {report.role_description}"
            )
            lines.append("  Responsibilities:")
            if report.responsibilities:
                lines += [f"  - {r}" for r in report.responsibilities]
            else:
                lines.append("  (none)")
            if report_skills_list:
                skill_parts = []
                for s in report_skills_list:
                    part = s.name
                    if s.requires_human_review:
                        part += " (requires review)"
                    skill_parts.append(part)
                lines.append(f"  Skills: {', '.join(skill_parts)}")
            else:
                lines.append("  Skills: (none)")
            lines.append(f"  Work hours: {report.work_hours or 'always active'}")
            lines.append(
                f"  Scheduler interval: {report.scheduler_interval_seconds} seconds"
            )
            if report.escalation_rules:
                lines.append("  Escalation rules:")
                lines += [f"  - {r}" for r in report.escalation_rules]
            else:
                lines.append("  Escalation rules: (none)")

    return "\n".join(lines)
