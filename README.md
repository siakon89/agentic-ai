# Meeting listener

A Strands bidirectional agent that opens a live session, listens to a conversation, then writes a summary and action points.

The listener uses [Amazon Nova Sonic](https://strandsagents.com/docs/user-guide/sdk/bidi/) through `BidiAgent`. When the session closes, a second Strands agent reads the transcript and returns structured notes.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PortAudio (`sudo apt-get install portaudio19-dev` on Debian/Ubuntu)
- AWS credentials that can invoke Amazon Nova Sonic and Amazon Nova Lite
- A Nova Sonic region: `us-east-1`, `us-west-2`, `eu-north-1`, or `ap-northeast-1`

Enable both models in the Amazon Bedrock console. Credentials can come from `aws configure`, standard AWS environment variables, or `AWS_BEARER_TOKEN_BEDROCK`.

## Run

```bash
export AWS_REGION=us-east-1
uv sync
uv run meeting-listener
```

Ultron's instructions are the [RISEN](https://dev.to/gunnargrosch/writing-system-prompts-that-actually-work-the-risen-framework-for-ai-agents-4p94) prompt in `prompts/ultron.md`. The agent loads that file when the session opens.

Ultron listens and stays silent until you address him by name. Say **Ultron** followed by a question or request and he answers out loud, then keeps listening. **Ultron, summarize** speaks the summary and action points and saves them under `notes/`. Ctrl+C closes the session and writes the full catalog. Typing works as well.

If the machine has no microphone or speaker, which is common on WSL, the session switches to typed input and skips PortAudio.

Notes print in the terminal and are saved under `notes/`.

Optional model overrides:

- `VOICE_MODEL_ID` (default `amazon.nova-2-5-sonic`)
- `NOTES_MODEL_ID` (default `amazon.nova-lite-v1:0`)

Use headphones, or rely on the built-in echo cancellation, so the microphone does not pick up the agent's opening line as part of the conversation.

## Assistant

`assistant` is the same kind of live session, limited to keeping a record of what is said. Ultron stays silent until you address him by name, then answers out loud. He does not summarize. Ctrl+C saves the transcript under `records/`.

```bash
uv run assistant
```

Its instructions are the RISEN prompt in `prompts/assistant.md`. Each extra ability lives in `src/assistant/capabilities/` and is listed in `CAPABILITIES`. Say **Ultron, research** and a topic. A swarm searches the web, checks the claims, and writes a short brief plus a long article under `records/`. Ultron speaks only the short brief. **Ultron, what did the research find** reads the latest report. **Ultron, email the research** sends that report to `siaterliskonsta@gmail.com`.

Sending mail uses Amazon SES in the same region as the rest of the assistant. The verified From and To address is `siaterliskonsta@gmail.com`.

The swarm uses [Nova 2 Lite](https://docs.aws.amazon.com/nova/latest/nova2-userguide/what-is-nova-2.html) (`us.amazon.nova-2-lite-v1:0`), the current Nova model with web grounding, extended thinking, and a 64K output limit:

- The researcher searches with [Nova Grounding](https://docs.aws.amazon.com/nova/latest/nova2-userguide/web-grounding.html).
- The reviewer checks claims with extended thinking set to high, and can open the cited pages.
- The gatherer writes the short brief and the long article.

Web Grounding runs in US regions. Keep `AWS_REGION` on `us-east-1`. The IAM identity also needs `bedrock:InvokeTool` on `system-tool/amazon.nova_grounding`.
