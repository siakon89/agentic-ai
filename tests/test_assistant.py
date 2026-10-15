import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from strands.bidi.types import BidiTextDeltaEvent

from assistant.address import AddressGate
from assistant.capabilities import CAPABILITIES, tools
from assistant.capabilities.research.mail import _subject, send_research
from assistant.capabilities.research.records import latest_research
from assistant.capabilities.research.search import text_from_grounded_response
from assistant.capabilities.research.swarm import build_research_swarm, split_report
from assistant.prompt import load_assistant_prompt
from assistant.record import write_record
from assistant.session import _streams
from hello_world_voice.config import aws_region, research_region
from hello_world_voice.transcript import format_transcript


class AssistantRecordTest(unittest.TestCase):
    def test_writes_the_transcript_only(self) -> None:
        messages = [
            {"role": "user", "content": [{"text": "Alex will send the draft."}]},
            {"role": "assistant", "content": [{"text": "Noted."}]},
        ]
        transcript = format_transcript(messages, assistant_name="BobV2")

        with tempfile.TemporaryDirectory() as folder:
            path = write_record(transcript, Path(folder))
            self.assertTrue(path.name.endswith(".md"))
            text = path.read_text(encoding="utf-8")

        self.assertIn("# Record", text)
        self.assertIn("Speaker: Alex will send the draft.", text)
        self.assertIn("BobV2: Noted.", text)
        self.assertNotIn("Action points", text)


class AddressGateTest(unittest.TestCase):
    def test_ignores_a_turn_that_does_not_use_the_name(self) -> None:
        gate = AddressGate()
        gate.note_user_text("but you are speaking now without addressing you")
        self.assertFalse(gate.addressed)

    def test_opens_when_the_name_is_used(self) -> None:
        gate = AddressGate()
        gate.note_user_text("BobV2, what did the research find")
        self.assertTrue(gate.addressed)

    def test_holds_a_reply_that_was_not_addressed(self) -> None:
        gate = AddressGate()
        gate.note_user_text("but you are speaking now without addressing you")
        reply = BidiTextDeltaEvent("I can only speak when you address me as BobV2.", "text-1")
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
        self.assertIn("You are BobV2", prompt)
        self.assertIn("Speak when the user addresses you as BobV2.", prompt)
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
        graph = build_research_swarm()
        self.assertEqual(list(graph.nodes), ["researcher", "reviewer", "gatherer"])
        edges = {(edge.from_node.node_id, edge.to_node.node_id) for edge in graph.edges}
        self.assertEqual(edges, {("researcher", "reviewer"), ("reviewer", "gatherer")})
        self.assertEqual(graph.nodes["researcher"].executor.model.config["max_tokens"], 2048)
        self.assertIsNone(graph.nodes["reviewer"].executor.model.config.get("max_tokens"))
        self.assertEqual(
            graph.nodes["reviewer"].executor.model.config["additional_request_fields"],
            {"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}},
        )
        self.assertEqual(graph.nodes["gatherer"].executor.model.config["max_tokens"], 2000)
        self.assertEqual(graph.nodes["researcher"].executor.model.config["model_id"], "global.amazon.nova-2-lite-v1:0")
        self.assertEqual(
            graph.nodes["researcher"].executor.model.client.meta.region_name,
            aws_region(),
        )
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("RESEARCH_REGION", None)
            self.assertEqual(research_region(), "us-east-1")
        researcher_prompt = graph.nodes["researcher"].executor.system_prompt
        self.assertIn("Call web_search exactly once.", researcher_prompt)
        self.assertIn("Three or four claims.", researcher_prompt)
        reviewer_prompt = graph.nodes["reviewer"].executor.system_prompt
        self.assertIn("Prefer that text over opening pages.", reviewer_prompt)
        gatherer_prompt = graph.nodes["gatherer"].executor.system_prompt
        self.assertIn("## Sources", gatherer_prompt)

    def test_splits_short_and_sources(self) -> None:
        report = split_report("## Short\nA brief.\n\n## Sources\n- Tip (https://example.com)")
        self.assertEqual(report.short, "A brief.")
        self.assertEqual(report.long, "- Tip (https://example.com)")

    def test_splits_legacy_long_heading(self) -> None:
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

    def test_truncates_a_long_search(self) -> None:
        text = text_from_grounded_response(
            {"output": {"message": {"content": [{"text": "x" * 7000}]}}}
        )
        self.assertLessEqual(len(text), 6100)
        self.assertTrue(text.endswith("[Search text truncated.]"))


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
            with patch.dict(
                "os.environ",
                {"ASSISTANT_EMAIL_TO": "you@example.com", "ASSISTANT_EMAIL_FROM": ""},
                clear=False,
            ):
                with patch("assistant.capabilities.research.mail._ses_send") as send:
                    spoken = send_research(path)
        send.assert_called_once_with(
            "you@example.com",
            "you@example.com",
            "Research: topic",
            "# Research: topic\n\nDetails.\n",
        )
        self.assertIn("you@example.com", spoken)

    def test_email_requires_a_recipient(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "2026-10-14-120000-research.md"
            path.write_text("# Research: topic\n", encoding="utf-8")
            with patch.dict("os.environ", {"ASSISTANT_EMAIL_TO": ""}, clear=False):
                spoken = send_research(path)
        self.assertIn("ASSISTANT_EMAIL_TO", spoken)

    def test_empty_report_uses_a_fallback_subject(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "empty.md"
            path.write_text("", encoding="utf-8")
            self.assertEqual(_subject(path), "Research report")


if __name__ == "__main__":
    unittest.main()
