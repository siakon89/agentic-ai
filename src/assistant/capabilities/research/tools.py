"""Voice tools for the research swarm."""

from strands import tool

from assistant.capabilities.research.mail import send_research
from assistant.capabilities.research.records import latest_research, write_research
from assistant.capabilities.research.swarm import run_research


@tool
def deep_research(topic: str) -> str:
    """Research a topic on the public web and return a short spoken brief.

    Call this when the user addresses you as Ultron and asks you to research
    something. Do not end the session.

    Args:
        topic: The subject to research.
    """
    try:
        report = run_research(topic)
    except Exception as error:
        return f"The research could not be finished ({error}). Say that in one sentence, then stay silent."

    path = write_research(topic, report.full)
    print(f"\nSaved research to {path}", flush=True)
    return (
        "Research is saved. Speak only the following brief out loud, then stay silent. "
        "Do not read the long article.\n\n"
        f"{report.short}"
    )


@tool
def read_research() -> str:
    """Read the latest research swarm report.

    Call this when the user addresses you as Ultron and asks what the research
    found, or asks you to read a saved research record. Do not end the session.
    """
    path = latest_research()
    if path is None:
        return "No research record has been saved yet. Say that in one sentence, then stay silent."
    return (
        "This is the latest research record. Speak a short answer from the Short section "
        "unless the user asked for more detail. Do not invent claims.\n\n"
        f"{path.read_text(encoding='utf-8')}"
    )


@tool
def email_research() -> str:
    """Email the latest research report to the user's address.

    Call this when the user addresses you as Ultron and asks you to email the
    research. Do not end the session.
    """
    path = latest_research()
    if path is None:
        return "There is no research record to email. Say that in one sentence, then stay silent."
    try:
        spoken = send_research(path)
    except Exception as error:
        return f"The email could not be sent ({error}). Say that in one sentence, then stay silent."
    return f"{spoken} Say that in one sentence, then stay silent."
