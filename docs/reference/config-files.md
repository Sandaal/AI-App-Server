# Server configuration files

Apps are configured in their own `ai-app.yaml`. The server itself needs no configuration file; these optional files add operator features. They live in the data folder (or pass the flag), and are read at start.

| File | Flag / variable | Helm value | For |
|---|---|---|---|
| `gateway.yaml` | `--gateway FILE` | `gateway:` | shared model deployments, routing, fallbacks, prices; `aiapp gateway reload` re-reads it |
| `console.yaml` | `--console-config FILE`, `AIAPP_CONSOLE_CONFIG` | `console:` | the hosted console with sign-in |
| `audit-export.yaml` | `--audit-export FILE`, `AIAPP_AUDIT_EXPORT` | `auditExport:` | sending the audit log to a SIEM |

## gateway.yaml

```yaml
deployments:
  gpt-east: { provider: azure-openai, deployment: gpt-4o, endpoint: "https://east.openai.azure.com", api_key_env: AZURE_EAST_KEY, weight: 3 }
  gpt-west: { provider: azure-openai, deployment: gpt-4o, endpoint: "https://west.openai.azure.com", api_key_env: AZURE_WEST_KEY }
  claude:   { provider: anthropic, model: claude-haiku-5-5 }
models:
  chat: { targets: [gpt-east, gpt-west], fallback: [claude] }
prices:
  anthropic/claude-haiku-5-5: { input: 1.0, output: 5.0 }   # USD per million tokens
```

Apps use it with `models: { chat: { use: chat } }`. See [Model providers](../install/models.md).

## console.yaml

```yaml
public_url: https://ai.example.com
oidc:
  issuer: https://login.microsoftonline.com/TENANT_ID/v2.0
  client_id: APP_REGISTRATION_CLIENT_ID
  client_secret_env: CONSOLE_CLIENT_SECRET   # optional (public clients use PKCE only); kv:/vault: work
  scopes: [openid, profile, email]           # default
  roles_claim: roles                         # or groups
roles:                                       # claim value -> viewer | auditor | operator | admin
  AIApp.Viewers: viewer
  AIApp.Admins: admin
session: 8h                                  # at most 168h
```

Without `roles:`, claim values named `viewer`, `auditor`, `operator` or `admin` are used as they are. See [The console](../operate/console.md).

## audit-export.yaml

```yaml
sinks:
  - { name: siem, type: syslog, address: "siem.internal:6514", network: tls }   # network: tcp (default), tls, udp
  - { name: splunk, type: http, url: "https://splunk:8088/services/collector", format: splunk,
      headers: { Authorization: "Splunk ${vault:secret/siem#hec}" } }
  - { name: otel, type: otlp, endpoint: "http://otel-collector:4318", headers: { api-key: "${OTLP_KEY}" } }
exclude: [key]          # fields never exported
redact_pii: true        # default
```

Each sink also takes `batch:` (default 100), `queue:` (default 10000) and `insecure_skip_verify:` (test SIEMs only). See [Audit log](../operate/audit.md).

## The data folder

| Path | What |
|---|---|
| `master.key` | the encryption key: back it up separately |
| `admin.sock` | the CLI's connection to the server |
| `audit/`, `blobs/`, `versions/`, the database files | encrypted data; back up with `aiapp backup` |
