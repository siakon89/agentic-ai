"""Saved reports from the research swarm."""

from datetime import datetime
from pathlib import Path


def write_research(topic: str, report: str, directory: Path | None = None) -> Path:
    """Save a short brief and a long article under records/."""
    folder = directory or Path("records")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}-research.md"
    path.write_text(f"# Research: {topic.strip()}\n\n{report.strip()}\n", encoding="utf-8")
    return path


def research_records(directory: Path | None = None) -> list[Path]:
    """Return saved research reports, oldest first."""
    folder = directory or Path("records")
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.glob("*-research.md") if path.is_file())


def latest_research(directory: Path | None = None) -> Path | None:
    """Return the most recent research report, if one exists."""
    records = research_records(directory)
    if not records:
        return None
    return records[-1]
