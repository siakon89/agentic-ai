"""Tools Ultron can call without ending the listening session."""

from strands import ToolContext, tool
from strands.bidi import BidiAgent

from meeting_listener.notes import save_catalog
from meeting_listener.transcript import format_transcript


@tool(context=True)
def save_summary(tool_context: ToolContext[BidiAgent]) -> str:
    """Save a summary of everything heard so far and return the words to speak.

    Call this only when the user addresses you as Ultron and asks for a summary.
    Do not end the session.
    """
    transcript = format_transcript(tool_context.agent.messages)
    if not transcript:
        return "Nothing has been captured yet. Stay silent and keep listening."

    try:
        saved = save_catalog(transcript)
    except Exception as error:
        return f"The summary could not be written ({error}). Stay silent and keep listening."

    print(f"\nSaved notes to {saved.path}", flush=True)
    return (
        "Notes are saved. Speak only the following, then stay silent and keep listening. "
        "Do not end the session.\n\n"
        f"{saved.spoken}"
    )
