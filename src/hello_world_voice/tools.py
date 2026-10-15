"""Tools Bob can call without ending the listening session."""

from strands import ToolContext, tool
from strands.bidi import BidiAgent

from hello_world_voice.notes import save_catalog
from hello_world_voice.transcript import format_transcript

VOICE_AGENT_ANSWER = (
    "A voice agent listens to speech, understands the turn, and answers out loud. "
    "It can hold a conversation, take notes from what it heard, and stay silent until you call it by name. "
    "I can do those three things. Say Bob and talk with me. Say Bob, take notes when you want a summary. "
    "I stay quiet until you use my name."
)


@tool
def explain_voice_agent() -> str:
    """Explain what a voice agent can do.

    Call this when the user addresses you as Bob and asks what a voice agent
    can do, or what you can do. Do not end the session.
    """
    return (
        "Speak only the following, then stay silent and keep listening. "
        "Do not end the session.\n\n"
        f"{VOICE_AGENT_ANSWER}"
    )


@tool(context=True)
def save_summary(tool_context: ToolContext[BidiAgent]) -> str:
    """Save notes for everything heard so far and return the words to speak.

    Call this only when the user addresses you as Bob and asks you to take
    notes or summarize. Do not end the session.
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
