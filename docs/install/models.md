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
| Local models run by the server (llama.cpp, vLLM) | `provider: local`, see [Local models](local-models.md) | none |
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

Several inference servers of your own (for example vLLM instances) can share one logical model with `routing: prefix`. Requests that share a prompt prefix (a conversation, or the same long system prompt) then go to the same server, which reuses its KV cache:

```yaml
deployments:
  vllm-a: { provider: openai-compatible, model: llama-3.1-8b, endpoint: "http://gpu-a:8000/v1" }
  vllm-b: { provider: openai-compatible, model: llama-3.1-8b, endpoint: "http://gpu-b:8000/v1" }
models:
  chat: { targets: [vllm-a, vllm-b], routing: prefix }
```

Apps then refer to the logical name: `models: { chat: { use: chat } }`. After editing, run `aiapp gateway reload`. `aiapp gateway` shows each deployment's health (circuit breakers), its measured time to first token, the calls it has in progress, and the cache.

### Routing by request, latency and cost

One logical model can mix hardware and providers: a small model on CPUs, a local GPU model, a hosted model and an engine built for long contexts. The gateway then sends each request to the deployment that suits it.

**Conditions** on a deployment limit the requests it takes:

| Setting | The deployment takes |
|---|---|
| `max_prompt_tokens: N` | prompts up to about N tokens (its context window) |
| `min_prompt_tokens: N` | only prompts of at least N tokens (long-context engines, prefill-heavy work) |
| `max_output_tokens: N` | only requests that set `max_tokens` to N or less (classification, extraction) |

Prompts are estimated at four characters a token. A request no deployment takes fails with an error that says how long it was.

**Routing strategies:**

| `routing:` | Picks |
|---|---|
| `weighted` (default) | at random, by `weight` |
| `prefix` | the same deployment for requests that share a prompt prefix |
| `latency` | the deployment predicted to answer first: its measured time to first token, times the calls it is already serving |
| `cost` | the cheapest deployment predicted to answer within `latency_target_ms`, and the fastest if none can |

```yaml
deployments:
  classify: { provider: local, model: qwen-0.5b, max_prompt_tokens: 2000, max_output_tokens: 16 }
  local:    { provider: local, model: qwen-7b, max_prompt_tokens: 8000 }
  hosted:   { provider: openai, model: gpt-4o-mini }
  longctx:  { provider: openai-compatible, model: llama-3.1-70b, endpoint: "http://dynamo:8000/v1", min_prompt_tokens: 8001 }
models:
  chat: { targets: [classify, local, hosted, longctx], routing: cost, latency_target_ms: 1500 }
prices:
  openai/gpt-4o-mini: { input: 0.15, output: 0.6 }
```

With this setup:

- a short classification goes to the small model;
- a prompt over 8,000 tokens goes to the long-context engine;
- other chats go to the free local model while it answers within 1.5 seconds. When requests queue on it, they go to the hosted model.

Deployments without a price count as free, so give hosted ones their `prices:`. A deployment that hasn't been measured yet is tried and measured first.

**Budgets:** when an app has used 80% of a daily or monthly model budget (`aiapp quota set APP --daily-usd …`), its `cost`-routed models take the cheapest deployment even if it misses the latency target.

**Prefill/decode-split engines** (NVIDIA Dynamo, vLLM's disaggregated serving, llm-d) do their split inside the engine. Add each engine's OpenAI-compatible endpoint as a deployment, and use conditions to send it the requests it is built for.
