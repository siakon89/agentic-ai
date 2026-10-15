"""Save the words captured during a session."""

from datetime import datetime
from pathlib import Path


def write_record(transcript: str, directory: Path | None = None) -> Path:
    """Save the transcript under records/ using the local time in the file name."""
    folder = directory or Path("records")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.md"
    body = transcript.strip()
    path.write_text(f"# Record\n\n{body}\n", encoding="utf-8")
    return path
