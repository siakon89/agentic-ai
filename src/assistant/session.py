"""Open Assistant's listening session and keep it open until Ctrl+C."""

import asyncio

from strands.bidi import BidiAgent
from strands.bidi.models import BedrockNovaSonicModel
from strands.types.content import Message

from assistant.address import guard
from assistant.capabilities import tools
from assistant.prompt import load_assistant_prompt
from hello_world_voice.audio import audio_devices_available, is_missing_audio_device, open_streams
from hello_world_voice.config import sonic_region, voice_model_id

_PLACEHOLDER = "Recording. Say 'Bob, research …' or address him. Ctrl+C saves the record."


async def listen() -> list[Message]:
    """Stream the conversation and return the message history.

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
    inputs, outputs = guard(*_streams(use_audio))
    try:
        await agent.run(inputs=inputs, outputs=outputs)
    except asyncio.CancelledError:
        pass
    return list(agent.messages)


def _streams(use_audio: bool):
    """Show written replies only when there is no speaker."""
    return open_streams(use_audio, placeholder=_PLACEHOLDER, show_text=not use_audio)


def _agent(use_audio: bool) -> BidiAgent:
    model = BedrockNovaSonicModel(
        model_id=voice_model_id(),
        region=sonic_region(),
        voice="matthew",
    )
    return BidiAgent(
        model=model,
        tools=tools(),
        system_prompt=load_assistant_prompt(use_audio=use_audio),
    )


def _explain(use_audio: bool) -> None:
    print("Opening a recording session. Bob stays silent until you address him.")
    if use_audio:
        print('Say "Bob" and he answers through the speakers.')
    else:
        print("No microphone or speaker is available, so type the conversation.")
    print('Say "Bob, research" and a topic to run the research swarm.')
    print('Say "Bob, email the research" to send the latest report.')
    print("Ctrl+C closes the session and saves the record.")
