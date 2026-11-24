# Ops agent

An agent that carries out tasks with your tools and MCP servers; chosen tools (like refunds) wait for a person's approval.

## What's in this folder

| | |
|---|---|
| `ai-app.yaml` | the app: models, settings, guardrails, page |
| `tools.py` | the agent's tools (examples: order and customer lookup, refund) |

`.github/copilot-instructions.md` teaches coding assistants this SDK.

## Run it

You need a running server ([install](https://sandaal.github.io/ai-app-server/install/)) and a model key:

```bash
aiapp secret set OPENAI_API_KEY          # or use another provider, see below
cd ops-agent
aiapp deploy
```

Open **http://127.0.0.1:8080/apps/ops-agent/** for the task page.

Or call it:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"task":"Order A-1001 was lost in transit. Refund it and summarise for the customer."}' \
  "http://127.0.0.1:8080/apps/ops-agent/run?wait=60"
```

## Extend it

- **Your tools:** replace `tools.py` with functions for your systems; the docstrings are what the agent reads.
- **MCP servers:** add tools from any MCP server under `mcp:` ([guide](https://sandaal.github.io/ai-app-server/build/agents/)).
- **Approvals:** list risky tools in `agent.approval_required`; decide at `/apps/ops-agent/_approvals/` or with `aiapp approve`.
- **Let other agents use it:** publish tools with `mcp_server:` ([guide](https://sandaal.github.io/ai-app-server/build/mcp-server/)).

## Change it and redeploy

1. Copy this folder into your own repository (keep the folder; rename `app:` in `ai-app.yaml` if you like).
2. Make your changes. While you work, `aiapp dev` redeploys on every save and keeps the last good version if something breaks.
3. Check it: `aiapp test` (if there is a `tests/` folder) and `aiapp eval` (with `evals/`).
4. Deploy to your server: `aiapp deploy`. Every deploy is a new version with no downtime; `aiapp rollback` goes back.

**Another model provider:** change `models:` in `ai-app.yaml` (Azure OpenAI, Anthropic, Gemini, Bedrock, or a local Ollama), see [Model providers](https://sandaal.github.io/ai-app-server/install/models/).

**Before others use it:** API keys or sign-in, HTTPS and quotas, see the [security checklist](https://sandaal.github.io/ai-app-server/operate/security/).

Blueprint: `workflow-agent` · [All settings](https://sandaal.github.io/ai-app-server/build/blueprints/) · [ai-app.yaml reference](https://sandaal.github.io/ai-app-server/build/manifest/)
