# Ticket triage

Sorts support tickets (or emails, feedback, anything) into your labels, one at a time or in batches.

## What's in this folder

| | |
|---|---|
| `ai-app.yaml` | the app: models, settings, guardrails, page |
| `tests/` | tests |
| `evals/golden.yaml` | quality checks |

`.github/copilot-instructions.md` teaches coding assistants this SDK.

## Run it

You need a running server ([install](https://sandaal.github.io/aiapp-server/install/)) and a model key:

```bash
aiapp secret set OPENAI_API_KEY          # or use another provider, see below
cd ticket-triage
aiapp deploy
```

Open **http://127.0.0.1:8080/apps/ticket-triage/** for the try-it page.

Or call it:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"text":"I was charged twice for my subscription"}' \
  http://127.0.0.1:8080/apps/ticket-triage/classify
```

## Extend it

- **Your labels:** edit `classification.labels`; good descriptions matter more than names.
- **Batches:** send `{"items": [{"id": "1", "text": "..."}, ...]}`.
- **Hands-free:** set `classification.topic` and `output_topic` to classify every record published to a topic and publish the results.
- **Several labels per text:** `multi_label: true`.

## Change it and redeploy

1. Copy this folder into your own repository (keep the folder; rename `app:` in `ai-app.yaml` if you like).
2. Make your changes. While you work, `aiapp dev` redeploys on every save and keeps the last good version if something breaks.
3. Check it: `aiapp test` (if there is a `tests/` folder) and `aiapp eval` (with `evals/`).
4. Deploy to your server: `aiapp deploy`. Every deploy is a new version with no downtime; `aiapp rollback` goes back.

**Another model provider:** change `models:` in `ai-app.yaml` (Azure OpenAI, Anthropic, Gemini, Bedrock, or a local Ollama), see [Model providers](https://sandaal.github.io/aiapp-server/install/models/).

**Before others use it:** API keys or sign-in, HTTPS and quotas, see the [security checklist](https://sandaal.github.io/aiapp-server/operate/security/).

Blueprint: `classification` · [All settings](https://sandaal.github.io/aiapp-server/build/blueprints/) · [ai-app.yaml reference](https://sandaal.github.io/aiapp-server/build/manifest/)
