# Local models (your own hardware)

The server can run models itself, so no data leaves your machines and calls cost nothing per token. It uses two inference engines:

- **llama.cpp on CPU:** any server or laptop. The Docker image includes it.
- **vLLM on NVIDIA or AMD GPUs.**

The server starts the engines, restarts them if they crash, and stops them when it stops. Apps call local models like any other model, and you can move an app between a hosted model and a local one by changing configuration only.

## 1. Get a model

```bash
aiapp model list --catalog              # models the server can download by name
aiapp model pull qwen2.5-1.5b-instruct  # a chat model (1.1 GB)
aiapp model pull nomic-embed-text-v1.5  # an embedding model for document search (140 MB)
```

| Catalog model | Kind | Size | Good for |
|---|---|---|---|
| `qwen2.5-0.5b-instruct` | chat | 470 MB | tests, simple tasks, slow CPUs |
| `qwen2.5-1.5b-instruct` | chat | 1.1 GB | chat and tool calling on a CPU |
| `nomic-embed-text-v1.5` | embedding | 140 MB | document search (768 dimensions) |

The catalog models are Apache-2.0 licensed. Any other model in GGUF format works too: give its URL and SHA-256.

```bash
aiapp model pull llama-3.1-8b --url https://huggingface.co/…/Llama-3.1-8B-Instruct-Q4_K_M.gguf --sha256 9f3a…
```

!!! info "Every download is checked"
    The server checks each download's SHA-256 against the catalog or `--sha256`, and discards the file if they differ. A model is code the server runs, so a pull without a checksum is refused.

**Servers without internet access:** copy the file over, then import it with `aiapp model import NAME /path/to/model.gguf --sha256 …`. A folder works too, for vLLM models in the Hugging Face format.

Stored models live in `<data-dir>/models/`. `aiapp model list` shows them, and `aiapp model rm NAME` deletes one, unless a local model still uses it.

## 2. Run it

Add the models to `gateway.yaml` in the data folder, under `local:`, then run `aiapp gateway reload` (or restart the server):

```yaml
local:
  qwen:  { engine: llama.cpp, model: qwen2.5-1.5b-instruct, context: 4096, threads: 8 }
  embed: { engine: llama.cpp, model: nomic-embed-text-v1.5, embeddings: true }
```

`aiapp model list` shows each local model's state: `starting` while it loads, then `ready`.

| Setting | Meaning |
|---|---|
| `engine` | `llama.cpp` (CPU, or GPU with a CUDA build) or `vllm` (GPU) |
| `model` | one of: a stored model; a path to a `.gguf` file or a model folder; or, for vLLM, a Hugging Face id such as `Qwen/Qwen2.5-7B-Instruct`, which vLLM downloads itself |
| `context` | context length in tokens (llama.cpp default 4096) |
| `threads` | CPU threads (llama.cpp) |
| `parallel` | requests answered at once (llama.cpp slots) |
| `embeddings` | serve embeddings instead of chat (llama.cpp) |
| `gpus` / `gpu_ids` | how many GPUs the model gets, or exactly which ones |
| `gpu_memory` | memory the model needs on each GPU, e.g. `20GB`; only GPUs that have it are used |
| `args`, `env` | extra engine arguments and environment variables |
| `replicas` | run this many engines for the model, each with its own GPUs (see below) |
| `routing` | how requests are spread over replicas: `prefix` (default) or `round-robin` |
| `cache_ram` | llama.cpp's RAM tier for evicted prompt caches, e.g. `4GB` (`"0"` turns it off; default 8 GB) |

A model that isn't pulled yet waits, without blocking the others. `aiapp model list` shows it as `failed`, with the `aiapp model pull` command to run, and it starts as soon as the pull finishes.

## 3. Use it in apps

Directly, in the app's `ai-app.yaml`:

```yaml
models:
  chat:      { provider: local, model: qwen }
  embedding: { provider: local, model: embed }
```

Or through a logical model, so that apps never name the provider:

```yaml
# gateway.yaml
deployments:
  local-qwen: { provider: local, model: qwen }
  gpt:        { provider: openai, model: gpt-4o-mini }
models:
  chat: { targets: [local-qwen], fallback: [gpt] }   # local first; hosted if the engine is down
```

```yaml
# ai-app.yaml
models:
  chat: { use: chat }
```

