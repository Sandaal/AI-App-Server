# Model providers

Store provider keys with the server. They are encrypted and never written into app files:

```bash
aiapp secret set OPENAI_API_KEY        # asks for the value
```

Environment variables work too (`OPENAI_API_KEY=… aiapp serve`, or `/etc/aiapp/env` for the Linux service).

## Providers

| Provider | `aiapp new … --provider` | Secrets |
|---|---|---|
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Azure OpenAI | `azure-openai` | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`; set the deployment names in `ai-app.yaml` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY`, plus `OPENAI_API_KEY` for embeddings (Anthropic has none) |
| Google Gemini | `gemini` | `GEMINI_API_KEY` |
| AWS Bedrock | `bedrock` | `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| Ollama (local, free) | `ollama` | none; first run `ollama pull llama3.2 && ollama pull nomic-embed-text` |
| vLLM, LM Studio, other OpenAI-compatible | edit `ai-app.yaml` | depends on the server |

## In an app

Each app names the models it uses, usually `chat` and `embedding`:

```yaml
models:
  chat:      { provider: openai, model: gpt-4o-mini }
  embedding: { provider: openai, model: text-embedding-3-small }
```

```yaml
# Azure OpenAI: use your deployment names
models:
  chat:      { provider: azure-openai, deployment: gpt-4o-mini }
  embedding: { provider: azure-openai, deployment: text-embedding-3-small }
```

```yaml
# Any OpenAI-compatible server
models:
  chat: { provider: openai-compatible, endpoint: "http://gpu-box:8000/v1", model: llama-3.1-8b, api_key_env: VLLM_KEY }
```

**Useful settings on a model:**

| Setting | What it does |
|---|---|
| `fallback: anthropic/claude-haiku-5-5` | used when the main model fails or is down |
| `api_key_env: MY_KEY` | which secret holds the key (also `kv:NAME` or `vault:PATH#KEY`, see [Secrets](../operate/secrets.md)) |
| `price: { input: 0.15, output: 0.60 }` | USD per million tokens, for cost tracking and budgets |
| `cache: false` | turn off the answer cache for this model |
| `semantic_cache: …` | reuse answers to near-identical questions in the same conversation context |

## For operators: one model setup for all apps

Describe deployments once in `DATA_DIR/gateway.yaml`, with weighted routing, fallbacks and prices:

```yaml
deployments:
  gpt-east: { provider: azure-openai, deployment: gpt-4o, endpoint: "https://east.openai.azure.com", api_key_env: AZURE_EAST_KEY, weight: 3 }
  gpt-west: { provider: azure-openai, deployment: gpt-4o, endpoint: "https://west.openai.azure.com", api_key_env: AZURE_WEST_KEY }
  claude:   { provider: anthropic, model: claude-haiku-5-5 }
models:
  chat: { targets: [gpt-east, gpt-west], fallback: [claude] }
prices:
  anthropic/claude-haiku-5-5: { input: 1.0, output: 5.0 }    # USD per million tokens
```

Apps then refer to the logical name: `models: { chat: { use: chat } }`. After editing, run `aiapp gateway reload`. `aiapp gateway` shows each deployment's health (circuit breakers) and the cache.
