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
