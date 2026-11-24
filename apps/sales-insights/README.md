# Sales insights

Answers questions about your data; the model writes read-only SQL, runs it, and shows you the query.

## What's in this folder

| | |
|---|---|
| `ai-app.yaml` | the app: models, settings, guardrails, page |
| `data/sales.csv` | example data; every CSV becomes a table |

`.github/copilot-instructions.md` teaches coding assistants this SDK.

## Run it

You need a running server ([install](https://sandaal.github.io/ai-app-server/install/)) and a model key:

```bash
aiapp secret set OPENAI_API_KEY          # or use another provider, see below
cd sales-insights
aiapp deploy
```

Open **http://127.0.0.1:8080/apps/sales-insights/** for the ask page.

Or call it:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"question":"Which region had the highest revenue last quarter?"}' \
  http://127.0.0.1:8080/apps/sales-insights/ask
```

## Extend it

- **Your database:** add PostgreSQL or SQL Server under `insights.databases` with a login that can only read, and list the `tables` it may use.
- **Business rules:** put definitions (fiscal year, currency, what "active customer" means) in `insights.instructions`.

## Change it and redeploy

1. Copy this folder into your own repository (keep the folder; rename `app:` in `ai-app.yaml` if you like).
2. Make your changes. While you work, `aiapp dev` redeploys on every save and keeps the last good version if something breaks.
3. Check it: `aiapp test` (if there is a `tests/` folder) and `aiapp eval` (with `evals/`).
4. Deploy to your server: `aiapp deploy`. Every deploy is a new version with no downtime; `aiapp rollback` goes back.

**Another model provider:** change `models:` in `ai-app.yaml` (Azure OpenAI, Anthropic, Gemini, Bedrock, or a local Ollama), see [Model providers](https://sandaal.github.io/ai-app-server/install/models/).

**Before others use it:** API keys or sign-in, HTTPS and quotas, see the [security checklist](https://sandaal.github.io/ai-app-server/operate/security/).

Blueprint: `insights` · [All settings](https://sandaal.github.io/ai-app-server/build/blueprints/) · [ai-app.yaml reference](https://sandaal.github.io/ai-app-server/build/manifest/)
