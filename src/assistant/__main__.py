"""Listen to a conversation and save a record of what was said."""

import asyncio

from assistant.record import write_record
from assistant.session import listen
from meeting_listener.transcript import format_transcript


async def run() -> None:
    messages = await listen()
    transcript = format_transcript(messages, assistant_name="Ultron")
    if not transcript:
        print("The session ended before any conversation was captured.")
        return

    path = write_record(transcript)
    print()
    print(path.read_text(encoding="utf-8"))
    print(f"Saved to {path}")


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
