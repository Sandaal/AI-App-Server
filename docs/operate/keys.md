# API keys and roles

## Keys

```bash
aiapp key create hr-bot --name website          # prints the key once: store it safely
aiapp key list hr-bot
aiapp key revoke hr-bot KEY_ID
```

**Once an app has a key, every caller needs one** (or a sign-in token): `Authorization: Bearer KEY` (or `X-API-Key: KEY`). Keys are stored hashed; a lost key can't be shown again, only replaced.

To require credentials before you have created any key:

```yaml
auth:
  required: true
```

## Roles

Give keys roles, and require roles on routes:

```bash
aiapp key create support --name agents --role refunds --role approver
```

```yaml
routes:
  - { path: /refund, handler: "handlers:refund", roles: [refunds] }
```

| Built-in role | Allows |
|---|---|
| `admin` | everything, including routes that require other roles |
| `approver` | deciding workflow approvals (`/apps/APP/_approvals/`) |
| `read-logs` | the app's model-call log at `/apps/APP/_logs` |
| `kv` | signing in to the [Redis protocol](../build/redis.md) to use the app's key-value data |
| `mcp` (by convention) | the app's MCP endpoint, when `mcp_server.roles: [mcp]` |

Any other name works as your own role. In handlers: `req.principal.has_role("refunds")`.

## Budgets per key

Model budgets can be set per app and per key; see [Quotas](quotas.md).
