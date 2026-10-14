"""Summarize a transcript into notes with action points."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field
from strands import Agent
from strands.models import BedrockModel

from meeting_listener.config import aws_region, notes_model_id

_NOTES_PROMPT = (
    "You write meeting notes from a transcript. "
    "Use only facts the transcript supports. "
    "Do not invent owners, dates, or tasks. "
    "Lines labeled Ultron are earlier spoken summaries. "
    "Use them as context, not as new discussion."
)


class ActionPoint(BaseModel):
    """One next step taken from the conversation."""

    task: str = Field(description="What needs to happen next.")
    owner: str | None = Field(
        default=None,
        description="Person responsible, only when the transcript names them.",
    )


class MeetingNotes(BaseModel):
    """Written notes for a listened-to conversation."""

    summary: str = Field(description="One short paragraph covering what was discussed.")
    action_points: list[ActionPoint] = Field(
        description="Concrete next steps. Leave empty when none were agreed."
    )


@dataclass(frozen=True)
class SavedNotes:
    """A catalog written to disk, plus the words Ultron should speak."""

    path: Path
    markdown: str
    spoken: str


def summarize(transcript: str, *, region: str | None = None) -> MeetingNotes:
    """Ask a text model for a summary and action points grounded in the transcript."""
    agent = Agent(
        model=BedrockModel(
            model_id=notes_model_id(),
            region_name=region or aws_region(),
            temperature=0.2,
        ),
        system_prompt=_NOTES_PROMPT,
        callback_handler=None,
    )
    return agent.structured_output(
        MeetingNotes,
        f"Summarize the conversation and list its action points.\n\nTranscript:\n{transcript}",
    )


def save_catalog(transcript: str) -> SavedNotes:
    """Summarize a transcript, write the markdown, and keep the spoken form."""
    notes = summarize(transcript)
    markdown = render_notes(notes, transcript)
    return SavedNotes(path=write_notes(markdown), markdown=markdown, spoken=render_spoken(notes))


def render_spoken(notes: MeetingNotes) -> str:
    """Format the summary and action points for Ultron to speak."""
    if notes.action_points:
        actions = "\n".join(_format_action(point) for point in notes.action_points)
    else:
        actions = "None."
    return f"Summary: {notes.summary.strip()}\nAction points:\n{actions}"


def render_notes(notes: MeetingNotes, transcript: str) -> str:
    """Format notes and the source transcript as Markdown."""
    if notes.action_points:
        actions = "\n".join(f"- {_format_action(point)}" for point in notes.action_points)
    else:
        actions = "- None."
    return (
        "# Meeting notes\n\n"
        "## Summary\n\n"
        f"{notes.summary.strip()}\n\n"
        "## Action points\n\n"
        f"{actions}\n\n"
        "## Transcript\n\n"
        f"{transcript.strip()}\n"
    )


def write_notes(markdown: str, directory: Path | None = None) -> Path:
    """Save notes under notes/ using the local time in the file name."""
    folder = directory or Path("notes")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def _format_action(point: ActionPoint) -> str:
    task = point.task.strip()
    owner = (point.owner or "").strip()
    if owner:
        return f"{task} ({owner})"
    return task
