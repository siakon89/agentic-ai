"""Open Ultron's listening session and keep it open until Ctrl+C."""

import asyncio

from strands.bidi import BidiAgent
from strands.bidi.models import BedrockNovaSonicModel
from strands.types.content import Message

from meeting_listener.audio import audio_devices_available, is_missing_audio_device, open_streams
from meeting_listener.config import aws_region, voice_model_id
from meeting_listener.prompt import load_ultron_prompt
from meeting_listener.tools import save_summary


async def listen() -> list[Message]:
    """Stream the conversation and return Ultron's message history.

    The microphone is used when a default input and output device exist.
    Otherwise the session accepts typed conversation.
    """
    if audio_devices_available():
        try:
            return await _session(use_audio=True)
        except OSError as error:
            if not is_missing_audio_device(error):
                raise
            print("The microphone could not be opened. Continuing with typed input.")

    return await _session(use_audio=False)


async def _session(*, use_audio: bool) -> list[Message]:
    _explain(use_audio)
    agent = _agent(use_audio)
    inputs, outputs = open_streams(use_audio)
    try:
        await agent.run(inputs=inputs, outputs=outputs)
    except asyncio.CancelledError:
        pass
    return list(agent.messages)


def _agent(use_audio: bool) -> BidiAgent:
    model = BedrockNovaSonicModel(
        model_id=voice_model_id(),
        region=aws_region(),
        voice="matthew",
    )
    return BidiAgent(
        model=model,
        tools=[save_summary],
        system_prompt=load_ultron_prompt(use_audio=use_audio),
    )


def _explain(use_audio: bool) -> None:
    print("Opening a listening session. Ultron stays silent until you address him.")
    if use_audio:
        print('Say "Ultron" and he answers through the speakers.')
    else:
        print("No microphone or speaker is available, so type the conversation.")
    print('Say "Ultron, summarize" for notes. The session stays open.')
    print("Ctrl+C closes the session and writes the full notes.")
