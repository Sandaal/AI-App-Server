# Invoice extraction

Upload invoices (PDF, scans, photos, Office files) and get the fields you define back as JSON, each with the page and quote it was found in.

## What's in this folder

| | |
|---|---|
| `ai-app.yaml` | the app: models, settings, guardrails, page |
| `schema.json` | the fields to extract (JSON Schema) |
| `instructions.md` | rules for the extraction |
| `samples/` | an example invoice |
| `tests/` | tests |
| `evals/` | quality checks |

`.github/copilot-instructions.md` teaches coding assistants this SDK.

## Run it

You need a running server ([install](https://sandaal.github.io/ai-app-server/install/)) and a model key:

```bash
aiapp secret set OPENAI_API_KEY          # or use another provider, see below
cd invoice-extraction
aiapp deploy
```

Open **http://127.0.0.1:8080/apps/invoice-extraction/** for the upload page.

Or call it:

```bash
curl -X POST -F file=@samples/invoice.txt \
  "http://127.0.0.1:8080/apps/invoice-extraction/extract?wait=60"
```

## Extend it

- **Other documents:** change `schema.json` to the fields of contracts, purchase orders, ID documents… and adjust `instructions.md`.
- **Large batches:** call `/extract` without `?wait`; it returns a job id, then fetch `/result?id=JOB`. `job_concurrency` sets how many run at once.
- **Send results on:** add a route or job in Python that posts the JSON to your ERP ([handlers guide](https://sandaal.github.io/ai-app-server/build/handlers/)).

## Change it and redeploy

1. Copy this folder into your own repository (keep the folder; rename `app:` in `ai-app.yaml` if you like).
2. Make your changes. While you work, `aiapp dev` redeploys on every save and keeps the last good version if something breaks.
3. Check it: `aiapp test` (if there is a `tests/` folder) and `aiapp eval` (with `evals/`).
4. Deploy to your server: `aiapp deploy`. Every deploy is a new version with no downtime; `aiapp rollback` goes back.

**Another model provider:** change `models:` in `ai-app.yaml` (Azure OpenAI, Anthropic, Gemini, Bedrock, or a local Ollama), see [Model providers](https://sandaal.github.io/ai-app-server/install/models/).

**Before others use it:** API keys or sign-in, HTTPS and quotas, see the [security checklist](https://sandaal.github.io/ai-app-server/operate/security/).

Blueprint: `document-extraction` · [All settings](https://sandaal.github.io/ai-app-server/build/blueprints/) · [ai-app.yaml reference](https://sandaal.github.io/ai-app-server/build/manifest/)
