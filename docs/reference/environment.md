# Environment variables

## Server

| Variable | Same as | Meaning |
|---|---|---|
| `AIAPP_DATA_DIR` | `--data-dir` | data folder (default `~/.aiapp`); also used by CLI commands |
| `AIAPP_APPS_DIR` | `--apps-dir` | deploy every app folder in it at start |
| `AIAPP_ENV` | `--env` | default environment overlay (`ai-app.ENV.yaml`) |
| `AIAPP_PUBLIC_URL` | `--public-url` | the server's address as browsers see it (page sign-in) |
| `AIAPP_METRICS_ADDR` | `--metrics-addr` | serve Prometheus `/metrics` here |
| `AIAPP_VECTOR_QUANTIZATION` | `--vector-quantization` | `int8` to store vectors in a quarter of the memory |
| `AIAPP_PYTHON` | `--python` | Python interpreter for workers |
| `AIAPP_UV` | | path to `uv` |
| `AIAPP_WHEELHOUSE` | `--wheelhouse` | install Python packages only from this folder (offline) |
| `AIAPP_MASTER_KEY_FILE` | | read the master key from this file |
| `AIAPP_CONSOLE_CONFIG` | `--console-config` | hosted console settings |
| `AIAPP_AUDIT_EXPORT` | `--audit-export` | audit export settings |
| `AIAPP_SECRET_TTL` | | how long vault secrets are cached (default `5m`) |

## Model providers

`OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`. Prefer `aiapp secret set` to environment variables.

## Vaults

| Variable | For |
|---|---|
| `AZURE_KEY_VAULT_URL` | Azure Key Vault (`kv:` references) |
| `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_FEDERATED_TOKEN_FILE` | Entra ID sign-in for Key Vault and Content Safety (managed identity needs none) |
| `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_ROLE_ID`, `VAULT_SECRET_ID`, `VAULT_K8S_ROLE`, `VAULT_K8S_MOUNT`, `VAULT_NAMESPACE` | HashiCorp Vault (`vault:` references) |

## Guardrails

`AZURE_CONTENT_SAFETY_ENDPOINT`, `AZURE_CONTENT_SAFETY_KEY` for `azure-content-safety`.

## OpenTelemetry

`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_{TRACES,METRICS,LOGS}_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_{TRACES,METRICS,LOGS}_EXPORTER=none`, `OTEL_METRIC_EXPORT_INTERVAL`. See [Monitoring](../operate/monitoring.md).
