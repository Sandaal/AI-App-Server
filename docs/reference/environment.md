# Environment variables

## Server

| Variable | Same as | Meaning |
|---|---|---|
| `AIAPP_DATA_DIR` | `--data-dir` | data folder (default `~/.aiapp`); also used by CLI commands |
| `AIAPP_APPS_DIR` | `--apps-dir` | deploy every app folder in it at start |
| `AIAPP_ENV` | `--env` | default environment overlay (`ai-app.ENV.yaml`) |
| `AIAPP_PUBLIC_URL` | `--public-url` | the server's address as browsers see it (page sign-in) |
| `AIAPP_METRICS_ADDR` | `--metrics-addr` | serve Prometheus `/metrics` here |
| `AIAPP_VECTOR_QUANTIZATION` | `--vector-quantization` | `auto` (default: int8 when vectors outgrow their memory budget), `int8` or `none` |
| `AIAPP_HAL_PROFILE` | | emulate a machine: a built-in profile (`gpu-server`, `grace-hopper`, …) or a JSON file from `aiapp hardware --save` |
| `AIAPP_PYTHON` | `--python` | Python interpreter for workers |
| `AIAPP_NODE` | `--node` | Node.js for apps with `runtime: node` |
| `AIAPP_NPM` | | npm, for Node apps' dependencies |
| `AIAPP_LLAMA_SERVER` | `--llama-server` | llama.cpp server for [local models](../install/local-models.md) |
| `AIAPP_VLLM` | `--vllm` | vLLM for local models on GPUs |
| `AIAPP_RESP_ADDR` | `--resp-addr` | serve the [Redis protocol](../build/redis.md) here |
| `AIAPP_RESP_TLS_CERT`, `AIAPP_RESP_TLS_KEY` | `--resp-tls-cert`, `--resp-tls-key` | TLS for the Redis protocol |
| `AIAPP_CLUSTER_ADDR` | `--cluster-addr` | Raft address for [clustering](../operate/cluster.md) (cluster API on the next port) |
| `AIAPP_CLUSTER_ADVERTISE` | `--cluster-advertise` | the address other nodes use to reach this one |
| `AIAPP_NODE_ID` | `--node-id` | this node's name in the cluster |
| `AIAPP_GPUS` | | GPUs to use, instead of detecting them: `0:24GB,1:24GB` or `2x80GB` |
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
