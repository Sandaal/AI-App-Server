# Customer support

A support assistant that answers from your help centre, looks up orders with your tools, asks a person before refunds, and hands conversations to a human when needed.

## What's in this folder

| | |
|---|---|
| `ai-app.yaml` | the app: models, settings, guardrails, page |
| `docs/` | the help-centre content it answers from |
| `tools.py` | functions the assistant can call (example order lookup and refund) |

`.github/copilot-instructions.md` teaches coding assistants this SDK.

## Run it

You need a running server ([install](https://sandaal.github.io/ai-app-server/install/)) and a model key:

```bash
aiapp secret set OPENAI_API_KEY          # or use another provider, see below
cd customer-support
aiapp deploy
```

Open **http://127.0.0.1:8080/apps/customer-support/** for the chat page.

Or call it:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"message":"Where is my order A-1001?"}' \
  http://127.0.0.1:8080/apps/customer-support/chat
```

## Extend it

- **Connect your systems:** replace the examples in `tools.py` with calls to your order, CRM or ticketing APIs. Each `@app.tool` function's docstring tells the model when to use it.
- **Approvals:** tools listed under `support.approval_required` wait for a person at `/apps/customer-support/_approvals/` (needs the `approver` role: `aiapp key create customer-support --role approver`).
- **Handoffs:** conversations handed to a person are published to the `support.handoffs` topic; add a [subscription](https://sandaal.github.io/ai-app-server/build/jobs-events/) that creates a ticket in your helpdesk.
- **Tone and rules:** edit `support.instructions`.

## Change it and redeploy

1. Copy this folder into your own repository (keep the folder; rename `app:` in `ai-app.yaml` if you like).
2. Make your changes. While you work, `aiapp dev` redeploys on every save and keeps the last good version if something breaks.
3. Check it: `aiapp test` (if there is a `tests/` folder) and `aiapp eval` (with `evals/`).
4. Deploy to your server: `aiapp deploy`. Every deploy is a new version with no downtime; `aiapp rollback` goes back.

**Another model provider:** change `models:` in `ai-app.yaml` (Azure OpenAI, Anthropic, Gemini, Bedrock, or a local Ollama), see [Model providers](https://sandaal.github.io/ai-app-server/install/models/).

**Before others use it:** API keys or sign-in, HTTPS and quotas, see the [security checklist](https://sandaal.github.io/ai-app-server/operate/security/).

Blueprint: `customer-support` · [All settings](https://sandaal.github.io/ai-app-server/build/blueprints/) · [ai-app.yaml reference](https://sandaal.github.io/ai-app-server/build/manifest/)