To move every app from hosted to local, or back, change `targets:` and run `aiapp gateway reload`. The apps don't change.

Everything an app does with a model works with local models:

- streaming, structured output (`json`) and tool-calling agents (`run`);
- embeddings and document search;
- guardrails, budgets, logs and traces.

Calls made while an engine is loading wait for it, for up to 3 minutes. If an engine can't start, calls fail with a retryable error, so a `fallback:` takes over.

## Faster answers for long contexts (context memory)

An engine keeps the computed prompt (its KV cache) for each conversation, so a follow-up question that starts with the same long context doesn't recompute it. The time to first token then falls from seconds to milliseconds. This holds for the same system prompt, retrieved documents and earlier turns. Two settings keep that cache useful:

- **Prefix-aware routing:** with `replicas: N`, each conversation keeps going to the replica that already holds its context. A new conversation goes to the replica with the fewest active conversations, and it moves only if its replica is much busier than the others.
- **A RAM tier:** when an engine's slots are full, older prompt caches move to RAM (`cache_ram`) instead of being discarded, and are restored on the next turn.

```yaml
local:
  qwen: { engine: llama.cpp, model: qwen2.5-1.5b-instruct, replicas: 2, parallel: 4, cache_ram: 4GB }
```

Measured with `scripts/bench-context.sh` (llama.cpp on 8 CPU cores, Qwen2.5 0.5B, six conversations with about 800 tokens of context each, asked in a random order):

| Setup | Warm time to first token (mean) | Cache hits |
|---|---|---|
| 2 replicas, round-robin | 1.21 s (p90 3.42 s) | 8 of 12 |
| 2 replicas, prefix routing | **0.08 s** (p90 0.08 s) | 12 of 12 |
| 1 replica with 1 slot, RAM tier off | 3.53 s | 1 of 12 |
| 1 replica with 1 slot, RAM tier 2 GB | **0.12 s** | 12 of 12 |

The same routing works across inference servers you run yourself (for example several vLLM instances): give the logical model `routing: prefix` in `gateway.yaml`, as shown in [Model providers](models.md). vLLM's own prefix caching is on by default.

## GPUs and vLLM

vLLM isn't in the Docker image, because GPU images are many gigabytes. Install it where the server runs (`pip install vllm`, see the [vLLM docs](https://docs.vllm.ai)), or point `--vllm` (or `AIAPP_VLLM`) at it.

```yaml
local:
  qwen7b:  { engine: vllm, model: Qwen/Qwen2.5-7B-Instruct, gpus: 1, gpu_memory: 20GB, context: 8192 }
  llama70: { engine: vllm, model: /models/Llama-3.1-70B-Instruct, gpus: 4 }   # tensor parallel over 4 GPUs
```

**How GPUs are given out:**

- **Detection:** the server finds the GPUs with `nvidia-smi`.
- **No sharing:** each GPU runs one model. A model with `gpus: N` gets its own N GPUs, and vLLM gets `--tensor-parallel-size N`.
- **Which GPUs:** the engine sees only its own, through `CUDA_VISIBLE_DEVICES` and `HIP_VISIBLE_DEVICES`.
- **Not enough GPUs:** if the GPUs can't hold every model, `aiapp gateway reload` refuses the change and says what is free.
- **AMD or other machines:** where `nvidia-smi` doesn't apply, list the GPUs with `AIAPP_GPUS=0:24GB,1:24GB`, or `2x80GB`. The same variable limits the server to some of a machine's GPUs.

!!! warning "Not yet tested on GPUs"
    The GPU features are tested against emulated GPUs. This covers how GPUs are given out, the vLLM command line and supervision. They have not yet been run on GPU hardware. CPU inference with llama.cpp is tested end to end with real models.

## Where things are

| What | Where |
|---|---|
| Stored models | `<data-dir>/models/NAME/` |
| Engine output (load errors, crashes) | `<data-dir>/logs/inference/NAME.log` |
| llama.cpp | `--llama-server` or `AIAPP_LLAMA_SERVER`; the Docker image has it at `/opt/llama/llama-server` |
| vLLM | `--vllm` or `AIAPP_VLLM` |

`aiapp backup` doesn't copy `<data-dir>/models`. After a restore, pull the models again; their checksums are in `gateway.yaml` or the catalog.
