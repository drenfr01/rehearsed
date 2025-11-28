"""Feedback prompt templates."""

FEEDBACK_SYSTEM_INSTRUCTIONS_TEMPLATE = """
<OBJECTIVE_AND_PERSONA>
{objective}
</OBJECTIVE_AND_PERSONA>

<INSTRUCTIONS>
{instructions}
</INSTRUCTIONS>

<CONSTRAINTS>
{constraints}
</CONSTRAINTS>

<CONTEXT>
{context}
</CONTEXT>
{output_format_section}
"""


def format_feedback_instructions(
    objective: str,
    instructions: str,
    constraints: str,
    context: str,
    output_format: str = "",
) -> str:
    """Format feedback instructions with the template.
    
    Args:
        objective: The objective of the feedback
        instructions: The instructions for the feedback
        constraints: The constraints for the feedback
        context: The context for the feedback
        output_format: The output format for the feedback (optional)
        
    Returns:
        Formatted feedback instructions string
    """
    output_format_section = ""
    if output_format:
        output_format_section = f"""
<OUTPUT_FORMAT>
{output_format}
</OUTPUT_FORMAT>
"""
    
    return FEEDBACK_SYSTEM_INSTRUCTIONS_TEMPLATE.format(
        objective=objective,
        instructions=instructions,
        constraints=constraints,
        context=context,
        output_format_section=output_format_section,
    )
