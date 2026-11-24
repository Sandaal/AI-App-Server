# Document summary

Summaries and key points of long documents, read in parts so length doesn't matter.

## What's in this folder

| | |
|---|---|
| `ai-app.yaml` | the app: models, settings, guardrails, page |
| `samples/` | an example report |

`.github/copilot-instructions.md` teaches coding assistants this SDK.

## Run it

You need a running server ([install](https://sandaal.github.io/aiapp-server/install/)) and a model key:

```bash
aiapp secret set OPENAI_API_KEY          # or use another provider, see below
cd document-summary
aiapp deploy
```

Open **http://127.0.0.1:8080/apps/document-summary/** for the upload page.

Or call it:

```bash
curl -X POST -F file=@samples/report.md \
  "http://127.0.0.1:8080/apps/document-summary/summarize?wait=120"
```

## Extend it

- **Style:** `summary.style` is `paragraph`, `bullets` or `executive`; `summary.max_words` sets the length.
- **Automatic summaries:** start the `summarize` job from a [schedule or event](https://sandaal.github.io/aiapp-server/build/jobs-events/) when new documents arrive.

## Change it and redeploy

1. Copy this folder into your own repository (keep the folder; rename `app:` in `ai-app.yaml` if you like).
2. Make your changes. While you work, `aiapp dev` redeploys on every save and keeps the last good version if something breaks.
3. Check it: `aiapp test` (if there is a `tests/` folder) and `aiapp eval` (with `evals/`).
4. Deploy to your server: `aiapp deploy`. Every deploy is a new version with no downtime; `aiapp rollback` goes back.

**Another model provider:** change `models:` in `ai-app.yaml` (Azure OpenAI, Anthropic, Gemini, Bedrock, or a local Ollama), see [Model providers](https://sandaal.github.io/aiapp-server/install/models/).

**Before others use it:** API keys or sign-in, HTTPS and quotas, see the [security checklist](https://sandaal.github.io/aiapp-server/operate/security/).

Blueprint: `summarization` · [All settings](https://sandaal.github.io/aiapp-server/build/blueprints/) · [ai-app.yaml reference](https://sandaal.github.io/aiapp-server/build/manifest/)
