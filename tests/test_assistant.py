import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from strands.bidi.types import BidiTextDeltaEvent

from assistant.address import AddressGate
from assistant.capabilities import CAPABILITIES, tools
from assistant.capabilities.research.mail import DEFAULT_RECIPIENT, _subject, send_research
from assistant.capabilities.research.records import latest_research
from assistant.capabilities.research.search import text_from_grounded_response
from assistant.capabilities.research.swarm import build_research_swarm, split_report
from assistant.prompt import load_assistant_prompt
from assistant.record import write_record
from assistant.session import _streams
from meeting_listener.transcript import format_transcript


class AssistantRecordTest(unittest.TestCase):
    def test_writes_the_transcript_only(self) -> None:
        messages = [
            {"role": "user", "content": [{"text": "Alex will send the draft."}]},
            {"role": "assistant", "content": [{"text": "Noted."}]},
        ]
        transcript = format_transcript(messages, assistant_name="Ultron")

        with tempfile.TemporaryDirectory() as folder:
            path = write_record(transcript, Path(folder))
            self.assertTrue(path.name.endswith(".md"))
            text = path.read_text(encoding="utf-8")

        self.assertIn("# Record", text)
        self.assertIn("Speaker: Alex will send the draft.", text)
        self.assertIn("Ultron: Noted.", text)
        self.assertNotIn("Action points", text)


class AddressGateTest(unittest.TestCase):
    def test_ignores_a_turn_that_does_not_use_the_name(self) -> None:
        gate = AddressGate()
        gate.note_user_text("but you are speaking now without addressing you")
        self.assertFalse(gate.addressed)

    def test_opens_when_the_name_is_used(self) -> None:
        gate = AddressGate()
        gate.note_user_text("Ultron, what did the research find")
        self.assertTrue(gate.addressed)

    def test_holds_a_reply_that_was_not_addressed(self) -> None:
        gate = AddressGate()
        gate.note_user_text("but you are speaking now without addressing you")
        reply = BidiTextDeltaEvent("I can only speak when you address me as Ultron.", "text-1")
        self.assertTrue(gate.hold_reply(reply))
        self.assertEqual(gate.release(), [])


class SessionDisplayTest(unittest.TestCase):
    def test_text_mode_shows_replies(self) -> None:
        _, outputs = _streams(False)
        self.assertTrue(outputs[0]._config["show_text"])

    def test_voice_mode_hides_written_replies(self) -> None:
        _, outputs = _streams(True)
        self.assertFalse(outputs[0]._console_output._config["show_text"])


class AssistantPromptTest(unittest.TestCase):
    def test_speaks_only_when_addressed(self) -> None:
        prompt = load_assistant_prompt(use_audio=True)
        self.assertIn("You are Ultron", prompt)
        self.assertIn("Speak when the user addresses you as Ultron.", prompt)
        self.assertIn("Stay silent when your name is not used.", prompt)
        self.assertNotIn("save_summary", prompt)
        self.assertIn("Do not answer in text.", prompt)
        self.assertIn("Do not answer in writing.", prompt)
        self.assertIn("deep_research", prompt)
        self.assertIn("read_research", prompt)
        self.assertIn("email_research", prompt)


class CapabilityRegistryTest(unittest.TestCase):
    def test_research_is_registered(self) -> None:
        names = [tool.tool_spec["name"] for tool in tools()]
        self.assertEqual(names, ["deep_research", "read_research", "email_research"])
        self.assertEqual([type(capability).__name__ for capability in CAPABILITIES], ["Research"])


class ResearchSwarmTest(unittest.TestCase):
    def test_three_roles(self) -> None:
        swarm = build_research_swarm()
        self.assertEqual(list(swarm.nodes), ["researcher", "reviewer", "gatherer"])

    def test_splits_short_and_long(self) -> None:
        report = split_report("## Short\nA brief.\n\n## Long\nA longer article.")
        self.assertEqual(report.short, "A brief.")
        self.assertEqual(report.long, "A longer article.")

    def test_reads_grounded_citations(self) -> None:
        text = text_from_grounded_response(
            {
                "output": {
                    "message": {
                        "content": [
                            {"text": "Nova can search."},
                            {
                                "citationsContent": {
                                    "citations": [{"location": {"web": {"url": "https://example.com"}}}]
                                }
                            },
                        ]
                    }
                }
            }
        )
        self.assertIn("Nova can search.", text)
        self.assertIn("Source: https://example.com", text)


class ResearchRecordTest(unittest.TestCase):
    def test_reads_the_latest_report(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            older = root / "2026-10-14-100000-research.md"
            newer = root / "2026-10-14-110000-research.md"
            older.write_text("# Research: older\n", encoding="utf-8")
            newer.write_text("# Research: newer\n", encoding="utf-8")
            self.assertEqual(latest_research(root), newer)

    def test_email_sends_through_ses(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "2026-10-14-120000-research.md"
            path.write_text("# Research: topic\n\nDetails.\n", encoding="utf-8")
            with patch("assistant.capabilities.research.mail._ses_send") as send:
                spoken = send_research(path)
        send.assert_called_once_with(
            DEFAULT_RECIPIENT,
            DEFAULT_RECIPIENT,
            "Research: topic",
            "# Research: topic\n\nDetails.\n",
        )
        self.assertIn(DEFAULT_RECIPIENT, spoken)

    def test_empty_report_uses_a_fallback_subject(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "empty.md"
            path.write_text("", encoding="utf-8")
            self.assertEqual(_subject(path), "Research report")


if __name__ == "__main__":
    unittest.main()
