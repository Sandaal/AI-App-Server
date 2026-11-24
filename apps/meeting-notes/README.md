# Meeting notes

Turns recordings or transcripts into a summary, decisions, action items with owners, and open questions.

## What's in this folder

| | |
|---|---|
| `ai-app.yaml` | the app: models, settings, guardrails, page |
| `samples/transcript.txt` | an example transcript |

`.github/copilot-instructions.md` teaches coding assistants this SDK.

## Run it

You need a running server ([install](https://sandaal.github.io/aiapp-server/install/)) and a model key:

```bash
aiapp secret set OPENAI_API_KEY          # or use another provider, see below
cd meeting-notes
aiapp deploy
```

Open **http://127.0.0.1:8080/apps/meeting-notes/** for the upload page.

Or call it:

```bash
curl -X POST -F file=@samples/transcript.txt \
  "http://127.0.0.1:8080/apps/meeting-notes/notes?wait=120"
```

## Extend it

- **Audio:** upload mp3, m4a, wav, webm, ogg or flac; the `transcribe` model turns it into text.
- **Your vocabulary:** list product and people names in `meeting_notes.vocabulary` so they are spelled right.
- **Send the notes on:** subscribe to the result and post action items to Teams, Jira or email ([guide](https://sandaal.github.io/aiapp-server/build/jobs-events/)).

## Change it and redeploy

1. Copy this folder into your own repository (keep the folder; rename `app:` in `ai-app.yaml` if you like).
2. Make your changes. While you work, `aiapp dev` redeploys on every save and keeps the last good version if something breaks.
3. Check it: `aiapp test` (if there is a `tests/` folder) and `aiapp eval` (with `evals/`).
4. Deploy to your server: `aiapp deploy`. Every deploy is a new version with no downtime; `aiapp rollback` goes back.

**Another model provider:** change `models:` in `ai-app.yaml` (Azure OpenAI, Anthropic, Gemini, Bedrock, or a local Ollama), see [Model providers](https://sandaal.github.io/aiapp-server/install/models/).

**Before others use it:** API keys or sign-in, HTTPS and quotas, see the [security checklist](https://sandaal.github.io/aiapp-server/operate/security/).

Blueprint: `meeting-notes` · [All settings](https://sandaal.github.io/aiapp-server/build/blueprints/) · [ai-app.yaml reference](https://sandaal.github.io/aiapp-server/build/manifest/)
