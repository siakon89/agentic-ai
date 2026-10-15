"""Open Bob's listening session and keep it open until Ctrl+C."""

import asyncio

from strands.bidi import BidiAgent
from strands.bidi.models import BedrockNovaSonicModel
from strands.types.content import Message

from hello_world_voice.address import guard
from hello_world_voice.audio import audio_devices_available, is_missing_audio_device, open_streams
from hello_world_voice.config import sonic_region, voice_model_id
from hello_world_voice.prompt import load_bob_prompt
from hello_world_voice.tools import explain_voice_agent, save_summary


async def listen() -> list[Message]:
    """Stream the conversation and return Bob's message history.

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
    inputs, outputs = guard(*open_streams(use_audio), name="Bob")
    try:
        await agent.run(inputs=inputs, outputs=outputs)
    except asyncio.CancelledError:
        pass
    return list(agent.messages)


def _agent(use_audio: bool) -> BidiAgent:
    model = BedrockNovaSonicModel(
        model_id=voice_model_id(),
        region=sonic_region(),
        voice="matthew",
    )
    return BidiAgent(
        model=model,
        tools=[save_summary, explain_voice_agent],
        system_prompt=load_bob_prompt(use_audio=use_audio),
    )


def _explain(use_audio: bool) -> None:
    print("Opening a listening session. Bob stays silent until you address him.")
    if use_audio:
        print('Say "Bob" and he answers through the speakers.')
    else:
        print("No microphone or speaker is available, so type the conversation.")
    print('Say "Bob, take notes" for a summary. The session stays open.')
    print('Say "Bob, what can a voice agent do?" to hear what he can do.')
    print("Ctrl+C closes the session and writes the full notes.")
