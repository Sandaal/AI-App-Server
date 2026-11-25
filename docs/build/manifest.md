# The ai-app.yaml file

Every app has one. Your editor can check it: `aiapp schema` prints its JSON Schema, and the [VS Code extension](vscode.md) uses it for completion.

```yaml
app: hr-bot                 # name: 2-63 lowercase letters, digits or hyphens; the URL is /apps/hr-bot/
version: "1.2.0"            # your version label; every deploy also gets a number
blueprint: knowledge-chat   # optional: a ready-made app type
runtime: python3.12         # or node: handlers in JavaScript (see JavaScript handlers)
workers: 2                  # worker processes for this app
rate_limit: 600             # requests per minute per client (optional)

models:                     # model names your app uses: app.models.chat, app.models.embedding
  chat:      { provider: openai, model: gpt-4o-mini, fallback: anthropic/claude-haiku-5-5 }
  embedding: { provider: openai, model: text-embedding-3-small }

sources:                    # documents to answer from
  - path: ./policies/
  - { name: handbook, git: { url: "https://github.com/contoso/handbook", token: "${GITHUB_TOKEN}" }, schedule: 1h }

routes:                     # your own HTTP routes; listing them replaces a blueprint's defaults,
  - { path: /chat }           #   so list the blueprint's routes too (path only: the handler is filled in)
  - { path: /ask, handler: "handlers:ask", stream: true, roles: [staff] }

jobs:                       # background work
  - { name: report, handler: "handlers:report", max_attempts: 3, timeout: 10m }
cron:                       # schedules
  - { name: nightly, schedule: "0 2 * * *", job: report, timezone: Europe/Paris }
topics:                     # event streams
  orders: { partitions: 4, retention: 7d }
subscriptions:              # handlers called for each event
  - { topic: orders, handler: "handlers:on_order", max_attempts: 5 }

guardrails:                 # checks on requests and answers
  - pii-redaction
  - prompt-injection
  - citations-required: { routes: [/chat] }

mcp:                        # MCP servers whose tools your app can use
  - { name: crm, url: "https://crm.example.com/mcp", headers: { Authorization: "Bearer ${CRM_TOKEN}" } }
mcp_server:                 # publish your tools and routes to AI agents
  tools: [lookup_order]
  roles: [mcp]

auth:                       # sign-in (API keys work without this)
  oidc: { issuer: "https://login.microsoftonline.com/TENANT/v2.0", audience: ["api://hr-bot"], client_id: "..." }
cors: { origins: ["https://intranet.contoso.com"] }
ui: chat-widget             # built-in page, or a folder of your own: ui: ./ui
```

## Sections

| Section | Guide |
|---|---|
| `models` | [Model providers](../install/models.md) |
| `sources` | [Documents and connectors](documents.md) |
| `routes`, `runtime` | [Python handlers](handlers.md), [JavaScript handlers](node.md) |
| `jobs`, `cron`, `topics`, `subscriptions` | [Jobs, schedules and events](jobs-events.md) |
| `guardrails`, `guardrail_mode` | [Guardrails](guardrails.md) |
| `mcp`, `agent` | [Agents, tools and MCP](agents.md) |
| `mcp_server` | [Publish apps to AI agents](mcp-server.md) |
| `auth`, `cors` | [Sign-in](../operate/sign-in.md), [Pages](web.md) |
| `ui` | [Pages and web components](web.md) |
| `cluster` | [Clusters](../operate/cluster.md#placement-and-routing) |
| `confidential` | [Confidential apps](../operate/confidential.md) |
| `insights`, `support`, `summary`, `classification`, `meeting_notes`, `content` | [Blueprint settings](blueprints.md) |

## Values from secrets

Anywhere in connector and MCP settings, `${NAME}` is replaced by a secret or environment variable, `${kv:NAME}` by an Azure Key Vault secret, and `${vault:MOUNT/PATH#KEY}` by a HashiCorp Vault secret. Never put keys in the file itself. See [Secrets and vaults](../operate/secrets.md).

## Environments

`ai-app.prod.yaml` next to `ai-app.yaml` is merged over it when you run `aiapp deploy --env prod` (or the server runs with `--env prod`). Use it for other models, quotas or sign-in in production:

```yaml
# ai-app.prod.yaml
models:
  chat: { use: chat }        # the operator's model setup in production
auth:
  oidc: { issuer: "https://login.microsoftonline.com/TENANT/v2.0", audience: ["api://hr-bot"] }
```
