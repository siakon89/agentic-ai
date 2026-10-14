"""Listen to a conversation, then write a summary and action points."""

import asyncio
import sys

from meeting_listener.notes import save_catalog, write_notes
from meeting_listener.session import listen
from meeting_listener.transcript import format_transcript


async def run() -> None:
    messages = await listen()
    transcript = format_transcript(messages)
    if not transcript:
        print("The session ended before any conversation was captured.")
        return

    print("\nSession closed. Writing the full catalog…")
    try:
        saved = save_catalog(transcript)
    except Exception as error:
        print(f"Could not summarize the transcript: {error}", file=sys.stderr)
        path = write_notes(f"# Transcript\n\n{transcript}\n")
        print(f"Saved the transcript to {path}")
        return

    print(saved.markdown)
    print(f"Saved to {saved.path}")


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
