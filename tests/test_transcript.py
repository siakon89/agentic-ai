import unittest
from unittest.mock import Mock

from meeting_listener.audio import default_audio_devices_present
from meeting_listener.notes import ActionPoint, MeetingNotes, render_notes, render_spoken
from meeting_listener.prompt import load_ultron_prompt
from meeting_listener.transcript import format_transcript


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
                    "Ultron: I'm listening.",
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


class UltronPromptTest(unittest.TestCase):
    def test_risen_sections(self) -> None:
        prompt = load_ultron_prompt(use_audio=True)
        for heading in ("# Role", "# Instructions", "# Steps", "# Expectation", "# Narrowing"):
            self.assertIn(heading, prompt)
        self.assertIn("You are Ultron", prompt)
        self.assertIn("save_summary", prompt)
        self.assertIn("speakers", prompt)
        self.assertIn("Reply only in English.", prompt)
        self.assertIn("Speak when the user addresses you as Ultron.", prompt)
        self.assertIn("Do not end the session after you speak", prompt)

    def test_text_channel(self) -> None:
        prompt = load_ultron_prompt(use_audio=False)
        self.assertIn("typed text", prompt)


if __name__ == "__main__":
    unittest.main()
