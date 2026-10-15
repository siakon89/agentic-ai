# Meeting listener

Two Strands voice sessions. `hello-world-voice` is Bob: he holds a conversation when you say his name, takes notes, and can explain what a voice agent can do. `assistant` is BobV2, a recorder with a research swarm.

Both use [Amazon Nova Sonic](https://strandsagents.com/docs/user-guide/sdk/bidi/) through `BidiAgent`. When Bob's session closes, a second Strands agent reads the transcript and returns structured notes.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PortAudio (`sudo apt-get install portaudio19-dev` on Debian/Ubuntu)
- AWS credentials that can invoke Amazon Nova Sonic and Amazon Nova Lite
- Nova Sonic in `eu-north-1` (override with `SONIC_REGION`)
- Amazon SES in that same region, with `ses:SendEmail`. Verify the address in `ASSISTANT_EMAIL_TO`. The assistant sends research from `ASSISTANT_EMAIL_FROM` when that is set, and otherwise from `ASSISTANT_EMAIL_TO`. While the account is in the SES sandbox, both the sender and the recipient must be verified.

Enable both models in the Amazon Bedrock console. Credentials can come from `aws configure`, standard AWS environment variables, or `AWS_BEARER_TOKEN_BEDROCK`.

## Hello world voice

```bash
export AWS_REGION=us-east-1
export SONIC_REGION=eu-north-1
uv sync
uv run hello-world-voice
```

Bob's instructions are the [RISEN](https://dev.to/gunnargrosch/writing-system-prompts-that-actually-work-the-risen-framework-for-ai-agents-4p94) prompt in `prompts/bob.md`. The agent loads that file when the session opens.

Bob stays silent until you say his name. A reply is dropped unless that turn contains **Bob**.

- Say **Bob** and continue, and he talks with you out loud.
- Say **Bob, take notes** and he speaks the summary and action points, then saves them under `notes/`.
- Say **Bob, what can a voice agent do?** and he explains what a voice agent can do.

Ctrl+C closes the session and writes the full notes. Typing works as well.

If the machine has no microphone or speaker, which is common on WSL, the session switches to typed input and skips PortAudio. When WSL does have a speaker, playback uses a deeper buffer so ALSA does not report an underrun while the agent is talking. Set `PULSE_LATENCY_MSEC` to change that buffer.

Notes print in the terminal and are saved under `notes/`.

Optional model overrides:

- `VOICE_MODEL_ID` (default `amazon.nova-2-5-sonic`)
- `NOTES_MODEL_ID` (default `amazon.nova-lite-v1:0`)

Use headphones, or rely on the built-in echo cancellation, so the microphone does not pick up the agent's opening line as part of the conversation.

Bob lives in `src/hello_world_voice/`. `session.py` opens the live conversation. `address.py` drops a reply unless that turn says "Bob". `audio.py` connects the microphone and speakers. `tools.py` is the notes tool and the voice-agent explanation he can call without hanging up. `notes.py` writes the summary and action points, `transcript.py` turns the history into text, and `prompt.py` loads `prompts/bob.md`. Saved notes go in `notes/`.

## Assistant

`assistant` is the same kind of live session, limited to keeping a record of what is said. BobV2 stays silent until you address him by name, then answers out loud. He does not summarize. Ctrl+C saves the transcript under `records/`.

```bash
export AWS_REGION=us-east-1
export SONIC_REGION=eu-north-1
export ASSISTANT_EMAIL_TO="you@example.com"
export ASSISTANT_EMAIL_FROM="you@example.com"  # optional; defaults to ASSISTANT_EMAIL_TO
uv sync
uv run assistant
```

Its instructions are the RISEN prompt in `prompts/assistant.md`. Each extra ability lives in `src/assistant/capabilities/` and is listed in `CAPABILITIES`. Say **BobV2, research** and a topic. Three agents then run in order: one search, a light claim check, and a short brief plus sources list under `records/`. BobV2 speaks only the short brief. **BobV2, what did the research find** reads the latest report. **BobV2, email the research** sends that report through Amazon SES to `ASSISTANT_EMAIL_TO`.

Those agents use [Nova 2 Lite](https://docs.aws.amazon.com/nova/latest/nova2-userguide/what-is-nova-2.html) through the global profile (`global.amazon.nova-2-lite-v1:0`) in your `AWS_REGION`, so Stockholm works for the researcher, reviewer, and gatherer:

- The researcher runs one [Nova Grounding](https://docs.aws.amazon.com/nova/latest/nova2-userguide/web-grounding.html) search and returns three or four claims.
- The reviewer checks those claims against the search packet with low extended thinking, and opens a page only when a URL is missing.
- The gatherer writes the short spoken brief and a short sources list.

Web Grounding itself still needs the US CRIS profile (`us.amazon.nova-2-lite-v1:0`), so the search tool calls Bedrock in `us-east-1` (override with `RESEARCH_REGION`). Keep Nova Sonic on `SONIC_REGION=eu-north-1`. The IAM identity also needs `bedrock:InvokeTool` on `system-tool/amazon.nova_grounding`.

The assistant lives in `src/assistant/`. `session.py` opens the live conversation and registers every capability. `address.py` drops a reply unless that turn says "BobV2". `prompt.py` loads `prompts/assistant.md` and appends each capability's instructions. `record.py` writes the session transcript under `records/`.

Extra abilities are packages under `src/assistant/capabilities/`, listed in `CAPABILITIES`. The research pipeline is `capabilities/research/`: `swarm.py` runs the researcher, then the reviewer, then the gatherer, `search.py` calls Nova Grounding, `records.py` reads saved reports, and `mail.py` sends the latest one. Their prompts are in `capabilities/research/prompts/`. Add another swarm by creating a package beside `research` and appending it to `CAPABILITIES`.
