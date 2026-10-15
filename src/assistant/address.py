"""Pass Ultron's replies through only after the user says his name."""

import re

from strands.bidi.types import (
    BidiAudioDeltaEvent,
    BidiAudioStartEvent,
    BidiAudioStopEvent,
    BidiOutputEvent,
    BidiReasoningDeltaEvent,
    BidiReasoningStartEvent,
    BidiReasoningStopEvent,
    BidiResponseStopEvent,
    BidiTextBlockEvent,
    BidiTextDeltaEvent,
    BidiTextStartEvent,
    BidiTextStopEvent,
    BidiToolUseBlocksEvent,
    BidiTranscriptBlockEvent,
    BidiTranscriptDeltaEvent,
    BidiTranscriptStartEvent,
    BidiTranscriptStopEvent,
)
from strands.bidi.types.io import InputStream, OutputStream

_NAME = re.compile(r"\bultron\b", re.IGNORECASE)

_REPLY_EVENTS = (
    BidiAudioStartEvent,
    BidiAudioDeltaEvent,
    BidiAudioStopEvent,
    BidiTextStartEvent,
    BidiTextDeltaEvent,
    BidiTextStopEvent,
    BidiTextBlockEvent,
    BidiReasoningStartEvent,
    BidiReasoningDeltaEvent,
    BidiReasoningStopEvent,
    BidiToolUseBlocksEvent,
)


class AddressGate:
    """Remember whether the current turn addressed Ultron by name."""

    def __init__(self) -> None:
        self.addressed = False
        self._pending: list[BidiOutputEvent] = []
        self._user_transcripts: dict[str, str] = {}
        self._typed_turn = False

    def note_user_text(self, text: str) -> None:
        """A typed turn is complete, so the name is either present or absent."""
        self.addressed = _named(text)
        self._typed_turn = True
        if not self.addressed:
            self._pending.clear()

    def observe(self, event: BidiOutputEvent) -> None:
        """Update the gate from a user transcript as it arrives."""
        if isinstance(event, BidiResponseStopEvent):
            self._typed_turn = False
        elif isinstance(event, BidiTranscriptStartEvent) and event.role == "user":
            self._user_transcripts[event.content_id] = ""
            if not self._typed_turn:
                self.addressed = False
                self._pending.clear()
        elif isinstance(event, BidiTranscriptDeltaEvent) and event.role == "user":
            heard = self._user_transcripts.get(event.content_id, "") + event.delta
            self._user_transcripts[event.content_id] = heard
            if _named(heard):
                self.addressed = True
        elif isinstance(event, BidiTranscriptBlockEvent) and event.role == "user" and _named(event.transcript):
            self.addressed = True

    def hold_reply(self, event: BidiOutputEvent) -> bool:
        """Keep an unrequested reply until the turn shows it was addressed."""
        if isinstance(event, BidiResponseStopEvent) and not self.addressed:
            self._pending.clear()
            return False
        if not _is_reply(event) or self.addressed:
            return False
        self._pending.append(event)
        return True

    def release(self) -> list[BidiOutputEvent]:
        """Return replies that were held until the name was heard."""
        if not self.addressed or not self._pending:
            return []
        pending = self._pending
        self._pending = []
        return pending


def guard(inputs: list[InputStream], outputs: list[OutputStream]) -> tuple[list[InputStream], list[OutputStream]]:
    """Share one gate across the session's input and output streams."""
    gate = AddressGate()
    return (
        [_GatedInput(stream, gate) for stream in inputs],
        [_GatedOutput(stream, gate) for stream in outputs],
    )


class _GatedInput:
    def __init__(self, inner: InputStream, gate: AddressGate) -> None:
        self._inner = inner
        self._gate = gate

    async def start(self, agent: object) -> None:
        start = getattr(self._inner, "start", None)
        if start is not None:
            await start(agent)

    async def stop(self) -> None:
        stop = getattr(self._inner, "stop", None)
        if stop is not None:
            await stop()

    async def __call__(self) -> object:
        item = await self._inner()
        text = _text_of(item)
        if text is not None:
            self._gate.note_user_text(text)
        return item


class _GatedOutput:
    def __init__(self, inner: OutputStream, gate: AddressGate) -> None:
        self._inner = inner
        self._gate = gate

    async def start(self, agent: object) -> None:
        await self._inner.start(agent)

    async def stop(self) -> None:
        await self._inner.stop()

    async def __call__(self, event: BidiOutputEvent) -> None:
        self._gate.observe(event)
        if self._gate.hold_reply(event):
            return
        for pending in self._gate.release():
            await self._inner(pending)
        await self._inner(event)


def _named(text: str) -> bool:
    return _NAME.search(text) is not None


def _text_of(item: object) -> str | None:
    if isinstance(item, str):
        return item
    if isinstance(item, dict) and isinstance(item.get("text"), str):
        return item["text"]
    text = getattr(item, "text", None)
    if isinstance(text, str):
        return text
    return None


def _is_reply(event: BidiOutputEvent) -> bool:
    if isinstance(event, _REPLY_EVENTS):
        return True
    if isinstance(event, (BidiTranscriptStartEvent, BidiTranscriptDeltaEvent, BidiTranscriptStopEvent, BidiTranscriptBlockEvent)):
        return event.role == "assistant"
    return False
