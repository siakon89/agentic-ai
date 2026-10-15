import os
import unittest
from unittest.mock import Mock, patch

from strands.bidi.types import BidiTextDeltaEvent

from hello_world_voice.address import AddressGate
from hello_world_voice.audio import (
    _is_recovered_underrun,
    default_audio_devices_present,
    playback_latency_ms,
)
from hello_world_voice.notes import ActionPoint, MeetingNotes, render_notes, render_spoken
from hello_world_voice.prompt import load_bob_prompt
from hello_world_voice.tools import VOICE_AGENT_ANSWER, explain_voice_agent
from hello_world_voice.transcript import format_transcript


class FormatTranscriptTest(unittest.TestCase):
    def test_keeps_speech_and_skips_tools(self) -> None:
        messages = [
            {"role": "assistant", "content": [{"text": "I'm listening."}]},
            {"role": "user", "content": [{"text": "Alex will send the draft by Friday."}]},
            {
                "role": "assistant",
                "content": [{"toolUse": {"name": "end_conversation", "toolUseId": "1", "input": {}}}],
            },
            {"role": "user", "content": [{"text": "  [Transcript unavailable.]  "}]},
            {"role": "user", "content": [{"text": "  Also   book   the room.  "}]},
            {
                "role": "user",
                "content": [
                    {
                        "text": (
                            "The listening session is open. Greet the user out loud "
                            "in one short sentence and invite them to talk."
                        )
                    }
                ],
            },
        ]

        self.assertEqual(
            format_transcript(messages),
            "\n".join(
                [
                    "Bob: I'm listening.",
                    "Speaker: Alex will send the draft by Friday.",
                    "Speaker: Also book the room.",
                ]
            ),
        )


class AudioDeviceProbeTest(unittest.TestCase):
    def test_requires_input_and_output(self) -> None:
        audio = Mock()
        self.assertTrue(default_audio_devices_present(audio))
        audio.get_default_input_device_info.assert_called_once()
        audio.get_default_output_device_info.assert_called_once()

    def test_missing_device(self) -> None:
        audio = Mock()
        audio.get_default_output_device_info.side_effect = OSError(-9996, "Invalid device")
        self.assertFalse(default_audio_devices_present(audio))


class PlaybackLatencyTest(unittest.TestCase):
    def test_wsl_deepens_the_speaker_buffer(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PULSE_LATENCY_MSEC", None)
            with patch("hello_world_voice.audio._on_wsl", return_value=True):
                with patch("hello_world_voice.audio._ignore_recovered_underruns"):
                    delay = playback_latency_ms()
            self.assertEqual(delay, 120)
            self.assertEqual(os.environ["PULSE_LATENCY_MSEC"], "120")

    def test_recovered_underrun_is_not_a_failure(self) -> None:
        self.assertTrue(_is_recovered_underrun(b"snd_pcm_recover", b"underrun occurred"))
        self.assertFalse(_is_recovered_underrun(b"snd_pcm_open", b"No such device"))


class RenderNotesTest(unittest.TestCase):
    def test_includes_owner_when_present(self) -> None:
        notes = MeetingNotes(
            summary="The team agreed to send a draft.",
            action_points=[
                ActionPoint(task="Send the draft", owner="Alex"),
                ActionPoint(task="Book the room", owner=None),
            ],
        )

        markdown = render_notes(notes, "Speaker: Send the draft.")

        self.assertIn("The team agreed to send a draft.", markdown)
        self.assertIn("- Send the draft (Alex)", markdown)
        self.assertIn("- Book the room", markdown)
        self.assertIn("Speaker: Send the draft.", markdown)

    def test_empty_actions(self) -> None:
        notes = MeetingNotes(summary="A status check.", action_points=[])
        self.assertIn("- None.", render_notes(notes, "Speaker: All good."))

    def test_spoken_summary(self) -> None:
        notes = MeetingNotes(
            summary="The team agreed to send a draft.",
            action_points=[ActionPoint(task="Send the draft", owner="Alex")],
        )
        spoken = render_spoken(notes)
        self.assertIn("Summary: The team agreed to send a draft.", spoken)
        self.assertIn("Send the draft (Alex)", spoken)


class BobPromptTest(unittest.TestCase):
    def test_risen_sections(self) -> None:
        prompt = load_bob_prompt(use_audio=True)
        for heading in ("# Role", "# Instructions", "# Steps", "# Expectation", "# Narrowing"):
            self.assertIn(heading, prompt)
        self.assertIn("You are Bob", prompt)
        self.assertIn("save_summary", prompt)
        self.assertIn("explain_voice_agent", prompt)
        self.assertIn("have a conversation", prompt)
        self.assertIn("take notes", prompt)
        self.assertIn("speakers", prompt)
        self.assertIn("Reply only in English.", prompt)
        self.assertIn("Speak when the user addresses you as Bob.", prompt)
        self.assertIn("Do not end the session after you speak", prompt)

    def test_text_channel(self) -> None:
        prompt = load_bob_prompt(use_audio=False)
        self.assertIn("typed text", prompt)


class BobAddressGateTest(unittest.TestCase):
    def test_ignores_a_turn_that_does_not_use_the_name(self) -> None:
        gate = AddressGate("Bob")
        gate.note_user_text("please summarize the meeting")
        self.assertFalse(gate.addressed)

    def test_opens_when_bob_is_named(self) -> None:
        gate = AddressGate()
        gate.note_user_text("Bob, what can a voice agent do?")
        self.assertTrue(gate.addressed)

    def test_holds_a_reply_that_was_not_addressed(self) -> None:
        gate = AddressGate("Bob")
        gate.note_user_text("what can a voice agent do?")
        reply = BidiTextDeltaEvent("A voice agent listens to speech.", "text-1")
        self.assertTrue(gate.hold_reply(reply))
        self.assertEqual(gate.release(), [])


class VoiceAgentAnswerTest(unittest.TestCase):
    def test_explains_conversation_notes_and_the_name(self) -> None:
        self.assertIn("hold a conversation", VOICE_AGENT_ANSWER)
        self.assertIn("take notes", VOICE_AGENT_ANSWER)
        self.assertIn("call it by name", VOICE_AGENT_ANSWER)
        self.assertEqual(explain_voice_agent.tool_spec["name"], "explain_voice_agent")


if __name__ == "__main__":
    unittest.main()
