# Code assistant

Answers questions about a codebase, citing files and line numbers.

## What's in this folder

| | |
|---|---|
| `ai-app.yaml` | the app: models, settings, guardrails, page |
| `repo/` | example code; point it at your own repository instead |

`.github/copilot-instructions.md` teaches coding assistants this SDK.

## Run it

You need a running server ([install](https://sandaal.github.io/aiapp-server/install/)) and a model key:

```bash
aiapp secret set OPENAI_API_KEY          # or use another provider, see below
cd code-assistant
aiapp deploy
```

Open **http://127.0.0.1:8080/apps/code-assistant/** for the chat page.

Or call it:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"message":"How is the discount calculated?"}' \
  http://127.0.0.1:8080/apps/code-assistant/chat
```

## Extend it

- **Your repository:** replace the `sources:` entry with a Git source (the commented example), with `schedule: 1h` to keep it in sync.
- **Several repositories:** list several sources.

## Change it and redeploy

1. Copy this folder into your own repository (keep the folder; rename `app:` in `ai-app.yaml` if you like).
2. Make your changes. While you work, `aiapp dev` redeploys on every save and keeps the last good version if something breaks.
3. Check it: `aiapp test` (if there is a `tests/` folder) and `aiapp eval` (with `evals/`).
4. Deploy to your server: `aiapp deploy`. Every deploy is a new version with no downtime; `aiapp rollback` goes back.

**Another model provider:** change `models:` in `ai-app.yaml` (Azure OpenAI, Anthropic, Gemini, Bedrock, or a local Ollama), see [Model providers](https://sandaal.github.io/aiapp-server/install/models/).

**Before others use it:** API keys or sign-in, HTTPS and quotas, see the [security checklist](https://sandaal.github.io/aiapp-server/operate/security/).

Blueprint: `code-assistant` · [All settings](https://sandaal.github.io/aiapp-server/build/blueprints/) · [ai-app.yaml reference](https://sandaal.github.io/aiapp-server/build/manifest/)
